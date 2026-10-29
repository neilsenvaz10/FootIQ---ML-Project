"""Auditable baseline monitoring for the production store (Phase 4.8D final safeguards). Read-only on the store (SQLite mode=ro); writes only its own checkpoint and report files.

A CHECKPOINT is an approved state: physical hash, logical hash (footiq-logical-v1 with the cut-off run id), per-table hashes, a per-(competition, season) digest of `matches`, and the
row digests of the approved scopes. Checkpoints are appended to `checkpoints.jsonl` and never rewritten; baseline v3 is checkpoint 1.

A REPORT compares the store with a checkpoint and sorts every difference into one of four verdicts. The existence of a sync run never makes a change legitimate on its own:
  NO_CHANGE                    nothing differs
  EXPECTED_LOG_ONLY            only the sync diary changed (sync_runs rows after the cut-off, sync_errors, source_snapshots, source_state)
  IMPORT_EXPLAINED             rows of an APPROVED scope (competition, season) changed or arrived, and the successful sync runs since the checkpoint account for them: the number of changed rows is
                               not more than the records those runs report as inserted+updated, every changed row now names an approved provider as its source, and nothing else changed except
                               their source links and new quarantine findings. A person must still approve it as the next checkpoint.
  UNEXPECTED                   anything else: a change in another competition or season, in teams, aliases, competitions, forecasts, simulation runs or meta; deleted rows; fewer quarantine rows
                               than before; changes that the runs do not explain. The report lists them and `approve` refuses.

    python app/store/baseline_monitor.py report  <store.sqlite> [--checkpoint N]     print/write the report (the daily report)
    python app/store/baseline_monitor.py approve <store.sqlite> --label TEXT --by NAME   append a new checkpoint (refused when the verdict is UNEXPECTED)
    python app/store/baseline_monitor.py init    <store.sqlite> --label TEXT --by NAME   create checkpoint 1 from the store as it is (baseline v3), only if no checkpoint exists
"""
import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from store import baseline_hash  # noqa: E402

DIR = C.ROOT / "data" / "supervised" / "phase4" / "baselines"
CHECKPOINTS = DIR / "checkpoints.jsonl"
REPORTS = DIR / "reports"
OPERATIONAL_TABLES = {"sync_runs", "sync_errors", "source_snapshots", "source_state"}
IMPORT_TABLES = {"matches", "match_sources", "quarantine"}
APPROVED_SCOPES = [("BUNDESLIGA", "2026-27")]
APPROVED_PROVIDERS = ("openligadb",)
IMPORT_RUN_KINDS = ("sync",)                       # runs that fetch from an approved provider; manual imports (p48d_import_*) are approved checkpoints of their own


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _conn(path):
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def digest(path, last_run_id: int, scopes=None) -> dict:
    scopes = scopes or APPROVED_SCOPES
    lg = baseline_hash.logical(path, last_run_id)
    c = _conn(path)
    try:
        by_group: dict = {}
        for r in c.execute("SELECT competition_key, season, record_id, content_hash FROM matches ORDER BY competition_key, season, record_id"):
            by_group.setdefault(f"{r['competition_key']}|{r['season']}", hashlib.sha256()).update(f"{r['record_id']}={r['content_hash']}\n".encode())
        groups = {k: v.hexdigest() for k, v in by_group.items()}
        rows = {f"{k}|{s}": {r["record_id"]: r["content_hash"] for r in c.execute("SELECT record_id, content_hash FROM matches WHERE competition_key=? AND season=?", (k, s))} for k, s in scopes}
        counts = dict(matches=c.execute("SELECT COUNT(*) n FROM matches").fetchone()["n"], quarantine=c.execute("SELECT COUNT(*) n FROM quarantine").fetchone()["n"])
    finally:
        c.close()
    return dict(physical_sha256=baseline_hash.physical_sha256(path), logical_sha256=lg["logical_sha256"], last_run_id=last_run_id, integrity_check=lg["integrity_check"], tables={k: v for k, v in lg["tables"].items()},
                groups=groups, scope_rows=rows, counts=counts, approved_scopes=[list(s) for s in scopes])


