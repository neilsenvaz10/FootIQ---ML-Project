"""Phase 4.20 part B: OFFLINE comparison of the newly downloaded 2026-27 files with the production store (opened mode=ro). Writes only into data/supervised/phase4/p420/staging/.

Per league: parse the openfootball file (primary, CC0), map clubs to the store's identifiers, compare with the stored rows, cross-check every result and date against football-data.co.uk (cross-check only),
and write a staging file of the results the store is missing plus a list of conflicts. Nothing is imported."""
import csv
import difflib
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RAW = HERE / "staging" / "raw"
OUT = HERE / "staging"
sys.path.insert(0, str(ROOT / "FootIQ_Dataset_Submission" / "_build"))
import footballtxt as ft  # noqa: E402

KEYS = ["EPL", "SERIEA", "LIGUE1", "BUNDESLIGA", "LALIGA"]
FD_FILE = {"EPL": "E0", "SERIEA": "I1", "LIGUE1": "F1", "BUNDESLIGA": "D1", "LALIGA": "SP1"}
TODAY = "2026-10-28"
ALIAS = {  # football-data.co.uk short names -> a form the fuzzy matcher can reach
    "man city": "manchester city", "man united": "manchester united", "nott m forest": "nottingham forest", "spurs": "tottenham", "wolves": "wolverhampton", "newcastle": "newcastle united",
    "leeds": "leeds united", "west ham": "west ham united", "brighton": "brighton hove albion", "inter": "internazionale", "milan": "ac milan", "paris sg": "paris saint germain",
    "st etienne": "saint etienne", "ein frankfurt": "eintracht frankfurt", "m gladbach": "borussia monchengladbach", "mainz": "mainz 05", "fc koln": "koln", "ath madrid": "atletico madrid",
    "ath bilbao": "athletic club", "sociedad": "real sociedad", "betis": "real betis", "vallecano": "rayo vallecano", "celta": "celta vigo", "espanol": "espanyol", "leverkusen": "bayer leverkusen",
    "dortmund": "borussia dortmund", "stuttgart": "vfb stuttgart", "hoffenheim": "tsg hoffenheim", "bayern munich": "bayern munchen", "werder bremen": "werder bremen", "heidenheim": "heidenheim",
    "hamburg": "hamburger sv", "lyon": "olympique lyonnais", "marseille": "olympique de marseille", "monaco": "as monaco", "lille": "lille osc", "nice": "ogc nice", "rennes": "stade rennais",
    "brest": "stade brestois", "lens": "rc lens", "strasbourg": "rc strasbourg", "toulouse": "toulouse fc", "nantes": "fc nantes", "lorient": "fc lorient", "paris fc": "paris fc", "metz": "fc metz"}
