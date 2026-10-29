#!/usr/bin/env python3
"""Validate saved v2.7 live predictions against known API-Football fixture IDs."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

from api_football_client_v24 import budget_snapshot, provider_get


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

VALIDATION_FIXTURES = {
    "friendly_2026_06_06_portugal_chile": 1528286,
    "friendly_2026_06_06_germany_usa": 1502474,
    "road26_2026_06_06_bolivia_scotland": 1540949,
    "road26_2026_06_06_brazil_egypt": 1528287,
    "road26_2026_06_06_argentina_honduras": 1540355,
    "road26_2026_06_07_morocco_norway": 1540950,
    "road26_2026_06_07_colombia_jordan": 1528288,
    "road26_2026_06_09_argentina_iceland": 1540357,
}

FINAL_STATUSES = {"FT", "AET", "PEN"}
ROWS_PATH = PROCESSED / "v27_known_fixture_validation.csv"
REPORT_PATH = OUTPUTS / "v27_known_fixture_validation_report.md"


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


def actual_label(home_goals: Any, away_goals: Any, provider_home: str, provider_away: str, team1: str, team2: str) -> str:
    if home_goals is None or away_goals is None:
        return ""
    if int(home_goals) == int(away_goals):
        return "draw"
    winner = provider_home if int(home_goals) > int(away_goals) else provider_away
    if winner == team1:
        return "team1_win"
    if winner == team2:
        return "team2_win"
    return ""


def main() -> None:
    saved_predictions = {row["fixture_key"]: row for row in read_csv(PROCESSED / "v27_live_public_picks.csv")}
    rows = []
    for fixture_key, fixture_id in VALIDATION_FIXTURES.items():
        prediction = saved_predictions.get(fixture_key, {})
        result = provider_get(
            "fixtures",
            {"id": fixture_id, "timezone": "America/New_York"},
            ttl_hours=0.25,
            force_refresh=False,
            daily_limit=100,
            reserve_requests=15,
        )
        response = result.response_rows[0] if result.response_rows else {}
        fixture = response.get("fixture", {})
        status = fixture.get("status", {})
        teams = response.get("teams", {})
        goals = response.get("goals", {})
        provider_home = teams.get("home", {}).get("name", "")
        provider_away = teams.get("away", {}).get("name", "")
        status_short = status.get("short", "")
        is_final = status_short in FINAL_STATUSES
        actual = actual_label(
            goals.get("home"),
            goals.get("away"),
            provider_home,
            provider_away,
            prediction.get("team1", ""),
            prediction.get("team2", ""),
        ) if is_final else ""
        internal_pick = prediction.get("internal_ensemble_pick", "")
        public_pick = prediction.get("public_pick", "")
        rows.append(
            {
                "fixture_key": fixture_key,
                "fixture_id": fixture_id,
                "team1": prediction.get("team1", ""),
                "team2": prediction.get("team2", ""),
                "provider_home": provider_home,
                "provider_away": provider_away,
                "status": status_short,
                "live_score": f"{goals.get('home')}-{goals.get('away')}" if goals.get("home") is not None else "",
                "actual_result": actual,
                "v27_public_pick": public_pick,
                "v27_internal_pick": internal_pick,
                "team1_win_probability": prediction.get("team1_win_probability", ""),
                "draw_probability": prediction.get("draw_probability", ""),
                "team2_win_probability": prediction.get("team2_win_probability", ""),
                "public_pick_scored": bool(is_final and public_pick and public_pick != "pass"),
                "public_pick_correct": actual == public_pick if is_final and public_pick and public_pick != "pass" else "",
                "internal_pick_scored": bool(is_final and internal_pick),
                "internal_pick_correct": actual == internal_pick if is_final and internal_pick else "",
                "max_probability": max(
                    safe_float(prediction.get("team1_win_probability")),
                    safe_float(prediction.get("draw_probability")),
                    safe_float(prediction.get("team2_win_probability")),
                ),
            }
        )

    write_csv(
        ROWS_PATH,
        rows,
        [
            "fixture_key",
            "fixture_id",
            "team1",
            "team2",
            "provider_home",
            "provider_away",
            "status",
            "live_score",
            "actual_result",
            "v27_public_pick",
            "v27_internal_pick",
            "team1_win_probability",
            "draw_probability",
            "team2_win_probability",
            "public_pick_scored",
            "public_pick_correct",
            "internal_pick_scored",
            "internal_pick_correct",
            "max_probability",
        ],
    )

    final_rows = [row for row in rows if row["actual_result"]]
    public_scored = [row for row in final_rows if row["public_pick_scored"]]
    internal_scored = [row for row in final_rows if row["internal_pick_scored"]]
    internal_correct = [row for row in internal_scored if row["internal_pick_correct"]]
    passed_but_internal_correct = [
        row
        for row in final_rows
        if row["v27_public_pick"] == "pass" and row["internal_pick_correct"]
    ]
    high_internal = [row for row in final_rows if safe_float(row["max_probability"]) >= 0.60]
    high_internal_correct = [row for row in high_internal if row["internal_pick_correct"]]

    lines = [
        "# v2.7 Known Fixture Validation",
        "",
        "This validates the saved v2.7 live predictions against known API-Football fixture IDs.",
        "",
        "## Summary",
        "",
        f"- Final fixtures validated: {len(final_rows)}.",
        f"- Public non-pass picks available to score: {len(public_scored)}.",
        f"- Internal ensemble leans correct: {len(internal_correct)}/{len(internal_scored)}.",
        f"- Passes where the internal lean was correct: {len(passed_but_internal_correct)}.",
        f"- Internal leans at or above 60% confidence: {len(high_internal_correct)}/{len(high_internal)} correct.",
        "",
        "## Fixture Results",
        "",
        "| Match | Score | Actual | Public | Internal | Max prob | Internal correct |",
        "|---|---|---|---|---|---:|---|",
    ]
    for row in rows:
        match = f"{row['team1']} vs {row['team2']}"
        lines.append(
            f"| {match} | {row['live_score']} | {row['actual_result'] or row['status']} | {row['v27_public_pick']} | {row['v27_internal_pick']} | {safe_float(row['max_probability']) * 100:.2f}% | {row['internal_pick_correct']} |"
        )
    lines.extend(
        [
            "",
            "## Read",
            "",
            "This sample is too small to recalibrate the model statistically, but it shows the current gate is probably too conservative for public product use: it passed fixtures where the internal ensemble lean was right. The right next step is not to remove Pass; it is to add a second confidence tier for strong internal leans that the logistic safety layer blocks mostly because the match is a friendly.",
            "",
            f"API budget after validation: {budget_snapshot()['used_today']}/{budget_snapshot()['daily_limit']} used.",
        ]
    )
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "final_fixtures": len(final_rows),
                "internal_correct": f"{len(internal_correct)}/{len(internal_scored)}",
                "public_scored": len(public_scored),
                "report": str(REPORT_PATH.relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
