"""Phase 4.8D Stage 1: bounded SCHEDULER TRIAL on a PRIVATE COPY. *** REPLAYED-SNAPSHOT TRIAL: NO REAL NETWORK REQUEST IS MADE. ***

The OpenLigaDB answers are served from the approved A1 snapshot (20261027T125704Z_p48c_bl1.json) by an in-process opener, and every socket connection is blocked while the
trial runs, so a request that escaped the opener would fail loudly. The real production scheduler stays disabled (config/sync.json is never changed or read for the trial's settings);
the trial uses its own SyncConfig, a private database (the production file as it was BEFORE the approved imports, from the verified backup restore), an isolated snapshot/ledger folder and a mocked clock.
"""
import hashlib
import os
import stat
import json
import shutil
import socket
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
from store import baseline_hash, db, sync  # noqa: E402

OUT = ROOT / "data" / "supervised" / "phase4" / "p48d"
A1 = ROOT / "data" / "snapshots" / "p48c" / "openligadb" / "20261027T125704Z_p48c_bl1.json"
SOURCE_COPY = OUT / "restore_test_bundesliga.sqlite"       # the verified restore of the pre-import backup (production before the approved imports)
WORK = OUT / "trial_work"
T0 = datetime(2026, 10, 27, 15, 0, 0, tzinfo=timezone.utc)
FMT = "%Y-%m-%dT%H:%M:%SZ"


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class Replay:
    """An in-process stand-in for api.openligadb.de that answers from the A1 payload. `mode` selects the scenario."""

    def __init__(self):
        self.matches = json.loads(A1.read_bytes())
        self.log, self.mode, self.change_bump = [], "normal", 0

    def group(self, g):
        return [m for m in self.matches if m["group"]["groupOrderID"] == g]

    def __call__(self, url, headers):
        self.log.append(url)
        assert url.startswith("https://api.openligadb.de/"), f"unexpected host: {url}"
        assert "FootIQ" in headers.get("User-Agent", "") or "openligaDB" in headers.get("User-Agent", "") or "OpenLigaDB" in headers.get("User-Agent", "")
        path = url.split("api.openligadb.de")[1]
        if self.mode == "down":
            return 503, b"", {}
        if path == "/getcurrentgroup/bl1":
            return 200, json.dumps({"groupName": "7. Spieltag", "groupOrderID": 7, "groupID": 1}).encode(), {}
        if path.startswith("/getlastchangedate/bl1/2026/"):
            g = int(path.rsplit("/", 1)[1])
            last = max(m["lastUpdateDateTime"] for m in self.group(g))
            return 200, json.dumps(f"{last}+{self.change_bump}" if self.change_bump else last).encode(), {}
        if path.startswith("/getmatchdata/bl1/2026/"):
            g = int(path.rsplit("/", 1)[1])
            ms = json.loads(json.dumps(self.group(g)))
            if self.mode == "tamper":                                     # a provider that disagrees with what we hold
                done = [m for m in ms if m["matchIsFinished"]]
                for r in done[0]["matchResults"]:
                    if r["resultTypeID"] in (1, 2):                         # change a stored final score
                        r["pointsTeam1"] += 1
                if len(done) > 1:                                          # and move another played match by a day
                    d = datetime.strptime(done[1]["matchDateTimeUTC"], FMT) + timedelta(days=1)
                    done[1]["matchDateTimeUTC"] = d.strftime(FMT)
                    done[1]["matchDateTime"] = d.strftime("%Y-%m-%dT%H:%M:%S")
            return 200, json.dumps(ms).encode(), {}
        raise AssertionError(f"unapproved URL requested: {url}")


def rmtree(path):
    def fix(func, p, exc):                                        # the saved snapshots are read-only files
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=fix) if Path(path).exists() else None


def sha(p):
    return baseline_hash.physical_sha256(p)


def q(path, sql, *a):
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def snapshot_tables(path):
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    out = {}
    for (t,) in c.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'").fetchall():
        out[t] = hashlib.sha256(repr(sorted(tuple(map(repr, r)) for r in c.execute(f'select * from "{t}"'))).encode()).hexdigest()[:12]
    c.close()
    return out


