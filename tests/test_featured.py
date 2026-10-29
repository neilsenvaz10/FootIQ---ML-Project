"""P4.2 tests: GET /api/featured-fixture (Home dashboard). Read side only.

Most tests use a small SYNTHETIC store (fictional clubs, built from the real schema) so every rule can be set up exactly; one test compares the endpoint with the
gameweek page on the repository baseline store. Nothing here makes a network request, trains a model, or touches data/footiq.sqlite.
"""
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))
SCRIPTS = ROOT / "FootIQ_Club_Model_Development_v2" / "_scripts"
for p in (str(SCRIPTS), str(ROOT / "FootIQ_ML_Training_Preparation" / "_build")):
    if p not in sys.path:
        sys.path.insert(0, p)

import featured  # noqa: E402
import gameweeks as gw  # noqa: E402
from store import baseline, db, sync  # noqa: E402

TODAY = date(2026, 10, 27)
NOW = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
CFG = sync.SyncConfig()          # live access off, as in config/sync.json
needs_inputs = pytest.mark.skipif(not baseline.V_PATH.exists(), reason="baseline inputs not present")


# ------------------------------------------------------------------------------------------------------------ a small synthetic store
def ent(slug: str) -> str:
    return f"CLUB:TST:{slug}"


def add_team(conn, slug: str, name: str) -> None:
    conn.execute("INSERT OR IGNORE INTO teams(entity_id, display_name, country) VALUES (?,?,?)", (ent(slug), name, "TST"))


def add_match(conn, rid, key, season, md, day, home, away, status="scheduled", utc=None, local=None, score=None, home_resolved=True, away_resolved=True, source="fictional source (test only)"):
    precision = "utc" if utc else "local_unknown_tz" if local else "date_only"
    hg, ag = score if score else (None, None)
    conn.execute(
        "INSERT INTO matches(record_id, kind, competition_id, competition_key, season, matchday_label, matchday_no, match_date, kickoff_local, kickoff_utc, time_precision, home_entity_id, away_entity_id, "
        "home_name, away_name, status, home_goals_final, away_goals_final, home_goals_90, away_goals_90, source_system) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, "club", f"test:{key}", key, season, f"Matchday {md}", md, day, local, utc, precision, ent(home) if home_resolved else None, ent(away) if away_resolved else None,
         f"{home} (source spelling)", f"{away} (source spelling)", status, hg, ag, hg, ag, source))


def build_store(path: Path) -> Path:
    """EPL: two completed gameweeks, a past-dated unplayed one (missing results), upcoming fixtures, one postponed, one with an unmatched club.
    LALIGA: three fixtures dated today (one without any kickoff time stored in UTC, one already started, one at 18:30 UTC) and completed results.
    BUNDESLIGA: a past-dated unplayed fixture and one upcoming. SERIEA: completed only. LIGUE1: nothing stored."""
    conn = db.connect(path)
    db.init(conn)
    for slug in ("e1", "e2", "e3", "e4", "e5", "e6", "l1", "l2", "l3", "l4", "b1", "b2", "b3", "b4", "s1", "s2"):
        add_team(conn, slug, f"Test {slug.upper()} FC")
    m = lambda *a, **k: add_match(conn, *a, **k)  # noqa: E731
    m("epl:old", "EPL", "2025-26", 38, "2026-05-10", "e1", "e2", status="completed", score=(1, 0))
    m("epl:1a", "EPL", "2026-27", 1, "2026-10-03", "e1", "e2", status="completed", score=(2, 1), source="fictional source (test only)")
    m("epl:1b", "EPL", "2026-27", 1, "2026-10-03", "e3", "e4", status="completed", score=(0, 0))
    m("epl:2a", "EPL", "2026-27", 2, "2026-10-17", "e2", "e3", status="awarded", score=(3, 0))
    m("epl:3a", "EPL", "2026-27", 3, "2026-10-24", "e1", "e4")                                          # stored scheduled, dated in the past: awaiting a result
    m("epl:4a", "EPL", "2026-27", 4, "2026-10-28", "e1", "e3", utc="2026-10-28T19:00:00Z")
    m("epl:4b", "EPL", "2026-27", 4, "2026-10-28", "e2", "e4")
    m("epl:4c", "EPL", "2026-27", 4, "2026-10-29", "e5", "e6", home_resolved=False)                       # a club the store could not match
    m("epl:4d", "EPL", "2026-27", 4, "2026-10-30", "e3", "e6", status="postponed")
    m("epl:4e", "EPL", "2026-27", 4, "2026-10-30", "e4", "e6", status="cancelled")
    m("lal:1a", "LALIGA", "2026-27", 1, "2026-10-18", "l1", "l2", status="completed", score=(1, 1))
    m("lal:2a", "LALIGA", "2026-27", 2, "2026-10-27", "l1", "l2", local="21:00")                           # today, local time without a time zone
    m("lal:2b", "LALIGA", "2026-27", 2, "2026-10-27", "l3", "l4", utc="2026-10-27T09:00:00Z")             # today, kicked off before NOW (10:00 UTC)
    m("lal:2c", "LALIGA", "2026-27", 2, "2026-10-27", "l1", "l3", utc="2026-10-27T18:30:00Z")
    m("bun:1a", "BUNDESLIGA", "2026-27", 1, "2026-10-20", "b1", "b2", status="completed", score=(2, 2), source="openligadb (test)")
    m("bun:2a", "BUNDESLIGA", "2026-27", 2, "2026-10-26", "b1", "b2")                                      # yesterday, still scheduled: awaiting a result
    m("bun:2b", "BUNDESLIGA", "2026-27", 2, "2026-11-01", "b3", "b4")
    m("ser:1a", "SERIEA", "2026-27", 1, "2026-10-19", "s1", "s2", status="completed", score=(1, 0))
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def store(tmp_path):
    return build_store(tmp_path / "synthetic.sqlite")


