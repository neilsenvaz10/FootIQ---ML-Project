"""Phase 4.19: the offline Champions League 2026-27 import (app/store/uefa_import.py). Pure functions plus runs against a small throw-away store; the production store is never written.

Run:  .venv\\Scripts\\python.exe -X utf8 -m pytest tests/test_uefa_import.py -q
"""
import hashlib
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

import config as C  # noqa: E402
import uefa_league_phase as LP  # noqa: E402
from store import db as store_db  # noqa: E402
from store import uefa_import as U  # noqa: E402

needs_staging = pytest.mark.skipif(not (U.STAGING.exists() and U.GATE.exists()), reason="Phase 4.17/4.19 staging files missing")


@pytest.fixture(scope="module")
def staging():
    return U.load_staging()


@pytest.fixture(scope="module")
def entities(staging):
    return set(staging.home_entity) | set(staging.away_entity)


@pytest.fixture()
def store(tmp_path, entities):
    """An empty store with the real schema and the 36 clubs, plus the 18 matchday-1 rows exactly as production holds them."""
    p = tmp_path / "t.sqlite"
    conn = store_db.connect(p)
    store_db.init(conn)
    conn.executemany("INSERT INTO teams(entity_id, display_name, country) VALUES (?,?,?)", [(e, e, None) for e in sorted(entities)])
    st = U.load_staging()
    md1 = [U.build_row(dict(matchday=int(r.matchday), date=str(r.date), home=r.home, away=r.away, home_entity=r.home_entity, away_entity=r.away_entity, hg=int(r.home_goals), ag=int(r.away_goals)), 1, "completed")
           for r in st[st.matchday == 1].itertuples()]
    ts = "2026-10-25T00:00:00Z"
    from store import baseline as B
    B.upsert_matches(conn, md1, ts)
    conn.commit()
    conn.close()
    return p


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def known_df(**kw):
    base = dict(competition_key="UCL", season="2026-27", matchday=1, date="2026-09-08", home="A", away="B", home_entity="E:A", away_entity="E:B", home_goals=1.0, away_goals=0.0, status="played", page_revid=1)
    base.update(kw)
    return pd.DataFrame([base])


# ---------------------------------------------------------------- data validation
@needs_staging
def test_the_staged_file_is_a_valid_36_team_league_phase(staging, entities):
    issues, bad = U.validate(staging, entities)
    assert issues == [] and not bad
    assert len(staging) == 144 and len(entities) == 36
    assert (pd.concat([staging.home_entity, staging.away_entity]).value_counts() == 8).all()                     # every club plays 8
    assert (staging.groupby("home_entity").size() == 4).all()                                                    # 4 at home, 4 away


@pytest.mark.parametrize("kw, code", [
    (dict(home_entity=None), "missing_team_identifier"),
    (dict(home_entity="E:UNKNOWN"), "unknown_team_identifier"),
    (dict(away_entity="E:A"), "home_equals_away"),
    (dict(date="2026-9-8"), "bad_date"),
    (dict(date="2025-09-08"), "date_outside_season"),
    (dict(status="postponed"), "bad_status"),
    (dict(home_goals=float("nan")), "played_without_score"),
    (dict(home_goals=-1.0), "implausible_score"),
    (dict(home_goals=13.0), "implausible_score"),
    (dict(home_goals=1.5), "implausible_score"),
    (dict(status="scheduled"), "scheduled_with_score"),
])
def test_validation_flags_each_kind_of_bad_row(kw, code):
    issues, bad = U.validate(known_df(**kw), {"E:A", "E:B"})
    assert code in {i["code"] for i in issues} and 0 in bad


def test_duplicate_and_reversed_rows_in_the_file_are_flagged():
    d = pd.concat([known_df(), known_df(), known_df(home_entity="E:B", away_entity="E:A", home="B", away="A")], ignore_index=True)
    codes = {i["code"] for i in U.validate(d, {"E:A", "E:B"})[0]}
    assert {"duplicate_in_file", "reversed_pairing_in_file"} <= codes


# ---------------------------------------------------------------- the verified gate and duplicate detection
@needs_staging
def test_the_gate_holds_exactly_the_18_matchday_2_results(staging):
    gate = U.load_gate()
    md2 = staging[staging.matchday == 2]
    assert len(gate) == 18 and set(gate) == set(zip(md2.home_entity, md2.away_entity))
    assert all(gate[(r.home_entity, r.away_entity)] == (str(r.date), int(r.home_goals), int(r.away_goals)) for r in md2.itertuples())


