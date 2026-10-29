"""Phase 4.8D Stage 1: guarded production import of EXACTLY six verified results from the saved, SHA-256-verified snapshots of 2026-10-27. No network.

    python app/store/import_p48d_stage1.py --step bundesliga            checks, backup, restore test and reconciliation on a PRIVATE copy; does NOT touch production
    python app/store/import_p48d_stage1.py --step bundesliga --execute  ... then the one-transaction import into data/footiq.sqlite, then the verification checkpoint
    python app/store/import_p48d_stage1.py --step laliga [--execute]    the same for La Liga (separate transaction, separate checkpoint; needs the Bundesliga checkpoint)

Safety (each aborts the run before anything is written):
  1. production identity: path, physical and logical hashes equal the previous recorded baseline/checkpoint; integrity_check ok; Git: nothing staged, HEAD unchanged; live_enabled false
  2. no concurrent writer (an exclusive lock can be taken) and no application process running
  3. SQLite online-backup of production, integrity-checked, hash-checked, and restored to a private database
  4. the proposed rows are reconciled on that restored copy; the result must equal the allow-list exactly (same records, same fields, same scores)
  5. the import itself is one transaction with its own post-condition check inside it; any mismatch rolls everything back
Only the allow-listed source records are ingested. Date protection is on. Nothing else is read from the snapshot into the store.
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
import config as C  # noqa: E402
from store import baseline_hash, db, sync  # noqa: E402

PROD = C.ROOT / "data" / "footiq.sqlite"
BACKUPS = C.ROOT / "data" / "backups"
OUT = C.ROOT / "data" / "supervised" / "phase4" / "p48d"
SNAPDIR = C.ROOT / "data" / "snapshots" / "p48c" / "openligadb"
HEAD = "970f461"
V2 = C.ROOT / "data" / "supervised" / "phase4" / "p48c" / "db_baseline_v2.json"

STEPS = {
    "bundesliga": dict(key="BUNDESLIGA", snapshot="20261027T125704Z_p48c_bl1.json", sha="b725c2f3e30a3320f75da9891a2cfd2b5b93aed231da16aab253cf81a6bd6b46", spec=sync.APPROVED["BUNDESLIGA"],
                       url="https://api.openligadb.de/getmatchdata/bl1/2026", season_matches=306,
                       expected=[("TSG 1899 Hoffenheim", "Bayer 04 Leverkusen", "2026-10-25", 3, 0), ("SC Freiburg", "FC Bayern München", "2026-10-25", 1, 3)], previous=None),
    "laliga": dict(key="LALIGA", snapshot="20261027T130112Z_p48c_la1.json", sha="efe9e2a94ae06151f39947cbcb04e73e5c8e5f1534447bc96c5f3284afc11508", spec=sync.OFFLINE_PREPARED["LALIGA"],
                   url="https://api.openligadb.de/getmatchdata/la1/2026", season_matches=380,
                   expected=[("Athletic Club", "Getafe CF", "2026-10-25", 4, 0), ("FC Barcelona", "Real Madrid CF", "2026-10-25", 1, 2), ("RC Celta de Vigo", "Real Betis Balompié", "2026-10-25", 0, 0),
                             ("Real Sociedad de Fútbol", "Levante UD", "2026-10-25", 2, 1)], previous="bundesliga"),
}
EXPECTED_FIELDS = {"status", "home_goals_final", "away_goals_final", "home_goals_90", "away_goals_90", "label_90_status", "outcome", "rated", "regular", "in_universe", "source_system", "licence", "model_home_entity", "model_away_entity"}


class Abort(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rows(path, sql, *a):
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def previous_state(step: str) -> dict:
    """The recorded state production must still be in: baseline v2 for the first step, the Bundesliga checkpoint for the second."""
    if STEPS[step]["previous"] is None:
        r = json.loads(V2.read_text(encoding="utf-8"))
        return dict(physical=r["physical_sha256"], logical=r["logical_sha256"], last_run=7, label="baseline v2")
    p = OUT / f"checkpoint_{STEPS[step]['previous']}.json"
    if not p.exists():
        raise Abort(f"the {STEPS[step]['previous']} checkpoint is missing: {p.name}")
    r = json.loads(p.read_text(encoding="utf-8"))
    return dict(physical=r["after"]["physical_sha256"], logical=r["after"]["logical_sha256"], last_run=r["after"]["last_baseline_run_id"], label=f"{STEPS[step]['previous']} checkpoint")


def git(*args):
    return subprocess.run(["git", *args], cwd=C.ROOT, capture_output=True, text=True).stdout.strip()


def processes_using_the_store() -> list:
    cmd = "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and ($_.CommandLine -like '*uvicorn*' -or $_.CommandLine -like '*main:app*' -or $_.CommandLine -like '*pytest*' -or $_.CommandLine -like '*footiq*sync*') } | ForEach-Object { $_.ProcessId.ToString() + ' ' + $_.CommandLine }"
    out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip().splitlines()
    return [l for l in out if "import_p48d_stage1" not in l]


def preconditions(step: str) -> dict:
    prev = previous_state(step)
    info = dict(step=step, expected_previous=prev["label"])
    info["path"], info["bytes"] = str(PROD), PROD.stat().st_size
    info["physical_sha256"] = baseline_hash.physical_sha256(PROD)
    lg = baseline_hash.logical(PROD, prev["last_run"])
    info["logical_sha256"], info["integrity_check"] = lg["logical_sha256"], lg["integrity_check"]
    info["physical_matches_record"], info["logical_matches_record"] = info["physical_sha256"] == prev["physical"], lg["logical_sha256"] == prev["logical"]
    info["git_staged"] = [x for x in git("diff", "--cached", "--name-only").splitlines() if x]
    info["git_head"] = git("log", "--oneline", "-1")
    info["live_enabled"] = json.loads((C.ROOT / "config" / "sync.json").read_text(encoding="utf-8"))["live_enabled"]
    info["application_processes"] = processes_using_the_store()
    try:
        c = sqlite3.connect(PROD, timeout=0)
        c.execute("BEGIN EXCLUSIVE")
        c.rollback()
        c.close()
        info["exclusive_lock_available"] = True
    except sqlite3.OperationalError as exc:
        info["exclusive_lock_available"] = False
        info["lock_error"] = str(exc)
    snap = SNAPDIR / STEPS[step]["snapshot"]
    info["snapshot_sha256"] = baseline_hash.physical_sha256(snap)
    info["snapshot_matches_record"] = info["snapshot_sha256"] == STEPS[step]["sha"]
    bad = [k for k, ok in (("physical hash differs from the record", info["physical_matches_record"]), ("logical hash differs from the record", info["logical_matches_record"]), ("integrity_check not ok", info["integrity_check"] == "ok"),
                           ("something is staged in Git", not info["git_staged"]), ("HEAD changed", info["git_head"].startswith(HEAD)), ("live_enabled is true", info["live_enabled"] is False),
                           ("an application/test process is running", not info["application_processes"]), ("no exclusive lock: a writer is active", info["exclusive_lock_available"]),
                           ("snapshot hash differs from the approved one", info["snapshot_matches_record"])) if not ok]
    info["failed"] = bad
    if bad:
        raise Abort("; ".join(bad))
    return info


def backup(step: str, prev: dict) -> dict:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst = BACKUPS / f"footiq.{stamp}.pre-{step}.sqlite"
    src = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
    out = sqlite3.connect(dst)
    src.backup(out)                                                       # SQLite's online backup API: a consistent snapshot even with a WAL
    out.close()
    src.close()
    lg = baseline_hash.logical(dst, prev["last_run"])
    ok = lg["logical_sha256"] == prev["logical"] and lg["integrity_check"] == "ok"
    restored = OUT / f"restore_test_{step}.sqlite"                        # restore to a private database and open it
    restored.unlink(missing_ok=True)
    shutil.copyfile(dst, restored)
    rl = baseline_hash.logical(restored, prev["last_run"])
    n = rows(restored, "SELECT COUNT(*) n FROM matches")[0]["n"]
    info = dict(path=str(dst.relative_to(C.ROOT)), bytes=dst.stat().st_size, physical_sha256=baseline_hash.physical_sha256(dst), logical_equals_production=ok, integrity_check=lg["integrity_check"],
                restore=dict(logical_equals_production=rl["logical_sha256"] == prev["logical"], integrity_check=rl["integrity_check"], matches=n))
    if not (ok and info["restore"]["logical_equals_production"] and rl["integrity_check"] == "ok" and n == 223510):
        raise Abort(f"backup verification failed: {info}")
    (BACKUPS / (dst.name + ".json")).write_text(json.dumps(info, indent=1), encoding="utf-8")
    return dict(info, restored_path=str(restored))


def parse(step: str):
    meta = json.loads((SNAPDIR / (STEPS[step]["snapshot"] + ".meta.json")).read_text(encoding="utf-8"))
    payload = (SNAPDIR / STEPS[step]["snapshot"]).read_bytes()
    _, _, ol = sync._adapters()
    now = datetime.strptime(meta["saved_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    recs = ol.parse_payload(payload, meta["saved_utc"], meta["snapshot_id"], now, STEPS[step]["spec"]["competition_id"])
    if len(recs) != STEPS[step]["season_matches"]:
        raise Abort(f"snapshot has {len(recs)} records, expected {STEPS[step]['season_matches']}")
    return meta, payload, recs


def allow_list(step: str, recs: list, conn) -> list:
    """Independently validate the approved rows against the snapshot AND the current database; return the matching records. Anything else in the snapshot is ignored."""
    resolver = sync.build_resolver(conn)
    spec = STEPS[step]["spec"]
    disp = lambda e: (conn.execute("SELECT display_name FROM teams WHERE entity_id=?", (e,)).fetchone() or [None])[0]  # noqa: E731
    found, problems = {}, []
    wanted = {(h, a): (d, gh, ga) for h, a, d, gh, ga in STEPS[step]["expected"]}
    for r in recs:
        he, _ = resolver.resolve("openligadb", spec["competition_id"], r.home_raw)
        ae, _ = resolver.resolve("openligadb", spec["competition_id"], r.away_raw)
        key = (disp(he), disp(ae))
        if key not in wanted:
            continue
        d, gh, ga = wanted[key]
        st = conn.execute("SELECT record_id, match_date, status, home_goals_final, home_entity_id, away_entity_id FROM matches WHERE competition_id=? AND season=? AND home_entity_id=? AND away_entity_id=?", (spec["competition_id"], spec["season_label"], he, ae)).fetchall()
        if r.match_date != d:
            continue                                                       # a different date for this pairing: it is not the approved row (date-disputed results stay out)
        if len(st) != 1:
            problems.append(f"{key}: {len(st)} stored fixtures for the pairing")
            continue
        if (r.status, r.regulation_home, r.regulation_away, r.label_eligible_90min) != ("completed", gh, ga, True):
            problems.append(f"{key}: source says {r.status} {r.regulation_home}-{r.regulation_away}, approved {gh}-{ga}")
        if st[0]["match_date"] != d or st[0]["status"] != "scheduled" or st[0]["home_goals_final"] is not None:
            problems.append(f"{key}: stored row is {dict(st[0])}, expected an unplayed fixture dated {d}")
        found[key] = r
    missing = [k for k in wanted if k not in found]
    if missing:
        problems.append(f"approved rows not found in the snapshot: {missing}")
    if len(found) != len(wanted) or problems:
        raise Abort("; ".join(problems) or "allow-list mismatch")
    return list(found.values())


def apply_import(conn: sqlite3.Connection, step: str, meta: dict, payload: bytes, recs_all: list, expect_rows: int) -> dict:
    """ONE transaction: register the snapshot, open the run, ingest only the allow-listed records, check the outcome, commit. Raises (and rolls back) on any mismatch."""
    spec, key = STEPS[step]["spec"], STEPS[step]["key"]
    allowed = allow_list(step, recs_all, conn)
    ts = utc_now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        _, _, ol = sync._adapters()
        before_cnt = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in ("matches", "match_sources", "quarantine", "team_aliases", "forecasts", "forecast_runs")}
        conn.execute("INSERT OR IGNORE INTO source_snapshots(snapshot_id, source, kind, url, path, sha256, bytes, retrieved_utc, revision, licence, attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (meta["snapshot_id"], "openligadb", "json", STEPS[step]["url"], str((SNAPDIR / STEPS[step]["snapshot"]).relative_to(C.ROOT)), meta["sha256"], meta["bytes"], meta["retrieved_utc"], None, ol.LICENCE, ol.ATTRIBUTION))
        run_id = conn.execute("INSERT INTO sync_runs(kind, source, competition_key, started_utc, outcome) VALUES (?,?,?,?, 'running')", (f"p48d_import_{step}", "openligadb", key, ts)).lastrowid
        st = sync.ingest_records(conn, allowed, spec["competition_id"], key, spec["season_label"], run_id, meta["snapshot_id"], ts, protect_dates=True)
        if (st["inserted"], st["updated"], st["quarantined"], st["confirmed"]) != (0, expect_rows, 0, 0):
            raise Abort(f"unexpected ingestion result {st}")
        after_cnt = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in before_cnt}
        if after_cnt != before_cnt:
            raise Abort(f"row counts changed: {before_cnt} -> {after_cnt}")
        latest = conn.execute("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND status IN ('completed','awarded')", (key,)).fetchone()[0]
        conn.execute("UPDATE sync_runs SET finished_utc=?, outcome='ok', requests=0, inserted=?, updated=?, unchanged=?, quarantined=?, latest_result_date=?, detail=? WHERE run_id=?",
                     (utc_now(), st["inserted"], st["updated"], st["unchanged"], st["quarantined"], latest, json.dumps(dict(snapshot=meta["snapshot_id"], sha256=meta["sha256"], allow_list=[r.source_ref for r in allowed], approved="Phase 4.8D Stage 1")), run_id))
        conn.commit()
        return dict(run_id=run_id, stats=st, allowed_source_refs=[r.source_ref for r in allowed], started_utc=ts)
    except BaseException:
        conn.rollback()
        raise


def diff(before_path, after_path) -> dict:
    b = {r["record_id"]: r for r in rows(before_path, "SELECT * FROM matches")}
    a = {r["record_id"]: r for r in rows(after_path, "SELECT * FROM matches")}
    skip = {"last_changed_utc", "change_count", "content_hash"}
    ch = {}
    for rid, new in a.items():
        old = b.get(rid)
        if old is None:
            ch[rid] = {"(new row)": (None, new["status"])}
            continue
        f = {k: (old[k], new[k]) for k in new if k not in skip and new[k] != old[k]}
        if f:
            ch[rid] = f
    return dict(changed=ch, deleted=sorted(set(b) - set(a)))


def standings_and_form(path, key, season="2026-27"):
    t, form = {}, {}
    for r in rows(path, "SELECT m.match_date d, m.record_id rid, t1.display_name hn, t2.display_name an, m.home_goals_final gh, m.away_goals_final ga FROM matches m JOIN teams t1 ON t1.entity_id=m.home_entity_id JOIN teams t2 ON t2.entity_id=m.away_entity_id "
                  "WHERE m.competition_key=? AND m.season=? AND m.status IN ('completed','awarded') AND m.home_goals_final IS NOT NULL ORDER BY m.match_date, m.record_id", key, season):
        for team, gf, ga in ((r["hn"], r["gh"], r["ga"]), (r["an"], r["ga"], r["gh"])):
            x = t.setdefault(team, dict(played=0, points=0, gf=0, ga=0))
            x["played"] += 1
            x["gf"] += gf
            x["ga"] += ga
            x["points"] += 3 if gf > ga else 1 if gf == ga else 0
            form.setdefault(team, []).append("W" if gf > ga else "D" if gf == ga else "L")
    order = sorted(t, key=lambda k: (-t[k]["points"], -(t[k]["gf"] - t[k]["ga"]), -t[k]["gf"], k))
    return {k: dict(t[k], gd=t[k]["gf"] - t[k]["ga"], rank=order.index(k) + 1, last5="".join(form[k][-5:])) for k in t}


def verify(step: str, before: Path, after: Path, run_id: int, meta: dict, allowed_refs: list, expect_rows: int) -> dict:
    d = diff(before, after)
    keys = STEPS[step]["key"]
    problems = []
    if len(d["changed"]) != expect_rows or d["deleted"]:
        problems.append(f"changed rows {len(d['changed'])} (expected {expect_rows}), deleted {len(d['deleted'])}")
    for rid, f in d["changed"].items():
        if not set(f) <= EXPECTED_FIELDS:
            problems.append(f"{rid}: unexpected fields {sorted(set(f) - EXPECTED_FIELDS)}")
    lg = baseline_hash.logical(after, run_id)
    tb = baseline_hash.logical(before, run_id)["tables"]
    changed_tables = sorted(t for t in lg["tables"] if lg["tables"][t]["sha256"] != tb[t]["sha256"])
    # tables allowed to change: matches, match_sources (the provenance upgrade), source_snapshots (+1), sync_runs (+1)
    if not set(changed_tables) <= {"matches", "match_sources", "source_snapshots", "sync_runs"}:
        problems.append(f"unexpected tables changed: {changed_tables}")
    src_before = {(r["source"], r["source_ref"]): r for r in rows(before, "SELECT * FROM match_sources")}
    src_after = {(r["source"], r["source_ref"]): r for r in rows(after, "SELECT * FROM match_sources")}
    changed_links = {k: (src_before.get(k), v) for k, v in src_after.items() if src_before.get(k) != v}
    links_ok = all(k[0] == "openligadb" and k[1] in allowed_refs and v[0] is not None and v[0]["role"] == "confirmation" and v[1]["role"] == "primary" and v[1]["snapshot_id"] == meta["snapshot_id"] and v[0]["provenance"] in v[1]["provenance"]
                   for k, v in changed_links.items()) and len(changed_links) == expect_rows and set(src_before) <= set(src_after) and len(src_after) == len(src_before)
    if not links_ok:
        problems.append(f"provenance links not as expected: {list(changed_links)}")
    c = sqlite3.connect(after)
    integ = dict(integrity_check=c.execute("PRAGMA integrity_check").fetchone()[0], foreign_key_check=len(c.execute("PRAGMA foreign_key_check").fetchall()),
                 forecasts=c.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0], forecast_runs=c.execute("SELECT COUNT(*) FROM forecast_runs").fetchone()[0], simulation_runs=c.execute("SELECT COUNT(*) FROM simulation_runs").fetchone()[0],
                 quarantine=c.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0], team_aliases=c.execute("SELECT COUNT(*) FROM team_aliases").fetchone()[0], matches=c.execute("SELECT COUNT(*) FROM matches").fetchone()[0])
    c.close()
    if integ["integrity_check"] != "ok" or integ["foreign_key_check"] or integ["forecasts"] or integ["quarantine"] != 273 or integ["matches"] != 223510:
        problems.append(f"integrity/count check failed: {integ}")
    sb, sa = standings_and_form(before, keys), standings_and_form(after, keys)
    return dict(problems=problems, row_changes=d["changed"], tables_changed=changed_tables, links_changed={f"{k[0]}:{k[1]}": dict(before=v[0], after=v[1]) for k, v in changed_links.items()}, integrity=integ,
                standings={t: dict(before=sb.get(t), after=sa[t]) for t in sa if sa[t] != sb.get(t)}, logical_sha256=lg["logical_sha256"], physical_sha256=baseline_hash.physical_sha256(after))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, choices=list(STEPS))
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    step = a.step
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(step=step, started_utc=utc_now(), execute=a.execute)
    try:
        prev = previous_state(step)
        report["preconditions"] = preconditions(step)
        report["backup"] = backup(step, prev)
        meta, payload, recs = parse(step)
        expect_rows = len(STEPS[step]["expected"])
        # reconcile on the RESTORED private copy: exactly the same code path as production
        trial = OUT / f"reconcile_trial_{step}.sqlite"
        trial.unlink(missing_ok=True)
        shutil.copyfile(report["backup"]["restored_path"], trial)
        tc = db.connect(trial)
        tc.execute("PRAGMA journal_mode=DELETE")
        res = apply_import(tc, step, meta, payload, recs, expect_rows)
        tc.close()
        rv = verify(step, Path(report["backup"]["restored_path"]), trial, res["run_id"], meta, res["allowed_source_refs"], expect_rows)
        report["reconciliation_on_private_copy"] = dict(import_result=res, verification=rv)
        if rv["problems"]:
            raise Abort("reconciliation on the private copy found: " + "; ".join(rv["problems"]))
        if not a.execute:
            report["result"] = "checks and reconciliation passed; production NOT touched (no --execute)"
        else:
            conn = db.connect(PROD)
            try:
                res = apply_import(conn, step, meta, payload, recs, expect_rows)
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            finally:
                conn.close()
            rv = verify(step, Path(report["backup"]["restored_path"]), PROD, res["run_id"], meta, res["allowed_source_refs"], expect_rows)
            lg = baseline_hash.logical(PROD, res["run_id"])
            report["production_import"] = dict(import_result=res, verification=rv)
            report["after"] = dict(physical_sha256=baseline_hash.physical_sha256(PROD), logical_sha256=lg["logical_sha256"], last_baseline_run_id=res["run_id"], tables=lg["tables"], excluded_rows=lg["excluded_rows"],
                                   journal_mode=lg["journal_mode"], integrity_check=lg["integrity_check"])
            report["result"] = "IMPORTED" if not rv["problems"] else "IMPORTED BUT VERIFICATION FAILED: restore the backup"
            (OUT / f"checkpoint_{step}.json").write_text(json.dumps(report, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    except Abort as exc:
        report["result"] = f"ABORTED: {exc}"
    report["finished_utc"] = utc_now()
    (OUT / f"report_{step}{'_execute' if a.execute else '_check'}.json").write_text(json.dumps(report, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k in ("step", "execute", "result", "started_utc", "finished_utc")}, indent=1))
    if "preconditions" in report:
        print({k: v for k, v in report["preconditions"].items() if k in ("physical_matches_record", "logical_matches_record", "integrity_check", "git_staged", "git_head", "live_enabled", "application_processes", "exclusive_lock_available", "snapshot_matches_record", "failed")})
    if "backup" in report:
        print("backup:", report["backup"]["path"], "restore ok:", report["backup"]["restore"])
    if "reconciliation_on_private_copy" in report:
        v = report["reconciliation_on_private_copy"]["verification"]
        print("trial:", report["reconciliation_on_private_copy"]["import_result"]["stats"], "problems:", v["problems"], "tables:", v["tables_changed"], "rows:", {k: sorted(f) for k, f in v["row_changes"].items()})
    return 0 if str(report["result"]).startswith(("IMPORTED", "checks")) and "FAILED" not in report["result"] else 1


if __name__ == "__main__":
    sys.exit(main())
