"""Phase 4.8B: the disabled sync writes nothing, and the 6-hour schedule behaves under a mocked clock. Synthetic stores only; no network, no production file."""
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from store import db, sync  # noqa: E402

T0 = datetime(2026, 11, 1, 6, 0, 0, tzinfo=timezone.utc)
FMT = "%Y-%m-%dT%H:%M:%SZ"
OK_RESULT = dict(inserted=0, updated=0, unchanged=0, quarantined=0, requests=1)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot_dir(p: Path) -> dict:
    return {f.name: (f.stat().st_size, sha(f)) for f in sorted(p.parent.iterdir()) if f.name.startswith(p.name)}


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "s.sqlite"
    conn = db.connect(path)
    db.init(conn)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    return path


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


def live_manager(store, monkeypatch, clock, results):
    """A live-enabled manager whose provider call is replaced; `results` is a list consumed one per check (a dict = success, an Exception = failure)."""
    monkeypatch.setattr(sync, "now_utc", lambda: clock().strftime(FMT))
    mgr = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True, periodic_minutes=360), clock=clock, opener=lambda u, h: pytest.fail("no request"))
    calls = []

    def fake(conn, key):
        calls.append(clock())
        r = results.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(mgr, "_sync_openligadb", fake)
    monkeypatch.setattr(sync, "_adapter_config", lambda: type("C", (), {"redact": staticmethod(lambda s: s)})())
    return mgr, calls


def rows(store, sql="SELECT kind, outcome FROM sync_runs ORDER BY run_id"):
    conn = db.connect(store, readonly=True)
    try:
        return [tuple(r) for r in conn.execute(sql)]
    finally:
        conn.close()


# ------------------------------------------------------------------------------------------------ database safety
def test_disabled_manager_is_inert_and_leaves_every_database_file_untouched(store):
    before = snapshot_dir(store)
    mgr = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=False, startup_delay_seconds=0), opener=lambda u, h: pytest.fail("no request"))
    mgr.start()
    assert mgr._thread is None                              # nothing to schedule: no thread
    assert mgr.check_once("startup_check") == dict(outcome="skipped_live_disabled", run_id=None)
    assert mgr.tick() == dict(outcome="skipped_live_disabled", run_id=None)
    assert mgr.next_due() is None
    mgr.stop()
    assert snapshot_dir(store) == before                    # same files, same bytes: no -wal/-shm appeared, no row written
    assert rows(store, "SELECT COUNT(*) FROM sync_runs") == [(0,)]


def test_read_only_connections_do_not_change_the_file(store):
    before = snapshot_dir(store)
    for _ in range(3):
        c = db.connect(store, readonly=True)
        c.execute("SELECT COUNT(*) FROM matches").fetchone()
        c.close()
    c = db.connect(store, readonly=True)
    c.close()
    assert sha(store) == before[store.name][1]


def test_connect_does_not_rewrite_a_database_that_is_already_in_wal_mode(store):
    before = sha(store)
    for _ in range(3):
        db.connect(store).close()
    assert sha(store) == before


# ------------------------------------------------------------------------------------------------ six-hour schedule under a mocked clock
def test_first_check_runs_then_nothing_is_due_for_six_hours(store, monkeypatch):
    clock = Clock()
    mgr, calls = live_manager(store, monkeypatch, clock, [OK_RESULT, OK_RESULT])
    assert mgr.tick("startup_check")["outcome"] == "ok" and len(calls) == 1
    clock.advance(hours=5, minutes=59)
    r = mgr.tick()
    assert r["outcome"] == "not_due" and r["next_due"] == (T0 + timedelta(hours=6)).strftime(FMT) and len(calls) == 1
    clock.advance(minutes=1)
    assert mgr.tick()["outcome"] == "ok" and len(calls) == 2
    assert rows(store) == [("startup_check", "ok"), ("periodic_check", "ok")]


