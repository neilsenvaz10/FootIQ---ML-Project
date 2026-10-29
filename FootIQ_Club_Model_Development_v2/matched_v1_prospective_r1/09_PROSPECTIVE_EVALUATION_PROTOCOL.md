# 09 Prospective evaluation protocol (pre-registered, version r1)

Supersedes `final_refit_v2_r1/08_PROSPECTIVE_COMPARISON_PROTOCOL.md` where they differ (this one adds the matched v1 refit and the stricter eligibility/timing rules). **No evaluation will be run until the conditions in "Start conditions" hold.** The frozen models are never changed during the evaluation.

## Models (fixed)
| Id | Model | sha256 |
|---|---|---|
| `v2_frozen` | Club v2-r1 LR, 62 features, C=0.01 | `55c1e4c5...3e56c` |
| `v1_matched` | v1 recipe (25 features, C=100) refit on the same 116,854 rows, cutoff 2026-09-20 | `33bd80f6...ec34` |
| `v1_original` | Club Baseline v1 LR as frozen 2026-10-20 (trained <= 2023-06-30) | `067426e8...c5b9` |
| `v1_elo` | v1 Elo ordered-logit mapping (reference only) | in `baseline_parameters.json` |

## Comparisons (decided in advance)
* **Primary contrast: `v2_frozen` minus `v1_matched`** — identical training rows, labels and cutoff, so the difference is due to features/Elo design, not data recency.
* **Secondary contrast 1: `v2_frozen` minus `v1_original`** — what the owner would gain over the deployed-style v1 as it stands. Secondary contrast 2: `v1_matched` minus `v1_original` (value of fresher data alone). `v1_elo` is descriptive.
* The comparator is not changed after this document is hashed (hash recorded in `PREREGISTRATION_r1.json`).

## Eligible population
A logged fixture is **primary-eligible** only if all hold: (a) both clubs have >= 5 prior rated matches and are Elo-connected (dataset v1.1 rule); (b) no club identity collision (`eligibility_exclusions_r1.json`: Police FC, Vision FC); (c) neither club has an unresolved past-dated fixture without a result in the source; (d) the latest completed result of the competition in the input snapshot is <= 14 days before the fixture date; (e) regular-round domestic league match; (f) the prediction was written, hashed and chained before the earliest possible kickoff (match date 00:00 UTC minus 14 h) minus 60 min; (g) the confirmed result is a 90-minute result without a conflict. Everything else is logged with its reasons and reported as separate strata, never pooled silently. Matches affected by Zimbabwe (zw1) are flagged and reported separately.

## Outcome confirmation
A result counts as confirmed when the same score appears for the fixture in two successive approved-source snapshots retrieved at least 24 h apart, the first at least 48 h after the match, with no conflicting row; postponed/abandoned/awarded matches are excluded and counted.

## Metrics
* **Primary: multiclass log loss**, mean paired difference per contrast.
* Secondary: multiclass Brier, accuracy (argmax), macro-F1 (argmax and the pre-declared draw-weight 1.45 rule, reported separately), calibration (reliability table in 10 bins per class, ECE, calibration intercept/slope for the home-win and draw classes).
* League groups: tier 1 / tier 2 / tier 3+; regions (top-5 European leagues, other Europe, South America, Africa, Asia/Oceania, North America); split-year vs calendar-year leagues. Groups with fewer than 300 evaluated matches are listed but not interpreted.
* Missing-history sensitivity: strata by min(home, away) prior matches (< 10, 10-29, >= 30), first season in competition, and coverage flags.
* Draw probability quality: mean predicted vs actual draw rate, draw AUC, binary draw log loss, draw calibration deciles, and draw rate by |Elo gap| band.
* Uncertainty: paired cluster bootstrap over competition x calendar month, 2,000 resamples, seed 20261021, percentile 95% intervals; no multiplicity adjustment for secondary items (reported with intervals only; claims are limited to the primary contrast).

## Minimum sample and stopping
* Start of analysis: first checkpoint when **>= 5,000 primary-eligible fixtures have confirmed outcomes, from >= 25 competitions, spanning >= 3 calendar months.** Interim checks before that are descriptive (coverage, eligibility rate, data quality only), with no model-comparison statistics published.
* Second checkpoint at >= 10,000 eligible results; hard end at 12 months after the first official batch or 15,000 eligible results, whichever comes first. No early stopping for efficacy.
* Harm monitor: if after >= 2,000 eligible results the primary contrast is > +0.010 (v2 worse) with the 95% interval above zero, the owner is told immediately; the models are still not modified (a fix would be a new version with a new evaluation).
* Descriptive success criteria for the primary contrast (the promotion decision remains the owner's): interval entirely below zero and point estimate <= -0.002; tier-1/tier-2 groups with > 2,000 matches not worse than `v1_matched` by > 0.005; ECE not worse by > 0.005; contrast 1 also not above zero.
* Inconclusive result is reported as inconclusive.

## Start conditions (all required)
1. Owner creates `OFFICIAL_LOGGING_APPROVED.json` containing the model hashes above (the logger refuses otherwise).
2. At least one upstream snapshot newer than 2026-09-20 has been ingested through `e3_ingest_results.py` and the logger shows a non-trivial primary-eligible share (see readiness report; at present 0%).
3. Official batches are written before kickoff; no batch for completed matches; dry-run batches are never counted.
