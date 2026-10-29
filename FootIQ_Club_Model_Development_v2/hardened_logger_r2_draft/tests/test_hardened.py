"""Regression + new adversarial tests for the hardened logger (draft protocol r2). Official-path tests run ONLY in a sandbox inside the system temp directory with synthetic approvals;
no official ledger, approval file or official prediction is created in the project."""
import copy, json, os, re, shutil, stat, sys, unittest
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from helpers import *


def rm_ro(path):
    os.chmod(path, stat.S_IWRITE); os.remove(path)


def recs_for(n, prefix="F"):
    return [dict(fixture_id=f"{prefix}{i}", model_key="mk", probs={"x": i}, prediction_timestamp_utc="2026-10-21T15:00:00Z") for i in range(n)]


def new_ledger(name):
    root = os.path.join(TMP, name, "ledger"); anc = os.path.join(TMP, name, "anchor", "anchor.jsonl")
    return ledger.ChainedLedger(root, anc)


# ------------------------------------------------------------------------------------------------ artifacts
class TestArtifacts(unittest.TestCase):
    NAMES = ["model_v1_original_preprocessing", "model_v1_elo_parameters", "elo2_parameters_and_meta", "code_v2_features", "model_v2_feature_contract", "feature_contract_v1", "model_matched_v1_preprocessing",
             "code_adapter_openligadb", "code_hardened_engine", "preprocessing_spec_v1"]

    def _copies(self):
        paths = artifacts.canonical_paths(); d = os.path.join(TMP, "art_copy"); os.makedirs(d, exist_ok=True); out = {}
        for k in self.NAMES + ["model_v1_original_pickle"]:
            dst = os.path.join(d, k + os.path.splitext(paths[k])[1]); shutil.copyfile(paths[k], dst); out[k] = dst
        return out

    def test_manifest_covers_everything_that_influences_a_prediction(self):
        m = artifacts.manifest()
        for k in ("model_v1_original_preprocessing", "model_v1_elo_parameters", "elo2_parameters_and_meta", "feature_contract_v1", "code_v2_features", "code_v1_feature_contract", "code_hardened_engine", "universe", "eligibility_exclusions"):
            self.assertIn(k, m)

    def test_each_tamper_is_detected(self):
        paths = self._copies(); exp = artifacts.manifest(paths)
        self.assertEqual(artifacts.verify(exp, paths), [])
        for k in list(paths):
            mutated = dict(paths)
            f = os.path.join(TMP, "art_copy", "mut_" + os.path.basename(paths[k])); shutil.copyfile(paths[k], f)
            with open(f, "ab") as fh: fh.write(b" ")
            mutated[k] = f
            self.assertTrue(any(k in p for p in artifacts.verify(exp, mutated)), k)

    def test_line_endings_do_not_change_text_digests(self):
        p = os.path.join(TMP, "crlf.json"); open(p, "wb").write(b'{"a": 1}\n'); h1 = artifacts.digest_file(p)
        q = os.path.join(TMP, "crlf2.json"); open(q, "wb").write(b'{"a": 1}\r\n'); self.assertEqual(h1, artifacts.digest_file(q))

    def test_prediction_aborts_when_feature_code_or_elo_or_preprocessing_changes(self):
        paths = self._copies(); exp = artifacts.manifest(paths)
        V, VS, RES = universe()
        for k in ("code_v2_features", "elo2_parameters_and_meta", "model_v1_original_preprocessing"):
            bad = dict(paths); f = os.path.join(TMP, "art_copy", "bad_" + k + os.path.splitext(paths[k])[1]); shutil.copyfile(paths[k], f); open(f, "ab").write(b" "); bad[k] = f
            with self.assertRaises(state.IntegrityError):
                engine.predict_core(VS, [real_snap()], T0 + pd.Timedelta(minutes=5), RES, exp, manifest_paths=bad)