def main():
    rmtree(WORK)
    WORK.mkdir(parents=True)
    trial = WORK / "trial.sqlite"
    for e in ("", "-wal", "-shm"):
        Path(str(trial) + e).unlink(missing_ok=True)
    shutil.copyfile(SOURCE_COPY, trial)
    c = sqlite3.connect(trial)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()
    sync.SNAPSHOT_DIR = WORK / "snapshots"                              # isolated snapshot, state and ledger files
    real_now = sync.now_utc
    clock = Clock(T0)
    sync.now_utc = lambda: clock.t.strftime(FMT)
    rep = dict(kind="REPLAYED-SNAPSHOT TRIAL (no real network request)", network_blocked=True, started_utc=datetime.now(timezone.utc).strftime(FMT), clock_start=T0.strftime(FMT),
               production_sha256_before=sha(ROOT / "data" / "footiq.sqlite"), snapshot=dict(file=A1.name, sha256=sha(A1)))
    blocked = []

    def deny(*a, **k):
        blocked.append(str(a)[:80])
        raise RuntimeError("network access is blocked during the replayed-snapshot trial")
    orig_connect, orig_cc = socket.socket.connect, socket.create_connection
    socket.socket.connect, socket.create_connection = deny, deny
    try:
        server = Replay()
        callbacks = []
        # 1. disabled scheduler: no change at all
        before = dict(file=sha(trial), tables=snapshot_tables(trial))
        off = sync.SyncManager(db_path=trial, cfg=sync.SyncConfig(live_enabled=False, startup_delay_seconds=0), opener=server, clock=clock)
        off.start()
        res_off = [off.check_once("startup_check"), off.tick()]
        off.stop()
        rep["1_disabled_scheduler"] = dict(thread_started=off._thread is not None, results=res_off, file_unchanged=before["file"] == sha(trial), tables_unchanged=before["tables"] == snapshot_tables(trial), requests=len(server.log))
        # 2. one supervised cycle (replayed)
        cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, startup_check=True, startup_delay_seconds=0)
        mgr = sync.SyncManager(db_path=trial, cfg=cfg, opener=server, on_change=lambda: callbacks.append(clock.t.strftime(FMT)), sleep=lambda s: None, clock=clock)
        rep["2_due_before_first_cycle"] = mgr.next_due().strftime(FMT)
        pre_rows = {r["record_id"]: r for r in q(trial, "SELECT * FROM matches")}
        r1 = mgr.tick("startup_check")
        post_rows = {r["record_id"]: r for r in q(trial, "SELECT * FROM matches")}
        changed = {rid: sorted(k for k in post_rows[rid] if k not in ("last_changed_utc", "change_count", "content_hash") and post_rows[rid][k] != pre_rows[rid][k]) for rid in post_rows if any(post_rows[rid][k] != pre_rows[rid][k] for k in post_rows[rid] if k not in ("last_changed_utc", "change_count", "content_hash"))}
        rep["2_supervised_cycle"] = dict(outcome=r1["outcome"], changed=r1.get("changed"), requests_replayed=len(server.log), urls=[u.replace("https://api.openligadb.de", "") for u in server.log], on_change_callbacks=len(callbacks),
                                         rows_changed={rid: [(post_rows[rid]["home_name"], post_rows[rid]["away_name"], post_rows[rid]["home_goals_final"], post_rows[rid]["away_goals_final"])] for rid in changed}, fields_changed=sorted({f for v in changed.values() for f in v}),
                                         sync_runs=q(trial, "SELECT run_id, kind, competition_key, outcome, requests, inserted, updated, unchanged, quarantined FROM sync_runs WHERE run_id>8"),
                                         links_upgraded=q(trial, "SELECT source_ref, role, snapshot_id FROM match_sources WHERE source='openligadb' AND source_ref IN ('83213','83214')"),
                                         next_due=mgr.next_due().strftime(FMT))
        # 3. due-time logic
        n = len(server.log)
        clock.t = T0 + timedelta(hours=5, minutes=59)
        d1 = mgr.tick()
        clock.t = T0 + timedelta(hours=6, minutes=1)
        d2 = mgr.tick()
        rep["3_due_logic"] = dict(at_5h59=d1["outcome"], at_6h01=d2["outcome"], requests_in_the_second_cycle=len(server.log) - n, second_cycle_changed=d2.get("changed"), idempotent=d2.get("changed") == 0)
        # 4. restart inside the interval
        clock.t = T0 + timedelta(hours=6, minutes=30)
        h = sha(trial)
        restarted = sync.SyncManager(db_path=trial, cfg=cfg, opener=server, sleep=lambda s: None, clock=clock)
        n = len(server.log)
        r4 = restarted.tick("startup_check")
        rep["4_restart"] = dict(outcome=r4["outcome"], next_due=r4.get("next_due"), requests=len(server.log) - n, file_unchanged=h == sha(trial))
        # 5. concurrency lock
        clock.t = T0 + timedelta(hours=12, minutes=1)
        c = sqlite3.connect(trial)
        c.execute("INSERT INTO sync_runs(kind, source, started_utc, outcome) VALUES ('periodic_check','all approved',?, 'running')", ((clock.t - timedelta(minutes=10)).strftime(FMT),))
        c.commit()
        c.close()
        n = len(server.log)
        r5a = mgr.check_once("periodic_check")
        clock.t += timedelta(minutes=30)
        r5b = mgr.check_once("periodic_check")
        rep["5_lock"] = dict(young_running_row=r5a["outcome"], requests_while_locked=0 if len(server.log) == n or r5a["outcome"] != "ok" else None, after_30_min=r5b["outcome"], abandoned_row=q(trial, "SELECT run_id, outcome FROM sync_runs WHERE outcome='abandoned'"))
        # 6. failure and back-off
        server.mode = "down"
        clock.t = mgr.next_due()
        r6a = mgr.tick()
        due1 = mgr.next_due()
        clock.t = due1
        r6b = mgr.tick()
        due2 = mgr.next_due()
        server.mode = "normal"
        clock.t = due2
        r6c = mgr.tick()
        rep["6_failure_backoff"] = dict(first_failure=r6a["outcome"], wait_after_first_hours=round((due1 - (due1 - timedelta(hours=12))).total_seconds() / 3600), next_due_after_first=due1.strftime(FMT), second_failure=r6b["outcome"],
                                        next_due_after_second=due2.strftime(FMT), recovered=r6c["outcome"], next_due_after_recovery=mgr.next_due().strftime(FMT), data_changed_by_failures=0,
                                        sync_errors=q(trial, "SELECT run_id, source, error FROM sync_errors"))
        # 7. quarantine handling: a provider that contradicts what is stored
        server.mode, server.change_bump = "tamper", 1
        stored_before = {r["record_id"]: (r["home_goals_final"], r["away_goals_final"], r["match_date"]) for r in q(trial, "SELECT record_id, home_goals_final, away_goals_final, match_date FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27'")}
        clock.t = mgr.next_due()
        qn = q(trial, "SELECT COUNT(*) n FROM quarantine")[0]["n"]
        r7 = mgr.tick()
        stored_after = {r["record_id"]: (r["home_goals_final"], r["away_goals_final"], r["match_date"]) for r in q(trial, "SELECT record_id, home_goals_final, away_goals_final, match_date FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27'")}
        rep["7_quarantine"] = dict(outcome=r7["outcome"], new_quarantine_rows=q(trial, "SELECT COUNT(*) n FROM quarantine")[0]["n"] - qn, reasons=[r["reason"][:110] for r in q(trial, "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 4")],
                                   stored_scores_and_dates_unchanged=stored_before == stored_after)
        # 8. logging evidence
        ledger = (sync.SNAPSHOT_DIR / "request_ledger.jsonl")
        rep["8_logging"] = dict(sync_runs=q(trial, "SELECT run_id, kind, source, competition_key, outcome, requests, inserted, updated, quarantined FROM sync_runs WHERE run_id>8 ORDER BY run_id"),
                                ledger_lines=len(ledger.read_text(encoding="utf-8").splitlines()) if ledger.exists() else 0, snapshot_files=len(list((sync.SNAPSHOT_DIR / "openligadb").glob("*.json"))) if (sync.SNAPSHOT_DIR / "openligadb").exists() else 0,
                                real_network_attempts_blocked=len(blocked), total_replayed_requests=len(server.log))
    finally:
        socket.socket.connect, socket.create_connection = orig_connect, orig_cc
        sync.now_utc = real_now
    rep["integrity"] = dict(integrity_check=q(trial, "PRAGMA integrity_check")[0]["integrity_check"], matches=q(trial, "SELECT COUNT(*) n FROM matches")[0]["n"])
    rep["production_sha256_after"] = sha(ROOT / "data" / "footiq.sqlite")
    rep["production_untouched_by_trial"] = rep["production_sha256_before"] == rep["production_sha256_after"]
    rep["config_sync_json_live_enabled"] = json.loads((ROOT / "config" / "sync.json").read_text(encoding="utf-8"))["live_enabled"]
    (OUT / "scheduler_trial.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    rmtree(WORK)
    print(json.dumps(rep, indent=1, default=str, ensure_ascii=False)[:9000])


if __name__ == "__main__":
    main()
