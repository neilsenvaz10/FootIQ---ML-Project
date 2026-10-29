# Daily World Cup Model Report

Date: 2026-06-26  
Generated: 2026-06-26 11:30 ET

## Executive Summary

- June 25 validation closed: 6 finals, 50.00% public-pick accuracy.
- Overall honest sample: 40 completed eligible fixtures, 23 public picks, 56.52% public-pick accuracy.
- June 26 slate: 6 fixtures, 2 Model Leans, 4 Passes.
- June 27 slate: 6 fixtures, 4 Model Leans, 2 Passes.
- No confirmed lineups were available at the refresh, so v2.12 does not alter today/tomorrow yet.
- Live tournament favorite remains France at 12.12%.

## June 26 Baseline Calls

| Match | Kickoff ET | Public tier | Pick | 1 | X | 2 | Diagnostic score | Weather |
|---|---:|---|---|---:|---:|---:|---|---|
| Norway vs France | 15:00 | Pass | No public pick | 15.62% | 30.22% | 54.17% | modal 0-1 | 24.9C |
| Senegal vs Iraq | 15:00 | Pass | No public pick | 52.00% | 33.57% | 14.43% | modal 1-1 | 17.9C |
| Cape Verde vs Saudi Arabia | 20:00 | Pass | No public pick | 29.58% | 36.82% | 33.61% | modal 1-1 | 31.1C |
| Uruguay vs Spain | 20:00 | Model Lean | Spain win | 9.13% | 28.11% | 62.76% | 0-1 | 20.1C |
| Egypt vs Iran | 23:00 | Pass | No public pick | 22.06% | 34.82% | 43.12% | modal 1-1 | 15.3C |
| New Zealand vs Belgium | 23:00 | Model Lean | Belgium win | 9.12% | 23.11% | 67.76% | 0-1 | 14.8C |

## June 27 Baseline Calls

| Match | Kickoff ET | Public tier | Pick | 1 | X | 2 | Diagnostic score | Weather |
|---|---:|---|---|---:|---:|---:|---|---|
| Croatia vs Ghana | 17:00 | Model Lean | Croatia win | 70.15% | 22.97% | 6.88% | 1-0 | 27.0C |
| Panama vs England | 17:00 | Model Lean | England win | 10.51% | 26.42% | 63.07% | 0-1 | 23.2C |
| Colombia vs Portugal | 19:30 | Model Lean | Draw | 31.07% | 38.59% | 30.33% | 1-1 | 29.7C |
| DR Congo vs Uzbekistan | 19:30 | Pass | No public pick | 26.40% | 32.06% | 41.54% | modal 1-1 | 32.1C |
| Algeria vs Austria | 22:00 | Pass | No public pick | 25.93% | 38.10% | 35.96% | modal 1-1 | 25.2C |
| Jordan vs Argentina | 22:00 | Model Lean | Argentina win | 5.97% | 19.56% | 74.46% | 0-1 | 30.0C |

## Stricter v2.11 Read

| Match | Baseline | v2.11 shadow |
|---|---|---|
| Norway vs France | Pass | Pass |
| Senegal vs Iraq | Pass | Pass |
| Cape Verde vs Saudi Arabia | Pass | Pass |
| Uruguay vs Spain | Spain lean | Pass |
| Egypt vs Iran | Pass | Pass |
| New Zealand vs Belgium | Belgium lean | Belgium lean |
| Croatia vs Ghana | Croatia lean | Pass |
| Panama vs England | England lean | Pass |
| Colombia vs Portugal | Draw lean | Pass |
| DR Congo vs Uzbekistan | Pass | Pass |
| Algeria vs Austria | Pass | Pass |
| Jordan vs Argentina | Argentina lean | Argentina lean |

## June 25 Validation

| Match | Result | Public call | Read |
|---|---|---|---|
| Curacao vs Ivory Coast | 0-2 | Ivory Coast lean | Correct |
| Ecuador vs Germany | 2-1 | Draw lean | Wrong |
| Japan vs Sweden | 1-1 | Japan lean | Wrong |
| Tunisia vs Netherlands | 1-3 | Netherlands lean | Correct |
| Paraguay vs Australia | 0-0 | Pass | Good pass: draw risk |
| Turkey vs USA | 3-2 | Pass | Good pass: protected wrong internal lean |

## Live Tournament Winner

| Rank | Team | Champion % |
|---:|---|---:|
| 1 | France | 12.12% |
| 2 | Spain | 10.72% |
| 3 | Argentina | 10.43% |
| 4 | Brazil | 7.23% |
| 5 | Germany | 6.62% |
| 6 | England | 6.17% |
| 7 | Colombia | 5.64% |
| 8 | Portugal | 4.72% |

## Status

- v2.8/v2.9 remains the live baseline.
- v2.11 remains shadow only. It is cleaner but still very conservative.
- v2.12 remains shadow only until confirmed lineup coverage improves.
- v2.13 now updates tournament title odds by locking completed group results and simulating what remains.
- API usage after the latest validation: 32/100 used, 53 remaining before the local stop.
