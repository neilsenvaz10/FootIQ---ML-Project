"""Phase 4.20 part B (2): stage the 2026-27 results the store is missing, from TWO independent sources that must agree, OFFLINE (store opened mode=ro; writes only under staging/).

  A  Wikipedia results grid (CC BY-SA 4.0), revision id recorded  -> the score (the grid has no dates)
  B  football-data.co.uk (no explicit licence, cross-check only)   -> an independent score AND the match date
The store's fixture date is inherited by A and compared with B's date. Tiers: verified_two_sources (scores equal and B's date equals the store date), date_differs, score_conflict, single_source_*.
Only verified_two_sources rows are written to staged_results_<KEY>.csv; everything else goes to held_<KEY>.csv with the reason. Nothing is imported."""
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RAW = HERE / "staging" / "raw"
OUT = HERE / "staging"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "FootIQ_Dataset_Submission" / "_build"))
import footballtxt as ft  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("sl_helpers", HERE / "stage_helpers.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

KEYS = ["EPL", "SERIEA", "LIGUE1", "BUNDESLIGA", "LALIGA"]
FD_FILE = {k: RAW / f"footballdatauk_{k}.csv" for k in KEYS}
SC = re.compile(r"(\d+)\s*[–−—-]\s*(\d+)")


def parse_matrix(w):
    names = {}
    for m in re.finditer(r"\|\s*name_([^\s=]+)\s*=\s*([^\n]+)", w):
        v = m.group(2)
        lk = re.search(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]", v)
        names[m.group(1)] = (lk.group(1).strip(), (lk.group(2) or lk.group(1)).strip()) if lk else (None, re.sub(r"[{}|]|nowrap", "", v).strip())
    res = {}
    for m in re.finditer(r"\|\s*match_([^\s_=]+)_([^\s=]+)\s*=\s*([^\n|]*)", w):
        sc = SC.search(re.sub(r"\[\[[^\]|]*\|", "", m.group(3)))
        res[(m.group(1), m.group(2))] = (int(sc.group(1)), int(sc.group(2))) if sc else None
    return names, res


db = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
summary = {}
for key in KEYS:
    tpl = RAW / f"wikipedia_{key}_table_season_api.json"                          # Ligue 1, Bundesliga and La Liga keep their results grid in a template page
    page = json.loads((tpl if tpl.exists() else RAW / f"wikipedia_{key}_season_api.json").read_text(encoding="utf-8"))["query"]["pages"][0]
    rev = page["revisions"][0]
    names, grid = parse_matrix(rev["slots"]["main"]["content"])
    stored = {(r["h"], r["a"]): dict(r) for r in db.execute("SELECT record_id, match_date, home_entity_id h, away_entity_id a, home_name, away_name, status, home_goals_final hg, away_goals_final ag, source_system "
                                                              "FROM matches WHERE competition_key=? AND season='2026-27'", (key,))}
    ent_name = {}
    for (h, a), r in stored.items():
        ent_name[h] = r["home_name"]
        ent_name[a] = r["away_name"]
    # map each grid abbreviation to exactly one club of this league
    abbr_ent, ambiguous = {}, []
    for ab, (tgt, disp) in names.items():
        e = H.resolve(ent_name, tgt or disp) or H.resolve(ent_name, disp)
        if e:
            abbr_ent[ab] = e
        else:
            ambiguous.append((ab, tgt or disp))
    dup_ents = [e for e, n in Counter(abbr_ent.values()).items() if n > 1]            # two grid abbreviations on one club = a mapping error: drop both, never guess
    for ab in [a for a, e in abbr_ent.items() if e in dup_ents]:
        ambiguous.append((ab, "maps to the same club as another abbreviation"))
        del abbr_ent[ab]
    fd = pd.read_csv(FD_FILE[key], encoding="utf-8-sig", on_bad_lines="skip")
    fd["date"] = pd.to_datetime(fd.Date, dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    fd = fd.dropna(subset=["date", "FTHG", "FTAG"])
    fd_map, fd_unmatched = {}, []
    for r in fd.itertuples():
        h, a = H.resolve(ent_name, r.HomeTeam), H.resolve(ent_name, r.AwayTeam)
        if h and a:
            fd_map[(h, a)] = (r.date, int(r.FTHG), int(r.FTAG))
        else:
            fd_unmatched.append((r.date, r.HomeTeam, r.AwayTeam))
    of_date = {}
    for m in ft.parse_text((RAW / f"openfootball_{key}.txt").read_text(encoding="utf-8"), 2026)[1]:
        h, a = H.resolve(ent_name, m["team1"]), H.resolve(ent_name, m["team2"])
        if h and a:
            of_date[(h, a)] = m["date"]
    pairs = set()
    for (a, b), sc in grid.items():
        if a in abbr_ent and b in abbr_ent and sc is not None:
            pairs.add((abbr_ent[a], abbr_ent[b], sc))
    wiki_map = {(h, a): sc for h, a, sc in pairs}
    staged, held, cnt = [], [], Counter()
    for (h, a), s in stored.items():
        w, f = wiki_map.get((h, a)), fd_map.get((h, a))
        if s["status"] == "completed":                                            # audit the stored results against both sources
            if w and w != (s["hg"], s["ag"]):
                held.append(dict(kind="stored_result_vs_wikipedia_differs", home=s["home_name"], away=s["away_name"], store=f"{s['hg']}-{s['ag']}", wikipedia=f"{w[0]}-{w[1]}"))
                cnt["stored_vs_wikipedia_differs"] += 1
            if f and (f[1], f[2]) != (s["hg"], s["ag"]):
                held.append(dict(kind="stored_result_vs_footballdatauk_differs", home=s["home_name"], away=s["away_name"], store=f"{s['hg']}-{s['ag']}", footballdatauk=f"{f[1]}-{f[2]}"))
                cnt["stored_vs_fduk_differs"] += 1
            if f and f[0] != s["match_date"]:
                held.append(dict(kind="stored_result_date_vs_footballdatauk_differs", home=s["home_name"], away=s["away_name"], store=s["match_date"], footballdatauk=f[0]))
                cnt["stored_date_vs_fduk_differs"] += 1
            cnt["stored_completed_checked"] += 1
            continue
        if not w and not f:
            continue
        base = dict(competition_key=key, season="2026-27", record_id=s["record_id"], home_entity=h, away_entity=a, home=s["home_name"], away=s["away_name"], store_status=s["status"], store_date=s["match_date"],
                    wikipedia_score=None if not w else f"{w[0]}-{w[1]}", wikipedia_revision=rev["revid"], wikipedia_revision_time=rev["timestamp"],
                    footballdatauk_date=None if not f else f[0], footballdatauk_score=None if not f else f"{f[1]}-{f[2]}")
        if w and f:
            if (f[1], f[2]) != w:
                held.append(dict(base, kind="score_conflict_between_sources", reason="Wikipedia and football-data.co.uk disagree on the score"))
                cnt["score_conflict"] += 1
            elif f[0] != s["match_date"] and of_date.get((h, a)) == f[0]:             # a second, independent source (openfootball, today's file) gives the same date as football-data.co.uk
                staged.append(dict(base, tier="verified_two_sources_date_corrected", date=f[0], home_goals=w[0], away_goals=w[1], openfootball_date=of_date.get((h, a))))
                cnt["verified_date_corrected"] += 1
            elif f[0] != s["match_date"]:
                held.append(dict(base, kind="date_differs", openfootball_date=of_date.get((h, a)), reason=f"sources agree on the score; football-data.co.uk dates it {f[0]}, the store {s['match_date']}, openfootball {of_date.get((h, a))}"))
                cnt["date_differs"] += 1
            else:
                staged.append(dict(base, tier="verified_two_sources", date=s["match_date"], home_goals=w[0], away_goals=w[1]))
                cnt["verified_two_sources"] += 1
        elif w:
            held.append(dict(base, kind="single_source_wikipedia", reason="football-data.co.uk has no row for this match; the date is only the store's fixture date"))
            cnt["single_source_wikipedia"] += 1
        else:
            held.append(dict(base, kind="single_source_footballdatauk", reason="Wikipedia grid has no score yet; football-data.co.uk has no licence we can store from"))
            cnt["single_source_footballdatauk"] += 1
    sid = Counter(s["status"] for s in stored.values())
    past = [s for s in stored.values() if s["status"] != "completed" and s["match_date"] < "2026-10-28"]
    resolved = {(r["home_entity"], r["away_entity"]) for r in staged}
    summary[key] = dict(wikipedia_revision=rev["revid"], wikipedia_revision_time=rev["timestamp"], grid_abbreviations=len(names), grid_clubs_mapped=len(abbr_ent), grid_ambiguous=ambiguous, grid_scores=len(pairs),
                        footballdatauk_rows=len(fd), footballdatauk_unmatched=fd_unmatched[:5], store_completed=sid.get("completed", 0), store_open_past_date=len(past),
                        staged_verified=len(staged), held=len(held), counters=dict(cnt), still_open_past_date_after_staging=len([s for s in past if (s["h"], s["a"]) not in resolved]),
                        staged_latest=max([r["date"] for r in staged], default=None))
    if staged:
        pd.DataFrame(staged).to_csv(OUT / f"staged_results_{key}.csv", index=False, encoding="utf-8-sig")
    if held:
        pd.DataFrame(held).to_csv(OUT / f"held_{key}.csv", index=False, encoding="utf-8-sig")
(OUT / "staged_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(summary, indent=1, ensure_ascii=False, default=str)[:7500])
