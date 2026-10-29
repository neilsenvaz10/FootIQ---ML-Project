"""Phase 4.11: football-data.org adapter, PL / SA / FL1, offline. Mock provider answers built from the stored 2026-27 fixtures, a private store copy, a mocked clock, no network and no real token.
The leagues are approved inside each test process only: in the shipped code they are prepared, not approved."""
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from store import baseline, db, footballdata as fd, sync  # noqa: E402

pytestmark = pytest.mark.skipif(not baseline.V_PATH.exists(), reason="baseline inputs are not present")
FMT = "%Y-%m-%dT%H:%M:%SZ"
T0 = datetime(2026, 11, 1, 6, 0, 0, tzinfo=timezone.utc)
TOKEN = "TESTTOKEN0123456789abcdef0123456789"
CODES = {"EPL": "PL", "SERIEA": "SA", "LIGUE1": "FL1"}
BL_URL = "https://api.openligadb.de/getmatchdata/bl1/2026"
BL_FILE = ROOT / "data" / "snapshots" / "p48c" / "openligadb" / "20261027T125704Z_p48c_bl1.json"


def url_of(key):
    return f"{fd.BASE}/competitions/{CODES[key]}/matches?season=2026"


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


def build_payload(path, key):
    """A v4-shaped answer that mirrors what the store already holds for this league-season (same pairings, dates, matchdays and verified scores)."""
    c = db.connect(path, readonly=True)
    rows = [dict(r) for r in c.execute("SELECT * FROM matches WHERE competition_key=? AND season='2026-27' ORDER BY matchday_no, match_date, record_id", (key,))]
    c.close()
    out = []
    for i, r in enumerate(rows):
        done = r["status"] == "completed"
        past = r["match_date"] < T0.strftime("%Y-%m-%d")
        sc = {"winner": None, "duration": "REGULAR", "fullTime": {"home": None, "away": None}, "halfTime": {"home": None, "away": None}}
        if done:
            sc["fullTime"] = {"home": r["home_goals_90"], "away": r["away_goals_90"]}
            sc["regularTime"] = {"home": r["home_goals_90"], "away": r["away_goals_90"]}
        out.append({"area": {"id": 2072}, "competition": {"id": 1, "code": CODES[key]}, "season": {"id": 9, "startDate": "2026-08-15", "endDate": "2027-05-23"}, "id": 700000 + 10000 * list(CODES).index(key) + i,
                    "utcDate": r["match_date"] + "T15:00:00Z", "status": "FINISHED" if done else "TIMED", "matchday": r["matchday_no"], "stage": "REGULAR_SEASON", "group": None, "lastUpdated": "2026-10-27T10:00:00Z",
                    "homeTeam": {"id": 100 + i, "name": r["home_name"], "shortName": r["home_name"], "tla": "HOM", "crest": ""}, "awayTeam": {"id": 200 + i, "name": r["away_name"], "shortName": r["away_name"], "tla": "AWY", "crest": ""},
                    "score": sc, "odds": {"msg": "Activate Odds-Package"}, "referees": []})
    return {"filters": {"season": "2026"}, "resultSet": {"count": len(out), "first": out[0]["utcDate"][:10], "last": out[-1]["utcDate"][:10], "played": sum(1 for m in out if m["status"] == "FINISHED")},
            "competition": {"id": 1, "name": "x", "code": CODES[key], "type": "LEAGUE"}, "matches": out}


class Provider:
    """Stands in for api.football-data.org (and, for the shared-scheduler test, api.openligadb.de). Records every request and the headers it carried."""

    def __init__(self, path, keys=("EPL", "SERIEA", "LIGUE1")):
        self.payload = {url_of(k): build_payload(path, k) for k in keys}
        self.mode = {u: "ok" for u in self.payload}
        self.queue = {}                      # url -> list of (status, headers) answers served before the normal one
        self.urls, self.headers = [], []
        if BL_FILE.exists():
            self.payload[BL_URL] = json.loads(BL_FILE.read_bytes())
            self.mode[BL_URL] = "ok"

    def __call__(self, url, headers):
        self.urls.append(url)
        self.headers.append(dict(headers))
        assert url in self.payload, f"unexpected URL {url}"
        if self.queue.get(url):
            st, hd = self.queue[url].pop(0)
            return st, b"{}", hd
        m = self.mode[url]
        if m == "down":
            return 503, b"", {}
        if m == "denied":
            return 403, b'{"message":"restricted"}', {}
        if m == "unauthorised":
            return 401, b'{"message":"bad token"}', {}
        if m == "garbage":
            return 200, b"<html>no</html>", {}
        return 200, json.dumps(self.payload[url]).encode(), {}


