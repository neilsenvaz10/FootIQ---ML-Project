"""Phase 4.8D FINAL supervised trial: THREE scheduler cycles of the full-season Bundesliga refresh against the real OpenLigaDB endpoint, on a PRIVATE COPY of production.

Real requests: at most 3 HTTPS GETs, all to https://api.openligadb.de/getmatchdata/bl1/2026, one per executed cycle, >= 60 s of real time apart, no retries, hard cap in the opener.
The six-hour spacing uses a MOCKED clock (the requests themselves are real). Failure injection, tampering and the lock test use the SAVED response with all sockets blocked.
Production is only read (consistent backup copy); the private configuration points at the copy and an isolated snapshot folder.
"""
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import stat
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
from store import baseline_hash, db, sync  # noqa: E402

OUT = ROOT / "data" / "supervised" / "phase4" / "p48d"
PROD = ROOT / "data" / "footiq.sqlite"
WORK = OUT / "trial3_work"
SNAPS = ROOT / "data" / "snapshots" / "p48d_trial2"
A1 = ROOT / "data" / "snapshots" / "p48c" / "openligadb" / "20261027T125704Z_p48c_bl1.json"
V3 = json.loads((ROOT / "data" / "supervised" / "phase4" / "p48c" / "db_baseline_v3.json").read_text(encoding="utf-8"))
URL = "https://api.openligadb.de/getmatchdata/bl1/2026"
HOST = "api.openligadb.de"
FMT = "%Y-%m-%dT%H:%M:%SZ"
MIN_GAP_S = 60
ALLOWED_CHANGE = {"sync_runs", "sync_errors", "source_snapshots", "source_state"}      # the only tables a cycle may touch when the provider's file has not changed


def rm(path):
    if Path(path).exists():
        shutil.rmtree(path, onerror=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))


def q(path, sql, *a):
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def valid_payload(body):
    data = json.loads(body)
    assert isinstance(data, list) and len(data) == 306, f"expected 306 matches, got {len(data) if isinstance(data, list) else type(data).__name__}"
    assert all(m.get("leagueShortcut") == "bl1" for m in data), "a match is not league bl1"
    per = {}
    for m in data:
        per[m["group"]["groupOrderID"]] = per.get(m["group"]["groupOrderID"], 0) + 1
    assert sorted(per) == list(range(1, 35)) and set(per.values()) == {9}, "matchdays are not 1..34 with 9 matches each"
    assert len({m["matchID"] for m in data}) == 306, "duplicate match ids"
    return data


class RealOpener:
    """The only way a request leaves this process. Exact URL, hard cap of 3, >= 60 s apart, payload validated BEFORE it is handed to the importer (an invalid one raises and nothing is ingested)."""

    def __init__(self):
        self.log, self.last = [], 0.0

    def __call__(self, url, headers):
        u = urlparse(url)
        assert u.scheme == "https" and u.hostname == HOST, f"blocked host {u.hostname}"
        assert url == URL, f"blocked URL (only {URL} is approved): {url}"
        assert len(self.log) < 3, "request cap (3) reached"
        gap = time.time() - self.last
        assert self.last == 0.0 or gap >= MIN_GAP_S, f"requests must be {MIN_GAP_S} s apart (only {gap:.0f} s)"
        self.last = time.time()
        entry = dict(n=len(self.log) + 1, url=url, requested_utc=datetime.now(timezone.utc).strftime(FMT))
        self.log.append(entry)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status, body, hdrs = r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            status, body, hdrs = e.code, e.read() if hasattr(e, "read") else b"", dict(e.headers or {})
        entry.update(status=status, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), answered_utc=datetime.now(timezone.utc).strftime(FMT))
        if status == 200:
            valid_payload(body)                                    # AssertionError (malformed/contradictory) stops the cycle before any ingestion
        return status, body, hdrs


class Replay:
    """The saved response, for failure injection. No network."""

    def __init__(self, payload):
        self.matches, self.mode, self.urls = json.loads(payload), "ok", []

    def __call__(self, url, headers):
        self.urls.append(url)
        assert url == URL
        if self.mode == "down":
            return 503, b"", {}
        if self.mode == "garbage":
            return 200, b"<html>not json</html>", {}
        return 200, json.dumps(self.matches).encode(), {}


def tables(path):
    return {k: v["sha256"] for k, v in baseline_hash.logical(path, 0)["tables"].items()}


