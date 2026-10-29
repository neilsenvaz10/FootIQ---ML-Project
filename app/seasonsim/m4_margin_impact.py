"""Are the proposed equivalence margins (0.15 goals, 0.075 share) practically acceptable for league-position outcomes?

What-if experiment on a PRIVATE COPY of the store (never saved, not a forecast, not a method selection): take the current Bundesliga and La Liga 2026-27 situation, build the conditional-Poisson (S1)
score distribution of every remaining fixture, and compare it with distorted copies whose winning margins are too large (winners score one more goal with probability q) or too small
(winners of 2+ goal margins score one fewer), by a measured amount in goals. Both versions are simulated with the SAME uniform random numbers and ranked with the league's real tie-break
procedure, so any difference in the probabilities comes from the distortion alone.
Reported for each distortion: the bias in the mean winning margin and in the one-goal share (measured on these fixtures), the largest change in any club's title / top-four / relegation probability
and the share of simulated seasons in which at least one club ends in a different position.
    FOOTIQ_STORE_PATH=<copy> python app/seasonsim/m4_margin_impact.py
"""
import json
import sys
from pathlib import Path

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from seasonsim import engine, eligibility, m4_protocol_review as R, m2_benchmark as B, rules, scoreline, service  # noqa: E402
from seasonsim.engine import SeasonInput  # noqa: E402
from store import db as store_db  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"


def coupled_sampler(pmf: np.ndarray, n: int, rng: np.random.Generator):
    """Draw the win/draw/loss outcome first and the score second, with two separate streams of uniform numbers, so that two score distributions with the SAME outcome probabilities produce
    identical outcomes (identical points) and differ only in the scores (goal difference, goals scored)."""
    F = pmf.shape[0]
    K = pmf.shape[1]
    G = np.arange(K)
    masks = [(G[:, None] > G[None, :]), (G[:, None] == G[None, :]), (G[:, None] < G[None, :])]
    u1, u2 = rng.random((n, F)), rng.random((n, F))
    sh = np.empty((n, F), dtype=np.int8)
    sa = np.empty((n, F), dtype=np.int8)
    for f in range(F):
        marg = np.array([pmf[f][m].sum() for m in masks])
        ocdf = np.cumsum(marg / marg.sum())
        ocdf[-1] = 1.0
        o = np.minimum(np.searchsorted(ocdf, u1[:, f], side="right"), 2)
        for k, m in enumerate(masks):
            sel = np.where(o == k)[0]
            if not len(sel):
                continue
            cond = (pmf[f] * m).reshape(-1)
            cdf = np.cumsum(cond / cond.sum())
            cdf[-1] = 1.0
            idx = np.minimum(np.searchsorted(cdf, u2[sel, f], side="right"), K * K - 1)
            sh[sel, f], sa[sel, f] = idx // K, idx % K
    return sh, sa


def base_inputs(key: str):
    conn = store_db.connect(readonly=True)
    try:
        rows = service._season_rows(conn, key, "2026-27")
        rem = [r for r in rows if not (r["status"] in eligibility.COMPLETED and r["hg"] is not None)]
        probs, _ = service.live_probabilities(conn, key, "2026-27", rem)
        inp, info, rem = service.build_input(conn, key, "2026-27", probs, rows, "S1")
        return inp
    finally:
        conn.close()


def late_season_inputs(key: str, cutoff: str, season: str = "2025-26"):
    """A late-season state of a COMPLETED season (pre-match probabilities and expected goals of the matches still to be played at `cutoff`), for the sensitivity experiment only."""
    import pandas as pd

    m = pd.read_pickle(OUT / "m2_matches.pkl").dropna(subset=["hg", "ag"])
    m = m[(m.league == key) & (m.season == season)]
    c = pd.Timestamp(cutoff)
    played, rem = m[m.dt < c], m[m.dt >= c]
    teams = sorted(set(m.home) | set(m.away))
    idx = {t: i for i, t in enumerate(teams)}
    pmf, _ = scoreline.build_pmf("S1", rem[["p1_H", "p1_D", "p1_A"]].values, rem.lam_h.values, rem.lam_a.values, key)
    return SeasonInput(teams=teams, names=teams, played_home=played.home.map(idx).values.astype(int), played_away=played.away.map(idx).values.astype(int), played_hg=played.hg.values.astype(int),
                       played_ag=played.ag.values.astype(int), fix_home=rem.home.map(idx).values.astype(int), fix_away=rem.away.map(idx).values.astype(int), pmf=pmf), len(rem)


def band_values(summary: dict) -> dict:
    out = {}
    for name in ("title", "top4", "relegation"):
        out[name] = np.array([0.5 * ((t[f"p_{name}_low"] or 0.0) + (t[f"p_{name}_high"] or 0.0)) if t.get(f"p_{name}_low") is not None else np.nan for t in summary["teams"]])
    return out