@pytest.fixture(scope="module")
def base_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("fd") / "base.sqlite"
    c = db.connect(path)
    db.init(c)
    baseline.import_baseline(c)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()
    return path


@pytest.fixture(scope="module")
def payloads(base_db):
    return {k: build_payload(base_db, k) for k in CODES}


@pytest.fixture
def rig(base_db, tmp_path, monkeypatch, payloads):
    p = tmp_path / "s.sqlite"
    shutil.copy(base_db, p)
    for k, spec in sync.PREPARED_PROVIDERS.items():
        monkeypatch.setitem(sync.APPROVED, k, spec)
    monkeypatch.setattr(sync, "SNAPSHOT_DIR", tmp_path / "snap")
    monkeypatch.setenv("FOOTIQ_CONTACT", "mailto:contact@footiq-test.local")
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", TOKEN)
    clock = Clock()
    monkeypatch.setattr(sync, "now_utc", lambda: clock.t.strftime(FMT))
    provider = Provider(p)
    slept = []
    cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0, sources={"footballdata": {"enabled": True, "competitions": ["EPL", "SERIEA", "LIGUE1"], "token_env": "FOOTBALL_DATA_API_TOKEN"}})
    mgr = sync.SyncManager(db_path=p, cfg=cfg, opener=provider, sleep=lambda s: slept.append(s), clock=clock)
    return dict(path=p, clock=clock, provider=provider, mgr=mgr, cfg=cfg, tmp=tmp_path, slept=slept)


def q(path, sql, *a):
    c = db.connect(path, readonly=True)
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def rows(path, key):
    return {r["record_id"]: r for r in q(path, "SELECT * FROM matches WHERE competition_key=? AND season='2026-27'", key)}


def scores(path, key):
    """Status, regular-time score and date of every fixture; 'awaiting_result' is the label of a scheduled fixture whose date has passed, so it is compared as 'scheduled'."""
    return {k: ("scheduled" if v["status"] == "awaiting_result" else v["status"], v["home_goals_90"], v["away_goals_90"], v["match_date"]) for k, v in rows(path, key).items()}


def later(rig, h=6, m=1):
    rig["clock"].t += timedelta(hours=h, minutes=m)


def first_scheduled(rig, key, before="2026-11-01"):
    return next(m for m in rig["provider"].payload[url_of(key)]["matches"] if m["status"] != "FINISHED" and m["utcDate"][:10] < before)


def detail(r, key):
    return next(d for d in r["details"] if d["competition"] == key)


# ------------------------------------------------------------------------------------------------ valid data, per league
def test_one_cycle_makes_one_authenticated_request_per_league_and_changes_no_verified_result(rig):
    before = {k: scores(rig["path"], k) for k in CODES}
    r = rig["mgr"].tick("startup_check")
    assert r["outcome"] == "ok" and rig["provider"].urls == [url_of("EPL"), url_of("SERIEA"), url_of("LIGUE1")]
    assert all(h["X-Auth-Token"] == TOKEN for h in rig["provider"].headers)
    assert rig["slept"].count(7.0) == 2                                                                           # a 7 s pause between leagues keeps the free tier (10 a minute) far away
    for k in CODES:
        d = detail(r, k)
        assert d["requests"] == 1 and d["quarantined"] == 0 and d["confirmed"] == sum(1 for v in before[k].values() if v[0] == "completed")
        assert scores(rig["path"], k) == before[k]                                                                # same statuses, scores and dates
        assert q(rig["path"], "SELECT COUNT(*) - COUNT(DISTINCT record_id) n FROM matches WHERE competition_key=?", k)[0]["n"] == 0
    snaps = q(rig["path"], "SELECT url, source, sha256, licence, attribution FROM source_snapshots WHERE source='footballdata'")
    assert {s["url"] for s in snaps} == {url_of(k) for k in CODES} and all(s["attribution"] == "Football data provided by the Football-Data.org API" for s in snaps)
    assert all("unconfirmed" in s["licence"] for s in snaps)                                                      # the storage permission is recorded as unconfirmed, not assumed
    links = q(rig["path"], "SELECT COUNT(*) n FROM match_sources WHERE source='footballdata'")[0]["n"]
    assert links == 380 + 380 + 306
    assert q(rig["path"], "PRAGMA integrity_check")[0]["integrity_check"] == "ok"