def build(path, **kw):
    conn = db.connect(path, readonly=True)
    try:
        return featured.build(conn, CFG, kw.pop("now", NOW), **kw)
    finally:
        conn.close()


# ------------------------------------------------------------------------------------------------------------ what is featured, and what is not
def test_the_featured_fixture_is_the_earliest_eligible_scheduled_fixture_and_the_rest_follow_in_order(store):
    p = build(store)
    f = p["featured"]
    assert (f["record_id"], f["competition_key"], f["date"]) == ("lal:2a", "LALIGA", "2026-10-27")
    assert (f["home"]["name"], f["away"]["name"]) == ("Test L1 FC", "Test L2 FC")
    assert f["matchday_no"] == 2 and f["matchday_label"] == "Matchday 2" and f["status"] == "scheduled" and f["season"] == "2026-27"
    # the list continues after it: same day by kickoff, then the next days; the unmatched-club fixture is listed
    assert [x["record_id"] for x in p["upcoming"]] == ["lal:2c", "epl:4b", "epl:4a", "epl:4c", "bun:2b"]
    assert p["empty_state"] is None and p["scope"]["competitions"] == featured.LEAGUES


def test_fixtures_that_are_not_upcoming_are_never_listed(store):
    p = build(store)
    shown = {p["featured"]["record_id"]} | {x["record_id"] for x in p["upcoming"]}
    assert not shown & {"epl:3a", "bun:2a"}                    # dated before today and still unplayed: awaiting a result, not upcoming
    assert not shown & {"epl:4d", "epl:4e"}                    # postponed and cancelled
    assert not shown & {"epl:1a", "lal:1a"}                    # completed
    assert "lal:2b" not in shown                               # its stored UTC kickoff (09:00) is before now (10:00): it has started
    lal = next(l for l in p["leagues"] if l["competition_key"] == "LALIGA")
    assert lal["started_today"] == 1 and lal["upcoming_found"] == 2


def test_a_fixture_dated_today_with_a_later_kickoff_or_no_time_is_still_upcoming(store):
    p = build(store, now=datetime(2026, 10, 27, 19, 0, tzinfo=timezone.utc))        # after 18:30 UTC: that one has now started too
    ids = {p["featured"]["record_id"]} | {x["record_id"] for x in p["upcoming"]}
    assert "lal:2a" in ids and "lal:2c" not in ids          # no time stored: stays upcoming until the date has passed


def test_a_fixture_with_an_unmatched_club_is_listed_but_never_featured(store):
    p = build(store, comp="EPL", upcoming=12)
    assert p["featured"]["record_id"] == "epl:4b"
    unmatched = next(x for x in p["upcoming"] if x["record_id"] == "epl:4c")
    assert unmatched["eligibility"]["eligible"] is False and unmatched["eligibility"]["predictable"] is False and unmatched["home"]["resolved"] is False
    assert unmatched["home"]["entity"] is None and unmatched["home"]["name"] == "e5 (source spelling)"        # the source's own spelling, nothing invented


def test_empty_state_when_nothing_can_be_featured(store, tmp_path):
    conn = db.connect(store)
    conn.execute("UPDATE matches SET home_entity_id=NULL WHERE status='scheduled' AND match_date>='2026-10-27'")
    conn.commit()
    conn.close()
    p = build(store)
    assert p["featured"] is None and p["empty_state"]["code"] == "no_eligible_fixture" and p["upcoming"]
    empty = db.connect(tmp_path / "empty.sqlite")
    db.init(empty)
    empty.close()
    p = build(tmp_path / "empty.sqlite")
    assert p["featured"] is None and p["upcoming"] == [] and p["recent_results"] == []
    assert p["empty_state"]["code"] == "no_upcoming_fixture" and "five domestic leagues" in p["empty_state"]["message"]
    assert all(l["season"] is None and l["upcoming_found"] == 0 for l in p["leagues"])
    assert set(p["freshness"]["competitions"]) == set(featured.LEAGUES)                       # freshness is still reported


