"""Prototype: rigorous position-probability bounds from points-only simulations. Soundness is checked by brute force against the real tie-break engine; edge cases are designed by hand."""
import itertools
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from seasonsim import engine, pointbounds, pointsonly, rules  # noqa: E402
from seasonsim.engine import K, SeasonInput  # noqa: E402


def prof(key):
    return rules.get_profile(key, "2026-27")


def make(names, played, fixtures):
    idx = {n: i for i, n in enumerate(names)}
    z = np.zeros((len(fixtures), K, K))
    return SeasonInput(teams=list(names), names=list(names), played_home=np.array([idx[m[0]] for m in played], dtype=int), played_away=np.array([idx[m[1]] for m in played], dtype=int),
                       played_hg=np.array([m[2] for m in played], dtype=int), played_ag=np.array([m[3] for m in played], dtype=int),
                       fix_home=np.array([idx[f[0]] for f in fixtures], dtype=int), fix_away=np.array([idx[f[1]] for f in fixtures], dtype=int), pmf=z)


def bounds_for(inp, key, outcome_rows, use=True):
    return pointbounds.position_bounds(inp, prof(key), np.array(outcome_rows, dtype=int).reshape(len(outcome_rows), len(inp.fix_home)), use)


def brute(inp, key, outcome_vec, G=3):
    """Every position each club can take over all score completions (0..G goals) of the fixtures consistent with the outcome vector, using the real engine; unresolved ties expand."""
    F, T = len(inp.fix_home), len(inp.teams)
    options = []
    for code in outcome_vec:
        options.append([(h, a) for h in range(G + 1) for a in range(G + 1) if (h > a and code == 0) or (h == a and code == 1) or (h < a and code == 2)])
    seen = [set() for _ in range(T)]
    for combo in itertools.product(*options):
        pmf = np.zeros((F, K, K))
        for f, (h, a) in enumerate(combo):
            pmf[f, h, a] = 1.0
        i2 = SeasonInput(**{**inp.__dict__, "pmf": pmf})
        r = engine.simulate(i2, prof(key), n=1, seed=1)
        for t in range(T):
            seen[t].add(int(r.pos[0, t]))
        for _s, ev in r.terminal_events["per_sim"]:
            for start, size, _k, members in ev["terminal"]:
                for t in members:
                    seen[t].update(range(start, start + size))
    return seen


def random_case(rng, T=4, F=3):
    names = [f"C{i}" for i in range(T)]
    pairs = [(a, b) for a in names for b in names if a != b]
    rng.shuffle(pairs)
    fixtures, played = pairs[:F], []
    for a, b in pairs[F:]:
        played.append((a, b, int(rng.integers(0, 3)), int(rng.integers(0, 3))))
    return names, played, fixtures


@pytest.mark.parametrize("key", ["BUNDESLIGA", "EPL", "LALIGA"])
def test_bounds_contain_every_position_reachable_by_some_scores_brute_force(key):
    rng = np.random.default_rng(7)
    tight = total = 0
    for _ in range(14):
        names, played, fixtures = random_case(rng)
        inp = make(names, played, fixtures)
        vectors = list(itertools.product((0, 1, 2), repeat=len(fixtures)))
        b = bounds_for(inp, key, vectors)
        for v, vec in enumerate(vectors):
            reach = brute(inp, key, vec)
            for t in range(len(names)):
                lo, hi = min(reach[t]), max(reach[t])
                assert b.best[v, t] <= lo and b.worst[v, t] >= hi, (key, played, fixtures, vec, names[t], reach[t], b.best[v, t], b.worst[v, t])      # sound: never too narrow
                total += 1
                tight += (b.best[v, t] == lo and b.worst[v, t] == hi)
    assert tight / total > 0.5                                                                           # informative, not vacuous (the rest is conservative, by design)


def test_with_nothing_left_to_play_the_bounds_equal_the_engines_table_when_ties_are_pairs():
    rng = np.random.default_rng(3)
    checked = 0
    for _ in range(60):
        names = [f"C{i}" for i in range(5)]
        played = [(a, b, int(rng.integers(0, 4)), int(rng.integers(0, 4))) for a in names for b in names if a != b]
        inp = make(names, played, [])
        for key in ("BUNDESLIGA", "EPL", "LALIGA"):
            b = pointbounds.position_bounds(inp, prof(key), np.zeros((1, 0), dtype=int))
            r = engine.simulate(inp, prof(key), n=1, seed=1)
            groups = {}
            for t in range(5):
                groups.setdefault(int(b.points[0, t]), []).append(t)
            if r.terminal_events["per_sim"] or any(len(g) > 2 for g in groups.values()):
                continue                                                                                   # unresolved ties or multi-club groups: bounds may legitimately be wider
            assert (b.best[0] == r.pos[0]).all() and (b.worst[0] == r.pos[0]).all(), (key, played)
            checked += 1
    assert checked > 40


