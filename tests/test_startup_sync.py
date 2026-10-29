"""Simplified synchronisation: sync_mode="startup" = ONE refresh attempt per backend launch, no recurring scheduler. Saved 2026-10-27 responses (Bundesliga, La Liga), a private store copy,
a mocked clock, no network. The shipped configuration still says "periodic": nothing here changes the running production backend."""
import copy
import json
import re
import shutil
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from store import baseline, baseline_monitor as BM, daily_audit as DA, db, sync  # noqa: E402

SNAP = ROOT / "data" / "snapshots" / "p48c" / "openligadb"
BL_FILE, LA_FILE = SNAP / "20261027T125704Z_p48c_bl1.json", SNAP / "20261027T130112Z_p48c_la1.json"
pytestmark = pytest.mark.skipif(not (baseline.V_PATH.exists() and BL_FILE.exists() and LA_FILE.exists()), reason="baseline inputs or the saved snapshots are not present")
BL_URL, LA_URL = "https://api.openligadb.de/getmatchdata/bl1/2026", "https://api.openligadb.de/getmatchdata/la1/2026"
FMT = "%Y-%m-%dT%H:%M:%SZ"
T0 = datetime(2026, 11, 1, 6, 0, 0, tzinfo=timezone.utc)
BOTH = {"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "LALIGA"]}}


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


class Provider:
    def __init__(self):
        self.payload = {BL_URL: json.loads(BL_FILE.read_bytes()), LA_URL: json.loads(LA_FILE.read_bytes())}
        self.mode = {BL_URL: "ok", LA_URL: "ok"}
        self.urls = []
        self.gate = None                                   # a threading.Event: when set, every request waits for it (proves the application does not wait for the refresh)

    def __call__(self, url, headers):
        self.urls.append(url)
        assert url in self.payload, f"unexpected URL {url}"
        if self.gate is not None:
            assert self.gate.wait(30)
        if self.mode[url] == "down":
            return 503, b"", {}
        return 200, json.dumps(self.payload[url]).encode(), {}


@pytest.fixture(scope="module")
def base_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("st") / "base.sqlite"
    c = db.connect(path)
    db.init(c)
    baseline.import_baseline(c)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()
    return path


@pytest.fixture
def rig(base_db, tmp_path, monkeypatch):
    p = tmp_path / "s.sqlite"
    shutil.copy(base_db, p)
    monkeypatch.setattr(sync, "SNAPSHOT_DIR", tmp_path / "snap")
    monkeypatch.setenv("FOOTIQ_CONTACT", "mailto:contact@footiq-test.local")
    monkeypatch.delenv("FOOTIQ_DISABLE_SYNC", raising=False)
    monkeypatch.setenv("FOOTIQ_SCHEDULER_LOCK", str(tmp_path / "private.lock"))
    clock = Clock()
    monkeypatch.setattr(sync, "now_utc", lambda: clock.t.strftime(FMT))
    provider = Provider()
    cfg = sync.SyncConfig(live_enabled=True, sync_mode="startup", startup_delay_seconds=0, max_retries=0, sources=copy.deepcopy(BOTH))

    def launch(c=None, **kw):
        m = sync.SyncManager(db_path=p, cfg=c or cfg, opener=provider, sleep=lambda s: None, clock=clock, **kw)
        m.start()
        return m

    def finish(m):
        if m._thread is not None:
            m._thread.join(60)
        return m
    return dict(path=p, clock=clock, provider=provider, cfg=cfg, launch=launch, finish=finish, tmp=tmp_path)


def q(path, sql, *a):
    c = db.connect(path, readonly=True)
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def tables(path):
    from store import baseline_hash
    t = baseline_hash.logical(path, 0)["tables"]
    return {k: v["sha256"] for k, v in t.items() if k not in ("sync_runs", "sync_errors", "source_snapshots", "source_state")}


def status(rig, now=None):
    c = db.connect(rig["path"], readonly=True)
    try:
        return sync.status(c, rig["cfg"], now or rig["clock"].t)
    finally:
        c.close()


# ------------------------------------------------------------------------------------------------ one refresh per launch
def test_a_launch_makes_one_request_per_league_and_nothing_keeps_running(rig):
    m = rig["finish"](rig["launch"]())
    assert sorted(rig["provider"].urls) == sorted([BL_URL, LA_URL]) and m.startup_state["state"] == "done" and m.startup_state["failed_leagues"] == []
    assert not m._thread.is_alive() and sync.active_scheduler_threads() == 0                                      # the refresh is over: no scheduler thread
    lock = sync.SchedulerLock(rig["tmp"] / "private.lock")
    assert lock.acquire()                                                                                         # and the lock is free again
    lock.release()
    n = len(rig["provider"].urls)
    rig["clock"].t += timedelta(hours=30)                                                                         # a day later, still running: nothing happens in the background
    time.sleep(0.4)
    assert len(rig["provider"].urls) == n and m.next_due() is None and m.tick()["outcome"] == "not_scheduled_startup_mode"
    assert q(rig["path"], "SELECT COUNT(*) n FROM sync_runs WHERE kind='startup_check'")[0]["n"] == 1
    assert q(rig["path"], "PRAGMA integrity_check")[0]["integrity_check"] == "ok"


def test_the_application_does_not_wait_for_the_refresh(rig):
    rig["provider"].gate = threading.Event()
    t0 = time.time()
    m = rig["launch"]()
    assert time.time() - t0 < 2 and m.startup_state["state"] in ("pending", "running")                           # start() returned while the provider has not even answered
    time.sleep(0.3)
    assert rig["provider"].gate is not None and m._thread.is_alive()
    rig["provider"].gate.set()
    rig["finish"](m)
    assert m.startup_state["state"] == "done"


def test_opening_or_reloading_the_frontend_can_never_trigger_a_refresh(rig):
    m = rig["finish"](rig["launch"]())
    n = len(rig["provider"].urls)
    for _ in range(5):                                                                                            # what every page load calls
        status(rig)
    assert len(rig["provider"].urls) == n
    src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    used = set(re.findall(r"sync_manager\.(\w+)", src))
    assert used <= {"start", "stop", "cfg", "lock_state", "lock_path", "startup_state"}, used                   # no route calls check_once / tick: only the lifespan starts the one refresh
    assert "check_once" not in src and ".tick(" not in src


def test_a_quick_restart_does_not_ask_again_and_a_later_launch_does(rig):
    rig["finish"](rig["launch"]())
    rig["provider"].urls.clear()
    rig["clock"].t += timedelta(minutes=5)
    m2 = rig["finish"](rig["launch"]())                                                                           # relaunched 5 minutes later: inside the 15-minute gap
    assert rig["provider"].urls == [] and m2.startup_state["state"] == "skipped_recent"
    rig["clock"].t += timedelta(minutes=20)
    m3 = rig["finish"](rig["launch"]())
    assert sorted(rig["provider"].urls) == sorted([BL_URL, LA_URL]) and m3.startup_state["state"] == "done"
    assert sorted(m3.startup_state["leagues"]) == ["BUNDESLIGA", "LALIGA"] and m3.startup_state["skipped"] == {}


def test_only_a_league_that_failed_or_is_stale_is_asked_again(rig):
    rig["provider"].mode[LA_URL] = "down"
    m1 = rig["finish"](rig["launch"]())
    assert m1.startup_state["failed_leagues"] == ["LALIGA"]
    rig["provider"].urls.clear()
    rig["provider"].mode[LA_URL] = "ok"
    rig["clock"].t += timedelta(minutes=3)                                                                        # Bundesliga succeeded 3 minutes ago, La Liga failed
    m2 = rig["finish"](rig["launch"]())
    assert rig["provider"].urls == [LA_URL] and list(m2.startup_state["skipped"]) == ["BUNDESLIGA"] and m2.startup_state["failed_leagues"] == []


# ------------------------------------------------------------------------------------------------ failures keep the app usable
def test_an_unavailable_api_leaves_local_data_untouched_and_the_error_is_visible(rig):
    before = tables(rig["path"])
    rig["provider"].mode.update({BL_URL: "down", LA_URL: "down"})
    m = rig["finish"](rig["launch"]())
    assert m.startup_state["state"] == "done" and sorted(m.startup_state["failed_leagues"]) == ["BUNDESLIGA", "LALIGA"] and "retries exhausted" in m.startup_state["errors"]["LALIGA"]
    assert tables(rig["path"]) == before and q(rig["path"], "PRAGMA integrity_check")[0]["integrity_check"] == "ok"
    assert len(rig["provider"].urls) == 2                                                                         # one attempt per league, no retry storm
    st = status(rig)
    assert st["sync_mode"] == "startup" and st["scheduler"]["mode"] == "startup" and st["scheduler"]["next_scheduled_check_utc"] is None
    assert "startup refresh only" in st["scheduler"]["status"] and st["scheduler"]["consecutive_failed_cycles"] == 1
    assert "retries exhausted" in st["scheduler"]["leagues"]["LALIGA"]["last_error"]["error"] and st["scheduler"]["leagues"]["LALIGA"]["next_check_utc"] is None
    assert "errors in" in sync.describe_startup(m.startup_state)


def test_a_failure_in_one_league_does_not_stop_the_other_and_the_next_success_clears_the_error(rig):
    rig["provider"].mode[BL_URL] = "down"
    m = rig["finish"](rig["launch"]())
    res = m.startup_state
    assert res["failed_leagues"] == ["BUNDESLIGA"]
    assert q(rig["path"], "SELECT COUNT(*) n FROM sync_runs WHERE kind='sync' AND competition_key='LALIGA' AND outcome='ok'")[0]["n"] == 1
    rig["provider"].mode[BL_URL] = "ok"
    rig["clock"].t += timedelta(minutes=2)
    rig["finish"](rig["launch"]())
    assert status(rig)["scheduler"]["leagues"]["BUNDESLIGA"]["last_error"] is None


def test_a_crash_inside_the_refresh_is_contained_and_releases_the_lock(rig, monkeypatch):
    m = sync.SyncManager(db_path=rig["path"], cfg=rig["cfg"], opener=rig["provider"], sleep=lambda s: None, clock=rig["clock"])
    monkeypatch.setattr(m, "check_once", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    m.start()
    m._thread.join(30)
    assert m.startup_state["state"] == "failed" and "boom" in m.startup_state["error"]
    lock = sync.SchedulerLock(rig["tmp"] / "private.lock")
    assert lock.acquire()
    lock.release()


# ------------------------------------------------------------------------------------------------ safeguards are the same ones
def test_conflicts_date_disputes_and_provenance_still_apply(rig):
    rig["finish"](rig["launch"]())
    la = rig["provider"].payload[LA_URL]
    stored = {r["record_id"]: (r["home_goals_90"], r["away_goals_90"], r["match_date"]) for r in q(rig["path"], "SELECT * FROM matches WHERE competition_key='LALIGA' AND season='2026-27'")}
    done = next(x for x in la if x["matchIsFinished"] and x["group"]["groupOrderID"] == 1)
    for res in done["matchResults"]:
        res["pointsTeam1"] += 2
    nxt = next(x for x in la if not x["matchIsFinished"] and x["group"]["groupOrderID"] == 25)
    moved = datetime.strptime(nxt["matchDateTimeUTC"], FMT) + timedelta(days=2)
    nxt["matchDateTimeUTC"], nxt["matchDateTime"] = moved.strftime(FMT), moved.strftime("%Y-%m-%dT%H:%M:%S")
    rig["clock"].t += timedelta(hours=1)
    m = rig["finish"](rig["launch"]())
    assert m.startup_state["state"] == "done"
    assert {r["record_id"]: (r["home_goals_90"], r["away_goals_90"], r["match_date"]) for r in q(rig["path"], "SELECT * FROM matches WHERE competition_key='LALIGA' AND season='2026-27'")} == stored
    reasons = [x["reason"] for x in q(rig["path"], "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 6")]
    assert any(x.startswith("CONFLICT") for x in reasons) and any(x.startswith("DATE_DIFFERENCE") for x in reasons)
    assert q(rig["path"], "SELECT COUNT(*) n FROM match_sources WHERE source='openligadb'")[0]["n"] > 0
    assert q(rig["path"], "SELECT COUNT(*) - COUNT(DISTINCT record_id) n FROM matches")[0]["n"] == 0


def test_an_identical_launch_stores_no_new_snapshot(rig):
    rig["finish"](rig["launch"]())
    n = q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots")[0]["n"]
    files = sorted((rig["tmp"] / "snap" / "openligadb").glob("*.json"))
    rig["clock"].t += timedelta(hours=2)
    rig["finish"](rig["launch"]())
    assert q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots")[0]["n"] == n and sorted((rig["tmp"] / "snap" / "openligadb").glob("*.json")) == files


def test_only_bundesliga_and_la_liga_can_ever_be_requested(rig):
    cfg = sync.SyncConfig(live_enabled=True, sync_mode="startup", startup_delay_seconds=0, max_retries=0,
                          sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "LALIGA", "EPL", "SERIEA", "LIGUE1"]}, "footballdata": {"enabled": True, "competitions": ["EPL", "SERIEA", "LIGUE1"]}})
    assert cfg.approved_competitions() == ["BUNDESLIGA", "LALIGA"]
    rig["finish"](rig["launch"](cfg))
    assert sorted(rig["provider"].urls) == sorted([BL_URL, LA_URL])


