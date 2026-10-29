"""Task 1 (frozen-model integrity) and Task 2 (club identity defect audit) for matched_v1_prospective_r1. Read-only on all inputs."""
import json, os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d11_prospective_logger as L
from v2_models import *  # noqa
sys.stdout.reconfigure(encoding="utf-8")
NEW = os.path.join(OUT, "matched_v1_prospective_r1"); os.makedirs(NEW, exist_ok=True)
out = {}
# ---------------- 1. integrity
fr = json.load(open(os.path.join(L.AD, "FROZEN.json")))
USER_HASH = "55c1e4c53bcfefd39d5e90a1ce60a75bc697668f7894e425305bdc9a65b3e56c"
integ = []
for f, h in fr["artifact_sha256"].items():
    a = sha(os.path.join(L.AD, f)); integ.append(dict(item=f"v2-r1/{f}", expected=h, actual=a, ok=h == a))
a = sha(os.path.join(L.AD, "club_v2_lr_final_candidate.pkl"))
integ.append(dict(item="v2-r1 candidate pickle vs hash quoted in the instruction", expected=USER_HASH, actual=a, ok=a == USER_HASH))
v1f = json.load(open(os.path.join(V1, "artifacts", "FROZEN.json")))
def nsha(path):
    b = open(path, "rb").read()
    if path.endswith(".json"):
        b = b.replace(bytes([13, 10]), bytes([10])).replace(bytes([10]), bytes([13, 10]))
    return hashlib.sha256(b).hexdigest()
for f, h in v1f["artifact_sha256"].items():
    a = sha(os.path.join(V1, "artifacts", f)); n = nsha(os.path.join(V1, "artifacts", f))
    integ.append(dict(item=f"v1/{f}" + ("" if a == h else " (CRLF-normalised hash: git autocrlf changed line endings only)"), expected=h, actual=a if a == h else n, ok=h == a or n == h))
trf = os.path.join(L.FD, "training_feature_table_v2_r1.pkl")
a = sha(trf); integ.append(dict(item="v2-r1 training feature table", expected=fr["input_sha256"]["training_feature_table"], actual=a, ok=a == fr["input_sha256"]["training_feature_table"]))
ds_path = os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv")
a = sha(ds_path); integ.append(dict(item="dataset v1.1", expected=fr["input_sha256"]["dataset_v1_1"], actual=a, ok=a == fr["input_sha256"]["dataset_v1_1"]))
wc = json.load(open(os.path.join(L.FD, "07_REPRODUCIBILITY_MANIFEST.json")))["world_cup_model_sha256"]
a = sha(os.path.join(P, "data", "model_artifacts", "v27", "live_match_model.pkl"))
integ.append(dict(item="World Cup model v27 (vs hash recorded in the previous step)", expected=wc, actual=a, ok=a == wc))
pd.DataFrame(integ).to_csv(os.path.join(NEW, "01_frozen_model_integrity.csv"), index=False)
print(pd.DataFrame(integ)[["item", "ok"]].to_string())
assert all(r["ok"] for r in integ)

# ---------------- 2. identity audit
H = pd.read_csv(os.path.join(P, "FootIQ_Dataset_Submission", "02_Historical_Club_Matches.csv"), low_memory=False)
H["country_folder"] = np.where(H.source_file.str.startswith("world/"), H.source_file.str.split("/").str[2], H.source_file.str.split("/").str[1])
w = H[H.home_team_id.str.startswith("world/") | H.away_team_id.str.startswith("world/")]
L2 = pd.concat([w[["home_team_id", "country_folder", "competition_id", "match_id"]].set_axis(["e", "cf", "c", "m"], axis=1),
                w[["away_team_id", "country_folder", "competition_id", "match_id"]].set_axis(["e", "cf", "c", "m"], axis=1)])
