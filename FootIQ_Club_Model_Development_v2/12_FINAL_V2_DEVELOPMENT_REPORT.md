# 12 Final v2 development report

Date: 2026-10-21. Branch `feat/club-ml-v2` (created for this work). **Nothing staged, committed, pushed, merged or deployed.** v1, the World Cup model, source datasets and earlier report folders are untouched; no databases touched; no packages installed.

## Headline
* Best v2 development candidate: **multinomial Logistic Regression, 62 features, C=0.01, uncalibrated** (`artifacts/candidate_v2_LR_full.pkl`; research artifact only).
* Mean log loss over 3 chronological folds (2021-22..2023-24): v1 Elo mapping 1.0220, v1 LR 1.0189, **v2 LR 1.0163**, RF 1.0173, HGB 1.0175.
* The gain over v1 LR is -0.0030 log loss (95% cluster-bootstrap CI -0.0044, -0.0016), consistent in all 3 folds; over the Elo mapping -0.0062 (-0.0086, -0.0041). That is a real but modest improvement (about 0.3% / 0.6% of the loss); accuracy barely moves (0.4936 vs 0.4928 v1 LR). It has **not** been validated on unseen data.

## Algorithms actually trained
Elo mappings, multinomial LR, Random Forest, HistGradientBoosting. XGBoost/LightGBM/CatBoost were not installed and were not trained.

## Features tested and selected
Tested groups: tuned Elo2, Elo extras, home advantage, form, goal-based (Poisson-style from actual scores), league context, rest/congestion (`04_FEATURE_ABLATION_RESULTS.csv`). Standalone, the groups passing the pre-registered rule (>= 0.0010 and better in >= 2 folds) were home advantage, form, goal-based, league context; Elo extras and rest/congestion did not. Jointly, however, the full 62-feature set beats the 43-feature selected set in all 3 folds (1.0163 vs 1.0176), so the full set is the candidate and the selected set is the simpler fallback.

## Other findings
* Elo vs LR vs trees: Elo2 tuning bought ~0.0004; LR on v1's 25 features -0.0031; full v2 features -0.0057 (LR). Trees (RF/HGB) are no better than LR (differences +0.0007, CI includes 0), except possibly in the cold-start group (1.0115/1.0109 vs 1.0180, n=1,523).
* Draws: v1 never predicted a draw because its draw probability is capped at ~0.29, not because it was miscalibrated. v2 improves draw discrimination slightly (AUC 0.543 -> 0.565); hard draw labels need an explicit decision rule (weight 1.45, tuned on folds 1-2, evaluated on fold 3: macro-F1 0.373 -> 0.442, accuracy 0.502 -> 0.484). See report 06.
* Calibration: models are already calibrated; vector scaling on a 12-month window did not help (report 07). Not recommended.
* League groups (`08_LEAGUE_GROUP_PERFORMANCE.csv`): gains in tiers 1, 2, 4, 5 and the cold-start set; tier 3 and 12 of 24 large competitions are not better than v1 LR (Premier League +0.0015, Bundesliga +0.0003); the largest gain is Ghana (-0.032) where home advantage is extreme (57.8% home wins).
* Season-transition regression, a common Elo remedy, made things worse here; rest features are unreliable because 45 of 93 competitions lack cup/continental fixtures.

## Remaining data limitations
Cup/continental results incomplete; 14% of rated matches sit in single-competition Elo islands (cross-league Elo not comparable); identity-review exclusions; calendar-year leagues evaluated separately; 582 Zimbabwe rows differ from v1's Elo values for an unresolved reason; no lineup, injury, xG or odds data; only three annual folds, so differences below ~0.001 are not distinguishable; hyperparameters and feature groups were chosen on the same three folds (mild optimism).

## Tests
Future-score-scrambling and placeholder-result tests pass at 3 cutoffs plus a fixture-level inference-parity test; artifacts reload with identical predictions (`supporting_tables/leakage_parity_tests.csv`, manifest). The v2-vs-v1 Elo consistency test fails for 582 zw1 rows (see limitations).

## Is prospective evaluation required before promotion?
**Yes.** The only evidence is development-fold evidence; v1's test/holdout cannot serve as fresh data. See `10_PROSPECTIVE_EVALUATION_PLAN.md`, including the open decision on refit-before-freeze.

## Files
Reports `00`-`12` in this folder, tables `02b`, `03b`, `04`, `05`, `08`, manifest `11`, `supporting_tables/`, `artifacts/` (3 candidate pickles), `_scripts/` (d0-d8, v2_common/features/models), `_work/` (intermediate tables, frozen protocol, feature table, out-of-fold predictions, logs). Re-run order: d0, d1, d2, d3, d4, d5, d6, d7, d8 with `.venv/Scripts/python.exe -I`.
