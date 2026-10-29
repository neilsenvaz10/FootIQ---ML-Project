#!/usr/bin/env python3
"""Build v2.8 confidence gate outputs.

V2.8 does not change the v2.7 prediction model. It changes the product layer:
instead of only "pick" or "pass", it publishes three tiers:
- Strong Pick
- Model Lean
- Pass
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

CONFIG_PATH = OUTPUTS / "confidence_gate_v28_config.json"
REPORT_PATH = OUTPUTS / "confidence_gate_v28_report.md"
HISTORICAL_METRICS_PATH = PROCESSED / "confidence_gate_v28_historical_metrics.csv"
LIVE_PATH = PROCESSED / "v28_live_public_picks.csv"
ADHOC_PATH = PROCESSED / "ad_hoc_v28_june10_predictions.csv"
KNOWN_VALIDATION_PATH = PROCESSED / "v28_known_fixture_validation.csv"

OUTCOME_LABELS = ["team1_win", "draw", "team2_win"]
V26_LABELS = ["home_win", "draw", "away_win"]

V28_CONFIG = {
    "version": "v2.8",
    "purpose": "Confidence-gate calibration for v2.7 predictions.",
    "base_model": "v2.7 calibrated ensemble; no model retraining.",
    "tiers": {
        "Strong Pick": "Ensemble and logistic public gates agree on the same non-pass outcome.",
        "Model Lean": "Ensemble has a usable directional signal, but the logistic safety layer blocks a strong public pick.",
        "Pass": "Signal is too close, too draw-heavy, or data quality is too weak.",
    },
    "rules": {
        "strong_pick": {
            "requires_consensus_non_pass": True,
        },
        "model_lean": {
            "ensemble_public_non_pass": True,
            "or_non_draw_top_probability_min": 0.60,
            "or_non_draw_top_gap_min": 0.18,
            "or_draw_probability_min": 0.38,
            "or_draw_gap_min": 0.03,
            "minimum_data_quality": 50,
        },
        "pass": {
            "default": True,
        },
    },
    "calibration_source": "data/processed/model_v26_test_predictions.csv",
    "note": "Model Lean is intentionally not marketed as a high-confidence pick.",
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


def pct(value: float) -> float:
    return round(100.0 * value, 2)


def outcome_from_probs(probs: list[float], labels: list[str]) -> tuple[str, float, float, float]:
    indexed = list(enumerate(probs))
    indexed.sort(key=lambda item: item[1], reverse=True)
    top_idx, top_prob = indexed[0]
    second_prob = indexed[1][1]
    return labels[top_idx], top_prob, second_prob, top_prob - second_prob


def strong_pick_from_consensus(ensemble_public: str, logistic_public: str) -> str:
    if ensemble_public and ensemble_public != "pass" and ensemble_public == logistic_public:
        return ensemble_public
    return ""


def classify_gate(
    *,
    probabilities: dict[str, float],
    labels: list[str],
    ensemble_public: str,
    logistic_public: str,
    internal_pick: str = "",
    data_quality: float = 100.0,
) -> dict[str, Any]:
    probs = [probabilities[label] for label in labels]
    top_pick, top_prob, second_prob, gap = outcome_from_probs(probs, labels)
    internal_pick = internal_pick or top_pick
    strong_pick = strong_pick_from_consensus(ensemble_public, logistic_public)

    if strong_pick:
        return {
            "v28_tier": "Strong Pick",
            "v28_pick": strong_pick,
            "v28_confidence": "High" if top_prob >= 0.66 else "Medium-high",
            "v28_reason": "Ensemble and logistic safety gate agree on the same public outcome.",
            "top_probability": round(top_prob, 5),
            "probability_gap": round(gap, 5),
        }

    if data_quality < V28_CONFIG["rules"]["model_lean"]["minimum_data_quality"]:
        return {
            "v28_tier": "Pass",
            "v28_pick": "pass",
            "v28_confidence": "Pass",
            "v28_reason": "Data quality is below the v2.8 model-lean floor.",
            "top_probability": round(top_prob, 5),
            "probability_gap": round(gap, 5),
        }

    draw_prob = probabilities.get("draw", 0.0)
    model_lean_pick = ""
    if ensemble_public and ensemble_public != "pass" and internal_pick != "draw":
        model_lean_pick = internal_pick
    elif internal_pick != "draw" and top_prob >= 0.60 and gap >= 0.18:
        model_lean_pick = internal_pick
    elif internal_pick == "draw" and top_prob >= 0.38 and gap >= 0.03:
        model_lean_pick = "draw"

    if model_lean_pick:
        if model_lean_pick == "draw":
            reason = "Draw is the ensemble's top outcome with enough separation to publish as a lean."
            confidence = "Low-medium"
        elif top_prob >= 0.64:
            reason = "Ensemble has a strong directional lean, but logistic safety blocks a strong pick."
            confidence = "Medium"
        else:
            reason = "Ensemble clears the model-lean bar, but logistic safety flags enough risk to avoid a strong pick."
            confidence = "Medium-low"
        return {
            "v28_tier": "Model Lean",
            "v28_pick": model_lean_pick,
            "v28_confidence": confidence,
            "v28_reason": reason,
            "top_probability": round(top_prob, 5),
            "probability_gap": round(gap, 5),
        }

    return {
        "v28_tier": "Pass",
        "v28_pick": "pass",
        "v28_confidence": "Pass",
        "v28_reason": f"Top probability is {top_prob:.1%} with draw probability {draw_prob:.1%}; edge is not clean enough.",
        "top_probability": round(top_prob, 5),
        "probability_gap": round(gap, 5),
    }


def v26_probabilities(row: dict[str, str]) -> dict[str, float]:
    return {
        "home_win": safe_float(row.get("ensemble_home_win_prob")),
        "draw": safe_float(row.get("ensemble_draw_prob")),
        "away_win": safe_float(row.get("ensemble_away_win_prob")),
    }


def convert_v26_pick_to_generic(pick: str) -> str:
    return {"home_win": "team1_win", "away_win": "team2_win"}.get(pick, pick)


def evaluate_historical_gate() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = read_csv(PROCESSED / "model_v26_test_predictions.csv")
    evaluated = []
    counts: Counter[str] = Counter()
    correct: Counter[str] = Counter()
    bucket_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for row in rows:
        probs = v26_probabilities(row)
        top_pick, _, _, _ = outcome_from_probs([probs[label] for label in V26_LABELS], V26_LABELS)
        gate = classify_gate(
            probabilities=probs,
            labels=V26_LABELS,
            ensemble_public=row.get("ensemble_public_pick", ""),
            logistic_public=row.get("logistic_regression_public_pick", ""),
            internal_pick=top_pick,
            data_quality=100.0,
        )
        actual = row["actual_result"]
        pick = gate["v28_pick"]
        scored = pick != "pass"
        is_correct = actual == pick if scored else ""
        counts[gate["v28_tier"]] += 1
        if scored and is_correct:
            correct[gate["v28_tier"]] += 1
        bucket_key = (gate["v28_tier"], row.get("tournament_bucket", ""))
        bucket_counts[bucket_key]["n"] += 1
        if scored and is_correct:
            bucket_counts[bucket_key]["correct"] += 1
        evaluated.append(
            {
                "source": "v26_test",
                "date": row["date"],
                "match": f"{row['home_team']} vs {row['away_team']}",
                "tournament_bucket": row.get("tournament_bucket", ""),
                "actual_result": actual,
                "v28_tier": gate["v28_tier"],
                "v28_pick": pick,
                "v28_correct": is_correct,
                "top_probability": gate["top_probability"],
                "probability_gap": gate["probability_gap"],
            }
        )

    metrics = []
    total = len(rows)
    for tier in ["Strong Pick", "Model Lean", "Pass"]:
        n = counts[tier]
        metrics.append(
            {
                "scope": "historical_v26_test",
                "tier": tier,
                "bucket": "all",
                "matches": n,
                "coverage_pct": pct(n / total) if total else 0.0,
                "accuracy_pct": pct(correct[tier] / n) if n and tier != "Pass" else "",
            }
        )
    for (tier, bucket), counter in sorted(bucket_counts.items()):
        n = counter["n"]
        if tier == "Pass":
            continue
        metrics.append(
            {
                "scope": "historical_v26_test",
                "tier": tier,
                "bucket": bucket,
                "matches": n,
                "coverage_pct": pct(n / total) if total else 0.0,
                "accuracy_pct": pct(counter["correct"] / n) if n else "",
            }
        )
    summary = {
        "historical_total": total,
        "historical_counts": dict(counts),
        "historical_correct": dict(correct),
    }
    return metrics, summary


def classify_live_row(row: dict[str, str]) -> dict[str, Any]:
    probs = {
        "team1_win": safe_float(row.get("team1_win_probability")),
        "draw": safe_float(row.get("draw_probability")),
        "team2_win": safe_float(row.get("team2_win_probability")),
    }
    return classify_gate(
        probabilities=probs,
        labels=OUTCOME_LABELS,
        ensemble_public=row.get("ensemble_public_pick_before_consensus") or row.get("ensemble_public_before_consensus", ""),
        logistic_public=row.get("logistic_public_pick_before_consensus") or row.get("logistic_public_before_consensus", ""),
        internal_pick=row.get("internal_ensemble_pick") or row.get("v27_internal_ensemble_pick", ""),
        data_quality=safe_float(row.get("data_quality_score"), 100.0),
    )


def decorate_live_predictions(input_path: Path, output_path: Path, source_name: str) -> list[dict[str, Any]]:
    rows = read_csv(input_path)
    out = []
    for row in rows:
        gate = classify_live_row(row)
        out.append(
            {
                **row,
                "v28_tier": gate["v28_tier"],
                "v28_pick": gate["v28_pick"],
                "v28_confidence": gate["v28_confidence"],
                "v28_reason": gate["v28_reason"],
                "v28_top_probability": gate["top_probability"],
                "v28_probability_gap": gate["probability_gap"],
                "v28_source": source_name,
            }
        )
    if out:
        fieldnames = list(out[0].keys())
        write_csv(output_path, out, fieldnames)
    return out


def validate_known_live(v28_live_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    predictions_by_key = {row["fixture_key"]: row for row in v28_live_rows}
    validation = read_csv(PROCESSED / "v27_known_fixture_validation.csv")
    out = []
    for row in validation:
        pred = predictions_by_key.get(row["fixture_key"], {})
        actual = row.get("actual_result", "")
        v28_pick = pred.get("v28_pick", "pass")
        scored = bool(actual and v28_pick != "pass")
        out.append(
            {
                **row,
                "v28_tier": pred.get("v28_tier", ""),
                "v28_pick": v28_pick,
                "v28_confidence": pred.get("v28_confidence", ""),
                "v28_scored": scored,
                "v28_correct": actual == v28_pick if scored else "",
                "v28_reason": pred.get("v28_reason", ""),
            }
        )
    if out:
        write_csv(KNOWN_VALIDATION_PATH, out, list(out[0].keys()))
    return out


def known_metrics(validation_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    final_rows = [row for row in validation_rows if row.get("actual_result")]
    by_tier: dict[str, Counter[str]] = defaultdict(Counter)
    for row in final_rows:
        tier = row.get("v28_tier", "Pass")
        by_tier[tier]["n"] += 1
        if safe_bool(row.get("v28_correct")):
            by_tier[tier]["correct"] += 1
    metrics = []
    total = len(final_rows)
    for tier in ["Strong Pick", "Model Lean", "Pass"]:
        n = by_tier[tier]["n"]
        metrics.append(
            {
                "scope": "known_live_validation",
                "tier": tier,
                "bucket": "all",
                "matches": n,
                "coverage_pct": pct(n / total) if total else 0.0,
                "accuracy_pct": pct(by_tier[tier]["correct"] / n) if n and tier != "Pass" else "",
            }
        )
    return metrics


def write_report(
    metrics: list[dict[str, Any]],
    v28_live: list[dict[str, Any]],
    v28_adhoc: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
) -> None:
    historical = [row for row in metrics if row["scope"] == "historical_v26_test" and row["bucket"] == "all"]
    known = [row for row in metrics if row["scope"] == "known_live_validation"]
    lines = [
        "# Confidence Gate v2.8",
        "",
        "V2.8 is a product confidence upgrade on top of v2.7. It does not retrain the prediction model.",
        "",
        "## Tiers",
        "",
        "| Tier | Meaning |",
        "|---|---|",
        "| Strong Pick | Ensemble and logistic safety gate agree. |",
        "| Model Lean | Ensemble has a usable signal, but the safety gate blocks a strong call. |",
        "| Pass | Edge is too weak, too draw-heavy, or data quality is too low. |",
        "",
        "## Historical Calibration",
        "",
        "| Tier | Matches | Coverage | Accuracy |",
        "|---|---:|---:|---:|",
    ]
    for row in historical:
        acc = f"{row['accuracy_pct']}%" if row["accuracy_pct"] != "" else ""
        lines.append(f"| {row['tier']} | {row['matches']} | {row['coverage_pct']}% | {acc} |")
    lines.extend(
        [
            "",
            "## Known Live Validation",
            "",
            "| Tier | Matches | Coverage | Accuracy |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in known:
        acc = f"{row['accuracy_pct']}%" if row["accuracy_pct"] != "" else ""
        lines.append(f"| {row['tier']} | {row['matches']} | {row['coverage_pct']}% | {acc} |")
    lines.extend(
        [
            "",
            "## Current v2.8 Live Labels",
            "",
            "| Match | v2.7 public | v2.8 tier | v2.8 pick | Top prob |",
            "|---|---|---|---|---:|",
        ]
    )
    for row in v28_live:
        match = f"{row.get('team1', '')} vs {row.get('team2', '')}"
        lines.append(
            f"| {match} | {row.get('public_pick', '')} | {row['v28_tier']} | {row['v28_pick']} | {safe_float(row['v28_top_probability']) * 100:.2f}% |"
        )
    if v28_adhoc:
        lines.extend(
            [
                "",
                "## Ad Hoc June 10 Slate With v2.8",
                "",
                "| Match | v2.8 tier | v2.8 pick | v2.7 internal | Predicted score |",
                "|---|---|---|---|---|",
            ]
        )
        for row in v28_adhoc:
            match = f"{row.get('team1', '')} vs {row.get('team2', '')}"
            lines.append(
                f"| {match} | {row['v28_tier']} | {row['v28_pick']} | {row.get('v27_internal_ensemble_pick', '')} | {row.get('predicted_score', '')} |"
            )
    lines.extend(
        [
            "",
            "## Honest Read",
            "",
            "Strong Pick is the product-grade call. Model Lean is useful but should be shown with softer language because its historical accuracy is much closer to a directional edge than a locked pick. This solves the v2.7 problem where useful ensemble signals were hidden behind Pass.",
        ]
    )
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    metrics, _summary = evaluate_historical_gate()
    v28_live = decorate_live_predictions(PROCESSED / "v27_live_public_picks.csv", LIVE_PATH, "v27_live")
    v28_adhoc = decorate_live_predictions(PROCESSED / "ad_hoc_v27_june10_predictions.csv", ADHOC_PATH, "ad_hoc_june10")
    validation_rows = validate_known_live(v28_live)
    metrics.extend(known_metrics(validation_rows))
    write_csv(
        HISTORICAL_METRICS_PATH,
        metrics,
        ["scope", "tier", "bucket", "matches", "coverage_pct", "accuracy_pct"],
    )
    config = dict(V28_CONFIG)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    write_report(metrics, v28_live, v28_adhoc, validation_rows)
    tier_counts = Counter(row["v28_tier"] for row in v28_live)
    print(
        json.dumps(
            {
                "v28_live_tiers": dict(tier_counts),
                "metrics": str(HISTORICAL_METRICS_PATH.relative_to(ROOT)),
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
