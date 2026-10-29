"""One-off, READ-ONLY verification of OpenLigaDB coverage for the Premier League (`pl`, `pl1`) and La Liga (`la1`), 2026-27.

Approved scope (2026-10-25): at most FIVE GET requests to api.openligadb.de, exactly the endpoints in ENDPOINTS, analysis only.
  * No result is imported: the production SQLite store is opened read-only (SQLite mode=ro) and never written.
  * No unattended synchronisation, no scheduling; config/sync.json is not read or changed.
  * Raw payloads are saved as immutable snapshots with sha256 under data/snapshots/investigation/ (git-ignored), with a request ledger.

    python app/store/investigate_openligadb.py --plan     show and verify everything, NO network
    python app/store/investigate_openligadb.py --run      make the requests (needs a configured contact), then analyse
    python app/store/investigate_openligadb.py --analyse  analyse the saved snapshots again, NO network
"""
import argparse
import difflib
import json
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from store import db, sync  # noqa: E402

HOST = "api.openligadb.de"
BASE = f"https://{HOST}"
ENDPOINTS = [
    ("leagues", f"{BASE}/getavailableleagues/2026"),
    ("pl", f"{BASE}/getmatchdata/pl/2026"),
    ("pl1", f"{BASE}/getmatchdata/pl1/2026"),
    ("la1", f"{BASE}/getmatchdata/la1/2026"),
    ("resulttypes", f"{BASE}/getresulttypes"),         # reserve: only requested if an unseen result kind appears
]
REQUEST_CAP = 5
MIN_INTERVAL_S, JITTER_S = 3.0, 1.5
KNOWN_KINDS = {"HalfTime", "After90Minutes", "AfterExtraTime", "AfterPenalties", "Unknown"}
OUT = C.ROOT / "data" / "snapshots" / "investigation"
LEAGUES = {"pl": ("EPL", "england:1-premierleague"), "pl1": ("EPL", "england:1-premierleague"), "la1": ("LALIGA", "espana:1-liga")}
SEASON = "2026-27"


def adapters():
    return sync._adapters()


def preflight() -> dict:
    common, _, ol = adapters()
    cfg = sync._adapter_config()
    ua_ok = True
    try:
        cfg.live_enabled = True
        cfg.user_agent("openligadb")
    except Exception:  # noqa: BLE001
        ua_ok = False
    sync_cfg = json.loads((C.ROOT / "config" / "sync.json").read_text(encoding="utf-8"))
    return dict(host=HOST, endpoints=[u for _, u in ENDPOINTS], request_cap=REQUEST_CAP, min_interval_s=MIN_INTERVAL_S, jitter_s=JITTER_S, documented_limit="60 requests/min/IP (swagger); fair use: sparing",
                contact_configured=cfg.contact_configured(), user_agent_builds=ua_ok, contact_file_git_ignored=(C.ROOT / "config" / ".gitignore").read_text(encoding="utf-8").split().count("contact.local") == 1,
                sync_json_live_enabled=sync_cfg["live_enabled"], attribution=ol.ATTRIBUTION, licence=ol.LICENCE, snapshot_dir=str(OUT.relative_to(C.ROOT)),
                store_opened="read-only (mode=ro)", ingestion="none")


def make_opener(counter: list):
    allowed = {u for _, u in ENDPOINTS}

    def opener(url, headers):
        u = urlparse(url)
        assert u.scheme == "https" and u.hostname == HOST, f"blocked host {u.hostname}"
        assert url in allowed, f"blocked URL (not one of the approved endpoints): {url}"
        assert len(counter) < REQUEST_CAP, "request cap reached"
        counter.append(url)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read() if hasattr(e, "read") else b"", dict(e.headers or {})
    return opener


