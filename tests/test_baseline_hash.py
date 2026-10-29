"""Phase 4.8C: the logical baseline hash detects business-data changes and ignores only the documented operational log rows. Synthetic stores; no production file."""
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from store import baseline_hash as BH  # noqa: E402
from store import db  # noqa: E402


@pytest.fixture
def store(tmp_path):
    p = tmp_path / "s.sqlite"
    c = db.connect(p)
    db.init(c)
    c.execute("INSERT INTO teams(entity_id, display_name, country) VALUES ('CLUB:T:a','A FC','T'),('CLUB:T:b','B FC','T')")
    for i in range(1, 8):
        c.execute("INSERT INTO sync_runs(run_id, kind, source, started_utc, outcome) VALUES (?,?,?,?,?)", (i, "baseline_import", "x", f"2026-10-25T08:0{i}:00Z", "ok"))
    c.commit()
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()
    return p


def mutate(p, sql, *a):
    c = sqlite3.connect(p)
    c.execute(sql, a)
    c.commit()
    c.close()


def test_logical_hash_ignores_only_operational_log_rows_after_the_baseline_runs(store):
    base = BH.logical(store)["logical_sha256"]
    mutate(store, "INSERT INTO sync_runs(run_id, kind, source, started_utc, outcome) VALUES (8,'startup_check','all approved','2026-10-27T10:37:37Z','skipped_live_disabled')")
    after = BH.logical(store)
    assert after["logical_sha256"] == base
    assert [r["run_id"] for r in after["excluded_rows"]] == [8] and after["exclusions"] == {"sync_runs": "run_id > 7"}


def test_physical_hash_sees_the_log_row_that_the_logical_hash_ignores(store):
    p1 = BH.physical_sha256(store)
    mutate(store, "INSERT INTO sync_runs(run_id, kind, source, started_utc, outcome) VALUES (8,'startup_check','all approved','2026-10-27T10:37:37Z','skipped_live_disabled')")
    c = sqlite3.connect(store)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()
    assert BH.physical_sha256(store) != p1


@pytest.mark.parametrize("sql", [
    "UPDATE teams SET display_name='A FC (changed)' WHERE entity_id='CLUB:T:a'",
    "INSERT INTO teams(entity_id, display_name, country) VALUES ('CLUB:T:c','C FC','T')",
    "DELETE FROM teams WHERE entity_id='CLUB:T:b'",
    "UPDATE sync_runs SET outcome='error' WHERE run_id=3",              # a baseline-era log row is business history, not excluded
    "INSERT INTO quarantine(run_id, source, source_ref, reason, created_utc) VALUES (3,'s','r','CONFLICT','2026-10-27T00:00:00Z')",
])
def test_any_change_to_business_data_or_baseline_rows_changes_the_logical_hash(store, sql):
    base = BH.logical(store)["logical_sha256"]
    mutate(store, sql)
    assert BH.logical(store)["logical_sha256"] != base


def test_hash_does_not_depend_on_row_order_page_layout_or_journal_mode(store, tmp_path):
    base = BH.logical(store)["logical_sha256"]
    c = sqlite3.connect(store)
    c.execute("DELETE FROM teams")
    c.execute("INSERT INTO teams(entity_id, display_name, country) VALUES ('CLUB:T:b','B FC','T')")      # reversed insertion order
    c.execute("INSERT INTO teams(entity_id, display_name, country) VALUES ('CLUB:T:a','A FC','T')")
    c.commit()
    c.execute("VACUUM")
    c.execute("PRAGMA journal_mode=DELETE")
    c.close()
    assert BH.logical(store)["logical_sha256"] == base


def test_a_schema_change_is_a_change_and_the_report_lists_every_table(store):
    base = BH.logical(store)
    mutate(store, "ALTER TABLE teams ADD COLUMN note TEXT")
    assert BH.logical(store)["logical_sha256"] != base["logical_sha256"]
    assert set(base["tables"]) >= {"matches", "teams", "sync_runs", "quarantine", "forecasts", "forecast_runs", "team_aliases", "match_sources", "simulation_runs"}
    assert base["algorithm"] == "footiq-logical-v1" and base["integrity_check"] == "ok"