def test_a_restart_inside_the_interval_makes_no_request_and_writes_no_row(store, monkeypatch):
    clock = Clock()
    mgr, calls = live_manager(store, monkeypatch, clock, [OK_RESULT])
    mgr.tick("startup_check")
    clock.advance(hours=1)
    again, calls2 = live_manager(store, monkeypatch, clock, [])        # a new process one hour later
    before = sha(store)
    assert again.tick("startup_check")["outcome"] == "not_due" and calls2 == []
    assert sha(store) == before                                    # a read-only look at a WAL file may create empty -shm/-wal files, but never changes the database file
    wal = Path(str(store) + "-wal")
    assert not wal.exists() or wal.stat().st_size == 0
    assert rows(store, "SELECT COUNT(*) FROM sync_runs") == [(1,)]


def test_failures_back_off_to_twelve_then_twenty_four_hours_and_success_resets(store, monkeypatch):
    clock = Clock()
    boom = RuntimeError("offline")
    mgr, calls = live_manager(store, monkeypatch, clock, [boom, boom, boom, boom, OK_RESULT, OK_RESULT])
    assert mgr.tick("startup_check")["outcome"] == "error"
    assert mgr.next_due() == T0 + timedelta(hours=12)               # one failure doubles the wait
    clock.t = T0 + timedelta(hours=12)
    assert mgr.tick()["outcome"] == "error"
    assert mgr.next_due() == clock.t + timedelta(hours=24)         # two failures: four times, the cap
    clock.advance(hours=24)
    assert mgr.tick()["outcome"] == "error"
    assert mgr.next_due() == clock.t + timedelta(hours=24)         # never longer than the cap
    clock.advance(hours=24)
    assert mgr.tick()["outcome"] == "error"
    clock.advance(hours=24)
    assert mgr.tick()["outcome"] == "ok"
    assert mgr.next_due() == clock.t + timedelta(hours=6)           # back to the normal interval
    assert len(calls) == 5


def test_failed_check_keeps_the_error_and_writes_no_football_data(store, monkeypatch):
    clock = Clock()
    mgr, _ = live_manager(store, monkeypatch, clock, [RuntimeError("HTTP 503")])
    assert mgr.tick("startup_check")["outcome"] == "error"
    assert rows(store, "SELECT COUNT(*) FROM sync_errors") == [(1,)] and rows(store, "SELECT COUNT(*) FROM matches") == [(0,)]


def test_a_second_process_cannot_start_while_a_recent_run_is_open_and_an_abandoned_one_is_released(store, monkeypatch):
    clock = Clock()
    mgr, calls = live_manager(store, monkeypatch, clock, [OK_RESULT])
    conn = db.connect(store)
    conn.execute("INSERT INTO sync_runs(kind, source, started_utc, outcome) VALUES ('periodic_check','all approved',?, 'running')", ((T0 - timedelta(minutes=10)).strftime(FMT),))
    conn.commit()
    conn.close()
    assert mgr.check_once("periodic_check")["outcome"] == "skipped_already_running" and calls == []
    clock.advance(minutes=30)                                       # the open row is now older than the lock window: treated as a crashed run
    assert mgr.check_once("periodic_check")["outcome"] == "ok"
    assert rows(store)[0] == ("periodic_check", "abandoned")


def test_interval_has_a_floor_and_the_shipped_config_is_six_hours_with_live_off():
    low = sync.SyncManager(cfg=sync.SyncConfig(periodic_minutes=1))
    assert low.period_seconds() == sync.MIN_PERIOD_MINUTES * 60
    cfg = sync.SyncConfig.load()
    assert cfg.periodic_minutes == 360                                                                              # (live access is ON since Phase 4.8E; see test_sync_monitoring)


