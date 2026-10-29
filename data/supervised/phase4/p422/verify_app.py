"""Phase 4.22: GET-only checks of the restarted backend after the import (no writes, no provider request)."""
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
out["health"] = get("/api/health")
s, comps = get("/api/competitions")
keys = [c["key"] for c in comps]
out["competitions"] = keys
fresh = {c["key"]: dict(latest=c["latest_result"], status=c["data_status"], warnings=[w["text"] for w in c["warnings"]]) for c in get("/api/data-freshness")[1]}
per = {}
for k in keys:
    r = {}
    s, d = get(f"/api/competitions/{k}/dashboard?season=2026-27")
    r["dashboard"] = (s, d["summary"]["matches"])
    if k != "UCL":
        st = d["standings"]
        r["standings"] = dict(teams=len(st), games_counted=sum(x["played"] for x in st) // 2, top3=[(x.get("team"), x["played"], x["points"]) for x in st[:3]])
    s, t = get(f"/api/competitions/{k}/teams")
    names = [x if isinstance(x, str) else x.get("team") or x.get("name") for x in (t if isinstance(t, list) else t.get("teams", []))]
    s, p = get(f"/api/predict?key={k}&home={urllib.parse.quote(names[0])}&away={urllib.parse.quote(names[1])}")
    pr = (p or {}).get("probabilities") or {}
    r["predict"] = (s, p.get("validation_badge") if p else None, round(sum(v for v in pr.values() if isinstance(v, (int, float))), 6) if pr else sorted((p or {}).keys())[:12])
    r["team_page"] = get(f"/api/team?key={k}&team={urllib.parse.quote(names[0])}")[0]
    s, m = get(f"/api/matches?comp={k}&status=all&limit=1")
    r["hub_counts"] = m["counts"]
    r["freshness"] = fresh[k]
    per[k] = r
out["per_competition"] = per
hub = {}
s, d = get("/api/matches?comp=UCL&status=upcoming&limit=50")
hub["upcoming"] = dict(counts=d["counts"], statuses=sorted({i["status"] for i in d["items"]}), first=[(i["date"], i["matchday_no"], i["home"]["name"], i["away"]["name"]) for i in d["items"][:3]], badge=sorted({i["validation_badge"] for i in d["items"]}))
s, d = get("/api/matches?comp=UCL&status=upcoming&matchday=5&limit=50")
hub["matchday5"] = dict(n=len(d["items"]), dates=sorted({i["date"] for i in d["items"]}))
s, d = get("/api/matches?comp=UCL&status=all&team=CLUB:ENG:arsenal-fc&limit=50")
hub["arsenal"] = dict(counts=d["counts"], rows=[(i["matchday_no"], i["status"], i["home"]["name"], i["away"]["name"]) for i in d["items"]])
s, d = get("/api/matches?comp=UCL&status=completed&limit=50")
hub["completed"] = dict(counts=d["counts"], statuses=sorted({i["status"] for i in d["items"]}))
s, d = get("/api/matches?status=upcoming&limit=50")
hub["all_six_upcoming"] = dict(counts=d["counts"], scope=d["scope"]["competitions"])
s, d = get("/api/matches?comp=UCL&status=awaiting_result&limit=5")
hub["awaiting"] = d["counts"]["awaiting_result"]
out["ucl_hub"] = hub
s, pr = get("/api/predict?key=UCL&home=Arsenal%20FC&away=Borussia%20Dortmund&date=2026-11-24")
out["ucl_prediction_for_stored_fixture"] = dict(status=s, badge=(pr or {}).get("validation_badge"), notes=(pr or {}).get("note") or (pr or {}).get("notes"), keys=sorted((pr or {}).keys())[:14])
s, lp = get("/api/competitions/UCL/league-phase?season=2026-27")
out["ucl_league_phase"] = dict(played=lp["matches_played"], in_data=lp["matches_in_data"], expected=lp["matches_expected"], teams=lp["teams"], criteria=lp["criteria_applied"], top3=[(r["position"], r["team"], r["played"], r["points"]) for r in lp["table"][:3]])
out["saved_simulations"] = [get(f"/api/season/runs?key={k}&season=2026-27")[1] for k in ("BUNDESLIGA", "LALIGA")]
out["archived"] = {k: (get(f"/api/competitions/{k}/teams")[0], get(f"/api/matches?comp={k}")[0]) for k in ("UEL", "UECL", "WC", "UNL", "COPA")}
s, st = get("/api/sync/status")
out["sync"] = dict(mode=st["sync_mode"], approved=st["approved_sources"], recent=[(c["kind"], c["started_utc"], c["outcome"], c["requests"]) for c in st["recent_checks"][:2]],
                   states={c["competition_key"]: c["state"] for c in st["competitions"]})
(__import__("pathlib").Path(__file__).resolve().parent / "verify_app_out.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
print(json.dumps(out, indent=1, default=str, ensure_ascii=False))
