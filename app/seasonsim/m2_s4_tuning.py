"""Candidate S4 (NOT part of the predeclared benchmark; proposed only after S1-S3 failed): S1 with expected goals shrunk towards the league mean,
lam' = exp(k*log(lam) + (1-k)*log(league mean)). k is tuned ONLY on the 2023-24 validation season (fit window before 2023-07-01); matches dated 2024-07-01 or later are not read.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import m2_benchmark as B  # noqa: E402
from seasonsim import scoreline  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"
KS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4]


def run() -> dict:
    df = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    fit = df[df.dt < "2023-07-01"]
    val = df[(df.dt >= "2023-07-01") & (df.dt < "2024-07-01")]               # the only matches used for the choice
    assert val.dt.max() < pd.Timestamp("2024-07-01")
    lam = {l: (float(g.hg.mean()), float(g.ag.mean())) for l, g in fit.groupby("league")}
    out = {"validation_matches": int(len(val)), "fit_matches": int(len(fit)), "by_k": {}}
    for k in KS:
        worst, per = 0.0, {}
        for lg in B.LEAGUES:
            e = val[val.league == lg]
            lh = np.exp(k * np.log(e.lam_h.values) + (1 - k) * np.log(lam[lg][0]))
            la = np.exp(k * np.log(e.lam_a.values) + (1 - k) * np.log(lam[lg][1]))
            pmf = scoreline.conditional_poisson(e[["p1_H", "p1_D", "p1_A"]].values, lh, la)
            st, act = B.model_stats(pmf), B.actual_stats(e.hg.values.astype(int), e.ag.values.astype(int))
            d = {x: st[x] - act[x] for x in ("mean_margin_home_win", "mean_margin_away_win", "share_one_goal_home_win", "share_one_goal_away_win")}
            norm = max(abs(d["mean_margin_home_win"]) / B.TOL_MARGIN, abs(d["mean_margin_away_win"]) / B.TOL_MARGIN, abs(d["share_one_goal_home_win"]) / B.TOL_SHARE, abs(d["share_one_goal_away_win"]) / B.TOL_SHARE)
            per[lg] = dict(max_normalised_deviation=round(norm, 3), passes=bool(norm <= 1.0), **{x: round(v, 3) for x, v in d.items()})
            worst = max(worst, norm)
        out["by_k"][str(k)] = dict(worst_normalised_deviation=round(worst, 3), leagues_passing=sum(v["passes"] for v in per.values()), per_league=per)
    best = min(out["by_k"], key=lambda k: out["by_k"][k]["worst_normalised_deviation"])
    out["best_k_on_validation"] = float(best)
    return out


if __name__ == "__main__":
    r = run()
    (OUT / "m2_s4_tuning.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    for k, v in r["by_k"].items():
        print(k, "worst", v["worst_normalised_deviation"], "passing", v["leagues_passing"], {l: p["max_normalised_deviation"] for l, p in v["per_league"].items()})
    print("best k on validation:", r["best_k_on_validation"])
