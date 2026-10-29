"""Phase 4.8D: the routine Bundesliga refresh is ONE full-season request per cycle. Saved snapshot (the approved 2026-10-27 response), a private store copy, a mocked clock, no network."""
import copy
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from store import baseline, baseline_hash, db, sync  # noqa: E402

A1 = ROOT / "data" / "snapshots" / "p48c" / "openligadb" / "20261027T125704Z_p48c_bl1.json"
pytestmark = pytest.mark.skipif(not (baseline.V_PATH.exists() and A1.exists()), reason="baseline inputs or the saved snapshot are not present")
URL = "https://api.openligadb.de/getmatchdata/bl1/2026"
FMT = "%Y-%m-%dT%H:%M:%SZ"
T0 = datetime(2026, 11, 1, 6, 0, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


class Provider:
    """Stands in for api.openligadb.de: serves one payload for the full-season URL and refuses every other URL."""

    def __init__(self, payload):
        self.matches = copy.deepcopy(payload)
        self.mode = "ok"
        self.urls = []

    def __call__(self, url, headers):
        self.urls.append(url)
        assert url == URL, f"only the full-season endpoint may be requested, got {url}"
        if self.mode == "down":
            return 503, b"", {}
        if self.mode == "garbage":
            return 200, b"<html>not json</html>", {}
        return 200, json.dumps(self.matches).encode(), {}

    def match(self, group, home_contains):
        return next(m for m in self.matches if m["group"]["groupOrderID"] == group and home_contains in m["team1"]["teamName"])


@pytest.fixture(scope="module")
def base_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("fs") / "base.sqlite"
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
    provider = Provider(json.loads(A1.read_bytes()))
    callbacks = []
    cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0)
    mgr = sync.SyncManager(db_path=p, cfg=cfg, opener=provider, on_change=lambda: callbacks.append(1), sleep=lambda s: None, clock=clock)
    return dict(path=p, clock=clock, provider=provider, mgr=mgr, cfg=cfg, callbacks=callbacks, tmp=tmp_path)


def q(path, sql, *a):
    c = db.connect(path, readonly=True)
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def data_tables(path):
    t = baseline_hash.logical(path, 0)["tables"]
    return {k: v["sha256"] for k, v in t.items() if k not in ("sync_runs", "sync_errors")}


def bl(path):
    return {r["record_id"]: r for r in q(path, "SELECT * FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27'")}


def test_the_initial_cycle_makes_exactly_one_full_season_request_and_imports_the_results(rig):
    already = q(rig["path"], "SELECT COUNT(*) n FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='completed'")[0]["n"]
    r = rig["mgr"].tick("startup_check")
    assert r["outcome"] == "ok" and rig["provider"].urls == [URL] and r["details"][0]["requests"] == 1
    done = q(rig["path"], "SELECT COUNT(*) n FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND status='completed'")[0]["n"]
    assert done == 63 and r["changed"] >= 1 and rig["callbacks"] == [1]
    snap = q(rig["path"], "SELECT url, sha256, bytes FROM source_snapshots WHERE source='openligadb'")
    assert snap and snap[-1]["url"] == URL and snap[-1]["bytes"] == len(json.dumps(rig["provider"].matches).encode())          # the snapshot is registered with its URL and hash
    links = q(rig["path"], "SELECT COUNT(*) n FROM match_sources WHERE source='openligadb' AND role='primary'")[0]["n"]
    assert links == 63 - already > 0                                                                                             # every result this snapshot supplied names it (the rest were already stored and are confirmations)


def test_full_season_stays_the_routine_even_when_a_source_state_record_exists_and_polling_is_opt_in(rig):
    rig["mgr"].tick("startup_check")
    assert q(rig["path"], "SELECT COUNT(*) n FROM source_state WHERE source='openligadb'")[0]["n"] == 1          # the state that used to switch the scheduler to polling for ever
    rig["provider"].urls.clear()
    rig["clock"].t = T0 + timedelta(hours=6, minutes=1)
    rig["mgr"].tick()
    assert rig["provider"].urls == [URL]                                                                           # still the one full-season GET
    assert sync.SyncConfig().refresh_mode == "full_season" and sync.SyncConfig.load().refresh_mode == "full_season"
    with pytest.raises(ValueError):
        sync.SyncConfig(refresh_mode="everything")


