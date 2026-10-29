#!/usr/bin/env python3
"""Audit and backtest package for World Cup Model v2.1.

This script does two things:
1. Explains sensitive 2026 rankings using feature layers and bracket path.
2. Runs a leak-aware v2.1-style backtest on 2018/2022 using historical squad
   tables, Elo/form cutoffs, and pre-tournament public squad metadata.
"""

from __future__ import annotations

import csv
import json
import math
import random
import re
import urllib.request
from collections import Counter, defaultdict
from io import StringIO
from pathlib import Path
from statistics import mean
from typing import Any

import lxml.html
import pandas as pd

import backtest_worldcup_model_v1 as bt
import build_player_impact_v21 as pi


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "squads"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

SIMULATIONS = 20000
BASE_GOAL_RATE = 1.18
POWER_GOAL_SCALE = 43.0
HOST_ADVANTAGE_GROUP_POWER = 3.0
HOST_ADVANTAGE_KNOCKOUT_POWER = 2.0
KNOCKOUT_NOISE = 3.5

WEIGHTS = {
    "elo_score": 0.30,
    "squad_score": 0.25,
    "manager_score": 0.15,
    "recent_form_score": 0.10,
    "tactical_score": 0.10,
    "ceiling_score": 0.05,
    "availability_score": 0.05,
}