# ------------------------------------------------------------------------------------------------ ledger
class TestLedger(unittest.TestCase):
    def test_duplicate_sealing_is_skipped_idempotently(self):
        L = new_ledger("dup"); r1 = L.append_batch(recs_for(3), "b1"); r2 = L.append_batch(recs_for(3), "b2"); r3 = L.append_batch(recs_for(5), "b3")
        self.assertEqual((r1["sealed"], r2["sealed"], r2["skipped"], r3["sealed"], r3["skipped"]), (3, 0, 3, 2, 3)); self.assertTrue(L.verify()["ok"]); self.assertEqual(len(L.records()), 5)

    def test_same_fixture_with_new_model_version_is_a_different_key(self):
        L = new_ledger("mk"); L.append_batch(recs_for(2), "a"); r = L.append_batch([dict(x, model_key="other") for x in recs_for(2)], "b"); self.assertEqual(r["sealed"], 2)

    def test_interrupted_writes_are_detected_and_recovered(self):
        for stage in ("intent", "partial", "tmp", "rename"):
            L = new_ledger("crash_" + stage); L.append_batch(recs_for(2), "good")
            with self.assertRaises(ledger.SimulatedCrash): L.append_batch(recs_for(2, "G"), "bad", _crash_after=stage)
            if os.path.exists(L.lock): os.remove(L.lock)
            v = L.verify(); self.assertFalse(v["ok"], stage)
            with self.assertRaises(ledger.LedgerError): L.append_batch(recs_for(1, "H"), "next")          # refuses to write on top of an unresolved interruption
            actions = L.recover(); self.assertTrue(actions, stage); v = L.verify(); self.assertTrue(v["ok"], (stage, v["errors"]))
            self.assertEqual(v["records"], 4 if stage == "rename" else 2, stage)                           # only the fully committed batch survives
            self.assertEqual(L.append_batch(recs_for(2, "G"), "retry")["sealed"], 0 if stage == "rename" else 2)

    def test_deleted_newest_batch_is_detected_by_the_anchor(self):
        L = new_ledger("tail"); L.append_batch(recs_for(2), "a"); r = L.append_batch(recs_for(2, "G"), "b")
        rm_ro(r["path"]); v = L.verify(); self.assertFalse(v["ok"]); self.assertTrue(any("deleted batch" in e for e in v["errors"]))

    def test_deleted_middle_reordered_and_modified_batches(self):
        L = new_ledger("mid"); p = [L.append_batch(recs_for(2, f"M{i}_"), f"b{i}")["path"] for i in range(3)]
        os.chmod(p[1], stat.S_IWRITE); os.rename(p[1], p[1] + ".moved")
        self.assertFalse(L.verify()["ok"])
        os.rename(p[1] + ".moved", p[1])
        a, b = p[0], p[2]; ta = a + ".x"; os.chmod(a, stat.S_IWRITE); os.chmod(b, stat.S_IWRITE)
        os.rename(a, ta); na = os.path.join(os.path.dirname(a), os.path.basename(b)[:7] + os.path.basename(a)[7:]); os.rename(ta, na)             # name collision-free swap attempt
        self.assertFalse(L.verify()["ok"])
        os.rename(na, a)
        os.chmod(p[0], stat.S_IWRITE); s = open(p[0], encoding="utf-8").read().replace('"x": 0', '"x": 9'); open(p[0], "w", encoding="utf-8").write(s)
        self.assertFalse(L.verify()["ok"])

    def test_missing_anchor_and_lock(self):
        L = new_ledger("anc"); L.append_batch(recs_for(2), "a"); os.remove(L.anchor_path); self.assertFalse(L.verify()["ok"])
        L2 = new_ledger("lock"); L2.append_batch(recs_for(1), "a"); open(L2.lock, "w").write("1")
        with self.assertRaises(ledger.LedgerError): L2.append_batch(recs_for(2, "Z"), "b")

    def test_batches_are_read_only_and_records_immutable(self):
        L = new_ledger("ro"); r = L.append_batch(recs_for(2), "a"); self.assertFalse(os.access(r["path"], os.W_OK))
        with self.assertRaises(PermissionError): open(r["path"], "a").write("x")


