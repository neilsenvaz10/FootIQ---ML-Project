"""Phase 4.8B: do repeated cold starts of the backend change the database? Runs on a PRIVATE COPY of the production store (the original is only read by a file copy).

    .venv\Scripts\python.exe data\supervised\phase4\p48b\db_startup_audit.py [starts]

Per start: SHA-256 of the main file, the sidecar files (-wal/-shm) with size and hash, sync_runs row count, journal mode and the newest matches.last_changed_utc,
before and after the backend ran (health ready, a set of read endpoints called, 12 s idle past the 5 s start-up delay, clean stop).
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "data" / "supervised" / "phase4" / "p48b"
WORK = OUT / "startup_audit_copy"
PROD = ROOT / "data" / "footiq.sqlite"
PORT = 8123


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def state(db: Path) -> dict:
    side = {}
    for ext in ("-wal", "-shm"):
        f = Path(str(db) + ext)
        side[ext] = dict(exists=f.exists(), bytes=f.stat().st_size if f.exists() else None)
    c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        info = dict(sync_runs=c.execute("select count(*) from sync_runs").fetchone()[0], journal_mode=c.execute("pragma journal_mode").fetchone()[0],
                    newest_last_changed=c.execute("select max(last_changed_utc) from matches").fetchone()[0], matches=c.execute("select count(*) from matches").fetchone()[0])
    finally:
        c.close()
    return dict(main_sha256=sha(db), main_bytes=db.stat().st_size, sidecars=side, **info)


def get(path: str, timeout=60):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=timeout) as r:
        return json.loads(r.read())


def main(n: int):
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    copy = WORK / "footiq.sqlite"
    for ext in ("", "-wal", "-shm"):
        if Path(str(PROD) + ext).exists():
            shutil.copyfile(str(PROD) + ext, str(copy) + ext)
    report = dict(production_file_only_copied=True, source_sha256_at_start=sha(PROD), runs=[], start_state=state(copy))
    env = dict(os.environ, FOOTIQ_STORE_PATH=str(copy), PYTHONUTF8="1")
    for i in range(1, n + 1):
        before = state(copy)
        log = open(WORK / f"backend_{i}.log", "w")
        proc = subprocess.Popen([sys.executable, "-B", "-m", "uvicorn", "main:app", "--app-dir", str(ROOT / "app"), "--port", str(PORT), "--log-level", "warning"], env=env, stdout=log, stderr=log, cwd=str(ROOT))
        ready = False
        t0 = time.time()
        try:
            while time.time() - t0 < 180:
                try:
                    if get("/api/health", 5).get("club_prediction_ready"):
                        ready = True
                        break
                except Exception:
                    time.sleep(1)
            codes = {}
            for p in ("/api/sync/status", "/api/featured-fixture", "/api/matches?limit=20", "/api/competitions", "/api/gameweeks?key=EPL", "/api/gameweek?key=BUNDESLIGA&matchday=9", "/api/meta"):
                try:
                    get(p)
                    codes[p] = 200
                except Exception as exc:  # noqa: BLE001
                    codes[p] = str(exc)[:80]
            time.sleep(12)                                              # past the 5 s start-up-check delay; a periodic check would be far later
        finally:
            proc.terminate()
            try:
                proc.wait(30)
            except Exception:
                proc.kill()
            log.close()
        after = state(copy)
        report["runs"].append(dict(start=i, ready=ready, seconds_to_ready=round(time.time() - t0, 1) if ready else None, endpoints=codes, before=before, after=after,
                                   main_file_changed=before["main_sha256"] != after["main_sha256"], sync_runs_added=after["sync_runs"] - before["sync_runs"]))
    report["source_sha256_at_end"] = sha(PROD)
    report["production_unchanged_by_audit"] = report["source_sha256_at_start"] == report["source_sha256_at_end"]
    (OUT / "db_startup_audit.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    for r in report["runs"]:
        print(r["start"], "ready", r["ready"], "main_changed", r["main_file_changed"], "sync_runs_added", r["sync_runs_added"], "sidecars", r["after"]["sidecars"])
    print("production unchanged by audit:", report["production_unchanged_by_audit"])


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
