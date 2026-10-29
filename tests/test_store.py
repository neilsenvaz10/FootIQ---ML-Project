"""Phase 1 tests: SQLite store, offline baseline import, parity, provenance, idempotency, frozen-artifact integrity, sync safety.
No test makes a network request: payloads come from the read-only OpenLigaDB pilot snapshot already in the repository."""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

import config as C  # noqa: E402
import integrity  # noqa: E402
from store import baseline, db, sync, views  # noqa: E402

PILOT = ROOT / "FootIQ_Club_Model_Development_v2" / "source_adapters_r1" / "pilot" / "run_20261021T141224Z" / "snapshots" / "openligadb" / "20261021T141231Z_R3_getmatchdata_bl1_2026.json"
needs_inputs = pytest.mark.skipif(not (baseline.V_PATH.exists() and PILOT.exists()), reason="baseline inputs / pilot snapshot not present")
NOW = datetime(2026, 10, 21, 14, 12, tzinfo=timezone.utc)
SCRIPTS = ROOT / "FootIQ_Club_Model_Development_v2" / "_scripts"
for p in (str(SCRIPTS), str(ROOT / "FootIQ_ML_Training_Preparation" / "_build")):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(scope="module")
def base_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("store") / "base.sqlite"
    conn = db.connect(path)
    db.init(conn)
    out = baseline.import_baseline(conn)
    conn.close()
    return path, out


@pytest.fixture()
def work_db(base_db, tmp_path):
    p = tmp_path / "work.sqlite"
    shutil.copy(base_db[0], p)
    conn = db.connect(p)
    yield conn, p
    conn.close()


def q(conn, sql, *a):
    return [tuple(r) for r in conn.execute(sql, a)]


