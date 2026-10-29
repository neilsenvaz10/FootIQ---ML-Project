"""Phase 2: chronological development protocol - sizes are verified, then the protocol is frozen BEFORE any model experiment."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
if os.path.exists(os.path.join(WORK, "protocol_frozen.json")):
    sys.exit("protocol already frozen")
ds = pd.read_csv(os.path.join(PREP, "01_CORRECTED_LEAGUE_TRAINING_DATASET_v1.1.csv"), low_memory=False, encoding=ENC,
                 usecols=["record_id", "competition_id", "season_corrected", "calendar_type", "match_date", "split", "season_status", "identity_review_flag", "tier"])
dev = ds[ds.match_date <= DEV_END].copy()          # development universe: nothing later than 2024-06-30
dev["split_year"] = dev.calendar_type.str.startswith("split")
dev["dev_primary"] = dev.season_status.isin(["complete", "in_progress_complete_through_cutoff"]) & ~dev.identity_review_flag & dev.split_year
dev["dev_secondary_calendar_year"] = dev.season_status.isin(["complete", "in_progress_complete_through_cutoff"]) & ~dev.identity_review_flag & ~dev.split_year
rows = []
for f in FOLDS:
    tr = dev[dev.match_date <= f["train_end"]]
    va = dev[(dev.match_date >= f["val_start"]) & (dev.match_date <= f["val_end"])]
    cal_start = (pd.Timestamp(f["train_end"]) - pd.DateOffset(years=1) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    core = tr[tr.match_date < cal_start]
    cal = tr[tr.match_date >= cal_start]
    rows.append(dict(**f, calibration_window_start=cal_start, train_rows=len(tr), core_fit_rows=len(core), calibration_rows=len(cal), val_rows=len(va), val_primary_rows=int(va.dev_primary.sum()),
                     val_secondary_calendar_year_rows=int(va.dev_secondary_calendar_year.sum()), val_leagues=int(va[va.dev_primary].competition_id.nunique()),
                     val_incomplete_or_flagged_rows_excluded=int((~va.dev_primary & ~va.dev_secondary_calendar_year).sum()), train_leagues=int(tr.competition_id.nunique())))
fold_tab = pd.DataFrame(rows)
print(fold_tab.to_string())
ok = all(fold_tab.val_primary_rows >= 8000) and all(fold_tab.core_fit_rows >= 10000) and fold_tab.train_rows.is_monotonic_increasing
protocol = dict(
    frozen_at=time.strftime("%Y-%m-%d %H:%M:%S"), seed=SEED, development_end_inclusive=DEV_END,
    forbidden_for_decisions="any outcome dated after 2024-06-30 (the v1 test 2024-07-01..2025-06-30 and the v1 forward holdout 2025-07-01..2026-09-30 were inspected in the v1 experiment and are never used for tuning, feature selection, calibration or promotion; v2 is not evaluated on them at all)",
    row_universe="the 116,854 eligible domestic-league rows of dataset v1.1 with match_date <= 2024-06-30 (train + validation of v1.1)",
    folds=rows, fold_sizes_verified=bool(ok),
    evaluation_rows="dev_primary = complete (or complete-through-cutoff) split-year league-seasons without identity-review flags, mirroring the v1.1 'primary' definition; calendar-year leagues are evaluated separately as dev_secondary_calendar_year, never pooled",
    calibration="within each fold the last 12 months of the fold's training period form a separate calibration window (calibrator fitted there, base model fitted on the earlier core window); uncalibrated models are fitted on the whole training window",
    metric="primary: mean multiclass log loss over the 3 folds; secondary: Brier, accuracy, macro F1, class F1, draw metrics, calibration error, fold standard deviation",
    selection_rule="a more complex model or additional feature group is preferred only if it lowers mean fold log loss by >= 0.0010 AND is not worse in at least 2 of 3 folds; otherwise the simpler alternative wins",
    tuning_budget="LR 3 values of C; RF 6 configurations; HGB 8 configurations; Elo parameter grid 18 configurations; every candidate evaluated only on fold validation windows",
    prohibited=["random shuffling", "fitting any transformer on validation rows", "same-day outcomes as information", "using data after 2024-06-30"],
    unavailable_algorithms=["xgboost", "lightgbm", "catboost"],
    expanding_window="train window always starts at 2018-08-01 and ends at the fold's train_end; features for any match use only strictly earlier calendar days (state history may start before 2018-08-01)")
json.dump(protocol, open(os.path.join(WORK, "protocol_frozen.json"), "w"), indent=1, default=str)
fold_tab.to_csv(os.path.join(OUT, "02b_CV_FOLD_SIZES.csv"), index=False)
print("protocol frozen; sizes verified:", ok, "sha256", sha(os.path.join(WORK, "protocol_frozen.json"))[:16])
