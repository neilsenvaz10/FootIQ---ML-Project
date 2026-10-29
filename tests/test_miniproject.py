"""Tests for the mini-project app (data prep, analytics, prediction wrapper, API).

Run:  .venv\\Scripts\\python.exe -X utf8 -m pytest tests/test_miniproject.py -q
The club-prediction tests build the 216k-match history state once (about 20-30 s).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

import analytics  # noqa: E402
import config as C  # noqa: E402
import predict  # noqa: E402

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)
needs_data = pytest.mark.skipif(not C.MATCHES_CSV.exists(), reason="run app/prepare_data.py first")


@needs_data
def test_matches_schema_and_scope():
    m = analytics.matches()
    assert [c["key"] for c in C.COMPETITIONS] == ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"] and len(C.COMPETITIONS) == 6      # the final six-competition scope
    assert set(m.competition_key) == {c["key"] for c in C.COMPETITIONS}                                                                         # the archived five never reach the application
    assert not m.duplicated(["competition_key", "date", "home", "away", "stage"]).any()
    assert m.home_goals.notna().all() and m.away_goals.notna().all() and (m.home_goals >= 0).all()
    assert m.date.str.match(r"^\d{4}-\d{2}-\d{2}$").all()
    assert (m.source != "").all() and (m.licence != "").all()          # attribution kept on every row


@needs_data
def test_audit_lists_every_competition_with_badge():
    a = analytics.audit()
    assert [r["competition_key"] for r in a] == [c["key"] for c in C.COMPETITIONS]
    badges = {r["competition_key"]: r["validation_badge"] for r in a}
    assert badges["UCL"] == C.NOT_VALIDATED
    assert all(badges[k] == C.VALIDATED for k in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"))


@needs_data
def test_standings_are_consistent():
    t = analytics.standings("EPL", "2023-24")
    assert len(t) == 20 and sum(x["played"] for x in t) == 2 * 380
    assert sum(x["gd"] for x in t) == 0 and sum(x["gf"] for x in t) == sum(x["ga"] for x in t)
    assert t[0]["points"] >= t[-1]["points"]


@needs_data
def test_club_names_are_one_to_one_with_entities():
    m = analytics.matches()
    club = m[m.home_entity_id != ""]
    pairs = pd.concat([club[["home", "home_entity_id"]].set_axis(["n", "e"], axis=1), club[["away", "away_entity_id"]].set_axis(["n", "e"], axis=1)]).drop_duplicates()
    assert not pairs.duplicated("e").any()


@needs_data
@pytest.mark.parametrize("key,home,away", [("EPL", "Arsenal FC", "Chelsea FC"), ("LALIGA", "FC Barcelona", "Real Madrid CF"), ("BUNDESLIGA", "FC Bayern München", "Borussia Dortmund"),
                                           ("SERIEA", "Juventus FC", "AC Milan"), ("LIGUE1", "Paris Saint-Germain FC", "Olympique de Marseille"), ("UCL", "Manchester City FC", "Real Madrid CF")])
def test_predictions_are_probabilities_with_badge(key, home, away):
    r = predict.predict(key, home, away)
    p = r["primary"]
    assert abs(p["home"] + p["draw"] + p["away"] - 1) < 1e-6 and min(p["home"], p["draw"], p["away"]) >= 0
    assert r["validation_badge"] == C.BY_KEY[key]["badge"]
    if key == "UCL":
        assert any("NOT validated" in n for n in r["notes"])


@needs_data
def test_fast_club_path_matches_original_inference_code():
    """The cached-state path must reproduce the project's own make_predictions exactly (same frozen models)."""
    lg, V, tier = predict._club_runtime()
    comp = C.BY_KEY["SERIEA"]
    dt = V.dt.max() + pd.Timedelta(days=1)
    h, a = predict._entity("SERIEA", "Juventus FC"), predict._entity("SERIEA", "AC Milan")
    fx = pd.DataFrame(dict(fixture_id=["T"], dt=[dt], h=[h], a=[a], comp=[comp["source_id"]], season=[analytics.seasons("SERIEA")[0]], tier=[tier[comp["source_id"]]],
                           home_name=["Juventus FC"], away_name=["AC Milan"], kickoff=["x"], kickoff_known=[False]))
    ref = lg.make_predictions(fx, V, "x", "x", "x")[0]
    mine = predict.predict("SERIEA", "Juventus FC", "AC Milan")
    assert np.allclose([mine["primary"][k] for k in ("home", "draw", "away")], [ref["v1_p_home"], ref["v1_p_draw"], ref["v1_p_away"]], atol=1e-9)
    assert np.allclose([mine["secondary"][k] for k in ("home", "draw", "away")], [ref["p_home"], ref["p_draw"], ref["p_away"]], atol=1e-9)


