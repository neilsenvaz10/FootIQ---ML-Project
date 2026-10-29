"""Phase 4.21: the offline domestic-results importer (app/store/league_results_import.py). Pure functions plus runs against a small throw-away store; the production store is never written.

Run:  .venv\\Scripts\\python.exe -X utf8 -m pytest tests/test_league_results_import.py -q
"""
import hashlib
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

from store import baseline as B  # noqa: E402
from store import db as store_db  # noqa: E402
from store import league_results_import as L  # noqa: E402

AS_OF = "2026-10-28"
ENT = {"a": "CLUB:TST:alpha", "b": "CLUB:TST:bravo", "c": "CLUB:TST:charlie", "d": "CLUB:TST:delta"}


def fixture_row(rid, key, h, a, day, status="scheduled", score=None):
    hg, ag = score if score else (None, None)
    return dict(record_id=rid, kind="club", competition_id=f"test:{key}", competition_key=key, season="2026-27", stage="Matchday 7", matchday_label="Matchday 7", matchday_no=7, match_date=day, kickoff_local=None,
                kickoff_utc=None, time_precision="date_only", home_entity_id=ENT[h], away_entity_id=ENT[a], model_home_entity=None, model_away_entity=None, home_name=f"{h} fc", away_name=f"{a} fc", status=status,
                home_goals_final=hg, away_goals_final=ag, home_goals_90=hg, away_goals_90=ag, label_90_status=None, outcome=None, shootout_winner=None, neutral=None, rated=None, regular=None, in_universe=0, tier=None,
                competition_type="domestic_league", source_system="openfootball (CC0 / public domain)", licence="CC0-1.0", src_order=None)


@pytest.fixture()
def store(tmp_path):
    p = tmp_path / "t.sqlite"
    conn = store_db.connect(p)
    store_db.init(conn)
    conn.executemany("INSERT INTO teams(entity_id, display_name, country) VALUES (?,?,?)", [(e, e, "TST") for e in ENT.values()])
    rows = [fixture_row("EPL:1", "EPL", "a", "b", "2026-10-17", "awaiting_result"), fixture_row("EPL:2", "EPL", "c", "d", "2026-10-17", "awaiting_result"),
            fixture_row("EPL:3", "EPL", "a", "c", "2026-10-10", "completed", (2, 2)), fixture_row("SA:1", "SERIEA", "a", "b", "2026-10-18", "scheduled"),
            fixture_row("EPL:future", "EPL", "b", "d", "2026-11-07", "scheduled")]
    B.upsert_matches(conn, rows, "2026-10-15T00:00:00Z")
    conn.commit()
    conn.close()
    return p


def staged_row(rid="EPL:1", key="EPL", h="a", a="b", day="2026-10-17", hg=1, ag=0, **over):
    row = dict(competition_key=key, season="2026-27", record_id=rid, home_entity=ENT[h], away_entity=ENT[a], home=f"{h} fc", away=f"{a} fc", store_status="awaiting_result", store_date=day,
               wikipedia_score=f"{hg}-{ag}", wikipedia_revision=555, wikipedia_revision_time="2026-10-27T00:00:00Z", footballdatauk_date=day, footballdatauk_score=f"{hg}-{ag}", tier="verified_two_sources",
               date=day, home_goals=hg, away_goals=ag)
    row.update(over)
    return row


def csv(tmp_path, rows, name="staged_results_EPL.csv"):
    p = tmp_path / name
    pd.DataFrame(rows).to_csv(p, index=False, encoding="utf-8-sig")
    return p


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def others_hash(p, record_ids):
    c = sqlite3.connect(p)
    marks = ",".join("?" * len(record_ids))
    h = hashlib.sha256(repr(c.execute(f"SELECT record_id, content_hash FROM matches WHERE record_id NOT IN ({marks}) ORDER BY 1", record_ids).fetchall()).encode()).hexdigest()
    c.close()
    return h


# ---------------------------------------------------------------- validation
@pytest.mark.parametrize("over, code", [
    (dict(home_entity=None), "missing_team_identifier"), (dict(home_entity="CLUB:TST:unknown"), "unknown_team_identifier"), (dict(away_entity=ENT["a"]), "home_equals_away"),
    (dict(date="2026-9-9", store_date="2026-9-9", footballdatauk_date="2026-9-9"), "bad_date"), (dict(date="2026-11-30", store_date="2026-11-30", footballdatauk_date="2026-11-30"), "result_dated_in_the_future"),
    (dict(date="2025-10-10", store_date="2025-10-10", footballdatauk_date="2025-10-10"), "date_outside_season"), (dict(footballdatauk_date="2026-10-18"), "dates_disagree"),
    (dict(store_date="2026-10-16"), "dates_disagree"), (dict(home_goals=-1), "implausible_score"), (dict(home_goals=16), "implausible_score"), (dict(home_goals=1.5), "implausible_score"),
    (dict(home_goals=float("nan")), "implausible_score"), (dict(footballdatauk_score="2-0"), "sources_disagree_on_score"), (dict(wikipedia_score="0-0"), "sources_disagree_on_score"),
    (dict(tier="single_source_wikipedia"), "not_two_source_verified"), (dict(competition_key="LALIGA"), "competition_not_allowed"), (dict(competition_key="BUNDESLIGA"), "competition_not_allowed"),
    (dict(competition_key="UCL"), "competition_not_allowed"), (dict(season="2025-26"), "bad_season")])
