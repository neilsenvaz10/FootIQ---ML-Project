"""Phases 1, 6, 7, 8: calibration (separate windows), draw analysis, group performance, cluster bootstrap, final-candidate artifacts. Development data only (<= 2024-06-30)."""
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_models import *  # noqa
from sklearn.metrics import roc_auc_score

sys.stdout.reconfigure(encoding="utf-8")
F = load_dev()
F = F[F.match_date <= DEV_END]
sel = json.load(open(os.path.join(WORK, "feature_selection.json")))
FULL, SEL = sel["full_v2_features"], sel["selected_features"]
best = json.load(open(os.path.join(WORK, "best_configs.json")))
oof = pd.read_pickle(os.path.join(WORK, "oof_predictions.pkl"))


def bhp(key):
    return json.loads(best[key]["hyperparameters"])


CANDS = {  # name -> (kind, hp, cols)
    "v2_LR_full": ("lr", bhp("lr|full_v2"), FULL),
    "v2_LR_selected": ("lr", bhp("lr|selected"), SEL),
    "v2_HGB_full": ("hgb", bhp("hgb|full_v2"), FULL),
    "v2_RF_full": ("rf", bhp("rf|full_v2"), FULL),
    "v1_LR_25": ("lr", dict(C=100.0), GROUPS["v1_all25"]),
}


# ---------------------------------------------------------------- calibration (vector scaling on log-probabilities)
def ece(P, y, k=10):
    """mean over classes of binned expected calibration error (one-vs-rest)"""
    out = []
    for c in range(3):
        p = P[:, c]; o = (y == c).astype(float)
        b = np.minimum((p * k).astype(int), k - 1)
        out.append(sum(abs(p[b == i].mean() - o[b == i].mean()) * (b == i).mean() for i in range(k) if (b == i).any()))
    return float(np.mean(out))


cal_rows, cal_oof = [], {}
for name, (kind, hp, cols) in CANDS.items():
    preds_u, preds_c = [], []
    for f in FOLDS:
        tr, va = fold_frames(F, f)
        cut = (pd.Timestamp(f["train_end"]) - pd.DateOffset(months=12)).strftime("%Y-%m-%d")
        core, calw = tr[tr.match_date <= cut], tr[tr.match_date > cut]
        calw = calw[calw.dev_primary]
        m, pp, Pc = fit_predict(kind, hp, cols, core, calw)
        cal = VecScale().fit(Pc, calw.y.astype(int).values)
        _, _, Pv = (None, None, m.predict_proba(pp.transform(va, kind == "lr")))
        msk = va.dev_primary.values
        yv = va.y.values[msk].astype(int)
        for lab, P in (("uncalibrated(core fit)", Pv[msk]), ("vector-scaled", cal.predict_proba(Pv[msk]))):
            r = metrics(yv, P); r.update(model=name, variant=lab, fold=f["fold"], ece=ece(P, yv), ece_draw=float(abs(P[:, 1].mean() - (yv == 1).mean())))
            cal_rows.append(r)
        pu = pd.DataFrame(Pv[msk], index=va.index[msk], columns=["pH", "pD", "pA"]); pu["fold"] = f["fold"]; preds_u.append(pu)
        pc = pd.DataFrame(cal.predict_proba(Pv[msk]), index=va.index[msk], columns=["pH", "pD", "pA"]); pc["fold"] = f["fold"]; preds_c.append(pc)
    cal_oof[(name, "core")] = pd.concat(preds_u); cal_oof[(name, "cal")] = pd.concat(preds_c)
C = pd.DataFrame(cal_rows)
Cs = C.groupby(["model", "variant"]).agg(mean_log_loss=("log_loss", "mean"), std_log_loss=("log_loss", "std"), mean_brier=("brier", "mean"), mean_ece=("ece", "mean"), mean_abs_draw_bias=("ece_draw", "mean"),
                                         mean_accuracy=("accuracy", "mean")).reset_index()
