# 07 Calibration and confusion-matrix analysis (generated 2026-10-20 23:25)

Tables: `07a_PER_CLASS_PERFORMANCE.csv`, `07b_CONFUSION_MATRICES.csv`, `07c_CALIBRATION_BINS.csv`, `07d_CALIBRATION_ECE.csv`. Class order H, D, A.

## Confusion matrices (rows = truth, columns = prediction), test primary
Logistic regression:
| true \ predicted | H | D | A |
|---|---|---|---|
| H | 5535 | 6 | 1212 |
| D | 2832 | 5 | 1222 |
| A | 2522 | 3 | 2308 |

Elo ordered logit:
| true \ predicted | H | D | A |
|---|---|---|---|
| H | 5594 | 0 | 1159 |
| D | 2882 | 0 | 1177 |
| A | 2605 | 0 | 2228 |

Forward holdout primary, logistic regression:
| true \ predicted | H | D | A |
|---|---|---|---|
| H | 2108 | 2 | 418 |
| D | 1123 | 4 | 460 |
| A | 914 | 1 | 740 |

## Class-specific performance (test and holdout primary)
| set | model | cls | support | predicted_count | precision | recall | f1 | mean_predicted_prob | observed_rate |
|---|---|---|---|---|---|---|---|---|---|
| test_primary | elo_ordered_logit | H | 6753 | 11081 | 0.5048 | 0.8284 | 0.6273 | 0.4375 | 0.4316 |
| test_primary | elo_ordered_logit | D | 4059 | 0 |  | 0.0000 | 0.0000 | 0.2598 | 0.2594 |
| test_primary | elo_ordered_logit | A | 4833 | 4564 | 0.4882 | 0.4610 | 0.4742 | 0.3027 | 0.3089 |
| test_primary | multinomial_logreg | H | 6753 | 10889 | 0.5083 | 0.8196 | 0.6275 | 0.4368 | 0.4316 |
| test_primary | multinomial_logreg | D | 4059 | 14 | 0.3571 | 0.0012 | 0.0025 | 0.2597 | 0.2594 |
| test_primary | multinomial_logreg | A | 4833 | 4742 | 0.4867 | 0.4776 | 0.4821 | 0.3036 | 0.3089 |
| forward_holdout_primary | elo_ordered_logit | H | 2528 | 4107 | 0.5108 | 0.8299 | 0.6324 | 0.4362 | 0.4381 |
| forward_holdout_primary | elo_ordered_logit | D | 1587 | 0 |  | 0.0000 | 0.0000 | 0.2574 | 0.2750 |
| forward_holdout_primary | elo_ordered_logit | A | 1655 | 1663 | 0.4594 | 0.4616 | 0.4605 | 0.3063 | 0.2868 |
| forward_holdout_primary | multinomial_logreg | H | 2528 | 4145 | 0.5086 | 0.8339 | 0.6318 | 0.4385 | 0.4381 |
| forward_holdout_primary | multinomial_logreg | D | 1587 | 7 | 0.5714 | 0.0025 | 0.0050 | 0.2591 | 0.2750 |
| forward_holdout_primary | multinomial_logreg | A | 1655 | 1618 | 0.4574 | 0.4471 | 0.4522 | 0.3024 | 0.2868 |

**The draw class is essentially never predicted** (a few matches out of thousands): the draw probability stays near 0.26 for almost every match because no feature separates draws; the F1 of the draw class is about 0.00-0.01. Away wins are recognised moderately (F1 about 0.45-0.48), home wins well (F1 about 0.63, helped by over-predicting H).