def test_a_repeated_identical_response_changes_nothing(rig):
    rig["mgr"].tick("startup_check")
    before = data_tables(rig["path"])
    rig["clock"].t = T0 + timedelta(hours=6, minutes=1)
    r = rig["mgr"].tick()
    assert r["outcome"] == "ok" and r["changed"] == 0 and r["details"][0]["unchanged"] > 0 and rig["callbacks"] == [1]
    changed = sorted(k for k, v in data_tables(rig["path"]).items() if v != before[k])
    assert set(changed) <= {"source_snapshots", "source_state"}                                                     # no match, link, alias or quarantine row moved
    assert q(rig["path"], "SELECT COUNT(*) - COUNT(DISTINCT record_id) n FROM matches")[0]["n"] == 0


def test_a_delayed_result_from_an_older_matchday_is_picked_up(rig):
    conn = db.connect(rig["path"], readonly=True)
    resolver = sync.build_resolver(conn)
    open_older = {(r["home_entity_id"], r["away_entity_id"]): r["record_id"] for r in conn.execute("SELECT record_id, home_entity_id, away_entity_id FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27' AND matchday_no<=5 AND status<>'completed'")}
    comp = sync.APPROVED["BUNDESLIGA"]["competition_id"]
    old = next(m for m in rig["provider"].matches if m["matchIsFinished"] and m["group"]["groupOrderID"] <= 5
               and (resolver.resolve("openligadb", comp, m["team1"]["teamName"])[0], resolver.resolve("openligadb", comp, m["team2"]["teamName"])[0]) in open_older)
    conn.close()
    finished = copy.deepcopy(old)                                                                                   # a match of an older matchday that is not yet a stored result: its result arrives late
    old["matchIsFinished"], old["matchResults"] = False, []
    rig["mgr"].tick("startup_check")
    rid = [dict(record_id=open_older[(resolver.resolve("openligadb", comp, old["team1"]["teamName"])[0], resolver.resolve("openligadb", comp, old["team2"]["teamName"])[0])])]
    assert bl(rig["path"])[rid[0]["record_id"]]["status"] != "completed"
    rig["provider"].matches = [finished if m["matchID"] == finished["matchID"] else m for m in rig["provider"].matches]
    rig["clock"].t = T0 + timedelta(hours=6, minutes=1)
    r = rig["mgr"].tick()
    assert r["changed"] == 1 and rig["provider"].urls == [URL, URL]                                                  # found by the same single request, three matchdays back
    assert bl(rig["path"])[rid[0]["record_id"]]["status"] == "completed"
    assert q(rig["path"], "SELECT role, snapshot_id FROM match_sources WHERE source='openligadb' AND source_ref=?", str(finished["matchID"]))[0]["role"] == "primary"


def test_a_corrected_historical_score_is_quarantined_and_never_overwrites(rig):
    rig["mgr"].tick("startup_check")
    stored = {k: (v["home_goals_final"], v["away_goals_final"]) for k, v in bl(rig["path"]).items()}
    m = rig["provider"].match(2, "")
    for res in m["matchResults"]:
        if res["resultTypeID"] in (1, 2):
            res["pointsTeam1"] += 2
    rig["clock"].t = T0 + timedelta(hours=6, minutes=1)
    r = rig["mgr"].tick()
    assert r["outcome"] == "ok" and r["details"][0]["quarantined"] >= 1
    assert {k: (v["home_goals_final"], v["away_goals_final"]) for k, v in bl(rig["path"]).items()} == stored
    assert any(x["reason"].startswith("CONFLICT") for x in q(rig["path"], "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 3"))


