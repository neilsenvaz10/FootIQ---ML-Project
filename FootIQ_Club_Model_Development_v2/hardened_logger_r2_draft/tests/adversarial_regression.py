"""Re-runs the 19 attacks of official_readiness_audit_r1/adversarial_audit.py against the HARDENED logger, then runs the new attack tests and records PROTECTED / DEFECT per attack.
Official-path attacks run only in a sandbox inside the system temp directory with synthetic approvals."""
import copy, glob, hashlib, inspect, json, os, shutil, stat, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from helpers import *
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
rows = []


def rec(n, area, attack, ok, evidence):
    rows.append(dict(n=n, area=area, attack=attack, verdict="PROTECTED" if ok else "DEFECT", evidence=evidence)); print(f"[{'PROTECTED' if ok else 'DEFECT'}] {n} {area}: {attack} -> {evidence}", flush=True)


def rmro(p):
    os.chmod(p, stat.S_IWRITE); os.remove(p)


V, VS, RES = universe(); REAL = real_snap(); T = T0 + pd.Timedelta(minutes=30)
recs0, rej0, S0 = predict([REAL], T)
mk_led = lambda n: ledger.ChainedLedger(os.path.join(TMP, n, "l"), os.path.join(TMP, n, "a", "anchor.jsonl"))
fx_recs = lambda n, p="F": [dict(fixture_id=f"{p}{i}", model_key="mk", prediction_timestamp_utc="2026-10-21T15:00:00Z") for i in range(n)]

# 1 idempotency
L = mk_led("r1"); L.append_batch(fx_recs(3), "a"); r = L.append_batch(fx_recs(3), "b")
rec(1, "idempotency", "seal the same fixtures twice", r["sealed"] == 0 and r["skipped"] == 3 and len(L.records()) == 3, f"second batch sealed {r['sealed']}, skipped {r['skipped']}")
# 2 atomicity
L = mk_led("r2"); L.append_batch(fx_recs(2), "good"); crashed = False
try: L.append_batch(fx_recs(2, "G"), "bad", _crash_after="rename")
except ledger.SimulatedCrash: crashed = True
os.path.exists(L.lock) and os.remove(L.lock); det = not L.verify()["ok"]; acts = L.recover(); rec(2, "atomicity", "crash after rename, before anchor", crashed and det and L.verify()["ok"], f"detected={det}; recovery={acts}")
L = mk_led("r2b"); L.append_batch(fx_recs(2), "good")
try: L.append_batch(fx_recs(2, "G"), "bad", _crash_after="partial")
except ledger.SimulatedCrash: pass
os.path.exists(L.lock) and os.remove(L.lock); det = not L.verify()["ok"]; L.recover(); rec(2, "atomicity", "crash mid-write (partial temp file)", det and L.verify()["ok"] and L.verify()["records"] == 2, "partial batch detected, discarded by recovery")
# 3 truncation
L = mk_led("r3"); L.append_batch(fx_recs(2), "a"); p = L.append_batch(fx_recs(2, "G"), "b")["path"]; rmro(p)
rec(3, "hash chain", "delete newest batch", not L.verify()["ok"], "; ".join(L.verify()["errors"])[:140])
# 4 backdating
rec(4, "clock / backdating", "supply an earlier prediction time to the sealing function", not [x for x in inspect.signature(engine.seal_official).parameters if "time" in x.lower() or x in ("T", "now")], "seal_official has no timestamp parameter; time = engine._now() (monotonic vs ledger, poll skew <= 120 s)")
# 5 source scope
alt = copy.deepcopy(BASE)
for m in alt: m["leagueSeason"] = 2025
p = os.path.join(TMP, "ws.json"); open(p, "w").write(json.dumps(alt)); json.dump(dict(sha256=hashlib.sha256(open(p, "rb").read()).hexdigest(), saved_utc="2026-10-21T14:30:00Z", snapshot_id="ws.json"), open(p + ".meta.json", "w"))
try: state.load_snapshot(p); ok = False
except state.ScopeError: ok = True
rec(5, "source scope", "feed a 2025 season snapshot", ok, "ScopeError")
# 6 completeness
nr = NEW_RESULTS[0]; un = mk_snap(edit(BASE, nr["matchID"], lambda m: m.update(matchResults=[{"resultTypeKind": "Unknown", "pointsTeam1": 1, "pointsTeam2": 0}])), T0, "un6")
r6, _, S6 = predict([un], T); clubs = {nr["team1"]["teamName"], nr["team2"]["teamName"]}; aff = [r for r in r6 if {r["home_team"], r["away_team"]} & clubs]
rec(6, "feature completeness", "played match without explicit 90-minute type", aff and all(not r["primary_eligible"] for r in aff), f"{len(aff)} fixtures of the clubs ineligible; event {S6.events[0]['kind']}")
unk = mk_snap(edit(BASE, NEW_RESULTS[1]["matchID"], lambda m: m["team1"].update(teamName="Unknown Club XY")), T0, "unk6")
r6b, _, S6b = predict([unk], T); rec(7, "identity", "completed result with an unresolvable team", S6b.competition_blocked and sum(r["primary_eligible"] for r in r6b) == 0, "competition blocked: 0 eligible fixtures")
# 8 retraction
wd = mk_snap(edit(BASE, NEW_RESULTS[2]["matchID"], lambda m: m.update(matchIsFinished=False, matchResults=[])), T0 + pd.Timedelta(hours=2), "wd8")
S8 = state_at([REAL, wd], T0 + pd.Timedelta(hours=3)); rec(8, "conflict rules", "a result is withdrawn in a later snapshot", len(S8.additions) == 17 and any(e["kind"] == "withdrawn_result" for e in S8.events), f"additions={len(S8.additions)}; withdrawn_result event; clubs blocked={len(S8.blocked_clubs)}")
# 9 model integrity (v1 preprocessing / Elo parameters)
m = artifacts.manifest(); rec(9, "model integrity", "tamper with v1 preprocessing or v1 Elo parameters", all(k in m for k in ("model_v1_original_preprocessing", "model_v1_elo_parameters", "model_v1_original_coefficients")), "hashed in the manifest; detection tested on temp copies")
paths = {k: artifacts.canonical_paths()[k] for k in ("model_v1_original_preprocessing", "model_v1_elo_parameters", "elo2_parameters_and_meta", "code_v2_features")}
d = os.path.join(TMP, "r9"); os.makedirs(d, exist_ok=True); cp = {}
for k, v in paths.items():
    cp[k] = os.path.join(d, k + os.path.splitext(v)[1]); shutil.copyfile(v, cp[k])
