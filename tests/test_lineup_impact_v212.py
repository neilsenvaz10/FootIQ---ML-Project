from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_lineup_impact_v212 as v212


class LineupImpactV212Tests(unittest.TestCase):
    def test_fuzzy_same_team_player_match(self):
        by_team, exact = v212.player_index()
        player, method, similarity = v212.match_player("Akam Hashem", "Iraq", by_team, exact)
        self.assertIsNotNone(player)
        self.assertEqual(player["player_name"], "Akam Hashim")
        self.assertEqual(method, "fuzzy")
        self.assertGreaterEqual(similarity, v212.V212_CONFIG["fuzzy_player_match_threshold"])

    def test_probability_adjustment_is_normalized_and_capped(self):
        base = {"team1_win": 0.45, "draw": 0.30, "team2_win": 0.25}
        adjusted, _, _ = v212.adjust_probabilities(base, 50.0, -50.0)
        self.assertAlmostEqual(sum(adjusted.values()), 1.0)
        for label in v212.LABELS:
            self.assertLessEqual(
                abs(adjusted[label] - base[label]),
                v212.V212_CONFIG["maximum_probability_movement"] + 1e-9,
            )

    def test_missing_lineups_inherit_v211(self):
        row = {"v211_tier": "Model Lean", "v211_pick": "team1_win"}
        decision = v212.classify_v212(
            row,
            {"team1_win": 0.65, "draw": 0.25, "team2_win": 0.10},
            False,
        )
        self.assertEqual(decision["v212_tier"], "Model Lean")
        self.assertEqual(decision["v212_pick"], "team1_win")

    def test_v211_pass_cannot_be_promoted(self):
        row = {"v211_tier": "Pass", "v211_pick": "pass"}
        decision = v212.classify_v212(
            row,
            {"team1_win": 0.80, "draw": 0.15, "team2_win": 0.05},
            True,
        )
        self.assertEqual(decision["v212_tier"], "Pass")
        self.assertEqual(decision["v212_pick"], "pass")

    def test_lineup_adjustment_can_downgrade_weak_edge(self):
        row = {"v211_tier": "Model Lean", "v211_pick": "team1_win"}
        decision = v212.classify_v212(
            row,
            {"team1_win": 0.48, "draw": 0.32, "team2_win": 0.20},
            True,
        )
        self.assertEqual(decision["v212_tier"], "Pass")
        self.assertTrue(decision["v212_changed_call"])


if __name__ == "__main__":
    unittest.main()