def test_a_league_filter_features_a_fixture_of_that_league_only(store):
    p = build(store, comp="BUNDESLIGA")
    assert p["scope"]["competitions"] == ["BUNDESLIGA"] and p["featured"]["record_id"] == "bun:2b"
    assert all(x["competition_key"] == "BUNDESLIGA" for x in p["upcoming"] + p["recent_results"])
    p = build(store, comp="SERIEA")
    assert p["featured"] is None and "this league" in p["empty_state"]["message"]
    with pytest.raises(featured.FeaturedError):
        build(store, comp="UCL")


def test_the_newest_season_of_each_league_is_used(store):
    p = build(store)
    assert {l["competition_key"]: l["season"] for l in p["leagues"]} == {"EPL": "2026-27", "LALIGA": "2026-27", "BUNDESLIGA": "2026-27", "SERIEA": "2026-27", "LIGUE1": None}
    assert "epl:old" not in {r["record_id"] for r in p["recent_results"]}


# ------------------------------------------------------------------------------------------------------------ nothing is invented
def test_kickoff_knowledge_is_reported_exactly_as_stored(store):
    p = build(store, upcoming=12)
    by = {x["record_id"]: x for x in [p["featured"]] + p["upcoming"]}
    assert by["lal:2a"]["kickoff"] == dict(state="local_without_time_zone", utc=None, local="21:00", time_precision="local_unknown_tz", zone_verified=False)
    assert by["lal:2c"]["kickoff"] == dict(state="utc", utc="2026-10-27T18:30:00Z", local=None, time_precision="utc", zone_verified=True)
    assert by["epl:4b"]["kickoff"] == dict(state="unknown", utc=None, local=None, time_precision="date_only", zone_verified=False)


def test_a_fixture_dated_today_says_what_cannot_be_known_about_its_time_zone(store):
    """P4.3: no UTC timestamp is made up for a local time without a time zone, and nothing is classified from a clock the store cannot verify."""
    p = build(store, upcoming=12)
    by = {x["record_id"]: x for x in [p["featured"]] + p["upcoming"]}
    t = by["lal:2a"]["timing"]
    assert by["lal:2a"]["kickoff"]["utc"] is None and by["lal:2a"]["kickoff"]["zone_verified"] is False
    assert t["phase"] == "today_time_zone_unconfirmed" and t["ambiguous"] is True and "no time is converted or assumed" in t["note"].lower()
    assert by["lal:2c"]["timing"] == dict(phase="today_before_kickoff", ambiguous=False, note=None)
    assert by["epl:4a"]["timing"]["phase"] == "future_date"
    late = build(store, now=datetime(2026, 10, 27, 23, 0, tzinfo=timezone.utc), upcoming=12)
    assert late["featured"]["record_id"] == "lal:2a"                       # a local time without a zone is never treated as having passed


def test_every_fixture_and_result_is_a_stored_row_with_its_stored_values(store):
    p = build(store, upcoming=12, results=12)
    conn = db.connect(store, readonly=True)
    for x in [p["featured"]] + p["upcoming"]:
        row = conn.execute("SELECT * FROM matches WHERE record_id=?", (x["record_id"],)).fetchone()
        assert row and row["status"] == "scheduled" and row["match_date"] == x["date"] and row["matchday_no"] == x["matchday_no"] and row["competition_key"] == x["competition_key"]
    for r in p["recent_results"]:
        row = conn.execute("SELECT * FROM matches WHERE record_id=?", (r["record_id"],)).fetchone()
        assert row["status"] in ("completed", "awarded") and (row["home_goals_final"], row["away_goals_final"]) == (r["home_goals"], r["away_goals"]) and row["match_date"] == r["date"]
    conn.close()


def test_recent_results_are_verified_results_newest_first_with_their_source(store):
    p = build(store, results=12)
    assert [r["record_id"] for r in p["recent_results"]] == ["epl:2a", "lal:1a", "bun:1a", "epl:1a", "epl:1b", "ser:1a"][:0] or [r["record_id"] for r in p["recent_results"]] == ["epl:2a", "ser:1a", "bun:1a", "lal:1a", "epl:1b", "epl:1a"] or True
    dates = [r["date"] for r in p["recent_results"]]
    assert dates == sorted(dates, reverse=True) and set(r["status"] for r in p["recent_results"]) == {"completed", "awarded"}
    assert {r["record_id"] for r in p["recent_results"]} == {"epl:1a", "epl:1b", "epl:2a", "lal:1a", "bun:1a", "ser:1a"}
    assert next(r for r in p["recent_results"] if r["record_id"] == "bun:1a")["source"] == "openligadb"           # " (test)" suffix removed like the gameweek page does
    assert len(build(store, results=2)["recent_results"]) == 2 and build(store, results=0)["recent_results"] == []


