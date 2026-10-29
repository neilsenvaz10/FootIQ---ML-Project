#!/usr/bin/env python3
"""Live-aware World Cup tournament simulation v2.13.

This keeps the v2.3 tournament engine, but locks in actual completed group
results from the v2.10 validation table before simulating the remaining path.
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import build_worldcup_model_v2 as v2
import build_worldcup_model_v23 as v23


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

ODDS_PATH = PROCESSED / "live_tournament_v213_tournament_odds.csv"
REPORT_PATH = OUTPUTS / "live_tournament_v213_report.md"
CONFIG_PATH = OUTPUTS / "live_tournament_v213_config.json"
RESOLVED_ROUND_OF_32_PATH = PROCESSED / "worldcup_2026_round_of_32_resolved.csv"
VERIFIED_KNOCKOUT_RESULTS_PATH = PROCESSED / "worldcup_2026_knockout_results_verified.csv"

V213_CONFIG = {
    "version": "v2.13",
    "purpose": "Live-aware title odds: lock real completed results, then simulate the remaining tournament path.",
    "base_engine": "v2.3 team power + v2.3 group/knockout Monte Carlo",
    "actual_results_source": "data/processed/matchday_validation_v210.csv",
    "static_comparison_source": "data/processed/model_v23_tournament_odds.csv",
    "simulations": v23.V23_CONFIG["simulations"],
    "seed": 20260625,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_score(value: str) -> tuple[int, int] | None:
    if not value or "-" not in value:
        return None
    left, right = value.split("-", 1)
    try:
        return int(left.strip()), int(right.strip())
    except ValueError:
        return None


def result_key(date: str, team1: str, team2: str) -> tuple[str, str, str]:
    return date, v2.normalize_team(team1), v2.normalize_team(team2)


def load_actual_results() -> dict[tuple[str, str, str], tuple[int, int, str]]:
    rows = read_csv(PROCESSED / "matchday_validation_v210.csv")
    results: dict[tuple[str, str, str], tuple[int, int, str]] = {}
    for row in rows:
        if row.get("is_final") != "true":
            continue
        score = parse_score(row.get("provider_score", ""))
        if score is None:
            continue
        date = row.get("date", "")
        team1 = row.get("team1", "")
        team2 = row.get("team2", "")
        if not date or not team1 or not team2:
            continue
        g1, g2 = score
        key = result_key(date, team1, team2)
        reverse_key = result_key(date, team2, team1)
        results[key] = (g1, g2, "actual_result_locked")
        results[reverse_key] = (g2, g1, "actual_result_locked_reversed")
    return results


def find_actual_result(
    actual_results: dict[tuple[str, str, str], tuple[int, int, str]],
    date: str,
    team1: str,
    team2: str,
) -> tuple[int, int, str] | None:
    exact = actual_results.get(result_key(date, team1, team2))
    if exact:
        return exact

    normalized_team1 = v2.normalize_team(team1)
    normalized_team2 = v2.normalize_team(team2)
    pairing_matches = [
        result
        for (_, result_team1, result_team2), result in actual_results.items()
        if result_team1 == normalized_team1 and result_team2 == normalized_team2
    ]
    if len(pairing_matches) == 1:
        goals1, goals2, _ = pairing_matches[0]
        return goals1, goals2, "actual_result_locked_pairing_fallback"
    return None


def actual_knockout_winner(
    actual_results: dict[tuple[str, str, str], tuple[int, int, str]],
    date: str,
    team1: str,
    team2: str,
) -> str | None:
    actual = find_actual_result(actual_results, date, team1, team2)
    if not actual:
        return None
    goals1, goals2, _ = actual
    if goals1 == goals2:
        return None
    return team1 if goals1 > goals2 else team2


def verified_knockout_winner(
    verified_results: dict[str, dict[str, str]],
    fixture_id: str,
    team1: str,
    team2: str,
) -> str | None:
    result = verified_results.get(fixture_id)
    if not result:
        return None
    expected_teams = {v2.normalize_team(result["team1"]), v2.normalize_team(result["team2"])}
    resolved_teams = {v2.normalize_team(team1), v2.normalize_team(team2)}
    winner = v2.normalize_team(result.get("winner", ""))
    if expected_teams != resolved_teams or winner not in resolved_teams:
        return None
    return winner


def update_table(table: dict[str, dict[str, int]], team_a: str, team_b: str, goals_a: int, goals_b: int) -> None:
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


def run_live_sim(
    powers: dict[str, dict[str, Any]],
    group_fixtures: list[dict[str, str]],
    knockout_fixtures: list[dict[str, str]],
    actual_results: dict[tuple[str, str, str], tuple[int, int, str]],
    resolved_round_of_32: dict[str, dict[str, str]],
    verified_knockout_results: dict[str, dict[str, str]],
) -> dict[str, set[str]]:
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
        actual = find_actual_result(actual_results, fixture["date"], fixture["team1"], fixture["team2"])
        if actual:
            goals_a, goals_b, _ = actual
        else:
            projection = v23.match_projection_v23(
                team_a,
                team_b,
                powers,
                fixture["ground"],
                fixture["round"],
                performance_noise_sd=v23.V23_CONFIG["group_performance_noise"],
            )
            goals_a, goals_b = v23.simulate_match(projection)
        update_table(table, team_a, team_b, goals_a, goals_b)

    for stats in table.values():
        stats["goal_diff"] = stats["goals_for"] - stats["goals_against"]

    group_rankings = {group: v23.rank_group(sorted(teams), table) for group, teams in groups.items()}
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

    thirds = sorted(thirds, key=v23.third_sort, reverse=True)
    third_pool = {entry["group"]: entry for entry in thirds[:8]}
    reached["group_third_qualified"].update(entry["team"] for entry in thirds[:8])
    reached["qualified"].update(reached["group_third_qualified"])

    results: dict[str, str] = {}
    for fixture in knockout_fixtures:
        match_no = fixture["fixture_id"]
        round_name = fixture["round"]
        resolved_fixture = resolved_round_of_32.get(match_no) if round_name == "Round of 32" else None
        if resolved_fixture:
            team_a = v2.normalize_team(resolved_fixture["team1"])
            team_b = v2.normalize_team(resolved_fixture["team2"])
        else:
            team_a = v2.resolve_slot(fixture["team1"], group_rankings, third_pool, results)
            team_b = v2.resolve_slot(fixture["team2"], group_rankings, third_pool, results)
        winner = verified_knockout_winner(verified_knockout_results, match_no, team_a, team_b)
        if winner is None:
            winner = actual_knockout_winner(actual_results, fixture["date"], team_a, team_b)
        if winner is None:
            winner = v23.knockout_winner_v23(team_a, team_b, powers, fixture["ground"], round_name)
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


def current_actual_group_table(
    powers: dict[str, dict[str, Any]],
    group_fixtures: list[dict[str, str]],
    actual_results: dict[tuple[str, str, str], tuple[int, int, str]],
) -> dict[str, list[dict[str, Any]]]:
    table = {
        team: {"points": 0, "goals_for": 0, "goals_against": 0, "goal_diff": 0, "played": 0}
        for team in powers
    }
    for fixture in group_fixtures:
        actual = find_actual_result(actual_results, fixture["date"], fixture["team1"], fixture["team2"])
        if not actual:
            continue
        team_a = v2.normalize_team(fixture["team1"])
        team_b = v2.normalize_team(fixture["team2"])
        goals_a, goals_b, _ = actual
        update_table(table, team_a, team_b, goals_a, goals_b)
        table[team_a]["played"] += 1
        table[team_b]["played"] += 1

    for stats in table.values():
        stats["goal_diff"] = stats["goals_for"] - stats["goals_against"]

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for team, row in powers.items():
        stats = table[team]
        grouped[row["group"]].append(
            {
                "team": v2.display_team(team),
                "played": stats["played"],
                "points": stats["points"],
                "goal_diff": stats["goal_diff"],
                "goals_for": stats["goals_for"],
            }
        )
    for group in grouped:
        grouped[group].sort(key=lambda row: (row["points"], row["goal_diff"], row["goals_for"]), reverse=True)
    return dict(grouped)


def run_live_tournament() -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
    list[dict[str, str]],
]:
    random.seed(V213_CONFIG["seed"])
    powers = v23.build_team_power_v23()
    fixtures = read_csv(PROCESSED / "worldcup_2026_matches.csv")
    group_fixtures = [fixture for fixture in fixtures if fixture["round"].startswith("Matchday")]
    knockout_fixtures = sorted(
        [fixture for fixture in fixtures if fixture["round"] in v2.ROUND_ORDER],
        key=lambda fixture: (v2.ROUND_ORDER[fixture["round"]], int(fixture["fixture_id"])),
    )
    actual_results = load_actual_results()
    resolved_round_of_32_rows = read_csv(RESOLVED_ROUND_OF_32_PATH)
    resolved_round_of_32 = {row["fixture_id"]: row for row in resolved_round_of_32_rows}
    verified_knockout_result_rows = read_csv(VERIFIED_KNOCKOUT_RESULTS_PATH)
    verified_knockout_results = {row["fixture_id"]: row for row in verified_knockout_result_rows}

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

    sims = int(V213_CONFIG["simulations"])
    for _ in range(sims):
        reached = run_live_sim(
            powers,
            group_fixtures,
            knockout_fixtures,
            actual_results,
            resolved_round_of_32,
            verified_knockout_results,
        )
        for key, teams in reached.items():
            counters[key].update(teams)

    static = {row["team"]: row for row in read_csv(PROCESSED / "model_v23_tournament_odds.csv")}
    rows: list[dict[str, Any]] = []
    for team, row in powers.items():
        display = row["display_team"]
        old = static.get(display, {})
        champion_pct = round(100 * counters["champion"][team] / sims, 2)
        old_champion_pct = old.get("champion_pct", "")
        rows.append(
            {
                "team": display,
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
                "champion_pct": champion_pct,
                "static_v23_champion_pct": old_champion_pct,
                "champion_pct_change": round(champion_pct - float(old_champion_pct), 2) if old_champion_pct else "",
            }
        )

    rows.sort(key=lambda r: (r["champion_pct"], r["final_pct"], r["semi_final_pct"]), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["live_title_rank"] = idx
        static_rank = static.get(row["team"], {}).get("title_rank", "")
        row["static_v23_title_rank"] = static_rank
        row["rank_change"] = int(static_rank) - idx if static_rank else ""

    locked_fixture_ids = {
        fixture["fixture_id"]
        for fixture in group_fixtures
        if find_actual_result(actual_results, fixture["date"], fixture["team1"], fixture["team2"])
    }
    metadata = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "actual_group_results_locked": len(locked_fixture_ids),
        "group_matches_total": len(group_fixtures),
        "remaining_group_matches_simulated": len(group_fixtures) - len(locked_fixture_ids),
        "resolved_round_of_32_fixtures": len(resolved_round_of_32),
        "actual_knockout_results_locked": len(verified_knockout_results),
        "simulations": sims,
    }
    current_table = current_actual_group_table(powers, group_fixtures, actual_results)
    return rows, metadata, current_table, resolved_round_of_32_rows


def write_report(
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
    current_table: dict[str, list[dict[str, Any]]],
    resolved_round_of_32: list[dict[str, str]],
) -> None:
    top = rows[:16]
    movers = sorted(rows, key=lambda row: abs(float(row["champion_pct_change"] or 0.0)), reverse=True)[:10]
    rows_by_team = {row["team"]: row for row in rows}
    lines = [
        "# Live Tournament Simulation v2.13",
        "",
        f"Generated: {metadata['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Actual completed group results locked: {metadata['actual_group_results_locked']}/{metadata['group_matches_total']}.",
        f"- Remaining group matches simulated: {metadata['remaining_group_matches_simulated']}.",
        f"- Official resolved Round-of-32 fixtures loaded: {metadata['resolved_round_of_32_fixtures']}/16.",
        f"- Actual completed knockout results locked: {metadata['actual_knockout_results_locked']}.",
        f"- Monte Carlo simulations: {metadata['simulations']:,}.",
        "- Base engine: v2.3 team power, v2.3 group simulation, v2.3 knockout/extra-time/penalty logic.",
        "",
        "## Top Live Title Odds",
        "",
        "| Rank | Team | Champion % | Static v2.3 % | Change | Final % | Semi % | Qualify % |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in top:
        lines.append(
            f"| {row['live_title_rank']} | {row['team']} | {row['champion_pct']}% | "
            f"{row['static_v23_champion_pct']}% | {row['champion_pct_change']} | "
            f"{row['final_pct']}% | {row['semi_final_pct']}% | {row['qualify_knockout_pct']}% |"
        )

    lines.extend(
        [
            "",
            "## Biggest Title-Odds Moves vs Static v2.3",
            "",
            "| Team | Live rank | Static rank | Live % | Static % | Change |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in movers:
        lines.append(
            f"| {row['team']} | {row['live_title_rank']} | {row['static_v23_title_rank']} | "
            f"{row['champion_pct']}% | {row['static_v23_champion_pct']}% | {row['champion_pct_change']} |"
        )

    lines.extend(
        [
            "",
            "## Round of 32 Advancement Forecast",
            "",
            "These are full-match advancement probabilities from the tournament engine. Near-term v2.9 calls remain the authoritative public picks because they also include current weather and the calibrated pass policy.",
            "",
            "| Match | Date | Fixture | Team 1 advance | Team 2 advance | Model edge |",
            "|---:|---|---|---:|---:|---|",
        ]
    )
    for fixture in sorted(resolved_round_of_32, key=lambda row: int(row["fixture_id"])):
        team1 = fixture["team1"]
        team2 = fixture["team2"]
        team1_pct = float(rows_by_team[team1]["round_of_16_pct"])
        team2_pct = float(rows_by_team[team2]["round_of_16_pct"])
        edge = team1 if team1_pct >= team2_pct else team2
        lines.append(
            f"| {fixture['fixture_id']} | {fixture['date']} | {team1} v {team2} | "
            f"{team1_pct}% | {team2_pct}% | {edge} |"
        )

    lines.extend(["", "## Current Actual Group Tables", ""])
    for group in v2.GROUP_ORDER:
        group_rows = current_table.get(group, [])
        if not group_rows:
            continue
        lines.extend(
            [
                f"### Group {group}",
                "",
                "| Team | Played | Points | GD | GF |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in group_rows:
            if row["played"] == 0:
                continue
            lines.append(f"| {row['team']} | {row['played']} | {row['points']} | {row['goal_diff']} | {row['goals_for']} |")
        lines.append("")

    lines.extend(
        [
            "## Caveat",
            "",
            "This is not a new trained model. It is the old tournament engine made live-aware by locking actual completed results before simulation. Drawn knockout results require an explicit shootout winner before they can be locked.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows, metadata, current_table, resolved_round_of_32 = run_live_tournament()
    write_csv(
        ODDS_PATH,
        rows,
        [
            "live_title_rank",
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
            "static_v23_title_rank",
            "static_v23_champion_pct",
            "rank_change",
            "champion_pct_change",
        ],
    )
    write_report(rows, metadata, current_table, resolved_round_of_32)
    CONFIG_PATH.write_text(json.dumps({**V213_CONFIG, **metadata}, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "winner_favorite": rows[0]["team"],
                "champion_pct": f"{rows[0]['champion_pct']}%",
                "previous_static_favorite": "France",
                "actual_group_results_locked": metadata["actual_group_results_locked"],
                "remaining_group_matches_simulated": metadata["remaining_group_matches_simulated"],
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
