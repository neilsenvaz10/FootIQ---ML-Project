"""Cold and warm cost of one gameweek page (EPL matchday 9, 10 fixtures) with the old statement and with variant B, idle and under CPU load. Private copy, read-only.

    FOOTIQ_STORE_PATH=<private copy> .venv/Scripts/python.exe -X utf8 data/supervised/phase4/p43/bench_gameweek.py

Cold = the first call in a fresh process on a fresh connection (SQLite's page cache empty). Warm = the next five calls on that connection. Five fresh processes per case."""
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

if len(sys.argv) > 2 and sys.argv[1] == "--child":
    from common import private_copy_path, team_form_old  # noqa: E402
    import gameweeks as gw  # noqa: E402
    from store import db  # noqa: E402

    if sys.argv[2] == "old":
        gw.team_form = team_form_old
    conn = db.connect(private_copy_path(), readonly=True)
    times = []
    for _ in range(6):
        t = time.perf_counter()
        gw.gameweek_fixtures(conn, "EPL", "2026-27", 9, date(2026, 10, 27))
        times.append(time.perf_counter() - t)
    print(json.dumps(times))
    sys.exit(0)


def run(impl):
    out = subprocess.run([sys.executable, "-X", "utf8", __file__, "--child", impl], capture_output=True, text=True, env=os.environ).stdout
    return json.loads(out.strip().splitlines()[-1])


def summarise(label, runs):
    cold = [r[0] for r in runs]
    warm = [x for r in runs for x in r[1:]]
    return {label: dict(cold_s=dict(median=round(statistics.median(cold), 3), min=round(min(cold), 3), max=round(max(cold), 3)),
                        warm_s=dict(median=round(statistics.median(warm), 3), min=round(min(warm), 3), max=round(max(warm), 3)))}


res = {}
for impl in ("old", "new"):
    res |= summarise(f"{impl}, idle", [run(impl) for _ in range(5)])
burners = [subprocess.Popen([sys.executable, "-c", "import time; t=time.time()\nwhile time.time()-t < 150: pass"]) for _ in range(24)]
try:
    time.sleep(3)
    for impl in ("old", "new"):
        res |= summarise(f"{impl}, 24 busy processes", [run(impl) for _ in range(3)])
finally:
    for b in burners:
        b.kill()
(HERE / "bench_gameweek.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
