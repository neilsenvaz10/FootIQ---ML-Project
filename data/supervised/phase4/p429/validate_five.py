"""Phase 4.29: validates the points-only simulation for the five domestic leagues on a PRIVATE COPY of the production store (the production file is only read).
Per league: small run first (1,000), seeded reproducibility, then 10,000. Independent oracle from plain SQL for completed / remaining counts, team count, current points and fixture accounting.
Usage: validate_five.py <copy.sqlite>   (the copy is made by the caller)."""
import json
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
from seasonsim import service  # noqa: E402

copy = Path(sys.argv[1])
out = {}
fails = []
for key in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"):
    c = sqlite3.connect(f"file:{copy.as_posix()}?mode=ro", uri=True)
    rows = c.execute("SELECT status, COALESCE(model_home_entity,home_entity_id), COALESCE(model_away_entity,away_entity_id), COALESCE(home_goals_90,home_goals_final), COALESCE(away_goals_90,away_goals_final) FROM matches WHERE competition_key=? AND season='2026-27' AND kind='club'", (key,)).fetchall()
    c.close()
    done = [r for r in rows if r[0] in ("completed", "awarded") and r[3] is not None]
    rem = len(rows) - len(done)
    pts = {}
    for _, h, a, hg, ag in done:
        pts[h] = pts.get(h, 0) + (3 if hg > ag else 1 if hg == ag else 0)
        pts[a] = pts.get(a, 0) + (3 if ag > hg else 1 if hg == ag else 0)
    teams = {r[1] for r in rows} | {r[2] for r in rows}
    per = {}
    t0 = time.time()
    small = service.run_points_only(key, "2026-27", 1000, 11, service.POINTS_ACTION, db_path=copy)
    small2 = service.run_points_only(key, "2026-27", 1000, 11, service.POINTS_ACTION, db_path=copy)
    big = service.run_points_only(key, "2026-27", 10000, 5, service.POINTS_ACTION, db_path=copy)
    per["seconds"] = round(time.time() - t0, 1)
    for tag, r, n in (("n1000", small, 1000), ("n10000", big, 10000)):
        t = r["result"]["summary"]["teams"]
        cur = sum(x["current_points"] for x in t)
        exp = sum(x["expected_points"] for x in t)
        chk = dict(
            teams=len(t) == len(teams), remaining=r["assumptions"]["remaining_fixtures"] == rem, remaining_per_team_sum=sum(x["remaining_fixtures"] for x in t) == 2 * rem,
            current_points=cur == sum(pts.values()) and all(x["current_points"] == pts.get(x["entity_id"], 0) for x in t),
            expected_between=cur + 2 * rem < exp < cur + 3 * rem, per_team_bounds=all(x["current_points"] <= x["points_min"] <= x["expected_points"] <= x["points_max"] <= x["current_points"] + 3 * x["remaining_fixtures"] for x in t),
            labelled=r["assumptions"]["label"].startswith("Experimental") and r["assumptions"]["mode"] == "points_only", simulations=r["assumptions"]["simulations"] == n,
            no_positions=all("p_title" not in x and "expected_rank" not in x for x in t), distribution_sums=all(abs(sum(x["distribution"]["probabilities"]) - 1) < 1e-9 for x in t))
        per[tag] = dict(checks=chk, completed=len(done), remaining=rem, teams=len(t), current_points_total=cur, expected_points_total=round(exp, 1), state=r["assumptions"]["eligibility"]["state"], bounds=r["result"]["position_bounds"]["status"],
                        top3=[(x["name"], x["current_points"], round(x["expected_points"], 1)) for x in t[:3]])
        for k, v in chk.items():
            if not v:
                fails.append(f"{key} {tag} {k}")
    per["reproducible"] = small["result"]["summary"]["teams"] == small2["result"]["summary"]["teams"] and small["assumptions"]["input_sha256"] == small2["assumptions"]["input_sha256"]
    if not per["reproducible"]:
        fails.append(f"{key} not reproducible")
    out[key] = per
    print(key, json.dumps({k: v for k, v in per.items() if k != "n1000"}, default=str)[:700])
Path(__file__).with_name("validate_five_result.json").write_text(json.dumps(dict(results=out, failures=fails), indent=1, default=str), encoding="utf-8")
print("FAILURES:", fails)
