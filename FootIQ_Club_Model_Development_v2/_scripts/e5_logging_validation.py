"""Validation of the prospective logger (e4) + a dry run. Dry-run records never count for evaluation."""
import json, os, shutil, sys, tempfile, stat
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e4_prospective_logger as E
import d11_prospective_logger as D
from v2_common import *  # noqa
sys.stdout.reconfigure(encoding="utf-8")
res = []
def rec(t, ok, d): res.append(dict(test=t, passed=bool(ok), detail=str(d))); print(res[-1], flush=True)

V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
snap_sha = sha(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
u = pd.read_csv(os.path.join(P, "FootIQ_Dataset_Submission", "09_Upcoming_Fixtures.csv"), low_memory=False)
u = u[u.competition_type == "domestic_league"]
ent = pd.concat([V[["competition_id", "home_team_name", "home_entity_id"]].set_axis(["competition_id", "n", "e"], axis=1), V[["competition_id", "away_team_name", "away_entity_id"]].set_axis(["competition_id", "n", "e"], axis=1)])
ent = ent.assign(s=ent.e.str.startswith("SRCSCOPED|")).sort_values("s").drop_duplicates(["competition_id", "n"])
tier = V.groupby("competition_id").tier.first()
def mk(df):
    df = df.merge(ent[["competition_id", "n", "e"]].rename(columns={"n": "home_team", "e": "h"}), on=["competition_id", "home_team"], how="left").merge(
        ent[["competition_id", "n", "e"]].rename(columns={"n": "away_team", "e": "a"}), on=["competition_id", "away_team"], how="left").dropna(subset=["h", "a"])
    return pd.DataFrame(dict(fixture_id=df.match_id.values, dt=pd.to_datetime(df.match_date).values, h=df.h.values, a=df.a.values, comp=df.competition_id.values, season=df.season.values,
                             tier=df.competition_id.map(tier).values, home_name=df.home_team.values, away_name=df.away_team.values,
                             kickoff=(df.match_date + " " + df.kickoff_time_local.fillna("00:00")).values, kickoff_known=df.kickoff_time_local.notna().values))
up = mk(u[(u.fixture_status == "upcoming") & (u.match_date >= "2026-10-22") & (u.match_date <= "2026-11-08")])
past = mk(u[u.fixture_status == "past_date_no_result_in_source"])
print("fixtures", len(up), "past-date-no-result fixtures", len(past))

# ---- dry run (counts_for_evaluation False)
recs, rej = E.predict(up, V, "frozen_universe_2026-10-20", snap_sha, "dry_run", past_no_result=past) if False else E.predict(up, V, past_no_result=past, snapshot_id="frozen_universe_2026-10-20", snapshot_sha=snap_sha, mode="dry_run")
dry_dir = os.path.join(E.LOGDIR, "DRY_RUN")
if os.path.exists(os.path.join(dry_dir, "CHAIN.jsonl")):
    for f in os.listdir(dry_dir): os.chmod(os.path.join(dry_dir, f), stat.S_IWRITE); os.remove(os.path.join(dry_dir, f))
(path, h), d = E.append_batch(recs, "dry_run", "dry_run_batch_001")
rej.to_csv(os.path.join(E.NEW, "08b_dry_run_rejected_fixtures.csv"), index=False)
R = pd.DataFrame(recs)
rec("dry run wrote an immutable chained batch", E.verify_chain(d) and not os.access(path, os.W_OK), f"{len(recs)} predictions, {len(rej)} rejected; {h[:12]}")
rec("dry-run records do not count for evaluation", (~R.counts_for_evaluation).all() and (R["mode"] == "dry_run").all(), "counts_for_evaluation=False")
soon = up.head(2).copy(); soon["dt"] = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize(); soon["fixture_id"] = ["soon1", "soon2"]
r_s, rj_s = E.predict(soon, V, past_no_result=past, snapshot_id="t", snapshot_sha="t", mode="dry_run")
rec("a fixture whose earliest possible kickoff is less than 60 min away (e.g. today) is rejected", len(r_s) == 0 and len(rj_s) == 2 and rj_s.reason.str.contains("backdating").all(), rj_s.reason.unique().tolist())
# ---- probabilities
ok = True
for m in ("v2_frozen", "v1_original", "v1_matched", "v1_elo"):
    pm = np.array([[x["probs"][m][c] for c in "HDA"] for x in recs]); ok &= np.allclose(pm.sum(1), 1) and (pm > 0).all()
rec("all four probability sets sum to 1 and are positive", ok, "")
# ---- v2 equals earlier dry run + independent scorers
old = [json.loads(l) for l in open(os.path.join(D.FD, "prospective_log", "DRY_RUN", "dry_run_batch_001.jsonl"), encoding="utf-8")]
od = {x["fixture_id"]: x for x in old}
diffs = [abs(x["probs"]["v2_frozen"]["H"] - od[x["fixture_id"]]["p_home"]) for x in recs if x["fixture_id"] in od]
rec("v2 probabilities identical to the previous dry run for the same fixtures", len(diffs) > 0 and max(diffs) < 1e-12, f"{len(diffs)} common, max diff {max(diffs):.1e}")
vdiff = [abs(x["probs"]["v1_original"]["H"] - od[x["fixture_id"]]["v1_p_home"]) for x in recs if x["fixture_id"] in od]
rec("original-v1 probabilities identical to previous dry run", max(vdiff) < 1e-12, f"max diff {max(vdiff):.1e}")
fx = up[up.fixture_id.isin(R.fixture_id)].reset_index(drop=True)
_, F1 = D.features_for(V, fx); F1 = F1.loc[fx.fixture_id]
co = json.load(open(os.path.join(E.MAD, "matched_v1_coefficients.json"))); pr = json.load(open(os.path.join(E.MAD, "matched_v1_preprocessing.json")))
x = F1[pr["feature_order"]]
ind = np.column_stack([x[c].isna().astype(float).values for c in pr["indicator_columns"]])
z = ((x.fillna(pd.Series(pr["median_train"])) - pd.Series(pr["mean_train"])) / pd.Series(pr["std_train"])).values
lg = np.hstack([z, ind]) @ np.array(co["coef"]).T + np.array(co["intercept"]); e = np.exp(lg - lg.max(1, keepdims=True)); Pn = e / e.sum(1, keepdims=True)
Pm = np.array([[r["probs"]["v1_matched"][c] for c in "HDA"] for r in R.set_index("fixture_id").loc[fx.fixture_id].reset_index().to_dict("records")])
rec("matched-v1 probabilities equal an independent numpy scorer", np.abs(Pm - Pn).max() < 1e-9, f"max diff {np.abs(Pm-Pn).max():.1e}")
rec("model hashes stored in every record equal the artifacts on disk", all(x["model_hashes"] == E.verify_models() for x in recs), E.verify_models())
# ---- backdating / completed-fixture rejection
done = V[V.match_date == "2026-09-20"].head(5)
bd = pd.DataFrame(dict(fixture_id=done.record_id.values, dt=pd.to_datetime(done.match_date).values, h=done.home_entity_id.values, a=done.away_entity_id.values, comp=done.competition_id.values, season=done.season_corrected.values,
                       tier=done.tier.values, home_name=done.home_team_name.values, away_name=done.away_team_name.values, kickoff="2026-09-20 00:00", kickoff_known=False))
r2, rj2 = E.predict(bd, V, past_no_result=past, snapshot_id="t", snapshot_sha="t", mode="dry_run")
rec("completed historical fixtures cannot be predicted (backdating refused)", len(r2) == 0 and len(rj2) == 5, rj2.reason.unique().tolist())
# ---- official mode gated
try:
    E.predict(up.head(3), V, past_no_result=past, snapshot_id="t", snapshot_sha="t", mode="official"); gated = False
except PermissionError as ex:
    gated = True
rec("official mode refuses without owner approval + pre-registration", gated and not os.path.exists(E.APPROVAL), "no OFFICIAL_LOGGING_APPROVED.json present")
# ---- tamper detection + read-only
tmp = tempfile.mkdtemp(); shutil.copytree(d, os.path.join(tmp, "c"))
bf = os.path.join(tmp, "c", "dry_run_batch_001.jsonl"); os.chmod(bf, stat.S_IWRITE)
s = open(bf, "rb").read(); open(bf, "wb").write(s.replace(b'"H": 0.', b'"H": 0.9', 1))
rec("tampering with a stored batch is detected by the chain check", (not D.verify_chain(os.path.join(tmp, "c"))) and E.verify_chain(d), "")
try:
    open(path, "a").write("x"); ro = False
except PermissionError:
    ro = True
rec("stored batch is read-only", ro, path)
# ---- eligibility logic with injected clock (in-memory only, nothing is logged)
fx_c = pd.DataFrame(dict(fixture_id=["TEST-collision"], dt=pd.to_datetime(["2026-12-05"]), h=["world/africa|Police FC"], a=[V[V.competition_id == "world/africa:rw1"].home_entity_id.iloc[0]], comp=["world/africa:rw1"], season=["2026-27"],
                         tier=[1.0], home_name=["Police FC"], away_name=["x"], kickoff=["2026-12-05 00:00"], kickoff_known=[False]))
r3, _ = E.predict(fx_c, V, past_no_result=past.iloc[0:0], snapshot_id="t", snapshot_sha="t", mode="dry_run", now=pd.Timestamp("2026-12-01", tz="UTC"))
rec("identity-collision fixture flagged ineligible", len(r3) == 1 and "identity_collision_unresolved" in r3[0]["eligibility_reasons"] and not r3[0]["primary_eligible"], r3[0]["eligibility_reasons"] if r3 else "")
# ---- eligibility summary of the dry run
allr = pd.Series([";".join(x["eligibility_reasons"]) or "ELIGIBLE" for x in recs]).str.replace(r"\(gap_days=\d+\)", "", regex=True).value_counts()
allr.to_csv(os.path.join(E.NEW, "08c_dry_run_eligibility_summary.csv"), header=["fixtures"])
print(allr.to_string())
pd.DataFrame(res).to_csv(os.path.join(E.NEW, "08_prospective_logging_validation.csv"), index=False)
print("ALL PASSED" if all(r["passed"] for r in res) else "FAILURES")
