"""Phases 3, 7: algorithm comparison with chronological fold CV, calibration with a separate window. Uses only rows dated <= 2024-06-30."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_models import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
F = load_dev()
F = F[F.match_date <= DEV_END]
A = pd.read_csv(os.path.join(OUT, "04_FEATURE_ABLATION_RESULTS.csv"))
# ---- feature-set selection from the ablation (rule frozen in the protocol: gain >= 0.0010 and better in >= 2 of 3 folds, no harm in the other probe)
acc = []
for gname, label in (("elo_plus", "03 "), ("home_adv", "04 "), ("form", "05 "), ("goal", "06 "), ("league", "07 "), ("rest", "08 ")):
    sub = A[A.feature_set.str.startswith(label)]
    good = sub.decision.str.startswith("gain")
    harm = (sub.delta_vs_elo2_only > 0.001).any()
    if good.any() and not harm:
        acc.append(gname)
SEL = GROUPS["elo2"] + sum([GROUPS[g] for g in acc], [])
FULL = GROUPS["elo2"] + sum([GROUPS[g] for g in ("elo_plus", "home_adv", "form", "goal", "league", "rest")], [])
FSETS = {"selected": SEL, "full_v2": FULL}
print("accepted groups:", acc, "selected features:", len(SEL))
json.dump(dict(accepted_groups=acc, selected_features=SEL, full_v2_features=FULL), open(os.path.join(WORK, "feature_selection.json"), "w"), indent=1)

HGB = [dict(learning_rate=0.03, max_depth=3, max_iter=300, l2_regularization=1.0, min_samples_leaf=200), dict(learning_rate=0.05, max_depth=3, max_iter=200, l2_regularization=1.0, min_samples_leaf=200),
       dict(learning_rate=0.05, max_depth=4, max_iter=150, l2_regularization=1.0, min_samples_leaf=300), dict(learning_rate=0.03, max_depth=4, max_iter=300, l2_regularization=5.0, min_samples_leaf=300),
       dict(learning_rate=0.08, max_depth=3, max_iter=100, l2_regularization=1.0, min_samples_leaf=200), dict(learning_rate=0.05, max_depth=6, max_iter=100, l2_regularization=5.0, min_samples_leaf=400),
       dict(learning_rate=0.02, max_depth=3, max_iter=500, l2_regularization=1.0, min_samples_leaf=200), dict(learning_rate=0.03, max_depth=2, max_iter=400, l2_regularization=1.0, min_samples_leaf=100)]
RF = [dict(n_estimators=300, max_depth=6, min_samples_leaf=50, max_features="sqrt"), dict(n_estimators=300, max_depth=8, min_samples_leaf=100, max_features="sqrt"),
      dict(n_estimators=300, max_depth=12, min_samples_leaf=100, max_features="sqrt"), dict(n_estimators=300, max_depth=None, min_samples_leaf=200, max_features="sqrt"),
      dict(n_estimators=300, max_depth=8, min_samples_leaf=50, max_features=0.5), dict(n_estimators=300, max_depth=10, min_samples_leaf=200, max_features=0.5)]
LR = [dict(C=0.01), dict(C=0.1), dict(C=1.0)]
rows, oof = [], {}


def run(name, fam, kind, hp, cols, fset):
    t0 = time.time()
    res, preds = fold_eval(F, kind, hp, cols)
    rr = pd.DataFrame(res)
    rows.append(dict(model=name, family=fam, feature_set=fset, n_features=len(cols), hyperparameters=json.dumps(hp, default=str), fold1_ll=rr.log_loss[0], fold2_ll=rr.log_loss[1], fold3_ll=rr.log_loss[2],
                     mean_log_loss=rr.log_loss.mean(), std_log_loss=rr.log_loss.std(ddof=0), mean_brier=rr.brier.mean(), mean_accuracy=rr.accuracy.mean(), mean_macro_f1=rr.macro_f1.mean(),
                     mean_f1_draw=rr.f1_D.mean(), mean_draw_predicted=rr.draw_predicted.mean(), mean_draw_recall=rr.draw_recall.mean(), seconds=round(time.time() - t0, 1)))
    oof[(name, fset, json.dumps(hp, default=str))] = preds
    print(name, fset, hp, round(rows[-1]["mean_log_loss"], 5), rows[-1]["seconds"], flush=True)


# ---- baselines on the same folds
for f in FOLDS:
    pass
res_e, pr_e = [], []
for f in FOLDS:
    tr, va = fold_frames(F, f)
    m = OrdLogit().fit(tr.elo1_diff.values, tr.y.astype(int).values)
    P = m.predict_proba(va.elo1_diff.values)
    msk = va.dev_primary.values
    res_e.append(metrics(va.y.values[msk].astype(int), P[msk]))
    p = pd.DataFrame(P[msk], index=va.index[msk], columns=["pH", "pD", "pA"]); p["fold"] = f["fold"]; pr_e.append(p)
rr = pd.DataFrame(res_e)
rows.append(dict(model="v1 Elo ordered-logit mapping (elo1_diff)", family="baseline", feature_set="elo_v1", n_features=1, hyperparameters="{}", fold1_ll=rr.log_loss[0], fold2_ll=rr.log_loss[1], fold3_ll=rr.log_loss[2],
                 mean_log_loss=rr.log_loss.mean(), std_log_loss=rr.log_loss.std(ddof=0), mean_brier=rr.brier.mean(), mean_accuracy=rr.accuracy.mean(), mean_macro_f1=rr.macro_f1.mean(),
                 mean_f1_draw=rr.f1_D.mean(), mean_draw_predicted=rr.draw_predicted.mean(), mean_draw_recall=rr.draw_recall.mean(), seconds=0))
oof[("v1 Elo mapping", "elo_v1", "{}")] = pd.concat(pr_e)
run("v1 Logistic Regression (25 features, C=100 as in v1)", "baseline", "lr", dict(C=100.0), GROUPS["v1_all25"], "v1_all25")
run("Elo2 ordered-logit-equivalent LR (elo2_diff only, C=100)", "baseline", "lr", dict(C=100.0), GROUPS["elo2"], "elo2")
# ---- v2 candidates
for fset, cols in FSETS.items():
    for hp in LR:
        run("Logistic Regression", "lr", "lr", hp, cols, fset)
    for hp in RF:
        run("Random Forest", "rf", "rf", hp, cols, fset)
    for hp in HGB:
        run("HistGradientBoosting", "hgb", "hgb", hp, cols, fset)
T = pd.DataFrame(rows)
T.to_csv(os.path.join(OUT, "05_ALGORITHM_COMPARISON.csv"), index=False)
pd.to_pickle(oof, os.path.join(WORK, "oof_predictions.pkl"))
best = {}
for (fam, fset), g in T[T.family.isin(["lr", "rf", "hgb"])].groupby(["family", "feature_set"]):
    b = g.sort_values("mean_log_loss").iloc[0]
    best[f"{fam}|{fset}"] = dict(hyperparameters=b.hyperparameters, mean_log_loss=b.mean_log_loss, std=b.std_log_loss)
json.dump(best, open(os.path.join(WORK, "best_configs.json"), "w"), indent=1)
print(json.dumps(best, indent=1))