Cs.to_csv(os.path.join(WORK, "calibration_summary.csv"), index=False)
C.to_csv(os.path.join(WORK, "calibration_by_fold.csv"), index=False)
print(Cs.to_string())

# ---------------------------------------------------------------- stacked OOF tables (uncalibrated full-train models from d4 + v1 baselines)
def get(prefix_name, fset=None, hp=None):
    for k, v in oof.items():
        if k[0] == prefix_name and (fset is None or k[1] == fset) and (hp is None or json.loads(k[2]) == hp):
            return v
    raise KeyError(prefix_name)


P = {
    "v1_Elo_mapping": get("v1 Elo mapping"),
    "v1_LR_25": get("v1 Logistic Regression (25 features, C=100 as in v1)"),
    "v2_LR_full": get("Logistic Regression", "full_v2", bhp("lr|full_v2")),
    "v2_HGB_full": get("HistGradientBoosting", "full_v2", bhp("hgb|full_v2")),
    "v2_RF_full": get("Random Forest", "full_v2", bhp("rf|full_v2")),
}
idx = P["v2_LR_full"].index
meta = F.loc[idx, ["competition_id", "season_corrected", "tier", "y", "elo1_diff", "elo2_diff", "home_n_prior", "away_n_prior", "match_date"]].copy()
meta["y"] = meta.y.astype(int)
meta["fold"] = P["v2_LR_full"].fold.values
Y = meta.y.values


def ll(pr, y):
    return -np.log(np.clip(pr[np.arange(len(y)), y], 1e-12, 1))


LL = {k: ll(v.loc[idx, ["pH", "pD", "pA"]].values, Y) for k, v in P.items()}

# ---------------------------------------------------------------- league group / tier / cold-start performance
rows = []
tier = meta.tier.astype(str)
cold = (meta[["home_n_prior", "away_n_prior"]].min(axis=1) < 10)
groups = {"all": np.ones(len(meta), bool)}
for t in sorted(tier.unique()):
    groups[f"tier={t}"] = (tier == t).values
groups["cold-start (a side with <10 prior matches)"] = cold.values
groups["established (both >=10 prior matches)"] = ~cold.values
for fo in (1, 2, 3):
    groups[f"fold {fo}"] = (meta.fold == fo).values
for comp, g in meta.groupby("competition_id"):
    if len(g) >= 600:
        groups[f"competition={comp}"] = (meta.competition_id == comp).values
for gname, mk in groups.items():
    r = dict(group=gname, n=int(mk.sum()), draw_rate=float((Y[mk] == 1).mean()))
    for k in LL:
        r[f"logloss_{k}"] = float(LL[k][mk].mean())
    r["delta_v2LR_vs_v1Elo"] = r["logloss_v2_LR_full"] - r["logloss_v1_Elo_mapping"]
    r["delta_v2LR_vs_v1LR"] = r["logloss_v2_LR_full"] - r["logloss_v1_LR_25"]
    pm = P["v2_LR_full"].loc[idx, ["pH", "pD", "pA"]].values[mk]
    r["acc_v2LR"] = float((pm.argmax(1) == Y[mk]).mean()); r["mean_pD_v2LR"] = float(pm[:, 1].mean())
    rows.append(r)
pd.DataFrame(rows).to_csv(os.path.join(OUT, "08_LEAGUE_GROUP_PERFORMANCE.csv"), index=False)

# ---------------------------------------------------------------- paired cluster bootstrap (cluster = competition x season)
rng = np.random.default_rng(SEED)
cl = (meta.competition_id.astype(str) + "|" + meta.season_corrected.astype(str)).values
codes, uniq = pd.factorize(cl)
K = len(uniq)
cnt = np.bincount(codes, minlength=K).astype(float)


def boot(a, b, B=2000):
    da = np.bincount(codes, weights=LL[a] - LL[b], minlength=K)
    out = np.empty(B)
    for i in range(B):
        w = np.bincount(rng.integers(0, K, K), minlength=K)
        out[i] = (w * da).sum() / (w * cnt).sum()
    d = (LL[a] - LL[b]).mean()
    return dict(a=a, b=b, mean_diff_logloss=float(d), ci_low=float(np.percentile(out, 2.5)), ci_high=float(np.percentile(out, 97.5)), clusters=K, prob_a_better=float((out < 0).mean()))


