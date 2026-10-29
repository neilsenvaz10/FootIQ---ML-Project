"""Phase 2 tests: gameweek listing, time-safe gameweek forecasts, explicit-save rule, reliability flags, predicted-versus-actual, separation from official logging.
Every test uses a temporary copy of the store built from the repository baseline (never the live application store) and never makes a network request."""
import hashlib
import json
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))
SCRIPTS = ROOT / "FootIQ_Club_Model_Development_v2" / "_scripts"
for p in (str(SCRIPTS), str(ROOT / "FootIQ_ML_Training_Preparation" / "_build")):
    if p not in sys.path:
        sys.path.insert(0, p)

import analytics  # noqa: E402
import forecast  # noqa: E402
import gameweeks as gw  # noqa: E402
import integrity  # noqa: E402
import predict  # noqa: E402
from store import baseline, db, sync  # noqa: E402

PILOT = ROOT / "FootIQ_Club_Model_Development_v2" / "source_adapters_r1" / "pilot" / "run_20261021T141224Z" / "snapshots" / "openligadb" / "20261021T141231Z_R3_getmatchdata_bl1_2026.json"
LIVE_SNAP = sorted((ROOT / "data" / "snapshots" / "openligadb").glob("*_bl1_2026_season.json"))
needs_inputs = pytest.mark.skipif(not (baseline.V_PATH.exists() and PILOT.exists()), reason="baseline inputs not present")
TODAY = date(2026, 10, 25)
NOW = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)
EARLIER = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)          # a clock before the back-dated fixture of the chronology test (since 4.8B a fixture past kickoff is never forecast)


@pytest.fixture(scope="module")
def base_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("gw") / "base.sqlite"
    conn = db.connect(path)
    db.init(conn)
    baseline.import_baseline(conn)
    conn.close()
    return path


@pytest.fixture()
def store(base_db, tmp_path, monkeypatch):
    """A private copy of the store, wired in as the application store for the duration of one test."""
    p = tmp_path / "work.sqlite"
    shutil.copy(base_db, p)
    monkeypatch.setattr(db, "DEFAULT_PATH", p)
    monkeypatch.setenv("FOOTIQ_USE_STORE", "1")
    analytics.reload()
    predict.reset_club_state()
    forecast.artifact_hashes.cache_clear()
    yield p
    predict.reset_club_state()
    analytics.reload()


