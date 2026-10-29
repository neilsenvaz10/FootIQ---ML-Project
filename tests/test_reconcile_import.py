"""Phase 4.23: the reconciliation importer (app/store/reconcile_import.py) and the evidence parsing it relies on. Pure functions plus runs against a small throw-away store; the production store is never written.

Run:  .venv\\Scripts\\python.exe -X utf8 -m pytest tests/test_reconcile_import.py -q
"""
import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matches as hub  # noqa: E402
from store import baseline as B  # noqa: E402
from store import db as store_db  # noqa: E402
from store import reconcile_import as R  # noqa: E402
from test_featured import CFG  # noqa: E402

AS_OF = "2026-10-28"
ENT = {k: f"CLUB:TST:{k}" for k in "abcdefgh"}


def fx(rid, key, h, a, day, status="scheduled", score=None, local=None):
    hg, ag = score if score else (None, None)
    return dict(record_id=rid, kind="club", competition_id=f"test:{key}", competition_key=key, season="2026-27", stage="Matchday 9", matchday_label="Matchday 9", matchday_no=9, match_date=day, kickoff_local=local,
                kickoff_utc=None, time_precision="local_unknown_tz" if local else "date_only", home_entity_id=ENT[h], away_entity_id=ENT[a], model_home_entity=None, model_away_entity=None, home_name=f"{h} fc", away_name=f"{a} fc",
                status=status, home_goals_final=hg, away_goals_final=ag, home_goals_90=hg, away_goals_90=ag, label_90_status=None, outcome=None, shootout_winner=None, neutral=None, rated=None, regular=None, in_universe=0, tier=None,
                competition_type="domestic_league", source_system="openfootball (CC0 / public domain)", licence="CC0-1.0", src_order=None)


@pytest.fixture()
def store(tmp_path):
    p = tmp_path / "t.sqlite"
    conn = store_db.connect(p)
    store_db.init(conn)
    conn.executemany("INSERT INTO teams(entity_id, display_name, country) VALUES (?,?,?)", [(e, e, "TST") for e in ENT.values()])
    rows = [fx("EPL:1", "EPL", "a", "b", "2026-10-18", "awaiting_result"),                                    # result, date right
            fx("LAL:1", "LALIGA", "c", "d", "2026-10-25", "scheduled", local="21:00"),                         # result, stored date a placeholder
            fx("SA:1", "SERIEA", "e", "f", "2026-11-23", "scheduled", local="20:45"),                          # date correction
            fx("LAL:2", "LALIGA", "g", "h", "2026-10-10", "awaiting_result"),                                  # postponed
            fx("EPL:done", "EPL", "a", "c", "2026-10-10", "completed", (2, 2)),                                # an existing verified result
            fx("SA:other", "SERIEA", "f", "e", "2026-12-05", "scheduled")]
    B.upsert_matches(conn, rows, "2026-10-15T00:00:00Z")
    conn.execute("INSERT INTO quarantine(run_id, source, source_ref, reason, payload, created_utc) VALUES (1,'openligadb','1','DATE_DIFFERENCE: stored 2026-10-10 vs source 2027-05-30: g v h','{}','2026-10-25T00:00:00Z')")
    conn.commit()
    conn.close()
    return p


def prop(change_id="R001", rid="EPL:1", key="EPL", h="a", a="b", action="add_result", tier="strong", exp_status="awaiting_result", exp_date="2026-10-18", new_date="2026-10-18", hg=1, ag=0, **over):
    row = dict(change_id=change_id, record_id=rid, competition_key=key, home=f"{h} fc", away=f"{a} fc", home_entity=ENT[h], away_entity=ENT[a], action=action, tier=tier, expected_store_status=exp_status,
               expected_store_date=exp_date, new_date=new_date, home_goals=hg, away_goals=ag, wikipedia_score=f"{hg}-{ag}", footballdatauk_score=f"{hg}-{ag}", fixturedownload_score=f"{hg}-{ag}", wikipedia_revision=7,
               openfootball_date=exp_date, footballdatauk_date=new_date, fixturedownload_date=new_date, openligadb_date=None, provider_date=None, evidence="test evidence")
    row.update(over)
    return row


def date_change(change_id="D001", rid="SA:1", key="SERIEA", h="e", a="f", exp_date="2026-11-23", new_date="2026-11-24", tier="strong", **over):
    base = dict(wikipedia_score=None, footballdatauk_score=None, fixturedownload_score=None, fixturedownload_date=new_date, openligadb_date=new_date, footballdatauk_date=None, provider_date=None)
    base.update(over)
    return prop(change_id, rid, key, h, a, "correct_date", tier, "scheduled", exp_date, new_date, None, None, **base)


