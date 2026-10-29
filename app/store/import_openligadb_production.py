"""APPROVED production import (2026-10-25) of the OpenLigaDB Premier League / La Liga snapshots, exactly as rehearsed.

    python app/store/import_openligadb_production.py

Stages (any failed check STOPS before the next one; a failure after writing starts is rolled back from the verified backup):
  1 no concurrent writers   2 timestamped backup that opens and passes integrity_check   3 production still equals the rehearsal's starting state
  4 apply (saved snapshots only, no network, dates protected)   5 compare with the approved rehearsal diff field by field   6 data checks.
"""
import csv
import json
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from store import db, rehearse_openligadb as R, sync, views  # noqa: E402

OUT = C.ROOT / "data" / "supervised" / "production_import"
REPORT = R.REH / "rehearsal_report.json"
KIND = "offline_snapshot_import"


class Stop(Exception):
    pass


def check(cond, msg):
    if not cond:
        raise Stop(msg)


def no_writers() -> dict:
    ps = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|uvicorn' } | ForEach-Object { $_.ProcessId.ToString() + ' ' + $_.CommandLine }"], capture_output=True, text=True).stdout
    import os
    mine = {str(os.getpid()), str(os.getppid())}                      # this process and its venv launcher
    others = [l for l in ps.splitlines() if l.strip() and l.split(" ")[0] not in mine and "powershell" not in l.lower()]
    ports = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count"], capture_output=True, text=True).stdout.strip()
    check(not others, f"other python processes are running: {others}")
    check(ports in ("0", ""), "something is listening on port 8000 (a backend could be writing)")
    c = sqlite3.connect(R.PROD, timeout=1)                          # an exclusive lock is only granted when nobody else holds the file
    try:
        c.execute("BEGIN EXCLUSIVE")
        c.execute("ROLLBACK")
    finally:
        c.close()
    return dict(other_python_processes=0, port_8000_listeners=0, exclusive_lock_acquired=True)


