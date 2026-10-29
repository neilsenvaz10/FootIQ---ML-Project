"""Retrospective backtest harness (NOT the official prospective evaluation; it reads and writes nothing under any prospective_log folder).

For a cut-off date D the state is rebuilt from results dated strictly before D only (`V[V.dt < D]`), every remaining fixture of the season is featurised
from that frozen state at its own date, outcome probabilities come from the frozen club v1 artifact and expected goals from the v2 feature generator,
and the season is simulated. The realised season (full results) is used only for scoring afterwards.

Out-of-sample seasons for frozen club v1 are 2024-25 and 2025-26 only (v1 was fitted on matches up to 2023-06-30 and tuned on 2023-24).
M2b (this module's `end_to_end`) scores the scoreline methods on season goal difference, goals scored and points: no ranking, hence no tie-break rules.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import config as C  # noqa: E402
import predict  # noqa: E402
from seasonsim import engine, scoreline  # noqa: E402
from seasonsim.engine import K, SeasonInput  # noqa: E402
from store import db as store_db  # noqa: E402

OUT = C.ROOT / "data" / "supervised" / "phase3"
LEAGUES = {"EPL": "england:1-premierleague", "LALIGA": "espana:1-liga", "BUNDESLIGA": "deutschland:1-bundesliga", "SERIEA": "italy:1-seriea", "LIGUE1": "europe/france:fr1"}
CUTOFFS = {"2024-25": ["2024-11-01", "2025-01-01", "2025-03-01"], "2025-26": ["2025-11-01", "2026-01-01", "2026-03-01"]}
EVAL_START = pd.Timestamp("2024-07-01")


def season_frames(conn, key: str, season: str) -> pd.DataFrame:
    df = pd.read_sql("SELECT record_id, match_date, COALESCE(model_home_entity, home_entity_id) h, COALESCE(model_away_entity, away_entity_id) a, status, home_goals_90 hg, away_goals_90 ag "
                     "FROM matches WHERE competition_key=? AND season=? AND kind='club'", conn, params=(key, season))
    df["dt"] = pd.to_datetime(df.match_date)
    return df


def probabilities_at(V: pd.DataFrame, cutoff: pd.Timestamp, fixtures: pd.DataFrame) -> pd.DataFrame:
    """Frozen-model probabilities and expected goals for fixtures (columns fixture_id, dt, h, a, comp, season, tier) from results strictly before `cutoff`."""
    lg, _, _ = predict._club_runtime()
    known = V[V.dt < cutoff]
    assert (known.dt < cutoff).all()
    F2, F1 = lg.features_for(known, fixtures)
    F2, F1 = F2.loc[fixtures.fixture_id], F1.loc[fixtures.fixture_id]
    v2m, v1m, v1prep, v1elo = predict._club_models()
    p1 = lg.v1_proba(v1m, v1prep, F1)
    p2 = v2m["model"].predict_proba(v2m["prep"].transform(F2, True))
    return pd.DataFrame(dict(fixture_id=fixtures.fixture_id.values, p1_H=p1[:, 0], p1_D=p1[:, 1], p1_A=p1[:, 2], p2_H=p2[:, 0], p2_D=p2[:, 1], p2_A=p2[:, 2], lam_h=F2.lambda_home.values, lam_a=F2.lambda_away.values))


def build_input(frame: pd.DataFrame, cutoff: pd.Timestamp, probs: pd.DataFrame, method: str, league: str, league_lams, emp, prob_col: str = "p1") -> tuple:
    teams = sorted(set(frame.h) | set(frame.a))
    idx = {t: i for i, t in enumerate(teams)}
    played = frame[(frame.dt < cutoff) & frame.status.isin(["completed", "awarded"])]
    rem = frame[~frame.record_id.isin(played.record_id)]
    pr = probs.set_index("fixture_id").loc[rem.record_id]
    pmf, info = scoreline.build_pmf(method, pr[[f"{prob_col}_H", f"{prob_col}_D", f"{prob_col}_A"]].values, pr.lam_h.values, pr.lam_a.values, league, league_lams, emp)
    inp = SeasonInput(teams=teams, names=teams, played_home=played.h.map(idx).values.astype(int), played_away=played.a.map(idx).values.astype(int),
                      played_hg=played.hg.values.astype(int), played_ag=played.ag.values.astype(int), fix_home=rem.h.map(idx).values.astype(int), fix_away=rem.a.map(idx).values.astype(int),
                      pmf=pmf, fix_ids=list(rem.record_id))
    return inp, info


def real_final(frame: pd.DataFrame, teams: list) -> dict:
    idx = {t: i for i, t in enumerate(teams)}
    pts, gf, ga = np.zeros(len(teams)), np.zeros(len(teams)), np.zeros(len(teams))
    for r in frame[frame.status.isin(["completed", "awarded"])].itertuples():
        h, a = idx[r.h], idx[r.a]
        pts[h] += 3 if r.hg > r.ag else 1 if r.hg == r.ag else 0
        pts[a] += 3 if r.ag > r.hg else 1 if r.hg == r.ag else 0
        gf[h] += r.hg; ga[h] += r.ag; gf[a] += r.ag; ga[a] += r.hg
    return dict(points=pts, gf=gf, gd=gf - ga)


def end_to_end(n_sims: int = 4000, seed: int = 7, methods=("S1", "S2", "S3")) -> dict:
    """M2b: do simulated season goal difference / goals / points cover the realised ones? Pooled over 2024-25 and 2025-26 and three cut-offs per season."""
    m2 = pd.read_pickle(OUT / "m2_matches.pkl")
    fit = m2[(m2.dt < EVAL_START) & m2.hg.notna()]
    emp = scoreline.Empirical().fit(fit.league.values, (fit.lam_h - fit.lam_a).values, fit.hg.values, fit.ag.values)
    league_lams = {l: (float(g.hg.mean()), float(g.ag.mean())) for l, g in fit.groupby("league")}
    lg, V, tiers = predict._club_runtime()
    conn = store_db.connect(readonly=True)
    rows = []
    try:
        meta = V.set_index("record_id")[["season_corrected", "tier", "competition_id"]]
        frames = {(k, s): season_frames(conn, k, s) for k in LEAGUES for s in CUTOFFS}
        for season, dates in CUTOFFS.items():
            for d in dates:
                cutoff = pd.Timestamp(d)
                fx = []
                for k, comp in LEAGUES.items():
                    f = frames[(k, season)]
                    rem = f[~((f.dt < cutoff) & f.status.isin(["completed", "awarded"]))]
                    fx.append(pd.DataFrame(dict(fixture_id=rem.record_id.values, dt=rem.dt.values, h=rem.h.values, a=rem.a.values, comp=comp, season=meta.loc[rem.record_id, "season_corrected"].values, tier=meta.loc[rem.record_id, "tier"].values)))
                fx = pd.concat(fx, ignore_index=True)
                probs = probabilities_at(V, cutoff, fx)
                for k in LEAGUES:
                    f = frames[(k, season)]
                    for m in methods:
                        inp, info = build_input(f, cutoff, probs, m, k, league_lams[k], emp)
                        res = engine.simulate(inp, {"points": {"win": 3, "draw": 1}}, n=n_sims, seed=seed, rank=False)
                        real = real_final(f, inp.teams)
                        for t in range(len(inp.teams)):
                            rows.append(dict(season=season, cutoff=d, league=k, method=m, team=inp.teams[t],
                                             gd_real=real["gd"][t], gd_mean=float(res.gd[:, t].mean()), gd_p10=float(np.percentile(res.gd[:, t], 10)), gd_p90=float(np.percentile(res.gd[:, t], 90)),
                                             gf_real=real["gf"][t], gf_mean=float(res.gf[:, t].mean()), gf_p10=float(np.percentile(res.gf[:, t], 10)), gf_p90=float(np.percentile(res.gf[:, t], 90)),
                                             pts_real=real["points"][t], pts_mean=float(res.points[:, t].mean()), pts_p10=float(np.percentile(res.points[:, t], 10)), pts_p90=float(np.percentile(res.points[:, t], 90)),
                                             remaining=int(((inp.fix_home == t) | (inp.fix_away == t)).sum())))
                print("done", season, d, flush=True)
    finally:
        conn.close()
    df = pd.DataFrame(rows)
    df.to_pickle(OUT / "m2b_rows.pkl")
    rep = dict(n_sims=n_sims, seed=seed, cutoffs=CUTOFFS, rows=len(df), methods={})
    for m in methods:
        d = df[(df.method == m) & (df.remaining > 0)]
        cov = lambda y, lo, hi: float(((d[y] >= d[lo]) & (d[y] <= d[hi])).mean())  # noqa: E731
        per = {k: dict(gd_cov=float(((g.gd_real >= g.gd_p10) & (g.gd_real <= g.gd_p90)).mean()), gf_cov=float(((g.gf_real >= g.gf_p10) & (g.gf_real <= g.gf_p90)).mean()),
                       pts_cov=float(((g.pts_real >= g.pts_p10) & (g.pts_real <= g.pts_p90)).mean()), n=int(len(g))) for k, g in d.groupby("league")}
        rep["methods"][m] = dict(n_team_cutoffs=int(len(d)), gd_coverage=cov("gd_real", "gd_p10", "gd_p90"), goals_scored_coverage=cov("gf_real", "gf_p10", "gf_p90"), points_coverage=cov("pts_real", "pts_p10", "pts_p90"),
                                 gd_mae=float((d.gd_real - d.gd_mean).abs().mean()), gd_bias=float((d.gd_mean - d.gd_real).mean()), pts_mae=float((d.pts_real - d.pts_mean).abs().mean()),
                                 per_league=per, gd_coverage_in_70_90=bool(0.70 <= cov("gd_real", "gd_p10", "gd_p90") <= 0.90))
    (OUT / "m2b_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


if __name__ == "__main__":
    r = end_to_end()
    for m, v in r["methods"].items():
        print(m, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items() if k != "per_league"})
        for lg, p in v["per_league"].items():
            print("   ", lg, {k: round(x, 3) if isinstance(x, float) else x for k, x in p.items()})
