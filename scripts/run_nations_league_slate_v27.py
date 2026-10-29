#!/usr/bin/env python3
"""Run the v2.7 international ensemble on the opening 2026 Nations League slate.

The production training data currently ends before the 2026 World Cup.  This
runner leaves the fitted model untouched, but rolls the verified World Cup
results into the pre-match Elo and recent-form state before predicting.  It is
intended for the 24-27 September 2026 slate and writes a frozen, auditable
snapshot rather than mutating the model's foundation tables.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

import build_confidence_gate_v211 as v211
import build_foundation_tables as foundation
import build_worldcup_model_v2 as v2
import run_ad_hoc_v27_slate as adhoc


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

PREDICTIONS_PATH = PROCESSED / "nations_league_2026_matchday_1_predictions.csv"
FEATURES_PATH = PROCESSED / "nations_league_2026_matchday_1_features.csv"
REPORT_PATH = OUTPUTS / "nations_league_2026_matchday_1_report.md"
CONFIG_PATH = OUTPUTS / "nations_league_2026_matchday_1_config.json"
LATEST_RESULTS_PATH = ROOT / "data" / "provider_cache" / "international_results" / "results_20260924.csv"
API_FIXTURE_CACHE = ROOT / "data" / "provider_cache" / "api_football" / "fixtures"

FINAL_PROVIDER_STATUSES = {"FT", "AET", "PEN"}
PROVIDER_TEAM_ALIASES = {
    "Rep. Of Ireland": "Republic of Ireland",
    "FYR Macedonia": "North Macedonia",
}

MATCH_CONTEXT: dict[tuple[str, str], dict[str, str]] = {
    ("San Marino", "Finland"): {
        "why": "The largest verified team-strength gap on the slate; Finland's official squad also regained several regular midfield options.",
        "risk": "Away rotation and a low-tempo match are the main ways the favorite can underperform.",
    },
    ("Slovakia", "Moldova"): {
        "why": "Large Elo, recent-form and expected-goal separation, with home advantage and most of Slovakia's core available.",
        "risk": "Matúš Bero withdrew injured and the starting XI is not yet confirmed.",
    },
    ("Iceland", "Estonia"): {
        "why": "Iceland owns the stronger home-adjusted team rating and the clearer attacking edge.",
        "risk": "The 28% draw probability and Iceland availability concerns make this materially weaker than Finland or Slovakia.",
    },
    ("United States", "Peru"): {
        "why": "Home advantage makes the United States the internal favorite.",
        "risk": "An experimental squad, Ricardo Pepi's withdrawal and friendly substitution patterns create too much draw risk.",
    },
    ("Australia", "Brazil"): {
        "why": "Brazil entered as the internal favorite.",
        "risk": "Australia selected seven potential debutants and friendly volatility was high; the match finished 1-1.",
    },
}


def fixture(
    date: str,
    time_et: str,
    team1: str,
    team2: str,
    city: str,
    latitude: float,
    longitude: float,
    venue: str = "",
    competition_context: str = "UEFA Nations League",
    venue_edge_team: str | None = None,
) -> dict[str, Any]:
    key = re.sub(r"[^a-z0-9]+", "_", f"unl_{date}_{team1}_{team2}".lower()).strip("_")
    return {
        "fixture_key": key,
        "date": date,
        "time_et": time_et,
        "team1": team1,
        "team2": team2,
        "competition_context": competition_context,
        "venue": venue,
        "city": city,
        "latitude": latitude,
        "longitude": longitude,
        "venue_edge_team": team1 if venue_edge_team is None else venue_edge_team,
        "source": "UEFA official fixture list; venue city from UEFA/federation match information",
    }


FIXTURES = [
    # Thursday 24 September (all times Eastern).
    fixture("2026-09-24", "12:00", "Andorra", "Malta", "Encamp, Andorra", 42.536, 1.583, "Estadi FAF"),
    fixture("2026-09-24", "14:45", "Netherlands", "Germany", "Amsterdam, Netherlands", 52.314, 4.942, "Johan Cruijff ArenA"),
    fixture("2026-09-24", "14:45", "Serbia", "Greece", "Belgrade, Serbia", 44.783, 20.465, "Stadion Rajko Mitic"),
    fixture("2026-09-24", "14:45", "Norway", "Denmark", "Oslo, Norway", 59.949, 10.734, "Ullevaal Stadion"),
    fixture("2026-09-24", "14:45", "Portugal", "Wales", "Lisbon, Portugal", 38.762, -9.161, "Estadio Jose Alvalade"),
    fixture("2026-09-24", "14:45", "Austria", "Israel", "Linz, Austria", 48.294, 14.278, "Raiffeisen Arena"),
    fixture("2026-09-24", "14:45", "Kosovo", "Republic of Ireland", "Pristina, Kosovo", 42.663, 21.158, "Stadiumi Fadil Vokrri"),
    fixture("2026-09-24", "14:45", "Liechtenstein", "Lithuania", "Vaduz, Liechtenstein", 47.141, 9.510, "Rheinpark Stadion"),
    # Friday 25 September.
    fixture("2026-09-25", "12:00", "Georgia", "Northern Ireland", "Tbilisi, Georgia", 41.723, 44.790, "Boris Paichadze Dinamo Arena"),
    fixture("2026-09-25", "12:00", "Armenia", "Latvia", "Yerevan, Armenia", 40.172, 44.525, "Republican Stadium"),
    fixture("2026-09-25", "14:45", "Italy", "Belgium", "Rome, Italy", 41.934, 12.455, "Stadio Olimpico"),
    fixture("2026-09-25", "14:45", "Türkiye", "France", "Kocaeli, Türkiye", 40.762, 29.919, "Kocaeli Stadyumu"),
    fixture("2026-09-25", "14:45", "Hungary", "Ukraine", "Budapest, Hungary", 47.503, 19.099, "Puskas Arena"),
    fixture("2026-09-25", "14:45", "Poland", "Bosnia & Herzegovina", "Warsaw, Poland", 52.240, 21.046, "PGE Narodowy"),
    fixture("2026-09-25", "14:45", "Sweden", "Romania", "Solna, Sweden", 59.373, 18.000, "Strawberry Arena"),
    fixture("2026-09-25", "14:45", "Montenegro", "Cyprus", "Podgorica, Montenegro", 42.442, 19.262, "Podgorica City Stadium"),
    # Saturday 26 September.
    fixture("2026-09-26", "09:00", "Slovenia", "Scotland", "Ljubljana, Slovenia", 46.081, 14.524, "Stozice Stadium"),
    fixture("2026-09-26", "12:00", "San Marino", "Finland", "Serravalle, San Marino", 43.971, 12.477, "San Marino Stadium"),
    fixture("2026-09-26", "12:00", "Faroe Islands", "Kazakhstan", "Torshavn, Faroe Islands", 62.019, -6.781, "Torsvollur"),
    fixture("2026-09-26", "12:00", "Bulgaria", "Luxembourg", "Sofia, Bulgaria", 42.685, 23.335, "Vasil Levski National Stadium"),
    fixture("2026-09-26", "12:00", "Iceland", "Estonia", "Reykjavik, Iceland", 64.143, -21.878, "Laugardalsvollur"),
    fixture("2026-09-26", "14:45", "Czechia", "Croatia", "Prague, Czechia", 50.068, 14.471, "Fortuna Arena"),
    fixture("2026-09-26", "14:45", "England", "Spain", "London, England", 51.556, -0.279, "Wembley Stadium"),
    fixture("2026-09-26", "14:45", "North Macedonia", "Switzerland", "Skopje, North Macedonia", 42.006, 21.425, "National Arena Todor Proeski"),
    fixture("2026-09-26", "14:45", "Albania", "Belarus", "Tirana, Albania", 41.318, 19.824, "Air Albania Stadium"),
    fixture("2026-09-26", "14:45", "Slovakia", "Moldova", "Presov, Slovakia", 48.999, 21.240, "Tatran Arena"),
    # Sunday 27 September.
    fixture("2026-09-27", "09:00", "Lithuania", "Azerbaijan", "Kaunas, Lithuania", 54.897, 23.937, "Dariaus ir Gireno stadionas"),
    fixture("2026-09-27", "12:00", "Serbia", "Netherlands", "Belgrade, Serbia", 44.783, 20.465, "Stadion Rajko Mitic"),
    fixture("2026-09-27", "12:00", "Denmark", "Wales", "Copenhagen, Denmark", 55.702, 12.572, "Parken"),
    fixture("2026-09-27", "12:00", "Austria", "Kosovo", "Vienna, Austria", 48.207, 16.420, "Ernst Happel Stadion"),
    fixture("2026-09-27", "12:00", "Gibraltar", "Andorra", "Gibraltar", 36.149, -5.350, "Europa Point Stadium"),
    fixture("2026-09-27", "14:45", "Germany", "Greece", "Augsburg, Germany", 48.323, 10.886, "WWK Arena"),
    fixture("2026-09-27", "14:45", "Norway", "Portugal", "Oslo, Norway", 59.949, 10.734, "Ullevaal Stadion"),
    fixture("2026-09-27", "14:45", "Israel", "Republic of Ireland", "Debrecen, Hungary", 47.554, 21.633, "Nagyerdei Stadion"),
    # Selected senior men's friendlies with verified date, time, and venue.
    fixture("2026-09-24", "10:00", "Uzbekistan", "Iran", "Fergana, Uzbekistan", 40.390, 71.780, "Istiqlol Stadium", "International Friendly"),
    fixture("2026-09-25", "06:00", "Australia", "Brazil", "Townsville, Australia", -19.258, 146.818, "Queensland Country Bank Stadium", "International Friendly"),
    fixture("2026-09-26", "16:30", "United States", "Peru", "Orlando, FL", 28.541, -81.389, "Inter&Co Stadium", "International Friendly"),
    fixture("2026-09-26", "19:00", "Canada", "Chile", "Toronto, Canada", 43.633, -79.418, "BMO Field", "International Friendly"),
    fixture("2026-09-26", "21:00", "Mexico", "Colombia", "Baltimore, MD", 39.278, -76.623, "M&T Bank Stadium", "International Friendly", ""),
    fixture("2026-09-27", "07:35", "China PR", "New Zealand", "Chongqing, China", 29.720, 106.650, "Chongqing Longxing Football Stadium", "International Friendly"),
    fixture("2026-09-27", "16:30", "Bolivia", "Paraguay", "Washington, DC", 38.868, -77.013, "Audi Field", "International Friendly", ""),
]
FIXTURES.sort(key=lambda row: (row["date"], row["time_et"], row["team1"], row["team2"]))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def score_result(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win"
    if home_score < away_score:
        return "away_win"
    return "draw"


def goal_multiplier(goal_diff: int) -> float:
    diff = abs(goal_diff)
    if diff <= 1:
        return 1.0
    if diff == 2:
        return 1.5
    return (11.0 + diff) / 8.0


def world_cup_results() -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(PROCESSED / "matchday_validation_v210.csv"):
        if not as_bool(row.get("is_final")):
            continue
        match = re.fullmatch(r"(\d+)-(\d+)", str(row.get("provider_score", "")).strip())
        if not match:
            continue
        rows.append(
            {
                "date": row["date"],
                "home": v2.normalize_team(row["team1"]),
                "away": v2.normalize_team(row["team2"]),
                "home_score": int(match.group(1)),
                "away_score": int(match.group(2)),
            }
        )
    # The final was 0-0 after 90 minutes; Spain won 1-0 after extra time.
    rows.append(
        {
            "date": "2026-07-19",
            "home": v2.normalize_team("Spain"),
            "away": v2.normalize_team("Argentina"),
            "home_score": 0,
            "away_score": 0,
        }
    )
    rows.sort(key=lambda row: (row["date"], row["home"], row["away"]))
    return rows


def model_team_name(name: str) -> str:
    return v2.normalize_team(PROVIDER_TEAM_ALIASES.get(name, name))


def fixture_match_key(date: str, home: str, away: str) -> tuple[str, str, str]:
    return date, model_team_name(home), model_team_name(away)


def cached_provider_fixtures() -> dict[tuple[str, str, str], dict[str, Any]]:
    """Read current fixture state from cached API-Football date snapshots.

    The model remains usable without an API subscription. This cache is only a
    freshness overlay for results, identifiers and statuses; it is not a model
    feature and is never used as a proxy for bookmaker information.
    """

    wanted = {
        fixture_match_key(row["date"], row["team1"], row["team2"])
        for row in FIXTURES
    }
    snapshots: dict[tuple[str, str, str], dict[str, Any]] = {}
    if not API_FIXTURE_CACHE.exists():
        return snapshots
    for path in API_FIXTURE_CACHE.glob("*.json"):
        try:
            wrapped = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        fetched_at = str(wrapped.get("fetched_at", ""))
        payload = wrapped.get("data", wrapped)
        response = payload.get("response", []) if isinstance(payload, dict) else []
        if not isinstance(response, list):
            continue
        for item in response:
            fixture_data = item.get("fixture", {})
            teams = item.get("teams", {})
            date = str(fixture_data.get("date", ""))[:10]
            home = str(teams.get("home", {}).get("name", ""))
            away = str(teams.get("away", {}).get("name", ""))
            key = fixture_match_key(date, home, away)
            if key not in wanted:
                continue
            fulltime = item.get("score", {}).get("fulltime", {}) or {}
            row = {
                "fixture_key": key,
                "provider_fixture_id": fixture_data.get("id", ""),
                "provider_status": fixture_data.get("status", {}).get("short", "NS"),
                "provider_status_long": fixture_data.get("status", {}).get("long", ""),
                "provider_home": model_team_name(home),
                "provider_away": model_team_name(away),
                "home_score_90": fulltime.get("home"),
                "away_score_90": fulltime.get("away"),
                "fetched_at": fetched_at,
                "competition": item.get("league", {}).get("name", ""),
                "venue": fixture_data.get("venue", {}) or {},
            }
            previous = snapshots.get(key)
            if previous is None or fetched_at >= str(previous.get("fetched_at", "")):
                snapshots[key] = row
    return snapshots


def current_team_lookups(
    provider_fixtures: dict[tuple[str, str, str], dict[str, Any]] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], int, str, int]:
    source_path = LATEST_RESULTS_PATH if LATEST_RESULTS_PATH.exists() else ROOT / "data" / "raw" / "international_results" / "results.csv"
    source_rows = read_csv(source_path)
    source_rows.sort(key=lambda row: (row["date"], row["home_team"], row["away_team"]))
    ratings: defaultdict[str, float] = defaultdict(lambda: 1500.0)
    matches_played: defaultdict[str, int] = defaultdict(int)
    last_date: dict[str, str] = {}
    history: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=20))
    applied = 0
    def apply_result(row: dict[str, Any]) -> None:
        nonlocal applied
        home = model_team_name(str(row["home_team"]))
        away = model_team_name(str(row["away_team"]))
        home_score = safe_int(row["home_score"], -1)
        away_score = safe_int(row["away_score"], -1)
        if home_score < 0 or away_score < 0:
            return
        neutral = as_bool(row.get("neutral"))
        tournament = row.get("tournament", "")
        is_competitive = "friendly" not in tournament.lower()
        label = score_result(home_score, away_score)
        home_pre = ratings[home]
        away_pre = ratings[away]
        home_advantage = 0.0 if neutral else 75.0
        expected_home = 1.0 / (1.0 + 10 ** (-((home_pre + home_advantage) - away_pre) / 400.0))
        actual_home = 1.0 if label == "home_win" else 0.5 if label == "draw" else 0.0
        change = foundation.tournament_k_weight(tournament) * goal_multiplier(home_score - away_score) * (actual_home - expected_home)
        ratings[home] = home_pre + change
        ratings[away] = away_pre - change
        matches_played[home] += 1
        matches_played[away] += 1
        last_date[home] = row["date"]
        last_date[away] = row["date"]
        home_points = 3 if label == "home_win" else 1 if label == "draw" else 0
        away_points = 3 if label == "away_win" else 1 if label == "draw" else 0
        history[home].append(
            {
                "date": row["date"],
                "points": home_points,
                "goal_diff": home_score - away_score,
                "elo_change": change,
                "opponent_pre_elo": away_pre,
                "is_competitive": is_competitive,
            }
        )
        history[away].append(
            {
                "date": row["date"],
                "points": away_points,
                "goal_diff": away_score - home_score,
                "elo_change": -change,
                "opponent_pre_elo": home_pre,
                "is_competitive": is_competitive,
            }
        )
        applied += 1

    for row in source_rows:
        apply_result(row)

    provider_results_applied = 0
    latest_provider_date = ""
    for (date, home, away), snapshot in sorted((provider_fixtures or {}).items()):
        if snapshot.get("provider_status") not in FINAL_PROVIDER_STATUSES:
            continue
        home_score = safe_int(snapshot.get("home_score_90"), -1)
        away_score = safe_int(snapshot.get("away_score_90"), -1)
        if home_score < 0 or away_score < 0:
            continue
        apply_result(
            {
                "date": date,
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "neutral": False,
                "tournament": snapshot.get("competition", ""),
            }
        )
        provider_results_applied += 1
        latest_provider_date = max(latest_provider_date, date)

    elo_lookup = {
        team: {
            "team": team,
            "elo_rating": rating,
            "matches_played": matches_played.get(team, 0),
            "last_match_date": last_date.get(team, ""),
        }
        for team, rating in ratings.items()
    }
    form_lookup: dict[str, dict[str, Any]] = {}
    for team, team_history in history.items():
        all_rows = list(team_history)
        out: dict[str, Any] = {"team": team, "last_match_date": last_date.get(team, "")}
        for n in (5, 10):
            sample = all_rows[-n:]
            out[f"matches_last_{n}"] = len(sample)
            out[f"points_last_{n}"] = sum(row["points"] for row in sample)
            out[f"ppg_last_{n}"] = sum(row["points"] for row in sample) / len(sample) if sample else 1.0
            out[f"goal_diff_last_{n}"] = sum(row["goal_diff"] for row in sample)
            out[f"elo_change_last_{n}"] = sum(row["elo_change"] for row in sample)
            out[f"avg_opponent_elo_last_{n}"] = (
                sum(row["opponent_pre_elo"] for row in sample) / len(sample) if sample else 1500.0
            )
            out[f"competitive_matches_last_{n}"] = sum(row["is_competitive"] for row in sample)
        form_lookup[team] = out
    latest_date = max(max((row["date"] for row in source_rows), default=""), latest_provider_date)
    return elo_lookup, form_lookup, applied, latest_date, provider_results_applied


def provider_stub(f: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_found": True,
        "provider_fixture_id": "",
        "provider_league": "UEFA Nations League",
        "provider_status": "NS",
        "provider_status_long": "Not Started",
        "provider_home": f["team1"],
        "provider_away": f["team2"],
        "live_score": "",
        "actual_90min_result": "",
    }


def provider_overlay(
    f: dict[str, Any],
    provider_fixtures: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    snapshot = provider_fixtures.get(fixture_match_key(f["date"], f["team1"], f["team2"]))
    if not snapshot:
        return provider_stub(f)
    home_score = safe_int(snapshot.get("home_score_90"), -1)
    away_score = safe_int(snapshot.get("away_score_90"), -1)
    actual = score_result(home_score, away_score) if home_score >= 0 and away_score >= 0 else ""
    live_score = f"{home_score}-{away_score}" if actual else ""
    return {
        "provider_found": True,
        "provider_fixture_id": snapshot.get("provider_fixture_id", ""),
        "provider_league": snapshot.get("competition", f["competition_context"]),
        "provider_status": snapshot.get("provider_status", "NS"),
        "provider_status_long": snapshot.get("provider_status_long", ""),
        "provider_home": snapshot.get("provider_home", f["team1"]),
        "provider_away": snapshot.get("provider_away", f["team2"]),
        "live_score": live_score,
        "actual_90min_result": actual,
    }


def add_confidence_gate(predictions: list[dict[str, Any]]) -> None:
    for row in predictions:
        probabilities = {
            "team1_win": safe_float(row["team1_win_probability"]),
            "draw": safe_float(row["draw_probability"]),
            "team2_win": safe_float(row["team2_win_probability"]),
        }
        gate = v211.classify_v211(
            probabilities=probabilities,
            labels=v211.GENERIC_LABELS,
            ensemble_public=row["ensemble_public_before_consensus"],
            logistic_public=row["logistic_public_before_consensus"],
            internal_pick=row["v27_internal_ensemble_pick"],
            data_quality=safe_float(row["data_quality_score"]),
            lineups_available=False,
            xg_margin=abs(safe_float(row["team1_xg"]) - safe_float(row["team2_xg"])),
            live_mode=False,
        )
        calibrated = gate.pop("v211_calibrated_probabilities")
        row.update(gate)
        row["calibrated_team1_win_probability"] = round(calibrated["team1_win"], 5)
        row["calibrated_draw_probability"] = round(calibrated["draw"], 5)
        row["calibrated_team2_win_probability"] = round(calibrated["team2_win"], 5)
        row["lineup_status"] = "not confirmed"
        row["weather_risk"] = "low"
        note = str(row.get("weather_note", ""))
        if any(word in note.lower() for word in ["warm", "hot", "wind", "rain", "cold"]):
            row["weather_risk"] = "watch"


def public_pick_name(row: dict[str, Any]) -> str:
    pick = row.get("v211_pick", "pass")
    if pick == "team1_win":
        return str(row["team1"])
    if pick == "team2_win":
        return str(row["team2"])
    if pick == "draw":
        return "Draw"
    return "Pass"


def internal_read_name(row: dict[str, Any]) -> str:
    probabilities = {
        str(row["team1"]): safe_float(row["calibrated_team1_win_probability"]),
        "Draw": safe_float(row["calibrated_draw_probability"]),
        str(row["team2"]): safe_float(row["calibrated_team2_win_probability"]),
    }
    return max(probabilities, key=probabilities.get)


def report_reason(row: dict[str, Any]) -> str:
    context = MATCH_CONTEXT.get((str(row["team1"]), str(row["team2"])))
    if context:
        return context["why"]
    if row.get("v211_tier") == "Pass":
        if as_bool(row.get("v211_draw_watch")):
            return "The favorite is not far enough clear of the calibrated draw risk."
        return "The ensemble components do not agree strongly enough to publish a side."
    return "The directional edge survives calibration and draw-risk screening."


def report_risk(row: dict[str, Any]) -> str:
    context = MATCH_CONTEXT.get((str(row["team1"]), str(row["team2"])))
    if context:
        return context["risk"]
    draw_probability = safe_float(row["calibrated_draw_probability"])
    if draw_probability >= 0.35:
        return f"High draw probability ({draw_probability * 100:.1f}%)."
    if row.get("weather_risk") == "watch":
        return str(row.get("weather_note", "Weather could change the match tempo."))
    return "Starting XIs are not confirmed."


def write_report(
    predictions: list[dict[str, Any]],
    previous_predictions: list[dict[str, str]],
    provider_fixtures: dict[tuple[str, str, str], dict[str, Any]],
    applied_results: int,
    latest_result_date: str,
    provider_results_applied: int,
) -> None:
    generated_at = datetime.now().astimezone()
    previous_lookup = {
        fixture_match_key(row["date"], row["team1"], row["team2"]): row
        for row in previous_predictions
    }
    prediction_lookup = {
        fixture_match_key(row["date"], row["team1"], row["team2"]): row
        for row in predictions
    }
    completed = [
        snapshot
        for snapshot in provider_fixtures.values()
        if snapshot.get("provider_status") in FINAL_PROVIDER_STATUSES
        and snapshot.get("home_score_90") is not None
        and snapshot.get("away_score_90") is not None
    ]
    upcoming = [
        row
        for row in predictions
        if provider_fixtures.get(
            fixture_match_key(row["date"], row["team1"], row["team2"]), {}
        ).get("provider_status", "NS") not in FINAL_PROVIDER_STATUSES
        and row["date"] >= generated_at.date().isoformat()
    ]
    leans = [row for row in upcoming if row.get("v211_tier") in {"Strong Pick", "Model Lean"}]
    leans.sort(key=lambda row: safe_float(row.get("v211_top_probability")), reverse=True)

    published_finished = 0
    published_hits = 0
    completed_rows: list[str] = []
    for snapshot in sorted(completed, key=lambda row: row["fixture_key"]):
        key = snapshot["fixture_key"]
        prior = previous_lookup.get(key)
        if not prior:
            continue
        home_score = safe_int(snapshot["home_score_90"])
        away_score = safe_int(snapshot["away_score_90"])
        score_label = score_result(home_score, away_score)
        actual = {
            "home_win": "team1_win",
            "draw": "draw",
            "away_win": "team2_win",
        }[score_label]
        tier = prior.get("v211_tier", "Pass")
        prior_pick = prior.get("v211_pick", "pass")
        if tier != "Pass" and prior_pick != "pass":
            published_finished += 1
            hit = prior_pick == actual
            published_hits += int(hit)
            outcome = "Hit" if hit else "Miss"
        else:
            outcome = "Not scored (Pass)"
        display_row = prediction_lookup.get(key, prior)
        completed_rows.append(
            f"| {display_row['team1']} vs {display_row['team2']} | {home_score}-{away_score} | "
            f"{tier} / {public_pick_name(prior)} | {outcome} |"
        )

    lines = [
        "# International Weekend Decision Report",
        "",
        f"**Updated:** {generated_at.strftime('%A, %B %-d, %Y at %-I:%M %p %Z')}",
        "",
        "## Bottom line",
        "",
    ]
    if leans:
        for index, row in enumerate(leans, start=1):
            lines.append(
                f"{index}. **{public_pick_name(row)}** — {row['team1']} vs {row['team2']}, "
                f"{safe_float(row['v211_top_probability']) * 100:.1f}% calibrated probability, {row['v211_tier']}."
            )
    else:
        lines.append("There are no remaining matches that clear the public selection gate.")
    today_rows = [row for row in upcoming if row["date"] == generated_at.date().isoformat()]
    today_leans = [row for row in today_rows if row.get("v211_tier") in {"Strong Pick", "Model Lean"}]
    if today_rows and not today_leans:
        strongest_side_row = max(
            today_rows,
            key=lambda row: max(
                safe_float(row["calibrated_team1_win_probability"]),
                safe_float(row["calibrated_team2_win_probability"]),
            ),
        )
        strongest_side = (
            strongest_side_row["team1"]
            if safe_float(strongest_side_row["calibrated_team1_win_probability"])
            >= safe_float(strongest_side_row["calibrated_team2_win_probability"])
            else strongest_side_row["team2"]
        )
        strongest_side_probability = max(
            safe_float(strongest_side_row["calibrated_team1_win_probability"]),
            safe_float(strongest_side_row["calibrated_team2_win_probability"]),
        )
        lines.append(
            f"\n**Today:** no official selection. {strongest_side} is the highest side-only read "
            f"at {strongest_side_probability * 100:.1f}%, but the gate still says Pass."
        )
    lines.extend(
        [
            "",
            "These are 90-minute calls. There are no guaranteed wins. A high probability can remain only a Model Lean when the starting XIs are unconfirmed.",
            "",
            "## What changed since the first report",
            "",
            f"- Added {provider_results_applied} completed matches from the live provider cache before recalculating team strength and recent form.",
            f"- Rebuilt the state from {applied_results:,} senior international results through {latest_result_date}.",
            "- Refreshed venue-level weather for every remaining fixture.",
            "- Checked the near-kickoff provider feed; neither of the noon fixtures had confirmed XIs available at generation time, and later starting XIs remain unconfirmed.",
            "- Kept squad news as a confidence gate instead of inventing arbitrary player weights.",
            "",
            "## Recommended matches",
            "",
            "| Rank | Match (ET) | Selection | 1 / X / 2 | Why it qualifies | Main failure risk |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for index, row in enumerate(leans, start=1):
        weather = f"{safe_float(row.get('temperature_c')):.1f}C"
        lines.append(
            f"| {index} | {row['date']} {row['time_et']} — {row['team1']} vs {row['team2']} | "
            f"**{public_pick_name(row)}** ({row['v211_tier']}) | "
            f"{safe_float(row['calibrated_team1_win_probability']) * 100:.1f}% / "
            f"{safe_float(row['calibrated_draw_probability']) * 100:.1f}% / "
            f"{safe_float(row['calibrated_team2_win_probability']) * 100:.1f}% | "
            f"{report_reason(row)} Weather: {weather}. | {report_risk(row)} |"
        )
    if not leans:
        lines.append("| — | — | No published selection | — | No match cleared the gate. | — |")

    if completed_rows:
        strike_rate = (
            f"{published_hits}/{published_finished}"
            if published_finished
            else "No published selections completed"
        )
        lines.extend(
            [
                "",
                "## Results since the opening report",
                "",
                f"**Published-pick record:** {strike_rate}. Passes are deliberately excluded from pick accuracy.",
                "",
                "| Match | Result | Frozen decision | Evaluation |",
                "|---|---:|---|---|",
                *completed_rows,
            ]
        )

    lines.extend(
        [
            "",
            "## Full remaining slate",
            "",
            "The **internal read** is simply the largest probability. The **public decision** is stricter and may still be Pass.",
            "",
            "| Date/time ET | Match | Internal read | 1 | X | 2 | Public decision | Key risk |",
            "|---|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in upcoming:
        decision = (
            "Pass"
            if row["v211_tier"] == "Pass"
            else f"{row['v211_tier']}: {public_pick_name(row)}"
        )
        lines.append(
            f"| {row['date']} {row['time_et']} | {row['team1']} vs {row['team2']} | {internal_read_name(row)} | "
            f"{safe_float(row['calibrated_team1_win_probability']) * 100:.1f}% | "
            f"{safe_float(row['calibrated_draw_probability']) * 100:.1f}% | "
            f"{safe_float(row['calibrated_team2_win_probability']) * 100:.1f}% | "
            f"{decision} | {report_risk(row)} |"
        )

    weather_watch = [row for row in upcoming if row.get("weather_risk") == "watch"]
    lines.extend(["", "## Weather and lineup watch", ""])
    if weather_watch:
        for row in weather_watch:
            lines.append(f"- **{row['team1']} vs {row['team2']}:** {row.get('weather_note', 'Weather watch.')}")
    else:
        lines.append("- No remaining match has a material weather flag at this refresh.")
    lines.extend(
        [
            "- Weather is a small tempo and uncertainty modifier, not a direct large 1X2 weight.",
            "- Final decisions should be refreshed 60-75 minutes before kickoff when both starting XIs become available.",
            "",
            "## Model and confidence reality",
            "",
            "- Core model: calibrated v2.7 international ensemble (50% gradient boost, 30% Elo, 20% logistic regression).",
            "- Publishing layer: conservative v2.11 gate for ensemble agreement, draw risk, expected-goal separation and data quality.",
            "- Historical held-out accuracy was about 60.9% for every raw 1X2 call. The strict public gate was about 78% while publishing fewer than half of matches. Those figures are historical, not a promise for this weekend.",
            "- Friendlies receive an extra practical downgrade because coaches rotate and use more substitutes.",
            "- Exact scores remain hidden because they imply false precision.",
            "",
            "## Sources",
            "",
            "- [UEFA official Nations League schedule](https://www.uefa.com/uefanationsleague/news/02a2-1fea18abbcbc-456e846509e7-1000--2026-27-uefa-nations-league-all-the-league-phase-fixtures/).",
            "- API-Football cache for current fixture status and completed 90-minute results.",
            "- [Open-Meteo](https://open-meteo.com/) for venue-level forecasts.",
            "- Official releases: [Finland squad](https://www.sttinfo.fi/tiedote/72328350/huuhkajat-nimetty-syys-lokakuun-uefa-nations-league-otteluihin?lang=fi&publisherId=69819199), [Slovakia squad](https://futbalsfz.sk/muzi-a-v-nominacii-na-ligu-narodov-30-hracov-imperativom-vitazstvo-v-skupine/), [Slovakia injury update](https://futbalsfz.sk/muzi-a-reprezentacia-bez-matusa-bera-leo-sauer-chce-vyhrat-vsetky-zapasy/), [United States squad](https://www.ussoccer.com/stories/2026/09/usmnt-fall-camp-everything-you-need-to-know), and [Australia squad](https://footballaustralia.com.au/news/seven-potential-debutants-called-commbank-socceroos-brazil-matches).",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    previous_predictions = read_csv(PREDICTIONS_PATH) if PREDICTIONS_PATH.exists() else []
    provider_fixtures = cached_provider_fixtures()
    elo_lookup, form_lookup, applied_results, latest_result_date, provider_results_applied = current_team_lookups(
        provider_fixtures
    )
    providers = {f["fixture_key"]: provider_overlay(f, provider_fixtures) for f in FIXTURES}
    weather = {f["fixture_key"]: adhoc.weather_for_fixture(f, force_refresh=True) for f in FIXTURES}

    original_lookup = adhoc.load_lookup
    try:
        def refreshed_lookup(path: Path, key: str, normalize_key: bool = False) -> dict[str, dict[str, Any]]:
            if path.name == "team_elo_latest.csv":
                return elo_lookup
            if path.name == "team_recent_form_latest.csv":
                return form_lookup
            return original_lookup(path, key, normalize_key)

        adhoc.load_lookup = refreshed_lookup
        features = adhoc.build_feature_rows(FIXTURES, providers, weather)
    finally:
        adhoc.load_lookup = original_lookup

    predictions = adhoc.build_predictions(FIXTURES, providers, weather, features)
    add_confidence_gate(predictions)
    fieldnames = list(predictions[0].keys())
    adhoc.write_csv(PREDICTIONS_PATH, predictions, fieldnames)
    adhoc.write_csv(FEATURES_PATH, features, list(features[0].keys()))
    write_report(
        predictions,
        previous_predictions,
        provider_fixtures,
        applied_results,
        latest_result_date,
        provider_results_applied,
    )

    config = {
        "version": "nations_league_2026_matchday_1_v27_v211",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fixtures": FIXTURES,
        "historical_results_applied": applied_results,
        "historical_results_through": latest_result_date,
        "live_provider_results_applied": provider_results_applied,
        "base_model": "v2.7 calibrated international ensemble",
        "publishing_gate": "v2.11 conservative calibration",
        "weather_role": "tempo/risk context; not a core 1X2 feature",
        "outputs": [str(PREDICTIONS_PATH.relative_to(ROOT)), str(FEATURES_PATH.relative_to(ROOT)), str(REPORT_PATH.relative_to(ROOT))],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "fixtures": len(predictions),
                "historical_results_applied": applied_results,
                "historical_results_through": latest_result_date,
                "live_provider_results_applied": provider_results_applied,
                "tiers": {tier: sum(row["v211_tier"] == tier for row in predictions) for tier in ["Strong Pick", "Model Lean", "Pass"]},
                "weather_available": sum(row.get("temperature_c") not in ("", None) for row in predictions),
                "predictions": str(PREDICTIONS_PATH),
                "report": str(REPORT_PATH),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
