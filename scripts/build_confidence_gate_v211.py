#!/usr/bin/env python3
"""Build the v2.11 confidence-calibration challenger.

V2.11 leaves the v2.7 probability engine untouched. It challenges the v2.8
publishing gate with conservative probability calibration, explicit draw-risk
protection, and lineup verification for Strong Picks.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import build_confidence_gate_v28 as v28


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
ET = ZoneInfo("America/New_York")

HISTORICAL_PATH = PROCESSED / "model_v26_test_predictions.csv"
VALIDATION_PATH = PROCESSED / "matchday_validation_v210.csv"
SNAPSHOTS_PATH = PROCESSED / "worldcup_matchday_v29_snapshots.csv"
SHADOW_PATH = PROCESSED / "confidence_gate_v211_shadow_predictions.csv"
METRICS_PATH = PROCESSED / "confidence_gate_v211_metrics.csv"
CONFIG_PATH = OUTPUTS / "confidence_gate_v211_config.json"
REPORT_PATH = OUTPUTS / "confidence_gate_v211_report.md"

GENERIC_LABELS = ["team1_win", "draw", "team2_win"]
HISTORICAL_LABELS = ["home_win", "draw", "away_win"]

V211_CONFIG = {
    "version": "v2.11",
    "role": "Shadow challenger to v2.8; does not overwrite the production matchday gate.",
    "probability_calibration": {
        "temperature": 1.15,
        "draw_multiplier": 1.10,
        "note": "Softens extreme probabilities and applies a conservative group-stage draw prior.",
    },
    "strong_pick": {
        "minimum_calibrated_top_probability": 0.76,
        "minimum_calibrated_gap": 0.58,
        "maximum_calibrated_draw_probability": 0.18,
        "minimum_xg_margin_when_available": 0.75,
        "minimum_data_quality": 85,
        "requires_ensemble_logistic_consensus": True,
        "requires_confirmed_lineups_live": True,
    },
    "model_lean": {
        "minimum_calibrated_top_probability": 0.60,
        "minimum_calibrated_gap": 0.30,
        "minimum_data_quality": 70,
        "requires_non_draw_direction": True,
    },
    "draw_risk": {
        "minimum_calibrated_draw_probability": 0.26,
        "maximum_xg_margin": 0.65,
        "high_draw_probability_without_xg": 0.34,
    },
    "honesty_note": "The 21 completed live fixtures informed these guardrails and are diagnostic development data, not unbiased v2.11 proof.",
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


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def calibrated_probabilities(probabilities: dict[str, float], labels: list[str]) -> dict[str, float]:
    temperature = V211_CONFIG["probability_calibration"]["temperature"]
    draw_multiplier = V211_CONFIG["probability_calibration"]["draw_multiplier"]
    powered = {}
    for label in labels:
        probability = max(1e-9, probabilities.get(label, 0.0))
        powered[label] = probability ** (1.0 / temperature)
    if "draw" in powered:
        powered["draw"] *= draw_multiplier
    total = sum(powered.values()) or 1.0
    return {label: powered[label] / total for label in labels}


def ordered_outcomes(probabilities: dict[str, float], labels: list[str]) -> list[tuple[str, float]]:
    return sorted(((label, probabilities[label]) for label in labels), key=lambda item: item[1], reverse=True)


def classify_v211(
    *,
    probabilities: dict[str, float],
    labels: list[str],
    ensemble_public: str,
    logistic_public: str,
    internal_pick: str,
    data_quality: float = 100.0,
    lineups_available: bool = False,
    xg_margin: float | None = None,
    live_mode: bool = False,
) -> dict[str, Any]:
    calibrated = calibrated_probabilities(probabilities, labels)
    ranked = ordered_outcomes(calibrated, labels)
    top_pick, top_probability = ranked[0]
    second_probability = ranked[1][1]
    gap = top_probability - second_probability
    draw_probability = calibrated.get("draw", 0.0)
    consensus = (
        ensemble_public
        if ensemble_public and ensemble_public != "pass" and ensemble_public == logistic_public
        else ""
    )

    strong = V211_CONFIG["strong_pick"]
    strong_shape = (
        consensus == top_pick
        and top_pick != "draw"
        and top_probability >= strong["minimum_calibrated_top_probability"]
        and gap >= strong["minimum_calibrated_gap"]
        and draw_probability <= strong["maximum_calibrated_draw_probability"]
        and data_quality >= strong["minimum_data_quality"]
        and (xg_margin is None or xg_margin >= strong["minimum_xg_margin_when_available"])
    )
    if strong_shape and (not live_mode or lineups_available):
        return gate_result(
            "Strong Pick",
            top_pick,
            "High",
            "Consensus survives probability calibration, draw protection, xG separation, and lineup verification.",
            calibrated,
            top_probability,
            gap,
            xg_margin,
            False,
        )

    if live_mode and consensus == top_pick and top_pick != "draw" and not lineups_available:
        return gate_result(
            "Pass",
            "pass",
            "Pass",
            "Consensus favorite is not published before confirmed-lineup verification.",
            calibrated,
            top_probability,
            gap,
            xg_margin,
            False,
        )

    lean = V211_CONFIG["model_lean"]
    if data_quality < lean["minimum_data_quality"]:
        return gate_result(
            "Pass",
            "pass",
            "Pass",
            "Data quality is below the v2.11 directional floor.",
            calibrated,
            top_probability,
            gap,
            xg_margin,
            False,
        )

    draw_risk_rule = V211_CONFIG["draw_risk"]
    close_xg_draw_risk = (
        xg_margin is not None
        and xg_margin <= draw_risk_rule["maximum_xg_margin"]
        and draw_probability >= draw_risk_rule["minimum_calibrated_draw_probability"]
    )
    probability_only_draw_risk = (
        xg_margin is None
        and draw_probability >= draw_risk_rule["high_draw_probability_without_xg"]
    )
    draw_risk = close_xg_draw_risk or probability_only_draw_risk
    if draw_risk:
        return gate_result(
            "Pass",
            "pass",
            "Pass",
            "Draw Watch: calibrated draw risk is high relative to the expected-goal separation.",
            calibrated,
            top_probability,
            gap,
            xg_margin,
            True,
        )

    directional_signal = ensemble_public not in {"", "pass"} or internal_pick == top_pick
    if (
        directional_signal
        and top_pick != "draw"
        and top_probability >= lean["minimum_calibrated_top_probability"]
        and gap >= lean["minimum_calibrated_gap"]
    ):
        return gate_result(
            "Model Lean",
            top_pick,
            "Medium",
            "Directional edge survives probability calibration and draw-risk screening.",
            calibrated,
            top_probability,
            gap,
            xg_margin,
            False,
        )

    return gate_result(
        "Pass",
        "pass",
        "Pass",
        "The calibrated directional edge is below the v2.11 publishing threshold.",
        calibrated,
        top_probability,
        gap,
        xg_margin,
        False,
    )


def gate_result(
    tier: str,
    pick: str,
    confidence: str,
    reason: str,
    probabilities: dict[str, float],
    top_probability: float,
    gap: float,
    xg_margin: float | None,
    draw_watch: bool,
) -> dict[str, Any]:
    return {
        "v211_tier": tier,
        "v211_pick": pick,
        "v211_confidence": confidence,
        "v211_reason": reason,
        "v211_top_probability": round(top_probability, 5),
        "v211_probability_gap": round(gap, 5),
        "v211_calibrated_draw_probability": round(probabilities.get("draw", 0.0), 5),
        "v211_xg_margin": round(xg_margin, 5) if xg_margin is not None else "",
        "v211_draw_watch": draw_watch,
        "v211_calibrated_probabilities": probabilities,
    }


def summarize_tiers(rows: list[dict[str, Any]], tier_key: str, pick_key: str, actual_key: str) -> dict[str, Any]:
    completed = [row for row in rows if row.get(actual_key)]
    picked = [row for row in completed if row.get(pick_key) not in {"", "pass"}]
    by_tier = {}
    for tier in ["Strong Pick", "Model Lean", "Pass"]:
        tier_rows = [row for row in completed if row.get(tier_key) == tier]
        tier_picks = [row for row in tier_rows if row.get(pick_key) not in {"", "pass"}]
        correct = sum(1 for row in tier_picks if row.get(pick_key) == row.get(actual_key))
        by_tier[tier] = {
            "matches": len(tier_rows),
            "picks": len(tier_picks),
            "correct": correct,
            "accuracy": correct / len(tier_picks) if tier_picks else None,
        }
    total_correct = sum(1 for row in picked if row.get(pick_key) == row.get(actual_key))
    return {
        "matches": len(completed),
        "picks": len(picked),
        "correct": total_correct,
        "accuracy": total_correct / len(picked) if picked else None,
        "coverage": len(picked) / len(completed) if completed else 0.0,
        "tiers": by_tier,
    }


def historical_comparison() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    rows = read_csv(HISTORICAL_PATH)
    evaluated = []
    for row in rows:
        probabilities = {
            "home_win": safe_float(row.get("ensemble_home_win_prob")),
            "draw": safe_float(row.get("ensemble_draw_prob")),
            "away_win": safe_float(row.get("ensemble_away_win_prob")),
        }
        raw_ranked = ordered_outcomes(probabilities, HISTORICAL_LABELS)
        v28_gate = v28.classify_gate(
            probabilities=probabilities,
            labels=HISTORICAL_LABELS,
            ensemble_public=row.get("ensemble_public_pick", ""),
            logistic_public=row.get("logistic_regression_public_pick", ""),
            internal_pick=raw_ranked[0][0],
            data_quality=100.0,
        )
        v211_gate = classify_v211(
            probabilities=probabilities,
            labels=HISTORICAL_LABELS,
            ensemble_public=row.get("ensemble_public_pick", ""),
            logistic_public=row.get("logistic_regression_public_pick", ""),
            internal_pick=raw_ranked[0][0],
            data_quality=100.0,
            live_mode=False,
        )
        evaluated.append(
            {
                "actual_result": row.get("actual_result", ""),
                "v28_tier": v28_gate["v28_tier"],
                "v28_pick": v28_gate["v28_pick"],
                "v211_tier": v211_gate["v211_tier"],
                "v211_pick": v211_gate["v211_pick"],
            }
        )
    return evaluated, summarize_tiers(evaluated, "v28_tier", "v28_pick", "actual_result"), summarize_tiers(
        evaluated, "v211_tier", "v211_pick", "actual_result"
    )


def snapshot_lookup() -> dict[tuple[str, str], dict[str, str]]:
    return {
        (row.get("fixture_key", ""), row.get("snapshot_timestamp_et", "")): row
        for row in read_csv(SNAPSHOTS_PATH)
    }


def parse_kickoff(row: dict[str, str]) -> datetime | None:
    try:
        return datetime.fromisoformat(f"{row['date']}T{row['time_et']}:00").replace(tzinfo=ET)
    except (KeyError, ValueError):
        return None


def live_shadow(freeze_time: datetime) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    validation_rows = read_csv(VALIDATION_PATH)
    snapshots = snapshot_lookup()
    out = []
    for row in validation_rows:
        snapshot = snapshots.get((row.get("fixture_key", ""), row.get("snapshot_timestamp_et", "")), {})
        probabilities = {
            "team1_win": safe_float(row.get("team1_win_probability")),
            "draw": safe_float(row.get("draw_probability")),
            "team2_win": safe_float(row.get("team2_win_probability")),
        }
        team1_xg = snapshot.get("team1_xg", "")
        team2_xg = snapshot.get("team2_xg", "")
        xg_margin = None
        if team1_xg not in ("", None) and team2_xg not in ("", None):
            xg_margin = abs(safe_float(team1_xg) - safe_float(team2_xg))
        gate = classify_v211(
            probabilities=probabilities,
            labels=GENERIC_LABELS,
            ensemble_public=snapshot.get("ensemble_public_before_consensus", ""),
            logistic_public=snapshot.get("logistic_public_before_consensus", ""),
            internal_pick=row.get("v27_internal_ensemble_pick", ""),
            data_quality=safe_float(snapshot.get("data_quality_score"), 0.0),
            lineups_available=safe_bool(row.get("lineups_available")),
            xg_margin=xg_margin,
            live_mode=True,
        )
        calibrated = gate.pop("v211_calibrated_probabilities")
        kickoff = parse_kickoff(row)
        shadow_eligible = bool(
            kickoff
            and kickoff > freeze_time
            and row.get("selected_snapshot_policy") == "latest_pre_kickoff"
        )
        out.append(
            {
                "fixture_key": row.get("fixture_key", ""),
                "date": row.get("date", ""),
                "time_et": row.get("time_et", ""),
                "team1": row.get("team1", ""),
                "team2": row.get("team2", ""),
                "provider_status": row.get("provider_status", ""),
                "provider_score": row.get("provider_score", ""),
                "actual_result": row.get("actual_result", ""),
                "eligible_for_accuracy": row.get("eligible_for_accuracy", ""),
                "v211_future_shadow_eligible": shadow_eligible,
                "v28_tier": row.get("v28_tier", ""),
                "v28_pick": row.get("v28_pick", ""),
                **gate,
                "v211_team1_probability": round(calibrated["team1_win"], 5),
                "v211_draw_probability": round(calibrated["draw"], 5),
                "v211_team2_probability": round(calibrated["team2_win"], 5),
                "lineups_available": row.get("lineups_available", ""),
                "data_quality_score": snapshot.get("data_quality_score", ""),
                "team1_xg": team1_xg,
                "team2_xg": team2_xg,
                "snapshot_timestamp_et": row.get("snapshot_timestamp_et", ""),
            }
        )
    eligible_finals = [
        row
        for row in out
        if safe_bool(row.get("eligible_for_accuracy")) and row.get("actual_result")
    ]
    return out, summarize_tiers(eligible_finals, "v28_tier", "v28_pick", "actual_result"), summarize_tiers(
        eligible_finals, "v211_tier", "v211_pick", "actual_result"
    )


def pct(value: float | None) -> str:
    return "" if value is None else f"{value * 100:.2f}%"


def metrics_rows(scope: str, version: str, summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "scope": scope,
            "version": version,
            "tier": "All public picks",
            "matches": summary["matches"],
            "picks": summary["picks"],
            "coverage_pct": round(summary["coverage"] * 100, 2),
            "accuracy_pct": round(summary["accuracy"] * 100, 2) if summary["accuracy"] is not None else "",
        }
    ]
    for tier, tier_summary in summary["tiers"].items():
        rows.append(
            {
                "scope": scope,
                "version": version,
                "tier": tier,
                "matches": tier_summary["matches"],
                "picks": tier_summary["picks"],
                "coverage_pct": round(tier_summary["matches"] / summary["matches"] * 100, 2) if summary["matches"] else 0.0,
                "accuracy_pct": round(tier_summary["accuracy"] * 100, 2) if tier_summary["accuracy"] is not None else "",
            }
        )
    return rows


def write_report(
    freeze_time: datetime,
    historical_v28: dict[str, Any],
    historical_v211: dict[str, Any],
    live_v28: dict[str, Any],
    live_v211: dict[str, Any],
    shadow_rows: list[dict[str, Any]],
) -> None:
    upcoming = [row for row in shadow_rows if not row.get("actual_result")]
    frozen_results = [
        row
        for row in shadow_rows
        if row.get("actual_result") and safe_bool(row.get("v211_future_shadow_eligible"))
    ]
    frozen_v28 = summarize_tiers(frozen_results, "v28_tier", "v28_pick", "actual_result")
    frozen_v211 = summarize_tiers(frozen_results, "v211_tier", "v211_pick", "actual_result")
    changes = [row for row in shadow_rows if row.get("actual_result") and row.get("v28_tier") != row.get("v211_tier")]
    lines = [
        "# Confidence Gate v2.11",
        "",
        f"Frozen for shadow evaluation: {freeze_time.isoformat(timespec='seconds')}",
        "",
        "V2.11 is a challenger publishing layer. It does not retrain or replace the v2.7 probability ensemble.",
        "",
        "## What Changed",
        "",
        "- Extreme probabilities are softened with temperature scaling and a small group-stage draw uplift.",
        "- Strong Pick now requires calibrated separation, low draw risk, xG separation, high data quality, and confirmed live lineups.",
        "- Model Lean must survive an explicit draw-risk screen.",
        "- V2.8 remains the baseline while v2.11 runs in shadow mode.",
        "",
        "## Historical Holdout Comparison",
        "",
        "| Version | Matches | Public picks | Coverage | Accuracy | Strong accuracy | Lean accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|",
        comparison_line("v2.8", historical_v28),
        comparison_line("v2.11", historical_v211),
        "",
        "## Current World Cup Diagnostic",
        "",
        "These completed matches informed v2.11, so this is an in-sample diagnostic rather than production proof.",
        "",
        "| Version | Genuine finals | Public picks | Coverage | Accuracy | Strong accuracy | Lean accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|",
        comparison_line("v2.8", live_v28),
        comparison_line("v2.11", live_v211),
        "",
        "## Frozen Shadow Results",
        "",
        "Only fixtures that kicked off after the original v2.11 freeze enter this unbiased challenger comparison.",
        "",
        "| Version | Frozen finals | Public picks | Coverage | Accuracy |",
        "|---|---:|---:|---:|---:|",
        shadow_comparison_line("v2.8", frozen_v28),
        shadow_comparison_line("v2.11", frozen_v211),
        "",
        "| Match | Actual | v2.8 | v2.11 |",
        "|---|---|---|---|",
    ]
    for row in frozen_results:
        lines.append(
            f"| {row['team1']} vs {row['team2']} | {row['provider_score']} ({row['actual_result']}) | "
            f"{row['v28_tier']}: {row['v28_pick']} | {row['v211_tier']}: {row['v211_pick']} |"
        )
    if not frozen_results:
        lines.append("| None yet |  |  |  |")
    lines.extend(
        [
        "",
        "## Upcoming Shadow Slate",
        "",
        "| Match | Kickoff ET | v2.8 | v2.11 | Calibrated 1/X/2 | Reason |",
        "|---|---:|---|---|---|---|",
        ]
    )
    for row in upcoming:
        match = f"{row['team1']} vs {row['team2']}"
        old_call = f"{row['v28_tier']}: {row['v28_pick']}"
        new_call = f"{row['v211_tier']}: {row['v211_pick']}"
        probs = f"{safe_float(row['v211_team1_probability']) * 100:.1f}/{safe_float(row['v211_draw_probability']) * 100:.1f}/{safe_float(row['v211_team2_probability']) * 100:.1f}"
        lines.append(f"| {match} | {row['date']} {row['time_et']} | {old_call} | {new_call} | {probs} | {row['v211_reason']} |")
    lines.extend(
        [
            "",
            "## Diagnostic Tier Changes",
            "",
            f"- Completed genuine/backfill rows with a changed tier: {len(changes)}.",
            f"- Future fixtures frozen for unbiased v2.11 shadow evaluation: {sum(1 for row in upcoming if safe_bool(row['v211_future_shadow_eligible']))}.",
            "",
            "## Production Rule",
            "",
            "Do not promote v2.11 from shadow mode based on the improved diagnostic score. Its rules were designed after observing the current World Cup sample. Promotion requires future, untouched results and comparison against v2.8 on the same fixtures.",
        ]
    )
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def comparison_line(version: str, summary: dict[str, Any]) -> str:
    strong = summary["tiers"]["Strong Pick"]["accuracy"]
    lean = summary["tiers"]["Model Lean"]["accuracy"]
    return (
        f"| {version} | {summary['matches']} | {summary['picks']} | {pct(summary['coverage'])} | "
        f"{pct(summary['accuracy'])} | {pct(strong)} | {pct(lean)} |"
    )


def shadow_comparison_line(version: str, summary: dict[str, Any]) -> str:
    return (
        f"| {version} | {summary['matches']} | {summary['picks']} | "
        f"{pct(summary['coverage'])} | {pct(summary['accuracy'])} |"
    )


def frozen_shadow_start() -> datetime:
    if CONFIG_PATH.exists():
        try:
            existing = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            value = existing.get("freeze_timestamp_et", "")
            if existing.get("version") == "v2.11" and value:
                parsed = datetime.fromisoformat(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=ET)
        except (json.JSONDecodeError, ValueError):
            pass
    return datetime.now(ET)


def main() -> None:
    freeze_time = frozen_shadow_start()
    _historical_rows, historical_v28, historical_v211 = historical_comparison()
    shadow_rows, live_v28, live_v211 = live_shadow(freeze_time)
    write_csv(
        SHADOW_PATH,
        shadow_rows,
        [
            "fixture_key",
            "date",
            "time_et",
            "team1",
            "team2",
            "provider_status",
            "provider_score",
            "actual_result",
            "eligible_for_accuracy",
            "v211_future_shadow_eligible",
            "v28_tier",
            "v28_pick",
            "v211_tier",
            "v211_pick",
            "v211_confidence",
            "v211_reason",
            "v211_top_probability",
            "v211_probability_gap",
            "v211_calibrated_draw_probability",
            "v211_xg_margin",
            "v211_draw_watch",
            "v211_team1_probability",
            "v211_draw_probability",
            "v211_team2_probability",
            "lineups_available",
            "data_quality_score",
            "team1_xg",
            "team2_xg",
            "snapshot_timestamp_et",
        ],
    )
    metrics = []
    metrics.extend(metrics_rows("historical_holdout", "v2.8", historical_v28))
    metrics.extend(metrics_rows("historical_holdout", "v2.11", historical_v211))
    metrics.extend(metrics_rows("world_cup_development", "v2.8", live_v28))
    metrics.extend(metrics_rows("world_cup_development", "v2.11", live_v211))
    write_csv(METRICS_PATH, metrics, ["scope", "version", "tier", "matches", "picks", "coverage_pct", "accuracy_pct"])
    config = {
        **V211_CONFIG,
        "freeze_timestamp_et": freeze_time.isoformat(timespec="seconds"),
        "inputs": [str(HISTORICAL_PATH.relative_to(ROOT)), str(VALIDATION_PATH.relative_to(ROOT)), str(SNAPSHOTS_PATH.relative_to(ROOT))],
        "outputs": [str(SHADOW_PATH.relative_to(ROOT)), str(METRICS_PATH.relative_to(ROOT)), str(REPORT_PATH.relative_to(ROOT))],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(freeze_time, historical_v28, historical_v211, live_v28, live_v211, shadow_rows)
    print(
        json.dumps(
            {
                "historical_v211_accuracy": pct(historical_v211["accuracy"]),
                "historical_v211_coverage": pct(historical_v211["coverage"]),
                "world_cup_diagnostic_accuracy": pct(live_v211["accuracy"]),
                "world_cup_diagnostic_coverage": pct(live_v211["coverage"]),
                "future_shadow_fixtures": sum(1 for row in shadow_rows if safe_bool(row["v211_future_shadow_eligible"])),
                "tiers": dict(Counter(row["v211_tier"] for row in shadow_rows if not row.get("actual_result"))),
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
