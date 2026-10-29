"""Phase 4.21 part B: rehearse the domestic import on a PRIVATE COPY of the production store (never on production), then run the application's own code (TestClient, sync disabled, no network) against
the copy: standings, hub counts, predictions. Production is only read; its sha256 is compared before and after."""
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PROD = ROOT / "data" / "footiq.sqlite"
REH = HERE / "rehearsal"
REH.mkdir(exist_ok=True)
COPY = REH / "footiq_domestic.sqlite"
sys.path.insert(0, str(ROOT / "app"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


before = sha(PROD)
for ext in ("", "-wal", "-shm"):
    Path(str(COPY) + ext).unlink(missing_ok=True)
src = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
dst = sqlite3.connect(COPY)
src.backup(dst)
dst.close()
src.close()

os.environ["FOOTIQ_STORE_PATH"] = str(COPY)
os.environ["FOOTIQ_DISABLE_SYNC"] = "1"
from store import league_results_import as L  # noqa: E402

rep = {"production_sha256_before": before}
r1 = L.run(COPY, apply=True, as_of="2026-10-28", report_dir=REH)
rep["first_apply"] = dict(counts=r1["counts"], applied=r1["applied"])
r2 = L.run(COPY, apply=True, as_of="2026-10-28")
rep["second_apply"] = dict(counts=r2["counts"], applied=r2["applied"])
c = sqlite3.connect(COPY)
rep["integrity"] = c.execute("PRAGMA integrity_check").fetchone()[0]
rep["fk_problems"] = len(c.execute("PRAGMA foreign_key_check").fetchall())
rep["completed_2026_27"] = dict(c.execute("SELECT competition_key, COUNT(*) FROM matches WHERE season='2026-27' AND status='completed' GROUP BY 1").fetchall())
rep["awaiting_past_date"] = dict(c.execute("SELECT competition_key, COUNT(*) FROM matches WHERE season='2026-27' AND status IN ('scheduled','awaiting_result') AND match_date < '2026-10-28' GROUP BY 1").fetchall())
rep["simulations"] = c.execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0]
rep["duplicates"] = c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM matches WHERE season='2026-27' GROUP BY competition_key, home_entity_id, away_entity_id, match_date HAVING COUNT(*)>1)").fetchone()[0]
c.close()

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

cl = TestClient(app)
out = {}
for k, team in (("EPL", "Arsenal FC"), ("SERIEA", "AC Milan"), ("LIGUE1", "Paris Saint-Germain FC")):
    d = cl.get(f"/api/competitions/{k}/dashboard", params={"season": "2026-27"}).json()
    top = d["standings"][:3] if d.get("standings") else None
    t = cl.get("/api/competitions/%s/teams" % k).json()
    names = [x if isinstance(x, str) else x.get("name") for x in (t if isinstance(t, list) else t.get("teams", []))]
    p = cl.get("/api/predict", params={"key": k, "home": names[0], "away": names[1]})
    pj = p.json()
    probs = pj.get("probabilities") or {}
    hub = cl.get("/api/matches", params={"comp": k, "status": "all", "limit": 1}).json()["counts"]
    out[k] = dict(matches_in_dashboard=d["summary"]["matches"], top3=[(r.get("team"), r.get("played"), r.get("points")) for r in (top or [])], hub_counts=hub, predict_status=p.status_code, badge=pj.get("validation_badge"),
                  probs_sum=round(sum(v for v in probs.values() if isinstance(v, (int, float))), 6) if probs else None)
rep["app_on_copy"] = out
rep["production_sha256_after"] = sha(PROD)
rep["production_unchanged"] = before == rep["production_sha256_after"]
(HERE / "rehearsal_domestic_report.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps(rep, indent=1, default=str, ensure_ascii=False)[:5000])