def csv(tmp_path, rows):
    p = tmp_path / "proposals.csv"
    pd.DataFrame(rows).to_csv(p, index=False, encoding="utf-8-sig")
    return p


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def snapshot_rows(p, exclude=()):
    c = sqlite3.connect(p)
    marks = ",".join("?" * len(exclude))
    out = c.execute(f"SELECT record_id, content_hash FROM matches WHERE record_id NOT IN ({marks}) ORDER BY 1", list(exclude)).fetchall()
    c.close()
    return out


def issues(rows):
    return {i["code"] for i in R.validate(pd.DataFrame(rows), set(ENT.values()), AS_OF)[0]}


# ---------------------------------------------------------------- validation
@pytest.mark.parametrize("row, code", [
    (prop(action="delete_match"), "bad_action"), (prop(tier="guess"), "bad_tier"), (prop(key="BUNDESLIGA"), "competition_not_allowed"), (prop(key="UCL"), "competition_not_allowed"),
    (prop(home_entity="CLUB:TST:unknown"), "unknown_team_identifier"), (prop(away_entity=ENT["a"]), "home_equals_away"), (prop(evidence=""), "no_evidence"),
    (prop(exp_date="2026-9-9"), "bad_expected_date"), (prop(hg=-1), "implausible_score"), (prop(hg=16), "implausible_score"), (prop(hg=1.5), "implausible_score"),
    (prop(fixturedownload_score=None, footballdatauk_score=None), "scores_not_two_source_verified"), (prop(footballdatauk_score="2-0"), "scores_not_two_source_verified"),
    (prop(new_date="2026-11-30", exp_date="2026-11-30", footballdatauk_date="2026-11-30", fixturedownload_date="2026-11-30"), "result_dated_in_the_future"),
    (prop(new_date="2026-10-19"), "date_differs_for_add_result"), (prop(action="add_result_with_date", new_date="2026-10-24", footballdatauk_date="2026-10-24", fixturedownload_date="2026-10-23"), "played_day_not_two_source_verified"),
    (prop(action="add_result_with_date", exp_date="2026-10-01", new_date="2026-10-18"), "bad_date_shift"), (prop(action="add_result_with_date"), "bad_date_shift"), (prop(tier="provider_assisted"), "result_must_be_strong"),
    (date_change(new_date="2026-11-23"), "no_change"), (date_change(new_date="2026-11-30"), "date_shift_too_large"), (date_change(exp_date="2026-10-20", new_date="2026-10-21"), "corrected_date_in_the_past"),
    (date_change(openligadb_date=None), "strong_needs_two_sources_without_the_provider"), (date_change(tier="provider_assisted", openligadb_date=None, fixturedownload_date="2026-11-25"), "provider_assisted_needs_two_sources"),
    (date_change(tier="decision"), "date_correction_cannot_be_a_decision"), (prop(action="set_postponed", tier="strong", exp_date="2026-10-10", hg=None, ag=None), "postponement_must_be_a_decision"),
    (prop(action="set_postponed", tier="decision", exp_date="2026-11-10", hg=None, ag=None), "postponement_of_a_future_fixture"), (prop(action="set_postponed", tier="decision", exp_date="2026-10-10", hg=1, ag=0), "postponement_with_a_score")])
def test_validation_flags_each_kind_of_bad_row(row, code):
    assert code in issues([row])


def test_duplicate_changes_are_flagged_and_a_clean_file_has_no_issue():
    assert {"duplicate_change_id", "two_changes_for_one_fixture"} <= issues([prop(), prop()])
    assert issues([prop(), date_change(), prop("R002", "LAL:2", "LALIGA", "g", "h", "set_postponed", "decision", "awaiting_result", "2026-10-10", None, None, None, wikipedia_score=None, footballdatauk_score=None,
                                              fixturedownload_score=None, footballdatauk_date=None, fixturedownload_date=None)]) == set()


# ---------------------------------------------------------------- classification
def decide(store, rows, tiers=("strong", "provider_assisted", "decision")):
    df = pd.DataFrame(rows)
    iss, bad = R.validate(df, set(ENT.values()), AS_OF)
    conn = sqlite3.connect(store)
    conn.row_factory = sqlite3.Row
    stored = R.L.stored_by_record(conn, R.ALLOWED)
    conn.close()
    return {d["change_id"]: d for d in R.classify(df, bad, stored, set(tiers))}


