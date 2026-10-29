"""Phase 4.29: one-off patch of tests/test_seasonsim_service.py (before-copy kept in p429/before/). Replaces hard-coded production counts by an SQL oracle and adds five-league tests."""
from pathlib import Path

p = Path(__file__).resolve().parents[4] / "tests" / "test_seasonsim_service.py"
raw = p.read_bytes()
bom = raw.startswith(b"\xef\xbb\xbf")
s = raw.decode("utf-8-sig")
crlf = chr(13) + chr(10) in s
s = s.replace(chr(13) + chr(10), chr(10))


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


rep('''# Phase 4.8D Stage 1: these tests start from a COPY of the PRODUCTION store, so the remaining-fixture counts follow its data. The six approved results (2 Bundesliga, 4 La Liga) lowered them:
# Bundesliga 245 -> 243 (306 - 63 finished), La Liga 291 -> 287 (380 - 93 stored results). Nothing else in these tests was changed.
''', '''# These tests start from a COPY of the PRODUCTION store, whose data keeps growing through verified imports. Phase 4.29: fixture counts and eligibility are therefore NOT hard-coded any more;
# they are recomputed per test from the copy with plain SQL (`oracle`), a count independent of the implementation. The engine arithmetic is covered by synthetic tests with fixed numbers.
''')
rep('''def n_runs(path):''', '''LEAGUES = ("BUNDESLIGA", "LALIGA", "EPL", "SERIEA", "LIGUE1")


def oracle(path, key, season="2026-27", today=TODAY):
    """Independent expectation from plain SQL on the copy: fixtures, completed (with a stored score), remaining, fixtures dated up to `today` without a result, clubs and the points already on the table."""
    c = sqlite3.connect(path)
    try:
        rows = c.execute("SELECT status, match_date, COALESCE(model_home_entity,home_entity_id), COALESCE(model_away_entity,away_entity_id), COALESCE(home_goals_90,home_goals_final), COALESCE(away_goals_90,away_goals_final) "
                         "FROM matches WHERE competition_key=? AND season=? AND kind='club'", (key, season)).fetchall()
    finally:
        c.close()
    done = [r for r in rows if r[0] in ("completed", "awarded") and r[4] is not None]
    pts = {}
    for _, _, h, a, hg, ag in done:
        pts[h] = pts.get(h, 0) + (3 if hg > ag else 1 if hg == ag else 0)
        pts[a] = pts.get(a, 0) + (3 if ag > hg else 1 if hg == ag else 0)
    missing = [r for r in rows if r[0] not in ("completed", "awarded", "postponed") and r[1] <= today.isoformat()]
    return dict(fixtures=len(rows), completed=len(done), remaining=len(rows) - len(done), missing=len(missing), clubs=len({r[2] for r in rows} | {r[3] for r in rows}), points=pts)


def n_runs(path):''')
rep('''    assert cfg["default_simulations"] == 10000 and cfg["initial_scope"] == ["BUNDESLIGA", "LALIGA"]
''', '''    assert cfg["default_simulations"] == 10000 and cfg["initial_scope"] == ["BUNDESLIGA", "LALIGA"]            # the full final-position simulator is unchanged
    assert cfg["points_only"]["scope"] == list(LEAGUES) and "UCL" not in cfg["points_only"]["scope"]            # Phase 4.29: the points-only mode covers the five domestic leagues, never the Champions League
    assert cfg["points_only"]["position_bounds"]["scope"] == ["BUNDESLIGA", "LALIGA"]
''')

a = s.index('@needs_store\ndef test_todays_eligibility_matches_the_planned_gates')
b = s.index('@needs_store\ndef test_eligibility_thresholds_at_the_boundaries')
s = s[:a] + '''@needs_store
def test_todays_eligibility_matches_the_planned_gates(copy_db):
    conn = db.connect(copy_db, readonly=True)
    try:
        s = {k: eligibility.assess(conn, k, "2026-27", TODAY) for k in LEAGUES}
    finally:
        conn.close()
    for k in LEAGUES:                                                              # counts are checked against an independent SQL count, not against constants
        o = oracle(copy_db, k)
        c = s[k]["counts"]
        assert c["fixtures"] == o["fixtures"] and c["completed"] == o["completed"] and c["remaining_to_simulate"] == o["remaining"] and c["missing_results"] == o["missing"]
        assert not s[k]["can_simulate"] and any("scoreline method" in b for b in s[k]["blockers"])     # nothing can run in the final-position mode while the scoreline gate is closed
    assert s["BUNDESLIGA"]["state"] == "ready" and s["LALIGA"]["state"] == "ready"
    assert any("initial scope" in b for b in s["EPL"]["blockers"])
    assert any("rules blocked" in b for b in s["SERIEA"]["blockers"]) and any("rules blocked" in b for b in s["LIGUE1"]["blockers"])


''' + s[b:]

rep('''rule_profile"]["bands"]["relegation"] == [18, 19, 20] and r["assumptions"]["remaining_fixtures"] == 287''',
    '''rule_profile"]["bands"]["relegation"] == [18, 19, 20] and r["assumptions"]["remaining_fixtures"] == oracle(copy_db, "LALIGA")["remaining"]''')

