"""B3: locked evaluation. Runs ONCE (a lock file is created first). Models and preprocessing are loaded from the frozen artifacts and not modified."""
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
LOCK = os.path.join(OUT, "EVALUATION_LOCK.json")
if os.path.exists(LOCK):
    sys.exit("test / forward-holdout evaluation already executed once - refusing to run again")
frozen = json.load(open(os.path.join(ART, "FROZEN.json")))
for f, h in frozen["artifact_sha256"].items():
    assert sha(os.path.join(ART, f)) == h, f"artifact changed after freezing: {f}"
json.dump(dict(started=time.strftime("%Y-%m-%d %H:%M:%S"), frozen_at=frozen["frozen_at"], note="evaluation of test and forward holdout executed once from frozen artifacts"), open(LOCK, "w"))

FEAT = json.load(open(os.path.join(PREP, "feature_contract_v1.1.json")))["feature_order"]
prep = json.load(open(os.path.join(ART, "preprocessing_train_fitted.json")))
base = json.load(open(os.path.join(ART, "baseline_parameters.json")))
cov = json.load(open(os.path.join(ART, "coverage_categories.json")))
mlr = pickle.load(open(os.path.join(ART, "multinomial_logreg.pkl"), "rb"))
prior = np.array([base["always_home_class_priors"][c] for c in CLASSES])
ep = base["elo_ordered_logit"]
med, ind_cols = prep["median_train"], prep["indicator_columns"]
mu, sd = pd.Series(prep["mean_train"]), pd.Series(prep["std_train"])


def transform(frame):
    x = frame[FEAT].copy()
    ind = np.column_stack([x[c].isna().astype(float).values for c in ind_cols])
    x = x.fillna(pd.Series(med))
    return np.hstack([((x - mu) / sd).values, ind])


def elo_proba(d):
    z = ep["scale_per_100_elo"] * np.asarray(d) / 100.0
    pA = expit(ep["threshold_away_draw"] - z)
    pAD = expit(ep["threshold_draw_home"] - z)
    return np.column_stack([1 - pAD, pAD - pA, pA])


