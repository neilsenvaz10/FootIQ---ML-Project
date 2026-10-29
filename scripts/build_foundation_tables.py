#!/usr/bin/env python3
"""Build model-ready foundation tables from downloaded public datasets."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
CONTRACTS = ROOT / "data" / "contracts"


def as_bool(value: str) -> bool:
    return str(value).strip().upper() == "TRUE"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def result_label(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win"
    if home_score < away_score:
        return "away_win"
    return "draw"


def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def tournament_k_weight(tournament: str) -> int:
    name = tournament.lower()
    if tournament == "FIFA World Cup":
        return 60
    if any(token in name for token in ["copa américa", "uefa euro", "african cup", "asian cup", "gold cup", "nations cup"]):
        return 50
    if "qualification" in name:
        return 40
    if "nations league" in name:
        return 35
    if "friendly" in name:
        return 20
    return 30


def goal_difference_multiplier(goal_diff: int) -> float:
    diff = abs(goal_diff)
    if diff <= 1:
        return 1.0
    if diff == 2:
        return 1.5
    return (11.0 + diff) / 8.0


def build_international_matches_and_elo() -> None:
    rows = read_csv(RAW / "international_results" / "results.csv")
    rows.sort(key=lambda row: (row["date"], row["home_team"], row["away_team"]))

    match_rows: list[dict[str, Any]] = []
    elo_rows: list[dict[str, Any]] = []
    ratings: defaultdict[str, float] = defaultdict(lambda: 1500.0)
    matches_played: defaultdict[str, int] = defaultdict(int)
    last_date: dict[str, str] = {}

    for idx, row in enumerate(rows, start=1):
        home = row["home_team"]
        away = row["away_team"]
        home_score = parse_int(row["home_score"])
        away_score = parse_int(row["away_score"])
        if home_score is None or away_score is None:
            continue
        neutral = as_bool(row["neutral"])
        tournament = row["tournament"]
        label = result_label(home_score, away_score)
        home_points = 3 if label == "home_win" else 1 if label == "draw" else 0
        away_points = 3 if label == "away_win" else 1 if label == "draw" else 0
        is_competitive = "friendly" not in tournament.lower()

        home_pre = ratings[home]
        away_pre = ratings[away]
        home_advantage = 0.0 if neutral else 75.0
        expected_home = 1.0 / (1.0 + math.pow(10.0, -((home_pre + home_advantage) - away_pre) / 400.0))
        actual_home = 1.0 if label == "home_win" else 0.5 if label == "draw" else 0.0
        k = tournament_k_weight(tournament)
        g = goal_difference_multiplier(home_score - away_score)
        change = k * g * (actual_home - expected_home)
        ratings[home] = home_pre + change
        ratings[away] = away_pre - change
        matches_played[home] += 1
        matches_played[away] += 1
        last_date[home] = row["date"]
        last_date[away] = row["date"]

        match_rows.append(
            {
                "match_id": idx,
                "date": row["date"],
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "result": label,
                "tournament": tournament,
                "city": row["city"],
                "country": row["country"],
                "neutral": neutral,
                "is_world_cup": tournament == "FIFA World Cup",
                "is_competitive": is_competitive,
                "home_points": home_points,
                "away_points": away_points,
                "goal_diff_home": home_score - away_score,
                "total_goals": home_score + away_score,
                "home_elo_pre": round(home_pre, 3),
                "away_elo_pre": round(away_pre, 3),
                "home_elo_post": round(ratings[home], 3),
                "away_elo_post": round(ratings[away], 3),
                "home_elo_change": round(change, 3),
                "away_elo_change": round(-change, 3),
                "elo_k": k,
                "elo_goal_multiplier": round(g, 3),
            }
        )

        team_rows = [
            (home, away, "home" if not neutral else "neutral", home_score, away_score, home_points, home_pre, ratings[home], change),
            (away, home, "away" if not neutral else "neutral", away_score, home_score, away_points, away_pre, ratings[away], -change),
        ]
        for team, opponent, venue, gf, ga, points, pre, post, delta in team_rows:
            elo_rows.append(
                {
                    "match_id": idx,
                    "date": row["date"],
                    "team": team,
                    "opponent": opponent,
                    "venue": venue,
                    "tournament": tournament,
                    "is_competitive": is_competitive,
                    "goals_for": gf,
                    "goals_against": ga,
                    "goal_diff": gf - ga,
                    "points": points,
                    "result": "win" if points == 3 else "draw" if points == 1 else "loss",
                    "pre_elo": round(pre, 3),
                    "post_elo": round(post, 3),
                    "elo_change": round(delta, 3),
                    "opponent_pre_elo": round(away_pre if team == home else home_pre, 3),
                }
            )

    latest = [
        {
            "team": team,
            "elo_rating": round(rating, 3),
            "matches_played": matches_played[team],
            "last_match_date": last_date.get(team, ""),
        }
        for team, rating in ratings.items()
    ]
    latest.sort(key=lambda row: row["elo_rating"], reverse=True)
    for rank, row in enumerate(latest, start=1):
        row["elo_rank"] = rank

    write_csv(
        PROCESSED / "international_matches.csv",
        match_rows,
        [
            "match_id",
            "date",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "result",
            "tournament",
            "city",
            "country",
            "neutral",
            "is_world_cup",
            "is_competitive",
            "home_points",
            "away_points",
            "goal_diff_home",
            "total_goals",
            "home_elo_pre",
            "away_elo_pre",
            "home_elo_post",
            "away_elo_post",
            "home_elo_change",
            "away_elo_change",
            "elo_k",
            "elo_goal_multiplier",
        ],
    )
    write_csv(
        PROCESSED / "team_elo_match_history.csv",
        elo_rows,
        [
            "match_id",
            "date",
            "team",
            "opponent",
            "venue",
            "tournament",
            "is_competitive",
            "goals_for",
            "goals_against",
            "goal_diff",
            "points",
            "result",
            "pre_elo",
            "post_elo",
            "elo_change",
            "opponent_pre_elo",
        ],
    )
    write_csv(PROCESSED / "team_elo_latest.csv", latest, ["elo_rank", "team", "elo_rating", "matches_played", "last_match_date"])
    build_recent_form(elo_rows)


def weighted_average(values: list[float], decay: float = 0.82) -> float:
    if not values:
        return 0.0
    weights = [math.pow(decay, len(values) - 1 - idx) for idx in range(len(values))]
    return sum(value * weight for value, weight in zip(values, weights)) / sum(weights)


def build_recent_form(elo_rows: list[dict[str, Any]]) -> None:
    by_team: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in elo_rows:
        by_team[row["team"]].append(row)

    form_rows: list[dict[str, Any]] = []
    for team, history in by_team.items():
        history.sort(key=lambda row: (row["date"], row["match_id"]))
        output: dict[str, Any] = {"team": team, "last_match_date": history[-1]["date"]}
        for n in (5, 10):
            sample = history[-n:]
            points = [float(row["points"]) for row in sample]
            goal_diff = [float(row["goal_diff"]) for row in sample]
            elo_delta = [float(row["elo_change"]) for row in sample]
            opponent_elo = [float(row["opponent_pre_elo"]) for row in sample]
            output[f"matches_last_{n}"] = len(sample)
            output[f"points_last_{n}"] = round(sum(points), 3)
            output[f"ppg_last_{n}"] = round(sum(points) / len(sample), 3) if sample else 0
            output[f"weighted_ppg_last_{n}"] = round(weighted_average(points), 3)
            output[f"goal_diff_last_{n}"] = round(sum(goal_diff), 3)
            output[f"weighted_goal_diff_last_{n}"] = round(weighted_average(goal_diff), 3)
            output[f"elo_change_last_{n}"] = round(sum(elo_delta), 3)
            output[f"weighted_elo_change_last_{n}"] = round(weighted_average(elo_delta), 3)
            output[f"avg_opponent_elo_last_{n}"] = round(sum(opponent_elo) / len(sample), 3) if sample else 0
            output[f"competitive_matches_last_{n}"] = sum(1 for row in sample if str(row["is_competitive"]) == "True")
        form_rows.append(output)

    form_rows.sort(key=lambda row: row["weighted_elo_change_last_10"], reverse=True)
    write_csv(
        PROCESSED / "team_recent_form_latest.csv",
        form_rows,
        [
            "team",
            "last_match_date",
            "matches_last_5",
            "points_last_5",
            "ppg_last_5",
            "weighted_ppg_last_5",
            "goal_diff_last_5",
            "weighted_goal_diff_last_5",
            "elo_change_last_5",
            "weighted_elo_change_last_5",
            "avg_opponent_elo_last_5",
            "competitive_matches_last_5",
            "matches_last_10",
            "points_last_10",
            "ppg_last_10",
            "weighted_ppg_last_10",
            "goal_diff_last_10",
            "weighted_goal_diff_last_10",
            "elo_change_last_10",
            "weighted_elo_change_last_10",
            "avg_opponent_elo_last_10",
            "competitive_matches_last_10",
        ],
    )


def build_worldcup_2026_tables() -> None:
    path = RAW / "openfootball" / "worldcup_2026.json"
    with path.open() as handle:
        data = json.load(handle)

    matches: list[dict[str, Any]] = []
    team_groups: dict[str, str] = {}
    for idx, match in enumerate(data["matches"], start=1):
        group = match.get("group", "")
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")
        if group:
            team_groups.setdefault(team1, group.replace("Group ", ""))
            team_groups.setdefault(team2, group.replace("Group ", ""))
        matches.append(
            {
                "fixture_id": idx,
                "round": match.get("round", ""),
                "date": match.get("date", ""),
                "time": match.get("time", ""),
                "team1": team1,
                "team2": team2,
                "group": group,
                "ground": match.get("ground", ""),
            }
        )

    teams = [{"team": team, "group": group} for team, group in sorted(team_groups.items(), key=lambda item: (item[1], item[0]))]
    write_csv(PROCESSED / "worldcup_2026_matches.csv", matches, ["fixture_id", "round", "date", "time", "team1", "team2", "group", "ground"])
    write_csv(PROCESSED / "worldcup_2026_teams.csv", teams, ["group", "team"])


def latest_worldbank_values(indicator_path: Path, value_name: str) -> dict[str, dict[str, Any]]:
    with indicator_path.open() as handle:
        payload = json.load(handle)
    values: dict[str, dict[str, Any]] = {}
    for row in payload[1]:
        if row.get("value") is None:
            continue
        iso3 = row.get("countryiso3code") or ""
        if not iso3:
            continue
        year = int(row["date"])
        if iso3 not in values or year > values[iso3][f"{value_name}_year"]:
            values[iso3] = {
                "iso3": iso3,
                "country": row["country"]["value"],
                f"{value_name}_year": year,
                value_name: row["value"],
            }
    return values


def build_worldbank_macro_table() -> None:
    gdp = latest_worldbank_values(RAW / "worldbank" / "gdp_per_capita_all.json", "gdp_per_capita_usd")
    pop = latest_worldbank_values(RAW / "worldbank" / "population_all.json", "population")
    rows: list[dict[str, Any]] = []
    for iso3 in sorted(set(gdp) | set(pop)):
        row = {
            "iso3": iso3,
            "country": gdp.get(iso3, pop.get(iso3, {})).get("country", ""),
            "gdp_per_capita_usd": gdp.get(iso3, {}).get("gdp_per_capita_usd", ""),
            "gdp_year": gdp.get(iso3, {}).get("gdp_per_capita_usd_year", ""),
            "population": pop.get(iso3, {}).get("population", ""),
            "population_year": pop.get(iso3, {}).get("population_year", ""),
        }
        rows.append(row)
    write_csv(PROCESSED / "worldbank_macro_latest.csv", rows, ["iso3", "country", "gdp_per_capita_usd", "gdp_year", "population", "population_year"])


def build_statsbomb_tables() -> None:
    match_rows: list[dict[str, Any]] = []
    match_lookup: dict[int, dict[str, Any]] = {}
    for path in sorted((RAW / "statsbomb" / "matches" / "43").glob("*.json")):
        season_id = path.stem
        season_name = "2018" if season_id == "3" else "2022" if season_id == "106" else season_id
        with path.open() as handle:
            for match in json.load(handle):
                match_id = int(match["match_id"])
                row = {
                    "match_id": match_id,
                    "season": season_name,
                    "match_date": match.get("match_date", ""),
                    "kick_off": match.get("kick_off", ""),
                    "competition_stage": match.get("competition_stage", {}).get("name", ""),
                    "home_team": match.get("home_team", {}).get("home_team_name", ""),
                    "away_team": match.get("away_team", {}).get("away_team_name", ""),
                    "home_score": match.get("home_score", ""),
                    "away_score": match.get("away_score", ""),
                    "stadium": match.get("stadium", {}).get("name", ""),
                    "stadium_country": match.get("stadium", {}).get("country", {}).get("name", ""),
                    "referee": match.get("referee", {}).get("name", ""),
                }
                match_rows.append(row)
                match_lookup[match_id] = row

    write_csv(
        PROCESSED / "statsbomb_worldcup_matches.csv",
        sorted(match_rows, key=lambda row: (row["season"], row["match_date"], row["match_id"])),
        [
            "match_id",
            "season",
            "match_date",
            "kick_off",
            "competition_stage",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "stadium",
            "stadium_country",
            "referee",
        ],
    )

    summaries: dict[tuple[int, str], defaultdict[str, float]] = {}
    for event_path in sorted((RAW / "statsbomb" / "events").glob("*.json")):
        match_id = int(event_path.stem)
        with event_path.open() as handle:
            events = json.load(handle)
        for event in events:
            team = event.get("team", {}).get("name")
            if not team:
                continue
            key = (match_id, team)
            summary = summaries.setdefault(key, defaultdict(float))
            event_type = event.get("type", {}).get("name", "")
            summary["events_total"] += 1
            summary[f"events_{event_type.lower().replace(' ', '_')}"] += 1
            if event.get("under_pressure"):
                summary["events_under_pressure"] += 1

            if event_type == "Shot":
                shot = event.get("shot", {})
                summary["shots"] += 1
                summary["shot_xg"] += float(shot.get("statsbomb_xg") or 0)
                if shot.get("outcome", {}).get("name") == "Goal":
                    summary["goals_from_shots"] += 1
                shot_type = shot.get("type", {}).get("name", "")
                if shot_type and shot_type != "Open Play":
                    summary["set_piece_shots"] += 1
            elif event_type == "Pass":
                passing = event.get("pass", {})
                summary["passes"] += 1
                if "outcome" not in passing:
                    summary["passes_completed"] += 1
                if passing.get("cross"):
                    summary["crosses"] += 1
                if passing.get("switch"):
                    summary["switches"] += 1
            elif event_type == "Dribble":
                summary["dribbles"] += 1
                if event.get("dribble", {}).get("outcome", {}).get("name") == "Complete":
                    summary["dribbles_completed"] += 1
            elif event_type == "Pressure":
                summary["pressures"] += 1
            elif event_type == "Duel":
                summary["duels"] += 1
                if event.get("duel", {}).get("outcome", {}).get("name") in {"Won", "Success"}:
                    summary["duels_won"] += 1

    rows: list[dict[str, Any]] = []
    for (match_id, team), values in summaries.items():
        meta = match_lookup.get(match_id, {})
        passes = values.get("passes", 0)
        dribbles = values.get("dribbles", 0)
        duels = values.get("duels", 0)
        rows.append(
            {
                "match_id": match_id,
                "season": meta.get("season", ""),
                "match_date": meta.get("match_date", ""),
                "team": team,
                "opponent": meta.get("away_team") if meta.get("home_team") == team else meta.get("home_team", ""),
                "events_total": int(values.get("events_total", 0)),
                "shots": int(values.get("shots", 0)),
                "shot_xg": round(values.get("shot_xg", 0), 4),
                "goals_from_shots": int(values.get("goals_from_shots", 0)),
                "set_piece_shots": int(values.get("set_piece_shots", 0)),
                "passes": int(passes),
                "passes_completed": int(values.get("passes_completed", 0)),
                "pass_completion_pct": round(100 * values.get("passes_completed", 0) / passes, 3) if passes else 0,
                "crosses": int(values.get("crosses", 0)),
                "switches": int(values.get("switches", 0)),
                "pressures": int(values.get("pressures", 0)),
                "dribbles": int(dribbles),
                "dribbles_completed": int(values.get("dribbles_completed", 0)),
                "dribble_success_pct": round(100 * values.get("dribbles_completed", 0) / dribbles, 3) if dribbles else 0,
                "duels": int(duels),
                "duels_won": int(values.get("duels_won", 0)),
                "duel_success_pct": round(100 * values.get("duels_won", 0) / duels, 3) if duels else 0,
                "events_under_pressure": int(values.get("events_under_pressure", 0)),
            }
        )

    write_csv(
        PROCESSED / "statsbomb_team_event_summary.csv",
        sorted(rows, key=lambda row: (row["season"], row["match_date"], row["match_id"], row["team"])),
        [
            "match_id",
            "season",
            "match_date",
            "team",
            "opponent",
            "events_total",
            "shots",
            "shot_xg",
            "goals_from_shots",
            "set_piece_shots",
            "passes",
            "passes_completed",
            "pass_completion_pct",
            "crosses",
            "switches",
            "pressures",
            "dribbles",
            "dribbles_completed",
            "dribble_success_pct",
            "duels",
            "duels_won",
            "duel_success_pct",
            "events_under_pressure",
        ],
    )


def build_contract_tables() -> None:
    contracts = {
        "player_availability_contract.csv": [
            "as_of_utc",
            "match_id",
            "team",
            "player",
            "position",
            "availability_status",
            "expected_minutes",
            "baseline_role",
            "player_impact_rating",
            "replacement_player",
            "replacement_impact_rating",
            "replacement_gap",
            "source",
            "source_url",
            "confidence_score",
            "notes",
        ],
        "squad_quality_contract.csv": [
            "as_of_utc",
            "team",
            "player",
            "position",
            "club",
            "league",
            "age",
            "club_minutes_last_365",
            "top5_league_minutes_last_365",
            "champions_league_minutes_last_365",
            "national_team_minutes_last_365",
            "player_impact_rating",
            "role_importance",
            "source",
            "confidence_score",
        ],
        "odds_snapshots_contract.csv": [
            "as_of_utc",
            "match_id",
            "sportsbook_or_exchange",
            "team1_win_decimal",
            "draw_decimal",
            "team2_win_decimal",
            "opening_or_live",
            "source",
            "source_url",
        ],
        "weather_snapshots_contract.csv": [
            "as_of_utc",
            "match_id",
            "venue",
            "forecast_time_local",
            "temperature_c",
            "apparent_temperature_c",
            "humidity_pct",
            "wind_kph",
            "precipitation_mm",
            "cloud_cover_pct",
            "source",
        ],
        "tactical_profile_contract.csv": [
            "as_of_utc",
            "team",
            "sample_window",
            "pressing_intensity",
            "press_resistance",
            "defensive_line_height",
            "counterattack_threat",
            "set_piece_attack",
            "set_piece_defense",
            "aerial_strength",
            "chance_creation_central",
            "chance_creation_wide",
            "transition_defense",
            "low_block_breaking",
            "source",
            "confidence_score",
        ],
        "manual_overrides_contract.csv": [
            "as_of_utc",
            "entity_type",
            "entity_id",
            "field_name",
            "old_value",
            "new_value",
            "reason",
            "analyst",
            "expires_at_utc",
        ],
    }
    for filename, fieldnames in contracts.items():
        write_csv(CONTRACTS / filename, [], fieldnames)


def build_manifest() -> None:
    rows = [
        {
            "dataset": "international_results",
            "status": "downloaded",
            "path": "data/raw/international_results",
            "license_or_terms": "Kaggle source lists CC0 public domain; verify before commercial release",
            "model_use": "historical results, Elo, recent form, baseline backtests",
            "production_readiness": "prototype_ok",
        },
        {
            "dataset": "StatsBomb open data",
            "status": "downloaded_subset_2018_2022_world_cup",
            "path": "data/raw/statsbomb",
            "license_or_terms": "StatsBomb open-data terms; attribution required; verify commercial scope",
            "model_use": "tactical event features and model prototyping",
            "production_readiness": "prototype_ok_not_live",
        },
        {
            "dataset": "OpenFootball World Cup 2026",
            "status": "downloaded",
            "path": "data/raw/openfootball/worldcup_2026.json",
            "license_or_terms": "Open data project terms; verify before commercial release",
            "model_use": "fixture and group simulation structure",
            "production_readiness": "prototype_ok",
        },
        {
            "dataset": "World Bank WDI GDP/population",
            "status": "downloaded",
            "path": "data/raw/worldbank",
            "license_or_terms": "World Bank Open Data / CC BY 4.0 unless otherwise marked",
            "model_use": "small macro prior only",
            "production_readiness": "production_ok_with_attribution",
        },
        {
            "dataset": "FIFA rankings",
            "status": "raw_page_snapshot_downloaded",
            "path": "data/raw/fifa/men_rankings_page_id3.html",
            "license_or_terms": "FIFA terms; use official data carefully",
            "model_use": "ranking reference / optional feature",
            "production_readiness": "needs_clean_feed_or_permission",
        },
        {
            "dataset": "licensed live football feed",
            "status": "not_acquired",
            "path": "data/contracts",
            "license_or_terms": "Required: API contract with provider",
            "model_use": "live fixtures, injuries, suspensions, lineups, player stats",
            "production_readiness": "required_for_sellable_product",
        },
        {
            "dataset": "odds feed",
            "status": "not_acquired",
            "path": "data/contracts/odds_snapshots_contract.csv",
            "license_or_terms": "Required: API contract with odds provider",
            "model_use": "market comparison and odds movement tracker",
            "production_readiness": "required_for_sellable_product",
        },
    ]
    write_csv(
        PROCESSED / "data_manifest.csv",
        rows,
        ["dataset", "status", "path", "license_or_terms", "model_use", "production_readiness"],
    )


def main() -> None:
    started = datetime.now(UTC).isoformat(timespec="seconds")
    print(f"started: {started}")
    build_international_matches_and_elo()
    build_worldcup_2026_tables()
    build_worldbank_macro_table()
    build_statsbomb_tables()
    build_contract_tables()
    build_manifest()
    finished = datetime.now(UTC).isoformat(timespec="seconds")
    print(f"finished: {finished}")


if __name__ == "__main__":
    main()
