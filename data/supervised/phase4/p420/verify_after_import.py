"""Phase 4.20 part A: read-only checks of the production store after the 18-result Champions League import."""
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DB = ROOT / "data" / "footiq.sqlite"
BK = ROOT / "data" / "backups" / "p420_pre_import_20261028" / "footiq.sqlite"


def q(path):
    c = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    r = dict(
        integrity=c.execute("PRAGMA integrity_check").fetchone()[0], fk_problems=len(c.execute("PRAGMA foreign_key_check").fetchall()),
        matches=c.execute("SELECT COUNT(*) FROM matches").fetchone()[0],
        ucl_by_season=dict(c.execute("SELECT season, COUNT(*) FROM matches WHERE competition_key='UCL' GROUP BY 1").fetchall()),
        other_rows_hash=hashlib.sha256(json.dumps(c.execute("SELECT record_id, content_hash FROM matches WHERE NOT (competition_key='UCL' AND season='2026-27') ORDER BY record_id").fetchall()).encode()).hexdigest(),
        old_ucl_2026_27_rows_hash=hashlib.sha256(json.dumps(c.execute("SELECT record_id, content_hash FROM matches WHERE competition_key='UCL' AND season='2026-27' AND record_id NOT LIKE 'WP:UCL:%' ORDER BY record_id").fetchall()).encode()).hexdigest(),
        simulations=[tuple(x) for x in c.execute("SELECT simulation_run_id, competition_key, season, n_simulations FROM simulation_runs ORDER BY 1")],
        simulations_sha=hashlib.sha256(json.dumps([tuple(x) for x in c.execute("SELECT * FROM simulation_runs ORDER BY simulation_run_id")], default=str).encode()).hexdigest(),
        quarantine=c.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0], teams=c.execute("SELECT COUNT(*) FROM teams").fetchone()[0],
        team_aliases=c.execute("SELECT COUNT(*) FROM team_aliases").fetchone()[0])
    if path == DB:
        r["new_rows"] = [tuple(x) for x in c.execute("SELECT match_date, home_name, home_goals_final, away_goals_final, away_name, status, source_system, licence, in_universe FROM matches WHERE record_id LIKE 'WP:UCL:2026-27:%' ORDER BY match_date, home_name")]
        r["duplicates_same_pair"] = c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM matches WHERE competition_key='UCL' AND season='2026-27' GROUP BY home_entity_id, away_entity_id HAVING COUNT(*)>1)").fetchone()[0]
        r["duplicates_same_day_any"] = c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM matches WHERE competition_key='UCL' GROUP BY season, match_date, home_entity_id, away_entity_id HAVING COUNT(*)>1)").fetchone()[0]
        r["bad_scores"] = c.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND status='completed' AND (home_goals_final IS NULL OR away_goals_final IS NULL OR home_goals_final<0 OR away_goals_final<0)").fetchone()[0]
        r["match_sources"] = [tuple(x) for x in c.execute("SELECT source, snapshot_id, licence, source_revision, COUNT(*) FROM match_sources WHERE snapshot_id LIKE 'uefa-ucl%' GROUP BY 1,2,3,4")]
        r["snapshot"] = [tuple(x) for x in c.execute("SELECT snapshot_id, sha256, revision, licence FROM source_snapshots WHERE snapshot_id LIKE 'uefa-ucl%'")]
        r["sync_run"] = [tuple(x) for x in c.execute("SELECT run_id, kind, source, outcome, inserted, updated, quarantined, latest_result_date FROM sync_runs WHERE kind='uefa_import'")]
        r["orphan_team_ids"] = c.execute("SELECT COUNT(*) FROM matches m WHERE m.competition_key='UCL' AND (m.home_entity_id NOT IN (SELECT entity_id FROM teams) OR m.away_entity_id NOT IN (SELECT entity_id FROM teams))").fetchone()[0]
    c.close()
    return r


before, after = q(BK), q(DB)
out = dict(before=before, after=after,
           only_ucl_2026_27_changed=before["other_rows_hash"] == after["other_rows_hash"], old_ucl_rows_unchanged=before["old_ucl_2026_27_rows_hash"] == after["old_ucl_2026_27_rows_hash"],
           simulations_unchanged=before["simulations_sha"] == after["simulations_sha"], quarantine_unchanged=before["quarantine"] == after["quarantine"],
           backup_sha256=hashlib.sha256(BK.read_bytes()).hexdigest(), production_sha256=hashlib.sha256(DB.read_bytes()).hexdigest())
(Path(__file__).resolve().parent / "after_import_verification.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k not in ("before",)}, indent=1, default=str, ensure_ascii=False)[:6500])