# ------------------------------------------------------------------------------------------------ switches, locks, defaults
def test_nothing_starts_when_sync_is_off_or_disabled_by_the_environment(rig, monkeypatch):
    off = sync.SyncManager(db_path=rig["path"], cfg=sync.SyncConfig(live_enabled=False, sync_mode="startup", sources=copy.deepcopy(BOTH)), opener=rig["provider"])
    off.start()
    assert off._thread is None and off.startup_state["state"] == "disabled" and "off" in sync.describe_startup(off.startup_state)
    monkeypatch.setenv("FOOTIQ_DISABLE_SYNC", "1")
    dis = sync.SyncManager(db_path=rig["path"], cfg=rig["cfg"], opener=rig["provider"])
    dis.start()
    assert dis._thread is None and dis.startup_state["reason"] == "FOOTIQ_DISABLE_SYNC=1" and rig["provider"].urls == []


def test_a_second_backend_launched_at_the_same_time_does_not_refresh(rig):
    rig["provider"].gate = threading.Event()
    first = rig["launch"]()
    time.sleep(0.3)
    second = sync.SyncManager(db_path=rig["path"], cfg=rig["cfg"], opener=rig["provider"], sleep=lambda s: None, clock=rig["clock"])
    second.start()
    assert second._thread is None and second.lock_state == "held_by_another_process" and second.startup_state["state"] == "skipped_other_process"
    rig["provider"].gate.set()
    rig["finish"](first)
    assert len(rig["provider"].urls) == 2                                                                         # still exactly one request per league