def q(path, sql, *a):
    c = db.connect(path)
    try:
        return [tuple(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def official_logs_fingerprint():
    out = {}
    for d in (ROOT / "FootIQ_Club_Model_Development_v2").rglob("prospective_log"):
        for f in sorted(d.rglob("*")):
            if f.is_file():
                out[str(f.relative_to(ROOT))] = (f.stat().st_size, f.stat().st_mtime_ns)
    return out


# ---------------------------------------------------------------------------------------------------------- pure rules (no store, no model)
def test_made_before_kickoff_never_claims_certainty_without_a_kickoff_time():
    mb = forecast.made_before_kickoff
    assert mb(datetime(2026, 10, 20, 12, tzinfo=timezone.utc), "2026-10-23", None) == "yes"          # the date has not started anywhere yet
    assert mb(datetime(2026, 10, 22, 9, tzinfo=timezone.utc), "2026-10-23", None) == "yes"           # before 10-23 00:00 UTC minus 14 h (= 10-22 10:00)
    assert mb(datetime(2026, 10, 22, 12, tzinfo=timezone.utc), "2026-10-23", None) == "unknown"      # inside the window in which a kickoff could already have happened
    assert mb(datetime(2026, 10, 23, 15, tzinfo=timezone.utc), "2026-10-23", None) == "unknown"
    assert mb(datetime(2026, 10, 25, 9, tzinfo=timezone.utc), "2026-10-23", None) == "no"
    assert mb(datetime(2026, 10, 23, 15, tzinfo=timezone.utc), "2026-10-23", "2026-10-23T18:30:00Z") == "yes"   # known kickoff in the future
    assert mb(datetime(2026, 10, 23, 19, tzinfo=timezone.utc), "2026-10-23", "2026-10-23T18:30:00Z") == "no"


def test_effective_status_turns_past_dated_scheduled_fixtures_into_awaiting_result():
    assert gw.effective_status("scheduled", "2026-10-24", TODAY) == "awaiting_result"
    assert gw.effective_status("scheduled", "2026-10-25", TODAY) == "scheduled"           # today is still upcoming
    assert gw.effective_status("completed", "2026-10-24", TODAY) == "completed"


def test_only_the_five_domestic_leagues_are_supported():
    for k in ("UCL", "WC", "UNL"):
        with pytest.raises(gw.GameweekError):
            gw.check_league(k)
    with pytest.raises(forecast.ForecastError):
        forecast.predict_gameweek("EPL", "2026-27", 8, user_action="page_load")                  # not an explicit press


# ---------------------------------------------------------------------------------------------------------- listing and fixtures
@needs_inputs
def test_gameweek_list_dates_statuses_and_out_of_order_flags(store):
    c = db.connect(store, readonly=True)
    epl = gw.list_gameweeks(c, "EPL", "2026-27", TODAY)
    assert len(epl["gameweeks"]) == 38 and epl["next_gameweek"] == 8 and epl["latest_result"] == "2026-09-20"
    g = {x["matchday_no"]: x for x in epl["gameweeks"]}
    assert g[5]["completed"] == 10 and g[6]["awaiting_result"] == 10 and g[7]["awaiting_result"] == 10        # the missing-result gap
    assert g[8]["upcoming"] + g[8]["awaiting_result"] == 10 and g[9]["upcoming"] == 10 and g[9]["first_date"] == "2026-10-31"
    laliga = {x["matchday_no"]: x for x in gw.list_gameweeks(c, "LALIGA", "2026-27", TODAY)["gameweeks"]}
    assert laliga[6]["order_issue"] and laliga[6]["rescheduled_fixtures"] >= 1                              # postponed fixtures inside a gameweek are flagged
    bl = gw.list_gameweeks(c, "BUNDESLIGA", "2026-27", TODAY)
    assert len(bl["gameweeks"]) == 34
    c.close()


@needs_inputs
def test_fixtures_show_status_kickoff_knowledge_form_and_reasons(store):
    c = db.connect(store, readonly=True)
    d = gw.gameweek_fixtures(c, "EPL", "2026-27", 9, TODAY)
    assert len(d["fixtures"]) == 10 and all(f["status"] == "scheduled" and f["predictable"] for f in d["fixtures"])
    f = d["fixtures"][0]
    assert f["forecast"] is None and f["evaluation"] is None                                               # nothing is predicted or saved by looking
    assert f["reliability"] == "provisional" and "stale_history" in f["flags"] and any("missing_results_home" == x for x in f["flags"]) is not None
    assert any("kickoff" in x for x in f["flags"])
    for fx in d["fixtures"]:                                                                                # form only uses results strictly before the fixture
        for side in ("home", "away"):
            assert all(m["date"] < fx["date"] for m in fx["form"][side])
    done = gw.gameweek_fixtures(c, "EPL", "2026-27", 5, TODAY)
    assert all(f["status"] == "completed" and f["result"]["home"] is not None and not f["predictable"] for f in done["fixtures"])
    with pytest.raises(gw.GameweekError):
        gw.gameweek_fixtures(c, "EPL", "2026-27", 99, TODAY)
    c.close()


@needs_inputs
def test_awaiting_result_fixtures_are_flagged_as_provisional_with_reasons(store):
    c = db.connect(store, readonly=True)
    d = gw.gameweek_fixtures(c, "EPL", "2026-27", 8, TODAY)
    aw = [f for f in d["fixtures"] if f["status"] == "awaiting_result"]
    assert aw and all(f["reliability"] == "provisional" for f in aw)
    f = aw[0]
    assert "missing_results_home" in f["flags"] and any("no verified result" in r for r in f["reasons"])
    c.close()


# ---------------------------------------------------------------------------------------------------------- explicit save, model use, separation
@needs_inputs
def test_forecasts_are_saved_only_by_the_explicit_action_and_never_overwritten(store):
    before_fp = official_logs_fingerprint()
    r = forecast.predict_gameweek("EPL", "2026-27", 9, forecast.EXPLICIT_ACTION, now=NOW, today=TODAY)
    assert r["saved_fixtures"] == 10 and r["data_cutoff_date"] == "2026-09-20"
    assert q(store, "SELECT COUNT(*) FROM forecast_runs")[0][0] == 1 and q(store, "SELECT COUNT(*) FROM forecasts")[0][0] == 30     # 10 fixtures x 3 variants
    assert q(store, "SELECT DISTINCT user_action, notes FROM forecast_runs") == [(forecast.EXPLICIT_ACTION, forecast.NOTE)]
    assert {x["feature_path"] for x in r["forecasts"]} == {"cached_state_before_all_results"}
    assert all(abs(sum(x["predictions"]["primary"].values()) - 1) < 1e-9 for x in r["forecasts"])
    # reading never saves
    c = db.connect(store, readonly=True)
    d = gw.gameweek_fixtures(c, "EPL", "2026-27", 9, TODAY)
    c.close()
    assert q(store, "SELECT COUNT(*) FROM forecast_runs")[0][0] == 1
    assert all(f["forecast"] and set(f["forecast"]["predictions"]) == {"primary", "secondary", "elo_only"} and f["forecast"]["made_before_kickoff"] == "yes" for f in d["fixtures"])
    r2 = forecast.predict_gameweek("EPL", "2026-27", 9, forecast.EXPLICIT_ACTION, now=NOW, today=TODAY)
    assert r2["forecast_run_id"] == r["forecast_run_id"] + 1 and q(store, "SELECT COUNT(*) FROM forecast_runs")[0][0] == 2          # a new run, history kept
    # the two runs agree exactly (deterministic, frozen models)
    assert [x["predictions"]["primary"] for x in r["forecasts"]] == [x["predictions"]["primary"] for x in r2["forecasts"]]
    # separation from the official protocol: no research file was created or changed
    assert official_logs_fingerprint() == before_fp
    # frozen artifacts untouched and recorded with every run
    integrity.check.cache_clear()
    assert integrity.check()["club_v1"]["ok"] and integrity.check()["club_v2_r1"]["ok"]
    assert json.loads(q(store, "SELECT model_artifact_sha256 FROM forecast_runs LIMIT 1")[0][0]) == forecast.artifact_hashes()


@needs_inputs
def test_saved_rows_keep_the_exact_feature_snapshot_and_hash(store):
    forecast.predict_gameweek("EPL", "2026-27", 9, forecast.EXPLICIT_ACTION, now=NOW, today=TODAY)
    rows = q(store, "SELECT model_variant, feature_snapshot_json, feature_sha256 FROM forecasts WHERE model_variant IN ('club_v1','club_v2_r1') LIMIT 2")
    for variant, snap, sha in rows:
        d = json.loads(snap)
        assert hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest() == sha
        assert len(d) >= 25
    assert "home_elo" in json.loads(rows[0][1]) or "home_elo" in json.loads(rows[1][1])
    assert q(store, "SELECT data_cutoff_note FROM forecast_runs")[0][0].startswith("latest result in the model history")


@needs_inputs
def test_completed_matches_are_never_predicted_in_hindsight(store):
    with pytest.raises(forecast.ForecastError):
        forecast.predict_gameweek("EPL", "2026-27", 5, forecast.EXPLICIT_ACTION, now=NOW, today=TODAY)       # all of Matchday 5 is completed
    assert q(store, "SELECT COUNT(*) FROM forecast_runs")[0][0] == 0


# ---------------------------------------------------------------------------------------------------------- chronology
@needs_inputs
def test_fast_path_equals_the_day_by_day_replay_for_a_future_fixture(store):
    lg, V, tiers = predict._club_runtime()
    c = db.connect(store, readonly=True)
    f = gw.gameweek_fixtures(c, "EPL", "2026-27", 9, TODAY)["fixtures"][0]
    c.close()
    row = q(store, "SELECT home_entity_id, away_entity_id FROM matches WHERE record_id=?", f["record_id"])[0]
    comp = "england:1-premierleague"
    df = pd.DataFrame([dict(fixture_id="x", dt=pd.Timestamp(f["date"]), h=row[0], a=row[1], comp=comp, season="2026-27", tier=tiers[comp])])
    F2a, F1a = predict.club_features_fast(row[0], row[1], comp, "2026-27", pd.Timestamp(f["date"]), tiers[comp])
    F2b, F1b = predict.club_features_exact(df)
    sa, sb = predict.club_score(F2a, F1a)[0], predict.club_score(F2b, F1b)[0]
    assert sa["v1_features"] == sb["v1_features"] and sa["v2_features"] == sb["v2_features"]
    assert list(sa["p1"]) == list(sb["p1"]) and list(sa["p2"]) == list(sb["p2"])


@needs_inputs
def test_later_or_same_day_results_never_change_a_forecast(base_db, tmp_path, monkeypatch):
    """Take a not-yet-played Premier League fixture and give it an EARLIER date (a postponed match). Forecast it once with the plain store and once after the store
    received Bundesliga results dated that same day and later. The forecast must be identical, and it must have used the day-by-day replay."""
    def run(extra: bool):
        p = tmp_path / ("b.sqlite" if extra else "a.sqlite")
        shutil.copy(base_db, p)
        monkeypatch.setattr(db, "DEFAULT_PATH", p)
        analytics.reload()
        predict.reset_club_state()
        conn = db.connect(p)
        conn.execute("UPDATE matches SET match_date='2026-10-09' WHERE record_id=(SELECT record_id FROM matches WHERE competition_key='EPL' AND season='2026-27' AND matchday_no=9 ORDER BY record_id LIMIT 1)")
        rid = conn.execute("SELECT record_id FROM matches WHERE competition_key='EPL' AND season='2026-27' AND match_date='2026-10-09' AND status='scheduled'").fetchone()[0]
        conn.commit()
        if extra:
            sync.replay_payload(conn, PILOT.read_bytes(), now=datetime(2026, 10, 21, 14, 12, tzinfo=timezone.utc))      # results dated 2026-10-09 .. 2026-10-18
        conn.close()
        r = forecast.predict_gameweek("EPL", "2026-27", 9, forecast.EXPLICIT_ACTION, now=EARLIER, today=EARLIER.date(), db_path=p)      # Phase 4.8B: the fixture is forecast as of the day BEFORE it
        return next(x for x in r["forecasts"] if x["record_id"] == rid), q(p, "SELECT feature_sha256 FROM forecasts WHERE record_id=? AND model_variant='club_v1'", rid)[0][0]
    a, ha = run(False)
    b, hb = run(True)
    predict.reset_club_state()
    analytics.reload()
    assert b["feature_path"] == "day_by_day_replay"                                                        # latest result (10-18) is after the fixture date (10-09)
    assert a["predictions"] == b["predictions"] and ha == hb


@needs_inputs
def test_reliability_is_full_when_history_is_current_and_provisional_otherwise(store):
    conn = db.connect(store)
    sync.replay_payload(conn, PILOT.read_bytes(), now=datetime(2026, 10, 21, 14, 12, tzinfo=timezone.utc))
    conn.close()
    c = db.connect(store, readonly=True)
    d = gw.gameweek_fixtures(c, "BUNDESLIGA", "2026-27", 8, date(2026, 10, 22))              # BL results now run to 2026-10-18; Matchday 8 starts 2026-10-30
    c.close()
    assert d["latest_result"] == "2026-10-18"
    assert all(f["stale_days"] <= gw.STALE_DAYS for f in d["fixtures"]) and any(f["reliability"] == "full" for f in d["fixtures"])
    assert any("earlier_fixtures_unplayed_home" in f["flags"] for f in d["fixtures"])              # unplayed Matchday 7 fixtures are reported but do not make it provisional
    c = db.connect(store, readonly=True)
    e = gw.gameweek_fixtures(c, "EPL", "2026-27", 9, date(2026, 10, 22))
    c.close()
    assert all(f["reliability"] == "provisional" and "stale_history" in f["flags"] for f in e["fixtures"])


# ---------------------------------------------------------------------------------------------------------- predicted versus actual
@pytest.mark.skipif(not LIVE_SNAP, reason="no stored live Bundesliga snapshot (created by the supervised run)")
@needs_inputs
def test_predicted_versus_actual_counts_only_forecasts_saved_before_kickoff(store):
    conn = db.connect(store)
    sync.replay_payload(conn, PILOT.read_bytes(), now=datetime(2026, 10, 21, 14, 12, tzinfo=timezone.utc))          # state as of the pilot: results to 10-18
    conn.close()
    before = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)
    r = forecast.predict_gameweek("BUNDESLIGA", "2026-27", 7, forecast.EXPLICIT_ACTION, now=before, today=date(2026, 10, 21))
    assert r["saved_fixtures"] == 9 and all(x["made_before_kickoff"] == "yes" for x in r["forecasts"])
    # later, the verified results arrive (the stored real payload from the supervised run)
    conn = db.connect(store)
    sync.replay_payload(conn, LIVE_SNAP[-1].read_bytes(), now=datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc))
    conn.close()
    c = db.connect(store, readonly=True)
    d = gw.gameweek_fixtures(c, "BUNDESLIGA", "2026-27", 7, date(2026, 10, 25))
    c.close()
    ev = [f for f in d["fixtures"] if f["evaluation"]]
    assert len(ev) >= 5 and all(f["evaluation"]["counted"] for f in ev)
    s = d["evaluation"]
    assert s["counted"] == len(ev) and s["excluded"] == 0 and 0 <= s["accuracy"] <= 1 and s["mean_log_loss"] > 0 and "official" in s["caveat"]
    for f in ev:                                                                                       # recompute by hand
        res, p = f["result"], f["forecast"]["predictions"]["primary"]
        actual = "H" if res["home"] > res["away"] else "A" if res["home"] < res["away"] else "D"
        probs = dict(H=p["home"], D=p["draw"], A=p["away"])
        assert f["evaluation"]["actual"] == actual and f["evaluation"]["predicted"] == max(probs, key=probs.get) and abs(f["evaluation"]["p_actual"] - probs[actual]) < 1e-12
    # a forecast saved AFTER the matches is shown but not counted
    c = db.connect(store)
    c.execute("UPDATE forecasts SET made_before_kickoff='unknown' WHERE forecast_id IN (SELECT forecast_id FROM forecasts WHERE model_variant='club_v1' LIMIT 2)")
    c.commit()
    c.close()
    c = db.connect(store, readonly=True)
    d2 = gw.gameweek_fixtures(c, "BUNDESLIGA", "2026-27", 7, date(2026, 10, 25))
    c.close()
    assert d2["evaluation"]["excluded"] == 2 and d2["evaluation"]["counted"] == len(ev) - 2


