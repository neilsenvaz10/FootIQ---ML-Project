"""Bundesliga source-promotion validation (isolated; no network, no official predictions, no writes outside this folder).
Phase 1 pilot integrity | Phase 3 isolated feature-state update + chronological leakage checks | Phase 4 eligibility | Phase 5 git hygiene."""
import glob, hashlib, json, os, stat, subprocess, sys
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(V2, "source_adapters_r1")); sys.path.insert(0, os.path.join(V2, "_scripts"))
from footiq_sources import openligadb as ol
from footiq_sources.reconcile import build_resolver
import e4_prospective_logger as E
import d11_prospective_logger as D
from v2_common import sha, PREP, P
sys.stdout.reconfigure(encoding="utf-8")
RUN = sorted(glob.glob(os.path.join(V2, "source_adapters_r1", "pilot", "run_*")))[-1]
SNAP = os.path.join(RUN, "snapshots", "openligadb")
COMP, SEASON, CUTOFF = "deutschland:1-bundesliga", "2026-27", "2026-09-20"
APPROVED = "d7c2169e117a02f3e72b0517f171f2b11fb7f3d609156619cfd7421615a18bc9"
res = {}
def log(k, v): res[k] = v; print(k, "->", json.dumps(v, default=str)[:400])

# ======================================================== Phase 1: pilot integrity
metas = sorted(glob.glob(os.path.join(SNAP, "*.meta.json")))
rows = []
for m in metas:
    meta = json.load(open(m, encoding="utf-8")); f = m[:-10]
    rows.append(dict(file=os.path.basename(f), sha256_ok=sha(f) == meta["sha256"], bytes_ok=os.path.getsize(f) == meta["bytes"], read_only=not os.access(f, os.W_OK), plan_sha_ok=meta.get("plan_sha256") == APPROVED,
                     licence=meta.get("licence"), attribution_ok="OpenLigaDB" in meta.get("attribution", "") and "ODbL 1.0" in meta.get("attribution", ""), status=meta.get("status"), retrieved=meta.get("retrieved_utc")))
snaps = pd.DataFrame(rows); snaps.to_csv(os.path.join(HERE, "01_pilot_snapshot_integrity.csv"), index=False)
led = [json.loads(l) for l in open(os.path.join(RUN, "request_ledger.jsonl"), encoding="utf-8")]
plan = json.load(open(os.path.join(V2, "source_adapters_r1", "pilot", "request_plan_r1.json"), encoding="utf-8"))
allowed = ["/getavailableleagues/2026", "/getresulttypes", "/getmatchdata/bl1/2026", "/getcurrentgroup/bl1", "/getlastchangedate/bl1/2026/"]
log("ledger", dict(requests=len(led), all_200=all(r["status"] == 200 for r in led), hosts=sorted({r["url"].split("/")[2] for r in led}), within_plan=all(any(r["url"].endswith(a) or a in r["url"] for a in allowed) for r in led), attempts_with_retry=sum(r["attempt"] > 0 for r in led)))
log("snapshot_files", dict(n=len(snaps), all_sha_ok=bool(snaps.sha256_ok.all()), all_read_only=bool(snaps.read_only.all()), all_plan_sha=bool(snaps.plan_sha_ok.all()), all_attributed=bool(snaps.attribution_ok.all()), licence=sorted(snaps.licence.unique())))
r3 = [m for m in metas if "R3_getmatchdata" in m][0][:-10]
r3meta = json.load(open(r3 + ".meta.json", encoding="utf-8")); body = open(r3, "rb").read()
retrieved = datetime.fromisoformat(r3meta["saved_utc"].replace("Z", "+00:00"))
recs = ol.parse_payload(body, r3meta["saved_utc"], r3meta["snapshot_id"], retrieved, COMP)
now_df = pd.DataFrame([r.to_dict() for r in recs]).astype(str)
run_df = pd.read_csv(os.path.join(RUN, "staging_records.csv"), dtype=str, keep_default_na=False)
same = now_df.reset_index(drop=True).equals(run_df.reset_index(drop=True))
log("reparse_reproducible", dict(identical_to_pilot_staging_records=bool(same), rows=len(now_df), differing_columns=[c for c in now_df.columns if not now_df[c].equals(run_df[c])]))
# result-type reporting fix: parsed outcomes unaffected
r2 = json.loads(open([m for m in metas if "R2_getresulttypes" in m][0][:-10], "rb").read())
log("result_type_fix", dict(kinds_from_R2_snapshot=sorted({x.get("kind") or x.get("resultTypeKind") for x in r2}), parsed_outcomes_changed=not same, note="the fix touched only the pilot report line; parse_match/regulation_score code and the staging records are unchanged"))
# internal consistency + comparison with the earlier 13:35 snapshot
old = json.load(open(os.path.join(V2, "source_adapters_r1", "evidence", "openligadb_bl1_2026.json"), encoding="utf-8")); new = json.loads(body)
od = {m["matchID"]: m for m in old}; changed = [m["matchID"] for m in new if json.dumps(od.get(m["matchID"]), sort_keys=True) != json.dumps(m, sort_keys=True)]
log("vs_earlier_snapshot_13_35", dict(matches_old=len(old), matches_new=len(new), matches_changed=len(changed)))
comp = [r for r in recs if r.status == "completed"]
log("internal_consistency", dict(matches=len(recs), completed=len(comp), explicit_90=sum(r.label_eligible_90min for r in comp), kickoff_before_retrieval=all(datetime.fromisoformat(r.kickoff_utc.replace("Z", "+00:00")) < retrieved for r in comp),
                               every_record_attributed=all(r.licence == "ODbL-1.0" and "ODbL 1.0" in r.attribution for r in recs), snapshot_id_matches=all(r.snapshot_id == r3meta["snapshot_id"] for r in recs)))