@needs_staging
def test_classification_against_a_store_with_matchday_1(store, staging, entities):
    conn = sqlite3.connect(store)
    stored = U.stored_rows(conn)
    conn.close()
    gate = U.load_gate()
    dec = U.classify(staging, set(), stored, gate, False, "2026-10-28")
    by = pd.DataFrame(dec).groupby("action").size().to_dict()
    assert by == {"unchanged": 18, "insert_result": 18, "skip_fixture_not_requested": 108}
    with_fx = pd.DataFrame(U.classify(staging, set(), stored, gate, True, "2026-10-28"))
    assert with_fx.action.value_counts().to_dict() == {"insert_fixture": 108, "unchanged": 18, "insert_result": 18}
    assert set(with_fx[with_fx.matchday == 3].new_status) == {"awaiting_result"} and set(with_fx[with_fx.matchday == 4].new_status) == {"scheduled"}       # dated before / after the as-of day


@needs_staging
def test_a_result_that_is_not_in_the_gate_is_never_imported(store, staging):
    conn = sqlite3.connect(store)
    stored = U.stored_rows(conn)
    conn.close()
    dec = pd.DataFrame(U.classify(staging, set(), stored, {}, False, "2026-10-28"))
    assert (dec.action == "skip_unverified_result").sum() == 18 and "insert_result" not in set(dec.action)
    gate = U.load_gate()
    k = next(iter(gate))
    gate[k] = (gate[k][0], gate[k][1] + 1, gate[k][2])                                                          # a gate that disagrees with the staged score
    assert (pd.DataFrame(U.classify(staging, set(), stored, gate, False, "2026-10-28")).action == "skip_unverified_result").sum() == 1


@needs_staging
def test_conflicts_with_the_store_are_quarantined_not_overwritten(store, staging):
    conn = sqlite3.connect(store)
    conn.execute("UPDATE matches SET away_goals_final=5 WHERE home_name='AEK Athens F.C.' AND season='2026-27'")          # wrong score
    conn.execute("UPDATE matches SET match_date='2026-09-12' WHERE home_name='Club Brugge KV' AND season='2026-27'")      # wrong date
    conn.commit()
    stored = U.stored_rows(conn)
    conn.close()
    dec = pd.DataFrame(U.classify(staging, set(), stored, U.load_gate(), False, "2026-10-28"))
    assert dec[dec.action == "quarantine_conflict"].home.tolist() == ["AEK Athens F.C.", "Club Brugge KV"]


@needs_staging
def test_the_reverse_pairing_of_a_stored_match_is_a_conflict(store, staging):
    conn = sqlite3.connect(store)
    stored = U.stored_rows(conn)
    conn.close()
    r = staging[staging.matchday == 1].iloc[0]
    swapped = staging.copy()
    swapped.loc[swapped.index == 40, ["home", "away", "home_entity", "away_entity"]] = [r.away, r.home, r.away_entity, r.home_entity]       # an md5 fixture that is the reverse of a stored md1 match
    dec = pd.DataFrame(U.classify(swapped, set(), stored, U.load_gate(), True, "2026-10-28"))
    assert dec.loc[40, "action"] == "quarantine_conflict" and "reverse" in dec.loc[40, "reason"]


# ---------------------------------------------------------------- repeatable imports, dry run, rollback safety
@needs_staging
def test_dry_run_changes_nothing_and_apply_is_repeatable(store):
    before = sha(store)
    rep = U.run(store, apply=False, as_of="2026-10-28")
    assert sha(store) == before and rep["counts"]["insert_result"] == 18 and rep["validation_issues"] == []
    first = U.run(store, apply=True, as_of="2026-10-28")
    assert first["applied"]["inserted"] == 18 and first["applied"]["updated"] == 0
    after = sha(store)
    second = U.run(store, apply=True, as_of="2026-10-28")
    assert second["applied"]["inserted"] == 0 and second["applied"]["updated"] == 0 and second["counts"]["unchanged"] == 36
    conn = sqlite3.connect(store)
    assert conn.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0] == 36
    assert conn.execute("SELECT COUNT(*) FROM (SELECT home_entity_id, away_entity_id FROM matches GROUP BY 1,2 HAVING COUNT(*)>1)").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM match_sources WHERE snapshot_id LIKE 'uefa-ucl-2026-27-staging-rev%'").fetchone()[0] == 18          # provenance for every inserted row
    assert conn.execute("SELECT DISTINCT licence FROM matches WHERE record_id LIKE 'WP:UCL:%'").fetchall() == [("CC BY-SA 4.0",)]
    conn.close()
    assert after != before