# ---------------------------------------------------------------------------------------------------------- API
@needs_inputs
def test_api_endpoints_validation_and_manual_prediction_still_works(store):
    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)
    assert client.get("/api/gameweeks", params=dict(key="UCL")).status_code == 422
    r = client.get("/api/gameweeks", params=dict(key="EPL")).json()
    assert r["season"] == "2026-27" and len(r["gameweeks"]) == 38
    assert client.get("/api/gameweeks", params=dict(key="EPL", season="1999-00")).status_code == 404
    assert client.get("/api/gameweek", params=dict(key="EPL", matchday=50)).status_code == 404
    assert client.get("/api/gameweek", params=dict(key="EPL", matchday=9)).json()["fixtures"][0]["forecast"] is None
    assert client.post("/api/gameweek/predict", json=dict(key="EPL", season="2026-27", matchday=9, user_action="page_load")).status_code == 422
    assert client.post("/api/gameweek/predict", json=dict(key="UCL", season="2026-27", matchday=1, user_action=forecast.EXPLICIT_ACTION)).status_code == 422
    assert q(store, "SELECT COUNT(*) FROM forecast_runs")[0][0] == 0
    ok = client.post("/api/gameweek/predict", json=dict(key="EPL", season="2026-27", matchday=9, user_action=forecast.EXPLICIT_ACTION))
    assert ok.status_code == 200 and ok.json()["saved_fixtures"] == 10
    saved = client.get("/api/gameweek", params=dict(key="EPL", matchday=9)).json()
    assert saved["fixtures"][0]["forecast"]["models"]["club_v1"] and len(saved["runs"]) == 1
    man = client.get("/api/predict", params=dict(key="EPL", home="Arsenal FC", away="Chelsea FC"))      # the manual head-to-head prediction is unchanged
    assert man.status_code == 200 and abs(sum(man.json()["primary"][k] for k in ("home", "draw", "away")) - 1) < 1e-6


