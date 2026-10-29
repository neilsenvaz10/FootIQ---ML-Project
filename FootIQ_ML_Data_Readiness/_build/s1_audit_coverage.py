"""Step 1-3: competition-season coverage audit (2018-19 .. 2025-26) from the original submission."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

club = pd.read_csv(os.path.join(SUBWORK, "club_matches_all.csv"), low_memory=False, keep_default_na=False, na_values=[""])
club["family"] = club.competition_id.map(lambda c: FAMILY.get(c, (None, None))[0])
club = club[club.family.notna() & club.season.isin(SEASONS)].copy()


def expected(family, season):
    """(expected_scheduled, basis, confidence). Only format-derived numbers I can justify; None otherwise."""
    y = int(season[:4])
    if family in ("Premier League", "La Liga", "Serie A"):
        return 380, "20 clubs x 38 rounds", "high"
    if family == "Bundesliga":
        return 306, "18 clubs x 34 rounds", "high"
    if family == "Ligue 1":
        return (380, "20 clubs x 38 rounds", "high") if y <= 2022 else (306, "18 clubs x 34 rounds", "high")
    if family == "UEFA Champions League":
        if y == 2019:
            return 119, "96 group + 16 R16 + 4 QF(single leg) + 2 SF + 1 F (COVID reformat)", "medium"
        if y >= 2024:
            return 189, "144 league phase + 16 playoff + 16 R16 + 8 QF + 4 SF + 1 F", "high"
        return 125, "96 group + 16 R16 + 8 QF + 4 SF + 1 F", "high"
    if family == "UEFA Europa League":
        if y <= 2020:
            return (None, "COVID-reformatted knockout (2019-20); exact count not derived", "low") if y == 2019 else \
                (205, "144 group + 32 R32 + 16 R16 + 8 QF + 4 SF + 1 F", "high")
        if y >= 2024:
            return 189, "144 league phase + 16 playoff + 16 R16 + 8 QF + 4 SF + 1 F", "high"
        return 141, "96 group + 16 KO playoff + 16 R16 + 8 QF + 4 SF + 1 F", "high"
    if family == "UEFA Conference League":
        if y < 2021:
            return 0, "competition did not exist", "high"
        if y >= 2024:
            return 189, "144 league phase + 16 playoff + 16 R16 + 8 QF + 4 SF + 1 F", "high"
        return 141, "96 group + 16 KO playoff + 16 R16 + 8 QF + 4 SF + 1 F", "high"
    return None, "knockout cup: draw size/replays vary; no authoritative structural count in this audit", "none"


rows = []
cov_kinds = {"FA Cup", "EFL Cup", "Copa del Rey", "DFB-Pokal", "Coppa Italia", "Coupe de France"}
for fam in dict.fromkeys(v[0] for v in FAMILY.values()):
    for s in SEASONS:
        sub = club[(club.family == fam) & (club.season == s)]
        exp, basis, conf = expected(fam, s)
        st = sub.match_status.value_counts().to_dict()
        n_comp = int(st.get("completed", 0)) + int(st.get("awarded", 0)) + int(st.get("abandoned", 0))
        n_uns = int(st.get("unscored", 0))
        rows.append(dict(
            competition=fam, season=s, expected_matches=exp, expected_basis=basis, expected_confidence=conf,
            observed_records_in_source=len(sub), observed_completed_scored=n_comp, observed_unscored=n_uns,
            observed_postponed=int(st.get("postponed", 0)), observed_cancelled=int(st.get("cancelled", 0)),
            observed_abandoned=int(st.get("abandoned", 0)), observed_awarded=int(st.get("awarded", 0)),
            source_file_present=len(sub) > 0,
            latest_completed_date=sub[sub.match_status.isin(["completed", "awarded", "abandoned"])].match_date.max()
            if len(sub) else None))
cm = pd.DataFrame(rows)
cm["missing_vs_expected"] = [(e - c) if pd.notna(e) else None for e, c in zip(cm.expected_matches, cm.observed_completed_scored)]
cm.to_csv(os.path.join(WORK, "coverage_baseline.csv"), index=False, encoding=ENC)
pd.set_option("display.width", 250)
print(cm[["competition", "season", "expected_matches", "observed_records_in_source", "observed_completed_scored",
          "observed_unscored", "observed_postponed", "observed_cancelled", "missing_vs_expected", "latest_completed_date"]].to_string())