L2 = L2[L2.e.str.startswith("world/")]
cc = L2.groupby("e").cf.nunique(); coll = cc[cc > 1]
coll_tab = L2[L2.e.isin(coll.index)].groupby(["e", "cf", "c"]).size().reset_index(name="rows_in_source")
coll_tab.to_csv(os.path.join(NEW, "02a_cross_country_entity_collisions_all_sources.csv"), index=False)
print(coll_tab.to_string())
ds = pd.read_csv(ds_path, low_memory=False, encoding=ENC)
inv = ds[ds.home_entity_id.isin(coll.index) | ds.away_entity_id.isin(coll.index)]
out["collision_entities"] = list(coll.index)
out["training_rows_touching_collisions"] = int(len(inv)); out["by_split"] = inv.split.value_counts().to_dict()
out["source_rows_by_entity_country_competition"] = {f"{r.e}|{r.cf}|{r.c}": int(r.rows_in_source) for r in coll_tab.itertuples()}
z = ds[(ds.competition_id == "world/africa:zw1") & (ds.season_corrected == "2021-22")]
out["zw1_2021_22_training_rows"] = int(len(z)); out["zw1_by_split"] = z.split.value_counts().to_dict()
zz = pd.concat([z[["record_id", "match_date", "home_entity_id"]].set_axis(["r", "d", "e"], axis=1), z[["record_id", "match_date", "away_entity_id"]].set_axis(["r", "d", "e"], axis=1)])
dup = zz.groupby(["e", "d"]).r.nunique(); out["zw1_same_club_same_date_pairs"] = int((dup > 1).sum())
out["zw1_source_observation"] = "openfootball world@42df8203 africa/zimbabwe/2021-22_zw1.txt: header 'Date Fri Jul 2 2021 - Sun Jun 26 2022'; Matchday 1-18 dated 2021-11-05..2022-06-26, Matchday 19-34 dated 2021-07-02..2021-11-13 (dates carry explicit weekday+year); upstream cited: rsssf zimb2021.html"

# --- materiality: frozen v2 predictions with as-is vs corrected-identity state, for current upcoming fixtures
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
fx_all = pd.read_csv(os.path.join(P, "FootIQ_Dataset_Submission", "09_Upcoming_Fixtures.csv"), low_memory=False)
fx_all = fx_all[(fx_all.competition_type == "domestic_league") & (fx_all.fixture_status == "upcoming") & (fx_all.match_date >= "2026-10-22")]


def fixtures_for(Vx):
    ent = pd.concat([Vx[["competition_id", "home_team_name", "home_entity_id"]].set_axis(["competition_id", "n", "e"], axis=1),
                     Vx[["competition_id", "away_team_name", "away_entity_id"]].set_axis(["competition_id", "n", "e"], axis=1)]).drop_duplicates(["competition_id", "n"], keep="last")
    u = fx_all.merge(ent.rename(columns={"n": "home_team", "e": "h"}), on=["competition_id", "home_team"], how="left").merge(
        ent.rename(columns={"n": "away_team", "e": "a"}), on=["competition_id", "away_team"], how="left").dropna(subset=["h", "a"])
    tier = Vx.groupby("competition_id").tier.first()
    return pd.DataFrame(dict(fixture_id=u.match_id.values, dt=pd.to_datetime(u.match_date).values, h=u.h.values, a=u.a.values, comp=u.competition_id.values,
                             season=u.season.values, tier=u.competition_id.map(tier).values))


v2 = L.load_models()[0]


def predict(Vx):
    fx = fixtures_for(Vx)
    F2, _ = L.features_for(Vx, fx)
    F2 = F2.loc[fx.fixture_id]
    return fx, pd.DataFrame(v2["model"].predict_proba(v2["prep"].transform(F2, True)), index=fx.fixture_id, columns=["pH", "pD", "pA"])


