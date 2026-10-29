"""Phase 4.8C: supervised, READ-ONLY OpenLigaDB verification for the Bundesliga (bl1), Premier League (pl) and La Liga (la1), season 2026-27.

Nothing is imported into production. The requests are GET only, one per league, exactly the URLs in ENDPOINTS, at least 3 s apart, with the adapters' safeguards
(contact string, user agent, request ledger, immutable snapshot with sha256). The comparison happens on a PRIVATE COPY of the production file; the production file
is only read by a file copy and is never opened for writing.

    python app/store/verify_openligadb_p48c.py --plan                      show and verify everything, NO network
    python app/store/verify_openligadb_p48c.py --run --only bl1            the Bundesliga request (1 GET)         [needs approval of the ledger]
    python app/store/verify_openligadb_p48c.py --run --only pl,la1         the Premier League and La Liga (2 GET) [needs a separate approval]
    python app/store/verify_openligadb_p48c.py --analyse [--dir PATH]      compare saved snapshots with a private copy of production, NO network
"""
import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import rehearse_openligadb as R  # noqa: E402
from store import baseline_hash, db, sync  # noqa: E402

HOST = "api.openligadb.de"
BASE = f"https://{HOST}"
ENDPOINTS = {"bl1": f"{BASE}/getmatchdata/bl1/2026", "pl": f"{BASE}/getmatchdata/pl/2026", "la1": f"{BASE}/getmatchdata/la1/2026"}
SPECS = {"bl1": ("BUNDESLIGA", sync.APPROVED["BUNDESLIGA"]), "pl": ("EPL", sync.OFFLINE_PREPARED["EPL"]), "la1": ("LALIGA", sync.OFFLINE_PREPARED["LALIGA"])}
MIN_INTERVAL_S, JITTER_S = 3.0, 1.5
PROD = C.ROOT / "data" / "footiq.sqlite"
OUT = C.ROOT / "data" / "snapshots" / "p48c"
WORK = C.ROOT / "data" / "supervised" / "phase4" / "p48c" / "work"
REPORT = C.ROOT / "data" / "supervised" / "phase4" / "p48c"


def preflight(only: list[str]) -> dict:
    common, _, ol = sync._adapters()
    cfg = sync._adapter_config()
    cfg.live_enabled = True
    ua_ok = True
    try:
        cfg.user_agent("openligadb")
    except Exception:  # noqa: BLE001
        ua_ok = False
    sync_cfg = json.loads((C.ROOT / "config" / "sync.json").read_text(encoding="utf-8"))
    return dict(host=HOST, endpoints=[ENDPOINTS[k] for k in only], request_cap=len(only), min_interval_s=MIN_INTERVAL_S, jitter_s=JITTER_S, contact_configured=cfg.contact_configured(),
                user_agent_builds=ua_ok, config_sync_live_enabled=sync_cfg["live_enabled"], note="config/sync.json stays false: this script enables the adapter for its own process only",
                attribution=ol.ATTRIBUTION, licence=ol.LICENCE, snapshot_dir=str(OUT.relative_to(C.ROOT)), production="copied (file copy) and never opened for writing", import_into_production="none")


def make_opener(allowed: set, sent: list):
    def opener(url, headers):
        u = urlparse(url)
        assert u.scheme == "https" and u.hostname == HOST, f"blocked host {u.hostname}"
        assert url in allowed, f"blocked URL (not on the approved list): {url}"
        assert len(sent) < len(allowed), "request cap reached"
        sent.append(url)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read() if hasattr(e, "read") else b"", dict(e.headers or {})
    return opener


