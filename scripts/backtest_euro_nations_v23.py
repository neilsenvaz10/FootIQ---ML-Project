#!/usr/bin/env python3
"""Euro 2024 and UEFA Nations League v2.3-lite tests.

This uses the v2.3 model shape without leaking 2026 player/market/manager data:
- pre-event Elo and recent form only
- squad quality is an Elo/tier proxy, not 2026 player impact
- manager is neutral 65 for every team
- market is neutral 50 for every team
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import backtest_worldcup_model_v1 as bt
import build_worldcup_model_v2 as v2
import build_worldcup_model_v23 as v23


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "international_results"
OUTPUTS = ROOT / "outputs"

SIMULATIONS = 20000
BASE_GOAL_RATE = v23.V23_CONFIG["base_goal_rate"]
POWER_GOAL_SCALE = v23.V23_CONFIG["power_goal_scale"]
GROUP_PERFORMANCE_NOISE = v23.V23_CONFIG["group_performance_noise"]
KNOCKOUT_PERFORMANCE_NOISE = v23.V23_CONFIG["knockout_performance_noise"]
EXTRA_TIME_GOAL_FACTOR = v23.V23_CONFIG["extra_time_goal_factor"]
PENALTY_DIFF_SCALE = v23.V23_CONFIG["penalty_diff_scale"]
PENALTY_MIN_PROBABILITY = v23.V23_CONFIG["penalty_min_probability"]
PENALTY_MAX_PROBABILITY = v23.V23_CONFIG["penalty_max_probability"]

DRAW_DECISION_MIN = v23.V23_CONFIG["draw_decision_min"]
DRAW_GAP_MAX = v23.V23_CONFIG["draw_gap_max"]
DRAW_FAVORITE_MAX = v23.V23_CONFIG["draw_favorite_max"]

WEIGHTS = v23.V23_CONFIG["weights"]
NEUTRAL_MANAGER_SCORE = 65.0
NEUTRAL_MARKET_SCORE = 50.0
NEUTRAL_AVAILABILITY_SCORE = 100.0

EURO_2024_GROUPS = {
    "A": ["Germany", "Scotland", "Hungary", "Switzerland"],
    "B": ["Spain", "Croatia", "Italy", "Albania"],
    "C": ["Slovenia", "Denmark", "Serbia", "England"],
    "D": ["Poland", "Netherlands", "Austria", "France"],
    "E": ["Belgium", "Slovakia", "Romania", "Ukraine"],
    "F": ["Turkey", "Georgia", "Portugal", "Czech Republic"],
}

EURO_R16_BRACKET = [
    ("E37", "2A", "2B"),
    ("E38", "1A", "2C"),
    ("E39", "1C", "3_1C"),
    ("E40", "1B", "3_1B"),
    ("E41", "2D", "2E"),
    ("E42", "1F", "3_1F"),
    ("E43", "1E", "3_1E"),
    ("E44", "1D", "2F"),
    ("E45", "WE40", "WE38"),
    ("E46", "WE42", "WE41"),
    ("E47", "WE39", "WE37"),
    ("E48", "WE43", "WE44"),
    ("E49", "WE45", "WE46"),
    ("E50", "WE48", "WE47"),
    ("E51", "WE49", "WE50"),
]

EURO_STAGE_BY_MATCH = {
    **{f"E{i}": "Round of 16" for i in range(37, 45)},
    **{f"E{i}": "Quarter-final" for i in range(45, 49)},
    "E49": "Semi-final",
    "E50": "Semi-final",
    "E51": "Final",
}

# UEFA Euro 24-team best-third matrix. Values are opponent groups for:
# 1B, 1C, 1E, 1F.
EURO_THIRD_MATRIX = {
    "ABCD": ("A", "D", "B", "C"),
    "ABCE": ("A", "E", "B", "C"),
    "ABCF": ("A", "F", "B", "C"),
    "ABDE": ("D", "E", "A", "B"),
    "ABDF": ("D", "F", "A", "B"),
    "ABEF": ("E", "F", "B", "A"),
    "ACDE": ("E", "D", "C", "A"),
    "ACDF": ("F", "D", "C", "A"),
    "ACEF": ("E", "F", "C", "A"),
    "ADEF": ("E", "F", "D", "A"),
    "BCDE": ("E", "D", "B", "C"),
    "BCDF": ("F", "D", "C", "B"),
    "BCEF": ("F", "E", "C", "B"),
    "BDEF": ("F", "E", "D", "B"),
    "CDEF": ("F", "E", "D", "C"),
}

UNL_2025_TEAMS = ["Germany", "Portugal", "Spain", "France"]
UNL_2025_BRACKET = [
    ("N1", "Germany", "Portugal"),
    ("N2", "Spain", "France"),
    ("N3", "WN1", "WN2"),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def expected_goals(power_a: float, power_b: float) -> tuple[float, float]:
    diff = power_a - power_b
    return (
        clamp(BASE_GOAL_RATE * math.exp(diff / POWER_GOAL_SCALE), 0.25, 3.2),
        clamp(BASE_GOAL_RATE * math.exp(-diff / POWER_GOAL_SCALE), 0.25, 3.2),
    )


def proxy_squad_score(elo_score: float, tier: str) -> float:
    base = 38.0 + elo_score * 0.47
    if "Tier 1" in tier:
        base += 6.0
    elif "Tier 2" in tier:
        base += 2.0
    elif "Tier 4" in tier:
        base -= 5.0
    squad = clamp(base, 35.0, 86.0)
    xi = clamp(squad + 1.0, 35.0, 88.0)
    bench = clamp(squad - 4.0, 30.0, 82.0)
    return squad * 0.45 + xi * 0.35 + bench * 0.20


def build_team_powers(teams: list[str], start_date: str, tactical_year: int) -> dict[str, dict[str, Any]]:
    elo, ranks, history = bt.latest_elo_as_of(start_date)
    tactical = bt.build_tactical_profiles_as_of(tactical_year)
    tiers = {}
    for team in teams:
        if team not in elo:
            raise RuntimeError(f"Missing Elo for {team} before {start_date}")
        _, tier = bt.ceiling_adjustment(elo[team], ranks[team])
        tiers[team] = tier
    # Use global pre-event percentiles, not within-field percentiles. Within-field
    # scoring is acceptable for a 48-team World Cup, but it badly distorts a
    # four-team finals test by making the fourth-best elite team look weak.
    elo_scores = v2.percentile_scores(elo)
    raw_recent = {team: bt.recent_form_adjustment(rows) for team, rows in history.items()}
    recent_scores = v2.percentile_scores(raw_recent)
    powers = {}
    for team in teams:
        tactical_adjustment = float(tactical.get(team, {}).get("tactical_adjustment", 0.0))
        tactical_score = v2.score_from_adjustment(tactical_adjustment, 1.35)
        squad_score = proxy_squad_score(elo_scores[team], tiers[team])
        ceiling_score = v2.ceiling_score_from_tier(tiers[team])
        power = (
            elo_scores[team] * WEIGHTS["elo_score"]
            + squad_score * WEIGHTS["squad_score"]
            + recent_scores[team] * WEIGHTS["recent_form_score"]
            + tactical_score * WEIGHTS["tactical_score"]
            + NEUTRAL_AVAILABILITY_SCORE * WEIGHTS["availability_score"]
            + NEUTRAL_MARKET_SCORE * WEIGHTS["market_score"]
            + ceiling_score * WEIGHTS["ceiling_score"]
            + NEUTRAL_MANAGER_SCORE * WEIGHTS["manager_score"]
        )
        powers[team] = {
            "team": team,
            "elo": round(elo[team], 3),
            "elo_rank": ranks[team],
            "elo_score": round(elo_scores[team], 3),
            "squad_score": round(squad_score, 3),
            "recent_form_score": round(recent_scores[team], 3),
            "tactical_score": round(tactical_score, 3),
            "availability_score": NEUTRAL_AVAILABILITY_SCORE,
            "market_score": NEUTRAL_MARKET_SCORE,
            "ceiling_score": round(ceiling_score, 3),
            "manager_score": NEUTRAL_MANAGER_SCORE,
            "v23_lite_power_score": round(power, 3),
            "contender_tier": tiers[team],
            "tactical_data_status": tactical.get(team, {}).get("tactical_data_status", "no_prior_tactical_data"),
        }
    return powers


def host_power(team: str, host: str, stage: str) -> float:
    if team != host:
        return 0.0
    return 3.0 if stage == "Group Stage" else 2.0


def match_projection(
    team_a: str,
    team_b: str,
    powers: dict[str, dict[str, Any]],
    host: str,
    stage: str,
    performance_noise_sd: float = 0.0,
) -> dict[str, Any]:
    power_a = powers[team_a]["v23_lite_power_score"] + host_power(team_a, host, stage)
    power_b = powers[team_b]["v23_lite_power_score"] + host_power(team_b, host, stage)
    if performance_noise_sd:
        power_a += random.gauss(0.0, performance_noise_sd)
        power_b += random.gauss(0.0, performance_noise_sd)
    lambda_a, lambda_b = expected_goals(power_a, power_b)
    p_a, p_draw, p_b = v2.scoreline_probabilities(lambda_a, lambda_b)
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


def is_draw_risk(projection: dict[str, Any]) -> bool:
    p1 = projection["team1_win_probability"]
    pd = projection["draw_probability"]
    p2 = projection["team2_win_probability"]
    return pd >= DRAW_DECISION_MIN and abs(p1 - p2) <= DRAW_GAP_MAX and max(p1, p2) <= DRAW_FAVORITE_MAX


def decision_pick(projection: dict[str, Any], team_a_result: str, team_b_result: str) -> str:
    if is_draw_risk(projection):
        return "draw"
    return team_a_result if projection["team1_win_probability"] >= projection["team2_win_probability"] else team_b_result


def simulate_match(projection: dict[str, Any]) -> tuple[int, int]:
    return v2.sample_poisson(projection["team1_xg_internal"]), v2.sample_poisson(projection["team2_xg_internal"])


def penalty_winner(team_a: str, team_b: str, power_diff_team1: float) -> str:
    p_a = clamp(sigmoid(power_diff_team1 / PENALTY_DIFF_SCALE), PENALTY_MIN_PROBABILITY, PENALTY_MAX_PROBABILITY)
    return team_a if random.random() < p_a else team_b


def knockout_winner(team_a: str, team_b: str, powers: dict[str, dict[str, Any]], host: str, stage: str) -> str:
    projection = match_projection(team_a, team_b, powers, host, stage, performance_noise_sd=KNOCKOUT_PERFORMANCE_NOISE)
    goals_a, goals_b = simulate_match(projection)
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    et_a = v2.sample_poisson(clamp(projection["team1_xg_internal"] * EXTRA_TIME_GOAL_FACTOR, 0.05, 1.0))
    et_b = v2.sample_poisson(clamp(projection["team2_xg_internal"] * EXTRA_TIME_GOAL_FACTOR, 0.05, 1.0))
    if et_a > et_b:
        return team_a
    if et_b > et_a:
        return team_b
    return penalty_winner(team_a, team_b, projection["power_diff_team1"])


def load_shootout_winners() -> dict[tuple[str, str, str], str]:
    out = {}
    for row in read_csv(RAW / "shootouts.csv"):
        home = bt.normalize_team(row["home_team"])
        away = bt.normalize_team(row["away_team"])
        out[(row["date"], home, away)] = bt.normalize_team(row["winner"])
        out[(row["date"], away, home)] = bt.normalize_team(row["winner"])
    return out


def load_euro_2024_matches() -> list[dict[str, Any]]:
    rows = [
        row
        for row in read_csv(PROCESSED / "international_matches.csv")
        if row["tournament"] == "UEFA Euro" and row["date"].startswith("2024-")
    ]
    rows.sort(key=lambda row: (row["date"], int(row["match_id"])))
    shootouts = load_shootout_winners()
    team_to_group = {
        team: group
        for group, teams in EURO_2024_GROUPS.items()
        for team in teams
    }
    matches = []
    for idx, row in enumerate(rows, start=1):
        home = bt.normalize_team(row["home_team"])
        away = bt.normalize_team(row["away_team"])
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        if idx <= 36:
            stage = "Group Stage"
        elif idx <= 44:
            stage = "Round of 16"
        elif idx <= 48:
            stage = "Quarter-final"
        elif idx <= 50:
            stage = "Semi-final"
        else:
            stage = "Final"
        winner = ""
        if stage != "Group Stage":
            if home_score > away_score:
                winner = home
            elif away_score > home_score:
                winner = away
            else:
                winner = shootouts.get((row["date"], home, away), "")
        matches.append(
            {
                "tournament": "Euro 2024",
                "match_no": idx,
                "date": row["date"],
                "stage": stage,
                "group": team_to_group.get(home, "") if stage == "Group Stage" else "",
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "winner": winner,
            }
        )
    return matches


def load_unl_2025_matches() -> list[dict[str, Any]]:
    rows = [
        row
        for row in read_csv(PROCESSED / "international_matches.csv")
        if row["tournament"] == "UEFA Nations League" and "2025-06-01" <= row["date"] <= "2025-06-10"
    ]
    rows.sort(key=lambda row: (row["date"], int(row["match_id"])))
    shootouts = load_shootout_winners()
    matches = []
    for idx, row in enumerate(rows, start=1):
        home = bt.normalize_team(row["home_team"])
        away = bt.normalize_team(row["away_team"])
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        stage = "Semi-final" if idx <= 2 else ("Third place" if idx == 3 else "Final")
        winner = ""
        if home_score > away_score:
            winner = home
        elif away_score > home_score:
            winner = away
        else:
            winner = shootouts.get((row["date"], home, away), "")
        matches.append(
            {
                "tournament": "UEFA Nations League 2025 Finals",
                "match_no": idx,
                "date": row["date"],
                "stage": stage,
                "group": "",
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "winner": winner,
            }
        )
    return matches


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


def third_assignment(thirds: list[dict[str, Any]]) -> dict[str, str]:
    best = sorted(thirds, key=third_sort, reverse=True)[:4]
    key = "".join(sorted(entry["group"] for entry in best))
    if key not in EURO_THIRD_MATRIX:
        raise RuntimeError(f"Unsupported best-third combo: {key}")
    one_b, one_c, one_e, one_f = EURO_THIRD_MATRIX[key]
    by_group = {entry["group"]: entry["team"] for entry in best}
    return {
        "3_1B": by_group[one_b],
        "3_1C": by_group[one_c],
        "3_1E": by_group[one_e],
        "3_1F": by_group[one_f],
    }


def resolve_euro_slot(slot: str, rankings: dict[str, list[str]], thirds: dict[str, str], winners: dict[str, str]) -> str:
    if slot.startswith("W"):
        return winners[slot[1:]]
    if slot.startswith("3_"):
        return thirds[slot]
    rank = int(slot[0]) - 1
    group = slot[1]
    return rankings[group][rank]


def run_euro_sim(powers: dict[str, dict[str, Any]], group_matches: list[dict[str, Any]]) -> dict[str, set[str]]:
    table = {
        team: {"points": 0, "goals_for": 0, "goals_against": 0, "goal_diff": 0}
        for teams in EURO_2024_GROUPS.values()
        for team in teams
    }
    for match in group_matches:
        home = match["home_team"]
        away = match["away_team"]
        projection = match_projection(home, away, powers, "Germany", "Group Stage", GROUP_PERFORMANCE_NOISE)
        hs, aw = simulate_match(projection)
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
    rankings = {group: rank_group(teams, table) for group, teams in EURO_2024_GROUPS.items()}
    thirds = [{"group": group, "team": rankings[group][2], "stats": table[rankings[group][2]]} for group in EURO_2024_GROUPS]
    third_slots = third_assignment(thirds)
    reached = {key: set() for key in ["qualified", "quarter_final", "semi_final", "final", "champion"]}
    for ranking in rankings.values():
        reached["qualified"].update(ranking[:2])
    reached["qualified"].update(third_slots.values())

    winners: dict[str, str] = {}
    for match_id, slot_a, slot_b in EURO_R16_BRACKET:
        team_a = resolve_euro_slot(slot_a, rankings, third_slots, winners)
        team_b = resolve_euro_slot(slot_b, rankings, third_slots, winners)
        stage = EURO_STAGE_BY_MATCH[match_id]
        winner = knockout_winner(team_a, team_b, powers, "Germany", stage)
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


def run_unl_sim(powers: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    reached = {key: set() for key in ["semi_final", "final", "champion"]}
    reached["semi_final"].update(UNL_2025_TEAMS)
    winners: dict[str, str] = {}
    for match_id, slot_a, slot_b in UNL_2025_BRACKET:
        team_a = winners[slot_a[1:]] if slot_a.startswith("W") else slot_a
        team_b = winners[slot_b[1:]] if slot_b.startswith("W") else slot_b
        stage = "Final" if match_id == "N3" else "Semi-final"
        winner = knockout_winner(team_a, team_b, powers, "Germany", stage)
        winners[match_id] = winner
        if stage == "Semi-final":
            reached["final"].add(winner)
        else:
            reached["champion"].add(winner)
    return reached


def tournament_odds_euro(powers: dict[str, dict[str, Any]], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    random.seed(202423)
    group_matches = [match for match in matches if match["stage"] == "Group Stage"]
    counters = {key: Counter() for key in ["qualified", "quarter_final", "semi_final", "final", "champion"]}
    for _ in range(SIMULATIONS):
        reached = run_euro_sim(powers, group_matches)
        for stage, teams in reached.items():
            counters[stage].update(teams)
    rows = []
    for group, teams in EURO_2024_GROUPS.items():
        for team in teams:
            rows.append(
                {
                    "tournament": "Euro 2024",
                    "team": team,
                    "group": group,
                    "power_score": powers[team]["v23_lite_power_score"],
                    "qualify_pct": round(100 * counters["qualified"][team] / SIMULATIONS, 2),
                    "quarter_final_pct": round(100 * counters["quarter_final"][team] / SIMULATIONS, 2),
                    "semi_final_pct": round(100 * counters["semi_final"][team] / SIMULATIONS, 2),
                    "final_pct": round(100 * counters["final"][team] / SIMULATIONS, 2),
                    "champion_pct": round(100 * counters["champion"][team] / SIMULATIONS, 2),
                }
            )
    rows.sort(key=lambda row: (row["champion_pct"], row["final_pct"], row["semi_final_pct"]), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["title_rank"] = idx
    return rows


def tournament_odds_unl(powers: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    random.seed(202523)
    counters = {key: Counter() for key in ["semi_final", "final", "champion"]}
    for _ in range(SIMULATIONS):
        reached = run_unl_sim(powers)
        for stage, teams in reached.items():
            counters[stage].update(teams)
    rows = []
    for team in UNL_2025_TEAMS:
        rows.append(
            {
                "tournament": "UEFA Nations League 2025 Finals",
                "team": team,
                "group": "",
                "power_score": powers[team]["v23_lite_power_score"],
                "qualify_pct": 100.0,
                "quarter_final_pct": "",
                "semi_final_pct": 100.0,
                "final_pct": round(100 * counters["final"][team] / SIMULATIONS, 2),
                "champion_pct": round(100 * counters["champion"][team] / SIMULATIONS, 2),
            }
        )
    rows.sort(key=lambda row: (row["champion_pct"], row["final_pct"]), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["title_rank"] = idx
    return rows


def match_metrics(tournament: str, matches: list[dict[str, Any]], powers: dict[str, dict[str, Any]], host: str, stages: set[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    brier = 0.0
    log_loss = 0.0
    correct = 0
    draw_picks = 0
    draw_pick_correct = 0
    draw_risk_count = 0
    actual_draws = 0
    actual_draws_in_draw_risk = 0
    n = 0
    for match in matches:
        if match["stage"] not in stages:
            continue
        projection = match_projection(match["home_team"], match["away_team"], powers, host, match["stage"])
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
        pred = decision_pick(projection, "home_win", "away_win")
        draw_risk = is_draw_risk(projection)
        n += 1
        correct += int(pred == actual)
        draw_picks += int(pred == "draw")
        draw_pick_correct += int(pred == actual == "draw")
        draw_risk_count += int(draw_risk)
        actual_draws += int(actual == "draw")
        actual_draws_in_draw_risk += int(actual == "draw" and draw_risk)
        for outcome, prob in probs.items():
            y = 1.0 if outcome == actual else 0.0
            brier += (prob - y) ** 2
        log_loss += -math.log(max(probs[actual], 1e-9))
        rows.append(
            {
                "tournament": tournament,
                "date": match["date"],
                "stage": match["stage"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "actual_result_90min": actual,
                "predicted_90min_result": pred,
                "draw_risk_flag": draw_risk,
                "home_win_probability": round(probs["home_win"], 4),
                "draw_probability": round(probs["draw"], 4),
                "away_win_probability": round(probs["away_win"], 4),
                "correct_90min": pred == actual,
            }
        )
    metrics = {
        "tournament": tournament,
        "stage_scope": ", ".join(sorted(stages)),
        "brier": round(brier / (n * 3), 4) if n else "",
        "log_loss": round(log_loss / n, 4) if n else "",
        "pick_accuracy_pct": round(100 * correct / n, 2) if n else "",
        "draw_pick_count": draw_picks,
        "draw_pick_accuracy_pct": round(100 * draw_pick_correct / draw_picks, 2) if draw_picks else "",
        "draw_risk_count": draw_risk_count,
        "actual_draws": actual_draws,
        "actual_draws_in_draw_risk": actual_draws_in_draw_risk,
        "matches": n,
    }
    return rows, metrics


def actual_champion(matches: list[dict[str, Any]]) -> str:
    final = next(match for match in matches if match["stage"] == "Final")
    return final["winner"]


def write_report(odds: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> None:
    by_tournament: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in odds:
        by_tournament[row["tournament"]].append(row)
    metric_by_tournament = {row["tournament"]: row for row in metrics}
    lines = [
        "# Euro 2024 + UEFA Nations League v2.3-lite Test",
        "",
        "This test uses the v2.3 model shape without 2026 player, manager, or market leakage.",
        "",
        "## Method",
        "",
        "- Team strength is built from pre-event Elo, recent form, tactical prior where available, proxy squad score, neutral manager score, neutral market score, and neutral availability.",
        "- Euro 2024 uses the official 24-team group format, best-third qualification matrix, and knockout bracket.",
        "- UEFA Nations League uses the four-team 2025 finals bracket: Germany vs Portugal and Spain vs France, then final.",
        "- Exact score is not a product prediction; score sampling is used internally for tournament simulation.",
        "",
    ]
    for tournament, rows in by_tournament.items():
        metric = metric_by_tournament[tournament]
        lines.extend(
            [
                f"## {tournament}",
                "",
                f"- 90-minute match Brier: {metric['brier']}",
                f"- 90-minute log loss: {metric['log_loss']}",
                f"- 90-minute pick accuracy: {metric['pick_accuracy_pct']}%",
                f"- Draw picks: {metric['draw_pick_count']} / actual draws: {metric['actual_draws']}",
                "",
                "| Rank | Team | Champion % | Final % | Power |",
                "|---:|---|---:|---:|---:|",
            ]
        )
        for row in rows[:8]:
            lines.append(
                f"| {row['title_rank']} | {row['team']} | {row['champion_pct']}% | {row['final_pct']}% | {row['power_score']} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Honest Read",
            "",
            "- This is a better architecture test than the 2018/2022 World Cup backtest because Euro 2024 and Nations League are closer to the current player era.",
            "- It is still v2.3-lite, not full v2.3, because historical verified player-impact and market feeds are not attached yet.",
            "- The output should be read as a contender-pool and calibration test, not proof the model can nail exact champions.",
        ]
    )
    (OUTPUTS / "euro_nations_model_v23_test_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    euro_matches = load_euro_2024_matches()
    euro_teams = [team for teams in EURO_2024_GROUPS.values() for team in teams]
    euro_powers = build_team_powers(euro_teams, "2024-06-14", 2024)
    euro_odds = tournament_odds_euro(euro_powers, euro_matches)
    euro_match_rows, euro_metrics = match_metrics("Euro 2024", euro_matches, euro_powers, "Germany", {"Group Stage"})
    euro_champion = actual_champion(euro_matches)
    euro_metrics["actual_champion"] = euro_champion
    euro_metrics["actual_champion_rank"] = next(row["title_rank"] for row in euro_odds if row["team"] == euro_champion)
    euro_metrics["actual_champion_probability_pct"] = next(row["champion_pct"] for row in euro_odds if row["team"] == euro_champion)

    unl_matches = load_unl_2025_matches()
    unl_powers = build_team_powers(UNL_2025_TEAMS, "2025-06-04", 2025)
    unl_odds = tournament_odds_unl(unl_powers)
    unl_match_rows, unl_metrics = match_metrics(
        "UEFA Nations League 2025 Finals",
        unl_matches,
        unl_powers,
        "Germany",
        {"Semi-final", "Final"},
    )
    unl_champion = actual_champion(unl_matches)
    unl_metrics["actual_champion"] = unl_champion
    unl_metrics["actual_champion_rank"] = next(row["title_rank"] for row in unl_odds if row["team"] == unl_champion)
    unl_metrics["actual_champion_probability_pct"] = next(row["champion_pct"] for row in unl_odds if row["team"] == unl_champion)

    all_odds = euro_odds + unl_odds
    all_matches = euro_match_rows + unl_match_rows
    all_metrics = [euro_metrics, unl_metrics]
    all_power_rows = [
        {"tournament": "Euro 2024", **row} for row in euro_powers.values()
    ] + [
        {"tournament": "UEFA Nations League 2025 Finals", **row} for row in unl_powers.values()
    ]

    write_csv(
        PROCESSED / "euro_nations_v23_tournament_odds.csv",
        all_odds,
        [
            "tournament",
            "title_rank",
            "team",
            "group",
            "power_score",
            "qualify_pct",
            "quarter_final_pct",
            "semi_final_pct",
            "final_pct",
            "champion_pct",
        ],
    )
    write_csv(
        PROCESSED / "euro_nations_v23_match_predictions.csv",
        all_matches,
        [
            "tournament",
            "date",
            "stage",
            "home_team",
            "away_team",
            "actual_result_90min",
            "predicted_90min_result",
            "draw_risk_flag",
            "home_win_probability",
            "draw_probability",
            "away_win_probability",
            "correct_90min",
        ],
    )
    write_csv(
        PROCESSED / "euro_nations_v23_metrics.csv",
        all_metrics,
        [
            "tournament",
            "stage_scope",
            "brier",
            "log_loss",
            "pick_accuracy_pct",
            "draw_pick_count",
            "draw_pick_accuracy_pct",
            "draw_risk_count",
            "actual_draws",
            "actual_draws_in_draw_risk",
            "matches",
            "actual_champion",
            "actual_champion_rank",
            "actual_champion_probability_pct",
        ],
    )
    write_csv(
        PROCESSED / "euro_nations_v23_team_power.csv",
        all_power_rows,
        [
            "tournament",
            "team",
            "elo",
            "elo_rank",
            "elo_score",
            "squad_score",
            "recent_form_score",
            "tactical_score",
            "availability_score",
            "market_score",
            "ceiling_score",
            "manager_score",
            "v23_lite_power_score",
            "contender_tier",
            "tactical_data_status",
        ],
    )
    OUTPUTS.mkdir(exist_ok=True)
    write_report(all_odds, all_metrics)
    (OUTPUTS / "euro_nations_model_v23_test_config.json").write_text(
        json.dumps(
            {
                "simulations": SIMULATIONS,
                "weights": WEIGHTS,
                "manager_score": NEUTRAL_MANAGER_SCORE,
                "market_score": NEUTRAL_MARKET_SCORE,
                "availability_score": NEUTRAL_AVAILABILITY_SCORE,
                "status": "v2.3-lite; no 2026 player/manager/market leakage",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"metrics": all_metrics, "top": {row["tournament"]: [] for row in all_odds}}, indent=2))
    for tournament in sorted({row["tournament"] for row in all_odds}):
        top = [row for row in all_odds if row["tournament"] == tournament][:5]
        print(tournament, top)


if __name__ == "__main__":
    main()