def test_a_changed_fixture_date_is_held_for_a_human(rig):
    rig["mgr"].tick("startup_check")
    dates = {k: v["match_date"] for k, v in bl(rig["path"]).items()}
    m = rig["provider"].match(4, "")
    moved = datetime.strptime(m["matchDateTimeUTC"], FMT) + timedelta(days=1)
    m["matchDateTimeUTC"], m["matchDateTime"] = moved.strftime(FMT), moved.strftime("%Y-%m-%dT%H:%M:%S")
    rig["clock"].t = T0 + timedelta(hours=6, minutes=1)
    r = rig["mgr"].tick()
    assert r["outcome"] == "ok"
    assert {k: v["match_date"] for k, v in bl(rig["path"]).items()} == dates
    assert any(x["reason"].startswith("DATE_DIFFERENCE") for x in q(rig["path"], "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 3"))


def test_a_malformed_response_fails_the_run_and_touches_no_data(rig):
    rig["mgr"].tick("startup_check")
    before = data_tables(rig["path"])
    rig["provider"].mode = "garbage"
    rig["clock"].t = T0 + timedelta(hours=6, minutes=1)
    r = rig["mgr"].tick()
    assert r["outcome"] == "error" and data_tables(rig["path"]) == before
    assert q(rig["path"], "PRAGMA integrity_check")[0]["integrity_check"] == "ok"


def test_provider_failure_backs_off_and_recovery_returns_to_six_hours(rig):
    mgr, clock, provider = rig["mgr"], rig["clock"], rig["provider"]
    mgr.tick("startup_check")
    provider.mode = "down"
    before = data_tables(rig["path"])
    clock.t = T0 + timedelta(hours=6, minutes=1)
    assert mgr.tick()["outcome"] == "error" and len(provider.urls) == 2                                              # one attempt, no retry
    assert mgr.next_due() == clock.t + timedelta(hours=12)
    assert data_tables(rig["path"]) == before
    clock.t = mgr.next_due()
    provider.mode = "ok"
    assert mgr.tick()["outcome"] == "ok"
    assert mgr.next_due() == clock.t + timedelta(hours=6)


def test_restart_inside_the_interval_and_a_concurrent_run_make_no_request(rig):
    mgr, clock, provider = rig["mgr"], rig["clock"], rig["provider"]
    mgr.tick("startup_check")
    n = len(provider.urls)
    restarted = sync.SyncManager(db_path=rig["path"], cfg=rig["cfg"], opener=provider, sleep=lambda s: None, clock=clock)
    clock.t = T0 + timedelta(hours=1)
    assert restarted.tick("startup_check")["outcome"] == "not_due" and len(provider.urls) == n
    conn = sqlite3.connect(rig["path"])
    conn.execute("INSERT INTO sync_runs(kind, source, started_utc, outcome) VALUES ('periodic_check','all approved',?, 'running')", ((clock.t - timedelta(minutes=5)).strftime(FMT),))
    conn.commit()
    conn.close()
    assert restarted.check_once("periodic_check")["outcome"] == "skipped_already_running" and len(provider.urls) == n


def test_other_leagues_are_not_synchronised_and_the_season_is_configuration_not_code():
    cfg = sync.SyncConfig(live_enabled=True, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA", "EPL", "LALIGA", "SERIEA", "LIGUE1"],
                                                                      "season_overrides": {"BUNDESLIGA": {"season": "2027", "season_label": "2027-28"}}, "verified_seasons": [["bl1", "2027"]]}})
    assert cfg.approved_competitions() == ["BUNDESLIGA", "LALIGA"]
    assert cfg.spec_for("BUNDESLIGA")["season"] == "2027" and cfg.spec_for("BUNDESLIGA")["season_label"] == "2027-28" and cfg.spec_for("BUNDESLIGA")["league"] == "bl1"
    assert sync.APPROVED["BUNDESLIGA"]["season"] == "2026"                                                           # the shipped default is untouched
    assert cfg.verified_seasons() == [("bl1", "2027")] and sync.SyncConfig().verified_seasons() == []


# ------------------------------------------------------------------------------------------------ Phase 4.8D final safeguards: snapshot reuse, request cap
def snap_files(rig):
    d = rig["tmp"] / "snap" / "openligadb"
    return sorted(p for p in d.glob("*.json") if not p.name.endswith(".meta.json")) if d.exists() else []


