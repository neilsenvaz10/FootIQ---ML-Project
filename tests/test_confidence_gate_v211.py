from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_confidence_gate_v211 as v211


class ConfidenceGateV211Tests(unittest.TestCase):
    def classify(self, probabilities, *, ensemble="team1_win", logistic="team1_win", internal="team1_win", lineups=True, xg_margin=1.0):
        return v211.classify_v211(
            probabilities=probabilities,
            labels=v211.GENERIC_LABELS,
            ensemble_public=ensemble,
            logistic_public=logistic,
            internal_pick=internal,
            data_quality=88.0 if lineups else 78.0,
            lineups_available=lineups,
            xg_margin=xg_margin,
            live_mode=True,
        )

    def test_verified_clear_favorite_can_be_strong(self):
        gate = self.classify({"team1_win": 0.832, "draw": 0.136, "team2_win": 0.032})
        self.assertEqual(gate["v211_tier"], "Strong Pick")
        self.assertEqual(gate["v211_pick"], "team1_win")

    def test_consensus_without_lineups_is_not_strong(self):
        gate = self.classify(
            {"team1_win": 0.832, "draw": 0.136, "team2_win": 0.032},
            lineups=False,
        )
        self.assertEqual(gate["v211_tier"], "Pass")
        self.assertIn("lineup", gate["v211_reason"].lower())

    def test_close_xg_and_draw_risk_force_pass(self):
        gate = self.classify(
            {"team1_win": 0.702, "draw": 0.224, "team2_win": 0.074},
            logistic="pass",
            lineups=False,
            xg_margin=0.48,
        )
        self.assertEqual(gate["v211_tier"], "Pass")
        self.assertTrue(gate["v211_draw_watch"])

    def test_clear_non_consensus_direction_can_remain_lean(self):
        gate = self.classify(
            {"team1_win": 0.739, "draw": 0.213, "team2_win": 0.048},
            logistic="pass",
            lineups=False,
            xg_margin=0.78,
        )
        self.assertEqual(gate["v211_tier"], "Model Lean")
        self.assertEqual(gate["v211_pick"], "team1_win")

    def test_calibrated_probabilities_sum_to_one(self):
        calibrated = v211.calibrated_probabilities(
            {"team1_win": 0.58, "draw": 0.29, "team2_win": 0.13},
            v211.GENERIC_LABELS,
        )
        self.assertAlmostEqual(sum(calibrated.values()), 1.0)
        self.assertGreater(calibrated["draw"], 0.29)


if __name__ == "__main__":
    unittest.main()