@needs_staging
def test_fixtures_are_added_only_on_request_and_complete_in_place(store, tmp_path):
    U.run(store, apply=True, as_of="2026-10-28")
    early = U.load_staging()
    early.loc[early.matchday == 2, ["home_goals", "away_goals"]] = float("nan")
    early.loc[early.matchday == 2, "status"] = "scheduled"
    p = tmp_path / "early.csv"
    early.to_csv(p, index=False, encoding="utf-8-sig")
    conn = sqlite3.connect(store)
    conn.execute("DELETE FROM matches WHERE stage='Matches > Matchday 2' AND competition_key='UCL'")               # as if matchday 2 had not been played yet
    conn.commit()
    conn.close()
    U.run(store, apply=True, include_fixtures=True, staging=p, as_of="2026-10-12", verify_fixtures=False)
    conn = sqlite3.connect(store)
    assert dict(conn.execute("SELECT status, COUNT(*) FROM matches WHERE stage='Matches > Matchday 2' GROUP BY 1")) == {"scheduled": 18}
    conn.close()
    r = U.run(store, apply=True, include_fixtures=True, as_of="2026-10-28", verify_fixtures=False)
    assert r["counts"]["complete_fixture"] == 18 and r["applied"]["updated"] == 18
    conn = sqlite3.connect(store)
    assert dict(conn.execute("SELECT status, COUNT(*) FROM matches WHERE stage='Matches > Matchday 2' GROUP BY 1")) == {"completed": 18}
    assert conn.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0] == 144
    conn.close()


@needs_staging
def test_a_conflicting_stored_row_is_kept_and_quarantined_on_apply(store):
    conn = sqlite3.connect(store)
    conn.execute("UPDATE matches SET home_goals_final=9 WHERE home_name='AEK Athens F.C.' AND season='2026-27'")
    conn.commit()
    conn.close()
    r = U.run(store, apply=True, as_of="2026-10-28")
    conn = sqlite3.connect(store)
    assert conn.execute("SELECT home_goals_final FROM matches WHERE home_name='AEK Athens F.C.' AND season='2026-27'").fetchone()[0] == 9
    assert r["applied"]["quarantined"] == 1 and conn.execute("SELECT COUNT(*) FROM quarantine WHERE reason LIKE 'quarantine_conflict%'").fetchone()[0] == 1
    conn.close()


def test_the_production_store_cannot_be_written_without_flag_and_matching_backup(tmp_path):
    before = sha(U.PRODUCTION) if U.PRODUCTION.exists() else None
    with pytest.raises(SystemExit, match="--production"):
        U.run(U.PRODUCTION, apply=True)
    with pytest.raises(SystemExit, match="--backup"):
        U.run(U.PRODUCTION, apply=True, production=True)
    wrong = tmp_path / "wrong.sqlite"
    wrong.write_bytes(b"not the store")
    with pytest.raises(SystemExit, match="--backup"):
        U.run(U.PRODUCTION, apply=True, production=True, backup=wrong)
    assert (sha(U.PRODUCTION) if U.PRODUCTION.exists() else None) == before


# ---------------------------------------------------------------- competition and season mapping
def test_built_rows_map_to_the_champions_league_and_stay_out_of_the_model_universe():
    row = U.build_row(dict(matchday=2, date="2026-10-13", home="A", away="B", home_entity="CLUB:X:a", away_entity="CLUB:X:b", hg=3, ag=1), 7, "completed")
    ucl = C.BY_KEY["UCL"]
    assert row["competition_id"] == ucl["source_id"] == U.COMPETITION_ID and row["competition_key"] == "UCL" and row["season"] == "2026-27"
    assert row["in_universe"] == 0 and row["model_home_entity"] is None and row["stage"] == "Matches > Matchday 2"                  # same stage text as the existing rows
    assert row["outcome"] == "H" and row["source_system"] == "wikipedia" and row["licence"] == "CC BY-SA 4.0"
    assert U.build_row(dict(matchday=3, date="2026-10-20", home="A", away="B", home_entity="x", away_entity="y", hg=None, ag=None), 7, "scheduled")["home_goals_final"] is None
    assert set(U.build_row(dict(matchday=2, date="d", home="A", away="B", home_entity="x", away_entity="y", hg=0, ag=0), 7, "completed")["outcome"]) == {"D"}


