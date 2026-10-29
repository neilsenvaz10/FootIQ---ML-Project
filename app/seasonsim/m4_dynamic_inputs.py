"""Inputs for the offline dynamic-strength prototype: for each historical cut-off, the frozen club v1 probabilities of every remaining fixture, computed from results
strictly before the cut-off, plus every club's v1 Elo at the cut-off and the realised final points (used for scoring only).

Development seasons (parameter choice, v1 in-sample or validation data): 2020-21, 2021-22, 2022-23, 2023-24.
Evaluation seasons (frozen v1 out-of-sample; NEVER used to choose a parameter): 2024-25, 2025-26.
Run against a private copy:  FOOTIQ_STORE_PATH=<copy> python app/seasonsim/m4_dynamic_inputs.py
"""
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import predict  # noqa: E402
from seasonsim import backtest  # noqa: E402
from store import db as store_db  # noqa: E402

OUT = backtest.OUT
DEV = ["2020-21", "2021-22", "2022-23", "2023-24"]
EVAL = ["2024-25", "2025-26"]


def cutoffs(season: str) -> list[str]:
    y = int(season[:4])
    return [f"{y}-11-01", f"{y + 1}-01-01", f"{y + 1}-03-01"]


def build_cutoff(V, conn, meta, season: str, cutoff: str) -> list[dict]:
    lg, _, _ = predict._club_runtime()
    c = pd.Timestamp(cutoff)
    frames, fx = {}, []
    for key, comp in backtest.LEAGUES.items():
        f = backtest.season_frames(conn, key, season)
        frames[key] = f
        rem = f[~((f.dt < c) & f.status.isin(["completed", "awarded"]))]
        fx.append(pd.DataFrame(dict(fixture_id=rem.record_id.values, dt=rem.dt.values, h=rem.h.values, a=rem.a.values, comp=comp, season=meta.loc[rem.record_id, "season_corrected"].values, tier=meta.loc[rem.record_id, "tier"].values)))
    fx = pd.concat(fx, ignore_index=True)
    known = V[V.dt < c]
    F2, F1 = lg.features_for(known, fx)
    F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
    v2m, v1m, v1prep, v1elo = predict._club_models()
    p1 = lg.v1_proba(v1m, v1prep, F1)
    fx = fx.assign(p_H=p1[:, 0], p_D=p1[:, 1], p_A=p1[:, 2], elo_h=F1.home_elo.values, elo_a=F1.away_elo.values)
    out = []
    for key in backtest.LEAGUES:
        f = frames[key]
        teams = sorted(set(f.h) | set(f.a))
        idx = {t: i for i, t in enumerate(teams)}
        played = f[(f.dt < c) & f.status.isin(["completed", "awarded"])]
        base = np.zeros(len(teams))
        for r in played.itertuples():
            base[idx[r.h]] += 3 if r.hg > r.ag else 1 if r.hg == r.ag else 0
            base[idx[r.a]] += 3 if r.ag > r.hg else 1 if r.hg == r.ag else 0
        real = backtest.real_final(f, teams)["points"]
        rem = fx[fx.fixture_id.isin(f.record_id)].merge(f[["record_id"]], left_on="fixture_id", right_on="record_id")
        elo = {}
        for r in rem.itertuples():
            elo.setdefault(r.h, r.elo_h)
            elo.setdefault(r.a, r.elo_a)
        out.append(dict(season=season, cutoff=cutoff, league=key, teams=teams, base_points=base, real_points=real, fixtures=rem[["fixture_id", "dt", "h", "a", "p_H", "p_D", "p_A", "elo_h", "elo_a"]].reset_index(drop=True),
                        elo=np.array([elo.get(t, np.nan) for t in teams]), role="development" if season in DEV else "evaluation"))
    return out


def main() -> None:
    lg, V, tiers = predict._club_runtime()
    conn = store_db.connect(readonly=True)
    meta = V.set_index("record_id")[["season_corrected", "tier"]]
    res = []
    t0 = time.time()
    try:
        for season in DEV + EVAL:
            for cutoff in cutoffs(season):
                res += build_cutoff(V, conn, meta, season, cutoff)
                print("done", season, cutoff, f"{time.time() - t0:.0f}s", flush=True)
                with open(OUT / "dyn_inputs.pkl", "wb") as fh:
                    pickle.dump(res, fh)
    finally:
        conn.close()
    print("cases:", len(res))


if __name__ == "__main__":
    main()
