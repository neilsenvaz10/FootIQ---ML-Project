"""How good is the Level-2 shortcut (Elo offsets tilting the cut-off probabilities) compared with the exact Level-3 computation (re-featurising with the project's state machines after a hypothetical result)?

For a handful of clubs at the 2025-03-01 cut-off: add ONE hypothetical completed match (club wins 2-0, or loses 0-2, at home against its next opponent, dated the day before the cut-off), recompute the frozen
v1 probabilities of that club's LATER fixtures exactly (features_for with the extra result), and compare the change with the tilt formula applied to the Elo update the extra result causes.
Offline, private copy, frozen models only read. Output: data/supervised/phase3/dyn_level3.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import predict  # noqa: E402
from seasonsim import backtest, dynamic  # noqa: E402
from store import db as store_db  # noqa: E402

OUT = backtest.OUT
CUT = pd.Timestamp("2025-03-01")


def probs(lg, V_known, fx):
    F2, F1 = lg.features_for(V_known, fx)
    F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
    v2m, v1m, v1prep, v1elo = predict._club_models()
    return lg.v1_proba(v1m, v1prep, F1), F1


def main() -> dict:
    lg, V, tiers = predict._club_runtime()
    conn = store_db.connect(readonly=True)
    meta = V.set_index("record_id")[["season_corrected", "tier"]]
    comp = backtest.LEAGUES["BUNDESLIGA"]
    f = backtest.season_frames(conn, "BUNDESLIGA", "2024-25")
    conn.close()
    rem = f[f.dt >= CUT].sort_values("dt")
    known = V[V.dt < CUT]
    K, HA = dynamic.elo_constants()
    sl = dynamic.tilt_slopes()
    teams = sorted(set(rem.h) | set(rem.a))[:6]
    template = known[known.competition_id == comp].iloc[[-1]].copy()
    rows = []
    for x in teams:
        mine = rem[(rem.h == x) | (rem.a == x)].head(4)
        first = mine.iloc[0]
        opp = first.a if first.h == x else first.h
        later = mine.iloc[1:]
        if later.empty:
            continue
        fx = pd.DataFrame(dict(fixture_id=later.record_id.values, dt=later.dt.values, h=later.h.values, a=later.a.values, comp=comp, season=meta.loc[later.record_id, "season_corrected"].values, tier=meta.loc[later.record_id, "tier"].values))
        p0, F0 = probs(lg, known, fx)
        for result, (gh, ga) in (("win 2-0", (2, 0)), ("loss 0-2", (0, 2))):
            syn = template.copy()
            syn["record_id"], syn["dt"], syn["home_entity_id"], syn["away_entity_id"] = "SYN:x", CUT - pd.Timedelta(days=1), x, opp
            syn["gh"], syn["ga"], syn["rated"] = gh, ga, True
            p1, F1 = probs(lg, pd.concat([known, syn], ignore_index=True), fx)
            e0x = float(F0.home_elo.iloc[0] if later.iloc[0].h == x else F0.away_elo.iloc[0])
            e0o_row = rem[(rem.h == opp) | (rem.a == opp)].iloc[0]
            # Elo of both clubs from a probe featurisation of their next fixtures is not needed: use the Elo rule on the clubs' cut-off ratings read from the same feature frames
            elo_x = e0x
            probe = pd.DataFrame(dict(fixture_id=[first.record_id], dt=[first["dt"]], h=[first.h], a=[first.a], comp=comp, season=meta.loc[[first.record_id], "season_corrected"].values, tier=meta.loc[[first.record_id], "tier"].values))
            _, Fp = probs(lg, known, probe)
            e_h, e_a = float(Fp.home_elo.iloc[0]), float(Fp.away_elo.iloc[0])
            # the hypothetical match is home = x, away = opp
            exp_h = 1.0 / (1.0 + 10.0 ** (-((e_h if first.h == x else e_a) + HA - (e_a if first.h == x else e_h)) / 400.0)) if True else None
            s = 1.0 if gh > ga else 0.0
            gd = abs(gh - ga)
            mult = 1.0 if gd <= 1 else (1.5 if gd == 2 else (11.0 + gd) / 8.0)
            d_x = K * mult * (s - exp_h)
            d_o = -d_x
            for i, r in enumerate(later.itertuples()):
                dh = d_x if r.h == x else (d_o if r.h == opp else 0.0)
                da = d_x if r.a == x else (d_o if r.a == opp else 0.0)
                logit = np.log(p0[i]) + sl["home"] * dh + sl["away"] * da
                t = np.exp(logit - logit.max())
                t /= t.sum()
                rows.append(dict(club=x, hypothetical=result, fixture=r.record_id, elo_change_of_club=round(d_x, 2), exact_change=(p1[i] - p0[i]).tolist(), tilt_change=(t - p0[i]).tolist()))
        print("done", x, flush=True)
    ex = np.array([r["exact_change"] for r in rows])
    ti = np.array([r["tilt_change"] for r in rows])
    slope = float((ex * ti).sum() / (ti * ti).sum())
    res = dict(comparisons=len(rows), mean_abs_exact_change=float(np.abs(ex).mean()), mean_abs_tilt_change=float(np.abs(ti).mean()), mean_abs_difference=float(np.abs(ex - ti).mean()),
               exact_over_tilt_slope=slope, correlation=float(np.corrcoef(ex.ravel(), ti.ravel())[0, 1]), share_of_exact_change_explained_by_tilt=float(1 - ((ex - ti) ** 2).sum() / (ex ** 2).sum()),
               examples=rows[:6])
    (OUT / "dyn_level3.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    print(json.dumps({k: v for k, v in main().items() if k != "examples"}, indent=1))
