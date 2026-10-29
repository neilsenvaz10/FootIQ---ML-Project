"""P4.2 performance investigation, step 1: what is in the store and how do the gameweek queries run? Read-only on a PRIVATE COPY of the production store.

    FOOTIQ_STORE_PATH=<private copy> python data/supervised/phase4/p42/perf_store_inspect.py
"""
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
from store import db  # noqa: E402

path = Path(os.environ["FOOTIQ_STORE_PATH"])
assert "rehearsal" in path.parts, "refusing to run against anything but a private copy"
conn = db.connect(path, readonly=True)
out = {"file_bytes": path.stat().st_size, "page_size": conn.execute("PRAGMA page_size").fetchone()[0], "page_count": conn.execute("PRAGMA page_count").fetchone()[0],
       "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0], "cache_size_pages": conn.execute("PRAGMA cache_size").fetchone()[0],
       "sqlite_version": sqlite3.sqlite_version}

# bytes per table and per index (dbstat is compiled into the SQLite that ships with Python on Windows when available)
try:
    rows = conn.execute("SELECT name, SUM(pgsize) AS bytes, COUNT(*) AS pages FROM dbstat GROUP BY name ORDER BY bytes DESC").fetchall()
    out["bytes_by_object"] = [dict(name=r[0], MB=round(r[1] / 1e6, 2), pages=r[2]) for r in rows[:14]]
except sqlite3.OperationalError as exc:
    out["bytes_by_object"] = f"dbstat unavailable: {exc}"

out["row_counts"] = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("matches", "teams", "team_aliases", "match_sources", "source_snapshots", "sync_runs", "quarantine", "forecast_runs", "forecasts", "simulation_runs")}
out["indexes_on_matches"] = [dict(name=r[1], unique=bool(r[2])) for r in conn.execute("PRAGMA index_list(matches)")]
for ix in out["indexes_on_matches"]:
    ix["columns"] = [r[2] for r in conn.execute(f"PRAGMA index_info({ix['name']})")]

# average stored size of one matches row
try:
    mb = conn.execute("SELECT SUM(pgsize) FROM dbstat WHERE name='matches'").fetchone()[0]
    out["avg_bytes_per_matches_row"] = round(mb / out["row_counts"]["matches"])
except sqlite3.OperationalError:
    pass

comp_id = conn.execute("SELECT competition_id FROM competitions WHERE competition_key='EPL'").fetchone()[0]
ent = conn.execute("SELECT home_entity_id FROM matches WHERE competition_key='EPL' AND season='2026-27' AND home_entity_id IS NOT NULL LIMIT 1").fetchone()[0]
queries = {
    "team_form (one call per team per fixture)": ("SELECT m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final, t1.display_name AS hn, t2.display_name AS an FROM matches m "
        "LEFT JOIN teams t1 ON t1.entity_id=m.home_entity_id LEFT JOIN teams t2 ON t2.entity_id=m.away_entity_id "
        "WHERE m.competition_id=? AND (m.home_entity_id=? OR m.away_entity_id=?) AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL "
        "ORDER BY m.match_date DESC, m.record_id DESC LIMIT ?", (comp_id, ent, ent, "2026-10-31", 5)),
    "_fixture_rows (once per request)": ("SELECT m.*, t1.display_name AS home_display, t2.display_name AS away_display FROM matches m LEFT JOIN teams t1 ON t1.entity_id = m.home_entity_id "
        "LEFT JOIN teams t2 ON t2.entity_id = m.away_entity_id WHERE m.competition_key=? AND m.season=? AND m.kind='club' ORDER BY m.match_date, m.record_id", ("EPL", "2026-27")),
    "seasons() DISTINCT": ("SELECT DISTINCT season FROM matches WHERE competition_key=? AND kind='club' ORDER BY season DESC", ("EPL",)),
    "competition_latest_result": ("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND status IN ('completed','awarded')", ("EPL",)),
}
out["plans_and_timings"] = {}
for name, (sql, params) in queries.items():
    plan = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + sql, params)]
    times = []
    for _ in range(5):
        t = time.perf_counter()
        n = len(conn.execute(sql, params).fetchall())
        times.append(time.perf_counter() - t)
    out["plans_and_timings"][name] = dict(plan=plan, rows=n, ms_runs=[round(x * 1000, 1) for x in times])
print(json.dumps(out, indent=1))