# ------------------------------------------------------------------------------------------------ approval
class TestApproval(unittest.TestCase):
    now = T0 + pd.Timedelta(minutes=30)

    def _v(self, path):
        return approval.validate_approval(path, self.now, expected_models=engine.E.verify_models(), expected_manifest_sha=artifacts.manifest_sha(artifacts.manifest()), competition_id=state.COMP, season=state.SEASON)

    def test_valid_approval_passes(self):
        p, a = mk_approval(self.now); self.assertEqual(self._v(p)["mode"], "official")

    def test_empty_missing_and_malformed_files(self):
        with self.assertRaises(approval.ApprovalError): self._v(os.path.join(TMP, "nope.json"))
        for name, content in (("empty.json", ""), ("braces.json", "{}"), ("junk.json", "not json"), ("list.json", "[1,2]"), ("null.json", "null")):
            p = os.path.join(TMP, name); open(p, "w").write(content)
            with self.assertRaises(approval.ApprovalError, msg=name): self._v(p)

    def test_expired_future_and_outside_window(self):
        for over in (dict(expires_utc=(self.now - pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")), dict(approved_utc=(self.now + pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")),
                     dict(sealing_window=dict(start_utc=(self.now + pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), end_utc=(self.now + pd.Timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%SZ")))):
            p, _ = mk_approval(self.now, "bad_time.json", **over)
            with self.assertRaises(approval.ApprovalError): self._v(p)

    def test_mismatched_models_manifest_scope_protocol_and_flags(self):
        hs = engine.E.verify_models()
        cases = {"model hash": dict(models=dict(hs, v2="0" * 64)), "manifest": dict(artifact_manifest_sha256="1" * 64), "competition": dict(competition_id="england:1-premierleague"), "season": dict(season="2025-26"),
                 "scope": dict(source_scope={"openligadb": {"league": "bl2", "season": "2026"}}), "mode": dict(mode="shadow"), "max": dict(max_fixtures=0), "matchdays": dict(matchdays=[])}
        for k, over in cases.items():
            p, _ = mk_approval(self.now, "m_" + k.replace(" ", "_") + ".json", **over)
            with self.assertRaises(approval.ApprovalError, msg=k): self._v(p)
        proto = mk_protocol(); p, a = mk_approval(self.now, "proto.json")
        bad = copy.deepcopy(a); bad["protocol"]["sha256"] = "2" * 64; json.dump(bad, open(p, "w"))
        with self.assertRaises(approval.ApprovalError) as cm: self._v(p)
        self.assertTrue(any("protocol file hash" in x for x in cm.exception.problems))
        bad["protocol"] = dict(version="r1", sha256=a["protocol"]["sha256"], path=a["protocol"]["path"]); json.dump(bad, open(p, "w"))
        with self.assertRaises(approval.ApprovalError): self._v(p)
        open(a["protocol"]["path"], "a").write("tampered after approval"); p2, _ = mk_approval(self.now, "proto2.json"); mk_protocol("# protocol r2 test file\n")

    def test_official_mode_is_off_by_default(self):
        old = os.environ.pop("FOOTIQ_OFFICIAL_MODE", None)
        try:
            self.assertFalse(approval.official_mode_enabled(True)); os.environ["FOOTIQ_OFFICIAL_MODE"] = "1"
            self.assertFalse(approval.official_mode_enabled(False)); self.assertTrue(approval.official_mode_enabled(True))
        finally:
            os.environ.pop("FOOTIQ_OFFICIAL_MODE", None)
            if old: os.environ["FOOTIQ_OFFICIAL_MODE"] = old
        self.assertFalse(os.path.exists(approval.CANONICAL_APPROVAL))


# ------------------------------------------------------------------------------------------------ source integrity
class TestSourceIntegrity(unittest.TestCase):
    def test_late_arriving_results_never_enter_earlier_predictions(self):
        ids = {m["matchID"] for m in NEW_RESULTS}
        early = mk_snap(strip_results(BASE, ids), "2026-10-20T10:00:00Z", "early"); real = real_snap()
        S1 = state_at([early, real], pd.Timestamp("2026-10-20T12:00:00Z")); S2 = state_at([early, real], T0 + pd.Timedelta(minutes=5))
        self.assertEqual((len(S1.additions), len(S2.additions)), (0, 18)); self.assertIn(real.snapshot_id, S1.excluded); self.assertNotEqual(S1.state_sha256, S2.state_sha256)

    def test_stale_snapshot_blocks_sealing_and_future_dated_snapshot_is_ignored(self):
        recs, rej, S = predict([real_snap()], T0 + pd.Timedelta(hours=25))
        self.assertEqual((len(recs), len(rej)), (0, 252)); self.assertEqual({w for _, w in rej}, {"stale_kickoff_snapshot"})
        r0, _, S0 = predict([real_snap()], T0 - pd.Timedelta(minutes=1)); self.assertEqual((len(r0), S0.used), (0, []))

    def test_out_of_order_and_duplicate_retrieval_time_snapshots_rejected(self):
        later = mk_snap(edit(BASE, NEW_RESULTS[0]["matchID"], lambda m: None, bump_update="2026-09-01T00:00:00"), T0 + pd.Timedelta(hours=1), "older_content")
        with self.assertRaises(state.OutOfOrderError): state_at([real_snap(), later], T0 + pd.Timedelta(hours=2))
        same = mk_snap(BASE, T0, "same_time")
        with self.assertRaises(state.OutOfOrderError): state_at([real_snap(), same], T0 + pd.Timedelta(hours=2))

    def test_wrong_league_or_season_snapshot_is_rejected(self):
        alt = copy.deepcopy(BASE)
        for m in alt: m["leagueSeason"] = 2025
        p = os.path.join(TMP, "wrong_season.json"); open(p, "w").write(json.dumps(alt)); json.dump(dict(sha256=hashlib.sha256(open(p, "rb").read()).hexdigest(), saved_utc="2026-10-21T14:30:00Z", snapshot_id="wrong_season.json"), open(p + ".meta.json", "w"))
        with self.assertRaises(state.ScopeError): state.load_snapshot(p)
        alt2 = copy.deepcopy(BASE)
        for m in alt2: m["leagueShortcut"] = "bl2"
        p2 = os.path.join(TMP, "wrong_league.json"); open(p2, "w").write(json.dumps(alt2)); json.dump(dict(sha256=hashlib.sha256(open(p2, "rb").read()).hexdigest(), saved_utc="2026-10-21T14:30:00Z", snapshot_id="wrong_league.json"), open(p2 + ".meta.json", "w"))
        with self.assertRaises(state.ScopeError): state.load_snapshot(p2)

    def test_withdrawn_result_quarantines_pair_and_blocks_clubs(self):
        nr = NEW_RESULTS[2]; wd = mk_snap(edit(BASE, nr["matchID"], lambda m: m.update(matchIsFinished=False, matchResults=[])), T0 + pd.Timedelta(hours=2), "withdrawn")
        recs, rej, S = predict([real_snap(), wd], T0 + pd.Timedelta(hours=3))
        self.assertEqual(len(S.additions), 17); self.assertTrue(any(e["kind"] == "withdrawn_result" for e in S.events))
        clubs = {nr["team1"]["teamName"], nr["team2"]["teamName"]}; aff = [r for r in recs if {r["home_team"], r["away_team"]} & clubs]
        self.assertTrue(aff and all(not r["primary_eligible"] and "incomplete_or_inconsistent_history" in r["eligibility_reasons"] for r in aff))

    def test_corrected_result_conflict(self):
        nr = NEW_RESULTS[0]; cor = mk_snap(edit(BASE, nr["matchID"], lambda m: set_score(m, 7, 7)), T0 + pd.Timedelta(hours=2), "corrected")
        S = state_at([real_snap(), cor], T0 + pd.Timedelta(hours=3)); self.assertEqual(len(S.additions), 17); self.assertTrue(any(e["kind"] == "corrected_result" for e in S.events))

    def test_duplicate_match_and_conflict_with_openfootball(self):
        d = copy.deepcopy(NEW_RESULTS[0]); d["matchID"] = 999999991
        S = state_at([mk_snap(BASE + [d], T0, "dup")], T0 + pd.Timedelta(minutes=5)); self.assertTrue(any(e["kind"] == "duplicate_ordered_pair" for e in S.events)); self.assertEqual(len(S.additions), 17)
        old = [m for m in BASE if m["matchIsFinished"] and m["matchDateTimeUTC"][:10] <= state.CUTOFF][0]
        S2 = state_at([mk_snap(edit(BASE, old["matchID"], lambda m: set_score(m, 9, 0)), T0, "cfo")], T0 + pd.Timedelta(minutes=5)); self.assertTrue(any(e["kind"] == "conflict_with_openfootball_score" for e in S2.events))

    def test_missing_played_matches_block_clubs_or_competition(self):
        nr = NEW_RESULTS[0]
        un = mk_snap(edit(BASE, nr["matchID"], lambda m: m.update(matchResults=[{"resultTypeKind": "Unknown", "pointsTeam1": 1, "pointsTeam2": 0}])), T0, "unclassified")
        recs, _, S = predict([un], T0 + pd.Timedelta(minutes=5)); clubs = {nr["team1"]["teamName"], nr["team2"]["teamName"]}
        self.assertTrue(any(e["kind"] == "played_match_no_explicit_90min_result" for e in S.events))
        self.assertTrue(all(not r["primary_eligible"] for r in recs if {r["home_team"], r["away_team"]} & clubs))
        unk = mk_snap(edit(BASE, nr["matchID"], lambda m: m["team1"].update(teamName="Unknown Club XY")), T0, "unknown_team")
        recs2, _, S2 = predict([unk], T0 + pd.Timedelta(minutes=5)); self.assertTrue(S2.competition_blocked); self.assertEqual(sum(r["primary_eligible"] for r in recs2), 0)
        frozen_played = [m for m in BASE if m["matchIsFinished"] and m["matchDateTimeUTC"][:10] <= state.CUTOFF][0]
        gone = mk_snap([m for m in BASE if m["matchID"] != frozen_played["matchID"]], T0, "missing_known")
        S3 = state_at([gone], T0 + pd.Timedelta(minutes=5)); self.assertTrue(any(e["kind"] == "known_match_missing_in_source" for e in S3.events))

    def test_removed_fixture_and_postponed_in_newest_snapshot(self):
        up = [m for m in BASE if not m["matchIsFinished"]][5]
        rem = mk_snap([m for m in BASE if m["matchID"] != up["matchID"]], T0 + pd.Timedelta(hours=1), "removed")
        S = state_at([real_snap(), rem], T0 + pd.Timedelta(hours=2)); self.assertTrue(any(e["kind"] == "fixture_removed_in_newest_snapshot" for e in S.events))

    def test_second_source_openfootball_agreement_and_conflict(self):
        V, VS, RES = universe(); nr = NEW_RESULTS[0]
        he = RES.resolve("openligadb", state.COMP, nr["team1"]["teamName"])[0]; ae = RES.resolve("openligadb", state.COMP, nr["team2"]["teamName"])[0]
        h, a = [(r["pointsTeam1"], r["pointsTeam2"]) for r in nr["matchResults"] if r["resultTypeKind"] == "After90Minutes"][0]
        s1 = pd.DataFrame([dict(record_id="of1", match_date=nr["matchDateTimeUTC"][:10], home_entity_id=he, away_entity_id=ae, gh=h, ga=a, retrieved_utc="2026-10-21T13:00:00Z", snapshot_sha256="a" * 64)])
        S = state_at([real_snap()], T0 + pd.Timedelta(minutes=5), s1_additions=s1)
        self.assertEqual(len(S.additions), 18); self.assertEqual(S.additions.agreement.value_counts().to_dict(), {"single_source": 17, "two_sources_agree": 1})
        S2 = state_at([real_snap()], T0 + pd.Timedelta(minutes=5), s1_additions=s1.assign(gh=h + 3))
        self.assertEqual(len(S2.additions), 17); self.assertTrue(any(e["kind"] == "conflict_between_sources_score" for e in S2.events)); self.assertTrue(S2.blocked_clubs)
        S3 = state_at([real_snap()], T0 - pd.Timedelta(minutes=5), s1_additions=s1.assign(retrieved_utc="2026-10-22T00:00:00Z"))
        self.assertEqual(len(S3.additions), 0)


# ------------------------------------------------------------------------------------------------ reassessment
class TestReassessment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.T = T0 + pd.Timedelta(minutes=30)
        recs, _, _ = predict([real_snap()], cls.T); cls.recs = recs
        cls.rec = min(recs, key=lambda r: r["scheduled_kickoff_utc"]); cls.mid = int(cls.rec["ol_match_id"])
        cls.RES = universe()[2]

    def _a(self, snaps, T_eval, checkpoint=False):
        return engine.reassess([self.rec], [real_snap()] + snaps, T_eval, self.RES, analysis_checkpoint=checkpoint)[0]

    def _later(self, fn, hours, label):
        return mk_snap(edit(BASE, self.mid, fn), T0 + pd.Timedelta(hours=hours), label)

    def test_rescheduled_postponed_and_stale_after_reschedule(self):
        a = self._a([self._later(lambda m: m.update(matchDateTimeUTC="2026-10-25T16:30:00Z"), 3, "r1")], T0 + pd.Timedelta(hours=4)); self.assertEqual(a["evaluation_eligibility"], "eligible_flagged_rescheduled"); self.assertIn("rescheduled_later", a["flags"])
        b = self._a([self._later(lambda m: m.update(matchDateTimeUTC="2026-11-20T16:30:00Z"), 3, "r2")], T0 + pd.Timedelta(hours=4)); self.assertIn("postponed_7_days_or_more", b["flags"]); self.assertEqual(b["evaluation_eligibility"], "ineligible_stale_after_reschedule")
        c = self._a([self._later(lambda m: m.update(matchDateTimeUTC="2026-10-21T14:45:00Z"), 3, "r3")], T0 + pd.Timedelta(hours=4)); self.assertEqual(c["evaluation_eligibility"], "ineligible_sealed_too_late_after_move")

    def test_identity_change_removal_need_two_snapshots(self):
        other = next(x["team1"] for x in BASE if x["team1"]["teamName"] not in (self.rec["home_team"], self.rec["away_team"]))
        s1 = self._later(lambda m: m.update(team2=copy.deepcopy(other)), 3, "i1"); a1 = self._a([s1], T0 + pd.Timedelta(hours=4)); self.assertIn("identity_change_awaiting_confirmation", a1["flags"]); self.assertEqual(a1["evaluation_eligibility"], "eligible")
        s2 = mk_snap(edit(BASE, self.mid, lambda m: m.update(team2=copy.deepcopy(other))), T0 + pd.Timedelta(hours=5), "i2"); a2 = self._a([s1, s2], T0 + pd.Timedelta(hours=6)); self.assertEqual(a2["evaluation_eligibility"], "ineligible_identity_changed")
        r1 = mk_snap([m for m in BASE if m["matchID"] != self.mid], T0 + pd.Timedelta(hours=3), "rm1"); self.assertEqual(self._a([r1], T0 + pd.Timedelta(hours=4))["evaluation_eligibility"], "pending_possible_removal")
        r2 = mk_snap([m for m in BASE if m["matchID"] != self.mid], T0 + pd.Timedelta(hours=5), "rm2"); self.assertEqual(self._a([r1, r2], T0 + pd.Timedelta(hours=6))["evaluation_eligibility"], "ineligible_fixture_removed")

    def test_missing_result_pending_then_excluded_at_checkpoint(self):
        s = mk_snap(BASE, pd.Timestamp("2026-11-05T12:00:00Z"), "after_ko"); T_eval = pd.Timestamp("2026-11-05T13:00:00Z")
        a = self._a([s], T_eval); self.assertIn("missing_result", a["flags"]); self.assertEqual(a["evaluation_eligibility"], "eligible")
        b = self._a([s], T_eval, checkpoint=True); self.assertEqual(b["evaluation_eligibility"], "ineligible_no_confirmed_result_at_checkpoint")

    def test_label_confirmation_correction_and_withdrawal(self):
        def res(h, a): return lambda m: m.update(matchIsFinished=True, matchResults=[{"resultTypeKind": "After90Minutes", "pointsTeam1": h, "pointsTeam2": a}])
        t1 = pd.Timestamp("2026-10-26T10:00:00Z"); t2 = t1 + pd.Timedelta(hours=30)
        s1, s2, s3 = (mk_snap(edit(BASE, self.mid, res(2, 1)), t1, "l1"), mk_snap(edit(BASE, self.mid, res(2, 1)), t2, "l2"), mk_snap(edit(BASE, self.mid, res(1, 1)), t2, "l3"))
        self.assertEqual(self._a([s1], t1 + pd.Timedelta(minutes=1))["label_status"], "pending_confirmation")
        c = self._a([s1, s2], t2 + pd.Timedelta(minutes=1)); self.assertEqual((c["label_status"], c["score_90min"]), ("confirmed", (2, 1)))
        self.assertEqual(self._a([s1, s3], t2 + pd.Timedelta(minutes=1))["label_status"], "conflict")
        wd = mk_snap(edit(BASE, self.mid, lambda m: m.update(matchIsFinished=False, matchResults=[])), t2, "l4")
        self.assertEqual(self._a([s1, wd], t2 + pd.Timedelta(minutes=1))["evaluation_eligibility"], "ineligible_unresolved_conflict")
        self.assertEqual(self._a([s1], t1 + pd.Timedelta(minutes=1), checkpoint=True)["evaluation_eligibility"], "ineligible_unconfirmed_at_checkpoint")

    def test_late_arriving_history_result_is_flagged_not_excluded(self):
        # a match involving a club of the fixture, played before sealing but first reported afterwards
        ids = {m["matchID"] for m in NEW_RESULTS}
        club = self.rec["home_team"]; target = next(m for m in NEW_RESULTS if club in (m["team1"]["teamName"], m["team2"]["teamName"]))
        base_without = strip_results(BASE, {target["matchID"]})
        rec = None
        recs, _, _ = predict([mk_snap(base_without, T0, "wo_target")], T0 + pd.Timedelta(minutes=30)); rec = min(recs, key=lambda r: r["scheduled_kickoff_utc"])
        later = mk_snap(BASE, T0 + pd.Timedelta(hours=3), "reported_late")
        a = engine.reassess([rec], [state.load_snapshot(os.path.join(TMP, "wo_target.json")), later], T0 + pd.Timedelta(hours=4), self.RES)[0]
        self.assertIn("late_arriving_history_result", a["flags"]); self.assertTrue(a["evaluation_eligibility"].startswith("eligible"))

    def test_sealed_record_unchanged_by_reassessment(self):
        before = json.dumps(self.rec, sort_keys=True); self._a([self._later(lambda m: m.update(matchDateTimeUTC="2026-10-25T16:30:00Z"), 3, "x1")], T0 + pd.Timedelta(hours=4)); self.assertEqual(before, json.dumps(self.rec, sort_keys=True))


# ------------------------------------------------------------------------------------------------ parity, reconstruction, determinism
class TestParity(unittest.TestCase):
    def test_determinism_and_exact_reconstruction(self):
        T = T0 + pd.Timedelta(minutes=30); r1, _, _ = predict([real_snap()], T); r2, _, _ = predict([real_snap()], T)
        self.assertEqual([r["record_sha256"] for r in r1], [r["record_sha256"] for r in r2]); V, VS, RES = universe()
        ok, fails = engine.reconstruct_batch(r1[:30], {real_snap().snapshot_id: real_snap()}, VS, RES, pin()); self.assertEqual((ok, fails), (30, []))
        bad = copy.deepcopy(r1[:3]); bad[0]["probs"]["v2_frozen"]["H"] += 0.01
        ok2, f2 = engine.reconstruct_batch(bad, {real_snap().snapshot_id: real_snap()}, VS, RES, pin()); self.assertEqual(len(f2), 1)

    def test_same_history_for_all_models_and_historical_feature_parity(self):
        V, VS, RES = universe(); S = state_at([real_snap()], T0 + pd.Timedelta(minutes=5)); fx = S.fixtures[["fixture_id", "dt", "h", "a", "comp", "season", "tier"]]
        F2, F1 = engine.D.features_for(S.universe, fx); F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
        self.assertTrue((F2.home_n_prior.values == F1.home_n_prior.values).all() and (F2.away_n_prior.values == F1.away_n_prior.values).all())
        self.assertTrue(np.allclose(F2.home_elo1.values, F1.home_elo.values, atol=1e-9) and np.allclose(F2.away_elo1.values, F1.away_elo.values, atol=1e-9))
        recs, _, _ = predict([real_snap()], T0 + pd.Timedelta(minutes=5)); self.assertEqual(len({r["state_sha256"] for r in recs}), 1)
        tt = pd.read_pickle(os.path.join(artifacts.V2, "final_refit_v2_r1", "training_feature_table_v2_r1.pkl")); v2 = engine.D.load_models()[0]
        day = V[(V.competition_id == state.COMP) & (V.match_date.between("2026-09-11", "2026-09-13"))]
        fxh = pd.DataFrame(dict(fixture_id=day.record_id.values, dt=pd.to_datetime(day.match_date).values, h=day.home_entity_id.values, a=day.away_entity_id.values, comp=state.COMP, season=state.SEASON, tier=1.0))
        Sfull = state.merged_state(V, [real_snap()], T0 + pd.Timedelta(minutes=5), RES, "x")
        Fh, _ = engine.D.features_for(Sfull.universe, fxh); Fh = Fh[~Fh.index.duplicated()]
        have = [i for i in fxh.fixture_id if i in tt.index]; self.assertEqual(len(have), 9)
        self.assertTrue(np.allclose(Fh.loc[have, v2["features"]].values.astype(float), tt.loc[have, v2["features"]].values.astype(float), equal_nan=True, atol=1e-9))


# ------------------------------------------------------------------------------------------------ official path in a temp sandbox
class TestSandboxOfficial(unittest.TestCase):
    def setUp(self):
        self.now = T0 + pd.Timedelta(minutes=30); self._orig = engine._now; engine._now = lambda: self.now
        self._env = os.environ.get("FOOTIQ_OFFICIAL_MODE"); os.environ["FOOTIQ_OFFICIAL_MODE"] = "1"
        V, VS, RES = universe(); self.VS, self.RES = VS, RES
        self.ledger_root = os.path.join(TMP, "sbx", "ledger"); self.anchor = os.path.join(TMP, "sbx", "anchor", "anchor.jsonl")

    def tearDown(self):
        engine._now = self._orig
        if self._env is None: os.environ.pop("FOOTIQ_OFFICIAL_MODE", None)
        else: os.environ["FOOTIQ_OFFICIAL_MODE"] = self._env
        d = os.path.join(TMP, "sbx")
        if os.path.exists(d): shutil.rmtree(d, onerror=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))

    def _seal(self, ap, snaps=None, flag=True, **kw):
        return engine.seal_official(approval_path=ap, snapshot_paths=snaps or [R3], ledger_root=self.ledger_root, anchor_path=self.anchor, V=self.VS, resolver=self.RES, official_flag=flag, sandbox=True, **kw)

    def test_signature_has_no_timestamp_parameter(self):
        import inspect
        self.assertFalse([p for p in inspect.signature(engine.seal_official).parameters if "time" in p.lower() or p in ("T", "now")])

    def test_disabled_by_default_and_production_paths_protected(self):
        ap, _ = mk_approval(self.now)
        with self.assertRaises(PermissionError): self._seal(ap, flag=False)
        os.environ.pop("FOOTIQ_OFFICIAL_MODE")
        with self.assertRaises(PermissionError): self._seal(ap)
        os.environ["FOOTIQ_OFFICIAL_MODE"] = "1"
        with self.assertRaises(PermissionError):
            engine.seal_official(approval_path=ap, snapshot_paths=[R3], ledger_root=self.ledger_root, anchor_path=self.anchor, V=self.VS, resolver=self.RES, official_flag=True, sandbox=False)
        with self.assertRaises(PermissionError):
            engine.seal_official(approval_path=os.path.join(os.path.expanduser("~"), "x.json"), snapshot_paths=[R3], ledger_root=self.ledger_root, anchor_path=self.anchor, V=self.VS, resolver=self.RES, official_flag=True, sandbox=True)
        self.assertFalse(os.path.exists(engine.CANON_LEDGER)); self.assertFalse(os.path.exists(approval.CANONICAL_APPROVAL))

    def test_end_to_end_idempotent_sealing_and_verification(self):
        ap, a = mk_approval(self.now); r = self._seal(ap)
        self.assertEqual(r["sealed"], 18); L = ledger.ChainedLedger(self.ledger_root, self.anchor); v = L.verify(); self.assertTrue(v["ok"], v["errors"]); self.assertEqual(v["records"], 18)
        recs = L.records(); self.assertTrue(all(x["sandbox"] and x["namespace"] == "official-sandbox" and {int(x["matchday"])} <= {7, 8} for x in recs))
        self.now = self.now + pd.Timedelta(minutes=5)
        r2 = self._seal(ap); self.assertEqual((r2["sealed"], r2["skipped"]), (0, 18)); self.assertEqual(L.verify()["records"], 18)
        blob = open(r["path"], encoding="utf-8").read(); self.assertIsNone(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", blob))

    def test_clock_regression_skew_and_future_snapshot_are_refused(self):
        ap, a = mk_approval(self.now); self._seal(ap)
        self.now = self.now - pd.Timedelta(hours=1)
        ap2, _ = mk_approval(self.now, "approval2.json")
        with self.assertRaises(engine.ClockError): self._seal(ap2)
        self.now = T0 + pd.Timedelta(minutes=40)
        skewed = mk_snap(BASE, T0 + pd.Timedelta(minutes=35), "skewed_clock", skew_s=900.0)
        ap3, _ = mk_approval(self.now, "approval3.json")
        with self.assertRaises(engine.ClockError): self._seal(ap3, snaps=[skewed.path])
        self.now = T0 - pd.Timedelta(minutes=10)
        ap4, _ = mk_approval(self.now, "approval4.json")
        with self.assertRaises(engine.ClockError): self._seal(ap4)

    def test_invalid_approvals_refuse_sealing(self):
        for over in (dict(artifact_manifest_sha256="0" * 64), dict(protocol=dict(version="r2", sha256="3" * 64, path=mk_protocol())), dict(max_fixtures=3)):
            ap, _ = mk_approval(self.now, "bad_sandbox.json", **over)
            with self.assertRaises((approval.ApprovalError, PermissionError)): self._seal(ap)
        self.assertFalse(os.path.exists(self.ledger_root))

    def test_interrupted_sealing_does_not_corrupt_and_can_be_recovered(self):
        ap, a = mk_approval(self.now); L = ledger.ChainedLedger(self.ledger_root, self.anchor)
        orig = ledger.ChainedLedger.append_batch
        def crash(self_, records, batch_id, header_extra=None, _crash_after=None): return orig(self_, records, batch_id, header_extra, _crash_after="rename")
        ledger.ChainedLedger.append_batch = crash
        try:
            with self.assertRaises(ledger.SimulatedCrash): self._seal(ap)
        finally:
            ledger.ChainedLedger.append_batch = orig
        if os.path.exists(L.lock): os.remove(L.lock)
        self.assertFalse(L.verify()["ok"]); L.recover(); self.assertTrue(L.verify()["ok"]); self.assertEqual(self._seal(ap)["sealed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