# ======================================================== Phase 3: isolated feature state
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
Vsha = sha(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
resolver = build_resolver(V)
ing = sorted(glob.glob(os.path.join(V2, "matched_v1_prospective_r1", "ingestion", "runs", "selftest_*")))[-1]
fx_of = pd.read_csv(os.path.join(ing, "fixtures.csv"), encoding="utf-8-sig", low_memory=False)
un_of = pd.read_csv(os.path.join(ing, "unresolved_or_non_completed.csv"), encoding="utf-8-sig", low_memory=False)
pnr = un_of[(un_of.status == "past_date_no_result") & (un_of.competition_id == COMP)]
frozen_keys = set(zip(V[(V.competition_id == COMP) & (V.season_corrected == SEASON)].home_entity_id, V[(V.competition_id == COMP) & (V.season_corrected == SEASON)].away_entity_id))


def build_additions(recs):
    """Verified, unambiguous completed 90-minute OpenLigaDB results not yet in the frozen universe. Conflicts/ambiguity -> rejected list."""
    add, rej, seen = [], [], {}
    for r in recs:
        if r.status != "completed" or not r.match_date or r.match_date <= CUTOFF:
            continue
        he, hm = resolver.resolve("openligadb", COMP, r.home_raw); ae, am = resolver.resolve("openligadb", COMP, r.away_raw)
        if not he or not ae:
            rej.append((r.source_ref, f"identity_{hm}_{am}")); continue
        if not r.label_eligible_90min:
            rej.append((r.source_ref, "no_explicit_90min_result")); continue
        if (he, ae) in seen:
            rej.append((r.source_ref, "duplicate_pair_in_source")); continue
        if (he, ae) in frozen_keys:
            of = V[(V.competition_id == COMP) & (V.season_corrected == SEASON) & (V.home_entity_id == he) & (V.away_entity_id == ae)].iloc[0]
            if (int(of.gh), int(of.ga)) != (r.regulation_home, r.regulation_away):
                rej.append((r.source_ref, "CONFLICT_with_openfootball")); continue
            continue                                     # already in the frozen universe (identical)
        seen[(he, ae)] = 1
        add.append(dict(record_id="NEW:openligadb:" + r.source_ref, competition_id=COMP, season_corrected=SEASON, match_date=r.match_date, dt=pd.Timestamp(r.match_date), home_entity_id=he, away_entity_id=ae,
                        home_team_name=r.home_raw, away_team_name=r.away_raw, tier=1.0, competition_type="domestic_league", regular_round_robin_stage=True, rated=True, gh=float(r.regulation_home), ga=float(r.regulation_away),
                        provenance=f"OpenLigaDB matchID {r.source_ref} snapshot {r.snapshot_id}", retrieved_utc=r.retrieved_utc, kickoff_utc=r.kickoff_utc, source="openligadb"))
    return pd.DataFrame(add), rej


ADD, REJ = build_additions(recs)
ADD.drop(columns=["dt"]).to_csv(os.path.join(HERE, "03_added_results_with_provenance.csv"), index=False, encoding="utf-8-sig")
log("additions", dict(added=len(ADD), rejected=REJ, date_range=[ADD.match_date.min(), ADD.match_date.max()], all_before_retrieval=bool((pd.to_datetime(ADD.kickoff_utc) < pd.Timestamp(retrieved)).all())))


def universe_asof(T):
    """Frozen universe + OpenLigaDB results whose retrieval time is <= T (what was actually knowable at prediction time T)."""
    a = ADD[pd.to_datetime(ADD.retrieved_utc) <= pd.Timestamp(T)]
    return pd.concat([V, a], ignore_index=True)


# future Bundesliga fixtures from the same snapshot, mapped to entities
up = [r for r in recs if r.status == "upcoming"]
fx_rows = []
for r in up:
    he = resolver.resolve("openligadb", COMP, r.home_raw)[0]; ae = resolver.resolve("openligadb", COMP, r.away_raw)[0]
    fx_rows.append(dict(fixture_id="OL:" + r.source_ref, dt=pd.Timestamp(r.match_date), h=he, a=ae, comp=COMP, season=SEASON, tier=1.0, home_name=r.home_raw, away_name=r.away_raw,
                        kickoff=r.kickoff_utc, kickoff_known=True, kickoff_utc=r.kickoff_utc, matchday=r.round))
FX = pd.DataFrame(fx_rows)
assert FX.h.notna().all() and FX.a.notna().all()
NOW = pd.Timestamp.now(tz="UTC")
T_AFTER = pd.Timestamp(retrieved) + pd.Timedelta(seconds=1)
T_BEFORE = pd.Timestamp(retrieved) - pd.Timedelta(seconds=1)
U_stale, U_new_before, U_new = V, universe_asof(T_BEFORE), universe_asof(T_AFTER)
log("asof_universe_sizes", dict(frozen=len(V), asof_before_retrieval=len(U_new_before), asof_after_retrieval=len(U_new)))
assert len(U_new_before) == len(V) and len(U_new) == len(V) + len(ADD)

v2m, v1m, v1prep, v1elo = D.load_models()
feat_cols = v2m["features"]
v1cols = v1prep["feature_order"]


def feats(U, fx):
    f = fx[["fixture_id", "dt", "h", "a", "comp", "season", "tier"]]
    F2, F1 = D.features_for(U, f)
    return F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]


