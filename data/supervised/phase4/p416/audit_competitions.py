"""Phase 4.16: READ-ONLY audit of the 11 mini-project competitions (5 domestic leagues + 6 international/continental). Reads data/miniproject/matches.csv, the production store (mode=ro)
and the local backend's GET endpoints. Makes no provider request, writes nothing but its own report next to this file."""
import json
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
import config as C  # noqa: E402

API = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent / "audit_report.json"


def get(path, **params):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:  # noqa: BLE001
            return e.code, None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


m = pd.read_csv(C.MATCHES_CSV, low_memory=False)
m["date"] = pd.to_datetime(m["date"])
db = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
report = {}
for comp in C.COMPETITIONS:
    k = comp["key"]
    d = m[m.competition_key == k]
    dup = int(d.duplicated(subset=["season", "date", "home", "away"]).sum())
    dup_pair_day = int(d.duplicated(subset=["date", "home", "away"]).sum())
    scored = d[d.home_goals.notna() & d.away_goals.notna()]
    seasons = sorted(d.season.astype(str).unique())
    latest = str(scored.date.max().date()) if len(scored) else None
    teams = sorted(set(d.home) | set(d.away))
    ent_missing = int(d.home_entity_id.isna().sum() + d.away_entity_id.isna().sum())
    rec = dict(name=comp["name"], group=comp["group"], model=comp["model"], badge=comp["badge"], rows=len(d), scored=len(scored), seasons=len(seasons), first_season=seasons[0] if seasons else None, last_season=seasons[-1] if seasons else None,
               first_date=str(d.date.min().date()), latest_result_in_dataset=latest, duplicate_rows_same_season_date_pair=dup, duplicate_rows_same_date_pair=dup_pair_day, distinct_teams=len(teams),
               rows_without_entity_id=ent_missing, outcome_basis=d.outcome_basis.value_counts().to_dict(), source=d.source.astype(str).str.slice(0, 40).value_counts().head(4).to_dict(), licences=sorted(d.licence.dropna().astype(str).str.slice(0, 60).unique())[:4])
    # production store (the live data layer: matches, sync)
    r = db.execute("SELECT COUNT(*) n, MAX(CASE WHEN status IN ('completed','awarded') THEN match_date END) latest FROM matches WHERE competition_key=?", (k,)).fetchone()
    rec["store_rows"], rec["store_latest_result"] = r["n"], r["latest"]
    # API support
    api = {}
    st, secs = get(f"/api/competitions/{k}/seasons")
    api["seasons"] = st
    last_season = secs[0] if st == 200 and isinstance(secs, list) and secs else None
    st, cov = get(f"/api/competitions/{k}/coverage")
    api["coverage"] = st
    if st == 200:
        rec["coverage_incomplete_seasons"] = [dict(season=x["season"], rows=x["rows_in_dataset"], expected=x["expected_matches"], pct=x["coverage_pct"]) for x in cov if x.get("note") == "incomplete or in progress"]
    st, tm = get(f"/api/competitions/{k}/teams", **({"season": last_season} if last_season else {}))
    api["teams"] = st
    if last_season:
        st, dash = get(f"/api/competitions/{k}/dashboard", season=last_season)
        api["dashboard"] = st
        api["dashboard_has_standings"] = bool(st == 200 and dash.get("standings"))
    # prediction: a real pair from the latest season in the dataset
    pred = {}
    if st and len(scored):
        ds = scored[scored.season.astype(str) == str(last_season)] if last_season else scored
        row = (ds if len(ds) else scored).sort_values("date").iloc[-1]
        q = dict(key=k, home=row.home, away=row.away)
        if comp["kind"] == "intl":
            q["venue"] = "neutral"
        s2, p = get("/api/predict", **q)
        pred = dict(status=s2, pair=f"{row.home} v {row.away}", detail=(p if s2 != 200 else {x: p.get(x) for x in ("model", "model_family", "badge", "p_home", "p_draw", "p_away", "label", "prediction", "confidence", "gate", "notes", "warnings", "data_end", "caveats") if x in p}))
        if s2 == 200:
            pred["keys"] = sorted(p.keys())[:30]
    rec["api"] = api
    rec["predict"] = pred
    report[k] = rec
# international feature inputs
elo = pd.read_csv(ROOT / "data" / "processed" / "team_elo_latest.csv")
im = ROOT / "data" / "processed" / "international_matches.csv"
raw = pd.read_csv(C.INTL_RESULTS)
report["_intl_inputs"] = dict(team_elo_latest_rows=len(elo), team_elo_columns=list(elo.columns)[:8], raw_results_rows=len(raw), raw_results_last_date=str(raw.date.max()), international_matches_csv_exists=im.exists(),
                              raw_nations_league_last=str(raw[raw.tournament == "UEFA Nations League"].date.max()), raw_copa_last=str(raw[raw.tournament == "Copa América"].date.max()),
                              raw_wc_2026_rows=int(((raw.tournament == "FIFA World Cup") & (raw.date.astype(str) >= "2026-01-01")).sum()), raw_wc_2026_scored=int(((raw.tournament == "FIFA World Cup") & (raw.date.astype(str) >= "2026-01-01") & raw.home_score.notna()).sum()))
OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
for k, v in report.items():
    if k.startswith("_"):
        print(k, v)
        continue
    print(f"== {k}: rows {v['rows']} scored {v['scored']} seasons {v['seasons']} ({v['first_season']}..{v['last_season']}) latest {v['latest_result_in_dataset']} store_latest {v['store_latest_result']} dup {v['duplicate_rows_same_season_date_pair']}/{v['duplicate_rows_same_date_pair']} teams {v['distinct_teams']} no-entity {v['rows_without_entity_id']}")
    print("   api", v["api"], "| incomplete", v.get("coverage_incomplete_seasons"))
    print("   predict", v["predict"].get("status"), v["predict"].get("pair"), str(v["predict"].get("detail"))[:260])
