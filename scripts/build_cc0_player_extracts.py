"""Phase 4.37 maintainer tool: CC0-only extracts of the Phase 4 player tables, from ROW-LEVEL provenance (`source_dataset` / `source_name` / `source_repos`).
Keeps a row only when its recorded source is openfootball (CC0 1.0) or martj42 (CC0 1.0); any row that names StatsBomb anywhere is dropped. The originals are not changed.
Writes FootIQ_Dataset_Submission/cc0_extracts/*.csv, README.md and EXTRACT_MANIFEST.json."""
import hashlib, json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "FootIQ_Dataset_Submission"
OUT = SRC / "cc0_extracts"
OUT.mkdir(exist_ok=True)
SB = re.compile(r"statsbomb|\bsb_|open-data", re.I)
CC0_SRC = re.compile(r"^(openfootball|martj42)", re.I)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(name):
    return pd.read_csv(SRC / name, dtype=str, encoding="utf-8-sig", keep_default_na=False)


def row_has_sb(df):
    return df.apply(lambda col: col.str.contains(SB)).any(axis=1)


man = {}
p04 = rd("04_Football_Players.csv")
p05 = rd("05_Player_Match_Statistics.csv")
p06 = rd("06_Teams.csv")
p07 = rd("07_Competitions.csv")
p08 = rd("08_Player_Team_Memberships.csv")
k04 = p04[p04.source_dataset.str.match(CC0_SRC) & ~row_has_sb(p04)]
k05 = p05[p05.source_dataset.str.match(CC0_SRC) & ~row_has_sb(p05)]
k08 = p08[p08.source_dataset.str.match(CC0_SRC) & ~row_has_sb(p08)]
k06 = p06[p06.source_name.str.match(CC0_SRC) & ~row_has_sb(p06)]
k07 = p07[p07.source_name.str.match(CC0_SRC) & ~row_has_sb(p07)]
# referential integrity inside the extract
k05 = k05[k05.player_id.isin(set(k04.player_id))]
k08 = k08[k08.player_id.isin(set(k04.player_id))]
for name, full, kept in (("04_Football_Players", p04, k04), ("05_Player_Match_Statistics", p05, k05), ("06_Teams", p06, k06), ("07_Competitions", p07, k07), ("08_Player_Team_Memberships", p08, k08)):
    fn = f"{name}_CC0.csv"
    kept.to_csv(OUT / fn, index=False, encoding="utf-8-sig")
    man[fn] = dict(source=f"FootIQ_Dataset_Submission/{name}.csv", rows_in_original=len(full), rows_kept=len(kept), rows_dropped=len(full) - len(kept), sha256=sha(OUT / fn),
                   sources_kept=kept[[c for c in kept.columns if c in ("source_dataset", "source_name")][0]].value_counts().to_dict())
checks = dict(
    statsbomb_cells=int(sum(row_has_sb(pd.read_csv(OUT / f"{n}_CC0.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False)).sum() for n in ("04_Football_Players", "05_Player_Match_Statistics", "06_Teams", "07_Competitions", "08_Player_Team_Memberships"))),
    players_in_05_not_in_04=int((~k05.player_id.isin(set(k04.player_id))).sum()),
    players_without_any_appearance_or_squad_row=int((~k04.player_id.isin(set(k05.player_id) | set(k08.player_id))).sum()),
)
# the per-player counters of the original must match the extract (proves they were not computed over mixed sources)
cnt = k05.groupby("player_id").size()
c04 = k04.set_index("player_id").n_match_appearance_records.astype(float)
checks["players_whose_appearance_counter_differs_from_extract"] = int(((c04 - cnt.reindex(c04.index).fillna(0)).abs() > 0).sum())
man["_checks"] = checks
(OUT / "EXTRACT_MANIFEST.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
(OUT / "README.md").write_text("""# CC0-only player extracts (Phase 4.37)

Row-level extracts of `04_Football_Players`, `05_Player_Match_Statistics`, `06_Teams`, `07_Competitions` and `08_Player_Team_Memberships` that contain **only rows whose recorded source is openfootball (CC0 1.0) or martj42/international_results (CC0 1.0)**.
Every row naming StatsBomb in any column was dropped (the StatsBomb Public Data User Agreement, section 1.2.1, forbids providing the data to third parties). The original tables stay on the maintainer's machine, unchanged.
`EXTRACT_MANIFEST.json` lists rows kept and dropped per table, SHA-256 of every extract and the integrity checks. Regenerate: `python scripts/build_cc0_player_extracts.py` (needs the original tables).
Credit: openfootball (github.com/openfootball) and Mart Jurisoo (github.com/martj42/international_results), both CC0 1.0; no attribution is required.
""", encoding="utf-8")
print(json.dumps(man, indent=1, ensure_ascii=False)[:3500])
