"""P4.3 tests: GET /api/matches (Matches hub) and the kickoff / time-zone rules it shares with the Home endpoint. Read side only.

Synthetic stores of fictional clubs built from the real schema (the helpers of tests/test_featured.py), so every rule can be set up exactly. Nothing here makes a network request,
trains a model, calls the gameweek view's slow statement, or touches data/footiq.sqlite.
"""
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import featured  # noqa: E402
import gameweeks as gw  # noqa: E402
import matches  # noqa: E402
from store import db  # noqa: E402
from test_featured import CFG, NOW, TODAY, add_match, add_team, big_store, build_store  # noqa: E402,F401


@pytest.fixture()
def store(tmp_path):
    return build_store(tmp_path / "synthetic.sqlite")


def build(path, **kw):
    conn = db.connect(path, readonly=True)
    try:
        return matches.build(conn, CFG, kw.pop("now", NOW), **kw)
    finally:
        conn.close()


def ids(payload):
    return [x["record_id"] for x in payload["items"]]


# ------------------------------------------------------------------------------------------------------------ statuses and counts
def test_each_status_lists_exactly_the_matches_in_it(store):
    assert set(ids(build(store, status="upcoming", limit=50))) == {"epl:4a", "epl:4b", "epl:4c", "lal:2a", "lal:2c", "bun:2b"}
    assert set(ids(build(store, status="awaiting_result", limit=50))) == {"epl:3a", "lal:2b", "bun:2a"}
    assert set(ids(build(store, status="completed", limit=50))) == {"epl:1a", "epl:1b", "epl:2a", "lal:1a", "bun:1a", "ser:1a"}
    assert set(ids(build(store, status="other", limit=50))) == {"epl:4d", "epl:4e"}
    assert len(ids(build(store, status="all", limit=50))) == 17


def test_counts_are_the_size_of_each_status_for_the_chosen_leagues_season_and_matchday(store):
    assert build(store)["counts"] == dict(upcoming=6, awaiting_result=3, completed=6, other=2, all=17)
    assert build(store, comp="EPL")["counts"] == dict(upcoming=3, awaiting_result=1, completed=3, other=2, all=9)
    assert build(store, comp="EPL", matchday=4)["counts"] == dict(upcoming=3, awaiting_result=0, completed=0, other=2, all=5)
    assert build(store, comp="EPL", season="2025-26")["counts"] == dict(upcoming=0, awaiting_result=0, completed=1, other=0, all=1)


def test_a_stored_utc_kickoff_that_has_passed_is_awaiting_a_result_not_live_and_a_local_time_without_a_zone_never_is(store):
    early = build(store, now=datetime(2026, 10, 27, 8, 0, tzinfo=timezone.utc), status="all", limit=50)
    by = {x["record_id"]: x for x in early["items"]}
    assert by["lal:2b"]["status"] == "scheduled" and by["lal:2b"]["timing"]["phase"] == "today_before_kickoff"          # 09:00 UTC has not come yet at 08:00
    late = build(store, now=datetime(2026, 10, 27, 23, 0, tzinfo=timezone.utc), status="all", limit=50)
    by = {x["record_id"]: x for x in late["items"]}
    assert by["lal:2b"]["status"] == "awaiting_result" and by["lal:2b"]["timing"]["phase"] == "kickoff_passed" and by["lal:2b"]["timing"]["ambiguous"] is True
    assert by["lal:2c"]["status"] == "awaiting_result"                                                                      # 18:30 UTC has passed at 23:00
    assert by["lal:2a"]["status"] == "scheduled" and by["lal:2a"]["timing"]["phase"] == "today_time_zone_unconfirmed"      # 21:00 local, zone unknown: never classified by the clock
    assert all(x["status"] != "live" for p in (early, late) for x in p["items"])


def test_the_next_utc_day_turns_a_missed_result_into_a_passed_date(store):
    p = build(store, now=datetime(2026, 10, 28, 0, 5, tzinfo=timezone.utc), status="all", limit=50)
    by = {x["record_id"]: x for x in p["items"]}
    assert by["lal:2a"]["status"] == "awaiting_result" and by["lal:2a"]["timing"]["phase"] == "date_passed" and by["lal:2a"]["timing"]["ambiguous"] is False
    assert p["today_utc"] == "2026-10-28"


