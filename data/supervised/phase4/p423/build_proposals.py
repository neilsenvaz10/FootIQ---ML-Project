"""Phase 4.23 task 5: build the staged proposals (staging/proposed_changes.csv) from the evidence files. OFFLINE; reads the store read-only; nothing is changed.

Each row is one proposed production change with its evidence trail:
  add_result            the open fixture gets its result; the stored date is right                       (>= 2 sources agree on the score)
  add_result_with_date  as above, and the stored date is wrong: the day it was played is given by >= 2 sources (football-data.co.uk results and the FixtureDownload schedule, local date)
  correct_date          an unplayed fixture's date changes (resolution 'strong' or 'provider_assisted' of reconcile_disputes.py)
  set_postponed         a fixture past its date with no result in any source and a moved date in the approved OpenLigaDB feed: status becomes 'postponed' (the date is not touched)
Tiers: strong = decided without football-data.org's date; provider_assisted = decided only when that date is counted; decision = needs the owner's judgement (postponement)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evidence as E  # noqa: E402

TZ = dict(EPL="Europe/London", SERIEA="Europe/Rome", LIGUE1="Europe/Paris", LALIGA="Europe/Madrid", BUNDESLIGA="Europe/Berlin")
STG = HERE / "staging"
AS_OF = "2026-10-28"
ev = pd.read_csv(STG / "open16_evidence.csv", encoding="utf-8-sig")
rec = pd.read_csv(STG / "date_reconciliation.csv", encoding="utf-8-sig")
raw_ev = json.loads((STG / "raw" / "evidence.json").read_text(encoding="utf-8"))
wiki_rev = {k: raw_ev[f"wikipedia_{k}_season_api.json"].get("retrieved_utc") for k in E.LEAGUES}


def local_date(utc, key):
    if not isinstance(utc, str):
        return None
    return datetime.strptime(utc.replace("Z", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TZ[key])).strftime("%Y-%m-%d")


def sc(x):
    if x is None or (isinstance(x, float) and pd.isna(x)) or x == "None":
        return None
    if isinstance(x, str):
        a, b = x.strip("() ").split(",")
        return int(a), int(b)
    return tuple(x)


conn = E.connect()
rows, held = [], []
cid = 0
for r in ev.to_dict("records"):
    k = r["competition_key"]
    votes = {"wikipedia": sc(r["wikipedia_score"]), "footballdatauk": sc(r["fduk_score"]), "fixturedownload": sc(r["fxd_score"])}
    present = {s: v for s, v in votes.items() if v}
    top = max(set(present.values()), key=list(present.values()).count) if present else None
    n_agree = list(present.values()).count(top) if top else 0
    conflicting = len(set(present.values())) > 1
    st = conn.execute("SELECT home_entity_id, away_entity_id, match_date, status FROM matches WHERE record_id=?", (r["record_id"],)).fetchone()
    base = dict(record_id=r["record_id"], competition_key=k, home=r["home"], away=r["away"], home_entity=st["home_entity_id"], away_entity=st["away_entity_id"], expected_store_date=st["match_date"], expected_store_status=st["status"])
    if top and n_agree >= 2 and not conflicting:
        d_fduk, d_fxd = r["fduk_date"] if isinstance(r["fduk_date"], str) else None, local_date(r["fxd_date_utc"], k)
        dates = [d for d in (d_fduk, d_fxd) if d]
        if dates and len(set(dates)) == 1 and (len(dates) == 2 or st["match_date"] == dates[0]):
            new_date = dates[0]
        else:
            held.append(dict(base, reason=f"score verified but the day it was played is not given by two sources (football-data.co.uk {d_fduk}, FixtureDownload {d_fxd}, store {st['match_date']})"))
            continue
        cid += 1
        action = "add_result" if new_date == st["match_date"] else "add_result_with_date"
        rows.append(dict(base, change_id=f"R{cid:03d}", action=action, tier="strong", new_date=new_date, home_goals=top[0], away_goals=top[1], wikipedia_score=f"{votes['wikipedia'][0]}-{votes['wikipedia'][1]}" if votes["wikipedia"] else None,
                         footballdatauk_score=f"{votes['footballdatauk'][0]}-{votes['footballdatauk'][1]}" if votes["footballdatauk"] else None, fixturedownload_score=f"{votes['fixturedownload'][0]}-{votes['fixturedownload'][1]}" if votes["fixturedownload"] else None,
                         footballdatauk_date=d_fduk, fixturedownload_date=d_fxd, openfootball_date=r["openfootball_date"], wikipedia_revision=r["wikipedia_revision"],
                         evidence=f"score {top[0]}-{top[1]} given by {n_agree} of {len(present)} sources ({', '.join(s for s, v in present.items() if v == top)}); played {new_date} per {', '.join(s for s, d in (('football-data.co.uk', d_fduk), ('FixtureDownload', d_fxd)) if d == new_date) or 'the stored fixture date'}"
                                  + (f"; stored date {st['match_date']} (openfootball) is a matchday placeholder" if action == "add_result_with_date" else "")))
    elif len(present) == 1 and not conflicting:
        held.append(dict(base, reason=f"single source for the score ({', '.join(present)}): not verified"))
    elif not present:
        # postponement evidence: no result in any source and the approved OpenLigaDB feed moved the date
        q = conn.execute("SELECT reason FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%' AND reason LIKE ? AND reason LIKE ?", (f"%stored {st['match_date']}%", f"%{r['home'].split()[0]}%")).fetchall()
        moved = [x["reason"] for x in q if r["away"].split()[0] in x["reason"] or r["away"] in x["reason"]]
        if moved:
            cid += 1
            rows.append(dict(base, change_id=f"R{cid:03d}", action="set_postponed", tier="decision", new_date=None, home_goals=None, away_goals=None, openfootball_date=r["openfootball_date"], fixturedownload_date=local_date(r["fxd_date_utc"], k),
                             evidence=f"no result in Wikipedia, football-data.co.uk, FixtureDownload or openfootball {max(1, (pd.Timestamp(AS_OF) - pd.Timestamp(st['match_date'])).days)} days after the fixture date; the approved OpenLigaDB feed holds it unfinished with its date moved to a placeholder ({moved[0].split(':')[1].split(' (')[0].strip()}); FixtureDownload still shows the old date without a score"))
        else:
            held.append(dict(base, reason="no result and no evidence of postponement"))
    else:
        held.append(dict(base, reason="sources disagree on the score"))

played_ids = {x["record_id"] for x in rows if x["action"] in ("add_result", "add_result_with_date")}
for r in rec.to_dict("records"):
    if r["action"] != "change_date" or r["record_id"] in played_ids:
        continue
    cid += 1
    rows.append(dict(change_id=f"D{cid:03d}", record_id=r["record_id"], competition_key=r["league"], home=r["home"], away=r["away"], expected_store_date=r["store_date"], expected_store_status=r["store_status"], action="correct_date",
                     tier="strong" if r["resolution"] == "strong" else "provider_assisted", new_date=r["proposed_date"], openfootball_date=r["openfootball_now"], fixturedownload_date=r["fixturedownload_local"], footballdatauk_date=r["footballdatauk_fixtures"],
                     openligadb_date=r["openligadb"], provider_date=r["provider"], evidence=r["evidence"]))
df = pd.DataFrame(rows)
ent = {r["record_id"]: (r["home_entity_id"], r["away_entity_id"]) for r in conn.execute("SELECT record_id, home_entity_id, away_entity_id FROM matches WHERE record_id IN (%s)" % ",".join("?" * len(df)), list(df.record_id))}
df["home_entity"] = df.record_id.map(lambda x: ent[x][0])
df["away_entity"] = df.record_id.map(lambda x: ent[x][1])
cols = ["change_id", "record_id", "competition_key", "home", "away", "home_entity", "away_entity", "action", "tier", "expected_store_status", "expected_store_date", "new_date", "home_goals", "away_goals", "wikipedia_score", "footballdatauk_score",
        "fixturedownload_score", "wikipedia_revision", "openfootball_date", "footballdatauk_date", "fixturedownload_date", "openligadb_date", "provider_date", "evidence"]
df = df.reindex(columns=cols)
df.to_csv(STG / "proposed_changes.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(held).to_csv(STG / "held_open16.csv", index=False, encoding="utf-8-sig")
print(df.groupby(["action", "tier"]).size().to_string())
print(df.groupby(["competition_key", "action", "tier"]).size().to_string())
print("held:", len(held))
for h in held:
    print("  ", h["competition_key"], h["home"], "v", h["away"], "-", h["reason"][:150])
