"""Adversarial audit of logger v2 (shadow module). Read-only on all frozen items; writes only to temp dirs and to this folder. Produces no official records.
Each test returns PROTECTED (the logger resists the attack) or DEFECT (it does not) with evidence. Test inputs are synthetic variants of the real pilot snapshot, never stored as data."""
import copy, glob, hashlib, inspect, json, os, stat, sys, tempfile
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(V2, "shadow_integration_r1")); sys.path.insert(0, os.path.join(V2, "shadow_integration_r1", "tests"))
import prospective_logger_v2 as L
from footiq_sources.reconcile import build_resolver
sys.stdout.reconfigure(encoding="utf-8")

V = pd.read_pickle(L.V_PATH); VS = V[V.match_date >= "2025-07-01"].copy(); RES = build_resolver(V); VSHA = L._universe_sha()
RUN = sorted(glob.glob(os.path.join(V2, "source_adapters_r1", "pilot", "run_*")))[-1]
R3 = glob.glob(os.path.join(RUN, "snapshots", "openligadb", "*R3_getmatchdata*.json"))[0]
BASE = json.load(open(R3, encoding="utf-8")); REAL = L.load_snapshot(R3); T0 = REAL.retrieved
TMP = tempfile.mkdtemp(); rows = []
def mk(matches, retrieved, label):
    body = json.dumps(matches).encode(); p = os.path.join(TMP, label + ".json"); open(p, "wb").write(body)
    json.dump(dict(sha256=hashlib.sha256(body).hexdigest(), saved_utc=pd.Timestamp(retrieved).strftime("%Y-%m-%dT%H:%M:%SZ"), snapshot_id=label + ".json"), open(p + ".meta.json", "w"))
    return L.load_snapshot(p)
def pred(snaps, T): return L.predict_shadow(VS, snaps, T, RES, VSHA, verify_universe=False)
def rec(area, attack, verdict, evidence, fix=""): rows.append(dict(area=area, attack=attack, verdict=verdict, evidence=evidence, required_fix=fix)); print(f"[{verdict}] {area}: {attack} -> {evidence}", flush=True)
newres = [m for m in BASE if m["matchIsFinished"] and m["matchDateTimeUTC"][:10] > L.CUTOFF]
T = T0 + pd.Timedelta(minutes=30)
recs, rej, M = pred([REAL], T)

