"""Phase 4.37: live verification of the application started from the SIMULATED CLONE (final proposed contents only). Usage: verify_clone.py <base_url> <out.json>
GET checks for the six competitions + predictions + simulator status, then (private clone store only) a points-only Monte Carlo run per domestic league. Nothing here touches production."""
import json, sys, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, "D:/Foot IQ/app")
B = sys.argv[1].rstrip("/")
checks = []


def call(path, body=None):
    req = urllib.request.Request(B + path, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def ok(n, c, d=""):
    checks.append(dict(name=n, ok=bool(c), detail=str(d)[:200]))


s, h = call("/api/health"); ok("health ok, club models ready", s == 200 and h["club_prediction_ready"], h)
s, comps = call("/api/competitions"); keys = [c["key"] for c in comps]
ok("exactly the six competitions", keys == ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL"], keys)
for k in keys:
    s, ss = call(f"/api/competitions/{k}/seasons"); season = ss[0]
    s, d = call(f"/api/competitions/{k}/dashboard?season={season}")
    ok(f"{k} dashboard", s == 200 and d, f"season {season}")
    s, up = call(f"/api/matches?comp={k}&status=upcoming&limit=50"); s2, done = call(f"/api/matches?comp={k}&status=completed&limit=3")
    ok(f"{k} upcoming and completed fixtures", s == 200 and s2 == 200 and up["items"] and done["items"], f"{up['counts']}")
    import datetime
    it = next(x for x in up["items"] if x["date"] > datetime.date.today().isoformat())      # a fixture dated after today (same-day fixtures are not predicted)
    q = urllib.parse.urlencode(dict(key=k, home=it["home"]["name"], away=it["away"]["name"], date=it["date"]))
    s, p = call("/api/predict?" + q)
    if p is None:
        ok(f"{k} prediction", False, f"HTTP {s} {it}")
    else:
        pr = p["primary"]; tot = pr["home"] + pr["draw"] + pr["away"]
        ok(f"{k} prediction (probabilities sum to 1, secondary and Elo present)", abs(tot - 1) < 1e-6 and p["secondary"] and p["elo_only"], f"{it['date']} H{pr['home']:.3f} D{pr['draw']:.3f} A{pr['away']:.3f}; {p['validation_badge']}")
s, a = call("/api/matches?comp=UCL&status=all&limit=1"); ok("UCL 54 completed + 90 scheduled", a["counts"]["completed"] == 54 and a["counts"]["upcoming"] == 90, a["counts"])
for k in ("UEL", "UECL", "WC", "UNL", "COPA"):
    ok(f"archived {k} excluded", call(f"/api/competitions/{k}/teams")[0] == 404 and call(f"/api/predict?key={k}&home=A&away=B")[0] == 404)
states = {}
for k in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"):
    s, st = call(f"/api/season/status?key={k}")
    states[k] = (st["state"], st["points_only"], st["counts"], st["missing_share"])
    ok(f"{k} simulator eligibility", s == 200 and st["points_only"].get("can_run", st["points_only"]) , f"{st['state']}; points_only {json.dumps(st['points_only'])[:110]}; counts {st['counts']}")
s, st = call("/api/season/status?key=UCL"); ok("UCL season simulator not offered", s in (404, 422) or (st and not st.get("can_simulate", False) and not st["points_only"].get("can_run", False)), f"HTTP {s}")
POINTS = "Run points-only simulation"
for k in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"):
    from seasonsim import service as S
    s, r = call("/api/season/points", dict(key=k, season="2026-27", simulations=1000, seed=7, user_action=S.POINTS_ACTION))
    ok(f"{k} Monte Carlo points-only run (1,000 simulations, private clone store)", s == 200 and r, f"HTTP {s}; keys {list(r.keys())[:6] if r else ''}")
w = max(len(c["name"]) for c in checks)
for c in checks:
    print(("PASS " if c["ok"] else "FAIL ") + c["name"].ljust(w) + "  " + c["detail"])
print(f"\n{sum(c['ok'] for c in checks)} of {len(checks)} checks passed")
json.dump(dict(base=B, checks=checks, states={k: str(v) for k, v in states.items()}), open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
