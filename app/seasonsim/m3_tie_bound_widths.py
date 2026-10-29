"""Planning analysis (not a product feature): how informative would position probabilities be if they needed NO scores, using only the simulated final POINTS?

For every club and band, a "lower" and an "upper" probability: the club surely / possibly reaches the band when clubs level on points are counted as worse / better than it.
The width (upper - lower) is the probability mass that only goal-based tie-breaks (or play-offs) could decide. No scoreline method, no tie-break rule and no coin is used.
Run against a private copy of the store:  FOOTIQ_STORE_PATH=<copy> python app/seasonsim/m3_tie_bound_widths.py
"""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import eligibility, pointsonly, service  # noqa: E402
from store import db as store_db  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"
BANDS = {"BUNDESLIGA": dict(title=(1, 1), top4=(1, 4), relegation=(17, 18), relegation_playoff=(16, 16)), "LALIGA": dict(title=(1, 1), top4=(1, 4), relegation=(18, 20))}


def points_matrix(key: str, n: int, seed: int):
    conn = store_db.connect(readonly=True)
    try:
        rows = service._season_rows(conn, key, "2026-27")
        played = [r for r in rows if r["status"] in eligibility.COMPLETED and r["hg"] is not None]
        pid = {r["record_id"] for r in played}
        rem = [r for r in rows if r["record_id"] not in pid]
        probs, _ = service.live_probabilities(conn, key, "2026-27", rem)
        teams = sorted({r["h"] for r in rows} | {r["a"] for r in rows})
        idx = {t: i for i, t in enumerate(teams)}
        base = np.zeros(len(teams), dtype=np.int64)
        for r in played:
            base[idx[r["h"]]] += 3 if r["hg"] > r["ag"] else 1 if r["hg"] == r["ag"] else 0
            base[idx[r["a"]]] += 3 if r["ag"] > r["hg"] else 1 if r["hg"] == r["ag"] else 0
        fh = np.array([idx[r["h"]] for r in rem]); fa = np.array([idx[r["a"]] for r in rem])
        pr = probs.set_index("record_id").loc[[r["record_id"] for r in rem]][["p1_H", "p1_D", "p1_A"]].values
        return pointsonly.simulate_points(base, fh, fa, pr, n, seed), service._names(conn, teams), teams
    finally:
        conn.close()


def bounds(points: np.ndarray, lo: int, hi: int) -> tuple:
    N, T = points.shape
    greater = (points[:, :, None] < points[:, None, :]).sum(axis=2)                       # clubs strictly above me
    geq = (points[:, :, None] <= points[:, None, :]).sum(axis=2) - 1                        # other clubs level or above me
    best, worst = greater + 1, geq + 1                                                      # best / worst possible position
    low = ((worst >= lo) & (worst <= hi)).mean(axis=0)                                      # surely inside the band even if every tie goes against me ... (inside both ends)
    sure = ((best >= lo) & (worst <= hi)).mean(axis=0)
    possible = ((worst >= lo) & (best <= hi)).mean(axis=0)
    return sure, possible


def run(n: int = 10000, seed: int = 11) -> dict:
    out = {}
    for key, bands in BANDS.items():
        pts, names, teams = points_matrix(key, n, seed)
        res = {}
        for b, (lo, hi) in bands.items():
            sure, poss = bounds(pts, lo, hi)
            w = poss - sure
            res[b] = dict(mean_width=round(float(w.mean()), 4), max_width=round(float(w.max()), 4), clubs_with_width_over_5pp=int((w > 0.05).sum()), clubs_with_possible_over_1pp=int((poss > 0.01).sum()),
                          example=[dict(club=names.get(teams[i], teams[i]), surely=round(float(sure[i]), 3), possibly=round(float(poss[i]), 3)) for i in np.argsort(-poss)[:3]])
        out[key] = res
    return out


if __name__ == "__main__":
    r = run()
    (OUT / "m3_tie_bound_widths.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps(r, indent=1))