def test_only_the_approved_leagues_can_ever_be_requested_and_the_other_leagues_are_prepared_or_blocked():
    cfg = sync.SyncConfig(live_enabled=True, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "EPL", "LALIGA", "SERIEA", "LIGUE1"]}})
    assert cfg.approved_competitions() == ["BUNDESLIGA", "LALIGA"]                        # a config edit alone cannot add a league: it must also be in APPROVED (EPL, Serie A, Ligue 1 are not)
    assert set(sync.APPROVED) == {"BUNDESLIGA", "LALIGA"} and set(sync.OFFLINE_PREPARED) == {"EPL", "LALIGA"}
    assert {k: v[0] for k, v in sync.READINESS.items()} == {"BUNDESLIGA": "approved_live_disabled", "EPL": "prepared_offline", "LALIGA": "approved_live_disabled", "SERIEA": "prepared_needs_token", "LIGUE1": "prepared_needs_token"}


# ------------------------------------------------------------------------------------------------ Phase 4.8C: honest freshness
sys.path.insert(0, str(ROOT / "tests"))
from test_featured import add_match, add_team  # noqa: E402


def run_row(store, **kw):
    c = db.connect(store)
    cols = dict(kind="sync", source="openligadb", competition_key="BUNDESLIGA", started_utc="2026-11-01T05:00:00Z", finished_utc="2026-11-01T05:00:05Z", outcome="ok", requests=1, inserted=0, updated=0, quarantined=0)
    cols.update(kw)
    c.execute(f"INSERT INTO sync_runs({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(cols.values()))
    c.commit()
    c.close()


def bl_status(store, now=datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)):
    c = db.connect(store, readonly=True)
    try:
        return {x["competition_key"]: x for x in sync.status(c, sync.SyncConfig(), now)["competitions"]}
    finally:
        c.close()


def test_an_offline_import_is_an_import_but_never_an_external_check(store):
    run_row(store, kind="offline_snapshot_import", competition_key="BUNDESLIGA", requests=0, updated=5, started_utc="2026-11-01T09:00:00Z", finished_utc="2026-11-01T09:00:01Z")
    bl = bl_status(store)["BUNDESLIGA"]
    assert bl["last_successful_external_check_utc"] is None and bl["last_successful_sync_utc"] is None
    assert bl["last_successful_import_utc"] == "2026-11-01T09:00:01Z" and bl["last_import_kind"] == "offline_snapshot_import" and bl["imported_records"] == 5
    assert bl["last_attempted_sync_utc"] is None                                     # nothing was attempted against a provider
    assert bl["state"] == "stale" and any("not an external check" in r for r in bl["state_reasons"])


def test_a_live_check_makes_an_approved_league_fresh_and_a_zero_request_run_does_not(store):
    run_row(store, requests=0)                                                       # a run that made no request is not a check
    assert bl_status(store)["BUNDESLIGA"]["state"] == "stale"
    run_row(store, requests=1, started_utc="2026-11-01T06:00:00Z", finished_utc="2026-11-01T06:00:03Z")
    bl = bl_status(store)["BUNDESLIGA"]
    assert bl["state"] == "fresh" and bl["last_successful_external_check_utc"] == "2026-11-01T06:00:03Z" and bl["last_external_check_new_records"] == 0
    assert bl["last_attempted_sync_utc"] == "2026-11-01T06:00:00Z" and bl["provider_readiness"] == "approved_live_disabled"


def test_a_check_that_finds_nothing_new_does_not_make_an_incomplete_history_complete(store):
    c = db.connect(store)
    add_team(c, "x", "X FC")
    add_team(c, "y", "Y FC")
    add_match(c, "bun:old", "BUNDESLIGA", "2026-27", 1, "2026-10-20", "x", "y")           # played date, no verified result
    c.commit()
    c.close()
    c = db.connect(store)
    c.execute("UPDATE matches SET status='awaiting_result' WHERE record_id='bun:old'")
    c.commit()
    c.close()
    run_row(store, requests=1, started_utc="2026-11-01T06:00:00Z", finished_utc="2026-11-01T06:00:03Z", updated=0)
    bl = bl_status(store)["BUNDESLIGA"]
    assert bl["last_successful_external_check_utc"] and bl["last_external_check_new_records"] == 0
    assert bl["state"] == "stale" and bl["awaiting_result"] == 1 and "does not make the history complete" in bl["history_note"]


