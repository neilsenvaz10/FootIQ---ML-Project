"""Two-part integrity baseline of a FootIQ results store (Phase 4.8C). Read-only: the file is opened with SQLite mode=ro.

  1. PHYSICAL hash: SHA-256 of the database file's bytes. Detects that anything wrote to the file (a log row, a checkpoint, a vacuum).
  2. LOGICAL hash (algorithm `footiq-logical-v1`, below): detects that the business data changed. It survives journal mode, page layout, VACUUM and row order.

Logical algorithm (exactly):
  * Tables: every row of `sqlite_master` with type 'table' whose name does not start with 'sqlite_', in ascending name order. The schema text of each table
    (sqlite_master.sql, whitespace-collapsed) is hashed too, so a changed column is a change.
  * Rows: all columns in table order, nothing dropped. Each value is normalised: NULL -> null, int -> int, float -> its Python repr as a string "f:<repr>",
    text -> text, blob -> "b:<hex>". A row becomes the compact JSON array of its values (ensure_ascii=False, separators (",", ":")).
  * Ordering: rows are sorted by that JSON string (a total order, so ties and rowid never matter).
  * Table hash: SHA-256 over "<table>\\n" + schema_hash + "\\n" + for each row (json + "\\n").
  * Combined: SHA-256 over one line per table "<table>:<row count>:<table hash>\\n".
  * Exclusions (the ONLY ones, listed in OPERATIONAL_EXCLUSIONS): rows of `sync_runs` with run_id > 7. Runs 1-7 are the baseline import, the early checks and the
    2026-10-25 production import and ARE hashed. Rows after them are operational diary lines (start-up checks); no match, fixture, prediction, forecast, simulation,
    team, alias, quarantine or snapshot row is ever excluded. Excluded rows are listed (id, kind, outcome, started) in the report so nothing is hidden.
A legitimately approved import adds sync_runs rows and match rows: it creates a NEW baseline (version), never a silent edit of this one.

    python app/store/baseline_hash.py <store.sqlite> [last_baseline_run_id]      prints the JSON report (default 7 = baseline v2)
"""
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

ALGORITHM = "footiq-logical-v1"
LAST_BASELINE_RUN_ID = 7            # baseline v2 (Phase 4.8C); baseline v3 (Phase 4.8D) passes the id of its last import run instead: the algorithm is the same, only the cut-off differs
OPERATIONAL_EXCLUSIONS = {"sync_runs": f"run_id > {LAST_BASELINE_RUN_ID}"}


def _norm(v):
    if v is None or isinstance(v, (int, str)):
        return v
    if isinstance(v, float):
        return "f:" + repr(v)
    if isinstance(v, (bytes, bytearray)):
        return "b:" + bytes(v).hex()
    return str(v)


def physical_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def logical(path, last_baseline_run_id: int = LAST_BASELINE_RUN_ID) -> dict:
    exclusions = {"sync_runs": f"run_id > {int(last_baseline_run_id)}"}
    conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    try:
        tables, combined, excluded = {}, hashlib.sha256(), []
        for name, sql in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
            schema_hash = hashlib.sha256(re.sub(r"\s+", " ", sql or "").encode()).hexdigest()
            query = f'SELECT * FROM "{name}"'
            if name in exclusions:
                query += f" WHERE NOT ({exclusions[name]})"
                for r in conn.execute(f'SELECT run_id, kind, outcome, started_utc FROM "{name}" WHERE {exclusions[name]} ORDER BY run_id'):
                    excluded.append(dict(table=name, run_id=r[0], kind=r[1], outcome=r[2], started_utc=r[3]))
            lines = sorted(json.dumps([_norm(v) for v in row], ensure_ascii=False, separators=(",", ":")) for row in conn.execute(query))
            h = hashlib.sha256((name + "\n" + schema_hash + "\n").encode())
            for line in lines:
                h.update((line + "\n").encode())
            tables[name] = dict(rows=len(lines), sha256=h.hexdigest())
            combined.update(f"{name}:{len(lines)}:{h.hexdigest()}\n".encode())
        return dict(algorithm=ALGORITHM, logical_sha256=combined.hexdigest(), tables=tables, exclusions=exclusions, excluded_rows=excluded,
                    integrity_check=conn.execute("PRAGMA integrity_check").fetchone()[0], journal_mode=conn.execute("PRAGMA journal_mode").fetchone()[0])
    finally:
        conn.close()


def baseline(path, last_baseline_run_id: int = LAST_BASELINE_RUN_ID) -> dict:
    out = logical(path, last_baseline_run_id)
    out["physical_sha256"] = physical_sha256(path)
    out["physical_bytes"] = Path(path).stat().st_size
    return out


if __name__ == "__main__":
    print(json.dumps(baseline(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else LAST_BASELINE_RUN_ID), indent=1, ensure_ascii=False))
