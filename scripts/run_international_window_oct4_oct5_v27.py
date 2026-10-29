#!/usr/bin/env python3
"""Refresh and audit the international slate for 4-5 October 2026."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import run_ad_hoc_v27_slate as adhoc
import run_international_window_oct2_oct5_v27 as previous
import run_nations_league_slate_v27 as base


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
PREDICTIONS_PATH = PROCESSED / "international_2026_10_04_to_10_05_predictions.csv"
FEATURES_PATH = PROCESSED / "international_2026_10_04_to_10_05_features.csv"
VALIDATION_PATH = PROCESSED / "international_2026_09_27_to_10_03_validation.csv"
REPORT_PATH = OUTPUTS / "international_2026_10_04_to_10_05_report.md"
CONFIG_PATH = OUTPUTS / "international_2026_10_04_to_10_05_config.json"


TODAY_AND_MONDAY = [row for row in previous.TARGET_FIXTURES if row["date"] >= "2026-10-04"]
TODAY_AND_MONDAY.append(
    previous.f(
        "2026-10-04",
        "14:00",
        "Egypt",
        "South Africa",
        "Cairo, Egypt",
        30.069,
        31.312,
        "Cairo International Stadium",
        "International Friendly",
    )
)
TARGET_FIXTURES = TODAY_AND_MONDAY


NEW_RESULTS: dict[tuple[str, str, str], tuple[int, int, str]] = {
    ("2026-10-02", "Kazakhstan", "Moldova"): (1, 2, "UEFA Nations League"),
    ("2026-10-02", "Cyprus", "Armenia"): (2, 0, "UEFA Nations League"),
    ("2026-10-02", "Latvia", "Montenegro"): (1, 2, "UEFA Nations League"),
    ("2026-10-02", "Belgium", "Türkiye"): (3, 0, "UEFA Nations League"),
    ("2026-10-02", "France", "Italy"): (1, 1, "UEFA Nations League"),
    ("2026-10-02", "Hungary", "Georgia"): (1, 0, "UEFA Nations League"),
    ("2026-10-02", "Ukraine", "Northern Ireland"): (0, 3, "UEFA Nations League"),
    ("2026-10-02", "Bosnia & Herzegovina", "Sweden"): (1, 1, "UEFA Nations League"),
    ("2026-10-02", "Poland", "Romania"): (6, 0, "UEFA Nations League"),
    ("2026-10-02", "Faroe Islands", "Slovakia"): (1, 1, "UEFA Nations League"),
    ("2026-10-02", "Colombia", "Paraguay"): (0, 1, "International Friendly"),
    ("2026-10-03", "Finland", "Albania"): (2, 1, "UEFA Nations League"),
    ("2026-10-03", "Croatia", "England"): (0, 7, "UEFA Nations League"),
    ("2026-10-03", "Belarus", "San Marino"): (4, 0, "UEFA Nations League"),
    ("2026-10-03", "Estonia", "Luxembourg"): (1, 0, "UEFA Nations League"),
    ("2026-10-03", "Iceland", "Bulgaria"): (3, 0, "UEFA Nations League"),
    ("2026-10-03", "North Macedonia", "Scotland"): (0, 2, "UEFA Nations League"),
    ("2026-10-03", "Spain", "Czechia"): (3, 1, "UEFA Nations League"),
    ("2026-10-03", "Switzerland", "Slovenia"): (2, 1, "UEFA Nations League"),
    ("2026-10-03", "India", "Brazil"): (0, 4, "International Friendly"),
    ("2026-10-03", "Russia", "Namibia"): (6, 0, "International Friendly"),
    ("2026-10-03", "Canada", "Peru"): (2, 0, "International Friendly"),
    ("2026-10-03", "Ivory Coast", "Cameroon"): (0, 1, "International Friendly"),
    ("2026-10-03", "Argentina", "Burkina Faso"): (7, 0, "International Friendly"),
    ("2026-10-03", "United States", "Mexico"): (3, 0, "International Friendly"),
}


def add_new_results(provider_fixtures: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    for (date, home, away), (home_score, away_score, competition) in NEW_RESULTS.items():
        key = base.fixture_match_key(date, home, away)
        provider_fixtures[key] = {
            "fixture_key": key,
            "provider_fixture_id": "verified-result",
            "provider_status": "FT",
            "provider_status_long": "Match Finished",
            "provider_home": base.model_team_name(home),
            "provider_away": base.model_team_name(away),
            "home_score_90": home_score,
            "away_score_90": away_score,
            "fetched_at": "2026-10-04T10:20:00-04:00",
            "competition": competition,
            "venue": {},
        }


def build_validation() -> tuple[pd.DataFrame, dict[str, Any]]:
    frozen = pd.read_csv(previous.PREDICTIONS_PATH)
    rows: list[dict[str, Any]] = []
    for row in frozen.to_dict("records"):
        key = (str(row["date"]), str(row["team1"]), str(row["team2"]))
        result = NEW_RESULTS.get(key)
        if result is None:
            continue
        rows.append(previous.validation_row(row, result[0], result[1]))

    old_path = PROCESSED / "international_2026_09_27_to_10_01_validation.csv"
    old = pd.read_csv(old_path)
    new = pd.DataFrame(rows)
    validation = pd.concat([old, new], ignore_index=True, sort=False)
    validation.to_csv(VALIDATION_PATH, index=False)
    published = new[new["public_pick_correct"].notna()]
    metrics = {
        "scored_matches": int(len(validation)),
        "raw_top_accuracy": float(validation["internal_top_correct"].mean()),
        "log_loss": float(validation["log_loss"].mean()),
        "brier": float(validation["brier"].mean()),
        "newly_scored_matches": int(len(new)),
        "new_window_raw_accuracy": float(new["internal_top_correct"].mean()),
        "new_window_published": int(len(published)),
        "new_window_published_hits": int(published["public_pick_correct"].sum()),
        "public_ledger_matches": 10 + int(len(published)),
        "public_ledger_hits": 7 + int(published["public_pick_correct"].sum()),
    }
    metrics["public_ledger_accuracy"] = metrics["public_ledger_hits"] / metrics["public_ledger_matches"]
    return validation, metrics


def write_report(
    predictions: list[dict[str, Any]],
    metrics: dict[str, Any],
    applied: int,
    through: str,
    recent_count: int,
) -> None:
    now = datetime.now().astimezone()
    in_play = {"1H", "HT", "2H", "ET", "P", "BT"}
    remaining = [
        row
        for row in predictions
        if row.get("provider_status") not in base.FINAL_PROVIDER_STATUSES | in_play
    ]
    leans = [row for row in remaining if row["v211_tier"] in {"Strong Pick", "Model Lean"}]
    leans.sort(key=lambda row: (row["date"], -base.safe_float(row["v211_top_probability"])))

    lines = [
        "# International Model Report: 4-5 October 2026",
        "",
        f"**Generated:** {now.strftime('%A, %B %-d, %Y at %-I:%M %p %Z')}",
        "",
        "## Accuracy",
        "",
        f"- Frozen public ledger: **{metrics['public_ledger_hits']}/{metrics['public_ledger_matches']} "
        f"({metrics['public_ledger_accuracy'] * 100:.1f}%)**.",
        f"- October 2-3 public calls: **{metrics['new_window_published_hits']}/"
        f"{metrics['new_window_published']}**.",
        f"- All {metrics['scored_matches']} scored 1/X/2 reads: **{metrics['raw_top_accuracy'] * 100:.1f}%** top-outcome accuracy.",
        f"- Log loss {metrics['log_loss']:.3f}; multiclass Brier {metrics['brier']:.3f}.",
        "",
        "## Remaining qualified calls",
        "",
        f"- Strong Picks: **{sum(row['v211_tier'] == 'Strong Pick' for row in remaining)}**. "
        f"Model Leans: **{sum(row['v211_tier'] == 'Model Lean' for row in remaining)}**.",
        "",
        "| Date/time ET | Competition | Match | Pick | 1 | X | 2 | Weather |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in leans:
        temp = row.get("temperature_c", "")
        weather = "Unavailable" if temp in ("", None) else f"{base.safe_float(temp):.1f}C; {row.get('weather_risk', 'low')}"
        lines.append(
            f"| {row['date']} {row['time_et']} | {row['category']} | {row['team1']} vs {row['team2']} | "
            f"**{base.public_pick_name(row)}** ({row['v211_tier']}) | "
            f"{base.safe_float(row['calibrated_team1_win_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_draw_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_team2_win_probability']) * 100:.1f}% | {weather} |"
        )
    if not leans:
        lines.append("| — | — | — | No remaining match clears the gate | — | — | — | — |")

    lines.extend(
        [
            "",
            "## Full remaining slate",
            "",
            "| Date/time ET | Competition | Match | Internal read | 1 | X | 2 | Decision |",
            "|---|---|---|---|---:|---:|---:|---|",
        ]
    )
    for row in remaining:
        decision = "Pass" if row["v211_tier"] == "Pass" else f"{row['v211_tier']}: {base.public_pick_name(row)}"
        lines.append(
            f"| {row['date']} {row['time_et']} | {row['category']} | {row['team1']} vs {row['team2']} | "
            f"{base.internal_read_name(row)} | "
            f"{base.safe_float(row['calibrated_team1_win_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_draw_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_team2_win_probability']) * 100:.1f}% | {decision} |"
        )

    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- Starting XIs remain pending for the noon and later matches at generation time.",
            "- A lineup check may downgrade a lean but cannot create one.",
            "- Exact scores remain hidden. Friendlies remain lower-trust than competitive fixtures.",
            "- This is not a loss-recovery plan; no match is guaranteed.",
            "",
            "## Freshness",
            "",
            f"- Rolling strength rebuilt from {applied:,} results through {through}, including {recent_count} verified/provider overlays.",
            "- Core model: v2.7 calibrated ensemble. Publication filter: v2.11 gate.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    _, metrics = build_validation()
    original_fixtures = list(base.FIXTURES)
    all_fixtures: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in original_fixtures + previous.TARGET_FIXTURES + TARGET_FIXTURES:
        key = base.fixture_match_key(row["date"], row["team1"], row["team2"])
        if key in seen:
            continue
        seen.add(key)
        all_fixtures.append(row)
    base.FIXTURES = all_fixtures

    provider_fixtures = base.cached_provider_fixtures()
    previous.add_verified_results(provider_fixtures)
    add_new_results(provider_fixtures)
    elo_lookup, form_lookup, applied, through, recent_count = base.current_team_lookups(provider_fixtures)
    providers = {row["fixture_key"]: base.provider_overlay(row, provider_fixtures) for row in TARGET_FIXTURES}
    weather = {row["fixture_key"]: adhoc.weather_for_fixture(row, force_refresh=True) for row in TARGET_FIXTURES}

    original_lookup = adhoc.load_lookup
    try:
        def refreshed_lookup(path: Path, key: str, normalize_key: bool = False) -> dict[str, dict[str, Any]]:
            if path.name == "team_elo_latest.csv":
                return elo_lookup
            if path.name == "team_recent_form_latest.csv":
                return form_lookup
            return original_lookup(path, key, normalize_key)

        adhoc.load_lookup = refreshed_lookup
        features = adhoc.build_feature_rows(TARGET_FIXTURES, providers, weather)
    finally:
        adhoc.load_lookup = original_lookup

    predictions = adhoc.build_predictions(TARGET_FIXTURES, providers, weather, features)
    base.add_confidence_gate(predictions)
    fixture_lookup = {row["fixture_key"]: row for row in TARGET_FIXTURES}
    for row in predictions:
        row["category"] = fixture_lookup[row["fixture_key"]]["category"]
    adhoc.write_csv(PREDICTIONS_PATH, predictions, list(predictions[0].keys()))
    adhoc.write_csv(FEATURES_PATH, features, list(features[0].keys()))
    write_report(predictions, metrics, applied, through, recent_count)

    config = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "window": ["2026-10-04", "2026-10-05"],
        "fixtures": TARGET_FIXTURES,
        "historical_results_applied": applied,
        "historical_results_through": through,
        "recent_result_overlays": recent_count,
        "validation_metrics": metrics,
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "fixtures": len(predictions),
        "historical_results_through": through,
        "tiers": {tier: sum(row["v211_tier"] == tier for row in predictions) for tier in ["Strong Pick", "Model Lean", "Pass"]},
        "validation": metrics,
        "report": str(REPORT_PATH),
    }, indent=2))


if __name__ == "__main__":
    main()