ds = pd.read_csv(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
fe = pd.read_csv(os.path.join(PREP, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
df = ds[["record_id", "competition_id", "competition_country", "season_corrected", "calendar_type", "split", "eval_primary", "eval_secondary_calendar_year", "tier", "match_date"]].merge(
    fe[["record_id"] + FEAT + ["y_90min_1x2"]], on="record_id")
df["y"] = df.y_90min_1x2.map({"H": 0, "D": 1, "A": 2}).astype(int)
ev = df[df.split.isin(["validation", "test", "forward_holdout"]) & (df.eval_primary | df.eval_secondary_calendar_year)].copy()
X = transform(ev)
P = {"always_home": np.tile(prior, (len(ev), 1)), "elo_ordered_logit": elo_proba(ev.elo_diff.values), "multinomial_logreg": mlr.predict_proba(X)}
MODELS = list(P)
ev["set"] = np.where(ev.eval_primary, ev.split + "_primary", ev.split + "_secondary_calendar_year")
SETS = ["validation_primary", "test_primary", "forward_holdout_primary", "test_secondary_calendar_year", "forward_holdout_secondary_calendar_year", "validation_secondary_calendar_year"]

# ---------------- groups defined a priori
def group_of(cid, tier):
    top5 = {"england:1-premierleague", "espana:1-liga", "deutschland:1-bundesliga", "italy:1-seriea", "europe/france:fr1"}
    europe = cid.startswith(("england:", "espana:", "deutschland:", "italy:", "austria:", "belgium:", "europe/"))
    if cid in top5:
        return "G1 top-5 European leagues"
    if not europe:
        return "G5 non-European leagues"
    t = 99 if pd.isna(tier) else int(tier)
    return "G2 other European tier-1" if t == 1 else ("G3 European tier-2" if t == 2 else "G4 European tier-3+")


ev["league_group"] = [group_of(c, t) for c, t in zip(ev.competition_id, ev.tier)]
cg = {r["competition_id"]: r["coverage_group"] for r in cov["league_table"]}
ev["coverage_group"] = ev.competition_id.map(cg).fillna("no_training_history")
q33, q67 = cov["history_depth_cut_points"]["q33"], cov["history_depth_cut_points"]["q67"]
mp = np.minimum(ev.home_n_prior, ev.away_n_prior)
ev["history_depth"] = np.where(mp < q33, "shallow (<%d)" % q33, np.where(mp >= q67, "deep (>=%d)" % q67, "medium"))
y_all = ev.y.values

# ---------------- predictions file
pred = ev[["record_id", "competition_id", "match_date", "split", "set", "league_group", "coverage_group", "history_depth"]].copy()
pred["y_true"] = ev.y_90min_1x2.values
for nm in MODELS:
    for k, c in enumerate(CLASSES):
        pred[f"{nm}__p_{c}"] = P[nm][:, k]
pred.to_csv(os.path.join(OUT, "predictions_validation_test_holdout.csv"), index=False)

# ---------------- metrics per set
rows = []
for s in SETS:
    m = (ev.set == s).values
    if not m.any():
        continue
    for nm in MODELS:
        rows.append(dict(set=s, model=nm, **metrics(y_all[m], P[nm][m])))
M = pd.DataFrame(rows)
M[M.set.str.startswith("validation")].to_csv(os.path.join(OUT, "03_VALIDATION_METRICS_RECOMPUTED.csv"), index=False)
M[M.set.str.startswith("test")].to_csv(os.path.join(OUT, "04_TEST_METRICS.csv"), index=False)
M[M.set.str.startswith("forward_holdout")].to_csv(os.path.join(OUT, "05_FORWARD_HOLDOUT_METRICS.csv"), index=False)
print(M.to_string())

# ---------------- per-class, confusion, calibration
pc, conf, cal, ece_rows = [], [], [], []
for s in ["validation_primary", "test_primary", "forward_holdout_primary", "test_secondary_calendar_year", "forward_holdout_secondary_calendar_year"]:
    m = (ev.set == s).values
    if not m.any():
        continue
    y = y_all[m]
    for nm in MODELS:
        p = P[nm][m]
        pred_k = p.argmax(1)
        cm = np.zeros((3, 3), int)
        for a, b in zip(y, pred_k):
            cm[a, b] += 1
        for i, ci in enumerate(CLASSES):
            for j, cj in enumerate(CLASSES):
                conf.append(dict(set=s, model=nm, true=ci, predicted=cj, count=int(cm[i, j])))
            tp, fp, fn = cm[i, i], cm[:, i].sum() - cm[i, i], cm[i, :].sum() - cm[i, i]
            pc.append(dict(set=s, model=nm, cls=ci, support=int(cm[i, :].sum()), predicted_count=int(cm[:, i].sum()), precision=tp / (tp + fp) if tp + fp else np.nan,
                           recall=tp / (tp + fn) if tp + fn else np.nan, f1=2 * tp / (2 * tp + fp + fn) if tp else 0.0, mean_predicted_prob=float(p[:, i].mean()), observed_rate=float((y == i).mean())))
            bins = np.linspace(0, 1, 11)
            idx = np.clip(np.digitize(p[:, i], bins) - 1, 0, 9)
            tot = 0.0
            for b in range(10):
                mb = idx == b
                if mb.sum():
                    gap = abs(p[mb, i].mean() - (y[mb] == i).mean())
                    tot += mb.sum() * gap
                    cal.append(dict(set=s, model=nm, cls=ci, bin=f"{bins[b]:.1f}-{bins[b + 1]:.1f}", n=int(mb.sum()), mean_predicted=float(p[mb, i].mean()), observed_frequency=float((y[mb] == i).mean())))
            ece_rows.append(dict(set=s, model=nm, cls=ci, ece=tot / len(y)))
        conf_top = p.max(1)
        idx = np.clip(np.digitize(conf_top, np.linspace(0, 1, 11)) - 1, 0, 9)
        tot = 0.0
        for b in range(10):
            mb = idx == b
            if mb.sum():
                tot += mb.sum() * abs(conf_top[mb].mean() - (pred_k[mb] == y[mb]).mean())
        ece_rows.append(dict(set=s, model=nm, cls="top-label", ece=tot / len(y)))
PC, CF, CAL, ECE = pd.DataFrame(pc), pd.DataFrame(conf), pd.DataFrame(cal), pd.DataFrame(ece_rows)
PC.to_csv(os.path.join(OUT, "07a_PER_CLASS_PERFORMANCE.csv"), index=False)
CF.to_csv(os.path.join(OUT, "07b_CONFUSION_MATRICES.csv"), index=False)
CAL.to_csv(os.path.join(OUT, "07c_CALIBRATION_BINS.csv"), index=False)
ECE.to_csv(os.path.join(OUT, "07d_CALIBRATION_ECE.csv"), index=False)

# ---------------- league-wise / group / coverage tables
def grouped(col, sets, min_n=1):
    out = []
    for s in sets:
        for g, sub in ev[ev.set == s].groupby(col):
            if len(sub) < min_n:
                continue
            ii = sub.index.map(lambda i: ev.index.get_loc(i))
            for nm in MODELS:
                out.append(dict(set=s, **{col: g}, model=nm, **metrics(y_all[ii], P[nm][ii])))
    return pd.DataFrame(out)


PRIM = ["test_primary", "forward_holdout_primary"]
SEC = ["test_secondary_calendar_year", "forward_holdout_secondary_calendar_year"]
LG = grouped("competition_id", PRIM + SEC, min_n=100)
LGR = grouped("league_group", PRIM + SEC)
CV = grouped("coverage_group", PRIM + SEC)
HD = grouped("history_depth", PRIM + SEC)
LG.to_csv(os.path.join(OUT, "06a_LEAGUE_WISE_METRICS.csv"), index=False)
LGR.to_csv(os.path.join(OUT, "06b_LEAGUE_GROUP_METRICS.csv"), index=False)
CV.to_csv(os.path.join(OUT, "08a_COVERAGE_GROUP_METRICS.csv"), index=False)
HD.to_csv(os.path.join(OUT, "08b_HISTORY_DEPTH_METRICS.csv"), index=False)

# ---------------- paired bootstrap of the log-loss difference
rng = np.random.default_rng(SEED)
boot = []
for s in PRIM + SEC:
    m = (ev.set == s).values
    if m.sum() < 50:
        continue
    y = y_all[m]
    L = {nm: -np.log(np.clip(P[nm][m][np.arange(m.sum()), y], 1e-15, 1)) for nm in MODELS}
    for a, b in (("multinomial_logreg", "elo_ordered_logit"), ("multinomial_logreg", "always_home"), ("elo_ordered_logit", "always_home")):
        d = L[a] - L[b]
        idx = rng.integers(0, len(d), size=(2000, len(d)))
        bm = d[idx].mean(1)
        boot.append(dict(set=s, comparison=f"{a} - {b} (log loss, negative = first is better)", mean_difference=float(d.mean()), ci95_low=float(np.percentile(bm, 2.5)), ci95_high=float(np.percentile(bm, 97.5)), n=int(m.sum())))
BOOT = pd.DataFrame(boot)
BOOT.to_csv(os.path.join(OUT, "02b_PAIRED_BOOTSTRAP_LOGLOSS_DIFFERENCES.csv"), index=False)

# ---------------- evaluation hashes
eh = {s: sha_list(ev[ev.set == s].record_id) for s in SETS if (ev.set == s).any()}
eh["train_ids"] = sha_list(df[df.split == "train"].record_id)
json.dump(dict(evaluation_set_sha256=eh, evaluation_set_sizes={s: int((ev.set == s).sum()) for s in SETS}), open(os.path.join(OUT, "_evaluation_split_hashes.json"), "w"), indent=1)

# ---------------- keep tables for the report writer
pd.to_pickle(dict(M=M, PC=PC, CF=CF, CAL=CAL, ECE=ECE, LG=LG, LGR=LGR, CV=CV, HD=HD, BOOT=BOOT, eh=eh), os.path.join(OUT, "_eval_tables.pkl"))
lock = json.load(open(LOCK))
lock["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
json.dump(lock, open(LOCK, "w"))
print("EVALUATION DONE (locked)")
