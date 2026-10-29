"""Experimental points-only simulation (approved 2026-10-25, option O5).

Only the outcome of each remaining fixture is simulated (home win, draw, away win, from the frozen club v1 probabilities) and awarded 3 / 1 / 0 points.
No score is generated and no tie-break is applied, so nothing here depends on the scoreline question: the output is each club's distribution of final POINTS
(expected value, 10-90% interval, histogram). It deliberately does not rank clubs, so there are no title, top-four, relegation or finishing-position probabilities.
"""
import numpy as np

WIN, DRAW = 3, 1


def simulate_points(base_points: np.ndarray, fix_home: np.ndarray, fix_away: np.ndarray, probs: np.ndarray, n: int, seed: int) -> np.ndarray:
    """probs: [F, 3] home / draw / away probabilities. Returns final points [n, T]. Same seed and inputs: identical output."""
    T, F = len(base_points), len(fix_home)
    pts = np.repeat(np.asarray(base_points, dtype=np.int64)[None, :], n, axis=0)
    if F == 0:
        return pts
    p = np.clip(np.asarray(probs, dtype=float), 0.0, None)
    p = p / p.sum(axis=1, keepdims=True)
    cdf = np.cumsum(p, axis=1)
    cdf[:, -1] = 1.0
    u = np.random.default_rng([seed, 2]).random((n, F))
    outcome = (u[:, :, None] > cdf[None, :, :2]).sum(axis=2)                      # 0 home win, 1 draw, 2 away win
    hp = np.where(outcome == 0, WIN, np.where(outcome == 1, DRAW, 0)).astype(np.int64)
    ap = np.where(outcome == 2, WIN, np.where(outcome == 1, DRAW, 0)).astype(np.int64)
    Hm = np.zeros((F, T), dtype=np.int64)
    Am = np.zeros((F, T), dtype=np.int64)
    Hm[np.arange(F), fix_home] = 1
    Am[np.arange(F), fix_away] = 1
    return pts + hp @ Hm + ap @ Am


def summarize_points(points: np.ndarray, ids: list, names: list, base_points: np.ndarray, remaining: np.ndarray, seed: int) -> dict:
    n, T = points.shape
    teams = []
    for t in np.argsort(-points.mean(axis=0), kind="stable"):
        col = points[:, t]
        lo, hi = int(col.min()), int(col.max())
        counts = np.bincount(col - lo, minlength=hi - lo + 1) / n
        teams.append(dict(entity_id=ids[t], name=names[t], current_points=int(base_points[t]), remaining_fixtures=int(remaining[t]),
                          expected_points=float(col.mean()), points_sd=float(col.std()), points_p10=float(np.percentile(col, 10)), points_p25=float(np.percentile(col, 25)),
                          points_median=float(np.percentile(col, 50)), points_p75=float(np.percentile(col, 75)), points_p90=float(np.percentile(col, 90)),
                          points_min=lo, points_max=hi, distribution=dict(first_points=lo, probabilities=[float(x) for x in counts])))
    return dict(n=n, seed=seed, teams=teams, standard_error_of_a_probability_max=float(0.5 / np.sqrt(n)),
                ordering="clubs are listed by expected final points only; no tie-break is applied and no finishing position is implied")
