"""Rebuild of the development feature table after the same-day Elo update fix (Elo2 params frozen, no grid, no re-selection)."""
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa
import v2_features as vf  # noqa

sys.stdout.reconfigure(encoding="utf-8")
proto = json.load(open(os.path.join(WORK, "protocol_frozen.json")))
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
ds = pd.read_csv(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC,
                 usecols=["record_id", "competition_id", "season_corrected", "calendar_type", "match_date", "split", "season_status", "identity_review_flag", "tier", "y_90min_1x2",
                          "home_entity_id", "away_entity_id", "competition_country"])
fe1 = pd.read_csv(os.path.join(PREP, "02_CORRECTED_FEATURE_DATASET_v1.1.csv"), low_memory=False, encoding=ENC)
ds = ds[ds.match_date <= DEV_END].copy()                         # development rows only
Vd = V[V.match_date <= DEV_END].copy()                           # the state never sees a match after 2024-06-30
df = pd.DataFrame(dict(record_id=Vd.record_id, dt=Vd.dt, h=Vd.home_entity_id, a=Vd.away_entity_id, comp=Vd.competition_id, season=Vd.season_corrected, tier=Vd.tier,
                       ctype=Vd.competition_type, regular=Vd.regular_round_robin_stage, rated=Vd.rated, gh=Vd.gh, ga=Vd.ga))
want = set(ds.record_id)
print("state universe", len(df), "development rows", len(ds), "last date", df.dt.max().date())
ds["y"] = ds.y_90min_1x2.map({"H": 0, "D": 1, "A": 2})
ds["split_year"] = ds.calendar_type.str.startswith("split")
ds["dev_primary"] = ds.season_status.isin(["complete", "in_progress_complete_through_cutoff"]) & ~ds.identity_review_flag & ds.split_year
ds["dev_secondary"] = ds.season_status.isin(["complete", "in_progress_complete_through_cutoff"]) & ~ds.identity_review_flag & ~ds.split_year


# defect-fix rebuild: Elo2 parameters stay FROZEN at the values chosen before the fix (no re-tuning)
chosen = (30.0, 50.0, 0.0)
print("frozen Elo2 params", chosen)

# ---------------- build all candidate features with the chosen Elo2
F = vf.build(df, want, chosen)
F = F.join(ds.set_index("record_id")[["competition_id", "season_corrected", "calendar_type", "match_date", "split", "dev_primary", "dev_secondary", "y", "tier"]], how="left")
F["competition_id"] = F["competition_id"].astype(str)
F.to_pickle(os.path.join(WORK, "features_v2_dev.pkl"))
json.dump(dict(elo2_params=dict(K=chosen[0], HA=chosen[1], season_regression=chosen[2]), note="rebuilt after same-day Elo update fix; params frozen from original grid", n_rows=len(F), columns=list(F.columns), built_from_matches_through=str(df.dt.max().date())),
          open(os.path.join(WORK, "features_v2_meta.json"), "w"), indent=1, default=str)
# v1 25-feature file restricted to the development rows (for baseline reproduction)
fe1[fe1.record_id.isin(want)].to_pickle(os.path.join(WORK, "features_v1_dev.pkl"))
print("features", F.shape, "NaN share by column (top):")
print(F.isna().mean().sort_values(ascending=False).head(12).round(4).to_string())