fxA, PA = predict(V)
Vc = V.copy()
cmap = {("world/africa:rw1", "Police FC"): "rwanda", ("world/africa:ug1", "Police FC"): "uganda", ("world/africa:gh1", "Vision FC"): "ghana", ("world/africa:rw1", "Vision FC"): "rwanda"}
for side in ("home", "away"):
    for (c, nm), ctry in cmap.items():
        m = (Vc.competition_id == c) & (Vc[f"{side}_team_name"] == nm)
        Vc.loc[m, f"{side}_entity_id"] = f"world/africa/{ctry}|{nm}"
Vc = Vc[~((Vc.competition_id == "world/africa:zw1") & (Vc.season_corrected == "2021-22"))]
fxB, PB = predict(Vc)
cmp_ = fxA.set_index("fixture_id").join(PA).join(PB, rsuffix="_corr", how="inner")
cmp_["max_abs_dp"] = np.abs(cmp_[["pH", "pD", "pA"]].values - cmp_[["pH_corr", "pD_corr", "pA_corr"]].values).max(1)
fxi = fx_all.set_index("match_id")
cmp_["home_team"] = fxi.loc[cmp_.index, "home_team"].values; cmp_["away_team"] = fxi.loc[cmp_.index, "away_team"].values
names = {"Police FC", "Vision FC"}
cmp_["collision_fixture"] = [((h in names) or (a in names)) and any(k[0] == c and k[1] in (h, a) for k in cmap) for h, a, c in zip(cmp_.home_team, cmp_.away_team, cmp_.comp)]
cmp_["zw1_fixture"] = (cmp_.comp == "world/africa:zw1").values
cmp_.reset_index().to_csv(os.path.join(NEW, "02b_prediction_sensitivity_to_identity_corrections.csv"), index=False)
g = lambda m, f: (float(f(cmp_[m].max_abs_dp)) if m.any() else None)
out["materiality"] = dict(upcoming_fixtures_compared=len(cmp_), fixtures_with_any_change=int((cmp_.max_abs_dp > 1e-9).sum()), max_abs_dp_all=float(cmp_.max_abs_dp.max()),
                          collision_fixtures=int(cmp_.collision_fixture.sum()), collision_max=g(cmp_.collision_fixture, np.max), collision_mean=g(cmp_.collision_fixture, np.mean),
                          zw1_fixtures=int(cmp_.zw1_fixture.sum()), zw1_max=g(cmp_.zw1_fixture, np.max), zw1_mean=g(cmp_.zw1_fixture, np.mean),
                          other_fixtures=int((~cmp_.collision_fixture & ~cmp_.zw1_fixture).sum()), other_max=g(~cmp_.collision_fixture & ~cmp_.zw1_fixture, np.max))
prop = pd.DataFrame([dict(defect="club-id collision", current_entity_id=e, competition_id=c, source_country_folder=cf, proposed_entity_id=f"world/africa/{cf}|{e.split('|')[1]}", rows_in_source=n,
                          evidence="identical id string for different clubs; the openfootball files sit in different country folders (rwanda/uganda/ghana)")
                     for e, cf, c, n in coll_tab[["e", "cf", "c", "rows_in_source"]].itertuples(index=False)])
prop.to_csv(os.path.join(NEW, "02c_identity_correction_proposal.csv"), index=False)
z[["record_id", "match_date", "home_team_name", "away_team_name", "provenance"]].to_csv(os.path.join(NEW, "02d_zw1_2021_22_quarantine_candidates.csv"), index=False)
json.dump(out, open(os.path.join(NEW, "02_identity_audit_summary.json"), "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
excl = dict(version="r1", rule="a fixture whose club entity id (in that competition) is listed is logged but flagged ineligible_identity_collision_unresolved and excluded from the primary evaluation",
            entities=[dict(entity_id=e, competition_id=c) for e, c in zip(prop.current_entity_id, prop.competition_id)],
            flag_only=[dict(competition_id="world/africa:zw1", reason="2021-22 season dates non-chronological in source; sensitivity measured; flagged, see audit")])
json.dump(excl, open(os.path.join(NEW, "eligibility_exclusions_r1.json"), "w"), indent=1)
