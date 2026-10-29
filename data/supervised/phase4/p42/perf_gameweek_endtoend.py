"""P4.2 performance investigation, step 5: what would /api/gameweek cost with each proposed fix, and is its OUTPUT identical?

Uses gameweeks.gameweek_fixtures (the function behind /api/gameweek) with gameweeks.team_form replaced IN MEMORY by an equivalent statement; app/ is not edited.
    A  current code                      on the unmodified private copy
    B  same statement + INDEXED BY       on the unmodified private copy (no schema change)
    D  composite indexes + UNION ALL     on the experiment copy that perf_gameweek_experiments.py created (two extra indexes)
Every gameweek in the sample is fetched with A, B and D and the three JSON payloads are compared byte for byte.

    python data/supervised/phase4/p42/perf_gameweek_endtoend.py <private copy> <experiment copy>
"""
import json
import sqlite3
import statistics
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
import gameweeks as gw  # noqa: E402
from store import db  # noqa: E402

plain, exp = Path(sys.argv[1]), Path(sys.argv[2])
assert "rehearsal" in plain.parts and "rehearsal" in exp.parts
TODAY = date(2026, 10, 27)
SAMPLE = [("EPL", 1), ("EPL", 5), ("EPL", 8), ("EPL", 9), ("EPL", 10), ("EPL", 20), ("BUNDESLIGA", 6), ("BUNDESLIGA", 7), ("BUNDESLIGA", 8), ("LALIGA", 6)]

ORIGINAL = gw.team_form
COLS = "m.record_id, m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final, t1.display_name AS hn, t2.display_name AS an"
TEAMS = "LEFT JOIN teams t1 ON t1.entity_id=m.home_entity_id LEFT JOIN teams t2 ON t2.entity_id=m.away_entity_id"
HINT_SQL = (f"SELECT {COLS} FROM matches m INDEXED BY idx_matches_comp_season_date {TEAMS} WHERE m.competition_id=? AND (m.home_entity_id=? OR m.away_entity_id=?) "
            "AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL ORDER BY m.match_date DESC, m.record_id DESC LIMIT ?")
UNION_SQL = ("SELECT u.match_date, u.home_entity_id, u.away_entity_id, u.home_goals_final, u.away_goals_final, t1.display_name AS hn, t2.display_name AS an FROM ("
             "SELECT * FROM (SELECT m.record_id, m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final FROM matches m INDEXED BY ix_exp_home "
             "WHERE m.competition_id=? AND m.home_entity_id=? AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL "
             "UNION ALL SELECT m.record_id, m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final FROM matches m INDEXED BY ix_exp_away "
             "WHERE m.competition_id=? AND m.away_entity_id=? AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL) "
             "ORDER BY match_date DESC, record_id DESC LIMIT ?) u LEFT JOIN teams t1 ON t1.entity_id=u.home_entity_id LEFT JOIN teams t2 ON t2.entity_id=u.away_entity_id ORDER BY u.match_date DESC, u.record_id DESC")


def shape(rows, entity):
    out = []
    for r in reversed(rows):
        home = r["home_entity_id"] == entity
        gf, ga = (r["home_goals_final"], r["away_goals_final"]) if home else (r["away_goals_final"], r["home_goals_final"])
        out.append(dict(date=r["match_date"], opponent=(r["an"] if home else r["hn"]), venue="H" if home else "A", gf=gf, ga=ga, result="W" if gf > ga else "D" if gf == ga else "L"))
    return out


def team_form_hint(conn, competition_id, entity, before_date, n=5):
    return shape(conn.execute(HINT_SQL, (competition_id, entity, entity, before_date, n)).fetchall(), entity)


def team_form_union(conn, competition_id, entity, before_date, n=5):
    return shape(conn.execute(UNION_SQL, (competition_id, entity, before_date, competition_id, entity, before_date, n)).fetchall(), entity)


def run(path, fn):
    gw.team_form = fn
    conn = db.connect(path, readonly=True)
    out, secs = {}, []
    for key, md in SAMPLE:
        season = gw.seasons(conn, key)[0]
        t = time.perf_counter()
        out[(key, md)] = json.dumps(gw.gameweek_fixtures(conn, key, season, md, TODAY), sort_keys=True)
        secs.append(time.perf_counter() - t)
    conn.close()
    gw.team_form = ORIGINAL
    return out, secs


res = {}
for label, path, fn in (("D composite indexes + UNION ALL (experiment copy)", exp, team_form_union), ("B INDEXED BY hint (no schema change)", plain, team_form_hint), ("A current code", plain, ORIGINAL)):
    payloads, secs = run(path, fn)
    res[label] = dict(payloads=payloads, seconds_per_gameweek=[round(x, 3) for x in secs])
ref = res["A current code"]["payloads"]
report = {"gameweeks_compared": len(SAMPLE), "sample": [f"{k} matchday {m}" for k, m in SAMPLE]}
for label, v in res.items():
    diffs = sum(v["payloads"][k] != ref[k] for k in SAMPLE)
    secs = v["seconds_per_gameweek"]
    report[label] = dict(payload_bytes_total=sum(len(x) for x in v["payloads"].values()), differs_from_current=diffs, seconds_per_gameweek_median=round(statistics.median(secs), 3),
                         seconds_per_gameweek_max=round(max(secs), 3), seconds_per_gameweek=secs)
print(json.dumps(report, indent=1))