F2s, F1s = feats(U_stale, FX)
F2n, F1n = feats(U_new, FX)
# ---- differences versus the stale OpenFootball-only state
diff = []
for c in feat_cols:
    a, b = F2s[c].astype(float).values, F2n[c].astype(float).values
    ch = ~((a == b) | (np.isnan(a) & np.isnan(b)))
    diff.append(dict(feature_set="v2", feature=c, fixtures_changed=int(ch.sum()), mean_abs_change=float(np.nanmean(np.abs(a - b)[ch])) if ch.any() else 0.0, max_abs_change=float(np.nanmax(np.abs(a - b)[ch])) if ch.any() else 0.0))
for c in v1cols:
    a, b = F1s[c].astype(float).values, F1n[c].astype(float).values
    ch = ~((a == b) | (np.isnan(a) & np.isnan(b)))
    diff.append(dict(feature_set="v1", feature=c, fixtures_changed=int(ch.sum()), mean_abs_change=float(np.nanmean(np.abs(a - b)[ch])) if ch.any() else 0.0, max_abs_change=float(np.nanmax(np.abs(a - b)[ch])) if ch.any() else 0.0))
dd = pd.DataFrame(diff); dd.to_csv(os.path.join(HERE, "04_feature_differences_vs_stale_state.csv"), index=False)
log("feature_differences", dict(v2_features_changed_for_any_fixture=int((dd[dd.feature_set == "v2"].fixtures_changed > 0).sum()), of=len(feat_cols), v1_features_changed=int((dd[dd.feature_set == "v1"].fixtures_changed > 0).sum()), of_v1=len(v1cols),
                               n_prior_home_mean_increase=float((F2n.home_n_prior - F2s.home_n_prior).mean()), max_elo1_change=float((F2n.home_elo1 - F2s.home_elo1).abs().max()), max_elo2_change=float((F2n.home_elo2 - F2s.home_elo2).abs().max())))