def test_a_failed_latest_attempt_and_an_old_check_are_stale_with_the_reason(store):
    run_row(store, requests=1, started_utc="2026-11-01T06:00:00Z", finished_utc="2026-11-01T06:00:03Z")
    run_row(store, outcome="error", requests=1, started_utc="2026-11-01T10:00:00Z", finished_utc="2026-11-01T10:00:02Z")
    bl = bl_status(store)["BUNDESLIGA"]
    assert bl["state"] == "stale" and any("latest sync attempt: error" in r for r in bl["state_reasons"]) and bl["last_attempt_outcome"] == "error"
    old = bl_status(store, datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc))["BUNDESLIGA"]
    assert old["state"] == "stale"


def test_leagues_without_a_provider_say_so_and_count_imports_and_quarantine_separately(store):
    run_row(store, kind="offline_snapshot_import", competition_key="EPL", requests=0, updated=299, quarantined=33)
    st = bl_status(store)
    assert st["EPL"]["provider_readiness"] == "prepared_offline" and st["EPL"]["imported_records"] == 299 and st["EPL"]["quarantined_records"] == 33
    assert st["SERIEA"]["provider_readiness"] == "prepared_needs_token" and st["SERIEA"]["last_successful_import_utc"] is None
    assert all(x["state"] == "stale" for k, x in st.items() if k != "BUNDESLIGA")


def test_the_live_path_holds_date_disagreements_instead_of_overwriting_dates(store, monkeypatch, tmp_path):
    """Phase 4.8C: _sync_openligadb ingests with protect_dates=True, so a source date that differs from the stored one is quarantined (DATE_DIFFERENCE) and the stored date stays."""
    seen = {}

    class FakeAdapter:
        def __init__(self, *a, **k): ...
        def _snap(self, name, body, meta):
            return meta
        def fetch_season(self, league, season):
            return [], dict(snapshot_id="s1", sha256="x", bytes=1, saved_utc="2026-11-01T05:00:00Z", url="u")

    import types
    seen_kwargs = {}
    monkeypatch.setattr(sync, "ingest_records", lambda *a, **k: seen_kwargs.update(k) or dict(inserted=0, updated=0, unchanged=0, confirmed=0, quarantined=0))
    monkeypatch.setattr(sync, "_adapters", lambda: (types.SimpleNamespace(HttpClient=lambda *a, **k: types.SimpleNamespace(get=lambda *x, **y: None), SnapshotStore=None), None, types.SimpleNamespace(OpenLigaDBAdapter=FakeAdapter, LICENCE="l", ATTRIBUTION="a")))
    monkeypatch.setattr(sync, "_adapter_config", lambda: types.SimpleNamespace(live_enabled=False, snapshot_dir=None, ledger_path=None, redact=lambda s: s))

    class Rec:
        pass
    monkeypatch.setattr(FakeAdapter, "fetch_season", lambda self, league, season: ([Rec()], dict(snapshot_id="s1", sha256="x", bytes=1, saved_utc="2026-11-01T05:00:00Z", url="u")))
    mgr = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True))
    conn = db.connect(store)
    mgr._sync_openligadb(conn, "BUNDESLIGA")
    conn.close()
    assert seen_kwargs.get("protect_dates") is True