def test_the_token_is_never_written_anywhere(rig):
    rig["mgr"].tick("startup_check")
    rig["provider"].mode[url_of("SERIEA")] = "down"
    later(rig)
    rig["mgr"].tick()
    hits = []
    for f in list(rig["tmp"].rglob("*")) + [rig["path"]]:
        if f.is_file() and TOKEN.encode() in f.read_bytes():
            hits.append(f.name)
    ledger = ROOT / "data" / "snapshots" / "request_ledger.jsonl"
    assert hits == [] and (not ledger.exists() or TOKEN not in ledger.read_text(encoding="utf-8"))
    assert fd.redact(f"HTTP failed with {TOKEN} inside") == "HTTP failed with [token-redacted] inside"


# ------------------------------------------------------------------------------------------------ new and delayed results
def test_new_and_delayed_results_are_ingested_once(rig):
    rig["mgr"].tick("startup_check")
    key = "EPL"
    waiting = [m for m in rig["provider"].payload[url_of(key)]["matches"] if m["status"] != "FINISHED" and m["utcDate"][:10] < "2026-10-25"]
    held = {x["source_ref"] for x in q(rig["path"], "SELECT source_ref FROM quarantine")}
    old, newer = waiting[0], waiting[-1]
    assert old["matchday"] < newer["matchday"]
    for i, m in enumerate((old, newer)):
        m["status"] = "FINISHED"
        m["score"] = {"winner": "HOME_TEAM", "duration": "REGULAR", "fullTime": {"home": 2 + i, "away": 1}, "halfTime": {"home": 1, "away": 0}, "regularTime": {"home": 2 + i, "away": 1}}
    later(rig)
    r = rig["mgr"].tick()
    assert detail(r, key)["inserted"] + detail(r, key)["updated"] == 2
    got = {v["home_goals_90"]: v for v in rows(rig["path"], key).values() if v["status"] == "completed" and v["away_goals_90"] == 1}
    assert 2 in got and 3 in got
    later(rig)
    r2 = rig["mgr"].tick()                                                                                         # the identical answer again: nothing moves
    assert detail(r2, key)["inserted"] == 0 and detail(r2, key)["updated"] == 0 and detail(r2, key)["snapshot_reused"] is True
    links = q(rig["path"], "SELECT role FROM match_sources WHERE source='footballdata' AND source_ref IN (?,?)", str(old["id"]), str(newer["id"]))
    assert [x["role"] for x in links] == ["primary", "primary"]


# ------------------------------------------------------------------------------------------------ duplicates
def test_duplicate_responses_store_one_snapshot_and_change_nothing(rig):
    rig["mgr"].tick("startup_check")
    n_snap = q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots WHERE source='footballdata'")[0]["n"]
    files = sorted((rig["tmp"] / "snap" / "footballdata").glob("*.json"))
    tables = {t: q(rig["path"], f"SELECT COUNT(*) n FROM {t}")[0]["n"] for t in ("matches", "match_sources", "quarantine")}
    for _ in range(2):
        later(rig)
        r = rig["mgr"].tick()
        assert all(detail(r, k)["snapshot_reused"] and detail(r, k)["inserted"] == 0 and detail(r, k)["updated"] == 0 for k in CODES)
    assert q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots WHERE source='footballdata'")[0]["n"] == n_snap
    assert sorted((rig["tmp"] / "snap" / "footballdata").glob("*.json")) == files
    assert {t: q(rig["path"], f"SELECT COUNT(*) n FROM {t}")[0]["n"] for t in tables} == tables


# ------------------------------------------------------------------------------------------------ missing / incomplete / unknown
def test_incomplete_or_malformed_answers_are_rejected_and_touch_no_data(rig):
    rig["mgr"].tick("startup_check")
    snap_before = q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots")[0]["n"]
    before = {k: scores(rig["path"], k) for k in CODES}
    pl, sa, fl = (rig["provider"].payload[url_of(k)] for k in ("EPL", "SERIEA", "LIGUE1"))
    pl["resultSet"]["count"] += 20                                                                                 # claims more matches than it holds: truncated or paged
    sa["matches"][5]["id"] = sa["matches"][6]["id"]                                                                # duplicate ids
    fl["competition"]["code"] = "BL1"                                                                              # somebody else's league
    later(rig)
    r = rig["mgr"].tick()
    assert r["outcome"] == "error" and all("error" in detail(r, k) for k in CODES)
    assert "incomplete response" in detail(r, "EPL")["error"] and "duplicate" in detail(r, "SERIEA")["error"] and "contradictory" in detail(r, "LIGUE1")["error"]
    assert {k: scores(rig["path"], k) for k in CODES} == before
    assert q(rig["path"], "SELECT COUNT(*) n FROM source_snapshots")[0]["n"] == snap_before                       # rejected bytes are not even registered
    assert not any("matchday" in x["error"] for x in q(rig["path"], "SELECT error FROM sync_errors ORDER BY id DESC LIMIT 0"))