def test_validation_flags_each_kind_of_bad_row(over, code):
    issues, bad = L.validate(pd.DataFrame([staged_row(**over)]), set(ENT.values()), AS_OF)
    assert code in {i["code"] for i in issues} and 0 in bad


def test_duplicates_in_the_file_are_flagged():
    df = pd.DataFrame([staged_row(), staged_row(), staged_row(rid="EPL:1b")])
    codes = [i["code"] for i in L.validate(df, set(ENT.values()), AS_OF)[0]]
    assert "duplicate_in_file" in codes and "duplicate_pairing_in_file" in codes


def test_a_clean_row_has_no_issue():
    assert L.validate(pd.DataFrame([staged_row()]), set(ENT.values()), AS_OF) == ([], set())


# ---------------------------------------------------------------- classification against the store
def decide(store, rows, disputed=None):
    df = pd.DataFrame(rows)
    issues, bad = L.validate(df, set(ENT.values()), AS_OF)
    conn = sqlite3.connect(store)
    conn.row_factory = sqlite3.Row
    stored = L.stored_by_record(conn, L.ALLOWED)
    conn.close()
    return {d["record_id"]: d for d in L.classify(df, bad, stored, disputed or {})}


def test_classification_covers_update_unchanged_and_every_conflict(store):
    rows = [staged_row("EPL:1"), staged_row("EPL:3", h="a", a="c", day="2026-10-10", hg=2, ag=2),                                   # open fixture / identical stored result
            staged_row("EPL:2", h="c", a="d", hg=0, ag=0, store_status="awaiting_result"), staged_row("NOPE", h="b", a="a"),         # open fixture / record not in the store
            staged_row("SA:1", key="SERIEA", day="2026-10-19")]                                                                      # date differs from the stored fixture
    d = decide(store, rows)
    assert d["EPL:1"]["action"] == "update_result" and d["EPL:3"]["action"] == "unchanged" and d["EPL:2"]["action"] == "update_result"
    assert d["NOPE"]["action"] == "quarantine_conflict" and "not in the store" in d["NOPE"]["reason"]
    assert d["SA:1"]["action"] == "quarantine_conflict" and "dated 2026-10-18" in d["SA:1"]["reason"]                              # the stored fixture is on another day: not resolved here


def test_a_stored_result_is_never_overwritten_and_other_conflicts_are_quarantined(store):
    d = decide(store, [staged_row("EPL:3", h="a", a="c", day="2026-10-10", hg=3, ag=1)])
    assert d["EPL:3"]["action"] == "quarantine_conflict" and "never overwritten" in d["EPL:3"]["reason"]
    conn = sqlite3.connect(store)
    conn.execute("UPDATE matches SET status='postponed' WHERE record_id='EPL:2'")
    conn.execute("UPDATE matches SET match_date='2026-10-16' WHERE record_id='EPL:1'")
    conn.commit()
    conn.close()
    d = decide(store, [staged_row("EPL:2", h="c", a="d"), staged_row("EPL:1")])
    assert d["EPL:2"]["action"] == "quarantine_conflict" and "postponed" in d["EPL:2"]["reason"]
    assert d["EPL:1"]["action"] == "quarantine_conflict" and "dated 2026-10-16" in d["EPL:1"]["reason"]


def test_a_reversed_pairing_and_a_disputed_date_are_quarantined_not_resolved(store):
    d = decide(store, [staged_row("EPL:1", h="b", a="a")])
    assert d["EPL:1"]["action"] == "quarantine_conflict" and "different pairing" in d["EPL:1"]["reason"]
    d = decide(store, [staged_row("EPL:1")], disputed={"EPL:1": ["2026-10-18"]})
    assert d["EPL:1"]["action"] == "quarantine_conflict" and "disputed" in d["EPL:1"]["reason"]


