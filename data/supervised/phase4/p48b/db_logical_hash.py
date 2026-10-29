"""Read-only logical fingerprint of a FootIQ store: one SHA-256 per table plus a combined hash that EXCLUDES the operational log rows written after the 2026-10-25 import
(sync_runs with run_id > 7). Two files with the same logical hash hold the same football data, provenance and quarantine, whatever their journal state or byte layout.

    .venv\Scripts\python.exe data\supervised\phase4\p48b\db_logical_hash.py <store.sqlite>

Opens the file with mode=ro; pass a COPY if the original must not even gain empty -shm/-wal files.
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

LAST_IMPORT_RUN = 7


def fingerprint(path: Path) -> dict:
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    tables, comb = {}, hashlib.sha256()
    try:
        for (t,) in c.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by 1").fetchall():
            q = f'select * from "{t}" order by 1,2' if t != "sync_runs" else f"select * from sync_runs where run_id<={LAST_IMPORT_RUN} order by 1"
            h, n = hashlib.sha256(), 0
            for r in c.execute(q):
                h.update(repr((t, tuple(r))).encode())
                comb.update(repr((t, tuple(r))).encode())
                n += 1
            tables[t] = dict(rows=n, sha256=h.hexdigest())
        extra = c.execute("select count(*), max(run_id) from sync_runs").fetchone()
        return dict(file=str(path), journal_mode=c.execute("pragma journal_mode").fetchone()[0], integrity_check=c.execute("pragma integrity_check").fetchone()[0],
                    logical_sha256=comb.hexdigest(), tables=tables, sync_runs_total=extra[0], sync_runs_after_import=extra[0] - min(extra[0], LAST_IMPORT_RUN),
                    newest_match_last_changed_utc=c.execute("select max(last_changed_utc) from matches").fetchone()[0])
    finally:
        c.close()


if __name__ == "__main__":
    print(json.dumps(fingerprint(Path(sys.argv[1])), indent=1))
