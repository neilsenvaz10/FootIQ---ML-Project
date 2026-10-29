#!/usr/bin/env python3
"""Leak-free backtest for World Cup model v1 on 2018 and 2022."""

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
RAW = ROOT / "data" / "raw"
OUTPUTS = ROOT / "outputs"

SIMULATIONS = 20000
BASE_GOAL_RATE = 1.22
RATING_GOAL_SCALE = 720.0
HOST_ADVANTAGE_GROUP = 55.0
HOST_ADVANTAGE_KNOCKOUT = 38.0
RECENT_FORM_CAP = 45.0
CEILING_CAP = 38.0
TACTICAL_CAP = 22.0
PENALTY_NOISE = 35.0

TEAM_ALIASES = {
    "USA": "United States",
    "United States": "United States",
    "IR Iran": "Iran",
}

DISPLAY_NAMES = {
    "United States": "USA",
}

GROUPS = {
    2018: {
        "A": ["Russia", "Saudi Arabia", "Egypt", "Uruguay"],
        "B": ["Portugal", "Spain", "Morocco", "Iran"],
        "C": ["France", "Australia", "Peru", "Denmark"],
        "D": ["Argentina", "Iceland", "Croatia", "Nigeria"],
        "E": ["Brazil", "Switzerland", "Costa Rica", "Serbia"],
        "F": ["Germany", "Mexico", "Sweden", "South Korea"],
        "G": ["Belgium", "Panama", "Tunisia", "England"],
        "H": ["Poland", "Senegal", "Colombia", "Japan"],
    },
    2022: {
        "A": ["Qatar", "Ecuador", "Senegal", "Netherlands"],
        "B": ["England", "Iran", "United States", "Wales"],
        "C": ["Argentina", "Saudi Arabia", "Mexico", "Poland"],
        "D": ["France", "Australia", "Denmark", "Tunisia"],
        "E": ["Spain", "Costa Rica", "Germany", "Japan"],
        "F": ["Belgium", "Canada", "Morocco", "Croatia"],
        "G": ["Brazil", "Serbia", "Switzerland", "Cameroon"],
        "H": ["Portugal", "Ghana", "Uruguay", "South Korea"],
    },
}

START_DATES = {
    2018: "2018-06-14",
    2022: "2022-11-20",
}

HOSTS = {
    2018: "Russia",
    2022: "Qatar",
}

R16_BRACKET = [
    ("M49", "1C", "2D"),
    ("M50", "1A", "2B"),
    ("M51", "1B", "2A"),
    ("M52", "1D", "2C"),
    ("M53", "1E", "2F"),
    ("M54", "1G", "2H"),
    ("M55", "1F", "2E"),
    ("M56", "1H", "2G"),
    ("M57", "WM49", "WM50"),
    ("M58", "WM53", "WM54"),
    ("M59", "WM51", "WM52"),
    ("M60", "WM55", "WM56"),
    ("M61", "WM57", "WM58"),
    ("M62", "WM59", "WM60"),
    ("M64", "WM61", "WM62"),
]

STAGE_BY_MATCH = {
    **{f"M{i}": "Round of 16" for i in range(49, 57)},
    **{f"M{i}": "Quarter-final" for i in range(57, 61)},
    "M61": "Semi-final",
    "M62": "Semi-final",
    "M64": "Final",
}


@dataclass(frozen=True)
class TeamRating:
    team: str
    group: str
    elo: float
    elo_rank: int
    total_rating: float
    recent_form_adjustment: float
    ceiling_adjustment: float
    tactical_adjustment: float
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


def safe_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except ValueError:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def weighted_average(values: list[float], decay: float = 0.82) -> float:
    if not values:
        return 0.0
    weights = [math.pow(decay, len(values) - 1 - idx) for idx in range(len(values))]
    return sum(value * weight for value, weight in zip(values, weights)) / sum(weights)


def poisson_pmf(lam: float, max_goals: int = 9) -> list[float]:
    probs = [math.exp(-lam)]
    for k in range(1, max_goals + 1):
        probs.append(probs[-1] * lam / k)
    total = sum(probs)
    probs[-1] += max(0.0, 1.0 - total)
    return probs


