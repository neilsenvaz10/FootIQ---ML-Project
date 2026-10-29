"""M2 data: time-safe pre-match v1 probabilities and expected goals (lambda) for every completed match of the five leagues, 2018-19 to 2026-09-20.

Each match is featurised from results strictly before its own date (the project's `features_for` replay), exactly like a prospective fixture.
Output: data/supervised/phase3/m2_matches.pkl (git-ignored). Nothing is trained; the frozen v1 artifact is only used to score.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import config as C  # noqa: E402
import predict  # noqa: E402

OUT = C.ROOT / "data" / "supervised" / "phase3"
LEAGUES = {"england:1-premierleague": "EPL", "espana:1-liga": "LALIGA", "deutschland:1-bundesliga": "BUNDESLIGA", "italy:1-seriea": "SERIEA", "europe/france:fr1": "LIGUE1"}
SPLIT = pd.Timestamp("2024-07-01")                         # fit window ends before it; evaluation (v1 test + forward holdout) starts on it


def build() -> pd.DataFrame:
    lg, V, tiers = predict._club_runtime()
    sel = V[V.competition_id.isin(LEAGUES) & (V.dt >= "2018-08-01")].copy()
    fx = pd.DataFrame(dict(fixture_id="FX:" + sel.record_id.astype(str), dt=sel.dt, h=sel.home_entity_id, a=sel.away_entity_id, comp=sel.competition_id, season=sel.season_corrected, tier=sel.tier.values))
    F2, F1 = lg.features_for(V, fx)
    F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
    v2m, v1m, v1prep, v1elo = predict._club_models()
    p1 = lg.v1_proba(v1m, v1prep, F1)
    p2 = v2m["model"].predict_proba(v2m["prep"].transform(F2, True))
    out = pd.DataFrame(dict(record_id=sel.record_id.values, league=sel.competition_id.map(LEAGUES).values, comp=sel.competition_id.values, season=sel.season_corrected.values, dt=sel.dt.values,
                            home=sel.home_entity_id.values, away=sel.away_entity_id.values, hg=sel.gh.values, ag=sel.ga.values,
                            p1_H=p1[:, 0], p1_D=p1[:, 1], p1_A=p1[:, 2], p2_H=p2[:, 0], p2_D=p2[:, 1], p2_A=p2[:, 2],
                            lam_h=F2.lambda_home.values, lam_a=F2.lambda_away.values, n_h=F2.home_n_prior.values, n_a=F2.away_n_prior.values))
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    df = build()
    df.to_pickle(OUT / "m2_matches.pkl")
    print(len(df), df.dt.min(), df.dt.max(), df.groupby("league").size().to_dict())
    print("lambda missing:", float(df.lam_h.isna().mean()))
