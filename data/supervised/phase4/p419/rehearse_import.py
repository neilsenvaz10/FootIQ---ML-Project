"""Phase 4.19 step 4: rehearse the Champions League import on PRIVATE COPIES of the production store (never on production). Production is only read (sqlite backup API from a mode=ro connection)
and its sha256 is compared before and after. Writes rehearsal_report.json; the copies stay in rehearsal/ (git-ignored data folder) for the compatibility check."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "app"))
from store import uefa_import as U  # noqa: E402

PROD = ROOT / "data" / "footiq.sqlite"
REH = HERE / "rehearsal"
REH.mkdir(exist_ok=True)
AS_OF = "2026-10-28"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def copy_store(dst):
    dst = Path(dst)
    for ext in ("", "-wal", "-shm"):
        Path(str(dst) + ext).unlink(missing_ok=True)                  # only this script's own rehearsal copies are replaced
    src = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
    out = sqlite3.connect(dst)
    src.backup(out)
    out.close()
    src.close()
    return dst


def snapshot(p):
    c = sqlite3.connect(f"file:{Path(p).as_posix()}?mode=ro", uri=True)
    r = dict(integrity=c.execute("PRAGMA integrity_check").fetchone()[0], fk_problems=len(c.execute("PRAGMA foreign_key_check").fetchall()),
             matches=c.execute("SELECT COUNT(*) FROM matches").fetchone()[0], ucl_2026_27=c.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0],
             other_rows_hash=hashlib.sha256(json.dumps(c.execute("SELECT record_id, content_hash FROM matches WHERE NOT (competition_key='UCL' AND season='2026-27') ORDER BY record_id").fetchall()).encode()).hexdigest(),
             sim_runs=c.execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0], quarantine=c.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0])
    c.close()
    return r


prod_before = sha(PROD)
rep = {"production_sha256_before": prod_before}
a = copy_store(REH / "footiq_results_only.sqlite")
rep["baseline"] = snapshot(a)
r1 = U.run(a, apply=True, as_of=AS_OF, report_dir=REH)
rep["results_only_first_apply"] = dict(counts=r1["counts"], applied=r1["applied"], after=snapshot(a))
r2 = U.run(a, apply=True, as_of=AS_OF)
rep["results_only_second_apply"] = dict(counts=r2["counts"], applied=r2["applied"], after=snapshot(a))

b = copy_store(REH / "footiq_with_fixtures.sqlite")
r3 = U.run(b, apply=True, include_fixtures=True, as_of=AS_OF, report_dir=REH)
rep["with_fixtures_first_apply"] = dict(counts=r3["counts"], applied=r3["applied"], after=snapshot(b))
r4 = U.run(b, apply=True, include_fixtures=True, as_of=AS_OF)
rep["with_fixtures_second_apply"] = dict(counts=r4["counts"], applied=r4["applied"], after=snapshot(b))
cb = sqlite3.connect(b)
rep["with_fixtures_status_counts"] = dict(cb.execute("SELECT status, COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' GROUP BY 1").fetchall())
rep["no_other_row_changed"] = snapshot(b)["other_rows_hash"] == rep["baseline"]["other_rows_hash"] and snapshot(a)["other_rows_hash"] == rep["baseline"]["other_rows_hash"]
cb.close()

# conflict handling: a stored row that disagrees with the verified staging is quarantined and never overwritten; a fixture that gets its result later is completed in place
d = copy_store(REH / "footiq_conflicts.sqlite")
cd = sqlite3.connect(d)
cd.execute("UPDATE matches SET home_goals_final=9 WHERE competition_key='UCL' AND season='2026-27' AND home_name='AEK Athens F.C.'")                  # matchday 1 row with a wrong score
cd.commit()
cd.close()
r5 = U.run(d, apply=True, as_of=AS_OF)
c5 = sqlite3.connect(d)
rep["conflict_case"] = dict(counts=r5["counts"], applied=r5["applied"], stored_score_still=c5.execute("SELECT home_goals_final FROM matches WHERE home_name='AEK Athens F.C.' AND season='2026-27'").fetchone()[0],
                            quarantined=c5.execute("SELECT reason FROM quarantine WHERE source='wikipedia' AND reason LIKE 'quarantine_conflict%'").fetchall())
c5.close()

# fixtures first, result afterwards: the verified results complete the stored fixtures in place (no second row). A staging file as it looked before matchday 2 was played is made from the real one.
import pandas as pd  # noqa: E402
e = copy_store(REH / "footiq_fixture_then_result.sqlite")
early = U.load_staging(U.STAGING)
md2 = early.matchday == 2
early.loc[md2, ["home_goals", "away_goals"]] = float("nan")
early.loc[md2, "status"] = "scheduled"
early_path = REH / "staging_before_matchday2.csv"
early.to_csv(early_path, index=False, encoding="utf-8-sig")
U.run(e, apply=True, include_fixtures=True, staging=early_path, as_of="2026-10-12")
ce = sqlite3.connect(e)
before = dict(ce.execute("SELECT status, COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' AND stage LIKE '%Matchday 2' GROUP BY 1").fetchall())
n_before = ce.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0]
ce.close()
r6 = U.run(e, apply=True, include_fixtures=True, as_of=AS_OF)
ce = sqlite3.connect(e)
rep["fixture_then_result"] = dict(matchday2_before=before, rows_before=n_before, rows_after=ce.execute("SELECT COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27'").fetchone()[0], counts=r6["counts"], applied=r6["applied"],
                                  matchday2_after=dict(ce.execute("SELECT status, COUNT(*) FROM matches WHERE competition_key='UCL' AND season='2026-27' AND stage LIKE '%Matchday 2' GROUP BY 1").fetchall()))
ce.close()

# the production guard
guard = {}
for label, kw in (("no_production_flag", dict()), ("production_flag_without_backup", dict(production=True)), ("production_flag_with_wrong_backup", dict(production=True, backup=a))):
    try:
        U.run(PROD, apply=True, **kw)
        guard[label] = "WROTE (bad)"
    except SystemExit as ex:
        guard[label] = f"refused: {ex}"
rep["production_guard"] = guard
rep["production_sha256_after"] = sha(PROD)
rep["production_unchanged"] = rep["production_sha256_before"] == rep["production_sha256_after"]
(HERE / "rehearsal_report.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps(rep, indent=1, default=str, ensure_ascii=False)[:7000])
