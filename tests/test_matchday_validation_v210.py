from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_matchday_v210 as v210


class MatchdayValidationV210Tests(unittest.TestCase):
    def test_snapshot_selection_deduplicates_fixture_when_provider_id_arrives_later(self):
        rows = [
            {
                "fixture_key": "local-brazil-norway",
                "provider_fixture_id": "",
                "date": "2026-07-05",
                "time_et": "16:00",
                "team1": "Brazil",
                "team2": "Norway",
                "snapshot_timestamp_et": "2026-07-04T10:00:00-04:00",
            },
            {
                "fixture_key": "provider-brazil-norway",
                "provider_fixture_id": "12345",
                "date": "2026-07-05",
                "time_et": "16:00",
                "team1": "Brazil",
                "team2": "Norway",
                "snapshot_timestamp_et": "2026-07-05T12:00:00-04:00",
            },
        ]

        selected = v210.select_prediction_rows(rows, "2026-07-05")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["provider_fixture_id"], "12345")
        self.assertEqual(selected[0]["snapshots_seen"], 2)

    def test_date_merge_preserves_other_dates_and_replaces_target(self):
        existing = [
            {"fixture_key": "old", "date": "2026-06-22", "provider_status": "NS", "provider_error": ""},
            {"fixture_key": "keep", "date": "2026-06-21", "provider_status": "FT", "provider_error": ""},
        ]
        fresh = [{"fixture_key": "old", "date": "2026-06-22", "provider_status": "FT", "provider_error": ""}]
        merged = v210.merge_date_rows(existing, fresh, "2026-06-22")
        by_key = {row["fixture_key"]: row for row in merged}
        self.assertEqual(by_key["old"]["provider_status"], "FT")
        self.assertEqual(by_key["keep"]["provider_status"], "FT")

    def test_date_merge_does_not_replace_good_result_with_provider_error(self):
        existing = [
            {"fixture_key": "match", "date": "2026-06-22", "provider_status": "FT", "provider_error": ""}
        ]
        fresh = [
            {"fixture_key": "match", "date": "2026-06-22", "provider_status": "", "provider_error": "rate limited"}
        ]
        merged = v210.merge_date_rows(existing, fresh, "2026-06-22")
        self.assertEqual(merged[0]["provider_status"], "FT")
        self.assertEqual(merged[0]["provider_error"], "")

    def test_regulation_goals_uses_fulltime_for_extra_time_fixture(self):
        response = {
            "goals": {"home": 3, "away": 2},
            "score": {"fulltime": {"home": 2, "away": 2}, "extratime": {"home": 3, "away": 2}},
        }

        self.assertEqual(v210.regulation_goals(response, "AET"), (2, 2, False))

    def test_regulation_goals_withholds_unresolved_extra_time_fixture(self):
        response = {
            "goals": {"home": 3, "away": 2},
            "score": {"fulltime": {"home": None, "away": None}},
        }

        self.assertEqual(v210.regulation_goals(response, "AET"), (3, 2, True))


if __name__ == "__main__":
    unittest.main()