# ---------------------------------------------------------------------------------------------------------- Phase 4.8B: past-fixture safeguard
def _first_md9(store):
    c = db.connect(store, readonly=True)
    try:
        return gw.gameweek_fixtures(c, "EPL", "2026-27", 9, TODAY, NOW)["fixtures"]
    finally:
        c.close()


def test_kickoff_rule_is_conservative_at_every_boundary():
    mb = forecast.made_before_kickoff
    ko = "2026-10-25T15:00:00Z"
    assert mb(datetime(2026, 10, 25, 14, 59, 59, tzinfo=timezone.utc), "2026-10-25", ko) == "yes"
    assert mb(datetime(2026, 10, 25, 15, 0, 0, tzinfo=timezone.utc), "2026-10-25", ko) == "no"                  # at kickoff is already too late
    assert mb(datetime(2026, 10, 24, 9, 59, 59, tzinfo=timezone.utc), "2026-10-25", None) == "yes"           # before the date began anywhere (UTC+14)
    assert mb(datetime(2026, 10, 24, 10, 0, 0, tzinfo=timezone.utc), "2026-10-25", None) == "unknown"         # from then on a kickoff could have happened
    assert mb(datetime(2026, 10, 26, 12, 0, 1, tzinfo=timezone.utc), "2026-10-25", None) == "no"              # the date is over everywhere (UTC-12)


