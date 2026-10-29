"""Final refit of the development-selected v2 candidate (LR, 62 features, C=0.01, no calibration). No search, no re-selection.
Creates the frozen prospective candidate in final_refit_v2_r1/. Refuses to run twice."""
import json
import os
import pickle
import platform
import stat
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_models import *  # noqa
import v2_features as vf  # noqa
import sklearn, scipy  # noqa

sys.stdout.reconfigure(encoding="utf-8")
FD = os.path.join(OUT, "final_refit_v2_r1")
AD = os.path.join(FD, "artifacts")
os.makedirs(AD, exist_ok=True)
if os.path.exists(os.path.join(AD, "FROZEN.json")):
    sys.exit("final candidate already frozen - refusing to refit")
FREEZE_TS = time.strftime("%Y-%m-%d %H:%M:%S %z")
HP = dict(C=0.01)                                           # frozen development hyperparameter
FULL = json.load(open(os.path.join(WORK, "feature_selection.json")))["full_v2_features"]
assert len(FULL) == 62
meta = json.load(open(os.path.join(WORK, "features_v2_meta.json")))
P2 = meta["elo2_params"]; params = (P2["K"], P2["HA"], P2["season_regression"])
assert params == (30.0, 50.0, 0.0)

# ---- data: every eligible row of dataset v1.1 (extraction 2026-10-20, before the freeze) and the full results universe
ds_path = os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv")
ds = pd.read_csv(ds_path, low_memory=False, encoding=ENC)
assert ds.extraction_date.nunique() == 1 and ds.label_90_status.eq("confirmed").all()
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
cutoff_date = str(ds.match_date.max())
print("dataset rows", len(ds), "last match date", cutoff_date, "universe rows", len(V), "universe last", V.match_date.max())
assert V.match_date.max() == cutoff_date
df = pd.DataFrame(dict(record_id=V.record_id, dt=V.dt, h=V.home_entity_id, a=V.away_entity_id, comp=V.competition_id, season=V.season_corrected, tier=V.tier,
                       ctype=V.competition_type, regular=V.regular_round_robin_stage, rated=V.rated, gh=V.gh, ga=V.ga))
want = set(ds.record_id)
t0 = time.time()
Fall = vf.build(df, want, params)
print("features built", Fall.shape, round(time.time() - t0), "s")
Fall = Fall.join(ds.set_index("record_id")[["competition_id", "season_corrected", "calendar_type", "match_date", "split", "season_status", "identity_review_flag", "y_90min_1x2", "tier"]], how="left")
Fall["y"] = Fall.y_90min_1x2.map({"H": 0, "D": 1, "A": 2})
Fall["competition_id"] = Fall["competition_id"].astype(str)
assert Fall.y.notna().all()
Fall = add_derived(Fall)

# ---- pipeline-identity check: the refit feature generator reproduces the corrected development table exactly for development rows
dev = pd.read_pickle(os.path.join(WORK, "features_v2_dev.pkl"))
common = dev.index.intersection(Fall.index)
numc = [c for c in dev.columns if dev[c].dtype.kind in "fiu" and c != "y" and c in Fall.columns]
mx = max(float(np.nanmax(np.abs(dev.loc[common, c].values.astype(float) - Fall.loc[common, c].values.astype(float)))) for c in numc)
print("dev-vs-full feature table max abs difference on", len(common), "development rows:", mx)
assert len(common) == len(dev) and mx < 1e-9, "feature generation not prefix-stable"

# ---- fit (preprocessing refitted on the final training set)
Fall = Fall.sort_values(["match_date"], kind="mergesort")
tr = Fall
pp = Prep(FULL).fit(tr)
X = pp.transform(tr, True)
model = LogisticRegression(solver="lbfgs", max_iter=3000, random_state=SEED, **HP).fit(X, tr.y.astype(int).values)
assert model.n_iter_[0] < 3000, "did not converge"
P_in = model.predict_proba(X)

# ---- routine check: the same fit routine applied at the development cutoff reproduces the corrected development candidate
trd = Fall[Fall.match_date <= DEV_END]
ppd = Prep(FULL).fit(trd)
md = LogisticRegression(solver="lbfgs", max_iter=3000, random_state=SEED, **HP).fit(ppd.transform(trd, True), trd.y.astype(int).values)
va3 = dev[(dev.match_date >= "2023-07-01")]
old = pickle.load(open(os.path.join(ART, "candidate_v2_LR_full.pkl"), "rb"))
Pd = md.predict_proba(ppd.transform(add_derived(va3.assign()), True))
Po = old["model"].predict_proba(old["prep"].transform(add_derived(va3), True))
routine_gap = float(np.abs(Pd - Po).max())
print("dev-cutoff refit vs pre-fix development artifact: max abs probability gap", routine_gap)

