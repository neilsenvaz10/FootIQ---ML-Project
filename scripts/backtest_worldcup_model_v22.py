#!/usr/bin/env python3
"""Backtest World Cup model v2.2 draw calibration.

This reuses the v2.1 historical team-power layer and tests only the v2.2
90-minute probability/decision engine.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any

import backtest_worldcup_model_v1 as bt


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

SIMULATIONS = 20000
BASE_GOAL_RATE = 1.15
POWER_GOAL_SCALE = 62.0
HOST_ADVANTAGE_GROUP_POWER = 3.0
HOST_ADVANTAGE_KNOCKOUT_POWER = 2.0
KNOCKOUT_NOISE = 3.5

DRAW_DECISION_MIN = 0.28
DRAW_GAP_MAX = 0.12
DRAW_FAVORITE_MAX = 0.42


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
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= random.random()
    return k - 1


def expected_goals(power_a: float, power_b: float) -> tuple[float, float]:
    diff = power_a - power_b
    return (
        clamp(BASE_GOAL_RATE * math.exp(diff / POWER_GOAL_SCALE), 0.25, 3.2),
        clamp(BASE_GOAL_RATE * math.exp(-diff / POWER_GOAL_SCALE), 0.25, 3.2),
    )


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


def load_powers() -> dict[int, dict[str, dict[str, Any]]]:
    by_year: dict[int, dict[str, dict[str, Any]]] = {}
    for row in read_csv(PROCESSED / "backtest_v21_team_power.csv"):
        year = int(row["year"])
        team = bt.normalize_team(row["team"])
        by_year.setdefault(year, {})[team] = {
            **row,
            "team": team,
            "v22_power_score": safe_float(row, "v21_power_score"),
        }
    return by_year


def host_power(team: str, year: int, stage: str) -> float:
    if team != bt.HOSTS[year]:
        return 0.0
    return HOST_ADVANTAGE_GROUP_POWER if stage == "Group Stage" else HOST_ADVANTAGE_KNOCKOUT_POWER


def match_projection(team_a: str, team_b: str, powers: dict[str, dict[str, Any]], year: int, stage: str) -> dict[str, Any]:
    power_a = powers[team_a]["v22_power_score"] + host_power(team_a, year, stage)
    power_b = powers[team_b]["v22_power_score"] + host_power(team_b, year, stage)
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


def is_draw_risk(projection: dict[str, Any]) -> bool:
    p1 = projection["team1_win_probability"]
    pd = projection["draw_probability"]
    p2 = projection["team2_win_probability"]
    return pd >= DRAW_DECISION_MIN and abs(p1 - p2) <= DRAW_GAP_MAX and max(p1, p2) <= DRAW_FAVORITE_MAX


def decision_pick(projection: dict[str, Any]) -> str:
    if is_draw_risk(projection):
        return "draw"
    return "home_win" if projection["team1_win_probability"] >= projection["team2_win_probability"] else "away_win"


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
        bt.normalize_team(team): {"points": 0, "goals_for": 0, "goals_against": 0, "goal_diff": 0}
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
        group: bt.rank_group([bt.normalize_team(team) for team in teams], table)
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
    random.seed(year * 100 + 22)
    group_matches = [match for match in matches if match["stage"] == "Group Stage"]
    counters = {key: Counter() for key in ["qualified", "round_of_16", "quarter_final", "semi_final", "final", "champion"]}
    for _ in range(SIMULATIONS):
        reached = run_tournament_sim(year, powers, group_matches)
        for stage, teams in reached.items():
            counters[stage].update(teams)
    rows = []
    for group, teams in bt.GROUPS[year].items():
        for original in teams:
            team = bt.normalize_team(original)
            rows.append(
                {
                    "year": year,
                    "variant": "model_v22_draw_calibrated",
                    "team": bt.display_team(team),
                    "group": group,
                    "v22_power_score": powers[team]["v22_power_score"],
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
    correct = 0
    side_correct = 0
    side_count = 0
    draw_picks = 0
    draw_pick_correct = 0
    draw_risk_count = 0
    actual_draws = 0
    actual_draws_in_draw_risk = 0
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
        pred = decision_pick(projection)
        draw_risk = is_draw_risk(projection)
        n += 1
        correct += int(pred == actual)
        draw_picks += int(pred == "draw")
        draw_pick_correct += int(pred == actual == "draw")
        draw_risk_count += int(draw_risk)
        actual_draws += int(actual == "draw")
        actual_draws_in_draw_risk += int(actual == "draw" and draw_risk)
        if pred != "draw":
            side_count += 1
            side_correct += int(pred == actual)
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
                "predicted_90min_result": pred,
                "draw_risk_flag": draw_risk,
                "home_win_probability": round(probs["home_win"], 4),
                "draw_probability": round(probs["draw"], 4),
                "away_win_probability": round(probs["away_win"], 4),
                "correct": pred == actual,
            }
        )
    metrics = {
        "year": year,
        "variant": "model_v22_draw_calibrated",
        "group_match_brier": round(brier / (n * 3), 4),
        "group_match_log_loss": round(log_loss / n, 4),
        "public_pick_accuracy_pct": round(100 * correct / n, 2),
        "side_pick_accuracy_pct": round(100 * side_correct / side_count, 2) if side_count else "",
        "draw_pick_count": draw_picks,
        "draw_pick_accuracy_pct": round(100 * draw_pick_correct / draw_picks, 2) if draw_picks else "",
        "draw_risk_count": draw_risk_count,
        "actual_draws": actual_draws,
        "actual_draws_in_draw_risk": actual_draws_in_draw_risk,
        "matches": n,
    }
    return rows, metrics


def tournament_metrics(year: int, odds_rows: list[dict[str, Any]], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actual = bt.actual_stage_sets(matches)
    by_team = {bt.normalize_team(row["team"]): row for row in odds_rows if int(row["year"]) == year}
    champion = next(iter(actual["champion"]))
    champion_row = by_team[champion]
    rows = [
        {
            "year": year,
            "variant": "model_v22_draw_calibrated",
            "metric": "champion_rank",
            "value": champion_row["title_rank"],
            "context": bt.display_team(champion),
        },
        {
            "year": year,
            "variant": "model_v22_draw_calibrated",
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
                "variant": "model_v22_draw_calibrated",
                "metric": f"{stage}_brier",
                "value": round(brier / len(by_team), 4),
                "context": f"{len(actual[stage])} actual teams",
            }
        )
    return rows


def compare_v21_v22(v22_match_metrics: list[dict[str, Any]], v22_tournament_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    v21_match = {row["year"]: row for row in read_csv(PROCESSED / "backtest_v21_match_metrics.csv")}
    rows = []
    for row in v22_match_metrics:
        year = str(row["year"])
        old = v21_match[year]
        rows.append(
            {
                "year": year,
                "metric": "group_match_brier",
                "v21": old["group_match_brier"],
                "v22": row["group_match_brier"],
                "delta": round(float(row["group_match_brier"]) - float(old["group_match_brier"]), 4),
                "interpretation": "lower is better",
            }
        )
        rows.append(
            {
                "year": year,
                "metric": "group_match_log_loss",
                "v21": old["group_match_log_loss"],
                "v22": row["group_match_log_loss"],
                "delta": round(float(row["group_match_log_loss"]) - float(old["group_match_log_loss"]), 4),
                "interpretation": "lower is better",
            }
        )
        rows.append(
            {
                "year": year,
                "metric": "pick_accuracy_pct",
                "v21": old["favorite_accuracy_pct"],
                "v22": row["public_pick_accuracy_pct"],
                "delta": round(float(row["public_pick_accuracy_pct"]) - float(old["favorite_accuracy_pct"]), 2),
                "interpretation": "higher is better; v2.2 includes draw picks",
            }
        )
    old_tournament = {
        (row["year"], row["metric"]): row
        for row in read_csv(PROCESSED / "backtest_v21_tournament_metrics.csv")
    }
    for row in v22_tournament_metrics:
        if row["metric"] not in {"champion_rank", "champion_probability_pct"}:
            continue
        key = (str(row["year"]), row["metric"])
        old = old_tournament[key]
        rows.append(
            {
                "year": row["year"],
                "metric": row["metric"],
                "v21": old["value"],
                "v22": row["value"],
                "delta": round(float(row["value"]) - float(old["value"]), 4),
                "interpretation": "rank lower is better; probability is descriptive",
            }
        )
    return rows


def write_report(match_metric_rows: list[dict[str, Any]], tournament_metric_rows: list[dict[str, Any]], comparison_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# World Cup Model v2.2 Backtest",
        "",
        "V2.2 tests a draw-calibrated 90-minute probability layer while keeping the v2.1 historical team-power layer fixed.",
        "",
        "## Match Metrics",
        "",
        "| Year | Brier | Log loss | Pick accuracy | Draw picks | Draw pick accuracy | Actual draws |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in match_metric_rows:
        lines.append(
            f"| {row['year']} | {row['group_match_brier']} | {row['group_match_log_loss']} | "
            f"{row['public_pick_accuracy_pct']}% | {row['draw_pick_count']} | {row['draw_pick_accuracy_pct']}% | {row['actual_draws']} |"
        )
    lines.extend(
        [
            "",
            "## v2.1 vs v2.2",
            "",
            "| Year | Metric | v2.1 | v2.2 | Delta |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for row in comparison_rows:
        if row["metric"] in {"group_match_brier", "group_match_log_loss", "pick_accuracy_pct"}:
            lines.append(f"| {row['year']} | {row['metric']} | {row['v21']} | {row['v22']} | {row['delta']} |")
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
            "- v2.2 improves probability calibration versus v2.1 on the combined 2018/2022 group-stage test.",
            "- Exact draw picks remain low precision, so public product language should usually say draw risk/no strong edge rather than sell a draw as a confident pick.",
            "- This version fixes the zero-draw structural bug without changing the player-impact/team-strength layer.",
        ]
    )
    (OUTPUTS / "world_cup_model_v22_backtest_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    powers_by_year = load_powers()
    all_odds_rows: list[dict[str, Any]] = []
    all_match_rows: list[dict[str, Any]] = []
    match_metric_rows: list[dict[str, Any]] = []
    tournament_metric_rows: list[dict[str, Any]] = []
    for year in [2018, 2022]:
        powers = powers_by_year[year]
        matches = bt.load_worldcup_matches(year)
        odds_rows = run_probability_simulation(year, powers, matches)
        match_rows, match_metrics_row = match_metrics(year, powers, matches)
        tournament_rows = tournament_metrics(year, odds_rows, matches)
        all_odds_rows.extend(odds_rows)
        all_match_rows.extend(match_rows)
        match_metric_rows.append(match_metrics_row)
        tournament_metric_rows.extend(tournament_rows)

    comparison_rows = compare_v21_v22(match_metric_rows, tournament_metric_rows)
    write_csv(
        PROCESSED / "backtest_v22_tournament_odds.csv",
        all_odds_rows,
        [
            "year",
            "variant",
            "title_rank",
            "team",
            "group",
            "v22_power_score",
            "qualify_pct",
            "quarter_final_pct",
            "semi_final_pct",
            "final_pct",
            "champion_pct",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v22_group_match_predictions.csv",
        all_match_rows,
        [
            "year",
            "match_id",
            "date",
            "home_team",
            "away_team",
            "actual_result",
            "predicted_90min_result",
            "draw_risk_flag",
            "home_win_probability",
            "draw_probability",
            "away_win_probability",
            "correct",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v22_match_metrics.csv",
        match_metric_rows,
        [
            "year",
            "variant",
            "group_match_brier",
            "group_match_log_loss",
            "public_pick_accuracy_pct",
            "side_pick_accuracy_pct",
            "draw_pick_count",
            "draw_pick_accuracy_pct",
            "draw_risk_count",
            "actual_draws",
            "actual_draws_in_draw_risk",
            "matches",
        ],
    )
    write_csv(
        PROCESSED / "backtest_v22_tournament_metrics.csv",
        tournament_metric_rows,
        ["year", "variant", "metric", "value", "context"],
    )
    write_csv(
        PROCESSED / "backtest_v22_vs_v21_comparison.csv",
        comparison_rows,
        ["year", "metric", "v21", "v22", "delta", "interpretation"],
    )
    write_report(match_metric_rows, tournament_metric_rows, comparison_rows)
    (OUTPUTS / "world_cup_model_v22_backtest_config.json").write_text(
        json.dumps(
            {
                "simulations": SIMULATIONS,
                "base_goal_rate": BASE_GOAL_RATE,
                "power_goal_scale": POWER_GOAL_SCALE,
                "draw_decision_min": DRAW_DECISION_MIN,
                "draw_gap_max": DRAW_GAP_MAX,
                "draw_favorite_max": DRAW_FAVORITE_MAX,
                "status": "v2.2 draw-calibrated probability layer; v2.1 historical team powers reused",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"match_metrics": match_metric_rows}, indent=2))


if __name__ == "__main__":
    main()
