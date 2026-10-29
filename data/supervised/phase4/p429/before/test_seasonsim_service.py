"""Season simulator service: eligibility gates, the disabled-by-default scoreline gate, explicit-action saving, reproducibility, API, leakage control.
Runs on a private copy of the store (the production store is only read by the model-history cache, never written)."""
# Phase 4.8D Stage 1: these tests start from a COPY of the PRODUCTION store, so the remaining-fixture counts follow its data. The six approved results (2 Bundesliga, 4 La Liga) lowered them:
# Bundesliga 245 -> 243 (306 - 63 finished), La Liga 291 -> 287 (380 - 93 stored results). Nothing else in these tests was changed.
import json
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from seasonsim import eligibility, rules, service, settings  # noqa: E402
from store import db  # noqa: E402

PROD = ROOT / "data" / "footiq.sqlite"


def _prod_runs() -> int:
    import sqlite3 as _s
    return _s.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True).execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0]


PROD_RUNS_AT_START = _prod_runs() if PROD.exists() else 0      # real runs a user saved from the app are legitimate; the tests only prove THEY add none
TODAY = date(2026, 10, 25)
needs_store = pytest.mark.skipif(not PROD.exists(), reason="results store not built")


@pytest.fixture(scope="module")
def copy_db(tmp_path_factory):
    dst = tmp_path_factory.mktemp("sim") / "store.sqlite"
    src = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
    out = sqlite3.connect(dst)
    src.backup(out)
    out.close()
    src.close()
    return dst


@pytest.fixture()
def gate_on(tmp_path, monkeypatch):
    """TEST ONLY: a config file that names a scoreline method, so the engine path can be exercised on a private copy. The shipped config keeps it disabled."""
    cfg = json.loads((ROOT / "config" / "season_sim.json").read_text(encoding="utf-8"))
    cfg["scoreline_method"] = "S1"
    cfg["scoreline_validation"] = dict(status="test_only")
    p = tmp_path / "season_sim.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setenv("FOOTIQ_SEASONSIM_CONFIG", str(p))
    return p


def n_runs(path):
    c = sqlite3.connect(path)
    try:
        return c.execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0]
    finally:
        c.close()


@needs_store
def test_shipped_config_keeps_the_simulation_disabled_until_a_scoreline_method_is_approved():
    cfg = settings.load()
    assert cfg["scoreline_method"] is None and cfg["scoreline_validation"]["approved_by_user"] is False
    assert cfg["default_simulations"] == 10000 and cfg["initial_scope"] == ["BUNDESLIGA", "LALIGA"]


@needs_store
def test_todays_eligibility_matches_the_planned_gates(copy_db):
    conn = db.connect(copy_db, readonly=True)
    try:
        s = {k: eligibility.assess(conn, k, "2026-27", TODAY) for k in ("BUNDESLIGA", "LALIGA", "EPL", "SERIEA", "LIGUE1")}
    finally:
        conn.close()
    assert s["BUNDESLIGA"]["state"] == "ready" and s["LALIGA"]["state"] == "ready"
    assert s["EPL"]["state"] == "not_eligible" and s["SERIEA"]["state"] == "not_eligible" and s["LIGUE1"]["state"] == "not_eligible"
    for k in s:                                                                    # nothing can run while the scoreline gate is closed
        assert not s[k]["can_simulate"] and any("scoreline method" in b for b in s[k]["blockers"])
    assert any("initial scope" in b for b in s["EPL"]["blockers"])
    assert any("rules blocked" in b for b in s["SERIEA"]["blockers"]) and any("rules blocked" in b for b in s["LIGUE1"]["blockers"])
    assert s["LALIGA"]["counts"]["missing_results"] == 1 and s["BUNDESLIGA"]["counts"]["remaining_to_simulate"] == 243


