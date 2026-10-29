"""Phase 4.19 step 2: per-match verification of the 18 Champions League matchday-2 results (13-14 Oct 2026). OFFLINE and READ-ONLY.
Compares, for every match: the staged row (saved Wikipedia revision) <-> the official UEFA results transcribed in Phase 4.17B (data/supervised/phase4/p417/verify_uefa.py, read from uefa.com on 2026-10-28)
<-> the production store (opened mode=ro). Writes md2_verification.csv and md2_verified_results.csv (the gate the importer reads). No network, nothing in the project is modified."""
import ast
import csv
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
P417 = ROOT / "data" / "supervised" / "phase4" / "p417"
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(P417))

# the official list lives in a script that runs on import, so evaluate just its OFFICIAL literal (D13/D14/D15 are the dates the script defines)
tree = ast.parse((P417 / "verify_uefa.py").read_text(encoding="utf-8"))
node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "OFFICIAL")
OFF = eval(compile(ast.Expression(node.value), "<official>", "eval"), {"D13": "2026-10-13", "D14": "2026-10-14", "D15": "2026-10-15"})[("UCL", 2)]
UEFA_PAGE = json.loads((P417 / "uefa_verification.json").read_text(encoding="utf-8"))["sources"]["UCL"]

import unicodedata, re  # noqa: E402,E401
STOP = {"fc", "cf", "sk", "fk", "afc", "ac", "as", "sc", "ssc", "sv", "bv", "tsg", "vfb", "vfl", "rb", "rc", "1", "club", "de", "the", "nk", "kv", "ks", "if", "bk"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return "".join(t for t in re.sub(r"[^a-z0-9 ]", " ", s).split() if t not in STOP)


def alike(a, b):
    na, nb = norm(a), norm(b)
    return na == nb or (len(na) >= 4 and len(nb) >= 4 and (na in nb or nb in na))


st = pd.read_csv(P417 / "uefa_2026_27_staging.csv", encoding="utf-8-sig")
st = st[(st.competition_key == "UCL") & (st.matchday == 2)].reset_index(drop=True)
c = sqlite3.connect(f"file:{(ROOT / 'data' / 'footiq.sqlite').as_posix()}?mode=ro", uri=True)
db = pd.read_sql_query("SELECT record_id, season, match_date, home_entity_id, away_entity_id, home_goals_final, away_goals_final, status FROM matches WHERE competition_key='UCL' AND season='2026-27'", c)
teams = set(r[0] for r in c.execute("SELECT entity_id FROM teams"))
c.close()

rows, gate = [], []
used = set()
for r in st.itertuples():
    cand = [o for i, o in enumerate(OFF) if i not in used and o[0] == r.date and o[2] == int(r.home_goals) and o[3] == int(r.away_goals) and alike(o[1], r.home) and alike(o[4], r.away)]
    # allow one name to differ by spelling (the official list uses short names, e.g. Slavia Praha vs SK Slavia Prague)
    if not cand:
        cand = [o for i, o in enumerate(OFF) if i not in used and o[0] == r.date and o[2] == int(r.home_goals) and o[3] == int(r.away_goals) and (alike(o[1], r.home) or alike(o[4], r.away))]
    o = cand[0] if cand else None
    if o:
        used.add(OFF.index(o))
    same_pair = db[(db.home_entity_id == r.home_entity) & (db.away_entity_id == r.away_entity)]
    rev_pair = db[(db.home_entity_id == r.away_entity) & (db.away_entity_id == r.home_entity)]
    checks = dict(
        date_ok=bool(o), home_away_ok=bool(o), score_ok=bool(o),
        competition_season_ok=r.competition_key == "UCL" and r.season == "2026-27" and 2 == r.matchday,
        identities_ok=bool(r.home_entity in teams and r.away_entity in teams and r.home_entity != r.away_entity),
        provenance_ok=bool(r.page_revid and r.page_timestamp and str(r.page_url).startswith("https://en.wikipedia.org/")),
        in_store=len(same_pair) > 0, reversed_in_store=len(rev_pair) > 0)
    ok = all(checks[k] for k in ("date_ok", "score_ok", "competition_season_ok", "identities_ok", "provenance_ok")) and not checks["in_store"] and not checks["reversed_in_store"]
    rows.append(dict(matchday=2, date=r.date, home=r.home, away=r.away, score=f"{int(r.home_goals)}-{int(r.away_goals)}", home_entity=r.home_entity, away_entity=r.away_entity,
                     official_uefa=(f"{o[1]} {o[2]}-{o[3]} {o[4]}" if o else "NOT FOUND"), **checks, wikipedia_revision=r.page_revid, wikipedia_revision_time=r.page_timestamp,
                     source_licence="CC BY-SA 4.0 (Wikipedia text)", cross_check_source=UEFA_PAGE, verdict="verified, not in store" if ok else "NOT VERIFIED"))
    if ok:
        gate.append(dict(competition_key="UCL", season="2026-27", matchday=2, date=r.date, home_entity=r.home_entity, away_entity=r.away_entity, home_goals=int(r.home_goals), away_goals=int(r.away_goals),
                         verified_against="uefa.com results page, read 2026-10-28 (Phase 4.17B transcription)", wikipedia_revision=r.page_revid))
pd.DataFrame(rows).to_csv(HERE / "md2_verification.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(gate).to_csv(HERE / "md2_verified_results.csv", index=False, encoding="utf-8-sig")
print(len(rows), "staged matchday-2 rows;", len(gate), "verified and not in the store;", len(OFF), "official lines;", len(used), "official lines matched")
print(pd.DataFrame(rows)[["date", "home", "away", "score", "official_uefa", "in_store", "verdict"]].to_string())
