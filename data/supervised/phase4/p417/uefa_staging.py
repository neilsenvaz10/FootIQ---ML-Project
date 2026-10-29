"""Phase 4.17 step 2: stage the 2026-27 UEFA league phases (UCL, UEL, UECL) from the Wikipedia snapshots ALREADY SAVED locally (retrieved 2026-10-20, revisions of 2026-10-19/20), using the
project's own parser (FootIQ_ML_Data_Readiness/_build/wp_parse.py) and identity mapping (05_CANONICAL_TEAM_IDENTITY_MAPPING.csv). No network. Read-only on project files; writes only here.
The openfootball repository holds no 2026-27 folder (checked in step 2a), so these snapshots are the only local source for 2026-27; they are CC BY-SA 4.0 (attribution required)."""
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BUILD = ROOT / "FootIQ_ML_Data_Readiness" / "_build"
sys.path.insert(0, str(BUILD))
import wp_parse  # noqa: E402

PAGES = {"UCL": "27c90c1b45_2026_27_UEFA_Champions_League_league_phase", "UEL": "1d9bd92488_2026_27_UEFA_Europa_League_league_phase", "UECL": "4ea22727ea_2026_27_UEFA_Conference_League_league_phase"}
EXPECT = {"UCL": 8, "UEL": 8, "UECL": 6}
mp = pd.read_csv(ROOT / "FootIQ_ML_Data_Readiness" / "05_CANONICAL_TEAM_IDENTITY_MAPPING.csv")
mp = mp[mp.source_system == "wikipedia"].set_index("source_team_key")
cur = pd.read_csv(ROOT / "data" / "miniproject" / "matches.csv", low_memory=False)
rows = []
for k, f in PAGES.items():
    d = json.loads((ROOT / "FootIQ_ML_Data_Readiness" / "raw_external" / "wikipedia" / f"{f}.json").read_text(encoding="utf-8"))
    for m in wp_parse.parse_page(d["wikitext"]):
        mm = re.search(r"Matchday (\d+)", m["stage_path"])
        if not mm:
            continue
        ids = []
        for side in ("t1", "t2"):
            code = m[f"{side}_code"]
            tgt = m[f"{side}_target"] if isinstance(m[f"{side}_target"], str) else m[f"{side}_display"]
            key = f"WP:{code}:{tgt}"
            r = mp.loc[key] if key in mp.index else None
            ids.append((r.canonical_team_id if r is not None and isinstance(r.canonical_team_id, str) else None, tgt, key, (r.resolution_status if r is not None else "not_in_mapping")))
        rows.append(dict(competition_key=k, season="2026-27", matchday=int(mm.group(1)), date=m["date"], home=ids[0][1], away=ids[1][1], home_entity=ids[0][0], away_entity=ids[1][0], home_map=ids[0][3], away_map=ids[1][3],
                         home_goals=m["s1"], away_goals=m["s2"], status="played" if m["s1"] is not None else "scheduled", page_revid=d["revid"], page_timestamp=d["timestamp"], page_url=d["url"], retrieved=d["retrieved"],
                         licence="CC BY-SA 4.0 (Wikipedia): attribution and share-alike apply"))
df = pd.DataFrame(rows)
df.to_csv(OUT / "uefa_2026_27_staging.csv", index=False, encoding="utf-8-sig")
rep = {}
for k in PAGES:
    d = df[df.competition_key == k]
    teams = sorted(set(d.home) | set(d.away))
    per = {t: dict(h=int((d.home == t).sum()), a=int((d.away == t).sum())) for t in teams}
    pairs = d.apply(lambda r: tuple(sorted([r.home, r.away])), axis=1)
    played = d[d.status == "played"]
    existing = cur[(cur.competition_key == k) & (cur.season == "2026-27")]
    # do the 18 rows the dataset already holds appear identically in the staging?
    sset = {(str(r.date), r.home_goals, r.away_goals) for r in played.itertuples()}
    eset = {(str(r.date), int(r.home_goals), int(r.away_goals)) for r in existing.itertuples()}
    unresolved = sorted({(r.home, r.home_map) for r in d.itertuples() if not r.home_entity} | {(r.away, r.away_map) for r in d.itertuples() if not r.away_entity})
    rep[k] = dict(matches=len(d), teams=len(teams), expected_per_team=EXPECT[k], teams_with_wrong_count=[t for t, v in per.items() if v["h"] + v["a"] != EXPECT[k]], teams_not_balanced_home_away=[t for t, v in per.items() if v["h"] != v["a"]],
                  duplicate_pairings=int(pairs.duplicated().sum()), played=len(played), scheduled=int((d.status == "scheduled").sum()), played_by_matchday=played.groupby("matchday").size().to_dict(), dates_by_matchday={int(m): [str(x) for x in sorted(set(g.date.dropna()))] for m, g in d.groupby("matchday")},
                  undated=int(d.date.isna().sum()), dataset_rows_2026_27=len(existing), dataset_rows_found_identically_in_staging=len(eset & sset), dataset_rows_missing_from_staging=sorted(eset - sset)[:5],
                  new_results_beyond_dataset=len(played) - len(existing), unresolved_identities=unresolved, scores_implausible=int(((played.home_goals > 12) | (played.away_goals > 12)).sum()))
(OUT / "uefa_staging_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(rep, indent=1, ensure_ascii=False, default=str)[:6000])