def sample_poisson(lam: float) -> int:
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= random.random()
    return k - 1


def expected_goals(rating_a: float, rating_b: float) -> tuple[float, float]:
    diff = rating_a - rating_b
    lambda_a = clamp(BASE_GOAL_RATE * math.exp(diff / RATING_GOAL_SCALE), 0.25, 3.4)
    lambda_b = clamp(BASE_GOAL_RATE * math.exp(-diff / RATING_GOAL_SCALE), 0.25, 3.4)
    return lambda_a, lambda_b


def scoreline_probabilities(lambda_a: float, lambda_b: float, max_goals: int = 9) -> tuple[float, float, float]:
    pa = poisson_pmf(lambda_a, max_goals)
    pb = poisson_pmf(lambda_b, max_goals)
    a_win = draw = b_win = 0.0
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


def latest_elo_as_of(start_date: str) -> tuple[dict[str, float], dict[str, int], dict[str, list[dict[str, str]]]]:
    rows = read_csv(PROCESSED / "team_elo_match_history.csv")
    history: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    latest: dict[str, tuple[str, float]] = {}
    for row in rows:
        if row["date"] >= start_date:
            continue
        team = normalize_team(row["team"])
        history[team].append(row)
        latest[team] = (row["date"], safe_float(row, "post_elo", 1500.0))

    elo = {team: value for team, (_, value) in latest.items()}
    sorted_teams = sorted(elo.items(), key=lambda item: item[1], reverse=True)
    ranks = {team: idx for idx, (team, _) in enumerate(sorted_teams, start=1)}
    return elo, ranks, history


def recent_form_adjustment(history: list[dict[str, str]]) -> float:
    sample = history[-10:]
    if not sample:
        return 0.0
    points = [safe_float(row, "points") for row in sample]
    elo_delta = [safe_float(row, "elo_change") for row in sample]
    opponent_elo = [safe_float(row, "opponent_pre_elo", 1700.0) for row in sample]
    weighted_elo = weighted_average(elo_delta)
    weighted_ppg = weighted_average(points)
    avg_opp = mean(opponent_elo)
    raw = weighted_elo * 1.8 + (weighted_ppg - 1.5) * 10.0 + (avg_opp - 1700.0) * 0.018
    return clamp(raw, -RECENT_FORM_CAP, RECENT_FORM_CAP)


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
    return clamp(raw, -CEILING_CAP, CEILING_CAP), tier


def build_tactical_profiles_as_of(year: int) -> dict[str, dict[str, Any]]:
    rows = [
        row for row in read_csv(PROCESSED / "statsbomb_team_event_summary.csv")
        if int(row["season"]) < year
    ]
    by_team: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_team[normalize_team(row["team"])].append(row)
    if not by_team:
        return {}

    raw: dict[str, dict[str, float]] = {}
    for team, team_rows in by_team.items():
        raw[team] = {
            "avg_xg": mean(safe_float(row, "shot_xg") for row in team_rows),
            "avg_shots": mean(safe_float(row, "shots") for row in team_rows),
            "avg_pressures": mean(safe_float(row, "pressures") for row in team_rows),
            "avg_pass_completion_pct": mean(safe_float(row, "pass_completion_pct") for row in team_rows),
            "avg_dribble_success_pct": mean(safe_float(row, "dribble_success_pct") for row in team_rows),
            "avg_duel_success_pct": mean(safe_float(row, "duel_success_pct") for row in team_rows),
        }

    metrics = list(next(iter(raw.values())).keys())
    stats = {}
    for metric in metrics:
        values = [profile[metric] for profile in raw.values()]
        sd = pstdev(values)
        stats[metric] = (mean(values), sd if sd > 0 else 1.0)

    profiles: dict[str, dict[str, Any]] = {}
    for team, profile in raw.items():
        zsum = 0.0
        for metric in metrics:
            avg, sd = stats[metric]
            zsum += (profile[metric] - avg) / sd
        profiles[team] = {
            "tactical_adjustment": clamp((zsum / len(metrics)) * 10.0, -TACTICAL_CAP, TACTICAL_CAP),
            "tactical_data_status": "prior_statsbomb_worldcup_data",
        }
    return profiles


