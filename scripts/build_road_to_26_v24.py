#!/usr/bin/env python3
"""Road to 26 model v2.4 test runner.

This is the first live-data slice of the World Cup model:
- creates projections for the Road to 26 June 2026 fixtures
- optionally fetches API-Football fixture data with caching and a request budget
- writes model-ready CSVs and a compact report
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import build_worldcup_model_v2 as v2
import build_worldcup_model_v23 as v23
from api_football_client_v24 import (
    APIFootballError,
    MissingAPIKeyError,
    budget_snapshot,
    provider_get,
)


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

REPORT_PATH = OUTPUTS / "road_to_26_model_v24_report.md"
CONFIG_PATH = OUTPUTS / "road_to_26_model_v24_config.json"
FIXTURES_PATH = PROCESSED / "road_to_26_v24_fixtures.csv"
PREDICTIONS_PATH = PROCESSED / "road_to_26_v24_predictions.csv"
PROVIDER_PATH = PROCESSED / "road_to_26_v24_provider_fixture_matches.csv"

ROAD_TO_26_SOURCE = "https://roadto26.com/"
V24_CONFIG = {
    "version": "v2.4 live-data slice",
    "model_base": "World Cup model v2.3",
    "api_provider": "API-Football / API-Sports",
    "api_base_url": "https://v3.football.api-sports.io",
    "official_fixture_source": ROAD_TO_26_SOURCE,
    "daily_api_limit": 100,
    "reserve_requests": 15,
    "fixture_ttl_hours": 2.0,
    "detail_ttl_hours": 0.5,
    "friendly_confidence_cap": "Medium",
    "notes": [
        "No API key is stored in code; scripts read API_FOOTBALL_KEY from .env.",
        "Provider data is cached under data/provider_cache/api_football.",
        "This Road to 26 test uses the v2.3 match engine plus fallback ratings for teams outside the 2026 World Cup field.",
    ],
}

ROAD_TO_26_FIXTURES = [
    {
        "fixture_key": "road26_2026_06_06_bolivia_scotland",
        "date": "2026-06-06",
        "time_et": "16:00",
        "team1": "Bolivia",
        "team2": "Scotland",
        "venue": "Sports Illustrated Stadium",
        "city": "Harrison, NJ",
        "source": ROAD_TO_26_SOURCE,
    },
    {
        "fixture_key": "road26_2026_06_06_brazil_egypt",
        "date": "2026-06-06",
        "time_et": "18:00",
        "team1": "Brazil",
        "team2": "Egypt",
        "venue": "Huntington Bank Field",
        "city": "Cleveland, OH",
        "source": ROAD_TO_26_SOURCE,
    },
    {
        "fixture_key": "road26_2026_06_06_argentina_honduras",
        "date": "2026-06-06",
        "time_et": "20:00",
        "team1": "Argentina",
        "team2": "Honduras",
        "venue": "Kyle Field",
        "city": "College Station, TX",
        "source": ROAD_TO_26_SOURCE,
    },
    {
        "fixture_key": "road26_2026_06_07_morocco_norway",
        "date": "2026-06-07",
        "time_et": "15:00",
        "team1": "Morocco",
        "team2": "Norway",
        "venue": "Sports Illustrated Stadium",
        "city": "Harrison, NJ",
        "source": ROAD_TO_26_SOURCE,
    },
    {
        "fixture_key": "road26_2026_06_07_colombia_jordan",
        "date": "2026-06-07",
        "time_et": "19:00",
        "team1": "Colombia",
        "team2": "Jordan",
        "venue": "Snapdragon Stadium",
        "city": "San Diego, CA",
        "source": ROAD_TO_26_SOURCE,
    },
    {
        "fixture_key": "road26_2026_06_09_argentina_iceland",
        "date": "2026-06-09",
        "time_et": "20:30",
        "team1": "Argentina",
        "team2": "Iceland",
        "venue": "Jordan-Hare Stadium",
        "city": "Auburn, AL",
        "source": ROAD_TO_26_SOURCE,
    },
]

TEAM_NAME_ALIASES = {
    "usa": "united states",
    "u.s.a.": "united states",
    "united states of america": "united states",
    "ivory coast": "ivory coast",
    "cote d ivoire": "ivory coast",
    "cote divoire": "ivory coast",
    "czechia": "czech republic",
    "korea republic": "south korea",
    "south korea": "south korea",
    "turkiye": "turkey",
    "cape verde islands": "cape verde",
    "cabo verde": "cape verde",
    "congo dr": "dr congo",
    "democratic republic of the congo": "dr congo",
}

ACTIVE_OR_FINAL_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "FT", "AET", "PEN"}
FINAL_STATUSES = {"FT", "AET", "PEN"}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def simple_team_key(team: str) -> str:
    key = strip_accents(team).lower()
    for old in [".", ",", "-", "_", "(", ")", "'", "\""]:
        key = key.replace(old, " ")
    key = " ".join(key.split())
    return TEAM_NAME_ALIASES.get(key, key)


def normalized_team(team: str) -> str:
    return v2.normalize_team(team)


def percentile_lookup(values: dict[str, float]) -> dict[str, float]:
    return v2.percentile_scores(values)


def build_global_fallback_power() -> dict[str, dict[str, Any]]:
    elo_rows = read_csv(PROCESSED / "team_elo_latest.csv")
    form_rows = read_csv(PROCESSED / "team_recent_form_latest.csv")
    elo_values = {normalized_team(row["team"]): safe_float(row, "elo_rating") for row in elo_rows}
    form_values = {
        normalized_team(row["team"]): safe_float(row, "weighted_ppg_last_5") * 18.0 + safe_float(row, "weighted_goal_diff_last_5") * 6.0
        for row in form_rows
    }
    elo_scores = percentile_lookup(elo_values)
    form_scores = percentile_lookup(form_values)
    rows: dict[str, dict[str, Any]] = {}
    weights = v23.V23_CONFIG["weights"]
    for team, elo_score in elo_scores.items():
        squad_override = v2.SQUAD_OVERRIDES.get(team)
        if squad_override:
            squad_score = squad_override[0] * 0.45 + squad_override[1] * 0.35 + squad_override[2] * 0.20
            squad_source = "v2_squad_override"
        else:
            squad_score = 50.0 + (elo_score - 50.0) * 0.35
            squad_source = "elo_proxy_neutral"
        manager_override = v2.MANAGER_OVERRIDES.get(team)
        if manager_override:
            manager_score = manager_override[1] * 0.65 + manager_override[2] * 0.35
            manager_source = "v2_manager_override"
        else:
            manager_score = v23.V23_CONFIG["unknown_manager_neutral_score"]
            manager_source = "neutral_unknown"
        recent_score = form_scores.get(team, 50.0)
        tactical_score = 50.0
        availability_score = 100.0
        market_score = 50.0
        ceiling_score = 88.0 if elo_score >= 94 else 78.0 if elo_score >= 86 else 64.0 if elo_score >= 72 else 50.0
        power = (
            elo_score * weights["elo_score"]
            + squad_score * weights["squad_score"]
            + recent_score * weights["recent_form_score"]
            + tactical_score * weights["tactical_score"]
            + availability_score * weights["availability_score"]
            + market_score * weights["market_score"]
            + ceiling_score * weights["ceiling_score"]
            + manager_score * weights["manager_score"]
        )
        rows[team] = {
            "team": team,
            "display_team": v2.display_team(team),
            "v24_power_score": round(power, 3),
            "global_match_power": round(power, 3),
            "raw_v23_power": "",
            "profile_adjustment": 0.0,
            "power_source": "global_elo_recent_fallback",
            "elo_score": round(elo_score, 3),
            "squad_score": round(squad_score, 3),
            "recent_form_score": round(recent_score, 3),
            "tactical_score": tactical_score,
            "availability_score": availability_score,
            "market_score": market_score,
            "ceiling_score": ceiling_score,
            "manager_score": round(manager_score, 3),
            "squad_source": squad_source,
            "manager_source": manager_source,
        }
    return rows


def build_match_power_rows() -> dict[str, dict[str, Any]]:
    fallback = build_global_fallback_power()
    world_cup_rows = {normalized_team(row["team"]): row for row in read_csv(PROCESSED / "model_v23_team_power.csv")}
    out = dict(fallback)
    for team, row in world_cup_rows.items():
        fallback_row = fallback.get(team, {})
        global_match_power = safe_float(fallback_row, "v24_power_score", safe_float(row, "v23_power_score"))
        raw_v23_power = safe_float(row, "v23_power_score", global_match_power)
        profile_adjustment = max(-4.0, min(4.0, (raw_v23_power - global_match_power) * 0.25))
        out[team] = {
            "team": team,
            "display_team": row["display_team"],
            "v24_power_score": round(global_match_power + profile_adjustment, 3),
            "global_match_power": round(global_match_power, 3),
            "raw_v23_power": round(raw_v23_power, 3),
            "profile_adjustment": round(profile_adjustment, 3),
            "power_source": "global_match_power_plus_capped_world_cup_profile",
            "elo_score": safe_float(row, "elo_score"),
            "squad_score": safe_float(row, "squad_score"),
            "recent_form_score": safe_float(row, "recent_form_score"),
            "tactical_score": safe_float(row, "tactical_score"),
            "availability_score": safe_float(row, "availability_score"),
            "market_score": safe_float(row, "market_score"),
            "ceiling_score": safe_float(row, "ceiling_score"),
            "manager_score": safe_float(row, "manager_score"),
            "squad_source": "player_impact_v21",
            "manager_source": row.get("manager_status_v23", ""),
        }
    return out


def scoreline_probs(lambda_a: float, lambda_b: float) -> tuple[float, float, float]:
    return v2.scoreline_probabilities(lambda_a, lambda_b)


def project_match(team1: str, team2: str, power_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    t1 = normalized_team(team1)
    t2 = normalized_team(team2)
    p1 = power_rows[t1]["v24_power_score"]
    p2 = power_rows[t2]["v24_power_score"]
    lambda_1, lambda_2 = v23.expected_goals(p1, p2)
    win_1, draw, win_2 = scoreline_probs(lambda_1, lambda_2)
    projection = {
        "team1": t1,
        "team2": t2,
        "team1_power": p1,
        "team2_power": p2,
        "power_diff_team1": p1 - p2,
        "team1_win_probability": win_1,
        "draw_probability": draw,
        "team2_win_probability": win_2,
        "team1_xg_internal": lambda_1,
        "team2_xg_internal": lambda_2,
    }
    verdict, confidence, reason = v23.public_verdict_v23(projection)
    if confidence == "High":
        confidence = "Medium"
        reason = f"{reason} Friendly rotation risk caps confidence."
    return {
        **projection,
        "public_verdict": verdict,
        "confidence": confidence,
        "model_reason": reason,
        "model_90min_pick": v23.model_pick_90min(projection),
    }


def match_provider_fixture(expected: dict[str, Any], provider_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    expected_set = {simple_team_key(expected["team1"]), simple_team_key(expected["team2"])}
    best: dict[str, Any] | None = None
    for row in provider_rows:
        teams = row.get("teams", {})
        home = teams.get("home", {}).get("name", "")
        away = teams.get("away", {}).get("name", "")
        provider_set = {simple_team_key(home), simple_team_key(away)}
        if provider_set == expected_set:
            return row
        if expected_set.intersection(provider_set) and row.get("fixture", {}).get("date", "").startswith(expected["date"]):
            best = row
    return best


def fetch_provider_fixture_rows(
    fixtures: list[dict[str, Any]],
    *,
    daily_limit: int,
    reserve_requests: int,
    force_refresh: bool,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    by_date: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    for date in sorted({fixture["date"] for fixture in fixtures}):
        try:
            result = provider_get(
                "fixtures",
                {"date": date, "timezone": "America/New_York"},
                ttl_hours=V24_CONFIG["fixture_ttl_hours"],
                force_refresh=force_refresh,
                daily_limit=daily_limit,
                reserve_requests=reserve_requests,
            )
            by_date[date] = result.response_rows
            if not by_date[date]:
                next_date = (datetime.fromisoformat(date).date() + timedelta(days=1)).isoformat()
                spillover = provider_get(
                    "fixtures",
                    {"date": next_date, "timezone": "America/New_York"},
                    ttl_hours=V24_CONFIG["fixture_ttl_hours"],
                    force_refresh=force_refresh,
                    daily_limit=daily_limit,
                    reserve_requests=reserve_requests,
                )
                by_date[date] = spillover.response_rows
        except (APIFootballError, MissingAPIKeyError) as exc:
            errors.append(f"{date}: {exc}")
            by_date[date] = []
    return by_date, errors


def fetch_fixture_detail_counts(
    fixture_id: int,
    status_short: str,
    *,
    daily_limit: int,
    reserve_requests: int,
    force_refresh: bool,
) -> dict[str, Any]:
    counts = {"lineups_count": "", "events_count": "", "statistics_count": ""}
    if status_short not in ACTIVE_OR_FINAL_STATUSES:
        return counts
    detail_endpoints = [
        ("fixtures/lineups", "lineups_count"),
        ("fixtures/events", "events_count"),
        ("fixtures/statistics", "statistics_count"),
    ]
    for endpoint, count_key in detail_endpoints:
        try:
            result = provider_get(
                endpoint,
                {"fixture": fixture_id},
                ttl_hours=V24_CONFIG["detail_ttl_hours"],
                force_refresh=force_refresh,
                daily_limit=daily_limit,
                reserve_requests=reserve_requests,
            )
            counts[count_key] = len(result.response_rows)
        except APIFootballError:
            counts[count_key] = "provider_error"
    return counts


def actual_result_label(home_goals: Any, away_goals: Any, home_name: str, away_name: str, expected_team1: str, expected_team2: str) -> str:
    if home_goals in ("", None) or away_goals in ("", None):
        return ""
    try:
        hg = int(home_goals)
        ag = int(away_goals)
    except (TypeError, ValueError):
        return ""
    if hg == ag:
        winner_key = "draw"
    elif hg > ag:
        winner_key = simple_team_key(home_name)
    else:
        winner_key = simple_team_key(away_name)
    if winner_key == "draw":
        return "draw"
    if winner_key == simple_team_key(expected_team1):
        return "team1_win"
    if winner_key == simple_team_key(expected_team2):
        return "team2_win"
    return ""


def build_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    fixtures = [dict(row) for row in ROAD_TO_26_FIXTURES]
    power_rows = build_match_power_rows()
    provider_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    provider_errors: list[str] = []
    if args.fetch_provider:
        provider_by_date, provider_errors = fetch_provider_fixture_rows(
            fixtures,
            daily_limit=args.daily_limit,
            reserve_requests=args.reserve_requests,
            force_refresh=args.force_refresh,
        )

    prediction_rows: list[dict[str, Any]] = []
    provider_rows_out: list[dict[str, Any]] = []
    for fixture in fixtures:
        projection = project_match(fixture["team1"], fixture["team2"], power_rows)
        t1 = normalized_team(fixture["team1"])
        t2 = normalized_team(fixture["team2"])
        provider_match = match_provider_fixture(fixture, provider_by_date.get(fixture["date"], []))
        provider_summary = {
            "provider_found": False,
            "provider_fixture_id": "",
            "provider_league": "",
            "provider_status": "",
            "provider_status_long": "",
            "provider_home": "",
            "provider_away": "",
        "provider_home_goals": "",
        "provider_away_goals": "",
        "live_score": "",
        "actual_90min_result": "",
            "lineups_count": "",
            "events_count": "",
            "statistics_count": "",
        }
        if provider_match:
            fixture_block = provider_match.get("fixture", {})
            teams_block = provider_match.get("teams", {})
            goals_block = provider_match.get("goals", {})
            league_block = provider_match.get("league", {})
            status_block = fixture_block.get("status", {})
            provider_fixture_id = fixture_block.get("id", "")
            status_short = status_block.get("short", "")
            detail_counts = {}
            if args.fetch_details and provider_fixture_id:
                detail_counts = fetch_fixture_detail_counts(
                    int(provider_fixture_id),
                    status_short,
                    daily_limit=args.daily_limit,
                    reserve_requests=args.reserve_requests,
                    force_refresh=args.force_refresh,
                )
            actual_90min_result = ""
            if status_short in FINAL_STATUSES:
                actual_90min_result = actual_result_label(
                    goals_block.get("home", ""),
                    goals_block.get("away", ""),
                    teams_block.get("home", {}).get("name", ""),
                    teams_block.get("away", {}).get("name", ""),
                    fixture["team1"],
                    fixture["team2"],
                )
            home_goals = goals_block.get("home", "")
            away_goals = goals_block.get("away", "")
            live_score = "" if home_goals in ("", None) or away_goals in ("", None) else f"{home_goals}-{away_goals}"
            provider_summary.update(
                {
                    "provider_found": True,
                    "provider_fixture_id": provider_fixture_id,
                    "provider_league": league_block.get("name", ""),
                    "provider_status": status_short,
                    "provider_status_long": status_block.get("long", ""),
                    "provider_home": teams_block.get("home", {}).get("name", ""),
                    "provider_away": teams_block.get("away", {}).get("name", ""),
                    "provider_home_goals": home_goals,
                    "provider_away_goals": away_goals,
                    "live_score": live_score,
                    "actual_90min_result": actual_90min_result,
                    **detail_counts,
                }
            )
        pick_correct = ""
        if provider_summary["actual_90min_result"]:
            pick_correct = provider_summary["actual_90min_result"] == projection["model_90min_pick"]
        prediction_rows.append(
            {
                **fixture,
                "team1_power": round(projection["team1_power"], 3),
                "team2_power": round(projection["team2_power"], 3),
                "power_diff_team1": round(projection["power_diff_team1"], 3),
                "team1_power_source": power_rows[t1]["power_source"],
                "team2_power_source": power_rows[t2]["power_source"],
                "public_verdict": projection["public_verdict"],
                "confidence": projection["confidence"],
                "model_90min_pick": projection["model_90min_pick"],
                "model_reason": projection["model_reason"],
                "team1_win_probability_internal": round(projection["team1_win_probability"], 4),
                "draw_probability_internal": round(projection["draw_probability"], 4),
                "team2_win_probability_internal": round(projection["team2_win_probability"], 4),
                "team1_xg_internal": round(projection["team1_xg_internal"], 3),
                "team2_xg_internal": round(projection["team2_xg_internal"], 3),
                "provider_found": provider_summary["provider_found"],
                "provider_fixture_id": provider_summary["provider_fixture_id"],
                "provider_status": provider_summary["provider_status"],
                "actual_90min_result": provider_summary["actual_90min_result"],
                "pick_correct": pick_correct,
            }
        )
        provider_rows_out.append({**fixture, **provider_summary})
    return fixtures, prediction_rows, provider_rows_out, provider_errors


def write_report(
    prediction_rows: list[dict[str, Any]],
    provider_rows: list[dict[str, Any]],
    provider_errors: list[str],
    args: argparse.Namespace,
) -> None:
    found_count = sum(1 for row in provider_rows if row["provider_found"])
    final_rows = [row for row in prediction_rows if row["actual_90min_result"]]
    correct_rows = [row for row in final_rows if row["pick_correct"] is True]
    snapshot = budget_snapshot(args.daily_limit, args.reserve_requests)
    lines = [
        "# Road to 26 Model v4 Test",
        "",
        "This is the first provider-connected test slice for the World Cup model. It uses the v2.3 match engine, cached API-Football fixture data where available, and global Elo/recent-form fallback ratings for teams outside the 48-team World Cup field.",
        "",
        "## API Budget",
        "",
        f"- Daily limit configured: {snapshot['daily_limit']}.",
        f"- Reserve kept untouched: {snapshot['reserve_requests']}.",
        f"- Requests counted today: {snapshot['used_today']}.",
        f"- Remaining before local stop: {snapshot['remaining_before_stop']}.",
        "",
        "## Provider Coverage",
        "",
        f"- Fixtures in Road to 26 test slate: {len(prediction_rows)}.",
        f"- API-Football fixture matches found: {found_count}.",
        f"- Finished fixtures available for scoring: {len(final_rows)}.",
    ]
    if final_rows:
        accuracy = 100 * len(correct_rows) / len(final_rows)
        lines.append(f"- Current pick accuracy on finished fixtures: {accuracy:.1f}%.")
    if provider_errors:
        lines.extend(["", "## Provider Errors", ""])
        for error in provider_errors:
            lines.append(f"- {error}")
    lines.extend(
        [
            "",
            "## Model Picks",
            "",
            "| Date | Match | Public verdict | Confidence | Pick | Provider status | Actual | Correct |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in prediction_rows:
        match = f"{row['team1']} vs {row['team2']}"
        lines.append(
            f"| {row['date']} {row['time_et']} ET | {match} | {row['public_verdict']} | {row['confidence']} | {row['model_90min_pick']} | {row['provider_status'] or 'not fetched/found'} | {row['actual_90min_result'] or ''} | {row['pick_correct']} |"
        )
    lines.extend(
        [
            "",
            "## How To Use This",
            "",
            "- Run before kickoff to get the model pick and provider fixture ID.",
            "- Run again after full time to capture the actual result and update the accuracy columns.",
            "- Keep details fetch enabled on matchday; lineups/events/statistics are only requested when API-Football marks the fixture active or final.",
            "",
            "## Caveat",
            "",
            "Friendlies are noisier than competitive matches because teams rotate squads, test shapes, and manage minutes. For that reason, v4 caps public confidence at Medium even when the raw model likes a favorite strongly.",
        ]
    )
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Road to 26 model v2.4 predictions.")
    parser.add_argument("--fetch-provider", action="store_true", help="Fetch API-Football fixture data.")
    parser.add_argument("--fetch-details", action="store_true", help="Fetch lineups/events/statistics for active/final fixtures.")
    parser.add_argument("--force-refresh", action="store_true", help="Ignore cache freshness and spend fresh requests.")
    parser.add_argument("--daily-limit", type=int, default=V24_CONFIG["daily_api_limit"])
    parser.add_argument("--reserve-requests", type=int, default=V24_CONFIG["reserve_requests"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fixtures, predictions, provider_rows, provider_errors = build_rows(args)
    write_csv(
        FIXTURES_PATH,
        fixtures,
        ["fixture_key", "date", "time_et", "team1", "team2", "venue", "city", "source"],
    )
    write_csv(
        PREDICTIONS_PATH,
        predictions,
        [
            "fixture_key",
            "date",
            "time_et",
            "team1",
            "team2",
            "venue",
            "city",
            "team1_power",
            "team2_power",
            "power_diff_team1",
            "team1_power_source",
            "team2_power_source",
            "public_verdict",
            "confidence",
            "model_90min_pick",
            "model_reason",
            "team1_win_probability_internal",
            "draw_probability_internal",
            "team2_win_probability_internal",
            "team1_xg_internal",
            "team2_xg_internal",
            "provider_found",
            "provider_fixture_id",
            "provider_status",
            "actual_90min_result",
            "pick_correct",
            "source",
        ],
    )
    write_csv(
        PROVIDER_PATH,
        provider_rows,
        [
            "fixture_key",
            "date",
            "time_et",
            "team1",
            "team2",
            "venue",
            "city",
            "provider_found",
            "provider_fixture_id",
            "provider_league",
            "provider_status",
            "provider_status_long",
            "provider_home",
            "provider_away",
            "provider_home_goals",
            "provider_away_goals",
            "actual_90min_result",
            "lineups_count",
            "events_count",
            "statistics_count",
            "source",
        ],
    )
    config = dict(V24_CONFIG)
    config["run_timestamp"] = datetime.now().isoformat(timespec="seconds")
    config["fetch_provider"] = args.fetch_provider
    config["fetch_details"] = args.fetch_details
    config["force_refresh"] = args.force_refresh
    config["api_budget_snapshot"] = budget_snapshot(args.daily_limit, args.reserve_requests)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(predictions, provider_rows, provider_errors, args)
    print(
        json.dumps(
            {
                "fixtures": len(fixtures),
                "predictions": len(predictions),
                "provider_found": sum(1 for row in provider_rows if row["provider_found"]),
                "provider_errors": len(provider_errors),
                "budget": budget_snapshot(args.daily_limit, args.reserve_requests),
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )
    if provider_errors and args.fetch_provider:
        sys.exit(2)


if __name__ == "__main__":
    main()