@needs_store
def test_eligibility_thresholds_at_the_boundaries(copy_db):
    conn = db.connect(copy_db)
    try:
        def state_after(n_missing: int) -> str:
            conn.execute("BEGIN")
            ids = [r[0] for r in conn.execute("SELECT record_id FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='completed' ORDER BY match_date LIMIT ?", (n_missing,))]
            conn.executemany("UPDATE matches SET status='awaiting_result' WHERE record_id=?", [(i,) for i in ids])
            st = eligibility.assess(conn, "BUNDESLIGA", "2026-27", TODAY)["state"]
            conn.execute("ROLLBACK")
            return st
        assert state_after(0) == "ready"
        assert state_after(1) == "ready"                      # 1/61 = 1.6% <= 2%
        assert state_after(2) == "provisional"                # 2/61 = 3.3% > 2%
        assert state_after(9) == "provisional"                # 9/61 = 14.8% <= 15%
        assert state_after(10) == "not_eligible"              # 10/61 = 16.4% > 15%
        conn.execute("BEGIN")                                                                  # staleness alone: push every unplayed fixture into the far future so nothing counts as "played without result"
        conn.execute("UPDATE matches SET match_date='2027-05-01' WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='scheduled'")
        assert eligibility.assess(conn, "BUNDESLIGA", "2026-27", date(2026, 10, 31))["state"] == "ready"           # newest result 2026-10-24: 7 days old (<= 7)
        assert eligibility.assess(conn, "BUNDESLIGA", "2026-27", date(2026, 11, 3))["state"] == "provisional"      # 10 days old (> 7, <= 21)
        assert eligibility.assess(conn, "BUNDESLIGA", "2026-27", date(2026, 11, 20))["state"] == "not_eligible"    # 27 days old (> 21)
        conn.execute("ROLLBACK")
        conn.execute("BEGIN")
        conn.execute("UPDATE matches SET status='cancelled' WHERE record_id=(SELECT record_id FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='scheduled' LIMIT 1)")
        st = eligibility.assess(conn, "BUNDESLIGA", "2026-27", TODAY)
        conn.execute("ROLLBACK")
        assert st["state"] == "not_eligible" and any("D7" in r for r in st["reasons"])           # cancelled/abandoned treatment is an open decision
    finally:
        conn.close()


@needs_store
def test_simulation_is_refused_without_the_button_and_while_the_scoreline_gate_is_closed(copy_db):
    before = n_runs(copy_db)
    with pytest.raises(service.SimError, match="explicitly presses"):
        service.run_simulation("BUNDESLIGA", "2026-27", 1000, 1, "page_load", today=TODAY, db_path=copy_db)
    with pytest.raises(service.SimError, match="no scoreline method"):
        service.run_simulation("BUNDESLIGA", "2026-27", 1000, 1, service.EXPLICIT_ACTION, today=TODAY, db_path=copy_db)
    assert n_runs(copy_db) == before


@needs_store
def test_blocked_leagues_stay_blocked_even_when_the_gate_is_open(copy_db, gate_on):
    before = n_runs(copy_db)
    for key in ("SERIEA", "LIGUE1", "EPL"):
        with pytest.raises(service.SimError, match="blocked"):
            service.run_simulation(key, "2026-27", 1000, 1, service.EXPLICIT_ACTION, today=TODAY, db_path=copy_db)
    with pytest.raises(service.SimError, match="between 1,?000 and 50,?000|number of simulations"):
        service.run_simulation("BUNDESLIGA", "2026-27", 10, 1, service.EXPLICIT_ACTION, today=TODAY, db_path=copy_db)
    assert n_runs(copy_db) == before


