"""P4.2 performance investigation, step 4: cost of the pieces Home already uses or could reuse (private copy, read-only)."""
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
import analytics  # noqa: E402
import config as C  # noqa: E402
from store import db, sync, views  # noqa: E402

path = Path(os.environ["FOOTIQ_STORE_PATH"])
assert "rehearsal" in path.parts
conn = db.connect(path, readonly=True)
out = {"has_planner_statistics_table": bool(conn.execute("SELECT 1 FROM sqlite_master WHERE name='sqlite_stat1'").fetchone())}


def timeit(fn, reps=7):
    ts = []
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t) * 1000)
    return dict(median_ms=round(statistics.median(ts), 1), min_ms=round(min(ts), 1), max_ms=round(max(ts), 1))


cfg = sync.SyncConfig.load()
out["sync.status (what /api/sync/status runs; 11 competitions)"] = timeit(lambda: sync.status(conn, cfg))
out["views.freshness alone"] = timeit(lambda: views.freshness(conn))
plan = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN SELECT MAX(CASE WHEN status IN ('completed','awarded') THEN match_date END), SUM(status='awaiting_result'), SUM(status='scheduled'), MAX(CASE WHEN status='scheduled' THEN match_date END), MIN(CASE WHEN status='awaiting_result' THEN match_date END) FROM matches WHERE competition_key=?", ("EPL",))]
out["views.freshness plan (one competition)"] = plan
rows_epl = conn.execute("SELECT COUNT(*) FROM matches WHERE competition_key='EPL'").fetchone()[0]
out["rows scanned by views.freshness per competition (EPL)"] = rows_epl

t = time.perf_counter()
analytics.matches()
out["analytics.matches() first call (loads the 20.5k-row dashboard frame)"] = round((time.perf_counter() - t) * 1000)
out["analytics.matches() cached"] = timeit(lambda: analytics.matches())
out["analytics.standings(EPL, 2026-27)"] = timeit(lambda: analytics.standings("EPL", "2026-27"))
out["analytics.recent_results(EPL, 2026-27)"] = timeit(lambda: analytics.recent_results("EPL", "2026-27"))
out["analytics.season_coverage(EPL)"] = timeit(lambda: analytics.season_coverage("EPL"))
out["analytics.audit()"] = timeit(lambda: analytics.audit())
print(json.dumps(out, indent=1))