def test_two_level_clubs_head_to_head_decides_in_la_liga_but_goal_difference_decides_in_the_bundesliga():
    # A and B level on 6 points; overall goal difference A +4, B +2; head-to-head goal difference B +1, A -1 (the same case as the engine test)
    names = ["A", "B", "X", "Y"]
    played = [("A", "B", 1, 0), ("B", "A", 2, 0), ("A", "X", 5, 0), ("B", "Y", 1, 0)]
    inp = make(names, played, [])
    zero = np.zeros((1, 0), dtype=int)
    for key, first in (("LALIGA", "B"), ("BUNDESLIGA", "A"), ("EPL", "A")):
        b = pointbounds.position_bounds(inp, prof(key), zero)
        i = names.index(first)
        assert b.best[0, i] == b.worst[0, i] == 1, key
    assert (pointbounds.position_bounds(inp, prof("LALIGA"), zero).best[0, 2:] >= 3).all()


def test_a_club_with_only_draws_left_has_an_exact_goal_difference_and_can_be_ordered_with_certainty():
    names = ["A", "B", "C", "D"]
    played = [("A", "C", 3, 0), ("B", "D", 1, 0)]
    fixtures = [("D", "A"), ("C", "B")]                     # both remaining matches are draws: A and B finish on 4 points, goal difference A +3, B +1
    inp = make(names, played, fixtures)
    b = pointbounds.position_bounds(inp, prof("BUNDESLIGA"), np.array([[1, 1]]))
    assert b.best[0, 0] == b.worst[0, 0] == 1 and b.best[0, 1] == b.worst[0, 1] == 2
    naive = pointbounds.position_bounds(inp, prof("BUNDESLIGA"), np.array([[1, 1]]), use_known_information=False)
    assert naive.best[0, 0] == 1 and naive.worst[0, 0] == 2                  # without the known information the tie would stay open


def test_a_pending_win_and_a_pending_loss_leave_the_goal_difference_order_open_but_one_sided_remainders_do_not():
    names = ["A", "B", "C", "D"]
    # both A and B have an away win left (goal difference can only rise, no upper limit): level on 6 points, order unresolved
    inp = make(names, [("A", "C", 1, 0), ("B", "D", 2, 0)], [("D", "A"), ("C", "B")])
    b = pointbounds.position_bounds(inp, prof("BUNDESLIGA"), np.array([[2, 2]]))
    assert b.points[0, 0] == b.points[0, 1] == 6
    assert (b.best[0, :2] == 1).all() and (b.worst[0, :2] == 2).all()
    # A (goal difference +1) has a defeat left, so its goal difference ends at 0 or lower; B (+2) has nothing left: when they finish level on points B is definitely above A
    inp2 = make(names, [("A", "C", 1, 0), ("B", "D", 2, 0)], [("D", "A")])
    b2 = pointbounds.position_bounds(inp2, prof("BUNDESLIGA"), np.array([[0]]))             # D beats A: A 3 points, B 3 points, D 3 points
    assert b2.points[0, 0] == b2.points[0, 1] == b2.points[0, 3] == 3 and b2.points[0, 2] == 0
    assert b2.best[0, 0] == 2 and b2.worst[0, 1] == 2                                         # A cannot finish above B; B cannot finish below A
    assert b2.best[0, 3] == 1 and b2.worst[0, 3] == 3                                         # D (goal difference at least -1, no upper limit) stays open against both


