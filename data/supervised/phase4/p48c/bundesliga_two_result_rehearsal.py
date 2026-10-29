"""Phase 4.8C: rehearsal of importing the two newly verified Bundesliga results (A1 snapshot) into a PRIVATE COPY of production. No network; production is only file-copied.

Hoffenheim 3-0 Leverkusen and Freiburg 1-3 Bayern (both 2026-10-25). Checks: row-level changes, provenance, standings, form, prediction features, saved forecast immutability,
repeat import, database integrity, rollback (transaction and file level). Output: bundesliga_rehearsal.json.
"""
import json
import shutil
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
for p in (str(ROOT / "FootIQ_Club_Model_Development_v2" / "_scripts"), str(ROOT / "FootIQ_ML_Training_Preparation" / "_build")):
    sys.path.insert(0, p)
import analytics  # noqa: E402
import forecast  # noqa: E402
import predict  # noqa: E402
from store import baseline_hash, db, sync  # noqa: E402

PROD = ROOT / "data" / "footiq.sqlite"
OUT = ROOT / "data" / "supervised" / "phase4" / "p48c"
SNAP = sorted((ROOT / "data" / "snapshots" / "p48c" / "openligadb").glob("*_p48c_bl1.json"))[-1]
META = json.loads((SNAP.parent / (SNAP.name + ".meta.json")).read_text(encoding="utf-8"))
KEY, SEASON = "BUNDESLIGA", "2026-27"
STAMP = "2026-10-27T13:10:00Z"
NOW = datetime(2026, 10, 27, 13, 10, tzinfo=timezone.utc)
TEAMS = {"Hoffenheim": "TSG 1899 Hoffenheim", "Leverkusen": "Bayer 04 Leverkusen", "Freiburg": "SC Freiburg", "Bayern": "FC Bayern München"}


def rows(path, sql, *a):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in c.execute(sql, a)]
    finally:
        c.close()


def standings(path):
    t = {}
    for r in rows(path, "SELECT t1.display_name hn, t2.display_name an, m.home_goals_final gh, m.away_goals_final ga FROM matches m JOIN teams t1 ON t1.entity_id=m.home_entity_id JOIN teams t2 ON t2.entity_id=m.away_entity_id "
                  "WHERE m.competition_key=? AND m.season=? AND m.status IN ('completed','awarded') AND m.home_goals_final IS NOT NULL", KEY, SEASON):
        for team, gf, ga in ((r["hn"], r["gh"], r["ga"]), (r["an"], r["ga"], r["gh"])):
            x = t.setdefault(team, dict(played=0, points=0, gf=0, ga=0))
            x["played"] += 1; x["gf"] += gf; x["ga"] += ga; x["points"] += 3 if gf > ga else 1 if gf == ga else 0
    order = sorted(t, key=lambda k: (-t[k]["points"], -(t[k]["gf"] - t[k]["ga"]), -t[k]["gf"], k))
    return {k: dict(t[k], gd=t[k]["gf"] - t[k]["ga"], rank=order.index(k) + 1) for k in t}


def form5(path, team):
    rs = rows(path, "SELECT m.match_date d, t1.display_name hn, m.home_goals_final gh, m.away_goals_final ga FROM matches m JOIN teams t1 ON t1.entity_id=m.home_entity_id JOIN teams t2 ON t2.entity_id=m.away_entity_id "
              "WHERE m.competition_key=? AND m.season=? AND m.status IN ('completed','awarded') AND m.home_goals_final IS NOT NULL AND (t1.display_name=? OR t2.display_name=?) ORDER BY m.match_date, m.record_id", KEY, SEASON, team, team)
    s = ""
    for r in rs[-5:]:
        gf, ga = (r["gh"], r["ga"]) if r["hn"] == team else (r["ga"], r["gh"])
        s += "W" if gf > ga else "D" if gf == ga else "L"
    return s


