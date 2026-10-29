import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import simulate_live_tournament_v213 as v213


def test_find_actual_result_prefers_exact_date():
    results = {
        v213.result_key("2026-06-13", "Australia", "Turkey"): (1, 0, "exact"),
        v213.result_key("2026-06-14", "Australia", "Turkey"): (2, 0, "other"),
    }

    assert v213.find_actual_result(results, "2026-06-13", "Australia", "Turkey") == (1, 0, "exact")


def test_find_actual_result_uses_unique_pairing_when_schedule_date_is_stale():
    results = {
        v213.result_key("2026-06-14", "Australia", "Turkey"): (2, 0, "provider"),
    }

    assert v213.find_actual_result(results, "2026-06-13", "Australia", "Turkey") == (
        2,
        0,
        "actual_result_locked_pairing_fallback",
    )


def test_find_actual_result_rejects_ambiguous_pairing_fallback():
    results = {
        v213.result_key("2026-06-14", "Australia", "Turkey"): (2, 0, "first"),
        v213.result_key("2026-07-10", "Australia", "Turkey"): (0, 1, "second"),
    }

    assert v213.find_actual_result(results, "2026-06-13", "Australia", "Turkey") is None


def test_actual_knockout_winner_locks_resolved_result():
    results = {
        v213.result_key("2026-06-28", "South Africa", "Canada"): (0, 1, "provider"),
    }

    assert v213.actual_knockout_winner(results, "2026-06-28", "South Africa", "Canada") == "Canada"


def test_actual_knockout_winner_does_not_guess_shootout_winner_from_draw():
    results = {
        v213.result_key("2026-06-28", "South Africa", "Canada"): (1, 1, "provider"),
    }

    assert v213.actual_knockout_winner(results, "2026-06-28", "South Africa", "Canada") is None


def test_verified_knockout_winner_handles_penalty_result():
    results = {
        "74": {
            "team1": "Germany",
            "team2": "Paraguay",
            "winner": "Paraguay",
        }
    }

    assert v213.verified_knockout_winner(results, "74", "Germany", "Paraguay") == "Paraguay"


def test_verified_knockout_winner_rejects_wrong_resolved_pairing():
    results = {
        "74": {
            "team1": "Germany",
            "team2": "Paraguay",
            "winner": "Paraguay",
        }
    }

    assert v213.verified_knockout_winner(results, "74", "Germany", "Sweden") is None
