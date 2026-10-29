"""Phase 4.24: GET-only check that the corrected dates and results show in the running application (hub, dashboard, standings)."""
import json
import urllib.parse
import urllib.request

B = "http://127.0.0.1:8000"


def get(path):
    with urllib.request.urlopen(B + path, timeout=120) as r:
        return json.loads(r.read())


out = {}
epl = get("/api/matches?comp=EPL&status=upcoming&matchday=10&limit=50")
want = {("Everton FC", "Coventry City FC"): "2026-11-06", ("Crystal Palace FC", "Liverpool FC"): "2026-11-08", ("Sunderland AFC", "Chelsea FC"): "2026-11-08"}
out["epl_matchday10_corrected"] = {f"{h} v {a}": next((i["date"] for i in epl["items"] if i["home"]["name"] == h and i["away"]["name"] == a), None) for (h, a) in want}
out["epl_matchday10_expected"] = {f"{h} v {a}": d for (h, a), d in want.items()}
out["epl_matchday10_dates"] = sorted({i["date"] for i in epl["items"]})
for key, home, away, exp in (("LALIGA", "Deportivo Alavés", "Málaga CF", "2026-10-23"), ("LALIGA", "Rayo Vallecano de Madrid", "Elche CF", "2026-10-24"), ("LALIGA", "Sevilla FC", "CA Osasuna", "2026-10-26"),
                             ("LIGUE1", "Toulouse FC", "ES Troyes AC", "2026-10-25"), ("LIGUE1", "Paris Saint-Germain FC", "Olympique Lyonnais", "2026-10-26"), ("SERIEA", "SSC Napoli", "AS Roma", "2026-10-24"),
                             ("EPL", "Chelsea FC", "Tottenham Hotspur FC", "2026-10-24")):
    res = get(f"/api/matches?comp={key}&status=completed&limit=50&order=desc")
    row = next((i for i in res["items"] if i["home"]["name"] == home and i["away"]["name"] == away), None)
    if row is None:
        res = get(f"/api/matches?comp={key}&status=completed&limit=50&order=desc&cursor={res['page']['next_cursor']}") if res["page"]["next_cursor"] else res
        row = next((i for i in res["items"] if i["home"]["name"] == home and i["away"]["name"] == away), None)
    out[f"{key} {home} v {away}"] = dict(found=bool(row), date=row and row["date"], expected=exp, result=row and (row["result"]["home_goals"], row["result"]["away_goals"]), status=row and row["status"], source=row and row["source"])
standings = {}
for k in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"):
    d = get(f"/api/competitions/{k}/dashboard?season=2026-27")
    st = d["standings"]
    standings[k] = dict(matches=d["summary"]["matches"], games=sum(x["played"] for x in st) // 2, top3=[(x["team"], x["played"], x["points"]) for x in st[:3]])
out["standings"] = standings
out["hub_counts"] = {k: get(f"/api/matches?comp={k}&status=all&limit=1")["counts"] for k in ("EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1", "UCL")}
out["ucl"] = dict(hub=get("/api/matches?comp=UCL&status=upcoming&limit=3"), predict=get("/api/predict?key=UCL&home=" + urllib.parse.quote("Arsenal FC") + "&away=" + urllib.parse.quote("Borussia Dortmund") + "&date=2026-11-24"))
out["ucl"] = dict(counts=out["ucl"]["hub"]["counts"], first=[(i["date"], i["matchday_no"], i["home"]["name"], i["away"]["name"], i["status"]) for i in out["ucl"]["hub"]["items"]], badge=out["ucl"]["predict"]["validation_badge"])
print(json.dumps(out, indent=1, default=str, ensure_ascii=False))
