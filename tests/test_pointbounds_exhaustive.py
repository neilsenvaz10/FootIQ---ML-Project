"""Position bounds validated against the REAL tie-break engine.

  * exhaustive small leagues: every win / draw / loss pattern of the unplayed matches and every score completion up to 3 goals per team, ranked by the real engine under every reading of the
    rule text it can express; every position the engine can produce must lie inside the bounds;
  * the real Bundesliga and La Liga 2026-27 state at realistic scale (random patterns, random consistent scores);
  * invariants: lower bound never above upper bound, everything between 0 and 100%, places add up, bands nest;
  * the engine oracle used here is the engine (same positions as engine.simulate).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from seasonsim import engine, pointbounds, rules  # noqa: E402
from seasonsim import m5_bounds_validation as V  # noqa: E402
from seasonsim.engine import K, SeasonInput  # noqa: E402
from store import db as store_db  # noqa: E402

PROD = ROOT / "data" / "footiq.sqlite"
needs_store = pytest.mark.skipif(not PROD.exists(), reason="results store not built")
KEYS = ["BUNDESLIGA", "LALIGA"]


@pytest.mark.parametrize("key", KEYS)
def test_exhaustive_small_leagues_every_position_the_real_engine_can_produce_lies_inside_the_bounds(key):
    rng = np.random.default_rng(21)
    tot = dict(violations=0, naive_violations=0, completions=0, tight=0, tight_checks=0, groups3=0, groups2=0, blocks=0, checks=0)
    for i in range(14):
        T, F = (4, 4) if i % 2 else (5, 3)
        names, played, fx = V.random_league(rng, T, F, gmax=1 if i % 3 else 2)
        r = V.exhaustive_case(V.make(names, played, fx), key, 3)
        assert all(x["violations"] == 0 for x in r["by_reading"].values()), (key, played, fx, r["by_reading"])
        tot["violations"] += r["violations"]
        tot["naive_violations"] += r["naive_violations"]
        tot["completions"] += r["completions"]
        tot["tight"] += r["tight"]
        tot["tight_checks"] += r["tight_checks"]
        tot["groups3"] += r["tie_groups_of_three_or_more"]
        tot["groups2"] += r["tie_groups_of_two"]
        tot["blocks"] += r["unresolved_blocks_in_engine"]
        tot["checks"] += r["club_checks"]
    assert tot["violations"] == 0 and tot["naive_violations"] == 0                                    # sound under both readings, with and without the known results
    assert tot["completions"] > 300_000 and tot["checks"] > 3000                                       # genuinely exhaustive, not a handful of examples
    assert tot["groups2"] > 100 and tot["groups3"] > 5 and tot["blocks"] > 0                           # pairs, multi-club ties and unresolved deciders were all exercised
    assert tot["tight"] / tot["tight_checks"] > 0.9                                                    # informative, not vacuous


def test_the_oracle_used_for_validation_is_the_engine_itself():
    rng = np.random.default_rng(8)
    for key in KEYS:
        prof = rules.get_profile(key, "2026-27")
        names, played, fx = V.random_league(rng, 5, 4, gmax=2)
        inp = V.make(names, played, fx)
        F = len(fx)
        for _ in range(25):
            sh = rng.integers(0, 4, size=(1, F))
            sa = rng.integers(0, 4, size=(1, F))
            pmf = np.zeros((F, K, K))
            for f in range(F):
                pmf[f, sh[0, f], sa[0, f]] = 1.0
            ref = engine.simulate(SeasonInput(**{**inp.__dict__, "pmf": pmf}), prof, n=1, seed=1)
            pos, term = V.engine_positions(inp, prof, sh, sa)
            assert (pos == ref.pos).all() and len(term) == len(ref.terminal_events["per_sim"])


@pytest.mark.parametrize("key", KEYS)
def test_with_nothing_left_to_play_the_bounds_contain_the_engine_table_even_for_multi_club_ties(key):
    rng = np.random.default_rng(13)
    multi = checked = 0
    for _ in range(120):
        names = [f"C{i}" for i in range(6)]
        played = [(a, b, int(rng.integers(0, 3)), int(rng.integers(0, 3))) for a in names for b in names if a != b]
        inp = V.make(names, played, [])
        prof = rules.get_profile(key, "2026-27")
        b = pointbounds.position_bounds(inp, prof, np.zeros((1, 0), dtype=int))
        multi += int(max(np.unique(b.points[0], return_counts=True)[1]) >= 3)
        for rname, rprof in V.readings(key).items():
            pos, term = V.engine_positions(inp, rprof, np.zeros((1, 0), dtype=np.int16), np.zeros((1, 0), dtype=np.int16))
            seen = V.reachable_sets(pos, term)
            for t in range(6):
                assert b.best[0, t] <= min(seen[t]) and b.worst[0, t] >= max(seen[t]), (key, rname, played)
                checked += 1
    assert multi >= 5 and checked == 120 * 12


@pytest.mark.parametrize("key", KEYS)
def test_the_reading_independent_prefix_only_ever_widens_the_prototype_bounds(key):
    rng = np.random.default_rng(17)
    prof = rules.get_profile(key, "2026-27")
    legacy = dict(prof, bounds_multi_club_prefix=None)
    for _ in range(25):
        names, played, fx = V.random_league(rng, 5, 5, gmax=1)
        inp = V.make(names, played, fx)
        probs = rng.dirichlet([4, 2.5, 3], size=len(fx))
        oc = pointbounds.draw_outcomes(probs, 300, 5)
        a, l = pointbounds.position_bounds(inp, prof, oc), pointbounds.position_bounds(inp, legacy, oc)
        assert (a.best <= l.best).all() and (a.worst >= l.worst).all()


@pytest.mark.parametrize("key", KEYS)
def test_lower_never_above_upper_everything_between_0_and_100_percent_and_the_places_add_up(key):
    rng = np.random.default_rng(4)
    prof = dict(rules.get_profile(key, "2026-27"), bands={"title": [1], "top4": [1, 2, 3, 4], "relegation": [5, 6]})
    for _ in range(8):
        names, played, fx = V.random_league(rng, 6, 8, gmax=2)
        inp = V.make(names, played, fx)
        probs = rng.dirichlet([4, 2.5, 3], size=len(fx))
        n = 400
        b = pointbounds.position_bounds(inp, prof, pointbounds.draw_outcomes(probs, n, 3))
        s = pointbounds.band_summary(b, prof, inp, names=("title", "top4", "relegation"))
        for name, band in s.items():
            places = band["positions"][1] - band["positions"][0] + 1
            assert sum(c["guaranteed"] for c in band["clubs"]) <= places + 1e-9 <= sum(c["possible"] for c in band["clubs"]) + 2e-9
            for c in band["clubs"]:
                assert 0.0 <= c["guaranteed"] <= c["possible"] <= 1.0 and 0.0 <= c["unresolved"] <= 1.0
                assert c["unresolved"] == pytest.approx(c["possible"] - c["guaranteed"], abs=1e-12) and c["se_guaranteed"] >= 0 and c["se_possible"] >= 0
        by = {name: {c["entity_id"]: c for c in band["clubs"]} for name, band in s.items()}
        for t in names:                                                                  # a bigger band is never less certain: title nests in top four
            assert by["title"][t]["guaranteed"] <= by["top4"][t]["guaranteed"] + 1e-12 and by["title"][t]["possible"] <= by["top4"][t]["possible"] + 1e-12


def test_a_finished_season_with_no_ties_has_no_unresolved_probability():
    names = ["A", "B", "C", "D"]
    played = [("A", "B", 1, 0), ("B", "A", 0, 3), ("A", "C", 2, 0), ("C", "A", 0, 1), ("A", "D", 4, 0), ("D", "A", 0, 1), ("B", "C", 1, 0), ("C", "B", 0, 1), ("B", "D", 2, 0), ("D", "B", 0, 1), ("C", "D", 3, 0), ("D", "C", 0, 1)]
    inp = V.make(names, played, [])
    for key in KEYS:
        prof = dict(rules.get_profile(key, "2026-27"), bands={"title": [1], "top4": [1, 2], "relegation": [4]})
        b = pointbounds.position_bounds(inp, prof, np.zeros((7, 0), dtype=int))
        s = pointbounds.band_summary(b, prof, inp, names=("title", "top4", "relegation"))
        for band in s.values():
            assert all(c["unresolved"] == 0.0 and c["guaranteed"] == c["possible"] for c in band["clubs"])
        assert [c["guaranteed"] for c in s["title"]["clubs"]][:2] == [1.0, 0.0]


@needs_store
@pytest.mark.parametrize("key", KEYS)
def test_real_season_state_the_engines_positions_stay_inside_the_bounds(key):
    conn = store_db.connect(PROD, readonly=True)
    try:
        inp = V.realistic_state(key, conn)
    finally:
        conn.close()
    r = V.realistic_check(inp, key, n=700, seed=9)
    assert r["violations"] == 0 and r["club_checks"] == 700 * len(inp.teams) * 2
    assert 0.3 < r["share_of_clubs_with_exact_position_known"] < 1.0                               # neither vacuous nor suspiciously perfect