# 1 duplicate sealing across batches
d = os.path.join(TMP, "dup"); L.write_shadow_batch(recs[:3], "b1", d); L.write_shadow_batch(recs[:3], "b2", d)
ids = [json.loads(l)["fixture_id"] for f in glob.glob(os.path.join(d, "b*.jsonl")) for l in open(f, encoding="utf-8")]
rec("idempotency", "seal the same fixtures twice in two batches", "DEFECT" if len(ids) != len(set(ids)) else "PROTECTED", f"{len(ids)} records for {len(set(ids))} distinct fixtures; chain valid={L.verify_chain(d)}", "refuse (or skip) any fixture already present in the chain; official batch name derived from the fixture set")
# 2 interrupted write leaves orphan file
d = os.path.join(TMP, "orphan"); L.write_shadow_batch(recs[:2], "good", d)
orphan = os.path.join(d, "crashed_batch.jsonl"); open(orphan, "w").write(json.dumps(recs[5]) + "\n")           # file written, chain line never appended
rec("atomicity", "crash after batch file write, before chain append", "DEFECT" if L.verify_chain(d) else "PROTECTED", f"verify_chain={L.verify_chain(d)} with an orphan batch file present; no temp-file+rename, no fsync, no recovery routine", "write to temp, fsync, rename, append chain line with fsync; startup recovery that fails on orphan/partial files")
# 3 truncation of the newest batch
d = os.path.join(TMP, "trunc"); L.write_shadow_batch(recs[:2], "a", d); p2, _ = L.write_shadow_batch(recs[2:4], "b", d)
os.chmod(p2, stat.S_IWRITE); os.remove(p2); lines = open(os.path.join(d, "CHAIN.jsonl")).read().splitlines(); open(os.path.join(d, "CHAIN.jsonl"), "w").write(lines[0] + "\n")
rec("hash chain", "delete newest batch and its chain line", "DEFECT" if L.verify_chain(d) else "PROTECTED", f"verify_chain={L.verify_chain(d)}: the chain is self-contained, so tail truncation is invisible", "record the latest chain hash outside the directory after every batch (owner-held ledger / external anchor)")
# 4 caller-controlled prediction timestamp
back = T0 + pd.Timedelta(minutes=1)
r_back, _, _ = pred([REAL], back)
rec("clock / backdating", "call the sealing function with an earlier T than the real clock", "DEFECT" if r_back and pd.Timestamp.now(tz="UTC") > back + pd.Timedelta(minutes=30) else "PROTECTED", f"records stamped {r_back[0]['prediction_timestamp_utc'] if r_back else None} accepted although the clock is later; no wall-clock or NTP/server-Date check", "official entry point must take T only from the system clock, compare it with the HTTP Date of the newest poll (skew limit) and reject explicit T")
# 5 wrong league/season snapshot
alt = copy.deepcopy(BASE)
for m in alt:
    m["leagueSeason"] = 2025
    m["matchDateTimeUTC"] = (pd.Timestamp(m["matchDateTimeUTC"]) - pd.Timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    m["matchDateTime"] = m["matchDateTimeUTC"]
s_old = mk(alt, T0 + pd.Timedelta(minutes=10), "wrong_season")
r5, _, M5 = pred([s_old], T0 + pd.Timedelta(minutes=40))
rec("source scope", "feed a 2025 season snapshot of the same league", "DEFECT" if len(M5.additions) > 0 else "PROTECTED", f"{len(M5.additions)} results added to the state with dates {M5.additions.match_date.min() if len(M5.additions) else None}", "reject snapshots whose leagueShortcut/leagueSeason differ from bl1/2026 and any addition dated <= 2026-09-20")
# 6 rejected completed result does not flag clubs
unc = copy.deepcopy(BASE); x = [m for m in unc if m["matchID"] == newres[0]["matchID"]][0]
x["matchResults"] = [{"resultTypeKind": "Unknown", "pointsTeam1": 1, "pointsTeam2": 0}]
s6 = mk(unc, T0 + pd.Timedelta(minutes=10), "unclassified")
r6, _, M6 = pred([s6], T0 + pd.Timedelta(minutes=40))
clubs = {x["team1"]["teamName"], x["team2"]["teamName"]}
aff = [r for r in r6 if {r["home_team"], r["away_team"]} & clubs]
unflagged = [r for r in aff if r["primary_eligible"]]
rec("feature completeness", "a played match with no explicit 90-minute type is excluded from the state", "DEFECT" if unflagged else "PROTECTED", f"{len(unflagged)} of {len(aff)} fixtures of the affected clubs stay primary-eligible with a missing match in their history", "any completed in-scope record rejected for any reason must flag both clubs (or the competition) as incomplete_history/unresolved_conflict")
unr = copy.deepcopy(BASE); y = [m for m in unr if m["matchID"] == newres[1]["matchID"]][0]; y["team1"] = dict(y["team1"], teamName="Unknown Club XY")
s6b = mk(unr, T0 + pd.Timedelta(minutes=10), "unknown_team")
r6b, _, M6b = pred([s6b], T0 + pd.Timedelta(minutes=40))
c2 = {newres[1]["team2"]["teamName"]}
aff2 = [r for r in r6b if c2 & {r["home_team"], r["away_team"]} and r["primary_eligible"]]
rec("identity", "completed result with an unresolvable team name", "DEFECT" if aff2 else "PROTECTED", f"{len(aff2)} eligible fixtures of the opponent club remain although its result is missing from the state", "unresolved/ambiguous identity in a completed record flags the competition (or the known club) as incomplete")
# 7 retraction
ret = copy.deepcopy(BASE)
for m in ret:
    if m["matchID"] == newres[2]["matchID"]: m["matchIsFinished"] = False; m["matchResults"] = []
s7 = mk(ret, T0 + pd.Timedelta(hours=2), "retracted")
r7, _, M7 = pred([REAL, s7], T0 + pd.Timedelta(hours=3))
rec("conflict rules", "a result disappears (completed -> not completed) in a later snapshot", "DEFECT" if len(M7.additions) == 18 else "PROTECTED", f"{len(M7.additions)} additions retained although the newest snapshot withdrew one; amendment A1.3(1)(b) calls this a conflict", "latest snapshot is authoritative for status; a retraction quarantines the pair and flags the clubs")
# 8 model integrity coverage
src = inspect.getsource(L.E.verify_models)
missing = [k for k in ("preprocessing_train_fitted", "baseline_parameters") if k not in src]
rec("model integrity", "tamper with the original-v1 preprocessing JSON or the v1 Elo parameters", "DEFECT" if missing else "PROTECTED", f"verify_models never hashes: {missing} (both are used for v1_original / v1_elo probabilities)", "hash every artifact used at prediction time (CRLF-normalised for JSON); also record hashes of feature code (v2_features.py, feature_contract.py, v2_models.py, d11, e4)")
rec("code integrity", "change the feature generator between sealing and reconstruction", "DEFECT" if "v2_features" not in inspect.getsource(L) else "PROTECTED", "logger_code_sha256 covers prospective_logger_v2.py only; changes elsewhere surface only as a failed reconstruction", "record the sha256 of all code dependencies in each record")
# 9 official gate content check
fa = os.path.join(TMP, "approval.json"); fm = os.path.join(TMP, "amend.json"); open(fa, "w").write("{}"); open(fm, "w").write("{}")
oa, om = L.APPROVAL, L.AMENDMENT_ACTIVE; L.APPROVAL, L.AMENDMENT_ACTIVE = fa, fm
try:
    L.ensure_official_allowed(); gate = "DEFECT"; ev = "empty {} approval and amendment files open the OFFICIAL gate; also no official writer or directory exists (write_shadow_batch asserts namespace=shadow)"
except PermissionError:
    gate = "PROTECTED"; ev = "gate rejects"
finally:
    L.APPROVAL, L.AMENDMENT_ACTIVE = oa, om
rec("namespace separation", "satisfy the official gate with empty files", gate, ev, "gate must validate approval content (model hashes, protocol r2 sha256, logger code hash, batch scope) and be written by the owner; implement a separate official writer + directory")
# 10 side-car persistence
rec("fixture changes", "kickoff moved / postponed / cancelled after sealing", "PARTIAL", "reassess() classifies correctly (tested) but returns dicts: there is no hash-chained writer, no schedule/trigger, and no function that applies it to the evaluation eligibility table", "add write_reassessment_batch + verify; run it at every manual poll")
rec("late results", "result dated before a fixture first appears in a snapshot retrieved after sealing", "GAP", "no function detects late-arriving history; the amendment does not state the eligibility consequence", "flag late_arriving_history_result in the side-car; keep eligible; report sensitivity analysis excluding them (amendment text)")
# 11 failures that must fail safe
r11, rej11, _ = pred([REAL], T0 + pd.Timedelta(hours=25))
rec("source availability", "no fresh poll (OpenLigaDB unreachable): only the 25 h old snapshot exists", "PROTECTED" if not r11 and len(rej11) == 252 else "DEFECT", f"{len(r11)} records, {len(rej11)} rejected: {sorted({w for _, w in rej11})}", "")
bad = os.path.join(TMP, "corrupt.json"); open(bad, "wb").write(b'{"truncated": ['); json.dump(dict(sha256=hashlib.sha256(b'{"truncated": [').hexdigest(), saved_utc="2026-10-21T16:00:00Z", snapshot_id="corrupt.json"), open(bad + ".meta.json", "w"))
try:
    L.load_snapshot(bad); v = "DEFECT"; e = "parsed"
except Exception as ex:
    v = "PROTECTED"; e = type(ex).__name__ + " (no records, no batch)"
rec("source availability", "truncated JSON body with a matching hash", v, e, "")
# 12 protections that work
tam = os.path.join(TMP, "tam.json"); open(tam, "wb").write(open(R3, "rb").read() + b" "); json.dump(json.load(open(R3 + ".meta.json")), open(tam + ".meta.json", "w"))
try: L.load_snapshot(tam); v = "DEFECT"
except L.IntegrityError: v = "PROTECTED"
rec("snapshot integrity", "append one byte to a saved snapshot", v, "IntegrityError on load", "")
sealed = copy.deepcopy(recs[3]); sealed["probs"]["v2_frozen"]["H"] += 0.01
rec("reconstruction", "alter a sealed probability", "PROTECTED" if not L.reconstruct(sealed, {REAL.snapshot_id: REAL}, VS, RES, VSHA, verify_universe=False)[0] else "DEFECT", "reconstruction mismatch detected", "")
blob = json.dumps(recs)
import re
rec("contact privacy", "scan sealed records for an email-like string / the configured contact", "PROTECTED" if not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", blob) else "DEFECT", "no email-like string in 252 records; logger never reads the contact", "")
fresh_late = mk(BASE, pd.Timestamp("2026-10-23T12:00:00Z"), "fresh_late")
r_late, rej_late, _ = pred([fresh_late], pd.Timestamp("2026-10-23T18:31:00Z"))
reasons_late = {w for _, w in rej_late}
rec("retrospective predictions", "seal at 2026-10-23 18:31 UTC, after the deadline of the first fixture (using a stale snapshot)", "PROTECTED" if "sealing_deadline_passed_no_backdating" in reasons_late else "DEFECT", f"rejected with: {sorted(reasons_late)}", "")
out = pd.DataFrame(rows); out.to_csv(os.path.join(HERE, "adversarial_audit_results.csv"), index=False, encoding="utf-8-sig")
print(out.verdict.value_counts().to_dict())
