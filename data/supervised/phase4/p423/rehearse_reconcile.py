"""Phase 4.23: rehearse the reconciliation import on a PRIVATE COPY of production (never on production), then run the application's own code against the copy (TestClient, sync disabled, no network).
Production is only read; its sha256 is compared before and after."""
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
sys.path.insert(0, str(ROOT / "app"))
AS_OF = "2026-10-28"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fresh_copy(name):
    dst = REH / name
    for ext in ("", "-wal", "-shm"):
        Path(str(dst) + ext).unlink(missing_ok=True)                                        # only this script's own rehearsal copies
    src = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
    out = sqlite3.connect(dst)
    src.backup(out)
    out.close()
    src.close()
    return dst


def facts(path):
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    r = dict(integrity=c.execute("PRAGMA integrity_check").fetchone()[0], fk=len(c.execute("PRAGMA foreign_key_check").fetchall()), matches=c.execute("SELECT COUNT(*) FROM matches").fetchone()[0],
             completed=dict(c.execute("SELECT competition_key, COUNT(*) FROM matches WHERE season='2026-27' AND status='completed' AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') GROUP BY 1").fetchall()),
             open_past=dict(c.execute("SELECT competition_key, COUNT(*) FROM matches WHERE season='2026-27' AND status IN ('scheduled','awaiting_result') AND match_date < ? AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1') GROUP BY 1", (AS_OF,)).fetchall()),
             postponed=c.execute("SELECT COUNT(*) FROM matches WHERE season='2026-27' AND status='postponed'").fetchone()[0], sims=c.execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0],
             quarantine=c.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0], duplicates=c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM matches WHERE season='2026-27' AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') GROUP BY competition_key, home_entity_id, away_entity_id HAVING COUNT(*)>1)").fetchone()[0],
             orphans=c.execute("SELECT COUNT(*) FROM matches m WHERE m.season='2026-27' AND m.competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') AND (m.home_entity_id NOT IN (SELECT entity_id FROM teams) OR m.away_entity_id NOT IN (SELECT entity_id FROM teams))").fetchone()[0],
             other_rows_hash=hashlib.sha256(repr(c.execute("SELECT record_id, content_hash FROM matches WHERE record_id NOT IN (SELECT record_id FROM matches WHERE 0) ORDER BY 1").fetchall()).encode()).hexdigest())
    c.close()
    return r


before = sha(PROD)
rep = {"production_sha256_before": before}
copy = fresh_copy("footiq_reconcile.sqlite")
rep["copy_before"] = facts(copy)
sys.path.insert(0, str(ROOT / "app"))
from store import reconcile_import as R  # noqa: E402

r1 = R.run(copy, apply=True, tiers=("strong", "provider_assisted", "decision"), as_of=AS_OF, report_dir=REH)
rep["first_apply"] = dict(counts=r1["counts"], applied=r1["applied"])
r2 = R.run(copy, apply=True, tiers=("strong", "provider_assisted", "decision"), as_of=AS_OF)
rep["second_apply"] = dict(counts=r2["counts"], applied=r2["applied"])
rep["copy_after"] = facts(copy)

# which rows changed, and how: compare the copy with the production hashes
c = sqlite3.connect(f"file:{copy.as_posix()}?mode=ro", uri=True)
c.execute(f"ATTACH DATABASE 'file:{PROD.as_posix()}?mode=ro' AS prod")
rep["rows_changed_vs_production"] = c.execute("SELECT COUNT(*) FROM main.matches m JOIN prod.matches p ON p.record_id=m.record_id WHERE m.content_hash<>p.content_hash").fetchone()[0]
rep["rows_added_vs_production"] = c.execute("SELECT COUNT(*) FROM main.matches m WHERE m.record_id NOT IN (SELECT record_id FROM prod.matches)").fetchone()[0]
rep["changed_by_type"] = {}
for row in c.execute("SELECT m.competition_key, m.status, p.status, (m.match_date<>p.match_date), COUNT(*) FROM main.matches m JOIN prod.matches p ON p.record_id=m.record_id WHERE m.content_hash<>p.content_hash GROUP BY 1,2,3,4"):
    rep["changed_by_type"][f"{row[0]}: {row[2]} -> {row[1]}, date changed={bool(row[3])}"] = row[4]
c.close()

os.environ["FOOTIQ_STORE_PATH"] = str(copy)
os.environ["FOOTIQ_DISABLE_SYNC"] = "1"
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

cl = TestClient(app)
app_out = {}
for k in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"):
    d = cl.get(f"/api/competitions/{k}/dashboard", params={"season": "2026-27"}).json()
    hub = cl.get("/api/matches", params={"comp": k, "status": "all", "limit": 1}).json()["counts"]
    t = cl.get(f"/api/competitions/{k}/teams").json()
    names = [x if isinstance(x, str) else x.get("name") for x in (t if isinstance(t, list) else t.get("teams", []))]
    p = cl.get("/api/predict", params=dict(key=k, home=names[0], away=names[1]))
    st = d.get("standings")
    app_out[k] = dict(matches=d["summary"]["matches"], standings_games=(sum(x["played"] for x in st) // 2 if st else None), top2=[(x["team"], x["played"], x["points"]) for x in (st or [])[:2]], hub=hub,
                      predict=(p.status_code, p.json().get("validation_badge")))
rep["app_on_copy"] = app_out
pm = cl.get("/api/matches", params=dict(comp="LALIGA", status="other", limit=10)).json()
rep["laliga_postponed_in_hub"] = [(i["home"]["name"], i["away"]["name"], i["date"], i["status"]) for i in pm["items"]]
sa = cl.get("/api/matches", params=dict(comp="SERIEA", status="upcoming", matchday=11, limit=20)).json()
rep["seriea_sample_after_date_change"] = [(i["date"], i["home"]["name"], i["away"]["name"], i["kickoff"]["state"]) for i in sa["items"][:3]]
rep["production_sha256_after"] = sha(PROD)
rep["production_unchanged"] = rep["production_sha256_after"] == before
(HERE / "rehearsal_reconcile_report.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps(rep, indent=1, default=str, ensure_ascii=False)[:6500])