def backup(stamp: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"footiq.{stamp}.backup.sqlite"
    src = sqlite3.connect(R.PROD)
    dst = sqlite3.connect(path)
    src.backup(dst)
    dst.close()
    src.close()
    c = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    integ = c.execute("PRAGMA integrity_check").fetchall()
    fk = c.execute("PRAGMA foreign_key_check").fetchall()
    fp = R.table_fingerprints(c)
    c.close()
    check(integ == [("ok",)], f"backup integrity_check: {integ}")
    return dict(path=str(path.relative_to(C.ROOT)), bytes=path.stat().st_size, sha256=R.sha_file(path), integrity_check="ok", foreign_key_violations=len(fk), fingerprints=fp)


def restore(backup_path: Path) -> None:
    src = sqlite3.connect(f"file:{backup_path.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(R.PROD)
    src.backup(dst)
    dst.close()
    src.close()


def norm(v):
    return "" if v is None else str(v)


def main() -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rep = dict(started_utc=stamp, stages={})
    rh = json.loads(REPORT.read_text(encoding="utf-8"))
    rep["stages"]["1_writers"] = no_writers()

    pre_manifest = R.manifest()
    bk = backup(stamp)
    rep["stages"]["2_backup"] = {k: v for k, v in bk.items() if k != "fingerprints"}
    prod = db.connect(R.PROD)
    pre_fp = R.table_fingerprints(prod)
    check(pre_fp == bk["fingerprints"], "backup does not equal production")
    counts = lambda c: {t: c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in ("matches", "match_sources", "source_snapshots", "team_aliases", "sync_runs", "quarantine", "forecast_runs", "forecasts")}  # noqa: E731
    rep["stages"]["3_start_state"] = dict(
        counts=counts(prod), table_fingerprints=pre_fp, manifest=pre_manifest,
        equals_rehearsal_start_tables=pre_fp == rh["fingerprints"]["before"],
        equals_rehearsal_start_files={k: v == rh["manifest"]["before"].get(k) for k, v in pre_manifest.items()})
    check(rep["stages"]["3_start_state"]["equals_rehearsal_start_tables"], "production differs from the rehearsal's starting state: STOP and request approval again")
    check(all(v for k, v in rep["stages"]["3_start_state"]["equals_rehearsal_start_files"].items() if k != "data/footiq.sqlite"), "a protected file differs from the rehearsal manifest")      # the store itself is judged by its table fingerprints (its file bytes can change when SQLite checkpoints)

    snaps = R.load_snapshots()
    ident = R.verify_identities(prod, snaps)
    check(len(ident["aliases"]) == 5 and all(v["accepted"] for v in ident["verdicts"]), "identity verification failed")
    prod.close()

    bpath = C.ROOT / bk["path"]
    try:
        run = R.apply(R.PROD, snaps, ident["aliases"], kind=KIND)                       # the only write
        rep["stages"]["4_apply"] = run
        prod = db.connect(R.PROD)
        # actual changes vs the approved rehearsal diff, field by field
        bconn = db.connect(bpath, readonly=True)
        changes, kinds = R.diff_matches(bconn, prod)
        actual = {(c["record_id"], c["change"], c["field"], norm(c["before"]), norm(c["after"])) for c in changes}
        with open(R.REH / "import_diff_matches.csv", encoding="utf-8-sig", newline="") as fh:
            approved = {(r["record_id"], r["change"], r["field"], norm(r["before"]), norm(r["after"])) for r in csv.DictReader(fh)}
        rep["stages"]["5_diff"] = dict(actual_field_changes=len(actual), approved_field_changes=len(approved), identical=actual == approved, only_in_actual=sorted(actual - approved)[:10], only_in_approved=sorted(approved - actual)[:10], summary=kinds)
        check(actual == approved, "field-level changes differ from the approved rehearsal diff")
        post_fp = R.table_fingerprints(prod)
        same = {t: post_fp[t] == rh["fingerprints"]["after"][t] for t in post_fp if t != "sync_runs"}
        rep["stages"]["5_tables_equal_rehearsal"] = same
        check(all(same.values()), f"tables differ from the rehearsal result: {[t for t, v in same.items() if not v]}")
        # data checks
        changed_ids = {a[0] for a in actual}
        before_rows = {r["record_id"]: dict(r) for r in bconn.execute("SELECT * FROM matches")}
        after_rows = {r["record_id"]: dict(r) for r in prod.execute("SELECT * FROM matches")}
        recovered = [rid for rid in changed_ids if before_rows[rid]["status"] in ("scheduled", "awaiting_result") and after_rows[rid]["status"] == "completed"]
        overwritten_scores = [rid for rid, b in before_rows.items() if b["status"] in ("completed", "awarded") and b["home_goals_90"] is not None and (b["home_goals_90"], b["away_goals_90"], b["home_goals_final"], b["away_goals_final"]) != (after_rows[rid]["home_goals_90"], after_rows[rid]["away_goals_90"], after_rows[rid]["home_goals_final"], after_rows[rid]["away_goals_final"])]
        date_changes = [rid for rid, b in before_rows.items() if b["match_date"] != after_rows[rid]["match_date"]]
        held5 = [d for d in rh["results_held_for_date_decision"]]
        held_ok = all(after_rows[d["store_record_id"]]["status"] == before_rows[d["store_record_id"]]["status"] and after_rows[d["store_record_id"]]["home_goals_90"] is None for d in held5)
        new_q = [r[0].split(":")[0] for r in prod.execute("SELECT reason FROM quarantine WHERE run_id IN (SELECT run_id FROM sync_runs WHERE kind=?)", (KIND,))]
        dup = prod.execute("SELECT COUNT(*) FROM (SELECT competition_id, season, home_entity_id, away_entity_id, COUNT(*) n FROM matches WHERE competition_key IN ('EPL','LALIGA') AND season='2026-27' GROUP BY 1,2,3,4 HAVING n>1)").fetchone()[0]
        dup_all = prod.execute("SELECT COUNT(*) - COUNT(DISTINCT record_id) FROM matches").fetchone()[0]
        integ = [tuple(r) for r in prod.execute("PRAGMA integrity_check")]
        fk = [tuple(r) for r in prod.execute("PRAGMA foreign_key_check")]
        bm = {r["record_id"]: r for r in bconn.execute("SELECT * FROM matches WHERE home_name='AFC Bournemouth' AND away_name='Brentford FC' AND season='2026-27'")}
        villa = [tuple(r) for r in prod.execute("SELECT home_goals_90, away_goals_90 FROM matches WHERE competition_key='EPL' AND season='2026-27' AND home_name='Aston Villa FC' AND away_name='Nottingham Forest FC'")]
        bb = [tuple(r) for r in prod.execute("SELECT home_goals_90, away_goals_90 FROM matches WHERE competition_key='EPL' AND season='2026-27' AND home_name='AFC Bournemouth' AND away_name='Brentford FC'")]
        by_league = Counter(after_rows[r]["competition_key"] for r in recovered)
        rep["stages"]["6_checks"] = dict(
            match_rows_updated=len(changed_ids), results_recovered=len(recovered), recovered_by_league=dict(by_league), existing_scores_overwritten=len(overwritten_scores), fixture_dates_changed=len(date_changes),
            rows_added_or_removed=len(after_rows) - len(before_rows), held_five_la_liga_results_not_imported=held_ok, held_count=len(held5),
            new_quarantine_by_type=dict(Counter(new_q)), duplicate_pairings_epl_laliga=dup, duplicate_record_ids=dup_all, integrity_check=integ, foreign_key_violations=len(fk),
            bournemouth_brentford_stored_score=bb, villa_forest_stored_score=villa, counts_after=counts(prod),
            expected=dict(match_rows_updated=586, results_recovered=30, quarantine=dict(DATE_DIFFERENCE=55, CONFLICT=1, **{"CONTRADICTORY SOURCE RESULT": 1})))
        check(len(changed_ids) == 586 and len(recovered) == 30 and by_league == Counter(EPL=10, LALIGA=20), "counts differ from the approved rehearsal")
        check(not overwritten_scores and not date_changes and held_ok and len(after_rows) == len(before_rows), "an existing score/date was altered or a held result was imported")
        check(Counter(new_q) == Counter({"DATE_DIFFERENCE": 55, "CONFLICT": 1, "CONTRADICTORY SOURCE RESULT": 1}), "unexpected quarantine entries")
        check(integ == [("ok",)] and not dup and not dup_all, "integrity / duplicate check failed")
        check(bb == [(2, 2)] and villa == [(1, 2)], "a conflicted stored score changed")
        # annotate the run with the real time of the import (all other stamps carry the snapshot time so that the result is reproducible)
        prod.execute("UPDATE sync_runs SET detail=json_set(COALESCE(detail,'{}'), '$.import_performed_utc', ?, '$.backup', ?) WHERE kind=?", (datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), bk["path"], KIND))
        prod.commit()
        bconn.close()
        rep["stages"]["7_freshness"] = {k: v for k, v in {r["competition_key"]: dict(r) for r in views.freshness(prod)}.items() if k in R.LEAGUES}
        rep["stages"]["7_standings_equal_rehearsal"] = {k: R.standings(prod, k) == rh["standings"][k]["after"] for k in R.LEAGUES}
        rep["stages"]["7_eligibility_equal_rehearsal"] = {k: R.eligibility(prod, k) == rh["eligibility"][k]["after"] for k in R.LEAGUES}
        check(all(rep["stages"]["7_standings_equal_rehearsal"].values()) and all(rep["stages"]["7_eligibility_equal_rehearsal"].values()), "standings/eligibility differ from the rehearsal")
        rep["post_fingerprints"] = R.table_fingerprints(prod)
        prod.close()
        rep["outcome"] = "SUCCESS"
    except Exception as exc:  # noqa: BLE001
        rep["outcome"] = f"FAILED: {type(exc).__name__}: {exc}"
        try:
            prod.close()
        except Exception:  # noqa: BLE001
            pass
        if "apply" in str(rep["stages"].keys()) or "4_apply" in rep["stages"]:
            restore(bpath)
            c = db.connect(R.PROD)
            rep["rolled_back_to_backup"] = R.table_fingerprints(c) == pre_fp
            c.close()
    rep["manifest_after"] = R.manifest()
    rep["manifest_unchanged_except_store"] = {k: v == pre_manifest[k] for k, v in rep["manifest_after"].items() if k != "data/footiq.sqlite"}
    (OUT / "import_report.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    return rep


if __name__ == "__main__":
    try:
        r = main()
    except Stop as s:
        print("STOPPED before any change:", s)
        sys.exit(2)
    print(r["outcome"])
    print(json.dumps({k: v for k, v in r["stages"].get("6_checks", {}).items() if k != "expected"}, default=str)[:1800])
    print("manifest files unchanged:", all(r["manifest_unchanged_except_store"].values()))
    sys.exit(0 if r["outcome"] == "SUCCESS" else 1)