# ---------------------------------------------------------------- league-phase standings with the imported results
@needs_staging
def test_league_phase_table_from_the_36_staged_results(staging):
    played = staging[staging.status == "played"]
    frame = pd.DataFrame(dict(competition_key="UCL", season="2026-27", stage="Matches > Matchday " + played.matchday.astype(str), home=played.home_entity, away=played.away_entity,
                              home_goals=played.home_goals, away_goals=played.away_goals))
    res = LP.league_phase(frame, "UCL", "2026-27")
    t = res["table"]
    assert res["matches_played"] == 36 and res["teams"] == 36 and not res["complete"] and res["criteria_applied"].startswith("1-5")
    assert {r["played"] for r in t} == {2} and sorted({r["position"] for r in t})[0] == 1
    decisive = int((played.home_goals != played.away_goals).sum())
    assert sum(r["points"] for r in t) == 3 * decisive + 2 * (36 - decisive)
    assert sum(r["gf"] for r in t) == sum(r["ga"] for r in t) == int(played.home_goals.sum() + played.away_goals.sum())


@needs_staging
def test_the_gate_results_are_the_matchday_2_results_of_the_table(staging):
    assert staging[staging.status == "played"].matchday.value_counts().sort_index().to_dict() == {1: 18, 2: 18}


# ---------------------------------------------------------------- verified fixtures (Phase 4.21)
needs_fixture_gate = pytest.mark.skipif(not U.FIXTURES_GATE.exists(), reason="Phase 4.21 verified-fixtures gate missing")


@needs_staging
@needs_fixture_gate
def test_the_fixtures_gate_holds_exactly_the_90_league_phase_fixtures_of_matchdays_4_to_8(staging):
    gate = U.load_fixture_gate()
    fx = staging[staging.status == "scheduled"]
    future = fx[fx.matchday >= 4]                                                    # the default staging (Phase 4.17) still lists matchday 3 as unplayed; the gate holds matchdays 4-8 only
    assert len(gate) == 90 and gate == {(r.home_entity, r.away_entity, str(r.date)) for r in future.itertuples()} and set(future.matchday) == {4, 5, 6, 7, 8}


@needs_staging
@needs_fixture_gate
def test_only_fixtures_in_the_gate_are_inserted_and_completed_matches_are_never_listed_as_upcoming(store):
    conn = sqlite3.connect(store)
    stored = U.stored_rows(conn)
    conn.close()
    st = U.load_staging()
    dec = pd.DataFrame(U.classify(st, set(), stored, U.load_gate(), True, "2026-10-28", U.load_fixture_gate()))
    inserted = dec[dec.action == "insert_fixture"]
    assert len(inserted) == 90 and set(inserted.new_status) == {"scheduled"} and inserted.date.min() >= "2026-11-03"       # all dated after the as-of day: none is a played match shown as upcoming
    assert not set(inserted.matchday) & {1, 2, 3} and (dec[dec.matchday == 3].action == "skip_unverified_fixture").all()
    shrunk = {x for x in U.load_fixture_gate() if x[2] != "2026-11-03"}
    dec2 = pd.DataFrame(U.classify(st, set(), stored, U.load_gate(), True, "2026-10-28", shrunk))
    assert (dec2.action == "skip_unverified_fixture").sum() == 9 + 18 and (dec2.action == "insert_fixture").sum() == 81         # the 9 removed fixtures, plus the 18 matchday-3 fixtures (not in the gate)
    changed = {(h, a, "2026-11-05") if d == "2026-11-03" else (h, a, d) for h, a, d in U.load_fixture_gate()}                      # a date that differs from UEFA's list
    assert (pd.DataFrame(U.classify(st, set(), stored, U.load_gate(), True, "2026-10-28", changed)).action == "skip_unverified_fixture").sum() >= 1


@needs_staging
@needs_fixture_gate
def test_run_with_the_gate_inserts_the_90_fixtures_repeatably_and_never_creates_knockout_rows(store):
    first = U.run(store, apply=True, include_fixtures=True, as_of="2026-10-28")
    assert first["counts"]["insert_fixture"] == 90 and first["applied"]["inserted"] == 18 + 90                # this store holds matchday 1: the 18 matchday-2 results plus the 90 gated fixtures
    second = U.run(store, apply=True, include_fixtures=True, as_of="2026-10-28")
    assert second["applied"]["inserted"] == 0 and second["applied"]["updated"] == 0
    conn = sqlite3.connect(store)
    assert conn.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0] == 18 + 18 + 90
    assert conn.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' AND stage NOT LIKE 'Matches > Matchday %'").fetchone()[0] == 0
    assert conn.execute("SELECT MAX(CAST(substr(stage, 20) AS INTEGER)) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0] == 8
    conn.close()


def test_a_knockout_matchday_in_the_staging_is_refused():
    df = known_df(matchday=9)
    issues, bad = U.validate(df, {"E:A", "E:B"})
    assert "not_a_league_phase_matchday" in {i["code"] for i in issues} and 0 in bad
    assert not U.validate(known_df(matchday=8), {"E:A", "E:B"})[0]
