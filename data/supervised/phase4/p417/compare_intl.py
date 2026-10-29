"""Phase 4.17 step 1: compare the staged CC0 international dataset with what FootIQ holds. READ-ONLY on every project file; writes only to data/supervised/phase4/p417/."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
ST = OUT / "staging" / "martj42" / "unpacked" / "international_results-master"
LOC = ROOT / "data" / "raw" / "international_results"
res = {}
new = pd.read_csv(ST / "results.csv")
old = pd.read_csv(LOC / "results.csv")
res["files_identical_by_sha256"] = {f: hashlib.sha256((ST / f).read_bytes()).hexdigest() == hashlib.sha256((LOC / f).read_bytes()).hexdigest() for f in ("results.csv", "shootouts.csv", "former_names.csv", "goalscorers.csv")}
res["rows"] = dict(local=len(old), staged=len(new), local_last=str(old.date.max()), staged_last=str(new.date.max()))
key = ["date", "home_team", "away_team", "tournament"]
for d in (old, new):
    d["k"] = d.date.astype(str) + "|" + d.home_team + "|" + d.away_team + "|" + d.tournament
ko, kn = set(old.k), set(new.k)
added, removed = new[~new.k.isin(ko)], old[~old.k.isin(kn)]
res["rows_added_in_staged"] = len(added)
res["rows_removed_in_staged"] = len(removed)
res["removed_sample"] = removed[key + ["home_score", "away_score"]].head(5).astype(str).values.tolist()
m = old.merge(new, on="k", suffixes=("_old", "_new"))
chg = m[(m.home_score_old.astype(str) != m.home_score_new.astype(str)) | (m.away_score_old.astype(str) != m.away_score_new.astype(str))]
res["rows_with_changed_score"] = len(chg)
res["changed_sample"] = chg[["k", "home_score_old", "away_score_old", "home_score_new", "away_score_new"]].head(10).astype(str).values.tolist()
res["changed_by_tournament"] = chg.k.str.split("|").str[3].value_counts().head(8).to_dict()
res["added_by_tournament"] = added.tournament.value_counts().head(15).to_dict()
res["added_date_range"] = [str(added.date.min()), str(added.date.max())]
res["added_scored"] = int(added.home_score.notna().sum())
dup = new[new.duplicated(subset=["date", "home_team", "away_team"], keep=False)]
res["staged_duplicate_same_date_pair"] = len(dup)
res["staged_duplicate_sample"] = dup[key + ["home_score", "away_score"]].head(6).astype(str).values.tolist()
# ---------- World Cup 2026
wc = new[(new.tournament == "FIFA World Cup") & (new.date >= "2026-01-01")].copy()
res["wc2026_staged"] = dict(rows=len(wc), scored=int(wc.home_score.notna().sum()), last_scored_date=str(wc[wc.home_score.notna()].date.max()), unscored=int(wc.home_score.isna().sum()), first=str(wc.date.min()), last=str(wc.date.max()),
                            on_or_after_2026_07_19=wc[wc.date >= "2026-07-19"][["date", "home_team", "away_team", "home_score", "away_score"]].astype(str).values.tolist())
sh = pd.read_csv(ST / "shootouts.csv")
shw = sh[sh.date >= "2026-06-01"]
res["shootouts_2026"] = len(shw)
mm = pd.read_csv(ROOT / "data" / "miniproject" / "matches.csv", low_memory=False)
w = mm[(mm.competition_key == "WC") & (mm.season.astype(str) == "2026")].copy()
wcn = wc.copy()
wcn["pair"] = wcn.date.astype(str) + "|" + wcn.home_team + "|" + wcn.away_team
w["pair"] = w.date.astype(str) + "|" + w.home + "|" + w.away
sc = {r.pair: (r.home_score, r.away_score) for r in wcn.itertuples()}
# the 27 duplicated knockout matches and the 4 conflicts, against the staged score
rows = []
for pair, g in w.groupby("pair"):
    if len(g) < 2:
        continue
    ko_ = g[g.stage == "Knockout"].iloc[0]
    gs_ = g[g.stage == "Group stage"].iloc[0]
    st = sc.get(pair)
    rows.append(dict(pair=pair, knockout_row=f"{ko_.home_goals}-{ko_.away_goals}", group_row=f"{gs_.home_goals}-{gs_.away_goals}", staged=(f"{int(st[0])}-{int(st[1])}" if st and pd.notna(st[0]) else "absent/unscored"),
                     differ=(ko_.home_goals, ko_.away_goals) != (gs_.home_goals, gs_.away_goals)))
res["duplicates_27"] = dict(total=len(rows), staged_matches_knockout_row=sum(1 for r in rows if r["staged"] == r["knockout_row"]), staged_matches_group_row=sum(1 for r in rows if r["staged"] == r["group_row"] and r["staged"] != r["knockout_row"]),
                            staged_absent=sum(1 for r in rows if r["staged"] == "absent/unscored"), conflicts_4=[r for r in rows if r["differ"]])
# every existing 2026 WC pair vs staged
dist = w.drop_duplicates("pair")
miss_in_staged = [p for p in dist.pair if p not in sc]
res["wc2026_local_pairs_not_in_staged"] = miss_in_staged[:10] + ([f"... {len(miss_in_staged)} total"] if len(miss_in_staged) > 10 else [])
res["wc2026_staged_pairs_not_in_local"] = [p for p in wcn.pair if p not in set(dist.pair)][:12]
disagree = [(p, f"{r.home_goals}-{r.away_goals}", f"{int(sc[p][0])}-{int(sc[p][1])}") for p, r in zip(dist.pair, dist.itertuples()) if p in sc and pd.notna(sc[p][0]) and (r.home_goals, r.away_goals) != (sc[p][0], sc[p][1]) and r.stage == "Knockout"]
res["wc2026_knockout_score_disagreements_local_vs_staged"] = disagree
# ---------- Nations League and Copa
unl = new[new.tournament == "UEFA Nations League"]
res["unl"] = dict(staged_rows=len(unl), local_rows=int((old.tournament == "UEFA Nations League").sum()), staged_last=str(unl.date.max()), after_2025_06_08=unl[unl.date > "2025-06-08"][["date", "home_team", "away_team", "home_score", "away_score"]].astype(str).values.tolist()[:40],
                  after_2025_06_08_count=int((unl.date > "2025-06-08").sum()))
cop = new[new.tournament == "Copa América"]
res["copa"] = dict(staged_rows=len(cop), local_rows=int((old.tournament == "Copa América").sum()), staged_last=str(cop.date.max()))
# ---------- new team names and former names
elo = pd.read_csv(ROOT / "data" / "processed" / "team_elo_latest.csv")
names_new = set(new.home_team) | set(new.away_team)
res["team_names_in_staged_not_in_local_results"] = sorted(names_new - (set(old.home_team) | set(old.away_team)))[:20]
res["teams_in_added_rows_without_rating"] = sorted((set(added.home_team) | set(added.away_team)) - set(elo.team))[:20]
res["added_rows_sample"] = added[key + ["home_score", "away_score"]].head(8).astype(str).values.tolist()
(OUT / "compare_intl_report.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(res, indent=1, ensure_ascii=False, default=str)[:9000])
