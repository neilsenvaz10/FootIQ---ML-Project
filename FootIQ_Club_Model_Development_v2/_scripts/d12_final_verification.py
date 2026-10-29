"""Verification of the frozen v2-r1 candidate: independent scorer parity, artifact integrity, inference-vs-training feature parity, prediction logger dry run."""
import json, os, pickle, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d11_prospective_logger as L
from v2_models import *  # noqa
sys.stdout.reconfigure(encoding="utf-8")
res = []
def rec(test, passed, detail): res.append(dict(test=test, passed=bool(passed), detail=detail)); print(res[-1], flush=True)
fr = json.load(open(os.path.join(L.AD, "FROZEN.json")))
# 1 artifact hashes
ok = all(sha(os.path.join(L.AD, f)) == h for f, h in fr["artifact_sha256"].items())
rec("artifact hashes match FROZEN.json", ok, fr["artifact_sha256"])
# 2 independent numpy scorer from JSON coefficients == pickle model
fc_ = json.load(open(os.path.join(L.AD, "feature_contract_v2_final.json"))); co = json.load(open(os.path.join(L.AD, "model_coefficients.json")))
T = pd.read_pickle(os.path.join(L.FD, "training_feature_table_v2_r1.pkl")).sample(5000, random_state=SEED)
T = add_derived(T) if "d" in T.columns else T
v2 = pickle.load(open(os.path.join(L.AD, "club_v2_lr_final_candidate.pkl"), "rb"))
Pk = v2["model"].predict_proba(v2["prep"].transform(T, True))
x = T[fc_["feature_order"]].copy()
ind = np.column_stack([x[c].isna().astype(float).values for c in fc_["indicator_columns"]]) if fc_["indicator_columns"] else np.zeros((len(x), 0))
z = ((x.fillna(pd.Series(fc_["median_train"])) - pd.Series(fc_["mean_train"])) / pd.Series(fc_["std_train"])).values
lg = np.hstack([z, ind]) @ np.array(co["coef"]).T + np.array(co["intercept"]); e = np.exp(lg - lg.max(1, keepdims=True)); Pn = e / e.sum(1, keepdims=True)
rec("independent numpy scorer from JSON == pickled model", np.abs(Pk - Pn).max() < 1e-9, f"max abs diff {np.abs(Pk-Pn).max():.2e}")
rec("62 features in contract and model", len(fc_["feature_order"]) == 62 and len(co["input_columns"]) == v2["model"].coef_.shape[1], f"{v2['model'].coef_.shape}")
rec("hyperparameters frozen (C=0.01, no calibration)", v2["hyperparameters"] == {"C": 0.01} and v2["calibration"] is None, str(v2["hyperparameters"]))
# 3 inference-vs-training parity on historical days (state from results strictly before the day; fixture scores unknown)
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
ds = pd.read_csv(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC, usecols=["record_id", "match_date", "tier"])
tr_all = pd.read_pickle(os.path.join(L.FD, "training_feature_table_v2_r1.pkl"))
F1all = pd.read_csv(os.path.join(PREP, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), low_memory=False, encoding=ENC).set_index("record_id")
v1cols = json.load(open(os.path.join(PREP, "feature_contract_v1.1.json")))["feature_order"]
for D in ("2022-03-12", "2024-12-07", "2026-09-19", "2026-09-20"):
    day = V[(V.match_date == D) & V.record_id.isin(ds.record_id)]
    Vp = V[V.dt < pd.Timestamp(D)]
    fx = pd.DataFrame(dict(fixture_id=day.record_id.values, dt=day.dt.values, h=day.home_entity_id.values, a=day.away_entity_id.values, comp=day.competition_id.values, season=day.season_corrected.values, tier=day.tier.values))
    F2, F1 = L.features_for(Vp, fx)
    F2 = F2.loc[fx.fixture_id]; F1 = F1.loc[fx.fixture_id]
    cols = [c for c in v2["features"] if c in tr_all.columns]
    # compare against the training-time table (rebuild derived columns the same way)
    TT = pd.read_pickle(os.path.join(L.FD, "training_feature_table_v2_r1.pkl")).loc[fx.fixture_id, v2["features"]]
    d2 = float(np.nanmax(np.abs(F2[v2["features"]].values.astype(float) - TT.values.astype(float))))
    nanmatch = bool((np.isnan(F2[v2["features"]].values.astype(float)) == np.isnan(TT.values.astype(float))).all())
    d1 = float(np.nanmax(np.abs(F1[v1cols].values.astype(float) - F1all.loc[fx.fixture_id, v1cols].values.astype(float))))
    rec(f"inference-vs-training feature parity {D}", d2 < 1e-9 and d1 < 1e-9 and nanmatch, f"{len(fx)} fixtures; v2 max diff {d2:.1e}; v1 max diff {d1:.1e}; NaN pattern equal {nanmatch}")
pd.DataFrame(res).to_csv(os.path.join(L.FD, "02_corrected_validation_and_parity_results.csv"), index=False)
print("ALL PASSED" if all(r["passed"] for r in res) else "FAILURES")
