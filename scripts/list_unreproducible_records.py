"""Lists the records of the production store that the PUBLISHED-evidence rebuild cannot reproduce (Phase 4.36). Compares a published-evidence replay (scripts/rebuild_current_state.py <folder> published)
with a store of the same schema. Scores are NOT written: only the teams, the dates and the status, with the reason.

    python scripts/list_unreproducible_records.py <replay.sqlite> <reference.sqlite> [output.csv]

<reference.sqlite> is the maintainer's current store (opened read-only). Without it the published evidence file (data/evidence/published) already lists every decision and why it is not applied."""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rep = sqlite3.connect(f"file:{Path(sys.argv[1]).resolve().as_posix()}?mode=ro", uri=True)
ref = sqlite3.connect(f"file:{Path(sys.argv[2]).resolve().as_posix()}?mode=ro", uri=True)
out = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "data" / "evidence" / "published" / "NOT_REPRODUCIBLE_FROM_PUBLISHED_EVIDENCE.csv"
SIX = "('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL')"
cols = "record_id, competition_key, home_name, away_name, status, match_date"
A = {r[0]: r for r in ref.execute(f"select {cols} from matches where season='2026-27' and competition_key in {SIX}")}
B = {r[0]: r for r in rep.execute(f"select {cols} from matches where season='2026-27' and competition_key in {SIX}")}
rows = []
for k, a in A.items():
    b = B.get(k)
    if b is None:
        continue
    done = ("completed", "awarded")
    if a[4] in done and b[4] not in done:
        rows.append((a[1], k, a[2], a[3], a[4], a[5], b[4], b[5], "result: second source not redistributable (Wikipedia plus a restricted cross-check source)"))
    elif a[5] != b[5]:
        rows.append((a[1], k, a[2], a[3], a[4], a[5], b[4], b[5], "date correction: second source not redistributable"))
rows.sort()
with open(out, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["competition_key", "record_id", "home", "away", "reference_status", "reference_date", "published_replay_status", "published_replay_date", "reason"])
    w.writerows(rows)
by = {}
for r in rows:
    by.setdefault((r[0], r[8].split(":")[0]), 0)
    by[(r[0], r[8].split(":")[0])] += 1
print(len(rows), "records;", by)
