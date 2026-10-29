"""P4.3 tests: gameweeks.team_form uses the (competition, season, date) index (variant B of docs/mini-project/phase4/P4_2_PERFORMANCE_INVESTIGATION.md).

The statement was planned on the store-wide (status, match_date) index and walked every completed match of every competition for each call. The hint changes the plan, not the result:
REFERENCE_SQL below is the statement as it was before, and every case here must return exactly what it returns. Performance is checked by work done (VM steps counted by SQLite,
the same on any machine) and by the query plan, with only a generous wall-clock bound, so the test does not depend on how busy the machine is.
"""
import sys
import time
from datetime import timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gameweeks as gw  # noqa: E402
from store import db  # noqa: E402
from test_featured import add_match, add_team, ent  # noqa: E402

REFERENCE_SQL = (
    "SELECT m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final, t1.display_name AS hn, t2.display_name AS an FROM matches m "
    "LEFT JOIN teams t1 ON t1.entity_id=m.home_entity_id LEFT JOIN teams t2 ON t2.entity_id=m.away_entity_id "
    "WHERE m.competition_id=? AND (m.home_entity_id=? OR m.away_entity_id=?) AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL "
    "ORDER BY m.match_date DESC, m.record_id DESC LIMIT ?")


def reference_form(conn, competition_id, entity, before_date, n=5):
    rows = conn.execute(REFERENCE_SQL, (competition_id, entity, entity, before_date, n)).fetchall()
    out = []
    for r in reversed(rows):
        home = r["home_entity_id"] == entity
        gf, ga = (r["home_goals_final"], r["away_goals_final"]) if home else (r["away_goals_final"], r["home_goals_final"])
        out.append(dict(date=r["match_date"], opponent=(r["an"] if home else r["hn"]), venue="H" if home else "A", gf=gf, ga=ga, result="W" if gf > ga else "D" if gf == ga else "L"))
    return out


def build(path: Path, noise: int = 0) -> Path:
    """EPL with every kind of row team_form must treat correctly, plus `noise` completed matches of other competitions (what made the old plan slow)."""
    conn = db.connect(path)
    db.init(conn)
    for s in ("a", "b", "c", "d", "n"):
        add_team(conn, s, f"Test {s.upper()} FC")
    day = lambda n: (__import__("datetime").date(2026, 9, 1) + timedelta(days=n)).isoformat()  # noqa: E731
    m = lambda *a, **k: add_match(conn, *a, **k)  # noqa: E731
    for i in range(7):                                                              # seven completed results for a, alternating home and away
        m(f"epl:r{i}", "EPL", "2026-27", 1 + i, day(i), "a" if i % 2 == 0 else "b", "b" if i % 2 == 0 else "a", status="completed", score=(i % 3, 1))
    m("epl:tie1", "EPL", "2026-27", 8, day(10), "a", "c", status="completed", score=(2, 2))     # two results on one day: the higher record id is the later one
    m("epl:tie2", "EPL", "2026-27", 8, day(10), "d", "a", status="completed", score=(0, 1))
    m("epl:award", "EPL", "2026-27", 9, day(11), "a", "d", status="awarded", score=(3, 0))
    m("epl:sched", "EPL", "2026-27", 9, day(12), "a", "b")                                       # never played: not form
    m("epl:await", "EPL", "2026-27", 9, day(12), "a", "c", status="awaiting_result")
    m("epl:post", "EPL", "2026-27", 9, day(12), "a", "d", status="postponed")
    m("epl:canc", "EPL", "2026-27", 9, day(12), "a", "b", status="cancelled")
    m("epl:aband", "EPL", "2026-27", 9, day(12), "a", "c", status="abandoned", score=(1, 0))
    m("epl:nogoal", "EPL", "2026-27", 9, day(12), "a", "d", status="completed", score=None)      # finished but no stored score: not form
    m("epl:same", "EPL", "2026-27", 10, day(20), "a", "b", status="completed", score=(5, 0))     # on the cutoff day itself
    m("epl:later", "EPL", "2026-27", 11, day(30), "a", "c", status="completed", score=(4, 4))    # after the cutoff: future data
    m("epl:unmatched", "EPL", "2026-27", 10, day(13), "a", "b", status="completed", score=(1, 1), home_resolved=False)
    m("lal:other", "LALIGA", "2026-27", 1, day(5), "a", "b", status="completed", score=(9, 9))   # the same clubs in another competition: not form
    for i in range(noise):
        m(f"noise:{i}", "LIGUE1", "2025-26", 1 + i % 38, day(-400 + i % 300), "c" if i % 2 else "d", "n", status="completed", score=(1, 0))
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def store(tmp_path):
    return build(tmp_path / "form.sqlite")


START = __import__("datetime").date(2026, 9, 1)


def cases(conn):
    """(competition id of the synthetic EPL, every entity incl. an unmatched one, cutoffs from before the first result to long after the last)."""
    return "test:EPL", [ent(s) for s in ("a", "b", "c", "d", "n")] + [None], [(START + timedelta(days=n)).isoformat() for n in (-5, 0, 1, 3, 6, 7, 10, 11, 12, 13, 20, 21, 30, 31, 60)]


