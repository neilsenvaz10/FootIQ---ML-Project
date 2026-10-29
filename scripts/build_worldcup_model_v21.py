#!/usr/bin/env python3
"""World Cup prediction model v2.1.

V2.1 keeps the v2 tournament engine but replaces the seed/proxy squad layer
with Player Impact Rating v2.1 team profiles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import build_worldcup_model_v2 as v2


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
INPUTS = ROOT / "data" / "inputs"
OUTPUTS = ROOT / "outputs"


def read_player_profiles() -> list[dict[str, Any]]:
    return v2.read_csv(INPUTS / "model_v21_team_profiles.csv")


def write_summary(v21_odds: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> None:
    pass_count = sum(1 for row in v2.read_csv(PROCESSED / "model_v21_group_match_predictions.csv") if row["confidence"] == "Pass")
    lines = [
        "# World Cup Model v2.1",
        "",
        "V2.1 keeps the weighted v2 tournament engine but replaces the seed/proxy squad inputs with Player Impact Rating v2.1 team scores.",
        "",
        "## Player Layer",
        "",
        "- 1,246 players populated from public squad tables.",
        "- Squad, expected XI, and bench scores are derived from player impact scores.",
        "- Ratings are model-derived and transparent; they are not copied from EA, FIFA, Transfermarkt, or a paid provider.",
        "",
        "## Weighting",
        "",
        "| Layer | Weight |",
        "|---|---:|",
    ]
    for key, value in v2.MODEL_CONFIG["weights"].items():
        lines.append(f"| {key} | {value:.0%} |")
    lines.extend(
        [
            "",
            "## Top Title Odds",
            "",
            "| Rank | Team | Champion % | Final % | Semi % |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for row in v21_odds[:12]:
        lines.append(f"| {row['title_rank']} | {row['team']} | {row['champion_pct']}% | {row['final_pct']}% | {row['semi_final_pct']}% |")
    lines.extend(
        [
            "",
            "## Biggest Changes vs v1",
            "",
            "| Team | V1 % | V2.1 % | Change |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in comparison[:10]:
        lines.append(f"| {row['team']} | {row['v1_champion_pct']}% | {row['v2_champion_pct']}% | {row['champion_pct_change']} |")
    lines.extend(
        [
            "",
            f"Group-stage no-edge/pass calls in v2.1: {pass_count}.",
            "",
            "## Honest Caveat",
            "",
            "This is a stronger product layer than v2 because player names and derived role scores are now populated. The biggest remaining weakness is that recent club/national minutes are still inferred rather than pulled from a licensed live feed.",
        ]
    )
    (OUTPUTS / "world_cup_model_v21_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    v2.create_or_refresh_team_profiles = read_player_profiles
    v2.MODEL_CONFIG["seed"] = 20260605
    v2.MODEL_CONFIG["profile_input"] = "data/inputs/model_v21_team_profiles.csv"
    v2.MODEL_CONFIG["player_impact_input"] = "data/processed/player_impact_v21.csv"

    fixtures = v2.read_csv(PROCESSED / "worldcup_2026_matches.csv")
    powers = v2.build_team_power()
    team_rows = sorted(powers.values(), key=lambda row: row["v2_power_score"], reverse=True)
    for idx, row in enumerate(team_rows, start=1):
        row["v21_power_rank"] = idx

    group_predictions = v2.build_group_predictions(powers, fixtures)
    v21_odds = v2.run_tournament(powers, fixtures)
    comparison = v2.compare_v1_v2(v21_odds)

    v2.write_csv(
        PROCESSED / "model_v21_group_match_predictions.csv",
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
            "confidence",
            "model_reason",
            "team1_win_probability_internal",
            "draw_probability_internal",
            "team2_win_probability_internal",
            "team1_internal_xg",
            "team2_internal_xg",
            "team1_power",
            "team2_power",
            "power_diff_team1",
        ],
    )
    v2.write_csv(
        PROCESSED / "model_v21_team_power.csv",
        team_rows,
        [
            "v21_power_rank",
            "team",
            "display_team",
            "group",
            "v1_total_rating",
            "v1_title_tier",
            "elo_score",
            "squad_score",
            "manager_score",
            "recent_form_score",
            "tactical_score",
            "ceiling_score",
            "availability_score",
            "v2_power_score",
            "manager_name",
            "preferred_style",
            "profile_source_status",
            "open_tactical_data_status",
        ],
    )
    v2.write_csv(
        PROCESSED / "model_v21_tournament_odds.csv",
        v21_odds,
        [
            "title_rank",
            "team",
            "group",
            "v2_power_score",
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
    v2.write_csv(
        PROCESSED / "model_v21_vs_v1_comparison.csv",
        comparison,
        [
            "team",
            "v1_title_rank",
            "v2_title_rank",
            "v1_champion_pct",
            "v2_champion_pct",
            "champion_pct_change",
            "v1_final_pct",
            "v2_final_pct",
            "final_pct_change",
        ],
    )
    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "world_cup_model_v21_config.json").write_text(json.dumps(v2.MODEL_CONFIG, indent=2), encoding="utf-8")
    write_summary(v21_odds, comparison)
    print(json.dumps({"teams": len(team_rows), "group_matches": len(group_predictions), "top": v21_odds[:5]}, indent=2))


if __name__ == "__main__":
    main()
