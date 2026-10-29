"""Phase 4.36: which of the production importer decisions have INDEPENDENT, REDISTRIBUTABLE evidence? Read-only analysis.
Redistributable sources: Wikipedia (CC BY-SA 4.0), openfootball (CC0), OpenLigaDB (ODbL). Restricted (never published): football-data.co.uk, FixtureDownload, football-data.org.
Needs a private replay database (scripts/rebuild_current_state.py output) to read the OpenLigaDB results that were held for a date disagreement. Usage: analyse_evidence.py <replay.sqlite>"""
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "data" / "supervised" / "phase4" / "p420"))
import stage_helpers as H  # noqa: E402

REPLAY = Path(sys.argv[1])
P4 = ROOT / "data" / "supervised" / "phase4"
c = sqlite3.connect(f"file:{REPLAY.as_posix()}?mode=ro", uri=True)
# OpenLigaDB finished matches the store could not take because of a date disagreement (held, with the source's own result)
old = []
for reason, payload in c.execute("SELECT reason, payload FROM quarantine WHERE source='openligadb'"):
    p = json.loads(payload)
    if p.get("result_type") not in (None, "none") and p.get("regulation_home") is not None:
        old.append(dict(comp=p.get("competition_key"), home=p.get("home_raw"), away=p.get("away_raw"), date=p.get("match_date"), hg=p.get("regulation_home"), ag=p.get("regulation_away")))
# OpenLigaDB results that WERE stored (source_system openligadb)
for r in c.execute("SELECT competition_id, home_name, away_name, match_date, home_goals_90, away_goals_90 FROM matches WHERE source_system='openligadb' AND status='completed'"):
    old.append(dict(comp=r[0], home=r[1], away=r[2], date=r[3], hg=r[4], ag=r[5]))
print("OpenLigaDB finished matches visible:", len(old))


def oldb_support(comp_id, home, away, date, score):
    for o in old:
        if o["comp"] == comp_id and H.alike(o["home"], home) and H.alike(o["away"], away):
            return dict(same_score=f"{o['hg']}-{o['ag']}" == score, oldb_date=o["date"], same_date=o["date"] == date)
    return None


COMP_ID = {"EPL": "england:1-premierleague", "LALIGA": "espana:1-liga", "SERIEA": "italy:1-seriea", "LIGUE1": "europe/france:fr1", "BUNDESLIGA": "deutschland:1-bundesliga"}
rows = []
for f in sorted((P4 / "p420" / "staging").glob("staged_results_*.csv")):
    d = pd.read_csv(f, encoding="utf-8-sig")
    for r in d.itertuples():
        score = f"{int(r.home_goals)}-{int(r.away_goals)}"
        s = oldb_support(COMP_ID[r.competition_key], r.home, r.away, str(r.date), score)
        rows.append(dict(kind="staged_result", key=r.competition_key, id=r.record_id, wikipedia=True, openfootball_score=False, openligadb_score=bool(s and s["same_score"]), restricted_used=True,
                         redistributable_independent=1 + int(bool(s and s["same_score"]))))
prop = pd.read_csv(P4 / "p423" / "staging" / "proposed_changes.csv", encoding="utf-8-sig")
for r in prop.itertuples():
    nn = lambda v: not (v is None or (isinstance(v, float) and pd.isna(v)))
    if r.action in ("add_result", "add_result_with_date"):
        score = f"{int(r.home_goals)}-{int(r.away_goals)}"
        s = oldb_support(COMP_ID[r.competition_key], r.home, r.away, str(r.new_date), score)
        n = 1 + int(bool(s and s["same_score"]))
        rows.append(dict(kind=r.action, key=r.competition_key, id=r.change_id, tier=r.tier, wikipedia=nn(r.wikipedia_score), openligadb_score=bool(s and s["same_score"]), redistributable_independent=n, restricted_used=True))
    elif r.action == "correct_date":
        red = int(nn(r.openligadb_date) and str(r.openligadb_date) == str(r.new_date))          # openfootball_date is the OLD date being corrected
        rows.append(dict(kind=r.action, key=r.competition_key, id=r.change_id, tier=r.tier, openligadb_date=nn(r.openligadb_date), redistributable_independent=red, restricted_used=True))
    else:
        rows.append(dict(kind=r.action, key=r.competition_key, id=r.change_id, tier=r.tier, redistributable_independent=int(nn(r.openligadb_date)), restricted_used=True))
df = pd.DataFrame(rows)
df["publishable"] = df.redistributable_independent >= 2
print(df.groupby(["kind", "key", "publishable"]).size().to_string())
df.to_csv(Path(__file__).with_name("evidence_analysis.csv"), index=False)