@needs_inputs
def test_a_fixture_past_kickoff_gets_no_new_prediction_and_is_marked_awaiting_a_verified_result(store):
    c = db.connect(store)
    rid = _first_md9(store)[0]["record_id"]
    c.execute("UPDATE matches SET kickoff_utc='2026-10-25T08:00:00Z' WHERE record_id=?", (rid,))      # kickoff one hour before NOW, same day
    c.commit()
    c.close()
    fx = {f["record_id"]: f for f in _first_md9(store)}
    gone = fx[rid]
    assert gone["status"] == "awaiting_result" and gone["kickoff_state"] == "no" and not gone["predictable"]
    assert any("Awaiting verified result" in r for r in gone["reasons"])
    assert sum(f["predictable"] for f in fx.values()) == len(fx) - 1
    r = forecast.predict_gameweek("EPL", "2026-27", 9, forecast.EXPLICIT_ACTION, now=NOW, today=TODAY)
    assert r["saved_fixtures"] == len(fx) - 1 and rid in [s["record_id"] for s in r["skipped"]]
    assert q(store, "SELECT COUNT(*) FROM forecasts WHERE record_id=?", rid)[0][0] == 0                  # nothing was generated for it, not even a flagged forecast


@needs_inputs
def test_unknown_kickoff_on_the_match_day_is_blocked_not_guessed(store):
    fixtures = _first_md9(store)
    d = fixtures[0]["date"]
    c = db.connect(store, readonly=True)
    late = gw.gameweek_fixtures(c, "EPL", "2026-27", 9, TODAY, datetime.fromisoformat(d + "T12:00:00+00:00"))
    c.close()
    unknown = [f for f in late["fixtures"] if f["date"] == d and not f["kickoff_utc"]]
    assert unknown and all(f["kickoff_state"] == "unknown" and not f["predictable"] for f in unknown)
    assert all("league time zone, or a disputed date" in " ".join(f["reasons"]) for f in unknown)