@needs_store
def test_bundesliga_run_is_saved_reproducible_and_fully_described(copy_db, gate_on):
    before = n_runs(copy_db)
    a = service.run_simulation("BUNDESLIGA", "2026-27", 2000, 42, service.EXPLICIT_ACTION, include_experimental=True, today=TODAY, db_path=copy_db)
    b = service.run_simulation("BUNDESLIGA", "2026-27", 2000, 42, service.EXPLICIT_ACTION, today=TODAY, db_path=copy_db)
    assert n_runs(copy_db) == before + 2 and a["run_id"] != b["run_id"]                 # every press adds a run; history is never overwritten
    assert a["result"]["summary"]["teams"] == b["result"]["summary"]["teams"]           # same seed and data: identical
    s = a["result"]["summary"]
    assert len(s["teams"]) == 18
    if s["final_position_probabilities_supported"]:
        assert sum(t["p_title"] for t in s["teams"]) == pytest.approx(1.0) and sum(t["p_top4"] for t in s["teams"]) == pytest.approx(4.0)
        assert sum(t["p_relegation"] for t in s["teams"]) == pytest.approx(2.0) and sum(t["p_relegation_playoff"] for t in s["teams"]) == pytest.approx(1.0)
    else:
        assert sum(t["p_title_low"] for t in s["teams"]) <= 1.0 <= sum(t["p_title_high"] for t in s["teams"])
    mat = np.array([t["position_probabilities"] for t in s["teams"]])
    assert np.allclose(mat.sum(axis=1) + np.array([t["position_unresolved_probability"] for t in s["teams"]]), 1)
    asm = a["assumptions"]
    assert asm["simulations"] == 2000 and asm["seed"] == 42 and asm["remaining_fixtures"] == 243
    for k in ("created_utc", "models", "artifact_sha256", "data_cutoff", "freshness", "eligibility", "scoreline", "rule_profile", "limitations", "input_sha256", "standard_error_max"):
        assert k in asm
    assert asm["models"]["primary"].lower().count("v1") or "v1" in json.dumps(asm["models"]).lower()
    assert asm["rule_profile"]["sources"][0]["sha256"] and asm["eligibility"]["state"] == "ready"
    assert a["result"]["experimental"]["label"].startswith("Experimental") and len(a["result"]["experimental"]["teams"]) == 18
    assert service.get_run(a["run_id"], copy_db)["assumptions"]["seed"] == 42
    assert [r["run_id"] for r in service.list_runs("BUNDESLIGA", "2026-27", copy_db)][:2] == [b["run_id"], a["run_id"]]
    # the real table is respected: nobody can finish with fewer points than they already have
    conn = db.connect(copy_db, readonly=True)
    try:
        pts = {r[0]: r[1] for r in conn.execute("SELECT t.display_name, SUM(CASE WHEN (m.home_entity_id=t.entity_id AND m.home_goals_90>m.away_goals_90) OR (m.away_entity_id=t.entity_id AND m.away_goals_90>m.home_goals_90) THEN 3 "
                                                "WHEN m.home_goals_90=m.away_goals_90 THEN 1 ELSE 0 END) FROM teams t JOIN matches m ON t.entity_id IN (m.home_entity_id, m.away_entity_id) WHERE m.competition_key='BUNDESLIGA' AND m.season='2026-27' AND m.status='completed' GROUP BY t.display_name")}
    finally:
        conn.close()
    assert all(t["points_p10"] >= pts.get(t["name"], 0) for t in s["teams"])


@needs_store
def test_la_liga_run_uses_its_verified_rule_profile_and_is_consistent(copy_db, gate_on):
    r = service.run_simulation("LALIGA", "2026-27", 1000, 7, service.EXPLICIT_ACTION, today=TODAY, db_path=copy_db)
    s = r["result"]["summary"]
    assert len(s["teams"]) == 20
    if s["final_position_probabilities_supported"]:
        assert sum(t["p_title"] for t in s["teams"]) == pytest.approx(1.0) and sum(t["p_relegation"] for t in s["teams"]) == pytest.approx(3.0)
    assert r["assumptions"]["rule_profile"]["bands"]["relegation"] == [18, 19, 20] and r["assumptions"]["remaining_fixtures"] == 287
    assert s["tie_resolution"]["share_with_an_unresolved_tie"] < 0.01


@needs_store
def test_cut_off_state_ignores_every_result_dated_on_or_after_the_cutoff():
    import predict
    from seasonsim import backtest

    lg, V, tiers = predict._club_runtime()
    cutoff = pd.Timestamp("2025-03-01")
    comp = "deutschland:1-bundesliga"
    fx = V[(V.competition_id == comp) & (V.dt >= cutoff) & (V.dt < cutoff + pd.Timedelta(days=21))].head(8)
    fixtures = pd.DataFrame(dict(fixture_id=fx.record_id.values, dt=fx.dt.values, h=fx.home_entity_id.values, a=fx.away_entity_id.values, comp=comp, season=fx.season_corrected.values, tier=fx.tier.values))
    a = backtest.probabilities_at(V, cutoff, fixtures)
    V2 = V.copy()
    late = V2.dt >= cutoff
    rng = np.random.default_rng(0)
    V2.loc[late, "gh"] = rng.integers(0, 6, late.sum())
    V2.loc[late, "ga"] = rng.integers(0, 6, late.sum())
    b = backtest.probabilities_at(V2, cutoff, fixtures)
    pd.testing.assert_frame_equal(a, b)                                                # bit-identical: later results cannot reach the cut-off state
    assert len(a) == 8 and a[["p1_H", "p1_D", "p1_A"]].sum(axis=1).round(9).eq(1).all()