@needs_data
def test_api_errors_are_clean():
    assert client.get("/api/predict", params=dict(key="XXX", home="a", away="b")).status_code == 404
    assert client.get("/api/predict", params=dict(key="EPL", home="Nobody FC", away="Arsenal FC")).status_code == 422
    assert client.get("/api/predict", params=dict(key="EPL", home="Arsenal FC", away="Chelsea FC", date="2020-01-01")).status_code == 422
    assert client.get("/api/predict", params=dict(key="EPL", home="Arsenal FC", away="Arsenal FC")).status_code == 422
    assert client.get("/api/competitions/EPL/dashboard", params=dict(season="1999-00")).status_code == 404


@needs_data
def test_api_dashboard_and_overview():
    assert [c["key"] for c in client.get("/api/competitions").json()] == ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"]
    d = client.get("/api/competitions/LIGUE1/dashboard", params=dict(season="2019-20")).json()
    assert d["standings"] and d["summary"]["matches"] == 279          # known source gap, must stay visible
    cov = [c for c in client.get("/api/competitions/LIGUE1/coverage").json() if c["season"] == "2019-20"][0]
    assert cov["note"] == "incomplete or in progress"
    assert client.get("/api/competitions/UCL/dashboard", params=dict(season="2024-25")).json()["standings"] is None   # no league table for cups


# ------------------------------------------------------------------------------------------------ API readiness
@needs_data
def test_unknown_team_and_self_headtohead_are_errors():
    assert client.get("/api/team", params=dict(key="EPL", team="Nobody FC")).status_code == 404
    assert client.get("/api/team", params=dict(key="EPL", team="Arsenal FC", opponent="Nobody FC")).status_code == 404
    assert client.get("/api/team", params=dict(key="EPL", team="Arsenal FC", opponent="Arsenal FC")).status_code == 422
    assert client.get("/api/team", params=dict(key="EPL", team="Arsenal")).status_code == 404      # old source spelling is not a valid name


@needs_data
def test_team_stats_and_h2h_agree_with_entity_ids_despite_spelling_changes():
    src = pd.read_csv(C.CLUB_SOURCE, encoding="utf-8-sig", low_memory=False)
    d = src[(src.competition_id == "england:1-premierleague") & src.final_score_home_excl_penalties.notna()]
    a, b = "CLUB:ENG:arsenal-fc", "CLUB:ENG:chelsea-fc"
    truth = len(d[((d.home_entity_id == a) & (d.away_entity_id == b)) | ((d.home_entity_id == b) & (d.away_entity_id == a))])
    r = client.get("/api/team", params=dict(key="EPL", team="Arsenal FC", opponent="Chelsea FC")).json()["head_to_head"]
    assert r["meetings"] == truth > 8 and r["a_wins"] + r["b_wins"] + r["draws"] == truth


@needs_data
def test_bad_dates_are_422_not_500():
    for p in (dict(key="EPL", date="notadate"), dict(key="EPL", date="2026-13-45"), dict(key="UCL", date="01/02/2026"), dict(key="UCL", date="2020-01-01"), dict(key="EPL", date="2020-01-01")):
        r = client.get("/api/predict", params=dict(home="Arsenal FC" if p["key"] == "EPL" else "Manchester City FC", away="Chelsea FC" if p["key"] == "EPL" else "Real Madrid CF", **p))
        assert r.status_code == 422 and isinstance(r.json()["detail"], str), (p, r.status_code)


@needs_data
def test_far_future_date_gets_a_low_confidence_note():
    r = client.get("/api/predict", params=dict(key="UCL", home="Manchester City FC", away="Real Madrid CF", date="2027-12-01")).json()
    assert any("days after the data ends" in n for n in r["notes"])


@needs_data
def test_meta_and_health_and_frozen_model_integrity():
    m = client.get("/api/meta").json()
    assert m["integrity"]["club_v1"]["ok"] and m["integrity"]["club_v2_r1"]["ok"]        # sha256 of every frozen artifact matches FROZEN.json
    assert any(a["licence"] == "CC BY-SA 4.0" for a in m["attribution"]) and len(m["limitations"]) >= 3
    assert not any(k in m["models"] for k in ("international_v27", "worldcup_simulator")) and "international_ratings" not in m["data_through"]
    assert m["validation_badges"]["UCL"] == C.NOT_VALIDATED
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and isinstance(h["club_prediction_ready"], bool)