def build_ratings(year: int, variant: str) -> dict[str, TeamRating]:
    start_date = START_DATES[year]
    elo, ranks, history = latest_elo_as_of(start_date)
    tactical = build_tactical_profiles_as_of(year) if variant == "model_v1" else {}
    ratings: dict[str, TeamRating] = {}
    for group, teams in GROUPS[year].items():
        for original_team in teams:
            team = normalize_team(original_team)
            if team not in elo:
                raise RuntimeError(f"Missing Elo for {team} before {year}")
            base = elo[team]
            rank = ranks[team]
            if variant == "elo_only":
                form_adj = ceiling_adj = tactical_adj = 0.0
                tier = "Elo-only baseline"
                tactical_status = "not_used"
                total = base
            else:
                form_adj = recent_form_adjustment(history[team])
                ceiling_adj, tier = ceiling_adjustment(base, rank)
                tactical_adj = float(tactical.get(team, {}).get("tactical_adjustment", 0.0))
                tactical_status = str(tactical.get(team, {}).get("tactical_data_status", "no_prior_tactical_data"))
                total = base + form_adj + ceiling_adj + tactical_adj
            ratings[team] = TeamRating(
                team=team,
                group=group,
                elo=base,
                elo_rank=rank,
                total_rating=total,
                recent_form_adjustment=form_adj,
                ceiling_adjustment=ceiling_adj,
                tactical_adjustment=tactical_adj,
                contender_tier=tier,
                tactical_data_status=tactical_status,
            )
    return ratings


def load_worldcup_matches(year: int) -> list[dict[str, Any]]:
    rows = [
        row for row in read_csv(PROCESSED / "statsbomb_worldcup_matches.csv")
        if int(row["season"]) == year
    ]
    rows.sort(key=lambda row: (row["match_date"], row["kick_off"], int(row["match_id"])))
    team_to_group = {
        normalize_team(team): group
        for group, teams in GROUPS[year].items()
        for team in teams
    }
    shootouts = {
        (row["date"], normalize_team(row["home_team"]), normalize_team(row["away_team"])): normalize_team(row["winner"])
        for row in read_csv(RAW / "international_results" / "shootouts.csv")
    }
    matches = []
    for row in rows:
        home = normalize_team(row["home_team"])
        away = normalize_team(row["away_team"])
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        stage = row["competition_stage"]
        group = team_to_group.get(home, "") if stage == "Group Stage" else ""
        winner = ""
        if stage != "Group Stage":
            if home_score > away_score:
                winner = home
            elif away_score > home_score:
                winner = away
            else:
                winner = shootouts.get((row["match_date"], home, away), "")
        matches.append(
            {
                "match_id": row["match_id"],
                "year": year,
                "date": row["match_date"],
                "stage": stage,
                "group": group,
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "winner": winner,
                "host_team": HOSTS[year],
            }
        )
    return matches


def host_adjustment(team: str, year: int, stage: str) -> float:
    if team != HOSTS[year]:
        return 0.0
    return HOST_ADVANTAGE_GROUP if stage == "Group Stage" else HOST_ADVANTAGE_KNOCKOUT


def match_projection(team_a: str, team_b: str, ratings: dict[str, TeamRating], year: int, stage: str) -> dict[str, Any]:
    rating_a = ratings[team_a].total_rating + host_adjustment(team_a, year, stage)
    rating_b = ratings[team_b].total_rating + host_adjustment(team_b, year, stage)
    lambda_a, lambda_b = expected_goals(rating_a, rating_b)
    p_a, p_draw, p_b = scoreline_probabilities(lambda_a, lambda_b)
    return {
        "team1": team_a,
        "team2": team_b,
        "rating_diff_team1": rating_a - rating_b,
        "team1_win_probability": p_a,
        "draw_probability": p_draw,
        "team2_win_probability": p_b,
        "team1_xg_internal": lambda_a,
        "team2_xg_internal": lambda_b,
    }