@needs_store
def test_api_status_and_refusals_without_writing_anything():
    from fastapi.testclient import TestClient

    import main

    c = TestClient(main.app)
    st = c.get("/api/season/status", params=dict(key="BUNDESLIGA", season="2026-27"))
    assert st.status_code == 200
    j = st.json()
    assert j["state"] in ("ready", "provisional") and j["can_simulate"] is False and j["rule_profile"]["usable"] is True and j["limits"]["default"] == 10000
    assert c.get("/api/season/status", params=dict(key="WC")).status_code == 422 or c.get("/api/season/status", params=dict(key="WC")).status_code == 404
    before = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True).execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0]
    bad = c.post("/api/season/simulate", json=dict(key="BUNDESLIGA", season="2026-27", user_action="page_load"))
    assert bad.status_code == 422 and "explicitly" in bad.json()["detail"]
    closed = c.post("/api/season/simulate", json=dict(key="BUNDESLIGA", season="2026-27", user_action=service.EXPLICIT_ACTION))
    assert closed.status_code == 422 and "disabled" in closed.json()["detail"]
    after = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True).execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0]
    assert before == after == PROD_RUNS_AT_START
    assert c.get("/api/season/run", params=dict(id=999)).status_code == 404


def test_rule_profiles_report_why_a_league_is_blocked():
    info = rules.profile_info("LIGUE1", "2026-27")
    assert not info["usable"] and "2026/27" in info["reason"]
    assert rules.profile_info("SERIEA", "2026-27")["status"] == "blocked"


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
    assert asm["mode"] == "points_only" and asm["label"].startswith("Experimental") and asm["simulations"] == 2000 and asm["seed"] == 5 and asm["remaining_fixtures"] == 243
    assert list(asm["models"]) == ["primary"] and "club_v1" in asm["artifact_sha256"]
    for k in ("created_utc", "freshness", "data_cutoff", "eligibility", "limitations", "input_sha256", "points_rule"):
        assert k in asm
    assert len(teams) == 18 and all(t["expected_points"] >= t["current_points"] and t["points_p10"] <= t["expected_points"] <= t["points_p90"] for t in teams)
    assert all(not any(k in t for k in POSITION_KEYS) for t in teams) and "final_position_probabilities_supported" not in a["result"]["summary"]
    c = sqlite3.connect(copy_db)
    played_points = sum(2 if h == a_ else 3 for h, a_ in c.execute("SELECT home_goals_90, away_goals_90 FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='completed'"))
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
    assert len(teams) == 20 and r["assumptions"]["remaining_fixtures"] == 287
    cur = sum(t["current_points"] for t in teams)
    total = sum(t["expected_points"] for t in teams)
    assert cur + 2 * 287 < total < cur + 3 * 287                                            # every remaining match adds 2 or 3 points to the table
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
    assert _prod_runs() == PROD_RUNS_AT_START


# ------------------------------------------------------------------------------------------- position ranges (lower and upper bounds) inside the points-only mode
BOUND_KEYS = {"guaranteed", "possible", "unresolved", "se_guaranteed", "se_possible"}