def test_the_shipped_configuration_is_startup_mode_and_the_periodic_mode_still_works(rig):
    assert sync.SyncConfig.load().sync_mode == "startup" and sync.SyncConfig().sync_mode == "periodic" and sync.SyncConfig().startup_min_gap_minutes == 15.0       # shipped: startup (4.15B); class default stays periodic
    with pytest.raises(ValueError):
        sync.SyncConfig(sync_mode="hourly")
    cfg = sync.SyncConfig(live_enabled=True, startup_delay_seconds=30, sources=copy.deepcopy(BOTH))                  # default periodic mode: the scheduler loop still starts
    m = sync.SyncManager(db_path=rig["path"], cfg=cfg, opener=lambda u, h: pytest.fail("no request in this test"))
    m.start()
    time.sleep(0.2)
    assert m._thread is not None and m._thread.is_alive() and sync.active_scheduler_threads() == 1 and m.next_due() is not None
    m.stop()
    m._thread.join(5)
    assert sync.active_scheduler_threads() == 0
    st = status(rig)
    assert st["sync_mode"] == "startup"                                                                           # (the rig's config)
    st2 = sync.status(db.connect(rig["path"], readonly=True), cfg, rig["clock"].t)
    assert st2["sync_mode"] == "periodic" and st2["scheduler"]["next_scheduled_check_utc"] is not None


