"""Matched v1 refit: original v1 LR recipe (25 v1 contract features, C=100, v1 preprocessing rule) on exactly the frozen v2-r1 training rows. No tuning. Refuses to run twice."""
import json, os, pickle, stat, sys, platform, subprocess, hashlib
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa
sys.path.insert(0, os.path.join(PREP, "_build"))
import feature_contract as fc  # noqa
import sklearn, scipy  # noqa
from sklearn.linear_model import LogisticRegression
sys.stdout.reconfigure(encoding="utf-8")
NEW = os.path.join(OUT, "matched_v1_prospective_r1"); AD = os.path.join(NEW, "artifacts"); os.makedirs(AD, exist_ok=True)
if os.path.exists(os.path.join(AD, "MATCHED_V1_FROZEN.json")):
    sys.exit("matched v1 refit already frozen")
V1SEED = 20261020                                                    # the seed used by original v1
contract = json.load(open(os.path.join(PREP, "feature_contract_v1.1.json"))); FEAT = contract["feature_order"]; assert len(FEAT) == 25
v1_params = json.load(open(os.path.join(V1, "artifacts", "multinomial_logreg_coefficients.json")))
assert v1_params["C"] == 100.0 and v1_params["penalty"] == "l2" and v1_params["solver"] == "lbfgs" and v1_params["max_iter"] == 3000
ds = pd.read_csv(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
fe = pd.read_csv(os.path.join(PREP, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
# ---- leak-safe recomputation of the v1 features from the results universe (contract code, unchanged) and comparison with the stored feature file
fr = V.rename(columns={"home_entity_id": "home", "away_entity_id": "away"})[["record_id", "dt", "home", "away", "tier", "rated", "gh", "ga", "in_scope"]].copy()
fr["completed"] = True; fr["want_features"] = fr.record_id.isin(set(ds.record_id))
rec = fc.build_features(fr).set_index("record_id")
fe = fe.set_index("record_id"); ds = ds.set_index("record_id")
assert set(rec.index) == set(ds.index) == set(fe.index)
rec = rec.loc[ds.index]; fe = fe.loc[ds.index]
mx = float(np.nanmax(np.abs(rec[FEAT].values.astype(float) - fe[FEAT].values.astype(float))))
nan_equal = bool((np.isnan(rec[FEAT].values.astype(float)) == np.isnan(fe[FEAT].values.astype(float))).all())
print("recomputed v1 features vs stored file: max abs diff", mx, "NaN pattern equal", nan_equal)
assert mx < 1e-9 and nan_equal
X = rec[FEAT].copy()
y = ds.y_90min_1x2.map({"H": 0, "D": 1, "A": 2}).values.astype(int)
# ---- v1 preprocessing rule (b2_fit_select_freeze.py), fitted on the full matched training set
nan_cols = [c for c in FEAT if X[c].isna().any()]
ind_cols = sorted(set(nan_cols) | {"home_venue_ppg5", "away_venue_ppg5"})
med = {c: float(X[c].median()) for c in FEAT}
imp = X.fillna(pd.Series(med)); mu = imp.mean(); sd = imp.std(ddof=0).replace(0, 1.0)
prep = dict(feature_order=FEAT, median_train=med, indicator_columns=ind_cols, mean_train=mu.to_dict(), std_train=sd.to_dict(), fitted_on="all 116,854 matched training rows (matches <= 2026-09-20)", n_fit_rows=len(X))
def transform(frame):
    x = frame[FEAT]
    ind = np.column_stack([x[c].isna().astype(float).values for c in ind_cols])
    return np.hstack([((x.fillna(pd.Series(med)) - mu) / sd).values, ind])
Z = transform(X)
mlr = LogisticRegression(C=100.0, penalty="l2", solver="lbfgs", max_iter=3000, random_state=V1SEED).fit(Z, y)
assert mlr.n_iter_[0] < 3000
P_in = mlr.predict_proba(Z)
# ---- artifacts
json.dump(prep, open(os.path.join(AD, "matched_v1_preprocessing.json"), "w"), indent=1)
json.dump(dict(classes_order=CLASSES, C=100.0, penalty="l2", solver="lbfgs", max_iter=3000, random_state=V1SEED, n_iter=int(mlr.n_iter_[0]), coef=mlr.coef_.tolist(), intercept=mlr.intercept_.tolist(),
               input_columns=FEAT + [f"missing_indicator__{c}" for c in ind_cols]), open(os.path.join(AD, "matched_v1_coefficients.json"), "w"), indent=1)
with open(os.path.join(AD, "matched_v1_lr_refit.pkl"), "wb") as fh:
    pickle.dump(mlr, fh)
# ---- equivalence with the frozen v2-r1 training data
v2t = pd.read_pickle(os.path.join(OUT, "final_refit_v2_r1", "training_feature_table_v2_r1.pkl"))
v2c = json.load(open(os.path.join(OUT, "final_refit_v2_r1", "artifacts", "feature_contract_v2_final.json")))
ids_v1 = sorted(ds.index); ids_v2 = sorted(v2t.index)
h = lambda l: hashlib.sha256("\n".join(map(str, l)).encode()).hexdigest()
y_v2 = v2t.loc[ds.index, "y"].values.astype(int)
eq = dict(identical_training_record_ids=ids_v1 == ids_v2, record_id_hash=h(ids_v1), n_rows_matched_v1=len(ids_v1), n_rows_v2=len(ids_v2),
          identical_targets_row_by_row=bool((y == y_v2).all()), target_hash=h([f"{i}:{t}" for i, t in zip(ds.index, y)]),
          class_definition="0=H,1=D,2=A = confirmed 90-minute 1X2 (dataset v1.1 y_90min_1x2) for both models",
          label_status_all_confirmed=bool((ds.label_90_status == "confirmed").all()),
          source_cutoff_matched_v1=str(ds.match_date.max()), source_cutoff_v2=json.load(open(os.path.join(OUT, "final_refit_v2_r1", "artifacts", "FROZEN.json")))["training_cutoff_last_match_date"],
          eligibility="both: every row of dataset v1.1 (confirmed 90-minute labels, regular-round domestic league, no further filtering)",
          matched_v1_inputs_subset_of_v1_contract=set(FEAT) <= set(contract["feature_order"]) and len(FEAT) == 25,
          v1_contract_features=FEAT, v2_features=v2c["feature_order"],
          v2_only_features_used_by_matched_v1=sorted(set(FEAT) - set(contract["feature_order"])),
          names_shared_between_contracts=sorted(set(FEAT) & set(v2c["feature_order"])),
          v1_features_not_in_v2_set=sorted(set(FEAT) - set(v2c["feature_order"])),
          v1_hyperparameters_equal_original=bool(v1_params["C"] == 100.0), preprocessing="v1 rule (median, mean/sd, missing indicators for NaN columns + both venue_ppg5), refit on the matched set",
          feature_recompute_max_abs_diff_vs_stored_v1_file=mx)
# independent contract verification: the original v1 artifact's input columns equal the contract
eq["original_v1_input_columns_match_contract"] = v1_params["input_columns"][:25] == FEAT
orig = pickle.load(open(os.path.join(V1, "artifacts", "multinomial_logreg.pkl"), "rb"))
oprep = json.load(open(os.path.join(V1, "artifacts", "preprocessing_train_fitted.json")))
eq["original_v1_indicator_columns"] = oprep["indicator_columns"]; eq["matched_v1_indicator_columns"] = ind_cols
cor = float(np.corrcoef(np.array(v1_params["coef"]).ravel(), mlr.coef_.ravel())[0, 1])
eq["coefficient_correlation_original_v1_vs_matched"] = cor
json.dump(eq, open(os.path.join(NEW, "05_training_data_equivalence.json"), "w"), indent=1, default=str)
print(json.dumps({k: eq[k] for k in eq if k not in ("v1_contract_features", "v2_features")}, indent=1, default=str))
git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, cwd=P).stdout.strip()
fz = dict(version="matched-v1-r1", description="original v1 multinomial LR recipe refit on the frozen v2-r1 training rows; not tuned; comparator, not a replacement of v1", seed=V1SEED, C=100.0,
          training_cutoff_last_match_date=str(ds.match_date.max()), training_rows=len(X), record_id_hash=eq["record_id_hash"], target_hash=eq["target_hash"],
          dependency_versions=dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__, platform=platform.platform()),
          git_head=git("rev-parse", "HEAD"), script_sha256=sha(os.path.abspath(__file__)), artifact_sha256={f: sha(os.path.join(AD, f)) for f in sorted(os.listdir(AD))},
          in_sample_log_loss=float(-np.log(np.clip(P_in[np.arange(len(y)), y], 1e-12, 1)).mean()), n_iter=int(mlr.n_iter_[0]), mean_pred=P_in.mean(0).tolist())
json.dump(fz, open(os.path.join(AD, "MATCHED_V1_FROZEN.json"), "w"), indent=1)
for f in os.listdir(AD):
    os.chmod(os.path.join(AD, f), stat.S_IREAD)
print(json.dumps(fz, indent=1))