BT = [boot("v2_LR_full", "v1_Elo_mapping"), boot("v2_LR_full", "v1_LR_25"), boot("v2_HGB_full", "v2_LR_full"), boot("v2_RF_full", "v2_LR_full"), boot("v1_LR_25", "v1_Elo_mapping")]
pd.DataFrame(BT).to_csv(os.path.join(WORK, "bootstrap_paired.csv"), index=False)
print(pd.DataFrame(BT).to_string())

# ---------------------------------------------------------------- draw analysis
dr = []
isd = (Y == 1)
for k, v in P.items():
    pm = v.loc[idx, ["pH", "pD", "pA"]].values
    dr.append(dict(model=k, mean_pD=float(pm[:, 1].mean()), actual_draw_rate=float(isd.mean()), pD_min=float(pm[:, 1].min()), pD_max=float(pm[:, 1].max()), pD_std=float(pm[:, 1].std()),
                   draw_auc=float(roc_auc_score(isd, pm[:, 1])), draw_logloss_binary=float(-(isd * np.log(np.clip(pm[:, 1], 1e-9, 1)) + (~isd) * np.log(np.clip(1 - pm[:, 1], 1e-9, 1))).mean()),
                   hard_draw_predictions=int((pm.argmax(1) == 1).sum())))
pd.DataFrame(dr).to_csv(os.path.join(WORK, "draw_probability_quality.csv"), index=False)
print(pd.DataFrame(dr).to_string())
# draw probability vs |Elo diff| bins
meta["abs_elo2"] = meta.elo2_diff.abs()
meta["bin"] = pd.cut(meta.abs_elo2, [-1, 25, 50, 100, 150, 200, 300, 2000])
pm = P["v2_LR_full"].loc[idx, "pD"].values; p1 = P["v1_Elo_mapping"].loc[idx, "pD"].values
meta["pD_v2LR"] = pm; meta["pD_v1Elo"] = p1; meta["isdraw"] = isd.astype(float)
bin_t = meta.groupby("bin", observed=True).agg(n=("y", "size"), actual_draw=("isdraw", "mean"), pD_v2LR=("pD_v2LR", "mean"), pD_v1Elo=("pD_v1Elo", "mean")).reset_index()
bin_t["bin"] = bin_t["bin"].astype(str)
bin_t.to_csv(os.path.join(WORK, "draw_vs_elo_diff.csv"), index=False)
print(bin_t.to_string())
# calibration curve of pD (deciles) for v2 LR and v1 Elo
cc = []
for k in ("v1_Elo_mapping", "v2_LR_full"):
    q = P[k].loc[idx, "pD"].values
    b = pd.qcut(q, 10, duplicates="drop")
    g = pd.DataFrame(dict(b=b, p=q, o=isd.astype(float))).groupby("b", observed=True).agg(n=("p", "size"), mean_pred=("p", "mean"), obs=("o", "mean")).reset_index()
    g["model"] = k; g["b"] = g.b.astype(str); cc.append(g)
pd.concat(cc).to_csv(os.path.join(WORK, "draw_calibration_deciles.csv"), index=False)
# draw rate by competition (top competitions)
dc = meta.groupby("competition_id").agg(n=("y", "size"), draw_rate=("isdraw", "mean"), mean_pD_v2LR=("pD_v2LR", "mean")).reset_index().query("n>=600").sort_values("draw_rate")
dc.to_csv(os.path.join(WORK, "draw_rate_by_competition.csv"), index=False)
# decision rules: scale draw probability by w, argmax; w tuned on folds 1-2 OOF, evaluated on fold 3 (and reported on all folds with fixed w)
from sklearn.metrics import f1_score