import time
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def main():
    work = OUT / "work_bl"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    cp, backup = work / "copy.sqlite", work / "pre_import_backup.sqlite"
    for e in ("", "-wal", "-shm"):
        if Path(str(PROD) + e).exists():
            shutil.copyfile(str(PROD) + e, str(cp) + e)
    c = sqlite3.connect(cp)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.execute("PRAGMA journal_mode=DELETE")
    c.close()
    prod_before = baseline_hash.physical_sha256(PROD)
    rec = json.loads((OUT / "db_baseline_v2.json").read_text(encoding="utf-8"))
    pre = baseline_hash.logical(cp)
    rep = dict(snapshot=SNAP.name, snapshot_sha256=META["sha256"], production_sha256_before=prod_before,
               copy_logical_equals_recorded_baseline=(pre["logical_sha256"] == rec["logical_sha256"]))
    shutil.copyfile(cp, backup)                                                    # file-level rollback point
    log('pre-import hashes done')
    st0 = standings(cp)
    f0 = {t: form5(cp, n) for t, n in TEAMS.items()}

    # --- forecasts saved BEFORE the import, on the copy (matchday 8 as of now)
    db.DEFAULT_PATH = cp
    analytics.reload()
    predict.reset_club_state()
    c = db.connect(cp, readonly=True)
    from datetime import date as _d
    import gameweeks as gw
    md = max(r["matchday_no"] for r in rows(cp, "SELECT matchday_no FROM matches WHERE competition_key=? AND season=? AND status IN ('completed','awarded')", KEY, SEASON)) + 1
    c.close()
    r1 = forecast.predict_gameweek(KEY, SEASON, md, forecast.EXPLICIT_ACTION, now=NOW, today=NOW.date(), db_path=cp)
    log('first forecast run saved')
    saved_before = rows(cp, "SELECT * FROM forecasts ORDER BY forecast_id")
    rep["forecast_matchday"] = md

    # --- the import (the whole A1 snapshot through the live-path ingestion; only the two results can change)
    original, sync.now_utc = sync.now_utc, (lambda: STAMP)
    before_rows = {r["record_id"]: r for r in rows(cp, "SELECT * FROM matches")}
    before_src = rows(cp, "SELECT * FROM match_sources")
    before_tables = baseline_hash.logical(cp)["tables"]
    try:
        conn = db.connect(cp)
        res = sync.replay_payload(conn, SNAP.read_bytes(), KEY, retrieved_utc=META["saved_utc"], now=datetime.strptime(META["saved_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc),
                                  kind="p48c_bundesliga_rehearsal", snapshot_id=META["snapshot_id"], url=META["url"], path=str(SNAP), protect_dates=True)
        conn.close()
    finally:
        sync.now_utc = original
    log('import done')
    rep["import_result"] = {k: res[k] for k in ("inserted", "updated", "unchanged", "confirmed", "quarantined", "records")}
    after_rows = {r["record_id"]: r for r in rows(cp, "SELECT * FROM matches")}
    skip = {"last_changed_utc", "change_count", "content_hash"}
    changes = []
    for rid, new in after_rows.items():
        old = before_rows.get(rid)
        if old is None:
            changes.append(dict(record_id=rid, field="(new row)"))
            continue
        for f in (f for f in new if f not in skip and new[f] != old[f]):
            changes.append(dict(record_id=rid, home=new["home_name"], away=new["away_name"], date=old["match_date"], field=f, before=old[f], after=new[f]))
    rep["row_level_changes"] = changes
    rep["rows_changed"] = len({c["record_id"] for c in changes})
    rep["rows_total_before_after"] = [len(before_rows), len(after_rows)]
    ids = {c["record_id"] for c in changes}
    before_keys = {(b["source"], b["source_ref"], b["record_id"], b["role"]) for b in before_src}
    rep["provenance"] = dict(
        new_match_sources_rows=[r for r in rows(cp, "SELECT source, source_ref, record_id, role, snapshot_id, licence, retrieved_utc, provenance FROM match_sources") if (r["source"], r["source_ref"], r["record_id"], r["role"]) not in before_keys],
        match_sources_for_changed_rows=rows(cp, f"SELECT source, source_ref, role, snapshot_id, licence FROM match_sources WHERE record_id IN ({','.join('?' * len(ids))}) ORDER BY record_id, role", *sorted(ids)),
        snapshot_registered=rows(cp, "SELECT snapshot_id, sha256, bytes, retrieved_utc, licence FROM source_snapshots WHERE snapshot_id=?", META["snapshot_id"]),
        sync_runs_added=rows(cp, "SELECT run_id, kind, source, competition_key, outcome, requests, inserted, updated, unchanged, quarantined FROM sync_runs WHERE run_id>8"))
    after_tables = baseline_hash.logical(cp)["tables"]
    rep["tables_changed"] = {t: [before_tables[t]["rows"], after_tables[t]["rows"]] for t in after_tables if after_tables[t]["sha256"] != before_tables[t]["sha256"]}

    log('diff + provenance done')
    # --- standings and form
    st1 = standings(cp)
    rep["standings_changes"] = {t: dict(before=st0.get(t), after=st1[t]) for t in st1 if st1[t] != st0.get(t)}
    rep["form_changes"] = {n: [f0[t], form5(cp, n)] for t, n in TEAMS.items()}

    # --- predictions: the same gameweek again after the import; saved rows must be unchanged
    analytics.reload()
    predict.reset_club_state()
    r2 = forecast.predict_gameweek(KEY, SEASON, md, forecast.EXPLICIT_ACTION, now=NOW, today=NOW.date(), db_path=cp)
    after_saved = rows(cp, "SELECT * FROM forecasts ORDER BY forecast_id")
    rep["saved_forecasts_immutable"] = after_saved[: len(saved_before)] == saved_before
    rep["forecast_runs"] = [r1["forecast_run_id"], r2["forecast_run_id"]]
    rep["cutoff_before_after"] = [r1["data_cutoff_date"], r2["data_cutoff_date"]]
    feat = lambda run, rid, var: json.loads(rows(cp, "SELECT feature_snapshot_json s FROM forecasts WHERE forecast_run_id=? AND record_id=? AND model_variant=?", run, rid, var)[0]["s"])  # noqa: E731
    pred_changes = []
    for fx in r2["forecasts"]:
        old = next(x for x in r1["forecasts"] if x["record_id"] == fx["record_id"])
        a1, b1 = feat(r1["forecast_run_id"], fx["record_id"], "club_v1"), feat(r2["forecast_run_id"], fx["record_id"], "club_v1")
        a2, b2 = feat(r1["forecast_run_id"], fx["record_id"], "club_v2_r1"), feat(r2["forecast_run_id"], fx["record_id"], "club_v2_r1")
        pred_changes.append(dict(fixture=f"{fx['home']} v {fx['away']}", date=fx["date"], v1_schema_identical=sorted(a1) == sorted(b1), v2_schema_identical=sorted(a2) == sorted(b2), v1_inputs=len(a1), v2_inputs=len(a2),
                                 v1_inputs_changed=sum(1 for k in a1 if a1[k] != b1[k]), v2_inputs_changed=sum(1 for k in a2 if a2[k] != b2[k]),
                                 v1_before=[round(x, 4) for x in old["predictions"]["primary"].values()], v1_after=[round(x, 4) for x in fx["predictions"]["primary"].values()],
                                 v2_before=[round(x, 4) for x in old["predictions"]["secondary"].values()], v2_after=[round(x, 4) for x in fx["predictions"]["secondary"].values()],
                                 involves_changed_teams=any(n in (fx["home"], fx["away"]) for n in TEAMS.values())))
    rep["prediction_changes"] = pred_changes

    log('second forecast run done')
    # --- repeat import: duplicate-free
    h_before = baseline_hash.logical(cp)["tables"]
    sync.now_utc = lambda: "2026-10-27T13:11:00Z"
    try:
        conn = db.connect(cp)
        res2 = sync.replay_payload(conn, SNAP.read_bytes(), KEY, retrieved_utc=META["saved_utc"], now=datetime.strptime(META["saved_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc),
                                   kind="p48c_bundesliga_rehearsal_repeat", snapshot_id=META["snapshot_id"], url=META["url"], path=str(SNAP), protect_dates=True)
        conn.close()
    finally:
        sync.now_utc = original
    h_after = baseline_hash.logical(cp)["tables"]
    rep["repeat_import"] = dict(result={k: res2[k] for k in ("inserted", "updated", "unchanged", "confirmed", "quarantined")},
                                tables_changed=[t for t in h_after if h_after[t] != h_before[t]],                      # only the diary (sync_runs) may differ
                                duplicate_record_ids=rows(cp, "SELECT COUNT(*) - COUNT(DISTINCT record_id) n FROM matches")[0]["n"],
                                duplicate_source_links=rows(cp, "SELECT COUNT(*) - COUNT(DISTINCT source || '|' || source_ref || '|' || record_id || '|' || role) n FROM match_sources")[0]["n"])

    log('repeat import done')
    # --- integrity and rollback
    c = sqlite3.connect(cp)
    rep["integrity"] = dict(integrity_check=c.execute("PRAGMA integrity_check").fetchone()[0], foreign_key_check=len(c.execute("PRAGMA foreign_key_check").fetchall()))
    c.close()
    # (a) transaction rollback: a failure inside an import leaves the data untouched
    tmp = work / "tx.sqlite"
    shutil.copyfile(backup, tmp)
    tx_before = baseline_hash.logical(tmp)["logical_sha256"]
    conn = db.connect(tmp)
    _, _, ol = sync._adapters()
    recs = ol.parse_payload(SNAP.read_bytes(), META["saved_utc"], META["snapshot_id"], NOW, sync.APPROVED[KEY]["competition_id"])
    conn.execute("BEGIN")
    rid = conn.execute("INSERT INTO sync_runs(kind, source, competition_key, started_utc, outcome) VALUES ('p48c_tx_test','openligadb',?,?, 'running')", (KEY, STAMP)).lastrowid
    st = sync.ingest_records(conn, recs, sync.APPROVED[KEY]["competition_id"], KEY, SEASON, rid, META["snapshot_id"], STAMP, protect_dates=True)
    inside = st["updated"]
    conn.rollback()
    conn.close()
    tx_after = baseline_hash.logical(tmp)["logical_sha256"]
    # (b) file-level rollback to the pre-import backup
    shutil.copyfile(backup, cp)
    rep["rollback"] = dict(transaction=dict(updates_inside_the_transaction=inside, logical_hash_unchanged_after_rollback=(tx_before == tx_after)),
                           file_restore=dict(restored_logical_equals_recorded_baseline=(baseline_hash.logical(cp)["logical_sha256"] == rec["logical_sha256"])))
    rep["production_sha256_after"] = baseline_hash.physical_sha256(PROD)
    rep["production_untouched"] = rep["production_sha256_after"] == prod_before
    (OUT / "bundesliga_rehearsal.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    db.DEFAULT_PATH = PROD
    analytics.reload()
    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({k: rep[k] for k in rep if k not in ("prediction_changes", "provenance", "row_level_changes")}, indent=1, default=str, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    main()