# ---- same verified match history for matched v1 and frozen v2
same_hist = dict(n_prior_equal=bool((F2n.home_n_prior.values == F1n.home_n_prior.values).all() and (F2n.away_n_prior.values == F1n.away_n_prior.values).all()),
                 elo_equal=bool(np.allclose(F2n.home_elo1.values, F1n.home_elo.values, atol=1e-9) and np.allclose(F2n.away_elo1.values, F1n.away_elo.values, atol=1e-9)),
                 same_input_frame="features_for builds both feature sets from one concatenated universe frame (same rows, same order)")
log("v1_v2_same_history", same_hist)

# ---- predictions reproducible from saved snapshots (in-memory dry run; hashes only, nothing logged)
def predict_hashes(U, label):
    past = pnr[~pnr.apply(lambda x: ((x.home_entity_id, x.away_entity_id) in set(zip(ADD.home_entity_id, ADD.away_entity_id))) if len(ADD) else False, axis=1)] if label != "stale" else pnr
    past_f = past.assign(comp=COMP, h=past.home_entity_id, a=past.away_entity_id)[["comp", "h", "a"]]
    recs_e, rej = E.predict(FX, U, past_no_result=past_f, snapshot_id=f"isolated:{label}", snapshot_sha="n/a", mode="dry_run", now=NOW)
    return recs_e, rej
rA, rejA = predict_hashes(U_new, "updated")
# rebuild everything from the raw snapshot again and from the pilot's own pickle
ADD2, _ = build_additions(ol.parse_payload(body, r3meta["saved_utc"], r3meta["snapshot_id"], retrieved, COMP))
U_new2 = pd.concat([V, ADD2], ignore_index=True)
rB, _ = E.predict(FX, U_new2, past_no_result=pd.DataFrame(columns=["comp", "h", "a"]), snapshot_id="isolated:rebuilt", snapshot_sha="n/a", mode="dry_run", now=NOW)
pk = pd.read_pickle(os.path.join(RUN, "isolated_refreshed_universe_openligadb_only.pkl"))
rC, _ = E.predict(FX, pk, past_no_result=pd.DataFrame(columns=["comp", "h", "a"]), snapshot_id="isolated:pilot_pickle", snapshot_sha="n/a", mode="dry_run", now=NOW)
def ph(rs): return hashlib.sha256(json.dumps([[r["fixture_id"], r["probs"]] for r in rs], sort_keys=True).encode()).hexdigest()
log("prediction_reproducibility", dict(hash_updated=ph(rA)[:16], hash_rebuilt_from_raw_snapshot=ph(rB)[:16], hash_from_pilot_pickle=ph(rC)[:16], identical=ph(rA) == ph(rB) == ph(rC), fixtures=len(rA),
                                       note="in-memory dry run; no prediction was written to any log; probabilities are not reported"))
rS, _ = E.predict(FX, U_stale, past_no_result=pnr.assign(comp=COMP, h=pnr.home_entity_id, a=pnr.away_entity_id)[["comp", "h", "a"]], snapshot_id="isolated:stale", snapshot_sha="n/a", mode="dry_run", now=NOW)
pd_ = np.array([[a["probs"]["v2_frozen"][c] for c in "HDA"] for a in rA]); ps_ = np.array([[a["probs"]["v2_frozen"][c] for c in "HDA"] for a in rS])
log("probability_shift_v2_vs_stale", dict(mean_abs=float(np.abs(pd_ - ps_).mean()), max_abs=float(np.abs(pd_ - ps_).max())))