def test_error_shape_is_uniform():
    r = client.get("/api/competitions/EPL/dashboard")                                  # the required 'season' is missing
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and r.json()["errors"][0]["field"].endswith("season")
    assert isinstance(client.get("/api/competitions/NOPE/seasons").json()["detail"], str)


def test_cors_allows_dev_origin_only(monkeypatch):
    ok = client.options("/api/competitions", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options("/api/competitions", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers
    assert "access-control-allow-credentials" not in ok.headers
    monkeypatch.setenv("FOOTIQ_CORS_ORIGINS", "*")
    import main as m
    with pytest.raises(RuntimeError):
        m.cors_origins()


# ------------------------------------------------------------------------------------------------ team season filter and performance
@needs_data
def test_teams_season_filter_returns_only_that_seasons_teams():
    allt = client.get("/api/competitions/EPL/teams").json()
    cur = client.get("/api/competitions/EPL/teams", params=dict(season="2026-27")).json()
    assert len(cur) == 20 and set(cur) <= set(allt) and len(allt) > len(cur)       # relegated/old clubs only in the all-seasons list
    assert "Huddersfield Town A.F.C." in allt and "Huddersfield Town A.F.C." not in cur
    assert client.get("/api/competitions/EPL/teams", params=dict(season="1999-00")).status_code == 404
    assert client.get("/api/competitions/WC/teams").status_code == 404                  # archived competitions are not served


def test_model_performance_matches_the_repository_evaluation_files():
    p = client.get("/api/models/performance").json()
    test = pd.read_csv(C.ROOT / "FootIQ_Club_Model_Baseline_v1" / "04_TEST_METRICS.csv")
    row = test[(test.set == "test_primary") & (test.model == "multinomial_logreg")].iloc[0]
    got = [m for m in p["club_v1"]["evaluation"][0]["models"] if m["model"] == "multinomial_logreg"][0]
    assert got["n"] == int(row.n) == 15645 and abs(got["accuracy"] - row.accuracy) < 1e-12 and abs(got["log_loss"] - row.log_loss) < 1e-12
    assert [x["key"] for x in p["club_v1"]["per_league"]] == ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"]
    assert "unbiased" in p["club_v2_r1"]["status"]
    assert "international_v27" not in p and "worldcup" not in p                         # the international and World Cup evaluations belong to removed competitions
    assert p["uefa_club"]["status"] == "Not validated" and len(p["caveats"]) >= 3


# ------------------------------------------------------------------------------------------------ form column, model inputs, bracket
@needs_data
def test_standings_include_last_five_results_form():
    t = analytics.standings("EPL", "2023-24")
    assert all(1 <= len(x["form"]) <= 5 and set(x["form"]) <= set("WDL") for x in t)
    d = analytics.matches()
    d = d[(d.competition_key == "EPL") & (d.season == "2023-24")].sort_values("date")
    team = t[0]["team"]
    last = d[(d.home == team) | (d.away == team)].iloc[-1]
    gf, ga = (last.home_goals, last.away_goals) if last.home == team else (last.away_goals, last.home_goals)
    assert t[0]["form"][-1] == ("W" if gf > ga else "D" if gf == ga else "L")


@needs_data
@pytest.mark.parametrize("key,home,away", [("EPL", "Arsenal FC", "Chelsea FC"), ("UCL", "Manchester City FC", "Real Madrid CF")])
def test_prediction_exposes_the_inputs_the_model_used(key, home, away):
    r = predict.predict(key, home, away)
    for side in ("home", "away"):
        i = r["inputs"][side]
        assert i["elo"] > 1000 and i["prior_matches"] > 0 and i["ppg5"] is not None and 0 <= i["ppg5"] <= 3
    assert r["inputs"]["home"]["elo"] != r["inputs"]["away"]["elo"]




@needs_data
@pytest.mark.parametrize("path", ["/api/worldcup/simulate", "/api/worldcup/bracket"])
def test_world_cup_routes_are_gone(path):
    assert client.get(path).status_code == 404


@needs_data
@pytest.mark.parametrize("key", ["WC", "UEL", "UECL", "UNL", "COPA"])
def test_the_five_removed_competitions_are_not_served(key):
    for path in (f"/api/competitions/{key}/seasons", f"/api/competitions/{key}/teams", f"/api/competitions/{key}/coverage", f"/api/competitions/{key}/league-phase?season=2025-26"):
        assert client.get(path).status_code == 404, path
    assert client.get("/api/predict", params=dict(key=key, home="A", away="B")).status_code == 404
    assert key not in {c["key"] for c in client.get("/api/competitions").json()} and key not in {f["key"] for f in client.get("/api/data-freshness").json()}
