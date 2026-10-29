"""Phase 4.24: read-only verification of production after the approved strong-tier reconciliation, against the byte-identical backup taken before it."""
import hashlib
import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
DB = ROOT / "data" / "footiq.sqlite"
BK = ROOT / "data" / "backups" / "p424_pre_reconcile_20261028" / "footiq.sqlite"
PROP = ROOT / "data" / "supervised" / "phase4" / "p423" / "staging" / "proposed_changes.csv"


def conn(p):
    c = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


now, old = conn(DB), conn(BK)
prop = pd.read_csv(PROP, encoding="utf-8-sig")
strong = prop[prop.tier == "strong"]
other = prop[prop.tier != "strong"]
out = {}
out["integrity"] = now.execute("PRAGMA integrity_check").fetchone()[0]
out["foreign_key_problems"] = len(now.execute("PRAGMA foreign_key_check").fetchall())
out["matches"] = dict(before=old.execute("SELECT COUNT(*) FROM matches").fetchone()[0], after=now.execute("SELECT COUNT(*) FROM matches").fetchone()[0])
out["completed_2026_27"] = dict(now.execute("SELECT competition_key, COUNT(*) FROM matches WHERE season='2026-27' AND status='completed' AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') GROUP BY 1").fetchall())
out["ucl_2026_27_by_status"] = dict(now.execute("SELECT status, COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' GROUP BY 1").fetchall())
out["open_past_dated"] = [tuple(r) for r in now.execute("SELECT competition_key, match_date, home_name, away_name, status FROM matches WHERE season='2026-27' AND status IN ('scheduled','awaiting_result') AND match_date < '2026-10-28' AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1') ORDER BY 1,2")]
bh = dict(old.execute("SELECT record_id, content_hash FROM matches").fetchall())
nh = dict(now.execute("SELECT record_id, content_hash FROM matches").fetchall())
changed = sorted(r for r, h in bh.items() if nh.get(r) != h)
out["rows_missing_after"] = [r for r in bh if r not in nh]
out["rows_added"] = len([r for r in nh if r not in bh])
out["changed_rows"] = len(changed)
out["changed_rows_are_exactly_the_43_strong_proposals"] = changed == sorted(strong.record_id)
out["non_approved_proposals_untouched"] = all(nh[r] == bh[r] for r in other.record_id)
out["non_approved_counts"] = dict(rows=len(other), by_action=other.groupby("action").size().to_dict())
rows_now = {r["record_id"]: dict(r) for r in now.execute(f"SELECT * FROM matches WHERE record_id IN ({','.join('?' * len(strong))})", list(strong.record_id))}
rows_old = {r["record_id"]: dict(r) for r in old.execute(f"SELECT * FROM matches WHERE record_id IN ({','.join('?' * len(strong))})", list(strong.record_id))}
bad = []
for p in strong.itertuples():
    n, o = rows_now[p.record_id], rows_old[p.record_id]
    ok = n["match_date"] == p.new_date and (n["home_entity_id"], n["away_entity_id"], n["competition_key"], n["season"], n["stage"]) == (o["home_entity_id"], o["away_entity_id"], o["competition_key"], o["season"], o["stage"])
    if p.action in ("add_result", "add_result_with_date"):
        ok = ok and n["status"] == "completed" and (n["home_goals_final"], n["away_goals_final"]) == (int(p.home_goals), int(p.away_goals)) and o["status"] in ("scheduled", "awaiting_result") and o["home_goals_final"] is None
        ok = ok and n["in_universe"] == 1 and n["source_system"] == "wikipedia" and n["licence"] == "CC BY-SA 4.0"
    else:
        ok = ok and n["status"] == o["status"] == "scheduled" and n["home_goals_final"] is None and n["time_precision"] == "date_only" and n["kickoff_local"] is None
    if not ok:
        bad.append(p.change_id)
