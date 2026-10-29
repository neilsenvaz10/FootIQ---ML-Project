"""Phase 4.8D Stage 2: supervised REAL-NETWORK scheduler trial, Bundesliga only, on a PRIVATE COPY of production. Production is never opened for writing; the production scheduler stays off.

    python real_network_trial.py --urls <approved URL> [<approved URL> ...]      the URLs are the ONLY ones the opener will fetch; the request cap equals their number

Stage A: one real GET to the previously approved endpoint https://api.openligadb.de/getmatchdata/bl1/2026 (the scheduler's first-fetch path).
Everything after that (restart, duplicate import, failure, quarantine, back-off) is a REPLAY of the saved response with the network blocked and is labelled as such.
"""
import argparse
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from store import baseline_hash, db, sync  # noqa: E402
import scheduler_trial as ST  # noqa: E402  (its Replay class serves a saved Bundesliga payload; importing it runs nothing)

OUT = ROOT / "data" / "supervised" / "phase4" / "p48d"
PROD = ROOT / "data" / "footiq.sqlite"
WORK = OUT / "real_trial_work"
SNAPS = ROOT / "data" / "snapshots" / "p48d_trial"
HOST = "api.openligadb.de"
FMT = "%Y-%m-%dT%H:%M:%SZ"
CUTOFF = 10                                      # baseline v3 cut-off run id


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


class RealOpener:
    """The only way a request leaves this process: HTTPS GET, exact allow-listed URLs, hard cap, every call logged with status, size and hash."""

    def __init__(self, urls, replay=None):
        self.allowed, self.log, self.replay, self.halted = set(urls), [], dict(replay or {}), None      # replay: URL -> bytes served from a SAVED response, never from the network (logged as such)

    def real_requests(self):
        return [e for e in self.log if not e.get("replayed")]

    def __call__(self, url, headers):
        u = urlparse(url)
        assert u.scheme == "https" and u.hostname == HOST, f"blocked host {u.hostname}"
        if url in self.replay:
            body = self.replay[url]
            self.log.append(dict(url=url, replayed=True, status=200, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), served_from="saved snapshot (no network)"))
            return 200, body, {}
        assert url in self.allowed, f"blocked URL (not on the approved list): {url}"
        assert not self.halted, f"STOPPED before this request: {self.halted}"
        assert len(self.real_requests()) < len(self.allowed), "request cap reached"
        entry = dict(url=url, requested_utc=datetime.now(timezone.utc).strftime(FMT))
        self.log.append(entry)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status, body, hdrs = r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            status, body, hdrs = e.code, e.read() if hasattr(e, "read") else b"", dict(e.headers or {})
        entry.update(status=status, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), answered_utc=datetime.now(timezone.utc).strftime(FMT))
        self.halted = self.check(url, status, body)                  # stop on a malformed or contradictory answer, and when the current matchday is not 7
        if self.halted:
            entry["halt"] = self.halted
        return status, body, hdrs

    @staticmethod
    def check(url, status, body):
        if status != 200:
            return f"HTTP {status}"
        try:
            data = json.loads(body)
        except ValueError:
            return "malformed JSON"
        if url.endswith("/getcurrentgroup/bl1"):
            return None if isinstance(data, dict) and data.get("groupOrderID") == 7 else f"current matchday is {data.get('groupOrderID') if isinstance(data, dict) else '?'}, not 7"
        if "/getlastchangedate/" in url:
            return None if isinstance(data, str) and data else "last-change date is not a non-empty string"
        if url.endswith("/getmatchdata/bl1/2026/7"):
            ok = isinstance(data, list) and len(data) == 9 and all(m.get("group", {}).get("groupOrderID") == 7 and m.get("leagueShortcut") == "bl1" for m in data) and len({m["matchID"] for m in data}) == 9
            return None if ok else "matchday 7 payload is not 9 distinct bl1 matches of group 7"
        return None


