# 03 Reconciliation of the "0.0030" log-loss improvement

The earlier report quoted "1.0189 (v1 LR) and 1.0163 (v2 LR)" next to "an improvement of 0.0030". Those are two different aggregations; 1.0189 - 1.0163 is **0.0026**, not 0.0030. Recomputed from the corrected feature table with the frozen configuration (`03_postfix_logloss_reconciliation.csv`, `02_postfix_fold_metrics.csv`):

| Model | Fold 1 (n=10,086) | Fold 2 (n=9,703) | Fold 3 (n=17,092) | Mean of 3 fold values | Row-weighted pooled (n=36,881) |
|---|---|---|---|---|---|
| v1 Elo mapping | 1.02981 | 1.02077 | 1.01543 | 1.02200 | 1.02077 |
| v1 LR (25 features, C=100) | 1.02665 | 1.01844 | 1.01175 | 1.01895 | 1.01759 |
| v2 LR (62 features, C=0.01) | 1.02458 | 1.01703 | 1.00731 | 1.01630 | 1.01459 |

* Fold-mean difference v2 - v1 LR = 1.01630 - 1.01895 = **-0.00264** (each fold weighted equally).
* Pooled difference = 1.01459 - 1.01759 = **-0.00300** (every match weighted equally; fold 3 is 46% of the rows and has the largest gain, -0.0044).
* The paired cluster bootstrap (130 competition-season clusters) is a pooled statistic: -0.00300, 95% CI (-0.00444, -0.00161). So **"0.0030" is the pooled estimate; the fold-mean estimate is 0.0026**; both are correct for their definition and the earlier text mixed them.
* Versus the Elo mapping: fold-mean -0.0057, pooled -0.0062 (CI -0.0086 to -0.0041).
* v2 wins in all three folds against both baselines (v1 LR margins -0.0021, -0.0014, -0.0044).

In relative terms the gain over v1 LR is 0.26-0.29% of the loss. This statement replaces the earlier wording in `12_FINAL_V2_DEVELOPMENT_REPORT.md` and `09_MODEL_SELECTION_REPORT.md` (those files are left as they were; this file is the correction).