def test_a_stored_result_wins_over_any_clock(store):
    conn = db.connect(store)
    conn.execute("UPDATE matches SET status='completed', home_goals_final=2, away_goals_final=2, home_goals_90=2, away_goals_90=2 WHERE record_id='lal:2a'")
    conn.commit()
    conn.close()
    by = {x["record_id"]: x for x in build(store, status="all", limit=50)["items"]}
    assert by["lal:2a"]["status"] == "completed" and by["lal:2a"]["timing"]["phase"] == "result_stored"
    assert by["lal:2a"]["result"] == dict(home_goals=2, away_goals=2, source="fictional source")
    assert "lal:2a" not in ids(build(store, status="upcoming", limit=50))


# ------------------------------------------------------------------------------------------------------------ nothing is invented
def test_kickoffs_are_reported_exactly_as_stored_with_their_verification(store):
    by = {x["record_id"]: x for x in build(store, status="all", limit=50)["items"]}
    assert by["lal:2a"]["kickoff"] == dict(state="local_without_time_zone", utc=None, local="21:00", time_precision="local_unknown_tz", zone_verified=False)
    assert by["lal:2c"]["kickoff"] == dict(state="utc", utc="2026-10-27T18:30:00Z", local=None, time_precision="utc", zone_verified=True)
    assert by["epl:4b"]["kickoff"] == dict(state="unknown", utc=None, local=None, time_precision="date_only", zone_verified=False)


def test_timing_says_what_cannot_be_known_for_fixtures_dated_today(store):
    by = {x["record_id"]: x["timing"] for x in build(store, status="all", limit=50)["items"]}
    assert by["lal:2a"]["phase"] == "today_time_zone_unconfirmed" and by["lal:2a"]["ambiguous"] is True and "time zone" in by["lal:2a"]["note"]
    assert by["lal:2c"] == dict(phase="today_before_kickoff", ambiguous=False, note=None)
    assert by["epl:4a"]["phase"] == "future_date" and by["bun:2a"]["phase"] == "date_passed" and by["epl:1a"]["phase"] == "result_stored" and by["epl:4d"]["phase"] == "not_played"
    conn = db.connect(store)
    conn.execute("UPDATE matches SET kickoff_local=NULL WHERE record_id='lal:2a'")
    conn.commit()
    conn.close()
    unknown = {x["record_id"]: x["timing"] for x in build(store, status="all", limit=50)["items"]}["lal:2a"]
    assert unknown["phase"] == "today_time_unknown" and unknown["ambiguous"] is True


def test_every_item_is_a_stored_row_with_its_stored_values(store):
    p = build(store, status="all", limit=50)
    conn = db.connect(store, readonly=True)
    for x in p["items"]:
        row = conn.execute("SELECT * FROM matches WHERE record_id=?", (x["record_id"],)).fetchone()
        assert row["match_date"] == x["date"] and row["competition_key"] == x["competition_key"] and row["matchday_no"] == x["matchday_no"] and row["status"] == x["stored_status"]
        assert (x["kickoff"]["utc"], x["kickoff"]["local"]) == (row["kickoff_utc"], row["kickoff_local"])
        if x["result"]:
            assert (x["result"]["home_goals"], x["result"]["away_goals"]) == (row["home_goals_final"], row["away_goals_final"])
    conn.close()


def test_a_finished_match_without_a_stored_score_shows_no_score_rather_than_zero_zero(tmp_path):
    path = build_store(tmp_path / "s.sqlite")
    conn = db.connect(path)
    add_match(conn, "epl:odd", "EPL", "2026-27", 5, "2026-10-20", "e1", "e5", status="completed", score=None)
    conn.commit()
    conn.close()
    x = next(i for i in build(path, comp="EPL", status="completed", limit=50)["items"] if i["record_id"] == "epl:odd")
    assert x["result"] is None and x["result_missing"] is True


def test_results_carry_their_source_without_the_licence_suffix(store):
    x = next(i for i in build(store, status="completed", limit=50)["items"] if i["record_id"] == "bun:1a")
    assert x["result"] == dict(home_goals=2, away_goals=2, source="openligadb") and x["source"] == "openligadb"


