"""Phase 4.21 part C: production READ-ONLY dry run of the fixtures import, then a rehearsal on a PRIVATE COPY of the store and the Matches hub on that copy (TestClient, sync disabled, no network)."""
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
COPY = REH / "footiq_ucl_fixtures.sqlite"
sys.path.insert(0, str(ROOT / "app"))
STG = ROOT / "data/supervised/phase4/p420/staging/uefa_2026_27_staging_v2.csv"
GATE = ROOT / "data/supervised/phase4/p420/staging/ucl_verified_results.csv"
FGATE = HERE / "ucl_verified_fixtures.csv"
AS_OF = "2026-10-28"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


before = sha(PROD)
from store import uefa_import as U  # noqa: E402

rep = {"production_sha256_before": before}
dry = U.run(PROD, apply=False, include_fixtures=True, staging=STG, gate_path=GATE, fixtures_gate_path=FGATE, as_of=AS_OF, report_dir=HERE / "ucl_fixtures_dryrun")
rep["production_dry_run"] = dict(counts=dry["counts"], issues=len(dry["validation_issues"]), fixtures_gate_sha256=dry["fixtures_gate_sha256"])
dry0 = U.run(PROD, apply=False, include_fixtures=False, staging=STG, gate_path=GATE, as_of=AS_OF)
rep["production_dry_run_results_only"] = dry0["counts"]
rep["production_unchanged_after_dry_runs"] = sha(PROD) == before

for ext in ("", "-wal", "-shm"):
    Path(str(COPY) + ext).unlink(missing_ok=True)
src = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
dst = sqlite3.connect(COPY)
src.backup(dst)
dst.close()
src.close()
r1 = U.run(COPY, apply=True, include_fixtures=True, staging=STG, gate_path=GATE, fixtures_gate_path=FGATE, as_of=AS_OF)
r2 = U.run(COPY, apply=True, include_fixtures=True, staging=STG, gate_path=GATE, fixtures_gate_path=FGATE, as_of=AS_OF)
rep["copy_first_apply"] = dict(counts=r1["counts"], applied=r1["applied"])
rep["copy_second_apply"] = dict(counts=r2["counts"], applied=r2["applied"])
c = sqlite3.connect(COPY)
rep["copy_integrity"] = c.execute("PRAGMA integrity_check").fetchone()[0]
rep["copy_fk"] = len(c.execute("PRAGMA foreign_key_check").fetchall())
rep["copy_ucl_status"] = dict(c.execute("SELECT status, COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' GROUP BY 1").fetchall())
rep["copy_ucl_by_matchday"] = dict(c.execute("SELECT stage, COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' GROUP BY 1 ORDER BY 1").fetchall())
rep["copy_duplicates"] = c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM matches WHERE competition_key='UCL' AND season='2026-27' GROUP BY home_entity_id, away_entity_id HAVING COUNT(*)>1)").fetchone()[0]
rep["copy_non_league_phase_rows"] = c.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' AND stage NOT LIKE 'Matches > Matchday %'").fetchone()[0]
rep["copy_completed_dated_after_today"] = c.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' AND status='completed' AND match_date > ?", (AS_OF,)).fetchone()[0]
rep["copy_unplayed_dated_before_today"] = c.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' AND status!='completed' AND match_date < ?", (AS_OF,)).fetchone()[0]
c.close()

os.environ["FOOTIQ_STORE_PATH"] = str(COPY)
os.environ["FOOTIQ_DISABLE_SYNC"] = "1"
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

cl = TestClient(app)
hub = {}
for status in ("upcoming", "completed", "awaiting_result", "all"):
    d = cl.get("/api/matches", params=dict(comp="UCL", status=status, limit=50)).json()
    hub[status] = dict(counts=d["counts"], returned=len(d["items"]), first=[(i["date"], i["matchday_no"], i["home"]["name"], i["away"]["name"], i["status"]) for i in d["items"][:2]],
                       statuses=sorted({i["status"] for i in d["items"]}), badges=sorted({i["validation_badge"] for i in d["items"]}))
rep["hub_on_copy"] = hub
d = cl.get("/api/matches", params=dict(comp="UCL", status="upcoming", matchday=5, limit=50)).json()
rep["hub_matchday5"] = dict(n=len(d["items"]), dates=sorted({i["date"] for i in d["items"]}), all_unplayed=all(i["status"] == "scheduled" for i in d["items"]))
d = cl.get("/api/matches", params=dict(comp="UCL", status="upcoming", team="CLUB:ENG:arsenal-fc", limit=50)).json()
rep["hub_arsenal_upcoming"] = [(i["date"], i["matchday_no"], i["home"]["name"], i["away"]["name"]) for i in d["items"]]
lp = cl.get("/api/competitions/UCL/league-phase", params={"season": "2026-27"}).json()
rep["league_phase_on_copy"] = dict(played=lp["matches_played"], in_data=lp["matches_in_data"], expected=lp["matches_expected"], complete=lp["complete"], note=lp["coverage_note"], criteria=lp["criteria_applied"])
upc = [i for i in cl.get("/api/matches", params=dict(comp="UCL", status="upcoming", limit=1)).json()["items"]]
pr = cl.get("/api/predict", params=dict(key="UCL", home="Arsenal FC", away="Real Madrid CF"))
rep["predict_ucl"] = dict(status=pr.status_code, badge=pr.json().get("validation_badge"), note=pr.json().get("note") or pr.json().get("notes"))
rep["production_sha256_after"] = sha(PROD)
rep["production_unchanged"] = rep["production_sha256_after"] == before
(HERE / "rehearsal_ucl_fixtures_report.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps(rep, indent=1, default=str, ensure_ascii=False)[:6500])
