"""Phase 4.17 step 1b: a fairer comparison of the staged CC0 results.csv with the local one (numeric scores; match identity = date + unordered team pair, tournament names compared separately).
READ-ONLY on project files; writes data/supervised/phase4/p417/compare_intl2_report.json."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
new = pd.read_csv(OUT / "staging" / "martj42" / "unpacked" / "international_results-master" / "results.csv")
old = pd.read_csv(ROOT / "data" / "raw" / "international_results" / "results.csv")
for d in (old, new):
    d["hs"] = pd.to_numeric(d.home_score, errors="coerce")
    d["as_"] = pd.to_numeric(d.away_score, errors="coerce")
    d["pair"] = d.date.astype(str) + "|" + d.apply(lambda r: "|".join(sorted([r.home_team, r.away_team])), axis=1)
res = {}
# exact identity first
for d in (old, new):
    d["k"] = d.date.astype(str) + "|" + d.home_team + "|" + d.away_team + "|" + d.tournament
ko, kn = set(old.k), set(new.k)
res["exact_rows_common"] = len(ko & kn)
mm = old.merge(new, on="k", suffixes=("_o", "_n"))
chg = mm[(mm.hs_o.fillna(-1) != mm.hs_n.fillna(-1)) | (mm.as__o.fillna(-1) != mm.as__n.fillna(-1))]
res["common_rows_with_different_score"] = len(chg)
res["common_rows_score_changes"] = chg[["k", "hs_o", "as__o", "hs_n", "as__n"]].head(15).astype(str).values.tolist()
removed, added = old[~old.k.isin(kn)], new[~new.k.isin(ko)]
res["rows_only_in_local"], res["rows_only_in_staged"] = len(removed), len(added)
# are the local-only rows the same match under another name (tournament or team naming)?
rp = removed.groupby("pair").size()
ap = added.groupby("pair").size()
same_pair = set(rp.index) & set(ap.index)
res["local_only_rows_matched_by_date_and_teams_to_a_staged_row"] = int(removed.pair.isin(same_pair).sum())
res["local_only_rows_with_no_staged_counterpart_by_date_and_teams"] = int((~removed.pair.isin(same_pair)).sum())
res["staged_only_rows_with_no_local_counterpart_by_date_and_teams"] = int((~added.pair.isin(same_pair)).sum())
ren = removed[removed.pair.isin(same_pair)].merge(added, on="pair", suffixes=("_o", "_n"))
res["renamed_tournament_examples"] = ren[ren.tournament_o != ren.tournament_n][["date_o", "home_team_o", "away_team_o", "tournament_o", "tournament_n"]].drop_duplicates().head(8).astype(str).values.tolist()
res["renamed_tournament_counts"] = ren[ren.tournament_o != ren.tournament_n].groupby(["tournament_o", "tournament_n"]).size().sort_values(ascending=False).head(8).reset_index().astype(str).values.tolist()
res["renamed_team_examples"] = ren[(ren.home_team_o != ren.home_team_n) | (ren.away_team_o != ren.away_team_n)][["date_o", "home_team_o", "away_team_o", "home_team_n", "away_team_n"]].drop_duplicates().head(8).astype(str).values.tolist()
lo = removed[~removed.pair.isin(same_pair)]
res["local_only_no_counterpart_by_tournament"] = lo.tournament.value_counts().head(10).to_dict()
res["local_only_no_counterpart_dates"] = [str(lo.date.min()), str(lo.date.max())]
res["local_only_no_counterpart_sample"] = lo[["date", "home_team", "away_team", "tournament", "hs", "as_"]].head(8).astype(str).values.tolist()
so = added[~added.pair.isin(same_pair)]
res["staged_only_by_tournament"] = so.tournament.value_counts().head(12).to_dict()
res["staged_only_date_range"] = [str(so.date.min()), str(so.date.max())]
res["staged_only_before_2026_06_03"] = int((so.date < "2026-06-03").sum())
res["staged_only_from_2026_06_03"] = int((so.date >= "2026-06-03").sum())
res["staged_only_before_sample"] = so[so.date < "2026-06-03"][["date", "home_team", "away_team", "tournament", "hs", "as_"]].head(10).astype(str).values.tolist()
# targets of the brief
res["staged_rows_after_local_cutoff_by_tournament"] = new[new.date > "2026-06-02"].tournament.value_counts().head(12).to_dict()
res["staged_rows_after_local_cutoff"] = int((new.date > "2026-06-02").sum())
unl = new[(new.tournament == "UEFA Nations League") & (new.date >= "2026-06-03")]
res["unl_2026_27_staged"] = dict(rows=len(unl), first=str(unl.date.min()), last=str(unl.date.max()), scored=int(unl.hs.notna().sum()))
res["unl_2026_27_rows"] = unl[["date", "home_team", "away_team", "hs", "as_"]].astype(str).values.tolist()[:60]
res["unl_total_staged_vs_local"] = [int((new.tournament == "UEFA Nations League").sum()), int((old.tournament == "UEFA Nations League").sum())]
# conflicting / duplicated rows inside the staged file
dd = new[new.duplicated(subset=["date", "home_team", "away_team"], keep=False)]
res["staged_internal_duplicates"] = dd[["date", "home_team", "away_team", "tournament", "hs", "as_"]].astype(str).values.tolist()
dl = old[old.duplicated(subset=["date", "home_team", "away_team"], keep=False)]
res["local_internal_duplicates"] = len(dl)
# World Cup 2026 staged completeness
wc = new[(new.tournament == "FIFA World Cup") & (new.date >= "2026-06-01")]
res["wc2026_staged"] = dict(rows=len(wc), scored=int(wc.hs.notna().sum()), last=str(wc.date.max()), final=wc[wc.date == wc.date.max()][["date", "home_team", "away_team", "hs", "as_"]].astype(str).values.tolist())
(OUT / "compare_intl2_report.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(res, indent=1, ensure_ascii=False, default=str)[:7500])