def last_detail(path):
    return json.loads(q(path, "SELECT detail FROM sync_runs WHERE kind='sync' ORDER BY run_id DESC LIMIT 1")[0]["detail"])


def test_a_byte_identical_response_reuses_the_latest_snapshot_but_the_check_and_its_history_are_still_recorded(rig):
    rig["mgr"].tick("startup_check")
    first = snap_files(rig)
    assert len(first) == 1
    registered = q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots WHERE source='openligadb'")[0]["n"]
    rig["clock"].t = T0 + timedelta(hours=6, minutes=1)
    r = rig["mgr"].tick()
    assert r["outcome"] == "ok" and snap_files(rig) == first                                                    # no second 317 kB file
    assert q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots WHERE source='openligadb'")[0]["n"] == registered
    d1 = last_detail(rig["path"])
    assert d1["snapshot_reused"] is True and d1["snapshot_id"] == first[0].name and d1["response_sha256"] == json.loads(Path(str(first[0]) + ".meta.json").read_text(encoding="utf-8"))["sha256"]
    assert d1["origin"] == "injected_opener" and d1["http_attempts"] == 1 and d1["checked_utc"] == (T0 + timedelta(hours=6, minutes=1)).strftime(FMT)
    runs = q(rig["path"], "SELECT kind, outcome, requests, started_utc FROM sync_runs WHERE kind IN ('startup_check','periodic_check','sync') ORDER BY run_id")
    assert [x["outcome"] for x in runs] == ["ok"] * 4 and [x["requests"] for x in runs] == [1, 1, 1, 1]       # both checks are in the run history
    ledger = (rig["tmp"] / "snap" / "request_ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(ledger) == 2 and all(json.loads(x)["status"] == 200 for x in ledger)                             # and in the request ledger
    meta = json.loads(Path(str(first[0]) + ".meta.json").read_text(encoding="utf-8"))
    assert meta["origin"] == "injected_opener"                                                                   # provenance of the bytes is stored with the snapshot


def test_a_different_response_is_never_deduplicated(rig):
    rig["mgr"].tick("startup_check")
    m = rig["provider"].match(2, "")
    m["lastUpdateDateTime"] = "2026-10-26T10:00:00.00"
    rig["clock"].t = T0 + timedelta(hours=6, minutes=1)
    rig["mgr"].tick()
    files = snap_files(rig)
    assert len(files) == 2 and last_detail(rig["path"])["snapshot_reused"] is False


def test_artifacts_without_an_origin_or_with_a_wrong_hash_are_never_reused_as_provider_data(rig):
    rig["mgr"].tick("startup_check")
    payload = json.dumps(rig["provider"].matches).encode()
    folder = rig["tmp"] / "snap" / "openligadb"
    fake = folder / "99991231T235959Z_bl1_2026_season.json"                                                      # sorts as the "latest", identical bytes, but no origin: a test/replay artifact
    fake.write_bytes(payload)
    Path(str(fake) + ".meta.json").write_text(json.dumps(dict(snapshot_id=fake.name, sha256=__import__("hashlib").sha256(payload).hexdigest(), bytes=len(payload), url=URL)), encoding="utf-8")
    rig["clock"].t = T0 + timedelta(hours=6, minutes=1)
    rig["mgr"].tick()
    assert last_detail(rig["path"])["snapshot_reused"] is False and len([f for f in snap_files(rig) if f.name != fake.name]) == 2     # a genuine snapshot was written instead
    # a genuine snapshot whose file no longer matches its recorded hash is not reused either
    fake.unlink()
    Path(str(fake) + ".meta.json").unlink()
    newest = snap_files(rig)[-1]
    newest.chmod(0o666)
    newest.write_bytes(newest.read_bytes() + b" ")
    rig["clock"].t = T0 + timedelta(hours=12, minutes=2)
    rig["mgr"].tick()
    assert last_detail(rig["path"])["snapshot_reused"] is False


def attempts_for(rig, mode, max_retries):
    cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=max_retries)
    mgr = sync.SyncManager(db_path=rig["path"], cfg=cfg, opener=rig["provider"], sleep=lambda s: None, clock=rig["clock"])
    rig["provider"].mode = mode
    rig["provider"].urls.clear()
    res = mgr.check_once("manual_check")
    return res, len(rig["provider"].urls)