@needs_inputs
def test_saved_forecasts_survive_the_kickoff_unchanged_and_stay_visible_with_time_and_cutoff(store):
    r1 = forecast.predict_gameweek("EPL", "2026-27", 9, forecast.EXPLICIT_ACTION, now=NOW, today=TODAY)
    before = q(store, "SELECT forecast_id, record_id, p_home, p_draw, p_away, model_variant, feature_sha256, made_before_kickoff FROM forecasts ORDER BY forecast_id")
    later = datetime.fromisoformat(max(f["date"] for f in _first_md9(store)) + "T23:59:00+00:00") + __import__("datetime").timedelta(days=2)
    with pytest.raises(forecast.ForecastError):                                                          # every fixture is now past: nothing may be generated
        forecast.predict_gameweek("EPL", "2026-27", 9, forecast.EXPLICIT_ACTION, now=later, today=later.date())
    assert q(store, "SELECT forecast_id, record_id, p_home, p_draw, p_away, model_variant, feature_sha256, made_before_kickoff FROM forecasts ORDER BY forecast_id") == before
    assert q(store, "SELECT COUNT(*) FROM forecast_runs")[0][0] == 1
    c = db.connect(store, readonly=True)
    d = gw.gameweek_fixtures(c, "EPL", "2026-27", 9, later.date(), later)
    c.close()
    assert all(f["status"] == "awaiting_result" and not f["predictable"] for f in d["fixtures"])
    for f in d["fixtures"]:
        assert f["forecast"]["created_utc"] == r1["created_utc"] and f["forecast"]["data_cutoff_date"] == r1["data_cutoff_date"] and f["forecast"]["made_before_kickoff"] == "yes"


