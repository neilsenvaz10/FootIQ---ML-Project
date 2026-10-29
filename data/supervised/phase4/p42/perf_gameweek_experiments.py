"""P4.2 performance investigation, step 3: why is team_form slow, and what would fix it? Runs on a SECOND private copy that it may modify
(ANALYZE, extra indexes); the first private copy, the production store and app/ are never touched.

    python data/supervised/phase4/p42/perf_gameweek_experiments.py <private copy> <experiment copy>

For every variant of the team_form statement it reports the query plan, how many rows the planner has to visit, the time per call (median and
minimum of 9 interleaved repetitions over the 20 teams of one gameweek) and whether the rows returned are IDENTICAL to the current statement for
every fixture of the two newest seasons of the five leagues (a read-only equivalence check; nothing is predicted).
"""
import json
import shutil
import sqlite3
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
from store import db  # noqa: E402

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
assert "rehearsal" in src.parts and "rehearsal" in dst.parts and src != dst, "private copies only"
shutil.copyfile(src, dst)
conn = sqlite3.connect(dst)
conn.row_factory = sqlite3.Row

COMMON_SELECT = ("SELECT m.record_id, m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final, t1.display_name AS hn, t2.display_name AS an FROM matches m {hint} "
                 "LEFT JOIN teams t1 ON t1.entity_id=m.home_entity_id LEFT JOIN teams t2 ON t2.entity_id=m.away_entity_id ")
TAIL = "ORDER BY m.match_date DESC, m.record_id DESC LIMIT ?"
CURRENT = COMMON_SELECT.format(hint="") + "WHERE m.competition_id=? AND (m.home_entity_id=? OR m.away_entity_id=?) AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL " + TAIL
HINTED = COMMON_SELECT.format(hint="INDEXED BY idx_matches_comp_season_date") + "WHERE m.competition_id=? AND (m.home_entity_id=? OR m.away_entity_id=?) AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL " + TAIL
UNION = ("SELECT * FROM (SELECT m.record_id, m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final FROM matches m INDEXED BY ix_exp_home WHERE m.competition_id=? AND m.home_entity_id=? AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL "
         "UNION ALL SELECT m.record_id, m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final FROM matches m INDEXED BY ix_exp_away WHERE m.competition_id=? AND m.away_entity_id=? AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL) "
         "ORDER BY match_date DESC, record_id DESC LIMIT ?")


def args_current(comp, ent, before, n=5):
    return (comp, ent, ent, before, n)


def args_union(comp, ent, before, n=5):
    return (comp, ent, before, comp, ent, before, n)


def keyrows(rows):
    return [(r[0], r[1]) for r in rows]          # (record_id, match_date): enough to show the same matches in the same order


comp_ids = {k: conn.execute("SELECT competition_id FROM competitions WHERE competition_key=?", (k,)).fetchone()[0] for k in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1")}
fixtures = []        # (competition_id, entity, date) for every club fixture of the two newest seasons of the five leagues
for key, cid in comp_ids.items():
    seasons = [r[0] for r in conn.execute("SELECT DISTINCT season FROM matches WHERE competition_key=? AND kind='club' ORDER BY season DESC LIMIT 2", (key,))]
    for season in seasons:
        for r in conn.execute("SELECT match_date, home_entity_id, away_entity_id FROM matches WHERE competition_id=? AND season=? AND home_entity_id IS NOT NULL AND away_entity_id IS NOT NULL", (cid, season)):
            fixtures.append((cid, r[1], r[0]))
            fixtures.append((cid, r[2], r[0]))
gw_sample = [(comp_ids["EPL"], r[0], "2026-10-31") for r in conn.execute("SELECT home_entity_id FROM matches WHERE competition_key='EPL' AND season='2026-27' AND matchday_no=9")] + \
            [(comp_ids["EPL"], r[0], "2026-10-31") for r in conn.execute("SELECT away_entity_id FROM matches WHERE competition_key='EPL' AND season='2026-27' AND matchday_no=9")]

out = {"private_copy": src.name, "fixtures_x_teams_checked_for_equality": len(fixtures), "gameweek_sample_calls": len(gw_sample)}


def rows_visited(comp, before):
    total = conn.execute("SELECT COUNT(*) FROM matches WHERE status IN ('completed','awarded') AND match_date<?", (before,)).fetchone()[0]
    same_comp = conn.execute("SELECT COUNT(*) FROM matches WHERE competition_id=? AND status IN ('completed','awarded') AND match_date<?", (comp, before)).fetchone()[0]
    return total, same_comp


total, same = rows_visited(comp_ids["EPL"], "2026-10-31")
out["rows_the_current_plan_walks_per_call"] = dict(completed_matches_before_the_fixture_date_in_the_whole_store=total, of_which_in_this_competition=same,
                                                       ratio=round(total / same, 1), matches_rows_in_store=conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0])