def run_requests() -> dict:
    common, _, ol = adapters()
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = sync._adapter_config()
    cfg.live_enabled = True
    cfg.snapshot_dir, cfg.ledger_path = str(OUT), str(OUT / "request_ledger.jsonl")
    sent: list = []
    client = common.HttpClient(cfg, "openligadb", min_interval_s=MIN_INTERVAL_S, jitter_s=JITTER_S, max_retries=2, opener=make_opener(sent))
    store = common.SnapshotStore(cfg.snapshot_dir)
    infos, kinds = {}, set()
    for name, url in ENDPOINTS[:4]:
        try:
            body, meta = client.get(url)
            infos[name] = store.save("openligadb", f"investigation_{name}", body, dict(meta, source="openligadb", licence=ol.LICENCE, attribution=ol.ATTRIBUTION))
            if name != "leagues":
                for m in json.loads(body):
                    kinds |= {r.get("resultTypeKind") for r in (m.get("matchResults") or [])}
        except Exception as exc:  # noqa: BLE001  (a missing league is a finding, not a crash)
            infos[name] = dict(error=f"{type(exc).__name__}: {cfg.redact(str(exc))[:200]}")
    if kinds - KNOWN_KINDS:
        body, meta = client.get(ENDPOINTS[4][1])
        infos["resulttypes"] = store.save("openligadb", "investigation_resulttypes", body, dict(meta, source="openligadb", licence=ol.LICENCE, attribution=ol.ATTRIBUTION))
    (OUT / "run_summary.json").write_text(json.dumps(dict(requests_sent=sent, count=len(sent), cap=REQUEST_CAP, snapshots=infos, unseen_result_kinds=sorted(kinds - KNOWN_KINDS)), indent=1), encoding="utf-8")
    return dict(requests_sent=sent, count=len(sent), snapshots=infos)


def latest_snapshot(name: str):
    files = sorted(p for p in (OUT / "openligadb").glob(f"*_investigation_{name}.json"))
    return files[-1] if files else None


