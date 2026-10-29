#!/usr/bin/env python3
"""Refresh the international slate from 2-5 October 2026.

The fitted v2.7 ensemble and v2.11 publication gate remain frozen.  This
runner adds verified results through 1 October to the rolling Elo/form state,
refreshes venue weather, and preserves the previous forecast for auditing.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import run_ad_hoc_v27_slate as adhoc
import run_international_window_sep29_oct5_v27 as previous
import run_nations_league_slate_v27 as base


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
PREDICTIONS_PATH = PROCESSED / "international_2026_10_02_to_10_05_predictions.csv"
FEATURES_PATH = PROCESSED / "international_2026_10_02_to_10_05_features.csv"
VALIDATION_PATH = PROCESSED / "international_2026_09_27_to_10_01_validation.csv"
REPORT_PATH = OUTPUTS / "international_2026_10_02_to_10_05_report.md"
CONFIG_PATH = OUTPUTS / "international_2026_10_02_to_10_05_config.json"


def f(
    date: str,
    time_et: str,
    team1: str,
    team2: str,
    city: str,
    latitude: float | str,
    longitude: float | str,
    venue: str,
    competition: str = "International Friendly",
    venue_edge_team: str | None = None,
) -> dict[str, Any]:
    return previous.f(
        date,
        time_et,
        team1,
        team2,
        city,
        latitude,
        longitude,
        venue,
        competition,
        venue_edge_team,
    )


UEFA_FIXTURES = [row for row in previous.TARGET_FIXTURES if row["date"] >= "2026-10-02"]

# Senior friendlies verified in the live provider. Youth and club friendlies
# are deliberately excluded because this model was not trained for them.
FRIENDLIES = [
    f(
        "2026-10-02",
        "20:00",
        "Colombia",
        "Paraguay",
        "Harrison, NJ",
        40.736,
        -74.150,
        "Sports Illustrated Stadium",
        venue_edge_team="",
    ),
    f(
        "2026-10-03",
        "10:00",
        "India",
        "Brazil",
        "Kolkata, India",
        22.568,
        88.409,
        "Vivekananda Yuba Bharati Krirangan",
    ),
    f(
        "2026-10-03",
        "11:00",
        "Russia",
        "Namibia",
        "Yekaterinburg, Russia",
        56.832,
        60.573,
        "Ekaterinburg Arena",
    ),
    f(
        "2026-10-03",
        "14:00",
        "Canada",
        "Peru",
        "Montreal, Canada",
        45.563,
        -73.552,
        "Stade Saputo",
    ),
    f(
        "2026-10-03",
        "15:00",
        "Ivory Coast",
        "Cameroon",
        "",
        "",
        "",
        "Venue not published in provider feed",
        venue_edge_team="",
    ),
    f(
        "2026-10-03",
        "20:00",
        "Argentina",
        "Burkina Faso",
        "Buenos Aires, Argentina",
        -34.545,
        -58.449,
        "Estadio Monumental",
    ),
    f(
        "2026-10-03",
        "22:00",
        "United States",
        "Mexico",
        "Glendale, AZ",
        33.528,
        -112.263,
        "State Farm Stadium",
        venue_edge_team="",
    ),
]

TARGET_FIXTURES = UEFA_FIXTURES + FRIENDLIES


VERIFIED_RESULTS: dict[tuple[str, str, str], tuple[int, int, str]] = {
    ("2026-09-29", "Finland", "Belarus"): (0, 0, "UEFA Nations League"),
    ("2026-09-29", "Moldova", "Faroe Islands"): (1, 1, "UEFA Nations League"),
    ("2026-09-29", "Czechia", "England"): (0, 2, "UEFA Nations League"),
    ("2026-09-29", "Spain", "Croatia"): (4, 1, "UEFA Nations League"),
    ("2026-09-29", "Scotland", "Switzerland"): (0, 3, "UEFA Nations League"),
    ("2026-09-29", "Slovenia", "North Macedonia"): (2, 0, "UEFA Nations League"),
    ("2026-09-29", "San Marino", "Albania"): (0, 3, "UEFA Nations League"),
    ("2026-09-29", "Slovakia", "Kazakhstan"): (2, 1, "UEFA Nations League"),
    ("2026-09-29", "Bulgaria", "Estonia"): (0, 0, "UEFA Nations League"),
    ("2026-09-29", "Luxembourg", "Iceland"): (0, 3, "UEFA Nations League"),
    ("2026-09-29", "Russia", "Iran"): (2, 0, "International Friendly"),
    ("2026-09-29", "United States", "Chile"): (4, 2, "International Friendly"),
    ("2026-09-29", "Mexico", "Peru"): (1, 1, "International Friendly"),
    ("2026-09-30", "Lithuania", "Andorra"): (3, 0, "International Friendly"),
    ("2026-10-01", "Azerbaijan", "Liechtenstein"): (0, 0, "UEFA Nations League"),
    ("2026-10-01", "Germany", "Serbia"): (2, 0, "UEFA Nations League"),
    ("2026-10-01", "Greece", "Netherlands"): (2, 2, "UEFA Nations League"),
    ("2026-10-01", "Denmark", "Portugal"): (2, 4, "UEFA Nations League"),
    ("2026-10-01", "Wales", "Norway"): (2, 1, "UEFA Nations League"),
    ("2026-10-01", "Israel", "Kosovo"): (0, 0, "UEFA Nations League"),
    ("2026-10-01", "Republic of Ireland", "Austria"): (2, 2, "UEFA Nations League"),
    ("2026-10-01", "Malta", "Gibraltar"): (1, 1, "UEFA Nations League"),
}


def add_verified_results(provider_fixtures: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    for (date, home, away), (home_score, away_score, competition) in VERIFIED_RESULTS.items():
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
            "fetched_at": "2026-10-02T11:30:00-04:00",
            "competition": competition,
            "venue": {},
        }


def result_label(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "team1_win"
    if home_score < away_score:
        return "team2_win"
    return "draw"


def validation_row(row: dict[str, Any], home_score: int, away_score: int) -> dict[str, Any]:
    actual = result_label(home_score, away_score)
    probabilities = [
        base.safe_float(row["calibrated_team1_win_probability"]),
        base.safe_float(row["calibrated_draw_probability"]),
        base.safe_float(row["calibrated_team2_win_probability"]),
    ]
    labels = ["team1_win", "draw", "team2_win"]
    actual_index = labels.index(actual)
    internal_index = max(range(3), key=lambda index: probabilities[index])
    published = row["v211_tier"] != "Pass" and row["v211_pick"] != "pass"
    return {
        "date": row["date"],
        "category": row["category"],
        "team1": row["team1"],
        "team2": row["team2"],
        "score": f"{home_score}-{away_score}",
        "tier": row["v211_tier"],
        "public_pick": row["v211_pick"],
        "actual": actual,
        "public_pick_correct": (row["v211_pick"] == actual) if published else None,
        "internal_top_correct": internal_index == actual_index,
        "log_loss": -math.log(max(probabilities[actual_index], 1e-15)),
        "brier": sum(
            (probabilities[index] - (1 if index == actual_index else 0)) ** 2
            for index in range(3)
        ),
    }


def build_validation() -> tuple[pd.DataFrame, dict[str, Any]]:
    prior = pd.read_csv(previous.PREDICTIONS_PATH)
    new_rows: list[dict[str, Any]] = []
    for row in prior.to_dict("records"):
        key = (str(row["date"]), str(row["team1"]), str(row["team2"]))
        result = VERIFIED_RESULTS.get(key)
        if result is None:
            continue
        new_rows.append(validation_row(row, result[0], result[1]))

    old_path = PROCESSED / "international_2026_09_27_28_validation.csv"
    old = pd.read_csv(old_path) if old_path.exists() else pd.DataFrame()
    new = pd.DataFrame(new_rows)
    validation = pd.concat([old, new], ignore_index=True, sort=False)
    validation.to_csv(VALIDATION_PATH, index=False)

    published_new = new[new["public_pick_correct"].notna()]
    metrics = {
        "scored_matches": int(len(validation)),
        "raw_top_accuracy": float(validation["internal_top_correct"].mean()),
        "log_loss": float(validation["log_loss"].mean()),
        "brier": float(validation["brier"].mean()),
        "newly_scored_matches": int(len(new)),
        "new_window_raw_accuracy": float(new["internal_top_correct"].mean()),
        "new_window_published": int(len(published_new)),
        "new_window_published_hits": int(published_new["public_pick_correct"].sum()),
        # The prior public ledger was 4/5 through 28 September.
        "public_ledger_matches": 5 + int(len(published_new)),
        "public_ledger_hits": 4 + int(published_new["public_pick_correct"].sum()),
    }
    metrics["public_ledger_accuracy"] = metrics["public_ledger_hits"] / metrics["public_ledger_matches"]
    return validation, metrics


def display_pick(row: dict[str, Any]) -> str:
    return base.public_pick_name(row)


def write_report(
    predictions: list[dict[str, Any]],
    metrics: dict[str, Any],
    applied: int,
    through: str,
    recent_count: int,
) -> None:
    now = datetime.now().astimezone()
    remaining = [
        row
        for row in predictions
        if row.get("provider_status") not in base.FINAL_PROVIDER_STATUSES | {"1H", "HT", "2H", "ET", "P", "BT"}
    ]
    leans = [row for row in remaining if row["v211_tier"] in {"Strong Pick", "Model Lean"}]
    leans.sort(key=lambda row: (row["date"], -base.safe_float(row["v211_top_probability"])))

    lines = [
        "# International Model Report: 2-5 October 2026",
        "",
        f"**Generated:** {now.strftime('%A, %B %-d, %Y at %-I:%M %p %Z')}",
        "",
        "## Accuracy audit",
        "",
        f"- Frozen public ledger: **{metrics['public_ledger_hits']}/{metrics['public_ledger_matches']} "
        f"({metrics['public_ledger_accuracy'] * 100:.1f}%)**.",
        f"- Newly completed Sep 29-Oct 1 public calls: **{metrics['new_window_published_hits']}/"
        f"{metrics['new_window_published']}**.",
        f"- Across {metrics['scored_matches']} recently scored fixtures, raw top-outcome accuracy is "
        f"**{metrics['raw_top_accuracy'] * 100:.1f}%**.",
        f"- Probability quality: log loss {metrics['log_loss']:.3f}; multiclass Brier {metrics['brier']:.3f}. "
        "Uniform baselines are 1.099 and 0.667.",
        "- Azerbaijan-Liechtenstein and Malta-Gibraltar were both published leans and both drew. "
        "They are retained as misses; no retroactive relabelling.",
        "",
        "## Remaining model-qualified calls",
        "",
        f"- Strong Picks: **{sum(row['v211_tier'] == 'Strong Pick' for row in remaining)}**. "
        f"Model Leans: **{sum(row['v211_tier'] == 'Model Lean' for row in remaining)}**.",
        "- No remaining 2 October match clears the gate. The confirmed Cyprus-Armenia and Latvia-Montenegro "
        "starting XIs do not change either match from Pass.",
        "",
        "| Date/time ET | Competition | Match | Pick | 1 | X | 2 | Weather |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in leans:
        temp = row.get("temperature_c", "")
        weather = "Unavailable"
        if temp not in ("", None):
            weather = f"{base.safe_float(temp):.1f}C; {row.get('weather_risk', 'low')}"
        lines.append(
            f"| {row['date']} {row['time_et']} | {row['category']} | {row['team1']} vs {row['team2']} | "
            f"**{display_pick(row)}** ({row['v211_tier']}) | "
            f"{base.safe_float(row['calibrated_team1_win_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_draw_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_team2_win_probability']) * 100:.1f}% | {weather} |"
        )
    if not leans:
        lines.append("| — | — | — | No match clears the gate | — | — | — | — |")

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
        decision = "Pass" if row["v211_tier"] == "Pass" else f"{row['v211_tier']}: {display_pick(row)}"
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
            "## Interpretation",
            "",
            "- Friendlies remain a separate, lower-trust category because rotation and substitutions are not reliably modelled.",
            "- Malta-Andorra is a numerical Model Lean but an operational yellow flag: Malta's 1-1 draw with Gibraltar "
            "is the same low-scoring favorite profile that has caused recent misses.",
            "- Brazil, Russia and Argentina have verified senior squads/training camps, but their friendly calls remain "
            "conditional on the starting XI rather than being promoted to Strong Pick.",
            "- Spain's official squad remains deep after injury replacements, but its starting XI still needs confirmation.",
            "- Saturday-Monday calls are early reads until the preceding matchday is complete and must be rerun.",
            "- Weather is a small tempo/risk modifier. It cannot manufacture a side where the 1/X/2 model says Pass.",
            "- Starting XIs are checked 60-75 minutes before kickoff; an XI check can downgrade a call but cannot create one.",
            "- Exact scores remain backend-only.",
            "",
            "## Freshness",
            "",
            f"- Rolling team strength rebuilt from {applied:,} results through {through}, including {recent_count} provider/verified overlays.",
            "- Core probabilities: v2.7 calibrated ensemble. Publication filter: v2.11 conservative gate.",
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
    add_verified_results(provider_fixtures)
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
        "window": ["2026-10-02", "2026-10-05"],
        "fixtures": TARGET_FIXTURES,
        "historical_results_applied": applied,
        "historical_results_through": through,
        "recent_result_overlays": recent_count,
        "validation_metrics": metrics,
        "outputs": [
            str(PREDICTIONS_PATH.relative_to(ROOT)),
            str(FEATURES_PATH.relative_to(ROOT)),
            str(VALIDATION_PATH.relative_to(ROOT)),
            str(REPORT_PATH.relative_to(ROOT)),
        ],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "fixtures": len(predictions),
                "historical_results_through": through,
                "recent_result_overlays": recent_count,
                "tiers": {
                    tier: sum(row["v211_tier"] == tier for row in predictions)
                    for tier in ["Strong Pick", "Model Lean", "Pass"]
                },
                "validation": metrics,
                "report": str(REPORT_PATH),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
