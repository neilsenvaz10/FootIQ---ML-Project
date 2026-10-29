"""Phase 4.21 part C: verify the 90 staged Champions League fixtures (matchdays 4-8) against UEFA's own fixture list (one page read on 2026-10-28; lines transcribed below, dates as UEFA prints them)
and write the fixtures gate for the importer: ucl_verified_fixtures.csv. OFFLINE; nothing is imported.
Two lines of the page contradicted themselves (the Dortmund v AEK Athens line also showed 28/01, the Sabah v Napoli line 20/01/2026): the matchday dates 27/01/2027 and 20/01/2027 that every other line gives are used."""
import importlib.util
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("H", HERE.parent / "p420" / "stage_helpers.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

RAW = """
4|2026-11-03|Atlético de Madrid|Bayern München;4|2026-11-03|Barcelona|Aston Villa;4|2026-11-03|Manchester United|Roma;4|2026-11-03|Feyenoord|Inter;4|2026-11-03|Bodø/Glimt|Lille;4|2026-11-03|Galatasaray|Stuttgart
4|2026-11-03|Shakhtar Donetsk|Sporting CP;4|2026-11-03|LASK|Slovan Bratislava;4|2026-11-03|Villarreal|Paris Saint-Germain;4|2026-11-04|AEK Athens|Real Madrid;4|2026-11-04|Slavia Praha|Arsenal;4|2026-11-04|Lens|Como
4|2026-11-04|Fenerbahçe|Liverpool;4|2026-11-04|Leipzig|Manchester City;4|2026-11-04|PSV Eindhoven|Club Brugge;4|2026-11-04|Porto|Napoli;4|2026-11-04|Borussia Dortmund|Real Betis;4|2026-11-04|Viking|Sabah
5|2026-11-24|Como|AEK Athens;5|2026-11-24|Arsenal|Borussia Dortmund;5|2026-11-24|Galatasaray|Aston Villa;5|2026-11-24|Bodø/Glimt|LASK;5|2026-11-24|Leipzig|Lens;5|2026-11-24|Real Madrid|PSV Eindhoven
5|2026-11-24|Feyenoord|Porto;5|2026-11-24|Manchester City|Napoli;5|2026-11-24|Slovan Bratislava|Real Betis;5|2026-11-25|Atlético de Madrid|Viking;5|2026-11-25|Sabah|Barcelona;5|2026-11-25|Shakhtar Donetsk|Fenerbahçe
5|2026-11-25|Sporting CP|Manchester United;5|2026-11-25|Inter|Stuttgart;5|2026-11-25|Slavia Praha|Villarreal;5|2026-11-25|Club Brugge|Liverpool;5|2026-11-25|Lille|Bayern München;5|2026-11-25|Paris Saint-Germain|Roma
6|2026-12-08|AEK Athens|Galatasaray;6|2026-12-08|Aston Villa|Paris Saint-Germain;6|2026-12-08|Bayern München|Slavia Praha;6|2026-12-08|Barcelona|Manchester City;6|2026-12-08|Manchester United|Leipzig;6|2026-12-08|Napoli|Club Brugge
6|2026-12-08|Roma|Sporting CP;6|2026-12-08|Villarreal|Sabah;6|2026-12-08|Viking|Feyenoord;6|2026-12-09|Arsenal|Real Madrid;6|2026-12-09|Lens|Bodø/Glimt;6|2026-12-09|Borussia Dortmund|Inter
6|2026-12-09|Real Betis|Como;6|2026-12-09|Liverpool|Porto;6|2026-12-09|LASK|Fenerbahçe;6|2026-12-09|PSV Eindhoven|Atlético de Madrid;6|2026-12-09|Stuttgart|Lille;6|2026-12-09|Slovan Bratislava|Shakhtar Donetsk
7|2027-01-19|AEK Athens|Roma;7|2027-01-19|Aston Villa|Borussia Dortmund;7|2027-01-19|Bodø/Glimt|Atlético de Madrid;7|2027-01-19|Stuttgart|Club Brugge;7|2027-01-19|Galatasaray|Feyenoord;7|2027-01-19|Real Madrid|LASK
7|2027-01-19|Inter|Liverpool;7|2027-01-19|Lille|Slovan Bratislava;7|2027-01-19|Porto|Slavia Praha;7|2027-01-20|Real Betis|Arsenal;7|2027-01-20|Manchester United|Bayern München;7|2027-01-20|Como|Paris Saint-Germain
7|2027-01-20|Sabah|Napoli;7|2027-01-20|Fenerbahçe|Villarreal;7|2027-01-20|Leipzig|Shakhtar Donetsk;7|2027-01-20|Sporting CP|Barcelona;7|2027-01-20|Lens|Manchester City;7|2027-01-20|Viking|PSV Eindhoven
8|2027-01-27|Borussia Dortmund|AEK Athens;8|2027-01-27|Arsenal|Sabah;8|2027-01-27|Slavia Praha|Aston Villa;8|2027-01-27|Atlético de Madrid|Fenerbahçe;8|2027-01-27|Barcelona|Como;8|2027-01-27|Bayern München|Real Betis
8|2027-01-27|Club Brugge|Bodø/Glimt;8|2027-01-27|Feyenoord|Leipzig;8|2027-01-27|Liverpool|Lens;8|2027-01-27|LASK|Porto;8|2027-01-27|Manchester City|Sporting CP;8|2027-01-27|Napoli|Viking
8|2027-01-27|PSV Eindhoven|Stuttgart;8|2027-01-27|Paris Saint-Germain|Galatasaray;8|2027-01-27|Shakhtar Donetsk|Real Madrid;8|2027-01-27|Roma|Lille;8|2027-01-27|Villarreal|Manchester United;8|2027-01-27|Slovan Bratislava|Inter
"""
OFFICIAL = [tuple(x.split("|")) for line in RAW.strip().splitlines() for x in line.split(";")]
OFFICIAL = [(int(m), d, h, a) for m, d, h, a in OFFICIAL]

st = pd.read_csv(HERE.parent / "p420" / "staging" / "uefa_2026_27_staging_v2.csv", encoding="utf-8-sig")
fx = st[(st.status == "scheduled")].reset_index(drop=True)
used, gate, problems = set(), [], []
for r in fx.itertuples():
    hit = [i for i, o in enumerate(OFFICIAL) if i not in used and o[0] == r.matchday and o[1] == r.date and H.alike(o[2], r.home) and H.alike(o[3], r.away)]
    if hit:
        used.add(hit[0])
        gate.append(dict(competition_key="UCL", season="2026-27", matchday=int(r.matchday), date=r.date, home_entity=r.home_entity, away_entity=r.away_entity, home=r.home, away=r.away,
                         verified_against="uefa.com fixtures list, read 2026-10-28 (Phase 4.21)", wikipedia_revision=r.page_revid))
    else:
        problems.append(f"MD{r.matchday} {r.date} {r.home} v {r.away}")
extra = [OFFICIAL[i] for i in range(len(OFFICIAL)) if i not in used]
pd.DataFrame(gate).to_csv(HERE / "ucl_verified_fixtures.csv", index=False, encoding="utf-8-sig")
print(f"staged fixtures: {len(fx)}; official lines: {len(OFFICIAL)}; verified: {len(gate)}; staged not on UEFA's list: {problems}; UEFA lines not staged: {extra}")
