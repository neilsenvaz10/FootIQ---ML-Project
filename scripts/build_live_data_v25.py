#!/usr/bin/env python3
"""Build model v2.5 live-data backbone tables.

V2.5 is the production-foundation step. It does not invent a new prediction
formula; it standardizes the live inputs the model needs every day.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import build_road_to_26_v24 as road24
import build_worldcup_model_v2 as v2
import build_worldcup_model_v23 as v23
import run_friendlies_v24 as friend24
from api_football_client_v24 import APIFootballError, budget_snapshot, provider_get


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

CONFIG_PATH = OUTPUTS / "live_data_v25_config.json"
REPORT_PATH = OUTPUTS / "live_data_v25_report.md"

FIXTURES_PATH = PROCESSED / "v25_fixtures_live.csv"
TEAM_STRENGTH_PATH = PROCESSED / "v25_team_strength_live.csv"
PROVIDER_STATUS_PATH = PROCESSED / "v25_provider_status_live.csv"
LINEUPS_PATH = PROCESSED / "v25_confirmed_lineups_live.csv"
AVAILABILITY_PATH = PROCESSED / "v25_player_availability_live.csv"
WEATHER_PATH = PROCESSED / "v25_weather_context_live.csv"
ODDS_PATH = PROCESSED / "v25_odds_snapshot_live.csv"
PREDICTIONS_PATH = PROCESSED / "v25_match_predictions_live.csv"
POSTMATCH_PATH = PROCESSED / "v25_postmatch_results_live.csv"
QUALITY_PATH = PROCESSED / "v25_data_quality_live.csv"

FINAL_STATUSES = road24.FINAL_STATUSES

ROAD_TO_26_COORDS = {
    "road26_2026_06_06_bolivia_scotland": (40.7368, -74.1504, ""),
    "road26_2026_06_06_brazil_egypt": (41.5061, -81.6995, ""),
    "road26_2026_06_06_argentina_honduras": (30.6102, -96.3409, ""),
    "road26_2026_06_07_morocco_norway": (40.7368, -74.1504, ""),
    "road26_2026_06_07_colombia_jordan": (32.7840, -117.1228, ""),
    "road26_2026_06_09_argentina_iceland": (32.6026, -85.4893, ""),
}

V25_CONFIG = {
    "version": "v2.5",
    "purpose": "Live-data backbone for fixtures, status, team strength, lineups, weather, odds placeholders, predictions, and postmatch scoring.",
    "model_engine": "v2.3/v2.4 match engine",
    "api_provider": "API-Football",
    "weather_provider": "Open-Meteo",
    "daily_api_limit": 100,
    "reserve_requests": 15,
    "fixture_ttl_hours": 0.5,
    "details_ttl_hours": 0.25,
    "weather_ttl_hours": 1.0,
    "tracked_scope": "Road to 26 fixtures plus selected live international friendlies.",
}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def tracked_fixtures() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fixture in road24.ROAD_TO_26_FIXTURES:
        row = dict(fixture)
        latitude, longitude, venue_edge_team = ROAD_TO_26_COORDS.get(row["fixture_key"], ("", "", ""))
        row.update(
            {
                "competition_context": "Road to 26 friendly",
                "latitude": latitude,
                "longitude": longitude,
                "venue_edge_team": venue_edge_team,
            }
        )
        rows.append(row)
    for fixture in friend24.FRIENDLY_FIXTURES:
        row = dict(fixture)
        row["competition_context"] = "International friendly live test"
        rows.append(row)
    rows.sort(key=lambda row: (row["date"], row["time_et"], row["fixture_key"]))
    return rows


def fetch_provider_rows_by_date(
    fixtures: list[dict[str, Any]],
    args: argparse.Namespace,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    by_date: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    for date in sorted({row["date"] for row in fixtures}):
        try:
            result = provider_get(
                "fixtures",
                {"date": date, "timezone": "America/New_York"},
                ttl_hours=args.fixture_ttl_hours,
                force_refresh=args.force_refresh,
                daily_limit=args.daily_limit,
                reserve_requests=args.reserve_requests,
            )
            by_date[date] = result.response_rows
            if not by_date[date]:
                next_date = (datetime.fromisoformat(date).date() + timedelta(days=1)).isoformat()
                spillover = provider_get(
                    "fixtures",
                    {"date": next_date, "timezone": "America/New_York"},
                    ttl_hours=args.fixture_ttl_hours,
                    force_refresh=args.force_refresh,
                    daily_limit=args.daily_limit,
                    reserve_requests=args.reserve_requests,
                )
                by_date[date] = spillover.response_rows
        except APIFootballError as exc:
            errors.append(f"{date}: {exc}")
            by_date[date] = []
    return by_date, errors


def provider_summary_for_fixture(fixture: dict[str, Any], rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    return friend24.provider_summary_for_fixture(fixture, rows, args)


def build_team_strength_rows(fixtures: list[dict[str, Any]], power_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    teams = sorted({v2.normalize_team(fixture["team1"]) for fixture in fixtures} | {v2.normalize_team(fixture["team2"]) for fixture in fixtures})
    rows: list[dict[str, Any]] = []
    for team in teams:
        power = power_rows.get(team, {})
        rows.append(
            {
                "team": v2.display_team(team),
                "normalized_team": team,
                "v25_match_power": power.get("v24_power_score", ""),
                "global_match_power": power.get("global_match_power", ""),
                "raw_world_cup_v23_power": power.get("raw_v23_power", ""),
                "profile_adjustment": power.get("profile_adjustment", ""),
                "elo_score": power.get("elo_score", ""),
                "squad_score": power.get("squad_score", ""),
                "recent_form_score": power.get("recent_form_score", ""),
                "tactical_score": power.get("tactical_score", ""),
                "availability_score": power.get("availability_score", ""),
                "market_score": power.get("market_score", ""),
                "ceiling_score": power.get("ceiling_score", ""),
                "manager_score": power.get("manager_score", ""),
                "power_source": power.get("power_source", "missing_power_source"),
                "squad_source": power.get("squad_source", ""),
                "manager_source": power.get("manager_source", ""),
            }
        )
    return rows


def build_weather_context(fixtures: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for fixture in fixtures:
        if fixture.get("latitude") in ("", None) or fixture.get("longitude") in ("", None):
            rows[fixture["fixture_key"]] = {
                "fixture_key": fixture["fixture_key"],
                "weather_found": False,
                "weather_error": "Missing venue coordinates.",
                "temperature_c": "",
                "precipitation_probability": "",
                "wind_speed_kmh": "",
                "weather_score": 100.0,
                "weather_goal_factor": 1.0,
                "weather_note": "Weather unavailable; neutral context applied.",
            }
            continue
        rows[fixture["fixture_key"]] = friend24.weather_for_fixture(
            fixture,
            force_refresh=args.force_weather,
        )
    return rows


def fixture_status_row(fixture: dict[str, Any], provider: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_key": fixture["fixture_key"],
        "date": fixture["date"],
        "time_et": fixture["time_et"],
        "team1": fixture["team1"],
        "team2": fixture["team2"],
        "competition_context": fixture["competition_context"],
        "provider_found": provider["provider_found"],
        "provider_fixture_id": provider["provider_fixture_id"],
        "provider_league": provider["provider_league"],
        "provider_status": provider["provider_status"],
        "provider_status_long": provider["provider_status_long"],
        "provider_home": provider["provider_home"],
        "provider_away": provider["provider_away"],
        "live_score": provider.get("live_score", ""),
        "provider_home_goals": provider["provider_home_goals"],
        "provider_away_goals": provider["provider_away_goals"],
        "actual_90min_result": provider["actual_90min_result"],
        "lineup_status": provider["lineup_status"],
        "lineups_count": provider["lineups_count"],
        "events_count": provider["events_count"],
        "statistics_count": provider["statistics_count"],
    }


def availability_rows_for_fixture(fixture: dict[str, Any], lineup_context: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for side in ["team1", "team2"]:
        team = v2.normalize_team(fixture[side])
        context = lineup_context.get(team, {})
        rows.append(
            {
                "fixture_key": fixture["fixture_key"],
                "team": fixture[side],
                "normalized_team": team,
                "availability_score": 100.0,
                "confirmed_lineup_available": bool(context),
                "matched_starters": context.get("matched_starters", ""),
                "total_starters": context.get("total_starters", ""),
                "lineup_power_adjustment": context.get("lineup_power_adjustment", 0.0),
                "provider_injury_status": "not_ingested_in_v25",
                "source_status": "neutral_until_injury_endpoint_is_integrated",
                "note": "v2.5 creates the table contract; v2.6 should ingest injuries/suspensions into this table.",
            }
        )
    return rows


def odds_rows_for_fixture(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "fixture_key": fixture["fixture_key"],
            "team1": fixture["team1"],
            "team2": fixture["team2"],
            "odds_provider": "",
            "snapshot_time": "",
            "team1_decimal_odds": "",
            "draw_decimal_odds": "",
            "team2_decimal_odds": "",
            "team1_implied_probability": "",
            "draw_implied_probability": "",
            "team2_implied_probability": "",
            "odds_status": "not_enabled_in_v25",
            "note": "v2.5 table contract only; live odds feed should be added after fixture/lineup/weather tables are stable.",
        }
    ]


def prediction_row_for_fixture(
    fixture: dict[str, Any],
    projection: dict[str, Any],
    provider: dict[str, Any],
    weather: dict[str, Any],
    lineup_context: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    team1 = v2.normalize_team(fixture["team1"])
    team2 = v2.normalize_team(fixture["team2"])
    team1_lineup = lineup_context.get(team1, {})
    team2_lineup = lineup_context.get(team2, {})
    pick_correct = ""
    if provider["actual_90min_result"]:
        pick_correct = provider["actual_90min_result"] == projection["model_90min_pick"]
    return {
        "fixture_key": fixture["fixture_key"],
        "date": fixture["date"],
        "time_et": fixture["time_et"],
        "team1": fixture["team1"],
        "team2": fixture["team2"],
        "competition_context": fixture["competition_context"],
        "provider_status": provider["provider_status"],
        "live_score": provider.get("live_score", ""),
        "public_verdict": projection["public_verdict"],
        "confidence": projection["confidence"],
        "model_90min_pick": projection["model_90min_pick"],
        "model_reason": projection["model_reason"],
        "team1_win_probability_internal": round(projection["team1_win_probability"], 4),
        "draw_probability_internal": round(projection["draw_probability"], 4),
        "team2_win_probability_internal": round(projection["team2_win_probability"], 4),
        "team1_xg_internal": round(projection["team1_xg_internal"], 3),
        "team2_xg_internal": round(projection["team2_xg_internal"], 3),
        "team1_power": round(projection["team1_power"], 3),
        "team2_power": round(projection["team2_power"], 3),
        "power_diff_team1": round(projection["power_diff_team1"], 3),
        "team1_venue_adjustment": projection["team1_venue_adjustment"],
        "team2_venue_adjustment": projection["team2_venue_adjustment"],
        "team1_lineup_adjustment": projection["team1_lineup_adjustment"],
        "team2_lineup_adjustment": projection["team2_lineup_adjustment"],
        "team1_matched_starters": team1_lineup.get("matched_starters", ""),
        "team2_matched_starters": team2_lineup.get("matched_starters", ""),
        "team1_formation": team1_lineup.get("formation", ""),
        "team2_formation": team2_lineup.get("formation", ""),
        "temperature_c": weather.get("temperature_c", ""),
        "weather_goal_factor": weather.get("weather_goal_factor", ""),
        "weather_note": weather.get("weather_note", ""),
        "actual_90min_result": provider["actual_90min_result"],
        "pick_correct": pick_correct,
    }


def postmatch_row_for_fixture(fixture: dict[str, Any], prediction: dict[str, Any], provider: dict[str, Any]) -> dict[str, Any]:
    is_final = provider["provider_status"] in FINAL_STATUSES
    return {
        "fixture_key": fixture["fixture_key"],
        "date": fixture["date"],
        "team1": fixture["team1"],
        "team2": fixture["team2"],
        "provider_status": provider["provider_status"],
        "is_final": is_final,
        "live_score": provider.get("live_score", ""),
        "actual_90min_result": provider["actual_90min_result"] if is_final else "",
        "model_90min_pick": prediction["model_90min_pick"],
        "pick_correct": prediction["pick_correct"] if is_final else "",
        "scoring_status": "scored" if is_final else "pending_final_whistle",
    }


def data_quality_row(
    fixture: dict[str, Any],
    provider: dict[str, Any],
    weather: dict[str, Any],
    lineup_context: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    team1 = v2.normalize_team(fixture["team1"])
    team2 = v2.normalize_team(fixture["team2"])
    has_lineups = bool(lineup_context.get(team1) or lineup_context.get(team2))
    missing = []
    if not provider["provider_found"]:
        missing.append("provider_fixture")
    if not weather.get("weather_found"):
        missing.append("weather")
    if provider["provider_status"] in road24.ACTIVE_OR_FINAL_STATUSES and not has_lineups:
        missing.append("confirmed_lineups")
    missing.append("odds_feed")
    missing.append("injury_feed")
    score = 100
    penalties = {"provider_fixture": 35, "weather": 8, "confirmed_lineups": 18, "odds_feed": 10, "injury_feed": 12}
    for item in missing:
        score -= penalties.get(item, 0)
    return {
        "fixture_key": fixture["fixture_key"],
        "team1": fixture["team1"],
        "team2": fixture["team2"],
        "provider_status": provider["provider_status"],
        "provider_found": provider["provider_found"],
        "weather_found": weather.get("weather_found", False),
        "confirmed_lineups_available": has_lineups,
        "odds_available": False,
        "injuries_available": False,
        "data_quality_score": max(0, score),
        "missing_inputs": ";".join(missing),
    }


def build_live_tables(args: argparse.Namespace) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    fixtures = tracked_fixtures()
    provider_by_date, provider_errors = fetch_provider_rows_by_date(fixtures, args)
    power_rows = road24.build_match_power_rows()
    weather_by_fixture = build_weather_context(fixtures, args)
    player_lookup = friend24.load_player_impact_lookup()
    expected_xi_scores = friend24.load_expected_xi_scores()

    fixture_rows = []
    provider_rows = []
    lineup_rows = []
    availability_rows = []
    odds_rows = []
    prediction_rows = []
    postmatch_rows = []
    quality_rows = []

    for fixture in fixtures:
        provider = provider_summary_for_fixture(fixture, provider_by_date.get(fixture["date"], []), args)
        lineup_context, extracted_lineups = friend24.extract_lineup_context(fixture, provider, player_lookup, expected_xi_scores)
        weather = weather_by_fixture[fixture["fixture_key"]]
        projection = friend24.project_context_match(fixture, power_rows, weather, lineup_context)
        prediction = prediction_row_for_fixture(fixture, projection, provider, weather, lineup_context)

        fixture_rows.append(
            {
                "fixture_key": fixture["fixture_key"],
                "date": fixture["date"],
                "time_et": fixture["time_et"],
                "team1": fixture["team1"],
                "team2": fixture["team2"],
                "competition_context": fixture["competition_context"],
                "venue": fixture.get("venue", ""),
                "city": fixture.get("city", ""),
                "latitude": fixture.get("latitude", ""),
                "longitude": fixture.get("longitude", ""),
                "venue_edge_team": fixture.get("venue_edge_team", ""),
                "source": fixture.get("source", ""),
            }
        )
        provider_rows.append(fixture_status_row(fixture, provider))
        lineup_rows.extend(extracted_lineups)
        availability_rows.extend(availability_rows_for_fixture(fixture, lineup_context))
        odds_rows.extend(odds_rows_for_fixture(fixture))
        prediction_rows.append(prediction)
        postmatch_rows.append(postmatch_row_for_fixture(fixture, prediction, provider))
        quality_rows.append(data_quality_row(fixture, provider, weather, lineup_context))

    team_rows = build_team_strength_rows(fixtures, power_rows)
    weather_rows = [{**fixture, **weather_by_fixture[fixture["fixture_key"]]} for fixture in fixtures]

    return (
        {
            "fixtures": fixture_rows,
            "team_strength": team_rows,
            "provider_status": provider_rows,
            "lineups": lineup_rows,
            "availability": availability_rows,
            "weather": weather_rows,
            "odds": odds_rows,
            "predictions": prediction_rows,
            "postmatch": postmatch_rows,
            "quality": quality_rows,
        },
        provider_errors,
    )


def write_tables(tables: dict[str, list[dict[str, Any]]]) -> None:
    write_csv(
        FIXTURES_PATH,
        tables["fixtures"],
        ["fixture_key", "date", "time_et", "team1", "team2", "competition_context", "venue", "city", "latitude", "longitude", "venue_edge_team", "source"],
    )
    write_csv(
        TEAM_STRENGTH_PATH,
        tables["team_strength"],
        [
            "team",
            "normalized_team",
            "v25_match_power",
            "global_match_power",
            "raw_world_cup_v23_power",
            "profile_adjustment",
            "elo_score",
            "squad_score",
            "recent_form_score",
            "tactical_score",
            "availability_score",
            "market_score",
            "ceiling_score",
            "manager_score",
            "power_source",
            "squad_source",
            "manager_source",
        ],
    )
    write_csv(
        PROVIDER_STATUS_PATH,
        tables["provider_status"],
        [
            "fixture_key",
            "date",
            "time_et",
            "team1",
            "team2",
            "competition_context",
            "provider_found",
            "provider_fixture_id",
            "provider_league",
            "provider_status",
            "provider_status_long",
            "provider_home",
            "provider_away",
            "live_score",
            "provider_home_goals",
            "provider_away_goals",
            "actual_90min_result",
            "lineup_status",
            "lineups_count",
            "events_count",
            "statistics_count",
        ],
    )
    write_csv(
        LINEUPS_PATH,
        tables["lineups"],
        [
            "fixture_key",
            "provider_fixture_id",
            "team",
            "normalized_team",
            "formation",
            "starter_order",
            "player_name",
            "position",
            "number",
            "grid",
            "impact_score",
            "impact_match_status",
        ],
    )
    write_csv(
        AVAILABILITY_PATH,
        tables["availability"],
        [
            "fixture_key",
            "team",
            "normalized_team",
            "availability_score",
            "confirmed_lineup_available",
            "matched_starters",
            "total_starters",
            "lineup_power_adjustment",
            "provider_injury_status",
            "source_status",
            "note",
        ],
    )
    write_csv(
        WEATHER_PATH,
        tables["weather"],
        [
            "fixture_key",
            "date",
            "time_et",
            "team1",
            "team2",
            "venue",
            "city",
            "weather_found",
            "weather_error",
            "weather_time_utc",
            "temperature_c",
            "precipitation_probability",
            "wind_speed_kmh",
            "weather_score",
            "weather_goal_factor",
            "weather_note",
            "source",
        ],
    )
    write_csv(
        ODDS_PATH,
        tables["odds"],
        [
            "fixture_key",
            "team1",
            "team2",
            "odds_provider",
            "snapshot_time",
            "team1_decimal_odds",
            "draw_decimal_odds",
            "team2_decimal_odds",
            "team1_implied_probability",
            "draw_implied_probability",
            "team2_implied_probability",
            "odds_status",
            "note",
        ],
    )
    write_csv(
        PREDICTIONS_PATH,
        tables["predictions"],
        [
            "fixture_key",
            "date",
            "time_et",
            "team1",
            "team2",
            "competition_context",
            "provider_status",
            "live_score",
            "public_verdict",
            "confidence",
            "model_90min_pick",
            "model_reason",
            "team1_win_probability_internal",
            "draw_probability_internal",
            "team2_win_probability_internal",
            "team1_xg_internal",
            "team2_xg_internal",
            "team1_power",
            "team2_power",
            "power_diff_team1",
            "team1_venue_adjustment",
            "team2_venue_adjustment",
            "team1_lineup_adjustment",
            "team2_lineup_adjustment",
            "team1_matched_starters",
            "team2_matched_starters",
            "team1_formation",
            "team2_formation",
            "temperature_c",
            "weather_goal_factor",
            "weather_note",
            "actual_90min_result",
            "pick_correct",
        ],
    )
    write_csv(
        POSTMATCH_PATH,
        tables["postmatch"],
        ["fixture_key", "date", "team1", "team2", "provider_status", "is_final", "live_score", "actual_90min_result", "model_90min_pick", "pick_correct", "scoring_status"],
    )
    write_csv(
        QUALITY_PATH,
        tables["quality"],
        [
            "fixture_key",
            "team1",
            "team2",
            "provider_status",
            "provider_found",
            "weather_found",
            "confirmed_lineups_available",
            "odds_available",
            "injuries_available",
            "data_quality_score",
            "missing_inputs",
        ],
    )


def write_report(tables: dict[str, list[dict[str, Any]]], provider_errors: list[str], args: argparse.Namespace) -> None:
    snapshot = budget_snapshot(args.daily_limit, args.reserve_requests)
    predictions = tables["predictions"]
    quality = tables["quality"]
    final_rows = [row for row in tables["postmatch"] if row["is_final"]]
    provider_found = sum(1 for row in tables["provider_status"] if row["provider_found"])
    weather_found = sum(1 for row in tables["weather"] if row.get("weather_found"))
    lineups_found = sum(1 for row in quality if row["confirmed_lineups_available"])
    avg_quality = sum(safe_float(row["data_quality_score"]) for row in quality) / len(quality) if quality else 0.0

    lines = [
        "# Live Data Backbone v2.5",
        "",
        "V2.5 turns the live-data pilot into reusable model-ready tables. The prediction formula is still the v2.3/v2.4 engine; the upgrade is data structure, repeatability, and auditability.",
        "",
        "## Run Summary",
        "",
        f"- Tracked fixtures: {len(tables['fixtures'])}.",
        f"- Provider fixture matches found: {provider_found}/{len(tables['fixtures'])}.",
        f"- Weather rows available: {weather_found}/{len(tables['fixtures'])}.",
        f"- Fixtures with confirmed lineup context: {lineups_found}/{len(tables['fixtures'])}.",
        f"- Final fixtures ready for scoring: {len(final_rows)}.",
        f"- Average data-quality score: {avg_quality:.1f}/100.",
        "",
        "## API Budget",
        "",
        f"- Requests counted today: {snapshot['used_today']} / {snapshot['daily_limit']}.",
        f"- Reserve kept untouched: {snapshot['reserve_requests']}.",
        f"- Remaining before local stop: {snapshot['remaining_before_stop']}.",
    ]
    if provider_errors:
        lines.extend(["", "## Provider Errors", ""])
        for error in provider_errors:
            lines.append(f"- {error}")
    lines.extend(
        [
            "",
            "## Model-Ready Tables",
            "",
            "| Table | Rows | Purpose |",
            "|---|---:|---|",
            f"| v25_fixtures_live | {len(tables['fixtures'])} | Canonical fixture scope. |",
            f"| v25_team_strength_live | {len(tables['team_strength'])} | One current strength row per team. |",
            f"| v25_provider_status_live | {len(tables['provider_status'])} | API-Football fixture/status/result layer. |",
            f"| v25_confirmed_lineups_live | {len(tables['lineups'])} | Confirmed starters plus player-impact matching. |",
            f"| v25_player_availability_live | {len(tables['availability'])} | Availability contract; injuries still neutral/pending. |",
            f"| v25_weather_context_live | {len(tables['weather'])} | Match-hour temperature/rain/wind context. |",
            f"| v25_odds_snapshot_live | {len(tables['odds'])} | Odds contract; live odds not enabled yet. |",
            f"| v25_match_predictions_live | {len(tables['predictions'])} | Final v2.5 match calls. |",
            f"| v25_postmatch_results_live | {len(tables['postmatch'])} | Scoring table for final results. |",
            f"| v25_data_quality_live | {len(tables['quality'])} | Missing-input and quality audit. |",
            "",
            "## Current Calls",
            "",
            "| Match | Status | Live score | Verdict | Confidence | Pick | Data quality |",
            "|---|---|---|---|---|---|---:|",
        ]
    )
    quality_by_key = {row["fixture_key"]: row for row in quality}
    for row in predictions:
        quality_score = quality_by_key.get(row["fixture_key"], {}).get("data_quality_score", "")
        lines.append(
            f"| {row['team1']} vs {row['team2']} | {row['provider_status'] or 'not found'} | {row['live_score'] or ''} | {row['public_verdict']} | {row['confidence']} | {row['model_90min_pick']} | {quality_score} |"
        )
    lines.extend(
        [
            "",
            "## What v2.5 Still Does Not Solve",
            "",
            "- Injury/suspension data is tabled but not fully ingested yet.",
            "- Odds movement is tabled but not connected to a live odds feed yet.",
            "- Data refresh is manual; v2.6 should add scheduled refresh logic and stronger prediction updates.",
        ]
    )
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build model v2.5 live-data backbone tables.")
    parser.add_argument("--force-refresh", action="store_true", help="Force API-Football fixture/status refresh.")
    parser.add_argument("--force-weather", action="store_true", help="Force Open-Meteo weather refresh.")
    parser.add_argument("--daily-limit", type=int, default=V25_CONFIG["daily_api_limit"])
    parser.add_argument("--reserve-requests", type=int, default=V25_CONFIG["reserve_requests"])
    parser.add_argument("--fixture-ttl-hours", type=float, default=V25_CONFIG["fixture_ttl_hours"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tables, provider_errors = build_live_tables(args)
    write_tables(tables)
    config = dict(V25_CONFIG)
    config["run_timestamp_et"] = datetime.now(friend24.ET).isoformat()
    config["api_budget_snapshot"] = budget_snapshot(args.daily_limit, args.reserve_requests)
    config["force_refresh"] = args.force_refresh
    config["force_weather"] = args.force_weather
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(tables, provider_errors, args)
    print(
        json.dumps(
            {
                "fixtures": len(tables["fixtures"]),
                "provider_found": sum(1 for row in tables["provider_status"] if row["provider_found"]),
                "lineup_rows": len(tables["lineups"]),
                "weather_rows": len(tables["weather"]),
                "provider_errors": len(provider_errors),
                "budget": budget_snapshot(args.daily_limit, args.reserve_requests),
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )
    if provider_errors:
        sys.exit(2)


if __name__ == "__main__":
    main()
