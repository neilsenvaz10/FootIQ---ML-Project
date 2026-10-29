"""Phase 4.38: source and licence of every row of the 8 proposed LFS files (read-only). Writes p438/out/lfs_licence_check.json"""
import json, re
from pathlib import Path
import pandas as pd
ROOT = Path("D:/Foot IQ")
LFS = ["FootIQ_Dataset_Submission/02_Historical_Club_Matches.csv", "FootIQ_ML_Data_Readiness/04d_COMBINED_CLUB_MATCHES_v1.0.csv", "FootIQ_ML_Data_Readiness/08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv",
       "FootIQ_ML_Data_Readiness/04a_LEAGUE_RESULTS_v1.0.csv", "FootIQ_ML_Data_Readiness/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv", "FootIQ_ML_Training_Preparation/03_ROW_LEVEL_CORRECTION_AND_EXCLUSION_LOG_v1.1.csv",
       "FootIQ_ML_Training_Preparation/01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv", "FootIQ_ML_Training_Preparation/_build/work/V_universe.pkl"]
bad = re.compile(r"football-?data|fixturedownload|api-?football|api-sports|statsbomb|provider_|guardian|apnews|fifa\.com", re.I)
out = {}
for f in LFS:
    p = ROOT / f
    df = pd.read_pickle(p) if f.endswith(".pkl") else pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False, encoding="utf-8-sig")
    df = df.astype(str)
    cols = df.columns.tolist()
    src = [c for c in cols if c.lower() in ("source_system", "source", "source_name", "licence", "license", "source_dataset")]
    d = dict(rows=len(df), source_columns=src)
    for c in src[:3]:
        d[c] = df[c].value_counts().head(8).to_dict()
    d["restricted_marker_cells"] = int(df.apply(lambda s: s.str.contains(bad)).sum().sum())
    d["restricted_marker_columns"] = [c for c in cols if bad.search(c)]
    out[f] = d
    print(f, d["rows"], {k: d[k] for k in src[:2]}, "restricted cells:", d["restricted_marker_cells"], d["restricted_marker_columns"])
json.dump(out, open(ROOT / "data/supervised/phase4/p438/out/lfs_licence_check.json", "w"), indent=1, default=str)