def check_ranges(pb, clubs):
    """Every claim made about the ranges, independent of the league."""
    assert pb["status"] == "available" and pb["kind"] == "lower_and_upper_bounds"
    assert pb["label"].startswith("Experimental") and "lower and upper bounds, not exact probabilities" in pb["label"]
    assert [b["id"] for b in pb["bands"]] == ["title", "top4", "relegation"] and pb["bands"][0]["positions"] == [1, 1] and pb["bands"][1]["positions"] == [1, 4]
    assert len(pb["clubs"]) == clubs and all(set(c) == {"entity_id", "name", "title", "top4", "relegation"} for c in pb["clubs"])
    for band in pb["bands"]:
        total_g = total_p = 0.0
        for c in pb["clubs"]:
            v = c[band["id"]]
            assert set(v) == BOUND_KEYS
            assert 0.0 <= v["guaranteed"] <= v["possible"] <= 1.0 and 0.0 <= v["unresolved"] <= 1.0          # lower never above upper; all within 0-100%
            assert v["unresolved"] == pytest.approx(v["possible"] - v["guaranteed"], abs=1e-12) and v["se_guaranteed"] >= 0 and v["se_possible"] >= 0
            total_g += v["guaranteed"]
            total_p += v["possible"]
        assert total_g <= band["places"] + 1e-9 <= total_p + 2e-9                                              # exactly `places` clubs fill the band in every season
    for c in pb["clubs"]:
        assert c["title"]["guaranteed"] <= c["top4"]["guaranteed"] + 1e-12 and c["title"]["possible"] <= c["top4"]["possible"] + 1e-12
    assert all(v for k, v in pb["checks"].items() if k != "places_sums")
    assert pb["monte_carlo"]["simulations"] == pb["ties"]["simulations"]
    assert len(pb["limitations"]) >= 5 and pb["rules"]["status"] == "verified" and pb["rules"]["sources"][0]["sha256"]


