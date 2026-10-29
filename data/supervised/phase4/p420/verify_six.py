"""Phase 4.20 part D: GET-only validation of the running backend for all six competitions (no writes, no provider request)."""
import json
import urllib.error
import urllib.parse
import urllib.request

B = "http://127.0.0.1:8000"


def get(path):
    try:
        with urllib.request.urlopen(B + path, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


out = {}
s, comps = get("/api/competitions")
keys = [c["key"] for c in comps]
out["competitions"] = keys
out["health"] = get("/api/health")[1]
fresh = {c["key"]: (c["latest_result"], c["data_status"]) for c in get("/api/data-freshness")[1]}
rows = {}
for k in keys:
    r = {}
    s, m = get(f"/api/matches?comp={k}&status=all&limit=1")
    r["hub"] = (s, m["counts"] if m else None, m["scope"]["seasons"] if m else None, len(m["facets"]["teams"]) if m else None)
    s, seasons = get(f"/api/competitions/{k}/seasons")
    season = seasons[0] if seasons else None
    s, d = get(f"/api/competitions/{k}/dashboard?season={season}")
    r["dashboard"] = (s, d["summary"]["matches"], bool(d.get("standings")) if k != "UCL" else "league-phase endpoint")
    s, t = get(f"/api/competitions/{k}/teams")
    names = [x if isinstance(x, str) else x.get("team") or x.get("name") for x in (t if isinstance(t, list) else t.get("teams", []))]
    s, pr = get(f"/api/predict?key={k}&home={urllib.parse.quote(names[0])}&away={urllib.parse.quote(names[1])}")
    r["predict"] = (s, pr.get("validation_badge") if pr else None)
    s, tm = get(f"/api/team?key={k}&team={urllib.parse.quote(names[0])}")
    r["team"] = s
    s, an = get(f"/api/competitions/{k}/coverage")
    r["coverage"] = s
    r["freshness"] = fresh.get(k)
    rows[k] = r
out["per_competition"] = rows
s, lp = get("/api/competitions/UCL/league-phase?season=2026-27")
out["ucl_league_phase"] = (s, lp["matches_played"], lp["matches_expected"], lp["teams"], lp["criteria_applied"])
s, runs = get("/api/season/runs?key=BUNDESLIGA&season=2026-27")
s2, runs2 = get("/api/season/runs?key=LALIGA&season=2026-27")
out["saved_simulations"] = (runs, runs2)
out["archived_404"] = {k: (get(f"/api/competitions/{k}/teams")[0], get(f"/api/matches?comp={k}")[0]) for k in ("UEL", "UECL", "WC", "UNL", "COPA")}
s, st = get("/api/sync/status")
out["sync"] = dict(mode=st["sync_mode"], approved=st["approved_sources"], last=[(c["kind"], c["started_utc"], c["outcome"], c["requests"]) for c in st["recent_checks"][:2]])
s, all6 = get("/api/matches?status=all&limit=50")
out["hub_all"] = (s, all6["scope"]["competitions"], all6["counts"])
print(json.dumps(out, indent=1, default=str, ensure_ascii=False))
