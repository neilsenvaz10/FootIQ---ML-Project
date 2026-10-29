"""Phase 4.8D: ONE supervised production cycle of the Bundesliga full-season refresh. A one-shot tool, not a scheduler: it builds an in-process SyncManager, calls tick() once, and exits.

    python app/store/run_one_cycle_p48d.py              preconditions, SQLite-safe backup, restore test: production is NOT touched
    python app/store/run_one_cycle_p48d.py --execute    ... then exactly one scheduled cycle against https://api.openligadb.de/getmatchdata/bl1/2026

The configuration file stays as it is (live_enabled false): live checking is enabled only inside this process, so nothing can keep running afterwards. The request guard allows the one
approved URL once (no retry); the response is validated before import; date protection, quarantine and provenance are the normal ones. The baseline is NOT approved by this tool.
"""
import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import import_p48d_stage1 as I  # noqa: E402  (its SQLite-safe backup, restore test and process/lock checks are reused)
from store import baseline_hash, baseline_monitor, db, sync  # noqa: E402

PROD = C.ROOT / "data" / "footiq.sqlite"
OUT = C.ROOT / "data" / "supervised" / "phase4" / "p48d"
URL = "https://api.openligadb.de/getmatchdata/bl1/2026"
V3 = json.loads((C.ROOT / "data" / "supervised" / "phase4" / "p48c" / "db_baseline_v3.json").read_text(encoding="utf-8"))
UNCHANGED_TABLES = ("competitions", "teams", "team_aliases", "forecasts", "forecast_runs", "simulation_runs", "meta", "quarantine", "match_sources", "matches")


class Abort(Exception):
    pass


def guard(real):
    calls = []

    def guarded(url, headers):
        if url != URL or calls:
            raise Abort(f"request guard: only {URL} once is approved (asked for {url}, call number {len(calls) + 1})")
        calls.append(url)
        return real(url, headers)
    guarded.calls = calls
    return guarded


def preconditions() -> dict:
    info = dict(path=str(PROD), bytes=PROD.stat().st_size)
    info["physical_sha256"] = baseline_hash.physical_sha256(PROD)
    lg = baseline_hash.logical(PROD, V3["last_baseline_run_id"])
    info.update(logical_sha256=lg["logical_sha256"], integrity_check=lg["integrity_check"], physical_equals_v3=info["physical_sha256"] == V3["physical_sha256"], logical_equals_v3=lg["logical_sha256"] == V3["logical_sha256"])
    cfg_file = sync.SyncConfig.load()
    info["config_live_enabled"] = cfg_file.live_enabled
    info["enabled_competitions"] = cfg_file.approved_competitions()
    info["git_staged"] = [x for x in I.git("diff", "--cached", "--name-only").splitlines() if x]
    info["git_head"] = I.git("log", "--oneline", "-1")
    info["application_processes"] = I.processes_using_the_store()
    try:
        c = sqlite3.connect(PROD, timeout=0)
        c.execute("BEGIN EXCLUSIVE")
        c.rollback()
        c.close()
        info["exclusive_lock_available"] = True
    except sqlite3.OperationalError as exc:
        info["exclusive_lock_available"] = False
        info["lock_error"] = str(exc)
    c = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
    info["forecasts"], info["forecast_runs"] = c.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0], c.execute("SELECT COUNT(*) FROM forecast_runs").fetchone()[0]
    c.close()
    integ = json.loads(subprocess.run([sys.executable, "-B", "-X", "utf8", str(C.ROOT / "data" / "supervised" / "phase4" / "phase4_integrity.py"), "check"], capture_output=True, text=True, cwd=C.ROOT).stdout)
    info["frozen_files_changed_vs_recorded"] = integ["frozen_files_in_hashes_before_json"]["changed"]            # only config/sync.json (your approved 6-hour interval) is expected here
    info["prospective_evaluation_files_in_manifest_changed"] = [k for k in integ["protected_manifest"]["differences_from_start"] if "prospective" in k]
    bad = [m for m, ok in (("physical hash is not baseline v3", info["physical_equals_v3"]), ("logical hash is not baseline v3", info["logical_equals_v3"]), ("integrity_check not ok", info["integrity_check"] == "ok"),
                           ("config live_enabled is not false before the run", info["config_live_enabled"] is False), ("enabled competitions are not exactly Bundesliga", info["enabled_competitions"] == ["BUNDESLIGA"]),
                           ("something is staged in Git", not info["git_staged"]), ("HEAD changed", info["git_head"].startswith(I.HEAD)), ("an application/test process is running", not info["application_processes"]),
                           ("no exclusive lock: a writer is active", info["exclusive_lock_available"]), ("saved forecasts exist", info["forecasts"] == 0 and info["forecast_runs"] == 0),
                           ("a frozen model/config file differs from its record", info["frozen_files_changed_vs_recorded"] == ["config/sync.json"]), ("a prospective-evaluation file differs", not info["prospective_evaluation_files_in_manifest_changed"])) if not ok]
    info["failed"] = bad
    if bad:
        raise Abort("; ".join(bad))
    return info