def run_requests(only: list[str]) -> dict:
    common, _, ol = sync._adapters()
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = sync._adapter_config()
    cfg.live_enabled = True
    cfg.snapshot_dir, cfg.ledger_path = str(OUT), str(OUT / "request_ledger.jsonl")
    sent: list = []
    client = common.HttpClient(cfg, "openligadb", min_interval_s=MIN_INTERVAL_S, jitter_s=JITTER_S, max_retries=0, opener=make_opener({ENDPOINTS[k] for k in only}, sent))
    store = common.SnapshotStore(cfg.snapshot_dir)
    infos = {}
    for k in only:
        try:
            body, meta = client.get(ENDPOINTS[k])
            infos[k] = store.save("openligadb", f"p48c_{k}", body, dict(meta, source="openligadb", licence=ol.LICENCE, attribution=ol.ATTRIBUTION))
        except Exception as exc:  # noqa: BLE001
            infos[k] = dict(error=f"{type(exc).__name__}: {cfg.redact(str(exc))[:200]}")
    summary = dict(requests_sent=sent, count=len(sent), cap=len(only), snapshots=infos, at_utc=sync.now_utc())
    (OUT / f"run_summary_{'_'.join(only)}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def latest(dirpath: Path, k: str):
    files = sorted((dirpath / "openligadb").glob(f"*_p48c_{k}.json"))
    return files[-1] if files else None


def private_copy() -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    dst = WORK / "prod_copy.sqlite"
    for ext in ("", "-wal", "-shm"):
        Path(str(dst) + ext).unlink(missing_ok=True)
        if Path(str(PROD) + ext).exists():
            shutil.copyfile(str(PROD) + ext, str(dst) + ext)
    c = sqlite3.connect(dst)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.execute("PRAGMA journal_mode=DELETE")
    c.close()
    return dst


def dry_run(dirpath: Path, only: list[str], protect_dates: bool) -> dict:
    """Replay the snapshots onto a fresh private copy exactly as the importer would, and report what would change. Production is untouched."""
    prod_before = baseline_hash.physical_sha256(PROD)
    cp = private_copy()
    base = sqlite3.connect(cp)
    base.row_factory = sqlite3.Row
    before = [dict(r) for r in base.execute("SELECT * FROM matches")]
    before_q = base.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
    base.close()
    original_now = sync.now_utc
    out = dict(protect_dates=protect_dates, leagues={}, changes=[])
    try:
        conn = db.connect(cp)
        for k in only:
            p = latest(dirpath, k)
            if not p:
                continue
            meta = json.loads((p.parent / (p.name + ".meta.json")).read_text(encoding="utf-8"))
            key, spec = SPECS[k]
            payload = p.read_bytes()
            ts = meta["saved_utc"]
            now = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            res = sync.replay_payload(conn, payload, key, retrieved_utc=ts, now=now, kind="p48c_dry_run", spec=spec, snapshot_id=meta["snapshot_id"], url=ENDPOINTS[k], path=str(p), protect_dates=protect_dates)
            out["leagues"][k] = dict(competition=key, snapshot=p.name, sha256=meta["sha256"], bytes=meta["bytes"], saved_utc=ts, **{x: res[x] for x in ("inserted", "updated", "unchanged", "confirmed", "quarantined", "records") if x in res},
                                     held_date_difference=res.get("held_date_difference", 0))
        conn.close()
    finally:
        sync.now_utc = original_now
    after = sqlite3.connect(cp)
    after.row_factory = sqlite3.Row
    b = {r["record_id"]: r for r in before}
    skip = {"last_changed_utc", "change_count", "content_hash"}
    kinds = Counter()
    for r in after.execute("SELECT * FROM matches"):
        r = dict(r)
        old = b.get(r["record_id"])
        if old is None:
            kinds["inserted"] += 1
            out["changes"].append(dict(record_id=r["record_id"], competition=r["competition_key"], change="INSERTED", field="", before="", after=f'{r["match_date"]} {r["status"]} {r["home_name"]} v {r["away_name"]}'))
            continue
        for f in (f for f in r if f not in skip and r[f] != old[f]):
            kinds[f"changed:{f}"] += 1
            out["changes"].append(dict(record_id=r["record_id"], competition=r["competition_key"], change="UPDATED", field=f, before=old[f], after=r[f], home=r["home_name"], away=r["away_name"], match_date=old["match_date"]))
    out["row_changes"] = dict(kinds)
    out["quarantine_added"] = after.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0] - before_q
    out["new_quarantine_reasons"] = [dict(r) for r in after.execute("SELECT substr(reason,1,140) AS reason, COUNT(*) n FROM quarantine WHERE id > (SELECT MAX(id) FROM quarantine) - ? GROUP BY 1", (max(out["quarantine_added"], 0),))]
    after.close()
    out["production_sha256_before"], out["production_sha256_after"] = prod_before, baseline_hash.physical_sha256(PROD)
    out["production_untouched"] = out["production_sha256_before"] == out["production_sha256_after"]
    return out


