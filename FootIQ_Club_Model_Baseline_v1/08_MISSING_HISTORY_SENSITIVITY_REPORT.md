# 08 Missing-history sensitivity report (generated 2026-10-20 23:25)

## Categories (defined from TRAIN-period evidence in `b2_fit_select_freeze.py`, stored in `artifacts/coverage_categories.json` before the test / holdout evaluation)
* **League coverage group:** `well_covered` = at least 3 league-seasons in the train period and at least 80% of them verified complete (`season_completeness_by_league_season.csv`): 39 leagues; `incomplete_history` = other leagues present in train: 24 leagues; `no_training_history` = leagues absent from the train period (appear only later).
* **Match history depth:** min(home_n_prior, away_n_prior) with cut points taken from the train distribution: shallow < 63, deep >= 257.
Only primary evaluation rows (complete league-seasons) are used, so these groups describe *structural* gaps in the history that feeds the features, not unfinished evaluation seasons.

## By league coverage group
| set | coverage_group | n_multinomial_logreg | accuracy_always_home | accuracy_elo_ordered_logit | accuracy_multinomial_logreg | log_loss_always_home | log_loss_elo_ordered_logit | log_loss_multinomial_logreg | logreg_minus_elo_logloss |
|---|---|---|---|---|---|---|---|---|---|
| forward_holdout_primary | incomplete_history | 1143 | 0.3981 | 0.4532 | 0.4471 | 1.0947 | 1.0331 | 1.0279 | -0.0052 |
| forward_holdout_primary | no_training_history | 726 | 0.5854 | 0.6006 | 0.6157 | 1.0167 | 0.9811 | 0.9559 | -0.0252 |
| forward_holdout_primary | well_covered | 3901 | 0.4225 | 0.4891 | 0.4855 | 1.0805 | 1.0103 | 1.0105 | 0.0002 |
| forward_holdout_secondary_calendar_year | incomplete_history | 306 | 0.4248 | 0.5294 | 0.5131 | 1.0830 | 0.9968 | 0.9891 | -0.0077 |
| forward_holdout_secondary_calendar_year | well_covered | 264 | 0.5038 | 0.5152 | 0.5265 | 1.0475 | 1.0032 | 0.9956 | -0.0076 |
| test_primary | incomplete_history | 1476 | 0.4234 | 0.4973 | 0.4925 | 1.0830 | 0.9999 | 0.9967 | -0.0032 |
| test_primary | no_training_history | 6379 | 0.4236 | 0.5015 | 0.5078 | 1.0779 | 1.0046 | 0.9994 | -0.0052 |
| test_primary | well_covered | 7790 | 0.4398 | 0.4992 | 0.4983 | 1.0728 | 1.0157 | 1.0157 | 0.0001 |
| test_secondary_calendar_year | incomplete_history | 1813 | 0.4407 | 0.4981 | 0.4992 | 1.0742 | 1.0014 | 0.9946 | -0.0068 |
| test_secondary_calendar_year | well_covered | 1636 | 0.4670 | 0.4670 | 0.4731 | 1.0638 | 1.0400 | 1.0387 | -0.0013 |

## By match history depth
| set | history_depth | n_multinomial_logreg | accuracy_always_home | accuracy_elo_ordered_logit | accuracy_multinomial_logreg | log_loss_always_home | log_loss_elo_ordered_logit | log_loss_multinomial_logreg | logreg_minus_elo_logloss |
|---|---|---|---|---|---|---|---|---|---|
| forward_holdout_primary | deep (>=257) | 2874 | 0.4332 | 0.4920 | 0.4871 | 1.0747 | 1.0121 | 1.0133 | 0.0012 |
| forward_holdout_primary | medium | 1715 | 0.4035 | 0.4828 | 0.4805 | 1.0914 | 1.0059 | 1.0034 | -0.0025 |
| forward_holdout_primary | shallow (<63) | 1181 | 0.5004 | 0.5250 | 0.5318 | 1.0533 | 1.0165 | 0.9974 | -0.0191 |
| forward_holdout_secondary_calendar_year | deep (>=257) | 1 | 1.0000 | 0.0000 | 0.0000 | 0.8303 | 1.1239 | 1.2083 | 0.0844 |
| forward_holdout_secondary_calendar_year | medium | 320 | 0.4562 | 0.4781 | 0.4844 | 1.0738 | 1.0368 | 1.0214 | -0.0155 |
| forward_holdout_secondary_calendar_year | shallow (<63) | 249 | 0.4659 | 0.5823 | 0.5663 | 1.0582 | 0.9516 | 0.9536 | 0.0020 |
| test_primary | deep (>=257) | 4387 | 0.4324 | 0.4962 | 0.4949 | 1.0749 | 1.0203 | 1.0199 | -0.0003 |
| test_primary | medium | 3923 | 0.4384 | 0.4971 | 0.4953 | 1.0747 | 1.0088 | 1.0104 | 0.0016 |
| test_primary | shallow (<63) | 7335 | 0.4275 | 0.5037 | 0.5091 | 1.0769 | 1.0038 | 0.9980 | -0.0058 |
| test_secondary_calendar_year | deep (>=257) | 101 | 0.5248 | 0.5446 | 0.5545 | 1.0321 | 1.0060 | 0.9985 | -0.0075 |
| test_secondary_calendar_year | medium | 1483 | 0.4491 | 0.4633 | 0.4727 | 1.0715 | 1.0357 | 1.0325 | -0.0032 |
| test_secondary_calendar_year | shallow (<63) | 1865 | 0.4525 | 0.4960 | 0.4944 | 1.0696 | 1.0077 | 1.0029 | -0.0048 |

## Findings (no model was altered after seeing these tables)
* The learned models beat always-home in every coverage group on both test and holdout. The ranking logistic regression ~ Elo > always-home is the same for well-covered and incomplete-history leagues.
* Well-covered leagues are *harder* than leagues with incomplete history (log loss about 1.01 vs 1.00 on test and 1.01 vs 1.03 on the holdout, with no consistent direction): the incomplete-history groups contain different, often smaller or more predictable leagues, so the comparison is confounded by league composition. There is no evidence in these data that incomplete history harms the model by a measurable margin, but there is also no evidence that it is harmless: the groups are not matched.
* History depth: matches whose clubs have few prior matches (shallow) are where the logistic regression gains most against Elo on the holdout (0.997 vs 1.016), plausibly because the form features partially compensate for an unreliable young Elo; for deep histories there is no gain.
* Leagues absent from the training period (`no_training_history`) are the largest test group; the model transfers to them without degradation (log loss 0.999 on test, 0.956 on the holdout, partly a composition effect again).
* Limits: the categories are coarse; the number of leagues per group is small; sampling error per group (a few hundred to a few thousand matches) is 0.01-0.03 in log loss.