def table_counts(path):
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    try:
        return {t: c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()}
    finally:
        c.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rep = dict(started_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), execute=a.execute)
    try:
        rep["preconditions"] = preconditions()
        rep["backup"] = I.backup("activation", dict(logical=V3["logical_sha256"], last_run=V3["last_baseline_run_id"]))
        if not a.execute:
            rep["result"] = "preconditions, backup and restore test passed; production NOT touched"
        else:
            restored = Path(rep["backup"]["restored_path"])
            before_rows = {r["record_id"]: dict(r) for r in db.connect(restored, readonly=True).execute("SELECT * FROM matches")}
            before_counts = table_counts(restored)
            cfg = sync.SyncConfig(live_enabled=True, startup_check=True, startup_delay_seconds=0, periodic_minutes=360, max_retries=0, refresh_mode="full_season",
                                  sources={"openligadb": {"enabled": True, "competitions": ["BUNDESLIGA"]}})
            g = {}

            def make_guard(real):
                g["opener"] = guard(real)
                return g["opener"]
            mgr = sync.SyncManager(db_path=PROD, cfg=cfg, request_guard=make_guard, sleep=lambda s: None)
            rep["config_used_in_process"] = dict(live_enabled=True, periodic_minutes=360, max_retries=0, refresh_mode="full_season", competitions=["BUNDESLIGA"], request_cap=1, url=URL,
                                                 note="config/sync.json was NOT edited: it stays live_enabled=false, so nothing outlives this process")
            rep["due_before"] = mgr.next_due().strftime("%Y-%m-%dT%H:%M:%SZ")
            res = mgr.tick("startup_check")                                # <<< the one production cycle (one real request)
            rep["cycle"] = dict(outcome=res["outcome"], changed=res.get("changed"), details=res.get("details"), requests_made=len(g["opener"].calls) if g.get("opener") else 0)
            # ---- verification against the backup
            conn = db.connect(PROD, readonly=True)
            after_rows = {r["record_id"]: dict(r) for r in conn.execute("SELECT * FROM matches")}
            skip = {"last_changed_utc", "change_count", "content_hash"}
            changed = {rid: sorted(k for k in r if k not in skip and r[k] != before_rows[rid][k]) for rid, r in after_rows.items() if any(r[k] != before_rows[rid][k] for k in r if k not in skip)}
            run = [dict(r) for r in conn.execute("SELECT run_id, kind, competition_key, outcome, requests, inserted, updated, unchanged, quarantined, detail FROM sync_runs WHERE run_id>10 ORDER BY run_id")]
            conn.close()
            after_counts = table_counts(PROD)
            rep["verification"] = dict(matches_changed=changed, match_rows_before_after=[len(before_rows), len(after_rows)], table_row_counts_changed={t: [before_counts.get(t), after_counts[t]] for t in after_counts if before_counts.get(t) != after_counts[t]},
                                       sync_runs=run, integrity_check=baseline_hash.logical(PROD, 10)["integrity_check"],
                                       unexpected=[t for t in UNCHANGED_TABLES if before_counts.get(t) != after_counts[t] and t not in ("matches", "match_sources", "quarantine")] + ([f"{len(changed)} match row(s) changed"] if changed else []))
            snaps = sorted(p for p in (C.ROOT / "data" / "snapshots" / "openligadb").glob("*_bl1_2026_season.json"))
            last = snaps[-1]
            meta = json.loads(Path(str(last) + ".meta.json").read_text(encoding="utf-8"))
            rep["snapshot"] = dict(file=last.name, sha256=meta["sha256"], bytes=meta["bytes"], origin=meta.get("origin"), url=meta.get("url"), status=meta.get("status"), saved_utc=meta.get("saved_utc"), sha256_matches_file=baseline_hash.physical_sha256(last) == meta["sha256"])
            rep["ledger_tail"] = (C.ROOT / "data" / "snapshots" / "request_ledger.jsonl").read_text(encoding="utf-8").splitlines()[-2:]
            cp = baseline_monitor.checkpoints()[-1]
            rep["baseline_monitor"] = {k: v for k, v in baseline_monitor.report(PROD, cp).items() if k in ("verdict", "reasons", "changed_tables", "approvable", "scope_changes", "explained_by")}
            rep["hashes_after"] = dict(physical_sha256=baseline_hash.physical_sha256(PROD), logical_sha256_v3_cutoff=baseline_hash.logical(PROD, 10)["logical_sha256"], baseline_v3_physical=V3["physical_sha256"], baseline_v3_logical=V3["logical_sha256"])
            rep["baseline_approved"] = False
            rep["result"] = "CYCLE DONE" if res["outcome"] == "ok" and not rep["verification"]["unexpected"] else "CYCLE DONE WITH PROBLEMS: stop and review"
    except Abort as exc:
        rep["result"] = f"ABORTED: {exc}"
    rep["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    name = "activation_cycle1.json" if a.execute else "activation_precheck.json"
    (OUT / name).write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=1, default=str, ensure_ascii=False)[:7000])
    return 0 if str(rep["result"]).startswith(("CYCLE DONE", "preconditions")) and "PROBLEMS" not in rep["result"] else 1


if __name__ == "__main__":
    sys.exit(main())