# ------------------------------------------------------------------------------------------------ schema
@needs_inputs
def test_schema_has_every_planned_table_and_phase_2_3_tables_are_empty(base_db):
    conn = db.connect(base_db[0], readonly=True)
    tables = {r[0] for r in q(conn, "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"competitions", "teams", "team_aliases", "matches", "match_sources", "source_snapshots", "sync_runs", "sync_errors", "quarantine", "source_state", "forecast_runs", "forecasts", "simulation_runs"} <= tables
    assert q(conn, "SELECT COUNT(*) FROM forecasts")[0][0] == 0 and q(conn, "SELECT COUNT(*) FROM forecast_runs")[0][0] == 0   # nothing is logged in Phase 1
    with pytest.raises(Exception):                                       # status vocabulary is enforced
        conn2 = db.connect(base_db[0])
        conn2.execute("INSERT INTO matches(record_id, kind, status) VALUES ('x','club','live')")
    conn.close()


@needs_inputs
def test_baseline_counts_and_statuses(base_db):
    path, out = base_db
    conn = db.connect(path, readonly=True)
    assert out["matches"]["inserted"] == 219954 and out["quality"]["v_rows"] == 216553
    assert dict(q(conn, "SELECT status, COUNT(*) FROM matches GROUP BY status")) == {"completed": 219746, "awarded": 205, "abandoned": 3, "scheduled": 3126, "awaiting_result": 430}
    assert q(conn, "SELECT COUNT(*) FROM matches WHERE in_universe=1")[0][0] == 216553
    awaiting = dict(q(conn, "SELECT competition_key, COUNT(*) FROM matches WHERE status='awaiting_result' AND competition_key IS NOT NULL GROUP BY 1"))
    assert awaiting == {"EPL": 20, "LALIGA": 20, "BUNDESLIGA": 18, "SERIEA": 20, "LIGUE1": 18}      # the 96 played matches missing from the source
    conn.close()


# ------------------------------------------------------------------------------------------------ parity
@needs_inputs
def test_dashboard_view_equals_the_original_csv_exactly(base_db):
    conn = db.connect(base_db[0], readonly=True)
    d = views.dashboard_matches(conn).astype(str)
    m = pd.read_csv(C.MATCHES_CSV, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    assert list(d.columns) == list(m.columns) and len(d) == len(m) == 20449
    for col in m.columns:
        assert (d[col].values == m[col].values).all(), col
    conn.close()


@needs_inputs
def test_model_universe_equals_the_frozen_pickle(base_db):
    import d11_prospective_logger as lg

    conn = db.connect(base_db[0], readonly=True)
    V = pd.read_pickle(baseline.V_PATH)
    a = lg.universe_frame(V).sort_values("record_id").reset_index(drop=True)
    b = lg.universe_frame(views.model_universe(conn)).sort_values("record_id").reset_index(drop=True)
    assert a.equals(b)
    conn.close()


@needs_inputs
def test_predictions_from_the_store_equal_predictions_from_the_frozen_pickle(base_db):
    import d11_prospective_logger as lg

    conn = db.connect(base_db[0], readonly=True)
    Vp, Vs = pd.read_pickle(baseline.V_PATH), views.model_universe(conn)
    tier = Vp.groupby("competition_id").tier.first()
    ent = {}
    for name, comp in (("Arsenal FC", "england:1-premierleague"), ("Chelsea FC", "england:1-premierleague"), ("Juventus FC", "italy:1-seriea"), ("AC Milan", "italy:1-seriea")):
        ent[name] = q(conn, "SELECT home_entity_id FROM matches WHERE competition_id=? AND home_name=? ORDER BY match_date DESC LIMIT 1", comp, name)[0][0]
    fx = pd.DataFrame(dict(fixture_id=["a", "b"], dt=[pd.Timestamp("2026-09-21")] * 2, h=[ent["Arsenal FC"], ent["Juventus FC"]], a=[ent["Chelsea FC"], ent["AC Milan"]],
                           comp=["england:1-premierleague", "italy:1-seriea"], season=["2026-27"] * 2, tier=[tier["england:1-premierleague"], tier["italy:1-seriea"]], home_name=["x", "y"], away_name=["x", "y"],
                           kickoff=["x"] * 2, kickoff_known=[False] * 2))
    r1 = lg.make_predictions(fx, Vp, "x", "x", "x")
    r2 = lg.make_predictions(fx, Vs, "x", "x", "x")
    for a, b in zip(r1, r2):
        for k in ("p_home", "p_draw", "p_away", "v1_p_home", "v1_p_draw", "v1_p_away", "v2_feature_sha256"):
            assert a[k] == b[k], k
    conn.close()


# ------------------------------------------------------------------------------------------------ provenance and idempotency
@needs_inputs
def test_every_match_has_provenance_and_inputs_are_hashed(base_db):
    conn = db.connect(base_db[0], readonly=True)
    assert q(conn, "SELECT COUNT(*) FROM matches m WHERE NOT EXISTS (SELECT 1 FROM match_sources s WHERE s.record_id=m.record_id)")[0][0] == 0
    assert q(conn, "SELECT COUNT(*) FROM match_sources WHERE licence IS NULL OR licence=''")[0][0] == 0
    snaps = dict(q(conn, "SELECT snapshot_id, sha256 FROM source_snapshots"))
    frozen = json.loads((ROOT / "FootIQ_Club_Model_Development_v2" / "final_refit_v2_r1" / "artifacts" / "FROZEN.json").read_text(encoding="utf-8"))["input_sha256"]["universe_pkl"]
    assert snaps["baseline-universe-v1.1"] == frozen                       # the imported universe is byte-for-byte the frozen training universe
    assert all(len(v) == 64 for v in snaps.values())
    reasons = {r[0] for r in q(conn, "SELECT reason FROM quarantine")}
    assert any(r.startswith("unresolved team identity") for r in reasons) and any("duplicates an already" in r for r in reasons)
    conn.close()


@needs_inputs
def test_baseline_import_is_idempotent(work_db):
    conn, _ = work_db
    before = q(conn, "SELECT COUNT(*), SUM(change_count) FROM matches")[0]
    out = baseline.import_baseline(conn)
    assert out["matches"] == dict(inserted=0, updated=0, unchanged=219954) and out["fixtures"]["inserted"] == 0 and out["fixtures"]["updated"] == 0
    assert q(conn, "SELECT COUNT(*), SUM(change_count) FROM matches")[0] == before
    assert q(conn, "SELECT COUNT(*) FROM match_sources")[0][0] == 223510


# ------------------------------------------------------------------------------------------------ offline replay of the OpenLigaDB pilot payload
@needs_inputs
def test_replay_recovers_the_18_missing_bundesliga_results_and_is_idempotent(work_db):
    conn, _ = work_db
    payload = PILOT.read_bytes()
    r1 = sync.replay_payload(conn, payload, now=NOW)
    assert r1["records"] == 306 and r1["confirmed"] == 36 and r1["updated"] >= 18 and r1["quarantined"] == 0 and r1["inserted"] == 0   # matches the recorded pilot: 36/36 agree, 18 recovered
    assert q(conn, "SELECT COUNT(*) FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='completed'")[0][0] == 54
    assert q(conn, "SELECT COUNT(*) FROM matches WHERE competition_key='BUNDESLIGA' AND status='awaiting_result'")[0][0] == 0
    assert q(conn, "SELECT MAX(match_date) FROM matches WHERE competition_key='BUNDESLIGA' AND status='completed'")[0][0] == "2026-10-18"
    assert q(conn, "SELECT COUNT(*) FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND kickoff_utc IS NOT NULL")[0][0] == 270     # 306 minus the 36 baseline results, which stay untouched
    assert q(conn, "SELECT COUNT(*) FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND in_universe=1 AND change_count>0")[0][0] == 18   # only the 18 recovered results changed
    assert q(conn, "SELECT COUNT(*) FROM match_sources WHERE source='openligadb' AND role='confirmation'")[0][0] >= 36
    assert q(conn, "SELECT COUNT(*) FROM match_sources WHERE source='openligadb' AND role='primary'")[0][0] == 18      # OpenLigaDB is the primary source of exactly the 18 results it supplied
    r2 = sync.replay_payload(conn, payload, now=NOW)
    assert r2["inserted"] == 0 and r2["updated"] == 0 and r2["quarantined"] == 0           # same payload twice changes nothing
    assert q(conn, "SELECT COUNT(*) FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27'")[0][0] == 306   # no duplicate rows
    assert q(conn, "SELECT COUNT(*) FROM match_sources WHERE source='openligadb'")[0][0] == 306
    assert q(conn, "SELECT COUNT(*) FROM match_sources WHERE source='openligadb' AND role='primary'")[0][0] == 18


@needs_inputs
def test_replay_never_creates_a_second_row_for_a_match(work_db):
    conn, _ = work_db
    sync.replay_payload(conn, PILOT.read_bytes(), now=NOW)
    dup = q(conn, "SELECT competition_id, season, home_entity_id, away_entity_id, COUNT(*) c FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' GROUP BY 1,2,3,4 HAVING c>1")
    assert dup == []


def _mutate(payload: bytes, fn) -> bytes:
    data = json.loads(payload)
    fn(data)
    return json.dumps(data).encode()


@needs_inputs
def test_conflicting_score_is_quarantined_and_never_overwrites(work_db):
    conn, _ = work_db

    def edit(data):
        m = next(x for x in data if x["matchIsFinished"] and x["matchDateTimeUTC"] < "2026-09-21")        # a match the baseline already holds
        for r in m["matchResults"]:
            if r["resultTypeKind"] == "After90Minutes":
                r["pointsTeam1"] += 3

    gid = q(conn, "SELECT home_goals_90 FROM matches WHERE competition_key='BUNDESLIGA' AND status='completed' AND match_date<'2026-09-21' AND season='2026-27' ORDER BY match_date LIMIT 1")
    before = q(conn, "SELECT record_id, home_goals_90, away_goals_90, change_count FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' ORDER BY record_id")
    r = sync.replay_payload(conn, _mutate(PILOT.read_bytes(), edit), now=NOW)
    assert r["quarantined"] == 1 and gid
    assert any("CONFLICT" in x[0] for x in q(conn, "SELECT reason FROM quarantine"))
    after = q(conn, "SELECT record_id, home_goals_90, away_goals_90, change_count FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='completed' AND match_date<'2026-09-21' ORDER BY record_id")
    assert [x for x in before if x in after]                                            # the stored baseline scores are untouched


@needs_inputs
def test_unresolved_team_and_missing_90_minute_type_are_quarantined(work_db):
    conn, _ = work_db

    def edit(data):
        data[0]["team1"]["teamName"] = "Totally Unknown FC"
        fin = [x for x in data if x["matchIsFinished"]][-1]
        fin["matchResults"] = [r for r in fin["matchResults"] if r["resultTypeKind"] != "After90Minutes"] or [dict(resultTypeKind="Unknown", pointsTeam1=1, pointsTeam2=0, resultName="Endergebnis")]

    r = sync.replay_payload(conn, _mutate(PILOT.read_bytes(), edit), now=NOW)
    reasons = " | ".join(x[0] for x in q(conn, "SELECT reason FROM quarantine WHERE source='openligadb'"))
    assert "unresolved team identity" in reasons and "without an explicit 90-minute result" in reasons and r["quarantined"] >= 2


# ------------------------------------------------------------------------------------------------ chronology: no same-day or later leakage
@needs_inputs
def test_results_added_by_a_sync_never_change_a_prediction_for_an_earlier_or_same_day_fixture(work_db):
    import d11_prospective_logger as lg

    conn, _ = work_db
    V0 = views.model_universe(conn)
    sync.replay_payload(conn, PILOT.read_bytes(), now=NOW)
    V1 = views.model_universe(conn)
    assert len(V1) == len(V0) + 18 and V1.dt.max() > V0.dt.max()
    tier = V0.groupby("competition_id").tier.first()["deutschland:1-bundesliga"]
    row = q(conn, "SELECT model_home_entity, model_away_entity, match_date FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='completed' AND match_date='2026-10-09' LIMIT 1")
    h, a, d = row[0][0] or q(conn, "SELECT home_entity_id FROM matches WHERE competition_key='BUNDESLIGA' AND match_date='2026-10-09' LIMIT 1")[0][0], row[0][1] or q(conn, "SELECT away_entity_id FROM matches WHERE competition_key='BUNDESLIGA' AND match_date='2026-10-09' LIMIT 1")[0][0], row[0][2]
    fx = pd.DataFrame(dict(fixture_id=["f"], dt=[pd.Timestamp(d)], h=[h], a=[a], comp=["deutschland:1-bundesliga"], season=["2026-27"], tier=[tier], home_name=["x"], away_name=["x"], kickoff=["x"], kickoff_known=[False]))
    p0 = lg.make_predictions(fx, V0, "x", "x", "x")[0]
    p1 = lg.make_predictions(fx, V1, "x", "x", "x")[0]
    for k in ("p_home", "p_draw", "p_away", "v1_p_home", "v1_p_draw", "v1_p_away", "v2_feature_sha256"):
        assert p0[k] == p1[k], k                    # results dated on or after the fixture's day (same-day included) are not used
    fx2 = fx.assign(dt=pd.Timestamp("2026-10-19"))   # a later date does see them
    q0 = lg.make_predictions(fx2, V0, "x", "x", "x")[0]
    q1 = lg.make_predictions(fx2, V1, "x", "x", "x")[0]
    assert q0["v2_feature_sha256"] != q1["v2_feature_sha256"]


# ------------------------------------------------------------------------------------------------ sync manager safety
def _opener_from(payload: bytes, log: list):
    data = json.loads(payload)

    def opener(url, headers):
        log.append(url)
        assert "OpenLigaDB" in headers["User-Agent"] or "openligaDB" in headers["User-Agent"] or "FootIQ" in headers["User-Agent"]
        path = url.split("api.openligadb.de")[1]
        if path.startswith("/getmatchdata/bl1/2026/"):
            g = int(path.rsplit("/", 1)[1])
            return 200, json.dumps([m for m in data if m["group"]["groupOrderID"] == g]).encode(), {}
        if path == "/getmatchdata/bl1/2026":
            return 200, payload, {}
        if path == "/getcurrentgroup/bl1":
            return 200, json.dumps({"groupName": "7. Spieltag", "groupOrderID": 7, "groupID": 1}).encode(), {}
        if path.startswith("/getlastchangedate/bl1/2026/"):
            return 200, json.dumps("2026-10-18T19:23:40").encode(), {}
        raise AssertionError(f"unapproved URL requested: {url}")
    return opener


@needs_inputs
def test_live_disabled_makes_no_network_request_and_writes_nothing(work_db):
    conn, path = work_db
    log = []
    mgr = sync.SyncManager(db_path=path, cfg=sync.SyncConfig(live_enabled=False), opener=lambda u, h: log.append(u) or (200, b"[]", {}))
    res = mgr.check_once("startup_check")
    assert res["outcome"] == "skipped_live_disabled" and log == []
    assert q(conn, "SELECT COUNT(*) FROM sync_runs WHERE kind='startup_check'") == [(0,)]          # Phase 4.8B: a disabled sync writes no row at all
    st = sync.status(conn, mgr.cfg)
    bl = next(c for c in st["competitions"] if c["competition_key"] == "BUNDESLIGA")
    assert bl["state"] == "stale" and bl["approved_sources"] == ["openligadb"] and any("live access is disabled" in r for r in bl["state_reasons"])
    epl = next(c for c in st["competitions"] if c["competition_key"] == "EPL")
    assert epl["state"] == "stale" and epl["approved_sources"] == [] and "no approved fresh source" in epl["state_reasons"][0]
    assert st["live_enabled"] is False and all(c["state"] != "live" for c in st["competitions"])


@needs_inputs
def test_live_path_uses_only_approved_endpoints_with_bounded_requests_and_is_idempotent(work_db, monkeypatch, tmp_path):
    conn, path = work_db
    monkeypatch.setenv("FOOTIQ_CONTACT", "mailto:contact@footiq-test.local")
    monkeypatch.setattr(sync, "SNAPSHOT_DIR", tmp_path / "snap")
    log, changes, sleeps = [], [], []
    mgr = sync.SyncManager(db_path=path, cfg=sync.SyncConfig(live_enabled=True), opener=_opener_from(PILOT.read_bytes(), log), on_change=lambda: changes.append(1), sleep=sleeps.append)
    r1 = mgr.check_once("startup_check")
    assert r1["outcome"] == "ok" and r1["changed"] >= 18 and changes == [1]
    assert len(log) == 1 and log[0].endswith("/getmatchdata/bl1/2026")                    # first run: one request for the season
    first_run_requests = len(log)
    r2 = mgr.check_once("periodic_check")
    assert r2["outcome"] == "ok" and r2["changed"] == 0 and changes == [1]                 # nothing changed -> no refresh
    assert 1 < len(log) <= 1 + 6                                                           # polling: current group + change dates (+ changed matchdays only)
    assert all(u.startswith("https://api.openligadb.de/") for u in log) and all("bl1" in u or "getcurrentgroup" in u for u in log)
    assert len(sleeps) == len(log) - first_run_requests - 1                                # within a run every request after the first waits (>= 3 s apart); runs are minutes apart
    assert q(conn, "SELECT COUNT(*) FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27'")[0][0] == 306
    assert q(conn, "SELECT outcome FROM sync_runs WHERE kind='startup_check'") == [("ok",)]


@needs_inputs
def test_provider_failure_keeps_cached_data_and_marks_the_run_failed(work_db, monkeypatch, tmp_path):
    conn, path = work_db
    monkeypatch.setenv("FOOTIQ_CONTACT", "mailto:contact@footiq-test.local")
    monkeypatch.setattr(sync, "SNAPSHOT_DIR", tmp_path / "snap")
    before = q(conn, "SELECT COUNT(*), MAX(match_date) FROM matches WHERE status='completed'")[0]
    mgr = sync.SyncManager(db_path=path, cfg=sync.SyncConfig(live_enabled=True), opener=lambda u, h: (503, b"", {}), sleep=lambda s: None)
    res = mgr.check_once("startup_check")
    assert res["outcome"] == "error"
    assert q(conn, "SELECT COUNT(*), MAX(match_date) FROM matches WHERE status='completed'")[0] == before          # cache untouched
    assert q(conn, "SELECT COUNT(*) FROM sync_errors")[0][0] >= 1
    bl = next(c for c in sync.status(conn, mgr.cfg)["competitions"] if c["competition_key"] == "BUNDESLIGA")
    assert bl["state"] == "stale"


def test_live_requires_a_real_contact(monkeypatch, tmp_path, base_db):
    monkeypatch.delenv("FOOTIQ_CONTACT", raising=False)
    monkeypatch.setenv("FOOTIQ_CONTACT_FILE", str(tmp_path / "missing.local"))
    shutil.copy(base_db[0], tmp_path / "w.sqlite")
    mgr = sync.SyncManager(db_path=tmp_path / "w.sqlite", cfg=sync.SyncConfig(live_enabled=True), opener=lambda u, h: pytest.fail("no request may be made without a contact"), sleep=lambda s: None)
    assert mgr.check_once("manual_check")["outcome"] == "error"


def test_shipped_config_has_live_access_on_only_for_the_approved_source():
    cfg = sync.SyncConfig.load()                                                         # Phase 4.8E/4.9: Bundesliga and La Liga; Phase 4.15B: startup-only refresh
    assert cfg.live_enabled is True and cfg.approved_competitions() == ["BUNDESLIGA", "LALIGA"] and cfg.startup_check and cfg.periodic_minutes >= 30 and cfg.sync_mode == "startup"
    adapters_cfg = json.loads((ROOT / "FootIQ_Club_Model_Development_v2" / "source_adapters_r1" / "config" / "adapters.json").read_text(encoding="utf-8"))
    assert adapters_cfg["live_enabled"] is False


# ------------------------------------------------------------------------------------------------ frozen artifacts and application wiring
def test_frozen_model_artifacts_are_unchanged_after_all_of_the_above():
    integrity.check.cache_clear()
    res = integrity.check()
    assert res["club_v1"]["ok"] and res["club_v2_r1"]["ok"]


@needs_inputs
def test_analytics_from_the_store_equals_analytics_from_the_csv(monkeypatch, base_db):
    import analytics

    monkeypatch.setattr(db, "DEFAULT_PATH", base_db[0])
    monkeypatch.setenv("FOOTIQ_USE_STORE", "0")
    analytics.reload()
    csv_frame, csv_audit, csv_cov = analytics.matches().copy(), analytics.audit(), analytics.season_coverage("EPL")
    monkeypatch.setenv("FOOTIQ_USE_STORE", "1")
    monkeypatch.setattr(analytics, "use_store", lambda: True)
    monkeypatch.setattr(analytics.store_db, "DEFAULT_PATH", base_db[0])
    monkeypatch.setattr(analytics.store_db, "connect", lambda readonly=False, _c=db.connect: _c(base_db[0], readonly=readonly))
    analytics.reload()
    st_frame = analytics.matches()
    assert st_frame.equals(csv_frame)
    assert analytics.audit() == csv_audit and analytics.season_coverage("EPL") == csv_cov
    audit_csv = pd.read_csv(C.AUDIT_CSV, encoding="utf-8-sig", keep_default_na=False).to_dict("records")
    audit_csv = [r for r in audit_csv if r["competition_key"] in C.BY_KEY]                   # the file prepare_data wrote also lists the five archived competitions
    assert csv_audit == audit_csv                                                            # computed audit equals the file prepare_data wrote (for the six supported)
    analytics.reload()


@needs_inputs
def test_sync_status_endpoint_lists_all_competitions_and_never_says_live():
    from fastapi.testclient import TestClient
    import main

    if not db.exists():
        pytest.skip("run app/store/build.py first")
    r = TestClient(main.app).get("/api/sync/status").json()
    assert [c["competition_key"] for c in r["competitions"]] == [c["key"] for c in C.COMPETITIONS]
    assert r["live_enabled"] is sync.SyncConfig.load().live_enabled and r["attribution"][0]["source"] == "OpenLigaDB"      # follows the shipped switch (on since Phase 4.8E)
    assert all(c["state"] in ("fresh", "stale") for c in r["competitions"])
    assert all(c["state"] != "live" for c in r["competitions"]) and "live score feed" in r["note"]


def test_contact_is_read_from_the_repo_root_config_file_not_the_adapters_folder(monkeypatch, tmp_path):
    """Regression: the supervised run found the sync looked for contact.local inside the research adapters folder, so a configured contact was never seen."""
    original = sync.CONTACT_FILE
    assert original.name == "contact.local" and original.parent.name == "config" and original.parent.parent == ROOT
    f = tmp_path / "contact.local"
    f.write_text("mailto:contact@footiq-test.local", encoding="utf-8")
    monkeypatch.delenv("FOOTIQ_CONTACT", raising=False)
    monkeypatch.delenv("FOOTIQ_CONTACT_FILE", raising=False)
    monkeypatch.setattr(sync, "CONTACT_FILE", f)
    assert sync._adapter_config().contact_configured()
    monkeypatch.setattr(sync, "CONTACT_FILE", tmp_path / "missing.local")
    assert not sync._adapter_config().contact_configured()