# ---- training data eligibility report
elig = []
def add(k, v): elig.append(dict(item=k, value=v))
add("dataset_file", ds_path); add("dataset_sha256", sha(ds_path)); add("dataset_version", ",".join(ds.dataset_version.unique())); add("extraction_date", ",".join(ds.extraction_date.unique()))
add("freeze_timestamp", FREEZE_TS); add("training_cutoff_last_match_date", cutoff_date); add("first_match_date", str(ds.match_date.min()))
add("training_rows", len(tr)); add("confirmed_90min_labels", int((ds.label_90_status == "confirmed").sum()))
for k, v in ds.season_status.value_counts().items(): add(f"season_status={k}", int(v))
add("identity_review_flagged_rows", int(ds.identity_review_flag.sum())); add("calendar_year_league_rows", int(ds.calendar_type.str.startswith("calendar").sum()))
for k, v in ds.split.value_counts().items(): add(f"v1_split={k}", int(v))
add("competitions", int(ds.competition_id.nunique())); add("clubs", int(pd.concat([ds.home_entity_id, ds.away_entity_id]).nunique()))
for k, v in tr.y.map({0: "H", 1: "D", 2: "A"}).value_counts().items(): add(f"label_{k}", int(v))
add("results_universe_rows_used_for_state", len(V)); add("results_universe_competition_types", json.dumps(V.competition_type.value_counts().to_dict()))
add("rows_excluded_by_dataset_v1.1_eligibility", "see FootIQ_ML_Training_Preparation/03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv (not re-derived)")
pd.DataFrame(elig).to_csv(os.path.join(FD, "05_training_data_eligibility.csv"), index=False)
print(pd.DataFrame(elig).to_string())

# ---- save artifacts
feat_contract = dict(version="v2-r1", model="multinomial_logistic_regression", classes_order=CLASSES, feature_order=FULL, n_features=62, indicator_columns=pp.ind,
                     model_input_columns=FULL + [f"missing_indicator__{c}" for c in pp.ind], median_train={k: float(v) for k, v in pp.med.items()},
                     mean_train={k: float(v) for k, v in pp.mu.items()}, std_train={k: float(v) for k, v in pp.sd.items()},
                     derived_columns="v2_models.add_derived: log1p of home/away_n_prior, league_n_prior, home/away_comp_n_prior; home_info_gap = d - home_info_date",
                     feature_generator="_scripts/v2_features.py (V2State; Elo2 K=30 HA=50 regression=0; Elo1 K=20 HA=60)", elo2_params=P2,
                     unknown_history_policy="NaN -> training median + missing indicator (only for columns that had NaN in the training set)")
json.dump(feat_contract, open(os.path.join(AD, "feature_contract_v2_final.json"), "w"), indent=1)
json.dump(dict(classes_order=CLASSES, C=HP["C"], penalty="l2", solver="lbfgs", max_iter=3000, random_state=SEED, n_iter=int(model.n_iter_[0]), intercept=model.intercept_.tolist(), coef=model.coef_.tolist(),
               input_columns=feat_contract["model_input_columns"], calibration="none"), open(os.path.join(AD, "model_coefficients.json"), "w"), indent=1)
with open(os.path.join(AD, "club_v2_lr_final_candidate.pkl"), "wb") as fh:
    pickle.dump(dict(version="v2-r1", kind="lr", hyperparameters=HP, features=FULL, prep=pp, model=model, calibration=None, seed=SEED, training_cutoff=cutoff_date, freeze_timestamp=FREEZE_TS,
                     trained_rows=len(tr), status="frozen prospective candidate - not deployed"), fh)
tr[["competition_id", "season_corrected", "match_date", "y"] + FULL].to_pickle(os.path.join(FD, "training_feature_table_v2_r1.pkl"))
git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, cwd=P).stdout.strip()
code_files = {f: sha(os.path.join(OUT, "_scripts", f)) for f in sorted(os.listdir(os.path.join(OUT, "_scripts"))) if f.endswith(".py")}
frozen = dict(version="v2-r1", frozen_at=FREEZE_TS, training_cutoff_last_match_date=cutoff_date, training_rows=len(tr), seed=SEED, hyperparameters=HP, calibration="none",
              algorithm="multinomial LogisticRegression (sklearn lbfgs, L2)", features=62, feature_selection_source="development folds only (<= 2024-06-30); no newer-data selection",
              dependency_versions=dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__, platform=platform.platform()),
              git=dict(branch=git("rev-parse", "--abbrev-ref", "HEAD"), head=git("rev-parse", "HEAD"), working_tree_note="new work is untracked/uncommitted by design; code identified by the script hashes below"),
              code_sha256=code_files, input_sha256=dict(dataset_v1_1=sha(ds_path), universe_pkl=sha(os.path.join(PREP, "_build", "work", "V_universe.pkl")),
                                                         training_feature_table=sha(os.path.join(FD, "training_feature_table_v2_r1.pkl"))),
              artifact_sha256={f: sha(os.path.join(AD, f)) for f in sorted(os.listdir(AD))},
              checks=dict(dev_feature_table_prefix_max_abs_diff=mx, dev_cutoff_refit_vs_prefix_artifact_max_prob_gap=routine_gap, converged_iterations=int(model.n_iter_[0]),
                          in_sample_log_loss=metrics(tr.y.values.astype(int), P_in)["log_loss"], mean_pred=P_in.mean(0).tolist(), train_class_rates=np.bincount(tr.y.astype(int).values, minlength=3).tolist()))
json.dump(frozen, open(os.path.join(AD, "FROZEN.json"), "w"), indent=1)
for f in os.listdir(AD):                                   # immutable: read-only attribute
    os.chmod(os.path.join(AD, f), stat.S_IREAD)
os.chmod(os.path.join(FD, "training_feature_table_v2_r1.pkl"), stat.S_IREAD)
print(json.dumps({k: frozen[k] for k in ("frozen_at", "training_cutoff_last_match_date", "training_rows", "artifact_sha256", "checks")}, indent=1))
