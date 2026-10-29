"""Phase 4.9: La Liga joins Bundesliga in the ONE existing scheduler. Saved 2026-10-27 responses of both leagues, a private store copy, a mocked clock, no network."""
import copy
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from store import baseline, baseline_hash, db, sync  # noqa: E402

SNAP = ROOT / "data" / "snapshots" / "p48c" / "openligadb"
BL_FILE, LA_FILE = SNAP / "20261027T125704Z_p48c_bl1.json", SNAP / "20261027T130112Z_p48c_la1.json"
pytestmark = pytest.mark.skipif(not (baseline.V_PATH.exists() and BL_FILE.exists() and LA_FILE.exists()), reason="baseline inputs or the saved snapshots are not present")
BL_URL, LA_URL = "https://api.openligadb.de/getmatchdata/bl1/2026", "https://api.openligadb.de/getmatchdata/la1/2026"
FMT = "%Y-%m-%dT%H:%M:%SZ"
T0 = datetime(2026, 11, 1, 6, 0, 0, tzinfo=timezone.utc)
KEY = "LALIGA"


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


class Provider:
    """Stands in for api.openligadb.de: one payload per full-season URL, every other URL is refused. A league can be switched off on its own."""

    def __init__(self):
        self.payload = {BL_URL: json.loads(BL_FILE.read_bytes()), LA_URL: json.loads(LA_FILE.read_bytes())}
        self.mode = {BL_URL: "ok", LA_URL: "ok"}
        self.urls = []

    def __call__(self, url, headers):
        self.urls.append(url)
        assert url in self.payload, f"only the two full-season endpoints may be requested, got {url}"
        if self.mode[url] == "down":
            return 503, b"", {}
        if self.mode[url] == "garbage":
            return 200, b"<html>not json</html>", {}
        return 200, json.dumps(self.payload[url]).encode(), {}

    @property
    def la(self):
        return self.payload[LA_URL]


@pytest.fixture(scope="module")
def base_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("la") / "base.sqlite"
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
    clock = Clock()
    monkeypatch.setattr(sync, "now_utc", lambda: clock.t.strftime(FMT))
    provider = Provider()
    callbacks = []
    cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "LALIGA"]}})
    mgr = sync.SyncManager(db_path=p, cfg=cfg, opener=provider, on_change=lambda: callbacks.append(1), sleep=lambda s: None, clock=clock)
    return dict(path=p, clock=clock, provider=provider, mgr=mgr, cfg=cfg, callbacks=callbacks, tmp=tmp_path)


def q(path, sql, *a):
    c = db.connect(path, readonly=True)
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def la(path):
    return {r["record_id"]: r for r in q(path, "SELECT * FROM matches WHERE competition_key='LALIGA' AND season='2026-27'")}


def tables(path):
    t = baseline_hash.logical(path, 0)["tables"]
    return {k: v["sha256"] for k, v in t.items() if k not in ("sync_runs", "sync_errors", "source_snapshots", "source_state")}


def later(rig, hours=6, minutes=1):
    rig["clock"].t = rig["clock"].t + timedelta(hours=hours, minutes=minutes)


def test_one_scheduler_cycle_makes_one_request_per_league_and_imports_la_liga(rig):
    r = rig["mgr"].tick("startup_check")
    assert r["outcome"] == "ok" and sorted(rig["provider"].urls) == sorted([BL_URL, LA_URL])
    assert {d["competition"]: d["requests"] for d in r["details"]} == {"BUNDESLIGA": 1, "LALIGA": 1}
    done = q(rig["path"], "SELECT COUNT(*) n FROM matches WHERE competition_key='LALIGA' AND season='2026-27' AND status='completed'")[0]["n"]
    assert 60 <= done < 98                                                                                        # the snapshot holds 98 finished matches; held ones are not applied
    snaps = q(rig["path"], "SELECT url, sha256 FROM source_snapshots WHERE source='openligadb'")
    assert {s["url"] for s in snaps} == {BL_URL, LA_URL}
    assert q(rig["path"], "SELECT COUNT(*) - COUNT(DISTINCT record_id) n FROM matches")[0]["n"] == 0             # never a second row for the same match
    assert q(rig["path"], "PRAGMA integrity_check")[0]["integrity_check"] == "ok"


