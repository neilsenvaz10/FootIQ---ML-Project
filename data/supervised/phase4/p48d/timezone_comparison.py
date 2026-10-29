"""Phase 4.8D Stage 1: eligibility under the production kickoff rule (app/kickoff.py) versus the isolated time-zone proposal with the evidence floor (app/kickoff_tz.py),
for every unplayed fixture of the five leagues in a PRIVATE COPY of production. Nothing is changed anywhere; the proposal is not wired into the application.
"""
import json
import re
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
import kickoff as OLD  # noqa: E402
import kickoff_tz as NEW  # noqa: E402

OUT = ROOT / "data" / "supervised" / "phase4" / "p48d"
PROD = ROOT / "data" / "footiq.sqlite"
LEAGUES = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"]
INSTANTS = ["2026-10-27T15:00:00Z", "2026-10-28T09:00:00Z", "2026-10-30T09:00:00Z", "2026-10-30T23:30:00Z", "2026-10-31T09:00:00Z", "2026-10-31T11:00:00Z"]
HORIZON = "2026-11-10"


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def main():
    cp = OUT / "tz_copy.sqlite"
    for e in ("", "-wal", "-shm"):
        Path(str(cp) + e).unlink(missing_ok=True)
        if Path(str(PROD) + e).exists():
            shutil.copyfile(str(PROD) + e, str(cp) + e)
    c = sqlite3.connect(cp)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    fixtures = [dict(r) for r in c.execute(f"SELECT record_id, competition_key k, match_date d, kickoff_utc ku, kickoff_local kl, status FROM matches WHERE status IN ('scheduled','awaiting_result') AND competition_key IN ({','.join('?' * 5)}) AND season='2026-27' AND match_date<=?", (*LEAGUES, HORIZON))]
    disputed = defaultdict(list)                                   # record_id -> the other candidate dates, from the date-disagreement quarantine
    sys.path.insert(0, str(ROOT / "app" / "store"))
    from store import sync  # noqa: E402
    resolver = sync.build_resolver(c)
    by_key = {}
    for f in fixtures:
        r = c.execute("SELECT competition_id, home_entity_id h, away_entity_id a FROM matches WHERE record_id=?", (f["record_id"],)).fetchone()
        by_key[(r["competition_id"], r["h"], r["a"], f["d"])] = f["record_id"]
    unmapped = 0
    for q in c.execute("SELECT payload, reason FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%'"):
        m = re.match(r"DATE_DIFFERENCE: stored (\d{4}-\d\d-\d\d) vs source (\d{4}-\d\d-\d\d)", q["reason"])
        pl = json.loads(q["payload"])
        he, _ = resolver.resolve("openligadb", pl["competition_key"], pl["home_raw"])
        ae, _ = resolver.resolve("openligadb", pl["competition_key"], pl["away_raw"])
        rid = by_key.get((pl["competition_key"], he, ae, m.group(1)))
        if rid:
            disputed[rid].append(m.group(2))
        else:
            unmapped += 1
    kinds = Counter()
    for f in fixtures:
        f["knowledge"] = "utc_kickoff" if f["ku"] else "local_time_no_zone" if f["kl"] else "date_only"
        f["alts"] = sorted(set(disputed.get(f["record_id"], [])))
        kinds[(f["k"], f["knowledge"])] += 1
    rep = dict(disputes_not_matching_an_unplayed_fixture_in_the_window=unmapped, fixtures_compared=len(fixtures), horizon_date=HORIZON, disputed_fixtures_among_them=sum(1 for f in fixtures if f["alts"]), instants={}, per_league_knowledge={f"{k}|{kn}": n for (k, kn), n in sorted(kinds.items())})
    violations = []
    for inst in INSTANTS:
        now = ts(inst)
        table = {k: dict(unplayed=0, old_yes=0, new_yes=0, gained=0, lost=0, old_unknown=0, new_unknown=0, no=0, gained_date_only=0, gained_local_time=0) for k in LEAGUES}
        for f in fixtures:
            t = table[f["k"]]
            o = OLD.made_before_kickoff(now, f["d"], f["ku"])
            n = NEW.made_before_kickoff_proposed(now, f["d"], f["ku"], f["k"], alt_dates=f["alts"])
            t["unplayed"] += 1
            t["old_yes"] += o == "yes"
            t["new_yes"] += n == "yes"
            t["old_unknown"] += o == "unknown"
            t["new_unknown"] += n == "unknown"
            t["no"] += n == "no"
            if n == "yes" and o != "yes":
                t["gained"] += 1
                t["gained_date_only"] += f["knowledge"] == "date_only"
                t["gained_local_time"] += f["knowledge"] == "local_time_no_zone"
            if o == "yes" and n != "yes":
                t["lost"] += 1
                violations.append(dict(instant=inst, record_id=f["record_id"], old=o, new=n, disputed=bool(f["alts"])))
            # invariants: a fixture with a stated kickoff is identical under both rules; a past date is never predictable; 'no' for old stays 'no' for new
            if f["ku"] and o != n:
                violations.append(dict(instant=inst, record_id=f["record_id"], why="stated kickoff differs", old=o, new=n))
            if o == "no" and n == "yes":
                violations.append(dict(instant=inst, record_id=f["record_id"], why="past fixture became predictable", old=o, new=n))
        rep["instants"][inst] = table
    rep["invariant_violations"] = violations
    rep["lost_only_for_disputed_fixtures"] = all(v.get("disputed") for v in violations if "why" not in v)
    (OUT / "timezone_comparison.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    c.close()
    for f in (cp, Path(str(cp) + "-wal"), Path(str(cp) + "-shm")):
        f.unlink(missing_ok=True)
    print(json.dumps({k: rep[k] for k in ("fixtures_compared", "disputed_fixtures_among_them", "per_league_knowledge", "invariant_violations", "lost_only_for_disputed_fixtures")}, indent=1))
    for inst, t in rep["instants"].items():
        print(inst)
        for k, v in t.items():
            print(f"  {k:11s} unplayed {v['unplayed']:3d}  old yes {v['old_yes']:3d}  new yes {v['new_yes']:3d}  gained {v['gained']:3d} (date-only {v['gained_date_only']}, local-time {v['gained_local_time']})  lost {v['lost']}  no {v['no']}")


if __name__ == "__main__":
    main()
