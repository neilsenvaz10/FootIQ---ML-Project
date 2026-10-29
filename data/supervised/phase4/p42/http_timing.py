"""Real-HTTP timings of what the Home page requests, against the running backend (private database copy, read-only requests, nothing is written).

    .venv/Scripts/python.exe -X utf8 data/supervised/phase4/p42/http_timing.py [http://127.0.0.1:8000]

Measured as a client sees them: a new connection per request, response read to the end. Misses are forced without restarting the server by asking for
(upcoming, results) pairs that have not been requested before (each pair is its own cache key). /api/gameweek is included only for comparison (one call).
"""
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
OUT = Path(__file__).resolve().parent / "http_timing.json"


def get(path, headers=None):
    req = urllib.request.Request(BASE + path, headers=headers or {})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
            code, hdr = r.status, {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        body, code, hdr = e.read(), e.code, {k.lower(): v for k, v in e.headers.items()}
    return (time.perf_counter() - t) * 1000, code, hdr, body


def summary(ms):
    return dict(n=len(ms), median_ms=round(statistics.median(ms), 1), min_ms=round(min(ms), 1), max_ms=round(max(ms), 1))


out = dict(base=BASE, measured_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

# 1. the featured-fixture endpoint
ms, code, hdr, body = get("/api/featured-fixture")
out["featured_first_request"] = dict(ms=round(ms, 1), status=code, cache=hdr.get("x-footiq-cache"), bytes=len(body), cache_control=hdr.get("cache-control"), etag=hdr.get("etag"))
etag = hdr["etag"]
hits = [get("/api/featured-fixture") for _ in range(30)]
out["featured_repeat_hits"] = dict(**summary([h[0] for h in hits]), all_hit=all(h[2].get("x-footiq-cache") == "hit" for h in hits))
conds = [get("/api/featured-fixture", {"If-None-Match": etag}) for _ in range(30)]
out["featured_conditional_304"] = dict(**summary([c[0] for c in conds]), all_304=all(c[1] == 304 for c in conds), body_bytes=sum(len(c[3]) for c in conds))

pairs = [(u, r) for u in (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12) for r in (1,)] + [(8, r) for r in (0, 2, 3, 4)]
misses = []
for u, r in pairs:
    m, c, h, b = get(f"/api/featured-fixture?upcoming={u}&results={r}")
    misses.append((m, c, h.get("x-footiq-cache")))
out["featured_uncached_builds"] = dict(**summary([m[0] for m in misses]), all_miss=all(m[2] == "miss" for m in misses), all_200=all(m[1] == 200 for m in misses))
out["featured_bytes_by_size"] = {f"upcoming={u}": len(get(f"/api/featured-fixture?upcoming={u}&results=8")[3]) for u in (1, 8, 12)}

# 2. the other requests the Home page makes (league overview) and the freshness call the shell makes
for name, path in [
    ("seasons", "/api/competitions/EPL/seasons"),
    ("coverage", "/api/competitions/EPL/coverage"),
    ("dashboard", "/api/competitions/EPL/dashboard?season=2026-27"),
    ("sync_status", "/api/sync/status"),
]:
    runs = [get(path) for _ in range(10)]
    out[f"home_other_{name}"] = dict(**summary([r[0] for r in runs]), status=runs[0][1], bytes=len(runs[0][3]))

# 3. for comparison only: the gameweek view the banner must not call, and the gameweek list
runs = [get("/api/gameweeks?key=EPL") for _ in range(3)]
out["compare_gameweeks_list"] = dict(**summary([r[0] for r in runs]), status=runs[0][1])
nxt = json.loads(runs[0][3])["next_gameweek"]
ms, code, _, body = get(f"/api/gameweek?key=EPL&matchday={nxt}")
out["compare_gameweek_page"] = dict(matchday=nxt, ms=round(ms, 1), status=code, bytes=len(body))

OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
