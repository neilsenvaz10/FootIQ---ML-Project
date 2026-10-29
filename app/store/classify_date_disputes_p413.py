"""Phase 4.13: READ-ONLY classification of the football-data.org date disputes of Phase 4.12 (PL, SA, FL1). Reads the saved snapshots and production (mode=ro); writes only the evidence files under
data/supervised/phase4/p413/. No network, no database write, no date is corrected.

    python app/store/classify_date_disputes_p413.py
"""
import csv
import glob
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from store import footballdata as fd, sync  # noqa: E402

PROD = C.ROOT / "data" / "footiq.sqlite"
OUT = C.ROOT / "data" / "supervised" / "phase4" / "p413"
ZONE = {"EPL": "Europe/London", "SERIEA": "Europe/Rome", "LIGUE1": "Europe/Paris"}
OLDB_PL = C.ROOT / "data" / "snapshots" / "p48c" / "openligadb" / "20261027T130107Z_p48c_pl.json"      # the only second source with fixture dates for these leagues (PL); it is a stale RESULTS feed, its dates are only corroboration


def utc(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def classify(d):
    """Ordered, deterministic rules. A class is a hypothesis about the cause; none of them says which date is right."""
    if d["provider_status"] == "FINISHED":
        return "A_FINISHED_MATCH_DATE_DIFFERS", "The provider shows the match as played on its date. Either the stored date was wrong or the provider's UTC date is the next day of a late kick-off."
    if d["provider_local_date"] == d["stored_date"]:
        return "B_TIMEZONE_REPRESENTATION", "The provider's UTC date differs but its LOCAL date equals the stored date: the same day, not a dispute."
    if d["second_source_date"] and d["second_source_date"] == d["provider_date_utc"]:
        return "C_PROVIDER_CORROBORATED_BY_SECOND_SOURCE", "A second, independent source (OpenLigaDB) has the provider's date: the stored date is probably outdated."
    if d["second_source_date"] and d["second_source_date"] == d["stored_date"]:
        return "D_STORED_CORROBORATED_BY_SECOND_SOURCE", "A second source has the stored date: the provider differs from two sources."
    if abs(d["diff_days"]) <= 3:
        return "E_PROBABLE_RESCHEDULE_UNVERIFIED", "A shift of 1 to 3 days on a fixture the provider has timed: typical of broadcaster selection or a schedule revision. No evidence says which date is current."
    return "F_LARGE_SHIFT_INVESTIGATE", "A shift of more than 3 days: genuine rescheduling or a data error; needs an official source."


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pc = sqlite3.connect(f"file:{PROD.as_posix()}?mode=ro", uri=True)
    pc.row_factory = sqlite3.Row
    resolver = sync.build_resolver(pc)
    second = {}
    if OLDB_PL.exists():
        comp = "england:1-premierleague"
        for m in json.loads(OLDB_PL.read_bytes()):
            h, a = (resolver.resolve("openligadb", comp, m["team1"]["teamName"])[0], resolver.resolve("openligadb", comp, m["team2"]["teamName"])[0])
            second[(h, a)] = (m["matchDateTimeUTC"] or "")[:10]
    rows = []
    for key, code in (("EPL", "PL"), ("SERIEA", "SA"), ("LIGUE1", "FL1")):
        comp = fd.LEAGUES[key][1]
        f = sorted(glob.glob(str(C.ROOT / "data" / "snapshots" / "footballdata" / f"*_{code}_2026_season.json")))[-1]
        data = json.loads(Path(f).read_bytes())
        stored = {}
        for r in pc.execute("SELECT * FROM matches WHERE competition_key=? AND season='2026-27'", (key,)):
            stored.setdefault((r["home_entity_id"], r["away_entity_id"]), []).append(dict(r))
        for m in data["matches"]:
            rec = fd.parse_match(m, "", "", datetime(2026, 10, 27, 18, 50, tzinfo=timezone.utc), key, "2026")
            if rec.match_date is None:
                continue                                                                           # provisional placeholder: ignored by the adapter, not a dispute
            he, _ = resolver.resolve(fd.SOURCE, comp, m["homeTeam"]["name"])
            ae, _ = resolver.resolve(fd.SOURCE, comp, m["awayTeam"]["name"])
            c = stored.get((he, ae), [])
            if len(c) != 1:
                continue
            s = c[0]
            if not s["match_date"] or s["match_date"] == rec.match_date or rec.status == "completed_unclassified_score":
                continue
            ko = utc(m["utcDate"])
            d = dict(league=key, matchday=s["matchday_no"], home=s["home_name"], away=s["away_name"], stored_date=s["match_date"], stored_kickoff_utc=s["kickoff_utc"], stored_time_precision=s["time_precision"],
                     stored_weekday=datetime.strptime(s["match_date"], "%Y-%m-%d").strftime("%a"), stored_status=s["status"], stored_source=s["source_system"],
                     provider_date_utc=rec.match_date, provider_kickoff_utc=m["utcDate"], provider_weekday=ko.strftime("%a"), provider_status=m["status"], provider_last_updated=m.get("lastUpdated"),
                     provider_local_date=ko.astimezone(ZoneInfo(ZONE[key])).strftime("%Y-%m-%d"), provider_local_time=ko.astimezone(ZoneInfo(ZONE[key])).strftime("%H:%M"),
                     diff_days=(datetime.strptime(rec.match_date, "%Y-%m-%d") - datetime.strptime(s["match_date"], "%Y-%m-%d")).days, second_source_date=second.get((he, ae)) if key == "EPL" else None)
            d["class"], d["cause"] = classify(d)
            rows.append(d)
    pc.close()
    with open(OUT / "date_disputes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = dict(total=len(rows), by_league=dict(Counter(r["league"] for r in rows)), by_class=dict(Counter(r["class"] for r in rows)),
                   by_league_class={k: dict(Counter(r["class"] for r in rows if r["league"] == k)) for k in ZONE}, diff_days=dict(sorted(Counter(r["diff_days"] for r in rows).items())),
                   by_league_diff={k: dict(sorted(Counter(r["diff_days"] for r in rows if r["league"] == k).items())) for k in ZONE},
                   stored_precision=dict(Counter((r["league"], r["stored_time_precision"]) for r in rows).most_common()) if False else {f"{a}/{b}": n for (a, b), n in Counter((r["league"], r["stored_time_precision"]) for r in rows).items()},
                   stored_weekday=dict(Counter(r["stored_weekday"] for r in rows)), provider_weekday=dict(Counter(r["provider_weekday"] for r in rows)),
                   provider_status=dict(Counter(r["provider_status"] for r in rows)), stored_kickoff_known=sum(1 for r in rows if r["stored_kickoff_utc"]),
                   same_weekday_pair=dict(Counter(f"{r['stored_weekday']}->{r['provider_weekday']}" for r in rows).most_common(12)),
                   late_kickoff_utc_hour_ge_21=sum(1 for r in rows if int(r["provider_kickoff_utc"][11:13]) >= 21),
                   second_source=dict(Counter(("none" if r["second_source_date"] is None else "has_provider_date" if r["second_source_date"] == r["provider_date_utc"] else "has_stored_date" if r["second_source_date"] == r["stored_date"] else "other") for r in rows if r["league"] == "EPL")),
                   finished_held=[r for r in rows if r["provider_status"] == "FINISHED"])
    (OUT / "classification_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "finished_held"}, indent=1, ensure_ascii=False))
    for r in summary["finished_held"]:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