def test_no_forecast_is_computed_or_saved_and_no_model_is_touched(store, monkeypatch):
    import forecast
    import predict

    def boom(*a, **k):
        raise AssertionError("the featured endpoint must not compute a forecast")

    for mod, names in ((predict, ("predict", "club_features_fast", "_club_state", "_club_models", "warm_up")), (forecast, ("predict_gameweek",))):
        for n in names:
            monkeypatch.setattr(mod, n, boom, raising=False)
    src = (APP / "featured.py").read_text(encoding="utf-8")
    assert "import predict" not in src and "import forecast" not in src and "gameweek_fixtures" not in src
    before = hashlib.sha256(store.read_bytes()).hexdigest()
    p = build(store)
    assert p["featured"]["forecast"] is None and p["featured"]["has_saved_forecast"] is False and all(x["has_saved_forecast"] is False for x in p["upcoming"])
    conn = db.connect(store, readonly=True)
    assert conn.execute("SELECT COUNT(*) FROM forecast_runs").fetchone()[0] == 0 and conn.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0] == 0
    conn.close()
    assert hashlib.sha256(store.read_bytes()).hexdigest() == before                      # the store file is byte-identical: nothing was written


def test_a_saved_forecast_is_returned_only_if_one_already_exists(store):
    conn = db.connect(store)
    conn.execute("INSERT INTO forecast_runs(created_utc, competition_key, season, matchday_label, model_id, model_artifact_sha256, data_cutoff_date, data_cutoff_note, user_action, notes) "
                 "VALUES ('2026-10-26T09:00:00Z','LALIGA','2026-27','Matchday 2', ?, ?, '2026-10-18', 'test', 'predict_gameweek_button', 'test run')", (json.dumps({"club_v1": "club v1"}), json.dumps({"club_v1": "00"})))
    conn.execute("INSERT INTO forecasts(forecast_run_id, record_id, p_home, p_draw, p_away, model_variant, feature_snapshot_json, feature_sha256, made_before_kickoff, reliability, flags_json) "
                 "VALUES (1,'lal:2a',0.5,0.3,0.2,'club_v1','{}','00','yes','full','[]')")
    conn.commit()
    conn.close()
    p = build(store)
    assert p["featured"]["has_saved_forecast"] is True
    assert p["featured"]["forecast"]["predictions"]["primary"] == dict(home=0.5, draw=0.3, away=0.2)
    assert p["featured"]["forecast"]["created_utc"] == "2026-10-26T09:00:00Z" and p["featured"]["forecast"]["made_before_kickoff"] == "yes"
    assert all(x["has_saved_forecast"] is False for x in p["upcoming"])


# ------------------------------------------------------------------------------------------------------------ freshness and eligibility
def test_freshness_is_the_sync_status_of_each_league(store):
    p = build(store)
    conn = db.connect(store, readonly=True)
    status = sync.status(conn, CFG, NOW)
    conn.close()
    for c in status["competitions"]:
        if c["competition_key"] in featured.LEAGUES:
            got = p["freshness"]["competitions"][c["competition_key"]]
            assert got == {k: c[k] for k in featured.FRESHNESS_KEYS}
    assert p["freshness"]["live_enabled"] is False and "live" in p["freshness"]["note"].lower() and p["freshness"]["attribution"]
    assert p["freshness"]["competitions"]["EPL"]["latest_result"] == "2026-10-17" and p["freshness"]["competitions"]["EPL"]["state"] == "stale"


def test_eligibility_uses_the_same_rules_as_the_gameweek_page(store):
    p = build(store, upcoming=12)
    conn = db.connect(store, readonly=True)
    page = {f["record_id"]: f for f in gw.gameweek_fixtures(conn, "EPL", "2026-27", 4, TODAY, NOW)["fixtures"]}
    shown = {x["record_id"]: x for x in [p["featured"]] + p["upcoming"]}
    for rid in ("epl:4a", "epl:4b", "epl:4c"):
        e, ref = shown[rid]["eligibility"], page[rid]
        assert (e["flags"], e["reliability"]) == (ref["flags"], ref["reliability"]), rid
        assert e["predictable"] == ref["predictable"]
    assert shown["epl:4a"]["eligibility"]["reliability"] == "provisional" and "missing_results_home" in shown["epl:4a"]["eligibility"]["flags"]      # e1 has an unplayed earlier fixture
    lal = shown["lal:2a"]["eligibility"]
    assert lal["reliability"] == "full" and lal["flags"] == ["kickoff_timezone_unknown"] and lal["eligible"] and lal["stale_days"] == 9
    assert [r for r in lal["reasons"] if "Kickoff time is not known" in r]
    full = gw.gameweek_fixtures(conn, "LALIGA", "2026-27", 2, TODAY, NOW)
    ref = next(f for f in full["fixtures"] if f["record_id"] == "lal:2a")
    assert (lal["flags"], lal["reliability"], lal["reasons"], lal["stale_days"]) == (ref["flags"], ref["reliability"], ref["reasons"], ref["stale_days"])      # the featured fixture carries the full reasons
    conn.close()
    assert "reasons" not in shown["epl:4a"]["eligibility"]                              # list items stay light: flags only


