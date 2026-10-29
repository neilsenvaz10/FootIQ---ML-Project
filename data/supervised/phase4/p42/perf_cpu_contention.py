"""Does CPU contention change how long /api/gameweek takes? Same request, same backend (private copy), idle versus 24 busy processes on a 12-thread CPU.

    .venv/Scripts/python.exe -X utf8 data/supervised/phase4/p42/perf_cpu_contention.py

Read-only requests. The busy processes only spin; they are always terminated (try/finally) and stop by themselves after 60 seconds."""
import json
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).with_name("perf_cpu_contention.json")
SPIN = "import time; t=time.time()\nwhile time.time()-t < 60: pass"


def get(path):
    t = time.perf_counter()
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        r.read()
    return round(time.perf_counter() - t, 2)


gw = "/api/gameweek?key=EPL&matchday=9"
res = {"request": gw}
res["idle_before_s"] = [get(gw) for _ in range(3)]
burners = [subprocess.Popen([sys.executable, "-c", SPIN]) for _ in range(24)]
try:
    time.sleep(3)
    res["with_24_busy_processes_s"] = [get(gw) for _ in range(3)]
finally:
    for b in burners:
        b.kill()
time.sleep(2)
res["idle_after_s"] = [get(gw) for _ in range(3)]
res["median_s"] = {k: statistics.median(v) for k, v in res.items() if isinstance(v, list)}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