def test_classification_applies_matching_proposals_and_skips_tiers_not_enabled(store):
    rows = [prop(), date_change(), date_change("D002", "SA:other", "SERIEA", "f", "e", "2026-12-05", "2026-12-06", tier="provider_assisted", openligadb_date=None, provider_date="2026-12-06")]
    d = decide(store, rows)
    assert {k: v["action"] for k, v in d.items()} == {"R001": "apply", "D001": "apply", "D002": "apply"}
    d = decide(store, rows, tiers=("strong",))
    assert d["D002"]["action"] == "skip_tier_not_enabled" and d["R001"]["action"] == "apply"


def test_a_stored_result_is_never_overwritten_and_stale_proposals_are_quarantined(store):
    d = decide(store, [prop("R010", "EPL:done", "EPL", "a", "c", exp_status="completed", exp_date="2026-10-10", new_date="2026-10-10", hg=3, ag=1)])
    assert d["R010"]["action"] == "quarantine_conflict" and "never overwritten" in d["R010"]["reason"]
    d = decide(store, [prop("R011", "EPL:done", "EPL", "a", "c", exp_status="completed", exp_date="2026-10-10", new_date="2026-10-10", hg=2, ag=2)])
    assert d["R011"]["action"] == "unchanged"                                                       # the same verified result is already there
    conn = sqlite3.connect(store)
    conn.execute("UPDATE matches SET match_date='2026-10-19' WHERE record_id='EPL:1'")
    conn.execute("UPDATE matches SET status='completed', home_goals_final=0, away_goals_final=0 WHERE record_id='SA:1'")
    conn.commit()
    conn.close()
    d = decide(store, [prop(), date_change()])
    assert d["R001"]["action"] == "quarantine_conflict" and "store changed" in d["R001"]["reason"]
    assert d["D001"]["action"] == "quarantine_conflict" and "not an open fixture" in d["D001"]["reason"]    # a played match's date is never changed by a date correction


def test_a_reversed_pairing_and_an_unknown_record_are_quarantined(store):
    d = decide(store, [prop(h="b", a="a"), prop("R020", "NOPE", h="b", a="a")])
    assert d["R001"]["action"] == "quarantine_conflict" and "different pairing" in d["R001"]["reason"]
    assert d["R020"]["action"] == "quarantine_conflict" and "not in the store" in d["R020"]["reason"]


# ---------------------------------------------------------------- dry run, apply, idempotence, duplicates, postponement, rollback
def full_set():
    return [prop(), prop("R002", "LAL:1", "LALIGA", "c", "d", "add_result_with_date", exp_status="scheduled", exp_date="2026-10-25", new_date="2026-10-24", hg=1, ag=2),
            prop("R003", "LAL:2", "LALIGA", "g", "h", "set_postponed", "decision", "awaiting_result", "2026-10-10", None, None, None, wikipedia_score=None, footballdatauk_score=None, fixturedownload_score=None,
                 footballdatauk_date=None, fixturedownload_date=None), date_change()]


