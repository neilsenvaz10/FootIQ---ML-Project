"""HTTP-level check of GET /api/featured-fixture on a PRIVATE COPY: headers, cache hit/miss, ETag/304, validation, timing (in-process TestClient)."""
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
path = Path(os.environ["FOOTIQ_STORE_PATH"])
assert "rehearsal" in path.parts
os.environ["FOOTIQ_STORE_PATH"] = str(path)

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

# no lifespan: do not start the sync manager or the model warm-up thread
client = TestClient(main.app)
miss = []
t = time.perf_counter()
r = client.get("/api/featured-fixture")
miss.append((time.perf_counter() - t) * 1000)
print("first request:", r.status_code, "cache:", r.headers["x-footiq-cache"], "| cache-control:", r.headers["cache-control"], "| etag:", r.headers["etag"], "| bytes:", len(r.content), "| ms:", round(miss[0], 1))
etag = r.headers["etag"]
hits = []
for _ in range(30):
    t = time.perf_counter()
    r2 = client.get("/api/featured-fixture")
    hits.append((time.perf_counter() - t) * 1000)
print("repeat requests:", r2.headers["x-footiq-cache"], "| median ms:", round(statistics.median(hits), 2), "| max ms:", round(max(hits), 2))
r3 = client.get("/api/featured-fixture", headers={"If-None-Match": etag})
print("conditional request:", r3.status_code, "| body bytes:", len(r3.content))
for q in ("?comp=UCL", "?upcoming=0", "?results=99", "?comp=EPL&upcoming=3&results=2"):
    rr = client.get("/api/featured-fixture" + q)
    body = rr.json()
    print(q.ljust(34), rr.status_code, body.get("detail") if rr.status_code != 200 else f"featured={body['featured']['competition_key'] if body['featured'] else None} upcoming={len(body['upcoming'])} results={len(body['recent_results'])} scope={body['scope']['competitions']}")
# several uncached builds, to get a distribution (the cache is dropped each time)
builds = []
for _ in range(10):
    main.featured_cache.clear()
    t = time.perf_counter()
    client.get("/api/featured-fixture")
    builds.append((time.perf_counter() - t) * 1000)
print("uncached builds ms: median", round(statistics.median(builds), 1), "min", round(min(builds), 1), "max", round(max(builds), 1))