# ------------------------------------------------------------------------------------------------------------ order, filters, facets
def test_default_order_is_ascending_for_upcoming_and_descending_otherwise_and_ascending_within_a_matchday(store):
    assert ids(build(store, status="upcoming", limit=50)) == ["lal:2a", "lal:2c", "epl:4b", "epl:4a", "epl:4c", "bun:2b"]
    assert ids(build(store, status="completed", limit=50)) == ["bun:1a", "ser:1a", "lal:1a", "epl:2a", "epl:1b", "epl:1a"]
    assert ids(build(store, status="awaiting_result", limit=50)) == ["lal:2b", "bun:2a", "epl:3a"]
    p = build(store, comp="EPL", matchday=4, status="all", limit=50)
    assert p["scope"]["order"] == "asc" and ids(p) == ["epl:4b", "epl:4a", "epl:4c", "epl:4d", "epl:4e"]
    assert ids(build(store, status="upcoming", order="desc", limit=50)) == ["bun:2b", "epl:4c", "epl:4a", "epl:4b", "lal:2c", "lal:2a"]


def test_league_season_and_matchday_filters(store):
    assert {i["competition_key"] for i in build(store, comp="EPL", status="all", limit=50)["items"]} == {"EPL"}
    p = build(store, comp="EPL", season="2025-26", status="all")
    assert ids(p) == ["epl:old"] and p["items"][0]["status"] == "completed" and p["scope"]["seasons"] == {"EPL": "2025-26"}
    assert {i["matchday_no"] for i in build(store, comp="EPL", matchday=1, status="all", limit=50)["items"]} == {1}
    assert build(store, comp="LIGUE1", status="all")["items"] == [] and build(store, comp="LIGUE1")["scope"]["seasons"] == {}
    with pytest.raises(matches.NotFound):
        build(store, comp="EPL", season="1999-00")
    with pytest.raises(matches.NotFound):
        build(store, season="1999-00")


def test_the_newest_season_of_each_league_is_the_default(store):
    p = build(store, status="all", limit=50)
    assert p["scope"]["seasons"] == {"EPL": "2026-27", "LALIGA": "2026-27", "BUNDESLIGA": "2026-27", "SERIEA": "2026-27"} and "epl:old" not in ids(p)


def test_facets_list_the_seasons_and_matchdays_of_the_selection(store):
    p = build(store, comp="EPL")
    assert {k: v for k, v in p["facets"].items() if k != "teams"} == dict(seasons=["2026-27", "2025-26"], matchdays=[1, 2, 3, 4])
    assert build(store, comp="LALIGA")["facets"]["matchdays"] == [1, 2]
    assert build(store)["facets"]["seasons"] == ["2026-27", "2025-26"] and build(store)["facets"]["matchdays"] == [1, 2, 3, 4]
    assert build(store)["facets"]["teams"] == []                                      # the teams facet belongs to one league-season


# ------------------------------------------------------------------------------------------------------------ eligibility, freshness, saved runs
def test_unplayed_matches_carry_the_gameweek_pages_eligibility_and_finished_ones_none(store, monkeypatch):
    p = build(store, status="all", limit=50)
    by = {x["record_id"]: x for x in p["items"]}
    assert by["epl:1a"]["eligibility"] is None and by["epl:4d"]["eligibility"] is None and by["epl:4a"]["eligibility"] is not None       # finished and postponed matches are not forecast candidates
    assert by["epl:4c"]["eligibility"]["eligible"] is False and by["epl:4c"]["eligibility"]["predictable"] is False        # a club the store could not match
    assert "kickoff_timezone_unknown" in by["lal:2a"]["eligibility"]["flags"] and "kickoff_time_unknown" in by["epl:4b"]["eligibility"]["flags"]
    monkeypatch.setattr(gw, "team_form", lambda *a, **k: [])
    conn = db.connect(store, readonly=True)
    for key, md in (("EPL", 4), ("LALIGA", 2), ("BUNDESLIGA", 2)):
        page = {f["record_id"]: f for f in gw.gameweek_fixtures(conn, key, "2026-27", md, TODAY)["fixtures"]}
        for rid, f in page.items():
            if rid in by and by[rid]["eligibility"] and f["predictable"]:
                assert (by[rid]["eligibility"]["flags"], by[rid]["eligibility"]["reliability"]) == (f["flags"], f["reliability"]), rid
    conn.close()


def test_freshness_is_the_sync_status_of_each_league(store):
    from store import sync

    p = build(store)
    conn = db.connect(store, readonly=True)
    status = sync.status(conn, CFG, NOW)
    conn.close()
    for c in status["competitions"]:
        if c["competition_key"] in featured.LEAGUES:
            assert p["freshness"]["competitions"][c["competition_key"]]["state"] == c["state"]
    assert p["freshness"]["live_enabled"] is False