def main():
    rm(WORK)
    WORK.mkdir(parents=True)
    rep = dict(kind="FINAL SUPERVISED TRIAL: 3 REAL full-season requests (mocked six-hour clock) + REPLAYED failure injection", started_utc=datetime.now(timezone.utc).strftime(FMT))
    # ---- safety before starting
    pre_phys, pre_log = baseline_hash.physical_sha256(PROD), baseline_hash.logical(PROD, V3["last_baseline_run_id"])
    rep["baseline_v3_check"] = dict(physical_equals=pre_phys == V3["physical_sha256"], logical_equals=pre_log["logical_sha256"] == V3["logical_sha256"], integrity=pre_log["integrity_check"],
                                    live_enabled_in_config=json.loads((ROOT / "config" / "sync.json").read_text(encoding="utf-8"))["live_enabled"])
    assert all(rep["baseline_v3_check"][k] for k in ("physical_equals", "logical_equals")) and rep["baseline_v3_check"]["live_enabled_in_config"] is False, "production is not in the expected state: stop"
    trial = WORK / "trial.sqlite"
    src = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(trial)
    src.backup(dst)
    dst.close()
    src.close()
    assert trial.resolve() != PROD.resolve() and WORK.resolve() in trial.resolve().parents
    sync.SNAPSHOT_DIR = SNAPS
    assert SNAPS.resolve() != (ROOT / "data" / "snapshots").resolve()
    SNAPS.mkdir(parents=True, exist_ok=True)
    rep["private_copy"] = dict(path=str(trial.relative_to(ROOT)), differs_from_production=True, logical_equals_baseline_v3=baseline_hash.logical(trial, 10)["logical_sha256"] == V3["logical_sha256"],
                               snapshot_dir=str(SNAPS.relative_to(ROOT)), manager_db_path_is_production=False, config_file_used_for_settings=False)
    a1 = {m["matchID"]: m for m in json.loads(A1.read_bytes())}
    start = datetime.now(timezone.utc).replace(microsecond=0)
    clock = Clock(start)
    real_now = sync.now_utc
    sync.now_utc = lambda: clock.t.strftime(FMT)
    cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, startup_check=True, startup_delay_seconds=0, max_retries=0)
    assert cfg.refresh_mode == "full_season"
    opener = RealOpener()
    callbacks = []
    mgr = sync.SyncManager(db_path=trial, cfg=cfg, opener=opener, on_change=lambda: callbacks.append(1), sleep=time.sleep, clock=clock)
    cycles, stop = [], None

    def snapshot_state():
        return dict(tables=tables(trial), matches={r["record_id"]: r for r in q(trial, "SELECT * FROM matches")}, runs=q(trial, "SELECT COUNT(*) n FROM sync_runs")[0]["n"], quarantine=q(trial, "SELECT COUNT(*) n FROM quarantine")[0]["n"])

    def run_cycle(n, manager, kind, due_clock):
        before = snapshot_state()
        n_req = len(opener.log)
        clock.t = due_clock
        res = manager.tick(kind)
        after = snapshot_state()
        st = {c["competition_key"]: c for c in sync.status(sqlite3.connect(f"file:{trial.as_posix()}?mode=ro", uri=True) if False else _ro(trial), cfg, clock.t)["competitions"]}["BUNDESLIGA"]
        skip = {"last_changed_utc", "change_count", "content_hash"}
        rows_changed = {rid: sorted(k for k in r if k not in skip and r[k] != before["matches"][rid][k]) for rid, r in after["matches"].items() if any(r[k] != before["matches"][rid][k] for k in r if k not in skip)}
        det = (res.get("details") or [{}])[0]
        e = opener.log[-1] if len(opener.log) > n_req else None
        snaps = sorted(p for p in (SNAPS / "openligadb").glob("*_bl1_2026_season.json"))
        return dict(cycle=n, kind=kind, mocked_clock=clock.t.strftime(FMT), outcome=res["outcome"], error=(det.get("error") if isinstance(det, dict) else None), real_request=e,
                    counts={k: det.get(k) for k in ("inserted", "updated", "unchanged", "confirmed", "quarantined", "requests")}, rows_changed=rows_changed,
                    tables_changed=sorted(k for k in after["tables"] if after["tables"][k] != before["tables"].get(k)), sync_runs_added=after["runs"] - before["runs"], quarantine_added=after["quarantine"] - before["quarantine"],
                    callbacks_total=len(callbacks), snapshot_file=snaps[-1].name if snaps else None, integrity=q(trial, "PRAGMA integrity_check")[0]["integrity_check"],
                    freshness=dict(state=st["state"], last_successful_external_check_utc=st["last_successful_external_check_utc"], last_attempted_sync_utc=st["last_attempted_sync_utc"], last_import_utc=st["last_successful_import_utc"],
                                   latest_verified_result=st["latest_result"], awaiting_result=st["awaiting_result"], reasons=st["state_reasons"]),
                    next_due=manager.next_due().strftime(FMT), production_unchanged=baseline_hash.physical_sha256(PROD) == pre_phys)

    def _ro(path):
        c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        return c

    try:
        # ---- cycle 1: due immediately
        rep["due_before_cycle_1"] = mgr.next_due().strftime(FMT)
        c1 = run_cycle(1, mgr, "startup_check", start)
        cycles.append(c1)
        if c1["outcome"] != "ok":
            stop = "cycle 1 did not end ok: stopped, no retry"
        # ---- cycle 2: only after the simulated six hours
        if not stop:
            clock.t = start + timedelta(hours=5, minutes=59)
            n0 = len(opener.log)
            early = mgr.tick("periodic_check")
            rep["cycle_2_early_check"] = dict(at_mocked="+5h59", outcome=early["outcome"], real_requests=len(opener.log) - n0)
            time.sleep(max(0, MIN_GAP_S + 2 - (time.time() - opener.last)))
            c2 = run_cycle(2, mgr, "periodic_check", start + timedelta(hours=6, minutes=1))
            cycles.append(c2)
            if c2["outcome"] != "ok":
                stop = "cycle 2 did not end ok: stopped, no retry"
        # ---- cycle 3: after a scheduler restart
        if not stop:
            restarted = sync.SyncManager(db_path=trial, cfg=cfg, opener=opener, on_change=lambda: callbacks.append(1), sleep=time.sleep, clock=clock)
            clock.t = start + timedelta(hours=6, minutes=30)
            n0 = len(opener.log)
            h = baseline_hash.physical_sha256(trial)
            r_early = restarted.tick("startup_check")
            rep["restart_check"] = dict(at_mocked="+6h30", outcome=r_early["outcome"], real_requests=len(opener.log) - n0, next_due=r_early.get("next_due"), private_copy_file_unchanged=h == baseline_hash.physical_sha256(trial))
            time.sleep(max(0, MIN_GAP_S + 2 - (time.time() - opener.last)))
            c3 = run_cycle(3, restarted, "periodic_check", start + timedelta(hours=12, minutes=2))
            cycles.append(c3)
            if c3["outcome"] != "ok":
                stop = "cycle 3 did not end ok: stopped, no retry"
    except AssertionError as exc:
        stop = f"guard stopped the trial: {exc}"
    rep["cycles"], rep["stopped"] = cycles, stop
    rep["real_requests_total"] = len(opener.log)
    rep["real_request_ledger"] = opener.log
    # ---- replayed part: no network
    orig_connect, orig_cc = socket.socket.connect, socket.create_connection

    def deny(*x, **k):
        raise RuntimeError("network blocked during the replayed part")
    socket.socket.connect, socket.create_connection = deny, deny
    try:
        if not stop:
            payload = (sorted((SNAPS / "openligadb").glob("*_bl1_2026_season.json"))[-1]).read_bytes()
            prov = Replay(payload)
            rmgr = sync.SyncManager(db_path=trial, cfg=cfg, opener=prov, sleep=lambda s: None, clock=clock)
            base_t = start + timedelta(hours=12, minutes=2)
            stable = {k: v for k, v in tables(trial).items() if k not in ("sync_runs", "sync_errors")}
            prov.mode = "down"
            clock.t = rmgr.next_due()
            f1 = rmgr.tick()
            d1 = rmgr.next_due()
            rep["replayed_provider_down"] = dict(outcome=f1["outcome"], single_attempt=len(prov.urls) == 1, data_tables_unchanged={k: v for k, v in tables(trial).items() if k not in ("sync_runs", "sync_errors")} == stable, wait_hours=round((d1 - clock.t).total_seconds() / 3600, 1))
            prov.mode = "garbage"
            clock.t = d1
            f2 = rmgr.tick()
            d2 = rmgr.next_due()
            rep["replayed_malformed"] = dict(outcome=f2["outcome"], data_tables_unchanged={k: v for k, v in tables(trial).items() if k not in ("sync_runs", "sync_errors")} == stable, wait_hours=round((d2 - clock.t).total_seconds() / 3600, 1))
            prov.mode = "ok"
            clock.t = d2
            f3 = rmgr.tick()
            rep["replayed_recovery"] = dict(outcome=f3["outcome"], changed=f3.get("changed"), next_due_after_hours=round((rmgr.next_due() - clock.t).total_seconds() / 3600, 1))
            # tampering: a changed score and a changed date must be quarantined, never applied
            stored = {r["record_id"]: (r["home_goals_final"], r["away_goals_final"], r["match_date"]) for r in q(trial, "SELECT record_id, home_goals_final, away_goals_final, match_date FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27'")}
            done = [m for m in prov.matches if m["matchIsFinished"]]
            for r_ in done[0]["matchResults"]:
                if r_["resultTypeID"] in (1, 2):
                    r_["pointsTeam1"] += 1
            moved = datetime.strptime(done[1]["matchDateTimeUTC"], FMT) + timedelta(days=1)
            done[1]["matchDateTimeUTC"], done[1]["matchDateTime"] = moved.strftime(FMT), moved.strftime("%Y-%m-%dT%H:%M:%S")
            qn = q(trial, "SELECT COUNT(*) n FROM quarantine")[0]["n"]
            clock.t = rmgr.next_due()
            t1 = rmgr.tick()
            rep["replayed_tamper"] = dict(outcome=t1["outcome"], new_quarantine_rows=q(trial, "SELECT COUNT(*) n FROM quarantine")[0]["n"] - qn, reasons=[r["reason"][:90] for r in q(trial, "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 2")],
                                          stored_scores_and_dates_unchanged=stored == {r["record_id"]: (r["home_goals_final"], r["away_goals_final"], r["match_date"]) for r in q(trial, "SELECT record_id, home_goals_final, away_goals_final, match_date FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27'")})
            # overlapping runs
            c = sqlite3.connect(trial)
            c.execute("INSERT INTO sync_runs(kind, source, started_utc, outcome) VALUES ('periodic_check','all approved',?, 'running')", ((clock.t - timedelta(minutes=5)).strftime(FMT),))
            c.commit()
            c.close()
            n = len(prov.urls)
            lock = rmgr.check_once("periodic_check")
            rep["replayed_overlap"] = dict(outcome=lock["outcome"], requests=len(prov.urls) - n)
            rep["replayed_requests_total"] = len(prov.urls)
    finally:
        socket.socket.connect, socket.create_connection = orig_connect, orig_cc
        sync.now_utc = real_now
    rep["private_copy_integrity"] = q(trial, "PRAGMA integrity_check")[0]["integrity_check"]
    # provider change versus the approved A1 response of 12:57 UTC
    last = [p for p in sorted((SNAPS / "openligadb").glob("*_bl1_2026_season.json"))]
    if last:
        cur = {m["matchID"]: m for m in json.loads(last[0].read_bytes())}
        sig = lambda m: (m["matchDateTimeUTC"], m["matchIsFinished"], tuple(sorted((r["resultTypeID"], r["pointsTeam1"], r["pointsTeam2"]) for r in m["matchResults"])))  # noqa: E731
        rep["provider_change_since_A1"] = dict(first_response_sha256=hashlib.sha256(last[0].read_bytes()).hexdigest(), a1_sha256=hashlib.sha256(A1.read_bytes()).hexdigest(), matches_changed=[i for i in cur if sig(cur[i]) != sig(a1[i])])
    post_phys = baseline_hash.physical_sha256(PROD)
    post_log = baseline_hash.logical(PROD, V3["last_baseline_run_id"])
    rep["production_after"] = dict(physical_equals_v3=post_phys == V3["physical_sha256"], logical_equals_v3=post_log["logical_sha256"] == V3["logical_sha256"], integrity=post_log["integrity_check"],
                                   live_enabled_in_config=json.loads((ROOT / "config" / "sync.json").read_text(encoding="utf-8"))["live_enabled"])
    (OUT / "real_network_trial3.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    rm(WORK)
    print(json.dumps(rep, indent=1, default=str, ensure_ascii=False)[:9000])


if __name__ == "__main__":
    main()
