"""Phase 4.17B: compare the STAGED 2026-27 UEFA results (from the saved Wikipedia snapshots) with UEFA's OWN published results, read from uefa.com on 2026-10-28 (WebFetch of the pages named in
OFFICIAL_SOURCES; the lists below are transcribed from those fetches). A staged match is VERIFIED when UEFA lists the same date, the same two teams (names compared after normalisation) and the same score.
Read-only on project files; writes data/supervised/phase4/p417/uefa_verification.json."""
import difflib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent
OFFICIAL_SOURCES = {
    "UCL": "https://www.uefa.com/uefachampionsleague/news/02a8-2176fa83582b-d99f0b27f405-1000--champions-league-league-phase-fixtures-and-results/",
    "UEL": "https://www.uefa.com/uefaeuropaleague/news/02a8-2174cafa5bb6-82bbc20c9b92-1000--2026-27-europa-league-all-the-league-phase-fixtures-and-re/",
    "UECL": "https://www.uefa.com/uefaconferenceleague/news/02a8-2174cb200f25-b94693ddff4e-1000--2026-27-conference-league-all-the-league-phase-fixtures/",
}
RETRIEVED = "2026-10-28"
D13, D14, D15 = "2026-10-13", "2026-10-14", "2026-10-15"
OFFICIAL = {
    ("UCL", 2): [(D13, "Arsenal", 3, 0, "Lille"), (D13, "Inter", 3, 4, "Club Brugge"), (D13, "Atlético de Madrid", 2, 0, "Manchester United"), (D13, "Galatasaray", 1, 4, "Barcelona"), (D13, "Viking", 3, 3, "Bayern München"),
                 (D13, "Leipzig", 1, 0, "PSV Eindhoven"), (D13, "Sabah", 2, 0, "Slavia Praha"), (D13, "Lens", 0, 2, "Sporting CP"), (D13, "Villarreal", 3, 1, "Napoli"), (D14, "Shakhtar Donetsk", 3, 1, "AEK Athens"),
                 (D14, "Aston Villa", 6, 0, "Fenerbahçe"), (D14, "Bodø/Glimt", 1, 0, "Borussia Dortmund"), (D14, "LASK", 3, 6, "Liverpool"), (D14, "Feyenoord", 3, 2, "Como"), (D14, "Manchester City", 2, 4, "Paris Saint-Germain"),
                 (D14, "Roma", 3, 4, "Real Madrid"), (D14, "Real Betis", 3, 2, "Porto"), (D14, "Slovan Bratislava", 0, 3, "Stuttgart")],
    ("UEL", 1): [("2026-09-16", "Ararat-Armenia", 1, 4, "Sparta Praha"), ("2026-09-16", "Omonia", 1, 0, "Celta"), ("2026-09-16", "Milan", 0, 2, "Benfica"), ("2026-09-16", "Leverkusen", 2, 0, "Celje"),
                 ("2026-09-16", "Hapoel Beer-Sheva", 0, 0, "GNK Dinamo"), ("2026-09-16", "Olympiacos", 2, 1, "Jagiellonia"), ("2026-09-16", "Anderlecht", 1, 2, "Lyon"), ("2026-09-16", "Sturm Graz", 0, 0, "Rennes"),
                 ("2026-09-16", "Sunderland", 1, 0, "AZ Alkmaar"), ("2026-09-17", "OFI Crete", 2, 0, "Hoffenheim"), ("2026-09-17", "Levski Sofia", 0, 1, "Salzburg"), ("2026-09-17", "Beşiktaş", 4, 1, "Marseille"),
                 ("2026-09-17", "Celtic", 1, 3, "Ferencváros"), ("2026-09-17", "Crystal Palace", 4, 0, "Lech Poznań"), ("2026-09-17", "Viktoria Plzeň", 0, 3, "Union SG"), ("2026-09-17", "Juventus", 5, 0, "N.E.C. Nijmegen"),
                 ("2026-09-17", "Lillestrøm", 1, 2, "Torreense"), ("2026-09-17", "Real Sociedad", 1, 2, "Bournemouth")],
    ("UEL", 2): [(D15, "Sparta Praha", 1, 1, "Lillestrøm"), (D15, "AZ Alkmaar", 2, 1, "Hapoel Beer-Sheva"), (D15, "Salzburg", 0, 4, "Milan"), (D15, "Lech Poznań", 0, 4, "Leverkusen"), (D15, "Celje", 0, 3, "Omonia"),
                 (D15, "Lyon", 3, 2, "Crystal Palace"), (D15, "Union SG", 1, 1, "Real Sociedad"), (D15, "Torreense", 1, 2, "Sunderland"), (D15, "Bournemouth", 3, 0, "Sturm Graz"), (D15, "Ferencváros", 2, 1, "Viktoria Plzeň"),
                 (D15, "GNK Dinamo", 1, 0, "Anderlecht"), (D15, "Jagiellonia", 3, 1, "Ararat-Armenia"), (D15, "N.E.C. Nijmegen", 1, 1, "Levski Sofia"), (D15, "Marseille", 0, 1, "Olympiacos"), (D15, "Celta", 1, 2, "Juventus"),
                 (D15, "Benfica", 4, 1, "Celtic"), (D15, "Rennes", 2, 1, "OFI Crete"), (D15, "Hoffenheim", 2, 3, "Beşiktaş")],
    ("UECL", 1): [(D15, "Lugano", 3, 2, "Crvena Zvezda"), (D15, "Hajduk Split", 2, 1, "Ajax"), (D15, "Gent", 1, 0, "Aarhus"), (D15, "Egnatia", 1, 1, "Midtjylland"), (D15, "KuPS Kuopio", 2, 4, "Trabzonspor"),
                  (D15, "Mjällby", 2, 0, "Inter Escaldes"), (D15, "Panathinaikos", 2, 1, "Borac"), (D15, "CSKA Sofia", 1, 2, "Monaco"), (D15, "Riga", 1, 1, "Kairat Almaty"), (D15, "Universitatea Craiova", 1, 1, "Getafe"),
                  (D15, "Atalanta", 3, 1, "Pafos"), (D15, "Brighton", 4, 0, "Kauno Žalgiris"), (D15, "Copenhagen", 3, 0, "Braga"), (D15, "Twente", 1, 0, "Thun"), (D15, "Hearts", 1, 1, "Nordsjælland"),
                  (D15, "Sint-Truidense", 2, 0, "Iberia Tbilisi"), (D15, "Freiburg", 3, 2, "Jablonec"), (D15, "Brann", 2, 1, "Lincoln Red Imps")],
}
STOP = {"fc", "cf", "sk", "fk", "afc", "ac", "as", "sc", "ssc", "sv", "bv", "tsg", "vfb", "vfl", "rb", "rc", "1", "club", "de", "the", "nk", "kv", "ks", "if", "bk", "fc.", "fk."}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return "".join(t for t in s.split() if t not in STOP)


