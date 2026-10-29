"""B2: fit on TRAIN, select on VALIDATION, freeze. Test and forward-holdout labels are masked here and never used."""
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
np.random.seed(SEED)
if os.path.exists(os.path.join(ART, "FROZEN.json")):
    sys.exit("already frozen - refusing to refit (one controlled experiment)")
contract = json.load(open(os.path.join(PREP, "feature_contract_v1.1.json")))
FEAT = contract["feature_order"]
ds = pd.read_csv(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
fe = pd.read_csv(os.path.join(PREP, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
df = ds[["record_id", "competition_id", "season_corrected", "split", "eval_primary", "eval_secondary_calendar_year", "tier"]].merge(
    fe[["record_id"] + FEAT + ["y_90min_1x2"]], on="record_id")
df["y"] = df.y_90min_1x2.map({"H": 0, "D": 1, "A": 2})
df.loc[df.split.isin(["test", "forward_holdout"]), ["y", "y_90min_1x2"]] = np.nan      # MASK: never used before the locked evaluation
tr, va = df[df.split == "train"].copy(), df[df.split == "validation"].copy()
print("train rows", len(tr), "validation rows", len(va), "validation primary rows", int(va.eval_primary.sum()))

# ---------------- preprocessing fitted on TRAIN only (preprocessing_spec_v1.1.json)
nan_cols = [c for c in FEAT if tr[c].isna().any()]
ind_cols = sorted(set(nan_cols) | {"home_venue_ppg5", "away_venue_ppg5"})
med = {c: float(tr[c].median()) for c in FEAT}
imp_tr = tr[FEAT].fillna(pd.Series(med))
mu = imp_tr.mean()
sd = imp_tr.std(ddof=0).replace(0, 1.0)
prep = dict(feature_order=FEAT, median_train=med, indicator_columns=ind_cols, mean_train=mu.to_dict(), std_train=sd.to_dict(), fitted_on="split == train", n_fit_rows=len(tr))


def transform(frame):
    x = frame[FEAT].copy()
    ind = np.column_stack([x[c].isna().astype(float).values for c in ind_cols])
    x = x.fillna(pd.Series(med))
    z = ((x - mu) / sd).values
    return np.hstack([z, ind])


Xtr, Xva = transform(tr), transform(va)
ytr, yva = tr.y.astype(int).values, va.y.astype(int).values
mask_p = va.eval_primary.values

# ---------------- model 1: always-home (training class frequencies provide the probabilities)
prior = np.bincount(ytr, minlength=3) / len(ytr)


def always_home(n):
    return np.tile(prior, (n, 1))


# ---------------- model 2: Elo ordered-logit mapping fitted on TRAIN
def nll(theta, d, y):
    b, c1, ld = theta
    c2 = c1 + np.exp(ld)
    z = b * d / 100.0
    pA = expit(c1 - z)
    pAD = expit(c2 - z)
    P = np.column_stack([1 - pAD, pAD - pA, pA])
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1)).mean()


r = minimize(nll, x0=[1.0, -0.5, 0.0], args=(tr.elo_diff.values, ytr), method="L-BFGS-B")
b_, c1_, ld_ = r.x
elo_params = dict(scale_per_100_elo=float(b_), threshold_away_draw=float(c1_), threshold_draw_home=float(c1_ + np.exp(ld_)), fitted_on="train",
                  train_nll=float(r.fun), converged=bool(r.success))


def elo_proba(d):
    z = b_ * np.asarray(d) / 100.0
    pA = expit(c1_ - z)
    pAD = expit(c1_ + np.exp(ld_) - z)
    return np.column_stack([1 - pAD, pAD - pA, pA])


# ---------------- model 3: multinomial logistic regression; C chosen on VALIDATION (primary rows) log loss
grid = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0]
rows, models = [], {}
for C in grid:
    m = LogisticRegression(C=C, solver="lbfgs", max_iter=3000, random_state=SEED)
    m.fit(Xtr, ytr)
    pv_ = m.predict_proba(Xva)
    mm = metrics(yva[mask_p], pv_[mask_p])
    rows.append(dict(C=C, accuracy=mm["accuracy"], macro_f1=mm["macro_f1"], log_loss=mm["log_loss"], brier=mm["brier"], n_validation_primary=mm["n"], iterations=int(m.n_iter_[0])))
    models[C] = m
gridtab = pd.DataFrame(rows)
bestC = float(gridtab.sort_values(["log_loss", "C"]).iloc[0].C)
mlr = models[bestC]
print(gridtab.to_string())
print("selected C =", bestC)

