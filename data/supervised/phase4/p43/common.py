"""Shared helpers for the P4.3 verification scripts (private copies only, read-only unless a script says otherwise).

OLD_SQL is the statement of gameweeks.team_form as it was at the end of P4.2; NEW_SQL is variant B (an INDEXED BY hint). `form_with` wraps either in the same
post-processing as the application function, so the two implementations can be compared in one process, before and after gameweeks.py is edited."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))

FIVE = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"]

OLD_SQL = (
    "SELECT m.match_date, m.home_entity_id, m.away_entity_id, m.home_goals_final, m.away_goals_final, t1.display_name AS hn, t2.display_name AS an FROM matches m "
    "LEFT JOIN teams t1 ON t1.entity_id=m.home_entity_id LEFT JOIN teams t2 ON t2.entity_id=m.away_entity_id "
    "WHERE m.competition_id=? AND (m.home_entity_id=? OR m.away_entity_id=?) AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL "
    "ORDER BY m.match_date DESC, m.record_id DESC LIMIT ?")
NEW_SQL = OLD_SQL.replace("FROM matches m ", "FROM matches m INDEXED BY idx_matches_comp_season_date ", 1)
assert NEW_SQL != OLD_SQL


def form_with(sql: str):
    def team_form(conn, competition_id: str, entity: str, before_date: str, n: int = 5) -> list[dict]:
        rows = conn.execute(sql, (competition_id, entity, entity, before_date, n)).fetchall()
        out = []
        for r in reversed(rows):
            home = r["home_entity_id"] == entity
            gf, ga = (r["home_goals_final"], r["away_goals_final"]) if home else (r["away_goals_final"], r["home_goals_final"])
            out.append(dict(date=r["match_date"], opponent=(r["an"] if home else r["hn"]), venue="H" if home else "A", gf=gf, ga=ga, result="W" if gf > ga else "D" if gf == ga else "L"))
        return out
    return team_form


team_form_old = form_with(OLD_SQL)
team_form_b = form_with(NEW_SQL)


def private_copy_path(env="FOOTIQ_STORE_PATH") -> Path:
    path = Path(os.environ[env])
    assert "rehearsal" in path.parts, "private copies only (a path inside a 'rehearsal' folder)"
    return path
