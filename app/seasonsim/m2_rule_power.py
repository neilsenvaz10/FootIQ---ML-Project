"""How demanding is the predeclared M2a rule? If the model were EXACTLY true (scores really drawn from its own distribution), how often would it still fail?

For each league the evaluation matches' S1 score distributions are treated as the truth, scores are drawn from them, and the predeclared criteria (C1, C2) are applied
to the drawn "actual" statistics. Nothing here changes the rule or reads any new result; it only measures the rule's sampling noise.
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
from seasonsim.engine import K  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"


def run(reps: int = 300, seed: int = 11) -> dict:
    df = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    ev = df[df.dt >= B.SPLIT]
    rng = np.random.default_rng(seed)
    per_league = {}
    ok = np.ones(reps, dtype=bool)
    for lg in B.LEAGUES:
        e = ev[ev.league == lg]
        pmf = scoreline.conditional_poisson(e[["p1_H", "p1_D", "p1_A"]].values, e.lam_h.values, e.lam_a.values)
        model = B.model_stats(pmf)
        flat = np.cumsum(pmf.reshape(len(e), -1), axis=1)
        passes = []
        for _ in range(reps):
            u = rng.random(len(e))[:, None]
            idx = (u > flat).sum(axis=1).clip(0, K * K - 1)
            hg, ag = idx // K, idx % K
            act = B.actual_stats(hg, ag)
            c1 = abs(model["mean_margin_home_win"] - act["mean_margin_home_win"]) <= B.TOL_MARGIN and abs(model["mean_margin_away_win"] - act["mean_margin_away_win"]) <= B.TOL_MARGIN
            c2 = abs(model["share_one_goal_home_win"] - act["share_one_goal_home_win"]) <= B.TOL_SHARE and abs(model["share_one_goal_away_win"] - act["share_one_goal_away_win"]) <= B.TOL_SHARE
            passes.append(c1 and c2)
        passes = np.array(passes)
        per_league[lg] = dict(n=int(len(e)), pass_probability_if_model_exactly_true=float(passes.mean()))
        ok &= passes
    return dict(reps=reps, per_league=per_league, probability_all_five_leagues_pass_if_model_exactly_true=float(ok.mean()))


if __name__ == "__main__":
    r = run()
    (OUT / "m2_rule_power.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps(r, indent=1))