def similar(a, b):
    na, nb = norm(a), norm(b)
    return na == nb or (len(na) >= 4 and len(nb) >= 4 and (na in nb or nb in na)) or difflib.SequenceMatcher(None, na, nb).ratio() >= 0.8


st = pd.read_csv(OUT / "uefa_2026_27_staging.csv")
rep = {"sources": OFFICIAL_SOURCES, "retrieved": RETRIEVED, "results": {}}
for (k, md), lst in OFFICIAL.items():
    d = st[(st.competition_key == k) & (st.matchday == md) & (st.status == "played")]
    rows, used = [], set()
    for date, h, hg, ag, a in lst:
        cand = [r for r in d.itertuples() if r.Index not in used and str(r.date) == date and int(r.home_goals) == hg and int(r.away_goals) == ag and (similar(r.home, h) or similar(r.away, a))]
        cand.sort(key=lambda r: -(similar(r.home, h) + similar(r.away, a)))                  # same date and score, at least one team name alike; both alike first
        if cand:
            used.add(cand[0].Index)
            alias = [] if similar(cand[0].home, h) and similar(cand[0].away, a) else [f"{cand[0].home if not similar(cand[0].home, h) else cand[0].away} = {h if not similar(cand[0].home, h) else a}"]
            rows.append(dict(date=date, official=f"{h} {hg}-{ag} {a}", staged=f"{cand[0].home} {int(cand[0].home_goals)}-{int(cand[0].away_goals)} {cand[0].away}", verdict="verified", name_variant_bridged=alias))
        else:
            near = [r for r in d.itertuples() if str(r.date) == date and similar(r.home, h) and similar(r.away, a)]
            rows.append(dict(date=date, official=f"{h} {hg}-{ag} {a}", staged=(f"{near[0].home} {int(near[0].home_goals)}-{int(near[0].away_goals)} {near[0].away}" if near else None), verdict=("DISPUTED: score or date differs" if near else "unsupported: no staged match")))
    extra = [f"{r.home} {int(r.home_goals)}-{int(r.away_goals)} {r.away}" for r in d.itertuples() if r.Index not in used]
    rep["results"][f"{k} matchday {md}"] = dict(official=len(lst), staged_played=len(d), verified=sum(1 for r in rows if r["verdict"] == "verified"), problems=[r for r in rows if r["verdict"] != "verified"], name_variants=[x for r in rows for x in r.get("name_variant_bridged", [])], staged_without_official=extra)
(OUT / "uefa_verification.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: {x: v[x] for x in ("official", "staged_played", "verified", "problems", "name_variants", "staged_without_official")} for k, v in rep["results"].items()}, indent=1, ensure_ascii=False))
