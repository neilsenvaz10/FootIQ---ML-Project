"""Tests for prospective_logger_v2 (shadow). No network. Real inputs: the live pilot snapshot R3 (retrieved 2026-10-21T14:12:31Z) and the frozen universe/models.
Variants of the snapshot built below are TEST INPUTS in a temp folder (late/conflicting/duplicate/rescheduled cases); they are never written to any data store."""
import copy, hashlib, json, os, re, stat, sys, tempfile, unittest, glob
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import prospective_logger_v2 as L
from footiq_sources.reconcile import build_resolver

RUN = sorted(glob.glob(os.path.join(L.V2, "source_adapters_r1", "pilot", "run_*")))[-1]
R3 = [p for p in glob.glob(os.path.join(RUN, "snapshots", "openligadb", "*R3_getmatchdata*.json"))][0]
BASE = json.load(open(R3, encoding="utf-8"))
T0 = pd.Timestamp(json.load(open(R3 + ".meta.json"))["saved_utc"])
V = V_SMALL = RES = VSHA = None
TMP = None


def setUpModule():
    global V, V_SMALL, RES, VSHA, TMP
    V = pd.read_pickle(L.V_PATH)
    V_SMALL = V[V.match_date >= "2025-07-01"].copy()
    RES = build_resolver(V)
    VSHA = L.sha(L.V_PATH)
    TMP = tempfile.mkdtemp()


