"""Offline run of the position-bounds prototype on a PRIVATE COPY of the store (never the production file; nothing is saved, no API or UI is involved).

    FOOTIQ_STORE_PATH=<copy> python app/seasonsim/m4_bounds_report.py
Reports, for the Bundesliga and La Liga 2026-27 and the bands of their verified rule profiles, the guaranteed / possible / unresolved probabilities with and without using the
known results (naive = every tie on points is left open), and the share of simulations in which a tie group is fully decided.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import eligibility, pointbounds, rules, service  # noqa: E402
from seasonsim.engine import K, SeasonInput  # noqa: E402
from store import db as store_db  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"


def season_input(key: str, season: str = "2026-27"):
    conn = store_db.connect(readonly=True)
    try:
        rows = service._season_rows(conn, key, season)
        played = [r for r in rows if r["status"] in eligibility.COMPLETED and r["hg"] is not None]
        pid = {r["record_id"] for r in played}
        rem = [r for r in rows if r["record_id"] not in pid]
        probs, _ = service.live_probabilities(conn, key, season, rem)
        teams = sorted({r["h"] for r in rows} | {r["a"] for r in rows})
        idx = {t: i for i, t in enumerate(teams)}
        names = service._names(conn, teams)
        inp = SeasonInput(teams=teams, names=[names.get(t, t) for t in teams], played_home=np.array([idx[r["h"]] for r in played]), played_away=np.array([idx[r["a"]] for r in played]),
                          played_hg=np.array([int(r["hg"]) for r in played]), played_ag=np.array([int(r["ag"]) for r in played]), fix_home=np.array([idx[r["h"]] for r in rem]),
                          fix_away=np.array([idx[r["a"]] for r in rem]), pmf=np.zeros((len(rem), K, K)))
        pr = probs.set_index("record_id").loc[[r["record_id"] for r in rem]][["p1_H", "p1_D", "p1_A"]].values
        return inp, pr
    finally:
        conn.close()


def run(n: int = 10000, seed: int = 11) -> dict:
    out = {}
    for key in ("BUNDESLIGA", "LALIGA"):
        inp, pr = season_input(key)
        profile = rules.get_profile(key, "2026-27")
        oc = pointbounds.draw_outcomes(pr, n, seed)
        t0 = time.time()
        ref = pointbounds.position_bounds(inp, profile, oc)
        t1 = time.time()
        nai = pointbounds.position_bounds(inp, profile, oc, use_known_information=False)
        sr, sn = pointbounds.band_summary(ref, profile, inp), pointbounds.band_summary(nai, profile, inp)
        res = dict(simulations=n, seconds_refined=round(t1 - t0, 1), tie_groups_refined=ref.stats["tie_groups"], tie_groups_fully_decided_refined=ref.stats["fully_decided_tie_groups"], bands={})
        for band in sr:
            res["bands"][band] = dict(positions=sr[band]["positions"], mean_unresolved_refined=round(sr[band]["mean_unresolved"], 4), mean_unresolved_naive=round(sn[band]["mean_unresolved"], 4),
                                      max_unresolved_refined=round(sr[band]["max_unresolved"], 4), max_unresolved_naive=round(sn[band]["max_unresolved"], 4),
                                      top_clubs=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items()} for c in sr[band]["clubs"][:4]])
        out[key] = res
    return out


if __name__ == "__main__":
    r = run()
    (OUT / "m4_bounds_report.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    for k, v in r.items():
        print(k, {a: v[a] for a in ("seconds_refined", "tie_groups_refined", "tie_groups_fully_decided_refined")})
        for b, x in v["bands"].items():
            print("  ", b, x["positions"], "mean unresolved refined/naive:", x["mean_unresolved_refined"], x["mean_unresolved_naive"], "max:", x["max_unresolved_refined"], x["max_unresolved_naive"])