def test_identical_repeat_changes_nothing_and_reuses_the_snapshot(rig):
    rig["mgr"].tick("startup_check")
    before, n_snap = tables(rig["path"]), q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots")[0]["n"]
    later(rig)
    r = rig["mgr"].tick()
    assert r["outcome"] == "ok" and r["changed"] == 0
    assert tables(rig["path"]) == before
    assert q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots")[0]["n"] == n_snap                           # byte-identical response: no new snapshot row
    assert all(d["snapshot_reused"] for d in r["details"])


def test_a_new_result_and_a_late_result_of_an_older_matchday_are_ingested(rig):
    conn = db.connect(rig["path"], readonly=True)
    resolver = sync.build_resolver(conn)
    comp = sync.APPROVED[KEY]["competition_id"]
    stored = {(r["home_entity_id"], r["away_entity_id"]): dict(r) for r in conn.execute("SELECT record_id, home_entity_id, away_entity_id, match_date, status FROM matches WHERE competition_key='LALIGA' AND season='2026-27'")}
    conn.close()

    def row(m):
        return stored.get((resolver.resolve("openligadb", comp, m["team1"]["teamName"])[0], resolver.resolve("openligadb", comp, m["team2"]["teamName"])[0]))

    safe = [m for m in rig["provider"].la if m["matchIsFinished"] and row(m) and row(m)["status"] != "completed" and row(m)["match_date"] == m["matchDateTimeUTC"][:10]]
    old = next(m for m in safe if m["group"]["groupOrderID"] <= 8)                                                  # an older matchday whose result is not stored yet
    finished = copy.deepcopy(old)
    old["matchIsFinished"], old["matchResults"] = False, []                                                         # first the provider has no result for it
    rig["mgr"].tick("startup_check")
    rid = row(old)["record_id"]
    assert la(rig["path"])[rid]["status"] != "completed"
    rig["provider"].payload[LA_URL] = [finished if m["matchID"] == finished["matchID"] else m for m in rig["provider"].la]       # the late result arrives
    later(rig)
    r = rig["mgr"].tick()
    assert next(d for d in r["details"] if d["competition"] == KEY)["inserted"] + next(d for d in r["details"] if d["competition"] == KEY)["updated"] == 1
    assert la(rig["path"])[rid]["status"] == "completed"
    link = q(rig["path"], "SELECT role FROM match_sources WHERE source='openligadb' AND source_ref=?", str(finished["matchID"]))
    assert link and link[0]["role"] == "primary"


def test_a_conflicting_score_is_quarantined_and_never_overwrites(rig):
    rig["mgr"].tick("startup_check")
    stored = {k: (v["home_goals_final"], v["away_goals_final"]) for k, v in la(rig["path"]).items()}
    m = next(m for m in rig["provider"].la if m["matchIsFinished"] and m["group"]["groupOrderID"] == 1)
    for res in m["matchResults"]:
        res["pointsTeam1"] += 2
    later(rig)
    r = rig["mgr"].tick()
    assert r["outcome"] == "ok"
    assert {k: (v["home_goals_final"], v["away_goals_final"]) for k, v in la(rig["path"]).items()} == stored
    assert any(x["reason"].startswith("CONFLICT") for x in q(rig["path"], "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 5"))


