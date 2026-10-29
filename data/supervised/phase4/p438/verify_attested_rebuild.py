"""Phase 4.38: checks the policy on rebuilt stores. Usage: verify_attested_rebuild.py <snapshot_replay.sqlite> <published_replay.sqlite> <out.json>"""
import csv, json, re, sqlite3, sys
ROOT = "D:/Foot IQ/"
snap, pub = [sqlite3.connect(f"file:{p}?mode=ro", uri=True) for p in sys.argv[1:3]]
un = [r["record_id"] for r in csv.DictReader(open(ROOT + "data/evidence/published/UNSUPPORTED_RESULTS.csv", encoding="utf-8-sig"))]
res = {}
q = "select count(*), count(distinct record_id) from match_sources where provenance like '%attested snapshot evidence%'"
res["snapshot_store_attested_provenance_rows"] = snap.execute(q).fetchone()
res["published_store_attested_provenance_rows"] = pub.execute(q).fetchone()
res["snapshot_attested_results_completed"] = snap.execute("select count(distinct ms.record_id) from match_sources ms join matches m using(record_id) where ms.provenance like '%attested snapshot evidence%' and m.status='completed'").fetchone()[0]
res["snapshot_sync_runs_labelled"] = snap.execute("select source, count(*) from sync_runs where source like 'attested%' group by 1").fetchall()
res["three_unsupported_results_status_in_snapshot"] = [snap.execute("select status, match_date, home_goals_final from matches where record_id=?", (r,)).fetchone() for r in un]
res["three_unsupported_results_status_in_published"] = [pub.execute("select status from matches where record_id=?", (r,)).fetchone() for r in un]
bad = re.compile(r"football-?data|fixturedownload|api-?football|statsbomb", re.I)
res["restricted_words_in_attested_provenance"] = sum(1 for (p,) in snap.execute("select provenance from match_sources where provenance like '%attested%'") if bad.search(p or ""))
res["sample_provenance"] = snap.execute("select source, substr(provenance,1,230) from match_sources where provenance like '%attested%' limit 2").fetchall()
res["completed_snapshot"] = dict(snap.execute("select competition_key,count(*) from matches where season='2026-27' and status in ('completed','awarded') and competition_key in ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') group by 1").fetchall())
res["completed_published"] = dict(pub.execute("select competition_key,count(*) from matches where season='2026-27' and status in ('completed','awarded') and competition_key in ('EPL','LALIGA','BUNDESLIGA','SERIEA','LIGUE1','UCL') group by 1").fetchall())
json.dump(res, open(sys.argv[3], "w"), indent=1, default=str); print(json.dumps(res, indent=1, default=str))