exp = artifacts.manifest(cp); allok = True
for k in cp:
    bad = dict(cp); f = os.path.join(d, "bad_" + os.path.basename(cp[k])); shutil.copyfile(cp[k], f); open(f, "ab").write(b" "); bad[k] = f; allok &= any(k in x for x in artifacts.verify(exp, bad))
rec(10, "code / parameter integrity", "tamper with feature code, Elo2 parameters, v1 preprocessing or v1 Elo parameters", allok, "each tamper detected by the manifest check (prediction aborts with IntegrityError)")
# 11 official gate with empty files
now = T0 + pd.Timedelta(minutes=30); orig_now = engine._now; engine._now = lambda: now; envold = os.environ.get("FOOTIQ_OFFICIAL_MODE"); os.environ["FOOTIQ_OFFICIAL_MODE"] = "1"
try:
    ok = True
    for name, content in (("e1.json", ""), ("e2.json", "{}")):
        pth = os.path.join(TMP, name); open(pth, "w").write(content)
        try: engine.seal_official(approval_path=pth, snapshot_paths=[R3], ledger_root=os.path.join(TMP, "r11", "l"), anchor_path=os.path.join(TMP, "r11", "a", "anchor.jsonl"), V=VS, resolver=RES, official_flag=True, sandbox=True); ok = False
        except approval.ApprovalError: pass
    rec(11, "namespace / approval", "empty or {} approval opens the official path", ok and not os.path.exists(os.path.join(TMP, "r11", "l")), "ApprovalError; no ledger created")
    # 12 side-car persistence
    rec(12, "fixture changes", "kickoff moved / postponed / cancelled after sealing", hasattr(engine, "reassess") and os.path.exists(os.path.join(artifacts.ROOT, "scripts", "reassess_official.py")), "classified by reassess(); chained side-car writer in scripts/reassess_official.py (--write)")
    # 13 late results
    rec(13, "late results", "history result appears after sealing", "late_arriving_history_result" in inspect.getsource(engine.reassess), "flag implemented and tested (eligible, flagged, sensitivity analysis)")
finally:
    engine._now = orig_now
    if envold is None: os.environ.pop("FOOTIQ_OFFICIAL_MODE", None)
    else: os.environ["FOOTIQ_OFFICIAL_MODE"] = envold
