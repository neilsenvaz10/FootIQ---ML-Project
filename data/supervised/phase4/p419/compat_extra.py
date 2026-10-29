"""Phase 4.19: extra read-only checks against the rehearsal copy that includes the fixtures (no network, sync disabled)."""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["FOOTIQ_STORE_PATH"] = str(HERE / "rehearsal" / "footiq_with_fixtures.sqlite")
os.environ["FOOTIQ_DISABLE_SYNC"] = "1"
sys.path.insert(0, str(HERE.parents[3] / "app"))
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

c = TestClient(app)
s = c.get("/api/sync/status").json()
u = [x for x in s["competitions"] if x["competition_key"] == "UCL"][0]
print({k: u.get(k) for k in ("latest_result", "awaiting_result", "scheduled", "last_fixture", "oldest_awaiting", "state", "state_reasons")})
r = c.get("/api/matches", params={"key": "UCL", "season": "2026-27"})
print("matches", r.status_code, r.text[:300])
r = c.get("/api/competitions/UCL/dashboard", params={"season": "2026-27"}).json()
print("summary", json.dumps(r["summary"])[:400])
print("results", len(r["results"]), json.dumps(r["results"][:1], ensure_ascii=False)[:300])
print("standings", json.dumps(r["standings"])[:300])