def public_verdict(projection: dict[str, Any]) -> tuple[str, str, str]:
    team1 = projection["team1"]
    team2 = projection["team2"]
    p1 = projection["team1_win_probability"]
    pd = projection["draw_probability"]
    p2 = projection["team2_win_probability"]
    fav = team1 if p1 >= p2 else team2
    dog = team2 if fav == team1 else team1
    fav_p = max(p1, p2)
    dog_p = min(p1, p2)
    gap = fav_p - dog_p
    avoid_defeat = fav_p + pd
    if fav_p >= 0.58 and gap >= 0.30:
        return fav, "win", "High"
    if fav_p >= 0.50 and gap >= 0.20:
        return fav, "win lean", "Medium"
    if avoid_defeat >= 0.72 and fav_p >= 0.40:
        return fav, "avoid defeat", "Medium-low"
    if pd >= 0.29 and gap <= 0.12:
        return "", "no strong edge", "Pass"
    if dog_p >= 0.27 and gap <= 0.16:
        return dog, "upset watch", "Low-medium"
    return fav, "slight lean", "Low"


def actual_group_table(matches: list[dict[str, Any]]) -> dict[str, list[str]]:
    table = {
        normalize_team(team): {"points": 0, "goals_for": 0, "goals_against": 0, "goal_diff": 0}
        for groups in GROUPS.values()
        for teams in groups.values()
        for team in teams
    }
    by_group: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for match in matches:
        if match["stage"] != "Group Stage":
            continue
        group = match["group"]
        by_group[group].append(match)
        home = match["home_team"]
        away = match["away_team"]
        hs = match["home_score"]
        aw = match["away_score"]
        table[home]["goals_for"] += hs
        table[home]["goals_against"] += aw
        table[away]["goals_for"] += aw
        table[away]["goals_against"] += hs
        if hs > aw:
            table[home]["points"] += 3
        elif aw > hs:
            table[away]["points"] += 3
        else:
            table[home]["points"] += 1
            table[away]["points"] += 1
    for stats in table.values():
        stats["goal_diff"] = stats["goals_for"] - stats["goals_against"]
    rankings = {}
    year = matches[0]["year"]
    for group, teams in GROUPS[year].items():
        ranking = sorted(
            [normalize_team(team) for team in teams],
            key=lambda team: (table[team]["points"], table[team]["goal_diff"], table[team]["goals_for"]),
            reverse=True,
        )
        rankings[group] = ranking
    return rankings


def actual_stage_sets(matches: list[dict[str, Any]]) -> dict[str, set[str]]:
    group_rankings = actual_group_table(matches)
    stage_sets = {
        "qualified": set(),
        "round_of_16": set(),
        "quarter_final": set(),
        "semi_final": set(),
        "final": set(),
        "champion": set(),
    }
    for ranking in group_rankings.values():
        stage_sets["qualified"].update(ranking[:2])
        stage_sets["round_of_16"].update(ranking[:2])

    for match in matches:
        stage = match["stage"]
        if stage == "Round of 16" and match["winner"]:
            stage_sets["quarter_final"].add(match["winner"])
        elif stage == "Quarter-finals" and match["winner"]:
            stage_sets["semi_final"].add(match["winner"])
        elif stage == "Semi-finals" and match["winner"]:
            stage_sets["final"].add(match["winner"])
        elif stage == "Final" and match["winner"]:
            stage_sets["champion"].add(match["winner"])
    return stage_sets


def simulate_group_match(projection: dict[str, Any]) -> tuple[int, int]:
    return sample_poisson(projection["team1_xg_internal"]), sample_poisson(projection["team2_xg_internal"])


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


def resolve_slot(slot: str, rankings: dict[str, list[str]], winners: dict[str, str]) -> str:
    if slot.startswith("W"):
        return winners[slot[1:]]
    rank = int(slot[0]) - 1
    group = slot[1]
    return rankings[group][rank]


