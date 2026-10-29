"""Phase 4.16: read-only end-to-end check of the five domestic leagues through the LOCAL backend's GET endpoints (no POST: nothing is predicted-and-saved, no provider request)."""
import json
import urllib.error
import urllib.parse
import urllib.request

API = "http://127.0.0.1:8000"


def get(path, **p):
    url = API + path + ("?" + urllib.parse.urlencode(p) if p else "")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


out = {}
for k in ("BUNDESLIGA", "LALIGA", "EPL", "SERIEA", "LIGUE1"):
    r = {}
    st, secs = get(f"/api/competitions/{k}/seasons")
    season = secs[0]
    st, dash = get(f"/api/competitions/{k}/dashboard", season=season)
    r["dashboard"] = st
    r["table_rows"] = len(dash["standings"]) if st == 200 else None
    r["played_in_table"] = sum(x.get("played", x.get("P", 0)) for x in dash["standings"]) // 2 if st == 200 else None
    st, up = get("/api/matches", comp=k, status="upcoming", limit=3)
    r["upcoming_status"] = st
    nxt = (up.get("matches") or up.get("items") or [None])[0] if st == 200 and isinstance(up, dict) else None
    st, comp = get("/api/matches", comp=k, status="completed", limit=2)
    r["completed_status"] = st
    c0 = (comp.get("matches") or comp.get("items") or [None])[0] if st == 200 and isinstance(comp, dict) else None
    r["latest_completed"] = dict(date=c0["date"], match=f"{c0['home']['name']} v {c0['away']['name']}", result=c0.get("result")) if c0 else None
    r["counts"] = (comp or {}).get("counts")
    if nxt:
        r["next_fixture"] = dict(date=nxt["date"], match=f"{nxt['home']['name']} v {nxt['away']['name']}", kickoff=nxt["kickoff"].get("utc"), status=nxt["status"])
        st, p = get("/api/predict", key=k, home=nxt["home"]["name"], away=nxt["away"]["name"], date=nxt["date"])
        r["predict_next_fixture"] = dict(status=st, probs=[round(p[x], 3) for x in ("p_home", "p_draw", "p_away") if p and x in p] if st == 200 else None, notes=(p or {}).get("notes", [])[:2] if st == 200 else None)
    st, gws = get("/api/gameweeks", key=k)
    r["gameweeks"] = st
    out[k] = r
st, feat = get("/api/featured-fixture")
out["featured_fixture"] = dict(status=st, record=(feat or {}).get("featured", {}) and feat["featured"].get("record_id"), freshness_keys=sorted((feat or {}).get("freshness", {}).keys())[:8] if isinstance((feat or {}).get("freshness"), dict) else str((feat or {}).get("freshness"))[:200])
st, sy = get("/api/sync/status")
out["sync"] = dict(status=st, mode=sy.get("sync_mode"), scheduler=sy["scheduler"]["status"], threads=sy["scheduler"]["active_scheduler_threads"], enabled=sy["scheduler"]["enabled_competitions"])
print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