def test_dry_run_changes_nothing_and_apply_is_repeatable_without_duplicates(store, tmp_path):
    p = csv(tmp_path, full_set())
    before = sha(store)
    rep = R.run(store, proposals=p, tiers=("strong", "decision"), as_of=AS_OF)
    assert sha(store) == before and rep["counts"] == {"apply": 4} and rep["validation_issues"] == []
    touched = ["EPL:1", "LAL:1", "LAL:2", "SA:1"]
    others = snapshot_rows(store, touched)
    first = R.run(store, apply=True, proposals=p, tiers=("strong", "decision"), as_of=AS_OF)
    assert first["applied"]["updated"] == 4 and first["applied"]["inserted"] == 0 and first["applied"]["quarantined"] == 0
    second = R.run(store, apply=True, proposals=p, tiers=("strong", "decision"), as_of=AS_OF)
    assert second["counts"] == {"unchanged": 4} and second["applied"]["updated"] == 0 and second["applied"]["inserted"] == 0
    assert snapshot_rows(store, touched) == others                                                  # every other row is byte-for-byte what it was
    c = sqlite3.connect(store)
    c.row_factory = sqlite3.Row
    r = {x["record_id"]: dict(x) for x in c.execute("SELECT * FROM matches")}
    assert len(r) == 6                                                                              # no row added, none removed
    assert (r["EPL:1"]["status"], r["EPL:1"]["home_goals_final"], r["EPL:1"]["away_goals_final"], r["EPL:1"]["outcome"], r["EPL:1"]["match_date"], r["EPL:1"]["in_universe"]) == ("completed", 1, 0, "H", "2026-10-18", 1)
    assert (r["EPL:1"]["source_system"], r["EPL:1"]["licence"]) == ("wikipedia", "CC BY-SA 4.0")
    lal = r["LAL:1"]
    assert (lal["status"], lal["match_date"], lal["home_goals_final"], lal["away_goals_final"], lal["outcome"]) == ("completed", "2026-10-24", 1, 2, "A")
    assert (lal["kickoff_local"], lal["time_precision"]) == (None, "date_only")                       # the stored time belonged to the placeholder date
    sa = r["SA:1"]
    assert (sa["match_date"], sa["status"], sa["kickoff_local"], sa["time_precision"], sa["home_goals_final"]) == ("2026-11-24", "scheduled", None, "date_only", None)
    assert (r["LAL:2"]["status"], r["LAL:2"]["match_date"], r["LAL:2"]["home_goals_final"]) == ("postponed", "2026-10-10", None)    # postponed: status only, the date and everything else stay
    assert c.execute("SELECT COUNT(*) FROM match_sources WHERE source='reconciliation'").fetchone()[0] == 4
    assert "test evidence" in c.execute("SELECT provenance FROM match_sources WHERE source_ref='RECON:R001'").fetchone()[0]
    assert c.execute("SELECT COUNT(*) FROM source_snapshots WHERE snapshot_id LIKE 'reconcile-p423-%'").fetchone()[0] == 1
    assert c.execute("SELECT COUNT(*) FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%'").fetchone()[0] == 1                      # the original finding is kept (nothing is deleted)
    assert [tuple(x) for x in c.execute("SELECT kind, outcome, updated FROM sync_runs WHERE kind='reconcile_import' ORDER BY run_id")] == [("reconcile_import", "ok", 4), ("reconcile_import", "ok", 0)]
    c.close()


def test_a_conflicting_row_is_quarantined_on_apply_and_the_rest_is_applied(store, tmp_path):
    bad = prop("R010", "EPL:done", "EPL", "a", "c", exp_status="completed", exp_date="2026-10-10", new_date="2026-10-10", hg=3, ag=1)
    p = csv(tmp_path, [prop(), bad])
    rep = R.run(store, apply=True, proposals=p, tiers=("strong",), as_of=AS_OF)
    assert rep["applied"]["updated"] == 1 and rep["applied"]["quarantined"] == 1
    c = sqlite3.connect(store)
    assert c.execute("SELECT home_goals_final, away_goals_final FROM matches WHERE record_id='EPL:done'").fetchone() == (2, 2)
    assert c.execute("SELECT COUNT(*) FROM quarantine WHERE reason LIKE 'quarantine_conflict%'").fetchone()[0] == 1
    c.close()


def test_postponed_fixtures_leave_the_upcoming_and_awaiting_lists_and_appear_under_other(store, tmp_path):
    def counts(p):
        conn = store_db.connect(p, readonly=True)
        try:
            return hub.build(conn, CFG, datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc), comp="LALIGA", status="all", limit=50)["counts"]
        finally:
            conn.close()
    before = counts(store)
    R.run(store, apply=True, proposals=csv(tmp_path, [full_set()[2]]), tiers=("decision",), as_of=AS_OF)
    after = counts(store)
    assert after["awaiting_result"] == before["awaiting_result"] - 1 and after["other"] == before["other"] + 1 and after["all"] == before["all"]   # the postponed match moves to "other"; the other open La Liga fixture stays awaiting


def test_a_failure_in_the_middle_of_an_apply_leaves_the_store_untouched_and_a_backup_restores_it(store, tmp_path, monkeypatch):
    p = csv(tmp_path, full_set())
    backup = tmp_path / "backup.sqlite"
    shutil.copy2(store, backup)
    before = sha(store)

    def boom(*a, **k):
        raise RuntimeError("disk full")
    monkeypatch.setattr(R.B, "upsert_matches", boom)
    with pytest.raises(RuntimeError):
        R.run(store, apply=True, proposals=p, tiers=("strong", "decision"), as_of=AS_OF)
    c = sqlite3.connect(store)
    assert c.execute("SELECT COUNT(*) FROM sync_runs WHERE kind='reconcile_import'").fetchone()[0] == 0           # the whole transaction rolled back, the run record included
    assert c.execute("SELECT status FROM matches WHERE record_id='EPL:1'").fetchone()[0] == "awaiting_result"
    c.close()
    monkeypatch.undo()
    R.run(store, apply=True, proposals=p, tiers=("strong", "decision"), as_of=AS_OF)
    assert sha(store) != before
    shutil.copy2(backup, store)                                                                       # the documented rollback: put the backup file back
    assert sha(store) == before