def checkpoints(file=None) -> list:
    f = Path(file or CHECKPOINTS)
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []


def _max_run_id(path) -> int:
    c = _conn(path)
    try:
        return c.execute("SELECT COALESCE(MAX(run_id), 0) FROM sync_runs").fetchone()[0]
    finally:
        c.close()


def append_checkpoint(entry: dict, file=None) -> dict:
    f = Path(file or CHECKPOINTS)
    f.parent.mkdir(parents=True, exist_ok=True)
    prior = checkpoints(f)
    entry = dict(entry, id=len(prior) + 1, created_utc=utc_now(), previous_physical_sha256=prior[-1]["physical_sha256"] if prior else None)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def report(path, checkpoint: dict, providers=APPROVED_PROVIDERS) -> dict:
    """Compare the store at `path` with `checkpoint`. Never writes to the store."""
    cut = checkpoint["last_run_id"]
    now = digest(path, cut, [tuple(s) for s in checkpoint["approved_scopes"]])
    out = dict(generated_utc=utc_now(), checkpoint_id=checkpoint["id"], checkpoint_label=checkpoint.get("label"), checkpoint_physical=checkpoint["physical_sha256"], checkpoint_logical=checkpoint["logical_sha256"],
               current_physical=now["physical_sha256"], current_logical=now["logical_sha256"], integrity_check=now["integrity_check"])
    changed_tables = sorted(t for t in now["tables"] if now["tables"][t]["sha256"] != checkpoint["tables"].get(t, {}).get("sha256"))
    out["changed_tables"] = changed_tables
    if now["physical_sha256"] == checkpoint["physical_sha256"]:
        return dict(out, verdict="NO_CHANGE", reasons=[], approvable=False)
    problems, notes = [], []
    if now["integrity_check"] != "ok":
        problems.append(f"PRAGMA integrity_check is {now['integrity_check']}")
    other = [t for t in changed_tables if t not in OPERATIONAL_TABLES | IMPORT_TABLES]
    if other:
        problems.append(f"business tables changed outside the approved import path: {other}")
    scopes = {f"{k}|{s}" for k, s in checkpoint["approved_scopes"]}
    changed_groups = sorted(g for g in set(now["groups"]) | set(checkpoint["groups"]) if now["groups"].get(g) != checkpoint["groups"].get(g))
    outside = [g for g in changed_groups if g not in scopes]
    if outside:
        problems.append(f"matches changed outside the approved scopes: {outside[:10]}")
    if now["counts"]["quarantine"] < checkpoint["counts"]["quarantine"]:
        problems.append(f"quarantine lost {checkpoint['counts']['quarantine'] - now['counts']['quarantine']} row(s): findings must never be deleted")
    scope_changes = {}
    for g in changed_groups:
        if g in scopes:
            old, new = checkpoint["scope_rows"].get(g, {}), now["scope_rows"].get(g, {})
            scope_changes[g] = dict(changed=sorted(r for r in new if r in old and new[r] != old[r]), added=sorted(set(new) - set(old)), removed=sorted(set(old) - set(new)))
            if scope_changes[g]["removed"]:
                problems.append(f"{g}: {len(scope_changes[g]['removed'])} match row(s) disappeared")
    out["scope_changes"] = {g: {k: (v if k != "changed" else v[:20]) for k, v in d.items()} | {"n_changed": len(d["changed"]), "n_added": len(d["added"])} for g, d in scope_changes.items()}
    if scope_changes and not problems:
        c = _conn(path)
        try:
            ph = ",".join("?" * len(IMPORT_RUN_KINDS))
            runs = c.execute(f"SELECT run_id, kind, competition_key, outcome, inserted, updated FROM sync_runs WHERE run_id>? AND outcome='ok' AND kind IN ({ph})", (cut, *IMPORT_RUN_KINDS)).fetchall()
            claimed_changed = sum((r["inserted"] or 0) + (r["updated"] or 0) for r in runs)
            claimed_added = sum(r["inserted"] or 0 for r in runs)
            n_changed = sum(len(d["changed"]) + len(d["added"]) for d in scope_changes.values())
            n_added = sum(len(d["added"]) for d in scope_changes.values())
            ids = [r for d in scope_changes.values() for r in d["changed"] + d["added"]]
            marks = ",".join("?" * len(ids)) if ids else "''"
            wrong_source = [r["record_id"] for r in c.execute(f"SELECT record_id, source_system FROM matches WHERE record_id IN ({marks})", ids) if not any(p in (r["source_system"] or "") for p in providers)] if ids else []
        finally:
            c.close()
        out["explained_by"] = dict(successful_runs_since_checkpoint=[dict(r) for r in runs], records_claimed=claimed_changed, rows_changed_or_added=n_changed)
        if n_changed > claimed_changed or n_added > claimed_added:
            problems.append(f"{n_changed} match row(s) changed or arrived but the successful sync runs since the checkpoint report only {claimed_changed} inserted+updated ({claimed_added} inserted): the difference is unexplained")
        if wrong_source:
            problems.append(f"{len(wrong_source)} changed row(s) do not name an approved provider as their source: {wrong_source[:5]}")
        if not runs:
            problems.append("match rows changed but no successful sync run since the checkpoint accounts for them")
    if problems:
        return dict(out, verdict="UNEXPECTED", reasons=problems, approvable=False)
    if scope_changes:
        return dict(out, verdict="IMPORT_EXPLAINED", reasons=["newly verified results in an approved scope, accounted for by successful sync runs: needs a person's approval as the next checkpoint"], approvable=True)
    if set(changed_tables) <= OPERATIONAL_TABLES | {"quarantine", "match_sources"} or not changed_tables:
        if "quarantine" in changed_tables:
            notes.append(f"{now['counts']['quarantine'] - checkpoint['counts']['quarantine']} new quarantine finding(s): they need a person's review")
        return dict(out, verdict="EXPECTED_LOG_ONLY", reasons=notes, approvable=True)
    return dict(out, verdict="UNEXPECTED", reasons=[f"changes not classified: {changed_tables}"], approvable=False)


