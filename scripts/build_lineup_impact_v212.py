#!/usr/bin/env python3
"""Build the v2.12 confirmed-lineup impact challenger.

V2.12 consumes the frozen v2.11 shadow predictions and adjusts their already
calibrated probabilities only when both teams have complete, pre-kickoff
lineups with strong player-identity coverage. It can downgrade a public call,
but it cannot promote a v2.11 Pass in this first shadow version.
"""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import build_road_to_26_v24 as road24


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
ET = ZoneInfo("America/New_York")

V211_SHADOW_PATH = PROCESSED / "confidence_gate_v211_shadow_predictions.csv"
LINEUP_SNAPSHOTS_PATH = PROCESSED / "worldcup_matchday_v29_lineup_snapshots.csv"
PLAYER_IMPACT_PATH = PROCESSED / "player_impact_v21.csv"
V212_SHADOW_PATH = PROCESSED / "confidence_gate_v212_shadow_predictions.csv"
LINEUP_AUDIT_PATH = PROCESSED / "confidence_gate_v212_lineup_audit.csv"
PLAYER_MATCH_AUDIT_PATH = PROCESSED / "confidence_gate_v212_player_matches.csv"
CONFIG_PATH = OUTPUTS / "confidence_gate_v212_config.json"
REPORT_PATH = OUTPUTS / "confidence_gate_v212_report.md"

LABELS = ["team1_win", "draw", "team2_win"]

V212_CONFIG = {
    "version": "v2.12",
    "role": "Confirmed-lineup challenger layered on frozen v2.11 predictions.",
    "minimum_starters_per_team": 11,
    "minimum_player_match_coverage": 0.90,
    "fuzzy_player_match_threshold": 0.88,
    "lineup_logit_per_rating_point": 0.035,
    "maximum_team_logit_adjustment": 0.18,
    "maximum_probability_movement": 0.05,
    "minimum_adjusted_top_probability_for_existing_pick": 0.56,
    "minimum_adjusted_gap_for_existing_pick": 0.24,
    "promotion_policy": "V2.12 may preserve or downgrade a v2.11 call; it cannot promote a v2.11 Pass during initial shadow evaluation.",
    "baseline": "Mean impact_score of the 11 players marked Starter in Player Impact Rating v2.1.",
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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def person_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower())


def team_key(value: str) -> str:
    return road24.simple_team_key(value)


def player_index() -> tuple[dict[str, list[dict[str, str]]], dict[str, dict[str, dict[str, str]]]]:
    by_team: dict[str, list[dict[str, str]]] = defaultdict(list)
    exact: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in read_csv(PLAYER_IMPACT_PATH):
        key = team_key(row.get("team", ""))
        by_team[key].append(row)
        exact[key][person_key(row.get("player_name", ""))] = row
    return dict(by_team), dict(exact)


def match_player(
    name: str,
    team: str,
    by_team: dict[str, list[dict[str, str]]],
    exact: dict[str, dict[str, dict[str, str]]],
) -> tuple[dict[str, str] | None, str, float]:
    tkey = team_key(team)
    pkey = person_key(name)
    direct = exact.get(tkey, {}).get(pkey)
    if direct:
        return direct, "exact", 1.0
    candidates = []
    for player in by_team.get(tkey, []):
        score = SequenceMatcher(None, pkey, person_key(player.get("player_name", ""))).ratio()
        candidates.append((score, player))
    candidates.sort(key=lambda item: item[0], reverse=True)
    if candidates and candidates[0][0] >= V212_CONFIG["fuzzy_player_match_threshold"]:
        return candidates[0][1], "fuzzy", candidates[0][0]
    return None, "unmatched", candidates[0][0] if candidates else 0.0


def parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=ET)
    except (TypeError, ValueError):
        return None


def parse_kickoff(row: dict[str, str]) -> datetime | None:
    try:
        return datetime.fromisoformat(f"{row['date']}T{row['time_et']}:00").replace(tzinfo=ET)
    except (KeyError, ValueError):
        return None


