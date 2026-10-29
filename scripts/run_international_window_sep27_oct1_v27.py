#!/usr/bin/env python3
"""Build a time-safe international slate for 27 September-1 October 2026.

The fitted international model is unchanged. Recent completed results are
rolled into Elo/form state, weather is refreshed, and Thursday decisions are
kept provisional until the Sunday results they depend on are known.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import run_ad_hoc_v27_slate as adhoc
import run_nations_league_slate_v27 as base


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
PREDICTIONS_PATH = PROCESSED / "international_2026_09_27_to_10_01_predictions.csv"
FEATURES_PATH = PROCESSED / "international_2026_09_27_to_10_01_features.csv"
REPORT_PATH = OUTPUTS / "international_2026_09_27_to_10_01_report.md"
CONFIG_PATH = OUTPUTS / "international_2026_09_27_to_10_01_config.json"


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
    row = base.fixture(
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
    row["category"] = competition
    return row


WINDOW_FIXTURES = [
    # Sunday 27 September — UEFA Nations League.
    f("2026-09-27", "09:00", "Lithuania", "Azerbaijan", "Kaunas, Lithuania", 54.897, 23.937, "Dariaus ir Gireno stadionas"),
    f("2026-09-27", "12:00", "Serbia", "Netherlands", "Belgrade, Serbia", 44.783, 20.465, "Stadion Rajko Mitic"),
    f("2026-09-27", "12:00", "Denmark", "Wales", "Copenhagen, Denmark", 55.702, 12.572, "Parken"),
    f("2026-09-27", "12:00", "Austria", "Kosovo", "Vienna, Austria", 48.207, 16.420, "Ernst Happel Stadion"),
    f("2026-09-27", "12:00", "Gibraltar", "Andorra", "Gibraltar", 36.149, -5.350, "Europa Sports Park"),
    f("2026-09-27", "14:45", "Germany", "Greece", "Augsburg, Germany", 48.323, 10.886, "WWK Arena"),
    f("2026-09-27", "14:45", "Norway", "Portugal", "Oslo, Norway", 59.949, 10.734, "Ullevaal Stadion"),
    f("2026-09-27", "14:45", "Israel", "Republic of Ireland", "Debrecen, Hungary", 47.554, 21.633, "Nagyerdei Stadion", venue_edge_team=""),
    # Sunday senior friendlies that had not begun at generation time.
    f("2026-09-27", "08:00", "Seychelles", "Sri Lanka", "Victoria, Seychelles", -4.620, 55.452, "Stade Linite", "International Friendly"),
    f("2026-09-27", "12:30", "Malta", "Liechtenstein", "Ta' Qali, Malta", 35.894, 14.415, "National Stadium", "International Friendly"),
    f("2026-09-27", "13:00", "Jordan", "Syria", "Amman, Jordan", 31.953, 35.910, "Amman International Stadium", "International Friendly"),
    f("2026-09-27", "16:30", "Bolivia", "Paraguay", "Washington, DC", 38.868, -77.013, "Audi Field", "International Friendly", venue_edge_team=""),
    # Monday 28 September — UEFA Nations League.
    f("2026-09-28", "12:00", "Georgia", "Ukraine", "Tbilisi, Georgia", 41.723, 44.790, "Boris Paichadze Dinamo Arena"),
    f("2026-09-28", "12:00", "Armenia", "Montenegro", "Yerevan, Armenia", 40.172, 44.525, "Republican Stadium"),
    f("2026-09-28", "12:00", "Latvia", "Cyprus", "Riga, Latvia", 56.955, 24.116, "Skonto Stadium"),
    f("2026-09-28", "14:45", "Belgium", "France", "Brussels, Belgium", 50.895, 4.334, "King Baudouin Stadium"),
    f("2026-09-28", "14:45", "Türkiye", "Italy", "Bursa, Türkiye", 40.210, 28.999, "Bursa Buyuksehir Stadyumu"),
    f("2026-09-28", "14:45", "Northern Ireland", "Hungary", "Belfast, Northern Ireland", 54.582, -5.956, "Windsor Park"),
    f("2026-09-28", "14:45", "Sweden", "Poland", "Solna, Sweden", 59.373, 18.000, "Strawberry Arena"),
    f("2026-09-28", "14:45", "Romania", "Bosnia & Herzegovina", "Bucharest, Romania", 44.438, 26.152, "Arena Nationala"),
    # Monday senior friendlies.
    f("2026-09-28", "06:25", "Japan", "Venezuela", "Hiroshima, Japan", 34.396, 132.459, "Edion Peace Wing Hiroshima", "International Friendly"),
    f("2026-09-28", "07:00", "South Korea", "Uruguay", "Seoul, South Korea", 37.568, 126.897, "Seoul World Cup Stadium", "International Friendly"),
    f("2026-09-28", "08:00", "Tajikistan", "Palestine", "Dushanbe, Tajikistan", 38.585, 68.780, "Central Republican Stadium", "International Friendly"),
    f("2026-09-28", "08:00", "Kyrgyzstan", "Lebanon", "Bishkek, Kyrgyzstan", 42.875, 74.604, "Dolen Omurzakov Stadium", "International Friendly"),
    # Tuesday 29 September — UEFA official Matchday 2 schedule.
    f("2026-09-29", "12:00", "Finland", "Belarus", "Helsinki, Finland", 60.187, 24.927, "Helsinki Olympic Stadium"),
    f("2026-09-29", "12:00", "Moldova", "Faroe Islands", "Chisinau, Moldova", 46.981, 28.867, "Stadionul Zimbru"),
    f("2026-09-29", "14:45", "Czechia", "England", "Prague, Czechia", 50.068, 14.471, "Fortuna Arena"),
    f("2026-09-29", "14:45", "Spain", "Croatia", "Seville, Spain", 37.384, -5.970, "Estadio Ramon Sanchez-Pizjuan"),
    f("2026-09-29", "14:45", "Scotland", "Switzerland", "Glasgow, Scotland", 55.826, -4.252, "Hampden Park"),
    f("2026-09-29", "14:45", "Slovenia", "North Macedonia", "Ljubljana, Slovenia", 46.081, 14.524, "Stadion Stozice"),
    f("2026-09-29", "14:45", "San Marino", "Albania", "Serravalle, San Marino", 43.971, 12.477, "San Marino Stadium"),
    f("2026-09-29", "14:45", "Slovakia", "Kazakhstan", "Kosice, Slovakia", 48.704, 21.244, "Kosicka Futbalova Arena"),
    f("2026-09-29", "14:45", "Bulgaria", "Estonia", "Plovdiv, Bulgaria", 42.143, 24.751, "Hristo Botev Stadium"),
    f("2026-09-29", "14:45", "Luxembourg", "Iceland", "Luxembourg", 49.577, 6.114, "Stade de Luxembourg"),
    # Thursday 1 October — early baseline only; refresh after Sunday results.
    f("2026-10-01", "12:00", "Azerbaijan", "Liechtenstein", "Baku, Azerbaijan", 40.410, 49.852, "Tofiq Bahramov Republican Stadium"),
    f("2026-10-01", "14:45", "Germany", "Serbia", "Munich, Germany", 48.219, 11.625, "Allianz Arena"),
    f("2026-10-01", "14:45", "Greece", "Netherlands", "Thessaloniki, Greece", 40.614, 22.972, "Toumba Stadium"),
    f("2026-10-01", "14:45", "Denmark", "Portugal", "Copenhagen, Denmark", 55.702, 12.572, "Parken"),
    f("2026-10-01", "14:45", "Wales", "Norway", "Cardiff, Wales", 51.472, -3.203, "Cardiff City Stadium"),
    f("2026-10-01", "14:45", "Israel", "Kosovo", "Debrecen, Hungary", 47.554, 21.633, "Nagyerdei Stadion", venue_edge_team=""),
    f("2026-10-01", "14:45", "Republic of Ireland", "Austria", "Dublin, Ireland", 53.335, -6.229, "Aviva Stadium"),
    f("2026-10-01", "14:45", "Malta", "Gibraltar", "Ta' Qali, Malta", 35.894, 14.415, "National Stadium"),
]


HISTORICAL_EXTRA_FIXTURES = [
    f("2026-09-24", "06:05", "Japan", "Uruguay", "Rifu, Japan", 38.336, 140.950, "Miyagi Stadium", "International Friendly"),
    f("2026-09-24", "07:00", "South Korea", "Ecuador", "Suwon, South Korea", 37.286, 127.037, "Suwon World Cup Stadium", "International Friendly"),
    f("2026-09-24", "05:30", "Palestine", "New Zealand", "Chongqing, China", 29.720, 106.650, "Tongliang Long Stadium", "International Friendly", venue_edge_team=""),
]


OFFICIAL_SEP25_RESULTS = [
    ("Georgia", "Northern Ireland", 0, 1),
    ("Armenia", "Latvia", 2, 0),
    ("Italy", "Belgium", 0, 2),
    ("Türkiye", "France", 0, 1),
    ("Hungary", "Ukraine", 0, 1),
    ("Poland", "Bosnia & Herzegovina", 0, 0),
    ("Sweden", "Romania", 2, 1),
    ("Montenegro", "Cyprus", 2, 1),
]


def add_official_results(provider_fixtures: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    for home, away, home_score, away_score in OFFICIAL_SEP25_RESULTS:
        key = base.fixture_match_key("2026-09-25", home, away)
        provider_fixtures[key] = {
            "fixture_key": key,
            "provider_fixture_id": "uefa-official",
            "provider_status": "FT",
            "provider_status_long": "Match Finished",
            "provider_home": base.model_team_name(home),
            "provider_away": base.model_team_name(away),
            "home_score_90": home_score,
            "away_score_90": away_score,
            "fetched_at": "2026-09-27T07:30:00-04:00",
            "competition": "UEFA Nations League",
            "venue": {},
        }


def pick_name(row: dict[str, Any]) -> str:
    return base.public_pick_name(row)


def write_report(predictions: list[dict[str, Any]], applied: int, through: str, recent_count: int) -> None:
    generated = datetime.now().astimezone()
    pending = [row for row in predictions if row.get("provider_status") not in base.FINAL_PROVIDER_STATUSES]
    for row in pending:
        row["is_provisional"] = row["date"] == "2026-10-01"
        if row["is_provisional"]:
            row["display_tier"] = "Provisional"
            row["display_pick"] = "Wait for Sunday results"
        else:
            row["display_tier"] = row["v211_tier"]
            row["display_pick"] = pick_name(row)

    approved_uefa = [
        row
        for row in pending
        if row["category"] == "UEFA Nations League"
        and not row["is_provisional"]
        and row["v211_tier"] in {"Strong Pick", "Model Lean"}
    ]
    approved_uefa.sort(key=lambda row: base.safe_float(row["v211_top_probability"]), reverse=True)
    friendly_leans = [
        row
        for row in pending
        if row["category"] == "International Friendly"
        and row["v211_tier"] in {"Strong Pick", "Model Lean"}
    ]
    provisional_leans = [
        row
        for row in pending
        if row["is_provisional"] and row["v211_tier"] in {"Strong Pick", "Model Lean"}
    ]

    lines = [
        "# International Decision Report: Sunday-Thursday",
        "",
        f"**Generated:** {generated.strftime('%A, %B %-d, %Y at %-I:%M %p %Z')}",
        "",
        "## Bankroll warning",
        "",
        "This report is not a loss-recovery plan. Do not increase stake size to recover the Iceland loss. If the remaining $25 is needed for anything else, the correct decision is not to bet it.",
        "",
        "## Decision summary",
        "",
        "- **Sunday:** no UEFA match clears the gate.",
        "- **Monday:** no UEFA match clears the gate.",
        "- **Tuesday:** the first model-qualified Nations League window.",
    ]
    for row in approved_uefa:
        lines.append(
            f"  - **{pick_name(row)}** in {row['team1']} vs {row['team2']}: "
            f"{base.safe_float(row['v211_top_probability']) * 100:.1f}% ({row['v211_tier']})."
        )
    for row in friendly_leans:
        lines.append(
            f"- **Friendly-only analytical lean:** {pick_name(row)} at "
            f"{base.safe_float(row['v211_top_probability']) * 100:.1f}%; wait for the XI because friendly rotation is not modelled reliably."
        )
    if provisional_leans:
        lines.append(
            "- **Thursday early watchlist:** "
            + ", ".join(
                f"{pick_name(row)} {base.safe_float(row['v211_top_probability']) * 100:.1f}%"
                for row in provisional_leans
            )
            + ". These are not final picks."
        )
    lines.extend(
        [
        "",
        "## Previous public selections",
        "",
        "- Lithuania beat Liechtenstein 2-0 — **hit**.",
        "- Finland beat San Marino 7-0 — **hit**.",
        "- Slovakia beat Moldova 2-0 — **hit**.",
        "- Iceland drew Estonia 1-1 — **miss**.",
        "- Current completed public record: **3/4 (75%)**. This is a tiny sample and not a guaranteed future rate.",
        "",
        "## UEFA Nations League",
        "",
        "| Date/time ET | Match | 1 | X | 2 | Decision |",
        "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in pending:
        if row["category"] != "UEFA Nations League":
            continue
        decision = row["display_tier"] if row["display_pick"] == "Pass" else f"{row['display_tier']}: {row['display_pick']}"
        lines.append(
            f"| {row['date']} {row['time_et']} | {row['team1']} vs {row['team2']} | "
            f"{base.safe_float(row['calibrated_team1_win_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_draw_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_team2_win_probability']) * 100:.1f}% | {decision} |"
        )

    lines.extend(
        [
            "",
            "## Senior international friendlies",
            "",
            "Friendlies are separated because lineup experimentation and substitutions make them less reliable.",
            "",
            "| Date/time ET | Match | 1 | X | 2 | Decision |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in pending:
        if row["category"] != "International Friendly":
            continue
        decision = row["v211_tier"] if pick_name(row) == "Pass" else f"{row['v211_tier']}: {pick_name(row)}"
        lines.append(
            f"| {row['date']} {row['time_et']} | {row['team1']} vs {row['team2']} | "
            f"{base.safe_float(row['calibrated_team1_win_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_draw_probability']) * 100:.1f}% | "
            f"{base.safe_float(row['calibrated_team2_win_probability']) * 100:.1f}% | {decision} |"
        )

    weather_watch = [row for row in pending if row.get("weather_risk") == "watch"]
    lines.extend(["", "## Weather and refresh rules", ""])
    for row in weather_watch:
        lines.append(f"- **{row['team1']} vs {row['team2']}:** {row.get('weather_note', 'Weather watch.')} ")
    lines.extend(
        [
            "- Weather is a small tempo/risk modifier, not a large outcome weight.",
            "- Thursday probabilities are deliberately provisional because today's results must be incorporated first.",
            "- Starting XIs should be checked 60-75 minutes before kickoff; a published lean can still be downgraded to Pass.",
            "",
            "## Model freshness",
            "",
            f"- Built from {applied:,} senior results through {through}, including {recent_count} live/official recent-result overlays.",
            "- Core model: calibrated v2.7 international ensemble; publication filter: conservative v2.11 gate.",
            "- Exact scores are intentionally hidden.",
            "- Wednesday has no verified UEFA Nations League fixture in this window.",
            "",
            "## Sources",
            "",
            "- [UEFA official Nations League fixtures](https://www.uefa.com/uefanationsleague/news/02a2-1fea18abbcbc-456e846509e7-1000--2026-27-uefa-nations-league-all-the-league-phase-fixtures/)",
            "- API-Football cache for current statuses/results through the free-plan date window.",
            "- [Open-Meteo](https://open-meteo.com/) venue forecasts.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    original_fixtures = list(base.FIXTURES)
    all_fixtures: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in original_fixtures + HISTORICAL_EXTRA_FIXTURES + WINDOW_FIXTURES:
        key = base.fixture_match_key(row["date"], row["team1"], row["team2"])
        if key in seen:
            continue
        seen.add(key)
        all_fixtures.append(row)

    base.FIXTURES = all_fixtures
    provider_fixtures = base.cached_provider_fixtures()
    add_official_results(provider_fixtures)
    elo_lookup, form_lookup, applied, through, recent_count = base.current_team_lookups(provider_fixtures)
    providers = {row["fixture_key"]: base.provider_overlay(row, provider_fixtures) for row in WINDOW_FIXTURES}
    weather = {row["fixture_key"]: adhoc.weather_for_fixture(row, force_refresh=True) for row in WINDOW_FIXTURES}

    original_lookup = adhoc.load_lookup
    try:
        def refreshed_lookup(path: Path, key: str, normalize_key: bool = False) -> dict[str, dict[str, Any]]:
            if path.name == "team_elo_latest.csv":
                return elo_lookup
            if path.name == "team_recent_form_latest.csv":
                return form_lookup
            return original_lookup(path, key, normalize_key)

        adhoc.load_lookup = refreshed_lookup
        features = adhoc.build_feature_rows(WINDOW_FIXTURES, providers, weather)
    finally:
        adhoc.load_lookup = original_lookup

    predictions = adhoc.build_predictions(WINDOW_FIXTURES, providers, weather, features)
    base.add_confidence_gate(predictions)
    fixture_lookup = {row["fixture_key"]: row for row in WINDOW_FIXTURES}
    for row in predictions:
        row["category"] = fixture_lookup[row["fixture_key"]]["category"]
    adhoc.write_csv(PREDICTIONS_PATH, predictions, list(predictions[0].keys()))
    adhoc.write_csv(FEATURES_PATH, features, list(features[0].keys()))
    write_report(predictions, applied, through, recent_count)

    config = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "window": ["2026-09-27", "2026-10-01"],
        "fixtures": WINDOW_FIXTURES,
        "historical_results_applied": applied,
        "historical_results_through": through,
        "recent_result_overlays": recent_count,
        "thursday_status": "provisional until Sunday results are incorporated",
        "outputs": [str(PREDICTIONS_PATH.relative_to(ROOT)), str(FEATURES_PATH.relative_to(ROOT)), str(REPORT_PATH.relative_to(ROOT))],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pending = [row for row in predictions if row.get("provider_status") not in base.FINAL_PROVIDER_STATUSES]
    print(
        json.dumps(
            {
                "fixtures": len(predictions),
                "pending": len(pending),
                "through": through,
                "recent_result_overlays": recent_count,
                "tiers_pending": {
                    tier: sum(row["v211_tier"] == tier for row in pending)
                    for tier in ["Strong Pick", "Model Lean", "Pass"]
                },
                "report": str(REPORT_PATH),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
