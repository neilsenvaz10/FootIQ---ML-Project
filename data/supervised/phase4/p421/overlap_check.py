"""Phase 4.21: do any of the 71 staged domestic results sit on one of the 96 disputed fixtures? (read-only)"""
import sqlite3, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "data" / "supervised" / "phase4" / "p420"))
import stage_helpers as H
db = sqlite3.connect(f"file:{(ROOT/'data'/'footiq.sqlite').as_posix()}?mode=ro", uri=True)
disp = pd.read_csv(ROOT / "data/supervised/phase4/p413/date_disputes.csv")
st = pd.concat([pd.read_csv(ROOT / f"data/supervised/phase4/p420/staging/staged_results_{k}.csv", encoding="utf-8-sig") for k in ("EPL", "SERIEA", "LIGUE1")])
hit = []
for k, g in disp.groupby("league"):
    ent = {}
    for r in db.execute("SELECT home_entity_id,home_name,away_entity_id,away_name FROM matches WHERE competition_key=? AND season='2026-27'", (k,)):
        ent[r[0]], ent[r[2]] = r[1], r[3]
    pairs = {(H.resolve(ent, r.home), H.resolve(ent, r.away)) for r in g.itertuples()}
    s = st[st.competition_key == k]
    hit += [(k, a, b) for a, b in zip(s.home_entity, s.away_entity) if (a, b) in pairs]
print("staged results on a disputed fixture:", len(hit), hit[:5])
print("staged dates", st.date.min(), st.date.max(), "disputed stored dates min", disp.stored_date.min())