def test_a_disputed_date_is_held_and_the_stored_date_stays(rig):
    rig["mgr"].tick("startup_check")
    dates = {k: v["match_date"] for k, v in la(rig["path"]).items()}
    m = next(m for m in rig["provider"].la if not m["matchIsFinished"] and m["group"]["groupOrderID"] == 20)
    moved = datetime.strptime(m["matchDateTimeUTC"], FMT) + timedelta(days=2)
    m["matchDateTimeUTC"], m["matchDateTime"] = moved.strftime(FMT), moved.strftime("%Y-%m-%dT%H:%M:%S")
    later(rig)
    assert rig["mgr"].tick()["outcome"] == "ok"
    assert {k: v["match_date"] for k, v in la(rig["path"]).items()} == dates
    assert any(x["reason"].startswith("DATE_DIFFERENCE") for x in q(rig["path"], "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 5"))


def test_the_existing_la_liga_date_disagreements_are_held_not_applied(rig):
    """The 24 disagreements known since Phase 4.8C come back from the saved response: all stay quarantined, none changes a stored date."""
    before = {k: v["match_date"] for k, v in la(rig["path"]).items()}
    rig["mgr"].tick("startup_check")
    held = [x for x in q(rig["path"], "SELECT reason FROM quarantine") if x["reason"].startswith("DATE_DIFFERENCE")]
    assert len(held) >= 20
    after = {k: v["match_date"] for k, v in la(rig["path"]).items()}
    assert all(after[k] == v for k, v in before.items())


def test_a_provider_failure_in_one_league_does_not_block_the_other(rig):
    rig["mgr"].tick("startup_check")
    rig["provider"].mode[LA_URL] = "down"
    rig["provider"].urls.clear()
    before = tables(rig["path"])
    later(rig)
    r = rig["mgr"].tick()
    assert r["outcome"] == "error"
    res = {d["competition"]: d for d in r["details"]}
    assert "error" in res[KEY] and "error" not in res["BUNDESLIGA"]                                                 # La Liga failed, Bundesliga completed its check in the same cycle
    assert sorted(rig["provider"].urls) == sorted([BL_URL, LA_URL])                                                  # one attempt each, no retry
    assert tables(rig["path"]) == before
    due = rig["mgr"].league_due()
    assert due["BUNDESLIGA"] == rig["clock"].t + timedelta(hours=6) and due[KEY] == rig["clock"].t + timedelta(hours=12)       # La Liga backs off alone
    st = sync.status(db.connect(rig["path"], readonly=True), rig["cfg"], rig["clock"].t)["scheduler"]["leagues"]
    assert st[KEY]["consecutive_failed_cycles"] == 1 and st["BUNDESLIGA"]["consecutive_failed_cycles"] == 0
    # the next cycle asks only the league that is due
    rig["provider"].urls.clear()
    rig["clock"].t = rig["clock"].t + timedelta(hours=6)
    r2 = rig["mgr"].tick()
    assert r2["outcome"] == "ok" and rig["provider"].urls == [BL_URL]
    rig["provider"].urls.clear()
    rig["provider"].mode[LA_URL] = "ok"
    rig["clock"].t = rig["clock"].t + timedelta(hours=6)
    r3 = rig["mgr"].tick()
    assert r3["outcome"] == "ok" and sorted(rig["provider"].urls) == sorted([BL_URL, LA_URL])                        # recovered: back to the six-hour rhythm
    assert rig["mgr"].league_due()[KEY] == rig["clock"].t + timedelta(hours=6)


def test_a_malformed_la_liga_response_touches_no_data(rig):
    rig["mgr"].tick("startup_check")
    before = tables(rig["path"])
    rig["provider"].mode[LA_URL] = "garbage"
    later(rig)
    r = rig["mgr"].tick()
    assert r["outcome"] == "error" and tables(rig["path"]) == before
    assert q(rig["path"], "PRAGMA integrity_check")[0]["integrity_check"] == "ok"


