# 01 Baseline (v1) diagnostic report

Scope: development data only (matches dated <= 2024-06-30). v1's own test (2024-07-01..2025-06-30) and forward holdout were not re-opened.
Numbers come from the three frozen chronological folds (see `02_CHRONOLOGICAL_CV_PROTOCOL.md`); tables are in `supporting_tables/`.

## Preservation check
`_work/phase0_checks.json` (copied to `supporting_tables/phase0_checks.json`): v1 artifacts, outputs, the 25-feature contract, the v1.1 dataset and the universe file were hash-verified (CRLF-normalised for text files, pickles byte-identical). The international World Cup model was not touched.

## Why did Elo dominate?
* Every other feature is largely a noisy restatement of team strength. Correlation with the tuned Elo difference (`supporting_tables/feature_corr_with_elo2_diff.csv`): Poisson-style home-win probability 0.87, expected goal difference 0.87, 10-match points-per-game difference 0.80, weighted PPG 0.78, 5-match goal difference 0.69.
* Result: adding the whole v1 25-feature set to a calibrated Elo mapping improves mean log loss by only 0.0031 (1.0220 -> 1.0189); form/goal/home-advantage groups each add 0.001-0.003 on top of Elo2 (`04_FEATURE_ABLATION_RESULTS.csv`).
* Elo itself was close to a local optimum: the 18-config grid (`03b_ELO_PARAMETER_GRID.csv`) spans only 1.0216-1.0244. v1-like settings (K20, HA 50-75) are within ~0.0005 of the best (K30/HA50). Season-transition regression to the league mean **hurt** (strength 0.2: +0.0003 to +0.0009; 0.4: +0.0019 to +0.0026 depending on K/HA).

## Why so little gain from form?
Form is largely already inside Elo (an exponentially weighted result history). A learning-curve check (LR on growing training fractions, fold 3: 1.0151 -> 1.0109 -> 1.0089 -> 1.0080 -> 1.0073) shows the models are not data-saturated, but the curve flattens; stronger regularisation did not matter (C=0.01 vs 1.0 differ by <0.0001), so v1 was **not over-regularised**; the information ceiling for these features is simply low.

## Draws
* Draws are 26.1% of dev-primary matches. v1's Elo mapping (a monotone ordered-logit) cannot give a draw probability above 0.29 (observed max 0.290) -> it **never** predicts a draw by argmax (0 of 36,881 stacked validation matches). v1 LR predicted 52.
* That is a *decision* problem, not necessarily a *probability* problem: v1's draw probabilities are well calibrated on average (mean 0.263 vs actual 0.261). The weak point is discrimination: draw AUC 0.543 (Elo mapping), 0.555 (v1 LR). See `06_DRAW_PREDICTION_ANALYSIS.md`.
* ~50% accuracy is **not** claimed as a ceiling; it is simply what these inputs produce in this data. Log loss and Brier are the primary metrics.

## League-specific home advantage
Home-win rates (competitions with >= 600 primary dev matches, n=35) range from 38.0% (Austria Bundesliga) to 57.8% (Ghana Premier League); draw rates from 21.6% to 31.7% (`supporting_tables/league_home_advantage.csv`). A single global home-advantage constant (v1 HA=60) cannot represent that spread. v2 adds shrunk league and team home advantage, which gave the second-largest single-group gain for LR (-0.0018).

## Disconnected Elo groups and identity fragmentation
`supporting_tables/structural_diagnostics.json`: 2,793 entities form 36 connected components over all recorded matches (the largest holds 73% of entities). Over rated league matches only there are 59 components; **14.1% of rated matches sit in 53 single-competition islands**, so their Elo values are only comparable inside the competition. Elo differences within a match are valid (both clubs are in the same island), but cross-league Elo levels are not comparable. v2 therefore adds league-relative Elo (`*_elo2_rel`) and never uses raw Elo levels as a cross-league scale. Identity-review-flagged league-seasons are excluded from evaluation exactly as in v1.1 (primary set 65,575 of 81,934 dev rows; the rest are calendar-year leagues, flagged or incomplete).

## Missing cups / continental results and rest days
The universe has 164,980 domestic-league, 6,819 continental, 2,851 domestic-cup, 518 league-cup and 160 global-club matches. 45 of the 93 development competitions have **no recorded cup/continental matches for their clubs at all** (36.7% of rows), so "days of rest" there are measured against league matches only and are overstated. 7.3% of rows show > 14 days of rest. v2 therefore includes explicit coverage flags (`*_cup_recorded_365`, `*_n_known_*`), and the rest/congestion group is treated as low-confidence (it gained 0.0007 alone and was rejected by the pre-registered rule as a standalone group).

## Cold start
4.6% of dev rows have a side with < 10 prior matches. v1 Elo is much worse there (1.0373 vs 1.0201 established); v2 narrows this gap strongly (see `08_LEAGUE_GROUP_PERFORMANCE.csv`).

## Caveat on the 582 zw1 rows
v2's re-implementation of v1 Elo (`elo1`) matches the v1 contract `elo_diff` exactly (max abs diff < 1e-13) for 99.29% of rows; the remaining 582 rows (0.71%) are all Zimbabwe Premier Soccer League 2021-22 onward (maximum difference 26 Elo points). Cause not isolated (likely an ordering/duplicated-fixture handling difference for this competition's source file); it does not affect leakage tests and is unlikely to move the aggregate results, but it is a documented, unresolved deviation.
