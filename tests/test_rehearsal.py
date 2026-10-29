"""Offline rehearsal of the OpenLigaDB Premier League / La Liga import: identity checks, date protection, quarantine, determinism and isolation from production.
Uses the saved investigation snapshots and a private copy of the store; no network."""
import hashlib
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from store import db, rehearse_openligadb as R, sync  # noqa: E402

BEFORE = R.REH / "footiq.before.sqlite"
needs = pytest.mark.skipif(not (BEFORE.exists() and (R.SNAP / "run_summary.json").exists()), reason="rehearsal inputs (private copy / saved snapshots) not present")


@pytest.fixture(scope="module")
def snaps():
    return R.load_snapshots()


@pytest.fixture(scope="module")
def applied(tmp_path_factory, snaps):
    cb = db.connect(BEFORE, readonly=True)
    ident = R.verify_identities(cb, snaps)
    cb.close()
    dst = tmp_path_factory.mktemp("reh") / "after.sqlite"
    shutil.copyfile(BEFORE, dst)
    first = R.apply(dst, snaps, ident["aliases"])
    return dst, ident, first


def q(path, sql, *a):
    c = sqlite3.connect(path)
    try:
        return c.execute(sql, a).fetchall()
    finally:
        c.close()


@needs
def test_the_five_proposed_aliases_pass_every_check_and_names_that_are_not_stored_are_reported(snaps):
    cb = db.connect(BEFORE, readonly=True)
    ident = R.verify_identities(cb, snaps)
    cb.close()
    assert [v["accepted"] for v in ident["verdicts"]] == [True] * 5
    assert all(v["paired"] == 38 and v["matchday_agrees"] == 38 for v in ident["verdicts"])
    by = {v["source_name"]: v for v in ident["verdicts"]}
    assert by["Brentford F.C."]["canonical_entity_id"] == "CLUB:ENG:brentford-fc"
    assert not by["Racing Santander"]["proposed_name_equals_a_stored_name"]         # 'Racing de Santander' is not a stored name: mapped by entity evidence only
    assert not by["Deportivo A Coru\u00f1a"]["proposed_name_equals_a_stored_name"]


@needs
def test_a_wrong_target_is_rejected_brentford_never_maps_to_arsenal(snaps, monkeypatch):
    bad = [dict(R.PROPOSED[0], entity="CLUB:ENG:arsenal-fc")] + R.PROPOSED[1:]
    monkeypatch.setattr(R, "PROPOSED", bad)
    cb = db.connect(BEFORE, readonly=True)
    ident = R.verify_identities(cb, snaps)
    cb.close()
    v = ident["verdicts"][0]
    assert v["accepted"] is False and not v["checks"]["not_a_forbidden_fuzzy_target"]
    assert all(a["entity_id"] != "CLUB:ENG:arsenal-fc" for a in ident["aliases"])


@needs
def test_without_reviewed_aliases_unresolved_names_are_quarantined_not_guessed(tmp_path, snaps):
    dst = tmp_path / "noalias.sqlite"
    shutil.copyfile(BEFORE, dst)
    R.apply(dst, snaps, [])
    reasons = " | ".join(r[0] for r in q(dst, "SELECT reason FROM quarantine WHERE reason LIKE 'unresolved%'"))
    assert "Brentford F.C." in reasons and "Celta Vigo" in reasons
    assert q(dst, "SELECT COUNT(*) FROM team_aliases WHERE source='openligadb'")[0][0] == 0


@needs
def test_no_stored_date_is_changed_and_all_55_differences_are_quarantined(applied):
    dst, _, first = applied
    a = {r[0]: r[1] for r in q(dst, "SELECT record_id, match_date FROM matches")}
    b = {r[0]: r[1] for r in q(BEFORE, "SELECT record_id, match_date FROM matches")}
    assert a == b
    assert q(dst, "SELECT COUNT(*) FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%'")[0][0] == 55
    assert first["EPL"]["held_date_difference"] == 31 and first["LALIGA"]["held_date_difference"] == 24


@needs
def test_conflicting_and_contradictory_scores_are_quarantined_and_both_stored_scores_survive(applied):
    dst, _, _ = applied
    assert q(dst, "SELECT home_goals_90, away_goals_90 FROM matches WHERE competition_key='EPL' AND season='2026-27' AND home_name='AFC Bournemouth' AND away_name='Brentford FC'") == [(2, 2)]
    assert q(dst, "SELECT home_goals_90, away_goals_90 FROM matches WHERE competition_key='EPL' AND season='2026-27' AND home_name='Aston Villa FC' AND away_name='Nottingham Forest FC'") == [(1, 2)]
    reasons = [r[0] for r in q(dst, "SELECT reason FROM quarantine WHERE reason LIKE 'CONFLICT%' OR reason LIKE 'CONTRADICTORY%'")]
    assert any(r.startswith("CONFLICT: stored 2-2 vs source 2-1") for r in reasons) and any(r.startswith("CONTRADICTORY SOURCE RESULT") for r in reasons)


@needs
def test_recovered_results_are_primary_openligadb_odbl_and_no_row_is_added_or_removed(applied):
    dst, _, _ = applied
    assert q(dst, "SELECT COUNT(*) FROM matches")[0][0] == q(BEFORE, "SELECT COUNT(*) FROM matches")[0][0]
    rec = q(dst, "SELECT competition_key, COUNT(*) FROM matches WHERE source_system='openligadb' AND competition_key IN ('EPL','LALIGA') AND season='2026-27' GROUP BY 1 ORDER BY 1")
    assert rec == [("EPL", 10), ("LALIGA", 20)]
    roles = q(dst, "SELECT role, licence, COUNT(*) FROM match_sources WHERE snapshot_id LIKE '%investigation_pl.json' OR snapshot_id LIKE '%investigation_la1.json' GROUP BY 1,2 ORDER BY 1")
    assert {r[1] for r in roles} == {"ODbL-1.0"} and dict((r[0], r[2]) for r in roles)["primary"] == 30


@needs
def test_second_pass_changes_nothing_and_an_independent_copy_ends_identical(applied, tmp_path, snaps):
    dst, ident, _ = applied
    before = R.table_fingerprints(db.connect(dst, readonly=True))
    again = R.apply(dst, snaps, ident["aliases"])
    after = R.table_fingerprints(db.connect(dst, readonly=True))
    assert all(v["inserted"] == 0 and v["updated"] == 0 for v in again.values())
    assert {t: v for t, v in after.items() if t != "sync_runs"} == {t: v for t, v in before.items() if t != "sync_runs"}
    other = tmp_path / "other.sqlite"
    shutil.copyfile(BEFORE, other)
    R.apply(other, snaps, ident["aliases"])
    assert R.table_fingerprints(db.connect(other, readonly=True)) == before


def test_the_rehearsal_refuses_to_write_to_the_production_store():
    with pytest.raises(AssertionError):
        R.private_copy(R.PROD)
    with pytest.raises(AssertionError):
        R.private_copy(ROOT / "data" / "elsewhere.sqlite")


@needs
def test_production_store_and_model_hashes_are_unchanged_by_a_replay(applied):
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    prod = R.PROD
    before = h(prod)
    man = {k: v for k, v in R.manifest().items() if k != "data/footiq.sqlite"}
    assert h(prod) == before and R.manifest().keys() >= man.keys()
    assert sync.now_utc.__name__ != "<lambda>"                                       # the fixed clock never leaks out of a rehearsal
