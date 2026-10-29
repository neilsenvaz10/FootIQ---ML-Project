#!/usr/bin/env python3
"""World Cup prediction model v1.

This MVP uses the public/open data already collected in this workspace.
It avoids exact-score outputs as a product promise, but uses internal goal
simulation for group tables and tournament paths.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
INPUTS = ROOT / "data" / "inputs"
OUTPUTS = ROOT / "outputs"

TEAM_ALIASES = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
}

DISPLAY_NAMES = {
    "United States": "USA",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
}

HOST_COUNTRY_BY_GROUND = {
    "Mexico City": "Mexico",
    "Guadalajara (Zapopan)": "Mexico",
    "Monterrey (Guadalupe)": "Mexico",
    "Toronto": "Canada",
    "Vancouver": "Canada",
    "Atlanta": "United States",
    "Boston (Foxborough)": "United States",
    "Dallas (Arlington)": "United States",
    "Houston": "United States",
    "Kansas City": "United States",
    "Los Angeles (Inglewood)": "United States",
    "Miami (Miami Gardens)": "United States",
    "New York/New Jersey (East Rutherford)": "United States",
    "Philadelphia": "United States",
    "San Francisco Bay Area (Santa Clara)": "United States",
    "Seattle": "United States",
}

GROUP_ORDER = list("ABCDEFGHIJKL")

ROUND_ORDER = {
    "Round of 32": 1,
    "Round of 16": 2,
    "Quarter-final": 3,
    "Semi-final": 4,
    "Match for third place": 5,
    "Final": 6,
}

MODEL_CONFIG = {
    "seed": 20260603,
    "simulations": 50000,
    "base_goal_rate": 1.22,
    "rating_goal_scale": 720.0,
    "host_advantage_group": 55.0,
    "host_advantage_knockout": 38.0,
    "recent_form_cap": 45.0,
    "ceiling_cap": 38.0,
    "tactical_cap": 22.0,
    "squad_availability_cap": 75.0,
    "knockout_draw_penalty_noise": 35.0,
}


@dataclass(frozen=True)
class TeamRating:
    team: str
    display_team: str
    group: str
    elo: float
    elo_rank: int
    recent_form_adjustment: float
    ceiling_adjustment: float
    tactical_adjustment: float
    squad_availability_adjustment: float
    total_rating: float
    contender_tier: str
    tactical_data_status: str


def normalize_team(team: str) -> str:
    return TEAM_ALIASES.get(team, team)


def display_team(team: str) -> str:
    return DISPLAY_NAMES.get(team, team)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def poisson_pmf(lam: float, max_goals: int = 9) -> list[float]:
    probs = [math.exp(-lam)]
    for k in range(1, max_goals + 1):
        probs.append(probs[-1] * lam / k)
    total = sum(probs)
    probs[-1] += max(0.0, 1.0 - total)
    return probs


def sample_poisson(lam: float) -> int:
    # Knuth's method is fine here because football goal rates are small.
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= random.random()
    return k - 1


def safe_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except ValueError:
        return default


def safe_int(row: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(float(row.get(key, default) or default))
    except ValueError:
        return default


def build_tactical_profiles() -> dict[str, dict[str, float | str]]:
    rows = read_csv(PROCESSED / "statsbomb_team_event_summary.csv")
    by_team: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_team[normalize_team(row["team"])].append(row)

    raw_profiles: dict[str, dict[str, float]] = {}
    for team, team_rows in by_team.items():
        shots = mean(safe_float(row, "shots") for row in team_rows)
        xg = mean(safe_float(row, "shot_xg") for row in team_rows)
        pressures = mean(safe_float(row, "pressures") for row in team_rows)
        pass_completion = mean(safe_float(row, "pass_completion_pct") for row in team_rows)
        dribble_success = mean(safe_float(row, "dribble_success_pct") for row in team_rows)
        duel_success = mean(safe_float(row, "duel_success_pct") for row in team_rows)
        under_pressure = mean(safe_float(row, "events_under_pressure") for row in team_rows)
        raw_profiles[team] = {
            "matches": float(len(team_rows)),
            "avg_shots": shots,
            "avg_xg": xg,
            "avg_pressures": pressures,
            "avg_pass_completion_pct": pass_completion,
            "avg_dribble_success_pct": dribble_success,
            "avg_duel_success_pct": duel_success,
            "avg_events_under_pressure": under_pressure,
        }

    metrics = [
        "avg_xg",
        "avg_shots",
        "avg_pressures",
        "avg_pass_completion_pct",
        "avg_dribble_success_pct",
        "avg_duel_success_pct",
    ]
    metric_values = {metric: [profile[metric] for profile in raw_profiles.values()] for metric in metrics}
    metric_stats = {
        metric: (mean(values), pstdev(values) if pstdev(values) > 0 else 1.0)
        for metric, values in metric_values.items()
    }

    profiles: dict[str, dict[str, float | str]] = {}
    for team, profile in raw_profiles.items():
        zsum = 0.0
        for metric in metrics:
            avg, sd = metric_stats[metric]
            zsum += (profile[metric] - avg) / sd
        tactical_adjustment = clamp((zsum / len(metrics)) * 10.0, -MODEL_CONFIG["tactical_cap"], MODEL_CONFIG["tactical_cap"])
        profiles[team] = {
            **profile,
            "tactical_adjustment": round(tactical_adjustment, 3),
            "tactical_data_status": "statsbomb_2018_2022_available",
        }
    return profiles


def read_availability_overrides() -> dict[str, float]:
    """Read optional injury/availability adjustments if the user fills them in.

    Expected columns are compatible with data/contracts/player_availability_contract.csv.
    The adjustment is replacement_gap * expected_minutes / 90, capped later.
    """
    candidates = [
        INPUTS / "player_availability_overrides.csv",
        ROOT / "data" / "contracts" / "player_availability_contract.csv",
    ]
    team_adjustments: defaultdict[str, float] = defaultdict(float)
    for path in candidates:
        if not path.exists():
            continue
        rows = read_csv(path)
        for row in rows:
            team = normalize_team(row.get("team", ""))
            if not team:
                continue
            gap = safe_float(row, "replacement_gap", 0.0)
            expected_minutes = safe_float(row, "expected_minutes", 90.0)
            status = (row.get("availability_status") or "").lower()
            direction = -1.0 if status in {"out", "injured", "suspended", "doubtful", "limited"} else 0.0
            if direction:
                team_adjustments[team] += direction * gap * clamp(expected_minutes / 90.0, 0.0, 1.0)
    return {
        team: clamp(value, -MODEL_CONFIG["squad_availability_cap"], MODEL_CONFIG["squad_availability_cap"])
        for team, value in team_adjustments.items()
    }


def recent_form_adjustment(form: dict[str, str]) -> float:
    weighted_elo = safe_float(form, "weighted_elo_change_last_10")
    weighted_ppg = safe_float(form, "weighted_ppg_last_10")
    opponent_elo = safe_float(form, "avg_opponent_elo_last_10", 1700.0)
    raw = weighted_elo * 1.8 + (weighted_ppg - 1.5) * 10.0 + (opponent_elo - 1700.0) * 0.018
    return clamp(raw, -MODEL_CONFIG["recent_form_cap"], MODEL_CONFIG["recent_form_cap"])


def ceiling_adjustment(elo: float, rank: int) -> tuple[float, str]:
    if elo >= 2025 or rank <= 8:
        tier = "Tier 1 contender"
    elif elo >= 1925 or rank <= 20:
        tier = "Tier 2 dark horse"
    elif elo >= 1800 or rank <= 40:
        tier = "Tier 3 knockout threat"
    else:
        tier = "Tier 4 participant"
    raw = (elo - 1850.0) * 0.10
    if tier == "Tier 1 contender":
        raw += 14.0
    elif tier == "Tier 2 dark horse":
        raw += 5.0
    elif tier == "Tier 4 participant":
        raw -= 12.0
    return clamp(raw, -MODEL_CONFIG["ceiling_cap"], MODEL_CONFIG["ceiling_cap"]), tier


def build_team_ratings() -> dict[str, TeamRating]:
    teams = read_csv(PROCESSED / "worldcup_2026_teams.csv")
    elo_rows = {normalize_team(row["team"]): row for row in read_csv(PROCESSED / "team_elo_latest.csv")}
    form_rows = {normalize_team(row["team"]): row for row in read_csv(PROCESSED / "team_recent_form_latest.csv")}
    tactical_profiles = build_tactical_profiles()
    availability = read_availability_overrides()

    ratings: dict[str, TeamRating] = {}
    missing: list[str] = []
    for row in teams:
        team = normalize_team(row["team"])
        if team not in elo_rows or team not in form_rows:
            missing.append(row["team"])
            continue
        elo = safe_float(elo_rows[team], "elo_rating")
        rank = safe_int(elo_rows[team], "elo_rank")
        form_adj = recent_form_adjustment(form_rows[team])
        ceiling_adj, tier = ceiling_adjustment(elo, rank)
        tactical = tactical_profiles.get(team, {})
        tactical_adj = float(tactical.get("tactical_adjustment", 0.0))
        tactical_status = str(tactical.get("tactical_data_status", "no_open_tactical_data"))
        squad_adj = availability.get(team, 0.0)
        total = elo + form_adj + ceiling_adj + tactical_adj + squad_adj
        ratings[team] = TeamRating(
            team=team,
            display_team=display_team(team),
            group=row["group"],
            elo=elo,
            elo_rank=rank,
            recent_form_adjustment=round(form_adj, 3),
            ceiling_adjustment=round(ceiling_adj, 3),
            tactical_adjustment=round(tactical_adj, 3),
            squad_availability_adjustment=round(squad_adj, 3),
            total_rating=round(total, 3),
            contender_tier=tier,
            tactical_data_status=tactical_status,
        )
    if missing:
        raise RuntimeError(f"Missing required team ratings for: {missing}")
    return ratings


def host_adjustment(team: str, ground: str, round_name: str) -> float:
    host_country = HOST_COUNTRY_BY_GROUND.get(ground, "")
    if not host_country or team != host_country:
        return 0.0
    if round_name.startswith("Matchday"):
        return MODEL_CONFIG["host_advantage_group"]
    return MODEL_CONFIG["host_advantage_knockout"]


def expected_goals(rating_a: float, rating_b: float) -> tuple[float, float]:
    diff = rating_a - rating_b
    base = MODEL_CONFIG["base_goal_rate"]
    scale = MODEL_CONFIG["rating_goal_scale"]
    lambda_a = clamp(base * math.exp(diff / scale), 0.25, 3.4)
    lambda_b = clamp(base * math.exp(-diff / scale), 0.25, 3.4)
    return lambda_a, lambda_b


def scoreline_probabilities(lambda_a: float, lambda_b: float, max_goals: int = 9) -> tuple[float, float, float]:
    pa = poisson_pmf(lambda_a, max_goals)
    pb = poisson_pmf(lambda_b, max_goals)
    a_win = 0.0
    draw = 0.0
    b_win = 0.0
    for i, p_i in enumerate(pa):
        for j, p_j in enumerate(pb):
            p = p_i * p_j
            if i > j:
                a_win += p
            elif i == j:
                draw += p
            else:
                b_win += p
    total = a_win + draw + b_win
    return a_win / total, draw / total, b_win / total


def match_projection(team_a: str, team_b: str, ratings: dict[str, TeamRating], ground: str = "", round_name: str = "") -> dict[str, Any]:
    rating_a = ratings[team_a].total_rating + host_adjustment(team_a, ground, round_name)
    rating_b = ratings[team_b].total_rating + host_adjustment(team_b, ground, round_name)
    lambda_a, lambda_b = expected_goals(rating_a, rating_b)
    p_a, p_draw, p_b = scoreline_probabilities(lambda_a, lambda_b)
    return {
        "team1": team_a,
        "team2": team_b,
        "team1_rating": rating_a,
        "team2_rating": rating_b,
        "rating_diff_team1": rating_a - rating_b,
        "team1_win_probability": p_a,
        "draw_probability": p_draw,
        "team2_win_probability": p_b,
        "team1_xg_internal": lambda_a,
        "team2_xg_internal": lambda_b,
    }


def verdict(row: dict[str, Any]) -> tuple[str, str, str]:
    t1 = display_team(row["team1"])
    t2 = display_team(row["team2"])
    p1 = row["team1_win_probability"]
    pd = row["draw_probability"]
    p2 = row["team2_win_probability"]
    fav_team = t1 if p1 >= p2 else t2
    dog_team = t2 if p1 >= p2 else t1
    fav_p = max(p1, p2)
    dog_p = min(p1, p2)
    avoid_defeat = fav_p + pd
    gap = fav_p - dog_p

    if fav_p >= 0.58 and gap >= 0.30:
        return f"{fav_team} win", "High", "Strong favorite; no major upset signal in available data"
    if fav_p >= 0.50 and gap >= 0.20:
        return f"{fav_team} win lean", "Medium", "Clearer team-strength edge, but football variance remains material"
    if avoid_defeat >= 0.72 and fav_p >= 0.40:
        return f"{fav_team} avoid defeat", "Medium-low", "Best call is protection against the draw/upset, not a clean win call"
    if pd >= 0.29 and gap <= 0.12:
        return "No strong edge", "Pass", "Market-style winner call would be forced; model sees a close game"
    if dog_p >= 0.27 and gap <= 0.16:
        return f"Upset watch: {dog_team} live", "Low-medium", "Underdog has enough probability to avoid a blind favorite pick"
    return f"{fav_team} slight lean", "Low", "Small model edge only"


def simulate_group_match(projection: dict[str, Any]) -> tuple[int, int]:
    goals_a = sample_poisson(projection["team1_xg_internal"])
    goals_b = sample_poisson(projection["team2_xg_internal"])
    return goals_a, goals_b


def rank_group(teams: list[str], table: dict[str, dict[str, int]]) -> list[str]:
    return sorted(
        teams,
        key=lambda team: (
            table[team]["points"],
            table[team]["goal_diff"],
            table[team]["goals_for"],
            random.random(),
        ),
        reverse=True,
    )


def third_place_sort_key(entry: dict[str, Any]) -> tuple[int, int, int, float]:
    stats = entry["stats"]
    return stats["points"], stats["goal_diff"], stats["goals_for"], random.random()


def resolve_slot(slot: str, group_rankings: dict[str, list[str]], third_pool: dict[str, dict[str, Any]], match_results: dict[str, str]) -> str:
    slot = slot.strip()
    if slot.startswith("W") or slot.startswith("L"):
        return match_results[slot]
    if len(slot) >= 2 and slot[0] in {"1", "2"} and slot[1] in GROUP_ORDER:
        rank = int(slot[0]) - 1
        return group_rankings[slot[1]][rank]
    if slot.startswith("3"):
        groups = slot[1:].split("/")
        available = [third_pool[group] for group in groups if group in third_pool]
        if not available:
            available = list(third_pool.values())
        if not available:
            raise RuntimeError(f"No third-place team available for slot {slot}")
        choice = sorted(available, key=third_place_sort_key, reverse=True)[0]
        del third_pool[choice["group"]]
        return choice["team"]
    raise RuntimeError(f"Unresolved bracket slot: {slot}")


def knockout_winner(team_a: str, team_b: str, ratings: dict[str, TeamRating], ground: str, round_name: str) -> str:
    projection = match_projection(team_a, team_b, ratings, ground, round_name)
    goals_a, goals_b = simulate_group_match(projection)
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    # Extra time / penalties: strength matters, but noise is deliberately large.
    diff = projection["rating_diff_team1"] + random.gauss(0.0, MODEL_CONFIG["knockout_draw_penalty_noise"])
    p_a = sigmoid(diff / 185.0)
    return team_a if random.random() < p_a else team_b


def run_tournament_simulation(
    ratings: dict[str, TeamRating],
    fixtures: list[dict[str, str]],
    group_fixtures: list[dict[str, str]],
    knockout_fixtures: list[dict[str, str]],
) -> dict[str, Any]:
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for rating in ratings.values():
        groups[rating.group].append(rating.team)

    table = {
        team: {"points": 0, "goals_for": 0, "goals_against": 0, "goal_diff": 0}
        for team in ratings
    }

    for fixture in group_fixtures:
        team_a = normalize_team(fixture["team1"])
        team_b = normalize_team(fixture["team2"])
        projection = match_projection(team_a, team_b, ratings, fixture["ground"], fixture["round"])
        goals_a, goals_b = simulate_group_match(projection)
        table[team_a]["goals_for"] += goals_a
        table[team_a]["goals_against"] += goals_b
        table[team_b]["goals_for"] += goals_b
        table[team_b]["goals_against"] += goals_a
        if goals_a > goals_b:
            table[team_a]["points"] += 3
        elif goals_b > goals_a:
            table[team_b]["points"] += 3
        else:
            table[team_a]["points"] += 1
            table[team_b]["points"] += 1

    for stats in table.values():
        stats["goal_diff"] = stats["goals_for"] - stats["goals_against"]

    group_rankings: dict[str, list[str]] = {
        group: rank_group(sorted(teams), table)
        for group, teams in groups.items()
    }

    qualified: set[str] = set()
    group_first: set[str] = set()
    group_second: set[str] = set()
    third_entries: list[dict[str, Any]] = []
    for group in GROUP_ORDER:
        ranking = group_rankings[group]
        group_first.add(ranking[0])
        group_second.add(ranking[1])
        qualified.add(ranking[0])
        qualified.add(ranking[1])
        third_entries.append({"group": group, "team": ranking[2], "stats": table[ranking[2]]})

    third_entries = sorted(third_entries, key=third_place_sort_key, reverse=True)
    third_qualified = {entry["team"] for entry in third_entries[:8]}
    third_pool = {entry["group"]: entry for entry in third_entries[:8]}
    qualified.update(third_qualified)

    match_results: dict[str, str] = {}
    reached = {
        "qualified": set(qualified),
        "group_first": group_first,
        "group_second": group_second,
        "group_third_qualified": third_qualified,
        "round_of_16": set(),
        "quarter_final": set(),
        "semi_final": set(),
        "final": set(),
        "champion": set(),
    }

    for fixture in knockout_fixtures:
        match_no = fixture["fixture_id"]
        round_name = fixture["round"]
        team_a = resolve_slot(fixture["team1"], group_rankings, third_pool, match_results)
        team_b = resolve_slot(fixture["team2"], group_rankings, third_pool, match_results)
        winner = knockout_winner(team_a, team_b, ratings, fixture["ground"], round_name)
        loser = team_b if winner == team_a else team_a
        match_results[f"W{match_no}"] = winner
        match_results[f"L{match_no}"] = loser

        if round_name == "Round of 32":
            reached["round_of_16"].add(winner)
        elif round_name == "Round of 16":
            reached["quarter_final"].add(winner)
        elif round_name == "Quarter-final":
            reached["semi_final"].add(winner)
        elif round_name == "Semi-final":
            reached["final"].add(winner)
        elif round_name == "Final":
            reached["champion"].add(winner)

    return reached


def build_match_predictions(ratings: dict[str, TeamRating], fixtures: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fixture in fixtures:
        if not fixture["round"].startswith("Matchday"):
            continue
        team_a = normalize_team(fixture["team1"])
        team_b = normalize_team(fixture["team2"])
        projection = match_projection(team_a, team_b, ratings, fixture["ground"], fixture["round"])
        public_verdict, confidence, reason = verdict(projection)
        rows.append(
            {
                "fixture_id": fixture["fixture_id"],
                "date": fixture["date"],
                "time": fixture["time"],
                "group": fixture["group"].replace("Group ", ""),
                "ground": fixture["ground"],
                "team1": display_team(team_a),
                "team2": display_team(team_b),
                "public_verdict": public_verdict,
                "confidence": confidence,
                "model_reason": reason,
                "team1_win_probability_internal": round(projection["team1_win_probability"], 4),
                "draw_probability_internal": round(projection["draw_probability"], 4),
                "team2_win_probability_internal": round(projection["team2_win_probability"], 4),
                "team1_internal_xg": round(projection["team1_xg_internal"], 3),
                "team2_internal_xg": round(projection["team2_xg_internal"], 3),
                "team1_rating": round(projection["team1_rating"], 3),
                "team2_rating": round(projection["team2_rating"], 3),
                "rating_diff_team1": round(projection["rating_diff_team1"], 3),
            }
        )
    return rows


def run_simulations(ratings: dict[str, TeamRating], fixtures: list[dict[str, str]]) -> list[dict[str, Any]]:
    random.seed(MODEL_CONFIG["seed"])
    group_fixtures = [fixture for fixture in fixtures if fixture["round"].startswith("Matchday")]
    knockout_fixtures = sorted(
        [fixture for fixture in fixtures if fixture["round"] in ROUND_ORDER],
        key=lambda fixture: (ROUND_ORDER[fixture["round"]], int(fixture["fixture_id"])),
    )

    counters: dict[str, Counter[str]] = {
        "qualified": Counter(),
        "group_first": Counter(),
        "group_second": Counter(),
        "group_third_qualified": Counter(),
        "round_of_16": Counter(),
        "quarter_final": Counter(),
        "semi_final": Counter(),
        "final": Counter(),
        "champion": Counter(),
    }

    sims = int(MODEL_CONFIG["simulations"])
    for _ in range(sims):
        reached = run_tournament_simulation(ratings, fixtures, group_fixtures, knockout_fixtures)
        for key, teams in reached.items():
            counters[key].update(teams)

    rows: list[dict[str, Any]] = []
    for team, rating in ratings.items():
        rows.append(
            {
                "team": rating.display_team,
                "group": rating.group,
                "contender_tier": rating.contender_tier,
                "total_rating": rating.total_rating,
                "group_first_pct": round(100 * counters["group_first"][team] / sims, 2),
                "group_second_pct": round(100 * counters["group_second"][team] / sims, 2),
                "third_place_qualified_pct": round(100 * counters["group_third_qualified"][team] / sims, 2),
                "qualify_knockout_pct": round(100 * counters["qualified"][team] / sims, 2),
                "round_of_16_pct": round(100 * counters["round_of_16"][team] / sims, 2),
                "quarter_final_pct": round(100 * counters["quarter_final"][team] / sims, 2),
                "semi_final_pct": round(100 * counters["semi_final"][team] / sims, 2),
                "final_pct": round(100 * counters["final"][team] / sims, 2),
                "champion_pct": round(100 * counters["champion"][team] / sims, 2),
            }
        )
    rows.sort(key=lambda row: (row["champion_pct"], row["final_pct"], row["semi_final_pct"]), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["title_rank"] = idx
    return rows


def model_notes(top_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# World Cup Model v1",
        "",
        "This is the first working MVP prediction engine built from the collected public/open data.",
        "",
        "## What It Uses",
        "",
        "- Prototype international Elo from 49k+ historical matches.",
        "- Recent form from each team's last 5 and last 10 matches.",
        "- A championship-ceiling adjustment so participant-level teams do not get unrealistic title odds.",
        "- Host advantage for Mexico, Canada, and USA based on match venue.",
        "- StatsBomb open tactical/event adjustment where 2018/2022 World Cup data exists.",
        "- Optional player-availability/replacement-gap override support.",
        "",
        "## What It Does Not Yet Have",
        "",
        "- Licensed live injury feed.",
        "- Confirmed or expected lineups.",
        "- Paid squad-quality/player-minute feed.",
        "- Paid odds feed.",
        "- Full tracking-data tactical layer.",
        "",
        "## Important Product Choice",
        "",
        "The model does not headline exact scores. It uses internal goal simulation only to build group tables and tournament paths.",
        "",
        "## Top Title Odds",
        "",
        "| Rank | Team | Champion % | Final % | Semi % | Tier |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for row in top_rows[:12]:
        lines.append(
            f"| {row['title_rank']} | {row['team']} | {row['champion_pct']:.2f}% | "
            f"{row['final_pct']:.2f}% | {row['semi_final_pct']:.2f}% | {row['contender_tier']} |"
        )
    lines.extend(
        [
            "",
            "## Model Caveat",
            "",
            "This is a v1 probability engine, not a final betting product. The outputs are useful for iteration, backtesting, and dashboard design; commercial confidence requires live licensed feeds and calibration.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    fixtures = read_csv(PROCESSED / "worldcup_2026_matches.csv")
    ratings = build_team_ratings()

    team_rows = [
        {
            "team": rating.display_team,
            "normalized_team": rating.team,
            "group": rating.group,
            "elo": rating.elo,
            "elo_rank": rating.elo_rank,
            "recent_form_adjustment": rating.recent_form_adjustment,
            "ceiling_adjustment": rating.ceiling_adjustment,
            "tactical_adjustment": rating.tactical_adjustment,
            "squad_availability_adjustment": rating.squad_availability_adjustment,
            "total_rating": rating.total_rating,
            "contender_tier": rating.contender_tier,
            "tactical_data_status": rating.tactical_data_status,
        }
        for rating in ratings.values()
    ]
    team_rows.sort(key=lambda row: row["total_rating"], reverse=True)
    for idx, row in enumerate(team_rows, start=1):
        row["model_rating_rank"] = idx

    match_rows = build_match_predictions(ratings, fixtures)
    odds_rows = run_simulations(ratings, fixtures)

    write_csv(
        PROCESSED / "model_v1_team_ratings.csv",
        team_rows,
        [
            "model_rating_rank",
            "team",
            "normalized_team",
            "group",
            "elo",
            "elo_rank",
            "recent_form_adjustment",
            "ceiling_adjustment",
            "tactical_adjustment",
            "squad_availability_adjustment",
            "total_rating",
            "contender_tier",
            "tactical_data_status",
        ],
    )
    write_csv(
        PROCESSED / "model_v1_group_match_predictions.csv",
        match_rows,
        [
            "fixture_id",
            "date",
            "time",
            "group",
            "ground",
            "team1",
            "team2",
            "public_verdict",
            "confidence",
            "model_reason",
            "team1_win_probability_internal",
            "draw_probability_internal",
            "team2_win_probability_internal",
            "team1_internal_xg",
            "team2_internal_xg",
            "team1_rating",
            "team2_rating",
            "rating_diff_team1",
        ],
    )
    write_csv(
        PROCESSED / "model_v1_tournament_odds.csv",
        odds_rows,
        [
            "title_rank",
            "team",
            "group",
            "contender_tier",
            "total_rating",
            "group_first_pct",
            "group_second_pct",
            "third_place_qualified_pct",
            "qualify_knockout_pct",
            "round_of_16_pct",
            "quarter_final_pct",
            "semi_final_pct",
            "final_pct",
            "champion_pct",
        ],
    )

    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "world_cup_model_v1_summary.md").write_text(model_notes(odds_rows), encoding="utf-8")
    (OUTPUTS / "world_cup_model_v1_config.json").write_text(json.dumps(MODEL_CONFIG, indent=2), encoding="utf-8")
    print(json.dumps({"teams": len(team_rows), "group_matches": len(match_rows), "simulations": MODEL_CONFIG["simulations"], "top_team": odds_rows[0]}, indent=2))


if __name__ == "__main__":
    main()