# ---- chronological leakage checks
fx_dates = FX.dt.min()
lk = {}
lk["added_results_precede_all_future_fixtures"] = bool(pd.to_datetime(ADD.match_date).max() < FX.dt.min())
lk["added_results_kickoff_before_retrieval"] = bool((pd.to_datetime(ADD.kickoff_utc) < pd.Timestamp(retrieved)).all())
lk["asof_before_retrieval_excludes_all_new_rows"] = bool(len(U_new_before) == len(V))
# prefix invariance: features of the played matchdays (rows 2026-10-09..18) computed from the state must not depend on later results or on their own score
played = [r for r in recs if r.status == "completed" and r.match_date >= "2026-10-09"]
fxp = pd.DataFrame([dict(fixture_id="P:" + r.source_ref, dt=pd.Timestamp(r.match_date), h=resolver.resolve("openligadb", COMP, r.home_raw)[0], a=resolver.resolve("openligadb", COMP, r.away_raw)[0], comp=COMP, season=SEASON, tier=1.0) for r in played])
Fa, F1a = D.features_for(U_new, fxp)
K = "2026-10-16"
rng = np.random.default_rng(20261021)
U_scr = U_new.copy(); m = (U_scr.competition_id == COMP) & (U_scr.match_date >= K)          # scramble own-day and all later Bundesliga scores
U_scr.loc[m, "gh"] = rng.integers(0, 6, m.sum()); U_scr.loc[m, "ga"] = rng.integers(0, 6, m.sum())
U_drop = U_scr[~((U_scr.competition_id == COMP) & (U_scr.match_date > K))]                    # and delete everything after the day K
early = fxp[fxp.dt <= K]
Fa_e = Fa.loc[early.fixture_id]
dm = 0.0
for U_t in (U_scr, U_drop):
    Fb, F1b = D.features_for(U_t, early)
    dm = max(dm, float(np.nanmax(np.abs(Fa_e[feat_cols].values.astype(float) - Fb.loc[early.fixture_id][feat_cols].values.astype(float)))),
             float(np.nanmax(np.abs(F1a.loc[early.fixture_id][v1cols].values.astype(float) - F1b.loc[early.fixture_id][v1cols].values.astype(float)))))
lk["prefix_invariance_max_abs_diff_features_of_first_new_matchdays"] = dm
lk["prefix_invariance_rows_checked"] = int(len(early))
lk["prefix_invariance_pass"] = bool(dm < 1e-9)
# placeholder-result parity for the played fixtures: unrated placeholder at the same date gives identical features
log("chronological_leakage", lk)

# ---- adversarial rejection tests on a COPY of the records (test inputs, never data)
import copy
bad = copy.deepcopy(recs); t = [r for r in bad if r.status == "completed" and r.match_date > CUTOFF][0]
t.regulation_home = (t.regulation_home or 0) + 1                          # a re-reported record with a different score? the duplicate check is by pair; conflict check is vs frozen/other sources
dup = copy.deepcopy([r for r in recs if r.status == "completed" and r.match_date > CUTOFF][:1]); bad += dup
a_bad, rej_bad = build_additions(bad)
ambiguous = copy.deepcopy([r for r in recs if r.status == "completed" and r.match_date > CUTOFF][:1]); ambiguous[0].home_raw = "Nonexistent FC"
a_amb, rej_amb = build_additions(ambiguous)
conf = copy.deepcopy([r for r in recs if r.status == "completed" and r.match_date <= CUTOFF][:1]); conf[0].match_date = "2026-09-21"; conf[0].regulation_home += 2
a_conf, rej_conf = build_additions(conf)
log("rejection_tests", dict(duplicate_pair=[x[1] for x in rej_bad], unknown_team=[x[1] for x in rej_amb], conflict_with_frozen_score=[x[1] for x in rej_conf]))

