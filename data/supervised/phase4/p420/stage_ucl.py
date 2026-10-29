"""Phase 4.20 part B: stage the Champions League 2026-27 league phase from the CURRENT Wikipedia revision downloaded today (staging/raw/wikipedia_ucl_league_phase_api.json), with the same parser
(FootIQ_ML_Data_Readiness/_build/wp_parse.py) and identity mapping as Phase 4.17. OFFLINE: reads files only, writes only under staging/. Then compares with the store and with the Phase 4.19 gate."""
import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "FootIQ_ML_Data_Readiness" / "_build"))
import wp_parse  # noqa: E402

api = json.loads((HERE / "staging" / "raw" / "wikipedia_ucl_league_phase_api.json").read_text(encoding="utf-8"))["query"]["pages"][0]
rev = api["revisions"][0]
wikitext = rev["slots"]["main"]["content"]
mp = pd.read_csv(ROOT / "FootIQ_ML_Data_Readiness" / "05_CANONICAL_TEAM_IDENTITY_MAPPING.csv")
mp = mp[mp.source_system == "wikipedia"].set_index("source_team_key")
rows = []
for m in wp_parse.parse_page(wikitext):
    mm = re.search(r"Matchday (\d+)", m["stage_path"])
    if not mm:
        continue
    ids = []
    for side in ("t1", "t2"):
        code = m[f"{side}_code"]
        tgt = m[f"{side}_target"] if isinstance(m[f"{side}_target"], str) else m[f"{side}_display"]
        r = mp.loc[f"WP:{code}:{tgt}"] if f"WP:{code}:{tgt}" in mp.index else None
        ids.append((r.canonical_team_id if r is not None and isinstance(r.canonical_team_id, str) else None, tgt))
    rows.append(dict(competition_key="UCL", season="2026-27", matchday=int(mm.group(1)), date=m["date"], home=ids[0][1], away=ids[1][1], home_entity=ids[0][0], away_entity=ids[1][0], home_goals=m["s1"], away_goals=m["s2"],
                     status="played" if m["s1"] is not None else "scheduled", page_revid=rev["revid"], page_timestamp=rev["timestamp"], page_url="https://en.wikipedia.org/wiki/" + api["title"].replace(" ", "_"),
                     retrieved="2026-10-28", licence="CC BY-SA 4.0 (Wikipedia): attribution and share-alike apply"))
new = pd.DataFrame(rows)
new.to_csv(HERE / "staging" / "uefa_2026_27_staging_v2.csv", index=False, encoding="utf-8-sig")
old = pd.read_csv(ROOT / "data" / "supervised" / "phase4" / "p417" / "uefa_2026_27_staging.csv", encoding="utf-8-sig")
old = old[old.competition_key == "UCL"]
c = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
store = {(r[0], r[1]): r[2:] for r in c.execute("SELECT home_entity_id, away_entity_id, match_date, home_goals_final, away_goals_final, status FROM matches WHERE competition_key='UCL' AND season='2026-27'")}
k = lambda df: {(r.home_entity, r.away_entity): (str(r.date), None if pd.isna(r.home_goals) else int(r.home_goals), None if pd.isna(r.away_goals) else int(r.away_goals), r.status) for r in df.itertuples()}
n, o = k(new), k(old)
rep = dict(revision=rev["revid"], revision_time=rev["timestamp"], rows=len(new), played=int((new.status == "played").sum()), by_matchday_played=new[new.status == "played"].matchday.value_counts().sort_index().to_dict(),
           unresolved_identities=int(new.home_entity.isna().sum() + new.away_entity.isna().sum()), teams=len(set(new.home_entity) | set(new.away_entity)),
           in_store=sum((h, a) in store for h, a in n), new_vs_old_staging=dict(same=sum(o.get(x) == v for x, v in n.items()), changed=[(x, o.get(x), v) for x, v in n.items() if o.get(x) != v][:60]),
           store_rows_that_differ_from_new=[(x, store[x], v) for x, v in n.items() if x in store and (store[x][0], store[x][1], store[x][2]) != v[:3] and store[x][3] == "completed"])
rep["changed_count"] = len(rep["new_vs_old_staging"]["changed"])
(HERE / "staging" / "ucl_stage_v2_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps({x: rep[x] for x in ("revision", "revision_time", "rows", "played", "by_matchday_played", "unresolved_identities", "teams", "in_store", "changed_count", "store_rows_that_differ_from_new")}, indent=1, default=str))
print(json.dumps(rep["new_vs_old_staging"]["changed"][:30], default=str, ensure_ascii=False)[:2500])
