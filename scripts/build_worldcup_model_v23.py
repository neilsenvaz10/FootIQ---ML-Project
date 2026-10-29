#!/usr/bin/env python3
"""World Cup prediction model v2.3.

V2.3 is a bias-control upgrade:
- manager quality is reduced from 15% to 3%
- unknown/manual-required managers are neutralized instead of punished
- a light market-sanity layer is added
- knockout resolution separates 90 minutes, extra time, and penalties
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import build_worldcup_model_v2 as v2


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
INPUTS = ROOT / "data" / "inputs"
OUTPUTS = ROOT / "outputs"

V23_CONFIG = {
    "version": "v2.3",
    "seed": 20260607,
    "simulations": 50000,
    "base_goal_rate": 1.15,
    "power_goal_scale": 62.0,
    "draw_decision_min": 0.28,
    "draw_gap_max": 0.12,
    "draw_favorite_max": 0.42,
    "firm_draw_gap_max": 0.04,
    "firm_draw_favorite_max": 0.38,
    "unknown_manager_neutral_score": 65.0,
    "group_performance_noise": 1.5,
    "knockout_performance_noise": 3.0,
    "extra_time_goal_factor": 0.28,
    "penalty_diff_scale": 35.0,
    "penalty_min_probability": 0.42,
    "penalty_max_probability": 0.58,
    "profile_input": "data/inputs/model_v21_team_profiles.csv",
    "player_impact_input": "data/processed/player_impact_v21.csv",
    "market_source": "Oddschecker 2026 World Cup winner odds article, published 2026-06-03",
    "market_source_url": "https://www.oddschecker.com/insight/football/20260603-who-is-favourite-to-win-the-world-cup-2026-latest-team-odds",
    "weights": {
        "elo_score": 0.30,
        "squad_score": 0.32,
        "recent_form_score": 0.10,
        "tactical_score": 0.10,
        "availability_score": 0.07,
        "market_score": 0.05,
        "ceiling_score": 0.03,
        "manager_score": 0.03,
    },
}

MARKET_PRIOR_ODDS = [
    {"team": "Spain", "market_rank": 1, "fractional_odds": "5/1", "confidence": 1.0},
    {"team": "France", "market_rank": 1, "fractional_odds": "5/1", "confidence": 1.0},
    {"team": "England", "market_rank": 3, "fractional_odds": "7/1", "confidence": 1.0},
    {"team": "Brazil", "market_rank": 4, "fractional_odds": "9/1", "confidence": 1.0},
    {"team": "Argentina", "market_rank": 5, "fractional_odds": "10/1", "confidence": 1.0},
    {"team": "Portugal", "market_rank": 6, "fractional_odds": "11/1", "confidence": 1.0},
]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
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


def fractional_implied_pct(fractional: str) -> float:
    numerator, denominator = fractional.split("/", 1)
    n = float(numerator)
    d = float(denominator)
    return 100.0 * d / (n + d)


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def read_player_profiles_v23() -> list[dict[str, Any]]:
    rows = v2.read_csv(INPUTS / "model_v21_team_profiles.csv")
    out = []
    neutral = V23_CONFIG["unknown_manager_neutral_score"]
    for row in rows:
        updated = dict(row)
        manager_name = (updated.get("manager_name") or "").strip().lower()
        source_status = (updated.get("profile_source_status") or "").lower()
        pedigree = safe_float(updated, "manager_pedigree_score")
        tactical_flex = safe_float(updated, "tactical_flexibility_score")
        old_score = pedigree * 0.65 + tactical_flex * 0.35
        is_unknown = manager_name in {"", "manual_required"} or "manual review required" in source_status
        updated["original_manager_score"] = round(old_score, 3)
        if is_unknown:
            updated["manager_pedigree_score"] = round(neutral, 2)
            updated["tactical_flexibility_score"] = round(neutral, 2)
            updated["manager_status_v23"] = "neutralized_unknown_manager"
            if updated.get("manager_name") == "manual_required":
                updated["manager_name"] = "manual_required_neutral"
        else:
            updated["manager_status_v23"] = "named_manager_profile"
        out.append(updated)
    return out


def build_market_prior_rows(teams: list[str]) -> list[dict[str, Any]]:
    prior_by_team = {v2.normalize_team(row["team"]): row for row in MARKET_PRIOR_ODDS}
    rows = []
    for team in teams:
        prior = prior_by_team.get(team)
        if prior:
            implied = fractional_implied_pct(prior["fractional_odds"])
            confidence = float(prior["confidence"])
            market_score = 50.0 + confidence * clamp(implied * 2.5, 0.0, 45.0)
            rows.append(
                {
                    "team": v2.display_team(team),
                    "normalized_team": team,
                    "market_rank": prior["market_rank"],
                    "fractional_odds": prior["fractional_odds"],
                    "raw_implied_pct": round(implied, 3),
                    "market_score": round(market_score, 3),
                    "confidence": confidence,
                    "source": V23_CONFIG["market_source"],
                    "source_url": V23_CONFIG["market_source_url"],
                    "note": "Top-six current outright market sanity prior; not used as betting advice.",
                }
            )
        else:
            rows.append(
                {
                    "team": v2.display_team(team),
                    "normalized_team": team,
                    "market_rank": "",
                    "fractional_odds": "",
                    "raw_implied_pct": "",
                    "market_score": 50.0,
                    "confidence": 0.0,
                    "source": "neutral_default",
                    "source_url": "",
                    "note": "No current market input used; neutral score avoids fabricating odds.",
                }
            )
    return rows


def ceiling_score_from_tier(tier: str) -> float:
    return v2.ceiling_score_from_tier(tier)


def build_team_power_v23() -> dict[str, dict[str, Any]]:
    profile_rows = read_player_profiles_v23()
    profiles = {v2.normalize_team(row["normalized_team"]): row for row in profile_rows}
    v1_rows = {v2.normalize_team(row["normalized_team"]): row for row in v2.read_csv(PROCESSED / "model_v1_team_ratings.csv")}
    teams = [v2.normalize_team(row["team"]) for row in v2.read_csv(PROCESSED / "worldcup_2026_teams.csv")]
    elo_scores = v2.percentile_scores({team: safe_float(v1_rows[team], "elo") for team in teams})
    recent_scores = v2.percentile_scores({team: safe_float(v1_rows[team], "recent_form_adjustment") for team in teams})
    tactical = v2.build_tactical_adjustments()
    availability = v2.read_availability_scores()
    market_rows = build_market_prior_rows(teams)
    market = {v2.normalize_team(row["normalized_team"]): safe_float(row, "market_score", 50.0) for row in market_rows}
    write_csv(
        PROCESSED / "model_v23_market_priors.csv",
        market_rows,
        [
            "team",
            "normalized_team",
            "market_rank",
            "fractional_odds",
            "raw_implied_pct",
            "market_score",
            "confidence",
            "source",
            "source_url",
            "note",
        ],
    )

    weights = V23_CONFIG["weights"]
    out = {}
    for team in teams:
        v1 = v1_rows[team]
        profile = profiles[team]
        squad_score = (
            safe_float(profile, "squad_quality_score") * 0.45
            + safe_float(profile, "expected_xi_score") * 0.35
            + safe_float(profile, "bench_depth_score") * 0.20
        )
        manager_score = safe_float(profile, "manager_pedigree_score") * 0.65 + safe_float(profile, "tactical_flexibility_score") * 0.35
        tactical_score = tactical.get(team, {}).get("tactical_score", 50.0)
        ceiling_score = ceiling_score_from_tier(v1["contender_tier"])
        availability_score = availability.get(team, 100.0)
        market_score = market.get(team, 50.0)
        power = (
            elo_scores[team] * weights["elo_score"]
            + squad_score * weights["squad_score"]
            + recent_scores[team] * weights["recent_form_score"]
            + float(tactical_score) * weights["tactical_score"]
            + availability_score * weights["availability_score"]
            + market_score * weights["market_score"]
            + ceiling_score * weights["ceiling_score"]
            + manager_score * weights["manager_score"]
        )
        out[team] = {
            "team": team,
            "display_team": v2.display_team(team),
            "group": v1["group"],
            "v1_total_rating": safe_float(v1, "total_rating"),
            "v1_title_tier": v1["contender_tier"],
            "elo_score": round(elo_scores[team], 3),
            "squad_score": round(squad_score, 3),
            "recent_form_score": round(recent_scores[team], 3),
            "tactical_score": round(float(tactical_score), 3),
            "availability_score": round(availability_score, 3),
            "market_score": round(market_score, 3),
            "ceiling_score": round(ceiling_score, 3),
            "manager_score": round(manager_score, 3),
            "original_manager_score": safe_float(profile, "original_manager_score"),
            "manager_status_v23": profile.get("manager_status_v23", ""),
            "v23_power_score": round(power, 3),
            "v2_power_score": round(power, 3),
            "manager_name": profile["manager_name"],
            "preferred_style": profile["preferred_style"],
            "profile_source_status": profile["profile_source_status"],
            "open_tactical_data_status": tactical.get(team, {}).get("status", "no_open_tactical_data"),
            "elo_contribution": round(elo_scores[team] * weights["elo_score"], 3),
            "squad_contribution": round(squad_score * weights["squad_score"], 3),
            "recent_form_contribution": round(recent_scores[team] * weights["recent_form_score"], 3),
            "tactical_contribution": round(float(tactical_score) * weights["tactical_score"], 3),
            "availability_contribution": round(availability_score * weights["availability_score"], 3),
            "market_contribution": round(market_score * weights["market_score"], 3),
            "ceiling_contribution": round(ceiling_score * weights["ceiling_score"], 3),
            "manager_contribution": round(manager_score * weights["manager_score"], 3),
        }
    return out


def host_power(team: str, ground: str, round_name: str) -> float:
    host = v2.HOST_COUNTRY_BY_GROUND.get(ground, "")
    if host != team:
        return 0.0
    return v2.MODEL_CONFIG["host_advantage_group_power"] if round_name.startswith("Matchday") else v2.MODEL_CONFIG["host_advantage_knockout_power"]


def expected_goals(power_a: float, power_b: float) -> tuple[float, float]:
    diff = power_a - power_b
    base = V23_CONFIG["base_goal_rate"]
    scale = V23_CONFIG["power_goal_scale"]
    return (
        clamp(base * math.exp(diff / scale), 0.25, 3.2),
        clamp(base * math.exp(-diff / scale), 0.25, 3.2),
    )


def match_projection_v23(
    team_a: str,
    team_b: str,
    powers: dict[str, dict[str, Any]],
    ground: str = "",
    round_name: str = "",
    performance_noise_sd: float = 0.0,
) -> dict[str, Any]:
    power_a = powers[team_a]["v23_power_score"] + host_power(team_a, ground, round_name)
    power_b = powers[team_b]["v23_power_score"] + host_power(team_b, ground, round_name)
    if performance_noise_sd:
        power_a += random.gauss(0.0, performance_noise_sd)
        power_b += random.gauss(0.0, performance_noise_sd)
    lambda_a, lambda_b = expected_goals(power_a, power_b)
    p_a, p_draw, p_b = v2.scoreline_probabilities(lambda_a, lambda_b)
    return {
        "team1": team_a,
        "team2": team_b,
        "team1_power": power_a,
        "team2_power": power_b,
        "power_diff_team1": power_a - power_b,
        "team1_win_probability": p_a,
        "draw_probability": p_draw,
        "team2_win_probability": p_b,
        "team1_xg_internal": lambda_a,
        "team2_xg_internal": lambda_b,
    }


def is_draw_risk(projection: dict[str, Any]) -> bool:
    p1 = projection["team1_win_probability"]
    pd = projection["draw_probability"]
    p2 = projection["team2_win_probability"]
    return (
        pd >= V23_CONFIG["draw_decision_min"]
        and abs(p1 - p2) <= V23_CONFIG["draw_gap_max"]
        and max(p1, p2) <= V23_CONFIG["draw_favorite_max"]
    )


def is_firm_draw_lean(projection: dict[str, Any]) -> bool:
    p1 = projection["team1_win_probability"]
    p2 = projection["team2_win_probability"]
    return (
        is_draw_risk(projection)
        and abs(p1 - p2) <= V23_CONFIG["firm_draw_gap_max"]
        and max(p1, p2) <= V23_CONFIG["firm_draw_favorite_max"]
    )


def model_pick_90min(projection: dict[str, Any]) -> str:
    if is_draw_risk(projection):
        return "draw"
    return "team1_win" if projection["team1_win_probability"] >= projection["team2_win_probability"] else "team2_win"


def public_verdict_v23(projection: dict[str, Any]) -> tuple[str, str, str]:
    t1 = v2.display_team(projection["team1"])
    t2 = v2.display_team(projection["team2"])
    p1 = projection["team1_win_probability"]
    p2 = projection["team2_win_probability"]
    fav_team = t1 if p1 >= p2 else t2

    if is_firm_draw_lean(projection):
        return (
            "Draw lean",
            "Low-medium",
            "The draw is not the largest raw probability, but neither side separates enough to force a winner.",
        )
    if is_draw_risk(projection):
        return (
            "Draw risk / no strong edge",
            "Pass",
            "Draw probability is high and the side gap is too narrow for a clean public winner call.",
        )

    verdict, confidence, reason = v2.public_verdict(projection)
    if verdict == "No strong edge":
        return verdict, confidence, "No side separates enough after the v2.3 bias-control rebalance."
    if "avoid defeat" in verdict:
        return verdict, confidence, f"{fav_team} is preferred, but draw/upset risk keeps this below a clean win call."
    return verdict, confidence, reason


def build_group_predictions_v23(powers: dict[str, dict[str, Any]], fixtures: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for fixture in fixtures:
        if not fixture["round"].startswith("Matchday"):
            continue
        team_a = v2.normalize_team(fixture["team1"])
        team_b = v2.normalize_team(fixture["team2"])
        projection = match_projection_v23(team_a, team_b, powers, fixture["ground"], fixture["round"])
        verdict, confidence, reason = public_verdict_v23(projection)
        rows.append(
            {
                "fixture_id": fixture["fixture_id"],
                "date": fixture["date"],
                "time": fixture["time"],
                "group": fixture["group"].replace("Group ", ""),
                "ground": fixture["ground"],
                "team1": v2.display_team(team_a),
                "team2": v2.display_team(team_b),
                "public_verdict": verdict,
                "model_90min_pick": model_pick_90min(projection),
                "confidence": confidence,
                "model_reason": reason,
                "team1_win_probability_internal": round(projection["team1_win_probability"], 4),
                "draw_probability_internal": round(projection["draw_probability"], 4),
                "team2_win_probability_internal": round(projection["team2_win_probability"], 4),
                "draw_risk_flag": is_draw_risk(projection),
                "team1_internal_xg": round(projection["team1_xg_internal"], 3),
                "team2_internal_xg": round(projection["team2_xg_internal"], 3),
                "team1_power": round(projection["team1_power"], 3),
                "team2_power": round(projection["team2_power"], 3),
                "power_diff_team1": round(projection["power_diff_team1"], 3),
            }
        )
    return rows


def simulate_match(projection: dict[str, Any]) -> tuple[int, int]:
    return v2.sample_poisson(projection["team1_xg_internal"]), v2.sample_poisson(projection["team2_xg_internal"])


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


def third_sort(entry: dict[str, Any]) -> tuple[int, int, int, float]:
    stats = entry["stats"]
    return stats["points"], stats["goal_diff"], stats["goals_for"], random.random()


def penalty_winner(team_a: str, team_b: str, power_diff_team1: float) -> str:
    p_a = clamp(
        sigmoid(power_diff_team1 / V23_CONFIG["penalty_diff_scale"]),
        V23_CONFIG["penalty_min_probability"],
        V23_CONFIG["penalty_max_probability"],
    )
    return team_a if random.random() < p_a else team_b


def knockout_winner_v23(team_a: str, team_b: str, powers: dict[str, dict[str, Any]], ground: str, round_name: str) -> str:
    projection = match_projection_v23(
        team_a,
        team_b,
        powers,
        ground,
        round_name,
        performance_noise_sd=V23_CONFIG["knockout_performance_noise"],
    )
    goals_a, goals_b = simulate_match(projection)
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b

    et_lambda_a = clamp(projection["team1_xg_internal"] * V23_CONFIG["extra_time_goal_factor"], 0.05, 1.0)
    et_lambda_b = clamp(projection["team2_xg_internal"] * V23_CONFIG["extra_time_goal_factor"], 0.05, 1.0)
    et_a = v2.sample_poisson(et_lambda_a)
    et_b = v2.sample_poisson(et_lambda_b)
    if et_a > et_b:
        return team_a
    if et_b > et_a:
        return team_b
    return penalty_winner(team_a, team_b, projection["power_diff_team1"])


def run_sim_v23(powers: dict[str, dict[str, Any]], group_fixtures: list[dict[str, str]], knockout_fixtures: list[dict[str, str]]) -> dict[str, set[str]]:
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for team, row in powers.items():
        groups[row["group"]].append(team)
    table = {
        team: {"points": 0, "goals_for": 0, "goals_against": 0, "goal_diff": 0}
        for team in powers
    }
    for fixture in group_fixtures:
        team_a = v2.normalize_team(fixture["team1"])
        team_b = v2.normalize_team(fixture["team2"])
        projection = match_projection_v23(
            team_a,
            team_b,
            powers,
            fixture["ground"],
            fixture["round"],
            performance_noise_sd=V23_CONFIG["group_performance_noise"],
        )
        goals_a, goals_b = simulate_match(projection)
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
    group_rankings = {group: rank_group(sorted(teams), table) for group, teams in groups.items()}
    reached = {
        "qualified": set(),
        "group_first": set(),
        "group_second": set(),
        "group_third_qualified": set(),
        "round_of_16": set(),
        "quarter_final": set(),
        "semi_final": set(),
        "final": set(),
        "champion": set(),
    }
    thirds = []
    for group in v2.GROUP_ORDER:
        ranking = group_rankings[group]
        reached["group_first"].add(ranking[0])
        reached["group_second"].add(ranking[1])
        reached["qualified"].update(ranking[:2])
        thirds.append({"group": group, "team": ranking[2], "stats": table[ranking[2]]})
    thirds = sorted(thirds, key=third_sort, reverse=True)
    third_pool = {entry["group"]: entry for entry in thirds[:8]}
    reached["group_third_qualified"].update(entry["team"] for entry in thirds[:8])
    reached["qualified"].update(reached["group_third_qualified"])
    results: dict[str, str] = {}
    for fixture in knockout_fixtures:
        match_no = fixture["fixture_id"]
        round_name = fixture["round"]
        team_a = v2.resolve_slot(fixture["team1"], group_rankings, third_pool, results)
        team_b = v2.resolve_slot(fixture["team2"], group_rankings, third_pool, results)
        winner = knockout_winner_v23(team_a, team_b, powers, fixture["ground"], round_name)
        loser = team_b if winner == team_a else team_a
        results[f"W{match_no}"] = winner
        results[f"L{match_no}"] = loser
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


def run_tournament_v23(powers: dict[str, dict[str, Any]], fixtures: list[dict[str, str]]) -> list[dict[str, Any]]:
    random.seed(V23_CONFIG["seed"])
    group_fixtures = [fixture for fixture in fixtures if fixture["round"].startswith("Matchday")]
    knockout_fixtures = sorted(
        [fixture for fixture in fixtures if fixture["round"] in v2.ROUND_ORDER],
        key=lambda fixture: (v2.ROUND_ORDER[fixture["round"]], int(fixture["fixture_id"])),
    )
    counters = {
        key: Counter()
        for key in [
            "qualified",
            "group_first",
            "group_second",
            "group_third_qualified",
            "round_of_16",
            "quarter_final",
            "semi_final",
            "final",
            "champion",
        ]
    }
    sims = V23_CONFIG["simulations"]
    for _ in range(sims):
        reached = run_sim_v23(powers, group_fixtures, knockout_fixtures)
        for key, teams in reached.items():
            counters[key].update(teams)
    rows = []
    for team, row in powers.items():
        rows.append(
            {
                "team": row["display_team"],
                "group": row["group"],
                "v23_power_score": row["v23_power_score"],
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
    rows.sort(key=lambda r: (r["champion_pct"], r["final_pct"], r["semi_final_pct"]), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["title_rank"] = idx
    return rows


def compare_v22_v23(v23_odds: list[dict[str, Any]], powers: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    v22_odds = {row["team"]: row for row in v2.read_csv(PROCESSED / "model_v22_tournament_odds.csv")}
    v22_power = {row["display_team"]: row for row in v2.read_csv(PROCESSED / "model_v22_team_power.csv")}
    rows = []
    power_by_display = {row["display_team"]: row for row in powers.values()}
    for row in v23_odds:
        team = row["team"]
        old = v22_odds.get(team)
        old_power = v22_power.get(team)
        new_power = power_by_display.get(team)
        rows.append(
            {
                "team": team,
                "v22_title_rank": old["title_rank"] if old else "",
                "v23_title_rank": row["title_rank"],
                "v22_champion_pct": old["champion_pct"] if old else "",
                "v23_champion_pct": row["champion_pct"],
                "champion_pct_change": round(float(row["champion_pct"]) - float(old["champion_pct"]), 2) if old else "",
                "v22_power_score": old_power["v22_power_score"] if old_power else "",
                "v23_power_score": new_power["v23_power_score"] if new_power else "",
                "power_change": round(float(new_power["v23_power_score"]) - float(old_power["v22_power_score"]), 3) if old_power and new_power else "",
                "manager_score_v23": new_power["manager_score"] if new_power else "",
                "market_score_v23": new_power["market_score"] if new_power else "",
            }
        )
    rows.sort(key=lambda r: abs(float(r["champion_pct_change"] or 0.0)), reverse=True)
    return rows


def write_summary(v23_odds: list[dict[str, Any]], group_predictions: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> None:
    draw_picks = [row for row in group_predictions if row["model_90min_pick"] == "draw"]
    draw_leans = [row for row in group_predictions if row["public_verdict"] == "Draw lean"]
    lines = [
        "# World Cup Model v2.3",
        "",
        "V2.3 is a bias-control and realism upgrade on v2.2.",
        "",
        "## What changed",
        "",
        "- Manager quality weight reduced from 15% to 3%.",
        "- Unknown/manual-required managers are neutralized to 65 rather than treated as weak.",
        "- Squad/player impact is increased to 32%.",
        "- Availability/injury impact is increased to 7%.",
        "- A light 5% market sanity layer is added for current top-six public outright odds.",
        "- Knockout resolution now separates 90 minutes, extra time, and penalties.",
        "- Group and knockout simulations include small performance-noise terms to represent match-to-match variance.",
        "",
        "## v2.3 Weights",
        "",
        "| Layer | Weight |",
        "|---|---:|",
    ]
    for key, value in V23_CONFIG["weights"].items():
        lines.append(f"| {key} | {value:.0%} |")
    lines.extend(
        [
            "",
            "## Draw Output",
            "",
            f"- 90-minute model draw picks in group stage: {len(draw_picks)}.",
            f"- Public draw leans: {len(draw_leans)}.",
            f"- Draw-risk/no-edge calls: {sum(1 for row in group_predictions if row['public_verdict'] == 'Draw risk / no strong edge')}.",
            "",
            "## Top Title Odds",
            "",
            "| Rank | Team | Champion % | Final % | Semi % |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for row in v23_odds[:12]:
        lines.append(f"| {row['title_rank']} | {row['team']} | {row['champion_pct']}% | {row['final_pct']}% | {row['semi_final_pct']}% |")
    lines.extend(
        [
            "",
            "## Biggest Changes vs v2.2",
            "",
            "| Team | v2.2 % | v2.3 % | Change | Power change |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in comparison[:12]:
        lines.append(
            f"| {row['team']} | {row['v22_champion_pct']}% | {row['v23_champion_pct']}% | {row['champion_pct_change']} | {row['power_change']} |"
        )
    lines.extend(
        [
            "",
            "## Honest Caveat",
            "",
            "The market layer currently uses a light top-six public prior, not a full paid odds feed. Teams without a market input receive a neutral market score, so this is a sanity check rather than a bookmaker-cloning layer.",
        ]
    )
    (OUTPUTS / "world_cup_model_v23_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    v2.MODEL_CONFIG.update(
        {
            "seed": V23_CONFIG["seed"],
            "simulations": V23_CONFIG["simulations"],
            "base_goal_rate": V23_CONFIG["base_goal_rate"],
            "power_goal_scale": V23_CONFIG["power_goal_scale"],
        }
    )
    fixtures = v2.read_csv(PROCESSED / "worldcup_2026_matches.csv")
    powers = build_team_power_v23()
    team_rows = sorted(powers.values(), key=lambda row: row["v23_power_score"], reverse=True)
    for idx, row in enumerate(team_rows, start=1):
        row["v23_power_rank"] = idx

    group_predictions = build_group_predictions_v23(powers, fixtures)
    v23_odds = run_tournament_v23(powers, fixtures)
    comparison = compare_v22_v23(v23_odds, powers)

    write_csv(
        PROCESSED / "model_v23_group_match_predictions.csv",
        group_predictions,
        [
            "fixture_id",
            "date",
            "time",
            "group",
            "ground",
            "team1",
            "team2",
            "public_verdict",
            "model_90min_pick",
            "confidence",
            "model_reason",
            "team1_win_probability_internal",
            "draw_probability_internal",
            "team2_win_probability_internal",
            "draw_risk_flag",
            "team1_internal_xg",
            "team2_internal_xg",
            "team1_power",
            "team2_power",
            "power_diff_team1",
        ],
    )
    write_csv(
        PROCESSED / "model_v23_team_power.csv",
        team_rows,
        [
            "v23_power_rank",
            "team",
            "display_team",
            "group",
            "v1_total_rating",
            "v1_title_tier",
            "elo_score",
            "squad_score",
            "recent_form_score",
            "tactical_score",
            "availability_score",
            "market_score",
            "ceiling_score",
            "manager_score",
            "original_manager_score",
            "manager_status_v23",
            "v23_power_score",
            "manager_name",
            "preferred_style",
            "profile_source_status",
            "open_tactical_data_status",
            "elo_contribution",
            "squad_contribution",
            "recent_form_contribution",
            "tactical_contribution",
            "availability_contribution",
            "market_contribution",
            "ceiling_contribution",
            "manager_contribution",
        ],
    )
    write_csv(
        PROCESSED / "model_v23_tournament_odds.csv",
        v23_odds,
        [
            "title_rank",
            "team",
            "group",
            "v23_power_score",
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
    write_csv(
        PROCESSED / "model_v23_vs_v22_comparison.csv",
        comparison,
        [
            "team",
            "v22_title_rank",
            "v23_title_rank",
            "v22_champion_pct",
            "v23_champion_pct",
            "champion_pct_change",
            "v22_power_score",
            "v23_power_score",
            "power_change",
            "manager_score_v23",
            "market_score_v23",
        ],
    )
    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "world_cup_model_v23_config.json").write_text(json.dumps(V23_CONFIG, indent=2), encoding="utf-8")
    write_summary(v23_odds, group_predictions, comparison)
    print(
        json.dumps(
            {
                "teams": len(team_rows),
                "group_matches": len(group_predictions),
                "draw_90min_picks": sum(1 for row in group_predictions if row["model_90min_pick"] == "draw"),
                "top": v23_odds[:8],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
