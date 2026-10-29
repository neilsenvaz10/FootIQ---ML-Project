"""Controlled OpenLigaDB Bundesliga 2026-27 pilot.

  python -I pilot_openligadb.py plan                         -> writes + prints the request plan and its sha256 (no network)
  python -I pilot_openligadb.py run --plan-sha256 <sha256>   -> executes EXACTLY that plan (needs owner approval = the sha, a configured contact, and live use)
  python -I pilot_openligadb.py rehearse                     -> dress rehearsal of the whole run against a local fake transport (no network)

Read-only, bounded, rate-limited: GET only, one host, <= 6 planned requests (hard cap 12 HTTP attempts incl. retries), >= 2 s between requests (+ jitter).
The contact string is never printed, logged or stored (env FOOTIQ_CONTACT or untracked config/contact.local). The official feature store, models, protocol and logger are not touched.
"""
import argparse, hashlib, json, os, sys, time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "_scripts"))
from footiq_sources import common, openligadb as ol
from footiq_sources.reconcile import build_resolver, reconcile_source

P = r"D:\Foot IQ"
V_PATH = os.path.join(P, "FootIQ_ML_Training_Preparation", "_build", "work", "V_universe.pkl")
PILOT_DIR = os.path.join(ROOT, "pilot")
HOST = "api.openligadb.de"
EXPECTED = dict(leagueId=4937, leagueShortcut="bl1", leagueSeason=2026)        # from the stored 2026-10-21 snapshot; R1 must confirm before R3 is sent
COMP = "deutschland:1-bundesliga"
SEASON_LABEL = "2026-27"
TRAIN_CUTOFF = "2026-09-20"

PLAN = {
    "plan_version": "r1", "source": "OpenLigaDB", "scheme": "https", "host": HOST, "method": "GET", "auth": "none", "request_body": "none", "cookies": "none",
    "requests": [
        {"id": "R1", "path": "/getavailableleagues/2026", "purpose": "confirm exact league id / shortcut / season for the Bundesliga 2026-27", "expected_size": "< 100 KB"},
        {"id": "R2", "path": "/getresulttypes", "purpose": "confirm result-type kinds (After90Minutes etc.) used for explicit regulation scores", "expected_size": "< 10 KB"},
        {"id": "R3", "path": "/getmatchdata/bl1/2026", "purpose": "whole Bundesliga season (306 matches): results, fixtures, kickoff UTC, ids, result types", "expected_size": "about 0.3 MB",
         "sent_only_if": "R1 confirmed leagueId=4937, shortcut=bl1, season=2026"},
        {"id": "R4", "path": "/getcurrentgroup/bl1", "purpose": "current matchday for the change-date polling probe", "expected_size": "< 2 KB"},
        {"id": "R5", "path": "/getlastchangedate/bl1/2026/{current_matchday-1}", "purpose": "change-date probe (no match data fetched)", "expected_size": "< 1 KB"},
        {"id": "R6", "path": "/getlastchangedate/bl1/2026/{current_matchday}", "purpose": "change-date probe (no match data fetched)", "expected_size": "< 1 KB"},
    ],
    "limits": {"planned_requests": 6, "max_http_attempts_total_including_retries": 12, "min_interval_seconds": 2.0, "max_extra_jitter_seconds": 1.5,
               "expected_duration_seconds": "about 15-30", "expected_rate": "at most ~25 requests/minute vs documented limit 60/minute/IP; whole pilot = 6 requests",
               "retry_policy": "429/5xx/network error: exponential back-off (Retry-After honoured), at most 2 retries per request, then abort"},
    "preconditions": ["contact configured via env FOOTIQ_CONTACT or untracked config/contact.local (checked before any request; value never shown)",
                      "no Bundesliga match scheduled between 1 h before kickoff and 3 h after kickoff (checked against the stored schedule)",
                      "plan sha256 supplied by the owner equals the sha256 of this plan"],
    "abort_if": ["R1 does not list leagueId 4937 / bl1 / 2026", "any HTTP status other than 200/429/5xx", "attempt budget exhausted", "response host differs from api.openligadb.de"],
    "user_agent": "FootIQ-ResultsAdapters-OpenLigaDBBot/1.0.0 (+local research project; <contact from env/untracked file - not shown>)",
    "attribution": "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0 (stored on every record and snapshot)",
    "outputs": ["raw snapshots (read-only, sha256) under snapshots/openligadb/", "pilot/<run_id>/ staging records, reconciliation tables, validation report, isolated refreshed universe (NOT the feature store)"],
    "not_done": ["no change to the official feature store, frozen datasets, models, protocol or logger", "no Wikipedia requests", "no official logging, no approval JSON", "no scheduler"],
}


def plan_sha(plan=PLAN):
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