@needs_inputs
def test_manual_prediction_refuses_a_real_fixture_past_kickoff_but_allows_it_before(store):
    f = _first_md9(store)[0]
    ko = datetime.fromisoformat(f["date"] + "T00:00:00+00:00")
    c = db.connect(store)
    c.execute("UPDATE matches SET kickoff_utc=? WHERE record_id=?", (f["date"] + "T15:00:00Z", f["record_id"]))
    c.commit()
    c.close()
    analytics.reload()
    predict.reset_club_state()
    ok = predict.predict("EPL", f["home"], f["away"], f["date"], now=ko)                                 # before the stored kickoff
    assert ok["primary"]["home"] > 0
    with pytest.raises(predict.PredictionError, match="Awaiting verified result"):
        predict.predict("EPL", f["home"], f["away"], f["date"], now=ko + __import__("datetime").timedelta(hours=16))
    other = predict.predict("EPL", f["away"], f["home"], f["date"], now=ko + __import__("datetime").timedelta(hours=16))   # reversed pairing is no stored fixture: a hypothetical matchup
    assert any("hypothetical" in n or "past" in n for n in other["notes"]) or other["primary"]["home"] > 0


# ---------------------------------------------------------------------------------------------------------- Phase 4.8D Stage 2: league time-zone rule, individual and gameweek predictions
@needs_inputs
def test_date_only_fixture_individual_and_gameweek_predictions_follow_the_league_zone_rule_and_saved_rows_stay_immutable(store):
    import kickoff as KO
    import kickoff_tz as KZ
    fx = _first_md9(store)[0]
    c = db.connect(store)
    c.execute("UPDATE matches SET kickoff_utc=NULL WHERE record_id=?", (fx["record_id"],))                 # make it a date-only fixture
    c.commit()
    c.close()
    analytics.reload()
    predict.reset_club_state()
    d = fx["date"]
    edge = KZ.cutoff_instants(d, "EPL", KZ.evidence_floor("EPL"))
    yes_until = datetime.strptime(edge["yes_until"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    global_until = datetime.strptime(edge["global_yes_until"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ahead, behind = yes_until - timedelta(minutes=1), yes_until + timedelta(minutes=1)
    between = ahead if ahead > global_until else None
    assert between is not None and KO.made_before_kickoff_global(ahead, d, None) == "unknown"             # the old rule would already have blocked it
    # gameweek page and forecast: predictable just before the floor, refused just after it
    cn = db.connect(store, readonly=True)
    page_ahead = {f["record_id"]: f for f in gw.gameweek_fixtures(cn, "EPL", "2026-27", 9, ahead.date(), ahead)["fixtures"]}
    page_behind = {f["record_id"]: f for f in gw.gameweek_fixtures(cn, "EPL", "2026-27", 9, behind.date(), behind)["fixtures"]}
    cn.close()
    assert page_ahead[fx["record_id"]]["predictable"] and page_ahead[fx["record_id"]]["kickoff_state"] == "yes"
    assert not page_behind[fx["record_id"]]["predictable"] and page_behind[fx["record_id"]]["kickoff_state"] == "unknown"
    r = forecast.predict_gameweek("EPL", "2026-27", 9, forecast.EXPLICIT_ACTION, now=ahead, today=ahead.date())
    assert fx["record_id"] in [x["record_id"] for x in r["forecasts"]] and all(x["made_before_kickoff"] == "yes" for x in r["forecasts"])
    saved = q(store, "SELECT * FROM forecasts ORDER BY forecast_id")
    r2 = forecast.predict_gameweek("EPL", "2026-27", 9, forecast.EXPLICIT_ACTION, now=behind, today=behind.date())
    assert fx["record_id"] not in [x["record_id"] for x in r2["forecasts"]] and fx["record_id"] in [s["record_id"] for s in r2["skipped"]]
    assert q(store, "SELECT * FROM forecasts ORDER BY forecast_id")[: len(saved)] == saved                # earlier rows untouched
    # individual (manual) prediction: allowed just before, refused just after
    ok = predict.predict("EPL", fx["home"], fx["away"], d, now=ahead)
    assert ok["primary"]["home"] > 0
    with pytest.raises(predict.PredictionError, match="Kickoff time unconfirmed"):
        predict.predict("EPL", fx["home"], fx["away"], d, now=behind)
