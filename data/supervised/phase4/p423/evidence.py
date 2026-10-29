"""Phase 4.23: evidence loader. Reads the production store READ-ONLY and the files downloaded into staging/raw/, maps every source's club names to the store's identifiers (one-to-one) and returns, per league and
(home_entity, away_entity), what each source says (date and score). No network, no write."""
import importlib.util
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
ROOT = ROOT.parent if (ROOT / "data").exists() is False else ROOT
HERE = Path(__file__).resolve().parent
RAW = HERE / "staging" / "raw"
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "FootIQ_Dataset_Submission" / "_build"))
import footballtxt as ft  # noqa: E402

_spec = importlib.util.spec_from_file_location("H", ROOT / "data" / "supervised" / "phase4" / "p420" / "stage_helpers.py")
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)
H.ALIAS.update({"man utd": "manchester united", "man city": "manchester city", "nott m forest": "nottingham forest", "spurs": "tottenham hotspur", "wolves": "wolverhampton wanderers", "leeds": "leeds united",
                "sheffield utd": "sheffield united", "newcastle": "newcastle united", "west ham": "west ham united", "brighton": "brighton hove albion", "coventry": "coventry city", "hull": "hull city",
                "paris sg": "paris saint germain", "psg": "paris saint germain", "marseille": "olympique de marseille", "lyon": "olympique lyonnais", "st etienne": "saint etienne", "troyes": "es troyes ac",
                "ath madrid": "club atletico de madrid", "atletico": "club atletico de madrid", "atletico madrid": "club atletico de madrid", "ath bilbao": "athletic club", "athletic bilbao": "athletic club",
                "alaves": "deportivo alaves", "malaga": "malaga cf", "la coruna": "rc deportivo la coruna", "deportivo": "rc deportivo la coruna", "racing santander": "real racing club de santander",
                "espanol": "rcd espanyol de barcelona", "espanyol": "rcd espanyol de barcelona", "betis": "real betis balompie", "vallecano": "rayo vallecano de madrid", "rayo vallecano": "rayo vallecano de madrid",
                "sociedad": "real sociedad de futbol", "celta": "rc celta de vigo", "havre athletic club": "le havre ac", "estac troyes": "es troyes ac", "losc lille": "lille osc", "rc lens": "racing club de lens", "r racing club": "real racing club de santander", "rc deportivo": "rc deportivo la coruna", "as monaco": "as monaco fc", "inter": "internazionale milano", "milan": "ac milan", "roma": "as roma", "lazio": "ss lazio", "napoli": "ssc napoli"})

LEAGUES = ["EPL", "SERIEA", "LIGUE1", "BUNDESLIGA", "LALIGA"]
DB = ROOT / "data" / "footiq.sqlite"


def connect():
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def store_rows(conn, key):
    rows = [dict(r) for r in conn.execute("SELECT record_id, match_date, home_entity_id h, away_entity_id a, home_name, away_name, status, home_goals_final hg, away_goals_final ag, kickoff_local, time_precision, "
                                          "matchday_no FROM matches WHERE competition_key=? AND season='2026-27'", (key,))]
    ent = {}
    for r in rows:
        ent[r["h"]], ent[r["a"]] = r["home_name"], r["away_name"]
    return rows, ent


def of_map(key, ent):
    out = {}
    title, parsed, issues = ft.parse_text((RAW / f"openfootball_{key}.txt").read_text(encoding="utf-8"), 2026)
    for m in parsed:
        h, a = H.resolve(ent, m["team1"]), H.resolve(ent, m["team2"])
        res = m["res"] or {}
        done = res.get("status") == "scored" and res.get("ft") is not None
        if h and a:
            out[(h, a)] = dict(date=m["date"], score=tuple(res["ft"]) if done else None, time=m["kickoff_local"])
    return out


