"""Phase 4.23 task 3: reconcile the 96 disputed fixture dates with every source available today. OFFLINE (store mode=ro + files in staging/raw + the private Phase 4.13 comparison file). Writes
staging/date_reconciliation.csv (one row per dispute with its full evidence trail) and staging/date_reconciliation_summary.json.

Sources and what they are:
  store/openfootball   the stored date is the openfootball snapshot of 2026-10-15; today's openfootball file is the SAME source, so the two count as ONE vote (CC0-1.0, storable)
  fixturedownload      independent free fixture feed, UTC date and time, converted to the league's local date (no explicit licence: cross-check only)
  openligadb           date held in the store's own quarantine (a DATE_DIFFERENCE finding of the approved OpenLigaDB feed, ODbL) - Premier League only
  footballdatauk       fixtures.csv, only the next few days (no explicit licence: cross-check only)
  football-data.org    the provider's date from the private Phase 4.13 comparison (storage terms unconfirmed): COUNTED AS EVIDENCE BUT FLAGGED; 'strong' resolutions do not depend on it
Rule: a date is RESOLVED when at least two independent sources give it and no other date ties it.
  strong            resolved WITHOUT the provider
  provider_assisted resolved only when the provider's date is counted
  unresolved        otherwise (stays quarantined)
A played match is not a dispute any more: its date is the day it was played (see the result staging)."""
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evidence as E  # noqa: E402

ROOT = E.ROOT
TZ = dict(EPL="Europe/London", SERIEA="Europe/Rome", LIGUE1="Europe/Paris", LALIGA="Europe/Madrid", BUNDESLIGA="Europe/Berlin")
disp = pd.read_csv(ROOT / "data" / "supervised" / "phase4" / "p413" / "date_disputes.csv")
conn = E.connect()
RX = re.compile(r"DATE_DIFFERENCE: stored (\d{4}-\d\d-\d\d) vs source (\d{4}-\d\d-\d\d): (.+?)(?: \(.*)?$")
oldb = {}
for q in conn.execute("SELECT source_ref, reason, payload FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%'"):
    m = RX.match(q["reason"])
    if m:
        oldb[(m.group(3).strip(), m.group(1))] = m.group(2)                 # (teams text, stored date) -> OpenLigaDB date

ctx = {}
for k in ("EPL", "SERIEA", "LIGUE1"):
    d = E.load(k, conn)
    ctx[k] = d
rows = []
for rec in disp.to_dict("records"):
    k = rec["league"]
    d = ctx[k]
    h, a = E.H.resolve(d["ent"], rec["home"]), E.H.resolve(d["ent"], rec["away"])
    s = d["rows"].get((h, a)) if h and a else None
    store_date = s["match_date"] if s else None
    of = d["of"].get((h, a), {}).get("date") if s else None
    fx = d["fxd"].get((h, a), {}) if s else {}
    fxd_local = None
    if fx.get("utc"):
        dt = datetime.strptime(fx["utc"].replace("Z", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TZ[k]))
        fxd_local = dt.strftime("%Y-%m-%d")
    ff = d["fduk_fx"].get((h, a), {}).get("date") if s else None
    prov = rec["provider_local_date"]
    ol = rec["second_source_date"] if isinstance(rec["second_source_date"], str) else None
    votes = {"openfootball (store)": of, "fixturedownload": fxd_local, "openligadb": ol, "footballdatauk fixtures": ff}
    votes_p = dict(votes, **{"football-data.org (provider)": prov})
    played = s and s["status"] == "completed"

    def decide(v):
        tally = Counter(x for x in v.values() if x)
        if not tally:
            return None, 0, True
        best, n = tally.most_common(1)[0]
        tied = sum(1 for c in tally.values() if c == n) > 1
        return best, n, tied

    b, n, tied = decide(votes)
    bp, np_, tiedp = decide(votes_p)
    if s is None:
        cls, new, why = "unresolved", None, "club names did not map to a stored fixture"
    elif n >= 2 and not tied:
        cls, new = "strong", b
        why = f"{n} independent sources give {b}: " + ", ".join(x for x, v in votes.items() if v == b)
    elif np_ >= 2 and not tiedp:
        cls, new = "provider_assisted", bp
        why = f"{np_} sources give {bp} only when the provider is counted: " + ", ".join(x for x, v in votes_p.items() if v == bp)
    else:
        cls, new = "unresolved", None
        why = "no date has two independent sources: " + "; ".join(f"{x} {v}" for x, v in votes_p.items() if v)
    action = "none"
    if cls in ("strong", "provider_assisted"):
        action = "keep_store_date" if new == store_date else "change_date"
    rows.append(dict(league=k, matchday=rec["matchday"], home=rec["home"], away=rec["away"], record_id=s["record_id"] if s else None, store_status=s["status"] if s else None, store_date=store_date,
                     openfootball_now=of, fixturedownload_local=fxd_local, fixturedownload_utc=fx.get("utc"), openligadb=ol, footballdatauk_fixtures=ff, provider=prov, phase413_class=rec["class"],
                     resolution=cls, proposed_date=new, action=action, evidence=why))
df = pd.DataFrame(rows)
df.to_csv(HERE / "staging" / "date_reconciliation.csv", index=False, encoding="utf-8-sig")
summ = dict(total=len(df), by_resolution=df.resolution.value_counts().to_dict(), by_action=df.action.value_counts().to_dict(), by_league=df.groupby(["league", "resolution"]).size().unstack(fill_value=0).to_dict("index"),
            by_league_action=df.groupby(["league", "action"]).size().unstack(fill_value=0).to_dict("index"), fixturedownload_matched=int(df.fixturedownload_local.notna().sum()),
            fixturedownload_agrees_with_provider=int((df.fixturedownload_local == df.provider).sum()), fixturedownload_agrees_with_openfootball=int((df.fixturedownload_local == df.openfootball_now).sum()))
(HERE / "staging" / "date_reconciliation_summary.json").write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8")
print(json.dumps(summ, indent=1, default=str))
