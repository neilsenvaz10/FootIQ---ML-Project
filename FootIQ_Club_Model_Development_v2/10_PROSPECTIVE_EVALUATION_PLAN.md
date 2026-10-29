# 10 Prospective evaluation plan

Status: **v2 is development-validated only.** No unseen results exist for it: the data in the repository run to 2026-09-20; the v1 test (2024-07-01..2025-06-30) and holdout (2025-07-01..2026-09-30) were inspected in v1 and are not treated as fresh. Only matches kicking off after the freeze below are genuinely unseen.

## Freeze
* Model: `v2_LR_full` (62 features, C=0.01, uncalibrated) with feature code `_scripts/v2_features.py` and Elo2 K=30/HA=50/regression 0; reference models v1 LR and v1 Elo mapping recorded alongside. Hashes in `11_REPRODUCIBILITY_MANIFEST.json`.
* Decision needed from the owner *before* the freeze: the artifact was fitted on data through 2024-06-30. Running it as-is means its coefficients are 2+ years stale although its Elo/form state can be rolled forward with known results. Option A: freeze the current artifact (clean, but staler). Option B: refit with the frozen hyperparameters on all results through the freeze date (not tuned on them) and register that as v2.1 before any prediction is made. This plan recommends B; it needs explicit approval and was not done.
* Freeze timestamp: to be recorded when approved. Matches with kickoff after it are eligible.

## Per-prediction log (append-only)
fixture identity (competition id, season, date, home/away entity ids, source record id when available); prediction timestamp; data-availability cutoff (results known as of that time, with the source retrieval time of the latest result used); model and feature-code version hashes; pH/pD/pA for v2 and for v1 LR and v1 Elo; pre-match feature values; eligibility flag.

## Eligibility
Domestic-league matches in competitions with >= 1 prior season in training; both clubs with resolved identities; fixture listed before kickoff and the prediction logged before kickoff. Exclude: matches predicted after kickoff, abandoned/awarded results, identity-review-flagged clubs (reported separately). Cold-start (< 10 prior matches) and calendar-year leagues reported as separate strata.

## Label
Confirmed 90-minute result (H/D/A), added only from the confirmed source; extra-time/penalty outcomes never used.

## Metrics and decision rule
Log loss (primary), Brier, ECE, accuracy, macro-F1 with the pre-registered draw-weight rule from report 06 (reported separately from probability metrics), by tier and league group; paired cluster bootstrap by competition x matchweek-month vs v1 LR and v1 Elo.
Minimum evidence before any promotion discussion: >= 5,000 eligible predictions, >= 25 competitions, >= 3 months of fixtures including at least one league's full month of rounds; the paired 95% interval of (v2 - v1 LR) log loss must exclude zero in favour of v2 and the point estimate be <= -0.002; no tier with > 2,000 matches may be worse than v1 by more than 0.005; calibration (ECE) not worse than v1 by more than 0.005.
If the sample is smaller, report as inconclusive. Coverage and eligibility rates are reported with every interim.