def fduk_map(key, ent):
    out = {}
    df = pd.read_csv(RAW / f"footballdatauk_{key}.csv", encoding="utf-8-sig", on_bad_lines="skip")
    df["date"] = pd.to_datetime(df.Date, dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    for r in df.dropna(subset=["date", "FTHG", "FTAG"]).itertuples():
        h, a = H.resolve(ent, r.HomeTeam), H.resolve(ent, r.AwayTeam)
        if h and a:
            out[(h, a)] = dict(date=r.date, score=(int(r.FTHG), int(r.FTAG)))
    return out


def fduk_fixtures(key, ent):
    div = dict(EPL="E0", SERIEA="I1", LIGUE1="F1", BUNDESLIGA="D1", LALIGA="SP1")[key]
    out = {}
    df = pd.read_csv(RAW / "footballdatauk_fixtures.csv", encoding="utf-8-sig", on_bad_lines="skip")
    df = df[df.Div == div]
    df["date"] = pd.to_datetime(df.Date, dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    for r in df.dropna(subset=["date"]).itertuples():
        h, a = H.resolve(ent, r.HomeTeam), H.resolve(ent, r.AwayTeam)
        if h and a:
            out[(h, a)] = dict(date=r.date, time=getattr(r, "Time", None))
    return out


def fxd_map(key, ent):
    out, unresolved = {}, []
    for x in json.loads((RAW / f"fixturedownload_{key}.json").read_text(encoding="utf-8")):
        h, a = H.resolve(ent, x["HomeTeam"]), H.resolve(ent, x["AwayTeam"])
        if not (h and a):
            unresolved.append((x["HomeTeam"], x["AwayTeam"]))
            continue
        sc = (x["HomeTeamScore"], x["AwayTeamScore"]) if x.get("HomeTeamScore") is not None else None
        out[(h, a)] = dict(date=x["DateUtc"][:10], utc=x["DateUtc"], score=sc)
    return out, unresolved


def parse_grid(w):
    """The results grid of a Wikipedia league page: ({abbreviation: (link target, display name)}, {(home abbr, away abbr): (score or None, other text)}). A cell may hold a piped link."""
    names = {}
    for m in re.finditer(r"\|\s*name_([^\s=]+)\s*=\s*([^\n]+)", w):
        v = m.group(2)
        lk = re.search(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]", v)
        names[m.group(1)] = (lk.group(1).strip(), (lk.group(2) or lk.group(1)).strip()) if lk else (None, re.sub(r"[{}|]|nowrap", "", v).strip())
    grid = {}
    for m in re.finditer(r"\|\s*match_([^\s_=]+)_([^\s=]+)\s*=\s*((?:\[\[[^\]]*\]\]|[^\n|])*)", w):      # a cell may hold a piped link, e.g. [[Chelsea F.C.-Tottenham Hotspur F.C. rivalry|0-2]]
        txt = re.sub(r"\[\[[^\]|]*\|", "", m.group(3))
        sc = re.search(r"(\d+)\s*[–−—-]\s*(\d+)", txt)
        grid[(m.group(1), m.group(2))] = ((int(sc.group(1)), int(sc.group(2))), None) if sc else (None, txt.strip())
    return names, grid


def wiki_scores(key, ent):
    tpl = RAW / f"wikipedia_{key}_table_season_api.json"
    page = json.loads((tpl if tpl.exists() else RAW / f"wikipedia_{key}_season_api.json").read_text(encoding="utf-8"))["query"]["pages"][0]
    rev = page["revisions"][0]
    w = rev["slots"]["main"]["content"]
    names, grid = parse_grid(w)
    ab = {}
    for k, (tgt, disp) in names.items():
        e = H.resolve(ent, tgt or disp) or H.resolve(ent, disp)
        if e:
            ab[k] = e
    for e, n in Counter(ab.values()).items():
        if n > 1:
            for k in [k for k, v in ab.items() if v == e]:
                del ab[k]
    out = {}
    for (a, b), (sc, other) in grid.items():
        if a in ab and b in ab:
            out[(ab[a], ab[b])] = dict(score=sc, note=other)
    return out, dict(revision=rev["revid"], timestamp=rev["timestamp"], mapped=len(ab), abbreviations=len(names))


def load(key, conn=None):
    conn = conn or connect()
    rows, ent = store_rows(conn, key)
    fx, fx_unres = fxd_map(key, ent)
    wk, wmeta = wiki_scores(key, ent)
    return dict(rows={(r["h"], r["a"]): r for r in rows}, ent=ent, of=of_map(key, ent), fduk=fduk_map(key, ent), fduk_fx=fduk_fixtures(key, ent), fxd=fx, fxd_unresolved=fx_unres, wiki=wk, wiki_meta=wmeta)