def test_a_finished_match_without_a_usable_score_an_award_and_extra_time_are_held_for_a_human(rig):
    rig["mgr"].tick("startup_check")
    key = "SERIEA"
    ms = [m for m in rig["provider"].payload[url_of(key)]["matches"] if m["status"] != "FINISHED" and m["utcDate"][:10] < "2026-10-25"][:3]
    ms[0]["status"], ms[0]["score"] = "FINISHED", {"duration": "REGULAR", "fullTime": {"home": None, "away": None}}
    ms[1]["status"], ms[1]["score"] = "AWARDED", {"duration": "REGULAR", "fullTime": {"home": 3, "away": 0}}
    ms[2]["status"], ms[2]["score"] = "FINISHED", {"duration": "EXTRA_TIME", "fullTime": {"home": 2, "away": 1}}
    before = scores(rig["path"], key)
    later(rig)
    r = rig["mgr"].tick()
    assert detail(r, key)["quarantined"] == 3 and detail(r, key)["inserted"] + detail(r, key)["updated"] == 0
    assert scores(rig["path"], key) == before
    reasons = [x["reason"] for x in q(rig["path"], "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 3")]
    assert all(x.startswith("completed without an explicit 90-minute result") for x in reasons)


def test_an_unknown_team_is_quarantined_and_no_fixture_or_entity_is_created(rig):
    rig["mgr"].tick("startup_check")
    key = "LIGUE1"
    m = rig["provider"].payload[url_of(key)]["matches"][50]
    m["homeTeam"]["name"] = m["homeTeam"]["shortName"] = "Olympique Atlantis"
    n_matches = q(rig["path"], "SELECT COUNT(*) n FROM matches")[0]["n"]
    n_teams = q(rig["path"], "SELECT COUNT(*) n FROM teams")[0]["n"]
    later(rig)
    r = rig["mgr"].tick()
    assert detail(r, key)["quarantined"] == 1
    assert q(rig["path"], "SELECT COUNT(*) n FROM matches")[0]["n"] == n_matches and q(rig["path"], "SELECT COUNT(*) n FROM teams")[0]["n"] == n_teams
    assert any("unresolved team identity" in x["reason"] and "Olympique Atlantis" in x["reason"] for x in q(rig["path"], "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 2"))


def test_a_scheduled_placeholder_midnight_is_neither_a_kickoff_nor_a_date(rig):
    """Seen on the first real read: SCHEDULED fixtures carry utcDate T00:00:00Z. They must not write a kick-off, change a stored date or open a date dispute; TIMED ones still do."""
    key = "SERIEA"
    ms = rig["provider"].payload[url_of(key)]["matches"]
    sched = [m for m in ms if m["status"] != "FINISHED" and m["utcDate"][:10] > "2026-12-01"][:5]
    stored_before = {m["id"]: None for m in sched}
    for m in sched:
        m["status"] = "SCHEDULED"
        d = datetime.strptime(m["utcDate"], FMT) + timedelta(days=1)                                              # a different day AND midnight: must still be ignored
        m["utcDate"] = d.strftime("%Y-%m-%dT00:00:00Z")
    rec = fd.parse_match(sched[0], "", "", T0, key, "2026")
    assert rec.kickoff_utc is None and rec.match_date is None and rec.time_precision == "none" and rec.status == "upcoming" and "provisional_date_placeholder_ignored" in rec.flags
    dates = {k: v["match_date"] for k, v in rows(rig["path"], key).items()}
    r = rig["mgr"].tick("startup_check")
    assert detail(r, key)["quarantined"] == 0
    assert {k: v["match_date"] for k, v in rows(rig["path"], key).items()} == dates
    assert q(rig["path"], "SELECT COUNT(*) n FROM matches WHERE competition_key=? AND kickoff_utc LIKE '%T00:00:00Z'", key)[0]["n"] == 0
    timed = fd.parse_match(next(m for m in ms if m["status"] == "TIMED"), "", "", T0, key, "2026")
    assert timed.kickoff_utc and timed.time_precision == "utc"


