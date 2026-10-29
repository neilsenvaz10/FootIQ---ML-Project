"""Phase 4 (step 1): Elo-parameter grid on development folds, then build all candidate features using ONLY matches dated <= 2024-06-30."""
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa
import v2_features as vf  # noqa

sys.stdout.reconfigure(encoding="utf-8")
proto = json.load(open(os.path.join(WORK, "protocol_frozen.json")))
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
ds = pd.read_csv(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC,
                 usecols=["record_id", "competition_id", "season_corrected", "calendar_type", "match_date", "split", "season_status", "identity_review_flag", "tier", "y_90min_1x2",
                          "home_entity_id", "away_entity_id", "competition_country"])
fe1 = pd.read_csv(os.path.join(PREP, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
ds = ds[ds.match_date <= DEV_END].copy()                         # development rows only
Vd = V[V.match_date <= DEV_END].copy()                           # the state never sees a match after 2024-06-30
df = pd.DataFrame(dict(record_id=Vd.record_id, dt=Vd.dt, h=Vd.home_entity_id, a=Vd.away_entity_id, comp=Vd.competition_id, season=Vd.season_corrected, tier=Vd.tier,
                       ctype=Vd.competition_type, regular=Vd.regular_round_robin_stage, rated=Vd.rated, gh=Vd.gh, ga=Vd.ga))
want = set(ds.record_id)
print("state universe", len(df), "development rows", len(ds), "last date", df.dt.max().date())
ds["y"] = ds.y_90min_1x2.map({"H": 0, "D": 1, "A": 2})
ds["split_year"] = ds.calendar_type.str.startswith("split")
ds["dev_primary"] = ds.season_status.isin(["complete", "in_progress_complete_through_cutoff"]) & ~ds.identity_review_flag & ds.split_year
ds["dev_secondary"] = ds.season_status.isin(["complete", "in_progress_complete_through_cutoff"]) & ~ds.identity_review_flag & ~ds.split_year


# ---------------- Elo grid (Elo-only ordered logit per fold; train window -> validation window)
def elo_pass(params):
    el = vf.Elo2(*params)
    diffs = {}
    for dt, g in df.sort_values(["dt", "record_id"], kind="mergesort").groupby("dt", sort=True):
        d = dt.toordinal()
        rows = list(g.itertuples())
        cache = {}
        pre = []
        for r in rows:
            if r.comp not in cache:
                cache[r.comp] = el.league_mean(r.comp, d)
            lm = cache[r.comp]
            eh, ea = el.eff(r.h, r.comp, r.season, lm), el.eff(r.a, r.comp, r.season, lm)
            if r.record_id in want:
                diffs[r.record_id] = eh - ea
            pre.append((eh, ea))
        for r, (eh, ea) in zip(rows, pre):
            if r.rated:
                el.update(r.h, r.a, r.comp, r.season, d, eh, ea, r.gh, r.ga)
    return pd.Series(diffs)


def ordlogit_fit(d, y):
    def nll(t):
        b, c1, ld = t
        z = b * d / 100.0
        pA = expit(c1 - z); pAD = expit(c1 + np.exp(ld) - z)
        P = np.column_stack([1 - pAD, pAD - pA, pA])
        return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1)).mean()
    return minimize(nll, [1.0, -0.5, 0.0], method="L-BFGS-B").x


def ordlogit_proba(t, d):
    b, c1, ld = t
    z = b * np.asarray(d) / 100.0
    pA = expit(c1 - z); pAD = expit(c1 + np.exp(ld) - z)
    return np.column_stack([1 - pAD, pAD - pA, pA])


grid = [(K, HA, R) for K in (15.0, 20.0, 30.0) for HA in (50.0, 75.0) for R in (0.0, 0.2, 0.4)]
rows = []
t0 = time.time()
for params in grid:
    diff = elo_pass(params)
    dd = ds.set_index("record_id")
    x = diff.reindex(dd.index)
    fl = []
    for f in FOLDS:
        tr = dd[dd.match_date <= f["train_end"]]
        va = dd[(dd.match_date >= f["val_start"]) & (dd.match_date <= f["val_end"]) & dd.dev_primary]
        t = ordlogit_fit(x[tr.index].values, tr.y.astype(int).values)
        fl.append(metrics(va.y.astype(int).values, ordlogit_proba(t, x[va.index].values))["log_loss"])
    rows.append(dict(K=params[0], HA=params[1], regression=params[2], fold1=fl[0], fold2=fl[1], fold3=fl[2], mean_log_loss=float(np.mean(fl)), std=float(np.std(fl))))
    print(rows[-1], round(time.time() - t0))
gt = pd.DataFrame(rows).sort_values("mean_log_loss")
gt.to_csv(os.path.join(OUT, "03b_ELO_PARAMETER_GRID.csv"), index=False)
best = gt.iloc[0]
v1_like = gt[(gt.K == 20) & (gt.HA == 75) & (gt.regression == 0)]
chosen = (float(best.K), float(best.HA), float(best.regression))
print("chosen Elo2 params", chosen)

# ---------------- build all candidate features with the chosen Elo2
F = vf.build(df, want, chosen)
F = F.join(ds.set_index("record_id")[["competition_id", "season_corrected", "calendar_type", "match_date", "split", "dev_primary", "dev_secondary", "y", "tier"]], how="left")
F["competition_id"] = F["competition_id"].astype(str)
F.to_pickle(os.path.join(WORK, "features_v2_dev.pkl"))
json.dump(dict(elo2_params=dict(K=chosen[0], HA=chosen[1], season_regression=chosen[2]), grid_best=best.to_dict(), n_rows=len(F), columns=list(F.columns), built_from_matches_through=str(df.dt.max().date())),
          open(os.path.join(WORK, "features_v2_meta.json"), "w"), indent=1, default=str)
# v1 25-feature file restricted to the development rows (for baseline reproduction)
fe1[fe1.record_id.isin(want)].to_pickle(os.path.join(WORK, "features_v1_dev.pkl"))
print("features", F.shape, "NaN share by column (top):")
print(F.isna().mean().sort_values(ascending=False).head(12).round(4).to_string())