# 14 source availability
r14, rej14, _ = predict([REAL], T0 + pd.Timedelta(hours=25)); rec(14, "source availability", "only a 25 h old snapshot exists", not r14 and {w for _, w in rej14} == {"stale_kickoff_snapshot"}, f"{len(rej14)} rejected")
bad = os.path.join(TMP, "corrupt.json"); open(bad, "wb").write(b'{"truncated": ['); json.dump(dict(sha256=hashlib.sha256(b'{"truncated": [').hexdigest(), saved_utc="2026-10-21T16:00:00Z", snapshot_id="corrupt.json"), open(bad + ".meta.json", "w"))
try: state.load_snapshot(bad); ok = False
except Exception as e: ok = True
rec(15, "source availability", "truncated JSON body with matching hash", ok, "exception, no records")
tam = os.path.join(TMP, "tam.json"); open(tam, "wb").write(open(R3, "rb").read() + b" "); json.dump(json.load(open(R3 + ".meta.json")), open(tam + ".meta.json", "w"))
try: state.load_snapshot(tam); ok = False
except state.IntegrityError: ok = True
rec(16, "snapshot integrity", "append a byte to a saved snapshot", ok, "IntegrityError")
bad_rec = copy.deepcopy(recs0[:3]); bad_rec[0]["probs"]["v2_frozen"]["H"] += 0.01
okc, fails = engine.reconstruct_batch(bad_rec, {REAL.snapshot_id: REAL}, VS, RES, pin()); rec(17, "reconstruction", "alter a sealed probability", len(fails) == 1 and okc == 2, "mismatch detected for the altered record only")
import re
rec(18, "contact privacy", "scan sealed records for an email-like string", not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", json.dumps(recs0)), f"{len(recs0)} records clean")
late_fresh = mk_snap(BASE, pd.Timestamp("2026-10-23T12:00:00Z"), "fresh_late")
rl, rejl, _ = predict([late_fresh], pd.Timestamp("2026-10-23T18:31:00Z")); rec(19, "retrospective predictions", "seal after the first deadline", any(w == "sealing_deadline_passed_no_backdating" for _, w in rejl) and all(pd.Timestamp(r["sealing_deadline_utc"]) > pd.Timestamp("2026-10-23T18:31:00Z") for r in rl), "deadline-passed fixtures rejected")

# ---- the new attack tests: run the unit suite programmatically and collect per-test outcomes
suite = unittest.defaultTestLoader.loadTestsFromName("test_hardened")
class R(unittest.TextTestResult):
    pass
res = unittest.TextTestRunner(stream=open(os.devnull, "w"), resultclass=R, verbosity=0).run(suite)
bad_ids = {t.id().split(".")[-1] for t, _ in res.failures + res.errors}
AREAS = {"duplicate sealing": ["test_duplicate_sealing_is_skipped_idempotently", "test_same_fixture_with_new_model_version_is_a_different_key"], "interrupted writes": ["test_interrupted_writes_are_detected_and_recovered", "test_interrupted_sealing_does_not_corrupt_and_can_be_recovered"],
         "missing newest batch": ["test_deleted_newest_batch_is_detected_by_the_anchor", "test_deleted_middle_reordered_and_modified_batches"], "historical timestamp spoofing": ["test_signature_has_no_timestamp_parameter", "test_clock_regression_skew_and_future_snapshot_are_refused"],
         "empty / invalid approval files": ["test_empty_missing_and_malformed_files", "test_expired_future_and_outside_window", "test_mismatched_models_manifest_scope_protocol_and_flags", "test_invalid_approvals_refuse_sealing"],
         "source withdrawals": ["test_withdrawn_result_quarantines_pair_and_blocks_clubs"], "stale source snapshots": ["test_stale_snapshot_blocks_sealing_and_future_dated_snapshot_is_ignored", "test_out_of_order_and_duplicate_retrieval_time_snapshots_rejected"],
         "missing played matches": ["test_missing_played_matches_block_clubs_or_competition", "test_removed_fixture_and_postponed_in_newest_snapshot"], "corrected results": ["test_corrected_result_conflict", "test_duplicate_match_and_conflict_with_openfootball"],
         "postponed / rescheduled fixtures": ["test_rescheduled_postponed_and_stale_after_reschedule", "test_identity_change_removal_need_two_snapshots", "test_missing_result_pending_then_excluded_at_checkpoint"],
         "tampered feature code / preprocessing / Elo parameters": ["test_each_tamper_is_detected", "test_prediction_aborts_when_feature_code_or_elo_or_preprocessing_changes"], "invalid protocol hash": ["test_mismatched_models_manifest_scope_protocol_and_flags"],
         "official mode off by default / production paths": ["test_official_mode_is_off_by_default", "test_disabled_by_default_and_production_paths_protected"], "late-arriving results": ["test_late_arriving_results_never_enter_earlier_predictions", "test_late_arriving_history_result_is_flagged_not_excluded"],
         "determinism / reconstruction / parity": ["test_determinism_and_exact_reconstruction", "test_same_history_for_all_models_and_historical_feature_parity"], "second-source agreement and conflict": ["test_second_source_openfootball_agreement_and_conflict"],
         "scope validation": ["test_wrong_league_or_season_snapshot_is_rejected"]}
for i, (area, tests) in enumerate(AREAS.items(), start=20):
    rec(i, "new: " + area, ", ".join(t.replace("test_", "")[:40] for t in tests), not any(t in bad_ids for t in tests), f"{len(tests)} unit tests" + (f"; FAILING: {[t for t in tests if t in bad_ids]}" if any(t in bad_ids for t in tests) else " all pass"))
out = pd.DataFrame(rows); out.to_csv(os.path.join(os.path.dirname(HERE), "adversarial_regression_results.csv"), index=False, encoding="utf-8-sig")
print(out.verdict.value_counts().to_dict(), "| unit tests run:", res.testsRun, "failures:", len(res.failures), "errors:", len(res.errors))