SENSITIVE_TEAMS = ["Germany", "Colombia", "Japan", "Portugal", "Netherlands"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def percentile_scores(values: dict[str, float]) -> dict[str, float]:
    ranked = sorted(values.items(), key=lambda item: item[1])
    if len(ranked) <= 1:
        return {team: 50.0 for team in values}
    return {team: 100.0 * idx / (len(ranked) - 1) for idx, (team, _) in enumerate(ranked)}


def normalize_team(team: str) -> str:
    return bt.normalize_team(team)


def ceiling_score_from_tier(tier: str) -> float:
    if "Tier 1" in tier:
        return 86.0
    if "Tier 2" in tier:
        return 66.0
    if "Tier 3" in tier:
        return 46.0
    return 25.0


def manager_proxy_score(elo_score: float, tier: str) -> float:
    base = 48.0 + 0.34 * elo_score
    if "Tier 1" in tier:
        base += 8.0
    elif "Tier 2" in tier:
        base += 3.0
    elif "Tier 4" in tier:
        base -= 4.0
    return clamp(base, 43.0, 88.0)


def expected_goals(power_a: float, power_b: float) -> tuple[float, float]:
    diff = power_a - power_b
    return (
        clamp(BASE_GOAL_RATE * math.exp(diff / POWER_GOAL_SCALE), 0.25, 3.2),
        clamp(BASE_GOAL_RATE * math.exp(-diff / POWER_GOAL_SCALE), 0.25, 3.2),
    )


def poisson_pmf(lam: float, max_goals: int = 9) -> list[float]:
    probs = [math.exp(-lam)]
    for k in range(1, max_goals + 1):
        probs.append(probs[-1] * lam / k)
    total = sum(probs)
    probs[-1] += max(0.0, 1.0 - total)
    return probs


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


def sample_poisson(lam: float) -> int:
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= random.random()
    return k - 1


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def fetch_historical_squads(year: int) -> str:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"wikipedia_{year}_world_cup_squads.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    url = f"https://en.wikipedia.org/wiki/{year}_FIFA_World_Cup_squads"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Codex local research"})
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
    path.write_text(html, encoding="utf-8")
    return html


def parse_historical_squad_tables(year: int) -> dict[str, pd.DataFrame]:
    html = fetch_historical_squads(year)
    doc = lxml.html.fromstring(html)
    squad_tables: dict[str, pd.DataFrame] = {}
    for table in doc.xpath('//table[contains(@class,"wikitable")]'):
        df = pd.read_html(StringIO(lxml.html.tostring(table, encoding="unicode")))[0]
        if "Player" not in df.columns or "Club" not in df.columns:
            continue
        heading = table.xpath('preceding::*[self::h2 or self::h3 or self::h4][1]')
        if not heading:
            continue
        team = normalize_team(heading[0].text_content().strip().replace("[edit]", ""))
        squad_tables[team] = df
    return squad_tables


def team_seed_from_elo(elo_score: float, tier: str) -> float:
    seed = 46.0 + 0.42 * elo_score
    if "Tier 1" in tier:
        seed += 8
    elif "Tier 2" in tier:
        seed += 3
    elif "Tier 4" in tier:
        seed -= 4
    return clamp(seed, 42.0, 88.0)


def build_historical_player_team_scores(year: int, elo_scores: dict[str, float], ratings: dict[str, bt.TeamRating]) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    squad_tables = parse_historical_squad_tables(year)
    player_rows: list[dict[str, Any]] = []
    team_scores: dict[str, dict[str, float]] = {}

    for group, teams in bt.GROUPS[year].items():
        for display in teams:
            team = normalize_team(display)
            if team not in squad_tables:
                raise RuntimeError(f"Missing historical squad table for {team} in {year}")
            table = squad_tables[team]
            rating = ratings[team]
            team_squad_seed = team_seed_from_elo(elo_scores[team], rating.contender_tier)
            expected_xi_seed = clamp(team_squad_seed + 1.0, 42, 90)
            cap_values = [float(value) for value in table["Caps"].fillna(0).tolist()]
            max_caps = max(cap_values) if cap_values else 1.0
            players: list[dict[str, Any]] = []
            for _, raw in table.iterrows():
                player_name, is_captain = pi.clean_player(str(raw["Player"]))
                position = str(raw["Pos."])
                if position not in pi.POSITION_UNIT:
                    position = "MF"
                age = pi.parse_age(str(raw["Date of birth (age)"]))
                caps = float(raw["Caps"] or 0)
                goals = float(raw["Goals"] or 0)
                club = str(raw["Club"])
                club_score, club_status = pi.club_level_score(club, team_squad_seed, rating.contender_tier)
                age_score = pi.age_prime_score(age, position)
                international_score = pi.cap_score(caps)
                goal_score = pi.goal_role_score(goals, caps, position)
                goal_weight = {"GK": 0.0, "DF": 0.10, "MF": 0.18, "FW": 0.28}.get(position, 0.18)
                scorer_bonus = 4.0 if position == "FW" and goals >= 35 and goals / max(caps, 1) >= 0.55 else 0.0
                if goals >= 70:
                    scorer_bonus += 4.0
                national_role = clamp(
                    44
                    + 30 * (caps / max(max_caps, 1))
                    + 0.16 * (international_score - 50)
                    + goal_weight * (goal_score - 50)
                    + (6 if is_captain else 0)
                    + scorer_bonus,
                    40,
                    96,
                )
                recent_minutes = clamp(
                    0.52 * club_score
                    + 0.22 * expected_xi_seed
                    + 0.16 * age_score
                    + 0.10 * international_score,
                    42,
                    95,
                )
                tactical_fit = clamp(
                    0.40 * national_role
                    + 0.25 * expected_xi_seed
                    + 0.20 * club_score
                    + 0.15 * age_score
                    + pi.position_age_adjustment(position, age),
                    42,
                    96,
                )
                form_score = clamp(
                    0.50 * recent_minutes
                    + 0.25 * age_score
                    + 0.15 * club_score
                    + 0.10 * international_score,
                    42,
                    96,
                )
                tournament_experience = clamp(
                    0.58 * international_score + 0.22 * club_score + 0.20 * age_score + (4 if is_captain else 0),
                    42,
                    97,
                )
                overall = clamp(
                    0.36 * club_score
                    + 0.22 * team_squad_seed
                    + 0.16 * international_score
                    + 0.12 * age_score
                    + 0.12 * goal_score
                    + 0.02 * expected_xi_seed,
                    42,
                    96,
                )
                pre_role_rating = clamp(0.46 * overall + 0.34 * national_role + 0.20 * club_score, 40, 97)
                players.append(
                    {
                        "year": year,
                        "team": team,
                        "group": group,
                        "player_name": player_name,
                        "position": position,
                        "unit": pi.POSITION_UNIT[position],
                        "age": age,
                        "caps": int(caps),
                        "goals": int(goals),
                        "club": club,
                        "is_captain": is_captain,
                        "overall_rating": round(overall, 2),
                        "club_level_score": round(club_score, 2),
                        "national_role_score": round(national_role, 2),
                        "tactical_fit_score": round(tactical_fit, 2),
                        "form_score": round(form_score, 2),
                        "tournament_experience_score": round(tournament_experience, 2),
                        "pre_role_rating": round(pre_role_rating, 2),
                        "club_score_source": club_status,
                    }
                )
            pi.expected_role_rows(players)
            for player in players:
                player["impact_score"] = round(
                    clamp(
                        0.30 * player["overall_rating"]
                        + 0.20 * player["club_level_score"]
                        + 0.22 * player["national_role_score"]
                        + 0.15 * player["tactical_fit_score"]
                        + 0.10 * player["form_score"]
                        + 0.03 * player["tournament_experience_score"],
                        40,
                        97,
                    ),
                    2,
                )
                player_rows.append(player)

            starters = [p for p in players if p["expected_role"] == "Starter"]
            rotation = [p for p in players if p["expected_role"] == "Rotation"]
            squad_quality = mean([p["impact_score"] for p in players])
            expected_xi = mean([p["impact_score"] for p in starters]) if starters else squad_quality
            bench_depth = mean([p["impact_score"] for p in rotation]) if rotation else squad_quality
            team_scores[team] = {
                "squad_quality_score": squad_quality,
                "expected_xi_score": expected_xi,
                "bench_depth_score": bench_depth,
                "squad_score": 0.45 * squad_quality + 0.35 * expected_xi + 0.20 * bench_depth,
                "players_entered": len(players),
            }
    return player_rows, team_scores


def build_tactical_scores(year: int) -> dict[str, float]:
    tactical = bt.build_tactical_profiles_as_of(year)
    return {team: clamp(50.0 + safe_float(profile, "tactical_adjustment") * 1.35, 0.0, 100.0) for team, profile in tactical.items()}


def build_power_ratings(year: int) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    v1_like = bt.build_ratings(year, "model_v1")
    teams = [normalize_team(team) for group in bt.GROUPS[year].values() for team in group]
    elo_scores = percentile_scores({team: v1_like[team].elo for team in teams})
    recent_scores = percentile_scores({team: v1_like[team].recent_form_adjustment for team in teams})
    tactical_scores = build_tactical_scores(year)
    player_rows, squad_scores = build_historical_player_team_scores(year, elo_scores, v1_like)
    powers: dict[str, dict[str, Any]] = {}
    for group, group_teams in bt.GROUPS[year].items():
        for original in group_teams:
            team = normalize_team(original)
            rating = v1_like[team]
            manager_score = manager_proxy_score(elo_scores[team], rating.contender_tier)
            tactical_score = tactical_scores.get(team, 50.0)
            ceiling_score = ceiling_score_from_tier(rating.contender_tier)
            availability_score = 100.0
            squad_score = squad_scores[team]["squad_score"]
            power = (
                elo_scores[team] * WEIGHTS["elo_score"]
                + squad_score * WEIGHTS["squad_score"]
                + manager_score * WEIGHTS["manager_score"]
                + recent_scores[team] * WEIGHTS["recent_form_score"]
                + tactical_score * WEIGHTS["tactical_score"]
                + ceiling_score * WEIGHTS["ceiling_score"]
                + availability_score * WEIGHTS["availability_score"]
            )
            powers[team] = {
                "year": year,
                "team": team,
                "group": group,
                "elo_score": round(elo_scores[team], 3),
                "squad_score": round(squad_score, 3),
                "manager_score": round(manager_score, 3),
                "recent_form_score": round(recent_scores[team], 3),
                "tactical_score": round(tactical_score, 3),
                "ceiling_score": round(ceiling_score, 3),
                "availability_score": round(availability_score, 3),
                "v21_power_score": round(power, 3),
                "contender_tier": rating.contender_tier,
                "players_entered": squad_scores[team]["players_entered"],
            }
    return powers, player_rows


def host_power(team: str, year: int, stage: str) -> float:
    if team != bt.HOSTS[year]:
        return 0.0
    return HOST_ADVANTAGE_GROUP_POWER if stage == "Group Stage" else HOST_ADVANTAGE_KNOCKOUT_POWER


def match_projection(team_a: str, team_b: str, powers: dict[str, dict[str, Any]], year: int, stage: str) -> dict[str, Any]:
    power_a = powers[team_a]["v21_power_score"] + host_power(team_a, year, stage)
    power_b = powers[team_b]["v21_power_score"] + host_power(team_b, year, stage)
    lambda_a, lambda_b = expected_goals(power_a, power_b)
    p_a, p_draw, p_b = scoreline_probabilities(lambda_a, lambda_b)
    return {
        "team1": team_a,
        "team2": team_b,
        "power_diff_team1": power_a - power_b,
        "team1_win_probability": p_a,
        "draw_probability": p_draw,
        "team2_win_probability": p_b,
        "team1_xg_internal": lambda_a,
        "team2_xg_internal": lambda_b,
    }


def simulate_group_match(projection: dict[str, Any]) -> tuple[int, int]:
    return sample_poisson(projection["team1_xg_internal"]), sample_poisson(projection["team2_xg_internal"])


def knockout_winner(team_a: str, team_b: str, powers: dict[str, dict[str, Any]], year: int, stage: str) -> str:
    projection = match_projection(team_a, team_b, powers, year, stage)
    goals_a, goals_b = simulate_group_match(projection)
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    diff = projection["power_diff_team1"] + random.gauss(0.0, KNOCKOUT_NOISE)
    return team_a if random.random() < sigmoid(diff / 10.0) else team_b


def run_tournament_sim(year: int, powers: dict[str, dict[str, Any]], group_matches: list[dict[str, Any]]) -> dict[str, set[str]]:
    table = {
        normalize_team(team): {"points": 0, "goals_for": 0, "goals_against": 0, "goal_diff": 0}
        for teams in bt.GROUPS[year].values()
        for team in teams
    }
    for match in group_matches:
        home = match["home_team"]
        away = match["away_team"]
        projection = match_projection(home, away, powers, year, "Group Stage")
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
        group: bt.rank_group([normalize_team(team) for team in teams], table)
        for group, teams in bt.GROUPS[year].items()
    }
    reached = {key: set() for key in ["qualified", "round_of_16", "quarter_final", "semi_final", "final", "champion"]}
    for ranking in rankings.values():
        reached["qualified"].update(ranking[:2])
        reached["round_of_16"].update(ranking[:2])

    winners: dict[str, str] = {}
    for match_id, slot_a, slot_b in bt.R16_BRACKET:
        team_a = bt.resolve_slot(slot_a, rankings, winners)
        team_b = bt.resolve_slot(slot_b, rankings, winners)
        stage = bt.STAGE_BY_MATCH[match_id]
        winner = knockout_winner(team_a, team_b, powers, year, stage)
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


