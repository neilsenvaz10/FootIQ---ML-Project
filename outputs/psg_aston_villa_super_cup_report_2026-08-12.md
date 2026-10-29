# PSG vs Aston Villa - UEFA Super Cup

Pre-kickoff snapshot: 12 August 2026 at 2:30 PM ET  
Kickoff: 3:00 PM ET / 9:00 PM CEST, Red Bull Arena Salzburg

## Final Call

- Full-match call: **Paris Saint-Germain to lift the trophy**
- Model trophy probability: **PSG 65.24% / Aston Villa 34.76%**
- Best 90-minute read: **Paris Saint-Germain win**
- Regulation confidence gate: **Pass**
- Model 1/X/2: **PSG 41.96% / Draw 36.37% / Aston Villa 21.68%**

The 90-minute winner is not clean enough for a Strong Pick or Model Lean under the saved v2.8 gate. Once extra time and penalties resolve the draw branch, PSG is the clearer full-match selection.

## Market Check

- Median 90-minute decimal odds: **PSG 1.72 / Draw 3.90 / Aston Villa 4.60**
- Approximate American odds: **PSG -139 / Draw +290 / Aston Villa +360**
- No-vig market probabilities: **PSG 55.10% / Draw 24.30% / Aston Villa 20.60%**
- Available full-match qualification odds: **PSG 1.40 (-250) / Aston Villa 2.99 (+199)**
- Full-match no-vig market probabilities: **PSG 68.11% / Aston Villa 31.89%**

The market is more confident in a PSG regulation win than the transferred model, but its full-match view is close to the model's 65.24% PSG trophy probability.

## Authoritative Lineups

The supplied lineup sheet is the source of truth. No players were replaced using historical or expected squad knowledge.

**PSG (4-3-3), coach Luis Enrique**

- Starters: #39 Safonov; #25 Mendes, #51 Pacho, #5 Marquinhos (captain), #2 Hakimi; #87 J. Neves, #17 Vitinha, #33 Zaire-Emery; #7 Kvaratskhelia, #14 Doue, #11 Akliouche.
- Bench: #30 Chevalier, #4 Beraldo, #6 Zabarnyi, #12 Digne, #21 Lucas, #24 Mayulu, #8 Ruiz, #27 Fernandez, #49 Mbaye, #29 Barcola, #47 Ndjantou, #10 Dembele.
- Listed missing: none.

**Aston Villa (4-2-3-1), coach Unai Emery**

- Starters: #40 Bizot; #22 Maatsen, #14 Torres, #3 Lindelof, #2 Cash; #35 Gomes, #8 Kamara; #10 Buendia, #53 G. Hemmings, #7 McGinn (captain); #39 B. Madjo.
- Bench: #60 Asemota, #42 Wright, #48 M. Cisse, #5 Mings, #32 Nedeljkovic, #45 T. Rowe, #26 Bogarde, #6 Barkley, #49 B. Burrowes, #74 Lynch, #47 Alysson, #18 Abraham.
- Listed missing: #31 Leon Bailey. No reason inferred.

## Lineup Adjustment

- Club Elo baseline: **PSG 1960 / Aston Villa 1892**.
- Effective confirmed-lineup Elo: **PSG 1938 / Aston Villa 1808**.
- PSG adjustment: **-22 Elo**, reflecting that several elite attacking options are on the bench while the defensive and midfield core remains strong.
- Aston Villa adjustment: **-84 Elo**, driven by the starter-role mix, especially the lower-experience attacking unit, while preserving the exact supplied team sheet.
- Sensitivity band: plausible lineup deductions produced **PSG 40.15-42.86%**, **Draw 35.66-36.37%**, and **Villa 20.80-24.19%**. The directional call did not change.

## Conditions

- Weather at kickoff: **22.6 C, 0% precipitation, 5.9 km/h wind**.
- Weather goal factor: **0.996**.
- Interpretation: comfortable conditions; effectively neutral for this matchup.

## Model

- Gradient boosting: **50%**
- Elo formula: **30%**
- Logistic regression: **20%**
- Poisson-lite: **0%** in the 1/X/2 ensemble

The saved model was trained and calibrated on international matches. Club Elo, recent club form, confirmed-lineup adjustments, neutral venue and weather are mapped into the same feature contract, so this is an experimental club-football transfer rather than a production-grade club model. Market odds are an independent diagnostic and are not blended into the prediction.
