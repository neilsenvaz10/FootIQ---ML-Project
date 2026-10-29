# 02 Model comparison report (generated 2026-10-20 23:25)

Lower log loss / Brier is better; higher accuracy / macro F1 is better. Primary sets are complete split-year league-seasons without identity flags (existing split manifest). Chance level for a 3-class problem: log loss 1.0986, Brier 0.6667.

| evaluation_set | model | n | accuracy | macro_f1 | log_loss | brier |
|---|---|---|---|---|---|---|
| validation_primary | always_home | 17092 | 0.4362 | 0.2025 | 1.0737 | 0.6496 |
| validation_primary | elo_ordered_logit | 17092 | 0.4965 | 0.3606 | 1.0154 | 0.6081 |
| validation_primary | multinomial_logreg | 17092 | 0.5009 | 0.3668 | 1.0118 | 0.6056 |
| test_primary | always_home | 15645 | 0.4316 | 0.2010 | 1.0758 | 0.6511 |
| test_primary | elo_ordered_logit | 15645 | 0.5000 | 0.3672 | 1.0097 | 0.6042 |
| test_primary | multinomial_logreg | 15645 | 0.5016 | 0.3707 | 1.0073 | 0.6026 |
| forward_holdout_primary | always_home | 5770 | 0.4381 | 0.2031 | 1.0753 | 0.6504 |
| forward_holdout_primary | elo_ordered_logit | 5770 | 0.4960 | 0.3643 | 1.0112 | 0.6058 |
| forward_holdout_primary | multinomial_logreg | 5770 | 0.4943 | 0.3630 | 1.0071 | 0.6032 |
| test_secondary_calendar_year | always_home | 3449 | 0.4532 | 0.2079 | 1.0693 | 0.6461 |
| test_secondary_calendar_year | elo_ordered_logit | 3449 | 0.4833 | 0.3479 | 1.0197 | 0.6111 |
| test_secondary_calendar_year | multinomial_logreg | 3449 | 0.4868 | 0.3493 | 1.0155 | 0.6085 |
| forward_holdout_secondary_calendar_year | always_home | 570 | 0.4614 | 0.2105 | 1.0665 | 0.6440 |
| forward_holdout_secondary_calendar_year | elo_ordered_logit | 570 | 0.5228 | 0.3814 | 0.9997 | 0.5985 |
| forward_holdout_secondary_calendar_year | multinomial_logreg | 570 | 0.5193 | 0.3749 | 0.9921 | 0.5941 |

## Decision made on validation only
Validation primary log loss: always_home 1.0737, elo_ordered_logit 1.0154, multinomial_logreg 1.0118. The multinomial logistic regression was selected before test and holdout were evaluated.

## What the locked evaluation shows
* **Test (2024-25), primary:** logistic regression log loss 1.0073 vs Elo 1.0097 vs always-home 1.0758; accuracy 0.502 / 0.500 / 0.432.
* **Forward holdout (2025-26 and early 2026-27), primary:** 1.0071 / 1.0112 / 1.0753; accuracy 0.494 / 0.496 / 0.438. In accuracy and macro F1 the Elo mapping is on par with or ahead of the logistic regression on the holdout, while the logistic regression keeps a slightly lower log loss and Brier score.
* Both learned models beat always-home by a wide margin in log loss (about 0.064-0.069 nats). The logistic regression improves on the single-feature Elo mapping by only about 0.002-0.004 nats: the 22 extra features add very little beyond `elo_diff`.

Paired bootstrap of per-match log-loss differences (2,000 resamples, seed 20261020; negative favours the first model):
| set | comparison | mean_difference | ci95_low | ci95_high | n |
|---|---|---|---|---|---|
| test_primary | multinomial_logreg - elo_ordered_logit (log loss, negative = first is better) | -0.00239 | -0.00384 | -0.00092 | 15645 |
| test_primary | multinomial_logreg - always_home (log loss, negative = first is better) | -0.06854 | -0.07365 | -0.06357 | 15645 |
| test_primary | elo_ordered_logit - always_home (log loss, negative = first is better) | -0.06615 | -0.07129 | -0.06096 | 15645 |
| forward_holdout_primary | multinomial_logreg - elo_ordered_logit (log loss, negative = first is better) | -0.00407 | -0.00641 | -0.00163 | 5770 |
| forward_holdout_primary | multinomial_logreg - always_home (log loss, negative = first is better) | -0.06816 | -0.07670 | -0.05973 | 5770 |
| forward_holdout_primary | elo_ordered_logit - always_home (log loss, negative = first is better) | -0.06409 | -0.07279 | -0.05548 | 5770 |
| test_secondary_calendar_year | multinomial_logreg - elo_ordered_logit (log loss, negative = first is better) | -0.00419 | -0.00715 | -0.00125 | 3449 |
| test_secondary_calendar_year | multinomial_logreg - always_home (log loss, negative = first is better) | -0.05379 | -0.06345 | -0.04420 | 3449 |
| test_secondary_calendar_year | elo_ordered_logit - always_home (log loss, negative = first is better) | -0.04960 | -0.05823 | -0.04018 | 3449 |
| forward_holdout_secondary_calendar_year | multinomial_logreg - elo_ordered_logit (log loss, negative = first is better) | -0.00765 | -0.01445 | -0.00051 | 570 |
| forward_holdout_secondary_calendar_year | multinomial_logreg - always_home (log loss, negative = first is better) | -0.07445 | -0.09814 | -0.05207 | 570 |
| forward_holdout_secondary_calendar_year | elo_ordered_logit - always_home (log loss, negative = first is better) | -0.06680 | -0.09008 | -0.04394 | 570 |

The interval for logistic regression vs Elo excludes zero in the primary test and holdout sets, but the effect is tiny (0.2-0.4% of the loss). No claim of a practically relevant gain over a calibrated Elo rating is justified.

## Honest assessment
* All three models, including the best, stay close to the probability that bookmaker-free data allows: accuracy about 50% with draws essentially never predicted (see file 07).
* The results are robust across validation, test and holdout (always-home is clearly the worst model and the logistic regression has the lowest log loss in all three), and the holdout did not collapse: no sign of temporal leakage or overfitting to validation.
