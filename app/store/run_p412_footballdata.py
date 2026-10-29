"""Phase 4.12: supervised, read-only validation of football-data.org (PL, SA, FL1; season 2026). A one-shot tool, not a scheduler.

    python app/store/run_p412_footballdata.py        at most THREE authenticated GETs (one per league, no retry, these exact URLs once each) into a PRIVATE COPY of production.

Production is opened read-only and its file hash is compared before and after. The token is read from FOOTBALL_DATA_API_TOKEN, is never printed, logged or stored, and is scrubbed from every text this tool
writes. The response bodies are kept in memory so that even a rejected answer can be analysed; a rejected body is saved under data/supervised/phase4/p412/rejected/ (it contains no token).
"""
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from store import baseline_hash, db, footballdata as fd, sync  # noqa: E402

PROD = C.ROOT / "data" / "footiq.sqlite"
OUT = C.ROOT / "data" / "supervised" / "phase4" / "p412"
LEDGER = C.ROOT / "data" / "snapshots" / "request_ledger.jsonl"
ORDER = ["EPL", "SERIEA", "LIGUE1"]
URLS = {k: f"{fd.BASE}/competitions/{fd.LEAGUES[k][0]}/matches?season=2026" for k in ORDER}


class Abort(Exception):
    pass


def ro(path):
    c = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def ledger_lines():
    return len(LEDGER.read_text(encoding="utf-8").splitlines()) if LEDGER.exists() else 0


