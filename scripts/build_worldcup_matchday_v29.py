#!/usr/bin/env python3
"""World Cup matchday runner v2.9.

V2.9 moves the project from model output files to matchday operations:
- discover today's World Cup fixtures from API-Football
- enrich with local schedule metadata, venue/weather, and lineup availability
- score with the v2.7 ensemble
- label with the v2.8 confidence gate
- save a pre-match/latest snapshot for audit
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import build_confidence_gate_v28 as v28
import build_road_to_26_v24 as road24
import build_worldcup_model_v2 as v2
import model_bakeoff_v26 as v26
import run_ad_hoc_v27_slate as adhoc
from api_football_client_v24 import APIFootballError, budget_snapshot, provider_get


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
ET = ZoneInfo("America/New_York")

FEATURES_PATH = PROCESSED / "worldcup_matchday_v29_features.csv"
PREDICTIONS_PATH = PROCESSED / "worldcup_matchday_v29_predictions.csv"
LINEUPS_PATH = PROCESSED / "worldcup_matchday_v29_lineups.csv"
LINEUP_SNAPSHOTS_PATH = PROCESSED / "worldcup_matchday_v29_lineup_snapshots.csv"
SNAPSHOT_PATH = PROCESSED / "worldcup_matchday_v29_snapshots.csv"
REPORT_PATH = OUTPUTS / "worldcup_matchday_v29_report.md"
CONFIG_PATH = OUTPUTS / "worldcup_matchday_v29_config.json"
VERIFIED_KNOCKOUT_RESULTS_PATH = PROCESSED / "worldcup_2026_knockout_results_verified.csv"

VENUE_META = {
    "Mexico City": {
        "venue": "Estadio Azteca",
        "city": "Mexico City, Mexico",
        "latitude": 19.3029,
        "longitude": -99.1504,
        "altitude_m": 2240,
        "venue_edge_team": "Mexico",
    },
    "Guadalajara (Zapopan)": {
        "venue": "Estadio Akron",
        "city": "Guadalajara, Mexico",
        "latitude": 20.6819,
        "longitude": -103.4620,
        "venue_edge_team": "Mexico",
    },
    "Monterrey (Guadalupe)": {
        "venue": "Estadio BBVA",
        "city": "Monterrey, Mexico",
        "latitude": 25.6680,
        "longitude": -100.2443,
        "venue_edge_team": "Mexico",
    },
    "Toronto": {
        "venue": "BMO Field",
        "city": "Toronto, Canada",
        "latitude": 43.6332,
        "longitude": -79.4186,
        "venue_edge_team": "Canada",
    },
    "Vancouver": {
        "venue": "BC Place",
        "city": "Vancouver, Canada",
        "latitude": 49.2768,
        "longitude": -123.1119,
        "venue_edge_team": "Canada",
    },
    "Atlanta": {"venue": "Mercedes-Benz Stadium", "city": "Atlanta, GA", "latitude": 33.7554, "longitude": -84.4008, "venue_edge_team": "United States"},
    "Boston (Foxborough)": {"venue": "Gillette Stadium", "city": "Foxborough, MA", "latitude": 42.0909, "longitude": -71.2643, "venue_edge_team": "United States"},
    "Dallas (Arlington)": {"venue": "AT&T Stadium", "city": "Arlington, TX", "latitude": 32.7473, "longitude": -97.0945, "venue_edge_team": "United States"},
    "Houston": {"venue": "NRG Stadium", "city": "Houston, TX", "latitude": 29.6847, "longitude": -95.4107, "venue_edge_team": "United States"},
    "Kansas City": {"venue": "Arrowhead Stadium", "city": "Kansas City, MO", "latitude": 39.0490, "longitude": -94.4839, "venue_edge_team": "United States"},
    "Los Angeles (Inglewood)": {"venue": "SoFi Stadium", "city": "Inglewood, CA", "latitude": 33.9535, "longitude": -118.3392, "venue_edge_team": "United States"},
    "Miami (Miami Gardens)": {"venue": "Hard Rock Stadium", "city": "Miami Gardens, FL", "latitude": 25.9580, "longitude": -80.2389, "venue_edge_team": "United States"},
    "New York/New Jersey (East Rutherford)": {"venue": "MetLife Stadium", "city": "East Rutherford, NJ", "latitude": 40.8135, "longitude": -74.0745, "altitude_m": 2, "venue_edge_team": "United States"},
    "Philadelphia": {"venue": "Lincoln Financial Field", "city": "Philadelphia, PA", "latitude": 39.9008, "longitude": -75.1675, "venue_edge_team": "United States"},
    "San Francisco Bay Area (Santa Clara)": {"venue": "Levi's Stadium", "city": "Santa Clara, CA", "latitude": 37.4030, "longitude": -121.9700, "venue_edge_team": "United States"},
    "Seattle": {"venue": "Lumen Field", "city": "Seattle, WA", "latitude": 47.5952, "longitude": -122.3316, "venue_edge_team": "United States"},
}

V29_CONFIG = {
    "version": "v2.9",
    "purpose": "World Cup matchday runner with v2.7 probabilities and v2.8 confidence labels.",
    "provider": "API-Football",
    "weather_provider": "Open-Meteo",
    "lineup_note": "Lineups are collected when provider exposes them; v2.9 stores them but does not yet adjust model strength from lineups.",
}


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


def append_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def simple_key(value: str) -> str:
    return road24.simple_team_key(value)


def knockout_slot_code(value: str) -> str:
    normalized = value.strip()
    compact = re.fullmatch(r"([WL])(\d+)", normalized, flags=re.IGNORECASE)
    if compact:
        return f"{compact.group(1).upper()}{compact.group(2)}"
    wordy = re.fullmatch(r"(winner|loser)\s+(\d+)", normalized, flags=re.IGNORECASE)
    if wordy:
        prefix = "W" if wordy.group(1).lower() == "winner" else "L"
        return f"{prefix}{wordy.group(2)}"
    return ""


def is_knockout_placeholder(value: str) -> bool:
    return bool(knockout_slot_code(value))


def knockout_resolutions() -> dict[str, dict[str, str]]:
    return {
        row["fixture_id"]: row
        for row in read_csv(ROOT / "data" / "inputs" / "worldcup_2026_knockout_resolutions.csv")
        if row.get("fixture_id")
    }


def knockout_slot_resolutions() -> dict[str, str]:
    slots = {}
    for row in read_csv(VERIFIED_KNOCKOUT_RESULTS_PATH):
        fixture_id = row.get("fixture_id", "")
        team1 = row.get("team1", "")
        team2 = row.get("team2", "")
        winner = row.get("winner", "")
        if not fixture_id or not team1 or not team2 or not winner:
            continue
        winner_key = simple_key(winner)
        loser = ""
        if simple_key(team1) == winner_key:
            loser = team2
        elif simple_key(team2) == winner_key:
            loser = team1
        slots[f"W{fixture_id}"] = winner
        if loser:
            slots[f"L{fixture_id}"] = loser
    return slots


def resolve_knockout_slot(value: str) -> str:
    slot = knockout_slot_code(value)
    if not slot:
        return value
    return knockout_slot_resolutions().get(slot, value)


def resolve_knockout_teams(
    fixture_id: str,
    team1: str,
    team2: str,
) -> tuple[str, str]:
    resolution = knockout_resolutions().get(str(fixture_id), {})
    if not resolution:
        return resolve_knockout_slot(team1), resolve_knockout_slot(team2)
    if is_knockout_placeholder(team1) or is_knockout_placeholder(team2):
        return resolution["team1"], resolution["team2"]
    return team1, team2


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", simple_key(value)).strip("_")


def parse_provider_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


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


def world_cup_rows(provider_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in provider_rows:
        league = row.get("league", {})
        if league.get("name") == "World Cup":
            rows.append(row)
    rows.sort(key=lambda row: row.get("fixture", {}).get("date", ""))
    return rows


def local_match_lookup(date: str) -> dict[frozenset[str], dict[str, str]]:
    out = {}
    for row in read_csv(PROCESSED / "worldcup_2026_matches.csv"):
        if row.get("date") != date:
            continue
        key = frozenset({simple_key(row["team1"]), simple_key(row["team2"])})
        out[key] = row
    return out


def local_match_at_kickoff(date: str, kickoff: datetime) -> dict[str, str]:
    kickoff_et = kickoff.astimezone(ET).strftime("%H:%M")
    for row in read_csv(PROCESSED / "worldcup_2026_matches.csv"):
        if row.get("date") != date:
            continue
        if parse_local_kickoff(date, row.get("time", "")).strftime("%H:%M") == kickoff_et:
            return row
    return {}


def provider_summary_from_row(row: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    fixture_block = row.get("fixture", {})
    teams_block = row.get("teams", {})
    goals = row.get("goals", {})
    league = row.get("league", {})
    status = fixture_block.get("status", {})
    home = teams_block.get("home", {}).get("name", "")
    away = teams_block.get("away", {}).get("name", "")
    if is_knockout_placeholder(home) or is_knockout_placeholder(away):
        home = fixture["team1"]
        away = fixture["team2"]
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


def build_fixtures(date: str, provider_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    local = local_match_lookup(date)
    fixtures = []
    providers = {}
    for row in world_cup_rows(provider_rows):
        fixture_block = row.get("fixture", {})
        teams = row.get("teams", {})
        home = teams.get("home", {}).get("name", "")
        away = teams.get("away", {}).get("name", "")
        key = frozenset({simple_key(home), simple_key(away)})
        kickoff = parse_provider_datetime(fixture_block["date"])
        local_row = local.get(key) or local_match_at_kickoff(date, kickoff)
        home, away = resolve_knockout_teams(local_row.get("fixture_id", ""), home, away)
        if is_knockout_placeholder(home) or is_knockout_placeholder(away):
            continue
        ground = local_row.get("ground") or row.get("fixture", {}).get("venue", {}).get("city", "")
        venue_meta = VENUE_META.get(ground, {})
        provider_venue = fixture_block.get("venue", {})
        fixture_key = f"worldcup_{date.replace('-', '_')}_{slug(home)}_{slug(away)}"
        fixture = {
            "fixture_key": fixture_key,
            "fixture_id": local_row.get("fixture_id", ""),
            "date": date,
            "time_et": kickoff.strftime("%H:%M"),
            "team1": v2.display_team(v2.normalize_team(home)),
            "team2": v2.display_team(v2.normalize_team(away)),
            "competition_context": "World Cup",
            "group": (local_row.get("group") or "").replace("Group ", ""),
            "round": local_row.get("round", ""),
            "ground": ground,
            "venue": provider_venue.get("name") or venue_meta.get("venue", ""),
            "city": provider_venue.get("city") or venue_meta.get("city", ""),
            "latitude": venue_meta.get("latitude", ""),
            "longitude": venue_meta.get("longitude", ""),
            "altitude_m": venue_meta.get("altitude_m", 0),
            "venue_edge_team": venue_meta.get("venue_edge_team", ""),
            "source": "API-Football World Cup fixture feed + local tournament schedule",
        }
        fixtures.append(fixture)
        providers[fixture_key] = provider_summary_from_row(row, fixture)
    return fixtures, providers


def parse_local_kickoff(date: str, value: str) -> datetime:
    match = re.fullmatch(r"(\d{2}):(\d{2}) UTC([+-]\d{1,2})", value.strip())
    if not match:
        return datetime.fromisoformat(f"{date}T12:00:00").replace(tzinfo=ET)
    hour, minute, offset = match.groups()
    local_tz = timezone(timedelta(hours=int(offset)))
    kickoff = datetime.fromisoformat(f"{date}T{hour}:{minute}:00").replace(tzinfo=local_tz)
    return kickoff.astimezone(ET)


def build_local_fixtures(date: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Recover a matchday after it ages out of the provider's free date window."""
    fixtures = []
    providers = {}
    for local_row in read_csv(PROCESSED / "worldcup_2026_matches.csv"):
        if local_row.get("date") != date:
            continue
        ground = local_row.get("ground", "")
        venue_meta = VENUE_META.get(ground, {})
        team1 = v2.display_team(v2.normalize_team(local_row.get("team1", "")))
        team2 = v2.display_team(v2.normalize_team(local_row.get("team2", "")))
        team1, team2 = resolve_knockout_teams(local_row.get("fixture_id", ""), team1, team2)
        if is_knockout_placeholder(team1) or is_knockout_placeholder(team2):
            continue
        kickoff = parse_local_kickoff(date, local_row.get("time", ""))
        fixture_key = f"worldcup_{date.replace('-', '_')}_{slug(team1)}_{slug(team2)}"
        fixture = {
            "fixture_key": fixture_key,
            "fixture_id": local_row.get("fixture_id", ""),
            "date": date,
            "time_et": kickoff.strftime("%H:%M"),
            "team1": team1,
            "team2": team2,
            "competition_context": "World Cup",
            "group": (local_row.get("group") or "").replace("Group ", ""),
            "round": local_row.get("round", ""),
            "ground": ground,
            "venue": venue_meta.get("venue", ""),
            "city": venue_meta.get("city", ""),
            "latitude": venue_meta.get("latitude", ""),
            "longitude": venue_meta.get("longitude", ""),
            "altitude_m": venue_meta.get("altitude_m", 0),
            "venue_edge_team": venue_meta.get("venue_edge_team", ""),
            "source": "Local locked tournament schedule; provider date window unavailable",
        }
        fixtures.append(fixture)
        providers[fixture_key] = {
            "provider_found": False,
            "provider_fixture_id": "",
            "provider_league": "World Cup",
            "provider_status": "LOCAL",
            "provider_status_long": "Provider date unavailable; local schedule fallback",
            "provider_home": team1,
            "provider_away": team2,
            "live_score": "",
            "actual_90min_result": "",
        }
    fixtures.sort(key=lambda row: row["time_et"])
    return fixtures, providers


