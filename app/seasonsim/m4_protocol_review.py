"""Independent review of the proposed Protocol v2 (synthetic data only; no confirmation set CA or CB is touched, nothing is applied to any real result).

Questions answered by simulation:
  Q3  Do the proposed testing sequence and the Holm league screen control the intended error rates?  (compares the sequence as proposed with Holm and Bonferroni over methods)
  Q5  Is the proposed CB sample large enough?  (acceptance probability of a correct / biased model as the sample grows)
  Q6  Are the stated power numbers reproducible?  (re-run with the same seed, a different seed, and check the sample-size formula)
The template is the real evaluation fixtures (probabilities and expected goals) of the five leagues; "truth" is a chosen scoreline distribution from which synthetic results are drawn.
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
from seasonsim import m2_protocol as P  # noqa: E402
from seasonsim import scoreline  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"
DELTA = np.array([0.15, 0.15, 0.075, 0.075])
ALPHA = 0.05
METHODS = ("S1", "S2", "S3")


def inflate(pmf: np.ndarray, q: float) -> np.ndarray:
    """Truth in which, with probability q, the winner of a decisive match scores one more goal: every mean winning margin rises by about q and one-goal wins become rarer."""
    G = np.arange(B.K)
    home, away = (G[:, None] > G[None, :]), (G[:, None] < G[None, :])
    sh = np.zeros_like(pmf)
    src_h = pmf * home[None]
    src_a = pmf * away[None]
    sh[:, 1:, :] += src_h[:, :-1, :]
    sh[:, -1, :] += src_h[:, -1, :]
    sh[:, :, 1:] += src_a[:, :, :-1]
    sh[:, :, -1] += src_a[:, :, -1]
    sh += pmf * (~(home | away))[None]
    return (1 - q) * pmf + q * sh


def deflate(pmf: np.ndarray, q: float) -> np.ndarray:
    """Opposite distortion: with probability q the winner of a win by two or more goals scores one goal fewer (winning margins shrink, one-goal wins become more common)."""
    G = np.arange(B.K)
    big_h = (G[:, None] - G[None, :]) >= 2
    big_a = (G[None, :] - G[:, None]) >= 2
    mh, ma = pmf * big_h[None], pmf * big_a[None]
    out = pmf.copy()
    moved_h = mh * q
    moved_a = ma * q
    out -= moved_h + moved_a
    out[:, :-1, :] += moved_h[:, 1:, :]                         # mass at (h, a) -> (h - 1, a)
    out[:, :, :-1] += moved_a[:, :, 1:]                         # mass at (h, a) -> (h, a - 1)
    return out


def solve_q(pm_truth: np.ndarray, distort, target: float = 1.0) -> float:
    """Distortion probability for which the model `pm_truth` sits exactly at `target` times the margin (largest of the four |bias| / margin)."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        r = float(np.max(np.abs(population_bias(pm_truth, distort(pm_truth, mid))) / DELTA))
        lo, hi = (mid, hi) if r < target else (lo, mid)
    return (lo + hi) / 2


def opposite_direction_demo(ev, pm, reps: int, rng) -> dict:
    """Two WRONG methods on opposite sides of the truth, each exactly on the margin boundary: M_a = S1 with margins too small, M_b = S1 with margins too large (truth = S1 inflated or deflated halfway)."""
    q_i = solve_q(pm["S1"], inflate)
    q_d = solve_q(pm["S1"], deflate)
    truth = pm["S1"]
    ma, mb = deflate(truth, q_d), inflate(truth, q_i)                       # methods that are wrong in opposite directions by exactly the margin
    ordered = [("Ma", ma), ("Mb", mb)]
    res = {}
    for n in (1158, 2606, 4321):
        cnt = dict(sequence_as_proposed=0, holm=0, bonferroni=0, each=dict(Ma=0, Mb=0))
        for _ in range(reps):
            idx = rng.integers(0, len(ev), n)
            est, se = P.sample_actual(truth[idx], rng)
            ps = {name: tost_p(P.model_vec(arr[idx]) - est, se) for name, arr in ordered}
            cnt["each"]["Ma"] += ps["Ma"] <= ALPHA
            cnt["each"]["Mb"] += ps["Mb"] <= ALPHA
            cnt["sequence_as_proposed"] += (ps["Ma"] <= ALPHA) or (ps["Mb"] <= ALPHA)
            order = sorted(ps, key=ps.get)
            cnt["holm"] += ps[order[0]] <= ALPHA / 2
            cnt["bonferroni"] += (ps["Ma"] <= ALPHA / 2) or (ps["Mb"] <= ALPHA / 2)
        res[str(n)] = dict(false_acceptance_each_method_alone=dict(Ma=round(cnt["each"]["Ma"] / reps, 3), Mb=round(cnt["each"]["Mb"] / reps, 3)), sequence_as_proposed=round(cnt["sequence_as_proposed"] / reps, 3),
                           holm_over_methods=round(cnt["holm"] / reps, 3), bonferroni_over_methods=round(cnt["bonferroni"] / reps, 3))
    return dict(deflation_probability=round(q_d, 3), inflation_probability=round(q_i, 3), bias_vs_margin_ratio=dict(Ma=round(float(np.max(np.abs(population_bias(ma, truth)) / DELTA)), 3), Mb=round(float(np.max(np.abs(population_bias(mb, truth)) / DELTA)), 3)),
                results_by_sample_size=res)


