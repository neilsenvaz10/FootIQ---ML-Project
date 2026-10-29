"""Phase 4.20 part C: exercise /api/matches for the Champions League on the Phase 4.19 rehearsal copy (results + fixtures), sync disabled, no network."""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["FOOTIQ_STORE_PATH"] = str(HERE.parent / "p419" / "rehearsal" / "footiq_with_fixtures.sqlite")
os.environ["FOOTIQ_DISABLE_SYNC"] = "1"
sys.path.insert(0, str(HERE.parents[3] / "app"))
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

c = TestClient(app)


def get(**q):
    r = c.get("/api/matches", params=q)
    return r.status_code, r.json()


s, d = get(comp="UCL", status="all", limit=50)
print("UCL all:", s, d["counts"], d["scope"], "facets", d["facets"]["seasons"][:3], d["facets"]["matchdays"], len(d["facets"]["teams"]), d["page"])
print("freshness UCL:", {k: d["freshness"]["competitions"]["UCL"][k] for k in ("state", "latest_result", "approved_sources", "awaiting_result", "scheduled")})
it = d["items"][0]
print("sample item:", json.dumps({k: it[k] for k in ("competition_key", "matchday_no", "matchday_label", "date", "status", "home", "away", "result", "validation_badge", "eligibility", "source")}, ensure_ascii=False))
s, d = get(comp="UCL", status="completed", matchday=2, limit=50)
print("UCL completed md2:", s, d["counts"], len(d["items"]), sorted({i["date"] for i in d["items"]}))
s, d = get(comp="UCL", status="all", team="CLUB:ENG:liverpool-fc", limit=50)
print("Liverpool:", s, d["counts"], [(i["matchday_no"], i["home"]["name"], i["away"]["name"], i["status"]) for i in d["items"]])
s, d = get(comp="UCL", status="upcoming", limit=5)
print("UCL upcoming:", s, d["counts"], [(i["date"], i["matchday_no"], i["home"]["name"]) for i in d["items"]])
s, d = get(comp="UCL", status="awaiting_result", limit=5)
print("UCL awaiting:", s, d["counts"])
s, d = get(limit=50, status="all")
print("all six, all statuses:", s, d["scope"]["competitions"], d["counts"], d["page"]["has_more"])
s, d = get(comp="EPL", status="all", team="CLUB:ENG:arsenal-fc", limit=50)
print("EPL Arsenal:", s, d["counts"], len(d["items"]), len(d["facets"]["teams"]))
print("bad team without comp:", get(team="CLUB:ENG:arsenal-fc")[0], "bad comp:", get(comp="UEL")[0], "bad team chars:", get(comp="UCL", team="x;drop")[0])
