"""Daily audit of the automatic Bundesliga synchronisation (Phase 4.8F). READ-ONLY: it never approves a checkpoint, resolves a finding, or writes to the database.

    python app/store/daily_audit.py [store.sqlite] [--no-http]          prints a short summary, writes data/supervised/phase4/baselines/audit/<date>.json and .md
    (or: powershell -File scripts\\ops\\footiq_service.ps1 audit)

Exit code: 0 PASS, 1 ATTENTION (the owner has something to read or decide), 2 ALERT (switch synchronisation off and investigate: see P4_8D_ACTIVATION_CHECKLIST.md).
The operational reviewer named in config/operations.json is responsible for reading it every day.
"""
import json
import sqlite3
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from store import baseline_monitor, sync  # noqa: E402

PROD = C.ROOT / "data" / "footiq.sqlite"
AUDIT_DIR = C.ROOT / "data" / "supervised" / "phase4" / "baselines" / "audit"
LEDGER = C.ROOT / "data" / "snapshots" / "request_ledger.jsonl"
OPERATIONS = C.ROOT / "config" / "operations.json"
BACKUPS = C.ROOT / "data" / "backups"
MAX_REQUESTS_24H = 12                                 # 4 cycles a day x at most 3 attempts


def _ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def run_audit(store=PROD, checkpoints_file=None, out_dir=AUDIT_DIR, now=None, http=True, ledger=LEDGER, operations=OPERATIONS, backups=BACKUPS, cfg=None) -> dict:
    now = now or datetime.now(timezone.utc)
    cfg = cfg or sync.SyncConfig.load()
    ops = json.loads(Path(operations).read_text(encoding="utf-8")) if Path(operations).exists() else {}
    items, owner_actions, alert = [], [], False

    def note(level, text):
        items.append(dict(level=level, text=text))

    # 1. the database itself
    c = sqlite3.connect(f"file:{Path(store).as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
    fk = len(c.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or fk:
        alert = True
        note("ALERT", f"database integrity: integrity_check={integrity}, foreign-key problems={fk}")
    else:
        note("OK", "database integrity_check ok, no foreign-key problems")
    # 2. the baseline monitor (never approves)
    cps = baseline_monitor.checkpoints(checkpoints_file)
    if not cps:
        note("ATTENTION", "no baseline checkpoint exists: run baseline_monitor.py init")
        verdict = None
    else:
        rep = baseline_monitor.report(store, cps[-1])
        verdict = rep["verdict"]
        if verdict in ("NO_CHANGE", "EXPECTED_LOG_ONLY"):
            note("OK", f"baseline monitor: {verdict} against checkpoint {cps[-1]['id']} ({cps[-1].get('label')})")
        elif verdict == "IMPORT_EXPLAINED":
            note("ATTENTION", "baseline monitor: new verified results were imported and are explained by successful sync runs; they are NOT yet an approved checkpoint")
            owner_actions.append("Read the changed rows in the report, then decide whether to approve them as the next checkpoint (baseline_monitor.py approve ... --by <your name>). Nothing was approved automatically.")
        else:
            alert = True
            note("ALERT", "baseline monitor: UNEXPECTED changes: " + "; ".join(rep["reasons"]))
    # 3. the scheduler as the log history shows it
    st = sync.status(c, cfg, now)
    sch, q = st["scheduler"], st["quarantine"]
    c.close()
    if cfg.approved_competitions() != ["BUNDESLIGA", "LALIGA"]:
        alert = True
        note("ALERT", f"enabled competitions are {cfg.approved_competitions()}, expected BUNDESLIGA and LALIGA only")
    if cfg.live_enabled:
        startup = cfg.sync_mode == "startup"
        limit_h = cfg.stale_after_hours if startup else 2 * cfg.periodic_minutes / 60 + 1                # startup mode refreshes only when FootIQ is launched
        for key in cfg.approved_competitions():
            comp = next(x for x in st["competitions"] if x["competition_key"] == key)
            lg = sch.get("leagues", {}).get(key, {})
            last = comp["last_successful_external_check_utc"]
            age_h = (now - _ts(last)).total_seconds() / 3600 if last else None
            if age_h is None or age_h > limit_h:
                note("ATTENTION", f"{key}: last successful source check is {'never' if age_h is None else f'{age_h:.1f} h ago'} (expected within {limit_h:g} h): " + ("start FootIQ to refresh" if startup else "is the backend running?"))
                owner_actions.append("Run `scripts\\ops\\footiq_service.ps1 status`; start the backend if it is not running.")
            else:
                note("OK", f"{key}: last successful source check {age_h:.1f} h ago; {comp['last_check_summary']}")
            if lg.get("consecutive_failed_cycles"):
                note("ATTENTION", f"{key}: {lg['consecutive_failed_cycles']} failed cycle(s) in a row (next check {lg['next_check_utc']})")
                owner_actions.append(f"{key}: look at the provider's site and data/snapshots/request_ledger.jsonl; do not retry by hand. At 3 or more failures switch sync off (checklist section 6).")
            else:
                note("OK", f"{key}: no failed cycles in a row")
        note("OK", f"scheduler: {sch['status']}")
    else:
        note("ATTENTION", "live synchronisation is switched OFF in config/sync.json")
    # 4. requests in the last 24 h
    n24 = 0
    if Path(ledger).exists():
        for line in Path(ledger).read_text(encoding="utf-8").splitlines():
            try:
                if _ts(json.loads(line)["ts"]) > now - timedelta(hours=24):
                    n24 += 1
            except (ValueError, KeyError):
                continue
    if n24 > MAX_REQUESTS_24H:
        note("ATTENTION", f"{n24} provider requests in the last 24 h (normal: about 4, never more than {MAX_REQUESTS_24H})")
        owner_actions.append("More requests than the schedule allows: check for a second backend or a manual run before anything else.")
    else:
        note("OK", f"{n24} provider request(s) in the last 24 h")
    # 5. quarantine
    prev = sorted(Path(out_dir).glob("*.json")) if Path(out_dir).exists() else []
    prev_open = json.loads(prev[-1].read_text(encoding="utf-8")).get("quarantine_needing_review") if prev else None
    if prev_open is not None and q["needs_operator_review"] > prev_open:
        note("ATTENTION", f"{q['needs_operator_review'] - prev_open} NEW quarantine finding(s) since the last audit ({q['needs_operator_review']} open in total)")
        owner_actions.append("Review the new findings with docs/mini-project/phase4/QUARANTINE_REVIEW_PROCEDURE.md. The system never resolves them itself.")
    elif q["needs_operator_review"]:
        note("INFO", f"{q['needs_operator_review']} unresolved sync finding(s) are open ({q['by_kind']}); " + ("none is new since the last audit" if prev_open is not None else "first audit, so there is no earlier count to compare with"))
    else:
        note("OK", "no unresolved sync findings")
    # 6. the running backend (optional): one backend, one scheduler thread
    if http and cfg.live_enabled:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{__import__('os').environ.get('FOOTIQ_PORT', '8000')}/api/sync/status", timeout=8) as r:
                live = json.loads(r.read())["scheduler"]
            if cfg.sync_mode == "startup":
                note("OK", f"backend answering (pid {live.get('process_id')}); startup-refresh mode, no recurring scheduler (threads here: {live.get('active_scheduler_threads')}); {live['status']}")
            elif live.get("active_scheduler_threads") == 1:
                note("OK", f"backend answering; exactly 1 scheduler thread (pid {live.get('process_id')}); {live['status']}")
            else:
                note("ATTENTION", f"backend answering but {live.get('active_scheduler_threads')} scheduler thread(s) here (lock: {live.get('lock_state')})")
                owner_actions.append("If the lock is held by another process that is fine; if no process schedules, restart with `scripts\\ops\\footiq_service.ps1 restart`.")
        except Exception as exc:  # noqa: BLE001
            if cfg.sync_mode == "startup":
                note("INFO", f"backend is not running ({type(exc).__name__}): normal in startup-refresh mode; launching FootIQ refreshes the data once")
            else:
                note("ATTENTION", f"backend is not answering on its port ({type(exc).__name__})")
                owner_actions.append("Start it: `scripts\\ops\\footiq_service.ps1 start`.")
    # 7. backups (information)
    b = sorted(Path(backups).glob("footiq.*.sqlite")) if Path(backups).exists() else []
    note("INFO", f"{len(b)} verified backup file(s) kept; newest: {b[-1].name if b else 'none'}")
    level = "ALERT" if alert else "ATTENTION" if any(i["level"] == "ATTENTION" for i in items) else "PASS"
    rep = dict(generated_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), verdict=level, baseline_verdict=verdict, operational_reviewer=ops.get("operational_reviewer"), reviewer_assigned=ops.get("assigned_utc"),
               quarantine_needing_review=q["needs_operator_review"], requests_last_24h=n24, items=items, owner_actions=owner_actions,
               rule="This audit is read-only: it never approves a checkpoint, resolves a finding or changes data. An ALERT means: set live_enabled=false, restart, keep the evidence.")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    day = now.strftime("%Y-%m-%d")
    (out / f"{day}.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    md = [f"# FootIQ daily audit {day}: {level}", "", f"Reviewer: {rep['operational_reviewer']}  |  baseline monitor: {verdict}  |  requests in 24 h: {n24}  |  findings needing review: {q['needs_operator_review']}", ""]
    md += [f"* **{i['level']}** {i['text']}" for i in items]
    md += ["", "## Needs the reviewer" if owner_actions else "## Nothing needs the reviewer today"] + [f"* {a}" for a in owner_actions]
    (out / f"{day}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return rep


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rep = run_audit(args[0] if args else PROD, http="--no-http" not in sys.argv)
    print(f"FootIQ daily audit: {rep['verdict']} (reviewer: {rep['operational_reviewer']})")
    for i in rep["items"]:
        print(f"  [{i['level']}] {i['text']}")
    for a in rep["owner_actions"]:
        print(f"  -> {a}")
    print(f"report: {AUDIT_DIR / (rep['generated_utc'][:10] + '.md')}")
    sys.exit({"PASS": 0, "ATTENTION": 1, "ALERT": 2}[rep["verdict"]])


if __name__ == "__main__":
    main()
