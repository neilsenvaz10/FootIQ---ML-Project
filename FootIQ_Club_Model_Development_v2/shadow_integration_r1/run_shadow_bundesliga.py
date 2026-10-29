"""Shadow-mode run (Bundesliga 2026-27 only, namespace SHADOW, counts_for_evaluation=False). Full prediction-generation path; no official records; no network."""
import glob, hashlib, json, os, shutil, stat, sys, tempfile
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import prospective_logger_v2 as L
from footiq_sources.reconcile import build_resolver
sys.stdout.reconfigure(encoding="utf-8")
res = {}
def log(k, v): res[k] = v; print(k, "->", json.dumps(v, default=str)[:350])

RUN = sorted(glob.glob(os.path.join(L.V2, "source_adapters_r1", "pilot", "run_*")))[-1]
R3 = glob.glob(os.path.join(RUN, "snapshots", "openligadb", "*R3_getmatchdata*.json"))[0]
snap = L.load_snapshot(R3)
V = pd.read_pickle(L.V_PATH); VSHA = L._universe_sha(); resolver = build_resolver(V)
ing = sorted(glob.glob(os.path.join(L.V2, "matched_v1_prospective_r1", "ingestion", "runs", "selftest_*")))[-1]
un = pd.read_csv(os.path.join(ing, "unresolved_or_non_completed.csv"), encoding="utf-8-sig", low_memory=False)
pnr_of = un[(un.status == "past_date_no_result") & (un.competition_id == L.COMP)]
T = pd.Timestamp.now(tz="UTC").floor("s")
log("prediction_timestamp_utc", str(T)); log("namespace", "shadow (official namespace closed: no approval file, no active amendment)")

recs, rejected, M = L.predict_shadow(V, [snap], T, resolver, VSHA, pnr_of)
recs2, rejected2, M2 = L.predict_shadow(V, [snap], T, resolver, VSHA, pnr_of)
# ---- 1 fixtures genuinely in the future + 2 freshness
ko = pd.to_datetime([r["scheduled_kickoff_utc"] for r in recs], utc=True)
log("future_check", dict(fixtures=len(recs), earliest_kickoff=str(ko.min()), all_kickoff_after_T=bool((ko > T).all()), all_kickoff_at_least_60min_after_T=bool((ko > T + pd.Timedelta(minutes=60)).all()),
                         rejected=rejected, rejected_count=len(rejected)))
age_h = float((T - snap.retrieved).total_seconds() / 3600)
log("freshness", dict(snapshot_id=snap.snapshot_id, retrieved_utc=str(snap.retrieved), age_hours_at_prediction=round(age_h, 2), kickoff_snapshot_within_24h=age_h <= 24, history_cutoff_date=M.history_cutoff_date,
                      competition_gap_days_to_first_fixture=int((ko.min().tz_localize(None).normalize() - pd.Timestamp(M.history_cutoff_date)).days)))
# ---- 3 hashes
log("hash_verification", dict(models=recs[0]["model_hashes"], snapshot_sha256=snap.sha256, frozen_universe_sha256=VSHA[:16], state_sha256=M.state_sha256[:16], results_added=len(M.additions)))
# ---- 4 deterministic output + reconstruction from the saved snapshot
log("deterministic", dict(identical_record_hashes_two_runs=[r["record_sha256"] for r in recs] == [r["record_sha256"] for r in recs2], n=len(recs)))
n_ok, bad = L.reconstruct_batch(recs, {snap.snapshot_id: snap}, V, resolver, VSHA, pnr_of)
ok_all = (n_ok == len(recs) and not bad)
log("reconstruction_all_records", dict(checked=len(recs), identical=n_ok, all_identical=ok_all, failures=bad[:3]))
# ---- 5 sealing deadlines
dl = pd.to_datetime([r["sealing_deadline_utc"] for r in recs], utc=True)
log("sealing_deadlines", dict(earliest_deadline=str(dl.min()), all_deadlines_after_T=bool((dl > T).all()), minutes_to_earliest_deadline=round(float((dl.min() - T).total_seconds() / 60), 1),
                              legacy_rule_earliest=min(r["legacy_deadline_utc"] for r in recs), legacy_rule_deadline_passed_for=int(sum(pd.Timestamp(r["legacy_deadline_utc"]) <= T for r in recs)),
                              note="no deadline has passed; nothing was backdated; legacy (date-based) rule shown for comparison only"))