## Calibration
Expected calibration error (10 equal-width bins; per class, and top-label confidence):
| set | model | cls | ece |
|---|---|---|---|
| validation_primary | elo_ordered_logit | H | 0.0088 |
| validation_primary | elo_ordered_logit | D | 0.0076 |
| validation_primary | elo_ordered_logit | A | 0.0129 |
| validation_primary | elo_ordered_logit | top-label | 0.0142 |
| validation_primary | multinomial_logreg | H | 0.0123 |
| validation_primary | multinomial_logreg | D | 0.0055 |
| validation_primary | multinomial_logreg | A | 0.0100 |
| validation_primary | multinomial_logreg | top-label | 0.0125 |
| test_primary | elo_ordered_logit | H | 0.0121 |
| test_primary | elo_ordered_logit | D | 0.0018 |
| test_primary | elo_ordered_logit | A | 0.0106 |
| test_primary | elo_ordered_logit | top-label | 0.0058 |
| test_primary | multinomial_logreg | H | 0.0143 |
| test_primary | multinomial_logreg | D | 0.0032 |
| test_primary | multinomial_logreg | A | 0.0077 |
| test_primary | multinomial_logreg | top-label | 0.0103 |
| forward_holdout_primary | elo_ordered_logit | H | 0.0190 |
| forward_holdout_primary | elo_ordered_logit | D | 0.0206 |
| forward_holdout_primary | elo_ordered_logit | A | 0.0216 |
| forward_holdout_primary | elo_ordered_logit | top-label | 0.0097 |
| forward_holdout_primary | multinomial_logreg | H | 0.0108 |
| forward_holdout_primary | multinomial_logreg | D | 0.0193 |
| forward_holdout_primary | multinomial_logreg | A | 0.0209 |
| forward_holdout_primary | multinomial_logreg | top-label | 0.0159 |
| test_secondary_calendar_year | elo_ordered_logit | H | 0.0201 |
| test_secondary_calendar_year | elo_ordered_logit | D | 0.0135 |
| test_secondary_calendar_year | elo_ordered_logit | A | 0.0282 |
| test_secondary_calendar_year | elo_ordered_logit | top-label | 0.0192 |
| test_secondary_calendar_year | multinomial_logreg | H | 0.0110 |
| test_secondary_calendar_year | multinomial_logreg | D | 0.0156 |
| test_secondary_calendar_year | multinomial_logreg | A | 0.0157 |
| test_secondary_calendar_year | multinomial_logreg | top-label | 0.0148 |
| forward_holdout_secondary_calendar_year | elo_ordered_logit | H | 0.0391 |
| forward_holdout_secondary_calendar_year | elo_ordered_logit | D | 0.0121 |
| forward_holdout_secondary_calendar_year | elo_ordered_logit | A | 0.0461 |
| forward_holdout_secondary_calendar_year | elo_ordered_logit | top-label | 0.0430 |
| forward_holdout_secondary_calendar_year | multinomial_logreg | H | 0.0399 |
| forward_holdout_secondary_calendar_year | multinomial_logreg | D | 0.0119 |
| forward_holdout_secondary_calendar_year | multinomial_logreg | A | 0.0441 |
| forward_holdout_secondary_calendar_year | multinomial_logreg | top-label | 0.0501 |

Reliability bins for the logistic regression on test primary (full set in `07c_CALIBRATION_BINS.csv`):
| cls | bin | n | mean_predicted | observed_frequency |
|---|---|---|---|---|
| H | 0.0-0.1 | 120 | 0.0760 | 0.0750 |
| H | 0.1-0.2 | 799 | 0.1595 | 0.1552 |
| H | 0.2-0.3 | 1906 | 0.2566 | 0.2529 |
| H | 0.3-0.4 | 3502 | 0.3527 | 0.3375 |
| H | 0.4-0.5 | 4223 | 0.4490 | 0.4362 |
| H | 0.5-0.6 | 2899 | 0.5443 | 0.5326 |
| H | 0.6-0.7 | 1448 | 0.6424 | 0.6630 |
| H | 0.7-0.8 | 588 | 0.7407 | 0.7976 |
| H | 0.8-0.9 | 160 | 0.8309 | 0.8812 |

| cls | bin | n | mean_predicted | observed_frequency |
|---|---|---|---|---|
| D | 0.0-0.1 | 14 | 0.0912 | 0.0000 |
| D | 0.1-0.2 | 1103 | 0.1708 | 0.1478 |
| D | 0.2-0.3 | 12714 | 0.2599 | 0.2618 |
| D | 0.3-0.4 | 1809 | 0.3126 | 0.3129 |
| D | 0.4-0.5 | 5 | 0.4376 | 0.4000 |

| cls | bin | n | mean_predicted | observed_frequency |
|---|---|---|---|---|
| A | 0.0-0.1 | 688 | 0.0721 | 0.0698 |
| A | 0.1-0.2 | 2892 | 0.1571 | 0.1573 |
| A | 0.2-0.3 | 4931 | 0.2508 | 0.2474 |
| A | 0.3-0.4 | 3732 | 0.3465 | 0.3577 |
| A | 0.4-0.5 | 1995 | 0.4432 | 0.4441 |
| A | 0.5-0.6 | 902 | 0.5453 | 0.5931 |
| A | 0.6-0.7 | 370 | 0.6434 | 0.6703 |
| A | 0.7-0.8 | 117 | 0.7377 | 0.7778 |
| A | 0.8-0.9 | 18 | 0.8256 | 0.8333 |

Assessment: class-wise ECE is 0.003-0.014 on the test set and 0.011-0.021 on the holdout - good for a model of this simplicity; the mean predicted probability of each class matches the observed rate within about 1 percentage point on the test set. The holdout draw rate (27.5%) was above the mean predicted draw probability (25.9%) and away wins were slightly over-predicted (30.2% vs 28.7%), which shows ordinary season-to-season variation rather than miscalibration of a single model (the Elo mapping shows the same pattern). No post-hoc calibration was applied or tuned.