def test_the_identity_report_lists_unresolved_names_without_guessing(rig):
    c = db.connect(rig["path"], readonly=True)
    resolver = sync.build_resolver(c)
    c.close()
    body = json.dumps(rig["provider"].payload[url_of("EPL")]).encode()
    ok = fd.identity_report(body, resolver, "england:1-premierleague")
    assert len(ok["resolved"]) == 20 and ok["unresolved"] == []
    pl = json.loads(body)
    pl["matches"][0]["homeTeam"]["name"] = pl["matches"][0]["homeTeam"]["shortName"] = "Arsenal Wanderers"
    bad = fd.identity_report(json.dumps(pl).encode(), resolver, "england:1-premierleague")
    assert [u["name"] for u in bad["unresolved"]] == ["Arsenal Wanderers"]


# ------------------------------------------------------------------------------------------------ conflicts
def test_conflicting_scores_and_disputed_dates_are_quarantined_and_never_applied(rig):
    rig["mgr"].tick("startup_check")
    key = "EPL"
    ms = rig["provider"].payload[url_of(key)]["matches"]
    done = next(m for m in ms if m["status"] == "FINISHED")
    done["score"]["regularTime"]["home"] += 3
    done["score"]["fullTime"]["home"] += 3
    future = next(m for m in ms if m["status"] != "FINISHED" and m["utcDate"] > "2027-01")
    moved = datetime.strptime(future["utcDate"], FMT) + timedelta(days=3)
    future["utcDate"] = moved.strftime(FMT)
    before = scores(rig["path"], key)
    later(rig)
    r = rig["mgr"].tick()
    assert r["outcome"] == "ok" and detail(r, key)["quarantined"] == 2
    assert scores(rig["path"], key) == before
    reasons = [x["reason"] for x in q(rig["path"], "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 2")]
    assert any(x.startswith("CONFLICT") for x in reasons) and any(x.startswith("DATE_DIFFERENCE") for x in reasons)


# ------------------------------------------------------------------------------------------------ rate limits and HTTP errors
def test_a_429_with_retry_after_is_waited_out_within_the_attempt_cap(rig):
    rig["mgr"].cfg.max_retries = 2
    rig["provider"].queue[url_of("EPL")] = [(429, {"Retry-After": "42"}), (429, {"Retry-After": "42"})]
    r = rig["mgr"].tick("startup_check")
    assert r["outcome"] == "ok" and detail(r, "EPL")["requests"] == 3 and rig["provider"].urls.count(url_of("EPL")) == 3
    assert 42.0 in rig["slept"]
    rig["provider"].urls.clear()
    later(rig)
    rig["provider"].queue[url_of("EPL")] = [(429, {"Retry-After": "5"})] * 5
    r2 = rig["mgr"].tick()
    assert "error" in detail(r2, "EPL") and rig["provider"].urls.count(url_of("EPL")) == 3                        # hard cap of 3 attempts, then the league backs off
    assert "error" not in detail(r2, "SERIEA") and "error" not in detail(r2, "LIGUE1")


def test_without_retries_one_429_fails_the_league_after_one_request(rig):
    rig["provider"].queue[url_of("SERIEA")] = [(429, {})]
    r = rig["mgr"].tick("startup_check")
    assert "error" in detail(r, "SERIEA") and rig["provider"].urls.count(url_of("SERIEA")) == 1
    assert "error" not in detail(r, "EPL") and "error" not in detail(r, "LIGUE1")


@pytest.mark.parametrize("mode", ["unauthorised", "denied"])
def test_401_and_403_are_not_retried(rig, mode):
    rig["mgr"].cfg.max_retries = 2
    rig["provider"].mode[url_of("EPL")] = mode
    r = rig["mgr"].tick("startup_check")
    assert "error" in detail(r, "EPL") and rig["provider"].urls.count(url_of("EPL")) == 1
    assert "HTTP 40" in detail(r, "EPL")["error"] and TOKEN not in detail(r, "EPL")["error"]


