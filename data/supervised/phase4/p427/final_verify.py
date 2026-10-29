"""Phase 4.27 part B: GET-only verification of the running application (default http://127.0.0.1:8000; pass another base URL as the first argument) for the six competitions. No write, no provider request.
Writes final_verify_<port>.json and prints a pass/fail table."""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

B = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
HERE = Path(__file__).resolve().parent
KEYS = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"]
EXPECT_COMPLETED = dict(EPL=80, LALIGA=99, BUNDESLIGA=63, SERIEA=80, LIGUE1=72, UCL=54)
checks, details = [], {}


def get(path):
    try:
        with urllib.request.urlopen(B + path, timeout=180) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def ok(name, cond, detail=""):
    checks.append((name, bool(cond), str(detail)[:160]))


s, h = get("/api/health")
ok("health ok and club models ready", s == 200 and h["status"] == "ok" and h["club_prediction_ready"], h)
s, comps = get("/api/competitions")
ok("exactly the six competitions", [c["key"] for c in comps] == KEYS, [c["key"] for c in comps])
fresh = {c["key"]: c for c in get("/api/data-freshness")[1]}
for k in KEYS:
    d = {}
    s, seasons = get(f"/api/competitions/{k}/seasons")
    season = seasons[0]
    s, dash = get(f"/api/competitions/{k}/dashboard?season={season}")
    ok(f"{k} dashboard", s == 200 and dash["summary"]["matches"] == EXPECT_COMPLETED[k], f"{dash['summary']['matches']} matches (expected {EXPECT_COMPLETED[k]})")
    ok(f"{k} results listed on the dashboard", len(dash["results"]) > 0, f"{len(dash['results'])} recent results, newest {dash['results'][0]['date']}")
    s, done = get(f"/api/matches?comp={k}&status=completed&limit=5")
    ok(f"{k} match results (hub)", s == 200 and done["counts"]["completed"] == EXPECT_COMPLETED[k] and done["items"] and all(i["result"] for i in done["items"]), done["counts"])
    s, up = get(f"/api/matches?comp={k}&status=upcoming&limit=10")
    today = up["today_utc"]
    up["items"] = [i for i in up["items"] if i["date"] > today] or up["items"]          # a fixture dated today cannot be forecast (its kickoff time zone is unverified): the demo uses the next later day
    ok(f"{k} upcoming fixtures", s == 200 and up["counts"]["upcoming"] > 0 and up["items"] and all(i["status"] == "scheduled" for i in up["items"]), f"{up['counts']['upcoming']} upcoming, next {up['items'][0]['date']} {up['items'][0]['home']['name']} v {up['items'][0]['away']['name']}")
    if k == "UCL":
        s, lp = get("/api/competitions/UCL/league-phase?season=2026-27")
        ok("UCL league-phase table", s == 200 and lp["teams"] == 36 and lp["matches_played"] == 54 and all(r["played"] == 3 for r in lp["table"]), f"{lp['teams']} clubs, {lp['matches_played']} played, provisional: {not lp['complete']}")
        d["table_top3"] = [(r["position"], r["team"], r["played"], r["points"], r["gd"]) for r in lp["table"][:3]]
    else:
        st = dash["standings"]
        ok(f"{k} standings", len(st) >= 18 and sum(x["played"] for x in st) // 2 == EXPECT_COMPLETED[k], f"{len(st)} clubs, {sum(x['played'] for x in st) // 2} games counted")
        d["table_top3"] = [(r["team"], r["played"], r["points"]) for r in st[:3]]
    s, t = get(f"/api/competitions/{k}/teams")
    names = [x if isinstance(x, str) else x.get("name") for x in (t if isinstance(t, list) else t.get("teams", []))]
    home, away = up["items"][0]["home"]["name"], up["items"][0]["away"]["name"]
    s, tm = get(f"/api/team?key={k}&team={urllib.parse.quote(home)}")
    ok(f"{k} team information and statistics", s == 200 and tm and "form" in tm, f"{home}: {list(tm.keys()) if tm else None}")
    q = urllib.parse.urlencode(dict(key=k, home=home, away=away, date=up["items"][0]["date"]))
    s, p = get("/api/predict?" + q)
    if p is None:
        ok(f"{k} prediction for the next stored fixture", False, f"HTTP {s} for {home} v {away} on {up['items'][0]['date']}")
        ok(f"{k} prediction label", False, "no prediction")
        probs = [0, 0, 0]
        p = dict(primary=dict(model="-"), secondary=dict(model="-"))
    else:
        probs = [p["primary"]["home"], p["primary"]["draw"], p["primary"]["away"]]
        ok(f"{k} prediction for the next stored fixture", s == 200 and abs(sum(probs) - 1) < 1e-6 and p["secondary"] and p["elo_only"], f"{home} v {away}: H {probs[0]:.3f} D {probs[1]:.3f} A {probs[2]:.3f}; models {p['primary']['model'][:12]} / {p['secondary']['model'][:14]}")
        want = "Not validated (indicative only)" if k == "UCL" else "Validated"
        ok(f"{k} prediction label", p["validation_badge"] == want, p["validation_badge"])
    f = fresh[k]
    ok(f"{k} data freshness indicator", f["latest_result"] and f["data_status"] in ("startup_updated", "historical_only"), f"{f['data_status']}, newest result {f['latest_result']}")
    d.update(prediction=dict(home=home, away=away, probs=[round(x, 3) for x in probs]), freshness=f["data_status_label"], latest=f["latest_result"], next_fixture=(up["items"][0]["date"], home, away))
    details[k] = d
s, allup = get("/api/matches?comp=UCL&status=all&limit=1")
ok("UCL 54 completed + 90 scheduled league-phase fixtures", allup["counts"]["completed"] == 54 and allup["counts"]["upcoming"] == 90 and allup["counts"]["awaiting_result"] == 0 and allup["counts"]["all"] == 144, allup["counts"])
s, mds = get("/api/matches?comp=UCL&status=all&limit=1")
ok("UCL matchday and team filters", get("/api/matches?comp=UCL&status=upcoming&matchday=5&limit=50")[1]["counts"]["upcoming"] == 18 and len(get("/api/matches?comp=UCL&status=upcoming&matchday=5&limit=50")[1]["items"]) == 18
   and get("/api/matches?comp=UCL&status=all&team=CLUB:ENG:arsenal-fc&limit=50")[1]["counts"]["all"] == 8, "matchday 5 = 18 fixtures; Arsenal = 8 matches")
for run, key in ((1, "BUNDESLIGA"), (2, "LALIGA")):
    s, r = get(f"/api/season/run?id={run}")
    ok(f"saved simulation {run} ({key}) retrievable", s == 200 and r["competition_key"] == key and r["assumptions"]["simulations"] == 10000, f"{r['assumptions']['label'] if r else ''}, seed {r['assumptions']['seed'] if r else ''}")
    details[f"simulation_{run}"] = dict(key=key, seed=r["assumptions"]["seed"], model=r["assumptions"]["models"]["primary"])
for k in ("UEL", "UECL", "WC", "UNL", "COPA"):
    ok(f"archived {k} excluded", get(f"/api/competitions/{k}/teams")[0] == 404 and get(f"/api/matches?comp={k}")[0] == 422 and get(f"/api/predict?key={k}&home=A&away=B")[0] == 404)
s, st = get("/api/sync/status")
ok("synchronisation startup-only, OpenLigaDB only", st["sync_mode"] == "startup" and st["approved_sources"] == ["openligadb"], f"{st['sync_mode']} {st['approved_sources']}")
s, meta = get("/api/meta")
ok("meta lists club models only and the attribution", s == 200 and "wikipedia" in json.dumps(meta).lower() and "openligadb" in json.dumps(meta).lower())
w = max(len(c[0]) for c in checks)
for n, c, d in checks:
    print(("PASS " if c else "FAIL ") + n.ljust(w) + "  " + d)
print(f"\n{sum(c for _, c, _ in checks)} of {len(checks)} checks passed")
(HERE / f"final_verify_{B.rsplit(':', 1)[-1]}.json").write_text(json.dumps(dict(base=B, checks=[dict(name=n, ok=c, detail=d) for n, c, d in checks], details=details), indent=1, ensure_ascii=False, default=str), encoding="utf-8")