STOP = {"fc", "cf", "afc", "ac", "as", "sc", "ssc", "sv", "bv", "tsg", "vfb", "vfl", "rb", "rc", "us", "ss", "ud", "cd", "rcd", "calcio", "de", "the", "1", "fsv", "sg", "osc", "ogc", "fk", "1899", "1909", "1907", "1913", "1946", "04", "05", "96", "98"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = " ".join(s.split())
    return ALIAS.get(s, s)


def core(s):
    return "".join(t for t in norm(s).split() if t not in STOP)


def alike(a, b):
    ca, cb = core(a), core(b)
    return ca == cb or (len(ca) >= 4 and len(cb) >= 4 and (ca in cb or cb in ca)) or difflib.SequenceMatcher(None, ca, cb).ratio() >= 0.82


db = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
summary, all_missing, all_conflicts, all_dates = {}, [], [], []
for key in KEYS:
    stored = [dict(r) for r in db.execute("SELECT record_id, match_date, home_entity_id h, away_entity_id a, home_name, away_name, status, home_goals_final hg, away_goals_final ag, source_system, kickoff_local, time_precision, content_hash "
                                          "FROM matches WHERE competition_key=? AND season='2026-27'", (key,))]
    by_pair = {(r["h"], r["a"]): r for r in stored}
    name_to_ent = {}
    for r in stored:
        name_to_ent.setdefault(r["home_name"], r["h"])
        name_to_ent.setdefault(r["away_name"], r["a"])
    # aliases of other seasons for names the 2026-27 rows do not use
    for r in db.execute("SELECT alias, entity_id FROM team_aliases WHERE competition_id=(SELECT competition_id FROM matches WHERE competition_key=? LIMIT 1)", (key,)):
        name_to_ent.setdefault(r["alias"], r["entity_id"])
    text = (RAW / f"openfootball_{key}.txt").read_text(encoding="utf-8")
    title, parsed, issues = ft.parse_text(text, 2026)
    fd = pd.read_csv(RAW / f"footballdatauk_{key}.csv", encoding="utf-8-sig", on_bad_lines="skip")
    fd["date"] = pd.to_datetime(fd.Date, dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    fd = fd.dropna(subset=["date", "FTHG", "FTAG"])
    fd_rows = [(r.date, r.HomeTeam, r.AwayTeam, int(r.FTHG), int(r.FTAG)) for r in fd.itertuples()]
    used_fd = set()
    unresolved, seen, cnt = set(), {}, Counter()
    missing, conflicts, date_changes, dup = [], [], [], []
    of_done = []
    for m in parsed:
        res = m["res"] or {}
        done = res.get("status") == "scored" and res.get("ft") is not None
        h = name_to_ent.get(m["team1"])
        a = name_to_ent.get(m["team2"])
        if not h or not a:
            unresolved.add((m["team1"] if not h else None, m["team2"] if not a else None))
            cnt["unresolved_identity"] += 1
            continue
        if (h, a) in seen:
            dup.append(dict(first_line=seen[(h, a)], line=m["line_no"], home=m["team1"], away=m["team2"]))
            cnt["duplicate_in_source"] += 1
            continue
        seen[(h, a)] = m["line_no"]
        s = by_pair.get((h, a))
        score = tuple(res["ft"]) if done else None
        rec = dict(competition_key=key, season="2026-27", stage=m["stage"], date=m["date"], kickoff_local=m["kickoff_local"], home=m["team1"], away=m["team2"], home_entity=h, away_entity=a,
                   home_goals=None if not done else score[0], away_goals=None if not done else score[1], status="played" if done else "scheduled", source_line=m["line_no"])
        if done:
            of_done.append(rec)
        if s is None:
            cnt["pair_not_in_store"] += 1
            conflicts.append(dict(rec, kind="pair_not_in_store", store=None))
            continue
        if done and s["status"] != "completed":
            missing.append(dict(rec, store_status=s["status"], store_date=s["match_date"], record_id=s["record_id"]))
        elif done and s["status"] == "completed":
            if (s["match_date"], s["hg"], s["ag"]) != (m["date"], score[0], score[1]):
                conflicts.append(dict(rec, kind="differs_from_stored_result", store=f"{s['match_date']} {s['hg']}-{s['ag']}", store_source=s["source_system"]))
                cnt["result_differs"] += 1
            else:
                cnt["result_identical"] += 1
        elif not done and s["status"] != "completed" and s["match_date"] != m["date"]:
            date_changes.append(dict(rec, store_date=s["match_date"], record_id=s["record_id"], store_source=s["source_system"], diff_days=(pd.Timestamp(m["date"]) - pd.Timestamp(s["match_date"])).days))
        elif not done and s["status"] == "completed":
            cnt["stored_result_newer_than_source"] += 1
    # cross-check each played match of the source against football-data.co.uk (date and score)
    for rec in of_done:
        cands = [i for i, f in enumerate(fd_rows) if f[0] == rec["date"] and alike(f[1], rec["home"]) and alike(f[2], rec["away"])]
        if not cands:                                                                    # same pairing on a neighbouring day = a date difference
            near = [i for i, f in enumerate(fd_rows) if abs((pd.Timestamp(f[0]) - pd.Timestamp(rec["date"])).days) <= 3 and alike(f[1], rec["home"]) and alike(f[2], rec["away"])]
            rec["crosscheck"] = "date_differs:" + fd_rows[near[0]][0] if near else "not_in_footballdata_uk"
        else:
            f = fd_rows[cands[0]]
            used_fd.add(cands[0])
            rec["crosscheck"] = "confirmed" if (f[3], f[4]) == (rec["home_goals"], rec["away_goals"]) else f"SCORE_DIFFERS:{f[3]}-{f[4]}"
    for rec in missing:
        rec["crosscheck"] = next((r["crosscheck"] for r in of_done if (r["home_entity"], r["away_entity"]) == (rec["home_entity"], rec["away_entity"])), "")
    fd_only = [fd_rows[i] for i in range(len(fd_rows)) if i not in used_fd]
    sid = Counter(s["status"] for s in stored)
    past_open = [s for s in stored if s["status"] in ("scheduled", "awaiting_result") and s["match_date"] < TODAY]
    still_open_after = [s for s in past_open if (s["h"], s["a"]) not in {(m["home_entity"], m["away_entity"]) for m in missing}]
    summary[key] = dict(
        store_rows=len(stored), store_completed=sid.get("completed", 0), store_open=sum(v for k, v in sid.items() if k != "completed"), store_latest_result=max([s["match_date"] for s in stored if s["status"] == "completed"], default=None),
        source_matches=len(parsed), source_played=len(of_done), source_latest_result=max([r["date"] for r in of_done], default=None), source_parse_issues=len(issues), source_title=title,
        fixtures_past_date_without_result_in_store=len(past_open), of_results_missing_from_store=len(missing), still_without_result_after_staging=len(still_open_after),
        crosscheck_of_played=dict(Counter(r["crosscheck"].split(":")[0] for r in of_done)), crosscheck_of_missing=dict(Counter(r["crosscheck"].split(":")[0] for r in missing)),
        footballdatauk_played_rows=len(fd_rows), footballdatauk_rows_not_in_source=len(fd_only), conflicts=len(conflicts), conflict_kinds=dict(Counter(c["kind"] for c in conflicts)),
        date_changes_for_unplayed=len(date_changes), duplicates_in_source=len(dup), unresolved_identities=sorted(map(str, unresolved)), counters=dict(cnt))
    all_missing += missing
    all_conflicts += conflicts
    all_dates += date_changes
    for nm, rows in (("missing_results", missing), ("conflicts", conflicts), ("date_changes", date_changes)):
        if rows:
            pd.DataFrame(rows).to_csv(OUT / f"{key}_{nm}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(fd_only, columns=["date", "home", "away", "hg", "ag"]).to_csv(OUT / f"{key}_footballdatauk_not_matched.csv", index=False, encoding="utf-8-sig")
(OUT / "staging_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(summary, indent=1, ensure_ascii=False, default=str)[:9000])
