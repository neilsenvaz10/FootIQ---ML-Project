"""Query plans, statement count, timing and a look at the payload of app/featured.py on a PRIVATE COPY of the production store (read-only)."""
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
import featured  # noqa: E402
from store import db, sync  # noqa: E402

path = Path(os.environ["FOOTIQ_STORE_PATH"])
assert "rehearsal" in path.parts, "private copies only"
conn = db.connect(path, readonly=True)
cfg = sync.SyncConfig.load()
now = datetime.now(timezone.utc)

params = {"newest_season": ("EPL",), "upcoming": ("EPL", "2026-27", now.date().isoformat(), 12), "results": ("EPL", "2026-27", 12), "season_rows": ("EPL", "2026-27")}
plans = {}
for name, sql in featured.STATEMENTS.items():
    plans[name] = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + sql, params[name])]

# the same statements WITHOUT the unary plus, to show what the planner would do on its own
bare = {name: sql.replace("+m.", "m.").replace("+kind", "kind") for name, sql in featured.STATEMENTS.items()}
bare_plans = {name: [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + sql, params[name])] for name, sql in bare.items()}

counter = []
conn.set_trace_callback(lambda sql: counter.append(sql.split()[0].upper()))
t = time.perf_counter()
payload = featured.build(conn, cfg, now)
first_ms = (time.perf_counter() - t) * 1000
statements = len(counter)
conn.set_trace_callback(None)

times = []
for _ in range(15):
    t = time.perf_counter()
    featured.build(conn, cfg, now)
    times.append((time.perf_counter() - t) * 1000)

out = dict(now=now.isoformat(), plans=plans, plans_without_the_unary_plus=bare_plans, statements_per_build=statements, build_ms_first=round(first_ms, 1),
           build_ms_median=round(statistics.median(times), 1), build_ms_max=round(max(times), 1))
brief = dict(featured=payload["featured"], empty_state=payload["empty_state"], upcoming_count=len(payload["upcoming"]), upcoming_first=payload["upcoming"][:2], results_count=len(payload["recent_results"]),
             results_first=payload["recent_results"][:2], leagues=payload["leagues"], payload_bytes=len(json.dumps(payload)))
print(json.dumps(out, indent=1))
print(json.dumps(brief, indent=1, default=str)[:6000])
