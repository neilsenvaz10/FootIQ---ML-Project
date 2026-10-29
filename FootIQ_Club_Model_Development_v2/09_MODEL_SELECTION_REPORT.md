# 09 Model selection report

All evidence is development-only (3 chronological folds, 2021-22 to 2023-24). Source tables: `05_ALGORITHM_COMPARISON.csv`, `08_LEAGUE_GROUP_PERFORMANCE.csv`, `supporting_tables/bootstrap_paired.csv`.

## Algorithms actually trained
Elo ordered-logit mapping (v1 and tuned Elo2), multinomial Logistic Regression (3 C values x 2 feature sets, plus v1 25-feature baseline), Random Forest (6 configs x 2 sets), HistGradientBoosting (8 configs x 2 sets). **XGBoost, LightGBM and CatBoost are not installed -> not trained** (no installs made).

## Mean log loss over the 3 folds (primary metric)
| Model | Features | Fold 1 | Fold 2 | Fold 3 | Mean |
|---|---|---|---|---|---|
| v1 Elo mapping | 1 | - | - | 1.0154 | 1.0220 |
| v1 Logistic Regression (C=100) | 25 | - | - | 1.0118 | 1.0189 |
| **v2 LR (C=0.01)** | 62 | 1.0246 | 1.0170 | 1.0073 | **1.0163** |
| v2 RF (depth 8, leaf 50) | 62 | 1.0267 | 1.0186 | 1.0066 | 1.0173 |
| v2 HGB (lr .03, depth 3, 300 it) | 62 | 1.0279 | 1.0186 | 1.0059 | 1.0175 |
| v2 LR selected groups | 43 | 1.0262 | 1.0177 | 1.0089 | 1.0176 |

(Full per-fold figures and all configurations: `05_ALGORITHM_COMPARISON.csv`.)

Paired cluster bootstrap, difference in log loss (negative = first is better; 130 league-season clusters):
* v2 LR vs v1 Elo: -0.0062 (95% CI -0.0086, -0.0041)
* v2 LR vs v1 LR: -0.0030 (95% CI -0.0044, -0.0016)
* v2 HGB minus v2 LR: +0.0007 (-0.0005, +0.0018); v2 RF minus v2 LR: +0.0007 (-0.0004, +0.0017) -> no evidence trees beat LR.

## Criteria
* Stability: v2 LR beats v1 Elo in all 3 folds (-0.0052, -0.0037, -0.0081) and v1 LR in all 3 (-0.0021, -0.0014, -0.0044). Fold std 0.0084.
* Calibration: well calibrated; no recalibration needed (report 07).
* Groups: improves tiers 1, 2, 4, 5 and the cold-start group over both baselines; tier 3 is worse than v1 LR (+0.0034, n=3,959) and 12 of 24 competitions with >= 600 matches are worse than v1 LR (e.g. Bundesliga +0.0003, Premier League +0.0015; the largest gain is Ghana, -0.032).
* Missing-coverage robustness: the full set includes explicit coverage flags; rest features alone were rejected as a group, but the full set beats the selected-groups set (without rest/Elo extras) in all 3 folds (-0.0013 on average). The group-wise rule and the joint result disagree mildly; the joint result is used and this is flagged.
* Inference availability: needs only fixture list + prior results; cup/continental completeness varies by competition.
* Cost/complexity: LR trains in seconds, RF ~140s, HGB ~18s per config set; LR is the simplest and equals or beats the trees.

## Roles
* **Best development candidate:** `v2_LR_full` (62 features, C=0.01, uncalibrated) — `artifacts/candidate_v2_LR_full.pkl`.
* **Simpler fallback:** `v2_LR_selected` (43 features).
* **Reference baseline:** v1 Logistic Regression (and v1 Elo mapping); v1 is not replaced.
* **Eligible for prospective evaluation:** `v2_LR_full`, once the prospective plan (report 10) is accepted. It is **not** promoted and not validated on unseen data.

## Is the improvement meaningful?
Statistically distinguishable from v1 in the development folds (CIs exclude zero) but small: 0.3% lower log loss than v1 LR, 0.6% than the Elo mapping, accuracy +0.35pp vs the Elo mapping (fold-mean 0.4936 vs 0.4901) and only +0.08pp vs v1 LR (0.4928). A fixed-hyperparameter selection from small grids on only three folds can overstate gains by a few 0.0001s. Treat it as a modest, probable improvement that still needs unseen data.
