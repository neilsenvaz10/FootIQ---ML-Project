# Training vs inference feature mismatch - preserved international model (documentation only; nothing was modified)

Sources: `scripts/model_bakeoff_v26.py` (training features), `scripts/build_live_predictions_v27.py` (inference features), `docs/baseline/RISK_REGISTER.md`.

| # | Feature / step | Training (v2.6 `build_feature_frame`) | Inference (v2.7 `build_live_feature_rows`) | Effect | Correction for the new club pipeline |
|---|---|---|---|---|---|
| 1 | `*_matches_prior_log` | `len(deque(maxlen=20))`, so capped at 20 (log1p <= 3.04) | total `matches_played` from `team_elo_latest.csv`, uncapped | Live values leave the training range for established teams | Use one uncapped count in both |
| 2 | `is_competitive` | any tournament that is not a friendly | only qualifier/nations league/euro/copa/gold cup/world cup keywords | Other competitive tournaments are scored as non-competitive live; changes draw prior and bucket | One explicit competition-type mapping stored with the dataset |
| 3 | Elo / form freshness | rebuilt chronologically, always as-of kick-off | read from `*_latest.csv`, which stop at 2026-06-02 | Stale ratings; `rest_days` saturates (days_since capped at 999) | Compute features as-of fixture date from the same match table |
| 4 | Home orientation / `neutral` | provider home/away and the neutral flag of the source | `venue_edge_team`, provider order or fixture order with neutral=1 | Orientation noise changes `home_field` and Elo-diff sign | Fixture feed must provide home/away and neutral explicitly |
| 5 | Categorical encoding | `get_dummies` on train+calibration+test concatenated | `reindex(columns, fill_value=0)` | Vocabulary leaks from future splits (R06); unseen buckets become all-zero | Fit vocabulary on training split only |
| 6 | Missing team defaults | not applicable (history empty -> ppg 1.0, elo 1500, days 999) | defaults 1500 / 1.0 / 999 on lookup failure | Silent imputation looks like real history | NaN + explicit `n_prior` |
| 7 | Labels | scores copied from results; ET/penalty semantics undefined (R04) | `actual_90min_result` from provider | Train labels may include extra-time goals | 90-minute labels only when verifiable (this dataset) |
| 8 | Elo update | home advantage 75 in the update, 55 in the probability head | n/a | Two different home-advantage constants | Single constant (60) used in the new pipeline |

None of these were fixed in the existing model or artifacts. A club model needs its own feature code shared by training and inference.