def test_saved_forecast_runs_of_the_gameweek_are_counted_never_computed(store):
    conn = db.connect(store)
    for n in range(2):
        conn.execute("INSERT INTO forecast_runs(created_utc, competition_key, season, matchday_label, model_id, model_artifact_sha256, data_cutoff_date, data_cutoff_note, user_action, notes) "
                     "VALUES (?, 'EPL', '2026-27', 'Matchday 4', ?, ?, '2026-10-18', 'test', 'predict_gameweek_button', 'test run')", (f"2026-10-26T09:0{n}:00Z", json.dumps({}), json.dumps({})))
    conn.commit()
    conn.close()
    by = {x["record_id"]: x for x in build(store, status="all", limit=50)["items"]}
    assert by["epl:4a"]["saved_forecast_runs"] == 2 and by["epl:1a"]["saved_forecast_runs"] == 0 and by["lal:2a"]["saved_forecast_runs"] == 0


def test_nothing_is_computed_saved_or_written(store, monkeypatch):
    import forecast
    import predict

    def boom(*a, **k):
        raise AssertionError("the matches endpoint must not compute a forecast")

    for mod, names in ((predict, ("predict", "club_features_fast", "_club_state", "_club_models", "warm_up")), (forecast, ("predict_gameweek",)), (gw, ("gameweek_fixtures", "team_form"))):
        for n in names:
            monkeypatch.setattr(mod, n, boom, raising=False)
    src = (APP / "matches.py").read_text(encoding="utf-8")
    assert "import predict" not in src and "import forecast" not in src and "gameweek_fixtures" not in src and "team_form" not in src
    before = hashlib.sha256(store.read_bytes()).hexdigest()
    for status in matches.STATUSES:
        build(store, status=status, limit=50)
    assert hashlib.sha256(store.read_bytes()).hexdigest() == before


# ------------------------------------------------------------------------------------------------------------ pagination
def walk(path, **kw):
    out, cursor, pages = [], None, 0
    while True:
        p = build(path, cursor=cursor, **kw)
        out += p["items"]
        pages += 1
        assert len(p["items"]) <= kw.get("limit", matches.DEFAULT_LIMIT) and p["page"]["returned"] == len(p["items"])
        cursor = p["page"]["next_cursor"]
        assert (cursor is not None) == p["page"]["has_more"]
        if not cursor:
            return out, pages