def test_a_lagging_results_feed_is_judged_by_the_newest_verified_match_date_not_by_the_last_check(store):
    c = db.connect(store)
    for slug, name in (("x", "X FC"), ("y", "Y FC"), ("z", "Z FC")):
        add_team(c, slug, name)
    add_match(c, "epl:done", "EPL", "2026-27", 1, "2026-10-12", "x", "y", status="completed", score=(1, 0))
    add_match(c, "epl:wait", "EPL", "2026-27", 2, "2026-10-17", "y", "z")
    c.commit()
    c.close()
    c = db.connect(store)
    c.execute("UPDATE matches SET status='awaiting_result' WHERE record_id='epl:wait'")
    c.commit()
    c.close()
    run_row(store, kind="sync", competition_key="EPL", requests=1, started_utc="2026-10-27T12:00:00Z", finished_utc="2026-10-27T12:00:03Z")        # a "fresh" check today does not hide the lag
    epl = bl_status(store, datetime(2026, 10, 27, 13, 0, tzinfo=timezone.utc))["EPL"]
    lag = epl["feed_lag"]
    assert lag["lagging"] and lag["latest_verified_result_date"] == "2026-10-12" and lag["days_since_latest_verified_result"] == 15 and lag["fixtures_past_date_without_result"] == 1
    assert "newest verified result 2026-10-12 (15 days ago)" in lag["message"]
    assert bl_status(store)["SERIEA"]["feed_lag"] is None                                                                                         # nothing stored, nothing claimed


def test_legacy_skipped_live_disabled_rows_are_not_attempts_and_do_not_delay_the_first_real_check(store, monkeypatch):
    """Found by the Phase 4.8D scheduler trial: production holds three such diary rows from before 4.8B; they used to count as failures and push the first check out by 24 hours."""
    for i, t in enumerate(("2026-10-25T08:22:01Z", "2026-10-25T08:51:17Z", "2026-10-27T10:37:37Z")):
        run_row(store, kind="startup_check", competition_key=None, source="all approved", outcome="skipped_live_disabled", requests=0, started_utc=t, finished_utc=t)
    clock = Clock(datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc))
    mgr, calls = live_manager(store, monkeypatch, clock, [OK_RESULT])
    assert mgr.next_due() == clock()                                   # due immediately: no real attempt has ever been made
    assert mgr.tick("startup_check")["outcome"] == "ok" and len(calls) == 1
    assert mgr.next_due() == clock() + timedelta(hours=6)


def test_max_retries_zero_means_exactly_one_request_per_call_and_a_failure_changes_no_data(store, monkeypatch, tmp_path):
    """Phase 4.8D Stage 2: supervised real-network trials set max_retries=0 so the request count is exact. The shipped default is 2 (Phase 4.8D final safeguards)."""
    assert sync.SyncConfig().max_retries == 2 and sync.SyncConfig.load().max_retries == 2                   # Phase 4.8D final safeguards: 2 retries, and a cycle is capped at 3 attempts anyway
    monkeypatch.setattr(sync, "SNAPSHOT_DIR", tmp_path / "snap")
    monkeypatch.setenv("FOOTIQ_CONTACT", "mailto:contact@footiq-test.local")
    seen = []
    mgr = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True, max_retries=0), opener=lambda u, h: seen.append(u) or (503, b"", {}), sleep=lambda s: None)
    before = BH_logical(store)
    res = mgr.check_once("manual_check")
    assert res["outcome"] == "error" and len(seen) == 1                      # one attempt, no retry
    assert BH_logical(store) == before                                       # a failed request leaves every data table untouched (only the two diaries may grow)
    seen.clear()
    mgr2 = sync.SyncManager(db_path=store, cfg=sync.SyncConfig(live_enabled=True, max_retries=2), opener=lambda u, h: seen.append(u) or (503, b"", {}), sleep=lambda s: None)
    mgr2.check_once("manual_check")
    assert len(seen) == 3                                                    # initial attempt + 2 retries: the knob works both ways


def BH_logical(path):
    """Hash of every table except the two diaries a failed check legitimately writes to (sync_runs rows, sync_errors)."""
    from store import baseline_hash
    t = baseline_hash.logical(path, 0)["tables"]
    return {k: v["sha256"] for k, v in t.items() if k not in ("sync_runs", "sync_errors")}
