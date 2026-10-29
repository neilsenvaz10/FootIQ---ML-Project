"""Phase 4.25: which files does the application actually open? READ-ONLY. Imports the FastAPI app with synchronisation disabled, installs an audit hook that records every open() and sqlite3.connect() inside the
project, and serves GET requests for all six competitions (health, meta, competitions, dashboard, teams, team, predict, matches, gameweeks, performance, freshness, sync status, league phase, featured fixture, season status).
No POST (nothing is forecast-saved, nothing simulated), no network, no write. Output: runtime_footprint.csv (path, bytes, mode) and a console summary."""
import csv
import os
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.environ["FOOTIQ_DISABLE_SYNC"] = "1"
os.environ["FOOTIQ_STORE_PATH"] = str(ROOT / "data" / "footiq.sqlite")
sys.path.insert(0, str(ROOT / "app"))
opened = {}
EXCL = (".venv", "node_modules", "__pycache__", "/.git/")


def hook(event, args):
    p = None
    if event == "open" and args and isinstance(args[0], (str, bytes)):
        p = args[0].decode(errors="ignore") if isinstance(args[0], bytes) else args[0]
        mode = str(args[1])
    elif event == "sqlite3.connect" and args:
        p = str(args[0])
        mode = "sqlite"
    else:
        return
    try:
        q = Path(p).resolve()
        rel = q.relative_to(ROOT).as_posix()
    except Exception:
        return
    if any(x in "/" + rel for x in EXCL) or rel.endswith(".pyc"):
        return
    opened.setdefault(rel, set()).add(mode)


sys.addaudithook(hook)
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

cl = TestClient(app)
KEYS = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"]
log = []


def get(path, **q):
    r = cl.get(path, params=q)
    log.append((path, r.status_code))
    return r


for p in ("/api/health", "/api/meta", "/api/competitions", "/api/models/performance", "/api/data-freshness", "/api/sync/status", "/api/featured-fixture"):
    get(p)
for k in KEYS:
    names = [x if isinstance(x, str) else x.get("name") for x in (lambda t: t if isinstance(t, list) else t.get("teams", []))(get(f"/api/competitions/{k}/teams").json())]
    for suffix in ("seasons", "coverage"):
        get(f"/api/competitions/{k}/{suffix}")
    get(f"/api/competitions/{k}/dashboard", season="2026-27")
    get("/api/team", key=k, team=names[0])
    get("/api/predict", key=k, home=names[0], away=names[1])
    get("/api/matches", comp=k, status="all", limit=5)
    if k != "UCL":
        get("/api/gameweeks", key=k)
        get("/api/season/status", key=k)
        get("/api/season/runs", key=k, season="2026-27")
get("/api/competitions/UCL/league-phase", season="2026-27")
bad = [(p, s) for p, s in log if s >= 500]
rows = []
for rel, modes in sorted(opened.items()):
    f = ROOT / rel
    rows.append((rel, f.stat().st_size if f.exists() else 0, "|".join(sorted(modes))))
with open(HERE / "runtime_footprint.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["path", "bytes", "modes"])
    w.writerows(rows)
print("requests:", len(log), "server errors:", bad)
print("files opened:", len(rows), "total", round(sum(r[1] for r in rows) / 1e6, 1), "MB")
top = {}
for rel, size, _ in rows:
    k = "/".join(rel.split("/")[:2]) if rel.startswith(("data/", "FootIQ_")) else rel.split("/")[0]
    top[k] = top.get(k, 0) + size
for k, v in sorted(top.items(), key=lambda x: -x[1]):
    print(f"  {v / 1e6:9.1f} MB  {k}")
for rel, size, m in sorted(rows, key=lambda r: -r[1])[:30]:
    print(f"  {size / 1e6:9.2f} MB  {m:8s} {rel}")

# imported Python modules located in the project (source files the running application depends on)
mods = sorted({Path(m.__file__).resolve().relative_to(ROOT).as_posix() for m in list(sys.modules.values()) if getattr(m, "__file__", None) and str(ROOT) in str(Path(m.__file__).resolve()) and ".venv" not in str(m.__file__)})
with open(HERE / "runtime_modules.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(mods))
print("project modules imported:", len(mods))
for m in mods:
    print("  ", m)
