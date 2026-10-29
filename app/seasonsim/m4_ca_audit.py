"""Review of the proposed confirmation set CA (other European first divisions, 2024-07-01 to 2026-09-20).

1. Manifest: the exact list of CA matches (identifiers, dates, clubs, league) with a sha256, written BEFORE any scoreline statistic exists for CA. It contains no score and no result.
2. Representativeness, using ONLY (a) pre-match predictors of CA matches (expected goals, v1 probabilities, history depth: no outcome is read) and (b) the actual goal statistics of the
   same leagues in the DEVELOPMENT window (before 2024-07-01), which is not CA.
3. Provenance audit: which analyses in this project have touched which matches.
Nothing here evaluates a scoreline method on CA.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import predict  # noqa: E402
from seasonsim import m2_benchmark as B  # noqa: E402
from seasonsim import scoreline  # noqa: E402

OUT = APP.parent / "data" / "supervised" / "phase3"
FIVE = {"england:1-premierleague", "espana:1-liga", "deutschland:1-bundesliga", "italy:1-seriea", "europe/france:fr1"}
START, END = pd.Timestamp("2024-07-01"), pd.Timestamp("2026-09-20")
EU_PREFIX = ("europe/", "belgium:", "austria:")


def ca_rows(V: pd.DataFrame) -> pd.DataFrame:
    x = V[(V.dt >= START) & (V.dt <= END) & (~V.competition_id.isin(FIVE)) & (V.competition_type == "domestic_league") & (V.tier == 1) & V.competition_id.str.startswith(EU_PREFIX)]
    return x


def manifest(V: pd.DataFrame) -> dict:
    x = ca_rows(V)[["record_id", "competition_id", "dt", "home_entity_id", "away_entity_id"]].sort_values(["competition_id", "dt", "record_id"])      # no result column is selected
    per = x.groupby("competition_id").size().sort_values(ascending=False)
    ca1 = sorted(per[per >= 300].index)
    ids = x.record_id.tolist()
    return dict(window=[str(START.date()), str(END.date())], matches=len(x), leagues=len(per), ca1_leagues=ca1, ca1_matches=int(per[per >= 300].sum()), ca2_matches=int(per[per < 300].sum()),
                per_league={k: int(v) for k, v in per.items()}, record_ids_sha256=hashlib.sha256("\n".join(ids).encode()).hexdigest(),
                note="identifiers, dates and clubs only; no score or result was read to build this list")


def prematch_covariates(V: pd.DataFrame) -> pd.DataFrame:
    """Expected goals and v1 probabilities of CA matches (and of Bundesliga / La Liga for comparison), from results strictly BEFORE each match. No outcome of these matches is used."""
    lg, _, _ = predict._club_runtime()
    sel = pd.concat([ca_rows(V), V[(V.dt >= START) & (V.dt <= END) & V.competition_id.isin(["deutschland:1-bundesliga", "espana:1-liga"])]])
    fx = pd.DataFrame(dict(fixture_id="FX:" + sel.record_id.astype(str), dt=sel.dt, h=sel.home_entity_id, a=sel.away_entity_id, comp=sel.competition_id, season=sel.season_corrected, tier=sel.tier.values))
    F2, F1 = lg.features_for(V, fx)
    F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
    v2m, v1m, v1prep, v1elo = predict._club_models()
    p1 = lg.v1_proba(v1m, v1prep, F1)
    return pd.DataFrame(dict(comp=sel.competition_id.values, group=np.where(sel.competition_id.isin(["deutschland:1-bundesliga", "espana:1-liga"]), "target", "CA"), lam_h=F2.lambda_home.values, lam_a=F2.lambda_away.values,
                             p_H=p1[:, 0], p_D=p1[:, 1], p_A=p1[:, 2], n_h=F2.home_n_prior.values, n_a=F2.away_n_prior.values, elo_diff=F1.elo_diff.values))


def smd(a: np.ndarray, b: np.ndarray) -> float:
    return float((np.nanmean(a) - np.nanmean(b)) / np.sqrt((np.nanvar(a) + np.nanvar(b)) / 2))


def representativeness(V: pd.DataFrame, cov: pd.DataFrame) -> dict:
    out = {}
    t, c = cov[cov.group == "target"], cov[cov.group == "CA"]
    feats = {"expected goals, home": "lam_h", "expected goals, away": "lam_a", "expected total goals": None, "v1 home-win probability": "p_H", "v1 draw probability": "p_D", "v1 away-win probability": "p_A", "Elo difference": "elo_diff", "history depth (home club prior matches)": "n_h"}
    rows = {}
    for name, col in feats.items():
        a = (t.lam_h + t.lam_a).values if col is None else t[col].values
        b = (c.lam_h + c.lam_a).values if col is None else c[col].values
        rows[name] = dict(target_mean=round(float(np.nanmean(a)), 3), ca_mean=round(float(np.nanmean(b)), 3), standardised_difference=round(smd(a, b), 3))
    # share of CA matches whose (expected total goals, strength gap) lie inside the 5-95% range of the target leagues
    tg, cg = (t.lam_h + t.lam_a).values, (c.lam_h + c.lam_a).values
    gap_t, gap_c = (t.p_H - t.p_A).values, (c.p_H - c.p_A).values
    inside = ((cg >= np.nanpercentile(tg, 5)) & (cg <= np.nanpercentile(tg, 95)) & (gap_c >= np.nanpercentile(gap_t, 5)) & (gap_c <= np.nanpercentile(gap_t, 95))).mean()
    per_league = {k: dict(n=int(len(g)), expected_total_goals=round(float((g.lam_h + g.lam_a).mean()), 2), mean_abs_strength_gap=round(float((g.p_H - g.p_A).abs().mean()), 3)) for k, g in cov.groupby("comp")}
    # development-window actual goal statistics (before 2024-07-01; NOT the CA window)
    d0 = V[(V.dt < START) & (V.competition_type == "domestic_league") & (V.tier == 1)]
    stats = {}
    for comp, g in d0.groupby("competition_id"):
        hg, ag = np.minimum(g.gh.values.astype(int), 9), np.minimum(g.ga.values.astype(int), 9)
        if len(g) < 400:
            continue
        act = B.actual_stats(hg, ag)
        stats[comp] = dict(n=int(len(g)), goals_per_match=round(float((hg + ag).mean()), 2), home_win_rate=round(float((hg > ag).mean()), 3), draw_rate=round(float((hg == ag).mean()), 3),
                           margin_home_win=round(act["mean_margin_home_win"], 3), margin_away_win=round(act["mean_margin_away_win"], 3), one_goal_share_home=round(act["share_one_goal_home_win"], 3), one_goal_share_away=round(act["share_one_goal_away_win"], 3))
    df = pd.DataFrame(stats).T
    ca_names = [k for k in df.index if k.startswith(EU_PREFIX) and k not in FIVE]
    tar = [k for k in ("deutschland:1-bundesliga", "espana:1-liga") if k in df.index]
    het = {}
    for col in ("goals_per_match", "margin_home_win", "margin_away_win", "one_goal_share_home", "one_goal_share_away", "draw_rate"):
        v = df.loc[ca_names, col].astype(float)
        het[col] = dict(ca_min=round(float(v.min()), 3), ca_median=round(float(v.median()), 3), ca_max=round(float(v.max()), 3), ca_sd=round(float(v.std()), 3),
                        target={k: float(df.loc[k, col]) for k in tar}, target_inside_ca_range=bool(all(v.min() <= float(df.loc[k, col]) <= v.max() for k in tar)),
                        target_z_vs_ca=[round(float((float(df.loc[k, col]) - v.mean()) / v.std()), 2) for k in tar])
    return dict(prematch=rows, share_of_ca_matches_inside_target_5_95_range=round(float(inside), 3), per_league_prematch=per_league, development_window_outcome_structure=stats, heterogeneity_development_window=het, n_ca_leagues_compared=len(ca_names))


def main() -> None:
    lg, V, _ = predict._club_runtime()
    man = manifest(V)
    (OUT / "ca_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print("manifest:", {k: man[k] for k in ("matches", "leagues", "ca1_matches", "ca2_matches", "record_ids_sha256")})
    cov = prematch_covariates(V)
    rep = representativeness(V, cov)
    (OUT / "m4_ca_representativeness.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("prematch", "share_of_ca_matches_inside_target_5_95_range", "heterogeneity_development_window")}, indent=1))


if __name__ == "__main__":
    main()
