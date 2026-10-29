"""Phase 4.21 part D: READ-ONLY check of the La Liga fixtures that are past their date without a result, to be run AFTER the next authorized startup refresh (it makes no request and triggers no refresh).
Compares the store with the Phase 4.20 findings: 7 open fixtures (6 played per football-data.co.uk with dates 23-26 Oct, 1 suspended match)."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
c = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
rows = c.execute("SELECT record_id, match_date, home_name, away_name, status FROM matches WHERE competition_key='LALIGA' AND season='2026-27' AND status IN ('scheduled','awaiting_result') AND match_date < date('now') ORDER BY match_date").fetchall()
last = c.execute("SELECT kind, started_utc, outcome, requests, inserted, updated, quarantined FROM sync_runs WHERE kind='startup_check' ORDER BY run_id DESC LIMIT 1").fetchone()
print("last startup check:", last)
print("La Liga completed:", c.execute("SELECT COUNT(*) FROM matches WHERE competition_key='LALIGA' AND season='2026-27' AND status='completed'").fetchone()[0], "(93 before; 99 if the six played matches arrived)")
print("still past their date without a result:", len(rows))
for r in rows:
    print("  ", r[1], r[2], "v", r[3], r[4])
