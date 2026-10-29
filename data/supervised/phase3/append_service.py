

# ----------------------------------------------------------------------------------------------------------- points-only mode
POSITION_KEYS = ("p_title", "p_top4", "p_relegation", "position_probabilities", "expected_rank", "final_position_probabilities_supported")


@needs_store
def test_points_only_status_follows_data_quality_and_the_approved_scope(copy_db):
    conn = db.connect(copy_db, readonly=True)
    try:
        st = {k: eligibility.assess(conn, k, "2026-27", TODAY)["points_only"] for k in ("BUNDESLIGA", "LALIGA", "EPL", "SERIEA", "LIGUE1")}
    finally:
        conn.close()
    assert st["BUNDESLIGA"]["can_run"] and st["LALIGA"]["can_run"]
    assert not st["EPL"]["can_run"] and any("Not eligible" in b for b in st["EPL"]["blockers"]) and any("approved scope" in b for b in st["EPL"]["blockers"])
    assert not st["SERIEA"]["can_run"] and not st["LIGUE1"]["can_run"]
    assert st["BUNDESLIGA"]["label"] == "Experimental — Points-only simulation"


@needs_store
def test_points_only_runs_with_the_scoreline_gate_closed_is_saved_on_action_only_and_has_no_positions(copy_db):
    assert settings.load()["scoreline_method"] is None                                      # the full simulator is still disabled
    before = n_runs(copy_db)
    with pytest.raises(service.SimError, match="explicitly presses"):
        service.run_points_only("BUNDESLIGA", "2026-27", 2000, 5, "page_load", today=TODAY, db_path=copy_db)
    with pytest.raises(service.SimError, match="blocked"):
        service.run_points_only("EPL", "2026-27", 2000, 5, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    assert n_runs(copy_db) == before
    a = service.run_points_only("BUNDESLIGA", "2026-27", 2000, 5, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    b = service.run_points_only("BUNDESLIGA", "2026-27", 2000, 5, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    assert n_runs(copy_db) == before + 2 and a["result"]["summary"]["teams"] == b["result"]["summary"]["teams"]
    asm, teams = a["assumptions"], a["result"]["summary"]["teams"]
    assert asm["mode"] == "points_only" and asm["label"].startswith("Experimental") and asm["simulations"] == 2000 and asm["seed"] == 5 and asm["remaining_fixtures"] == 245
    assert list(asm["models"]) == ["primary"] and "club_v1" in asm["artifact_sha256"]
    for k in ("created_utc", "freshness", "data_cutoff", "eligibility", "limitations", "input_sha256", "points_rule"):
        assert k in asm
    assert len(teams) == 18 and all(t["expected_points"] >= t["current_points"] and t["points_p10"] <= t["expected_points"] <= t["points_p90"] for t in teams)
    assert all(not any(k in t for k in POSITION_KEYS) for t in teams) and "final_position_probabilities_supported" not in a["result"]["summary"]
    c = sqlite3.connect(copy_db)
    played_points = sum(3 if h > a_ else 2 for h, a_ in c.execute("SELECT home_goals_90, away_goals_90 FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='completed'"))
    c.close()
    assert sum(t["current_points"] for t in teams) == played_points                          # points already on the table: 3 per decisive result, 2 per draw
    runs = service.list_runs("BUNDESLIGA", "2026-27", copy_db)
    assert runs[0]["mode"] == "points_only" and service.get_run(a["run_id"], copy_db)["assumptions"]["mode"] == "points_only"
    with pytest.raises(service.SimError, match="no scoreline method"):                      # the complete final-position simulator remains disabled
        service.run_simulation("BUNDESLIGA", "2026-27", 1000, 1, service.EXPLICIT_ACTION, today=TODAY, db_path=copy_db)


@needs_store
def test_points_only_la_liga_run_is_sane(copy_db):
    r = service.run_points_only("LALIGA", "2026-27", 1000, 3, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    teams = r["result"]["summary"]["teams"]
    assert len(teams) == 20 and r["assumptions"]["remaining_fixtures"] == 291
    cur = sum(t["current_points"] for t in teams)
    total = sum(t["expected_points"] for t in teams)
    assert cur + 2 * 291 < total < cur + 3 * 291                                            # every remaining match adds 2 or 3 points to the table
    assert r["assumptions"]["eligibility"]["state"] in ("ready", "provisional")


@needs_store
def test_points_only_api_refusals_write_nothing():
    from fastapi.testclient import TestClient

    import main

    c = TestClient(main.app)
    j = c.get("/api/season/status", params=dict(key="BUNDESLIGA", season="2026-27")).json()
    assert j["points_only"]["can_run"] is True and j["can_simulate"] is False and j["points_only"]["limitations"]
    assert c.get("/api/season/status", params=dict(key="EPL", season="2026-27")).json()["points_only"]["can_run"] is False
    bad = c.post("/api/season/points", json=dict(key="BUNDESLIGA", season="2026-27", user_action="page_load"))
    assert bad.status_code == 422 and "explicitly" in bad.json()["detail"]
    blocked = c.post("/api/season/points", json=dict(key="EPL", season="2026-27", user_action=service.POINTS_ACTION))
    assert blocked.status_code == 422 and "blocked" in blocked.json()["detail"]
    assert sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True).execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0] == 0
