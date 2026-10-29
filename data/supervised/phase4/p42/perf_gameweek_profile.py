"""P4.2 performance investigation, step 2: profile /api/gameweek (gameweeks.gameweek_fixtures) on a PRIVATE COPY of the production store.

    FOOTIQ_STORE_PATH=<private copy> python data/supervised/phase4/p42/perf_gameweek_profile.py [matchday]

Reports wall time, the number of SQL statements, where the time goes (cProfile, top entries by own time), and the time of the team_form
statements alone. It changes nothing: the store is opened read-only.
"""
import cProfile
import io
import json
import os
import pstats
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
import gameweeks  # noqa: E402
from store import db  # noqa: E402

path = Path(os.environ["FOOTIQ_STORE_PATH"])
assert "rehearsal" in path.parts, "refusing to run against anything but a private copy"
matchday = int(sys.argv[1]) if len(sys.argv) > 1 else 9
today = gameweeks.today_utc()

conn = db.connect(path, readonly=True)
statements = Counter()
conn.set_trace_callback(lambda sql: statements.update([sql.strip().split()[0].upper() + " " + (sql.split("FROM")[1].split()[0] if "FROM" in sql else "")]))

# wall time of the whole view, three runs
runs = []
for _ in range(3):
    t = time.perf_counter()
    view = gameweeks.gameweek_fixtures(conn, "EPL", "2026-27", matchday, today)
    runs.append(time.perf_counter() - t)

# where the time goes
prof = cProfile.Profile()
prof.enable()
gameweeks.gameweek_fixtures(conn, "EPL", "2026-27", matchday, today)
prof.disable()
buf = io.StringIO()
stats = pstats.Stats(prof, stream=buf).sort_stats("tottime")
stats.print_stats(8)
top = [line for line in buf.getvalue().splitlines() if line.strip()][-12:]

# the team_form statements on their own
tf_times = []
for fx in view["fixtures"]:
    for ent in (fx["home_entity"], fx["away_entity"]):
        t = time.perf_counter()
        gameweeks.team_form(conn, "england:1-premierleague" if False else conn.execute("SELECT competition_id FROM competitions WHERE competition_key='EPL'").fetchone()[0], ent, fx["date"])
        tf_times.append(time.perf_counter() - t)

out = dict(today_utc=today.isoformat(), matchday=matchday, fixtures=len(view["fixtures"]), seconds_per_run=[round(x, 2) for x in runs],
           team_form_calls=len(tf_times), team_form_seconds_total=round(sum(tf_times), 2), team_form_ms_each=dict(min=round(min(tf_times) * 1000), median=round(sorted(tf_times)[len(tf_times) // 2] * 1000), max=round(max(tf_times) * 1000)),
           share_of_run_spent_in_team_form=round(sum(tf_times) / (sum(runs) / len(runs)), 2), sql_statements_over_3_runs=dict(statements.most_common(8)), cprofile_top_by_own_time=top)
print(json.dumps(out, indent=1))
