"""Phase 4.22: read-only verification of production after the approved import (71 domestic results + 90 Champions League fixtures), compared with the byte-identical backup taken before it."""
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DB = ROOT / "data" / "footiq.sqlite"
BK = ROOT / "data" / "backups" / "p422_pre_import_20261028" / "footiq.sqlite"


def conn(p):
    c = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


now, old = conn(DB), conn(BK)
out = {}
out["integrity"] = now.execute("PRAGMA integrity_check").fetchone()[0]
out["foreign_key_problems"] = len(now.execute("PRAGMA foreign_key_check").fetchall())
out["journal_mode"] = now.execute("PRAGMA journal_mode").fetchone()[0]
out["matches"] = dict(before=old.execute("SELECT COUNT(*) FROM matches").fetchone()[0], after=now.execute("SELECT COUNT(*) FROM matches").fetchone()[0])
out["completed_2026_27"] = dict(now.execute("SELECT competition_key, COUNT(*) FROM matches WHERE season='2026-27' AND status='completed' AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') GROUP BY 1").fetchall())
out["ucl_2026_27_by_status"] = dict(now.execute("SELECT status, COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' GROUP BY 1").fetchall())
out["ucl_2026_27_by_stage"] = dict(now.execute("SELECT stage, COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' GROUP BY 1 ORDER BY 1").fetchall())
out["ucl_non_league_phase_rows"] = now.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' AND stage NOT LIKE 'Matches > Matchday %'").fetchone()[0]
out["ucl_fixture_dates"] = dict(now.execute("SELECT stage, MIN(match_date) || ' to ' || MAX(match_date) FROM matches WHERE competition_key='UCL' AND season='2026-27' AND status='scheduled' GROUP BY stage ORDER BY stage").fetchall())

# every row that existed before: identical, except exactly the 71 domestic fixtures that received a result
bh = dict(old.execute("SELECT record_id, content_hash FROM matches").fetchall())
nh = dict(now.execute("SELECT record_id, content_hash FROM matches").fetchall())
changed = sorted(r for r, h in bh.items() if nh.get(r) != h)
out["rows_missing_after"] = [r for r in bh if r not in nh]
out["changed_existing_rows"] = len(changed)
out["new_rows"] = len([r for r in nh if r not in bh])
ch = [dict(r) for r in now.execute(f"SELECT * FROM matches WHERE record_id IN ({','.join('?' * len(changed))})", changed)]
oldrows = {r["record_id"]: dict(r) for r in old.execute(f"SELECT * FROM matches WHERE record_id IN ({','.join('?' * len(changed))})", changed)}
out["changed_rows_by_competition"] = {}
for r in ch:
    out["changed_rows_by_competition"][r["competition_key"]] = out["changed_rows_by_competition"].get(r["competition_key"], 0) + 1
out["changed_rows_were_open_fixtures"] = all(oldrows[r["record_id"]]["status"] in ("scheduled", "awaiting_result") for r in ch)
out["changed_rows_keep_date_clubs_and_id"] = all(oldrows[r["record_id"]][k] == r[k] for r in ch for k in ("match_date", "home_entity_id", "away_entity_id", "competition_key", "season", "stage", "matchday_no"))
out["changed_rows_now_completed_wikipedia_in_universe"] = all(r["status"] == "completed" and r["source_system"] == "wikipedia" and r["licence"] == "CC BY-SA 4.0" and r["in_universe"] == 1 and r["home_goals_final"] is not None for r in ch)
out["new_rows_are_ucl_scheduled_fixtures"] = all(r["competition_key"] == "UCL" and r["season"] == "2026-27" and r["status"] == "scheduled" and r["in_universe"] == 0 and r["home_goals_final"] is None
                                                 for r in now.execute("SELECT * FROM matches WHERE record_id NOT IN (SELECT record_id FROM matches WHERE 0)") if r["record_id"] not in bh)
out["archived_rows_unchanged"] = all(nh[r] == bh[r] for r in bh if r not in changed) and not any(oldrows[r]["competition_key"] in ("UEL", "UECL", "WC", "UNL", "COPA") for r in changed)
out["duplicates_same_pair_2026_27"] = now.execute("SELECT COUNT(*) FROM (SELECT 1 FROM matches WHERE season='2026-27' AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') GROUP BY competition_key, home_entity_id, away_entity_id HAVING COUNT(*)>1)").fetchone()[0]
out["duplicates_ucl_all_seasons_same_day"] = now.execute("SELECT COUNT(*) FROM (SELECT 1 FROM matches WHERE competition_key='UCL' GROUP BY season, match_date, home_entity_id, away_entity_id HAVING COUNT(*)>1)").fetchone()[0]
out["orphan_team_ids"] = now.execute("SELECT COUNT(*) FROM matches m WHERE m.competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') AND m.season='2026-27' AND (m.home_entity_id NOT IN (SELECT entity_id FROM teams) OR m.away_entity_id NOT IN (SELECT entity_id FROM teams))").fetchone()[0]
out["completed_without_score"] = now.execute("SELECT COUNT(*) FROM matches WHERE status='completed' AND (home_goals_final IS NULL OR away_goals_final IS NULL) AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL')").fetchone()[0]
out["match_sources_new"] = [tuple(r) for r in now.execute("SELECT source, role, snapshot_id, COUNT(*) FROM match_sources WHERE snapshot_id LIKE 'wikipedia-%' OR snapshot_id LIKE 'uefa-ucl-2026-27-staging-rev1381604353' GROUP BY source, role, snapshot_id ORDER BY snapshot_id")]
out["source_snapshots_new"] = [tuple(r) for r in now.execute("SELECT snapshot_id, revision, licence FROM source_snapshots WHERE snapshot_id LIKE 'wikipedia-%' OR snapshot_id LIKE 'uefa-ucl-%' ORDER BY 1")]
out["sync_runs_new"] = [tuple(r) for r in now.execute("SELECT run_id, kind, outcome, inserted, updated, unchanged, quarantined FROM sync_runs WHERE kind IN ('league_results_import','uefa_import') ORDER BY run_id DESC LIMIT 3")]
sims = lambda c: hashlib.sha256(json.dumps([tuple(x) for x in c.execute("SELECT * FROM simulation_runs ORDER BY simulation_run_id")], default=str).encode()).hexdigest()
out["simulations"] = dict(rows=[tuple(r) for r in now.execute("SELECT simulation_run_id, competition_key, season, n_simulations FROM simulation_runs ORDER BY 1")], sha_before=sims(old), sha_after=sims(now))
out["simulations_unchanged"] = out["simulations"]["sha_before"] == out["simulations"]["sha_after"]
out["quarantine"] = dict(before=old.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0], after=now.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0])
out["backup_sha256"] = hashlib.sha256(BK.read_bytes()).hexdigest()
out["wal_bytes"] = Path(str(DB) + "-wal").stat().st_size if Path(str(DB) + "-wal").exists() else 0
(Path(__file__).resolve().parent / "after_import_verification.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps(out, indent=1, default=str, ensure_ascii=False))