def test_restart_inside_the_interval_makes_no_request_and_a_new_league_is_due_alone(rig):
    rig["mgr"].tick("startup_check")
    n = len(rig["provider"].urls)
    restarted = sync.SyncManager(db_path=rig["path"], cfg=rig["cfg"], opener=rig["provider"], sleep=lambda s: None, clock=rig["clock"])
    rig["clock"].t = T0 + timedelta(hours=1)
    assert restarted.tick("startup_check")["outcome"] == "not_due" and len(rig["provider"].urls) == n
    # a league that has never been attempted is due by itself; the other one is not asked
    only_bl = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA"]}})
    solo = sync.SyncManager(db_path=rig["path"], cfg=only_bl, opener=rig["provider"], sleep=lambda s: None, clock=rig["clock"])
    assert solo.tick()["outcome"] == "not_due"
    both = sync.SyncManager(db_path=rig["path"], cfg=sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "LALIGA"]}}),
                            opener=rig["provider"], sleep=lambda s: None, clock=rig["clock"])
    assert both.tick()["outcome"] == "not_due"


def test_a_league_first_listed_later_is_checked_alone_at_its_own_time(base_db, tmp_path, monkeypatch):
    p = tmp_path / "s.sqlite"
    shutil.copy(base_db, p)
    monkeypatch.setattr(sync, "SNAPSHOT_DIR", tmp_path / "snap")
    monkeypatch.setenv("FOOTIQ_CONTACT", "mailto:contact@footiq-test.local")
    clock = Clock()
    monkeypatch.setattr(sync, "now_utc", lambda: clock.t.strftime(FMT))
    provider = Provider()
    bl_only = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA"]}})
    sync.SyncManager(db_path=p, cfg=bl_only, opener=provider, sleep=lambda s: None, clock=clock).tick("startup_check")
    assert provider.urls == [BL_URL]
    provider.urls.clear()
    clock.t = T0 + timedelta(hours=1)                                                                               # Bundesliga is not due, La Liga has never been attempted
    both = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "LALIGA"]}})
    r = sync.SyncManager(db_path=p, cfg=both, opener=provider, sleep=lambda s: None, clock=clock).tick("startup_check")
    assert r["outcome"] == "ok" and provider.urls == [LA_URL] and [d["competition"] for d in r["details"]] == [KEY]


def test_the_status_lists_both_leagues_with_independent_states(rig):
    rig["mgr"].tick("startup_check")
    conn = db.connect(rig["path"], readonly=True)
    st = sync.status(conn, rig["cfg"], rig["clock"].t)
    conn.close()
    comps = {c["competition_key"]: c for c in st["competitions"]}
    for k in ("BUNDESLIGA", "LALIGA"):
        assert comps[k]["provider_readiness"] == "approved_live_enabled" and comps[k]["last_successful_external_check_utc"]
    assert set(st["scheduler"]["leagues"]) == {"BUNDESLIGA", "LALIGA"}
    assert st["quarantine"]["needs_operator_review"] > 0 and "date disagreement" in st["quarantine"]["warning"]
    assert comps["EPL"]["provider_readiness"] == "prepared_offline"


def test_the_scheduler_thread_is_one_for_both_leagues(base_db, tmp_path, monkeypatch):
    import time
    p = tmp_path / "s.sqlite"
    shutil.copy(base_db, p)
    monkeypatch.delenv("FOOTIQ_DISABLE_SYNC", raising=False)
    monkeypatch.setenv("FOOTIQ_SCHEDULER_LOCK", str(tmp_path / "private.lock"))
    cfg = sync.SyncConfig(live_enabled=True, startup_delay_seconds=30, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "LALIGA"]}})
    mgr = sync.SyncManager(db_path=p, cfg=cfg, opener=lambda u, h: pytest.fail("no request in this test"))
    mgr.start()
    mgr.start()
    time.sleep(0.2)
    assert sync.active_scheduler_threads() == 1
    mgr.stop()
    mgr._thread.join(5)
    assert sync.active_scheduler_threads() == 0