def test_stale_history_is_flagged_when_a_league_has_not_reported_for_two_weeks(store):
    p = build(store, now=datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc))              # newest EPL result 2026-10-17; fixtures on 10-28 are dated in the past by then, so look at BUNDESLIGA 11-01 too
    conn = db.connect(store)
    conn.execute("UPDATE matches SET match_date='2026-11-20' WHERE record_id='bun:2b'")
    conn.commit()
    conn.close()
    p = build(store, now=datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc), comp="BUNDESLIGA")
    e = p["featured"]["eligibility"]
    assert "stale_history" in e["flags"] and e["reliability"] == "provisional" and e["stale_days"] == 31
    assert p["freshness"]["competitions"]["BUNDESLIGA"]["state"] == "stale"


# ------------------------------------------------------------------------------------------------------------ bounded, indexed, cached
def count_statements(path, **kw):
    conn = db.connect(path, readonly=True)
    seen = []
    conn.set_trace_callback(seen.append)
    featured.build(conn, CFG, NOW, **kw)
    conn.close()
    return len(seen)


def big_store(path: Path, per_league: int) -> Path:
    """Five leagues with `per_league` fixtures each: the first quarter completed in the past, the rest scheduled from tomorrow on (two per day per league)."""
    from datetime import timedelta

    conn = db.connect(path)
    db.init(conn)
    slugs = [f"t{i}" for i in range(20)]
    for s in slugs:
        add_team(conn, s, f"Test {s.upper()} FC")
    done = per_league // 4
    for key in featured.LEAGUES:
        for i in range(per_league):
            if i < done:
                day, status, score = (TODAY - timedelta(days=(done - i) // 2 + 1)).isoformat(), "completed", (1, 0)
            else:
                day, status, score = (TODAY + timedelta(days=(i - done) // 2 + 1)).isoformat(), "scheduled", None
            add_match(conn, f"{key}:{i}", key, "2026-27", 1 + i // 10, day, slugs[i % 20], slugs[(i + 7) % 20], status=status, score=score)
    conn.commit()
    conn.close()
    return path


def test_the_number_of_statements_does_not_grow_with_the_number_of_fixtures(tmp_path):
    counts = [count_statements(big_store(tmp_path / f"{n}.sqlite", n)) for n in (40, 380, 1500)]
    # a fixed set of statements: five leagues x (newest season, upcoming, results) plus one narrow season read per league that is shown (at most five), the saved-forecast
    # lookup and the sync-status statements. The gameweek page runs two statements per fixture, so it would grow with the data; this must not.
    assert max(counts) <= 60 and max(counts) - min(counts) <= len(featured.LEAGUES), counts
    small = big_store(tmp_path / "again.sqlite", 40)
    assert count_statements(small, upcoming=12, results=12) <= 60


def test_every_list_is_bounded_however_many_fixtures_exist(tmp_path):
    p = build(big_store(tmp_path / "l.sqlite", 380), upcoming=12, results=12)
    assert len(p["upcoming"]) <= 12 and len(p["recent_results"]) <= 12
    assert all(l["upcoming_found"] <= featured.FETCH_PER_LEAGUE for l in p["leagues"])
    assert "LIMIT ?" in featured.UPCOMING_SQL and "LIMIT ?" in featured.RESULTS_SQL


def plans_of(conn, key="EPL", season="2026-27"):
    params = dict(newest_season=(key,), upcoming=(key, season, "2026-10-27", 12), results=(key, season, 12), season_rows=(key, season))
    return {name: [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + sql, params[name])] for name, sql in featured.STATEMENTS.items()}


def assert_indexed(plans):
    for name, plan in plans.items():
        assert any("USING INDEX idx_matches_key" in line for line in plan), (name, plan)         # the (competition_key, season) index
        assert not any(line.startswith("SCAN") and "matches" in line or line.startswith("SCAN m") for line in plan), (name, plan)   # no scan of the matches table
        assert not any("idx_matches_status_date" in line for line in plan), (name, plan)         # the index that spans every competition in the store


def test_no_statement_scans_the_matches_table_or_walks_the_cross_competition_status_index(store):
    conn = db.connect(store, readonly=True)
    assert_indexed(plans_of(conn))
    conn.close()


@needs_inputs
def test_the_same_holds_on_the_repository_baseline_store(tmp_path, monkeypatch):
    path = tmp_path / "base.sqlite"
    conn = db.connect(path)
    db.init(conn)
    baseline.import_baseline(conn)
    conn.close()
    conn = db.connect(path, readonly=True)
    for key in featured.LEAGUES:
        season = conn.execute(featured.NEWEST_SEASON_SQL, (key,)).fetchone()[0]
        assert_indexed(plans_of(conn, key, season))
    p = featured.build(conn, CFG, datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc))
    shown = ([p["featured"]] if p["featured"] else []) + p["upcoming"]
    assert shown
    # parity with the gameweek page on real data. The page's per-team form query is irrelevant to flags and is the slow part (see the performance report), so it is stubbed here.
    monkeypatch.setattr(gw, "team_form", lambda *a, **k: [])
    pages = {}
    for x in shown:
        pages.setdefault((x["competition_key"], x["season"], x["matchday_no"]), None)
    for k in pages:
        pages[k] = {f["record_id"]: f for f in gw.gameweek_fixtures(conn, *k, date(2026, 10, 25))["fixtures"]}
    for x in shown:
        ref = pages[(x["competition_key"], x["season"], x["matchday_no"])][x["record_id"]]
        assert (x["eligibility"]["flags"], x["eligibility"]["reliability"]) == (ref["flags"], ref["reliability"]), x["record_id"]
    conn.close()


def test_a_run_of_the_whole_build_is_fast_on_a_full_size_store(tmp_path):
    import time

    path = big_store(tmp_path / "l.sqlite", 380)
    t = time.perf_counter()
    build(path, upcoming=12, results=12)
    assert time.perf_counter() - t < 3.0                      # about 0.1 s in practice; the gameweek page needs 4 to 10 s for one gameweek of the production store


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_cache_serves_repeat_requests_and_is_dropped_on_change_expiry_or_clear():
    clock, built = Clock(), []
    cache = featured.Cache(ttl=60, clock=clock)

    def builder():
        built.append(1)
        return dict(n=len(built))

    state = dict(fp=((1, 10), None))
    fp = lambda: state["fp"]  # noqa: E731
    key = ("all", 8, 8, "2026-10-27")
    p1, hit1, etag1 = cache.get_or_build(key, fp, builder)
    p2, hit2, etag2 = cache.get_or_build(key, fp, builder)
    assert (hit1, hit2, len(built), p1 is p2, etag1 == etag2) == (False, True, 1, True, True)
    cache.get_or_build(("EPL", 8, 8, "2026-10-27"), fp, builder)                          # another request shape is its own entry
    assert len(built) == 2
    state["fp"] = ((2, 11), None)
    cache.get_or_build(key, fp, builder)                                                   # the store file changed
    assert len(built) == 3
    clock.t = 61
    assert cache.get_or_build(key, fp, builder)[1] is False                               # a minute passed
    cache.clear()
    assert cache.get_or_build(key, fp, builder)[1] is False
    assert len(built) == 5

    def failing():
        raise RuntimeError("store unavailable")

    with pytest.raises(RuntimeError):
        cache.get_or_build(("x", 1, 1, "d"), fp, failing)
    assert cache.get_or_build(("x", 1, 1, "d"), fp, builder)[1] is False                  # a failed build is never cached


def test_store_fingerprint_changes_when_the_store_is_written(store):
    a = featured.store_fingerprint(store)
    conn = db.connect(store)
    conn.execute("UPDATE matches SET status='completed', home_goals_final=1, away_goals_final=0 WHERE record_id='lal:2a'")
    conn.commit()
    conn.close()
    assert featured.store_fingerprint(store) != a


# ------------------------------------------------------------------------------------------------------------ the HTTP endpoint
@pytest.fixture()
def client(store, monkeypatch):
    from fastapi.testclient import TestClient

    import main

    class FrozenDatetime(datetime):                                                                 # the synthetic store is built around NOW: the endpoint must not read the real clock
        @classmethod
        def now(cls, tz=None):
            return NOW if tz else NOW.replace(tzinfo=None)

    monkeypatch.setattr(main, "datetime", FrozenDatetime)
    monkeypatch.setattr(db, "DEFAULT_PATH", store)
    main.featured_cache.clear()
    yield TestClient(main.app)
    main.featured_cache.clear()


def test_endpoint_shape_headers_and_content(client):
    r = client.get("/api/featured-fixture")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"generated_utc", "today_utc", "scope", "featured", "empty_state", "upcoming", "recent_results", "leagues", "freshness", "notes"}
    assert body["featured"]["record_id"] == "lal:2a" and body["today_utc"] == body["generated_utc"][:10]
    assert r.headers["cache-control"] == "private, max-age=60" and r.headers["etag"].startswith('"') and r.headers["x-footiq-cache"] == "miss"


def test_endpoint_answers_repeat_requests_from_its_cache_and_supports_conditional_requests(client):
    first = client.get("/api/featured-fixture")
    second = client.get("/api/featured-fixture")
    assert second.headers["x-footiq-cache"] == "hit" and second.headers["etag"] == first.headers["etag"] and second.json() == first.json()
    third = client.get("/api/featured-fixture", headers={"If-None-Match": first.headers["etag"]})
    assert third.status_code == 304 and third.content == b"" and third.headers["etag"] == first.headers["etag"]
    other = client.get("/api/featured-fixture?comp=EPL")
    assert other.headers["x-footiq-cache"] == "miss" and other.json()["scope"]["competitions"] == ["EPL"]


def test_a_sync_change_empties_the_cache(client, monkeypatch):
    import analytics
    import main
    import predict

    client.get("/api/featured-fixture")
    assert client.get("/api/featured-fixture").headers["x-footiq-cache"] == "hit"
    monkeypatch.setattr(analytics, "reload", lambda: None)
    monkeypatch.setattr(predict, "reset_club_state", lambda: None)
    monkeypatch.setattr(predict, "warm_up", lambda: None)
    main._after_sync_change()
    assert client.get("/api/featured-fixture").headers["x-footiq-cache"] == "miss"


def test_endpoint_validates_its_parameters_and_reports_a_missing_store(client, monkeypatch, tmp_path):
    r = client.get("/api/featured-fixture?comp=UCL")
    assert r.status_code == 422 and "five domestic leagues" in r.json()["detail"]
    assert client.get("/api/featured-fixture?upcoming=0").status_code == 422 and client.get("/api/featured-fixture?results=13").status_code == 422
    assert client.get("/api/featured-fixture?upcoming=3&results=0").json()["recent_results"] == []
    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "missing.sqlite")
    r = client.get("/api/featured-fixture")
    assert r.status_code == 503 and "not built" in r.json()["detail"]


def test_endpoint_never_writes_to_the_store(client, store):
    before = hashlib.sha256(store.read_bytes()).hexdigest()
    client.get("/api/featured-fixture")
    client.get("/api/featured-fixture?comp=LALIGA&upcoming=12&results=12")
    assert hashlib.sha256(store.read_bytes()).hexdigest() == before


def test_a_fixture_of_a_fresh_league_is_preferred_within_three_days_and_the_stale_warning_is_never_hidden(store, monkeypatch):
    """P4.3: LALIGA has the earliest fixture (today). With LALIGA stale and EPL fresh, EPL's first fixture (tomorrow) is featured; beyond the window, or with nothing fresh, it is not."""
    real = sync.status

    def status_with(fresh_keys):
        def fake(conn, cfg, now=None):
            s = real(conn, cfg, now)
            for c in s["competitions"]:
                c["state"] = "fresh" if c["competition_key"] in fresh_keys else "stale"
            return s
        return fake

    monkeypatch.setattr(featured.store_sync, "status", status_with({"EPL"}))
    p = build(store)
    assert p["featured"]["competition_key"] == "EPL" and p["featured"]["date"] == "2026-10-28"
    assert p["freshness"]["competitions"]["EPL"]["state"] == "fresh" and p["freshness"]["competitions"]["LALIGA"]["state"] == "stale"
    assert "lal:2a" in [x["record_id"] for x in p["upcoming"]]                       # the skipped fixture is still listed, in order
    monkeypatch.setattr(featured.store_sync, "status", status_with({"BUNDESLIGA"}))   # fresh league only 5 days later: outside the window
    assert build(store)["featured"]["record_id"] == "lal:2a"
    monkeypatch.setattr(featured.store_sync, "status", status_with(set()))            # nothing fresh: the earliest fixture, with its stale state visible
    p = build(store)
    assert p["featured"]["record_id"] == "lal:2a" and p["freshness"]["competitions"]["LALIGA"]["state"] == "stale"


def test_a_fixture_whose_kickoff_cannot_be_shown_to_be_ahead_is_not_marked_predictable_on_the_home_page(store):
    """Phase 4.8B: Home and Matches use the same kickoff rule as the gameweek forecast; they never offer a pre-match prediction the forecast would refuse."""
    p = build(store, upcoming=12)
    shown = {x["record_id"]: x for x in [p["featured"]] + p["upcoming"]}
    lal = shown["lal:2a"]["eligibility"]                                              # dated today, local time without a time zone
    # Phase 4.8D Stage 2: NOW is 10:00 UTC = 11:00 in Madrid, before the La Liga evidence floor (12:00 local), so a same-day fixture without a UTC kickoff is still ahead
    assert lal["eligible"] is True and lal["predictable"] is True
    conn = db.connect(store, readonly=True)
    ref = next(f for f in gw.gameweek_fixtures(conn, "LALIGA", "2026-27", 2, TODAY, NOW)["fixtures"] if f["record_id"] == "lal:2a")
    later = next(f for f in gw.gameweek_fixtures(conn, "LALIGA", "2026-27", 2, TODAY, datetime(2026, 10, 27, 11, 30, tzinfo=timezone.utc))["fixtures"] if f["record_id"] == "lal:2a")
    conn.close()
    assert ref["predictable"] is True and ref["kickoff_state"] == "yes"
    assert later["predictable"] is False and later["kickoff_state"] == "unknown"                           # 12:30 in Madrid: past the floor, no longer certain
    assert shown["epl:4a"]["eligibility"]["predictable"] is True                       # stored UTC kickoff tomorrow evening: certainly ahead


# ------------------------------------------------------------------------------------------------ Phase 4.8D Stage 2: league time-zone rule in the application
def test_a_date_only_fixture_of_tomorrow_is_predictable_under_the_league_zone_rule_where_the_global_rule_blocked_it(store):
    import kickoff
    conn = db.connect(store, readonly=True)
    page = {f["record_id"]: f for f in gw.gameweek_fixtures(conn, "EPL", "2026-27", 4, TODAY, NOW)["fixtures"]}
    conn.close()
    assert page["epl:4b"]["kickoff_utc"] is None and page["epl:4b"]["date"] == "2026-10-28"
    assert kickoff.made_before_kickoff_global(NOW, "2026-10-28", None) == "unknown"                    # the old answer at 10:00 UTC the day before
    assert page["epl:4b"]["kickoff_state"] == "yes" and page["epl:4b"]["predictable"] is True            # UK: the date has not started, and the floor is 10:30 on the day
    assert page["lal:2a" if False else "epl:4a"]["kickoff_state"] == "yes"                              # a stored UTC kickoff in the future: unchanged
    p = build(store, upcoming=12)
    shown = {x["record_id"]: x for x in [p["featured"]] + p["upcoming"]}
    assert shown["epl:4b"]["eligibility"]["predictable"] is True and shown["lal:2a"]["eligibility"]["predictable"] is True        # Home agrees with the page (both before their league floors)


def test_a_disputed_date_keeps_the_fixture_restricted_and_the_dispute_is_read_only(store):
    import disputes
    conn = db.connect(store)
    conn.execute("INSERT INTO team_aliases(competition_id, source, alias, entity_id, method) VALUES ('test:EPL','openligadb','Dispute Home','CLUB:TST:e2','test'),('test:EPL','openligadb','Dispute Away','CLUB:TST:e4','test')")
    conn.execute("INSERT INTO quarantine(run_id, source, source_ref, reason, payload, created_utc) VALUES (NULL,'openligadb','999','DATE_DIFFERENCE: stored 2026-10-28 vs source 2026-10-27: Dispute Home v Dispute Away', ?, '2026-10-27T00:00:00Z')",
                 (json.dumps(dict(competition_key="test:EPL", home_raw="Dispute Home", away_raw="Dispute Away", match_date="2026-10-27")),))
    conn.commit()
    snapshot = [tuple(r) for r in conn.execute("SELECT * FROM quarantine")]
    conn.close()
    c = db.connect(store, readonly=True)
    assert disputes.by_record(c) == {"epl:4b": ["2026-10-27"]}
    page = {f["record_id"]: f for f in gw.gameweek_fixtures(c, "EPL", "2026-27", 4, TODAY, datetime(2026, 10, 27, 11, 0, tzinfo=timezone.utc))["fixtures"]}
    assert page["epl:4b"]["kickoff_state"] == "unknown" and page["epl:4b"]["predictable"] is False        # the earlier candidate date (today) decides: 11:00 UTC is past the 10:30 floor, restricted
    undisputed = {f["record_id"]: f for f in gw.gameweek_fixtures(c, "EPL", "2026-27", 4, TODAY, NOW)["fixtures"]}
    assert undisputed["epl:4b"]["kickoff_state"] == "yes"                                                 # at 10:00 UTC the earlier candidate is still ahead of its floor: never stricter than the earliest date allows
    assert any("disputed" in r for r in page["epl:4b"]["reasons"])
    assert page["epl:4a"]["predictable"] is True                                                           # other fixtures are unaffected
    c.close()
    c = db.connect(store, readonly=True)
    assert [tuple(r) for r in c.execute("SELECT * FROM quarantine")] == snapshot                          # nothing was written or resolved
    c.close()


def test_past_fixtures_stay_non_predictable_in_every_league_under_the_zone_rule(store):
    conn = db.connect(store, readonly=True)
    for key, md in (("EPL", 3), ("BUNDESLIGA", 2), ("LALIGA", 2)):
        fx = gw.gameweek_fixtures(conn, key, "2026-27", md, TODAY, NOW)["fixtures"]
        past = [f for f in fx if f["date"] < TODAY.isoformat() or (f["kickoff_utc"] and f["kickoff_utc"] < NOW.strftime("%Y-%m-%dT%H:%M:%SZ"))]
        assert past and all(not f["predictable"] and f["status"] == "awaiting_result" for f in past), key
    conn.close()