def power_curve(ev, pm, rng, reps: int) -> dict:
    """Probability that the TRUE model (truth = S1, method S1) is accepted at level alpha, versus the number of matches, at the three candidate margins."""
    out = {}
    for name, d in {"0.10 / 0.05": np.array([0.10, 0.10, 0.05, 0.05]), "0.15 / 0.075": DELTA, "0.20 / 0.10": np.array([0.20, 0.20, 0.10, 0.10])}.items():
        row = {}
        for n in (686, 1158, 1464, 1800, 2200, 2606, 3300, 4321):
            acc = 0
            for _ in range(reps):
                idx = rng.integers(0, len(ev), n)
                est, se = P.sample_actual(pm["S1"][idx], rng)
                acc += tost_p(P.model_vec(pm["S1"][idx]) - est, se, d) <= ALPHA
            row[str(n)] = round(acc / reps, 3)
        out[name] = row
    return out


def template():
    df = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    fit, ev = df[df.dt < B.SPLIT], df[df.dt >= B.SPLIT].reset_index(drop=True)
    emp = scoreline.Empirical().fit(fit.league.values, (fit.lam_h - fit.lam_a).values, fit.hg.values, fit.ag.values)
    lams = {l: (float(g.hg.mean()), float(g.ag.mean())) for l, g in fit.groupby("league")}
    pm = {m: np.zeros((len(ev), B.K, B.K)) for m in METHODS}
    for lg in B.LEAGUES:
        idx = np.where(ev.league.values == lg)[0]
        e = ev.iloc[idx]
        for m in METHODS:
            pm[m][idx] = scoreline.build_pmf(m, e[["p1_H", "p1_D", "p1_A"]].values, e.lam_h.values, e.lam_a.values, lg, lams[lg], emp)[0]
    spread = {q: inflate(pm["S1"], q) for q in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40)}
    return ev, pm, spread


def tost_p(d: np.ndarray, se: np.ndarray, delta: np.ndarray = DELTA) -> float:
    """Intersection-union equivalence p-value of one method: the worst of the four statistics' two one-sided tests."""
    p = np.maximum(1 - norm.cdf((d + delta) / se), 1 - norm.cdf((delta - d) / se))
    return float(p.max())


def decide(ps: dict, procedure: str) -> list:
    """Methods accepted as equivalent by a procedure; ps: method -> p-value."""
    if procedure == "sequence_as_proposed":                 # S1; if not accepted S2; if not S3  (each at alpha)
        for m in METHODS:
            if ps[m] <= ALPHA:
                return [m]
        return []
    if procedure == "bonferroni_over_methods":
        return [m for m in METHODS if ps[m] <= ALPHA / 3]
    if procedure == "holm_over_methods":
        order = sorted(METHODS, key=lambda m: ps[m])
        acc = []
        for i, m in enumerate(order):
            if ps[m] <= ALPHA / (3 - i):
                acc.append(m)
            else:
                break
        return [m for m in METHODS if m in acc][:1]       # the first accepted method in the pre-set order is chosen
    raise ValueError(procedure)


def population_bias(pm_method: np.ndarray, truth: np.ndarray) -> np.ndarray:
    return P.model_vec(pm_method) - P.model_vec(truth)


