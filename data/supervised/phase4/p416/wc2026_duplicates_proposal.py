"""Phase 4.16: PROPOSAL ONLY. Lists the 27 World Cup 2026 knockout matches that data/miniproject/matches.csv holds twice and writes what a clean version would look like to
data/supervised/phase4/p416/wc2026_dedup_proposal.csv. It reads matches.csv and changes nothing: matches.csv, the store and the running backend are untouched.

Rule proposed for review (not applied): keep the row labelled 'Knockout' (verified source, recorded score after extra time) and drop the 'Group stage' twin, which comes from the
matchday-validation file. On 4 matches the twins disagree (1-1 vs 3-2 and so on): the lower 'Group stage' score looks like the 90-minute score and the 'Knockout' one the score after extra time,
which would be a useful 90-minute label, but that is a hypothesis to verify against the cited sources, not something to import."""
import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
m = pd.read_csv(ROOT / "data" / "miniproject" / "matches.csv", low_memory=False)
wc = m[(m.competition_key == "WC") & (m.season.astype(str) == "2026")].copy()
rows = []
for (date, home, away), g in wc.groupby(["date", "home", "away"]):
    if len(g) < 2:
        continue
    ko = g[g.stage == "Knockout"].iloc[0]
    gs = g[g.stage == "Group stage"].iloc[0]
    differs = (ko.home_goals, ko.away_goals) != (gs.home_goals, gs.away_goals)
    rows.append(dict(date=date, home=home, away=away, keep_stage="Knockout", keep_score=f"{ko.home_goals}-{ko.away_goals}", keep_source=str(ko.source)[:70], drop_stage="Group stage",
                     drop_score=f"{gs.home_goals}-{gs.away_goals}", drop_source=str(gs.source)[:70], scores_differ=differs,
                     note=("twin score is lower: possibly the 90-minute score, verify before using it" if differs and gs.home_goals + gs.away_goals < ko.home_goals + ko.away_goals else "")))
out = ROOT / "data" / "supervised" / "phase4" / "p416" / "wc2026_dedup_proposal.csv"
with open(out, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} duplicated knockout matches; {sum(1 for r in rows if r['scores_differ'])} with differing scores; rows after dropping the twins: {len(wc) - len(rows)} (103 distinct fixtures of 104; the final is absent)")
for r in rows:
    if r["scores_differ"]:
        print(r["date"], r["home"], "v", r["away"], "keep", r["keep_score"], "drop", r["drop_score"])
