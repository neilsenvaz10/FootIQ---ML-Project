"""Phase 4.8C Stage 2: full reconciliation of the Premier League and La Liga snapshots (A2/A3) against a PRIVATE COPY of production. No network, no production write.
Proposed import = ingest with date protection (the live path since 4.8C). Output: stage2_reconciliation.json and stage2_proposed_diff.csv."""
import csv
import json
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "app" / "store"))
from store import baseline_hash, db, sync  # noqa: E402

SNAP = ROOT / "data" / "snapshots" / "p48c"
OUT = ROOT / "data" / "supervised" / "phase4" / "p48c"
PROD = ROOT / "data" / "footiq.sqlite"
SEASON = "2026-27"
KEYS = {"pl": ("EPL", sync.OFFLINE_PREPARED["EPL"]), "la1": ("LALIGA", sync.OFFLINE_PREPARED["LALIGA"])}
NOW = datetime(2026, 10, 27, 13, 5, tzinfo=timezone.utc)


def latest(k):
    p = sorted((SNAP / "openligadb").glob(f"*_p48c_{k}.json"))[-1]
    return p, json.loads((p.parent / (p.name + ".meta.json")).read_text(encoding="utf-8"))


def table(conn, key):
    t = {}
    for r in conn.execute("SELECT home_entity_id h, away_entity_id a, home_name hn, away_name an, home_goals_final gh, away_goals_final ga FROM matches WHERE competition_key=? AND season=? AND status IN ('completed','awarded') AND home_goals_final IS NOT NULL", (key, SEASON)):
        for ent, name, gf, ga in ((r["h"], r["hn"], r["gh"], r["ga"]), (r["a"], r["an"], r["ga"], r["gh"])):
            x = t.setdefault(ent, dict(team=name, played=0, points=0, gf=0, ga=0))
            x["played"] += 1
            x["gf"] += gf
            x["ga"] += ga
            x["points"] += 3 if gf > ga else 1 if gf == ga else 0
    return t


def form(conn, key, ent):
    rows = conn.execute("SELECT match_date d, home_entity_id h, home_goals_final gh, away_goals_final ga FROM matches WHERE competition_key=? AND season=? AND status IN ('completed','awarded') AND home_goals_final IS NOT NULL AND (home_entity_id=? OR away_entity_id=?) ORDER BY match_date, record_id", (key, SEASON, ent, ent)).fetchall()
    out = []
    for r in rows[-5:]:
        gf, ga = (r["gh"], r["ga"]) if r["h"] == ent else (r["ga"], r["gh"])
        out.append("W" if gf > ga else "D" if gf == ga else "L")
    return "".join(out)