def knockout_winner(team_a: str, team_b: str, ratings: dict[str, TeamRating], year: int, stage: str) -> str:
    projection = match_projection(team_a, team_b, ratings, year, stage)
    goals_a, goals_b = simulate_group_match(projection)
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    p_a = sigmoid((projection["rating_diff_team1"] + random.gauss(0.0, PENALTY_NOISE)) / 185.0)
    return team_a if random.random() < p_a else team_b


def run_tournament_sim(year: int, ratings: dict[str, TeamRating], group_matches: list[dict[str, Any]]) -> dict[str, set[str]]:
    table = {
        normalize_team(team): {"points": 0, "goals_for": 0, "goals_against": 0, "goal_diff": 0}
        for teams in GROUPS[year].values()
        for team in teams
    }
    for match in group_matches:
        home = match["home_team"]
        away = match["away_team"]
        projection = match_projection(home, away, ratings, year, "Group Stage")
        hs, aw = simulate_group_match(projection)
        table[home]["goals_for"] += hs
        table[home]["goals_against"] += aw
        table[away]["goals_for"] += aw
        table[away]["goals_against"] += hs
        if hs > aw:
            table[home]["points"] += 3
        elif aw > hs:
            table[away]["points"] += 3
        else:
            table[home]["points"] += 1
            table[away]["points"] += 1
    for stats in table.values():
        stats["goal_diff"] = stats["goals_for"] - stats["goals_against"]
    rankings = {
        group: rank_group([normalize_team(team) for team in teams], table)
        for group, teams in GROUPS[year].items()
    }
    reached = {
        "qualified": set(),
        "round_of_16": set(),
        "quarter_final": set(),
        "semi_final": set(),
        "final": set(),
        "champion": set(),
    }
    for ranking in rankings.values():
        reached["qualified"].update(ranking[:2])
        reached["round_of_16"].update(ranking[:2])

    winners: dict[str, str] = {}
    for match_id, slot_a, slot_b in R16_BRACKET:
        team_a = resolve_slot(slot_a, rankings, winners)
        team_b = resolve_slot(slot_b, rankings, winners)
        stage = STAGE_BY_MATCH[match_id]
        winner = knockout_winner(team_a, team_b, ratings, year, stage)
        winners[match_id] = winner
        if stage == "Round of 16":
            reached["quarter_final"].add(winner)
        elif stage == "Quarter-final":
            reached["semi_final"].add(winner)
        elif stage == "Semi-final":
            reached["final"].add(winner)
        elif stage == "Final":
            reached["champion"].add(winner)
    return reached