def analyse(key, body, now):
    """Facts about one answer, compared with production (read-only)."""
    code, comp_id = fd.LEAGUES[key]
    out = {}
    try:
        data = json.loads(body)
    except ValueError:
        return dict(parse_error="not JSON", bytes=len(body))
    ms = data.get("matches") if isinstance(data, dict) else None
    if not isinstance(ms, list):
        return dict(no_match_list=True, top_level_keys=sorted(data)[:10] if isinstance(data, dict) else None, message=str(data.get("message"))[:200] if isinstance(data, dict) else None)
    rs, season = data.get("resultSet") or {}, (ms[0].get("season") if ms else {}) or {}
    fin = [m for m in ms if m.get("status") == "FINISHED"]
    past = [m for m in ms if m.get("status") in ("SCHEDULED", "TIMED") and (m.get("utcDate") or "9") < (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")]
    statuses = {}
    for m in ms:
        statuses[m.get("status")] = statuses.get(m.get("status"), 0) + 1
    out.update(competition_code=(data.get("competition") or {}).get("code"), filters=data.get("filters"), result_set=rs, matches=len(ms), statuses=statuses, season_start=season.get("startDate"), season_end=season.get("endDate"),
               current_matchday=season.get("currentMatchday"), finished=len(fin), newest_finished_utc=max((m["utcDate"] for m in fin), default=None),
               unfinished_past_their_date=len(past), oldest_unfinished_past=min((m["utcDate"] for m in past), default=None), provider_newest_lastUpdated=max((m.get("lastUpdated") or "" for m in ms), default=None),
               duration_values=sorted({(m.get("score") or {}).get("duration") for m in fin} - {None}), has_regularTime=sum(1 for m in fin if (m.get("score") or {}).get("regularTime")),
               distinct_teams=len({(m["homeTeam"] or {}).get("name") for m in ms}), matchdays=len({m.get("matchday") for m in ms}), unknown_statuses=sorted(set(statuses) - {"SCHEDULED", "TIMED", "FINISHED", "IN_PLAY", "PAUSED", "POSTPONED", "SUSPENDED", "CANCELLED", "AWARDED"}))
    try:
        fd.validate_payload(body, code)
        out["adapter_validation"] = "accepted"
    except Exception as exc:  # noqa: BLE001
        out["adapter_validation"] = f"REJECTED: {type(exc).__name__}: {exc}"[:300]
    # ---- against production
    pc = ro(PROD)
    resolver = sync.build_resolver(pc)
    out["identity"] = fd.identity_report(body, resolver, comp_id)
    stored = {}
    for r in pc.execute("SELECT * FROM matches WHERE competition_key=? AND season='2026-27'", (key,)):
        stored.setdefault((r["home_entity_id"], r["away_entity_id"]), []).append(dict(r))
    prod_newest = pc.execute("SELECT MAX(match_date) FROM matches WHERE competition_key=? AND status IN ('completed','awarded')", (key,)).fetchone()[0]
    prod_completed = pc.execute("SELECT COUNT(*) FROM matches WHERE competition_key=? AND season='2026-27' AND status='completed'", (key,)).fetchone()[0]
    pc.close()
    agree = conflict = new_result = missing_in_provider = moved = unmatched = ambiguous = 0
    conflict_rows, moved_rows, new_rows = [], [], []
    seen = set()
    for m in ms:
        he, _ = resolver.resolve(fd.SOURCE, comp_id, (m["homeTeam"] or {}).get("name") or "")
        ae, _ = resolver.resolve(fd.SOURCE, comp_id, (m["awayTeam"] or {}).get("name") or "")
        if not he or not ae:
            unmatched += 1
            continue
        c = stored.get((he, ae), [])
        if len(c) != 1:
            ambiguous += 1 if c else 0
            unmatched += 0 if c else 1
            continue
        s = c[0]
        seen.add((he, ae))
        if s["match_date"] and (m.get("utcDate") or "")[:10] != s["match_date"]:
            moved += 1
            moved_rows.append(dict(stored=s["match_date"], provider=m["utcDate"][:10], home=s["home_name"], away=s["away_name"], provider_status=m["status"]))
        rec = fd.parse_match(m, "", "", now, key, "2026")
        if rec.status == "completed":
            if s["status"] == "completed":
                if (s["home_goals_90"], s["away_goals_90"]) == (rec.regulation_home, rec.regulation_away):
                    agree += 1
                else:
                    conflict += 1
                    conflict_rows.append(dict(home=s["home_name"], away=s["away_name"], stored=[s["home_goals_90"], s["away_goals_90"]], provider=[rec.regulation_home, rec.regulation_away], date=s["match_date"]))
            else:
                new_result += 1
                new_rows.append(dict(home=s["home_name"], away=s["away_name"], date=s["match_date"], score=[rec.regulation_home, rec.regulation_away], stored_status=s["status"]))
        elif s["status"] == "completed":
            missing_in_provider += 1                                      # production has a verified result the provider does not show as finished
    out["against_production"] = dict(production_fixtures=sum(len(v) for v in stored.values()), production_completed=prod_completed, production_newest_result=prod_newest, matched_pairs=len(seen), unmatched_provider_rows=unmatched,
                                     ambiguous=ambiguous, results_agree=agree, results_conflict=conflict, results_new_to_production=new_result, production_results_not_finished_at_provider=missing_in_provider,
                                     fixtures_with_moved_date=moved, conflicts=conflict_rows[:10], moved_dates=moved_rows[:10], new_results=new_rows[:10])
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rejected").mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    rep = dict(started_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), urls=URLS)
    try:
        tok = fd.load_token()                                              # raises TokenMissing / TokenInvalid; the value is never printed
    except Exception as exc:  # noqa: BLE001
        print("STOP:", type(exc).__name__)
        return
    rep["token"] = dict(available=True, length=len(tok), shown=False)
    prod_before, ledger_before = baseline_hash.physical_sha256(PROD), ledger_lines()
    rep.update(production_sha256_before=prod_before, ledger_lines_before=ledger_before)
    priv = OUT / "private_copy.sqlite"
    for ext in ("", "-wal", "-shm"):
        Path(str(priv) + ext).unlink(missing_ok=True)
    s_, d_ = ro(PROD), sqlite3.connect(priv)
    s_.backup(d_)
    d_.close()
    s_.close()
    for k in ORDER:
        sync.APPROVED[k] = sync.PREPARED_PROVIDERS[k]                      # this process only; nothing is persisted
    bodies, calls, answers = {}, [], {}

    def make_guard(real):
        def guarded(url, headers):
            if url not in URLS.values() or url in calls or len(calls) >= 3:
                raise Abort(f"request guard: only the three approved URLs, once each (asked for {url}, call {len(calls) + 1})")
            calls.append(url)
            try:
                st, body, hd = real(url, headers)
            except Exception as exc:  # noqa: BLE001  (HTTPError etc.: keep the status and the body for analysis)
                st = getattr(exc, "code", None)
                body = exc.read() if hasattr(exc, "read") else b""
                answers[url] = dict(status=st, bytes=len(body), headers={k: v for k, v in dict(getattr(exc, "headers", {}) or {}).items() if k.lower().startswith("x-") or k.lower() == "retry-after"})
                bodies[url] = body
                raise
            bodies[url] = body
            answers[url] = dict(status=st, bytes=len(body), headers={k: v for k, v in dict(hd).items() if k.lower().startswith("x-") and "token" not in k.lower() or k.lower() == "retry-after"})
            return st, body, hd
        return guarded
    cfg = sync.SyncConfig(live_enabled=True, startup_check=True, startup_delay_seconds=0, periodic_minutes=360, max_retries=0, refresh_mode="full_season",
                          sources={"footballdata": {"enabled": True, "competitions": ORDER, "token_env": fd.DEFAULT_TOKEN_ENV}})
    mgr = sync.SyncManager(db_path=priv, cfg=cfg, request_guard=make_guard)
    pc = ro(priv)
    q_before = pc.execute("SELECT COALESCE(MAX(id),0) FROM quarantine").fetchone()[0]
    before = {r["record_id"]: dict(r) for r in pc.execute("SELECT * FROM matches WHERE competition_key IN ('EPL','SERIEA','LIGUE1') AND season='2026-27'")}
    pc.close()
    res = mgr.check_once("manual_check", only=ORDER)                      # <<< up to three real requests, into the private copy
    rep["cycle_outcome"] = res["outcome"]
    rep["requests_made"] = len(calls)
    rep["production_untouched"] = baseline_hash.physical_sha256(PROD) == prod_before
    rep["ledger_lines_after"] = ledger_lines()
    per = {d["competition"]: d for d in res.get("details", [])}
    pc = ro(priv)
    after = {r["record_id"]: dict(r) for r in pc.execute("SELECT * FROM matches WHERE competition_key IN ('EPL','SERIEA','LIGUE1') AND season='2026-27'")}
    newq = [dict(r) for r in pc.execute("SELECT reason, source_ref FROM quarantine WHERE id>? ORDER BY id", (q_before,))]
    pc.close()
    skip = {"last_changed_utc", "change_count", "content_hash"}
    rep["leagues"] = {}
    for k in ORDER:
        url = URLS[k]
        L = dict(request=dict(url=url, **answers.get(url, dict(status=None, note="not requested"))))
        d = per.get(k, {})
        L["scheduler_outcome"] = {x: (fd.redact(str(v))[:300]) for x, v in d.items()}
        body = bodies.get(url)
        if body is not None and L["request"].get("status") == 200:
            try:
                L["analysis"] = analyse(k, body, now)
            except Exception as exc:  # noqa: BLE001  (a reporting bug must not lose the answer)
                L["analysis"] = dict(analysis_error=f"{type(exc).__name__}: {exc}"[:300])
                (OUT / "rejected" / f"{fd.LEAGUES[k][0]}_2026_unanalysed.json").write_bytes(body)
            if L["analysis"].get("adapter_validation", "").startswith("REJECTED"):
                (OUT / "rejected" / f"{fd.LEAGUES[k][0]}_2026.json").write_bytes(body)
        elif body:
            L["error_body"] = fd.redact(body.decode("utf-8", "replace"))[:300]
        mine = {rid: r for rid, r in after.items() if r["competition_key"] == k}
        ch = {rid: sorted(f for f in r if f not in skip and r[f] != before[rid][f]) for rid, r in mine.items() if rid in before and any(r[f] != before[rid][f] for f in r if f not in skip)}
        fields = {}
        for fl in ch.values():
            for f in fl:
                fields[f] = fields.get(f, 0) + 1
        L["dry_run_on_copy"] = dict(rows_changed=len(ch), changed_fields=fields, new_rows=len(set(mine) - {r for r in before if before[r]["competition_key"] == k}),
                                    quarantined_by_kind={}, results_changed=[rid for rid, fl in ch.items() if set(fl) & {"home_goals_90", "away_goals_90", "match_date"} and before[rid]["status"] == "completed"])
        rep["leagues"][k] = L
    kinds = {}
    for x in newq:
        kk = x["reason"].split(":")[0][:40]
        kinds[kk] = kinds.get(kk, 0) + 1
    rep["new_quarantine_findings_in_copy"] = dict(total=len(newq), by_kind=kinds, samples=[fd.redact(x["reason"])[:160] for x in newq[:8]])
    text = json.dumps(rep, indent=1, ensure_ascii=False, default=str)
    text = fd.redact(text)
    (OUT / "report.json").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