def main():
    work = OUT / "work_stage2"
    work.mkdir(parents=True, exist_ok=True)
    cp = work / "copy.sqlite"
    for e in ("", "-wal", "-shm"):
        Path(str(cp) + e).unlink(missing_ok=True)
        if Path(str(PROD) + e).exists():
            shutil.copyfile(str(PROD) + e, str(cp) + e)
    c0 = sqlite3.connect(cp)
    c0.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c0.execute("PRAGMA journal_mode=DELETE")
    c0.close()
    prod_before = baseline_hash.physical_sha256(PROD)
    b = sqlite3.connect(cp)
    b.row_factory = sqlite3.Row
    before_rows = {r["record_id"]: dict(r) for r in b.execute("SELECT * FROM matches")}
    before_q = {(r["source"], r["source_ref"], r["reason"]) for r in b.execute("SELECT source, source_ref, reason FROM quarantine")}
    st_before = {k: table(b, KEYS[k][0]) for k in KEYS}
    form_before = {k: {e: form(b, KEYS[k][0], e) for e in st_before[k]} for k in KEYS}
    resolver = sync.build_resolver(b)
    rep = dict(generated_utc=sync.now_utc(), leagues={})
    snaps = {}
    _, _, ol = sync._adapters()
    for k, (key, spec) in KEYS.items():
        p, meta = latest(k)
        snaps[k] = (p, meta)
        raw = json.loads(p.read_bytes())
        recs = ol.parse_payload(p.read_bytes(), meta["saved_utc"], meta["snapshot_id"], NOW, spec["competition_id"])
        names = sorted({r.home_raw for r in recs} | {r.away_raw for r in recs})
        ident = {}
        for n in names:
            e, how = resolver.resolve("openligadb", spec["competition_id"], n)
            ident[n] = dict(entity=e, method=how)
        pairs = Counter((m["team1"]["teamName"], m["team2"]["teamName"]) for m in raw)
        fin = [m for m in raw if m["matchIsFinished"]]
        past_unfinished = [m for m in raw if not m["matchIsFinished"] and m["matchDateTimeUTC"] < NOW.strftime("%Y-%m-%dT%H:%M:%SZ")]
        rep["leagues"][k] = dict(
            competition=key, snapshot=p.name, sha256=meta["sha256"], bytes=meta["bytes"], retrieved_utc=meta["retrieved_utc"], http_status=meta["status"],
            total_fixtures=len(raw), matchdays=len({m["group"]["groupOrderID"] for m in raw}), teams=len(names), finished=len(fin), source_statuses=dict(Counter(r.status for r in recs)),
            identity=dict(unresolved=[n for n, v in ident.items() if not v["entity"]], methods=dict(Counter(str(v["method"]) for v in ident.values())),
                          entities_used_twice=[e for e, c in Counter(v["entity"] for v in ident.values() if v["entity"]).items() if c > 1]),
            duplicates=dict(duplicate_matchids=len(raw) - len({m["matchID"] for m in raw}), duplicate_ordered_pairs=sum(1 for v in pairs.values() if v > 1)),
            source_past_date_without_result=len(past_unfinished),
            source_finished_without_final_result=[m["matchID"] for m in fin if not any(r["resultTypeID"] == 2 for r in (m["matchResults"] or []))])
    b.close()
    original, sync.now_utc = sync.now_utc, (lambda: "2026-10-27T13:05:00Z")
    try:
        conn = db.connect(cp)
        for k, (key, spec) in KEYS.items():
            p, meta = snaps[k]
            now = datetime.strptime(meta["saved_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            res = sync.replay_payload(conn, p.read_bytes(), key, retrieved_utc=meta["saved_utc"], now=now, kind="p48c_dry_run", spec=spec, snapshot_id=meta["snapshot_id"],
                                      url=f"https://api.openligadb.de/getmatchdata/{k}/2026", path=str(p), protect_dates=True)
            rep["leagues"][k]["reconciliation"] = {x: res.get(x, 0) for x in ("inserted", "updated", "unchanged", "confirmed", "quarantined", "held_date_difference")}
        again = {k: sync.replay_payload(conn, snaps[k][0].read_bytes(), KEYS[k][0], retrieved_utc=snaps[k][1]["saved_utc"], now=NOW, kind="p48c_dry_run_repeat", spec=KEYS[k][1],
                                        snapshot_id=snaps[k][1]["snapshot_id"], protect_dates=True) for k in KEYS}
        conn.close()
    finally:
        sync.now_utc = original
    a = sqlite3.connect(cp)
    a.row_factory = sqlite3.Row
    after_rows = {r["record_id"]: dict(r) for r in a.execute("SELECT * FROM matches")}
    skip = {"last_changed_utc", "change_count", "content_hash"}
    diff = []
    for rid, new in after_rows.items():
        old = before_rows.get(rid)
        if old is None:
            diff.append(dict(record_id=rid, competition=new["competition_key"], home=new["home_name"], away=new["away_name"], match_date=new["match_date"], field="(new row)", before="", after=new["status"]))
            continue
        for f in (f for f in new if f not in skip and new[f] != old[f]):
            diff.append(dict(record_id=rid, competition=new["competition_key"], home=new["home_name"], away=new["away_name"], match_date=old["match_date"], field=f, before=old[f], after=new[f]))
    with open(OUT / "stage2_proposed_diff.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["record_id", "competition", "home", "away", "match_date", "field", "before", "after"])
        w.writeheader()
        w.writerows(diff)
    after_q = {(r["source"], r["source_ref"], r["reason"]) for r in a.execute("SELECT source, source_ref, reason FROM quarantine")}
    rep["quarantine"] = dict(before=len(before_q), after=len(after_q), new_findings=len(after_q - before_q), removed=len(before_q - after_q),
                             date_difference_total=sum(1 for q in after_q if q[2].startswith("DATE_DIFFERENCE")), score_conflicts=sorted(q[2][:90] for q in after_q if q[2].startswith(("CONFLICT", "CONTRADICTORY"))))
    for k, (key, spec) in KEYS.items():
        L = rep["leagues"][k]
        ch = [d for d in diff if d["competition"] == key]
        newly = sorted({(d["home"], d["away"], d["match_date"]) for d in ch if d["field"] == "status" and d["after"] == "completed"})
        sc = lambda h, aw, d: a.execute("SELECT home_goals_final, away_goals_final FROM matches WHERE competition_key=? AND home_name=? AND away_name=? AND match_date=?", (key, h, aw, d)).fetchone()  # noqa: E731
        L["newly_available_results"] = [dict(home=h, away=aw, date=d, score="%s-%s" % tuple(sc(h, aw, d))) for h, aw, d in newly]
        L["status_only_changes_scheduled_to_awaiting"] = sum(1 for d in ch if d["field"] == "status" and d["after"] == "awaiting_result")
        L["row_changes_by_field"] = dict(Counter(d["field"] for d in ch))
        L["rows_changed"] = len({d["record_id"] for d in ch})
        L["dates_changed"] = sum(1 for d in ch if d["field"] == "match_date")
        L["scores_overwritten"] = sum(1 for d in ch if d["field"] in ("home_goals_final", "away_goals_final") and d["before"] not in (None, ""))
        L["repeat_import"] = {x: again[k].get(x, 0) for x in ("inserted", "updated", "unchanged", "confirmed", "quarantined")}
        aw = a.execute("SELECT COUNT(*), MIN(match_date) FROM matches WHERE competition_key=? AND season=? AND status='awaiting_result'", (key, SEASON)).fetchone()
        L["store_after_import"] = dict(completed=a.execute("SELECT COUNT(*) FROM matches WHERE competition_key=? AND season=? AND status='completed'", (key, SEASON)).fetchone()[0],
                                       awaiting_result=aw[0], oldest_awaiting=aw[1],
                                       newest_result=a.execute("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND season=? AND status='completed'", (key, SEASON)).fetchone()[0])
        sb, sa = st_before[k], table(a, key)
        L["standings_changes"] = [dict(team=sa[e]["team"], played=[sb.get(e, {}).get("played", 0), sa[e]["played"]], points=[sb.get(e, {}).get("points", 0), sa[e]["points"]],
                                       gd=[sb.get(e, {"gf": 0, "ga": 0})["gf"] - sb.get(e, {"gf": 0, "ga": 0})["ga"], sa[e]["gf"] - sa[e]["ga"]]) for e in sa if sa[e] != sb.get(e)]
        L["form_changes"] = [dict(team=sa[e]["team"], last5_before=form_before[k].get(e, ""), last5_after=form(a, key, e)) for e in sa if form(a, key, e) != form_before[k].get(e, "")]
    fr = {c["competition_key"]: c for c in sync.status(a, sync.SyncConfig(), NOW)["competitions"]}
    for k, (key, _) in KEYS.items():
        c = fr[key]
        rep["leagues"][k]["freshness_after_import"] = {x: c[x] for x in ("state", "state_reasons", "latest_result", "awaiting_result", "last_successful_external_check_utc", "last_successful_import_utc", "last_import_kind", "provider_readiness", "history_note")}
    rep["integrity_of_copy"] = dict(integrity_check=a.execute("PRAGMA integrity_check").fetchone()[0], foreign_key_check=len(a.execute("PRAGMA foreign_key_check").fetchall()),
                                    matches_before=len(before_rows), matches_after=len(after_rows), rows_deleted=len(set(before_rows) - set(after_rows)))
    a.close()
    rep["production_sha256_before"], rep["production_sha256_after"] = prod_before, baseline_hash.physical_sha256(PROD)
    rep["production_untouched"] = prod_before == rep["production_sha256_after"]
    (OUT / "stage2_reconciliation.json").write_text(json.dumps(rep, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(rep, indent=1, default=str, ensure_ascii=False)[:11000])


if __name__ == "__main__":
    main()
