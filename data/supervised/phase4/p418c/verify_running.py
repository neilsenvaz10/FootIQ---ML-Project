"""Phase 4.18C: GET-only checks of the running backend (read-only; no writes, no provider requests)."""
import json
import urllib.error
import urllib.parse
import urllib.request

B = "http://127.0.0.1:8000"


def get(path):
    try:
        with urllib.request.urlopen(B + path, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


out = {}
s, comps = get("/api/competitions")
keys = [c["key"] for c in comps]
out["competitions"] = (s, keys)
out["health"] = get("/api/health")
archived = ["UEL", "UECL", "WC", "UNL", "COPA"]
res = {}
for k in archived:
    for p in (f"/api/competitions/{k}/teams", f"/api/competitions/{k}/seasons", f"/api/competitions/{k}/dashboard?season=2026-27", f"/api/competitions/{k}/coverage"):
        res[p] = get(p)[0]
res["/api/worldcup/simulate"] = get("/api/worldcup/simulate")[0]
res["/api/worldcup/bracket"] = get("/api/worldcup/bracket")[0]
out["archived_status_codes"] = res
preds = {}
for k in keys:
    s, t = get(f"/api/competitions/{k}/teams")
    teams = [x if isinstance(x, str) else x.get("team") or x.get("name") for x in (t if isinstance(t, list) else t.get("teams", []))]
    a, b = teams[0], teams[1]
    q = urllib.parse.urlencode(dict(key=k, home=a, away=b))
    s, p = get("/api/predict?" + q)
    if s != 200:
        preds[k] = (s, a, b)
    else:
        pr = p.get("probabilities") or p.get("v2_r1") or p
        preds[k] = (s, a, b, json.dumps(p)[:260])
out["predictions"] = preds
s, runs = get("/api/season/runs?key=BUNDESLIGA&season=2026-27")
out["season_runs"] = (s, runs if not isinstance(runs, list) else [{k: r.get(k) for k in ("simulation_run_id", "competition_key", "season", "n_simulations")} for r in runs])
out["freshness"] = get("/api/data-freshness")
out["sync_status"] = get("/api/sync/status")
out["league_phase_UCL"] = get("/api/competitions/UCL/league-phase")[0]
print(json.dumps(out, indent=1, default=str)[:9000])