def test_a_cycle_of_equal_mini_table_results_stays_open_because_the_rule_text_is_silent_about_it():
    names = ["A", "B", "C", "D"]
    cyc = [("A", "B", 1, 0), ("B", "A", 0, 0), ("B", "C", 1, 0), ("C", "B", 0, 0), ("C", "A", 1, 0), ("A", "C", 0, 0)]       # each of A, B, C: 5 mini-table points, mini goal difference 0
    done = make(names, cyc + [("A", "D", 3, 0), ("D", "A", 0, 0), ("B", "D", 1, 0), ("D", "B", 0, 0), ("C", "D", 2, 0), ("D", "C", 0, 0)], [])
    zero = np.zeros((1, 0), dtype=int)
    b = pointbounds.position_bounds(done, prof("LALIGA"), zero)
    # three clubs level on points AND in the mini-table: art. 10 only passes to the next criterion when two clubs remain level, so the text decides nothing here: unresolved among themselves
    assert (b.best[0, :3] == 1).all() and (b.worst[0, :3] == 3).all() and b.best[0, 3] == b.worst[0, 3] == 4
    legacy = pointbounds.position_bounds(done, dict(prof("LALIGA"), bounds_multi_club_prefix=None), zero)                      # the prototype continued down the list: exact order by overall goal difference
    assert (legacy.best[0, :3] == legacy.worst[0, :3]).all() and sorted(legacy.best[0, :3]) == [1, 2, 3]
    open_ = make(names, cyc + [("A", "D", 3, 0), ("D", "A", 0, 0), ("B", "D", 1, 0), ("D", "B", 0, 0)], [("C", "D"), ("D", "C")])
    b2 = pointbounds.position_bounds(open_, prof("LALIGA"), np.array([[0, 1]]))                    # C still has a win and a draw to play
    tied = [t for t in range(3) if b2.points[0, t] == b2.points[0, 0]]
    assert len(tied) == 3 and not (b2.best[0, :3] == b2.worst[0, :3]).all()


def reading_case():
    """A, B, C level on 8 points; A and B level on 7 mini-table points (C has 2). Head-to-head goal difference over the whole group puts A above B (+4 v +3); between the two clubs only it puts B above A (-2 v +2)."""
    names = ["A", "B", "C", "D"]
    played = [("A", "B", 1, 0), ("B", "A", 3, 0), ("A", "C", 6, 0), ("C", "A", 0, 0), ("B", "C", 1, 0), ("C", "B", 0, 0), ("A", "D", 0, 0), ("B", "D", 0, 0), ("C", "D", 1, 0), ("D", "C", 0, 1)]
    return names, make(names, played, [])


def test_the_prefix_keeps_the_bounds_true_under_both_readings_of_the_la_liga_multi_club_rule():
    from seasonsim import m5_bounds_validation as V

    names, inp = reading_case()
    zero = np.zeros((1, 0), dtype=int)
    p = prof("LALIGA")
    assert (pointbounds.position_bounds(inp, p, zero).points[0] == [8, 8, 8, 2]).all()
    pos_i, _ = V.engine_positions(inp, p, np.zeros((1, 0), dtype=np.int16), np.zeros((1, 0), dtype=np.int16))                                      # mini-table over the original group
    pos_ii, _ = V.engine_positions(inp, dict(p, h2h_scope="current_group"), np.zeros((1, 0), dtype=np.int16), np.zeros((1, 0), dtype=np.int16))    # only the clubs still level
    assert pos_i[0, 0] == 1 and pos_i[0, 1] == 2 and pos_ii[0, 1] == 1 and pos_ii[0, 0] == 2                      # the two readings really disagree about A and B
    legacy = pointbounds.position_bounds(inp, dict(p, bounds_multi_club_prefix=None), zero)
    assert legacy.best[0, 0] == legacy.worst[0, 0] == 1                                                              # the prototype followed one reading: unsound under the other
    robust = pointbounds.position_bounds(inp, p, zero)
    for pos in (pos_i, pos_ii):
        assert (robust.best[0] <= pos[0]).all() and (pos[0] <= robust.worst[0]).all()
    assert robust.best[0, 0] == robust.best[0, 1] == 1 and robust.worst[0, 0] == robust.worst[0, 1] == 2           # A and B stay open; C (2 mini-table points) is surely third; D last
    assert robust.best[0, 2] == robust.worst[0, 2] == 3 and robust.best[0, 3] == robust.worst[0, 3] == 4