def test_the_production_store_cannot_be_written_without_flag_and_matching_backup(tmp_path):
    before = sha(R.PRODUCTION) if R.PRODUCTION.exists() else None
    with pytest.raises(SystemExit, match="--production"):
        R.run(R.PRODUCTION, apply=True, proposals=PROPOSAL_PLACEHOLDER)
    with pytest.raises(SystemExit, match="--backup"):
        R.run(R.PRODUCTION, apply=True, production=True, proposals=PROPOSAL_PLACEHOLDER)
    wrong = tmp_path / "wrong.sqlite"
    wrong.write_bytes(b"not the store")
    with pytest.raises(SystemExit, match="--backup"):
        R.run(R.PRODUCTION, apply=True, production=True, backup=wrong, proposals=PROPOSAL_PLACEHOLDER)
    assert (sha(R.PRODUCTION) if R.PRODUCTION.exists() else None) == before


PROPOSAL_PLACEHOLDER = R.PROPOSALS


# ---------------------------------------------------------------- the real staged proposals, read-only
@pytest.mark.skipif(not (R.PRODUCTION.exists() and R.PROPOSALS.exists()), reason="production store or the Phase 4.23 proposals are missing")
def test_the_real_proposals_are_clean_against_production_read_only():
    before = sha(R.PRODUCTION)
    rep = R.run(R.PRODUCTION, tiers=("strong", "provider_assisted", "decision"), as_of=AS_OF)
    assert sha(R.PRODUCTION) == before
    assert rep["rows"] == 104 and rep["validation_issues"] == []
    by_type = pd.DataFrame(rep["decisions"]).groupby("action_type").size().to_dict()
    assert by_type == {"add_result": 4, "add_result_with_date": 8, "correct_date": 91, "set_postponed": 1}
    assert set(rep["counts"]) <= {"apply", "unchanged"}                                             # no conflict: after an import every row is 'unchanged'


# ---------------------------------------------------------------- evidence parsing and team mapping used to build the proposals
EVIDENCE = ROOT / "data" / "supervised" / "phase4" / "p423" / "evidence.py"


@pytest.mark.skipif(not EVIDENCE.exists(), reason="Phase 4.23 evidence helpers missing")
class TestEvidenceHelpers:
    @staticmethod
    def mod():
        import importlib.util
        spec = importlib.util.spec_from_file_location("p423_evidence", EVIDENCE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_a_results_grid_cell_with_a_piped_derby_link_keeps_its_score(self):
        E = self.mod()
        names, grid = E.parse_grid("|match_CHE_TOT = [[Chelsea F.C.–Tottenham Hotspur F.C. rivalry|0–2]]\n|match_ARS_LIV =3–1\n|match_MUN_LEE =\n|name_CHE=[[Chelsea F.C.|Chelsea]]")
        assert grid[("CHE", "TOT")] == ((0, 2), None) and grid[("ARS", "LIV")] == ((3, 1), None) and grid[("MUN", "LEE")][0] is None and names["CHE"] == ("Chelsea F.C.", "Chelsea")

    def test_clubs_are_mapped_one_to_one_even_when_names_overlap(self):
        E = self.mod()
        ent = {"inter": "FC Internazionale Milano", "milan": "AC Milan", "psg": "Paris Saint-Germain FC", "parisfc": "Paris FC", "esp": "RCD Espanyol de Barcelona", "bar": "FC Barcelona", "havre": "Le Havre AC"}
        h = E.H.resolve
        assert h(ent, "Inter Milan") == "inter" and h(ent, "Milan") == "milan" and h(ent, "AC Milan") == "milan" and h(ent, "Inter") == "inter"
        assert h(ent, "Paris SG") == "psg" and h(ent, "Paris FC") == "parisfc" and h(ent, "Paris Saint-Germain") == "psg"
        assert h(ent, "Barcelona") == "bar" and h(ent, "Espanol") == "esp" and h(ent, "Havre Athletic Club") == "havre"
        assert h(ent, "Nonexistent Town") is None