def fetch_lineups(provider_id: Any, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if provider_id in ("", None):
        return [], {"lineups_available": False, "lineups_count": 0, "lineup_status": "missing_provider_fixture_id"}
    try:
        result = provider_get(
            "fixtures/lineups",
            {"fixture": provider_id},
            ttl_hours=args.lineup_ttl_hours,
            force_refresh=args.force_lineups,
            daily_limit=args.daily_limit,
            reserve_requests=args.reserve_requests,
        )
    except APIFootballError as exc:
        return [], {"lineups_available": False, "lineups_count": 0, "lineup_status": f"provider_error:{exc}"}

    rows = []
    for team_row in result.response_rows:
        team = team_row.get("team", {})
        formation = team_row.get("formation", "")
        starters = team_row.get("startXI", []) or []
        starter_names = []
        for starter in starters:
            player = starter.get("player", {})
            starter_names.append(player.get("name", ""))
        rows.append(
            {
                "provider_fixture_id": provider_id,
                "team": team.get("name", ""),
                "formation": formation,
                "starter_count": len(starters),
                "starters": "; ".join(name for name in starter_names if name),
            }
        )
    return rows, {
        "lineups_available": bool(rows),
        "lineups_count": len(rows),
        "lineup_status": "available" if rows else "not_available_yet",
    }


def weather_for_fixture(fixture: dict[str, Any], force_refresh: bool) -> dict[str, Any]:
    return adhoc.weather_for_fixture(fixture, force_refresh)


def apply_lineup_quality(feature_rows: list[dict[str, Any]], lineup_summary: dict[str, dict[str, Any]]) -> None:
    for row in feature_rows:
        summary = lineup_summary.get(row["fixture_key"], {})
        row["lineups_available"] = summary.get("lineups_available", False)
        row["lineups_count"] = summary.get("lineups_count", 0)
        row["lineup_status"] = summary.get("lineup_status", "")
        if row["lineups_available"]:
            row["data_quality_score"] = min(95, safe_float(row["data_quality_score"], 78) + 10)


def apply_v28_gate(prediction_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in prediction_rows:
        gate = v28.classify_live_row(row)
        out.append(
            {
                **row,
                "v28_tier": gate["v28_tier"],
                "v28_pick": gate["v28_pick"],
                "v28_confidence": gate["v28_confidence"],
                "v28_reason": gate["v28_reason"],
                "v28_top_probability": gate["top_probability"],
                "v28_probability_gap": gate["probability_gap"],
            }
        )
    return out


def prediction_fieldnames() -> list[str]:
    return [
        "snapshot_timestamp_et",
        "fixture_key",
        "provider_fixture_id",
        "date",
        "time_et",
        "group",
        "round",
        "team1",
        "team2",
        "provider_status",
        "provider_home",
        "provider_away",
        "venue",
        "city",
        "lineups_available",
        "lineups_count",
        "lineup_status",
        "v28_tier",
        "v28_pick",
        "v28_confidence",
        "v28_reason",
        "v27_public_pick",
        "v27_internal_ensemble_pick",
        "ensemble_public_before_consensus",
        "logistic_public_before_consensus",
        "team1_win_probability",
        "draw_probability",
        "team2_win_probability",
        "predicted_score",
        "modal_score",
        "top_scorelines",
        "team1_xg",
        "team2_xg",
        "temperature_c",
        "weather_note",
        "data_quality_score",
        "missing_live_features",
        "live_score",
        "actual_90min_result",
    ]


def plain_best_read(row: dict[str, Any]) -> str:
    outcomes = {
        f"{row['team1']} win": safe_float(row.get("team1_win_probability")),
        "Draw": safe_float(row.get("draw_probability")),
        f"{row['team2']} win": safe_float(row.get("team2_win_probability")),
    }
    return max(outcomes, key=outcomes.get)


def write_report(
    *,
    date: str,
    snapshot_time: str,
    fixtures: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    provider_count: int,
    config: dict[str, Any],
) -> None:
    strong = sum(1 for row in predictions if row["v28_tier"] == "Strong Pick")
    lean = sum(1 for row in predictions if row["v28_tier"] == "Model Lean")
    passes = sum(1 for row in predictions if row["v28_tier"] == "Pass")
    weather_found = sum(1 for row in predictions if row.get("temperature_c") not in ("", None))
    lines = [
        "# World Cup Matchday Runner v2.9",
        "",
        f"Snapshot: {snapshot_time}",
        "",
        "## Run Summary",
        "",
        f"- Matchday date: {date}.",
        f"- World Cup provider fixtures found: {provider_count}.",
        f"- Fixtures scored: {len(predictions)}.",
        f"- Weather rows with temperature: {weather_found}/{len(predictions)}.",
        f"- Lineup team rows available: {len(lineups)}.",
        f"- Strong Picks: {strong}.",
        f"- Model Leans: {lean}.",
        f"- Passes: {passes}.",
        "",
        "## Predictions",
        "",
        "| Match | Kickoff ET | Status | Confidence gate | Best read | 1 | X | 2 | xG | Weather | Lineups |",
        "|---|---:|---|---|---|---:|---:|---:|---|---|---:|",
    ]
    for row in predictions:
        match = f"{row['team1']} vs {row['team2']}"
        weather = (
            f"{row['temperature_c']}C; {row.get('weather_note', '')}"
            if row.get("temperature_c") not in ("", None)
            else "unavailable"
        )
        xg = f"{row['team1_xg']}-{row['team2_xg']}"
        lines.append(
            f"| {match} | {row['time_et']} | {row['provider_status'] or 'not found'} | {row['v28_tier']} | {plain_best_read(row)} | "
            f"{safe_float(row['team1_win_probability']) * 100:.2f}% | {safe_float(row['draw_probability']) * 100:.2f}% | "
            f"{safe_float(row['team2_win_probability']) * 100:.2f}% | {xg} | {weather} | {row['lineups_count']} |"
        )
    lines.extend(
        [
            "",
            "## Operational Notes",
            "",
            "- This is the latest snapshot; validation selects the last eligible pre-kickoff snapshot when one exists.",
            "- v2.9 archives lineup availability and starter names; the separate v2.12 shadow layer applies bounded player-strength adjustments.",
            "- v2.8 `Model Lean` is directional; `Strong Pick` remains the stricter product-grade label.",
            "- `Best read` always states the likeliest 90-minute outcome. A `Pass` means that outcome is not separated enough to recommend confidently.",
            "- Weather uses the U.S. National Weather Service first for U.S. venues, with Open-Meteo as fallback; Open-Meteo remains primary elsewhere.",
            "- Exact-score distributions remain available to the backend probability engine but are intentionally hidden from public reports.",
            "",
            "## API Budget",
            "",
            f"- Used today: {config['api_budget']['used_today']}/{config['api_budget']['daily_limit']}.",
            f"- Remaining before local stop: {config['api_budget']['remaining_before_stop']}.",
        ]
    )
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    report_text = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    dated_report_path = OUTPUTS / f"worldcup_matchday_v29_report_{date}.md"
    dated_report_path.write_text(report_text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build v2.9 World Cup matchday predictions.")
    parser.add_argument("--date", default=datetime.now(ET).date().isoformat())
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--force-weather", action="store_true")
    parser.add_argument("--force-lineups", action="store_true")
    parser.add_argument("--skip-lineups", action="store_true")
    parser.add_argument("--daily-limit", type=int, default=100)
    parser.add_argument("--reserve-requests", type=int, default=15)
    parser.add_argument("--fixture-ttl-hours", type=float, default=0.1)
    parser.add_argument("--lineup-ttl-hours", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot_time = datetime.now(ET).isoformat(timespec="seconds")
    provider_error = ""
    try:
        provider_rows = fetch_provider_rows(args.date, args)
    except APIFootballError as exc:
        provider_rows = []
        provider_error = str(exc)
    fixtures, providers = build_fixtures(args.date, provider_rows)
    fixture_source = "provider"
    if not fixtures and provider_error:
        fixtures, providers = build_local_fixtures(args.date)
        fixture_source = "local_schedule_fallback"
    if not fixtures:
        raise APIFootballError(provider_error or f"No World Cup fixtures found for {args.date}")
    weather = {fixture["fixture_key"]: weather_for_fixture(fixture, args.force_weather) for fixture in fixtures}

    lineup_rows = []
    lineup_summary = {}
    for fixture in fixtures:
        if args.skip_lineups:
            lineup_summary[fixture["fixture_key"]] = {
                "lineups_available": False,
                "lineups_count": 0,
                "lineup_status": "skipped",
            }
            continue
        provider = providers[fixture["fixture_key"]]
        rows, summary = fetch_lineups(provider.get("provider_fixture_id"), args)
        for lineup_row in rows:
            lineup_row.update(
                {
                    "snapshot_timestamp_et": snapshot_time,
                    "fixture_key": fixture["fixture_key"],
                    "date": fixture["date"],
                    "time_et": fixture["time_et"],
                }
            )
        lineup_rows.extend(rows)
        lineup_summary[fixture["fixture_key"]] = summary

    feature_rows = adhoc.build_feature_rows(fixtures, providers, weather)
    apply_lineup_quality(feature_rows, lineup_summary)
    predictions = adhoc.build_predictions(fixtures, providers, weather, feature_rows)
    predictions = apply_v28_gate(predictions)

    fixture_meta = {fixture["fixture_key"]: fixture for fixture in fixtures}
    feature_meta = {row["fixture_key"]: row for row in feature_rows}
    latest_rows = []
    for row in predictions:
        fixture = fixture_meta.get(row["fixture_key"], {})
        feature = feature_meta.get(row["fixture_key"], {})
        latest_rows.append(
            {
                "snapshot_timestamp_et": snapshot_time,
                "group": fixture.get("group", ""),
                "round": fixture.get("round", ""),
                "lineups_available": feature.get("lineups_available", False),
                "lineups_count": feature.get("lineups_count", 0),
                "lineup_status": feature.get("lineup_status", ""),
                "live_score": feature.get("live_score", ""),
                "actual_90min_result": feature.get("actual_90min_result", ""),
                **row,
            }
        )

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
            "lineups_available",
            "lineups_count",
            "lineup_status",
        ],
    )
    write_csv(PREDICTIONS_PATH, latest_rows, prediction_fieldnames())
    append_csv(SNAPSHOT_PATH, latest_rows, prediction_fieldnames())
    lineup_fieldnames = [
        "snapshot_timestamp_et",
        "fixture_key",
        "provider_fixture_id",
        "date",
        "time_et",
        "team",
        "formation",
        "starter_count",
        "starters",
    ]
    write_csv(LINEUPS_PATH, lineup_rows, lineup_fieldnames)
    append_csv(LINEUP_SNAPSHOTS_PATH, lineup_rows, lineup_fieldnames)

    config = {
        **V29_CONFIG,
        "date": args.date,
        "snapshot_timestamp_et": snapshot_time,
        "api_budget": budget_snapshot(args.daily_limit, args.reserve_requests),
        "force_refresh": args.force_refresh,
        "force_weather": args.force_weather,
        "force_lineups": args.force_lineups,
        "skip_lineups": args.skip_lineups,
        "fixture_source": fixture_source,
        "provider_error": provider_error,
        "outputs": [
            str(PREDICTIONS_PATH.relative_to(ROOT)),
            str(FEATURES_PATH.relative_to(ROOT)),
            str(LINEUPS_PATH.relative_to(ROOT)),
            str(LINEUP_SNAPSHOTS_PATH.relative_to(ROOT)),
            str(SNAPSHOT_PATH.relative_to(ROOT)),
            str(REPORT_PATH.relative_to(ROOT)),
            str((OUTPUTS / f"worldcup_matchday_v29_report_{args.date}.md").relative_to(ROOT)),
        ],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(
        date=args.date,
        snapshot_time=snapshot_time,
        fixtures=fixtures,
        predictions=latest_rows,
        lineups=lineup_rows,
        provider_count=len(world_cup_rows(provider_rows)),
        config=config,
    )
    print(
        json.dumps(
            {
                "date": args.date,
                "fixtures": len(fixtures),
                "lineup_rows": len(lineup_rows),
                "tiers": Counter(row["v28_tier"] for row in latest_rows),
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