P_va = {"always_home": always_home(len(va)), "elo_ordered_logit": elo_proba(va.elo_diff.values), "multinomial_logreg": mlr.predict_proba(Xva)}
val_rows = []
for nm, P in P_va.items():
    for name, msk in (("validation_primary", mask_p), ("validation_secondary_calendar_year", va.eval_secondary_calendar_year.values), ("validation_all_rows", np.ones(len(va), bool))):
        if msk.sum():
            val_rows.append(dict(model=nm, evaluation_set=name, **metrics(yva[msk], P[msk])))
valtab = pd.DataFrame(val_rows)
sel = valtab[valtab.evaluation_set == "validation_primary"].sort_values("log_loss")
best_model = sel.iloc[0].model
print(valtab.to_string())
print("best by validation primary log loss:", best_model)

# ---------------- coverage-quality categories from TRAINING-period evidence only (defined before any test / holdout evaluation)
ss = pd.read_csv(os.path.join(PREP, "season_completeness_by_league_season.csv"), encoding=ENC)
trs = tr.groupby(["competition_id", "season_corrected"]).size().reset_index(name="n").merge(ss[["competition_id", "season_corrected", "season_status"]], on=["competition_id", "season_corrected"], how="left")
lg = trs.groupby("competition_id").agg(train_league_seasons=("season_corrected", "nunique"), complete_share=("season_status", lambda s: float(s.eq("complete").mean()))).reset_index()
tr["min_prior"] = np.minimum(tr.home_n_prior, tr.away_n_prior)
q33, q67 = [float(x) for x in tr.min_prior.quantile([1 / 3, 2 / 3])]
lg["coverage_group"] = np.where((lg.train_league_seasons >= 3) & (lg.complete_share >= 0.80), "well_covered", "incomplete_history")
cov = dict(rule="a league is well_covered when it has >=3 league-seasons in the TRAIN period and >=80% of them are verified complete (season_completeness_by_league_season.csv); other leagues with train evidence are incomplete_history; leagues absent from train are no_training_history. Match-level history depth = min(home_n_prior, away_n_prior), shallow < q33, deep >= q67 of the train distribution",
           history_depth_cut_points=dict(q33=q33, q67=q67), league_table=lg.to_dict("records"))
json.dump(cov, open(os.path.join(ART, "coverage_categories.json"), "w"), indent=1)
print("coverage groups (train evidence):", lg.coverage_group.value_counts().to_dict(), "cut points", q33, q67)

# ---------------- save artifacts + freeze record
json.dump(prep, open(os.path.join(ART, "preprocessing_train_fitted.json"), "w"), indent=1)
json.dump(dict(always_home_class_priors=dict(zip(CLASSES, prior.tolist())), elo_ordered_logit=elo_params), open(os.path.join(ART, "baseline_parameters.json"), "w"), indent=1)
with open(os.path.join(ART, "multinomial_logreg.pkl"), "wb") as f:
    pickle.dump(mlr, f)
json.dump(dict(classes_order=CLASSES, C=bestC, penalty="l2", solver="lbfgs", max_iter=3000, random_state=SEED, coef=mlr.coef_.tolist(), intercept=mlr.intercept_.tolist(),
               input_columns=FEAT + [f"missing_indicator__{c}" for c in ind_cols]), open(os.path.join(ART, "multinomial_logreg_coefficients.json"), "w"), indent=1)
gridtab.to_csv(os.path.join(OUT, "03b_VALIDATION_C_GRID.csv"), index=False)
valtab.to_csv(os.path.join(OUT, "03_VALIDATION_METRICS.csv"), index=False)
pv = va[["record_id", "competition_id", "split", "eval_primary", "eval_secondary_calendar_year"]].copy()
pv["y_true"] = va.y_90min_1x2.values
for nm, P in P_va.items():
    for k, c in enumerate(CLASSES):
        pv[f"{nm}__p_{c}"] = P[:, k]
pv.to_csv(os.path.join(OUT, "predictions_validation.csv"), index=False)
import importlib.metadata as md
freeze = dict(frozen_at=time.strftime("%Y-%m-%d %H:%M:%S"), selected_model_by_validation_primary_log_loss=best_model, selected_C=bestC,
              selection_criterion="multiclass log loss on validation primary rows", random_seed=SEED, train_rows=len(tr), validation_rows=len(va),
              validation_primary_rows=int(mask_p.sum()), dependency_versions={p: md.version(p) for p in ["numpy", "pandas", "scikit-learn", "scipy"]},
              artifact_sha256={f: sha(os.path.join(ART, f)) for f in sorted(os.listdir(ART)) if f != "FROZEN.json"})
json.dump(freeze, open(os.path.join(ART, "FROZEN.json"), "w"), indent=1)
chk = tr[FEAT].median()
assert all(abs(chk[c] - med[c]) < 1e-12 for c in FEAT)
print("FROZEN; preprocessing statistics equal train-only recomputation")
