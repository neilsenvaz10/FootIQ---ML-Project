"""Dress rehearsal of the whole pilot against a LOCAL fake transport serving the stored 2026-10-21 OpenLigaDB snapshot. No network. Output is labelled rehearsal."""
import json, os, sys, time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pilot_openligadb as pilot
from footiq_sources import common

sys.stdout.reconfigure(encoding="utf-8")
body = open(os.path.join(ROOT, "evidence", "openligadb_bl1_2026.json"), "rb").read()
season = json.loads(body)
lg = {k: season[0][k] for k in ("leagueId", "leagueShortcut", "leagueSeason", "leagueName")}
kinds = sorted({r["resultTypeKind"] for m in season for r in m["matchResults"]})
requests_seen = []


def opener(url, headers):
    path = url.replace("https://api.openligadb.de", "")
    requests_seen.append((path, "contact" in json.dumps(headers).lower()))
    assert "User-Agent" in headers and "Bot/" in headers["User-Agent"]
    if path == "/getavailableleagues/2026":
        return 200, json.dumps([lg, dict(lg, leagueId=1, leagueShortcut="zz-test-decoy")]).encode(), {}
    if path == "/getresulttypes":
        return 200, json.dumps([{"resultTypeKind": k} for k in kinds]).encode(), {}
    if path == "/getmatchdata/bl1/2026":
        return 200, body, {"Content-Type": "application/json"}
    if path == "/getcurrentgroup/bl1":
        return 200, json.dumps({"groupOrderID": 10}).encode(), {}
    if path.startswith("/getlastchangedate/bl1/2026/"):
        g = int(path.rsplit("/", 1)[1])
        return 200, json.dumps(max(m["lastUpdateDateTime"] for m in season if m["group"]["groupOrderID"] == g)).encode(), {}
    return 404, b"", {}


cfg = common.AdapterConfig(live_enabled=False, contact="mailto:rehearsal@footiq-test.local")
out = os.path.join(pilot.PILOT_DIR, "rehearsal_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
now = datetime.now(timezone.utc)
recs, sea, rep, info = pilot.run_pilot(cfg, out, opener=opener, sleep=lambda s: None, now=now, label="rehearsal")
rep = pilot.analyse(recs, sea, rep, info, out, now)
rep["REHEARSAL_NOTE"] = "local fake transport serving the stored snapshot; not a live retrieval"
pilot.write_report(rep, out)
assert len(requests_seen) == 6 and [p for p, _ in requests_seen][2] == "/getmatchdata/bl1/2026"
print("requests:", [p for p, _ in requests_seen])
print(json.dumps({k: rep[k] for k in ("league_confirmed", "result_type_kinds", "http_attempts_used", "new_verified_results", "team_mapping_errors", "results_with_valid_kickoff_utc",
                                      "openfootball_fixtures_missing_in_source", "source_fixtures_not_in_openfootball", "bundesliga_eligibility_dry_run", "polling_probe")}, indent=1, default=str))
print(json.dumps(rep["integrity"], indent=1)); print(json.dumps(rep["reconciliation"], indent=1))
# no contact string anywhere in outputs
blob = ""
for r, _, fs in os.walk(out):
    for f in fs:
        if f.endswith((".json", ".csv", ".jsonl")):
            blob += open(os.path.join(r, f), encoding="utf-8", errors="ignore").read()
assert "rehearsal@footiq-test.local" not in blob, "contact leaked into outputs"
print("contact not present in any output file")
