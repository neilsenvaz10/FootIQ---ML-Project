"""Phase 4.17B: the 104 staged 2026-27 Nations League results (CC0 dataset) against UEFA's own results page, read from uefa.com on 2026-10-28. Read-only; writes unl_verification.json."""
import difflib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent
SRC = "https://www.uefa.com/uefanationsleague/news/02a2-1fea18abbcbc-456e846509e7-1000--2026-27-uefa-nations-league-all-the-league-phase-fixtures-a/"
TEXT = """24 Sept|Andorra|1-2|Malta;24 Sept|Netherlands|1-1|Germany;24 Sept|Serbia|1-2|Greece;24 Sept|Norway|3-2|Denmark;24 Sept|Portugal|1-0|Wales;24 Sept|Austria|3-1|Israel;24 Sept|Kosovo|1-0|Republic of Ireland;24 Sept|Liechtenstein|0-2|Lithuania;
25 Sept|Georgia|0-1|Northern Ireland;25 Sept|Armenia|2-0|Latvia;25 Sept|Italy|0-2|Belgium;25 Sept|Türkiye|0-1|France;25 Sept|Hungary|0-1|Ukraine;25 Sept|Poland|0-0|Bosnia and Herzegovina;25 Sept|Sweden|2-1|Romania;25 Sept|Montenegro|2-1|Cyprus;
26 Sept|Slovenia|0-0|Scotland;26 Sept|San Marino|0-7|Finland;26 Sept|Faroe Islands|1-1|Kazakhstan;26 Sept|Bulgaria|1-2|Luxembourg;26 Sept|Iceland|1-1|Estonia;26 Sept|Czechia|1-2|Croatia;26 Sept|England|2-3|Spain;26 Sept|North Macedonia|0-3|Switzerland;26 Sept|Albania|2-0|Belarus;26 Sept|Slovakia|2-0|Moldova;
27 Sept|Lithuania|1-1|Azerbaijan;27 Sept|Serbia|1-2|Netherlands;27 Sept|Denmark|2-0|Wales;27 Sept|Austria|3-1|Kosovo;27 Sept|Gibraltar|0-0|Andorra;27 Sept|Germany|0-1|Greece;27 Sept|Norway|1-2|Portugal;27 Sept|Israel|0-3|Republic of Ireland;
28 Sept|Georgia|0-0|Ukraine;28 Sept|Armenia|2-3|Montenegro;28 Sept|Latvia|0-0|Cyprus;28 Sept|Belgium|0-1|France;28 Sept|Türkiye|1-4|Italy;28 Sept|Northern Ireland|0-0|Hungary;28 Sept|Romania|2-4|Bosnia and Herzegovina;28 Sept|Sweden|3-1|Poland;
29 Sept|Finland|0-0|Belarus;29 Sept|Moldova|1-1|Faroe Islands;29 Sept|Czechia|0-2|England;29 Sept|Spain|4-1|Croatia;29 Sept|Scotland|0-3|Switzerland;29 Sept|Slovenia|2-0|North Macedonia;29 Sept|San Marino|0-3|Albania;29 Sept|Slovakia|2-1|Kazakhstan;29 Sept|Bulgaria|0-0|Estonia;29 Sept|Luxembourg|0-3|Iceland;
1 Oct|Azerbaijan|0-0|Liechtenstein;1 Oct|Germany|2-0|Serbia;1 Oct|Greece|2-2|Netherlands;1 Oct|Denmark|2-4|Portugal;1 Oct|Wales|2-1|Norway;1 Oct|Israel|0-0|Kosovo;1 Oct|Republic of Ireland|2-2|Austria;1 Oct|Malta|1-1|Gibraltar;
2 Oct|Kazakhstan|1-2|Moldova;2 Oct|Cyprus|2-0|Armenia;2 Oct|Latvia|1-2|Montenegro;2 Oct|Belgium|3-0|Türkiye;2 Oct|France|1-1|Italy;2 Oct|Hungary|1-0|Georgia;2 Oct|Ukraine|0-3|Northern Ireland;2 Oct|Bosnia and Herzegovina|1-1|Sweden;2 Oct|Poland|6-0|Romania;2 Oct|Faroe Islands|1-1|Slovakia;
3 Oct|Finland|2-1|Albania;3 Oct|Croatia|0-7|England;3 Oct|Belarus|4-0|San Marino;3 Oct|Estonia|1-0|Luxembourg;3 Oct|Iceland|3-0|Bulgaria;3 Oct|Spain|3-1|Czechia;3 Oct|North Macedonia|0-2|Scotland;3 Oct|Switzerland|2-1|Slovenia;
4 Oct|Azerbaijan|1-0|Lithuania;4 Oct|Kosovo|1-1|Austria;4 Oct|Malta|1-0|Andorra;4 Oct|Greece|0-0|Germany;4 Oct|Netherlands|2-1|Serbia;4 Oct|Portugal|2-1|Norway;4 Oct|Wales|0-1|Denmark;4 Oct|Republic of Ireland|1-1|Israel;
5 Oct|Cyprus|2-1|Latvia;5 Oct|France|4-1|Belgium;5 Oct|Italy|3-1|Türkiye;5 Oct|Northern Ireland|0-0|Georgia;5 Oct|Ukraine|1-2|Hungary;5 Oct|Bosnia and Herzegovina|1-0|Poland;5 Oct|Romania|0-1|Sweden;5 Oct|Montenegro|0-0|Armenia;
6 Oct|Kazakhstan|2-2|Faroe Islands;6 Oct|Croatia|1-2|Spain;6 Oct|England|3-0|Czechia;6 Oct|Scotland|1-2|Slovenia;6 Oct|Switzerland|3-0|North Macedonia;6 Oct|Albania|2-1|San Marino;6 Oct|Belarus|1-0|Finland;6 Oct|Moldova|0-4|Slovakia;6 Oct|Estonia|0-0|Iceland;6 Oct|Luxembourg|0-2|Bulgaria"""
ALIAS = {"turkiye": "turkey", "czechia": "czechrepublic"}
MONTH = {"Sept": "09", "Oct": "10"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    return ALIAS.get(s, s)


official = []
for item in TEXT.replace("\n", "").split(";"):
    d, h, sc, a = item.split("|")
    day, mon = d.split()
    hg, ag = sc.split("-")
    official.append((f"2026-{MONTH[mon]}-{int(day):02d}", h, int(hg), int(ag), a))
new = pd.read_csv(OUT / "staging" / "martj42" / "unpacked" / "international_results-master" / "results.csv")
st = new[(new.tournament == "UEFA Nations League") & (new.date >= "2026-06-03")].copy()
used, rows = set(), []
for date, h, hg, ag, a in official:
    c = [r for r in st.itertuples() if r.Index not in used and r.date == date and r.home_score == hg and r.away_score == ag and norm(r.home_team) == norm(h) and norm(r.away_team) == norm(a)]
    if c:
        used.add(c[0].Index)
        rows.append(("verified", date, h, hg, ag, a))
    else:
        near = [r for r in st.itertuples() if r.home_team and norm(r.home_team) == norm(h) and norm(r.away_team) == norm(a)]
        rows.append(("DISPUTED: date or score differs" if near else "unsupported: no staged match", date, h, hg, ag, a, [f"{r.date} {r.home_team} {r.home_score}-{r.away_score} {r.away_team}" for r in near]))
extra = [f"{r.date} {r.home_team} {r.home_score}-{r.away_score} {r.away_team}" for r in st.itertuples() if r.Index not in used]
res = dict(source=SRC, retrieved="2026-10-28", official=len(official), staged=len(st), verified=sum(1 for r in rows if r[0] == "verified"), problems=[r for r in rows if r[0] != "verified"], staged_without_official=extra)
(OUT / "unl_verification.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "source"}, indent=1, ensure_ascii=False))
