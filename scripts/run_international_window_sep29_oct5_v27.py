#!/usr/bin/env python3
"""Run the international model from 29 September through 5 October 2026."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import run_ad_hoc_v27_slate as adhoc
import run_international_window_sep27_oct1_v27 as previous
import run_nations_league_slate_v27 as base


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
PREDICTIONS_PATH = PROCESSED / "international_2026_09_29_to_10_05_predictions.csv"
FEATURES_PATH = PROCESSED / "international_2026_09_29_to_10_05_features.csv"
VALIDATION_PATH = PROCESSED / "international_2026_09_27_28_validation.csv"
REPORT_PATH = OUTPUTS / "international_2026_09_29_to_10_05_report.md"
CONFIG_PATH = OUTPUTS / "international_2026_09_29_to_10_05_config.json"


def f(
    date: str,
    time_et: str,
    team1: str,
    team2: str,
    city: str,
    latitude: float,
    longitude: float,
    venue: str,
    competition: str = "UEFA Nations League",
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


TARGET_FIXTURES = [
    # Tuesday 29 September — UEFA Nations League Matchday 2.
    *[row for row in previous.WINDOW_FIXTURES if row["date"] == "2026-09-29"],
    # Tuesday/Wednesday senior friendlies verified in the live provider.
    f("2026-09-29", "12:00", "Russia", "Iran", "Kazan, Russia", 55.821, 49.161, "Ak Bars Arena", "International Friendly"),
    f("2026-09-29", "20:00", "United States", "Chile", "St. Louis, MO", 38.631, -90.210, "CITYPARK", "International Friendly"),
    f("2026-09-29", "21:00", "Mexico", "Peru", "Harrison, NJ", 40.736, -74.150, "Sports Illustrated Stadium", "International Friendly", venue_edge_team=""),
    f("2026-09-30", "12:00", "Lithuania", "Andorra", "Kaunas, Lithuania", 54.897, 23.937, "Dariaus ir Gireno stadionas", "International Friendly"),
    # Thursday 1 October.
    f("2026-10-01", "12:00", "Azerbaijan", "Liechtenstein", "Baku, Azerbaijan", 40.410, 49.852, "Tofiq Bahramov Republican Stadium"),
    f("2026-10-01", "14:45", "Germany", "Serbia", "Munich, Germany", 48.219, 11.625, "Allianz Arena"),
    f("2026-10-01", "14:45", "Greece", "Netherlands", "Thessaloniki, Greece", 40.614, 22.972, "Toumba Stadium"),
    f("2026-10-01", "14:45", "Denmark", "Portugal", "Copenhagen, Denmark", 55.702, 12.572, "Parken"),
    f("2026-10-01", "14:45", "Wales", "Norway", "Cardiff, Wales", 51.472, -3.203, "Cardiff City Stadium"),
    f("2026-10-01", "14:45", "Israel", "Kosovo", "Debrecen, Hungary", 47.554, 21.633, "Nagyerdei Stadion", venue_edge_team=""),
    f("2026-10-01", "14:45", "Republic of Ireland", "Austria", "Dublin, Ireland", 53.335, -6.229, "Aviva Stadium"),
    f("2026-10-01", "14:45", "Malta", "Gibraltar", "Ta' Qali, Malta", 35.894, 14.415, "National Stadium"),
    # Friday 2 October.
    f("2026-10-02", "10:00", "Kazakhstan", "Moldova", "Astana, Kazakhstan", 51.108, 71.402, "Astana Arena"),
    f("2026-10-02", "12:00", "Cyprus", "Armenia", "Nicosia, Cyprus", 35.160, 33.363, "GSP Stadium"),
    f("2026-10-02", "12:00", "Latvia", "Montenegro", "Riga, Latvia", 56.955, 24.116, "Skonto Stadions"),
    f("2026-10-02", "14:45", "Belgium", "Türkiye", "Liege, Belgium", 50.610, 5.543, "Stade Maurice Dufrasne"),
    f("2026-10-02", "14:45", "France", "Italy", "Saint-Denis, France", 48.924, 2.360, "Stade de France"),
    f("2026-10-02", "14:45", "Hungary", "Georgia", "Budapest, Hungary", 47.503, 19.099, "Puskas Arena"),
    f("2026-10-02", "14:45", "Ukraine", "Northern Ireland", "Trnava, Slovakia", 48.373, 17.590, "Anton Malatinsky Stadium", venue_edge_team=""),
    f("2026-10-02", "14:45", "Bosnia & Herzegovina", "Sweden", "Zenica, Bosnia & Herzegovina", 44.205, 17.907, "Bilino Polje"),
    f("2026-10-02", "14:45", "Poland", "Romania", "Warsaw, Poland", 52.240, 21.046, "PGE Narodowy"),
    f("2026-10-02", "14:45", "Faroe Islands", "Slovakia", "Torshavn, Faroe Islands", 62.019, -6.781, "Torsvollur"),
    # Saturday 3 October.
    f("2026-10-03", "09:00", "Finland", "Albania", "Helsinki, Finland", 60.187, 24.927, "Helsinki Olympic Stadium"),
    f("2026-10-03", "12:00", "Belarus", "San Marino", "Budapest, Hungary", 47.535, 19.108, "Illovszky Rudolf Stadion", venue_edge_team=""),
    f("2026-10-03", "12:00", "Croatia", "England", "Rijeka, Croatia", 45.347, 14.403, "Stadion HNK Rijeka"),
    f("2026-10-03", "12:00", "Estonia", "Luxembourg", "Tallinn, Estonia", 59.421, 24.732, "A. Le Coq Arena"),
    f("2026-10-03", "12:00", "Iceland", "Bulgaria", "Reykjavik, Iceland", 64.143, -21.878, "Laugardalsvollur"),
    f("2026-10-03", "14:45", "North Macedonia", "Scotland", "Skopje, North Macedonia", 42.006, 21.425, "National Arena Todor Proeski"),
    f("2026-10-03", "14:45", "Spain", "Czechia", "Oviedo, Spain", 43.361, -5.870, "Nuevo Carlos Tartiere"),
    f("2026-10-03", "14:45", "Switzerland", "Slovenia", "Lucerne, Switzerland", 47.033, 8.305, "Swissporarena"),
    # Sunday 4 October.
    f("2026-10-04", "09:00", "Azerbaijan", "Lithuania", "Baku, Azerbaijan", 40.400, 49.944, "8KM Stadium"),
    f("2026-10-04", "12:00", "Kosovo", "Austria", "Pristina, Kosovo", 42.663, 21.158, "Stadiumi Fadil Vokrri"),
    f("2026-10-04", "12:00", "Malta", "Andorra", "Ta' Qali, Malta", 35.894, 14.415, "National Stadium"),
    f("2026-10-04", "14:45", "Greece", "Germany", "Thessaloniki, Greece", 40.614, 22.972, "Toumba Stadium"),
    f("2026-10-04", "14:45", "Netherlands", "Serbia", "Eindhoven, Netherlands", 51.441, 5.468, "Philips Stadion"),
    f("2026-10-04", "14:45", "Portugal", "Norway", "Porto, Portugal", 41.162, -8.584, "Estadio do Dragao"),
    f("2026-10-04", "14:45", "Republic of Ireland", "Israel", "Backa Topola, Serbia", 45.809, 19.632, "TSC Arena", venue_edge_team=""),
    f("2026-10-04", "14:45", "Wales", "Denmark", "Cardiff, Wales", 51.472, -3.203, "Cardiff City Stadium"),
    # Monday 5 October.
    f("2026-10-05", "12:00", "Cyprus", "Latvia", "Nicosia, Cyprus", 35.160, 33.363, "GSP Stadium"),
    f("2026-10-05", "14:45", "France", "Belgium", "Saint-Denis, France", 48.924, 2.360, "Stade de France"),
    f("2026-10-05", "14:45", "Italy", "Türkiye", "Bologna, Italy", 44.492, 11.310, "Stadio Renato Dall'Ara"),
    f("2026-10-05", "14:45", "Northern Ireland", "Georgia", "Belfast, Northern Ireland", 54.582, -5.956, "Windsor Park"),
    f("2026-10-05", "14:45", "Ukraine", "Hungary", "Trnava, Slovakia", 48.373, 17.590, "Anton Malatinsky Stadium", venue_edge_team=""),
    f("2026-10-05", "14:45", "Bosnia & Herzegovina", "Poland", "Zenica, Bosnia & Herzegovina", 44.205, 17.907, "Bilino Polje"),
    f("2026-10-05", "14:45", "Romania", "Sweden", "Bucharest, Romania", 44.438, 26.152, "National Arena"),
    f("2026-10-05", "14:45", "Montenegro", "Armenia", "Podgorica, Montenegro", 42.442, 19.262, "Podgorica City Stadium"),
]


OFFICIAL_SEP27_RESULTS = [
    ("Lithuania", "Azerbaijan", 1, 1),
    ("Serbia", "Netherlands", 1, 2),
    ("Denmark", "Wales", 2, 0),
    ("Austria", "Kosovo", 3, 1),
    ("Gibraltar", "Andorra", 0, 0),
    ("Germany", "Greece", 0, 1),
    ("Norway", "Portugal", 1, 2),
    ("Israel", "Republic of Ireland", 0, 3),
]


FROZEN_ACTUALS = {
    ("2026-09-27", "Lithuania", "Azerbaijan"): (1, 1),
    ("2026-09-27", "Serbia", "Netherlands"): (1, 2),
    ("2026-09-27", "Denmark", "Wales"): (2, 0),
    ("2026-09-27", "Austria", "Kosovo"): (3, 1),
    ("2026-09-27", "Gibraltar", "Andorra"): (0, 0),
    ("2026-09-27", "Germany", "Greece"): (0, 1),
    ("2026-09-27", "Norway", "Portugal"): (1, 2),
    ("2026-09-27", "Israel", "Republic of Ireland"): (0, 3),
    ("2026-09-27", "Seychelles", "Sri Lanka"): (0, 3),
    ("2026-09-27", "Malta", "Liechtenstein"): (2, 0),
    ("2026-09-27", "Jordan", "Syria"): (1, 1),
    ("2026-09-27", "Bolivia", "Paraguay"): (0, 2),
    ("2026-09-28", "Georgia", "Ukraine"): (0, 0),
    ("2026-09-28", "Armenia", "Montenegro"): (2, 3),
    ("2026-09-28", "Latvia", "Cyprus"): (0, 0),
    ("2026-09-28", "Belgium", "France"): (0, 1),
    ("2026-09-28", "Türkiye", "Italy"): (1, 4),
    ("2026-09-28", "Northern Ireland", "Hungary"): (0, 0),
    ("2026-09-28", "Sweden", "Poland"): (3, 1),
    ("2026-09-28", "Romania", "Bosnia & Herzegovina"): (2, 4),
    ("2026-09-28", "Japan", "Venezuela"): (2, 1),
    ("2026-09-28", "South Korea", "Uruguay"): (1, 4),
    ("2026-09-28", "Tajikistan", "Palestine"): (2, 4),
}


def add_official_sep27(provider_fixtures: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    for home, away, home_score, away_score in OFFICIAL_SEP27_RESULTS:
        key = base.fixture_match_key("2026-09-27", home, away)
        provider_fixtures[key] = {
            "fixture_key": key,
            "provider_fixture_id": "uefa-official",
            "provider_status": "FT",
            "provider_status_long": "Match Finished",
            "provider_home": base.model_team_name(home),
            "provider_away": base.model_team_name(away),
            "home_score_90": home_score,
            "away_score_90": away_score,
            "fetched_at": "2026-09-29T10:20:00-04:00",
            "competition": "UEFA Nations League",
            "venue": {},
        }


def build_validation() -> tuple[pd.DataFrame, dict[str, Any]]:
    frozen = pd.read_csv(previous.PREDICTIONS_PATH)
    rows: list[dict[str, Any]] = []
    for row in frozen.to_dict("records"):
        key = (row["date"], row["team1"], row["team2"])
        if key not in FROZEN_ACTUALS:
            continue
        home_score, away_score = FROZEN_ACTUALS[key]
        actual_index = 0 if home_score > away_score else 1 if home_score == away_score else 2
        actual_label = ["team1_win", "draw", "team2_win"][actual_index]
        probabilities = [
            base.safe_float(row["calibrated_team1_win_probability"]),
            base.safe_float(row["calibrated_draw_probability"]),
            base.safe_float(row["calibrated_team2_win_probability"]),
        ]
        top_index = max(range(3), key=lambda index: probabilities[index])
        public = row["v211_tier"] != "Pass" and row["v211_pick"] != "pass"
        rows.append(
            {
                "date": row["date"],
                "category": row["category"],
                "team1": row["team1"],
                "team2": row["team2"],
                "score": f"{home_score}-{away_score}",
                "tier": row["v211_tier"],
                "public_pick": row["v211_pick"],
                "actual": actual_label,
                "public_pick_correct": (row["v211_pick"] == actual_label) if public else None,
                "internal_top_correct": top_index == actual_index,
                "log_loss": -math.log(max(probabilities[actual_index], 1e-15)),
                "brier": sum((probabilities[index] - (1 if index == actual_index else 0)) ** 2 for index in range(3)),
            }
        )
    validation = pd.DataFrame(rows)
    validation.to_csv(VALIDATION_PATH, index=False)
    published = validation[validation["public_pick_correct"].notna()]
    passes = validation[validation["tier"] == "Pass"]
    metrics = {
        "matches": len(validation),
        "raw_top_accuracy": float(validation["internal_top_correct"].mean()),
        "log_loss": float(validation["log_loss"].mean()),
        "brier": float(validation["brier"].mean()),
        "published_matches_in_window": len(published),
        "published_accuracy_in_window": float(published["public_pick_correct"].mean()) if len(published) else None,
        "pass_internal_accuracy": float(passes["internal_top_correct"].mean()),
    }
    return validation, metrics


def decision_name(row: dict[str, Any]) -> str:
    return base.public_pick_name(row)


def decision_status(row: dict[str, Any]) -> str:
    date = str(row["date"])
    teams = {str(row["team1"]), str(row["team2"])}
    if date in {"2026-09-29", "2026-10-01"}:
        return "Current; XI pending"
    if date == "2026-10-02" and teams == {"Kazakhstan", "Moldova"}:
        return "Provisional after Tuesday results"
    if date >= "2026-10-03":
        return "Provisional; prior matchday pending"
    return "Current early read"


def write_report(predictions: list[dict[str, Any]], metrics: dict[str, Any], applied: int, through: str, recent_count: int) -> None:
    generated = datetime.now().astimezone()
    leans = [row for row in predictions if row["v211_tier"] in {"Strong Pick", "Model Lean"}]
    leans.sort(key=lambda row: (row["date"], -base.safe_float(row["v211_top_probability"])))
    lines = [
        "# International Model Report: 29 September-5 October 2026",
        "",
        f"**Generated:** {generated.strftime('%A, %B %-d, %Y at %-I:%M %p %Z')}",
        "",
        "## Accuracy audit",
        "",
        "- Frozen public record across the current international run: **4 hits from 5 completed published selections (80%)**.",
        "- UEFA-only published record: **3/4 (75%)**; the Malta friendly lean also won 2-0.",
        f"- On the latest {metrics['matches']} completed matches, the raw largest-probability outcome was correct {metrics['raw_top_accuracy'] * 100:.1f}% of the time.",
        f"- Internal favorites on matches labelled Pass were correct only {metrics['pass_internal_accuracy'] * 100:.1f}% of the time, supporting the strict publication gate.",
        f"- Probability metrics: log loss {metrics['log_loss']:.3f}, multiclass Brier {metrics['brier']:.3f}. Uniform baselines are 1.099 and 0.667 respectively.",
        "",
        "## Model decision",
        "",
        "Keep the core v2.7 ensemble and v2.11 gate unchanged for now. Five completed public picks are too few for a responsible retune. Shadow-test a rule that downgrades 60-70% favorites when calibrated draw risk is at least 27%, but require historical backtesting before promoting it; this would address the Iceland profile without post-hoc overfitting.",
        "",
        "League-phase internationals behave more like a World Cup group stage than a knockout round: more rotation, more draws and less stable incentives. The strict gate—not raw pick accuracy—is the relevant product layer here.",
        "",
        "## Ranked model leans",
        "",
        "| Date/time ET | Match | Pick | 1 | X | 2 | Status | Weather |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for row in leans:
        weather = f"{base.safe_float(row.get('temperature_c')):.1f}C; {row.get('weather_risk', 'low')}"
        lines.append(
            f"| {row['date']} {row['time_et']} | {row['team1']} vs {row['team2']} | **{decision_name(row)}** ({row['v211_tier']}) | "
            f"{base.safe_float(row['calibrated_team1_win_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_draw_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_team2_win_probability']) * 100:.1f}% | {decision_status(row)} | {weather} |"
        )
    if not leans:
        lines.append("| — | — | No match clears the gate | — | — | — | — | — |")

    lines.extend(
        [
            "",
            "## Full slate",
            "",
            "| Date/time ET | Competition | Match | Internal read | 1 | X | 2 | Public decision |",
            "|---|---|---|---|---:|---:|---:|---|",
        ]
    )
    for row in predictions:
        internal = base.internal_read_name(row)
        decision = "Pass" if row["v211_tier"] == "Pass" else f"{row['v211_tier']}: {decision_name(row)}"
        lines.append(
            f"| {row['date']} {row['time_et']} | {row['category']} | {row['team1']} vs {row['team2']} | {internal} | "
            f"{base.safe_float(row['calibrated_team1_win_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_draw_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_team2_win_probability']) * 100:.1f}% | {decision} |"
        )
    lines.extend(
        [
            "",
            "## Operating rules",
            "",
            "- Probabilities are 90-minute 1/X/2 only.",
            "- Squad availability is checked as a confidence gate; player absences do not receive invented subjective weights.",
            "- Starting XIs should be checked 60-75 minutes before kickoff. A lean may be downgraded, never upgraded merely to increase the number of picks.",
            "- Saturday-through-Monday probabilities are early baselines because those teams have another matchday first; rerun after each intervening round.",
            "- Weather is a small tempo/risk modifier. Exact scores remain hidden.",
            "- Do not treat several individually plausible selections as a guaranteed parlay; joint hit probability falls quickly.",
            "",
            "## Data freshness and sources",
            "",
            f"- Team strength rebuilt from {applied:,} senior results through {through}, including {recent_count} recent official/provider overlays.",
            "- [UEFA official Nations League fixtures](https://www.uefa.com/uefanationsleague/news/02a2-1fea18abbcbc-456e846509e7-1000--2026-27-uefa-nations-league-all-the-league-phase-fixtures/)",
            "- API-Football cache for current results and near-term fixture status.",
            "- [Open-Meteo](https://open-meteo.com/) for venue forecasts.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    validation, metrics = build_validation()
    original_fixtures = list(base.FIXTURES)
    all_fixtures: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in original_fixtures + previous.HISTORICAL_EXTRA_FIXTURES + previous.WINDOW_FIXTURES + TARGET_FIXTURES:
        key = base.fixture_match_key(row["date"], row["team1"], row["team2"])
        if key in seen:
            continue
        seen.add(key)
        all_fixtures.append(row)
    base.FIXTURES = all_fixtures
    provider_fixtures = base.cached_provider_fixtures()
    previous.add_official_results(provider_fixtures)
    add_official_sep27(provider_fixtures)
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
        "window": ["2026-09-29", "2026-10-05"],
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
