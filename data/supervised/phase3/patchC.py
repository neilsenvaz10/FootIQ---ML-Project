p = "tests/test_seasonsim_engine.py"
s = open(p, encoding="utf-8").read()
s = s.replace('''def test_exact_tie_reaches_the_final_decider_and_is_reported():
    inp = season([("A", "B", 1, 1), ("B", "A", 1, 1)], ["A", "B"])
    r = engine.simulate(inp, prof("BUNDESLIGA"), n=4000, seed=3)
    p_first = (r.pos[:, 0] == 1).mean()
    assert 0.45 < p_first < 0.55                                    # coin flip placeholder (decision D6)
    s = engine.summarize(r, inp, prof("BUNDESLIGA"))
    assert s["tie_resolution"]["share_where_a_final_decider_was_needed"] == pytest.approx(1.0)''',
'''def test_an_exact_tie_is_left_unresolved_never_decided_by_a_coin_and_probabilities_are_withheld():
    inp = season([("A", "B", 1, 1), ("B", "A", 1, 1)], ["A", "B"])
    r = engine.simulate(inp, prof("BUNDESLIGA"), n=2000, seed=3)
    assert len({tuple(r.pos[i]) for i in range(2000)}) == 1               # no randomness: the bookkeeping order is identical in every simulation
    s = engine.summarize(r, inp, prof("BUNDESLIGA"))
    assert s["final_position_probabilities_supported"] is False and "title" in s["bands_with_unresolved_ties"]
    assert s["tie_resolution"]["share_with_an_unresolved_tie"] == pytest.approx(1.0)
    for t in s["teams"]:
        assert t["p_title"] is None and t["p_title_low"] == 0.0 and t["p_title_high"] == 1.0           # only bounds
        assert t["expected_rank"] is None and t["position_unresolved_probability"] == 1.0 and sum(t["position_probabilities"]) == 0.0''')
s = s.replace('''    assert np.allclose(mat.sum(axis=1), 1) and np.allclose(mat.sum(axis=0), 1)
    assert sum(t["p_title"] for t in s["teams"]) == pytest.approx(1.0)
    assert all(0 <= t["p_top4"] <= 1 for t in s["teams"])''',
'''    unres = np.array([t["position_unresolved_probability"] for t in s["teams"]])
    assert np.allclose(mat.sum(axis=1) + unres, 1)                                              # every simulation is either resolved or reported as unresolved
    assert sum(t["p_title_low"] for t in s["teams"]) <= 1.0 + 1e-9 <= sum(t["p_title_high"] for t in s["teams"]) + 2e-9
    if s["final_position_probabilities_supported"]:
        assert np.allclose(mat.sum(axis=0), 1) and sum(t["p_title"] for t in s["teams"]) == pytest.approx(1.0)
    assert all(0 <= t["p_top4_low"] <= t["p_top4_high"] <= 1 for t in s["teams"])''')
open(p, "w", encoding="utf-8", newline="\n").write(s)

p = "tests/test_seasonsim_service.py"
s = open(p, encoding="utf-8").read()
s = s.replace('''    assert len(s["teams"]) == 18 and sum(t["p_title"] for t in s["teams"]) == pytest.approx(1.0)
    assert sum(t["p_relegation"] for t in s["teams"]) == pytest.approx(2.0) and sum(t["p_relegation_playoff"] for t in s["teams"]) == pytest.approx(1.0)
    assert sum(t["p_top4"] for t in s["teams"]) == pytest.approx(4.0)
    mat = np.array([t["position_probabilities"] for t in s["teams"]])
    assert np.allclose(mat.sum(axis=0), 1) and np.allclose(mat.sum(axis=1), 1)''',
'''    assert len(s["teams"]) == 18
    if s["final_position_probabilities_supported"]:
        assert sum(t["p_title"] for t in s["teams"]) == pytest.approx(1.0) and sum(t["p_top4"] for t in s["teams"]) == pytest.approx(4.0)
        assert sum(t["p_relegation"] for t in s["teams"]) == pytest.approx(2.0) and sum(t["p_relegation_playoff"] for t in s["teams"]) == pytest.approx(1.0)
    else:
        assert sum(t["p_title_low"] for t in s["teams"]) <= 1.0 <= sum(t["p_title_high"] for t in s["teams"])
    mat = np.array([t["position_probabilities"] for t in s["teams"]])
    assert np.allclose(mat.sum(axis=1) + np.array([t["position_unresolved_probability"] for t in s["teams"]]), 1)''')
s = s.replace('''    assert len(s["teams"]) == 20 and sum(t["p_title"] for t in s["teams"]) == pytest.approx(1.0) and sum(t["p_relegation"] for t in s["teams"]) == pytest.approx(3.0)''',
'''    assert len(s["teams"]) == 20
    if s["final_position_probabilities_supported"]:
        assert sum(t["p_title"] for t in s["teams"]) == pytest.approx(1.0) and sum(t["p_relegation"] for t in s["teams"]) == pytest.approx(3.0)''')
s = s.replace('''    assert s["tie_resolution"]["share_where_a_final_decider_was_needed"] < 0.01''', '''    assert s["tie_resolution"]["share_with_an_unresolved_tie"] < 0.01''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
