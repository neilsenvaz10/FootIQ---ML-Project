#!/usr/bin/env python3
"""Portugal group-winner scenario for World Cup model v2.3.

This keeps the main v2.3 model untouched and runs a conditional Monte Carlo:
only simulations where Portugal finishes first in Group K are accepted, then
the official bracket slots are resolved from that state.
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import build_worldcup_model_v2 as v2
import build_worldcup_model_v23 as v23


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

CONFIG = {
    "version": "v2.3-portugal-group-winner-scenario",
    "base_model": "v2.3",
    "seed": 20260609,
    "accepted_simulations": 50000,
    "condition": "Portugal finishes first in Group K",
    "note": "Conditional scenario only; not a new production model.",
}

PORTUGAL = "Portugal"


class ThirdPlaceAssignmentError(RuntimeError):
    """Raised when the available third-place teams cannot fill listed slots."""


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float) -> float:
    return round(100.0 * value, 2)


def third_entry_key(entry: dict[str, Any]) -> tuple[int, int, int, str]:
    stats = entry["stats"]
    return (
        int(stats["points"]),
        int(stats["goal_diff"]),
        int(stats["goals_for"]),
        str(entry["team"]),
    )


def build_third_assignments(
    knockout_fixtures: list[dict[str, str]],
    third_pool: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    third_slots = []
    for fixture in knockout_fixtures:
        if fixture["round"] != "Round of 32":
            continue
        for side in ("team1", "team2"):
            slot = fixture[side]
            if slot.startswith("3"):
                third_slots.append(
                    {
                        "fixture_id": fixture["fixture_id"],
                        "slot": slot,
                        "eligible_groups": slot[1:].split("/"),
                    }
                )

    slots_by_constraint = sorted(
        third_slots,
        key=lambda item: (
            len([group for group in item["eligible_groups"] if group in third_pool]),
            int(item["fixture_id"]),
        ),
    )

    def search(index: int, available: set[str], assigned: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]] | None:
        if index == len(slots_by_constraint):
            return assigned

        slot = slots_by_constraint[index]
        candidates = [
            third_pool[group]
            for group in slot["eligible_groups"]
            if group in available and group in third_pool
        ]
        candidates = sorted(candidates, key=third_entry_key, reverse=True)
        for candidate in candidates:
            group = candidate["group"]
            next_assigned = dict(assigned)
            next_assigned[slot["fixture_id"]] = candidate
            result = search(index + 1, available - {group}, next_assigned)
            if result is not None:
                return result
        return None

    result = search(0, set(third_pool), {})
    if result is None:
        raise ThirdPlaceAssignmentError("Could not assign third-place teams to listed bracket pools.")
    return result


def resolve_slot(
    slot: str,
    fixture_id: str,
    group_rankings: dict[str, list[str]],
    third_assignments: dict[str, dict[str, Any]],
    results: dict[str, str],
) -> str:
    if slot.startswith("W") or slot.startswith("L"):
        return results[slot]
    if len(slot) >= 2 and slot[0] in {"1", "2"} and slot[1] in v2.GROUP_ORDER:
        return group_rankings[slot[1]][int(slot[0]) - 1]
    if slot.startswith("3"):
        return third_assignments[fixture_id]["team"]
    raise RuntimeError(f"Unresolved slot: {slot}")


def simulate_group_stage(
    powers: dict[str, dict[str, Any]],
    group_fixtures: list[dict[str, str]],
) -> tuple[dict[str, list[str]], dict[str, dict[str, Any]], dict[str, dict[str, int]]]:
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
        projection = v23.match_projection_v23(
            team_a,
            team_b,
            powers,
            fixture["ground"],
            fixture["round"],
            performance_noise_sd=v23.V23_CONFIG["group_performance_noise"],
        )
        goals_a, goals_b = v23.simulate_match(projection)
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

    group_rankings = {
        group: v23.rank_group(sorted(teams), table)
        for group, teams in groups.items()
    }
    thirds = []
    for group in v2.GROUP_ORDER:
        ranking = group_rankings[group]
        thirds.append({"group": group, "team": ranking[2], "stats": table[ranking[2]]})
    thirds = sorted(thirds, key=v23.third_sort, reverse=True)
    third_pool = {entry["group"]: entry for entry in thirds[:8]}
    return group_rankings, third_pool, table


def run_knockout_trace(
    powers: dict[str, dict[str, Any]],
    knockout_fixtures: list[dict[str, str]],
    group_rankings: dict[str, list[str]],
    third_pool: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results: dict[str, str] = {}
    path: list[dict[str, Any]] = []
    third_assignments = build_third_assignments(knockout_fixtures, third_pool)

    for fixture in knockout_fixtures:
        match_no = fixture["fixture_id"]
        round_name = fixture["round"]
        slot_a = fixture["team1"]
        slot_b = fixture["team2"]
        team_a = resolve_slot(slot_a, match_no, group_rankings, third_assignments, results)
        team_b = resolve_slot(slot_b, match_no, group_rankings, third_assignments, results)
        portugal_in_match = team_a == PORTUGAL or team_b == PORTUGAL
        opponent = team_b if team_a == PORTUGAL else team_a

        winner = v23.knockout_winner_v23(team_a, team_b, powers, fixture["ground"], round_name)
        loser = team_b if winner == team_a else team_a
        results[f"W{match_no}"] = winner
        results[f"L{match_no}"] = loser

        if portugal_in_match:
            path.append(
                {
                    "round": round_name,
                    "fixture_id": match_no,
                    "ground": fixture["ground"],
                    "slot_a": slot_a,
                    "slot_b": slot_b,
                    "opponent": opponent,
                    "result": "win" if winner == PORTUGAL else "loss",
                }
            )
            if winner != PORTUGAL:
                break

    return path


def top_counter(counter: Counter[str], denominator: int, limit: int = 8) -> str:
    if denominator <= 0:
        return ""
    parts = []
    for item, count in counter.most_common(limit):
        parts.append(f"{v2.display_team(item)} {pct(count / denominator)}%")
    return "; ".join(parts)


def summarize_paths(
    accepted_paths: list[list[dict[str, Any]]],
    accepted: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    stage_order = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"]
    opponent_by_stage: dict[str, Counter[str]] = {stage: Counter() for stage in stage_order}
    appearances_by_stage: Counter[str] = Counter()
    wins_by_stage: Counter[str] = Counter()
    elimination: Counter[str] = Counter()
    exact_paths: Counter[tuple[str, ...]] = Counter()

    for path in accepted_paths:
        labels = []
        portugal_lost = False
        for row in path:
            stage = row["round"]
            opponent = row["opponent"]
            appearances_by_stage[stage] += 1
            opponent_by_stage[stage].update([opponent])
            labels.append(f"{stage}: {v2.display_team(opponent)}")
            if row["result"] == "win":
                wins_by_stage[stage] += 1
            else:
                elimination[stage] += 1
                labels.append(f"eliminated in {stage}")
                portugal_lost = True
                break
        if path and not portugal_lost and path[-1]["round"] == "Final" and path[-1]["result"] == "win":
            elimination["Champion"] += 1
            labels.append("Champion")
        exact_paths.update([tuple(labels)])

    round_rows = []
    for stage in stage_order:
        apps = appearances_by_stage[stage]
        wins = wins_by_stage[stage]
        round_rows.append(
            {
                "stage": stage,
                "portugal_appearance_pct_given_group_first": pct(apps / accepted),
                "portugal_win_pct_given_stage_appearance": pct(wins / apps) if apps else 0.0,
                "top_opponents_when_stage_reached": top_counter(opponent_by_stage[stage], apps),
            }
        )

    elimination_rows = []
    for stage in ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final", "Champion"]:
        elimination_rows.append(
            {
                "outcome": stage if stage == "Champion" else f"Eliminated in {stage}",
                "pct_given_group_first": pct(elimination[stage] / accepted),
                "count": elimination[stage],
            }
        )

    path_rows = []
    for labels, count in exact_paths.most_common(25):
        path_rows.append(
            {
                "path_rank": len(path_rows) + 1,
                "path": " > ".join(labels),
                "pct_given_group_first": pct(count / accepted),
                "count": count,
            }
        )

    return round_rows, elimination_rows, path_rows


def write_report(
    group_match: dict[str, str],
    baseline_odds: dict[str, str],
    accepted: int,
    attempts: int,
    round_rows: list[dict[str, Any]],
    elimination_rows: list[dict[str, Any]],
    path_rows: list[dict[str, Any]],
) -> None:
    champ = next(row for row in elimination_rows if row["outcome"] == "Champion")
    lines = [
        "# Portugal Group-Winner Scenario v2.3",
        "",
        "This is a conditional Monte Carlo scenario using the existing v2.3 World Cup tournament engine.",
        "",
        "## First correction",
        "",
        "The saved v2.3 model did not call Colombia to beat Portugal in the final group match. It marked Colombia vs Portugal as a draw lean.",
        "",
        "| Match | Team 1 win | Draw | Team 2 win | Public call |",
        "|---|---:|---:|---:|---|",
        (
            f"| {group_match['team1']} vs {group_match['team2']} | "
            f"{float(group_match['team1_win_probability_internal']) * 100:.2f}% | "
            f"{float(group_match['draw_probability_internal']) * 100:.2f}% | "
            f"{float(group_match['team2_win_probability_internal']) * 100:.2f}% | "
            f"{group_match['public_verdict']} |"
        ),
        "",
        "Colombia ranked above Portugal because Colombia had a slightly higher v2.3 power score and a higher simulated chance of winning Group K, not because of one deterministic Portugal loss.",
        "",
        "| Team | Power | Group 1st % | Group 2nd % | Champion % |",
        "|---|---:|---:|---:|---:|",
        (
            f"| Colombia | {baseline_odds['Colombia']['v23_power_score']} | "
            f"{baseline_odds['Colombia']['group_first_pct']}% | "
            f"{baseline_odds['Colombia']['group_second_pct']}% | "
            f"{baseline_odds['Colombia']['champion_pct']}% |"
        ),
        (
            f"| Portugal | {baseline_odds['Portugal']['v23_power_score']} | "
            f"{baseline_odds['Portugal']['group_first_pct']}% | "
            f"{baseline_odds['Portugal']['group_second_pct']}% | "
            f"{baseline_odds['Portugal']['champion_pct']}% |"
        ),
        "",
        "## What-if condition",
        "",
        f"- Accepted simulations: {accepted:,}.",
        f"- Attempts needed: {attempts:,}.",
        f"- Acceptance rate: {attempts and pct(accepted / attempts)}%.",
        f"- Portugal title chance if it tops Group K: {champ['pct_given_group_first']}%.",
        "",
        "## Bracket if Portugal is 1K",
        "",
        "| Stage | Bracket slot |",
        "|---|---|",
        "| Round of 32 | 1K vs 3D/E/I/J/L |",
        "| Round of 16 | Winner of 1B vs 3E/F/G/I/J |",
        "| Quarter-final | Winner from the 1J/2H/2D/2G side |",
        "| Semi-final | Winner from the W91/W92 branch |",
        "| Final | Winner from the other half of the bracket |",
        "",
        "## Conditional Portugal Path",
        "",
        "| Stage | Portugal reaches stage | Win if stage reached | Most common opponents |",
        "|---|---:|---:|---|",
    ]
    for row in round_rows:
        lines.append(
            f"| {row['stage']} | {row['portugal_appearance_pct_given_group_first']}% | "
            f"{row['portugal_win_pct_given_stage_appearance']}% | {row['top_opponents_when_stage_reached']} |"
        )

    lines.extend(
        [
            "",
            "## Portugal Finish Distribution",
            "",
            "| Outcome | % if Portugal tops group |",
            "|---|---:|",
        ]
    )
    for row in elimination_rows:
        lines.append(f"| {row['outcome']} | {row['pct_given_group_first']}% |")

    lines.extend(
        [
            "",
            "## Most Common Exact Paths",
            "",
            "| Rank | Path | % |",
            "|---:|---|---:|",
        ]
    )
    for row in path_rows[:10]:
        lines.append(f"| {row['path_rank']} | {row['path']} | {row['pct_given_group_first']}% |")

    lines.extend(
        [
            "",
            "## Caveat",
            "",
            "This is still the v2.3 tournament simulator, so it uses the v2.3 power model and Poisson knockout engine. It is not yet the v2.6 ensemble/calibration layer.",
        ]
    )
    (OUTPUTS / "portugal_group_winner_v23_scenario.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    random.seed(CONFIG["seed"])
    fixtures = v2.read_csv(PROCESSED / "worldcup_2026_matches.csv")
    powers = v23.build_team_power_v23()
    group_fixtures = [fixture for fixture in fixtures if fixture["round"].startswith("Matchday")]
    knockout_fixtures = sorted(
        [fixture for fixture in fixtures if fixture["round"] in v2.ROUND_ORDER],
        key=lambda fixture: (v2.ROUND_ORDER[fixture["round"]], int(fixture["fixture_id"])),
    )

    accepted_paths: list[list[dict[str, Any]]] = []
    attempts = 0
    accepted = 0
    while accepted < CONFIG["accepted_simulations"]:
        attempts += 1
        group_rankings, third_pool, _table = simulate_group_stage(powers, group_fixtures)
        if group_rankings["K"][0] != PORTUGAL:
            continue
        try:
            path = run_knockout_trace(powers, knockout_fixtures, group_rankings, dict(third_pool))
        except ThirdPlaceAssignmentError:
            continue
        accepted_paths.append(path)
        accepted += 1

    round_rows, elimination_rows, path_rows = summarize_paths(accepted_paths, accepted)

    write_csv(
        PROCESSED / "portugal_group_winner_v23_round_summary.csv",
        round_rows,
        [
            "stage",
            "portugal_appearance_pct_given_group_first",
            "portugal_win_pct_given_stage_appearance",
            "top_opponents_when_stage_reached",
        ],
    )
    write_csv(
        PROCESSED / "portugal_group_winner_v23_elimination.csv",
        elimination_rows,
        ["outcome", "pct_given_group_first", "count"],
    )
    write_csv(
        PROCESSED / "portugal_group_winner_v23_top_paths.csv",
        path_rows,
        ["path_rank", "path", "pct_given_group_first", "count"],
    )
    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "portugal_group_winner_v23_config.json").write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")

    group_predictions = v2.read_csv(PROCESSED / "model_v23_group_match_predictions.csv")
    group_match = next(row for row in group_predictions if row["team1"] == "Colombia" and row["team2"] == "Portugal")
    baseline_rows = v2.read_csv(PROCESSED / "model_v23_tournament_odds.csv")
    baseline_odds = {row["team"]: row for row in baseline_rows}
    write_report(group_match, baseline_odds, accepted, attempts, round_rows, elimination_rows, path_rows)

    print(
        json.dumps(
            {
                "accepted": accepted,
                "attempts": attempts,
                "acceptance_rate_pct": pct(accepted / attempts),
                "portugal_champion_if_group_first_pct": next(
                    row["pct_given_group_first"] for row in elimination_rows if row["outcome"] == "Champion"
                ),
                "top_round_of_32_opponents": round_rows[0]["top_opponents_when_stage_reached"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
