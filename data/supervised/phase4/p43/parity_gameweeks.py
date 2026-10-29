"""Does the whole gameweek payload stay identical when team_form uses variant B? Every gameweek of the newest season of the five leagues, plus two per older season.

    FOOTIQ_STORE_PATH=<private copy> .venv/Scripts/python.exe -X utf8 data/supervised/phase4/p43/parity_gameweeks.py

Run BEFORE gameweeks.py is edited (it swaps gameweeks.team_form for the old and the new implementation of common.py, so it also works afterwards). Reads only.
The payload includes form, status, flags, reasons, reliability, saved forecast and evaluation of every fixture, so it covers everything team_form could influence."""
import json
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIVE, private_copy_path, team_form_b, team_form_old  # noqa: E402

import gameweeks as gw  # noqa: E402
from store import db  # noqa: E402

path = private_copy_path()
conn = db.connect(path, readonly=True)
today = date(2026, 10, 27)
LEAGUES = [sys.argv[1]] if len(sys.argv) > 1 and sys.argv[1] != "ALL" else FIVE          # one league per process, so the five can run side by side
STRIDE = int(sys.argv[2]) if len(sys.argv) > 2 else 1                                       # every STRIDE-th gameweek of the newest season
TAG = LEAGUES[0] if len(LEAGUES) == 1 else "ALL"


def matchdays(key, season):
    return sorted(r[0] for r in conn.execute("SELECT DISTINCT matchday_no FROM matches WHERE competition_key=? AND season=? AND kind='club' AND matchday_no IS NOT NULL", (key, season)))


targets = []
for key in LEAGUES:
    seasons = gw.seasons(conn, key)
    targets += [(key, seasons[0], md) for md in matchdays(key, seasons[0])[::STRIDE]]
    for s in seasons[1:]:
        mds = matchdays(key, s)
        targets += [(key, s, mds[len(mds) // 4]), (key, s, mds[(3 * len(mds)) // 4])]
print("gameweeks to compare:", len(targets))

seconds = {"old": 0.0, "new": 0.0}
diffs = []
fixtures = Counter()
forms = Counter()
bytes_total = 0
for i, (key, season, md) in enumerate(targets, 1):
    gw.team_form = team_form_old
    t = time.perf_counter(); a = gw.gameweek_fixtures(conn, key, season, md, today); seconds["old"] += time.perf_counter() - t
    gw.team_form = team_form_b
    t = time.perf_counter(); b = gw.gameweek_fixtures(conn, key, season, md, today); seconds["new"] += time.perf_counter() - t
    sa, sb = json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True)
    bytes_total += len(sa)
    if sa != sb:
        diffs.append(dict(key=key, season=season, matchday=md))
    for f in a["fixtures"]:
        fixtures["stored_" + f["stored_status"]] += 1
        fixtures["effective_" + f["status"]] += 1
        for side in ("home", "away"):
            forms[f"form_length_{len(f['form'][side])}"] += 1
    if i % 25 == 0:
        print(f"  {i}/{len(targets)} compared, differences so far {len(diffs)}", flush=True)

out = dict(private_copy=path.name, gameweeks=len(targets), payload_bytes_compared=bytes_total, differences=len(diffs), first_differences=diffs[:5],
           fixtures_by_status=dict(sorted(fixtures.items())), form_lengths=dict(sorted(forms.items())), seconds_total=dict(old=round(seconds["old"], 1), new=round(seconds["new"], 1)),
           seconds_per_gameweek=dict(old=round(seconds["old"] / len(targets), 2), new=round(seconds["new"] / len(targets), 2)))
Path(__file__).with_name(f"parity_gameweeks_{TAG}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