@needs_store
@pytest.mark.parametrize("key,clubs,relegation", [("BUNDESLIGA", 18, [17, 18]), ("LALIGA", 20, [18, 20])])
def test_points_only_run_carries_labelled_lower_and_upper_bounds_and_no_exact_probabilities(copy_db, key, clubs, relegation):
    r = service.run_points_only(key, "2026-27", 2000, 5, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    pb, summary = r["result"]["position_bounds"], r["result"]["summary"]
    check_ranges(pb, clubs)
    assert pb["bands"][2]["positions"] == relegation
    assert [c["entity_id"] for c in pb["clubs"]] == [t["entity_id"] for t in summary["teams"]]                 # same order as the expected-points table
    blob = json.dumps(r["result"])
    assert not any(k in blob for k in ("p_title", "p_top4", "p_relegation", "position_probabilities", "expected_rank", "final_position_probabilities_supported"))
    assert all(not any(k in t for k in POSITION_KEYS) for t in summary["teams"])                                  # the points table itself still carries no position field
    assert r["assumptions"]["position_bounds"]["status"] == "available" and r["assumptions"]["mode"] == "points_only" and r["assumptions"]["label"].startswith("Experimental")
    assert service.get_run(r["run_id"], copy_db)["result"]["position_bounds"] == pb                             # saved with the run
    top = pb["clubs"][0]                                                                                         # the club with most expected points is the likeliest champion
    assert top["title"]["possible"] == max(c["title"]["possible"] for c in pb["clubs"])
    assert settings.load()["scoreline_method"] is None                                                           # the final-position simulator is still disabled
    with pytest.raises(service.SimError, match="no scoreline method"):
        service.run_simulation(key, "2026-27", 1000, 1, service.EXPLICIT_ACTION, today=TODAY, db_path=copy_db)


@needs_store
def test_ranges_follow_each_leagues_verified_rules_and_disclose_what_stays_unresolved(copy_db):
    bl = service.run_points_only("BUNDESLIGA", "2026-27", 1000, 5, service.POINTS_ACTION, today=TODAY, db_path=copy_db)["result"]["position_bounds"]
    ll = service.run_points_only("LALIGA", "2026-27", 1000, 5, service.POINTS_ACTION, today=TODAY, db_path=copy_db)["result"]["position_bounds"]
    assert bl["rules"]["criteria_used"]["two_clubs"][:2] == ["goal_difference", "goals_scored"] and bl["rules"]["criteria_used"]["three_or_more_clubs"] == ["goal_difference", "goals_scored"]
    assert ll["rules"]["criteria_used"]["two_clubs"][0] == "h2h_goal_difference" and ll["rules"]["criteria_used"]["three_or_more_clubs"] == ["h2h_points"]
    assert any("16th place plays a relegation play-off" in x for x in bl["limitations"]) and any("never simulated" in x for x in bl["limitations"])
    assert any("fair-play" in x or "fair play" in x for x in ll["limitations"]) and any("neutral-ground" in x for x in ll["limitations"])
    assert bl["rules"]["live_confirmation"] is None and "PENDING" in ll["rules"]["live_confirmation"]                # La Liga stays pending until the checksum is verified
    assert any("checksum" in x for x in ll["limitations"])
    for pb in (bl, ll):
        assert pb["rules"]["deciders_never_simulated"]["resolved_by"] == "unresolved_not_simulated" and pb["rules"]["interpretation_notes"]
        assert pb["ties"]["tie_groups"] > 0 and 0 <= pb["ties"]["tie_groups_fully_decided"] <= pb["ties"]["tie_groups"]


@needs_store
def test_the_points_distributions_do_not_change_when_the_ranges_are_switched_off(copy_db, tmp_path, monkeypatch):
    on = service.run_points_only("LALIGA", "2026-27", 1500, 21, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    cfg = json.loads((ROOT / "config" / "season_sim.json").read_text(encoding="utf-8"))
    cfg["points_only"]["position_bounds"]["enabled"] = False
    p = tmp_path / "season_sim_off.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setenv("FOOTIQ_SEASONSIM_CONFIG", str(p))
    off = service.run_points_only("LALIGA", "2026-27", 1500, 21, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    assert off["result"]["summary"] == on["result"]["summary"]                                                     # bit-identical points distributions
    assert off["result"]["position_bounds"]["status"] == "unavailable" and "switched off" in off["result"]["position_bounds"]["reason"]
    assert "clubs" not in off["result"]["position_bounds"]


@needs_store
def test_ranges_are_reproducible_for_a_seed_and_independent_of_other_runs(copy_db):
    a = service.run_points_only("BUNDESLIGA", "2026-27", 1200, 33, service.POINTS_ACTION, today=TODAY, db_path=copy_db)["result"]["position_bounds"]
    service.run_points_only("BUNDESLIGA", "2026-27", 1200, 34, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    b = service.run_points_only("BUNDESLIGA", "2026-27", 1200, 33, service.POINTS_ACTION, today=TODAY, db_path=copy_db)["result"]["position_bounds"]
    assert a == b


def tiny():
    from seasonsim import pointsonly

    names = ["A", "B", "C", "D"]
    idx = {n: i for i, n in enumerate(names)}
    played = [dict(h="A", a="B", hg=1, ag=0), dict(h="C", a="D", hg=0, ag=0)]
    fh, fa = np.array([idx["B"], idx["D"], idx["A"]]), np.array([idx["C"], idx["A"], idx["D"]])
    pr = np.array([[0.4, 0.3, 0.3]] * 3)
    base = np.array([3, 0, 1, 1])
    return names, idx, played, fh, fa, pr, pointsonly.simulate_points(base, fh, fa, pr, 50, 4)


def test_ranges_are_withheld_outside_the_scope_for_blocked_rules_or_without_verified_settings(monkeypatch):
    names, idx, played, fh, fa, pr, points = tiny()
    args = (names, names, idx, played, fh, fa, pr, 50, 4, points)
    off = service.build_position_bounds("EPL", "2026-27", *args)
    assert off["status"] == "unavailable" and "approved scope" in off["reason"] and "clubs" not in off
    real = settings.load()
    wide = dict(real, points_only=dict(real["points_only"], position_bounds=dict(real["points_only"]["position_bounds"], scope=["BUNDESLIGA", "LALIGA", "EPL", "SERIEA"])))
    monkeypatch.setattr(service.settings, "load", lambda: wide)
    assert "no verified settings" in service.build_position_bounds("EPL", "2026-27", *args)["reason"]                      # verified rules, but no bounds settings declared
    assert "league rules blocked" in service.build_position_bounds("SERIEA", "2026-27", *args)["reason"]


def test_ranges_are_withheld_if_an_internal_check_fails_instead_of_showing_wrong_numbers(monkeypatch):
    from seasonsim import pointbounds as PB

    names, idx, played, fh, fa, pr, points = tiny()
    real = rules.get_profile("BUNDESLIGA", "2026-27")
    monkeypatch.setattr(service.rules, "get_profile", lambda k, s: dict(real, bands={"title": [1], "top4": [1, 2], "relegation": [4]}))
    args = ("BUNDESLIGA", "2026-27", names, names, idx, played, fh, fa, pr, 50, 4, points)
    ok = service.build_position_bounds(*args)
    assert ok["status"] == "available" and ok["checks"]["places_sums_consistent"]
    assert "internal consistency" in service.build_position_bounds(*args[:-1], points + 1)["reason"]                       # the ranges and the points simulation disagree
    good = PB.band_counts
    monkeypatch.setattr(PB, "band_counts", lambda b, lo, hi: (lambda s, p: (p + 1, p))(*good(b, lo, hi)))                   # a lower bound above its upper bound
    assert "internal consistency" in service.build_position_bounds(*args)["reason"]


@needs_store
def test_status_announces_the_ranges_only_where_they_are_approved_and_the_rules_are_verified(copy_db):
    conn = db.connect(copy_db, readonly=True)
    try:
        st = {k: eligibility.assess(conn, k, "2026-27", TODAY)["points_only"] for k in ("BUNDESLIGA", "LALIGA", "EPL", "SERIEA", "LIGUE1")}
    finally:
        conn.close()
    assert st["BUNDESLIGA"]["position_bounds"]["available"] and st["LALIGA"]["position_bounds"]["available"]
    assert st["BUNDESLIGA"]["position_bounds"]["bands"] == ["title", "top4", "relegation"]
    for k in ("EPL", "SERIEA", "LIGUE1"):
        assert not st[k]["position_bounds"]["available"] and any("approved scope" in b for b in st[k]["position_bounds"]["blockers"])
    assert any("rules blocked" in b for b in st["SERIEA"]["position_bounds"]["blockers"])
    assert "lower and upper bounds" in st["BUNDESLIGA"]["note"] and "never as exact probabilities" in st["BUNDESLIGA"]["note"]


@needs_store
def test_api_returns_and_saves_the_ranges_on_a_private_copy_and_never_touches_production(copy_db, monkeypatch):
    from fastapi.testclient import TestClient

    import main

    monkeypatch.setattr(db, "DEFAULT_PATH", copy_db)
    c = TestClient(main.app)
    j = c.get("/api/season/status", params=dict(key="LALIGA", season="2026-27")).json()
    assert j["points_only"]["position_bounds"]["available"] is True and any("lower and upper bounds" in x for x in j["points_only"]["limitations"])
    r = c.post("/api/season/points", json=dict(key="LALIGA", season="2026-27", user_action=service.POINTS_ACTION, simulations=1000, seed=3))
    assert r.status_code == 200
    body = r.json()
    check_ranges(body["result"]["position_bounds"], 20)
    got = c.get("/api/season/run", params=dict(id=body["run_id"])).json()
    assert got["result"]["position_bounds"] == body["result"]["position_bounds"] and got["assumptions"]["mode"] == "points_only"
    assert _prod_runs() == PROD_RUNS_AT_START


@needs_store
def test_an_unexpected_failure_in_the_ranges_never_breaks_the_points_only_run(copy_db, monkeypatch):
    from seasonsim import pointbounds as PB

    good = service.run_points_only("LALIGA", "2026-27", 1200, 8, service.POINTS_ACTION, today=TODAY, db_path=copy_db)

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(PB, "position_bounds", boom)
    bad = service.run_points_only("LALIGA", "2026-27", 1200, 8, service.POINTS_ACTION, today=TODAY, db_path=copy_db)
    assert bad["result"]["summary"] == good["result"]["summary"]                                                  # the approved points results are unaffected
    pb = bad["result"]["position_bounds"]
    assert pb["status"] == "unavailable" and "RuntimeError" in pb["reason"] and "clubs" not in pb
    assert bad["assumptions"]["position_bounds"]["status"] == "unavailable"