rep('''    assert c.get("/api/season/status", params=dict(key="EPL", season="2026-27")).json()["points_only"]["can_run"] is False
''', '''    for k in LEAGUES:                                                               # Phase 4.29: the scope is the five domestic leagues
        assert c.get("/api/season/status", params=dict(key=k, season="2026-27")).json()["points_only"]["can_run"] is True
    assert c.get("/api/season/status", params=dict(key="UCL", season="2026-27")).status_code in (400, 404, 422)      # the Champions League is not a domestic league
''')
rep('''    blocked = c.post("/api/season/points", json=dict(key="EPL", season="2026-27", user_action=service.POINTS_ACTION))
    assert blocked.status_code == 422 and "blocked" in blocked.json()["detail"]
''', '''    ucl = c.post("/api/season/points", json=dict(key="UCL", season="2026-27", user_action=service.POINTS_ACTION))
    assert ucl.status_code in (400, 404, 422)
''')

a = s.index('@needs_store\ndef test_points_only_status_follows_data_quality_and_the_approved_scope')
b = s.index('@needs_store\ndef test_points_only_runs_with_the_scoreline_gate_closed')
s = s[:a] + '''@needs_store
def test_points_only_status_follows_data_quality_and_the_approved_scope(copy_db, monkeypatch):
    conn = db.connect(copy_db, readonly=True)
    try:
        st = {k: eligibility.assess(conn, k, "2026-27", TODAY) for k in LEAGUES}
        # data quality blocks only a genuinely not-eligible season; provisional data (for example Serie A fixtures past their date without a result) still runs
        for k in LEAGUES:
            assert st[k]["points_only"]["can_run"] == (st[k]["state"] != "not_eligible")
            assert st[k]["points_only"]["label"] == "Experimental \\u2014 Points-only simulation"
        assert st["BUNDESLIGA"]["points_only"]["can_run"] and st["LALIGA"]["points_only"]["can_run"]
        real = settings.load()
        narrow = dict(real, points_only=dict(real["points_only"], scope=["BUNDESLIGA", "LALIGA"]))                   # the scope check still blocks a league outside it
        monkeypatch.setattr(settings, "load", lambda: narrow)
        epl = eligibility.assess(conn, "EPL", "2026-27", TODAY)["points_only"]
    finally:
        conn.close()
    assert not epl["can_run"] and any("approved scope" in b for b in epl["blockers"])


''' + s[b:]

rep('''    with pytest.raises(service.SimError, match="blocked"):
        service.run_points_only("EPL", "2026-27", 2000, 5, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    assert n_runs(copy_db) == before
''', '''    real = settings.load()
    narrow = dict(real, points_only=dict(real["points_only"], scope=["BUNDESLIGA", "LALIGA"]))
    monkeypatch.setattr(settings, "load", lambda: narrow)
    with pytest.raises(service.SimError, match="blocked"):
        service.run_points_only("EPL", "2026-27", 2000, 5, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    monkeypatch.undo()
    assert n_runs(copy_db) == before
''')
rep('def test_points_only_runs_with_the_scoreline_gate_closed_is_saved_on_action_only_and_has_no_positions(copy_db):',
    'def test_points_only_runs_with_the_scoreline_gate_closed_is_saved_on_action_only_and_has_no_positions(copy_db, monkeypatch):')
rep('''asm["simulations"] == 2000 and asm["seed"] == 5 and asm["remaining_fixtures"] == 243''',
    '''asm["simulations"] == 2000 and asm["seed"] == 5 and asm["remaining_fixtures"] == oracle(copy_db, "BUNDESLIGA")["remaining"]''')