def timed(sql, argfn, sample):
    t = time.perf_counter()
    for comp, ent, before in sample:
        conn.execute(sql, argfn(comp, ent, before)).fetchall()
    return (time.perf_counter() - t) / len(sample)


def plan(sql, argfn):
    comp, ent, before = gw_sample[0]
    return [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + sql, argfn(comp, ent, before))]


def bench(label, sql, argfn, reps=9):
    # interleaving is done by the caller; this just times one repetition over the gameweek sample
    return timed(sql, argfn, gw_sample)


variants = {"A current statement (planner picks idx_matches_status_date)": (CURRENT, args_current)}
results = {}
repeats = {k: [] for k in variants}

# ---- B: same statement, planner told to use the competition/season/date index
variants["B same statement with INDEXED BY idx_matches_comp_season_date"] = (HINTED, args_current)
repeats["B same statement with INDEXED BY idx_matches_comp_season_date"] = []

# ---- C: ANALYZE (planner statistics), same statement as A
# ---- D: two new composite indexes + UNION ALL
for rep in range(9):
    for k, (sql, argfn) in variants.items():
        repeats[k].append(bench(k, sql, argfn))

for k, (sql, argfn) in variants.items():
    results[k] = dict(plan=plan(sql, argfn), ms_per_call_median=round(statistics.median(repeats[k]) * 1000, 1), ms_per_call_min=round(min(repeats[k]) * 1000, 1), ms_per_call_max=round(max(repeats[k]) * 1000, 1))

conn.execute("ANALYZE")
conn.commit()
variants_c = {"C current statement after ANALYZE": (CURRENT, args_current)}
reps_c = {k: [bench(k, sql, argfn) for _ in range(9)] for k, (sql, argfn) in variants_c.items()}
for k, (sql, argfn) in variants_c.items():
    results[k] = dict(plan=plan(sql, argfn), ms_per_call_median=round(statistics.median(reps_c[k]) * 1000, 1), ms_per_call_min=round(min(reps_c[k]) * 1000, 1), ms_per_call_max=round(max(reps_c[k]) * 1000, 1))

conn.execute("CREATE INDEX ix_exp_home ON matches (competition_id, home_entity_id, match_date)")
conn.execute("CREATE INDEX ix_exp_away ON matches (competition_id, away_entity_id, match_date)")
conn.commit()
variants_d = {"D two composite indexes + UNION ALL": (UNION, args_union)}
reps_d = {k: [bench(k, sql, argfn) for _ in range(9)] for k, (sql, argfn) in variants_d.items()}
for k, (sql, argfn) in variants_d.items():
    results[k] = dict(plan=plan(sql, argfn), ms_per_call_median=round(statistics.median(reps_d[k]) * 1000, 1), ms_per_call_min=round(min(reps_d[k]) * 1000, 1), ms_per_call_max=round(max(reps_d[k]) * 1000, 1))
out["variants"] = results

# ---- equivalence: B and D return the same matches in the same order as A for every fixture checked
mismatch_b = mismatch_d = 0
for comp, ent, before in fixtures:
    # A must be run without the ANALYZE effect on the plan; the result set does not depend on the plan
    a = keyrows(conn.execute(CURRENT, args_current(comp, ent, before)).fetchall())
    b = keyrows(conn.execute(HINTED, args_current(comp, ent, before)).fetchall())
    d = keyrows(conn.execute(UNION, args_union(comp, ent, before)).fetchall())
    mismatch_b += a != b
    mismatch_d += a != d
out["equivalence"] = dict(calls_compared=len(fixtures), B_differs_from_A=mismatch_b, D_differs_from_A=mismatch_d)
out["experiment_copy_bytes_after_indexes"] = dst.stat().st_size
print(json.dumps(out, indent=1))
conn.close()