def analyse() -> dict:
    common, identity, ol = adapters()
    conn = db.connect(readonly=True)
    resolver = sync.build_resolver(conn)
    report = dict(generated_utc=sync.now_utc(), snapshot_sha256={}, leagues={})
    # --- which leagues exist
    p = latest_snapshot("leagues")
    if p:
        listing = json.loads(p.read_bytes())
        report["snapshot_sha256"]["leagues"] = json.loads((p.parent / (p.name + ".meta.json")).read_text(encoding="utf-8"))["sha256"]
        report["listing"] = {x["leagueShortcut"]: dict(id=x["leagueId"], name=x["leagueName"]) for x in listing if x["leagueShortcut"] in ("pl", "pl1", "la1", "bl1", "sa", "seriea", "fl1", "ligue1") or any(w in x["leagueName"] for w in ("Serie", "Ligue"))}
    for lg_key, (ckey, comp_id) in LEAGUES.items():
        p = latest_snapshot(lg_key)
        if not p:
            continue
        meta = json.loads((p.parent / (p.name + ".meta.json")).read_text(encoding="utf-8"))
        report["snapshot_sha256"][lg_key] = meta["sha256"]
        raw = json.loads(p.read_bytes())
        recs = ol.parse_payload(p.read_bytes(), meta["saved_utc"], meta["snapshot_id"], datetime.now(timezone.utc), comp_id)
        store_rows = [dict(r) for r in conn.execute("SELECT * FROM matches WHERE competition_id=? AND season=?", (comp_id, SEASON))]
        by_pair = defaultdict(list)
        for r in store_rows:
            by_pair[(r["home_entity_id"], r["away_entity_id"])].append(r)
        store_names = sorted({r["home_name"] for r in store_rows} | {r["away_name"] for r in store_rows})
        today = datetime.now(timezone.utc).date().isoformat()
        L = dict(source_matches=len(recs), store_matches=len(store_rows))
        L["statuses"] = dict(Counter(r.status for r in recs))
        L["result_kinds"] = dict(Counter(k.get("resultTypeKind") for m in raw for k in (m.get("matchResults") or [])))
        L["teams_in_source"] = len({r.home_raw for r in recs} | {r.away_raw for r in recs})
        pair_count = Counter((r.home_raw, r.away_raw) for r in recs)
        L["duplicate_ordered_pairs"] = sum(1 for v in pair_count.values() if v > 1)
        per_team = Counter([r.home_raw for r in recs] + [r.away_raw for r in recs])
        L["matches_per_team"] = dict(min=min(per_team.values()) if per_team else 0, max=max(per_team.values()) if per_team else 0)
        per_md = Counter(r.round for r in recs)
        L["matchdays"] = dict(count=len(per_md), sizes=dict(Counter(per_md.values())))
        L["kickoff_utc_available"] = sum(r.kickoff_utc is not None for r in recs)
        dates = [r.match_date for r in recs if r.match_date]
        L["date_range"] = [min(dates), max(dates)] if dates else None
        comp = [r for r in recs if r.status == "completed"]
        L["completed"] = len(comp)
        L["completed_with_explicit_90min"] = sum(r.label_eligible_90min for r in comp)
        L["latest_completed_date"] = max((r.match_date for r in comp), default=None)
        updates = sorted(m.get("lastUpdateDateTime") for m in raw if m.get("lastUpdateDateTime"))
        L["last_update_min_max"] = [updates[0], updates[-1]] if updates else None
        L["matches_without_any_lastUpdate"] = sum(1 for m in raw if not m.get("lastUpdateDateTime"))
        # --- identity mapping
        names = sorted({r.home_raw for r in recs} | {r.away_raw for r in recs})
        mapping, unresolved = {}, []
        for n in names:
            e, how = resolver.resolve("openligadb", comp_id, n)
            if e:
                mapping[n] = (e, how)
            else:
                unresolved.append(dict(name=n, method=how, suggestions=difflib.get_close_matches(n, store_names, n=3, cutoff=0.5)))
        L["identity"] = dict(resolved=len(mapping), by_method=dict(Counter(h for _, h in mapping.values())), unresolved=unresolved,
                             store_teams_not_in_source=sorted(set(store_names) - {n for n in names} - {store_n for store_n in store_names if any(mapping.get(n, (None,))[0] == next((r['home_entity_id'] for r in store_rows if r['home_name'] == store_n), None) for n in names)}))
        # --- comparison with the store, fixture by fixture (twice: strict identity mapping, and "assisted" where each unresolved name is assumed to be its top suggestion, pending human review)
        ent_by_name = {}
        for r in store_rows:
            ent_by_name[r["home_name"]] = r["home_entity_id"]
            ent_by_name[r["away_name"]] = r["away_entity_id"]

        def compare(mp):
            cmp = Counter()
            detail = defaultdict(list)
            seen = set()
            for r in recs:
                he, ae = mp.get(r.home_raw), mp.get(r.away_raw)
                if not he or not ae:
                    cmp["identity_unresolved"] += 1
                    continue
                rows = by_pair.get((he, ae), [])
                if len(rows) != 1:
                    cmp["pairing_not_in_store" if not rows else "pairing_ambiguous_in_store"] += 1
                    if len(detail["pairing_not_in_store"]) < 5 and not rows:
                        detail["pairing_not_in_store"].append(f"{r.home_raw} v {r.away_raw} {r.match_date}")
                    continue
                s = rows[0]
                seen.add(s["record_id"])
                cmp["matched"] += 1
                local = (r.kickoff_local or "")[:10]
                cmp["date_agrees_utc"] += r.match_date == s["match_date"]
                cmp["date_agrees_local"] += local == s["match_date"]
                if local != s["match_date"] and r.match_date != s["match_date"]:
                    cmp["date_disagrees_both"] += 1
                    d = (datetime.fromisoformat(local) - datetime.fromisoformat(s["match_date"])).days if local else None
                    cmp[f"date_off_by_{d}_days"] += 1
                    if len(detail["date_disagreements"]) < 8:
                        detail["date_disagreements"].append(f"{r.home_raw} v {r.away_raw}: source local {local} / utc {r.match_date}, store {s['match_date']}")
                cmp["matchday_agrees"] += str(s["matchday_no"]) == str(r.round)
                if str(s["matchday_no"]) != str(r.round) and len(detail["matchday_disagreements"]) < 8:
                    detail["matchday_disagreements"].append(f"{r.home_raw} v {r.away_raw}: source {r.round}, store {s['matchday_no']}")
                sc = s["status"] in ("completed", "awarded")
                if r.status == "completed" and r.label_eligible_90min:
                    if sc:
                        same = (s["home_goals_90"], s["away_goals_90"]) == (r.regulation_home, r.regulation_away)
                        cmp["completed_both_scores_agree" if same else "completed_both_SCORE_CONFLICT"] += 1
                        if not same:
                            detail["conflicts"].append(f"{r.home_raw} v {r.away_raw}: source {r.regulation_home}-{r.regulation_away}, store {s['home_goals_90']}-{s['away_goals_90']}")
                    elif s["status"] in ("awaiting_result", "scheduled"):
                        cmp["recovered_in_principle" if s["match_date"] < today else "completed_in_source_but_store_date_not_passed"] += 1
                    else:
                        cmp["completed_source_store_status_" + s["status"]] += 1
                elif sc:
                    cmp["store_completed_but_source_not_completed"] += 1
                    if len(detail["store_completed_source_not"]) < 8:
                        detail["store_completed_source_not"].append(f"{r.home_raw} v {r.away_raw} ({s['match_date']}) source status {r.status}")
                if s["status"] == "awaiting_result" and r.status != "completed":
                    cmp["still_missing_in_source"] += 1
            return cmp, detail, seen

        strict_map = {n: e for n, (e, _) in mapping.items()}
        cmp, detail, seen_store = compare(strict_map)
        assisted_map = dict(strict_map)
        assumed = {}
        for u in unresolved:
            tgt = next((ent_by_name[x] for x in u["suggestions"] if x in ent_by_name), None)
            if tgt:
                assisted_map[u["name"]] = tgt
                assumed[u["name"]] = u["suggestions"][0]
        cmp2, detail2, _ = compare(assisted_map)
        L["comparison"] = dict(cmp)
        L["comparison_details"] = {k: v for k, v in detail.items()}
        L["comparison_if_suggested_aliases_were_reviewed_and_accepted"] = dict(assumed_aliases=assumed, **cmp2)
        L["comparison_assisted_details"] = {k: v for k, v in detail2.items()}
        L["name_mapping"] = {n: dict(entity=e, method=h, store_name=next((sn for sn, se in ent_by_name.items() if se == e), None)) for n, (e, h) in mapping.items()}
        L["store_fixtures_missing_from_source"] = len([r for r in store_rows if r["record_id"] not in seen_store])
        L["store_awaiting_result_total"] = sum(r["status"] == "awaiting_result" for r in store_rows)
        L["store_completed_total"] = sum(r["status"] in ("completed", "awarded") for r in store_rows)
        L["store_latest_result"] = max((r["match_date"] for r in store_rows if r["status"] in ("completed", "awarded")), default=None)
        L["pairs"] = sorted(f"{r.home_raw}|{r.away_raw}" for r in recs)
        report["leagues"][lg_key] = L
    # --- pl versus pl1
    if "pl" in report["leagues"] and "pl1" in report["leagues"]:
        a, b = set(report["leagues"]["pl"]["pairs"]), set(report["leagues"]["pl1"]["pairs"])
        report["pl_vs_pl1"] = dict(pl=len(a), pl1=len(b), identical_pairings=len(a & b), only_pl=len(a - b), only_pl1=len(b - a))
    for L in report["leagues"].values():
        L.pop("pairs", None)
    conn.close()
    return report


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--analyse", action="store_true")
    a = ap.parse_args()
    if a.plan:
        print(json.dumps(preflight(), indent=1))
        return
    if a.run:
        pf = preflight()
        assert pf["contact_configured"] and pf["user_agent_builds"], "no configured contact: refusing to make requests"
        print(json.dumps(run_requests(), indent=1, default=str))
    rep = analyse()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "findings.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