@pytest.mark.parametrize("status,order", [("upcoming", None), ("upcoming", "desc"), ("completed", None), ("completed", "asc"), ("all", None), ("all", "asc")])
def test_paging_visits_every_match_once_in_order_across_leagues_with_ties(tmp_path, status, order):
    path = big_store(tmp_path / "big.sqlite", 120)
    whole = build(path, status=status, order=order, limit=50)
    out, pages = walk(path, status=status, order=order, limit=17)
    keys = [(x["date"], x["kickoff"]["utc"] or "", featured.LEAGUES.index(x["competition_key"]), x["record_id"]) for x in out]
    assert len(keys) == len(set(keys)) == whole["counts"][status] and pages == -(-whole["counts"][status] // 17)
    assert keys == sorted(keys, reverse=(whole["scope"]["order"] == "desc"))
    assert [x["record_id"] for x in out][:50] == ids(whole)                                             # a long walk agrees with one big page


def test_a_deep_page_costs_the_same_number_of_statements_as_the_first(tmp_path):
    path = big_store(tmp_path / "big.sqlite", 380)
    first = build(path, status="upcoming", limit=25)
    cursor, last = first["page"]["next_cursor"], first
    for _ in range(20):
        last = build(path, status="upcoming", limit=25, cursor=cursor)
        cursor = last["page"]["next_cursor"]
    conn = db.connect(path, readonly=True)
    seen = []
    conn.set_trace_callback(seen.append)
    matches.build(conn, CFG, NOW, status="upcoming", limit=25, cursor=cursor)
    conn.close()
    conn = db.connect(path, readonly=True)
    seen_first = []
    conn.set_trace_callback(seen_first.append)
    matches.build(conn, CFG, NOW, status="upcoming", limit=25)
    conn.close()
    assert abs(len(seen) - len(seen_first)) <= 5


def test_the_last_page_has_no_cursor_and_an_empty_selection_is_an_empty_page(store):
    p = build(store, status="completed", limit=50)
    assert p["page"] == dict(limit=50, returned=6, has_more=False, next_cursor=None)
    e = build(store, comp="LIGUE1", status="all")
    assert e["items"] == [] and e["page"]["has_more"] is False and e["counts"]["all"] == 0


@pytest.mark.parametrize("bad", ["", "not-base64!!", "e30", "W10", "WyIyMDI2LTEwLTI3IiwiIiw5LCJ4Il0", "WyJub3QtYS1kYXRlIiwiIiwwLCJ4Il0"])
def test_a_cursor_that_is_not_one_of_ours_is_refused(store, bad):
    with pytest.raises(matches.MatchesError):
        build(store, cursor=bad or "x")


def test_requests_outside_the_bounds_are_refused(store):
    for kw in (dict(comp="UEL"), dict(status="live"), dict(limit=0), dict(limit=matches.MAX_LIMIT + 1), dict(matchday=0), dict(matchday=matches.MAX_MATCHDAY + 1), dict(season="2026"), dict(order="sideways")):
        with pytest.raises(matches.MatchesError):
            build(store, **kw)


# ------------------------------------------------------------------------------------------------------------ bounded and indexed
def count_statements(path, **kw):
    conn = db.connect(path, readonly=True)
    seen = []
    conn.set_trace_callback(seen.append)
    matches.build(conn, CFG, NOW, **kw)
    conn.close()
    return len(seen)


def test_the_number_of_statements_does_not_grow_with_the_number_of_matches(tmp_path):
    counts = [count_statements(big_store(tmp_path / f"{n}.sqlite", n), status="upcoming", limit=50) for n in (40, 380, 1500)]
    assert max(counts) <= 90 and max(counts) - min(counts) <= 2 * len(featured.LEAGUES), counts


def test_every_statement_is_anchored_on_the_competition_season_index_and_never_scans_or_uses_the_status_index(tmp_path):
    path = big_store(tmp_path / "plans.sqlite", 120)
    conn = db.connect(path, readonly=True)
    cursor = ("2026-10-30", "", 1, "x")
    statements = []
    for status in matches.STATUSES:
        for order in matches.ORDERS:
            for md in (None, 3):
                for cur in (None, cursor):
                    for league in (0, 1, 4):
                        sql, args = matches.page_query("EPL", "2026-27", md, status, order, cur, league, "2026-10-27", "2026-10-27T10:00:00Z", 26)
                        assert "LIMIT ?" in sql and args[-1] == 26
                        statements.append((sql, args))
    statements += [(matches.COUNTS_SQL.replace("{matchday}", ""), ("2026-10-27", "2026-10-27", "x", "EPL", "2026-27")), (matches.COUNTS_SQL.replace("{matchday}", " AND m.matchday_no=?"), ("2026-10-27", "2026-10-27", "x", "EPL", "2026-27", 3)),
                   (matches.MATCHDAYS_SQL, ("EPL", "2026-27")), (matches.SEASONS_SQL, ("EPL",)), (featured.SEASON_SQL, ("EPL", "2026-27"))]
    for sql, args in statements:
        plan = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + sql, args)]
        assert any("idx_matches_key" in line for line in plan), (sql[:90], plan)
        assert not any(line.startswith("SCAN") and "matches" in line or line.startswith("SCAN m") for line in plan), (sql[:90], plan)
        assert not any("idx_matches_status_date" in line for line in plan), (sql[:90], plan)
    conn.close()


def test_a_page_of_a_full_size_store_is_built_quickly(tmp_path):
    import time

    path = big_store(tmp_path / "full.sqlite", 380)
    t = time.perf_counter()
    build(path, status="upcoming", limit=50)
    build(path, status="all", limit=50, order="desc")
    assert time.perf_counter() - t < 3.0                  # tens of milliseconds in practice; the gameweek page needs seconds for one gameweek of the production store


# ------------------------------------------------------------------------------------------------------------ the HTTP endpoint
@pytest.fixture()
def client(store, monkeypatch):
    from fastapi.testclient import TestClient

    import main

    monkeypatch.setattr(db, "DEFAULT_PATH", store)
    main.matches_cache.clear()
    yield TestClient(main.app)
    main.matches_cache.clear()


