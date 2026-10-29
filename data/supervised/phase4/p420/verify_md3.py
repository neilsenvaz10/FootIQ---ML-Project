"""Phase 4.20 part B: verify the 18 staged Champions League matchday-3 results against UEFA's own results page (read 2026-10-28 with a single page read; lines transcribed below) and write the gate file
for the importer: ucl_verified_results.csv = matchday 2 (Phase 4.19 gate) + matchday 3. OFFLINE; nothing is imported."""
import importlib.util
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("H", HERE / "stage_helpers.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
OFFICIAL_MD3 = [  # (date, home, home goals, away goals, away) as printed on uefa.com
    ("2026-10-20", "Manchester City", 5, 1, "AEK Athens"), ("2026-10-21", "Bayern München", 2, 2, "Arsenal"), ("2026-10-21", "Aston Villa", 3, 1, "Viking"), ("2026-10-20", "Stuttgart", 1, 1, "Atlético de Madrid"),
    ("2026-10-20", "Napoli", 4, 3, "Bodø/Glimt"), ("2026-10-20", "Paris Saint-Germain", 4, 2, "Barcelona"), ("2026-10-20", "Sabah", 1, 2, "Borussia Dortmund"), ("2026-10-21", "Club Brugge", 3, 0, "Lens"),
    ("2026-10-21", "Lille", 2, 4, "Galatasaray"), ("2026-10-21", "Inter", 1, 0, "Shakhtar Donetsk"), ("2026-10-20", "Fenerbahçe", 2, 2, "Slavia Praha"), ("2026-10-20", "Liverpool", 4, 3, "Villarreal"),
    ("2026-10-21", "Real Betis", 1, 0, "Feyenoord"), ("2026-10-21", "Como", 4, 1, "Manchester United"), ("2026-10-20", "Roma", 4, 0, "Slovan Bratislava"), ("2026-10-21", "Sporting CP", 2, 3, "LASK"),
    ("2026-10-21", "Real Madrid", 4, 1, "Leipzig"), ("2026-10-20", "Porto", 0, 1, "PSV Eindhoven")]
st = pd.read_csv(HERE / "staging" / "uefa_2026_27_staging_v2.csv", encoding="utf-8-sig")
md3 = st[(st.matchday == 3) & (st.status == "played")].reset_index(drop=True)
used, rows, problems = set(), [], []
for r in md3.itertuples():
    hit = [i for i, o in enumerate(OFFICIAL_MD3) if i not in used and o[0] == r.date and o[2] == int(r.home_goals) and o[3] == int(r.away_goals) and H.alike(o[1], r.home) and H.alike(o[4], r.away)]
    if hit:
        used.add(hit[0])
        rows.append(dict(competition_key="UCL", season="2026-27", matchday=3, date=r.date, home_entity=r.home_entity, away_entity=r.away_entity, home_goals=int(r.home_goals), away_goals=int(r.away_goals),
                         verified_against="uefa.com results page, read 2026-10-28 (Phase 4.20)", wikipedia_revision=r.page_revid))
    else:
        problems.append(f"{r.date} {r.home} {r.home_goals}-{r.away_goals} {r.away}")
md2 = pd.read_csv(HERE.parent / "p419" / "md2_verified_results.csv", encoding="utf-8-sig")
gate = pd.concat([md2, pd.DataFrame(rows)], ignore_index=True)
gate.to_csv(HERE / "staging" / "ucl_verified_results.csv", index=False, encoding="utf-8-sig")
print(f"staged matchday-3 results: {len(md3)}; official lines: {len(OFFICIAL_MD3)}; verified: {len(rows)}; problems: {problems}; gate rows: {len(gate)}")
