"""Do static team strengths explain the under-coverage of the simulated points intervals? (diagnostic only; no model or probability is changed)

The M2b backtest found that the 10-90% simulated interval for final points contained the realised points about 75% of the time instead of 80%. In that backtest every
remaining fixture was given its probability at the cut-off (static strengths). The "oracle" check below compares them with the pre-match probabilities the same frozen model
produced at each match's own date (it has seen the results in between, so it is not available at the cut-off; it only measures how much the probabilities drift).

Law of total variance: Var(actual - E_static) = E[Var(points | drifted probabilities)] + Var(E_dyn - E_static) + noise from the model's own error.
If Var(E_dyn - E_static) is about the size of the missing variance, static strengths explain the gap.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
OUT = APP.parent / "data" / "supervised" / "phase3"
Z90 = norm.ppf(0.9)
SEASON_OF = {"2024-25": ("2024-07-01", "2025-06-30"), "2025-26": ("2025-07-01", "2026-06-30")}


def outcome_points(row) -> tuple:
    return 3 * row.p1_H + row.p1_D, 3 * row.p1_A + row.p1_D


def run() -> dict:
    rows = pd.read_pickle(OUT / "m2b_rows.pkl")
    rows = rows[(rows.method == "S1") & (rows.remaining > 0)].copy()                      # points do not depend on the scoreline method
    m = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    m["e_home"], m["e_away"] = 3 * m.p1_H + m.p1_D, 3 * m.p1_A + m.p1_D
    m["pts_home"] = np.where(m.hg > m.ag, 3, np.where(m.hg == m.ag, 1, 0))
    m["pts_away"] = np.where(m.ag > m.hg, 3, np.where(m.hg == m.ag, 1, 0))
    out_rows, mismatch = [], 0
    for (season, cutoff, league), g in rows.groupby(["season", "cutoff", "league"]):
        lo, hi = SEASON_OF[season]
        ms = m[(m.league == league) & (m.dt >= lo) & (m.dt <= hi)]
        c = pd.Timestamp(cutoff)
        for r in g.itertuples():
            h, a = ms[ms.home == r.team], ms[ms.away == r.team]
            before = h[h.dt < c].pts_home.sum() + a[a.dt < c].pts_away.sum()
            real = h.pts_home.sum() + a.pts_away.sum()
            e_dyn = before + h[h.dt >= c].e_home.sum() + a[a.dt >= c].e_away.sum()
            if abs(real - r.pts_real) > 0.5:
                mismatch += 1
                continue
            sd_sim = (r.pts_p90 - r.pts_p10) / (2 * Z90)
            out_rows.append(dict(season=season, cutoff=cutoff, league=league, team=r.team, real=r.pts_real, e_static=r.pts_mean, e_dyn=e_dyn, sd_sim=sd_sim, p10=r.pts_p10, p90=r.pts_p90, before=before))
    d = pd.DataFrame(out_rows)
    d["resid"] = d.real - d.e_static
    d["drift"] = d.e_dyn - d.e_static
    d["z"] = d.resid / d.sd_sim
    res = dict(rows=int(len(d)), skipped_because_totals_differ=int(mismatch), by_cutoff_month={}, pooled={})

    def block(x: pd.DataFrame) -> dict:
        var_resid, var_sim, var_drift = float(x.resid.var(ddof=0)), float((x.sd_sim ** 2).mean()), float(x.drift.var(ddof=0))
        slope = float(np.polyfit(x.e_static - x.before, x.real - x.before, 1)[0])                 # 1 would mean the remaining-points forecast is calibrated on average
        cov = float(((x.real >= x.p10) & (x.real <= x.p90)).mean())
        sd_wide = np.sqrt(x.sd_sim ** 2 + var_drift)
        cov_wide = float((x.resid.abs() <= Z90 * sd_wide).mean())                                    # normal-approximation coverage with the drift variance added (in-sample, diagnostic)
        cov_norm = float((x.resid.abs() <= Z90 * x.sd_sim).mean())
        var_after_drift = float((x.real - x.e_dyn).var(ddof=0))                                     # what is left when the probabilities are allowed to drift (oracle)
        return dict(n=int(len(x)), variance_left_after_oracle_drift=round(var_after_drift, 2), coverage_simulated_interval=round(cov, 3), coverage_normal_approximation=round(cov_norm, 3), coverage_after_adding_drift_variance=round(cov_wide, 3),
                    observed_residual_variance=round(var_resid, 2), mean_simulated_variance=round(var_sim, 2), missing_variance=round(var_resid - var_sim, 2), drift_variance=round(var_drift, 2),
                    share_of_missing_variance_explained_by_drift=None if var_resid - var_sim <= 0 else round(min(var_drift / (var_resid - var_sim), 9.99), 2),
                    std_of_standardised_residual=round(float(x.z.std()), 3), mean_bias_points=round(float(x.resid.mean()), 2), calibration_slope_of_remaining_points=round(slope, 3),
                    mean_abs_drift_points=round(float(x.drift.abs().mean()), 2))

    res["pooled"] = block(d)
    for cutoff, x in d.groupby(d.cutoff.str[5:7]):
        res["by_cutoff_month"][{"11": "1 Nov", "01": "1 Jan", "03": "1 Mar"}[cutoff]] = block(x)
    res["by_league"] = {lg: block(x) for lg, x in d.groupby("league")}
    # does the drift behave like a random walk that grows with the remaining fixtures? (variance of drift per remaining match)
    rem = rows.set_index(["season", "cutoff", "league", "team"]).remaining
    d["remaining"] = [rem.loc[(r.season, r.cutoff, r.league, r.team)] for r in d.itertuples()]
    res["drift_variance_per_remaining_match"] = {str(k): round(float(x.drift.var(ddof=0) / x.remaining.mean()), 3) for k, x in d.groupby(pd.cut(d.remaining, [0, 12, 20, 28, 40]))}
    d.to_pickle(OUT / "m2_static_diag_rows.pkl")
    return res


if __name__ == "__main__":
    r = run()
    (OUT / "m2_static_diag.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "by_league"}, indent=1))
    print({lg: (v["coverage_simulated_interval"], v["share_of_missing_variance_explained_by_drift"]) for lg, v in r["by_league"].items()})
