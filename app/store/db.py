"""SQLite schema and connection helpers. Standard library only.

The database file is an operational cache: it can always be rebuilt from the repository's CSV baseline with `python app/store/build.py`.
It is git-ignored (see .gitignore). Nothing here writes to research folders or model artifacts.
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import os

DEFAULT_PATH = Path(os.environ.get("FOOTIQ_STORE_PATH") or ROOT / "data" / "footiq.sqlite")   # FOOTIQ_STORE_PATH lets a demo or test use a private copy
SCHEMA_VERSION = 1

MATCH_STATUSES = ("completed", "awarded", "abandoned", "scheduled", "awaiting_result", "postponed", "cancelled")

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS competitions (
  competition_id TEXT PRIMARY KEY, competition_key TEXT, name TEXT, comp_group TEXT, competition_type TEXT, country TEXT, tier REAL, kind TEXT
);

-- model_*_entity: the identity-corrected ids the frozen models were trained with (they differ from the dashboard ids in 795 baseline rows)
-- one row per club / national team entity (the project's canonical ids, e.g. CLUB:ENG:arsenal-fc)
CREATE TABLE IF NOT EXISTS teams (entity_id TEXT PRIMARY KEY, display_name TEXT, country TEXT);

-- every spelling a source uses, per competition; never fuzzy-matched silently (method records how it was resolved)
CREATE TABLE IF NOT EXISTS team_aliases (
  competition_id TEXT NOT NULL, source TEXT NOT NULL, alias TEXT NOT NULL, entity_id TEXT NOT NULL REFERENCES teams(entity_id), method TEXT,
  PRIMARY KEY (competition_id, source, alias)
);

-- immutable record of every payload / file the data came from
CREATE TABLE IF NOT EXISTS source_snapshots (
  snapshot_id TEXT PRIMARY KEY, source TEXT NOT NULL, kind TEXT, url TEXT, path TEXT, sha256 TEXT, bytes INTEGER,
  retrieved_utc TEXT, revision TEXT, licence TEXT, attribution TEXT
);

CREATE TABLE IF NOT EXISTS matches (
  record_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('club','international')),
  competition_id TEXT, competition_key TEXT, season TEXT, stage TEXT, matchday_label TEXT, matchday_no INTEGER,
  match_date TEXT, kickoff_local TEXT, kickoff_utc TEXT, time_precision TEXT,
  home_entity_id TEXT, away_entity_id TEXT, model_home_entity TEXT, model_away_entity TEXT, home_name TEXT, away_name TEXT,
  status TEXT NOT NULL CHECK (status IN {MATCH_STATUSES!r}),
  home_goals_final INTEGER, away_goals_final INTEGER, home_goals_90 INTEGER, away_goals_90 INTEGER,
  label_90_status TEXT, outcome TEXT, shootout_winner TEXT, neutral TEXT,
  rated INTEGER, regular INTEGER, in_universe INTEGER NOT NULL DEFAULT 0, tier REAL, competition_type TEXT,
  source_system TEXT, licence TEXT, src_order INTEGER,
  first_seen_utc TEXT, last_changed_utc TEXT, change_count INTEGER NOT NULL DEFAULT 0, content_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_matches_comp_season_date ON matches (competition_id, season, match_date);
CREATE INDEX IF NOT EXISTS idx_matches_key ON matches (competition_key, season);
CREATE INDEX IF NOT EXISTS idx_matches_pair ON matches (competition_id, season, home_entity_id, away_entity_id);
CREATE INDEX IF NOT EXISTS idx_matches_status_date ON matches (status, match_date);

-- which source(s) say what about a match; a source_ref is unique, so the same payload can never create a second row
CREATE TABLE IF NOT EXISTS match_sources (
  source TEXT NOT NULL, source_ref TEXT NOT NULL, record_id TEXT NOT NULL REFERENCES matches(record_id),
  role TEXT NOT NULL DEFAULT 'primary' CHECK (role IN ('primary','confirmation')),
  snapshot_id TEXT, licence TEXT, retrieved_utc TEXT, source_revision TEXT, provenance TEXT,
  PRIMARY KEY (source, source_ref)
);
CREATE INDEX IF NOT EXISTS idx_match_sources_record ON match_sources (record_id);

CREATE TABLE IF NOT EXISTS sync_runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, source TEXT, competition_key TEXT,
  started_utc TEXT NOT NULL, finished_utc TEXT, outcome TEXT NOT NULL, requests INTEGER DEFAULT 0,
  inserted INTEGER DEFAULT 0, updated INTEGER DEFAULT 0, unchanged INTEGER DEFAULT 0, quarantined INTEGER DEFAULT 0,
  latest_result_date TEXT, detail TEXT
);
CREATE TABLE IF NOT EXISTS sync_errors (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER REFERENCES sync_runs(run_id), source TEXT, at_utc TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS quarantine (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, source TEXT, source_ref TEXT, reason TEXT, payload TEXT, created_utc TEXT
);
CREATE TABLE IF NOT EXISTS source_state (source TEXT NOT NULL, scope TEXT NOT NULL, state_json TEXT, updated_utc TEXT, PRIMARY KEY (source, scope));

-- reserved for Phases 2 and 3 (created empty now so the schema can be reviewed as a whole)
CREATE TABLE IF NOT EXISTS forecast_runs (
  forecast_run_id INTEGER PRIMARY KEY AUTOINCREMENT, created_utc TEXT NOT NULL, competition_key TEXT, season TEXT, matchday_label TEXT,
  model_id TEXT, model_artifact_sha256 TEXT, data_cutoff_date TEXT, data_cutoff_note TEXT, user_action TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS forecasts (
  forecast_id INTEGER PRIMARY KEY AUTOINCREMENT, forecast_run_id INTEGER NOT NULL REFERENCES forecast_runs(forecast_run_id), record_id TEXT NOT NULL REFERENCES matches(record_id),
  p_home REAL, p_draw REAL, p_away REAL, model_variant TEXT, feature_snapshot_json TEXT, feature_sha256 TEXT,
  made_before_kickoff TEXT CHECK (made_before_kickoff IN ('yes','no','unknown')), reliability TEXT CHECK (reliability IN ('full','provisional','unavailable')), flags_json TEXT
);
CREATE TABLE IF NOT EXISTS simulation_runs (
  simulation_run_id INTEGER PRIMARY KEY AUTOINCREMENT, created_utc TEXT NOT NULL, competition_key TEXT, season TEXT, n_simulations INTEGER, seed INTEGER,
  model_id TEXT, data_cutoff_date TEXT, assumptions_json TEXT, result_json TEXT
);
"""


def connect(path=None, readonly: bool = False) -> sqlite3.Connection:
    path = Path(path or DEFAULT_PATH)
    if readonly:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        if conn.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":      # asking is free; switching rewrites the file header
            conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
    conn.commit()


def exists(path=None) -> bool:
    p = Path(path or DEFAULT_PATH)
    return p.exists() and p.stat().st_size > 0