# ---------------------------------------------------------------- dry run, apply, idempotence, provenance
def test_dry_run_changes_nothing_and_apply_is_repeatable(store, tmp_path):
    p = csv(tmp_path, [staged_row("EPL:1"), staged_row("EPL:2", h="c", a="d", hg=0, ag=0)])
    before = sha(store)
    others_before = others_hash(store, ["EPL:1", "EPL:2"])
    rep = L.run(store, apply=False, paths=[p], as_of=AS_OF)
    assert sha(store) == before and rep["counts"] == {"update_result": 2} and rep["validation_issues"] == []
    first = L.run(store, apply=True, paths=[p], as_of=AS_OF)
    assert first["applied"]["updated"] == 2 and first["applied"]["inserted"] == 0 and first["applied"]["quarantined"] == 0
    second = L.run(store, apply=True, paths=[p], as_of=AS_OF)
    assert second["counts"] == {"unchanged": 2} and second["applied"]["updated"] == 0 and second["applied"]["inserted"] == 0
    c = sqlite3.connect(store)
    c.row_factory = sqlite3.Row
    r = dict(c.execute("SELECT * FROM matches WHERE record_id='EPL:1'").fetchone())
    c.row_factory = None
    assert (r["status"], r["home_goals_final"], r["away_goals_final"], r["outcome"], r["match_date"]) == ("completed", 1, 0, "H", "2026-10-17")        # the stored fixture date is kept
    assert (r["rated"], r["regular"], r["in_universe"], r["model_home_entity"], r["model_away_entity"]) == (1, 1, 1, ENT["a"], ENT["b"])             # enters the model universe like a synced result
    assert (r["source_system"], r["licence"], r["home_goals_90"], r["label_90_status"]) == ("wikipedia", "CC BY-SA 4.0", 1, "confirmed")
    assert dict(c.execute("SELECT outcome, COUNT(*) FROM matches WHERE record_id IN ('EPL:1','EPL:2') GROUP BY 1").fetchall()) == {"H": 1, "D": 1}
    assert c.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 5                                                                           # no row added, none removed
    assert c.execute("SELECT COUNT(*) FROM match_sources WHERE source='wikipedia' AND role='primary'").fetchone()[0] == 2
    assert c.execute("SELECT snapshot_id, revision, licence FROM source_snapshots WHERE snapshot_id LIKE 'wikipedia-EPL%'").fetchall() == [("wikipedia-EPL-season-rev555", "555", "CC BY-SA 4.0")]
    assert c.execute("SELECT kind, outcome, updated FROM sync_runs WHERE kind='league_results_import' ORDER BY run_id").fetchall() == [("league_results_import", "ok", 2), ("league_results_import", "ok", 0)]
    c.close()
    assert others_hash(store, ["EPL:1", "EPL:2"]) == others_before                                                                               # every other row is byte-for-byte what it was


def test_no_other_row_changes_and_conflicts_are_quarantined_on_apply(store, tmp_path):
    before = others_hash(store, ["EPL:1"])
    p = csv(tmp_path, [staged_row("EPL:1"), staged_row("EPL:3", h="a", a="c", day="2026-10-10", hg=3, ag=1)])
    rep = L.run(store, apply=True, paths=[p], as_of=AS_OF)
    assert rep["applied"]["updated"] == 1 and rep["applied"]["quarantined"] == 1
    assert others_hash(store, ["EPL:1"]) == before                                                    # the conflicting stored result is untouched too
    c = sqlite3.connect(store)
    assert c.execute("SELECT home_goals_final, away_goals_final FROM matches WHERE record_id='EPL:3'").fetchone() == (2, 2)
    assert c.execute("SELECT COUNT(*) FROM quarantine WHERE reason LIKE 'quarantine_conflict%'").fetchone()[0] == 1
    c.close()


def test_the_production_store_cannot_be_written_without_flag_and_matching_backup(tmp_path):
    before = sha(L.PRODUCTION) if L.PRODUCTION.exists() else None
    with pytest.raises(SystemExit, match="--production"):
        L.run(L.PRODUCTION, apply=True, paths=[])
    with pytest.raises(SystemExit, match="--backup"):
        L.run(L.PRODUCTION, apply=True, production=True, paths=[])
    wrong = tmp_path / "wrong.sqlite"
    wrong.write_bytes(b"not the store")
    with pytest.raises(SystemExit, match="--backup"):
        L.run(L.PRODUCTION, apply=True, production=True, backup=wrong, paths=[])
    assert (sha(L.PRODUCTION) if L.PRODUCTION.exists() else None) == before


# ---------------------------------------------------------------- the real staged files, read-only
@pytest.mark.skipif(not (L.PRODUCTION.exists() and len(L.staged_paths()) == 3), reason="production store or the Phase 4.20 staging files are missing")
def test_the_real_staged_domestic_results_are_clean_against_production_read_only():
    before = sha(L.PRODUCTION)
    rep = L.run(L.PRODUCTION, apply=False, as_of=AS_OF)
    assert sha(L.PRODUCTION) == before
    assert rep["rows_staged"] == 71 and rep["validation_issues"] == []
    assert {k: sum(v.values()) for k, v in rep["by_league"].items()} == {"EPL": 17, "SERIEA": 29, "LIGUE1": 25}
    assert set(rep["counts"]) <= {"update_result", "unchanged"} and sum(rep["counts"].values()) == 71       # no conflict, nothing invalid (after an import all 71 are 'unchanged')
