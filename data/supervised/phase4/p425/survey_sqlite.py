"""Phase 4.25: READ-ONLY survey of every .sqlite file in the project: size, sha256, content facts (opened with mode=ro&immutable=1, so no -wal / -shm file is touched). Writes sqlite_survey.csv.
Nothing is moved, changed or deleted."""
import csv
import hashlib
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
paths = sorted(p for p in ROOT.rglob("*.sqlite") if ".venv" not in p.parts and "node_modules" not in p.parts)
rows = []
for p in paths:
    st = p.stat()
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 23), b""):
            h.update(chunk)
    facts = dict(matches=None, ucl_2026_27=None, sync_runs=None, max_run=None, sims=None, quarantine=None, last_import=None, tables=None, error=None)
    try:
        c = sqlite3.connect(f"file:{p.as_posix()}?mode=ro&immutable=1", uri=True)
        tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        facts["tables"] = len(tabs)
        if "matches" in tabs:
            facts["matches"] = c.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
            facts["ucl_2026_27"] = c.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0]
        if "sync_runs" in tabs:
            facts["sync_runs"], facts["max_run"] = c.execute("SELECT COUNT(*), MAX(run_id) FROM sync_runs").fetchone()
            facts["last_import"] = c.execute("SELECT MAX(started_utc) FROM sync_runs").fetchone()[0]
        if "simulation_runs" in tabs:
            facts["sims"] = c.execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0]
        if "quarantine" in tabs:
            facts["quarantine"] = c.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
        c.close()
    except Exception as e:                                                                      # a damaged or non-store file is reported, not hidden
        facts["error"] = f"{type(e).__name__}: {e}"[:80]
    rel = p.relative_to(ROOT).as_posix()
    side = [x for x in (Path(str(p) + "-wal"), Path(str(p) + "-shm")) if x.exists()]
    rows.append(dict(path=rel, bytes=st.st_size, mtime=int(st.st_mtime), sha256=h.hexdigest(), sidecar_bytes=sum(x.stat().st_size for x in side), **facts))
    print(rel, st.st_size, h.hexdigest()[:10], facts["matches"], facts["max_run"], file=sys.stderr)
with open(HERE / "sqlite_survey.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(len(rows), "sqlite files,", round(sum(r["bytes"] for r in rows) / 1e9, 2), "GB")