# ------------------------------------------------------------------------------------------------ the daily audit understands the mode
def test_the_audit_does_not_expect_a_scheduler_or_a_six_hour_rhythm_in_startup_mode(rig, tmp_path):
    rig["finish"](rig["launch"]())
    cps = tmp_path / "cps.jsonl"
    BM.init(rig["path"], "v3", "tester", cps)
    now = T0 + timedelta(hours=20)                                                                                # 20 h after the last refresh: stale for a six-hour schedule, normal for startup mode
    common = dict(checkpoints_file=cps, out_dir=tmp_path / "audit", now=now, http=False, ledger=tmp_path / "none.jsonl", operations=tmp_path / "none.json", backups=tmp_path / "b")
    rep = DA.run_audit(rig["path"], cfg=rig["cfg"], **common)
    texts = " | ".join(i["text"] for i in rep["items"])
    assert rep["verdict"] == "PASS" and "BUNDESLIGA: last successful source check" in texts and "attention" not in texts.lower()
    periodic = sync.SyncConfig(live_enabled=True, periodic_minutes=360, sources=copy.deepcopy(BOTH))
    rep2 = DA.run_audit(rig["path"], cfg=periodic, **dict(common, out_dir=tmp_path / "audit2"))
    assert rep2["verdict"] == "ATTENTION"                                                                         # the same data is late for the six-hour rhythm
