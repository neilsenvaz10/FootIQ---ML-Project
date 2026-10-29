#!/usr/bin/env python3
"""Validate v2.9 World Cup matchday snapshots.

V2.10 keeps the prediction model stable and adds post-match accountability:
- read the v2.9 snapshot audit file
- select the latest pre-kickoff prediction for each provider fixture
- fetch current fixture results/statuses
- score Strong Pick / Model Lean / Pass behavior
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import build_road_to_26_v24 as road24
from api_football_client_v24 import APIFootballError, budget_snapshot, provider_get


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
ET = ZoneInfo("America/New_York")

SNAPSHOTS_PATH = PROCESSED / "worldcup_matchday_v29_snapshots.csv"
MANUAL_RESULTS_PATH = PROCESSED / "worldcup_manual_results.csv"
VALIDATION_PATH = PROCESSED / "matchday_validation_v210.csv"
REPORT_PATH = OUTPUTS / "matchday_validation_v210_report.md"
CONFIG_PATH = OUTPUTS / "matchday_validation_v210_config.json"

OUTCOME_LABELS = ["team1_win", "draw", "team2_win"]
PROB_COLUMNS = {
    "team1_win": "team1_win_probability",
    "draw": "draw_probability",
    "team2_win": "team2_win_probability",
}

V210_CONFIG = {
    "version": "v2.10",
    "purpose": "Post-match validation for v2.9 World Cup matchday predictions.",
    "base_predictions": "data/processed/worldcup_matchday_v29_snapshots.csv",
    "snapshot_policy": "Use the latest snapshot taken at or before kickoff for each provider fixture ID.",
    "scoring_scope": "Regulation 1/X/2 labels. AET/PEN fixtures use score.fulltime and are withheld if that field is unavailable.",
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


def pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value * 100:.2f}%"


def parse_snapshot_time(value: str) -> datetime | None:
    try:
        if not value:
            return None
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=ET)
        return parsed
    except ValueError:
        return None


def parse_kickoff(row: dict[str, str]) -> datetime | None:
    try:
        return datetime.fromisoformat(f"{row['date']}T{row['time_et']}:00").replace(tzinfo=ET)
    except (KeyError, ValueError):
        return None


def row_probability(row: dict[str, str], outcome: str) -> float:
    return safe_float(row.get(PROB_COLUMNS[outcome]), 0.0)


def top_outcome(row: dict[str, str]) -> tuple[str, float, float]:
    probs = [(label, row_probability(row, label)) for label in OUTCOME_LABELS]
    probs.sort(key=lambda item: item[1], reverse=True)
    return probs[0][0], probs[0][1], probs[0][1] - probs[1][1]


def select_prediction_rows(rows: list[dict[str, str]], date_filter: str) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        team_keys = sorted(
            [
                road24.simple_team_key(row.get("team1", "")),
                road24.simple_team_key(row.get("team2", "")),
            ]
        )
        if not all(team_keys):
            continue
        if date_filter and row.get("date") != date_filter:
            continue
        fixture_identity = "|".join(
            [
                row.get("date", ""),
                row.get("time_et", ""),
                *team_keys,
            ]
        )
        grouped.setdefault(fixture_identity, []).append(row)

    selected = []
    for fixture_id, fixture_rows in grouped.items():
        annotated = []
        for row in fixture_rows:
            snapshot_time = parse_snapshot_time(row.get("snapshot_timestamp_et", ""))
            kickoff_time = parse_kickoff(row)
            before_kickoff = bool(snapshot_time and kickoff_time and snapshot_time <= kickoff_time)
            annotated.append((before_kickoff, snapshot_time or datetime.min.replace(tzinfo=ET), row))

        before_rows = [item for item in annotated if item[0]]
        pool = before_rows or annotated
        pool.sort(key=lambda item: item[1])
        chosen = dict(pool[-1][2])
        chosen["snapshots_seen"] = len(fixture_rows)
        chosen["selected_snapshot_policy"] = "latest_pre_kickoff" if before_rows else "fallback_latest_available"
        selected.append(chosen)

    selected.sort(key=lambda row: (row.get("date", ""), row.get("time_et", ""), row.get("team1", "")))
    return selected


def manual_result(row: dict[str, str]) -> dict[str, Any] | None:
    wanted = frozenset({road24.simple_team_key(row.get("team1", "")), road24.simple_team_key(row.get("team2", ""))})
    for result_row in read_csv(MANUAL_RESULTS_PATH):
        if result_row.get("date") != row.get("date"):
            continue
        candidate = frozenset(
            {
                road24.simple_team_key(result_row.get("team1", "")),
                road24.simple_team_key(result_row.get("team2", "")),
            }
        )
        if candidate != wanted:
            continue
        score1 = int(result_row["score1"])
        score2 = int(result_row["score2"])
        actual = road24.actual_result_label(
            score1,
            score2,
            result_row["team1"],
            result_row["team2"],
            row.get("team1", ""),
            row.get("team2", ""),
        )
        same_orientation = road24.simple_team_key(result_row["team1"]) == road24.simple_team_key(row.get("team1", ""))
        provider_score = f"{score1}-{score2}" if same_orientation else f"{score2}-{score1}"
        return {
            "provider_status": result_row.get("status", "FT"),
            "provider_status_long": f"Manual sourced result: {result_row.get('source_url', '')}",
            "provider_home": result_row["team1"],
            "provider_away": result_row["team2"],
            "provider_score": provider_score,
            "actual_result": actual,
            "is_final": True,
            "needs_90min_review": False,
            "provider_error": "",
        }
    return None


def regulation_goals(response: dict[str, Any], status_short: str) -> tuple[Any, Any, bool]:
    goals = response.get("goals", {})
    if status_short not in {"AET", "PEN"}:
        return goals.get("home"), goals.get("away"), False

    fulltime = response.get("score", {}).get("fulltime", {}) or {}
    home = fulltime.get("home")
    away = fulltime.get("away")
    if home is not None and away is not None:
        return home, away, False
    return goals.get("home"), goals.get("away"), True


def fetch_result(row: dict[str, str], args: argparse.Namespace) -> dict[str, Any]:
    fallback = manual_result(row)
    if fallback:
        return fallback
    if not row.get("provider_fixture_id"):
        return {"provider_error": "Missing provider fixture ID and no manual result fallback."}
    try:
        result = provider_get(
            "fixtures",
            {"id": row["provider_fixture_id"], "timezone": "America/New_York"},
            ttl_hours=args.ttl_hours,
            force_refresh=args.force_refresh,
            daily_limit=args.daily_limit,
            reserve_requests=args.reserve_requests,
        )
    except APIFootballError as exc:
        fallback = result_from_snapshot(row, provider_error=str(exc))
        if fallback.get("provider_status"):
            fallback["provider_status_long"] = fallback.get("provider_status_long") or "Snapshot fallback after provider result lookup failed."
            return fallback
        return {"provider_error": str(exc)}

    if not result.response_rows:
        fallback = result_from_snapshot(row, provider_error="No provider fixture row returned.")
        if fallback.get("provider_status"):
            fallback["provider_status_long"] = fallback.get("provider_status_long") or "Snapshot fallback after empty provider result lookup."
            return fallback
        return {"provider_error": "No provider fixture row returned."}
    response = result.response_rows[0]
    fixture = response.get("fixture", {})
    teams = response.get("teams", {})
    status = fixture.get("status", {})
    home = teams.get("home", {}).get("name", "")
    away = teams.get("away", {}).get("name", "")
    status_short = status.get("short", "")
    home_goals, away_goals, needs_90min_review = regulation_goals(response, status_short)
    live_score = ""
    if home_goals is not None and away_goals is not None:
        live_score = f"{home_goals}-{away_goals}"
    actual = ""
    if status_short in road24.FINAL_STATUSES and not needs_90min_review:
        actual = road24.actual_result_label(
            home_goals,
            away_goals,
            home,
            away,
            row.get("team1", ""),
            row.get("team2", ""),
        )
    return {
        "provider_status": status_short,
        "provider_status_long": status.get("long", ""),
        "provider_home": home,
        "provider_away": away,
        "provider_score": live_score,
        "actual_result": actual,
        "is_final": status_short in road24.FINAL_STATUSES,
        "needs_90min_review": needs_90min_review,
        "provider_error": "",
    }


def result_from_snapshot(row: dict[str, str], provider_error: str = "") -> dict[str, Any]:
    status_short = row.get("provider_status", "")
    actual = row.get("actual_90min_result", "")
    live_score = row.get("live_score", "")
    return {
        "provider_status": status_short,
        "provider_status_long": row.get("provider_status_long", ""),
        "provider_home": row.get("provider_home", ""),
        "provider_away": row.get("provider_away", ""),
        "provider_score": live_score,
        "actual_result": actual,
        "is_final": status_short in road24.FINAL_STATUSES or bool(actual),
        "needs_90min_review": status_short in {"AET", "PEN"},
        "provider_error": provider_error,
    }


def bool_text(value: Any) -> str:
    if value == "":
        return ""
    return "true" if bool(value) else "false"


def brier_score(row: dict[str, str], actual: str) -> float:
    return sum((row_probability(row, label) - (1.0 if label == actual else 0.0)) ** 2 for label in OUTCOME_LABELS)


def log_loss(row: dict[str, str], actual: str) -> float:
    probability = max(1e-6, min(1 - 1e-6, row_probability(row, actual)))
    return -math.log(probability)


def exact_score_correct(predicted_score: str, provider_score: str) -> str:
    if not predicted_score or not provider_score:
        return ""
    return bool_text(predicted_score == provider_score)


def pass_read(row: dict[str, str], actual: str, internal_correct: bool | str) -> str:
    if row.get("v28_tier") != "Pass" or not actual:
        return ""
    internal_pick = row.get("v27_internal_ensemble_pick", "")
    top_pick, top_prob, gap = top_outcome(row)
    draw_prob = row_probability(row, "draw")
    if actual == "draw" and draw_prob >= 0.30:
        return "good_pass_draw_risk"
    if internal_pick and internal_correct is False:
        return "good_pass_protected_wrong_internal"
    if internal_pick and internal_correct is True and top_pick != "draw" and top_prob >= 0.50 and gap >= 0.15:
        return "possible_too_conservative"
    return "neutral_pass"


def validation_read(row: dict[str, Any]) -> str:
    if row.get("provider_error"):
        return "provider_error"
    if row.get("is_final") != "true":
        return "pending"
    if row.get("eligible_for_accuracy") != "true":
        return "backfill_not_scored"
    if row["v28_tier"] == "Pass":
        return row.get("pass_read", "neutral_pass")
    if row.get("v28_pick_correct") == "true":
        return "pick_correct"
    return "pick_wrong"


def build_validation_row(row: dict[str, str], result: dict[str, Any]) -> dict[str, Any]:
    actual = result.get("actual_result", "")
    is_final = bool(result.get("is_final"))
    eligible_for_accuracy = row.get("selected_snapshot_policy") == "latest_pre_kickoff"
    v28_pick = row.get("v28_pick", "")
    internal_pick = row.get("v27_internal_ensemble_pick", "")
    scored_public = bool(is_final and eligible_for_accuracy and actual and v28_pick and v28_pick != "pass")
    scored_internal = bool(is_final and eligible_for_accuracy and actual and internal_pick)
    public_correct: bool | str = actual == v28_pick if scored_public else ""
    internal_correct: bool | str = actual == internal_pick if scored_internal else ""
    actual_probability = row_probability(row, actual) if actual else ""
    top_pick, top_prob, gap = top_outcome(row)
    validation = {
        "fixture_key": row.get("fixture_key", ""),
        "provider_fixture_id": row.get("provider_fixture_id", ""),
        "date": row.get("date", ""),
        "time_et": row.get("time_et", ""),
        "team1": row.get("team1", ""),
        "team2": row.get("team2", ""),
        "venue": row.get("venue", ""),
        "city": row.get("city", ""),
        "snapshot_timestamp_et": row.get("snapshot_timestamp_et", ""),
        "selected_snapshot_policy": row.get("selected_snapshot_policy", ""),
        "eligible_for_accuracy": bool_text(eligible_for_accuracy),
        "snapshots_seen": row.get("snapshots_seen", ""),
        "provider_status": result.get("provider_status", ""),
        "provider_status_long": result.get("provider_status_long", ""),
        "provider_home": result.get("provider_home", row.get("provider_home", "")),
        "provider_away": result.get("provider_away", row.get("provider_away", "")),
        "provider_score": result.get("provider_score", ""),
        "is_final": bool_text(is_final),
        "needs_90min_review": bool_text(result.get("needs_90min_review", False)),
        "actual_result": actual,
        "v28_tier": row.get("v28_tier", ""),
        "v28_pick": v28_pick,
        "v28_confidence": row.get("v28_confidence", ""),
        "v27_internal_ensemble_pick": internal_pick,
        "v28_pick_scored": bool_text(scored_public),
        "v28_pick_correct": bool_text(public_correct),
        "internal_pick_scored": bool_text(scored_internal),
        "internal_pick_correct": bool_text(internal_correct),
        "actual_probability": round(actual_probability, 5) if actual_probability != "" else "",
        "top_outcome": top_pick,
        "top_probability": round(top_prob, 5),
        "probability_gap": round(gap, 5),
        "team1_win_probability": row.get("team1_win_probability", ""),
        "draw_probability": row.get("draw_probability", ""),
        "team2_win_probability": row.get("team2_win_probability", ""),
        "predicted_score": row.get("predicted_score", ""),
        "modal_score": row.get("modal_score", ""),
        "exact_score_correct": exact_score_correct(row.get("predicted_score", ""), result.get("provider_score", "")) if is_final else "",
        "brier_score": round(brier_score(row, actual), 5) if actual else "",
        "log_loss": round(log_loss(row, actual), 5) if actual else "",
        "temperature_c": row.get("temperature_c", ""),
        "weather_note": row.get("weather_note", ""),
        "lineups_available": row.get("lineups_available", ""),
        "lineups_count": row.get("lineups_count", ""),
        "provider_error": result.get("provider_error", ""),
    }
    validation["pass_read"] = pass_read(row, actual, internal_correct) if eligible_for_accuracy else ""
    validation["validation_read"] = validation_read(validation)
    return validation


def accuracy(rows: list[dict[str, Any]], correct_key: str) -> float | None:
    scored = [row for row in rows if row.get(correct_key) in {"true", "false"}]
    if not scored:
        return None
    return sum(1 for row in scored if row[correct_key] == "true") / len(scored)


def average(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [safe_float(row.get(key), None) for row in rows if row.get(key) not in ("", None)]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def write_report(rows: list[dict[str, Any]], args: argparse.Namespace, config: dict[str, Any], report_path: Path = REPORT_PATH) -> None:
    final_rows = [row for row in rows if row["is_final"] == "true"]
    eligible_final_rows = [row for row in final_rows if row["eligible_for_accuracy"] == "true"]
    backfill_final_rows = [row for row in final_rows if row["eligible_for_accuracy"] != "true"]
    pending_rows = [row for row in rows if row["is_final"] != "true" and not row.get("provider_error")]
    provider_error_rows = [row for row in rows if row.get("provider_error")]
    scored_public = [row for row in eligible_final_rows if row["v28_pick_scored"] == "true"]
    pass_rows = [row for row in eligible_final_rows if row["v28_tier"] == "Pass"]
    tier_counts = Counter(row["v28_tier"] for row in rows)
    final_tier_counts = Counter(row["v28_tier"] for row in final_rows)
    eligible_tier_counts = Counter(row["v28_tier"] for row in eligible_final_rows)
    pass_reads = Counter(row.get("pass_read", "") for row in pass_rows if row.get("pass_read"))

    lines = [
        "# Matchday Validation v2.10",
        "",
        f"Snapshot source: `{SNAPSHOTS_PATH.relative_to(ROOT)}`",
        "",
        "## Summary",
        "",
        f"- Fixture predictions selected: {len(rows)}.",
        f"- Final fixture statuses found: {len(final_rows)}.",
        f"- Eligible pre-kickoff finals scored: {len(eligible_final_rows)}.",
        f"- Backfill finals not scored: {len(backfill_final_rows)}.",
        f"- Pending/live fixtures: {len(pending_rows)}.",
        f"- Provider errors: {len(provider_error_rows)}.",
        f"- Public pick accuracy: {pct(accuracy(scored_public, 'v28_pick_correct')) or 'not enough finals yet'}.",
        f"- Internal ensemble accuracy: {pct(accuracy(eligible_final_rows, 'internal_pick_correct')) or 'not enough finals yet'}.",
        f"- Average probability assigned to actual result: {pct(average(eligible_final_rows, 'actual_probability')) or 'not enough finals yet'}.",
        f"- Average Brier score: {average(eligible_final_rows, 'brier_score') if eligible_final_rows else 'not enough finals yet'}.",
        f"- Average log loss: {average(eligible_final_rows, 'log_loss') if eligible_final_rows else 'not enough finals yet'}.",
        "",
        "## Tier Counts",
        "",
        "| Tier | Selected | Final | Eligible final | Accuracy when picked |",
        "|---|---:|---:|---:|---:|",
    ]
    for tier in ["Strong Pick", "Model Lean", "Pass"]:
        tier_final_scored = [row for row in eligible_final_rows if row["v28_tier"] == tier and row["v28_pick_scored"] == "true"]
        lines.append(
            f"| {tier} | {tier_counts[tier]} | {final_tier_counts[tier]} | {eligible_tier_counts[tier]} | {pct(accuracy(tier_final_scored, 'v28_pick_correct')) or ''} |"
        )

    lines.extend(
        [
            "",
            "## Pass Reads",
            "",
            f"- Good pass from draw risk: {pass_reads['good_pass_draw_risk']}.",
            f"- Good pass protecting against wrong internal lean: {pass_reads['good_pass_protected_wrong_internal']}.",
            f"- Possible too conservative: {pass_reads['possible_too_conservative']}.",
            f"- Neutral pass: {pass_reads['neutral_pass']}.",
            "",
            "## Fixture Validation",
            "",
            "| Match | Date | Status | Score | Actual | Tier | Pick | Actual prob | Policy | Read |",
            "|---|---|---|---|---|---|---|---:|---|---|",
        ]
    )
    for row in rows:
        match = f"{row['team1']} vs {row['team2']}"
        actual_prob = pct(safe_float(row["actual_probability"], None)) if row.get("actual_probability") != "" else ""
        lines.append(
            f"| {match} | {row['date']} {row['time_et']} | {row['provider_status'] or row['provider_error']} | "
            f"{row['provider_score']} | {row['actual_result']} | {row['v28_tier']} | {row['v28_pick']} | "
            f"{actual_prob} | {row['selected_snapshot_policy']} | {row['validation_read']} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- v2.10 does not change model weights. It measures the v2.9/v2.8 pipeline.",
            "- Accuracy metrics only count fixtures with a pre-kickoff snapshot. Post-match backfills are retained but not scored.",
            "- Exact score is diagnostic only; product confidence is judged on 1/X/2 outcome and pass behavior.",
            "- AET/PEN matches are flagged because the current model is a regulation-result model.",
            "",
            "## API Budget",
            "",
            f"- Used today: {config['api_budget']['used_today']}/{config['api_budget']['daily_limit']}.",
            f"- Remaining before local stop: {config['api_budget']['remaining_before_stop']}.",
        ]
    )
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_date_rows(existing: list[dict[str, str]], fresh: list[dict[str, Any]], date_filter: str) -> list[dict[str, Any]]:
    existing_by_key = {row.get("fixture_key", ""): row for row in existing if row.get("date") == date_filter}
    replacements = {}
    for row in fresh:
        previous = existing_by_key.get(row.get("fixture_key", ""))
        if row.get("provider_error") and previous and not previous.get("provider_error"):
            replacements[row.get("fixture_key", "")] = previous
        else:
            replacements[row.get("fixture_key", "")] = row
    merged = [row for row in existing if row.get("date") != date_filter]
    merged.extend(replacements.values())
    merged.sort(key=lambda row: (row.get("date", ""), row.get("time_et", ""), row.get("team1", "")))
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate v2.9 World Cup matchday predictions.")
    parser.add_argument("--date", default="", help="Optional YYYY-MM-DD fixture date filter.")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--ttl-hours", type=float, default=0.25)
    parser.add_argument("--daily-limit", type=int, default=100)
    parser.add_argument("--reserve-requests", type=int, default=15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot_rows = read_csv(SNAPSHOTS_PATH)
    selected = select_prediction_rows(snapshot_rows, args.date)
    rows = [build_validation_row(row, fetch_result(row, args)) for row in selected]
    fieldnames = [
        "fixture_key",
        "provider_fixture_id",
        "date",
        "time_et",
        "team1",
        "team2",
        "venue",
        "city",
        "snapshot_timestamp_et",
        "selected_snapshot_policy",
        "eligible_for_accuracy",
        "snapshots_seen",
        "provider_status",
        "provider_status_long",
        "provider_home",
        "provider_away",
        "provider_score",
        "is_final",
        "needs_90min_review",
        "actual_result",
        "v28_tier",
        "v28_pick",
        "v28_confidence",
        "v27_internal_ensemble_pick",
        "v28_pick_scored",
        "v28_pick_correct",
        "internal_pick_scored",
        "internal_pick_correct",
        "actual_probability",
        "top_outcome",
        "top_probability",
        "probability_gap",
        "team1_win_probability",
        "draw_probability",
        "team2_win_probability",
        "predicted_score",
        "modal_score",
        "exact_score_correct",
        "brier_score",
        "log_loss",
        "temperature_c",
        "weather_note",
        "lineups_available",
        "lineups_count",
        "pass_read",
        "validation_read",
        "provider_error",
    ]
    validation_path = VALIDATION_PATH
    report_path = REPORT_PATH
    config_path = CONFIG_PATH
    if args.date:
        validation_path = PROCESSED / f"matchday_validation_v210_{args.date}.csv"
        report_path = OUTPUTS / f"matchday_validation_v210_report_{args.date}.md"
        config_path = OUTPUTS / f"matchday_validation_v210_config_{args.date}.json"
    write_csv(validation_path, rows, fieldnames)
    config = {
        **V210_CONFIG,
        "date_filter": args.date,
        "force_refresh": args.force_refresh,
        "ttl_hours": args.ttl_hours,
        "api_budget": budget_snapshot(args.daily_limit, args.reserve_requests),
        "outputs": [
            str(validation_path.relative_to(ROOT)),
            str(report_path.relative_to(ROOT)),
            str(config_path.relative_to(ROOT)),
        ],
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(rows, args, config, report_path)
    if args.date:
        merged_rows = merge_date_rows(read_csv(VALIDATION_PATH), rows, args.date)
        write_csv(VALIDATION_PATH, merged_rows, fieldnames)
        merged_config = {
            **V210_CONFIG,
            "date_filter": "",
            "last_merged_date": args.date,
            "api_budget": config["api_budget"],
            "outputs": [
                str(VALIDATION_PATH.relative_to(ROOT)),
                str(REPORT_PATH.relative_to(ROOT)),
                str(CONFIG_PATH.relative_to(ROOT)),
            ],
        }
        CONFIG_PATH.write_text(json.dumps(merged_config, indent=2), encoding="utf-8")
        write_report(merged_rows, args, merged_config, REPORT_PATH)
    print(
        json.dumps(
            {
                "selected_fixtures": len(rows),
                "final_fixtures": sum(1 for row in rows if row["is_final"] == "true"),
                "eligible_final_fixtures": sum(1 for row in rows if row["is_final"] == "true" and row["eligible_for_accuracy"] == "true"),
                "pending_or_live": sum(1 for row in rows if row["is_final"] != "true" and not row.get("provider_error")),
                "public_pick_accuracy": pct(accuracy([row for row in rows if row["v28_pick_scored"] == "true"], "v28_pick_correct")) or "",
                "report": str(report_path.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
