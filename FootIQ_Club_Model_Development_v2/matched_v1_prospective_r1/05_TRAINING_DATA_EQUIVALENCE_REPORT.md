# 05 Training-data equivalence report (matched v1 vs frozen v2-r1)

Machine-readable: `05_training_data_equivalence.json`. All checks computed by `e2_matched_v1_refit.py` from the frozen v2-r1 training table and dataset v1.1.

| Check | Result |
|---|---|
| Training record ids identical | **Yes** — 116,854 = 116,854; sha256 of the sorted id list `f1137ab4...8c94` |
| Training targets identical row by row | **Yes** — sha256 of id:target pairs `5f9f76bd...eaa6` |
| Source-data cutoff | 2026-09-20 for both |
| Eligibility criteria | identical: every row of dataset v1.1 (confirmed 90-minute labels, regular-round domestic league, extra-time/penalty/ambiguous results already excluded), no extra filtering; both used the full set including incomplete-season and identity-review rows as in development |
| Class definition | identical: 0=H, 1=D, 2=A from confirmed 90-minute `y_90min_1x2` |
| Source snapshot | identical: dataset v1.1 extraction 2026-10-20, results universe sha prefix 1c4d758b01d3d30a |
| Feature contracts verified independently | v1: artifact input columns == `feature_contract_v1.1.json` (25) for both the original and the matched model; v2: `feature_contract_v2_final.json` (62); matched v1 uses 0 features outside the v1 contract |

## Documented differences (by design, not defects)
* Feature sets differ: v1 25 features vs v2 62 features (`names_shared_between_contracts` and `v1_features_not_in_v2_set` in the json: v1 Elo K20/HA60 level features, history-depth counts and 10-match goal averages are not in v2's set; v2 adds its own Elo, form, goal-model, home-advantage, league-context and rest features).
* Regularisation differs: v1 C=100 (original) vs v2 C=0.01 (development-selected).
* The v2 generator contains the same-day-update fix; the v1 contract code was never affected.
* Both models inherit the same known data defects (Police FC / Vision FC collisions, zw1 2021-22 dates) because they share training rows.

Exact comparability of the training data is achieved; differences are limited to the model recipe, which is what the comparison is meant to test.
