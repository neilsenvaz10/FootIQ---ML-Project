"""M2a: benchmark of the three scoreline methods against the criteria declared in docs/mini-project/PHASE3_PLAN.md section 5 BEFORE any result was seen.

Predeclared distribution criteria, per league, evaluated on matches dated 2024-07-01 or later (v1 test + forward holdout), scoreline parameters fitted
on matches before 2024-07-01 only:
  C1  mean goal margin given a home win (and given an away win) within +-0.10 goals of the actual mean
  C2  share of 1-goal margins among home wins (and among away wins) within +-0.05 of the actual share
A method is acceptable only if C1 and C2 hold in EVERY one of the five leagues (the plan's wording: "in every league"), and, in M2b, its simulated season goal
differences cover the real ones at 70-90% for the 10-90% interval. Nothing here is tuned on the evaluation matches.

    python app/seasonsim/m2_benchmark.py        (needs data/supervised/phase3/m2_matches.pkl from m2_data.py)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import scoreline  # noqa: E402
from seasonsim.engine import K  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"
SPLIT = pd.Timestamp("2024-07-01")
TOL_MARGIN, TOL_SHARE = 0.10, 0.05
LEAGUES = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"]
G = np.arange(K)
GD = G[:, None] - G[None, :]
HOME, AWAY, DRAW = GD > 0, GD < 0, GD == 0


def model_stats(pmf: np.ndarray) -> dict:
    """Probability-weighted statistics pooled over matches: pmf [n, K, K]."""
    tot = pmf.sum(axis=0)                                           # expected number of each scoreline
    pH, pA, pD = tot[HOME].sum(), tot[AWAY].sum(), tot[DRAW].sum()
    d = np.diag(tot)
    return dict(mean_margin_home_win=float((tot * GD)[HOME].sum() / pH), mean_margin_away_win=float((tot * -GD)[AWAY].sum() / pA),
                share_one_goal_home_win=float(tot[GD == 1].sum() / pH), share_one_goal_away_win=float(tot[GD == -1].sum() / pA),
                share_00_in_draws=float(d[0] / pD), share_11_in_draws=float(d[1] / pD), share_22plus_in_draws=float(d[2:].sum() / pD),
                mean_total_goals=float((tot * (G[:, None] + G[None, :])).sum() / tot.sum()))


def actual_stats(hg: np.ndarray, ag: np.ndarray) -> dict:
    hg, ag = np.minimum(hg, K - 1), np.minimum(ag, K - 1)
    d = hg - ag
    hw, aw, dr = d > 0, d < 0, d == 0
    return dict(mean_margin_home_win=float(d[hw].mean()), mean_margin_away_win=float((-d[aw]).mean()),
                share_one_goal_home_win=float((d[hw] == 1).mean()), share_one_goal_away_win=float((d[aw] == -1).mean()),
                share_00_in_draws=float(((hg == 0) & dr).sum() / dr.sum()), share_11_in_draws=float(((hg == 1) & dr).sum() / dr.sum()),
                share_22plus_in_draws=float(((hg >= 2) & dr).sum() / dr.sum()), mean_total_goals=float((hg + ag).mean()))


def bootstrap_ci(hg, ag, reps=400, seed=0):
    rng = np.random.default_rng(seed)
    n = len(hg)
    keys = ("mean_margin_home_win", "mean_margin_away_win", "share_one_goal_home_win", "share_one_goal_away_win")
    draws = {k: [] for k in keys}
    for _ in range(reps):
        i = rng.integers(0, n, n)
        s = actual_stats(hg[i], ag[i])
        for k in keys:
            draws[k].append(s[k])
    return {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in draws.items()}


def run(df: pd.DataFrame, probs: str = "p1") -> dict:
    df = df.dropna(subset=["hg", "ag"]).copy()
    fit, ev = df[df.dt < SPLIT], df[df.dt >= SPLIT]
    emp = scoreline.Empirical().fit(fit.league.values, (fit.lam_h - fit.lam_a).values, fit.hg.values, fit.ag.values)
    league_lams = {l: (float(g.hg.mean()), float(g.ag.mean())) for l, g in fit.groupby("league")}
    report = dict(split=str(SPLIT.date()), fit_matches=int(len(fit)), eval_matches=int(len(ev)), probabilities=probs, tolerance=dict(margin=TOL_MARGIN, share=TOL_SHARE), leagues={})
    for lg in LEAGUES:
        e = ev[ev.league == lg]
        P = e[[f"{probs}_H", f"{probs}_D", f"{probs}_A"]].values
        act = actual_stats(e.hg.values.astype(int), e.ag.values.astype(int))
        ci = bootstrap_ci(e.hg.values.astype(int), e.ag.values.astype(int))
        lg_rep = dict(n=int(len(e)), actual=act, actual_95ci=ci, methods={})
        for m in ("S1", "S2", "S3"):
            pmf, info = scoreline.build_pmf(m, P, e.lam_h.values, e.lam_a.values, lg, league_lams[lg], emp)
            st = model_stats(pmf)
            dev = {k: st[k] - act[k] for k in act}
            c1 = abs(dev["mean_margin_home_win"]) <= TOL_MARGIN and abs(dev["mean_margin_away_win"]) <= TOL_MARGIN
            c2 = abs(dev["share_one_goal_home_win"]) <= TOL_SHARE and abs(dev["share_one_goal_away_win"]) <= TOL_SHARE
            ll = float(-np.mean(np.log(np.clip(pmf[np.arange(len(e)), np.minimum(e.hg.values.astype(int), K - 1), np.minimum(e.ag.values.astype(int), K - 1)], 1e-12, None))))
            lg_rep["methods"][m] = dict(model=st, deviation=dev, C1_margin_ok=bool(c1), C2_one_goal_share_ok=bool(c2), passes=bool(c1 and c2), mean_log_score_of_actual_scoreline=ll, info=info)
        report["leagues"][lg] = lg_rep
    report["verdict"] = {}
    for m in ("S1", "S2", "S3"):
        per = {lg: report["leagues"][lg]["methods"][m]["passes"] for lg in LEAGUES}
        report["verdict"][m] = dict(per_league=per, passes_every_league=all(per.values()), passes_bundesliga_and_la_liga_only=bool(per["BUNDESLIGA"] and per["LALIGA"]),
                                    mean_log_score=float(np.mean([report["leagues"][lg]["methods"][m]["mean_log_score_of_actual_scoreline"] for lg in LEAGUES])))
    return report


def show(report: dict) -> None:
    print(f"fit {report['fit_matches']} matches before {report['split']}; evaluation {report['eval_matches']} matches")
    for lg in LEAGUES:
        r = report["leagues"][lg]
        a = r["actual"]
        print(f"\n{lg} n={r['n']}  actual: margin|H {a['mean_margin_home_win']:.3f} margin|A {a['mean_margin_away_win']:.3f} 1-goal|H {a['share_one_goal_home_win']:.3f} 1-goal|A {a['share_one_goal_away_win']:.3f}")
        for m, x in r["methods"].items():
            d = x["deviation"]
            print(f"  {m}: margin|H {d['mean_margin_home_win']:+.3f} margin|A {d['mean_margin_away_win']:+.3f} 1-goal|H {d['share_one_goal_home_win']:+.3f} 1-goal|A {d['share_one_goal_away_win']:+.3f}  C1 {x['C1_margin_ok']} C2 {x['C2_one_goal_share_ok']}  logscore {x['mean_log_score_of_actual_scoreline']:.4f}  fallbacks {x['info'].get('fallback_fixtures')}")
    print("\nVERDICT (predeclared: every league):", {m: v["passes_every_league"] for m, v in report["verdict"].items()})


if __name__ == "__main__":
    df = pd.read_pickle(OUT / "m2_matches.pkl")
    rep = run(df, "p1")
    (OUT / "m2_distribution_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    show(rep)
