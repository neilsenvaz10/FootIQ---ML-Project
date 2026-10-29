"""Phase 4.10: Premier League through the same scheduler, from the saved OpenLigaDB responses only (no network). EPL is not in sync.APPROVED unless a source passes the freshness gate,
so these tests approve it inside the test process only."""
import copy
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from store import baseline, db, sync  # noqa: E402

PL_FILE = ROOT / "data" / "snapshots" / "p48c" / "openligadb" / "20261027T130107Z_p48c_pl.json"
BL_FILE = ROOT / "data" / "snapshots" / "p48c" / "openligadb" / "20261027T125704Z_p48c_bl1.json"
pytestmark = pytest.mark.skipif(not (baseline.V_PATH.exists() and PL_FILE.exists() and BL_FILE.exists()), reason="baseline inputs or the saved snapshots are not present")
PL_URL, BL_URL = "https://api.openligadb.de/getmatchdata/pl/2026", "https://api.openligadb.de/getmatchdata/bl1/2026"
FMT = "%Y-%m-%dT%H:%M:%SZ"
T0 = datetime(2026, 11, 1, 6, 0, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


class Provider:
    def __init__(self):
        self.payload = {PL_URL: json.loads(PL_FILE.read_bytes()), BL_URL: json.loads(BL_FILE.read_bytes())}
        self.mode = {PL_URL: "ok", BL_URL: "ok"}
        self.urls = []

    def __call__(self, url, headers):
        self.urls.append(url)
        assert url in self.payload, url
        if self.mode[url] == "down":
            return 503, b"", {}
        return 200, json.dumps(self.payload[url]).encode(), {}


@pytest.fixture(scope="module")
def base_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("epl") / "base.sqlite"
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
    monkeypatch.setitem(sync.APPROVED, "EPL", sync.OFFLINE_PREPARED["EPL"])
    monkeypatch.setattr(sync, "SNAPSHOT_DIR", tmp_path / "snap")
    monkeypatch.setenv("FOOTIQ_CONTACT", "mailto:contact@footiq-test.local")
    clock = Clock()
    monkeypatch.setattr(sync, "now_utc", lambda: clock.t.strftime(FMT))
    provider = Provider()
    cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "EPL"]}})
    mgr = sync.SyncManager(db_path=p, cfg=cfg, opener=provider, sleep=lambda s: None, clock=clock)
    return dict(path=p, clock=clock, provider=provider, mgr=mgr, cfg=cfg)


def q(path, sql, *a):
    c = db.connect(path, readonly=True)
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def epl(path):
    return {r["record_id"]: r for r in q(path, "SELECT * FROM matches WHERE competition_key='EPL' AND season='2026-27'")}


def test_the_stale_saved_response_adds_no_result_and_the_status_says_the_feed_is_lagging(rig):
    r = rig["mgr"].tick("startup_check")                                                                          # first cycle brings the private copy to the state of the 2026-10-25 import
    assert r["outcome"] == "ok" and sorted(rig["provider"].urls) == sorted([BL_URL, PL_URL])
    before = {k: v["status"] for k, v in epl(rig["path"]).items()}
    rig["clock"].t += timedelta(hours=6, minutes=1)
    r = rig["mgr"].tick()                                                                                         # the provider answers again with the very same bytes
    d = next(x for x in r["details"] if x["competition"] == "EPL")
    assert d["inserted"] == 0 and d["updated"] == 0 and d["requests"] == 1
    assert {k: v["status"] for k, v in epl(rig["path"]).items()} == before
    conn = db.connect(rig["path"], readonly=True)
    st = sync.status(conn, rig["cfg"], rig["clock"].t)
    conn.close()
    comp = next(c for c in st["competitions"] if c["competition_key"] == "EPL")
    assert comp["state"] == "stale" and comp["feed_lag"] and comp["feed_lag"]["lagging"]                       # a reachable endpoint is not a fresh one
    assert comp["latest_verified_result_date"] == "2026-10-12"


def test_fresh_results_for_the_waiting_fixtures_are_ingested_through_the_same_path(rig):
    rig["mgr"].tick("startup_check")
    pl = rig["provider"].payload[PL_URL]
    held = {x["source_ref"] for x in q(rig["path"], "SELECT source_ref FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%'")}
    waiting = [m for m in pl if not m["matchIsFinished"] and m["matchDateTimeUTC"] < "2026-10-25" and str(m["matchID"]) not in held][:3]
    assert len(waiting) == 3
    done_before = sum(1 for v in epl(rig["path"]).values() if v["status"] == "completed")
    for i, m in enumerate(waiting):
        m["matchIsFinished"] = True
        m["matchResults"] = [dict(resultID=900000 + i, resultName="Endergebnis", resultTypeID=2, resultOrderID=1, pointsTeam1=2, pointsTeam2=i, resultTypeKind="After90Minutes", resultDescription="")]
    rig["clock"].t += timedelta(hours=6, minutes=1)
    r = rig["mgr"].tick()
    d = next(x for x in r["details"] if x["competition"] == "EPL")
    gained = d["inserted"] + d["updated"]
    assert 1 <= gained <= 3                                                                                       # a fixture whose date the provider also disputes is held, not imported
    assert sum(1 for v in epl(rig["path"]).values() if v["status"] == "completed") == done_before + gained


def test_a_conflicting_score_and_a_moved_date_are_quarantined_not_applied(rig):
    rig["mgr"].tick("startup_check")
    stored = {k: (v["home_goals_final"], v["away_goals_final"], v["match_date"]) for k, v in epl(rig["path"]).items()}
    pl = rig["provider"].payload[PL_URL]
    done = next(m for m in pl if m["matchIsFinished"])
    for res in done["matchResults"]:
        res["pointsTeam1"] += 3
    nxt = next(m for m in pl if not m["matchIsFinished"] and m["matchDateTimeUTC"] > "2026-12")
    moved = datetime.strptime(nxt["matchDateTimeUTC"], FMT) + timedelta(days=2)
    nxt["matchDateTimeUTC"], nxt["matchDateTime"] = moved.strftime(FMT), moved.strftime("%Y-%m-%dT%H:%M:%S")
    rig["clock"].t += timedelta(hours=6, minutes=1)
    assert rig["mgr"].tick()["outcome"] == "ok"
    assert {k: (v["home_goals_final"], v["away_goals_final"], v["match_date"]) for k, v in epl(rig["path"]).items()} == stored
    reasons = [x["reason"] for x in q(rig["path"], "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 6")]
    assert any(x.startswith("CONFLICT") for x in reasons) and any(x.startswith("DATE_DIFFERENCE") for x in reasons)


def test_an_epl_failure_backs_off_alone_and_bundesliga_keeps_its_rhythm(rig):
    rig["mgr"].tick("startup_check")
    rig["provider"].mode[PL_URL] = "down"
    rig["clock"].t += timedelta(hours=6, minutes=1)
    r = rig["mgr"].tick()
    res = {d["competition"]: d for d in r["details"]}
    assert "error" in res["EPL"] and "error" not in res["BUNDESLIGA"]
    due = rig["mgr"].league_due()
    assert due["BUNDESLIGA"] == rig["clock"].t + timedelta(hours=6) and due["EPL"] == rig["clock"].t + timedelta(hours=12)
