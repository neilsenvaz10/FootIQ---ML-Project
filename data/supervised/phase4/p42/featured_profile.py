"""Where do the ~120 ms of featured.build go? (private copy, read-only)"""
import cProfile
import io
import os
import pstats
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
import featured  # noqa: E402
from store import db, sync  # noqa: E402

path = Path(os.environ["FOOTIQ_STORE_PATH"])
assert "rehearsal" in path.parts
conn = db.connect(path, readonly=True)
cfg = sync.SyncConfig.load()
now = datetime.now(timezone.utc)

# per statement
stmts = {}
for name, sql, params in [("sync.status (all 11 competitions)", None, None)]:
    t = time.perf_counter()
    for _ in range(5):
        sync.status(conn, cfg, now)
    stmts[name] = round((time.perf_counter() - t) / 5 * 1000, 1)
for key in ("EPL", "SERIEA"):
    t = time.perf_counter(); [conn.execute(featured.NEWEST_SEASON_SQL, (key,)).fetchone() for _ in range(5)]; stmts[f"{key} newest season"] = round((time.perf_counter() - t) / 5 * 1000, 2)
    t = time.perf_counter(); [conn.execute(featured.UPCOMING_SQL, (key, "2026-27", now.date().isoformat(), 12)).fetchall() for _ in range(5)]; stmts[f"{key} upcoming"] = round((time.perf_counter() - t) / 5 * 1000, 2)
    t = time.perf_counter(); [conn.execute(featured.RESULTS_SQL, (key, "2026-27", 12)).fetchall() for _ in range(5)]; stmts[f"{key} results"] = round((time.perf_counter() - t) / 5 * 1000, 2)
    t = time.perf_counter(); [conn.execute(featured.SEASON_SQL, (key, "2026-27")).fetchall() for _ in range(5)]; stmts[f"{key} season rows"] = round((time.perf_counter() - t) / 5 * 1000, 2)
print("ms per call:", stmts)

prof = cProfile.Profile()
prof.enable()
for _ in range(5):
    featured.build(conn, cfg, now)
prof.disable()
buf = io.StringIO()
pstats.Stats(prof, stream=buf).sort_stats("cumtime").print_stats(14)
print("\n".join(line for line in buf.getvalue().splitlines() if line.strip())[-2600:])