def run_probability_simulation(year: int, powers: dict[str, dict[str, Any]], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    random.seed(year * 100 + 21)
    group_matches = [match for match in matches if match["stage"] == "Group Stage"]
    counters = {key: Counter() for key in ["qualified", "round_of_16", "quarter_final", "semi_final", "final", "champion"]}
    for _ in range(SIMULATIONS):
        reached = run_tournament_sim(year, powers, group_matches)
        for stage, teams in reached.items():
            counters[stage].update(teams)
    rows = []
    for group, teams in bt.GROUPS[year].items():
        for original in teams:
            team = normalize_team(original)
            rows.append(
                {
                    "year": year,
                    "variant": "model_v21_proxy",
                    "team": bt.display_team(team),
                    "group": group,
                    "v21_power_score": powers[team]["v21_power_score"],
                    "qualify_pct": round(100 * counters["qualified"][team] / SIMULATIONS, 2),
                    "quarter_final_pct": round(100 * counters["quarter_final"][team] / SIMULATIONS, 2),
                    "semi_final_pct": round(100 * counters["semi_final"][team] / SIMULATIONS, 2),
                    "final_pct": round(100 * counters["final"][team] / SIMULATIONS, 2),
                    "champion_pct": round(100 * counters["champion"][team] / SIMULATIONS, 2),
                }
            )
    rows.sort(key=lambda row: (row["year"], -float(row["champion_pct"])))
    for year_value in sorted({row["year"] for row in rows}):
        rank = 1
        for row in [r for r in rows if r["year"] == year_value]:
            row["title_rank"] = rank
            rank += 1
    return rows


def match_metrics(year: int, powers: dict[str, dict[str, Any]], matches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    brier = 0.0
    log_loss = 0.0
    fav_correct = 0
    n = 0
    for match in matches:
        if match["stage"] != "Group Stage":
            continue
        projection = match_projection(match["home_team"], match["away_team"], powers, year, "Group Stage")
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
        pred = max(probs, key=probs.get)
        fav_correct += int(pred == actual)
        n += 1
        for outcome, prob in probs.items():
            y = 1.0 if outcome == actual else 0.0
            brier += (prob - y) ** 2
        log_loss += -math.log(max(probs[actual], 1e-9))
        rows.append(
            {
                "year": year,
                "match_id": match["match_id"],
                "date": match["date"],
                "home_team": bt.display_team(match["home_team"]),
                "away_team": bt.display_team(match["away_team"]),
                "actual_result": actual,
                "predicted_result": pred,
                "home_win_probability": round(probs["home_win"], 4),
                "draw_probability": round(probs["draw"], 4),
                "away_win_probability": round(probs["away_win"], 4),
                "correct": pred == actual,
            }
        )
    metrics = {
        "year": year,
        "variant": "model_v21_proxy",
        "group_match_brier": round(brier / (n * 3), 4),
        "group_match_log_loss": round(log_loss / n, 4),
        "favorite_accuracy_pct": round(100 * fav_correct / n, 2),
        "matches": n,
    }
    return rows, metrics


def tournament_metrics(year: int, odds_rows: list[dict[str, Any]], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actual = bt.actual_stage_sets(matches)
    by_team = {normalize_team(row["team"]): row for row in odds_rows if int(row["year"]) == year}
    champion = next(iter(actual["champion"]))
    champion_row = by_team[champion]
    rows = [
        {
            "year": year,
            "variant": "model_v21_proxy",
            "metric": "champion_rank",
            "value": champion_row["title_rank"],
            "context": bt.display_team(champion),
        },
        {
            "year": year,
            "variant": "model_v21_proxy",
            "metric": "champion_probability_pct",
            "value": champion_row["champion_pct"],
            "context": bt.display_team(champion),
        },
    ]
    for stage, col in [
        ("qualified", "qualify_pct"),
        ("quarter_final", "quarter_final_pct"),
        ("semi_final", "semi_final_pct"),
        ("final", "final_pct"),
        ("champion", "champion_pct"),
    ]:
        brier = 0.0
        for team, row in by_team.items():
            p = float(row[col]) / 100.0
            y = 1.0 if team in actual[stage] else 0.0
            brier += (p - y) ** 2
        rows.append(
            {
                "year": year,
                "variant": "model_v21_proxy",
                "metric": f"{stage}_brier",
                "value": round(brier / len(by_team), 4),
                "context": f"{len(actual[stage])} actual teams",
            }
        )
    return rows


def build_sensitive_audit() -> list[dict[str, Any]]:
    powers = {row["team"]: row for row in read_csv(PROCESSED / "model_v21_team_power.csv")}
    odds = {row["team"]: row for row in read_csv(PROCESSED / "model_v21_tournament_odds.csv")}
    rows = []
    for team in SENSITIVE_TEAMS:
        power = powers[team if team != "USA" else "United States"]
        odd = odds[team]
        contributions = {
            key: safe_float(power, key) * weight
            for key, weight in WEIGHTS.items()
        }
        notes = {
            "Germany": "Higher recent-form/tactical score plus clean Group E winner path.",
            "Colombia": "Same group as Portugal but higher power and better group-winner probability.",
            "Japan": "Slightly ahead of Netherlands mostly through recent form and Group F winner path.",
            "Portugal": "Strong squad, but low recent-form/manager-tactical layers and Group K path pressure.",
            "Netherlands": "Strong squad/Elo, but low recent form and second-place risk behind Japan; 2F can meet 1C early.",
        }[team]
        rows.append(
            {
                "team": team,
                "group": odd["group"],
                "title_rank": odd["title_rank"],
                "power_rank": power["v21_power_rank"],
                "champion_pct": odd["champion_pct"],
                "final_pct": odd["final_pct"],
                "group_first_pct": odd["group_first_pct"],
                "group_second_pct": odd["group_second_pct"],
                "qualify_knockout_pct": odd["qualify_knockout_pct"],
                "power_score": power["v2_power_score"],
                "elo_score": power["elo_score"],
                "squad_score": power["squad_score"],
                "manager_score": power["manager_score"],
                "recent_form_score": power["recent_form_score"],
                "tactical_score": power["tactical_score"],
                "ceiling_score": power["ceiling_score"],
                "elo_contribution": round(contributions["elo_score"], 3),
                "squad_contribution": round(contributions["squad_score"], 3),
                "manager_contribution": round(contributions["manager_score"], 3),
                "recent_form_contribution": round(contributions["recent_form_score"], 3),
                "tactical_contribution": round(contributions["tactical_score"], 3),
                "ceiling_contribution": round(contributions["ceiling_score"], 3),
                "availability_contribution": round(contributions["availability_score"], 3),
                "audit_note": notes,
            }
        )
    return rows


def write_report(match_metric_rows: list[dict[str, Any]], tournament_metric_rows: list[dict[str, Any]], audit_rows: list[dict[str, Any]], odds_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# World Cup Model v2.1 Audit + Backtest",
        "",
        "This package audits the sensitive 2026 rankings and runs a v2.1-style historical backtest on 2018 and 2022.",
        "",
        "## Sensitive Ranking Audit",
        "",
        "| Team | Title rank | Champion % | Group 1st % | Power | Main note |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in audit_rows:
        lines.append(
            f"| {row['team']} | {row['title_rank']} | {row['champion_pct']}% | {row['group_first_pct']}% | {row['power_score']} | {row['audit_note']} |"
        )
    lines.extend(
        [
            "",
            "## Historical Backtest Metrics",
            "",
            "| Year | Brier | Log loss | Favorite accuracy | Matches |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in match_metric_rows:
        lines.append(
            f"| {row['year']} | {row['group_match_brier']} | {row['group_match_log_loss']} | {row['favorite_accuracy_pct']}% | {row['matches']} |"
        )
    lines.extend(
        [
            "",
            "## Champion Test",
            "",
            "| Year | Champion | Rank | Champion probability |",
            "|---:|---|---:|---:|",
        ]
    )
    for year in [2018, 2022]:
        rank = next(row for row in tournament_metric_rows if row["year"] == year and row["metric"] == "champion_rank")
        prob = next(row for row in tournament_metric_rows if row["year"] == year and row["metric"] == "champion_probability_pct")
        lines.append(f"| {year} | {rank['context']} | {rank['value']} | {prob['value']}% |")
    lines.extend(
        [
            "",
            "## Honest Interpretation",
            "",
            "- The backtest uses historical public squad metadata, not the 2026 player table.",
            "- Manager scores are neutral historical proxies, not hand-rated historical manager data.",
            "- Club level is still a heuristic, so this tests the architecture more than a final commercial-grade data feed.",
            "- If v2.1 proxy does not clearly beat v1 on every metric, that is useful: it tells us which layers need real minutes/role data before production.",
        ]
    )
    (OUTPUTS / "world_cup_model_v21_audit_backtest_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    all_power_rows: list[dict[str, Any]] = []
    all_player_rows: list[dict[str, Any]] = []
    all_odds_rows: list[dict[str, Any]] = []
    all_match_rows: list[dict[str, Any]] = []
    match_metric_rows: list[dict[str, Any]] = []
    tournament_metric_rows: list[dict[str, Any]] = []
    for year in [2018, 2022]:
        powers, player_rows = build_power_ratings(year)
        matches = bt.load_worldcup_matches(year)
        odds_rows = run_probability_simulation(year, powers, matches)
        match_rows, match_metrics_row = match_metrics(year, powers, matches)
        tournament_rows = tournament_metrics(year, odds_rows, matches)
        power_rows = sorted(powers.values(), key=lambda row: row["v21_power_score"], reverse=True)
        for rank, row in enumerate(power_rows, start=1):
            row["v21_power_rank"] = rank
        all_power_rows.extend(power_rows)
        all_player_rows.extend(player_rows)
        all_odds_rows.extend(odds_rows)
        all_match_rows.extend(match_rows)
        match_metric_rows.append(match_metrics_row)
        tournament_metric_rows.extend(tournament_rows)

    audit_rows = build_sensitive_audit()
    write_csv(
        PROCESSED / "model_v21_sensitive_team_audit.csv",
        audit_rows,
        [
            "team",
            "group",
            "title_rank",
            "power_rank",
            "champion_pct",
            "final_pct",
            "group_first_pct",
            "group_second_pct",
            "qualify_knockout_pct",
            "power_score",
            "elo_score",
            "squad_score",
            "manager_score",
            "recent_form_score",
            "tactical_score",
            "ceiling_score",
            "elo_contribution",
            "squad_contribution",
            "manager_contribution",
            "recent_form_contribution",
            "tactical_contribution",
            "ceiling_contribution",
            "availability_contribution",
            "audit_note",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v21_team_power.csv",
        all_power_rows,
        [
            "year",
            "v21_power_rank",
            "team",
            "group",
            "elo_score",
            "squad_score",
            "manager_score",
            "recent_form_score",
            "tactical_score",
            "ceiling_score",
            "availability_score",
            "v21_power_score",
            "contender_tier",
            "players_entered",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v21_player_impact.csv",
        all_player_rows,
        [
            "year",
            "team",
            "group",
            "player_name",
            "position",
            "unit",
            "expected_role",
            "age",
            "caps",
            "goals",
            "club",
            "is_captain",
            "overall_rating",
            "club_level_score",
            "national_role_score",
            "tactical_fit_score",
            "form_score",
            "tournament_experience_score",
            "impact_score",
            "club_score_source",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v21_tournament_odds.csv",
        all_odds_rows,
        [
            "year",
            "variant",
            "title_rank",
            "team",
            "group",
            "v21_power_score",
            "qualify_pct",
            "quarter_final_pct",
            "semi_final_pct",
            "final_pct",
            "champion_pct",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v21_group_match_predictions.csv",
        all_match_rows,
        [
            "year",
            "match_id",
            "date",
            "home_team",
            "away_team",
            "actual_result",
            "predicted_result",
            "home_win_probability",
            "draw_probability",
            "away_win_probability",
            "correct",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v21_match_metrics.csv",
        match_metric_rows,
        ["year", "variant", "group_match_brier", "group_match_log_loss", "favorite_accuracy_pct", "matches"],
    )
    write_csv(
        PROCESSED / "backtest_v21_tournament_metrics.csv",
        tournament_metric_rows,
        ["year", "variant", "metric", "value", "context"],
    )
    write_report(match_metric_rows, tournament_metric_rows, audit_rows, all_odds_rows)
    (OUTPUTS / "world_cup_model_v21_audit_backtest_config.json").write_text(
        json.dumps(
            {
                "simulations": SIMULATIONS,
                "weights": WEIGHTS,
                "historical_squad_sources": {
                    "2018": "https://en.wikipedia.org/wiki/2018_FIFA_World_Cup_squads",
                    "2022": "https://en.wikipedia.org/wiki/2022_FIFA_World_Cup_squads",
                },
                "status": "v2.1-style proxy backtest; historical manager/minutes feeds not licensed",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"audit_rows": len(audit_rows), "match_metrics": match_metric_rows}, indent=2))


if __name__ == "__main__":
    main()