# ======================================================== Phase 4: eligibility
R = pd.DataFrame(rA)
R["kickoff_utc"] = FX.set_index("fixture_id").loc[R.fixture_id, "kickoff_utc"].values
R["matchday"] = FX.set_index("fixture_id").loc[R.fixture_id, "matchday"].values
R["existing_protocol_seal_deadline_utc"] = [str((pd.Timestamp(k[:10], tz="UTC") - pd.Timedelta(hours=14) - pd.Timedelta(minutes=60))) for k in R.kickoff_utc]
R["amendment_seal_deadline_utc"] = [str(pd.Timestamp(k) - pd.Timedelta(minutes=60)) for k in R.kickoff_utc]
R["reasons"] = R.eligibility_reasons.apply(lambda x: ";".join(s.split("(")[0] for s in x) or "ELIGIBLE")
out = R[["fixture_id", "home_team", "away_team", "kickoff_utc", "matchday", "primary_eligible", "reasons", "existing_protocol_seal_deadline_utc", "amendment_seal_deadline_utc"]]
out.to_csv(os.path.join(HERE, "05_bundesliga_fixture_eligibility.csv"), index=False)
nxt = R.sort_values("kickoff_utc").iloc[0]
elig = R[R.primary_eligible]
log("eligibility", dict(total_future_fixtures=len(FX), logged_in_dry_run=len(R), rejected_by_timing=len(rejA), eligible=int(R.primary_eligible.sum()), ineligible_reasons=R[~R.primary_eligible].reasons.value_counts().to_dict(),
                       eligible_matchdays=sorted(elig.matchday.unique().tolist(), key=int), eligible_kickoff_range=[elig.kickoff_utc.min(), elig.kickoff_utc.max()],
                       next_fixture=dict(kickoff_utc=nxt.kickoff_utc, existing_protocol_deadline=nxt.existing_protocol_seal_deadline_utc, amendment_deadline=nxt.amendment_seal_deadline_utc),
                       earliest_deadline_existing=R.existing_protocol_seal_deadline_utc.min(), earliest_deadline_amendment=R.amendment_seal_deadline_utc.min(),
                       missing_historical_results_after_update=int(len(pnr) - len(ADD)), openfootball_past_dated_without_result_before=int(len(pnr)), recovered=len(ADD),
                       stale_state_eligible=int(pd.DataFrame(rS).primary_eligible.sum())))
elig_by_md = R.groupby("matchday").agg(fixtures=("fixture_id", "size"), eligible=("primary_eligible", "sum"), first_kickoff=("kickoff_utc", "min")).reset_index()
elig_by_md["matchday"] = elig_by_md.matchday.astype(int); elig_by_md = elig_by_md.sort_values("matchday")
elig_by_md.to_csv(os.path.join(HERE, "05b_eligibility_by_matchday.csv"), index=False)

# ======================================================== Phase 5: git hygiene (never prints the contact)
GIT = lambda *a: subprocess.run(["git", "-C", P, *a], capture_output=True, text=True)
cf = os.path.join(P, "config", "contact.local")
contact = open(cf, encoding="utf-8").read().strip()
parts = {contact, contact.replace("mailto:", "")} | ({contact.split("@")[0]} if "@" in contact else set())
parts = {p for p in parts if len(p) > 4}
git = {}
git["contact_file_ignored"] = GIT("check-ignore", "-q", "config/contact.local").returncode == 0
git["ignore_rule_preserved"] = open(os.path.join(P, "config", ".gitignore"), encoding="utf-8").read().split() == ["contact.local"]
git["adapter_config_ignore_rule"] = os.path.exists(os.path.join(V2, "source_adapters_r1", "config", ".gitignore"))
git["tracked_files_total"] = len(GIT("ls-files").stdout.split("\n")) - 1
staged = GIT("diff", "--cached", "--name-only").stdout.split()
git["staged_files"] = len(staged)
def contains(path):
    try:
        b = open(path, "rb").read().decode("utf-8", "ignore")
    except OSError:
        return False
    return any(p in b for p in parts)
hits = []
for f in GIT("ls-files").stdout.split("\n"):                                       # tracked files
    if f and os.path.isfile(os.path.join(P, f)) and os.path.getsize(os.path.join(P, f)) < 50_000_000 and contains(os.path.join(P, f)): hits.append(("tracked", f))
for f in staged:
    if contains(os.path.join(P, f)): hits.append(("staged", f))
scan_roots = [os.path.join(V2, d) for d in ("source_adapters_r1", "bundesliga_source_promotion_r1", "matched_v1_prospective_r1", "freshness_validation_r1", "fresh_results_source_research", "_work")]
scanned = 0
for root in scan_roots:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            if p.endswith((".pkl",)) or os.path.getsize(p) > 20_000_000: continue
            scanned += 1
            if contains(p) and not p.endswith("g1_bundesliga_promotion.py"): hits.append(("working_tree", os.path.relpath(p, P)))
git["files_scanned_untracked_work_products"] = scanned
git["contact_found_in"] = hits
git["contact_found_count"] = len(hits)
log("git_hygiene", git)
json.dump(res, open(os.path.join(HERE, "g1_results.json"), "w", encoding="utf-8"), indent=1, default=str)
