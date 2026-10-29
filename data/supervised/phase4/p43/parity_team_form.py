"""Is variant B identical to the current team_form? Old statement versus the INDEXED BY statement versus an independent pure-Python oracle, on a broad sample.

    FOOTIQ_STORE_PATH=<private copy> .venv/Scripts/python.exe -X utf8 data/supervised/phase4/p43/parity_team_form.py [sample_size]

Run BEFORE gameweeks.py is edited. Reads only. Every call is also checked for time safety: no returned match is dated on or after the cutoff, none is unplayed or without a score."""
import json
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIVE, form_with, OLD_SQL, NEW_SQL, private_copy_path, team_form_b, team_form_old  # noqa: E402

import gameweeks  # noqa: E402
from store import db  # noqa: E402

SAMPLE = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
path = private_copy_path()
conn = db.connect(path, readonly=True)
rng = random.Random(20261027)

comp_ids = {k: conn.execute("SELECT competition_id FROM competitions WHERE competition_key=?", (k,)).fetchone()[0] for k in FIVE}
names = dict(conn.execute("SELECT entity_id, display_name FROM teams").fetchall())

# every fixture of the five leagues (all seasons): (competition_id, season, matchday, date, status, home, away, record_id)
fx = [tuple(r) for r in conn.execute("SELECT competition_id, season, matchday_no, match_date, status, home_entity_id, away_entity_id, record_id FROM matches WHERE competition_key IN (%s) AND kind='club'" % ",".join("?" * 5), FIVE)]
print("fixtures in the five leagues:", len(fx))

# ---- the oracle: the specification, written independently of SQL ("last n completed results of a team in this competition dated strictly before the cutoff")
hist = {}
for r in conn.execute("SELECT competition_id, match_date, record_id, home_entity_id, away_entity_id, home_goals_final, away_goals_final FROM matches WHERE competition_id IN (%s) AND status IN ('completed','awarded') AND home_goals_final IS NOT NULL" % ",".join("?" * 5), list(comp_ids.values())):
    for ent in {r["home_entity_id"], r["away_entity_id"]} - {None}:
        hist.setdefault((r["competition_id"], ent), []).append(tuple(r))
for v in hist.values():
    v.sort(key=lambda x: (x[1], x[2]))


def oracle(cid, ent, before, n=5):
    if ent is None:
        return []
    rows = [x for x in hist.get((cid, ent), []) if x[1] < before][-n:]
    out = []
    for _cid, d, _rid, h, a, hg, ag in rows:
        home = h == ent
        gf, ga = (hg, ag) if home else (ag, hg)
        out.append(dict(date=d, opponent=names.get(a if home else h), venue="H" if home else "A", gf=gf, ga=ga, result="W" if gf > ga else "D" if gf == ga else "L"))
    return out


def pairs(rows):
    for cid, season, md, d, status, h, a, rid in rows:
        yield (cid, h, d, status, season, md, rid, "home")
        yield (cid, a, d, status, season, md, rid, "away")


# ---- the broad sample for old-versus-new: stratified by league and season, plus every special case present in the data
by_ls = {}
for row in fx:
    by_ls.setdefault((row[0], row[1]), []).append(row)
chosen = {}
per_stratum = max(5, SAMPLE // (2 * len(by_ls)))
for key, rows in sorted(by_ls.items()):
    for row in rng.sample(rows, min(per_stratum, len(rows))):
        chosen[row[7]] = row
specials = Counter()
for row in fx:
    cid, season, md, d, status, h, a, rid = row
    tag = None
    if status in ("scheduled", "awaiting_result", "abandoned", "awarded") and season >= "2025-26":
        tag = "status_" + status
    elif md is not None and md <= 2:
        tag = "first_matchdays"
    elif h is None or a is None:
        tag = "unmatched_club"
    if tag and specials[tag] < 120:
        specials[tag] += 1
        chosen[rid] = row
sample = list(pairs(chosen.values()))
print("old-versus-new sample:", len(chosen), "fixtures,", len(sample), "team-date calls; specials:", dict(specials))

# ---- sanity: the harness's copy of the old statement is the application's function (only meaningful before gameweeks.py is edited)
chk = rng.sample(sample, 25)
same_as_app = all(form_with(OLD_SQL)(conn, c, e, d) == gameweeks.team_form(conn, c, e, d) for c, e, d, *_ in chk)
print("harness OLD_SQL equals gameweeks.team_form on 25 calls:", same_as_app)

plans = {k: [r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + s, ("c", "e", "e", "2026-01-01", 5))][0] for k, s in (("old", OLD_SQL), ("b", NEW_SQL))}
print("plans:", plans)

t_old = []
t_new = []
mism_old_new = []
mism_oracle = []
cats = Counter()
leak = []
for cid, ent, d, status, season, md, rid, side in sample:
    t = time.perf_counter(); a = team_form_old(conn, cid, ent, d); t_old.append(time.perf_counter() - t)
    t = time.perf_counter(); b = team_form_b(conn, cid, ent, d); t_new.append(time.perf_counter() - t)
    o = oracle(cid, ent, d)
    if a != b:
        mism_old_new.append(dict(record_id=rid, side=side, old=a, new=b))
    if a != o or b != o:
        mism_oracle.append(dict(record_id=rid, side=side, old=a, new=b, oracle=o))
    if any(m["date"] >= d for m in a + b):
        leak.append(dict(record_id=rid, side=side, before=d))
    cats[f"results_returned={len(a)}"] += 1
    cats[f"fixture_status={status}"] += 1
    if ent is None:
        cats["unmatched_club"] += 1

# ---- the oracle against variant B on every call a gameweek page of the two newest seasons could make
newest = {}
for row in fx:
    newest.setdefault(row[0], set()).add(row[1])
two = {cid: sorted(s)[-2:] for cid, s in newest.items()}
full = list(pairs([r for r in fx if r[1] in two[r[0]]]))
t = time.perf_counter()
mism_full = []
for cid, ent, d, status, season, md, rid, side in full:
    b = team_form_b(conn, cid, ent, d)
    if b != oracle(cid, ent, d) or any(m["date"] >= d for m in b):
        mism_full.append(dict(record_id=rid, side=side))
full_s = time.perf_counter() - t

out = dict(
    private_copy=path.name, harness_old_sql_equals_application_function=same_as_app, plans=plans,
    sample=dict(fixtures=len(chosen), calls=len(sample), specials=dict(specials), categories=dict(sorted(cats.items()))),
    old_versus_new_differences=len(mism_old_new), old_or_new_versus_oracle_differences=len(mism_oracle), future_data_leaks=len(leak),
    oracle_versus_new_on_two_newest_seasons=dict(calls=len(full), differences=len(mism_full), seconds=round(full_s, 1)),
    seconds_per_call=dict(old_median=round(statistics.median(t_old), 3), new_median=round(statistics.median(t_new), 3), old_max=round(max(t_old), 3), new_max=round(max(t_new), 3)),
    first_differences=(mism_old_new + mism_oracle + mism_full)[:5],
)
Path(__file__).with_name("parity_team_form.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "sample"}, indent=1))
print("sample categories:", json.dumps(out["sample"]["categories"]))
