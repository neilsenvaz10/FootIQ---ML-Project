"""Post-fix re-evaluation of the FROZEN development configuration (no tuning, no re-selection) and metric reconciliation."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_models import *  # noqa
sys.stdout.reconfigure(encoding="utf-8")
OUTD = os.path.join(OUT, "final_refit_v2_r1")
F = load_dev(); F = F[F.match_date <= DEV_END]
FULL = json.load(open(os.path.join(WORK, "feature_selection.json")))["full_v2_features"]
assert len(FULL) == 62
rows, preds = [], {}
def fold_rows(name, fn):
    res, pr = [], []
    for f in FOLDS:
        tr, va = fold_frames(F, f)
        P = fn(tr, va); msk = va.dev_primary.values
        y = va.y.values[msk].astype(int)
        res.append(dict(model=name, fold=f["fold"], **metrics(y, P[msk])))
        p = pd.DataFrame(P[msk], index=va.index[msk], columns=["pH", "pD", "pA"]); p["y"] = y; pr.append(p)
    rows.extend(res); preds[name] = pd.concat(pr)
def elo(tr, va):
    return OrdLogit().fit(tr.elo1_diff.values, tr.y.astype(int).values).predict_proba(va.elo1_diff.values)
fold_rows("v1 Elo mapping", elo)
fold_rows("v1 LR (25 features, C=100)", lambda tr, va: fit_predict("lr", dict(C=100.0), GROUPS["v1_all25"], tr, va)[2])
fold_rows("v2 LR (62 features, C=0.01)", lambda tr, va: fit_predict("lr", dict(C=0.01), FULL, tr, va)[2])
R = pd.DataFrame(rows); R.to_csv(os.path.join(OUTD, "02_postfix_fold_metrics.csv"), index=False)
piv = R.pivot(index="model", columns="fold", values="log_loss"); piv["fold_mean"] = piv.mean(axis=1)
n = R[R.model == "v2 LR (62 features, C=0.01)"].set_index("fold").n
piv["row_weighted_pooled"] = [float(sum(R[(R.model == m) & (R.fold == k)].log_loss.iloc[0] * n[k] for k in (1, 2, 3)) / n.sum()) for m in piv.index]
piv.to_csv(os.path.join(OUTD, "03_postfix_logloss_reconciliation.csv")); print(piv.round(5).to_string())
b = "v1 LR (25 features, C=100)"; c = "v2 LR (62 features, C=0.01)"
print("fold-mean diff v2-v1LR", piv.loc[c, "fold_mean"] - piv.loc[b, "fold_mean"], " pooled diff", piv.loc[c, "row_weighted_pooled"] - piv.loc[b, "row_weighted_pooled"])
# paired cluster bootstrap on the pooled sample
meta = F.loc[preds[c].index, ["competition_id", "season_corrected"]]
cl = (meta.competition_id.astype(str) + "|" + meta.season_corrected.astype(str)).values
codes, u = pd.factorize(cl); K = len(u); cnt = np.bincount(codes, minlength=K).astype(float)
def ll(p): return -np.log(np.clip(p[["pH", "pD", "pA"]].values[np.arange(len(p)), p.y.values], 1e-12, 1))
rng = np.random.default_rng(SEED); out = []
for a, bb in ((c, "v1 Elo mapping"), (c, b)):
    d = ll(preds[a]) - ll(preds[bb]); da = np.bincount(codes, weights=d, minlength=K); bs = []
    for _ in range(2000):
        w = np.bincount(rng.integers(0, K, K), minlength=K); bs.append((w * da).sum() / (w * cnt).sum())
    out.append(dict(a=a, b=bb, pooled_diff=float(d.mean()), ci_low=float(np.percentile(bs, 2.5)), ci_high=float(np.percentile(bs, 97.5)), clusters=K))
pd.DataFrame(out).to_csv(os.path.join(OUTD, "03b_postfix_bootstrap.csv"), index=False); print(pd.DataFrame(out).to_string())
pre = pd.read_csv(os.path.join(WORK, "pre_fix", "05_ALGORITHM_COMPARISON.csv"))
print(pre[(pre.family == "lr") & (pre.feature_set == "full_v2") & pre.hyperparameters.str.contains("0.01")][["fold1_ll", "fold2_ll", "fold3_ll", "mean_log_loss"]])
