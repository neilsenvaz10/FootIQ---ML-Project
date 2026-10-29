# 08 Prospective comparison protocol (pre-registered; v2-r1 vs v1)

## Comparators (fixed in advance)
* **Primary comparator: the original frozen Club Baseline v1 multinomial logistic regression** (`FootIQ_Club_Model_Baseline_v1/artifacts/multinomial_logreg.pkl`, sha256 `067426e8...c5b9`, C=100, fitted on matches <= 2023-06-30, preprocessing `preprocessing_train_fitted.json`). Its predictions come from v1's own artifacts and feature contract with no change.
* **Secondary reference: v1 Elo ordered-logit mapping** (`baseline_parameters.json`), reported but not a gate.
* **Known fairness limitation:** v2-r1 trains on data through 2026-09-20 while v1 stops at 2023-06-30, so any v2 advantage mixes better features/models with fresher training data and fresher coefficients. A same-data v1 refit ("v1-R": v1's 25 features, C=100, same procedure, trained on the same 116,854 rows) would isolate that. **v1-R has NOT been created or approved.** If you want it, approve it *before the first official batch*; it would then be frozen and logged alongside, as a pre-declared secondary comparator. The primary comparator is never silently swapped.

## What is predicted
Domestic-league regular-round fixtures in competitions present in training, with both clubs resolved to entity ids, scheduled kickoff **after** the freeze timestamp (2026-10-21 17:45 +05:30). Primary evaluation population = logged fixtures that satisfy the dataset-v1.1 rule (both clubs >= 5 prior rated matches and Elo-connected: `eligible_dataset_v1_1_rule`). All other logged fixtures are reported separately (cold-start stratum), never mixed silently.

## Prediction log (one JSON line per fixture, hash-chained batches, read-only files)
fixture id; competition and season; home/away team names and entity ids; scheduled kickoff (date + time, `kickoff_time_known` flag; if the time is unknown the kickoff is taken as 00:00 on the match date); prediction timestamp; feature availability cutoff; latest result date in the input; input data version; model version; p_home/p_draw/p_away for v2-r1, v1 LR and v1 Elo; history depth; eligibility status; feature-vector hash; previous-batch hash. Implementation and verification: `_scripts/d11_prospective_logger.py`, dry run in `prospective_log/DRY_RUN/`.

Validity rules for an official batch:
1. The batch is written and its hash recorded **before** the earliest kickoff in it; a batch with any kickoff already past is rejected.
2. The results snapshot must contain every completed result available from the sources up to the stated feature availability cutoff, and that cutoff must be within 48 hours before the prediction timestamp. (The current snapshot ends 2026-09-20, so **no official batch can be produced until results since then are ingested through the same v1.1 pipeline.**)
3. Models, feature code and preprocessing must hash-match `FROZEN.json`; the logger verifies this before predicting.
4. Predictions are never edited or deleted; corrections are new, flagged batches.

## Outcomes
The confirmed 90-minute result is taken from a source snapshot extracted at least 48 hours after the match, labelled with the same `label_90_status` rules as v1.1 (only "confirmed"; extra-time/penalty results excluded; postponed/abandoned matches excluded and counted). Outcomes are attached by fixture id only after the batch is sealed; no outcome may be used to change either model, the feature code or the protocol.

## Metrics (computed by a script fixed before outcomes arrive)
Primary: multiclass log loss, paired difference v2-r1 minus v1 LR with cluster bootstrap (cluster = competition x calendar month, 2,000 resamples, seed 20261021). Secondary: multiclass Brier, ECE (10 bins, one-vs-rest), accuracy, macro-F1 (argmax, and separately the weight-1.45 draw rule from the development report), draw AUC, results by tier and league group, cold-start stratum, coverage and eligibility rates, and stability by calendar month.

## Minimum evidence and decision gates (descriptive; the promotion decision stays with the project owner)
* At least 5,000 primary-eligible predictions with confirmed outcomes, from at least 25 competitions and covering at least three calendar months. Below that: report as inconclusive, no gate evaluated.
* Gate A: 95% interval of the paired log-loss difference (v2-r1 - v1 LR) entirely below zero and point estimate <= -0.002.
* Gate B: no tier with > 2,000 matches worse than v1 by more than 0.005 log loss; ECE not worse than v1 by more than 0.005.
* Interim looks are reported with coverage but never used to stop early in favour of v2.
* If the model or feature code must change, a new version (v2-r2) and a new evaluation start; accumulated v2-r1 results stay as recorded.