def test_bundesliga_uses_only_overall_goal_difference_and_goals_scored_for_three_or_more_clubs():
    names = ["A", "B", "C", "D"]
    # B beats A twice, C beats B twice, A beats C twice (a cycle: 6 points each among them) and all three beat or draw D: A, B, C finish level on 10 points with goal differences +3, +2, +1
    played = [("A", "D", 3, 0), ("B", "D", 2, 0), ("C", "D", 1, 0), ("D", "A", 0, 0), ("D", "B", 0, 0), ("D", "C", 0, 0), ("A", "B", 0, 1), ("B", "A", 1, 0), ("B", "C", 0, 1), ("C", "B", 1, 0), ("C", "A", 0, 1), ("A", "C", 1, 0)]
    inp = make(names, played, [])
    zero = np.zeros((1, 0), dtype=int)
    b = pointbounds.position_bounds(inp, prof("BUNDESLIGA"), zero)
    assert list(b.points[0]) == [10, 10, 10, 3]
    assert [int(x) for x in b.best[0]] == [int(x) for x in b.worst[0]] == [1, 2, 3, 4]                       # overall goal difference separates all three exactly
    ll = pointbounds.position_bounds(inp, prof("LALIGA"), zero)                                               # La Liga: a cycle in the mini-table decides nothing and the text is silent beyond it
    assert (ll.best[0, :3] == 1).all() and (ll.worst[0, :3] == 3).all() and ll.best[0, 3] == ll.worst[0, 3] == 4


def test_refined_bounds_are_never_wider_than_the_naive_tie_bounds_and_guaranteed_never_exceeds_possible():
    rng = np.random.default_rng(11)
    names, played, fixtures = random_case(rng, 5, 5)
    inp = make(names, played, fixtures)
    probs = rng.dirichlet([4, 2.5, 3], size=len(fixtures))
    oc = pointbounds.draw_outcomes(probs, 500, 5)
    for key in ("BUNDESLIGA", "LALIGA", "EPL"):
        ref = pointbounds.position_bounds(inp, prof(key), oc)
        nai = pointbounds.position_bounds(inp, prof(key), oc, use_known_information=False)
        assert (ref.best >= nai.best).all() and (ref.worst <= nai.worst).all()
        s = pointbounds.band_summary(ref, {"bands": {"title": [1], "top4": [1, 2], "relegation": [4, 5]}}, inp)
        for band in s.values():
            for c in band["clubs"]:
                assert 0 <= c["guaranteed"] <= c["possible"] <= 1 and c["unresolved"] == pytest.approx(c["possible"] - c["guaranteed"])
        assert sum(c["guaranteed"] for c in s["title"]["clubs"]) <= 1 + 1e-9 <= sum(c["possible"] for c in s["title"]["clubs"]) + 1e-9


def test_outcomes_use_the_same_random_stream_as_the_points_only_simulation():
    rng = np.random.default_rng(2)
    probs = rng.dirichlet([4, 2.5, 3], size=6)
    fh, fa = np.array([0, 1, 2, 3, 0, 2]), np.array([1, 2, 3, 0, 2, 0])
    base = np.array([5, 6, 7, 8])
    pts = pointsonly.simulate_points(base, fh, fa, probs, 300, 9)
    names = list("ABCD")
    inp = SeasonInput(teams=names, names=names, played_home=np.array([], dtype=int), played_away=np.array([], dtype=int), played_hg=np.array([], dtype=int), played_ag=np.array([], dtype=int),
                      fix_home=fh, fix_away=fa, pmf=np.zeros((6, K, K)))
    oc = pointbounds.draw_outcomes(probs, 300, 9)
    ctx = pointbounds._Ctx(inp, prof("EPL"), oc, True)
    assert np.array_equal(ctx.points + base, pts)


def test_the_known_gaps_stay_open_no_information_no_certainty():
    names = ["A", "B", "C"]
    inp = make(names, [], [("A", "B"), ("B", "A")])
    b = pointbounds.position_bounds(inp, prof("LALIGA"), np.array([[1, 1]]))               # two draws: A and B level on 2 points, head-to-head goal difference exactly 0, goal difference unknown to be equal? both exact 0
    assert b.points[0, 0] == b.points[0, 1] == 2 and b.points[0, 2] == 0
    assert b.best[0, 2] == b.worst[0, 2] == 3
    # equal on every known criterion but the final deciders (fair play / neutral match) are outside the information: unresolved
    assert (b.best[0, :2] == 1).all() and (b.worst[0, :2] == 2).all()


def test_a_finished_season_has_no_remaining_fixtures_and_an_empty_outcome_stream():
    oc = pointbounds.draw_outcomes(np.zeros((0, 3)), 5, 1)
    assert oc.shape == (5, 0)
    names = ["A", "B", "C"]
    inp = make(names, [("A", "B", 1, 0), ("B", "A", 0, 0), ("A", "C", 2, 0), ("C", "A", 0, 1), ("B", "C", 1, 0), ("C", "B", 0, 0)], [])
    b = pointbounds.position_bounds(inp, prof("BUNDESLIGA"), oc)
    assert b.best.shape == (5, 3) and (b.best == b.worst).all() and (b.best[0] == [1, 2, 3]).all()
