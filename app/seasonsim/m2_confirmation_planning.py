"""Planning numbers for the proposed confirmation protocol (nothing here evaluates any scoreline method on any result).

1. Matches needed for the pooled equivalence test to accept a correct model with 90% power, for three practical margins.
2. How long forward data take to accumulate for different scopes, and how large the independent European sample is.
3. Smallest between-league difference in a statistic that a heterogeneity test could detect (relevant to league-specific methods).
Uses only the models' own expected distributions (S1 as a stand-in for "a correct model") to measure sampling noise.
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
FIXTURES_PER_SEASON = {"BUNDESLIGA": 306, "LALIGA": 380, "EPL": 380, "SERIEA": 380, "LIGUE1": 306}


def run() -> dict:
    df = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    ev = df[df.dt >= B.SPLIT]
    rng = np.random.default_rng(3)
    res = {}
    # --- noise per square-root of matches (pooled over leagues, one draw of the real size) and per league
    per_league_se, c_pooled = {}, None
    for lg in B.LEAGUES:
        e = ev[ev.league == lg]
        pmf = scoreline.conditional_poisson(e[["p1_H", "p1_D", "p1_A"]].values, e.lam_h.values, e.lam_a.values)
        ses = np.mean([P.sample_actual(pmf, rng)[1] for _ in range(60)], axis=0)
        per_league_se[lg] = dict(n=int(len(e)), se=dict(zip(P.KEYS, [float(x) for x in ses])), c=dict(zip(P.KEYS, [float(x * np.sqrt(len(e))) for x in ses])))
    c = {k: float(np.mean([v["c"][k] for v in per_league_se.values()])) for k in P.KEYS}
    res["standard_error_times_sqrt_n"] = {k: round(v, 3) for k, v in c.items()}
    # --- 1. sample size for 90% power of the pooled equivalence test (90% CI inside +-margin, alpha 0.05 per side), true deviation 0
    z = norm.ppf(0.95) + norm.ppf(0.90)
    res["matches_needed_for_90pct_power_if_the_model_is_exactly_right"] = {}
    for name, (dm, ds) in {"margins 0.10 goals / 0.05 share": (0.10, 0.05), "margins 0.15 goals / 0.075 share": (0.15, 0.075), "margins 0.20 goals / 0.10 share": (0.20, 0.10)}.items():
        need = {k: (z * c[k] / (dm if k.startswith("margin") else ds)) ** 2 for k in P.KEYS}
        res["matches_needed_for_90pct_power_if_the_model_is_exactly_right"][name] = dict(by_statistic={k: int(np.ceil(v)) for k, v in need.items()}, binding=int(np.ceil(max(need.values()))))
    # --- 2. accumulation of independent data
    seasons = {lg: n for lg, n in FIXTURES_PER_SEASON.items()}
    scopes = {"Bundesliga + La Liga": ["BUNDESLIGA", "LALIGA"], "five leagues": list(seasons)}
    res["matches_per_season"] = {k: int(sum(seasons[x] for x in v)) for k, v in scopes.items()}
    res["forward_matches_already_available_after_2026-09-20"] = {"Bundesliga": 25, "La Liga": 20, "Premier League": 10, "Serie A": 0, "Ligue 1": 0}
    # --- 3. detectability of between-league differences: smallest true difference detected with 80% power at 5% two-sided (two leagues, equal size n each)
    mdd = {}
    for n_each in (380, 700, 1400):
        mdd[str(n_each)] = {k: round(float((norm.ppf(0.975) + norm.ppf(0.80)) * np.sqrt(2) * c[k] / np.sqrt(n_each)), 3) for k in P.KEYS}
    res["smallest_detectable_difference_between_two_leagues_80pct_power"] = mdd
    res["per_league_standard_errors_at_evaluation_size"] = per_league_se
    return res


if __name__ == "__main__":
    r = run()
    (OUT / "m2_confirmation_planning.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "per_league_standard_errors_at_evaluation_size"}, indent=1))
