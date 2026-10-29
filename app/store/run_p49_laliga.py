"""Phase 4.9: the La Liga retrieval, in two guarded stages. A one-shot tool, not a scheduler.

    python app/store/run_p49_laliga.py get       ONE real GET of https://api.openligadb.de/getmatchdata/la1/2026 into a PRIVATE COPY of production (no retry, no other URL); the response is saved
                                                 with its SHA-256, validated, and reconciled on the copy. Production is opened read-only and is compared before and after.
    python app/store/run_p49_laliga.py import    (after review) imports the SAME saved response into production, with a verified backup first; makes no request.

Date protection, quarantine and provenance are the normal ones: a differing date or score is held for a human, never applied.
"""
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from store import baseline_hash, db, sync  # noqa: E402

PROD = C.ROOT / "data" / "footiq.sqlite"
OUT = C.ROOT / "data" / "supervised" / "phase4" / "p49"
URL = "https://api.openligadb.de/getmatchdata/la1/2026"
KEY = "LALIGA"
LEDGER = C.ROOT / "data" / "snapshots" / "request_ledger.jsonl"
SNAPDIR = C.ROOT / "data" / "snapshots" / "openligadb"


class Abort(Exception):
    pass


def ro(path):
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def ledger_lines() -> int:
    return len(LEDGER.read_text(encoding="utf-8").splitlines()) if LEDGER.exists() else 0


def guard(real):
    calls = []

    def guarded(url, headers):
        if url != URL or calls:
            raise Abort(f"request guard: only {URL} once is approved (asked for {url}, call number {len(calls) + 1})")
        calls.append(url)
        return real(url, headers)
    guarded.calls = calls
    return guarded