def daily_report(path, file=None, reports_dir=None) -> dict:
    cps = checkpoints(file)
    if not cps:
        raise SystemExit("no checkpoint exists yet: run 'init' first")
    rep = report(path, cps[-1])
    d = Path(reports_dir or REPORTS)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    return rep


def approve(path, label: str, by: str, file=None) -> dict:
    cps = checkpoints(file)
    rep = report(path, cps[-1])
    if rep["verdict"] == "UNEXPECTED":
        raise PermissionError("refused: the report shows unexpected changes: " + "; ".join(rep["reasons"]))
    entry = digest(path, _max_run_id(path))
    return append_checkpoint(dict(entry, label=label, approved_by=by, verdict_when_approved=rep["verdict"], reasons_when_approved=rep["reasons"]), file)


def init(path, label: str, by: str, file=None) -> dict:
    if checkpoints(file):
        raise PermissionError("checkpoints already exist; use 'approve'")
    return append_checkpoint(dict(digest(path, _max_run_id(path)), label=label, approved_by=by, verdict_when_approved="INITIAL"), file)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["report", "approve", "init"])
    ap.add_argument("store")
    ap.add_argument("--label", default="")
    ap.add_argument("--by", default="")
    a = ap.parse_args()
    if a.command == "report":
        rep = daily_report(a.store)
        print(json.dumps({k: rep[k] for k in ("verdict", "reasons", "changed_tables", "current_physical", "current_logical", "checkpoint_id")}, indent=1))
    elif a.command == "approve":
        assert a.label and a.by, "--label and --by are required"
        print(json.dumps({k: v for k, v in approve(a.store, a.label, a.by).items() if k in ("id", "label", "approved_by", "physical_sha256", "logical_sha256", "verdict_when_approved")}, indent=1))
    else:
        assert a.label and a.by, "--label and --by are required"
        print(json.dumps({k: v for k, v in init(a.store, a.label, a.by).items() if k in ("id", "label", "approved_by", "physical_sha256", "logical_sha256")}, indent=1))


if __name__ == "__main__":
    main()