def data_tables(path):
    t = baseline_hash.logical(path, CUTOFF)["tables"]
    return {k: v["sha256"] for k, v in t.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", nargs="+", required=True)
    ap.add_argument("--stage", default="A", choices=["A", "B"])
    ap.add_argument("--replay-group", type=int, default=None, help="Stage B: answer getmatchdata/bl1/2026/<group> from the saved A1 snapshot instead of the network")
    a = ap.parse_args()
    rm(WORK)
    WORK.mkdir(parents=True)
    trial = WORK / "trial.sqlite"
    src = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(trial)
    src.backup(dst)                                                  # consistent private copy; production is only read
    if a.stage == "A":
        dst.execute("DELETE FROM source_state WHERE source='openligadb'")  # private copy only: forces the first-fetch path (one full-season request) instead of the polling path
    dst.commit()
    dst.close()
    src.close()
    prod_before = baseline_hash.physical_sha256(PROD)
    sync.SNAPSHOT_DIR = SNAPS
    SNAPS.mkdir(parents=True, exist_ok=True)
    start = datetime.now(timezone.utc).replace(microsecond=0)
    clock = ST.Clock(start)
    real_now = sync.now_utc
    sync.now_utc = lambda: clock.t.strftime(FMT)
    rep = dict(kind="STAGE A: REAL-NETWORK cycle (first-fetch path) + REPLAYED follow-ups", started_utc=start.strftime(FMT), approved_urls=a.urls, request_cap=len(a.urls), stage=a.stage, production_sha256_before=prod_before,
               private_copy_note="source_state row deleted in the private copy only, so the scheduler uses the first-fetch endpoint")
    before_t, before_rows = data_tables(trial), {r["record_id"]: r for r in q(trial, "SELECT * FROM matches")}
    before_links = {(r["source"], r["source_ref"]): r for r in q(trial, "SELECT * FROM match_sources")}
    before_q = q(trial, "SELECT COUNT(*) n FROM quarantine")[0]["n"]
    replay = {}
    if a.replay_group:
        a1 = json.loads((ROOT / "data" / "snapshots" / "p48c" / "openligadb" / "20261027T125704Z_p48c_bl1.json").read_bytes())
        replay[f"https://{HOST}/getmatchdata/bl1/2026/{a.replay_group}"] = json.dumps([m for m in a1 if m["group"]["groupOrderID"] == a.replay_group]).encode()
    opener = RealOpener(a.urls, replay)
    cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, startup_check=True, startup_delay_seconds=0, max_retries=0)
    callbacks = []
    mgr = sync.SyncManager(db_path=trial, cfg=cfg, opener=opener, on_change=lambda: callbacks.append(1), clock=clock)
    rep["due_before"] = mgr.next_due().strftime(FMT)
    try:
        r1 = mgr.tick("startup_check")                               # <<< the real request happens here
    finally:
        pass
    rep["real_network"] = dict(outcome=r1["outcome"], changed=r1.get("changed"), details=r1.get("details"), ledger=opener.log, real_requests=len(opener.real_requests()), replayed_requests=len(opener.log) - len(opener.real_requests()), change_callbacks=len(callbacks))
    after_rows = {r["record_id"]: r for r in q(trial, "SELECT * FROM matches")}
    skip = {"last_changed_utc", "change_count", "content_hash"}
    changed = {rid: {k: (before_rows[rid][k], v) for k, v in row.items() if k not in skip and before_rows[rid][k] != v} for rid, row in after_rows.items() if any(before_rows[rid][k] != v for k, v in row.items() if k not in skip)}
    after_links = {(r["source"], r["source_ref"]): r for r in q(trial, "SELECT * FROM match_sources")}
    snap = sorted((SNAPS / "openligadb").glob("*.json"))
    snap = [p for p in snap if not p.name.endswith(".meta.json")]
    last = snap[-1] if snap else None
    rep["reconciliation"] = dict(rows_changed=len(changed), changes={rid: {k: [str(x) for x in v] for k, v in f.items()} for rid, f in list(changed.items())[:12]}, matches_before_after=[len(before_rows), len(after_rows)],
                                 quarantine_added=q(trial, "SELECT COUNT(*) n FROM quarantine")[0]["n"] - before_q,
                                 tables_changed=sorted(k for k, v in data_tables(trial).items() if v != before_t.get(k)),
                                 links_changed=[f"{k[0]}:{k[1]}" for k in after_links if before_links.get(k) != after_links[k]], links_added=len(set(after_links) - set(before_links)),
                                 snapshot=dict(file=last.name if last else None, sha256=hashlib.sha256(last.read_bytes()).hexdigest() if last else None, bytes=last.stat().st_size if last else None),
                                 sync_runs=q(trial, "SELECT run_id, kind, competition_key, outcome, requests, inserted, updated, unchanged, quarantined, latest_result_date FROM sync_runs WHERE run_id>10"),
                                 source_state=q(trial, "SELECT scope, state_json FROM source_state"))
    imported = ["83213", "83214", "85426", "85428", "85429", "85432"]
    rep["provenance_of_the_imported_results"] = [dict(source_ref=r["source_ref"], role=r["role"], snapshot=r["snapshot_id"]) for r in q(trial, f"SELECT source_ref, role, snapshot_id FROM match_sources WHERE source='openligadb' AND source_ref IN ({','.join('?' * 6)})", *imported)]
    rep["next_due_after_cycle"] = mgr.next_due().strftime(FMT)
    # ---- replayed follow-ups: the network is blocked from here on
    orig_connect, orig_cc = socket.socket.connect, socket.create_connection

    def deny(*x, **k):
        raise RuntimeError("network blocked during the replayed part of the trial")
    socket.socket.connect, socket.create_connection = deny, deny
    try:
        saved_payload = (ROOT / "data" / "snapshots" / "p48c" / "openligadb" / "20261027T125704Z_p48c_bl1.json").read_bytes()      # the approved full-season response, for every replay
        server = ST.Replay()
        server.matches = json.loads(saved_payload)
        server.log.clear()
        # 1. duplicate: the same cycle again at the same instant is not due; after 6 h it runs and imports nothing
        d1 = mgr.tick()
        restarted = sync.SyncManager(db_path=trial, cfg=cfg, opener=server, sleep=lambda s: None, clock=clock)
        d2 = restarted.tick("startup_check")
        clock.t = start + timedelta(hours=6, minutes=1)
        t_before = data_tables(trial)
        d3 = sync.SyncManager(db_path=trial, cfg=cfg, opener=server, sleep=lambda s: None, clock=clock, on_change=lambda: callbacks.append(2)).tick("periodic_check")
        t_after = data_tables(trial)
        rep["replayed_followups"] = dict(label="REPLAYED SNAPSHOT (no network)", same_instant=d1["outcome"], restart_inside_interval=d2["outcome"], cycle_after_6h=dict(outcome=d3["outcome"], changed=d3.get("changed"), requests=len(server.log)),
                                         duplicate_import_tables_changed=sorted(k for k in t_after if t_after[k] != t_before[k] and k not in ("sync_runs",)), duplicate_record_ids=q(trial, "SELECT COUNT(*) - COUNT(DISTINCT record_id) n FROM matches")[0]["n"])
        # 2. a failing provider cannot corrupt the database, and it backs off
        server.mode = "down"
        clock.t = restarted.next_due()
        data_before = {k: v for k, v in data_tables(trial).items() if k not in ("sync_runs", "sync_errors")}
        f1 = restarted.tick()
        due_f1 = restarted.next_due()
        rep["replayed_failure"] = dict(outcome=f1["outcome"], data_tables_unchanged={k: v for k, v in data_tables(trial).items() if k not in ("sync_runs", "sync_errors")} == data_before, next_due=due_f1.strftime(FMT),
                                       wait_hours=round((due_f1 - clock.t).total_seconds() / 3600, 1), integrity=q(trial, "PRAGMA integrity_check")[0]["integrity_check"])
        # 3. a provider that contradicts what is stored is quarantined, never applied
        server.mode, server.change_bump = "tamper", 1
        clock.t = restarted.next_due()
        stored = {r["record_id"]: (r["home_goals_final"], r["away_goals_final"], r["match_date"]) for r in q(trial, "SELECT record_id, home_goals_final, away_goals_final, match_date FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27'")}
        qn = q(trial, "SELECT COUNT(*) n FROM quarantine")[0]["n"]
        t1 = restarted.tick()
        rep["replayed_quarantine"] = dict(outcome=t1["outcome"], new_quarantine_rows=q(trial, "SELECT COUNT(*) n FROM quarantine")[0]["n"] - qn,
                                          reasons=[r["reason"][:100] for r in q(trial, "SELECT reason FROM quarantine ORDER BY id DESC LIMIT 4")],
                                          stored_scores_and_dates_unchanged=stored == {r["record_id"]: (r["home_goals_final"], r["away_goals_final"], r["match_date"]) for r in q(trial, "SELECT record_id, home_goals_final, away_goals_final, match_date FROM matches WHERE competition_key='BUNDESLIGA' AND season='2026-27'")})
        rep["replayed_requests_total"] = len(server.log)
    finally:
        socket.socket.connect, socket.create_connection = orig_connect, orig_cc
        sync.now_utc = real_now
    rep["private_copy_integrity"] = q(trial, "PRAGMA integrity_check")[0]["integrity_check"]
    rep["production_sha256_after"] = baseline_hash.physical_sha256(PROD)
    rep["production_untouched"] = rep["production_sha256_after"] == prod_before
    rep["config_sync_json_live_enabled"] = json.loads((ROOT / "config" / "sync.json").read_text(encoding="utf-8"))["live_enabled"]
    name = f"real_network_trial_stage{a.stage}.json"
    (OUT / name).write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    rm(WORK)
    print(json.dumps(rep, indent=1, default=str, ensure_ascii=False)[:7000])


if __name__ == "__main__":
    main()
