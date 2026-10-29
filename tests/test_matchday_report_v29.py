import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_worldcup_matchday_v29 as v29


def prediction(team1_probability, draw_probability, team2_probability):
    return {
        "team1": "Germany",
        "team2": "Paraguay",
        "team1_win_probability": team1_probability,
        "draw_probability": draw_probability,
        "team2_win_probability": team2_probability,
    }


def test_plain_best_read_returns_team1_win():
    assert v29.plain_best_read(prediction(0.4492, 0.3484, 0.2024)) == "Germany win"


def test_plain_best_read_returns_draw():
    assert v29.plain_best_read(prediction(0.34, 0.38, 0.28)) == "Draw"


def test_plain_best_read_returns_team2_win():
    assert v29.plain_best_read(prediction(0.20, 0.30, 0.50)) == "Paraguay win"


def test_knockout_placeholder_row_is_matched_by_kickoff(monkeypatch):
    rows = [
        {
            "date": "2026-07-03",
            "time": "18:00 UTC-4",
            "team1": "1J",
            "team2": "2H",
            "round": "Round of 32",
            "ground": "Miami (Miami Gardens)",
        }
    ]
    monkeypatch.setattr(v29, "read_csv", lambda _path: rows)

    kickoff = datetime.fromisoformat("2026-07-03T18:00:00-04:00")

    assert v29.local_match_at_kickoff("2026-07-03", kickoff)["ground"] == "Miami (Miami Gardens)"


def test_knockout_placeholder_teams_resolve(monkeypatch):
    monkeypatch.setattr(
        v29,
        "knockout_resolutions",
        lambda: {"92": {"team1": "Mexico", "team2": "England"}},
    )

    assert v29.resolve_knockout_teams("92", "W79", "W80") == ("Mexico", "England")


def test_named_knockout_teams_are_not_overwritten(monkeypatch):
    monkeypatch.setattr(
        v29,
        "knockout_resolutions",
        lambda: {"92": {"team1": "Mexico", "team2": "England"}},
    )

    assert v29.resolve_knockout_teams("92", "Mexico", "England") == ("Mexico", "England")