def decide(pm, w):
    q = pm.copy(); q[:, 1] *= w
    return q.argmax(1)


rules = []
for k in ("v1_Elo_mapping", "v2_LR_full", "v2_HGB_full"):
    pm = P[k].loc[idx, ["pH", "pD", "pA"]].values
    m12 = (meta.fold <= 2).values; m3 = (meta.fold == 3).values
    grid = np.arange(1.0, 2.61, 0.05)
    sc = [f1_score(Y[m12], decide(pm[m12], w), average="macro") for w in grid]
    wb = float(grid[int(np.argmax(sc))])
    for lab, w, mk in (("argmax (w=1)", 1.0, m3), (f"draw-weight w={wb:.2f} tuned on folds 1-2 (macro-F1)", wb, m3)):
        pr = decide(pm[mk], w)
        rules.append(dict(model=k, rule=lab, evaluated_on="fold 3 (2023-24)", n=int(mk.sum()), accuracy=float((pr == Y[mk]).mean()), macro_f1=float(f1_score(Y[mk], pr, average="macro")),
                          draw_predicted=int((pr == 1).sum()), draw_precision=float(((pr == 1) & (Y[mk] == 1)).sum() / max((pr == 1).sum(), 1)), draw_recall=float(((pr == 1) & (Y[mk] == 1)).sum() / (Y[mk] == 1).sum()),
                          f1_draw=float(f1_score(Y[mk] == 1, pr == 1))))
pd.DataFrame(rules).to_csv(os.path.join(WORK, "draw_decision_rules.csv"), index=False)
print(pd.DataFrame(rules).to_string())

# ---------------------------------------------------------------- feature diagnostics: correlation with Elo diff, v1 feature set redundancy
corr = F.loc[F.dev_primary, FULL].corrwith(F.loc[F.dev_primary, "elo2_diff"]).sort_values(key=abs, ascending=False)
corr.to_csv(os.path.join(WORK, "feature_corr_with_elo2_diff.csv"), header=["corr_with_elo2_diff"])
# learning curve (under-fit check): LR full_v2 trained on growing fractions of training window, fold 3
tr, va = fold_frames(F, FOLDS[2]); lc = []
for frac in (0.1, 0.25, 0.5, 0.75, 1.0):
    sub = tr.iloc[: int(len(tr) * frac)]
    _, _, Pv = fit_predict("lr", dict(C=0.01), FULL, sub, va)
    mk = va.dev_primary.values
    lc.append(dict(train_fraction=frac, train_rows=len(sub), val_log_loss=metrics(va.y.values[mk].astype(int), Pv[mk])["log_loss"]))
pd.DataFrame(lc).to_csv(os.path.join(WORK, "learning_curve_fold3.csv"), index=False)
print(pd.DataFrame(lc).to_string())

# ---------------------------------------------------------------- final development-fit candidates (all development rows <= 2024-06-30), saved as research artifacts only
os.makedirs(ART, exist_ok=True)
cut = (pd.Timestamp(DEV_END) - pd.DateOffset(months=12)).strftime("%Y-%m-%d")
dev = F[F.match_date <= DEV_END]
core, calw = dev[dev.match_date <= cut], dev[(dev.match_date > cut) & dev.dev_primary]
for name in ("v2_LR_full", "v2_LR_selected", "v2_HGB_full"):
    kind, hp, cols = CANDS[name]
    m, pp, Pc = fit_predict(kind, hp, cols, core, calw)
    cal = VecScale().fit(Pc, calw.y.astype(int).values)
    mf, ppf, _ = fit_predict(kind, hp, cols, dev, dev.iloc[:5])
    with open(os.path.join(ART, f"candidate_{name}.pkl"), "wb") as fh:
        pickle.dump(dict(kind=kind, hyperparameters=hp, features=cols, prep=ppf, model=mf, calibrator_core_model=m, calibrator_prep=pp, calibrator=cal, trained_on="matches dated <= 2024-06-30",
                         status="research candidate - not for deployment", seed=SEED), fh)
print("artifacts written")
