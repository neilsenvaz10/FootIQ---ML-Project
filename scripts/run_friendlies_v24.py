#!/usr/bin/env python3
"""Run v2.4 live-data tests for selected international friendlies."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

import build_road_to_26_v24 as road24
import build_worldcup_model_v2 as v2
import build_worldcup_model_v23 as v23
from api_football_client_v24 import APIFootballError, budget_snapshot, cache_path, provider_get


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
WEATHER_CACHE = ROOT / "data" / "provider_cache" / "open_meteo"
NWS_WEATHER_CACHE = ROOT / "data" / "provider_cache" / "nws"

PREDICTIONS_PATH = PROCESSED / "friendlies_v24_predictions.csv"
PROVIDER_PATH = PROCESSED / "friendlies_v24_provider_fixture_matches.csv"
WEATHER_PATH = PROCESSED / "friendlies_v24_weather_context.csv"
LINEUPS_PATH = PROCESSED / "friendlies_v24_confirmed_lineups.csv"
REPORT_PATH = OUTPUTS / "friendlies_v24_report.md"
CONFIG_PATH = OUTPUTS / "friendlies_v24_config.json"

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
WEATHER_TTL_HOURS = 1.0

FRIENDLY_FIXTURES = [
    {
        "fixture_key": "friendly_2026_06_06_portugal_chile",
        "date": "2026-06-06",
        "time_et": "13:45",
        "team1": "Portugal",
        "team2": "Chile",
        "venue": "Lisbon - Oeiras",
        "city": "Oeiras, Portugal",
        "latitude": 38.7223,
        "longitude": -9.1393,
        "venue_edge_team": "Portugal",
        "source": "API-Football fixture feed",
    },
    {
        "fixture_key": "friendly_2026_06_06_germany_usa",
        "date": "2026-06-06",
        "time_et": "14:30",
        "team1": "Germany",
        "team2": "USA",
        "venue": "Soldier Field",
        "city": "Chicago, IL",
        "latitude": 41.8623,
        "longitude": -87.6167,
        "venue_edge_team": "USA",
        "source": "API-Football fixture feed",
    },
]


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


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def player_key(name: str) -> str:
    key = road24.strip_accents(name).lower()
    for old in [".", ",", "-", "_", "(", ")", "'", "\""]:
        key = key.replace(old, " ")
    return " ".join(key.split())


def load_player_impact_lookup() -> dict[str, dict[str, dict[str, Any]]]:
    lookup: dict[str, dict[str, dict[str, Any]]] = {}
    path = PROCESSED / "player_impact_v21.csv"
    if not path.exists():
        return lookup
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            team = v2.normalize_team(row.get("normalized_team") or row.get("team") or "")
            lookup.setdefault(team, {})[player_key(row.get("player_name", ""))] = row
    return lookup


def load_expected_xi_scores() -> dict[str, float]:
    scores: dict[str, float] = {}
    path = ROOT / "data" / "inputs" / "model_v21_team_profiles.csv"
    if not path.exists():
        return scores
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            team = v2.normalize_team(row.get("normalized_team") or row.get("team") or "")
            scores[team] = safe_float(row.get("expected_xi_score"), 0.0)
    return scores


def parse_match_datetime_et(fixture: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(f"{fixture['date']}T{fixture['time_et']}:00").replace(tzinfo=ET)


def weather_cache_path(fixture: dict[str, Any]) -> Path:
    return WEATHER_CACHE / f"{fixture['fixture_key']}.json"


def nws_weather_cache_path(fixture: dict[str, Any]) -> Path:
    return NWS_WEATHER_CACHE / f"{fixture['fixture_key']}.json"


def cache_is_fresh(path: Path, ttl_hours: float) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) <= ttl_hours * 3600


def fetch_open_meteo(fixture: dict[str, Any], *, force_refresh: bool = False) -> dict[str, Any]:
    path = weather_cache_path(fixture)
    if not force_refresh and cache_is_fresh(path, WEATHER_TTL_HOURS):
        return json.loads(path.read_text(encoding="utf-8"))

    match_utc = parse_match_datetime_et(fixture).astimezone(UTC)
    start_date = match_utc.date().isoformat()
    end_date = (match_utc.date() + timedelta(days=1)).isoformat()
    params = {
        "latitude": fixture["latitude"],
        "longitude": fixture["longitude"],
        "hourly": "temperature_2m,precipitation_probability,wind_speed_10m",
        "timezone": "UTC",
        "start_date": start_date,
        "end_date": end_date,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        reason = getattr(exc, "reason", str(exc))
        return {"error": f"Open-Meteo network error: {reason}", "fixture_key": fixture["fixture_key"]}

    path.parent.mkdir(parents=True, exist_ok=True)
    wrapped = {
        "fixture_key": fixture["fixture_key"],
        "fetched_at": datetime.now(ET).isoformat(),
        "weather_source": "Open-Meteo",
        "data": payload,
    }
    path.write_text(json.dumps(wrapped, indent=2, sort_keys=True), encoding="utf-8")
    return wrapped


def fetch_nws_hourly(fixture: dict[str, Any], *, force_refresh: bool = False) -> dict[str, Any]:
    """Fetch a U.S. NWS hourly forecast and normalize it to Open-Meteo's shape."""
    path = nws_weather_cache_path(fixture)
    if not force_refresh and cache_is_fresh(path, WEATHER_TTL_HOURS):
        return json.loads(path.read_text(encoding="utf-8"))

    headers = {
        "User-Agent": "WorldCupPredictionModel/2.9 (local research project)",
        "Accept": "application/geo+json",
    }
    latitude = float(fixture["latitude"])
    longitude = float(fixture["longitude"])
    points_url = f"https://api.weather.gov/points/{latitude:.4f},{longitude:.4f}"
    try:
        points_request = urllib.request.Request(points_url, headers=headers)
        with urllib.request.urlopen(points_request, timeout=15) as response:
            points = json.loads(response.read().decode("utf-8"))
        hourly_url = points.get("properties", {}).get("forecastHourly", "")
        if not hourly_url:
            raise ValueError("NWS points response did not include forecastHourly")
        hourly_request = urllib.request.Request(hourly_url, headers=headers)
        with urllib.request.urlopen(hourly_request, timeout=15) as response:
            forecast = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        reason = getattr(exc, "reason", str(exc))
        return {"error": f"NWS network error: {reason}", "fixture_key": fixture["fixture_key"]}

    times = []
    temperatures = []
    precipitation = []
    wind_speeds = []
    short_forecasts = []
    for period in forecast.get("properties", {}).get("periods", []):
        start = datetime.fromisoformat(period["startTime"]).astimezone(UTC)
        temp = safe_float(period.get("temperature"), 18.0)
        if str(period.get("temperatureUnit", "F")).upper() == "F":
            temp = (temp - 32.0) * 5.0 / 9.0
        rain = safe_float((period.get("probabilityOfPrecipitation") or {}).get("value"), 0.0)
        wind_values = [
            safe_float(value)
            for value in re.findall(r"\d+(?:\.\d+)?", str(period.get("windSpeed", "")))
        ]
        wind_mph = sum(wind_values) / len(wind_values) if wind_values else 0.0
        times.append(start.replace(tzinfo=None).isoformat(timespec="minutes"))
        temperatures.append(round(temp, 2))
        precipitation.append(rain)
        wind_speeds.append(round(wind_mph * 1.60934, 2))
        short_forecasts.append(period.get("shortForecast", ""))

    if not times:
        return {"error": "NWS returned no hourly forecast periods.", "fixture_key": fixture["fixture_key"]}

    wrapped = {
        "fixture_key": fixture["fixture_key"],
        "fetched_at": datetime.now(ET).isoformat(),
        "weather_source": "U.S. National Weather Service",
        "short_forecasts": short_forecasts,
        "data": {
            "hourly": {
                "time": times,
                "temperature_2m": temperatures,
                "precipitation_probability": precipitation,
                "wind_speed_10m": wind_speeds,
            }
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(wrapped, indent=2, sort_keys=True), encoding="utf-8")
    return wrapped


def nearest_hour_weather(fixture: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("error"):
        return {
            "fixture_key": fixture["fixture_key"],
            "weather_found": False,
            "weather_error": payload["error"],
            "temperature_c": "",
            "precipitation_probability": "",
            "wind_speed_kmh": "",
            "weather_score": 100.0,
            "weather_goal_factor": 1.0,
            "weather_note": "Weather unavailable; neutral context applied.",
            "weather_source": payload.get("weather_source", ""),
        }
    hourly = payload.get("data", {}).get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return {
            "fixture_key": fixture["fixture_key"],
            "weather_found": False,
            "weather_error": "No hourly weather rows returned.",
            "temperature_c": "",
            "precipitation_probability": "",
            "wind_speed_kmh": "",
            "weather_score": 100.0,
            "weather_goal_factor": 1.0,
            "weather_note": "Weather unavailable; neutral context applied.",
            "weather_source": payload.get("weather_source", ""),
        }

    match_utc = parse_match_datetime_et(fixture).astimezone(UTC)
    candidates = []
    for idx, raw_time in enumerate(times):
        dt = datetime.fromisoformat(raw_time).replace(tzinfo=UTC)
        candidates.append((abs((dt - match_utc).total_seconds()), idx, dt))
    _, idx, matched_time = min(candidates)
    temp = safe_float((hourly.get("temperature_2m") or [None])[idx], 18.0)
    rain = safe_float((hourly.get("precipitation_probability") or [None])[idx], 0.0)
    wind = safe_float((hourly.get("wind_speed_10m") or [None])[idx], 0.0)

    heat_penalty = max(0.0, temp - 22.0) * 1.8
    cold_penalty = max(0.0, 8.0 - temp) * 1.2
    rain_penalty = rain * 0.08
    wind_penalty = max(0.0, wind - 20.0) * 0.35
    weather_score = max(55.0, min(103.0, 100.0 - heat_penalty - cold_penalty - rain_penalty - wind_penalty))
    weather_goal_factor = max(0.86, min(1.03, 1.0 - (100.0 - weather_score) * 0.004))
    if temp >= 30 and rain >= 45:
        note = "Hot conditions with meaningful rain/thunderstorm risk; lowers tempo and raises disruption risk."
    elif rain >= 45 or wind >= 24:
        note = "Weather friction from rain/wind; lowers scoring slightly."
    elif temp >= 26:
        note = "Warm conditions; lowers tempo slightly and nudges draw risk up."
    elif temp <= 8:
        note = "Cold conditions; modest tempo friction."
    else:
        note = "Comfortable weather; no meaningful penalty."
    return {
        "fixture_key": fixture["fixture_key"],
        "weather_found": True,
        "weather_error": "",
        "weather_time_utc": matched_time.isoformat(),
        "temperature_c": round(temp, 1),
        "precipitation_probability": round(rain, 1),
        "wind_speed_kmh": round(wind, 1),
        "weather_score": round(weather_score, 2),
        "weather_goal_factor": round(weather_goal_factor, 3),
        "weather_note": note,
        "weather_source": payload.get("weather_source", "Open-Meteo"),
    }


def weather_for_fixture(fixture: dict[str, Any], *, force_refresh: bool = False) -> dict[str, Any]:
    latitude = safe_float(fixture.get("latitude"), 0.0)
    longitude = safe_float(fixture.get("longitude"), 0.0)
    is_contiguous_us = 24.0 <= latitude <= 50.0 and -125.0 <= longitude <= -66.0
    fetchers = [fetch_nws_hourly, fetch_open_meteo] if is_contiguous_us else [fetch_open_meteo, fetch_nws_hourly]
    errors = []
    last_row: dict[str, Any] = {}
    for fetcher in fetchers:
        payload = fetcher(fixture, force_refresh=force_refresh)
        row = nearest_hour_weather(fixture, payload)
        if row.get("weather_found"):
            row["weather_error"] = "; ".join(errors)
            return row
        if row.get("weather_error"):
            errors.append(row["weather_error"])
        last_row = row
    last_row["weather_error"] = "; ".join(errors)
    return last_row


def build_weather_rows(fixtures: list[dict[str, Any]], *, force_refresh: bool) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for fixture in fixtures:
        rows[fixture["fixture_key"]] = weather_for_fixture(fixture, force_refresh=force_refresh)
    return rows


def project_context_match(
    fixture: dict[str, Any],
    power_rows: dict[str, dict[str, Any]],
    weather: dict[str, Any],
    lineup_context: dict[str, dict[str, Any]],
    *,
    venue_advantage_power: float = 1.5,
) -> dict[str, Any]:
    team1 = v2.normalize_team(fixture["team1"])
    team2 = v2.normalize_team(fixture["team2"])
    power1 = power_rows[team1]["v24_power_score"]
    power2 = power_rows[team2]["v24_power_score"]
    venue_team = v2.normalize_team(fixture.get("venue_edge_team", ""))
    team1_venue_adjustment = venue_advantage_power if venue_team == team1 else 0.0
    team2_venue_adjustment = venue_advantage_power if venue_team == team2 else 0.0
    team1_lineup_adjustment = safe_float(lineup_context.get(team1, {}).get("lineup_power_adjustment"), 0.0)
    team2_lineup_adjustment = safe_float(lineup_context.get(team2, {}).get("lineup_power_adjustment"), 0.0)
    adjusted_power1 = power1 + team1_venue_adjustment + team1_lineup_adjustment
    adjusted_power2 = power2 + team2_venue_adjustment + team2_lineup_adjustment
    lambda_1, lambda_2 = v23.expected_goals(adjusted_power1, adjusted_power2)
    goal_factor = safe_float(weather.get("weather_goal_factor"), 1.0)
    lambda_1 = max(0.25, lambda_1 * goal_factor)
    lambda_2 = max(0.25, lambda_2 * goal_factor)
    win_1, draw, win_2 = v2.scoreline_probabilities(lambda_1, lambda_2)
    projection = {
        "team1": team1,
        "team2": team2,
        "team1_power": adjusted_power1,
        "team2_power": adjusted_power2,
        "power_diff_team1": adjusted_power1 - adjusted_power2,
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
    if weather.get("weather_goal_factor", 1.0) < 0.95 and verdict != "Draw risk / no strong edge":
        reason = f"{reason} Weather lowers expected tempo slightly."
    return {
        **projection,
        "public_verdict": verdict,
        "confidence": confidence,
        "model_90min_pick": v23.model_pick_90min(projection),
        "model_reason": reason,
        "team1_base_power": power1,
        "team2_base_power": power2,
        "team1_venue_adjustment": team1_venue_adjustment,
        "team2_venue_adjustment": team2_venue_adjustment,
        "team1_lineup_adjustment": team1_lineup_adjustment,
        "team2_lineup_adjustment": team2_lineup_adjustment,
        "weather_goal_factor": goal_factor,
    }


def fetch_detail_counts(fixture_id: int, status_short: str, args: argparse.Namespace) -> dict[str, Any]:
    counts = {"lineups_count": "", "events_count": "", "statistics_count": "", "lineup_status": "not_requested"}
    if status_short not in road24.ACTIVE_OR_FINAL_STATUSES:
        counts["lineup_status"] = "not_started_no_confirmed_lineups"
        return counts
    endpoint_map = [
        ("fixtures/lineups", "lineups_count"),
        ("fixtures/events", "events_count"),
        ("fixtures/statistics", "statistics_count"),
    ]
    for endpoint, key in endpoint_map:
        try:
            result = provider_get(
                endpoint,
                {"fixture": fixture_id},
                ttl_hours=0.25,
                force_refresh=args.force_refresh,
                daily_limit=args.daily_limit,
                reserve_requests=args.reserve_requests,
            )
            counts[key] = len(result.response_rows)
        except APIFootballError:
            counts[key] = "provider_error"
    counts["lineup_status"] = "confirmed_or_provider_checked"
    return counts


def provider_summary_for_fixture(
    fixture: dict[str, Any],
    provider_rows: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    provider_match = road24.match_provider_fixture(fixture, provider_rows)
    summary = {
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
        "lineup_status": "provider_fixture_not_found",
    }
    if not provider_match:
        return summary
    fixture_block = provider_match.get("fixture", {})
    teams_block = provider_match.get("teams", {})
    goals_block = provider_match.get("goals", {})
    league_block = provider_match.get("league", {})
    status_block = fixture_block.get("status", {})
    fixture_id = fixture_block.get("id", "")
    status_short = status_block.get("short", "")
    detail_counts = fetch_detail_counts(int(fixture_id), status_short, args) if fixture_id else {}
    actual_90min_result = ""
    if status_short in road24.FINAL_STATUSES:
        actual_90min_result = road24.actual_result_label(
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
    summary.update(
        {
            "provider_found": True,
            "provider_fixture_id": fixture_id,
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
    return summary


def extract_lineup_context(
    fixture: dict[str, Any],
    provider: dict[str, Any],
    player_lookup: dict[str, dict[str, dict[str, Any]]],
    expected_xi_scores: dict[str, float],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not provider.get("provider_fixture_id"):
        return {}, []
    path = cache_path("fixtures/lineups", {"fixture": int(provider["provider_fixture_id"])})
    if not path.exists():
        return {}, []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, []
    lineups = payload.get("data", {}).get("response", [])
    context: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for team_block in lineups:
        team_name = team_block.get("team", {}).get("name", "")
        normalized_team = v2.normalize_team(team_name)
        formation = team_block.get("formation", "")
        impacts: list[float] = []
        matched_count = 0
        starters = team_block.get("startXI", []) or []
        for idx, entry in enumerate(starters, start=1):
            player = entry.get("player", {})
            name = player.get("name", "")
            impact_row = player_lookup.get(normalized_team, {}).get(player_key(name))
            impact_score = safe_float(impact_row.get("impact_score"), 0.0) if impact_row else 0.0
            match_status = "matched_player_impact_v21" if impact_row else "no_player_impact_match"
            if impact_row:
                matched_count += 1
                impacts.append(impact_score)
            rows.append(
                {
                    "fixture_key": fixture["fixture_key"],
                    "provider_fixture_id": provider["provider_fixture_id"],
                    "team": team_name,
                    "normalized_team": normalized_team,
                    "formation": formation,
                    "starter_order": idx,
                    "player_name": name,
                    "position": player.get("pos", ""),
                    "number": player.get("number", ""),
                    "grid": player.get("grid", ""),
                    "impact_score": round(impact_score, 3) if impact_row else "",
                    "impact_match_status": match_status,
                }
            )
        expected_xi = expected_xi_scores.get(normalized_team, 0.0)
        avg_impact = mean(impacts) if impacts else 0.0
        adjustment = 0.0
        if matched_count >= 6 and expected_xi:
            adjustment = clamp((avg_impact - expected_xi) * 0.06, -1.5, 1.5)
        context[normalized_team] = {
            "formation": formation,
            "matched_starters": matched_count,
            "total_starters": len(starters),
            "confirmed_xi_avg_impact": round(avg_impact, 3) if impacts else "",
            "expected_xi_score": round(expected_xi, 3) if expected_xi else "",
            "lineup_power_adjustment": round(adjustment, 3),
        }
    return context, rows


def build_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    fixtures = [dict(row) for row in FRIENDLY_FIXTURES]
    power_rows = road24.build_match_power_rows()
    weather_rows = build_weather_rows(fixtures, force_refresh=args.force_weather)
    player_lookup = load_player_impact_lookup()
    expected_xi_scores = load_expected_xi_scores()
    provider_errors: list[str] = []
    try:
        provider_result = provider_get(
            "fixtures",
            {"date": "2026-06-06", "timezone": "America/New_York"},
            ttl_hours=0.25,
            force_refresh=args.force_refresh,
            daily_limit=args.daily_limit,
            reserve_requests=args.reserve_requests,
        )
        provider_rows = provider_result.response_rows
    except APIFootballError as exc:
        provider_errors.append(str(exc))
        provider_rows = []

    predictions: list[dict[str, Any]] = []
    provider_out: list[dict[str, Any]] = []
    weather_out: list[dict[str, Any]] = []
    lineup_out: list[dict[str, Any]] = []
    for fixture in fixtures:
        weather = weather_rows[fixture["fixture_key"]]
        provider = provider_summary_for_fixture(fixture, provider_rows, args)
        lineup_context, lineup_rows = extract_lineup_context(fixture, provider, player_lookup, expected_xi_scores)
        projection = project_context_match(fixture, power_rows, weather, lineup_context)
        team1_norm = v2.normalize_team(fixture["team1"])
        team2_norm = v2.normalize_team(fixture["team2"])
        team1_lineup = lineup_context.get(team1_norm, {})
        team2_lineup = lineup_context.get(team2_norm, {})
        pick_correct = ""
        if provider["actual_90min_result"]:
            pick_correct = provider["actual_90min_result"] == projection["model_90min_pick"]
        row = {
            **fixture,
            "team1_power": round(projection["team1_power"], 3),
            "team2_power": round(projection["team2_power"], 3),
            "team1_base_power": round(projection["team1_base_power"], 3),
            "team2_base_power": round(projection["team2_base_power"], 3),
            "team1_venue_adjustment": projection["team1_venue_adjustment"],
            "team2_venue_adjustment": projection["team2_venue_adjustment"],
            "team1_lineup_adjustment": projection["team1_lineup_adjustment"],
            "team2_lineup_adjustment": projection["team2_lineup_adjustment"],
            "team1_lineup_matched_starters": team1_lineup.get("matched_starters", ""),
            "team2_lineup_matched_starters": team2_lineup.get("matched_starters", ""),
            "team1_confirmed_xi_avg_impact": team1_lineup.get("confirmed_xi_avg_impact", ""),
            "team2_confirmed_xi_avg_impact": team2_lineup.get("confirmed_xi_avg_impact", ""),
            "team1_formation": team1_lineup.get("formation", ""),
            "team2_formation": team2_lineup.get("formation", ""),
            "power_diff_team1": round(projection["power_diff_team1"], 3),
            "public_verdict": projection["public_verdict"],
            "confidence": projection["confidence"],
            "model_90min_pick": projection["model_90min_pick"],
            "model_reason": projection["model_reason"],
            "team1_win_probability_internal": round(projection["team1_win_probability"], 4),
            "draw_probability_internal": round(projection["draw_probability"], 4),
            "team2_win_probability_internal": round(projection["team2_win_probability"], 4),
            "team1_xg_internal": round(projection["team1_xg_internal"], 3),
            "team2_xg_internal": round(projection["team2_xg_internal"], 3),
            "temperature_c": weather.get("temperature_c", ""),
            "weather_score": weather.get("weather_score", ""),
            "weather_goal_factor": weather.get("weather_goal_factor", ""),
            "weather_note": weather.get("weather_note", ""),
            "provider_found": provider["provider_found"],
            "provider_fixture_id": provider["provider_fixture_id"],
            "provider_status": provider["provider_status"],
            "provider_status_long": provider["provider_status_long"],
            "live_score": provider["live_score"],
            "actual_90min_result": provider["actual_90min_result"],
            "pick_correct": pick_correct,
            "lineup_status": provider["lineup_status"],
            "lineups_count": provider["lineups_count"],
            "events_count": provider["events_count"],
            "statistics_count": provider["statistics_count"],
        }
        predictions.append(row)
        provider_out.append({**fixture, **provider})
        weather_out.append({**fixture, **weather})
        lineup_out.extend(lineup_rows)
    return predictions, provider_out, weather_out, lineup_out, provider_errors


def write_report(
    predictions: list[dict[str, Any]],
    provider_rows: list[dict[str, Any]],
    weather_rows: list[dict[str, Any]],
    lineup_rows: list[dict[str, Any]],
    provider_errors: list[str],
    args: argparse.Namespace,
) -> None:
    snapshot = budget_snapshot(args.daily_limit, args.reserve_requests)
    lines = [
        "# International Friendlies v2.4 Test",
        "",
        "This is an ad hoc v2.4 live-data run for Portugal-Chile and Germany-USA. It uses the same v2.3 match engine as the Road to 26 pilot, plus a small venue/weather context layer.",
        "",
        "## Run Plan",
        "",
        "- Use API-Football fixture feed for status, venue, and result tracking.",
        "- Pull lineups/events/statistics only if the provider marks a match active or final.",
        "- Pull Open-Meteo weather at match-hour coordinates.",
        "- Apply venue edge at +1.5 power for the local/host-side context.",
        "- Apply temperature/weather as a goal-tempo factor, not as a huge team-strength feature.",
        "- If confirmed lineups exist, apply a capped player-impact adjustment where v2.1 player ratings match the starters.",
        "",
        "## API Budget",
        "",
        f"- Requests counted today: {snapshot['used_today']} / {snapshot['daily_limit']}.",
        f"- Remaining before local stop: {snapshot['remaining_before_stop']}.",
    ]
    if provider_errors:
        lines.extend(["", "## Provider Errors", ""])
        for error in provider_errors:
            lines.append(f"- {error}")
    lines.extend(
        [
            "",
            "## Picks",
            "",
            "| Match | Status | Live score | Weather | Verdict | Confidence | Pick | Internal 1X2 | Lineup context |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in predictions:
        internal = (
            f"{row['team1']} {row['team1_win_probability_internal']:.2f} / "
            f"D {row['draw_probability_internal']:.2f} / "
            f"{row['team2']} {row['team2_win_probability_internal']:.2f}"
        )
        weather = f"{row['temperature_c']} C, factor {row['weather_goal_factor']}"
        lineup = (
            f"{row['team1']} {row['team1_lineup_adjustment']:+.2f} "
            f"({row['team1_lineup_matched_starters']}/11), "
            f"{row['team2']} {row['team2_lineup_adjustment']:+.2f} "
            f"({row['team2_lineup_matched_starters']}/11)"
        )
        lines.append(
            f"| {row['team1']} vs {row['team2']} | {row['provider_status'] or 'not found'} | {row['live_score'] or ''} | {weather} | {row['public_verdict']} | {row['confidence']} | {row['model_90min_pick']} | {internal} | {lineup} |"
        )
    lines.extend(
        [
            "",
            "## Weather Context",
            "",
            "| Match | Venue | Temp C | Rain % | Wind km/h | Weather score | Note |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in weather_rows:
        lines.append(
            f"| {row['team1']} vs {row['team2']} | {row['venue']} | {row.get('temperature_c', '')} | {row.get('precipitation_probability', '')} | {row.get('wind_speed_kmh', '')} | {row.get('weather_score', '')} | {row.get('weather_note', '')} |"
        )
    lines.extend(
        [
            "",
            "## Honest Read",
            "",
            "This is a genuine model run, but it is still not a confirmed-lineup model unless API-Football has lineups. If lineups are not available yet, player-level impact stays neutral and the model relies on team strength, recent form, venue, and weather context.",
        ]
    )
    if lineup_rows:
        lines.extend(["", "## Confirmed Starters", ""])
        grouped: dict[str, list[str]] = {}
        for row in lineup_rows:
            grouped.setdefault(f"{row['team']} ({row['formation']})", []).append(row["player_name"])
        for team, players in grouped.items():
            lines.append(f"- {team}: {', '.join(players)}")
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run selected international friendly predictions for model v2.4.")
    parser.add_argument("--force-refresh", action="store_true", help="Refresh API-Football fixture/status cache.")
    parser.add_argument("--force-weather", action="store_true", help="Refresh Open-Meteo weather cache.")
    parser.add_argument("--daily-limit", type=int, default=100)
    parser.add_argument("--reserve-requests", type=int, default=15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    predictions, provider_rows, weather_rows, lineup_rows, provider_errors = build_rows(args)
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
            "team1_base_power",
            "team2_base_power",
            "team1_venue_adjustment",
            "team2_venue_adjustment",
            "team1_lineup_adjustment",
            "team2_lineup_adjustment",
            "team1_lineup_matched_starters",
            "team2_lineup_matched_starters",
            "team1_confirmed_xi_avg_impact",
            "team2_confirmed_xi_avg_impact",
            "team1_formation",
            "team2_formation",
            "power_diff_team1",
            "public_verdict",
            "confidence",
            "model_90min_pick",
            "model_reason",
            "team1_win_probability_internal",
            "draw_probability_internal",
            "team2_win_probability_internal",
            "team1_xg_internal",
            "team2_xg_internal",
            "temperature_c",
            "weather_score",
            "weather_goal_factor",
            "weather_note",
            "provider_found",
            "provider_fixture_id",
            "provider_status",
            "provider_status_long",
            "live_score",
            "actual_90min_result",
            "pick_correct",
            "lineup_status",
            "lineups_count",
            "events_count",
            "statistics_count",
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
            "live_score",
            "actual_90min_result",
            "lineup_status",
            "lineups_count",
            "events_count",
            "statistics_count",
            "source",
        ],
    )
    write_csv(
        LINEUPS_PATH,
        lineup_rows,
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
        WEATHER_PATH,
        weather_rows,
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
    CONFIG_PATH.write_text(
        json.dumps(
            {
                "version": "v2.4",
                "run_timestamp_et": datetime.now(ET).isoformat(),
                "fixtures": FRIENDLY_FIXTURES,
                "api_budget_snapshot": budget_snapshot(args.daily_limit, args.reserve_requests),
                "weather_source": "Open-Meteo forecast API",
                "temperature_model": "Weather changes goal tempo via weather_goal_factor; venue context is +1.5 power for the local side.",
                "force_refresh": args.force_refresh,
                "force_weather": args.force_weather,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_report(predictions, provider_rows, weather_rows, lineup_rows, provider_errors, args)
    print(
        json.dumps(
            {
                "predictions": len(predictions),
                "provider_found": sum(1 for row in provider_rows if row["provider_found"]),
                "provider_errors": len(provider_errors),
                "report": str(REPORT_PATH.relative_to(ROOT)),
                "budget": budget_snapshot(args.daily_limit, args.reserve_requests),
            },
            indent=2,
        )
    )
    if provider_errors:
        sys.exit(2)


if __name__ == "__main__":
    main()