out["rows_not_matching_their_proposal"] = bad
out["changes_by_type"] = {f"{k[0]}:{k[1]}": int(v) for k, v in strong.groupby(["competition_key", "action"]).size().items()}
out["results_with_corrected_played_date"] = int((strong.action == "add_result_with_date").sum())
out["no_verified_result_overwritten"] = all(nh[r] == bh[r] for r, row in ((r, 0) for r in bh) if old.execute("SELECT status FROM matches WHERE record_id=?", (r,)).fetchone()[0] == "completed")
out["archived_rows_unchanged"] = all(nh[r] == bh[r] for (r,) in old.execute("SELECT record_id FROM matches WHERE competition_key IN ('UEL','UECL','WC','UNL','COPA')"))
out["duplicates_same_pair_2026_27"] = now.execute("SELECT COUNT(*) FROM (SELECT 1 FROM matches WHERE season='2026-27' AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') GROUP BY competition_key, home_entity_id, away_entity_id HAVING COUNT(*)>1)").fetchone()[0]
out["duplicates_same_day_any"] = now.execute("SELECT COUNT(*) FROM (SELECT 1 FROM matches WHERE competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') GROUP BY competition_key, season, match_date, home_entity_id, away_entity_id HAVING COUNT(*)>1)").fetchone()[0]
out["orphan_team_ids"] = now.execute("SELECT COUNT(*) FROM matches m WHERE m.season='2026-27' AND m.competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') AND (m.home_entity_id NOT IN (SELECT entity_id FROM teams) OR m.away_entity_id NOT IN (SELECT entity_id FROM teams))").fetchone()[0]
out["completed_without_score"] = now.execute("SELECT COUNT(*) FROM matches WHERE status='completed' AND (home_goals_final IS NULL OR away_goals_final IS NULL) AND competition_key IN ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL')").fetchone()[0]
qh = lambda c: hashlib.sha256(repr([tuple(r) for r in c.execute("SELECT id, run_id, source, source_ref, reason, payload, created_utc FROM quarantine ORDER BY id").fetchall()]).encode()).hexdigest()
out["quarantine"] = dict(before=old.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0], after=now.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0], rows_identical=qh(old) == qh(now))
sims = lambda c: hashlib.sha256(json.dumps([tuple(x) for x in c.execute("SELECT * FROM simulation_runs ORDER BY simulation_run_id")], default=str).encode()).hexdigest()
out["simulations"] = dict(rows=[tuple(r) for r in now.execute("SELECT simulation_run_id, competition_key, season, n_simulations FROM simulation_runs ORDER BY 1")], unchanged=sims(old) == sims(now), sha=sims(now))
out["provenance"] = dict(match_sources=now.execute("SELECT COUNT(*) FROM match_sources WHERE source='reconciliation'").fetchone()[0], snapshots=[tuple(r) for r in now.execute("SELECT snapshot_id, substr(sha256,1,12) FROM source_snapshots WHERE snapshot_id LIKE 'reconcile-p423-%'")],
                         sync_run=[tuple(r) for r in now.execute("SELECT run_id, kind, outcome, inserted, updated, unchanged, quarantined FROM sync_runs WHERE kind='reconcile_import'")])
out["other_tables_unchanged"] = {t: old.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == (now.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] - (1 if t == "sync_runs" else 0) - (43 if t == "match_sources" else 0) - (1 if t == "source_snapshots" else 0)) for t in ("teams", "team_aliases", "competitions", "forecasts", "forecast_runs", "match_sources", "source_snapshots", "sync_runs", "simulation_runs", "quarantine")}
out["backup_sha256"] = hashlib.sha256(BK.read_bytes()).hexdigest()
out["wal_bytes"] = Path(str(DB) + "-wal").stat().st_size if Path(str(DB) + "-wal").exists() else 0
# a fingerprint of every match row right after the import, to isolate what the startup refresh changes later
Path(HERE := Path(__file__).resolve().parent).joinpath("after_import_row_hashes.json").write_text(json.dumps(nh), encoding="utf-8")
(HERE / "after_import_verification.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps(out, indent=1, default=str, ensure_ascii=False))
