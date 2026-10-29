#!/usr/bin/env python3
"""World Cup prediction model v2.2.

V2.2 keeps the v2.1 team-strength layer and recalibrates the 90-minute
1/X/2 engine so draws are represented as a real model outcome.
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

V22_CONFIG = {
    "version": "v2.2",
    "seed": 20260606,
    "simulations": 50000,
    "base_goal_rate": 1.15,
    "power_goal_scale": 62.0,
    "draw_decision_min": 0.28,
    "draw_gap_max": 0.12,
    "draw_favorite_max": 0.42,
    "firm_draw_gap_max": 0.04,
    "firm_draw_favorite_max": 0.38,
    "profile_input": "data/inputs/model_v21_team_profiles.csv",
    "player_impact_input": "data/processed/player_impact_v21.csv",
    "weights": v2.MODEL_CONFIG["weights"],
}


def read_player_profiles() -> list[dict[str, Any]]:
    return v2.read_csv(INPUTS / "model_v21_team_profiles.csv")


def is_draw_risk(projection: dict[str, Any]) -> bool:
    p1 = projection["team1_win_probability"]
    pd = projection["draw_probability"]
    p2 = projection["team2_win_probability"]
    return (
        pd >= V22_CONFIG["draw_decision_min"]
        and abs(p1 - p2) <= V22_CONFIG["draw_gap_max"]
        and max(p1, p2) <= V22_CONFIG["draw_favorite_max"]
    )


def is_firm_draw_lean(projection: dict[str, Any]) -> bool:
    p1 = projection["team1_win_probability"]
    p2 = projection["team2_win_probability"]
    return (
        is_draw_risk(projection)
        and abs(p1 - p2) <= V22_CONFIG["firm_draw_gap_max"]
        and max(p1, p2) <= V22_CONFIG["firm_draw_favorite_max"]
    )


def model_pick_90min(projection: dict[str, Any]) -> str:
    if is_draw_risk(projection):
        return "draw"
    return "team1_win" if projection["team1_win_probability"] >= projection["team2_win_probability"] else "team2_win"


def public_verdict_v22(projection: dict[str, Any]) -> tuple[str, str, str]:
    t1 = v2.display_team(projection["team1"])
    t2 = v2.display_team(projection["team2"])
    p1 = projection["team1_win_probability"]
    p2 = projection["team2_win_probability"]
    fav_team = t1 if p1 >= p2 else t2

    if is_firm_draw_lean(projection):
        return (
            "Draw lean",
            "Low-medium",
            "The draw is not the largest raw probability, but the win sides are close enough that forcing a side is weaker than the 1X2 draw risk.",
        )
    if is_draw_risk(projection):
        return (
            "Draw risk / no strong edge",
            "Pass",
            "Draw probability is high for this model and neither side separates enough for a public winner call.",
        )

    verdict, confidence, reason = v2.public_verdict(projection)
    if verdict == "No strong edge":
        return verdict, confidence, "No side separates enough, but draw risk is below the v2.2 draw-call threshold."
    if "avoid defeat" in verdict:
        return verdict, confidence, f"{fav_team} is preferred, but the calibrated draw layer keeps this below a clean win call."
    return verdict, confidence, reason


def build_group_predictions_v22(powers: dict[str, dict[str, Any]], fixtures: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for fixture in fixtures:
        if not fixture["round"].startswith("Matchday"):
            continue
        team_a = v2.normalize_team(fixture["team1"])
        team_b = v2.normalize_team(fixture["team2"])
        projection = v2.match_projection(team_a, team_b, powers, fixture["ground"], fixture["round"])
        verdict, confidence, reason = public_verdict_v22(projection)
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


def compare_v21_v22(v22_odds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    v21 = {row["team"]: row for row in v2.read_csv(PROCESSED / "model_v21_tournament_odds.csv")}
    rows = []
    for row in v22_odds:
        team = row["team"]
        old = v21.get(team)
        rows.append(
            {
                "team": team,
                "v21_title_rank": old["title_rank"] if old else "",
                "v22_title_rank": row["title_rank"],
                "v21_champion_pct": old["champion_pct"] if old else "",
                "v22_champion_pct": row["champion_pct"],
                "champion_pct_change": round(float(row["champion_pct"]) - float(old["champion_pct"]), 2) if old else "",
                "v21_final_pct": old["final_pct"] if old else "",
                "v22_final_pct": row["final_pct"],
                "final_pct_change": round(float(row["final_pct"]) - float(old["final_pct"]), 2) if old else "",
            }
        )
    rows.sort(key=lambda r: abs(float(r["champion_pct_change"] or 0.0)), reverse=True)
    return rows


def write_summary(v22_odds: list[dict[str, Any]], group_predictions: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> None:
    draw_picks = [row for row in group_predictions if row["model_90min_pick"] == "draw"]
    draw_leans = [row for row in group_predictions if row["public_verdict"] == "Draw lean"]
    lines = [
        "# World Cup Model v2.2",
        "",
        "V2.2 keeps the Player Impact Rating v2.1 team layer and recalibrates the 90-minute 1/X/2 engine.",
        "",
        "## What changed",
        "",
        f"- Base goal rate lowered from 1.18 to {V22_CONFIG['base_goal_rate']}.",
        f"- Power-to-goal scale widened from 43 to {V22_CONFIG['power_goal_scale']}, reducing overconfident side separation.",
        "- Draw risk is now a first-class match state instead of being buried under side picks.",
        "- Public draw language is conservative: most draw calls are framed as draw risk/no strong edge, not certainty.",
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
    for row in v22_odds[:12]:
        lines.append(f"| {row['title_rank']} | {row['team']} | {row['champion_pct']}% | {row['final_pct']}% | {row['semi_final_pct']}% |")
    lines.extend(
        [
            "",
            "## Biggest Changes vs v2.1",
            "",
            "| Team | v2.1 % | v2.2 % | Change |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in comparison[:10]:
        lines.append(f"| {row['team']} | {row['v21_champion_pct']}% | {row['v22_champion_pct']}% | {row['champion_pct_change']} |")
    lines.extend(
        [
            "",
            "## Honest Caveat",
            "",
            "This fixes the no-draw behavior in the public match layer, but it does not magically make exact draw calls easy. The backtest shows draw-aware calibration improves probability quality while hard draw picks remain difficult.",
        ]
    )
    (OUTPUTS / "world_cup_model_v22_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    v2.create_or_refresh_team_profiles = read_player_profiles
    v2.MODEL_CONFIG.update(
        {
            "seed": V22_CONFIG["seed"],
            "simulations": V22_CONFIG["simulations"],
            "base_goal_rate": V22_CONFIG["base_goal_rate"],
            "power_goal_scale": V22_CONFIG["power_goal_scale"],
            "profile_input": V22_CONFIG["profile_input"],
            "player_impact_input": V22_CONFIG["player_impact_input"],
            "draw_decision_min": V22_CONFIG["draw_decision_min"],
            "draw_gap_max": V22_CONFIG["draw_gap_max"],
            "draw_favorite_max": V22_CONFIG["draw_favorite_max"],
        }
    )

    fixtures = v2.read_csv(PROCESSED / "worldcup_2026_matches.csv")
    powers = v2.build_team_power()
    team_rows = sorted(powers.values(), key=lambda row: row["v2_power_score"], reverse=True)
    for idx, row in enumerate(team_rows, start=1):
        row["v22_power_rank"] = idx
        row["v22_power_score"] = row["v2_power_score"]

    group_predictions = build_group_predictions_v22(powers, fixtures)
    v22_odds = v2.run_tournament(powers, fixtures)
    comparison = compare_v21_v22(v22_odds)

    v2.write_csv(
        PROCESSED / "model_v22_group_match_predictions.csv",
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
    v2.write_csv(
        PROCESSED / "model_v22_team_power.csv",
        team_rows,
        [
            "v22_power_rank",
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
            "v22_power_score",
            "manager_name",
            "preferred_style",
            "profile_source_status",
            "open_tactical_data_status",
        ],
    )
    v2.write_csv(
        PROCESSED / "model_v22_tournament_odds.csv",
        v22_odds,
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
        PROCESSED / "model_v22_vs_v21_comparison.csv",
        comparison,
        [
            "team",
            "v21_title_rank",
            "v22_title_rank",
            "v21_champion_pct",
            "v22_champion_pct",
            "champion_pct_change",
            "v21_final_pct",
            "v22_final_pct",
            "final_pct_change",
        ],
    )
    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "world_cup_model_v22_config.json").write_text(json.dumps(V22_CONFIG, indent=2), encoding="utf-8")
    write_summary(v22_odds, group_predictions, comparison)
    print(
        json.dumps(
            {
                "teams": len(team_rows),
                "group_matches": len(group_predictions),
                "draw_90min_picks": sum(1 for row in group_predictions if row["model_90min_pick"] == "draw"),
                "top": v22_odds[:5],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
