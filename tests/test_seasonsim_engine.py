"""Season simulator engine: tie-break procedures, invariants, determinism, scoreline models. No model, no store, no network."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from seasonsim import engine, rules, scoreline  # noqa: E402
from seasonsim.engine import K, SeasonInput  # noqa: E402


def season(played, names, fixtures=(), pmfs=None):
    idx = {n: i for i, n in enumerate(names)}
    ph = np.array([idx[m[0]] for m in played], dtype=int)
    pa = np.array([idx[m[1]] for m in played], dtype=int)
    hg = np.array([m[2] for m in played], dtype=int)
    ag = np.array([m[3] for m in played], dtype=int)
    fh = np.array([idx[f[0]] for f in fixtures], dtype=int)
    fa = np.array([idx[f[1]] for f in fixtures], dtype=int)
    pmf = np.zeros((len(fixtures), K, K)) if pmfs is None else pmfs
    return SeasonInput(teams=list(names), names=list(names), played_home=ph, played_away=pa, played_hg=hg, played_ag=ag, fix_home=fh, fix_away=fa, pmf=pmf)


def order(res, inp, n=0):
    return [inp.names[t] for t in np.argsort(res.pos[n])]


def prof(key):
    return rules.get_profile(key, "2026-27")


def two_club_case():
    # A and B level on 6 points. Overall GD: A +4, B +2. Head-to-head GD: B +1, A -1.
    played = [("A", "B", 1, 0), ("B", "A", 2, 0), ("A", "X", 5, 0), ("B", "Y", 1, 0)]
    return season(played, ["A", "B", "X", "Y"])


def multi_club_case():
    names = ["A", "B", "C", "D1", "D2", "D3", "D4"]
    m = []
    for q in ("B", "C"):                                          # A beats B and C home and away
        m += [("A", q, 1, 0), (q, "A", 0, 1)]
    m += [("B", "C", 0, 0), ("C", "B", 0, 0)]                     # B and C draw twice
    m += [("D1", "A", 1, 0), ("D2", "A", 1, 0), ("D3", "A", 1, 0), ("D4", "A", 1, 0)]   # A lost its 4 games vs dummies: 12 points
    for t, margin in (("B", 5), ("C", 1)):                         # B and C: 3 wins + 1 draw vs dummies = 10, plus 2 from each other = 12
        m += [(t, "D1", margin, 0), (t, "D2", margin, 0), (t, "D3", margin, 0), (t, "D4", 1, 1)]
    return season(m, names)


def test_tie_break_order_differs_by_league_for_two_clubs():
    inp = two_club_case()
    for key, expected_first in (("EPL", "A"), ("BUNDESLIGA", "A"), ("LALIGA", "B")):
        r = engine.simulate(inp, prof(key), n=20, seed=1)
        assert order(r, inp)[0] == expected_first, key        # goal difference first (EPL, BL); head-to-head goal difference first for two clubs (LL)
        assert len({tuple(order(r, inp, i)) for i in range(20)}) == 1


def test_multi_club_tie_uses_the_mini_table_in_la_liga_but_goal_difference_in_the_premier_league():
    inp = multi_club_case()
    la = order(engine.simulate(inp, prof("LALIGA"), n=5, seed=1), inp)[:3]
    assert la == ["A", "B", "C"]                                   # mini-table points: A 12 vs 2, 2; then B over C on overall goal difference
    assert order(engine.simulate(inp, prof("EPL"), n=5, seed=1), inp)[:3] == ["B", "C", "A"]          # overall goal difference first: B +13, C +1, A 0
    assert order(engine.simulate(inp, prof("BUNDESLIGA"), n=5, seed=1), inp)[:3] == ["B", "C", "A"]


def test_an_exact_tie_is_left_unresolved_never_decided_by_a_coin_and_probabilities_are_withheld():
    inp = season([("A", "B", 1, 1), ("B", "A", 1, 1)], ["A", "B"])
    r = engine.simulate(inp, prof("BUNDESLIGA"), n=2000, seed=3)
    assert len({tuple(r.pos[i]) for i in range(2000)}) == 1               # no randomness: the bookkeeping order is identical in every simulation
    s = engine.summarize(r, inp, prof("BUNDESLIGA"))
    assert s["final_position_probabilities_supported"] is False and "title" in s["bands_with_unresolved_ties"]
    assert s["tie_resolution"]["share_with_an_unresolved_tie"] == pytest.approx(1.0)
    for t in s["teams"]:
        assert t["p_title"] is None and t["p_title_low"] == 0.0 and t["p_title_high"] == 1.0           # only bounds
        assert t["expected_rank"] is None and t["position_unresolved_probability"] == 1.0 and sum(t["position_probabilities"]) == 0.0


def test_blocked_profiles_refuse_to_run():
    for key in ("SERIEA", "LIGUE1"):
        with pytest.raises(rules.RuleBlocked):
            rules.get_profile(key, "2026-27")
    with pytest.raises(rules.RuleBlocked):
        rules.get_profile("LALIGA", "2019-20")
    assert rules.profile_info("BUNDESLIGA", "2026-27")["usable"] and rules.profile_info("LALIGA", "2026-27")["usable"]


def test_every_usable_profile_has_a_primary_source_with_hash_and_date():
    for key in ("BUNDESLIGA", "LALIGA", "EPL"):
        info = rules.profile_info(key, "2026-27")
        assert info["usable"] and info["sources"] and all(s.get("sha256") and s.get("retrieved") and s["kind"].endswith("(primary)") for s in info["sources"])


def test_zero_remaining_fixtures_gives_the_real_table_with_probability_one():
    inp = two_club_case()
    r = engine.simulate(inp, prof("EPL"), n=50, seed=9)
    s = engine.summarize(r, inp, prof("EPL"))
    assert all(max(t["position_probabilities"]) == pytest.approx(1.0) for t in s["teams"])
    assert [t["name"] for t in s["teams"]][:2] in (["A", "B"], ["B", "A"])


def league(n_teams=6, seed=0):
    rng = np.random.default_rng(seed)
    names = [f"T{i}" for i in range(n_teams)]
    fixtures = [(a, b) for a in names for b in names if a != b]
    F = len(fixtures)
    p = rng.dirichlet([4, 2.5, 3], size=F)
    pmf = scoreline.conditional_poisson(p, rng.uniform(0.9, 2.0, F), rng.uniform(0.7, 1.6, F))
    return season([], names, fixtures, pmf), p


def test_invariants_probabilities_sum_to_one_and_same_seed_is_identical():
    inp, _ = league()
    pr = prof("EPL")
    a, b, c = (engine.simulate(inp, pr, n=2000, seed=s) for s in (5, 5, 6))
    assert np.array_equal(a.pos, b.pos) and np.array_equal(a.points, b.points)
    assert not np.array_equal(a.pos, c.pos)
    s = engine.summarize(a, inp, pr)
    mat = np.array([t["position_probabilities"] for t in s["teams"]])
    unres = np.array([t["position_unresolved_probability"] for t in s["teams"]])
    assert np.allclose(mat.sum(axis=1) + unres, 1)                                              # every simulation is either resolved or reported as unresolved
    assert sum(t["p_title_low"] for t in s["teams"]) <= 1.0 + 1e-9 <= sum(t["p_title_high"] for t in s["teams"]) + 2e-9
    if s["final_position_probabilities_supported"]:
        assert np.allclose(mat.sum(axis=0), 1) and sum(t["p_title"] for t in s["teams"]) == pytest.approx(1.0)
    assert all(0 <= t["p_top4_low"] <= t["p_top4_high"] <= 1 for t in s["teams"])
    assert sum(t["expected_points"] for t in s["teams"]) <= 3 * len(inp.fix_home)       # points come only from results (3 per decided match, 2 per draw)


def test_sampled_outcome_frequencies_reproduce_the_input_probabilities():
    inp, p = league(4, 2)
    n = 20000
    rng = np.random.default_rng([3, 0])
    sh, sa = engine._sample_scores(inp.pmf, n, rng)
    freq = np.stack([(sh > sa).mean(axis=0), (sh == sa).mean(axis=0), (sh < sa).mean(axis=0)], axis=1)
    assert np.abs(freq - p).max() < 0.012                                        # about 3 standard errors at n=20000


def test_monotonic_a_stronger_club_never_has_lower_expected_points():
    inp, _ = league(4, 1)
    pr = prof("EPL")
    base = engine.summarize(engine.simulate(inp, pr, n=6000, seed=4), inp, pr)
    t0 = next(t for t in base["teams"] if t["name"] == "T0")
    pmf = inp.pmf.copy()
    for f, (h, a) in enumerate(zip(inp.fix_home, inp.fix_away)):
        if h == 0 or a == 0:                                                     # shift T0's matches towards T0 winning
            g = np.zeros((K, K)); g[2, 0] = 1.0
            pmf[f] = 0.5 * pmf[f] + 0.5 * (g if h == 0 else g.T)
    inp2 = SeasonInput(**{**inp.__dict__, "pmf": pmf})
    t1 = next(t for t in engine.summarize(engine.simulate(inp2, pr, n=6000, seed=4), inp2, pr)["teams"] if t["name"] == "T0")
    assert t1["expected_points"] > t0["expected_points"]


# ----------------------------------------------------------------------------------------------------------- scoreline models
def test_scoreline_pmfs_sum_to_one_and_respect_the_model_outcome_probabilities():
    rng = np.random.default_rng(1)
    lh, la = rng.uniform(0.8, 2.2, 40), rng.uniform(0.6, 1.8, 40)
    p = scoreline.outcome_marginals(scoreline.conditional_poisson(np.full((40, 3), 1 / 3), lh * 1.1, la * 0.95))   # realistic probabilities (a model's, not arbitrary triples)
    s1, _ = scoreline.build_pmf("S1", p, lh, la, "X")
    s2, i2 = scoreline.build_pmf("S2", p, lh, la, "X")
    for pmf in (s1, s2):
        assert np.allclose(pmf.reshape(40, -1).sum(axis=1), 1)
    assert np.allclose(scoreline.outcome_marginals(s1), p, atol=1e-9)
    assert np.allclose(scoreline.outcome_marginals(s2), p, atol=1e-5)
    assert i2["fallback_fixtures"] == 0
    odd = np.array([[0.99995, 0.00003, 0.00002]])                          # needs more than 8 expected goals: reported as a fallback, never hidden
    _, info = scoreline.build_pmf("S2", odd, np.array([1.4]), np.array([1.1]), "X")
    assert info["fallback_fixtures"] == 1


def test_conditional_poisson_never_puts_mass_on_scores_inconsistent_with_the_outcome():
    p = np.array([[1.0, 0.0, 0.0]])
    pmf, _ = scoreline.build_pmf("S1", p, np.array([1.4]), np.array([1.1]), "X")
    assert pmf[0][~(scoreline._HOME)].sum() < 1e-6


def test_empirical_scoreline_model_keeps_outcome_probabilities_and_needs_a_fit():
    rng = np.random.default_rng(2)
    n = 3000
    x = rng.normal(0.3, 0.6, n)
    hg = rng.poisson(np.clip(1.4 + x / 2, 0.2, None)); ag = rng.poisson(np.clip(1.1 - x / 2, 0.2, None))
    emp = scoreline.Empirical().fit(np.array(["L"] * n), x, hg, ag)
    p = rng.dirichlet([4, 2.5, 3], size=25)
    pmf, _ = scoreline.build_pmf("S3", p, np.full(25, 1.5), np.full(25, 1.1), "L", empirical=emp)
    assert np.allclose(pmf.reshape(25, -1).sum(axis=1), 1)
    assert np.allclose(scoreline.outcome_marginals(pmf), p / p.sum(axis=1, keepdims=True), atol=1e-9)
    with pytest.raises(ValueError):
        scoreline.build_pmf("S3", p, np.full(25, 1.5), np.full(25, 1.1), "L")
    pmf2, info = scoreline.build_pmf("S1", p, np.full(25, np.nan), np.full(25, 1.1), "L")
    assert info["missing_expected_goals"] == 25 and np.isfinite(pmf2).all()


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


def test_la_liga_profile_carries_a_pending_live_confirmation_and_the_others_do_not():
    assert "PENDING" in rules.profile_info("LALIGA", "2026-27")["live_confirmation"]
    assert "35b0a9e4a011325a5dd1144b790cf986bdcdb33a2c2b1c4cf6fed7872d6146ac" in rules.profile_info("LALIGA", "2026-27")["live_confirmation"]
    assert rules.profile_info("BUNDESLIGA", "2026-27")["live_confirmation"] is None
