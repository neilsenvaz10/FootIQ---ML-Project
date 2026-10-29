# Daily World Cup Model Report

Date: 2026-06-25  
Generated: 2026-06-25 10:32 ET

## Executive Summary

- Today's slate has 6 fixtures.
- Baseline v2.8/v2.9 produced 4 Model Leans and 2 Passes.
- The stricter v2.11 challenger is more conservative today: 1 Model Lean and 5 Passes.
- No confirmed lineups were available at the morning refresh, so v2.12 lineup impact does not change today's calls yet.
- Yesterday's validated public-pick accuracy was 75.00%.
- Overall honest pre-kickoff sample is now 34 completed eligible fixtures, with 19 public picks and 57.89% public-pick accuracy.

## Today's Baseline Calls

| Match | Kickoff ET | Public tier | Pick | 1 | X | 2 | Diagnostic score | Weather |
|---|---:|---|---|---:|---:|---:|---|---|
| Curacao vs Ivory Coast | 16:00 | Model Lean | Ivory Coast win | 12.53% | 27.32% | 60.15% | 0-1 | 30.7C |
| Ecuador vs Germany | 16:00 | Model Lean | Draw | 28.25% | 40.65% | 31.10% | 1-1 | 29.3C |
| Tunisia vs Netherlands | 19:00 | Model Lean | Netherlands win | 8.84% | 24.32% | 66.83% | 0-1 | 22.2C |
| Japan vs Sweden | 19:00 | Model Lean | Japan win | 59.36% | 30.83% | 9.81% | 1-0 | 33.3C |
| Paraguay vs Australia | 22:00 | Pass | No public pick | 31.68% | 35.73% | 32.59% | modal 1-1 | 18.0C |
| Turkey vs USA | 22:00 | Pass | No public pick | 32.77% | 36.34% | 30.89% | modal 1-1 | 18.2C |

## Today's Stricter Challenger Read

| Match | v2.8 baseline | v2.11 challenger | Read |
|---|---|---|---|
| Curacao vs Ivory Coast | Ivory Coast lean | Pass | Draw risk too high after calibration |
| Ecuador vs Germany | Draw lean | Pass | Draw risk too high / low separation |
| Japan vs Sweden | Japan lean | Pass | Draw risk too high after calibration |
| Tunisia vs Netherlands | Netherlands lean | Netherlands lean | Directional edge survives calibration |
| Paraguay vs Australia | Pass | Pass | Too balanced |
| Turkey vs USA | Pass | Pass | Too balanced |

## Yesterday's Validation

| Match | Result | Public call | Read |
|---|---|---|---|
| Bosnia & Herzegovina vs Qatar | 3-1 | Pass | Neutral pass |
| Switzerland vs Canada | 2-1 | Pass | Good pass; avoided wrong internal lean |
| Morocco vs Haiti | 4-2 | Morocco lean | Correct |
| Scotland vs Brazil | 0-3 | Brazil lean | Correct |
| Czech Republic vs Mexico | 0-3 | Mexico lean | Correct |
| South Africa vs South Korea | 1-0 | South Korea lean | Wrong |

Yesterday's public-pick accuracy: 75.00%.

## Current Model Status

- v2.8/v2.9 remains the live baseline because it is less afraid to make useful picks.
- v2.11 remains a shadow challenger. It looks better on historical holdout, but in the frozen live shadow it is currently too conservative.
- v2.12 is not promoted yet. It needs more confirmed lineup data before we can trust it as a production layer.
- Exact scores are diagnostics only. The sellable product should be outcome/pick/pass logic, not exact-score claims.

## Why Multiple Reports Exist

- `worldcup_matchday_v29_report`: today's fixture predictions, weather, xG, score diagnostics, and API budget.
- `matchday_validation_v210_report`: actual-result validation and accuracy tracking.
- `confidence_gate_v211_report`: stricter calibrated confidence challenger.
- `confidence_gate_v212_report`: confirmed-lineup impact challenger.

Business-facing view: use this daily report.  
Engineering/audit view: keep the four layer reports so we can debug, validate, and avoid changing the model blindly.
