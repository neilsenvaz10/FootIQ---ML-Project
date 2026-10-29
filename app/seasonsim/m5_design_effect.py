"""How much does dependence between matches played at the same time inflate the standard errors of the four scoreline statistics? (Protocol v3 planning, offline.)

Uses ONLY the development window (matches before 2024-07-01) of the five leagues, which is not the Benchmark v1 window and not a confirmation set (no CA or CB match is read).
For each statistic (mean winning margin in home wins, in away wins; share of one-goal wins among home wins, among away wins) the naive standard error treats matches as independent,
and the cluster-robust standard error treats all matches of one league and one calendar week as a cluster. The design effect is the ratio of the two variances: sample sizes planned
with the naive formula must be multiplied by it.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import m2_benchmark as B  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"


def cluster_se(x: np.ndarray, cluster: np.ndarray) -> tuple:
    """Naive and cluster-robust standard error of the mean of x (one observation per match in the subset)."""
    n = len(x)
    mu = x.mean()
    naive = x.std(ddof=1) / np.sqrt(n)
    tot = pd.Series(x - mu).groupby(cluster).sum()
    robust = np.sqrt((tot ** 2).sum() * n / (n - 1)) / n
    return float(naive), float(robust)


def main() -> dict:
    df = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    d0 = df[df.dt < B.SPLIT].copy()
    d0["gd"] = d0.hg - d0.ag
    d0["cluster"] = d0.league.astype(str) + "|" + d0.dt.dt.to_period("W").astype(str)
    res = dict(window="matches before 2024-07-01 (development window), five leagues", matches=int(len(d0)), clusters=int(d0.cluster.nunique()), statistics={}, by_league={})
    spec = {"margin_home": (d0.gd > 0, d0.gd), "margin_away": (d0.gd < 0, -d0.gd), "share1_home": (d0.gd > 0, (d0.gd == 1).astype(float)), "share1_away": (d0.gd < 0, ((-d0.gd) == 1).astype(float))}
    for name, (mask, val) in spec.items():
        x, c = val[mask].values.astype(float), d0.cluster[mask].values
        naive, robust = cluster_se(x, c)
        res["statistics"][name] = dict(n=int(mask.sum()), mean=round(float(x.mean()), 4), se_naive=round(naive, 5), se_cluster=round(robust, 5), design_effect=round((robust / naive) ** 2, 3))
    for lg, g in d0.groupby("league"):
        row = {}
        for name, (mask, val) in spec.items():
            m = mask.loc[g.index]
            x, c = val.loc[g.index][m].values.astype(float), g.cluster[m].values
            naive, robust = cluster_se(x, c)
            row[name] = round((robust / naive) ** 2, 3)
        res["by_league"][lg] = row
    res["largest_design_effect"] = max(v["design_effect"] for v in res["statistics"].values())
    return res


if __name__ == "__main__":
    r = main()
    (OUT / "m5_design_effect.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps(r, indent=1))
