

# ----------------------------------------------------------------------------------------------------------- points-only mode
from seasonsim import pointsonly  # noqa: E402


def test_points_only_awards_3_1_0_and_conserves_points():
    fh = np.array([0, 2, 1])
    fa = np.array([1, 3, 0])
    probs = np.array([[0.5, 0.3, 0.2], [0.2, 0.3, 0.5], [0.6, 0.2, 0.2]])
    base = np.array([10, 20, 5, 7])
    pts = pointsonly.simulate_points(base, fh, fa, probs, 5000, 1)
    gained = pts - base
    assert gained.min() >= 0
    assert gained.sum(axis=1).min() >= 2 * 3 and gained.sum(axis=1).max() <= 3 * 3                    # each match adds 2 (draw) or 3 points to the table
    assert np.array_equal(pts, pointsonly.simulate_points(base, fh, fa, probs, 5000, 1)) and not np.array_equal(pts, pointsonly.simulate_points(base, fh, fa, probs, 5000, 2))
    exp_t0 = (3 * 0.5 + 0.3 * 1) + (3 * 0.2 + 0.2 * 1)                                               # team 0: home in fixture 0, away in fixture 2
    assert abs(gained[:, 0].mean() - exp_t0) < 0.06


def test_points_only_frequencies_match_the_probabilities_and_zero_fixtures_is_deterministic():
    pts = pointsonly.simulate_points(np.array([0, 0]), np.array([0]), np.array([1]), np.array([[0.55, 0.25, 0.20]]), 40000, 4)
    assert abs((pts[:, 0] == 3).mean() - 0.55) < 0.012 and abs((pts[:, 0] == 1).mean() - 0.25) < 0.012 and abs((pts[:, 1] == 3).mean() - 0.20) < 0.012
    none = pointsonly.simulate_points(np.array([7, 9]), np.array([], dtype=int), np.array([], dtype=int), np.zeros((0, 3)), 10, 1)
    assert (none == np.array([7, 9])).all()


def test_points_only_summary_has_distributions_and_no_positions():
    base = np.array([3, 3, 0])
    pts = pointsonly.simulate_points(base, np.array([0, 1, 2]), np.array([1, 2, 0]), np.array([[0.4, 0.3, 0.3]] * 3), 3000, 9)
    s = pointsonly.summarize_points(pts, ["a", "b", "c"], ["A", "B", "C"], base, np.array([2, 2, 2]), 9)
    for t in s["teams"]:
        d = t["distribution"]
        assert sum(d["probabilities"]) == pytest.approx(1.0) and d["first_points"] == t["points_min"]
        assert t["points_p10"] <= t["points_median"] <= t["points_p90"] and t["remaining_fixtures"] == 2
        assert t["expected_points"] == pytest.approx(sum((d["first_points"] + i) * p for i, p in enumerate(d["probabilities"])))
        assert not any(k.startswith(("p_", "position", "expected_rank")) for k in t)                # nothing that implies a table position
    assert "no finishing position" in s["ordering"]