class BudgetedClient(common.HttpClient):
    """HttpClient limited to the planned host/method and a hard attempt budget."""
    def __init__(self, *a, max_attempts=12, **kw):
        super().__init__(*a, **kw)
        self.max_attempts, self.used = max_attempts, 0

    def get(self, url, params=None, headers=None):
        if urlparse(url).hostname != HOST or urlparse(url).scheme != "https":
            raise common.LiveAccessDenied("destination not in the approved plan")
        inner = self._opener

        def counted(u, h):
            self.used += 1
            if self.used > self.max_attempts:
                raise common.SourceUnavailable("attempt budget exhausted")
            if inner:
                return inner(u, h)
            import urllib.request, urllib.error
            req = urllib.request.Request(u, headers=h)
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.status, r.read(), dict(r.headers)
            except urllib.error.HTTPError as e:
                return e.code, b"", dict(e.headers or {})
        self._opener = counted
        try:
            return super().get(url, params, headers)
        finally:
            self._opener = inner


def schedule_guard(now):
    """Refuse to run near Bundesliga kickoffs (terms: be gentle while matches are in play) using the stored schedule."""
    d = json.load(open(os.path.join(ROOT, "evidence", "openligadb_bl1_2026.json"), encoding="utf-8"))
    for m in d:
        ko = ol._parse_utc(m["matchDateTimeUTC"])
        if ko - timedelta(hours=1) <= now <= ko + timedelta(hours=3):
            return False, m["matchDateTimeUTC"]
    return True, None


def run_pilot(cfg, outdir, opener=None, sleep=time.sleep, now=None, label="live"):
    now = now or datetime.now(timezone.utc)
    if not cfg.contact_configured():
        raise common.LiveAccessDenied("contact not configured (env FOOTIQ_CONTACT or config/contact.local)")
    ok, ko = schedule_guard(now)
    if not ok:
        raise common.LiveAccessDenied(f"a Bundesliga match is scheduled around {ko}; pilot not run")
    cfg.live_enabled = True                                            # in-memory only; adapters.json keeps live_enabled=false
    cfg.snapshot_dir = os.path.join(outdir, "snapshots"); cfg.ledger_path = os.path.join(outdir, "request_ledger.jsonl")
    os.makedirs(outdir, exist_ok=True)
    cl = BudgetedClient(cfg, "OpenLigaDB", min_interval_s=2.0, jitter_s=1.5, max_retries=2, max_attempts=12, opener=opener, sleep=sleep)
    store = common.SnapshotStore(cfg.snapshot_dir)
    snaps = {}

    def get(rid, path):
        body, meta = cl.get("https://" + HOST + path)
        info = store.save("openligadb", f"{rid}_" + path.strip("/").replace("/", "_"), body, dict(meta, source="openligadb", licence=ol.LICENCE, attribution=ol.ATTRIBUTION, plan_request=rid, plan_sha256=plan_sha()))
        snaps[rid] = info
        return json.loads(body.decode("utf-8")), body, info
    rep = dict(run_label=label, plan_sha256=plan_sha(), started_utc=common.utc_now(), requests_sent=[])
    leagues, _, _ = get("R1", "/getavailableleagues/2026")
    match = [l for l in leagues if l.get("leagueShortcut") == "bl1" and str(l.get("leagueSeason")) == "2026"]
    if len(match) != 1 or match[0].get("leagueId") != EXPECTED["leagueId"]:
        raise RuntimeError(f"R1 did not confirm league {EXPECTED}: aborting before R3")
    rep["league_confirmed"] = {k: match[0].get(k) for k in ("leagueId", "leagueShortcut", "leagueSeason", "leagueName")}
    rtypes, _, _ = get("R2", "/getresulttypes")
    rep["result_type_kinds"] = sorted({r.get("kind") or r.get("resultTypeKind") for r in rtypes})
    season, body, info = get("R3", "/getmatchdata/bl1/2026")
    retrieved = info["saved_utc"]
    recs = ol.parse_payload(body, retrieved, info["snapshot_id"], datetime.now(timezone.utc) if label == "live" else now, COMP)
    cur, _, _ = get("R4", "/getcurrentgroup/bl1")
    g = cur["groupOrderID"]
    probes = {}
    for rid, grp in (("R5", max(1, g - 1)), ("R6", g)):
        val, _, _ = get(rid, f"/getlastchangedate/bl1/2026/{grp}")
        probes[grp] = val
    rep["polling_probe"] = dict(current_matchday=g, last_change_dates=probes,
                                season_snapshot_max_lastUpdate_by_matchday={str(k): max((m.get("lastUpdateDateTime") or "") for m in season if (m.get("group") or {}).get("groupOrderID") == k) for k in probes})
    rep["http_attempts_used"] = cl.used; rep["requests_planned"] = 6
    return recs, season, rep, info