def test_a_provider_outage_in_one_league_leaves_the_others_and_their_schedules_alone(rig):
    rig["mgr"].tick("startup_check")
    rig["provider"].mode[url_of("SERIEA")] = "down"
    rig["provider"].urls.clear()
    later(rig)
    r = rig["mgr"].tick()
    assert "error" in detail(r, "SERIEA") and "error" not in detail(r, "EPL") and "error" not in detail(r, "LIGUE1")
    due = rig["mgr"].league_due()
    assert due["SERIEA"] == rig["clock"].t + timedelta(hours=12) and due["EPL"] == due["LIGUE1"] == rig["clock"].t + timedelta(hours=6)
    rig["provider"].urls.clear()
    rig["clock"].t += timedelta(hours=6)
    rig["provider"].mode[url_of("SERIEA")] = "ok"
    r2 = rig["mgr"].tick()
    assert sorted(rig["provider"].urls) == sorted([url_of("EPL"), url_of("LIGUE1")])                                # only the leagues that are due are asked
    rig["clock"].t += timedelta(hours=6)
    r3 = rig["mgr"].tick()
    assert "error" not in detail(r3, "SERIEA")
    assert rig["mgr"].league_due()["SERIEA"] == rig["clock"].t + timedelta(hours=6)


# ------------------------------------------------------------------------------------------------ token problems
@pytest.mark.parametrize("value", [None, "", "   ", "short", "has a space in it 0123456789", "x" * 200])
def test_a_missing_or_invalid_token_stops_the_league_before_any_request(rig, monkeypatch, value):
    if value is None:
        monkeypatch.delenv("FOOTBALL_DATA_API_TOKEN")
    else:
        monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", value)
    before = {k: scores(rig["path"], k) for k in CODES}
    r = rig["mgr"].tick("startup_check")
    assert r["outcome"] == "error" and rig["provider"].urls == []                                                  # not one request, not even a failed one
    assert all(("TokenMissing" in detail(r, k)["error"] or "TokenInvalid" in detail(r, k)["error"]) for k in CODES)
    assert {k: scores(rig["path"], k) for k in CODES} == before
    assert not (rig["tmp"] / "snap" / "footballdata").exists()
    conn = db.connect(rig["path"], readonly=True)
    st = sync.status(conn, rig["cfg"], rig["clock"].t)["scheduler"]["leagues"]
    conn.close()
    assert all(st[k]["consecutive_failed_cycles"] == 1 for k in CODES)


def test_a_missing_token_does_not_stop_another_provider_in_the_same_scheduler(rig, monkeypatch):
    if BL_URL not in rig["provider"].payload:
        pytest.skip("saved Bundesliga response not present")
    monkeypatch.delenv("FOOTBALL_DATA_API_TOKEN")
    cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0, sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA"]},
                                                                                       "footballdata": {"enabled": True, "competitions": ["EPL"]}})
    mgr = sync.SyncManager(db_path=rig["path"], cfg=cfg, opener=rig["provider"], sleep=lambda s: None, clock=rig["clock"])
    r = mgr.tick("startup_check")
    assert "error" not in detail(r, "BUNDESLIGA") and "TokenMissing" in detail(r, "EPL")["error"] and rig["provider"].urls == [BL_URL]


# ------------------------------------------------------------------------------------------------ nothing is active
def test_the_three_leagues_are_prepared_not_approved_and_the_shipped_config_requests_nothing():
    assert set(sync.PREPARED_PROVIDERS) == {"EPL", "SERIEA", "LIGUE1"} and not set(sync.PREPARED_PROVIDERS) & set(sync.APPROVED)
    listed = sync.SyncConfig(live_enabled=True, sources={"footballdata": {"enabled": True, "competitions": ["EPL", "SERIEA", "LIGUE1"]}})
    assert listed.approved_competitions() == []                                                                    # listing them in the config cannot approve them
    shipped = sync.SyncConfig.load()
    assert shipped.sources["footballdata"]["enabled"] is False and shipped.sources["footballdata"]["competitions"] == []
    assert "EPL" not in shipped.approved_competitions() and shipped.token_env() == "FOOTBALL_DATA_API_TOKEN"
    assert {k: sync.READINESS[k][0] for k in ("EPL", "SERIEA", "LIGUE1")} == {"EPL": "prepared_offline", "SERIEA": "prepared_needs_token", "LIGUE1": "prepared_needs_token"}


def test_status_shows_the_football_data_attribution_once_a_league_is_approved(rig):
    rig["mgr"].tick("startup_check")
    conn = db.connect(rig["path"], readonly=True)
    st = sync.status(conn, rig["cfg"], rig["clock"].t)
    conn.close()
    assert [(a["source"], a["text"]) for a in st["attribution"]] == [("football-data.org", "Football data provided by the Football-Data.org API")]
    comps = {c["competition_key"]: c for c in st["competitions"]}
    for k in CODES:
        assert comps[k]["provider_readiness"] == "approved_live_enabled" and comps[k]["last_successful_external_check_utc"] and "football-data.org" in comps[k]["provider_note"]
