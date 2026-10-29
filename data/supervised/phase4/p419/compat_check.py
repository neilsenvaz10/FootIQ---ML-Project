"""Phase 4.19 step 5: run the application's own code (FastAPI TestClient, no server, sync disabled) against a PRIVATE rehearsal copy of the store and report what the Champions League views show.
Usage: python compat_check.py <store copy> <label>.  Never pointed at production; makes no network request."""
import json
import os
import sys
from pathlib import Path

store, label = sys.argv[1], sys.argv[2]
os.environ["FOOTIQ_STORE_PATH"] = store
os.environ["FOOTIQ_DISABLE_SYNC"] = "1"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

cl = TestClient(app)
out = {"store": store}


def get(path):
    r = cl.get(path)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else None)


s, comps = get("/api/competitions")
out["competitions"] = [c["key"] for c in comps]
s, d = get("/api/competitions/UCL/seasons")
out["seasons"] = d
s, db = get("/api/competitions/UCL/dashboard?season=2026-27")
out["dashboard_status"] = s
out["dashboard_keys"] = sorted(db.keys()) if isinstance(db, dict) else None
s, lp = get("/api/competitions/UCL/league-phase?season=2026-27")
out["league_phase"] = dict(status=s, matches_in_data=lp["matches_in_data"], matches_played=lp["matches_played"], expected=lp["matches_expected"], complete=lp["complete"], teams=lp["teams"], criteria=lp["criteria_applied"],
                           note=lp["coverage_note"], top5=[(r["position"], r["team"], r["played"], r["points"], r["gd"], r["gf"], r["zone"]) for r in lp["table"][:5]], bottom2=[(r["position"], r["team"], r["played"], r["points"]) for r in lp["table"][-2:]],
                           played_values=sorted({r["played"] for r in lp["table"]}))
s, t = get("/api/competitions/UCL/teams")
teams = t if isinstance(t, list) else t.get("teams", [])
names = [x if isinstance(x, str) else x.get("team") or x.get("name") for x in teams]
out["teams_listed"] = len(names)
s, tm = get("/api/team?key=UCL&team=Liverpool%20FC")
out["team_stats"] = dict(status=s, keys=sorted(tm.keys())[:14] if isinstance(tm, dict) else None)
s, gw = get("/api/gameweeks?key=UCL")
out["gameweeks"] = dict(status=s, sample=(gw if not isinstance(gw, (list, dict)) else json.dumps(gw)[:400]))
s, mt = get("/api/matches?key=UCL&season=2026-27")
out["matches_endpoint"] = dict(status=s, n=(len(mt) if isinstance(mt, list) else (len(mt.get("matches", [])) if isinstance(mt, dict) else None)), body=(json.dumps(mt)[:300] if s != 200 else ""))
s, fr = get("/api/data-freshness")
u = next(x for x in fr if x["key"] == "UCL")
out["freshness_UCL"] = {k: u[k] for k in ("latest_result", "days_since_latest_result", "data_status", "data_status_label", "has_warnings", "warnings")}
s, p = get("/api/predict?key=UCL&home=Liverpool%20FC&away=Real%20Madrid%20CF")
out["prediction"] = dict(status=s, badge=p.get("validation_badge") if p else None, models=[k for k in (p or {}) if k in ("club_v1", "club_v2_r1", "elo", "v1", "v2_r1", "probabilities", "models")], note=(p or {}).get("note") or (p or {}).get("notes"),
                         probs=(p or {}).get("probabilities"))
s, p2 = get("/api/predict?key=UCL&home=Liverpool%20FC&away=Real%20Madrid%20CF")
out["prediction_repeat_identical"] = p == p2
s, sy = get("/api/sync/status")
out["sync_disabled_in_this_check"] = True
s, ft = get("/api/featured-fixture")
out["featured_fixture_status"] = s
print(json.dumps(out, indent=1, default=str, ensure_ascii=False)[:6000])
(Path(__file__).resolve().parent / f"compat_{label}.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