def test_the_hinted_statement_returns_exactly_what_the_reference_statement_returns(store):
    conn = db.connect(store, readonly=True)
    cid, entities, dates = cases(conn)
    compared = 0
    for entity in entities:
        for before in dates:
            for n in (1, 5, 10):
                assert gw.team_form(conn, cid, entity, before, n) == reference_form(conn, cid, entity, before, n), (entity, before, n)
                compared += 1
    assert compared == 6 * 15 * 3
    conn.close()


def test_form_is_the_last_results_of_the_team_in_this_competition_strictly_before_the_cutoff(store):
    conn = db.connect(store, readonly=True)
    cid, _, _ = cases(conn)
    form = gw.team_form(conn, cid, ent("a"), "2026-09-21")                          # day 20 (a 5-0 result) is the cutoff day itself: excluded
    assert [f["date"] for f in form] == ["2026-09-06", "2026-09-07", "2026-09-11", "2026-09-11", "2026-09-12"]
    assert [f["result"] for f in form][-3:] == ["D", "W", "W"]                       # 2-2 at home, then 1-0 away at d, then the 3-0 award at home
    assert [f["venue"] for f in form][-3:] == ["H", "A", "H"]
    assert [f["date"] for f in gw.team_form(conn, cid, ent("a"), "2026-09-11", 3)] == ["2026-09-05", "2026-09-06", "2026-09-07"]   # earlier cutoff: nothing from day 10 on
    conn.close()


def test_unplayed_postponed_cancelled_abandoned_unscored_other_competition_and_future_rows_are_never_form(store):
    conn = db.connect(store, readonly=True)
    cid, _, _ = cases(conn)
    everything = gw.team_form(conn, cid, ent("a"), "2026-12-31", 50)
    # seven results, two on the same day, the award, day 20 and day 30: twelve. Not in it: scheduled, awaiting, postponed, cancelled, abandoned, the unscored one,
    # the row whose club is unmatched, and the 9-9 of the same clubs in another competition.
    assert len(everything) == 12 and (9, 9) not in {(r["gf"], r["ga"]) for r in everything}
    assert gw.team_form(conn, cid, None, "2026-12-31") == [] and gw.team_form(conn, cid, ent("n"), "2026-12-31") == []
    assert gw.team_form(conn, cid, ent("a"), "2026-09-01") == []                    # no history before the first result: an empty form, not an error
    conn.close()


def test_a_cutoff_earlier_than_a_result_never_lets_that_result_in(store):
    conn = db.connect(store, readonly=True)
    cid, _, _ = cases(conn)
    for day_no in range(0, 32):
        cutoff = (__import__("datetime").date(2026, 9, 1) + timedelta(days=day_no)).isoformat()
        assert all(f["date"] < cutoff for f in gw.team_form(conn, cid, ent("a"), cutoff, 50)), cutoff
    conn.close()


def test_the_plan_uses_the_competition_season_index_and_not_the_store_wide_status_index(store):
    conn = db.connect(store, readonly=True)
    sql = gw.TEAM_FORM_SQL
    plan = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + sql, ("c", "e", "e", "2026-01-01", 5))]
    assert any("idx_matches_comp_season_date" in line for line in plan), plan
    assert not any("idx_matches_status_date" in line for line in plan), plan
    ref = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + REFERENCE_SQL, ("c", "e", "e", "2026-01-01", 5))]
    assert gw.TEAM_FORM_SQL.replace(" INDEXED BY idx_matches_comp_season_date", "") == REFERENCE_SQL and ref                        # the only change is the hint
    conn.close()


def vm_steps(conn, fn, every=100):
    steps = [0]

    def tick():
        steps[0] += 1
        return 0

    conn.set_progress_handler(tick, every)
    fn()
    conn.set_progress_handler(None, 0)
    return steps[0] * every


def test_the_work_done_does_not_grow_with_the_other_competitions_in_the_store(tmp_path):
    """Environment-independent performance guard: SQLite's own count of virtual-machine steps. The reference statement does work proportional to ALL completed matches in the store."""
    path = build(tmp_path / "noisy.sqlite", noise=30000)
    conn = db.connect(path, readonly=True)
    cid, _, _ = cases(conn)
    new = vm_steps(conn, lambda: [gw.team_form(conn, cid, ent("a"), "2026-12-31") for _ in range(5)])
    old = vm_steps(conn, lambda: [reference_form(conn, cid, ent("a"), "2026-12-31") for _ in range(5)])
    assert new < 20_000, new                                  # a few dozen rows of this competition
    assert old > 20 * new, (old, new)                         # the reference walked the 30,000 other rows every time
    conn.close()


def test_a_gameweek_of_ten_fixtures_builds_quickly_on_a_store_with_many_other_matches(tmp_path):
    path = build(tmp_path / "noisy.sqlite", noise=30000)
    conn = db.connect(path, readonly=True)
    cid, _, _ = cases(conn)
    t = time.perf_counter()
    for _ in range(20):                                       # two calls per fixture, ten fixtures
        gw.team_form(conn, cid, ent("a"), "2026-10-01")
    assert time.perf_counter() - t < 2.0                      # milliseconds in practice; the reference needs seconds on a store this size on a quiet machine
    conn.close()


def test_a_store_without_the_index_still_answers_with_the_same_result(store):
    conn = db.connect(store)
    cid, _, _ = cases(conn)
    expected = reference_form(conn, cid, ent("a"), "2026-12-31")
    conn.execute("DROP INDEX idx_matches_comp_season_date")
    assert gw.team_form(conn, cid, ent("a"), "2026-12-31") == expected
    conn.close()