def run_probability_simulation(year: int, variant: str, ratings: dict[str, TeamRating], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    random.seed(year * 100 + (1 if variant == "model_v1" else 2))
    group_matches = [match for match in matches if match["stage"] == "Group Stage"]
    counters = {key: Counter() for key in ["qualified", "round_of_16", "quarter_final", "semi_final", "final", "champion"]}
    for _ in range(SIMULATIONS):
        reached = run_tournament_sim(year, ratings, group_matches)
        for stage, teams in reached.items():
            counters[stage].update(teams)
    rows: list[dict[str, Any]] = []
    for group, teams in GROUPS[year].items():
        for original_team in teams:
            team = normalize_team(original_team)
            rating = ratings[team]
            rows.append(
                {
                    "year": year,
                    "variant": variant,
                    "team": display_team(team),
                    "group": group,
                    "elo": round(rating.elo, 3),
                    "elo_rank": rating.elo_rank,
                    "total_rating": round(rating.total_rating, 3),
                    "contender_tier": rating.contender_tier,
                    "qualify_pct": round(100 * counters["qualified"][team] / SIMULATIONS, 2),
                    "quarter_final_pct": round(100 * counters["quarter_final"][team] / SIMULATIONS, 2),
                    "semi_final_pct": round(100 * counters["semi_final"][team] / SIMULATIONS, 2),
                    "final_pct": round(100 * counters["final"][team] / SIMULATIONS, 2),
                    "champion_pct": round(100 * counters["champion"][team] / SIMULATIONS, 2),
                    "recent_form_adjustment": round(rating.recent_form_adjustment, 3),
                    "ceiling_adjustment": round(rating.ceiling_adjustment, 3),
                    "tactical_adjustment": round(rating.tactical_adjustment, 3),
                    "tactical_data_status": rating.tactical_data_status,
                }
            )
    rows.sort(key=lambda row: (row["year"], row["variant"], row["champion_pct"], row["final_pct"]), reverse=True)
    current = None
    rank = 0
    for row in rows:
        key = (row["year"], row["variant"])
        if key != current:
            current = key
            rank = 0
        rank += 1
        row["title_rank"] = rank
    return rows


def evaluate_group_matches(year: int, variant: str, ratings: dict[str, TeamRating], matches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    brier_sum = 0.0
    log_loss_sum = 0.0
    favorite_correct = 0
    selected = 0
    selected_correct = 0
    avoid_selected = 0
    avoid_correct = 0
    pass_count = 0
    group_matches = [match for match in matches if match["stage"] == "Group Stage"]
    for match in group_matches:
        projection = match_projection(match["home_team"], match["away_team"], ratings, year, "Group Stage")
        probs = {
            "home_win": projection["team1_win_probability"],
            "draw": projection["draw_probability"],
            "away_win": projection["team2_win_probability"],
        }
        if match["home_score"] > match["away_score"]:
            actual = "home_win"
        elif match["away_score"] > match["home_score"]:
            actual = "away_win"
        else:
            actual = "draw"
        y = {key: 1.0 if key == actual else 0.0 for key in probs}
        brier_sum += sum((probs[key] - y[key]) ** 2 for key in probs) / 3.0
        log_loss_sum += -math.log(max(1e-9, probs[actual]))
        favorite = "home_win" if probs["home_win"] >= probs["away_win"] and probs["home_win"] >= probs["draw"] else "away_win" if probs["away_win"] >= probs["draw"] else "draw"
        if favorite == actual:
            favorite_correct += 1

        verdict_team, verdict_type, confidence = public_verdict(projection)
        verdict_correct = ""
        if verdict_type in {"win", "win lean"}:
            selected += 1
            expected = "home_win" if verdict_team == match["home_team"] else "away_win"
            verdict_correct = str(actual == expected)
            selected_correct += int(actual == expected)
        elif verdict_type == "avoid defeat":
            avoid_selected += 1
            if verdict_team == match["home_team"]:
                ok = actual in {"home_win", "draw"}
            else:
                ok = actual in {"away_win", "draw"}
            avoid_correct += int(ok)
            verdict_correct = str(ok)
        elif verdict_type == "no strong edge":
            pass_count += 1

        rows.append(
            {
                "year": year,
                "variant": variant,
                "date": match["date"],
                "group": match["group"],
                "home_team": display_team(match["home_team"]),
                "away_team": display_team(match["away_team"]),
                "actual_score": f"{match['home_score']}-{match['away_score']}",
                "actual_result": actual,
                "home_win_prob": round(probs["home_win"], 4),
                "draw_prob": round(probs["draw"], 4),
                "away_win_prob": round(probs["away_win"], 4),
                "model_favorite_result": favorite,
                "favorite_correct": str(favorite == actual),
                "public_verdict_team": display_team(verdict_team) if verdict_team else "",
                "public_verdict_type": verdict_type,
                "confidence": confidence,
                "verdict_correct": verdict_correct,
            }
        )
    n = len(group_matches)
    metrics = {
        "year": year,
        "variant": variant,
        "matches": n,
        "group_wdl_brier": round(brier_sum / n, 4),
        "group_wdl_log_loss": round(log_loss_sum / n, 4),
        "favorite_accuracy_pct": round(100 * favorite_correct / n, 2),
        "selected_win_pick_count": selected,
        "selected_win_pick_accuracy_pct": round(100 * selected_correct / selected, 2) if selected else "",
        "avoid_defeat_pick_count": avoid_selected,
        "avoid_defeat_accuracy_pct": round(100 * avoid_correct / avoid_selected, 2) if avoid_selected else "",
        "pass_count": pass_count,
    }
    return rows, metrics


def evaluate_tournament(year: int, variant: str, odds_rows: list[dict[str, Any]], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actual = actual_stage_sets(matches)
    by_team = {normalize_team(row["team"]): row for row in odds_rows if row["year"] == year and row["variant"] == variant}
    champion = next(iter(actual["champion"]))
    champion_row = by_team[champion]
    rows = [
        {
            "year": year,
            "variant": variant,
            "metric": "actual_champion",
            "value": display_team(champion),
        },
        {
            "year": year,
            "variant": variant,
            "metric": "champion_pre_tournament_rank",
            "value": champion_row["title_rank"],
        },
        {
            "year": year,
            "variant": variant,
            "metric": "champion_pre_tournament_probability_pct",
            "value": champion_row["champion_pct"],
        },
        {
            "year": year,
            "variant": variant,
            "metric": "champion_in_top_5",
            "value": str(int(champion_row["title_rank"]) <= 5),
        },
        {
            "year": year,
            "variant": variant,
            "metric": "champion_in_top_10",
            "value": str(int(champion_row["title_rank"]) <= 10),
        },
    ]
    for stage, probability_column in [
        ("qualified", "qualify_pct"),
        ("quarter_final", "quarter_final_pct"),
        ("semi_final", "semi_final_pct"),
        ("final", "final_pct"),
        ("champion", "champion_pct"),
    ]:
        brier = 0.0
        for team, row in by_team.items():
            p = float(row[probability_column]) / 100.0
            y = 1.0 if team in actual[stage] else 0.0
            brier += (p - y) ** 2
        rows.append(
            {
                "year": year,
                "variant": variant,
                "metric": f"{stage}_brier",
                "value": round(brier / len(by_team), 4),
            }
        )
    return rows


def report_md(match_metrics: list[dict[str, Any]], tournament_metrics: list[dict[str, Any]], odds_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# World Cup Model v1 Backtest",
        "",
        "Backtest tournaments: 2018 and 2022.",
        "",
        "The test is leak-free for team strength: ratings/form are taken only from matches before each tournament start date. Tactical priors are only used when historical StatsBomb World Cup data existed before that tournament; 2018 has no open tactical prior, 2022 can use 2018.",
        "",
        "## Group Match Metrics",
        "",
        "| Year | Variant | Brier | Log Loss | Favorite Accuracy | Win Picks | Win Pick Accuracy | Avoid Picks | Avoid Accuracy | Passes |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in match_metrics:
        lines.append(
            f"| {row['year']} | {row['variant']} | {row['group_wdl_brier']} | {row['group_wdl_log_loss']} | "
            f"{row['favorite_accuracy_pct']}% | {row['selected_win_pick_count']} | {row['selected_win_pick_accuracy_pct']}% | "
            f"{row['avoid_defeat_pick_count']} | {row['avoid_defeat_accuracy_pct']}% | {row['pass_count']} |"
        )
    lines.extend(["", "## Champion Backtest", "", "| Year | Variant | Champion | Rank | Probability | Top 5? | Top 10? |", "|---:|---|---|---:|---:|---|---|"])
    by_key = defaultdict(dict)
    for row in tournament_metrics:
        by_key[(row["year"], row["variant"])][row["metric"]] = row["value"]
    for key in sorted(by_key):
        row = by_key[key]
        lines.append(
            f"| {key[0]} | {key[1]} | {row['actual_champion']} | {row['champion_pre_tournament_rank']} | "
            f"{row['champion_pre_tournament_probability_pct']}% | {row['champion_in_top_5']} | {row['champion_in_top_10']} |"
        )
    lines.extend(["", "## Top 5 Title Odds By Tournament", ""])
    for year in [2018, 2022]:
        for variant in ["model_v1", "elo_only"]:
            top = [row for row in odds_rows if row["year"] == year and row["variant"] == variant]
            top.sort(key=lambda row: int(row["title_rank"]))
            lines.append(f"### {year} {variant}")
            lines.append("")
            lines.append("| Rank | Team | Champion % | Final % | Semi % |")
            lines.append("|---:|---|---:|---:|---:|")
            for row in top[:5]:
                lines.append(f"| {row['title_rank']} | {row['team']} | {row['champion_pct']}% | {row['final_pct']}% | {row['semi_final_pct']}% |")
            lines.append("")
    lines.extend(
        [
            "## Read",
            "",
            "The useful question is not whether the model picked the exact champion. The useful questions are whether the champion was among serious contenders, whether probabilities were calibrated, whether group qualification odds were sane, and whether the layered model improves on Elo-only.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    all_odds: list[dict[str, Any]] = []
    all_group_predictions: list[dict[str, Any]] = []
    all_match_metrics: list[dict[str, Any]] = []
    all_tournament_metrics: list[dict[str, Any]] = []
    all_team_ratings: list[dict[str, Any]] = []

    for year in [2018, 2022]:
        matches = load_worldcup_matches(year)
        for variant in ["model_v1", "elo_only"]:
            ratings = build_ratings(year, variant)
            all_team_ratings.extend(
                {
                    "year": year,
                    "variant": variant,
                    "team": display_team(team),
                    "group": rating.group,
                    "elo": round(rating.elo, 3),
                    "elo_rank": rating.elo_rank,
                    "total_rating": round(rating.total_rating, 3),
                    "recent_form_adjustment": round(rating.recent_form_adjustment, 3),
                    "ceiling_adjustment": round(rating.ceiling_adjustment, 3),
                    "tactical_adjustment": round(rating.tactical_adjustment, 3),
                    "contender_tier": rating.contender_tier,
                    "tactical_data_status": rating.tactical_data_status,
                }
                for team, rating in ratings.items()
            )
            odds_rows = run_probability_simulation(year, variant, ratings, matches)
            all_odds.extend(odds_rows)
            group_rows, metrics = evaluate_group_matches(year, variant, ratings, matches)
            all_group_predictions.extend(group_rows)
            all_match_metrics.append(metrics)
            all_tournament_metrics.extend(evaluate_tournament(year, variant, odds_rows, matches))

    write_csv(
        PROCESSED / "backtest_v1_tournament_odds.csv",
        all_odds,
        [
            "title_rank",
            "year",
            "variant",
            "team",
            "group",
            "elo",
            "elo_rank",
            "total_rating",
            "contender_tier",
            "qualify_pct",
            "quarter_final_pct",
            "semi_final_pct",
            "final_pct",
            "champion_pct",
            "recent_form_adjustment",
            "ceiling_adjustment",
            "tactical_adjustment",
            "tactical_data_status",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v1_team_ratings.csv",
        all_team_ratings,
        [
            "year",
            "variant",
            "team",
            "group",
            "elo",
            "elo_rank",
            "total_rating",
            "recent_form_adjustment",
            "ceiling_adjustment",
            "tactical_adjustment",
            "contender_tier",
            "tactical_data_status",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v1_group_match_predictions.csv",
        all_group_predictions,
        [
            "year",
            "variant",
            "date",
            "group",
            "home_team",
            "away_team",
            "actual_score",
            "actual_result",
            "home_win_prob",
            "draw_prob",
            "away_win_prob",
            "model_favorite_result",
            "favorite_correct",
            "public_verdict_team",
            "public_verdict_type",
            "confidence",
            "verdict_correct",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v1_match_metrics.csv",
        all_match_metrics,
        [
            "year",
            "variant",
            "matches",
            "group_wdl_brier",
            "group_wdl_log_loss",
            "favorite_accuracy_pct",
            "selected_win_pick_count",
            "selected_win_pick_accuracy_pct",
            "avoid_defeat_pick_count",
            "avoid_defeat_accuracy_pct",
            "pass_count",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v1_tournament_metrics.csv",
        all_tournament_metrics,
        ["year", "variant", "metric", "value"],
    )
    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "world_cup_model_v1_backtest_report.md").write_text(
        report_md(all_match_metrics, all_tournament_metrics, all_odds),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "simulations_per_variant": SIMULATIONS,
                "match_metrics": all_match_metrics,
                "report": str(OUTPUTS / "world_cup_model_v1_backtest_report.md"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