def latest_pre_kickoff_lineups() -> dict[str, dict[str, dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(LINEUP_SNAPSHOTS_PATH):
        grouped[(row.get("fixture_key", ""), team_key(row.get("team", "")))].append(row)
    selected: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for (fixture_key, tkey), rows in grouped.items():
        annotated = []
        for row in rows:
            snapshot_time = parse_time(row.get("snapshot_timestamp_et", ""))
            kickoff = parse_kickoff(row)
            if snapshot_time and kickoff and snapshot_time <= kickoff:
                annotated.append((snapshot_time, row))
        if annotated:
            annotated.sort(key=lambda item: item[0])
            selected[fixture_key][tkey] = annotated[-1][1]
    return dict(selected)


def baseline_players(team: str, by_team: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    players = [row for row in by_team.get(team_key(team), []) if row.get("expected_role") == "Starter"]
    players.sort(key=lambda row: safe_float(row.get("impact_score")), reverse=True)
    return players[:11]


def evaluate_team_lineup(
    lineup: dict[str, str],
    team: str,
    by_team: dict[str, list[dict[str, str]]],
    exact: dict[str, dict[str, dict[str, str]]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    starter_names = [name.strip() for name in lineup.get("starters", "").split(";") if name.strip()]
    matches = []
    matched_players = []
    for starter_name in starter_names:
        player, method, score = match_player(starter_name, team, by_team, exact)
        if player:
            matched_players.append(player)
        matches.append(
            {
                "snapshot_timestamp_et": lineup.get("snapshot_timestamp_et", ""),
                "fixture_key": lineup.get("fixture_key", ""),
                "date": lineup.get("date", ""),
                "time_et": lineup.get("time_et", ""),
                "team": team,
                "provider_player_name": starter_name,
                "matched_player_name": player.get("player_name", "") if player else "",
                "match_method": method,
                "match_similarity": round(score, 5),
                "impact_score": player.get("impact_score", "") if player else "",
                "expected_role": player.get("expected_role", "") if player else "",
                "unit": player.get("unit", "") if player else "",
            }
        )
    baseline = baseline_players(team, by_team)
    baseline_score = sum(safe_float(row.get("impact_score")) for row in baseline) / len(baseline) if baseline else 0.0
    actual_score = sum(safe_float(row.get("impact_score")) for row in matched_players) / len(matched_players) if matched_players else 0.0
    coverage = len(matched_players) / len(starter_names) if starter_names else 0.0
    baseline_names = {person_key(row.get("player_name", "")): row.get("player_name", "") for row in baseline}
    actual_keys = {person_key(row.get("player_name", "")) for row in matched_players}
    missing_expected = [name for key, name in baseline_names.items() if key not in actual_keys]
    unexpected_starters = [
        row.get("player_name", "")
        for row in matched_players
        if row.get("expected_role") != "Starter"
    ]
    complete = (
        len(starter_names) >= V212_CONFIG["minimum_starters_per_team"]
        and coverage >= V212_CONFIG["minimum_player_match_coverage"]
        and len(baseline) == 11
    )
    audit = {
        "snapshot_timestamp_et": lineup.get("snapshot_timestamp_et", ""),
        "fixture_key": lineup.get("fixture_key", ""),
        "date": lineup.get("date", ""),
        "time_et": lineup.get("time_et", ""),
        "team": team,
        "formation": lineup.get("formation", ""),
        "starter_count": len(starter_names),
        "matched_starters": len(matched_players),
        "match_coverage": round(coverage, 5),
        "baseline_xi_score": round(baseline_score, 5),
        "actual_xi_score": round(actual_score, 5),
        "lineup_delta": round(actual_score - baseline_score, 5),
        "missing_expected_starters": "; ".join(missing_expected),
        "unexpected_starters": "; ".join(unexpected_starters),
        "lineup_complete": complete,
    }
    return audit, matches


def normalize_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    total = sum(probabilities.values()) or 1.0
    return {label: probabilities[label] / total for label in LABELS}


def adjust_probabilities(
    base: dict[str, float],
    team1_delta: float,
    team2_delta: float,
) -> tuple[dict[str, float], float, float]:
    per_point = V212_CONFIG["lineup_logit_per_rating_point"]
    cap = V212_CONFIG["maximum_team_logit_adjustment"]
    adjustment1 = clamp(team1_delta * per_point, -cap, cap)
    adjustment2 = clamp(team2_delta * per_point, -cap, cap)
    logits = {
        "team1_win": math.log(max(base["team1_win"], 1e-9)) + adjustment1,
        "draw": math.log(max(base["draw"], 1e-9)),
        "team2_win": math.log(max(base["team2_win"], 1e-9)) + adjustment2,
    }
    maximum = max(logits.values())
    exp_values = {label: math.exp(logits[label] - maximum) for label in LABELS}
    adjusted = normalize_probabilities(exp_values)
    largest_move = max(abs(adjusted[label] - base[label]) for label in LABELS)
    movement_cap = V212_CONFIG["maximum_probability_movement"]
    if largest_move > movement_cap:
        scale = movement_cap / largest_move
        adjusted = {label: base[label] + scale * (adjusted[label] - base[label]) for label in LABELS}
        adjusted = normalize_probabilities(adjusted)
    return adjusted, adjustment1, adjustment2


def classify_v212(row: dict[str, str], adjusted: dict[str, float], valid_lineups: bool) -> dict[str, Any]:
    if not valid_lineups:
        return {
            "v212_tier": row.get("v211_tier", "Pass"),
            "v212_pick": row.get("v211_pick", "pass"),
            "v212_reason": "Inherited v2.11 because both verified pre-kickoff lineups are not available.",
            "v212_changed_call": False,
        }
    if row.get("v211_pick") in {"", "pass"}:
        return {
            "v212_tier": "Pass",
            "v212_pick": "pass",
            "v212_reason": "Confirmed lineups evaluated; initial v2.12 policy cannot promote a v2.11 Pass.",
            "v212_changed_call": False,
        }
    ranked = sorted(adjusted.items(), key=lambda item: item[1], reverse=True)
    top_pick, top_probability = ranked[0]
    gap = top_probability - ranked[1][1]
    original_pick = row.get("v211_pick", "")
    if (
        top_pick == original_pick
        and top_probability >= V212_CONFIG["minimum_adjusted_top_probability_for_existing_pick"]
        and gap >= V212_CONFIG["minimum_adjusted_gap_for_existing_pick"]
    ):
        return {
            "v212_tier": row.get("v211_tier", "Model Lean"),
            "v212_pick": original_pick,
            "v212_reason": "Confirmed-lineup adjustment preserves the v2.11 directional call.",
            "v212_changed_call": False,
        }
    return {
        "v212_tier": "Pass",
        "v212_pick": "pass",
        "v212_reason": "Confirmed-lineup adjustment weakens or reverses the v2.11 directional edge.",
        "v212_changed_call": True,
    }


def frozen_shadow_start() -> datetime:
    if CONFIG_PATH.exists():
        try:
            existing = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            value = existing.get("freeze_timestamp_et", "")
            if existing.get("version") == "v2.12" and value:
                parsed = datetime.fromisoformat(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=ET)
        except (json.JSONDecodeError, ValueError):
            pass
    return datetime.now(ET)


def build_shadow(freeze_time: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = read_csv(V211_SHADOW_PATH)
    lineups = latest_pre_kickoff_lineups()
    by_team, exact = player_index()
    shadow = []
    lineup_audits = []
    player_matches = []
    for row in rows:
        fixture_lineups = lineups.get(row.get("fixture_key", ""), {})
        team_audits = {}
        for team_field in ["team1", "team2"]:
            team = row.get(team_field, "")
            lineup = fixture_lineups.get(team_key(team))
            if not lineup:
                continue
            audit, matches = evaluate_team_lineup(lineup, team, by_team, exact)
            lineup_audits.append(audit)
            player_matches.extend(matches)
            team_audits[team_field] = audit
        valid_lineups = (
            safe_bool(team_audits.get("team1", {}).get("lineup_complete"))
            and safe_bool(team_audits.get("team2", {}).get("lineup_complete"))
        )
        base = {
            "team1_win": safe_float(row.get("v211_team1_probability")),
            "draw": safe_float(row.get("v211_draw_probability")),
            "team2_win": safe_float(row.get("v211_team2_probability")),
        }
        base = normalize_probabilities(base)
        delta1 = safe_float(team_audits.get("team1", {}).get("lineup_delta"))
        delta2 = safe_float(team_audits.get("team2", {}).get("lineup_delta"))
        adjusted, logit1, logit2 = adjust_probabilities(base, delta1, delta2) if valid_lineups else (base, 0.0, 0.0)
        decision = classify_v212(row, adjusted, valid_lineups)
        kickoff = parse_kickoff(row)
        lineup_times = [parse_time(audit.get("snapshot_timestamp_et", "")) for audit in team_audits.values()]
        lineup_times = [value for value in lineup_times if value]
        latest_lineup_time = max(lineup_times) if lineup_times else None
        shadow_eligible = bool(
            valid_lineups
            and kickoff
            and kickoff > freeze_time
            and latest_lineup_time
            and latest_lineup_time <= kickoff
        )
        shadow.append(
            {
                **row,
                "v212_freeze_timestamp_et": freeze_time.isoformat(timespec="seconds"),
                "v212_lineup_snapshot_et": latest_lineup_time.isoformat(timespec="seconds") if latest_lineup_time else "",
                "v212_lineups_valid": valid_lineups,
                "v212_lineup_shadow_eligible": shadow_eligible,
                "v212_team1_lineup_score": team_audits.get("team1", {}).get("actual_xi_score", ""),
                "v212_team1_baseline_score": team_audits.get("team1", {}).get("baseline_xi_score", ""),
                "v212_team1_lineup_delta": team_audits.get("team1", {}).get("lineup_delta", ""),
                "v212_team2_lineup_score": team_audits.get("team2", {}).get("actual_xi_score", ""),
                "v212_team2_baseline_score": team_audits.get("team2", {}).get("baseline_xi_score", ""),
                "v212_team2_lineup_delta": team_audits.get("team2", {}).get("lineup_delta", ""),
                "v212_team1_logit_adjustment": round(logit1, 5),
                "v212_team2_logit_adjustment": round(logit2, 5),
                "v212_team1_probability": round(adjusted["team1_win"], 5),
                "v212_draw_probability": round(adjusted["draw"], 5),
                "v212_team2_probability": round(adjusted["team2_win"], 5),
                **decision,
            }
        )
    return shadow, lineup_audits, player_matches


def write_report(
    freeze_time: datetime,
    shadow: list[dict[str, Any]],
    lineup_audits: list[dict[str, Any]],
    player_matches: list[dict[str, Any]],
) -> None:
    total_players = len(player_matches)
    matched_players = sum(1 for row in player_matches if row.get("match_method") != "unmatched")
    fuzzy_players = sum(1 for row in player_matches if row.get("match_method") == "fuzzy")
    identity_coverage = matched_players / total_players if total_players else 0.0
    eligible = [row for row in shadow if safe_bool(row.get("v212_lineup_shadow_eligible"))]
    completed_eligible = [row for row in eligible if row.get("actual_result")]
    completed_picks = [row for row in completed_eligible if row.get("v212_pick") not in {"", "pass"}]
    completed_correct = sum(1 for row in completed_picks if row.get("v212_pick") == row.get("actual_result"))
    lines = [
        "# Confirmed-Lineup Impact v2.12",
        "",
        f"Frozen for lineup shadow evaluation: {freeze_time.isoformat(timespec='seconds')}",
        "",
        "V2.12 adjusts frozen v2.11 probabilities only when both confirmed starting XIs pass identity and timing checks.",
        "",
        "## Guardrails",
        "",
        "- Both teams require 11 starters and at least 90% player-identity coverage.",
        "- Only lineup snapshots captured at or before kickoff can enter evaluation.",
        "- A team adjustment is capped in log-odds space and final probability movement is capped at five percentage points.",
        "- V2.12 can preserve or downgrade a v2.11 call; it cannot create a pick from a v2.11 Pass.",
        "",
        "## Identity Audit",
        "",
        f"- Provider starters inspected: {total_players}.",
        f"- Matched to Player Impact Rating v2.1: {matched_players}/{total_players} ({identity_coverage * 100:.2f}%).",
        f"- Controlled fuzzy matches: {fuzzy_players}.",
        "",
        "| Team | Formation | Matched | Baseline XI | Confirmed XI | Delta | Missing expected starters |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for audit in lineup_audits:
        lines.append(
            f"| {audit['team']} | {audit['formation']} | {audit['matched_starters']}/{audit['starter_count']} | "
            f"{safe_float(audit['baseline_xi_score']):.2f} | {safe_float(audit['actual_xi_score']):.2f} | "
            f"{safe_float(audit['lineup_delta']):+.2f} | {audit['missing_expected_starters']} |"
        )
    lines.extend(
        [
            "",
            "## Frozen Lineup Shadow Results",
            "",
            f"- Completed lineup-eligible fixtures: {len(completed_eligible)}.",
            f"- Public picks scored: {len(completed_picks)}.",
            f"- Correct public picks: {completed_correct}.",
            f"- Accuracy: {completed_correct / len(completed_picks) * 100:.2f}%." if completed_picks else "- Accuracy: not enough completed public picks.",
            "",
            "## Lineup-Eligible Shadow Calls",
            "",
            "| Match | Kickoff | Result | v2.11 | v2.12 | Base 1/X/2 | Adjusted 1/X/2 | Lineup deltas |",
            "|---|---:|---|---|---|---|---|---|",
        ]
    )
    for row in eligible:
        base = f"{safe_float(row['v211_team1_probability']) * 100:.1f}/{safe_float(row['v211_draw_probability']) * 100:.1f}/{safe_float(row['v211_team2_probability']) * 100:.1f}"
        adjusted = f"{safe_float(row['v212_team1_probability']) * 100:.1f}/{safe_float(row['v212_draw_probability']) * 100:.1f}/{safe_float(row['v212_team2_probability']) * 100:.1f}"
        lines.append(
            f"| {row['team1']} vs {row['team2']} | {row['date']} {row['time_et']} | {row.get('provider_score') or 'pending'} | "
            f"{row['v211_tier']}: {row['v211_pick']} | "
            f"{row['v212_tier']}: {row['v212_pick']} | {base} | {adjusted} | "
            f"{safe_float(row['v212_team1_lineup_delta']):+.2f} / {safe_float(row['v212_team2_lineup_delta']):+.2f} |"
        )
    if not eligible:
        lines.append("| None yet |  |  |  |  |  |  |  |")
    lines.extend(
        [
            "",
            "## Honest Read",
            "",
            "V2.12 has no accuracy claim yet. Its first job is reliable player identity, pre-kickoff timing, bounded probability movement, and an auditable comparison against v2.11 on the same fixtures.",
        ]
    )
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    freeze_time = frozen_shadow_start()
    shadow, lineup_audits, player_matches = build_shadow(freeze_time)
    shadow_fields = list(shadow[0].keys()) if shadow else []
    write_csv(V212_SHADOW_PATH, shadow, shadow_fields)
    write_csv(
        LINEUP_AUDIT_PATH,
        lineup_audits,
        [
            "snapshot_timestamp_et",
            "fixture_key",
            "date",
            "time_et",
            "team",
            "formation",
            "starter_count",
            "matched_starters",
            "match_coverage",
            "baseline_xi_score",
            "actual_xi_score",
            "lineup_delta",
            "missing_expected_starters",
            "unexpected_starters",
            "lineup_complete",
        ],
    )
    write_csv(
        PLAYER_MATCH_AUDIT_PATH,
        player_matches,
        [
            "snapshot_timestamp_et",
            "fixture_key",
            "date",
            "time_et",
            "team",
            "provider_player_name",
            "matched_player_name",
            "match_method",
            "match_similarity",
            "impact_score",
            "expected_role",
            "unit",
        ],
    )
    config = {
        **V212_CONFIG,
        "freeze_timestamp_et": freeze_time.isoformat(timespec="seconds"),
        "inputs": [
            str(V211_SHADOW_PATH.relative_to(ROOT)),
            str(LINEUP_SNAPSHOTS_PATH.relative_to(ROOT)),
            str(PLAYER_IMPACT_PATH.relative_to(ROOT)),
        ],
        "outputs": [
            str(V212_SHADOW_PATH.relative_to(ROOT)),
            str(LINEUP_AUDIT_PATH.relative_to(ROOT)),
            str(PLAYER_MATCH_AUDIT_PATH.relative_to(ROOT)),
            str(REPORT_PATH.relative_to(ROOT)),
        ],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(freeze_time, shadow, lineup_audits, player_matches)
    total_players = len(player_matches)
    matched_players = sum(1 for row in player_matches if row.get("match_method") != "unmatched")
    print(
        json.dumps(
            {
                "lineup_teams_audited": len(lineup_audits),
                "starters_matched": f"{matched_players}/{total_players}",
                "identity_coverage": f"{matched_players / total_players * 100:.2f}%" if total_players else "",
                "lineup_shadow_fixtures": sum(1 for row in shadow if safe_bool(row.get("v212_lineup_shadow_eligible"))),
                "lineup_statuses": dict(Counter("valid" if safe_bool(row.get("v212_lineups_valid")) else "inherited" for row in shadow)),
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