a = s.index('@needs_store\ndef test_points_only_la_liga_run_is_sane')
b = s.index('@needs_store\ndef test_points_only_api_refusals_write_nothing')
s = s[:a] + '''@needs_store
def test_points_only_la_liga_run_is_sane(copy_db):
    o = oracle(copy_db, "LALIGA")
    r = service.run_points_only("LALIGA", "2026-27", 1000, 3, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    teams = r["result"]["summary"]["teams"]
    assert len(teams) == o["clubs"] == 20 and r["assumptions"]["remaining_fixtures"] == o["remaining"]            # remaining = fixtures - results with a stored score (a postponed match stays remaining)
    cur = sum(t["current_points"] for t in teams)
    total = sum(t["expected_points"] for t in teams)
    assert cur == sum(o["points"].values()) and cur + 2 * o["remaining"] < total < cur + 3 * o["remaining"]      # every remaining match adds 2 or 3 points to the table
    assert r["assumptions"]["eligibility"]["state"] in ("ready", "provisional")


@needs_store
@pytest.mark.parametrize("key", LEAGUES)
def test_points_only_runs_for_each_domestic_league_with_correct_accounting(copy_db, key):
    o = oracle(copy_db, key)
    before = n_runs(copy_db)
    a = service.run_points_only(key, "2026-27", 1000, 21, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    b = service.run_points_only(key, "2026-27", 1000, 21, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    assert n_runs(copy_db) == before + 2                                                                        # saved only because the user action was passed
    t = a["result"]["summary"]["teams"]
    assert t == b["result"]["summary"]["teams"] and a["assumptions"]["input_sha256"] == b["assumptions"]["input_sha256"]   # same seed and data: identical
    assert len(t) == o["clubs"] and a["assumptions"]["remaining_fixtures"] == o["remaining"]
    assert sum(x["remaining_fixtures"] for x in t) == 2 * o["remaining"]                                          # each remaining fixture counted once for each of its two clubs: none twice, no completed one
    assert all(x["current_points"] == o["points"].get(x["entity_id"], 0) for x in t)
    cur, total = sum(x["current_points"] for x in t), sum(x["expected_points"] for x in t)
    assert cur + 2 * o["remaining"] < total < cur + 3 * o["remaining"]
    assert all(x["current_points"] <= x["points_min"] <= x["expected_points"] <= x["points_max"] <= x["current_points"] + 3 * x["remaining_fixtures"] for x in t)
    assert a["assumptions"]["mode"] == "points_only" and a["assumptions"]["label"].startswith("Experimental")
    assert all(not any(k in x for k in POSITION_KEYS) for x in t)                                                 # no finishing positions, no exact table probabilities
    assert a["assumptions"]["eligibility"]["state"] in ("ready", "provisional")
    assert a["assumptions"]["eligibility"]["counts"]["missing_results"] == o["missing"]                           # missing results stay disclosed, never hidden
    pb = a["result"]["position_bounds"]
    assert (pb["status"] == "available") == (key in ("BUNDESLIGA", "LALIGA"))                                    # ranges only where verified tie-break settings exist
    if pb["status"] != "available":
        assert "Bundesliga and La Liga only" in pb["reason"] and "clubs" not in pb
    different = service.run_points_only(key, "2026-27", 1000, 22, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    assert different["result"]["summary"]["teams"] != t


@needs_store
def test_fixtures_past_their_date_without_a_result_are_disclosed_and_counted_once(copy_db):
    later = date(2026, 12, 1)                                                      # far enough that scheduled fixtures dated before it have no result yet
    conn = db.connect(copy_db, readonly=True)
    try:
        st = eligibility.assess(conn, "SERIEA", "2026-27", later)
    finally:
        conn.close()
    expected = oracle(copy_db, "SERIEA", today=later)
    assert st["counts"]["missing_results"] == expected["missing"] > 0 and any("no verified result" in r for r in st["reasons"])      # disclosed
    assert st["counts"]["remaining_to_simulate"] == expected["remaining"]                                                              # and still counted exactly once among the remaining fixtures


''' + s[b:]

rep('''assert off["status"] == "unavailable" and "approved scope" in off["reason"] and "clubs" not in off''',
    '''assert off["status"] == "unavailable" and "Bundesliga and La Liga only" in off["reason"] and "clubs" not in off''')
rep('''any("approved scope" in b for b in st[k]["position_bounds"]["blockers"])''',
    '''any("Bundesliga and La Liga only" in b for b in st[k]["position_bounds"]["blockers"])''')

s += '''

# ----------------------------------------------------------------------------------- engine arithmetic on fixed, synthetic numbers (no database)
def test_points_engine_arithmetic_with_certain_outcomes():
    from seasonsim import pointsonly

    base = np.array([10, 4, 0], dtype=np.int64)
    fh, fa = np.array([0, 1, 2]), np.array([1, 2, 0])
    certain = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])           # fixture 0: home win, 1: draw, 2: away win
    pts = pointsonly.simulate_points(base, fh, fa, certain, 50, 9)
    expected = np.array([10 + 3 + 3, 4 + 1, 0 + 1])                                      # club 0 wins at home and away, clubs 1 and 2 draw
    assert (pts == expected[None, :]).all()
    assert pts.sum(axis=1).tolist() == [int(base.sum()) + 3 + 2 + 3] * 50                # a decisive match adds 3 to the table, a draw adds 2


def test_points_engine_is_seed_reproducible_and_adds_two_or_three_per_fixture():
    from seasonsim import pointsonly

    base = np.zeros(4, dtype=np.int64)
    fh, fa = np.array([0, 2, 1, 3]), np.array([1, 3, 2, 0])
    pr = np.tile([0.45, 0.27, 0.28], (4, 1))
    a, b, c = (pointsonly.simulate_points(base, fh, fa, pr, 400, s) for s in (5, 5, 6))
    assert (a == b).all() and not (a == c).all()
    assert ((a.sum(axis=1) >= 2 * 4) & (a.sum(axis=1) <= 3 * 4)).all()
    assert (pointsonly.simulate_points(base + 7, fh[:0], fa[:0], pr[:0], 10, 1) == 7).all()                  # no remaining fixture: the table is final
'''
if crlf:
    s = s.replace(chr(10), chr(13) + chr(10))
p.write_bytes(s.encode("utf-8-sig" if bom else "utf-8"))
print("patched")
