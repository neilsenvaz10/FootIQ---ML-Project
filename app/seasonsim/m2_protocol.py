"""Why the predeclared M2a rule is so demanding, and operating characteristics of a PROPOSED revised protocol.

Nothing here is applied to the observed benchmark results: the original pass/fail outcome stands. The proposed protocols are evaluated only on synthetic samples drawn from known
truths (the evaluation matches' own S1 distributions, or a deliberately biased variant), so that their type-I error (a correct model is rejected) and power (a biased model is
rejected) are known BEFORE any protocol is approved for use.

Statistics per league (as in the original rule): d_k = model statistic - actual statistic for k in
  margin in home wins, margin in away wins, share of one-goal margins among home wins, among away wins.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import m2_benchmark as B  # noqa: E402
from seasonsim import scoreline  # noqa: E402
from seasonsim.engine import K  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"
G = np.arange(K)
GD = G[:, None] - G[None, :]
KEYS = ("margin_home", "margin_away", "share1_home", "share1_away")
TOL_ORIG = dict(margin_home=0.10, margin_away=0.10, share1_home=0.05, share1_away=0.05)


def model_vec(pmf) -> np.ndarray:
    s = B.model_stats(pmf)
    return np.array([s["mean_margin_home_win"], s["mean_margin_away_win"], s["share_one_goal_home_win"], s["share_one_goal_away_win"]])


def sample_actual(pmf: np.ndarray, rng) -> tuple:
    """Draw one season of scores from the pmfs; return the four statistics and their standard errors."""
    n = len(pmf)
    cdf = np.cumsum(pmf.reshape(n, -1), axis=1)
    idx = (rng.random(n)[:, None] > cdf).sum(axis=1).clip(0, K * K - 1)
    d = (idx // K) - (idx % K)
    hw, aw = d > 0, d < 0
    est = np.array([d[hw].mean(), (-d[aw]).mean(), (d[hw] == 1).mean(), (d[aw] == -1).mean()])
    se = np.array([d[hw].std(ddof=1) / np.sqrt(hw.sum()), (-d[aw]).std(ddof=1) / np.sqrt(aw.sum()),
                   np.sqrt(est[2] * (1 - est[2]) / hw.sum()), np.sqrt(est[3] * (1 - est[3]) / aw.sum())])
    return est, se


def protocols(dev: np.ndarray, se: np.ndarray, delta: np.ndarray) -> dict:
    """Decision of each protocol for ONE league. dev = model - actual."""
    out = {"P0_original_point_tolerance": bool((np.abs(dev) <= np.array([TOL_ORIG[k] for k in KEYS])).all())}
    for name, level in (("P1_equivalence_90CI", 0.90), ("P1b_equivalence_96.7CI_3_methods", 1 - 0.1 / 3)):
        z = norm.ppf(1 - (1 - level) / 2)
        out[name] = bool(((np.abs(dev) + z * se) <= delta).all())
    # P2: no statistically detectable deviation after Holm over the 4 statistics x 5 leagues (family of 20), AND the point estimate inside the practical bound
    z_holm_worst = norm.ppf(1 - 0.05 / 20 / 2)
    out["P2_Holm_nonrejection_plus_bound"] = bool(((np.abs(dev) / se) <= z_holm_worst).all() and (np.abs(dev) <= delta).all())
    return out


def pooled_protocol(per_league: dict, leagues: list, tol: np.ndarray, level: float = 0.90) -> dict:
    """P3 (proposed primary): pooled equivalence + per-league screen. per_league[lg] = (dev, se)."""
    inv = np.array([1.0 / per_league[lg][1] ** 2 for lg in leagues])
    dev = np.array([per_league[lg][0] for lg in leagues])
    pooled = (inv * dev).sum(axis=0) / inv.sum(axis=0)
    pooled_se = 1.0 / np.sqrt(inv.sum(axis=0))
    z = norm.ppf(1 - (1 - level) / 2)
    pooled_ok = bool(((np.abs(pooled) + z * pooled_se) <= tol).all())               # 90% CI of the pooled deviation lies inside the practical margin (two one-sided tests)
    z_holm = norm.ppf(1 - 0.05 / (4 * len(leagues)) / 2)
    flagged = [lg for lg in leagues if ((np.abs(per_league[lg][0]) / per_league[lg][1] > z_holm) & (np.abs(per_league[lg][0]) > tol)).any()]
    return dict(pooled_equivalence=pooled_ok, no_league_flagged=not flagged, accepted=pooled_ok and not flagged, flagged=flagged)


def run(reps: int = 400, seed: int = 21) -> dict:
    df = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    ev = df[df.dt >= B.SPLIT]
    fit = df[df.dt < B.SPLIT]
    lam_mean = {l: (float(g.hg.mean()), float(g.ag.mean())) for l, g in fit.groupby("league")}
    rng = np.random.default_rng(seed)
    deltas = {"delta_A (0.15 goals, 0.06 share)": np.array([0.15, 0.15, 0.06, 0.06]), "delta_B (0.20 goals, 0.08 share)": np.array([0.20, 0.20, 0.08, 0.08]), "delta_C (0.25 goals, 0.10 share)": np.array([0.25, 0.25, 0.10, 0.10])}
    scen = {"T0_model_exactly_true": 1.0, "T1_true_spread_80pct_of_model": 0.8, "T2_true_spread_60pct_of_model": 0.6, "T3_true_spread_40pct_of_model": 0.4}
    result = {"reps": reps, "scenarios": {}, "analytic_sampling_noise": {}}
    # --- analytic noise: tolerance measured in standard errors of the actual statistic (one draw of the real sample sizes)
    for lg in B.LEAGUES:
        e = ev[ev.league == lg]
        pmf = scoreline.conditional_poisson(e[["p1_H", "p1_D", "p1_A"]].values, e.lam_h.values, e.lam_a.values)
        est, se = sample_actual(pmf, np.random.default_rng(1))
        tol = np.array([TOL_ORIG[k] for k in KEYS])
        pass_each = 2 * norm.cdf(tol / se) - 1
        result["analytic_sampling_noise"][lg] = dict(n=int(len(e)), standard_errors=dict(zip(KEYS, [round(float(x), 4) for x in se])), tolerance_in_standard_errors=dict(zip(KEYS, [round(float(x), 2) for x in tol / se])),
                                                      pass_probability_each_statistic=dict(zip(KEYS, [round(float(x), 3) for x in pass_each])), pass_probability_if_independent=round(float(np.prod(pass_each)), 3))
    prod = float(np.prod([v["pass_probability_if_independent"] for v in result["analytic_sampling_noise"].values()]))
    result["analytic_all_five_pass_probability_if_independent"] = round(prod, 3)
    # --- operating characteristics by simulation
    for sname, k in scen.items():
        truth_pmfs, model_pmfs, bias = {}, {}, {}
        for lg in B.LEAGUES:
            e = ev[ev.league == lg]
            P = e[["p1_H", "p1_D", "p1_A"]].values
            model_pmfs[lg] = scoreline.conditional_poisson(P, e.lam_h.values, e.lam_a.values)
            lh = np.exp(k * np.log(e.lam_h.values) + (1 - k) * np.log(lam_mean[lg][0]))
            la = np.exp(k * np.log(e.lam_a.values) + (1 - k) * np.log(lam_mean[lg][1]))
            truth_pmfs[lg] = scoreline.conditional_poisson(P, lh, la)
            bias[lg] = dict(zip(KEYS, [round(float(x), 3) for x in model_vec(model_pmfs[lg]) - model_vec(truth_pmfs[lg])]))
        acc = {}
        for lg in B.LEAGUES:
            mv = model_vec(model_pmfs[lg])
            draws = []
            for _ in range(reps):
                est, se = sample_actual(truth_pmfs[lg], rng)
                draws.append(protocols(mv - est, se, None) if False else (mv - est, se))
            acc[lg] = draws
        names = None
        table = {}
        for dname, delta in deltas.items():
            per_rep = []
            for r in range(reps):
                per_rep.append({lg: protocols(*acc[lg][r], delta) for lg in B.LEAGUES})
            names = list(per_rep[0][B.LEAGUES[0]])
            table[dname] = {nm: dict(per_league={lg: round(float(np.mean([x[lg][nm] for x in per_rep])), 3) for lg in B.LEAGUES}, all_five=round(float(np.mean([all(x[lg][nm] for lg in B.LEAGUES) for x in per_rep])), 3)) for nm in names}
        tol = np.array([TOL_ORIG[k] for k in KEYS])
        p3 = {"all_five_leagues": [], "bundesliga_and_la_liga": []}
        for r in range(reps):
            per = {lg: acc[lg][r] for lg in B.LEAGUES}
            p3["all_five_leagues"].append(pooled_protocol(per, list(B.LEAGUES), tol)["accepted"])
            p3["bundesliga_and_la_liga"].append(pooled_protocol(per, ["BUNDESLIGA", "LALIGA"], tol)["accepted"])
        table["P3_pooled_equivalence_plus_league_screen (tolerances 0.10 goals / 0.05 share as practical margins)"] = {k: round(float(np.mean(v)), 3) for k, v in p3.items()}
        result["scenarios"][sname] = dict(true_bias_of_the_model_vs_truth=bias, acceptance_probability=table)
    return result


def scope_power(reps: int = 400, seed: int = 5) -> dict:
    """Operating characteristics of the proposed pooled protocol for a Bundesliga + La Liga scope at two choices of practical margin."""
    df = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    ev, fit = df[df.dt >= B.SPLIT], df[df.dt < B.SPLIT]
    lam_mean = {l: (float(g.hg.mean()), float(g.ag.mean())) for l, g in fit.groupby("league")}
    rng = np.random.default_rng(seed)
    leagues = ["BUNDESLIGA", "LALIGA"]
    margins = {"margins 0.10 goals / 0.05 share": np.array([0.10, 0.10, 0.05, 0.05]), "margins 0.15 goals / 0.075 share": np.array([0.15, 0.15, 0.075, 0.075])}
    out = {"matches_in_scope": int(sum((ev.league == lg).sum() for lg in leagues))}
    for sname, k in {"model exactly true": 1.0, "true spread 80% of model (margin bias about 0.05)": 0.8, "true spread 60% of model (margin bias about 0.09)": 0.6, "true spread 40% of model (margin bias about 0.12)": 0.4}.items():
        truth, model = {}, {}
        for lg in leagues:
            e = ev[ev.league == lg]
            P = e[["p1_H", "p1_D", "p1_A"]].values
            model[lg] = scoreline.conditional_poisson(P, e.lam_h.values, e.lam_a.values)
            truth[lg] = scoreline.conditional_poisson(P, np.exp(k * np.log(e.lam_h.values) + (1 - k) * np.log(lam_mean[lg][0])), np.exp(k * np.log(e.lam_a.values) + (1 - k) * np.log(lam_mean[lg][1])))
        res = {m: [] for m in margins}
        for _ in range(reps):
            per = {}
            for lg in leagues:
                est, se = sample_actual(truth[lg], rng)
                per[lg] = (model_vec(model[lg]) - est, se)
            for m, tol in margins.items():
                res[m].append(pooled_protocol(per, leagues, tol)["accepted"])
        out[sname] = {m: round(float(np.mean(v)), 3) for m, v in res.items()}
    return out


if __name__ == "__main__":
    r = run()
    r["bundesliga_la_liga_scope"] = scope_power()
    (OUT / "m2_protocol.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps(r["bundesliga_la_liga_scope"], indent=1))
    print(json.dumps(r["analytic_sampling_noise"], indent=0)[:1800])
    print("analytic all-five:", r["analytic_all_five_pass_probability_if_independent"])
    for s, v in r["scenarios"].items():
        print("\n", s, "bias(home margin, 1-goal share) by league:", {l: (b["margin_home"], b["share1_home"]) for l, b in v["true_bias_of_the_model_vs_truth"].items()})
        for d, t in v["acceptance_probability"].items():
            if d.startswith("P3"):
                print("  ", d[:40], t)
            else:
                print("  ", d, {n: x["all_five"] for n, x in t.items()})
