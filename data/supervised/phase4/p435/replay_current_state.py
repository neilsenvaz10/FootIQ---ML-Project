"""Phase 4.35: replays the documented import chain onto a PRIVATE copy to test whether the current six-competition state can be rebuilt from repository inputs. Never touches production.
Usage: replay_current_state.py <scratch_dir>
Chain: baseline build -> saved OpenLigaDB snapshots (Bundesliga, La Liga; date protection on) -> UEFA importer (verified results + fixtures gates) -> domestic results importer -> reconciliation importer (strong tier).
Then compares the replay with the production store (read-only) on the content columns of `matches` (timestamps and run counters ignored)."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PY = sys.executable
S = Path(sys.argv[1])
S.mkdir(parents=True, exist_ok=True)
DB = S / "replay.sqlite"
for ext in ("", "-wal", "-shm"):
    Path(str(DB) + ext).unlink(missing_ok=True)
sys.path.insert(0, str(ROOT / "app"))
P4 = ROOT / "data" / "supervised" / "phase4"
log = {}


def run(name, args):
    r = subprocess.run([PY, "-X", "utf8", *args], cwd=ROOT, capture_output=True, text=True)
    log[name] = dict(returncode=r.returncode, tail=(r.stdout + r.stderr).strip().splitlines()[-6:])
    print(f"{name}: exit {r.returncode}")
    if r.returncode:
        print("\n".join(log[name]["tail"]))
    return r.returncode


run("1 baseline build", ["app/store/build.py", "--path", str(DB)])
# 2. saved OpenLigaDB snapshots (ODbL), applied with date protection as the application does
from store import db, sync  # noqa: E402

conn = db.connect(DB)
# 2-pre. the five reviewed OpenLigaDB team aliases accepted on 25 Oct (app/store/rehearse_openligadb.py review; our own mapping work)
ALIASES = [("england:1-premierleague", "Brentford F.C.", "CLUB:ENG:brentford-fc"), ("espana:1-liga", "Celta Vigo", "CLUB:ESP:rc-celta-vigo"), ("espana:1-liga", "Deportivo A Coruña", "CLUB:ESP:rcd-la-coruna"),
           ("espana:1-liga", "FC Villareal", "CLUB:ESP:villarreal-cf"), ("espana:1-liga", "Racing Santander", "CLUB:ESP:real-racing-santander")]
for cid, alias, ent in ALIASES:
    conn.execute("INSERT OR IGNORE INTO team_aliases(competition_id, source, alias, entity_id, method) VALUES (?,?,?,?,?)", (cid, "openligadb", alias, ent, "reviewed_alias_2026-10-25"))
conn.commit()
# 2a. the 25 Oct offline import of the saved Premier League and La Liga investigation snapshots (OpenLigaDB feeds not approved for live use; dates protected)
for key, snap in (("EPL", "20261025T090708Z_investigation_pl.json"), ("LALIGA", "20261025T090713Z_investigation_la1.json")):
    payload = (ROOT / "data" / "snapshots" / "investigation" / "openligadb" / snap).read_bytes()
    res = sync.replay_payload(conn, payload, competition_key=key, retrieved_utc="2026-10-25T09:07:13Z", snapshot_name=f"replay-offline-{key.lower()}", spec=sync.OFFLINE_PREPARED[key], kind="offline_snapshot_import", protect_dates=True)
    log[f"2a offline {key}"] = res
    print("2a offline", key, {k: res[k] for k in ("inserted", "updated", "unchanged", "quarantined")})
# 2b. the approved live feeds (Bundesliga, La Liga): the latest full-season snapshots, as the start-up refresh stores them
for key, snap in (("BUNDESLIGA", "20261027T170038Z_bl1_2026_season.json"), ("LALIGA", "20261027T180630Z_la1_2026_season.json")):
    payload = (ROOT / "data" / "snapshots" / "openligadb" / snap).read_bytes()
    res = sync.replay_payload(conn, payload, competition_key=key, retrieved_utc="2026-10-27T18:00:00Z", snapshot_name=f"replay-{key.lower()}", protect_dates=True)
    log[f"2 openligadb {key}"] = res
    print("2 openligadb", key, {k: res[k] for k in ("inserted", "updated", "unchanged", "quarantined")})
conn.close()
common = ["--store", str(DB), "--apply", "--as-of", "2026-10-28"]
run("3 uefa_import (results + fixtures)", ["app/store/uefa_import.py", *common, "--include-fixtures", "--staging", str(P4 / "p420/staging/uefa_2026_27_staging_v2.csv"), "--gate", str(P4 / "p420/staging/ucl_verified_results.csv"),
                                         "--fixtures-gate", str(P4 / "p421/ucl_verified_fixtures.csv"), "--report-dir", str(S / "r_uefa")])
run("4 league_results_import", ["app/store/league_results_import.py", *common, "--report-dir", str(S / "r_league")])
run("5 reconcile_import (strong)", ["app/store/reconcile_import.py", *common, "--report-dir", str(S / "r_reconcile")])

# 6. the start-up refresh runs again after the reconciliation (it re-reads the same saved full-season snapshots; results held for a date disagreement are accepted once the dates agree)
conn = db.connect(DB)
import os
for key, snap in (() if os.environ.get("SKIP6") else (("BUNDESLIGA", "20261027T170038Z_bl1_2026_season.json"), ("LALIGA", "20261027T180630Z_la1_2026_season.json"))):
    payload = (ROOT / "data" / "snapshots" / "openligadb" / snap).read_bytes()
    res = sync.replay_payload(conn, payload, competition_key=key, retrieved_utc="2026-10-28T13:46:00Z", snapshot_name=f"replay-startup-{key.lower()}", kind="startup_refresh", protect_dates=True)
    log[f"6 startup refresh {key}"] = res
    print("6 startup refresh", key, {k: res[k] for k in ("inserted", "updated", "unchanged", "quarantined")})
conn.close()

# ---- compare with production (read-only) on content columns
COLS = ["record_id", "kind", "competition_id", "competition_key", "season", "stage", "matchday_label", "matchday_no", "match_date", "kickoff_local", "kickoff_utc", "time_precision", "home_entity_id", "away_entity_id",
        "model_home_entity", "model_away_entity", "home_name", "away_name", "status", "home_goals_final", "away_goals_final", "home_goals_90", "away_goals_90", "shootout_winner", "neutral", "rated", "regular", "in_universe",
        "tier", "competition_type", "source_system", "licence"]
SIX = "('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL')"
a = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
b = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
q = f"select {','.join(COLS)} from matches where competition_key in {SIX}"
A = {r[0]: r for r in a.execute(q)}
B = {r[0]: r for r in b.execute(q)}
only_a, only_b = set(A) - set(B), set(B) - set(A)
diff = [k for k in A if k in B and A[k] != B[k]]
cols = {}
for k in diff:
    for i, (x, y) in enumerate(zip(A[k], B[k])):
        if x != y:
            cols[COLS[i]] = cols.get(COLS[i], 0) + 1
summary = dict(production_rows=len(A), replay_rows=len(B), only_in_production=len(only_a), only_in_replay=len(only_b), rows_differing=len(diff), differing_columns=cols)
for label, DBc in (("production", a), ("replay", b)):
    summary[label + "_completed_by_comp"] = dict(DBc.execute(f"select competition_key,count(*) from matches where season='2026-27' and competition_key in {SIX} and status in ('completed','awarded') group by 1").fetchall())
    summary[label + "_scheduled_by_comp"] = dict(DBc.execute(f"select competition_key,count(*) from matches where season='2026-27' and competition_key in {SIX} and status='scheduled' group by 1").fetchall())
ex = [(k, [(COLS[i], x, y) for i, (x, y) in enumerate(zip(A[k], B[k])) if x != y]) for k in diff[:6]]
summary["examples"] = ex
print(json.dumps(summary, indent=1, default=str))
(S / "replay_summary.json").write_text(json.dumps(dict(log=log, comparison=summary), indent=1, default=str), encoding="utf-8")
