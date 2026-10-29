#!/usr/bin/env python3
"""Run an ad hoc v2.7 slate with scoreline estimates.

This is intentionally separate from the main v2.5/v2.7 live pipeline so a
one-off test slate does not mutate the tracked production fixtures.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import build_live_predictions_v27 as v27
import build_road_to_26_v24 as road24
import build_worldcup_model_v2 as v2
import model_bakeoff_v26 as v26
import run_friendlies_v24 as friend24
from api_football_client_v24 import APIFootballError, budget_snapshot, provider_get


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

PREDICTIONS_PATH = PROCESSED / "ad_hoc_v27_june10_predictions.csv"
FEATURES_PATH = PROCESSED / "ad_hoc_v27_june10_features.csv"
REPORT_PATH = OUTPUTS / "ad_hoc_v27_june10_report.md"
CONFIG_PATH = OUTPUTS / "ad_hoc_v27_june10_config.json"

SLATE_FIXTURES = [
    {
        "fixture_key": "adhoc_2026_06_10_portugal_nigeria",
        "date": "2026-06-10",
        "time_et": "15:45",
        "team1": "Portugal",
        "team2": "Nigeria",
        "competition_context": "International friendly",
        "venue": "Leiria",
        "city": "Leiria, Portugal",
        "latitude": 39.7436,
        "longitude": -8.8071,
        "venue_edge_team": "Portugal",
        "source": "API-Football fixture feed",
    },
    {
        "fixture_key": "adhoc_2026_06_10_england_costa_rica",
        "date": "2026-06-10",
        "time_et": "16:00",
        "team1": "England",
        "team2": "Costa Rica",
        "competition_context": "International friendly",
        "venue": "Inter&Co Stadium",
        "city": "Orlando, FL",
        "latitude": 28.5411,
        "longitude": -81.3890,
        "venue_edge_team": "",
        "source": "API-Football fixture feed; venue from public reports",
    },
    {
        "fixture_key": "adhoc_2026_06_10_bolivia_algeria",
        "date": "2026-06-10",
        "time_et": "16:00",
        "team1": "Bolivia",
        "team2": "Algeria",
        "competition_context": "International friendly",
        "venue": "",
        "city": "",
        "latitude": "",
        "longitude": "",
        "venue_edge_team": "",
        "source": "API-Football fixture feed; venue unavailable",
    },
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def simple_team_key(team: str) -> str:
    return road24.simple_team_key(team)


def fetch_provider_rows(date: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    result = provider_get(
        "fixtures",
        {"date": date, "timezone": "America/New_York"},
        ttl_hours=args.fixture_ttl_hours,
        force_refresh=args.force_refresh,
        daily_limit=args.daily_limit,
        reserve_requests=args.reserve_requests,
    )
    return result.response_rows


def find_provider_match(fixture: dict[str, Any], provider_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    expected = {simple_team_key(fixture["team1"]), simple_team_key(fixture["team2"])}
    for row in provider_rows:
        teams = row.get("teams", {})
        home = teams.get("home", {}).get("name", "")
        away = teams.get("away", {}).get("name", "")
        if {simple_team_key(home), simple_team_key(away)} == expected:
            return row
    return None


def provider_summary(fixture: dict[str, Any], provider_rows: list[dict[str, Any]]) -> dict[str, Any]:
    match = find_provider_match(fixture, provider_rows)
    if not match:
        return {
            "provider_found": False,
            "provider_fixture_id": "",
            "provider_league": "",
            "provider_status": "",
            "provider_status_long": "",
            "provider_home": "",
            "provider_away": "",
            "live_score": "",
            "actual_90min_result": "",
        }
    fixture_block = match.get("fixture", {})
    teams_block = match.get("teams", {})
    goals = match.get("goals", {})
    league = match.get("league", {})
    status = fixture_block.get("status", {})
    home = teams_block.get("home", {}).get("name", "")
    away = teams_block.get("away", {}).get("name", "")
    home_goals = goals.get("home")
    away_goals = goals.get("away")
    actual = ""
    if status.get("short") in road24.FINAL_STATUSES:
        actual = road24.actual_result_label(home_goals, away_goals, home, away, fixture["team1"], fixture["team2"])
    live_score = ""
    if home_goals is not None and away_goals is not None:
        live_score = f"{home_goals}-{away_goals}"
    return {
        "provider_found": True,
        "provider_fixture_id": fixture_block.get("id", ""),
        "provider_league": league.get("name", ""),
        "provider_status": status.get("short", ""),
        "provider_status_long": status.get("long", ""),
        "provider_home": home,
        "provider_away": away,
        "live_score": live_score,
        "actual_90min_result": actual,
    }


def weather_for_fixture(fixture: dict[str, Any], force_refresh: bool) -> dict[str, Any]:
    if fixture.get("latitude") in ("", None) or fixture.get("longitude") in ("", None):
        return {
            "fixture_key": fixture["fixture_key"],
            "weather_found": False,
            "weather_error": "Venue coordinates unavailable.",
            "weather_time_utc": "",
            "temperature_c": "",
            "precipitation_probability": "",
            "wind_speed_kmh": "",
            "weather_score": 100.0,
            "weather_goal_factor": 1.0,
            "weather_note": "Weather unavailable; neutral context applied.",
        }
    return friend24.weather_for_fixture(fixture, force_refresh=force_refresh)


def load_lookup(path: Path, key: str, normalize_key: bool = False) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    out = {}
    for row in rows:
        lookup_key = row.get(key, "")
        if normalize_key:
            lookup_key = v2.normalize_team(lookup_key)
        if lookup_key:
            out[lookup_key] = row
    return out


def avg_total(row: dict[str, str], total_key: str, count_key: str, default: float = 0.0) -> float:
    count = safe_float(row.get(count_key), 0.0)
    if count <= 0:
        return default
    return safe_float(row.get(total_key), default * count) / count


def parse_date(value: Any) -> datetime | None:
    try:
        if not value:
            return None
        return datetime.strptime(str(value), "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def days_since(fixture_date: datetime | None, last_match_date: Any) -> float:
    last = parse_date(last_match_date)
    if fixture_date is None or last is None:
        return 999.0
    return min(max((fixture_date - last).days, 0), 999)


def build_feature_rows(
    fixtures: list[dict[str, Any]],
    providers: dict[str, dict[str, Any]],
    weather: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    elo = load_lookup(PROCESSED / "team_elo_latest.csv", "team", normalize_key=True)
    form = load_lookup(PROCESSED / "team_recent_form_latest.csv", "team", normalize_key=True)
    rows = []
    for fixture in fixtures:
        provider = providers[fixture["fixture_key"]]
        home, away, orientation_source, neutral, home_field = v27.choose_orientation(fixture, provider)
        fixture_date = parse_date(fixture["date"])
        home_elo_row = elo.get(home, {})
        away_elo_row = elo.get(away, {})
        home_form = form.get(home, {})
        away_form = form.get(away, {})
        is_comp, is_wc, bucket = v27.tournament_flags(fixture["competition_context"])

        home_elo = safe_float(home_elo_row.get("elo_rating"), 1500.0)
        away_elo = safe_float(away_elo_row.get("elo_rating"), 1500.0)
        home_ppg5 = safe_float(home_form.get("ppg_last_5"), 1.0)
        away_ppg5 = safe_float(away_form.get("ppg_last_5"), 1.0)
        home_ppg10 = safe_float(home_form.get("ppg_last_10"), 1.0)
        away_ppg10 = safe_float(away_form.get("ppg_last_10"), 1.0)
        home_gd5 = avg_total(home_form, "goal_diff_last_5", "matches_last_5", 0.0)
        away_gd5 = avg_total(away_form, "goal_diff_last_5", "matches_last_5", 0.0)
        home_gd10 = avg_total(home_form, "goal_diff_last_10", "matches_last_10", 0.0)
        away_gd10 = avg_total(away_form, "goal_diff_last_10", "matches_last_10", 0.0)
        home_elochg5 = avg_total(home_form, "elo_change_last_5", "matches_last_5", 0.0)
        away_elochg5 = avg_total(away_form, "elo_change_last_5", "matches_last_5", 0.0)
        home_elochg10 = avg_total(home_form, "elo_change_last_10", "matches_last_10", 0.0)
        away_elochg10 = avg_total(away_form, "elo_change_last_10", "matches_last_10", 0.0)
        home_days = days_since(fixture_date, home_form.get("last_match_date") or home_elo_row.get("last_match_date"))
        away_days = days_since(fixture_date, away_form.get("last_match_date") or away_elo_row.get("last_match_date"))
        home_matches = safe_float(home_elo_row.get("matches_played"), 0.0)
        away_matches = safe_float(away_elo_row.get("matches_played"), 0.0)

        missing = []
        if home not in elo:
            missing.append(f"home_elo:{v2.display_team(home)}")
        if away not in elo:
            missing.append(f"away_elo:{v2.display_team(away)}")
        if home not in form:
            missing.append(f"home_form:{v2.display_team(home)}")
        if away not in form:
            missing.append(f"away_form:{v2.display_team(away)}")

        weather_row = weather[fixture["fixture_key"]]
        rows.append(
            {
                "fixture_key": fixture["fixture_key"],
                "date": fixture["date"],
                "time_et": fixture["time_et"],
                "team1": fixture["team1"],
                "team2": fixture["team2"],
                "home_team": home,
                "away_team": away,
                "home_display": v2.display_team(home),
                "away_display": v2.display_team(away),
                "orientation_source": orientation_source,
                "competition_context": fixture["competition_context"],
                "tournament_bucket": bucket,
                "neutral": neutral,
                "home_field": home_field,
                "is_competitive": is_comp,
                "is_world_cup": is_wc,
                "home_elo_pre": home_elo,
                "away_elo_pre": away_elo,
                "elo_diff": home_elo - away_elo,
                "abs_elo_diff": abs(home_elo - away_elo),
                "elo_avg": (home_elo + away_elo) / 2.0,
                "home_recent_ppg5": home_ppg5,
                "away_recent_ppg5": away_ppg5,
                "recent_ppg5_diff": home_ppg5 - away_ppg5,
                "recent_gd5_diff": home_gd5 - away_gd5,
                "recent_elochg5_diff": home_elochg5 - away_elochg5,
                "recent_oppelo5_diff": safe_float(home_form.get("avg_opponent_elo_last_5"), 1500.0) - safe_float(away_form.get("avg_opponent_elo_last_5"), 1500.0),
                "recent_ppg10_diff": home_ppg10 - away_ppg10,
                "recent_gd10_diff": home_gd10 - away_gd10,
                "recent_elochg10_diff": home_elochg10 - away_elochg10,
                "rest_days_diff": home_days - away_days,
                "home_matches_prior_log": math.log1p(home_matches),
                "away_matches_prior_log": math.log1p(away_matches),
                "matches_prior_log_diff": math.log1p(home_matches) - math.log1p(away_matches),
                "temperature_c": weather_row.get("temperature_c", ""),
                "weather_goal_factor": weather_row.get("weather_goal_factor", ""),
                "weather_note": weather_row.get("weather_note", ""),
                "provider_status": provider.get("provider_status", ""),
                "provider_status_long": provider.get("provider_status_long", ""),
                "provider_fixture_id": provider.get("provider_fixture_id", ""),
                "provider_home": provider.get("provider_home", ""),
                "provider_away": provider.get("provider_away", ""),
                "live_score": provider.get("live_score", ""),
                "actual_90min_result": provider.get("actual_90min_result", ""),
                "data_quality_score": 78 if provider.get("provider_found") else 43,
                "missing_live_features": ";".join(missing),
            }
        )
    return rows


def poisson_pmf(lam: float, max_goals: int = 8) -> list[float]:
    probs = [math.exp(-lam)]
    for goal in range(1, max_goals + 1):
        probs.append(probs[-1] * lam / goal)
    total = sum(probs)
    if total < 1.0:
        probs[-1] += 1.0 - total
    return probs


def scoreline_grid(lambda_1: float, lambda_2: float, internal_pick: str, max_goals: int = 8) -> dict[str, Any]:
    p1 = poisson_pmf(lambda_1, max_goals=max_goals)
    p2 = poisson_pmf(lambda_2, max_goals=max_goals)
    rows = []
    for s1, prob1 in enumerate(p1):
        for s2, prob2 in enumerate(p2):
            prob = prob1 * prob2
            if s1 > s2:
                outcome = "team1_win"
            elif s1 == s2:
                outcome = "draw"
            else:
                outcome = "team2_win"
            rows.append({"score": f"{s1}-{s2}", "team1_goals": s1, "team2_goals": s2, "outcome": outcome, "probability": prob})
    rows.sort(key=lambda row: row["probability"], reverse=True)
    consistent = [row for row in rows if row["outcome"] == internal_pick]
    return {
        "modal_score": rows[0]["score"],
        "modal_score_probability": rows[0]["probability"],
        "pick_consistent_score": (consistent[0] if consistent else rows[0])["score"],
        "pick_consistent_score_probability": (consistent[0] if consistent else rows[0])["probability"],
        "top_scores": "; ".join(f"{row['score']} {row['probability'] * 100:.2f}%" for row in rows[:5]),
    }


def score_projection(fixture: dict[str, Any], weather: dict[str, Any], internal_pick: str) -> dict[str, Any]:
    power_rows = road24.build_match_power_rows()
    projection = friend24.project_context_match(fixture, power_rows, weather, {})
    score = scoreline_grid(projection["team1_xg_internal"], projection["team2_xg_internal"], internal_pick)
    return {
        "team1_xg": projection["team1_xg_internal"],
        "team2_xg": projection["team2_xg_internal"],
        "poisson_team1_win_probability": projection["team1_win_probability"],
        "poisson_draw_probability": projection["draw_probability"],
        "poisson_team2_win_probability": projection["team2_win_probability"],
        **score,
    }


def result_from_home_pick(pick: str, feature_row: dict[str, Any]) -> str:
    return v27.team_result_from_home_pick(pick, feature_row)


def build_predictions(
    fixtures: list[dict[str, Any]],
    providers: dict[str, dict[str, Any]],
    weather: dict[str, dict[str, Any]],
    feature_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    artifact = v27.train_final_artifact(force=False)
    probs_by_model = v27.predict_models(artifact, feature_rows)
    ensemble_rule = artifact["pass_rules"]["ensemble"]
    logistic_rule = artifact["pass_rules"]["logistic_regression"]
    ensemble_public = v26.pick_with_pass(
        probs_by_model["ensemble"],
        ensemble_rule["min_confidence"],
        ensemble_rule["min_gap"],
        ensemble_rule["draw_risk_min"],
        ensemble_rule["draw_gap_max"],
    )
    logistic_public = v26.pick_with_pass(
        probs_by_model["logistic_regression"],
        logistic_rule["min_confidence"],
        logistic_rule["min_gap"],
        logistic_rule["draw_risk_min"],
        logistic_rule["draw_gap_max"],
    )

    by_key = {fixture["fixture_key"]: fixture for fixture in fixtures}
    rows = []
    for idx, feature_row in enumerate(feature_rows):
        fixture = by_key[feature_row["fixture_key"]]
        ensemble_probs = probs_by_model["ensemble"][idx]
        logistic_probs = probs_by_model["logistic_regression"][idx]
        team1_is_home = v2.normalize_team(feature_row["team1"]) == feature_row["home_team"]
        team1_win = ensemble_probs[0] if team1_is_home else ensemble_probs[2]
        team2_win = ensemble_probs[2] if team1_is_home else ensemble_probs[0]
        draw = ensemble_probs[1]
        internal_home_pick = v26.LABELS[int(np.argmax(ensemble_probs))]
        internal_pick = result_from_home_pick(internal_home_pick, feature_row)
        consensus_home_pick = ensemble_public[idx] if ensemble_public[idx] != "pass" and ensemble_public[idx] == logistic_public[idx] else "pass"
        public_pick = result_from_home_pick(consensus_home_pick, feature_row)
        score = score_projection(fixture, weather[fixture["fixture_key"]], internal_pick)
        rows.append(
            {
                "fixture_key": fixture["fixture_key"],
                "provider_fixture_id": feature_row["provider_fixture_id"],
                "date": fixture["date"],
                "time_et": fixture["time_et"],
                "team1": fixture["team1"],
                "team2": fixture["team2"],
                "provider_status": feature_row["provider_status"],
                "provider_home": feature_row["provider_home"],
                "provider_away": feature_row["provider_away"],
                "venue": fixture.get("venue", ""),
                "city": fixture.get("city", ""),
                "v27_public_pick": public_pick,
                "v27_internal_ensemble_pick": internal_pick,
                "ensemble_public_before_consensus": result_from_home_pick(ensemble_public[idx], feature_row),
                "logistic_public_before_consensus": result_from_home_pick(logistic_public[idx], feature_row),
                "team1_win_probability": round(float(team1_win), 5),
                "draw_probability": round(float(draw), 5),
                "team2_win_probability": round(float(team2_win), 5),
                "logistic_home_win_probability": round(float(logistic_probs[0]), 5),
                "logistic_draw_probability": round(float(logistic_probs[1]), 5),
                "logistic_away_win_probability": round(float(logistic_probs[2]), 5),
                "predicted_score": score["pick_consistent_score"],
                "modal_score": score["modal_score"],
                "predicted_score_probability": round(float(score["pick_consistent_score_probability"]), 5),
                "modal_score_probability": round(float(score["modal_score_probability"]), 5),
                "top_scorelines": score["top_scores"],
                "team1_xg": round(float(score["team1_xg"]), 3),
                "team2_xg": round(float(score["team2_xg"]), 3),
                "poisson_team1_win_probability": round(float(score["poisson_team1_win_probability"]), 5),
                "poisson_draw_probability": round(float(score["poisson_draw_probability"]), 5),
                "poisson_team2_win_probability": round(float(score["poisson_team2_win_probability"]), 5),
                "temperature_c": weather[fixture["fixture_key"]].get("temperature_c", ""),
                "weather_note": weather[fixture["fixture_key"]].get("weather_note", ""),
                "data_quality_score": feature_row["data_quality_score"],
                "missing_live_features": feature_row["missing_live_features"],
            }
        )
    return rows


def write_report(predictions: list[dict[str, Any]], config: dict[str, Any]) -> None:
    lines = [
        "# Ad Hoc v2.7 Slate: June 10 Friendlies",
        "",
        "This run uses the v2.7 calibrated ensemble for 1X2 probabilities and the Poisson/xG layer for scoreline estimates.",
        "",
        "## Fixture Check",
        "",
        "- API-Football lists these senior men's fixtures on Wednesday, June 10, 2026 ET.",
        "- Confirmed lineups were not available at run time because all three matches were still `NS` / not started.",
        "- Portugal-Nigeria uses Leiria weather and Portugal venue edge.",
        "- England-Costa Rica uses Orlando/Inter&Co Stadium weather from public venue reports.",
        "- Bolivia-Algeria had no provider venue coordinates, so weather is neutral.",
        "",
        "## Predictions",
        "",
        "| Match | v2.7 public | Internal lean | 1 | X | 2 | Predicted score | xG | Weather |",
        "|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for row in predictions:
        xg = f"{row['team1_xg']}-{row['team2_xg']}"
        temp = f"{row['temperature_c']}C" if row["temperature_c"] != "" else "neutral"
        lines.append(
            f"| {row['team1']} vs {row['team2']} | {row['v27_public_pick']} | {row['v27_internal_ensemble_pick']} | "
            f"{float(row['team1_win_probability']) * 100:.2f}% | {float(row['draw_probability']) * 100:.2f}% | "
            f"{float(row['team2_win_probability']) * 100:.2f}% | {row['predicted_score']} | {xg} | {temp} |"
        )
    lines.extend(
        [
            "",
            "## Scoreline Caveat",
            "",
            "The predicted score is the highest-probability scoreline consistent with the v2.7 internal lean. The raw modal exact score is also saved in the CSV because exact scores are noisy and often cluster around 1-0, 1-1, or 2-0.",
            "",
            "## Top Exact Scorelines",
            "",
        ]
    )
    for row in predictions:
        lines.append(f"- {row['team1']} vs {row['team2']}: {row['top_scorelines']}")
    lines.extend(
        [
            "",
            "## API Budget",
            "",
            f"- Used today: {config['api_budget']['used_today']}/{config['api_budget']['daily_limit']}.",
            f"- Remaining before local stop: {config['api_budget']['remaining_before_stop']}.",
        ]
    )
    OUTPUTS.mkdir(exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ad hoc v2.7 fixture slate.")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--force-weather", action="store_true")
    parser.add_argument("--daily-limit", type=int, default=100)
    parser.add_argument("--reserve-requests", type=int, default=15)
    parser.add_argument("--fixture-ttl-hours", type=float, default=6.0)
    args = parser.parse_args()

    try:
        provider_rows_by_date = {
            date: fetch_provider_rows(date, args)
            for date in sorted({fixture["date"] for fixture in SLATE_FIXTURES})
        }
    except APIFootballError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        raise

    providers = {
        fixture["fixture_key"]: provider_summary(fixture, provider_rows_by_date.get(fixture["date"], []))
        for fixture in SLATE_FIXTURES
    }
    weather = {
        fixture["fixture_key"]: weather_for_fixture(fixture, args.force_weather)
        for fixture in SLATE_FIXTURES
    }
    feature_rows = build_feature_rows(SLATE_FIXTURES, providers, weather)
    predictions = build_predictions(SLATE_FIXTURES, providers, weather, feature_rows)

    write_csv(
        FEATURES_PATH,
        feature_rows,
        [
            "fixture_key",
            "date",
            "time_et",
            "team1",
            "team2",
            "home_display",
            "away_display",
            "orientation_source",
            "competition_context",
            "tournament_bucket",
            *v26.FEATURE_COLUMNS,
            "temperature_c",
            "weather_goal_factor",
            "weather_note",
            "provider_status",
            "provider_status_long",
            "provider_fixture_id",
            "provider_home",
            "provider_away",
            "live_score",
            "actual_90min_result",
            "data_quality_score",
            "missing_live_features",
        ],
    )
    write_csv(
        PREDICTIONS_PATH,
        predictions,
        [
            "fixture_key",
            "provider_fixture_id",
            "date",
            "time_et",
            "team1",
            "team2",
            "provider_status",
            "provider_home",
            "provider_away",
            "venue",
            "city",
            "v27_public_pick",
            "v27_internal_ensemble_pick",
            "ensemble_public_before_consensus",
            "logistic_public_before_consensus",
            "team1_win_probability",
            "draw_probability",
            "team2_win_probability",
            "logistic_home_win_probability",
            "logistic_draw_probability",
            "logistic_away_win_probability",
            "predicted_score",
            "modal_score",
            "predicted_score_probability",
            "modal_score_probability",
            "top_scorelines",
            "team1_xg",
            "team2_xg",
            "poisson_team1_win_probability",
            "poisson_draw_probability",
            "poisson_team2_win_probability",
            "temperature_c",
            "weather_note",
            "data_quality_score",
            "missing_live_features",
        ],
    )
    config = {
        "version": "ad_hoc_v27_june10",
        "fixtures": SLATE_FIXTURES,
        "api_budget": budget_snapshot(args.daily_limit, args.reserve_requests),
        "outputs": [
            str(PREDICTIONS_PATH.relative_to(ROOT)),
            str(FEATURES_PATH.relative_to(ROOT)),
            str(REPORT_PATH.relative_to(ROOT)),
        ],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(predictions, config)
    print(
        json.dumps(
            {
                "fixtures": len(predictions),
                "report": str(REPORT_PATH.relative_to(ROOT)),
                "predictions": [
                    {
                        "match": f"{row['team1']} vs {row['team2']}",
                        "internal_pick": row["v27_internal_ensemble_pick"],
                        "public_pick": row["v27_public_pick"],
                        "predicted_score": row["predicted_score"],
                    }
                    for row in predictions
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