def mk_snap(matches, retrieved, label):
    body = json.dumps(matches).encode("utf-8")
    p = os.path.join(TMP, label + ".json")
    with open(p, "wb") as fh:
        fh.write(body)
    with open(p + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(dict(sha256=hashlib.sha256(body).hexdigest(), saved_utc=pd.Timestamp(retrieved).strftime("%Y-%m-%dT%H:%M:%SZ"), snapshot_id=label + ".json", plan_sha256="test"), fh)
    return L.load_snapshot(p)


def new_results():
    return [m for m in BASE if m["matchIsFinished"] and m["matchDateTimeUTC"][:10] > L.CUTOFF]


def strip(matches, ids):
    out = copy.deepcopy(matches)
    for m in out:
        if m["matchID"] in ids:
            m["matchIsFinished"] = False; m["matchResults"] = []
    return out


def pred(snaps, T, V_=None, verify=False):
    return L.predict_shadow(V_ if V_ is not None else V_SMALL, snaps, T, RES, VSHA, verify_universe=verify)


REAL = None
def real_snap():
    global REAL
    if REAL is None:
        REAL = L.load_snapshot(R3)
    return REAL


class TestRetrievalFilter(unittest.TestCase):
    def test_late_arriving_results_never_enter_earlier_predictions(self):
        ids = {m["matchID"] for m in new_results()}
        early = mk_snap(strip(BASE, ids), "2026-10-20T10:00:00Z", "early")          # same season before the 18 results were entered
        real = real_snap()
        T_mid = pd.Timestamp("2026-10-20T12:00:00Z")                                # after 'early', before the real snapshot
        recs_mid, rej, M_mid = pred([early, real], T_mid)
        self.assertEqual(len(M_mid.additions), 0); self.assertIn(real.snapshot_id, M_mid.snapshots_excluded)
        recs_late, _, M_late = pred([early, real], T0 + pd.Timedelta(minutes=5))
        self.assertEqual(len(M_late.additions), 18)
        self.assertTrue((pd.to_datetime(M_late.additions.retrieved_utc, utc=True) <= T0 + pd.Timedelta(minutes=5)).all())
        self.assertNotEqual(recs_mid[0]["state_sha256"], recs_late[0]["state_sha256"])
        self.assertTrue(all(r["history_cutoff_date"] < r["scheduled_kickoff_utc"][:10] for r in recs_late))
        # the stale-state record had fewer prior matches than the updated one for the same club
        a = {r["fixture_id"]: r for r in recs_mid}; b = {r["fixture_id"]: r for r in recs_late}
        k = next(iter(a)); self.assertEqual(b[k]["home_n_prior"] - a[k]["home_n_prior"], 2)

    def test_snapshot_retrieved_after_prediction_time_is_not_even_needed_to_exist(self):
        recs, rej, M = pred([real_snap()], T0 - pd.Timedelta(minutes=1))
        self.assertEqual((len(recs), len(M.additions), M.snapshots_used), (0, 0, []))


class TestConflictsAndDuplicates(unittest.TestCase):
    def test_conflict_between_snapshots_quarantines_pair_and_flags_clubs(self):
        real = real_snap(); nr = new_results()[0]
        alt = copy.deepcopy(BASE)
        for m in alt:
            if m["matchID"] == nr["matchID"]:
                for r in m["matchResults"]:
                    if r["resultTypeKind"] == "After90Minutes": r["pointsTeam1"] += 3
        later = mk_snap(alt, T0 + pd.Timedelta(hours=1), "conflicting_later")
        recs, rej, M = pred([real, later], T0 + pd.Timedelta(hours=2))
        self.assertEqual(len(M.additions), 17); self.assertIn((str(nr["matchID"]), "CONFLICT_between_snapshots"), M.rejects)
        flagged = [r for r in recs if "unresolved_conflict" in r["eligibility_reasons"]]
        self.assertTrue(flagged and all(not r["primary_eligible"] for r in flagged))

    def test_conflict_with_openfootball_score(self):
        old = [m for m in BASE if m["matchIsFinished"] and m["matchDateTimeUTC"][:10] <= L.CUTOFF][0]
        alt = copy.deepcopy(BASE)
        for m in alt:
            if m["matchID"] == old["matchID"]:
                for r in m["matchResults"]:
                    if r["resultTypeKind"] == "After90Minutes": r["pointsTeam2"] += 2
        recs, rej, M = pred([mk_snap(alt, T0, "conflict_of")], T0 + pd.Timedelta(minutes=1))
        self.assertIn((str(old["matchID"]), "CONFLICT_with_openfootball"), M.rejects)

    def test_duplicate_match_rejected(self):
        nr = new_results()[0]; alt = copy.deepcopy(BASE)
        d = copy.deepcopy(nr); d["matchID"] = 999999991; alt.append(d)
        recs, rej, M = pred([mk_snap(alt, T0, "dup")], T0 + pd.Timedelta(minutes=1))
        self.assertTrue(any(w == "duplicate_pair_in_snapshot" for _, w in M.rejects)); self.assertEqual(len(M.additions), 17)

    def test_result_without_explicit_90min_type_never_enters_state(self):
        nr = new_results()[0]; alt = copy.deepcopy(BASE)
        for m in alt:
            if m["matchID"] == nr["matchID"]:
                m["matchResults"] = [r for r in m["matchResults"] if r["resultTypeKind"] != "After90Minutes"] + [{"resultTypeKind": "Unknown", "pointsTeam1": 1, "pointsTeam2": 0}]
        recs, rej, M = pred([mk_snap(alt, T0, "unclassified")], T0 + pd.Timedelta(minutes=1))
        self.assertEqual(len(M.additions), 17)


class TestSealingAndKickoff(unittest.TestCase):
    def test_deadlines_no_backdating_and_kickoff_snapshot_freshness(self):
        real = real_snap()
        r_ok, rej_ok, _ = pred([real], T0 + pd.Timedelta(minutes=30))
        self.assertEqual(len(r_ok), 252); self.assertEqual(rej_ok, [])
        first = min(r_ok, key=lambda r: r["scheduled_kickoff_utc"])
        self.assertEqual(first["sealing_deadline_utc"][:16], "2026-10-23 17:30"); self.assertGreater(first["sealed_before_deadline_by_minutes"], 0)
        # after the first deadline: matchday-7 fixtures are refused, later ones are still fine (unless the kickoff snapshot is stale)
        r_late, rej_late, _ = pred([real], pd.Timestamp("2026-10-23T17:31:00Z") - pd.Timedelta(hours=2))      # just 2h earlier: still allowed
        self.assertEqual(len(rej_late), 0 if (pd.Timestamp("2026-10-23T15:31:00Z") - T0) <= pd.Timedelta(hours=24) else len(rej_late))
        r23, rej23, _ = pred([real], T0 + pd.Timedelta(hours=23))
        self.assertEqual(len(r23), 252)
        r25, rej25, _ = pred([real], T0 + pd.Timedelta(hours=25))
        self.assertEqual((len(r25), len(rej25)), (0, 252)); self.assertTrue({w for _, w in rej25} == {"stale_kickoff_snapshot"})

    def test_deadline_passed_is_rejected_not_backdated(self):
        fresh = mk_snap(BASE, pd.Timestamp("2026-10-23T12:00:00Z"), "fresh_kickoff")      # a snapshot taken just before matchday 7
        recs, rej, _ = pred([fresh], pd.Timestamp("2026-10-23T17:45:00Z"))
        md7 = [w for f, w in rej]; self.assertIn("sealing_deadline_passed_no_backdating", md7)
        self.assertTrue(all(pd.Timestamp(r["sealing_deadline_utc"]) > pd.Timestamp("2026-10-23T17:45:00Z") for r in recs))


class TestFixtureChanges(unittest.TestCase):
    def setUp(self):
        self.real = real_snap()
        self.T = T0 + pd.Timedelta(minutes=30)
        self.recs, _, _ = pred([self.real], self.T)
        self.rec = min(self.recs, key=lambda r: r["scheduled_kickoff_utc"])
        self.mid = int(self.rec["ol_match_id"])

    def _later(self, mutate, hours=3, label="later"):
        alt = copy.deepcopy(BASE)
        for m in alt:
            if m["matchID"] == self.mid: mutate(m)
        return mk_snap(alt, T0 + pd.Timedelta(hours=hours), label + str(hours))

    def _assess(self, snap, T_eval=None):
        out = L.reassess([self.rec], [self.real, snap], T_eval or snap.retrieved + pd.Timedelta(minutes=1), RES)
        return out[0]

    def test_rescheduled_later_keeps_prediction_and_flags(self):
        s = self._later(lambda m: m.update(matchDateTimeUTC="2026-10-25T16:30:00Z"))
        a = self._assess(s); self.assertIn("rescheduled_later", a["flags"]); self.assertEqual(a["evaluation_eligibility"], "eligible_flagged_rescheduled")

    def test_postponed_more_than_7_days(self):
        s = self._later(lambda m: m.update(matchDateTimeUTC="2026-11-20T16:30:00Z"))
        self.assertIn("postponed_more_than_7_days", self._assess(s)["flags"])

    def test_kickoff_moved_earlier_than_seal(self):
        s = self._later(lambda m: m.update(matchDateTimeUTC="2026-10-21T14:45:00Z"))            # earlier than the sealing time + 60 min
        a = self._assess(s); self.assertIn("kickoff_moved_earlier", a["flags"]); self.assertEqual(a["evaluation_eligibility"], "ineligible_sealed_too_late_after_move")

    def test_identity_change_and_removal(self):
        a = self._assess(self._later(lambda m: m.update(team2=copy.deepcopy(next(x["team1"] for x in BASE if x["team1"]["teamName"] != m["team1"]["teamName"] and x["team1"]["teamName"] != m["team2"]["teamName"])))))
        self.assertIn("fixture_identity_changed", a["flags"]); self.assertEqual(a["evaluation_eligibility"], "ineligible_identity_changed")
        alt = [m for m in BASE if m["matchID"] != self.mid]
        gone = L.reassess([self.rec], [self.real, mk_snap(alt, T0 + pd.Timedelta(hours=5), "removed")], T0 + pd.Timedelta(hours=6), RES)[0]
        self.assertEqual(gone["evaluation_eligibility"], "ineligible_fixture_removed")

    def test_missing_result_after_kickoff(self):
        s = mk_snap(BASE, pd.Timestamp("2026-11-05T12:00:00Z"), "after_kickoff")                    # match (2026-10-23) never got a result
        a = L.reassess([self.rec], [self.real, s], pd.Timestamp("2026-11-05T13:00:00Z"), RES)[0]
        self.assertIn("missing_result", a["flags"]); self.assertEqual(a["evaluation_eligibility"], "ineligible_no_result_after_7_days")

    def test_label_confirmation_and_result_conflict(self):
        def res(h, a):
            return lambda m: m.update(matchIsFinished=True, matchResults=[{"resultTypeKind": "After90Minutes", "pointsTeam1": h, "pointsTeam2": a}])
        t1 = pd.Timestamp("2026-10-26T10:00:00Z"); t2 = t1 + pd.Timedelta(hours=30)
        def snap(h, a, t, lab):
            alt = copy.deepcopy(BASE)
            for m in alt:
                if m["matchID"] == self.mid: res(h, a)(m)
            return mk_snap(alt, t, lab)
        s1, s2, s3 = snap(2, 1, t1, "r1"), snap(2, 1, t2, "r2"), snap(1, 1, t2, "r3")
        self.assertEqual(L.reassess([self.rec], [self.real, s1], t1 + pd.Timedelta(minutes=1), RES)[0]["label_status"], "pending_confirmation")
        self.assertEqual(L.reassess([self.rec], [self.real, s1, s2], t2 + pd.Timedelta(minutes=1), RES)[0]["label_status"], "confirmed")
        c = L.reassess([self.rec], [self.real, s1, s3], t2 + pd.Timedelta(minutes=1), RES)[0]
        self.assertEqual((c["label_status"], c["evaluation_eligibility"]), ("conflict", "ineligible_unresolved_conflict"))

    def test_sealed_record_is_never_modified_by_reassessment(self):
        before = json.dumps(self.rec, sort_keys=True)
        self._assess(self._later(lambda m: m.update(matchDateTimeUTC="2026-10-25T16:30:00Z")))
        self.assertEqual(before, json.dumps(self.rec, sort_keys=True)); self.assertEqual(self.rec["record_sha256"], L._hash_record({k: v for k, v in self.rec.items() if k != "record_sha256"}))


class TestReconstruction(unittest.TestCase):
    def test_reconstruction_is_exact_and_detects_tampering(self):
        real = real_snap(); T = T0 + pd.Timedelta(minutes=30)
        recs, _, _ = pred([real], T)
        recs2, _, _ = pred([real], T)
        self.assertEqual([r["record_sha256"] for r in recs], [r["record_sha256"] for r in recs2])     # deterministic
        ok, diffs = L.reconstruct(recs[5], {real.snapshot_id: real}, V_SMALL, RES, VSHA, verify_universe=False)
        self.assertTrue(ok, diffs)
        bad = copy.deepcopy(recs[5]); bad["probs"]["v2_frozen"]["H"] += 0.01
        self.assertFalse(L.reconstruct(bad, {real.snapshot_id: real}, V_SMALL, RES, VSHA, verify_universe=False)[0])
        with open(os.path.join(TMP, "tamper.json"), "wb") as fh: fh.write(open(R3, "rb").read() + b" ")
        meta = json.load(open(R3 + ".meta.json")); json.dump(meta, open(os.path.join(TMP, "tamper.json.meta.json"), "w"))
        with self.assertRaises(L.IntegrityError): L.load_snapshot(os.path.join(TMP, "tamper.json"))

    def test_model_hash_failure_blocks_prediction(self):
        orig = L.E.verify_models
        L.E.verify_models = lambda: (_ for _ in ()).throw(RuntimeError("model integrity failure"))
        try:
            with self.assertRaises(RuntimeError): pred([real_snap()], T0 + pd.Timedelta(minutes=5))
        finally:
            L.E.verify_models = orig


class TestParityAndPrivacy(unittest.TestCase):
    def test_historical_feature_parity_with_training_table(self):
        tt = pd.read_pickle(os.path.join(L.V2, "final_refit_v2_r1", "training_feature_table_v2_r1.pkl"))
        day = V[(V.competition_id == L.COMP) & (V.match_date.between("2026-09-11", "2026-09-13"))]
        fx = pd.DataFrame(dict(fixture_id=day.record_id.values, dt=pd.to_datetime(day.match_date).values, h=day.home_entity_id.values, a=day.away_entity_id.values, comp=L.COMP, season=L.SEASON, tier=1.0))
        v2 = L.D.load_models()[0]
        M = L.merged_asof(V, [real_snap()], T0 + pd.Timedelta(minutes=5), RES, VSHA)                # universe WITH the 18 later results
        have = [i for i in fx.fixture_id if i in tt.index]
        self.assertEqual(len(have), 9)
        rows = []
        for d, g in fx.groupby("dt"):                                                                 # (a) per fixture date: state strictly before that date
            F2, _ = L.D.features_for(M.universe[M.universe.dt < d], g)
            rows.append(F2.loc[g.fixture_id])
        a = pd.concat(rows).loc[have, v2["features"]].values.astype(float)
        F2b, _ = L.D.features_for(M.universe, fx)                                                     # (b) full merged universe incl. the later additions (the matches' own rows give duplicate ids with identical features)
        F2b = F2b[~F2b.index.duplicated()]
        b = tt.loc[have, v2["features"]].values.astype(float); c = F2b.loc[have, v2["features"]].values.astype(float)
        self.assertTrue(np.allclose(a, b, equal_nan=True, atol=1e-9)); self.assertTrue(np.allclose(c, b, equal_nan=True, atol=1e-9))

    def test_all_models_share_one_history(self):
        real = real_snap(); M = L.merged_asof(V_SMALL, [real], T0 + pd.Timedelta(minutes=5), RES, VSHA)
        fx = M.fixtures[["fixture_id", "dt", "h", "a", "comp", "season", "tier"]]
        F2, F1 = L.D.features_for(M.universe, fx); F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
        self.assertTrue((F2.home_n_prior.values == F1.home_n_prior.values).all() and (F2.away_n_prior.values == F1.away_n_prior.values).all())
        self.assertTrue(np.allclose(F2.home_elo1.values, F1.home_elo.values, atol=1e-9) and np.allclose(F2.away_elo1.values, F1.away_elo.values, atol=1e-9))
        recs, _, _ = pred([real], T0 + pd.Timedelta(minutes=5))
        self.assertEqual(len({r["state_sha256"] for r in recs}), 1)                                 # one state, one cutoff, for every record and model

    def test_official_namespace_is_closed(self):
        with self.assertRaises(PermissionError):
            L.predict_shadow(V_SMALL, [real_snap()], T0 + pd.Timedelta(minutes=5), RES, VSHA, namespace="official", verify_universe=False)
        self.assertFalse(os.path.exists(L.APPROVAL))

    def test_immutable_batches_and_no_contact_or_email_in_records(self):
        recs, _, _ = pred([real_snap()], T0 + pd.Timedelta(minutes=5))
        d = os.path.join(TMP, "shadowlog")
        path, h = L.write_shadow_batch(recs[:5], "t1", d)
        self.assertTrue(L.verify_chain(d)); self.assertFalse(os.access(path, os.W_OK))
        blob = open(path, encoding="utf-8").read()
        self.assertIsNone(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", blob))                             # no email-like string anywhere in a record
        os.chmod(path, stat.S_IWRITE); open(path, "ab").write(b" "); self.assertFalse(L.verify_chain(d))
        with self.assertRaises(AssertionError):
            L.write_shadow_batch([dict(recs[0], counts_for_evaluation=True)], "t2", os.path.join(TMP, "x"))

    def test_scope_is_bundesliga_only(self):
        real = real_snap(); other = copy.deepcopy(BASE)
        recs, rej, M = L.predict_shadow(V_SMALL, [real], T0 + pd.Timedelta(minutes=5), RES, VSHA, scope_competitions=("england:1-premierleague",), verify_universe=False)
        self.assertEqual(len(recs), 0); self.assertTrue(all(w == "out_of_scope_competition" for _, w in rej))


if __name__ == "__main__":
    unittest.main(verbosity=2)