def test_endpoint_shape_headers_and_paging_over_http(client):
    r = client.get("/api/matches?status=all&limit=4")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"generated_utc", "today_utc", "scope", "counts", "items", "page", "facets", "freshness", "notes"}
    assert r.headers["cache-control"] == "private, max-age=60" and r.headers["etag"].startswith('"') and r.headers["x-footiq-cache"] == "miss"
    seen = [x["record_id"] for x in body["items"]]
    cursor = body["page"]["next_cursor"]
    while cursor:
        page = client.get(f"/api/matches?status=all&limit=4&cursor={cursor}").json()
        seen += [x["record_id"] for x in page["items"]]
        cursor = page["page"]["next_cursor"]
    assert len(seen) == len(set(seen)) == 17


def test_endpoint_cache_and_conditional_requests(client):
    first = client.get("/api/matches?comp=EPL")
    second = client.get("/api/matches?comp=EPL")
    assert second.headers["x-footiq-cache"] == "hit" and second.headers["etag"] == first.headers["etag"] and second.json() == first.json()
    third = client.get("/api/matches?comp=EPL", headers={"If-None-Match": first.headers["etag"]})
    assert third.status_code == 304 and third.content == b""
    assert client.get("/api/matches?comp=LALIGA").headers["x-footiq-cache"] == "miss"


def test_a_sync_change_empties_the_matches_cache(client, monkeypatch):
    import analytics
    import main
    import predict

    client.get("/api/matches")
    assert client.get("/api/matches").headers["x-footiq-cache"] == "hit"
    monkeypatch.setattr(analytics, "reload", lambda: None)
    monkeypatch.setattr(predict, "reset_club_state", lambda: None)
    monkeypatch.setattr(predict, "warm_up", lambda: None)
    main._after_sync_change()
    assert client.get("/api/matches").headers["x-footiq-cache"] == "miss"


def test_endpoint_validation_unknown_season_and_missing_store(client, monkeypatch, tmp_path):
    for q in ("comp=UEL", "status=live", "limit=0", "limit=51", "matchday=0", "matchday=61", "season=2026", "order=up", "cursor=garbage"):
        r = client.get(f"/api/matches?{q}")
        assert r.status_code == 422 and r.json()["detail"], q
    assert client.get("/api/matches?comp=EPL&season=1999-00").status_code == 404
    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "missing.sqlite")
    r = client.get("/api/matches")
    assert r.status_code == 503 and "not built" in r.json()["detail"]


def test_endpoint_never_writes_to_the_store(client, store):
    before = hashlib.sha256(store.read_bytes()).hexdigest()
    for q in ("", "?comp=LALIGA&status=all&limit=50", "?status=completed&order=asc", "?comp=EPL&matchday=4&status=all"):
        client.get("/api/matches" + q)
    assert hashlib.sha256(store.read_bytes()).hexdigest() == before


# ------------------------------------------------------------------------------------------------------------ the Champions League in the hub (Phase 4.20)
def ucl_store(tmp_path):
    """The domestic synthetic store plus a Champions League 2026-27 league phase as the real rows are stored: stage 'Matches > Matchday N', no matchday number, wikipedia source."""
    path = build_store(tmp_path / "ucl.sqlite")
    conn = db.connect(path)
    for slug in ("u1", "u2", "u3", "u4"):
        add_team(conn, slug, f"Test {slug.upper()} FC")
    rows = [("ucl:1a", 1, "2026-09-09", "u1", "u2", "completed", (2, 0)), ("ucl:1b", 1, "2026-09-09", "u3", "u4", "completed", (1, 1)), ("ucl:2a", 2, "2026-10-14", "u1", "u3", "completed", (0, 3)),
            ("ucl:2b", 2, "2026-10-14", "u2", "u4", "completed", (2, 2)), ("ucl:3a", 3, "2026-10-21", "u1", "u4", "scheduled", None),                           # dated in the past, no result yet
            ("ucl:3b", 3, "2026-10-21", "u2", "u3", "scheduled", None), ("ucl:11a", 11, "2026-12-09", "u1", "u2", "scheduled", None)]
    for rid, md, day, h, a, status, score in rows:
        add_match(conn, rid, "UCL", "2026-27", md, day, h, a, status=status, score=score, source="wikipedia")
    conn.execute("UPDATE matches SET matchday_no=NULL, matchday_label='Matches > Matchday ' || substr(matchday_label, 10) WHERE competition_key='UCL'")
    conn.commit()
    conn.close()
    return path


