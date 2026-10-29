"""Phase 4.36: compares a private replay database with the production store (read-only): rows, completed results, scheduled fixtures, competition counts, match dates, team mappings,
simulation eligibility and Champions League coverage. Usage: compare_replay.py <replay.sqlite> <label>"""
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
from seasonsim import eligibility  # noqa: E402
from store import db  # noqa: E402

R = Path(sys.argv[1])
LABEL = sys.argv[2]
SIX = ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL")
prod = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
rep = sqlite3.connect(f"file:{R.as_posix()}?mode=ro", uri=True)
out = dict(label=LABEL)
q = lambda c, sql, *a: c.execute(sql, a).fetchall()
out["total_rows"] = dict(production=q(prod, "select count(*) from matches")[0][0], replay=q(rep, "select count(*) from matches")[0][0])
for name, where in (("completed_2026_27", "status in ('completed','awarded')"), ("scheduled_2026_27", "status='scheduled'"), ("awaiting_result_2026_27", "status='awaiting_result'"), ("postponed_2026_27", "status='postponed'")):
    out[name] = {k: dict(production=dict(q(prod, f"select competition_key,count(*) from matches where season='2026-27' and competition_key in {SIX} and {where} group by 1")).get(k, 0),
                         replay=dict(q(rep, f"select competition_key,count(*) from matches where season='2026-27' and competition_key in {SIX} and {where} group by 1")).get(k, 0)) for k in SIX}
cols = "record_id, match_date, status, home_goals_final, away_goals_final, home_entity_id, away_entity_id"
A = {r[0]: r for r in prod.execute(f"select {cols} from matches where competition_key in {SIX}")}
B = {r[0]: r for r in rep.execute(f"select {cols} from matches where competition_key in {SIX}")}
out["rows_six_competitions"] = dict(production=len(A), replay=len(B), only_in_production=len(set(A) - set(B)), only_in_replay=len(set(B) - set(A)))
out["match_dates_differing"] = sum(1 for k in A if k in B and A[k][1] != B[k][1])
out["results_differing"] = sum(1 for k in A if k in B and A[k][2:5] != B[k][2:5])
out["team_pair_mapping_differing"] = sum(1 for k in A if k in B and A[k][5:7] != B[k][5:7])
tp, tr = set(prod.execute("select entity_id, display_name from teams")), set(rep.execute("select entity_id, display_name from teams"))
ap_, ar_ = set(prod.execute("select competition_id, source, alias, entity_id from team_aliases")), set(rep.execute("select competition_id, source, alias, entity_id from team_aliases"))
out["teams"] = dict(production=len(tp), replay=len(tr), differing=len(tp ^ tr))
out["team_aliases"] = dict(production=len(ap_), replay=len(ar_), differing=len(ap_ ^ ar_))
ucl = lambda c: dict(completed=q(c, "select count(*) from matches where competition_key='UCL' and season='2026-27' and status in ('completed','awarded')")[0][0], scheduled=q(c, "select count(*) from matches where competition_key='UCL' and season='2026-27' and status='scheduled'")[0][0],
                     matchdays=sorted({r[0] for r in c.execute("select matchday_no from matches where competition_key='UCL' and season='2026-27'") if r[0]}))
out["champions_league"] = dict(production=ucl(prod), replay=ucl(rep))
elig = {}
for label, path in (("production", ROOT / "data" / "footiq.sqlite"), ("replay", R)):
    conn = db.connect(path, readonly=True)
    try:
        for k in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"):
            a = eligibility.assess(conn, k, "2026-27", date(2026, 10, 28))
            elig.setdefault(k, {})[label] = dict(state=a["state"], points_only_can_run=a["points_only"]["can_run"], missing_results=a["counts"]["missing_results"], remaining=a["counts"]["remaining_to_simulate"], blockers=a["points_only"]["blockers"])
    finally:
        conn.close()
out["simulation_eligibility"] = elig
print(json.dumps(out, indent=1, default=str))
(Path(__file__).with_name(f"compare_{LABEL}.json")).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