def test_a_cycle_never_makes_more_than_three_requests_whatever_max_retries_says(rig):
    assert sync.SyncConfig().max_retries == 2 and sync.SyncConfig.load().max_retries == 2 and sync.MAX_REQUESTS_PER_CYCLE == 3
    res, n = attempts_for(rig, "down", 2)
    assert res["outcome"] == "error" and n == 3                                                                  # first try + 2 retries
    res, n = attempts_for(rig, "down", 10)
    assert res["outcome"] == "error" and n == 3                                                                  # a larger setting is capped
    res, n = attempts_for(rig, "down", 0)
    assert n == 1
    assert q(rig["path"], "SELECT COUNT(*) n FROM matches WHERE status='completed' AND competition_key='BUNDESLIGA' AND source_system LIKE 'openligadb%'")[0]["n"] == 0     # three failed cycles changed no data


def test_malformed_or_contradictory_responses_are_not_retried_and_nothing_is_saved(rig):
    res, n = attempts_for(rig, "garbage", 2)
    assert res["outcome"] == "error" and n == 1 and snap_files(rig) == []
    rig["provider"].matches = [dict(m, leagueShortcut="pl") for m in rig["provider"].matches]                    # valid JSON, wrong league
    res, n = attempts_for(rig, "ok", 2)
    assert res["outcome"] == "error" and n == 1 and snap_files(rig) == []
    rig["provider"].matches = rig["provider"].matches[:-1] + [dict(rig["provider"].matches[0])]                  # duplicate match id
    res, n = attempts_for(rig, "ok", 2)
    assert res["outcome"] == "error" and n == 1 and snap_files(rig) == []
    errs = q(rig["path"], "SELECT error FROM sync_errors ORDER BY id DESC LIMIT 3")
    assert all(("malformed" in e["error"] or "contradictory" in e["error"]) for e in errs)


def test_failed_cycles_are_counted_and_back_off_12_then_24_hours(rig):
    mgr, clock, provider = rig["mgr"], rig["clock"], rig["provider"]
    mgr.tick("startup_check")
    provider.mode = "down"
    clock.t = T0 + timedelta(hours=6, minutes=1)
    mgr.tick()
    clock.t = mgr.next_due()
    mgr.tick()
    conn = db.connect(rig["path"], readonly=True)
    st = sync.status(conn, rig["cfg"], clock.t)["scheduler"]
    conn.close()
    assert st["consecutive_failed_cycles"] == 2 and st["last_cycle_outcome"] == "error" and "backing off after 2 failed cycle(s)" in st["status"]
    assert datetime.strptime(st["next_scheduled_check_utc"], FMT).replace(tzinfo=timezone.utc) == clock.t + timedelta(hours=24)


def test_a_request_guard_wraps_the_real_opener_and_the_bytes_keep_the_provider_origin(rig):
    """The supervised production cycle uses request_guard: it can restrict the real opener (exact URL, hard cap) while the snapshot is still recorded as provider data."""
    calls = []

    def guard(real):
        assert real is sync._urllib_opener                                                                         # it wraps the real network opener, not a test opener

        def guarded(url, headers):
            calls.append(url)
            assert url == URL and len(calls) <= 1, "guard: only the approved URL, once"
            return 200, json.dumps(rig["provider"].matches).encode(), {}
        return guarded
    mgr = sync.SyncManager(db_path=rig["path"], cfg=rig["cfg"], request_guard=guard, sleep=lambda s: None, clock=rig["clock"])
    r = mgr.tick("startup_check")
    assert r["outcome"] == "ok" and calls == [URL]
    meta = json.loads(Path(str(snap_files(rig)[0]) + ".meta.json").read_text(encoding="utf-8"))
    assert meta["origin"] == "provider_http" and last_detail(rig["path"])["origin"] == "provider_http"
