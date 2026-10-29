"""Does the speed of ONE team_form call (the statement behind /api/gameweek) depend on what else the machine is doing? Private copy, read-only.

    FOOTIQ_STORE_PATH=data/supervised/rehearsal/phase4_p42.sqlite .venv/Scripts/python.exe -X utf8 data/supervised/phase4/p42/perf_load_sensitivity.py LABEL

Same statement, same database file, same process; run it while something else is busy and again when the machine is idle and compare."""
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
import gameweeks  # noqa: E402
from store import db  # noqa: E402

path = Path(os.environ["FOOTIQ_STORE_PATH"])
assert "rehearsal" in path.parts, "private copies only"
conn = db.connect(path, readonly=True)
comp_id, entity = conn.execute("SELECT competition_id, home_entity_id FROM matches WHERE competition_key='EPL' AND season='2026-27' AND home_entity_id IS NOT NULL LIMIT 1").fetchone()
ms = []
for _ in range(10):
    t = time.perf_counter()
    gameweeks.team_form(conn, comp_id, entity, "2026-10-31")
    ms.append((time.perf_counter() - t) * 1000)
label = sys.argv[1] if len(sys.argv) > 1 else "run"
res = dict(label=label, calls=len(ms), ms=[round(x) for x in ms], median_ms=round(statistics.median(ms)), min_ms=round(min(ms)), max_ms=round(max(ms)), at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
print(json.dumps(res))
with open(Path(__file__).with_name("perf_load_sensitivity.jsonl"), "a", encoding="utf-8") as fh:
    fh.write(json.dumps(res) + "\n")