def compare_with_previous(dirpath: Path, only: list[str]) -> dict:
    """Source change since the snapshot behind the production import (what the provider itself changed), match by OpenLigaDB matchID."""
    prev = {"bl1": sorted((C.ROOT / "data" / "snapshots" / "openligadb").glob("*_bl1_2026_season.json")),
            "pl": sorted((C.ROOT / "data" / "snapshots" / "investigation" / "openligadb").glob("*_investigation_pl.json")),
            "la1": sorted((C.ROOT / "data" / "snapshots" / "investigation" / "openligadb").glob("*_investigation_la1.json"))}
    out = {}
    for k in only:
        new_p, old_p = latest(dirpath, k), (prev[k][-1] if prev[k] else None)
        if not new_p or not old_p:
            continue
        new = {m["matchID"]: m for m in json.loads(new_p.read_bytes())}
        old = {m["matchID"]: m for m in json.loads(old_p.read_bytes())}

        def sig(m):
            res = sorted((r.get("resultTypeID"), r.get("pointsTeam1"), r.get("pointsTeam2")) for r in (m.get("matchResults") or []))
            return (m.get("matchDateTimeUTC"), bool(m.get("matchIsFinished")), tuple(res))
        changed = [mid for mid in new if mid in old and sig(new[mid]) != sig(old[mid])]
        out[k] = dict(previous_snapshot=old_p.name, previous_matches=len(old), new_matches=len(new), only_in_new=len(set(new) - set(old)), only_in_old=len(set(old) - set(new)),
                      changed_matches=len(changed), newly_finished=sum(1 for mid in changed if new[mid].get("matchIsFinished") and not old[mid].get("matchIsFinished")),
                      date_changed=sum(1 for mid in changed if new[mid].get("matchDateTimeUTC") != old[mid].get("matchDateTimeUTC")))
    return out


def analyse(dirpath: Path, only: list[str], tag: str) -> dict:
    rep = dict(generated_utc=sync.now_utc(), snapshot_dir=str(dirpath), only=only, source_change_since_import_snapshot=compare_with_previous(dirpath, only),
               dry_run_as_the_live_path_would_import=dry_run(dirpath, only, protect_dates=False), dry_run_with_date_protection=dry_run(dirpath, only, protect_dates=True))
    REPORT.mkdir(parents=True, exist_ok=True)
    for name in ("dry_run_as_the_live_path_would_import", "dry_run_with_date_protection"):
        ch = rep[name].pop("changes")
        with open(REPORT / f"verify_{tag}_{name}_changes.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["record_id", "competition", "change", "field", "before", "after", "home", "away", "match_date"])
            w.writeheader()
            w.writerows(ch)
    (REPORT / f"verify_{tag}.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--only", default="bl1")
    ap.add_argument("--dir", default=str(OUT))
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()
    only = [x for x in a.only.split(",") if x]
    assert set(only) <= set(ENDPOINTS), only
    if a.plan or not (a.run or a.analyse):
        print(json.dumps(preflight(only), indent=1))
    if a.run:
        pf = preflight(only)
        assert pf["contact_configured"] and pf["user_agent_builds"], "a configured contact is required (config/contact.local or FOOTIQ_CONTACT)"
        print(json.dumps(run_requests(only), indent=1, default=str))
    if a.analyse or a.run:
        rep = analyse(Path(a.dir), only, a.tag or "_".join(only))
        print(json.dumps({k: rep[k] for k in rep if k != "snapshot_dir"}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