def analyse(recs, season, rep, info, outdir, now_utc):
    """Validation + reconciliation against the frozen openfootball universe. Writes only below outdir."""
    import glob
    V = pd.read_pickle(V_PATH)
    ing = os.path.join(os.path.dirname(ROOT), "matched_v1_prospective_r1", "ingestion", "runs")
    selfrun = sorted(glob.glob(os.path.join(ing, "selftest_*")))[-1]
    fx = pd.read_csv(os.path.join(selfrun, "fixtures.csv"), encoding="utf-8-sig", low_memory=False)
    un = pd.read_csv(os.path.join(selfrun, "unresolved_or_non_completed.csv"), encoding="utf-8-sig", low_memory=False)
    pnr = un[(un.status == "past_date_no_result") & (un.competition_id == COMP)]
    res = build_resolver(V)
    ret = datetime.fromisoformat(info["saved_utc"].replace("Z", "+00:00"))
    out = reconcile_source(recs, "openligadb", COMP, SEASON_LABEL, V, pnr[["home_entity_id", "away_entity_id", "match_date"]], res, now_utc.strftime("%Y-%m-%d"))
    for k, v in out.items():
        if isinstance(v, pd.DataFrame):
            v.to_csv(os.path.join(outdir, f"reconcile_{k}.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame([r.to_dict() for r in recs]).astype(str).to_csv(os.path.join(outdir, "staging_records.csv"), index=False, encoding="utf-8-sig")
    # integrity checks
    ids = [m["matchID"] for m in season]
    pairs = [(m["team1"]["teamId"], m["team2"]["teamId"]) for m in season]
    teams = {t for p in pairs for t in p}
    chk = dict(matches=len(season), unique_matchIDs=len(set(ids)), duplicate_matchIDs=len(ids) - len(set(ids)), duplicate_ordered_pairs=len(pairs) - len(set(pairs)), teams=len(teams),
               matchdays=len({(m.get("group") or {}).get("groupOrderID") for m in season}))
    comp = [r for r in recs if r.status == "completed"]
    chk["completed"] = len(comp)
    chk["completed_with_kickoff_before_retrieval"] = sum(datetime.fromisoformat(r.kickoff_utc.replace("Z", "+00:00")) < ret for r in comp)
    chk["completed_with_kickoff_after_retrieval"] = len(comp) - chk["completed_with_kickoff_before_retrieval"]
    chk["valid_kickoff_utc"] = sum(1 for r in recs if r.kickoff_utc and "2026-07-01" <= r.kickoff_utc[:10] <= "2027-07-01")
    chk["label_eligible_explicit_90min"] = sum(r.label_eligible_90min for r in recs)
    chk["completed_not_label_eligible"] = [r.source_ref for r in comp if not r.label_eligible_90min]
    chk["lastUpdate_after_retrieval"] = sum(1 for m in season if m.get("lastUpdateDateTime") and datetime.fromisoformat(m["lastUpdateDateTime"]).replace(tzinfo=timezone.utc) - timedelta(hours=2) > ret)
    s = out["summary"]
    allf = out.get("all", pd.DataFrame())
    new_ok = [r for r in comp if r.match_date and r.match_date > TRAIN_CUTOFF and r.label_eligible_90min and datetime.fromisoformat(r.kickoff_utc.replace("Z", "+00:00")) < ret]
    of_fix = pd.concat([fx[fx.competition_id == COMP][["match_date", "home_entity_id", "away_entity_id"]], pnr[["match_date", "home_entity_id", "away_entity_id"]]])
    of_pairs = set(zip(of_fix.home_entity_id, of_fix.away_entity_id))
    ol_pairs = set()
    unres = []
    for r in recs:
        he, hm = res.resolve("openligadb", COMP, r.home_raw); ae, am = res.resolve("openligadb", COMP, r.away_raw)
        if he and ae: ol_pairs.add((he, ae))
    allof = set(zip(V[(V.competition_id == COMP) & (V.season_corrected == SEASON_LABEL)].home_entity_id, V[(V.competition_id == COMP) & (V.season_corrected == SEASON_LABEL)].away_entity_id)) | of_pairs
    rep.update(integrity=chk, reconciliation=s, new_verified_results=len(new_ok), new_verified_result_dates=[min(r.match_date for r in new_ok), max(r.match_date for r in new_ok)] if new_ok else None,
               openfootball_fixtures_missing_in_source=len(allof - ol_pairs), source_fixtures_not_in_openfootball=len(ol_pairs - allof),
               team_mapping_errors=s["unresolved_team_identities"], results_with_valid_kickoff_utc=chk["valid_kickoff_utc"])
    # --- isolated refreshed universe (NOT the feature store) and a dry-run eligibility check of the Bundesliga fixtures
    add = pd.DataFrame(dict(record_id=["NEW:openligadb:" + r.source_ref for r in new_ok], competition_id=COMP, season_corrected=SEASON_LABEL, match_date=[r.match_date for r in new_ok],
                            dt=pd.to_datetime([r.match_date for r in new_ok]), home_entity_id=[res.resolve("openligadb", COMP, r.home_raw)[0] for r in new_ok],
                            away_entity_id=[res.resolve("openligadb", COMP, r.away_raw)[0] for r in new_ok], home_team_name=[r.home_raw for r in new_ok], away_team_name=[r.away_raw for r in new_ok],
                            tier=1.0, competition_type="domestic_league", regular_round_robin_stage=True, rated=True, gh=[float(r.regulation_home) for r in new_ok], ga=[float(r.regulation_away) for r in new_ok],
                            provenance=["OpenLigaDB matchID " + r.source_ref + " retrieved " + r.retrieved_utc for r in new_ok]))
    refreshed = pd.concat([V, add], ignore_index=True)
    refreshed.to_pickle(os.path.join(outdir, "isolated_refreshed_universe_openligadb_only.pkl"))
    import e4_prospective_logger as E
    upc = fx[(fx.competition_id == COMP) & (fx.status == "upcoming")].copy()
    recovered_pairs = {(r["home"], r["away"]) for r in []}
    rec_keys = set()
    if "recovered" in out:
        for r in out["recovered"].itertuples():
            rec_keys.add((r.home, r.away))
    still = pnr.copy()
    ent = {}
    for r in recs:
        he = res.resolve("openligadb", COMP, r.home_raw)[0]; ae = res.resolve("openligadb", COMP, r.away_raw)[0]
        if r.status == "completed": ent[(he, ae)] = True
    still = still[~still.apply(lambda x: (x.home_entity_id, x.away_entity_id) in ent, axis=1)]
    pnr_f = still.assign(comp=COMP, h=still.home_entity_id, a=still.away_entity_id)[["comp", "h", "a"]]
    fxd = pd.DataFrame(dict(fixture_id=(upc.competition_id + "|" + upc.match_date.astype(str) + "|" + upc.home_team).values, dt=pd.to_datetime(upc.match_date).values, h=upc.home_entity_id.values, a=upc.away_entity_id.values,
                            comp=upc.competition_id.values, season=upc.season.values, tier=upc.tier.values, home_name=upc.home_team.values, away_name=upc.away_team.values,
                            kickoff=(upc.match_date.astype(str) + " " + upc.kickoff_local.fillna("00:00")).values, kickoff_known=upc.kickoff_local.notna().values))
    recs_e, rej = E.predict(fxd, refreshed, past_no_result=pnr_f, snapshot_id="isolated_pilot_openligadb_only", snapshot_sha="n/a", mode="dry_run", now=now_utc)
    R = pd.DataFrame(recs_e)
    reasons = R.eligibility_reasons.explode().astype(str).str.replace(r"\(gap_days=\d+\)", "", regex=True).value_counts().to_dict() if len(R) else {}
    rep["bundesliga_eligibility_dry_run"] = dict(fixtures_checked=len(fxd), logged_in_dry_run=len(R), rejected_by_timing=len(rej), primary_eligible=int(R.primary_eligible.sum()) if len(R) else 0, failing_checks=reasons,
                                                 note="dry run only; nothing was logged officially and the official feature store was not updated; features computed from an isolated universe copy")
    return rep


def write_report(rep, outdir):
    json.dump(rep, open(os.path.join(outdir, "pilot_validation_report.json"), "w", encoding="utf-8"), indent=1, default=str)


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("plan"); r = sp.add_parser("run"); r.add_argument("--plan-sha256", required=True); sp.add_parser("rehearse")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.cmd == "plan":
        os.makedirs(PILOT_DIR, exist_ok=True)
        p = os.path.join(PILOT_DIR, "request_plan_r1.json")
        if not os.path.exists(p):
            json.dump(PLAN, open(p, "w", encoding="utf-8"), indent=1)
        print(json.dumps(PLAN, indent=1)); print("PLAN_SHA256", plan_sha())
        return
    cfg = common.AdapterConfig.load()
    if a.cmd == "run":
        if a.plan_sha256 != plan_sha():
            sys.exit("plan sha256 does not match the proposed plan: not approved, nothing sent")
        if not cfg.contact_configured():
            sys.exit("pilot aborted: contact not configured (env FOOTIQ_CONTACT or config/contact.local)")
        rid = "run_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()); out = os.path.join(PILOT_DIR, rid); os.makedirs(out)
        try:
            recs, season, rep, info = run_pilot(cfg, out)
        except Exception as e:
            sys.exit("pilot aborted: " + cfg.redact(str(e)))
        write_report(analyse(recs, season, rep, info, out, datetime.now(timezone.utc)), out)
        print("done", out)


if __name__ == "__main__":
    main()
