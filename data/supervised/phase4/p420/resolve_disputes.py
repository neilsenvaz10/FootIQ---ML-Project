"""Phase 4.20 part B (3): re-examine the 96 date disputes of Phase 4.13 with the evidence available today. OFFLINE (store mode=ro; files already downloaded). Writes staging/date_dispute_resolution.csv + .json.

Evidence per disputed fixture:
  store       the date the store holds (openfootball snapshot of 2026-10-15)
  of_now      the date in today's openfootball file (CC0)
  provider    football-data.org date (private Phase 4.13 staging; never stored in the app)
  ol          OpenLigaDB date, where the Phase 4.13 comparison had one (EPL)
  result      date of the played match in football-data.co.uk (cross-check source) when the match has been played
Rule: every source counts once; the store's own date is the 15 Oct openfootball snapshot, the same source as today's openfootball file. A date is RESOLVED when at least two independent sources give it
(and no other date ties it): R_date_change_supported (the store date is replaced by that date) or R_store_date_confirmed. One source against one source stays U_unresolved (quarantined).
Resolved is an evidence verdict only: whether the date may be STORED still depends on the licence of the sources that carry it (see the report)."""
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RAW = HERE / "staging" / "raw"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "FootIQ_Dataset_Submission" / "_build"))
import footballtxt as ft  # noqa: E402
import stage_helpers as H  # noqa: E402

db = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
disp = pd.read_csv(ROOT / "data" / "supervised" / "phase4" / "p413" / "date_disputes.csv")
ctx = {}
for key in ("EPL", "SERIEA", "LIGUE1"):
    rows = db.execute("SELECT record_id, match_date, home_entity_id, away_entity_id, home_name, away_name, status FROM matches WHERE competition_key=? AND season='2026-27'", (key,)).fetchall()
    ent = {}
    for r in rows:
        ent[r[2]], ent[r[3]] = r[4], r[5]
    of = {}
    for m in ft.parse_text((RAW / f"openfootball_{key}.txt").read_text(encoding="utf-8"), 2026)[1]:
        h, a = H.resolve(ent, m["team1"]), H.resolve(ent, m["team2"])
        if h and a:
            of[(h, a)] = (m["date"], m["res"] and m["res"].get("status") == "scored")
    fd = pd.read_csv(RAW / f"footballdatauk_{key}.csv", encoding="utf-8-sig", on_bad_lines="skip")
    fd["date"] = pd.to_datetime(fd.Date, dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    played = {}
    for r in fd.dropna(subset=["date", "FTHG"]).itertuples():
        h, a = H.resolve(ent, r.HomeTeam), H.resolve(ent, r.AwayTeam)
        if h and a:
            played[(h, a)] = r.date
    ctx[key] = dict(rows={(r[2], r[3]): r for r in rows}, ent=ent, of=of, played=played)
out = []
for rec in disp.to_dict("records"):
    r = type("R", (), rec)()
    c = ctx[r.league]
    h, a = H.resolve(c["ent"], r.home), H.resolve(c["ent"], r.away)
    st = c["rows"].get((h, a)) if h and a else None
    of_now = c["of"].get((h, a), (None, None))[0] if h and a else None
    res = c["played"].get((h, a)) if h and a else None
    prov = r.provider_local_date
    ol = r.second_source_date if isinstance(r.second_source_date, str) else None
    store_now = st[1] if st else None
    votes = {"openfootball_now": of_now, "football-data.org": prov, "OpenLigaDB": ol, "football-data.co.uk": res}      # the store's own date is the openfootball snapshot of 15 Oct, i.e. the same source as openfootball_now
    tally = Counter(v for v in votes.values() if v)
    best, n = (tally.most_common(1)[0] if tally else (None, 0))
    tied = sum(1 for v in tally.values() if v == n) > 1
    if st is None:
        cls, why, newd = "U_unresolved", "club names did not map to a stored fixture", None
    elif n >= 2 and not tied and best != store_now:
        cls, newd = "R_date_change_supported", best
        why = f"{n} independent sources give {best} ({', '.join(k for k, v in votes.items() if v == best)}); the store's {store_now} comes from one source (openfootball)"
    elif n >= 2 and not tied and best == store_now:
        cls, newd, why = "R_store_date_confirmed", store_now, f"{n} sources give {best}"
    else:
        cls, newd = "U_unresolved", None
        why = f"one source each: store/openfootball {store_now}/{of_now}, football-data.org {prov}, OpenLigaDB {ol}, football-data.co.uk {res}"
    out.append(dict(league=r.league, matchday=r.matchday, home=r.home, away=r.away, store_date=store_now, openfootball_now=of_now, provider_local_date=prov, openligadb_date=ol, played_date_footballdatauk=res,
                    phase413_class=rec["class"], resolution=cls, resolved_date=newd, evidence=why, record_id=st[0] if st else None))
df = pd.DataFrame(out)
df.to_csv(HERE / "staging" / "date_dispute_resolution.csv", index=False, encoding="utf-8-sig")
summ = dict(total=len(df), by_resolution=df.resolution.value_counts().to_dict(), by_league=df.groupby(["league", "resolution"]).size().unstack(fill_value=0).to_dict("index"),
            phase413_class_vs_resolution=df.groupby(["phase413_class", "resolution"]).size().unstack(fill_value=0).to_dict("index"))
(HERE / "staging" / "date_dispute_summary.json").write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8")
print(json.dumps(summ, indent=1, default=str))