# ---- 6 leakage canary: a synthetic LATER snapshot (retrieved after T) with an extra completed result must not change any sealed record
base = json.load(open(R3, encoding="utf-8")); canary = [dict(m) for m in base]
tmp = tempfile.mkdtemp(); future = canary[[i for i, m in enumerate(canary) if not m["matchIsFinished"]][0]]
future.update(matchIsFinished=True, matchResults=[{"resultTypeKind": "After90Minutes", "pointsTeam1": 5, "pointsTeam2": 0}])
body = json.dumps(canary).encode(); p = os.path.join(tmp, "canary.json"); open(p, "wb").write(body)
json.dump(dict(sha256=hashlib.sha256(body).hexdigest(), saved_utc=(T + pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), snapshot_id="canary_future.json"), open(p + ".meta.json", "w"))
cs = L.load_snapshot(p)
recs_c, _, Mc = L.predict_shadow(V, [snap, cs], T, resolver, VSHA, pnr_of)
log("leakage_canary", dict(canary_retrieved=str(cs.retrieved), excluded=Mc.snapshots_excluded, sealed_records_identical=[r["record_sha256"] for r in recs_c] == [r["record_sha256"] for r in recs],
                           additions_retrieved_after_T=int((pd.to_datetime(M.additions.retrieved_utc, utc=True) > T).sum()), additions_dated_after_first_fixture=int((pd.to_datetime(M.additions.match_date) >= ko.min().tz_localize(None).normalize()).sum())))
shutil.rmtree(tmp, ignore_errors=True)
# ---- 7 one history for all models
log("single_history_cutoff", dict(distinct_state_hashes=len({r["state_sha256"] for r in recs}), distinct_cutoff_dates=len({r["history_cutoff_date"] for r in recs}), models_per_record=sorted(recs[0]["probs"])))
# ---- 8 eligibility
R = pd.DataFrame(recs); R["reasons"] = R.eligibility_reasons.apply(lambda x: ";".join(s.split("(")[0] for s in x) or "ELIGIBLE")
log("eligibility", dict(total_future_fixtures=len(R), eligible=int(R.primary_eligible.sum()), ineligible_reasons=R[~R.primary_eligible].reasons.value_counts().to_dict(),
                        eligible_by_matchday=R[R.primary_eligible].groupby("matchday").size().to_dict(), earliest_deadline=str(dl.min())))
R[["fixture_id", "home_team", "away_team", "matchday", "scheduled_kickoff_utc", "sealing_deadline_utc", "legacy_deadline_utc", "sealed_before_deadline_by_minutes", "primary_eligible", "reasons"]].to_csv(os.path.join(HERE, "shadow_fixture_summary.csv"), index=False)
# ---- 9 write the shadow batch (immutable) and verify
name = "shadow_batch_" + T.strftime("%Y%m%dT%H%M%SZ")
path, h = L.write_shadow_batch(recs, name)
back = [json.loads(l) for l in open(path, encoding="utf-8")]
log("immutability", dict(batch=os.path.basename(path), batch_sha256=h[:16], records=len(back), chain_ok=L.verify_chain(), read_only=not os.access(path, os.W_OK), all_counts_for_evaluation_false=all(r["counts_for_evaluation"] is False for r in back),
                         namespaces=sorted({r["namespace"] for r in back})))
d = tempfile.mkdtemp(); shutil.copytree(L.SHADOW_DIR, os.path.join(d, "c")); bp = os.path.join(d, "c", os.path.basename(path)); os.chmod(bp, stat.S_IWRITE); open(bp, "ab").write(b" ")
log("tamper_detected", not L.D.verify_chain(os.path.join(d, "c"))); shutil.rmtree(d, ignore_errors=True)
# ---- 10 official evidence: none created
log("official_artifacts", dict(approval_json_exists=os.path.exists(L.APPROVAL), amendment_active_file_exists=os.path.exists(L.AMENDMENT_ACTIVE),
                               official_log_dir_exists=os.path.exists(os.path.join(L.V2, "matched_v1_prospective_r1", "prospective_log", "OFFICIAL"))))
# ---- 11 contact privacy
contact = open(r"D:\Foot IQ\config\contact.local", encoding="utf-8").read().strip()
parts = {p for p in {contact, contact.replace("mailto:", ""), contact.split("@")[0]} if len(p) > 4}
hits = []
for root in (L.SHADOW_DIR, HERE):
    for dp, dn, fn in os.walk(root):
        for f in fn:
            fp = os.path.join(dp, f)
            if f.endswith((".pyc",)): continue
            try: txt = open(fp, encoding="utf-8", errors="ignore").read()
            except OSError: continue
            if any(x in txt for x in parts): hits.append(os.path.relpath(fp, HERE))
log("contact_privacy", dict(files_scanned_in_shadow_and_integration_folders=sum(len(fn) for _, _, fn in os.walk(HERE)), hits=hits))
json.dump(res, open(os.path.join(HERE, "shadow_run_results.json"), "w", encoding="utf-8"), indent=1, default=str)