def simulate(ev, pm, truth, n: int, reps: int, rng) -> dict:
    N = len(ev)
    res = {p: dict(false_accept=0, any_accept=0, accept_equivalent=0) for p in ("sequence_as_proposed", "bonferroni_over_methods", "holm_over_methods")}
    bias = {m: population_bias(pm[m], truth) for m in METHODS}
    equiv = {m: bool((np.abs(bias[m]) <= DELTA).all()) for m in METHODS}
    boundary = {m: float(np.max(np.abs(bias[m]) / DELTA)) for m in METHODS}            # 1.0 = exactly on the margin
    for _ in range(reps):
        idx = rng.integers(0, N, n)
        est, se = P.sample_actual(truth[idx], rng)
        ps = {m: tost_p(P.model_vec(pm[m][idx]) - est, se) for m in METHODS}
        for proc in res:
            acc = decide(ps, proc)
            res[proc]["any_accept"] += bool(acc)
            res[proc]["false_accept"] += any(not equiv[m] for m in acc)
            res[proc]["accept_equivalent"] += any(equiv[m] for m in acc)
    for proc in res:
        res[proc] = {k: round(v / reps, 3) for k, v in res[proc].items()}
    return dict(true_bias_vs_margin_ratio=boundary, truly_equivalent=equiv, procedures=res)


def find_boundary_k(pm, spread) -> float:
    """Interpolate the spread factor for which the S1 model sits exactly on the margin (largest |bias| / margin = 1)."""
    pts = [(0.0, population_bias(pm["S1"], pm["S1"]))] + [(k, population_bias(pm["S1"], v)) for k, v in sorted(spread.items())]
    ratios = [(k, float(np.max(np.abs(b) / DELTA))) for k, b in pts]
    return ratios


def league_screen(ev, pm, truth, n: int, reps: int, rng) -> dict:
    """Holm screen over 4 statistics x 5 leagues: how often is a league flagged (detectable AND larger than the margin)?"""
    z_h = norm.ppf(1 - ALPHA / 20 / 2)
    flagged_any = 0
    per_league = {lg: 0 for lg in B.LEAGUES}
    for _ in range(reps):
        idx = rng.integers(0, len(ev), n)
        any_f = False
        for lg in B.LEAGUES:
            sub = idx[ev.league.values[idx] == lg]
            est, se = P.sample_actual(truth[sub], rng)
            d = P.model_vec(pm["S1"][sub]) - est
            if ((np.abs(d) / se > z_h) & (np.abs(d) > DELTA)).any():
                per_league[lg] += 1
                any_f = True
        flagged_any += any_f
    return dict(any_league_flagged=round(flagged_any / reps, 3), by_league={k: round(v / reps, 3) for k, v in per_league.items()})


def run(reps: int = 800, seed: int = 31) -> dict:
    ev, pm, spread = template()
    ratios = find_boundary_k(pm, spread)
    rng = np.random.default_rng(seed)
    out = dict(reps=reps, seed=seed, margins=DELTA.tolist(), inflation_bias_table=[dict(inflation_probability=k, S1_worst_bias_over_margin=round(r, 2)) for k, r in ratios], scenarios={})
    k_b = min(spread, key=lambda k: abs(dict(ratios)[k] - 1.0))                          # the tabulated inflation closest to the margin boundary for S1
    scenarios = {"truth = S1 (S1 exactly right)": pm["S1"], "truth = S3 (S3 exactly right)": pm["S3"], f"truth = winners score +1 goal with probability {k_b} (S1 on the margin boundary)": spread[k_b],
                 "truth = winners score +1 goal with probability 0.40 (every method far outside the margin)": spread[0.40]}
    for name, truth in scenarios.items():
        out["scenarios"][name] = {str(n): simulate(ev, pm, truth, n, reps, rng) for n in (686, 1158, 2606, 4321)}
    out["opposite_direction_demo"] = opposite_direction_demo(ev, pm, 1500, rng)
    out["power_curve_correct_model_single_method_alpha_0.05"] = power_curve(ev, pm, rng, 500)
    out["holm_league_screen_false_flags_when_S1_is_exactly_right"] = {str(n): league_screen(ev, pm, pm["S1"], n, 300, rng) for n in (1158, 4321)}
    out["holm_league_screen_when_S1_is_at_the_boundary"] = {str(n): league_screen(ev, pm, spread[k_b], n, 300, rng) for n in (1158, 4321)}
    return out


if __name__ == "__main__":
    r = run()
    (OUT / "m4_protocol_review.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps(r["inflation_bias_table"]))
    for s, v in r["scenarios"].items():
        print("\n", s)
        for n, x in v.items():
            print("  n=", n, "bias/margin", x["true_bias_vs_margin_ratio"], "equiv", x["truly_equivalent"])
            for p, y in x["procedures"].items():
                print("      ", p, y)
    print(json.dumps({k: r[k] for k in r if k.startswith(("holm", "opposite", "power"))}, indent=1))