def distort_table(inp, profile, n: int, seed: int) -> list:
    ref = engine.simulate(inp, profile, n, seed)
    sref = engine.summarize(ref, inp, profile)
    bref = band_values(sref)
    res = []
    for label, make in (("winners +1 goal, probability 0.15 (margin bias about +0.15)", lambda p: R.inflate(p, 0.15)), ("winners +1 goal, probability 0.30", lambda p: R.inflate(p, 0.30)), ("big wins shrink, probability 0.30 (margin bias about -0.18)", lambda p: R.deflate(p, 0.30))):
        pmf2 = make(inp.pmf)
        inp2 = SeasonInput(**{**inp.__dict__, "pmf": pmf2})
        r2 = engine.simulate(inp2, profile, n, seed)
        s2 = engine.summarize(r2, inp2, profile)
        b2 = band_values(s2)
        ch = {}
        for name in ("title", "top4", "relegation"):
            d = {sref["teams"][i]["entity_id"]: bref[name][i] for i in range(len(sref["teams"]))}
            d2 = {s2["teams"][i]["entity_id"]: b2[name][i] for i in range(len(s2["teams"]))}
            ch[name] = round(max(abs(d[k] - d2[k]) for k in d if not (np.isnan(d[k]) or np.isnan(d2[k]))), 4)
        res.append(dict(distortion=label, bias_margin_home_win=round(B.model_stats(pmf2)["mean_margin_home_win"] - B.model_stats(inp.pmf)["mean_margin_home_win"], 3), max_change_title=ch["title"], max_change_top4=ch["top4"],
                        max_change_relegation=ch["relegation"], share_of_seasons_with_any_position_change=round(float((ref.pos != r2.pos).any(axis=1).mean()), 3), mean_clubs_changing_position=round(float((ref.pos != r2.pos).sum(axis=1).mean()), 3)))
    return res


def run_late(n: int = 6000, seed: int = 17) -> dict:
    out = {}
    original = engine._sample_scores
    engine._sample_scores = coupled_sampler
    try:
        for key, cutoffs in (("BUNDESLIGA", ("2026-04-10", "2026-05-01")), ("LALIGA", ("2026-04-18", "2026-05-09"))):
            for c in cutoffs:
                inp, left = late_season_inputs(key, c)
                out[f"{key} {c} ({left} matches left)"] = distort_table(inp, rules.get_profile(key, "2026-27"), n, seed)
    finally:
        engine._sample_scores = original
    return out


def run(n: int = 6000, seed: int = 17) -> dict:
    out = {}
    original = engine._sample_scores
    engine._sample_scores = coupled_sampler                                    # restored in the finally below
    for key in ("BUNDESLIGA", "LALIGA"):
        inp = base_inputs(key)
        profile = rules.get_profile(key, "2026-27")
        names = [t for t in inp.names]
        ref = engine.simulate(inp, profile, n, seed)
        sref = engine.summarize(ref, inp, profile)
        bref = band_values(sref)
        res = []
        for label, make in (("winners score +1 goal with probability 0.05", lambda p: R.inflate(p, 0.05)), ("... 0.10", lambda p: R.inflate(p, 0.10)), ("... 0.15", lambda p: R.inflate(p, 0.15)), ("... 0.25", lambda p: R.inflate(p, 0.25)),
                            ("big wins shrink by one goal with probability 0.15", lambda p: R.deflate(p, 0.15)), ("... 0.30", lambda p: R.deflate(p, 0.30)), ("... 0.50", lambda p: R.deflate(p, 0.50))):
            pmf2 = make(inp.pmf)
            inp2 = SeasonInput(**{**inp.__dict__, "pmf": pmf2})
            st = B.model_stats(pmf2)
            st0 = B.model_stats(inp.pmf)
            r2 = engine.simulate(inp2, profile, n, seed)
            s2 = engine.summarize(r2, inp2, profile)
            b2 = band_values(s2)
            order = {t: i for i, t in enumerate(inp.teams)}
            ch = []
            for name in ("title", "top4", "relegation"):
                d = {sref["teams"][i]["entity_id"]: bref[name][i] for i in range(len(sref["teams"]))}
                d2 = {s2["teams"][i]["entity_id"]: b2[name][i] for i in range(len(s2["teams"]))}
                ch.append(max(abs(d[k] - d2[k]) for k in d if not (np.isnan(d[k]) or np.isnan(d2[k]))))
            same_positions = (ref.pos == r2.pos).all(axis=1).mean()
            moved = (ref.pos != r2.pos).sum(axis=1)
            res.append(dict(distortion=label, bias_margin_home_win=round(st["mean_margin_home_win"] - st0["mean_margin_home_win"], 3), bias_margin_away_win=round(st["mean_margin_away_win"] - st0["mean_margin_away_win"], 3),
                            bias_one_goal_share_home=round(st["share_one_goal_home_win"] - st0["share_one_goal_home_win"], 3), max_change_title_probability=round(ch[0], 4), max_change_top4_probability=round(ch[1], 4),
                            max_change_relegation_probability=round(ch[2], 4), share_of_seasons_with_any_position_change=round(float(1 - same_positions), 3), mean_clubs_changing_position=round(float(moved.mean()), 3),
                            points_identical_in_every_season=bool((ref.points == r2.points).all()),
                            mean_abs_change_in_expected_points=round(float(np.abs(r2.points.mean(axis=0) - ref.points.mean(axis=0)).mean()), 3)))
        out[key] = res
    engine._sample_scores = original
    return out


if __name__ == "__main__":
    r = run()
    r["late_season_states_2025_26_completed_season"] = run_late()
    (OUT / "m4_margin_impact.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    for k, rows in r["late_season_states_2025_26_completed_season"].items():
        print(k)
        for x in rows:
            print("  ", x)
    for k, rows in r.items():
        print(k)
        for x in rows:
            print("  ", x)
