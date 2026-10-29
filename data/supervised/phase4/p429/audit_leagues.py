"""Phase 4.29: read-only audit of the five domestic leagues for the season simulator (counts, duplicates, statuses, team counts). Opens the production store read-only."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
c = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
for k in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"):
    rows = c.execute("SELECT status, COUNT(*), SUM(COALESCE(home_goals_90,home_goals_final) IS NULL) FROM matches WHERE competition_key=? AND season='2026-27' AND kind='club' GROUP BY status", (k,)).fetchall()
    total = sum(r[1] for r in rows)
    teams = c.execute("SELECT COUNT(DISTINCT t) FROM (SELECT COALESCE(model_home_entity,home_entity_id) t FROM matches WHERE competition_key=? AND season='2026-27' AND kind='club' UNION SELECT COALESCE(model_away_entity,away_entity_id) FROM matches WHERE competition_key=? AND season='2026-27' AND kind='club')", (k, k)).fetchone()[0]
    dup = c.execute("SELECT COUNT(*) FROM (SELECT COALESCE(model_home_entity,home_entity_id) h, COALESCE(model_away_entity,away_entity_id) a, COUNT(*) n FROM matches WHERE competition_key=? AND season='2026-27' AND kind='club' GROUP BY h,a HAVING n>1)", (k,)).fetchone()[0]
    nullid = c.execute("SELECT COUNT(*) FROM matches WHERE competition_key=? AND season='2026-27' AND kind='club' AND (home_entity_id IS NULL OR away_entity_id IS NULL)", (k,)).fetchone()[0]
    print(k, "total", total, "teams", teams, "duplicate home-away pairs", dup, "null team identity", nullid, "statuses (status, n, rows without goals):", rows)