def test_the_champions_league_is_listed_with_a_matchday_taken_from_its_stage_label(tmp_path):
    path = ucl_store(tmp_path)
    p = build(path, comp="UCL", status="all", limit=50)
    assert p["scope"]["competitions"] == ["UCL"] and p["counts"] == dict(upcoming=1, awaiting_result=2, completed=4, other=0, all=7)
    by = {i["record_id"]: i for i in p["items"]}
    assert by["ucl:2a"]["matchday_no"] == 2 and by["ucl:11a"]["matchday_no"] == 11 and by["ucl:2a"]["matchday_label"] == "Matches > Matchday 2"
    assert by["ucl:2a"]["result"] == dict(home_goals=0, away_goals=3, source="wikipedia")
    assert {i["validation_badge"] for i in p["items"]} == {"Not validated (indicative only)"}
    assert build(path, status="all", limit=50)["scope"]["competitions"] == ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"]


def test_the_matchday_filter_and_facet_work_for_the_champions_league_and_do_not_confuse_1_with_11(tmp_path):
    path = ucl_store(tmp_path)
    assert build(path, comp="UCL")["facets"]["matchdays"] == [1, 2, 3, 11]
    assert ids(build(path, comp="UCL", matchday=1, status="all")) == ["ucl:1b", "ucl:1a"] or sorted(ids(build(path, comp="UCL", matchday=1, status="all"))) == ["ucl:1a", "ucl:1b"]
    p = build(path, comp="UCL", matchday=11, status="all")
    assert ids(p) == ["ucl:11a"] and p["counts"]["all"] == 1
    assert build(path, comp="UCL", matchday=3, status="awaiting_result")["counts"]["awaiting_result"] == 2


def test_the_team_filter_restricts_rows_and_counts_and_needs_a_league(tmp_path):
    path = ucl_store(tmp_path)
    p = build(path, comp="UCL", status="all", team="CLUB:TST:u4", limit=50)
    assert sorted(ids(p)) == ["ucl:1b", "ucl:2b", "ucl:3a"] and p["counts"]["all"] == 3 and p["scope"]["team"] == "CLUB:TST:u4"
    assert [t["entity"] for t in build(path, comp="UCL")["facets"]["teams"]] == ["CLUB:TST:u1", "CLUB:TST:u2", "CLUB:TST:u3", "CLUB:TST:u4"]
    epl = build(path, comp="EPL", status="all", team="CLUB:TST:e1", limit=50)
    assert epl["counts"]["all"] == len(epl["items"]) > 0 and all("CLUB:TST:e1" in (i["home"]["entity"], i["away"]["entity"]) for i in epl["items"])
    for kw in (dict(team="CLUB:TST:u4"), dict(comp="UCL", team="x;drop table"), dict(comp="UCL", team="a")):
        with pytest.raises(matches.MatchesError):
            build(path, **kw)
    with pytest.raises(matches.MatchesError):
        build(path, comp="UEL")                                                       # an archived competition is not a hub competition


def test_champions_league_rows_carry_no_gameweek_eligibility_and_the_freshness_has_an_entry(tmp_path):
    path = ucl_store(tmp_path)
    p = build(path, comp="UCL", status="awaiting_result", limit=50)
    assert [i["eligibility"] for i in p["items"]] == [None, None]                         # the gameweek rules are domestic-only
    fresh = p["freshness"]["competitions"]["UCL"]
    assert fresh["latest_result"] == "2026-10-14" and fresh["approved_sources"] == [] and fresh["state"] != "fresh"
    assert "UCL" in build(path)["freshness"]["competitions"] and set(build(path)["freshness"]["competitions"]) == {"EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"}


def test_the_champions_league_adds_a_fixed_number_of_statements(tmp_path):
    path = ucl_store(tmp_path)
    counts = []
    for kw in (dict(comp="UCL", status="all"), dict(comp="UCL", status="all", team="CLUB:TST:u1"), dict(comp="UCL", status="completed", matchday=2)):
        conn = db.connect(path, readonly=True)
        seen = []
        conn.set_trace_callback(seen.append)
        matches.build(conn, CFG, NOW, **kw)
        conn.close()
        counts.append(len([x for x in seen if x.lstrip().upper().startswith("SELECT")]))
    assert max(counts) - min(counts) <= 1 and max(counts) < 20