def private_copy(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("", "-wal", "-shm"):
        Path(str(dest) + ext).unlink(missing_ok=True)
    src = ro(PROD)
    dst = sqlite3.connect(dest)
    src.backup(dst)
    dst.close()
    src.close()


def validate(body: bytes, conn) -> dict:
    """Facts about the response: league, season, teams, fixture coverage against what production already stores."""
    data = json.loads(body)
    resolver = sync.build_resolver(conn)
    comp = sync.APPROVED[KEY]["competition_id"]
    teams = sorted({m["team1"]["teamName"] for m in data} | {m["team2"]["teamName"] for m in data})
    unresolved = [t for t in teams if resolver.resolve("openligadb", comp, t)[0] is None]
    per_day = {}
    for m in data:
        per_day[m["group"]["groupOrderID"]] = per_day.get(m["group"]["groupOrderID"], 0) + 1
    stored = {(r["home_entity_id"], r["away_entity_id"]) for r in conn.execute("SELECT home_entity_id, away_entity_id FROM matches WHERE competition_key=? AND season='2026-27'", (KEY,))}
    pairs = {(resolver.resolve("openligadb", comp, m["team1"]["teamName"])[0], resolver.resolve("openligadb", comp, m["team2"]["teamName"])[0]) for m in data}
    return dict(matches=len(data), leagues=sorted({m["leagueShortcut"] for m in data}), seasons=sorted({m["leagueSeason"] for m in data}), teams=len(teams), unresolved_team_names=unresolved,
                matchdays=len(per_day), matches_per_matchday=sorted(set(per_day.values())), unique_match_ids=len({m["matchID"] for m in data}), finished=sum(1 for m in data if m["matchIsFinished"]),
                fixtures_in_production=len(stored), fixtures_matched_in_production=len(pairs & stored), fixtures_not_in_production=len(pairs - stored), production_fixtures_missing_from_response=len(stored - pairs))


def snapshot_of(key_part: str):
    files = sorted(p for p in SNAPDIR.glob(f"*{key_part}*.json") if not p.name.endswith(".meta.json"))
    return files[-1] if files else None


def stage_get():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = dict(started_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), stage="get", url=URL)
    prod_before = baseline_hash.physical_sha256(PROD)
    ledger_before = ledger_lines()
    rep["production_physical_sha256_before"], rep["ledger_lines_before"] = prod_before, ledger_before
    priv = OUT / "private_copy.sqlite"
    private_copy(priv)
    pc = ro(priv)
    before = {r["record_id"]: dict(r) for r in pc.execute("SELECT * FROM matches WHERE competition_key=?", (KEY,))}
    q_before = pc.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
    pc.close()
    cfg = sync.SyncConfig(live_enabled=True, startup_check=True, startup_delay_seconds=0, periodic_minutes=360, max_retries=0, refresh_mode="full_season",
                          sources={"openligadb": {"enabled": True, "competitions": [KEY]}})
    g = {}

    def make_guard(real):
        g["opener"] = guard(real)
        return g["opener"]
    mgr = sync.SyncManager(db_path=priv, cfg=cfg, request_guard=make_guard, sleep=lambda s: None)
    res = mgr.check_once("manual_check", only=[KEY])                       # <<< the one real request (private copy)
    rep["cycle"] = dict(outcome=res["outcome"], details=res.get("details"), requests_made=len(g["opener"].calls) if g.get("opener") else 0)
    rep["production_physical_sha256_after"] = baseline_hash.physical_sha256(PROD)
    rep["production_untouched"] = prod_before == rep["production_physical_sha256_after"]
    rep["ledger_lines_after"] = ledger_lines()
    if res["outcome"] != "ok":
        rep["result"] = "STOP: the request or its validation failed; nothing was imported"
    else:
        snap = snapshot_of(f"{sync.APPROVED[KEY]['league']}_{sync.APPROVED[KEY]['season']}_season")
        meta = json.loads(Path(str(snap) + ".meta.json").read_text(encoding="utf-8"))
        body = snap.read_bytes()
        rep["snapshot"] = dict(file=str(snap.relative_to(C.ROOT)).replace("\\", "/"), sha256=hashlib.sha256(body).hexdigest(), sha256_in_meta=meta.get("sha256"), bytes=len(body), origin=meta.get("origin"), url=meta.get("url"), status=meta.get("status"), saved_utc=meta.get("saved_utc"))
        pr = ro(PROD)
        rep["validation"] = validate(body, pr)
        pr.close()
        pc = ro(priv)
        after = {r["record_id"]: dict(r) for r in pc.execute("SELECT * FROM matches WHERE competition_key=?", (KEY,))}
        skip = {"last_changed_utc", "change_count", "content_hash"}
        changed = {rid: {k: [before[rid][k], r[k]] for k in r if k not in skip and r[k] != before[rid][k]} for rid, r in after.items() if rid in before and any(r[k] != before[rid][k] for k in r if k not in skip)}
        new_completed = [rid for rid, c in changed.items() if c.get("status", [None, None])[1] == "completed"]
        q_rows = [dict(r) for r in pc.execute("SELECT reason, COUNT(*) n FROM quarantine WHERE id > ? GROUP BY substr(reason, 1, 14)", (q_before,))] if False else []
        newq = [dict(r) for r in pc.execute("SELECT reason FROM quarantine ORDER BY id DESC LIMIT ?", (pc.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0] - q_before,))] if pc.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0] > q_before else []
        kinds = {}
        for x in newq:
            k = x["reason"].split(":")[0].split(" ")[0]
            kinds[k] = kinds.get(k, 0) + 1
        rep["dry_run"] = dict(rows_before_after=[len(before), len(after)], rows_changed=len(changed), changed_fields=sorted({f for c in changed.values() for f in c}), results_that_would_be_imported=len(new_completed),
                              new_rows=len(set(after) - set(before)), would_be_quarantined_additionally=kinds, completed_before=sum(1 for r in before.values() if r["status"] == "completed"),
                              completed_after_in_copy=sum(1 for r in after.values() if r["status"] == "completed"), changes_that_touch_a_stored_date_or_score=[rid for rid, c in changed.items() if set(c) & {"match_date", "home_goals_final", "away_goals_final"} and before[rid]["status"] == "completed"],
                              importable_record_ids=sorted(new_completed))
        pc.close()
        v = rep["validation"]
        bad = [m for m, ok in (("league", v["leagues"] == [sync.APPROVED[KEY]["league"]]), ("season", v["seasons"] == [2026]), ("380 matches", v["matches"] == 380), ("20 teams", v["teams"] == 20), ("38 matchdays of 10", v["matchdays"] == 38 and v["matches_per_matchday"] == [10]),
                               ("unique ids", v["unique_match_ids"] == 380), ("no unresolved team", not v["unresolved_team_names"]), ("all fixtures matched", v["fixtures_matched_in_production"] == v["fixtures_in_production"] and not v["fixtures_not_in_production"]),
                               ("hash matches meta", rep["snapshot"]["sha256"] == rep["snapshot"]["sha256_in_meta"]), ("exactly one request", rep["cycle"]["requests_made"] == 1 and rep["ledger_lines_after"] == ledger_before + 1),
                               ("production untouched", rep["production_untouched"]), ("no stored date or score would change", not rep["dry_run"]["changes_that_touch_a_stored_date_or_score"])) if not ok]
        data = json.loads(body)
        fin = [m for m in data if m["matchIsFinished"]]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        past = [m for m in data if not m["matchIsFinished"] and m["matchDateTimeUTC"] < today[:10]]
        rep["freshness"] = dict(finished=len(fin), newest_finished_kickoff=max((m["matchDateTimeUTC"] for m in fin), default=None), unfinished_past_their_date=len(past),
                                oldest_unfinished_past=min((m["matchDateTimeUTC"] for m in past), default=None), provider_last_update=max(m["lastUpdateDateTime"] for m in data),
                                production_newest_result=ro(PROD).execute("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND status IN ('completed','awarded')", (KEY,)).fetchone()[0])
        rep["validation_failed"] = bad
        rep["result"] = "VALIDATED" if not bad else "STOP: " + "; ".join(bad)
    (OUT / "get_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in rep if k not in ("dry_run",)} | {"dry_run": {k: v for k, v in rep.get("dry_run", {}).items() if k != "importable_record_ids"}}, indent=1, ensure_ascii=False, default=str))


BACKUPS = C.ROOT / "data" / "backups"
V3 = json.loads((C.ROOT / "data" / "supervised" / "phase4" / "p48c" / "db_baseline_v3.json").read_text(encoding="utf-8"))


def table_counts(path):
    c = ro(path)
    try:
        return {t: c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()}
    finally:
        c.close()


def backend_status():
    import urllib.request
    with urllib.request.urlopen("http://127.0.0.1:8000/api/sync/status", timeout=8) as r:
        return json.loads(r.read())


def stage_import():
    get = json.loads((OUT / "get_report.json").read_text(encoding="utf-8"))
    rep = dict(started_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), stage="import")
    bad = []
    if get.get("result") != "VALIDATED":
        bad.append("the GET stage did not validate")
    snap = C.ROOT / get["snapshot"]["file"]
    body = snap.read_bytes()
    meta = json.loads(Path(str(snap) + ".meta.json").read_text(encoding="utf-8"))
    if hashlib.sha256(body).hexdigest() != get["snapshot"]["sha256"]:
        bad.append("the saved response no longer matches its recorded SHA-256")
    phys = baseline_hash.physical_sha256(PROD)
    rep["production_physical_sha256_before"] = phys
    if phys != get["production_physical_sha256_before"]:
        bad.append("production changed since the dry run (the dry run no longer describes it)")
    sch = backend_status()["scheduler"]
    rep["backend_before"] = dict(status=sch["status"], active_scheduler_threads=sch.get("active_scheduler_threads"), next_check=sch["next_scheduled_check_utc"], enabled=sch.get("enabled_competitions"), failed=sch["consecutive_failed_cycles"])
    if sch.get("active_scheduler_threads") != 1 or "running" in sch["status"]:
        bad.append("scheduler is not idle with exactly one thread")
    nxt = datetime.strptime(sch["next_scheduled_check_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if (nxt - datetime.now(timezone.utc)).total_seconds() < 30 * 60:
        bad.append("the Bundesliga check is due within 30 minutes: do this afterwards")
    lg = baseline_hash.logical(PROD, V3["last_baseline_run_id"])
    rep["integrity_before"] = lg["integrity_check"]
    if lg["integrity_check"] != "ok":
        bad.append("integrity_check not ok")
    c = ro(PROD)
    fc = c.execute("SELECT (SELECT COUNT(*) FROM forecasts) a, (SELECT COUNT(*) FROM forecast_runs) b").fetchone()
    rep["forecasts_before"] = [fc["a"], fc["b"]]
    c.close()
    rep["preconditions_failed"] = bad
    if bad:
        rep["result"] = "STOP before backup/import: " + "; ".join(bad)
        (OUT / "import_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
        print(json.dumps(rep, indent=1))
        return
    # ---- SQLite-safe backup, verified, restored to a private file
    BACKUPS.mkdir(parents=True, exist_ok=True)
    dst = BACKUPS / f"footiq.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.pre-laliga-import.sqlite"
    src = ro(PROD)
    out = sqlite3.connect(dst)
    src.backup(out)
    out.close()
    src.close()
    restored = OUT / "restore_test.sqlite"
    restored.unlink(missing_ok=True)
    shutil.copyfile(dst, restored)
    bl_, rl_ = baseline_hash.logical(dst, V3["last_baseline_run_id"]), baseline_hash.logical(restored, V3["last_baseline_run_id"])
    before_counts = table_counts(PROD)
    rep["backup"] = dict(path=dst.relative_to(C.ROOT).as_posix(), bytes=dst.stat().st_size, physical_sha256=baseline_hash.physical_sha256(dst), integrity=bl_["integrity_check"],
                         logical_equals_production=bl_["logical_sha256"] == lg["logical_sha256"], restore_integrity=rl_["integrity_check"], restore_logical_equals_production=rl_["logical_sha256"] == lg["logical_sha256"],
                         restore_matches_rows=table_counts(restored)["matches"], production_matches_rows=before_counts["matches"])
    b = rep["backup"]
    if not (b["integrity"] == "ok" and b["logical_equals_production"] and b["restore_integrity"] == "ok" and b["restore_logical_equals_production"] and b["restore_matches_rows"] == b["production_matches_rows"]):
        rep["result"] = "STOP: backup verification failed; production not touched"
        (OUT / "import_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
        print(json.dumps(rep, indent=1))
        return
    (BACKUPS / (dst.name + ".json")).write_text(json.dumps(rep["backup"], indent=1), encoding="utf-8")
    rc = ro(restored)
    before_rows = {r["record_id"]: dict(r) for r in rc.execute("SELECT * FROM matches")}
    rc.close()
    # ---- the one controlled import cycle: the SAME saved response, no request
    cfg = sync.SyncConfig(live_enabled=True, periodic_minutes=360, max_retries=0, refresh_mode="full_season", sources={"openligadb": {"enabled": True, "competitions": [KEY]}})
    mgr = sync.SyncManager(db_path=PROD, cfg=cfg, sleep=lambda s: None)
    conn = db.connect(PROD)
    run_id = mgr._begin_run(conn, "manual_check")
    if run_id is None:
        raise Abort("another check is running")
    spec = sync.APPROVED[KEY]
    saved = datetime.strptime(meta["saved_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    try:
        sync.validate_season_payload(body, spec["league"])
        res = sync.replay_payload(conn, body, KEY, retrieved_utc=meta["saved_utc"], now=saved, kind="sync", spec=spec, snapshot_id=meta["snapshot_id"], url=URL, protect_dates=True)
        conn.execute("UPDATE sync_runs SET requests=1 WHERE run_id=?", (res["run_id"],))                # the one real GET that produced these bytes (ledger line 3)
        detail = [dict(competition=KEY, inserted=res["inserted"], updated=res["updated"], unchanged=res["unchanged"], confirmed=res["confirmed"], quarantined=res["quarantined"], requests=1, snapshot_reused=False)]
        conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='ok', requests=1, inserted=?, detail=? WHERE run_id=?", (sync.now_utc(), res["inserted"] + res["updated"], json.dumps(detail), run_id))
        conn.commit()
        rep["import"] = dict(cycle_run_id=run_id, sync_run_id=res["run_id"], stats={k: res[k] for k in ("inserted", "updated", "unchanged", "confirmed", "quarantined")}, snapshot_id=meta["snapshot_id"])
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='error', detail=? WHERE run_id=?", (sync.now_utc(), json.dumps([dict(competition=KEY, error=f"{type(exc).__name__}: {exc}"[:300])]), run_id))
        conn.commit()
        rep["import_error"] = f"{type(exc).__name__}: {exc}"
    conn.close()
    # ---- verification against the backup
    pc = ro(PROD)
    after_rows = {r["record_id"]: dict(r) for r in pc.execute("SELECT * FROM matches")}
    skip = {"last_changed_utc", "change_count", "content_hash"}
    changed = {rid: sorted(k for k in r if k not in skip and r[k] != before_rows[rid][k]) for rid, r in after_rows.items() if any(r[k] != before_rows[rid][k] for k in r if k not in skip)}
    fc = pc.execute("SELECT (SELECT COUNT(*) FROM forecasts) a, (SELECT COUNT(*) FROM forecast_runs) b").fetchone()
    pc.close()
    after_counts = table_counts(PROD)
    rep["verification"] = dict(matches_changed=changed, rows_before_after=[len(before_rows), len(after_rows)], table_row_counts_changed={t: [before_counts[t], after_counts[t]] for t in after_counts if before_counts.get(t) != after_counts[t]},
                               integrity=baseline_hash.logical(PROD, V3["last_baseline_run_id"])["integrity_check"], forecasts_after=[fc["a"], fc["b"]], ledger_lines=ledger_lines())
    rep["result"] = "IMPORTED" if not rep.get("import_error") and not changed else "IMPORT DONE WITH PROBLEMS: review"
    (OUT / "import_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(rep, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "get":
        stage_get()
    elif len(sys.argv) > 1 and sys.argv[1] == "import":
        stage_import()
    else:
        raise SystemExit(__doc__)
