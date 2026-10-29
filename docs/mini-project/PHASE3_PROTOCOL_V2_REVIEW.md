# Protocol v2 independent review (2026-10-25)

**Follow-up (2026-10-26): the corrections identified here are written into [PHASE3_VALIDATION_PROTOCOL_V3.md](PHASE3_VALIDATION_PROTOCOL_V3.md) (corrected sample sizes, Holm over methods, descriptive league screen, CA depth stratum, CB as monitoring, hash register).**

Scope: a review of `PHASE3_FINAL_VALIDATION_PROTOCOL.md` using synthetic data and pre-match model outputs only. **The revised protocol was not run on CA or CB; no scoreline method was selected; full final-position simulation stays disabled. No CA or CB outcome was read for this review.** The original benchmark and its failed verdict are untouched.

Scripts (all offline, seeded, outputs in `data/supervised/phase3/`, git-ignored): `app/seasonsim/m4_protocol_review.py` (error rates, power), `m4_ca_audit.py` (CA manifest and representativeness), `m4_margin_impact.py` (what a margin means for league outcomes), `m4_reproducibility.py`.

## Answers to the six questions

### 1. Are pooled European leagues representative of the Bundesliga and La Liga?
**Partly; the pooled set is usable as a screen, not as proof.**
* CA has 47 first divisions (11,024 matches, 2024-07-01 to 2026-09-20) other than the five big leagues, listed in `ca_manifest.json` (SHA-256 of the identifier list `c3ac167d…056c7`; built from identifiers, dates and clubs only).
* Pre-match, CA matches look like the target on win probabilities (home-win probability standardised difference -0.01) but differ on others: expected total goals 2.78 versus 2.97 (standardised difference 0.31), draw probability 0.255 versus 0.234 (-0.51). **History depth is very different**: CA home clubs have 105 earlier matches in our data on average versus 514 for the target, standardised difference 4.9. Our v1 model uses long histories, so its inputs are weaker for CA clubs; a method that passes on CA has not shown it passes where the model is strongest.
* 83.9% of CA matches fall inside the target's 5th to 95th percentile range of expected goals.
* Outcome structure (development window only, before 2024-07-01, which is not CA): the target's goals per match (Bundesliga 3.00, La Liga 2.66) lie inside the CA range 2.46 to 3.12; winning margins also lie inside the range. So no sign of a target outside the pool, but the Bundesliga sits at about +1.2 standard deviations on goals per match.
* **Consequence:** CA can say "the method is not wrong everywhere in Europe"; it cannot replace a check on the two target leagues (CB).

### 2. Are margins 0.15 and 0.075 practical for league-position outcomes?
**Yes for the probabilities we display; they are a statement about match-level bias, not about positions.** `m4_margin_impact.py` re-simulates seasons with coupled random numbers (points identical, only goal tie-breaks differ) and distorts scorelines so that the bias in winning margin is 0.05 or 0.10 goals:
* At a bias of 0.15 goals (the recommended margin itself) the largest change in any club's title, top-four or relegation probability is 0.05, 0.30 and 0.17 percentage points in the Bundesliga now (0.37 points for relegation with 54 matches left) and at most 0.12 in La Liga; at 0.10 it is at most 0.18. That is small against the sampling error of 10,000 simulations (about +-1 point), but it is **not** below the one-decimal display precision (corrected 2026-10-26: this paragraph first said it was).
* The share of seasons in which some club's final position changes is larger (25% to 33%), but those are tie-breaks between clubs level on points; probabilities of the bands barely move.
* Late in the season (few matches left) tie-break effects matter more, which is why the bounds prototype separates guaranteed from possible (see `PHASE3_POSITION_BOUNDS_PROTOTYPE.md`).
* The inflation table shows how fast a seemingly small distortion reaches the margin: if the winners score one extra goal in 5% of matches, the worst-case statistic S1 bias is 0.36 of the margin; at 15% it is 1.08 of the margin (the margin is exceeded).
* **Caveat:** these are simulations of hypothetical distortions, not measurements of the real methods.

### 3. Do S1 then S2 then S3 and the Holm correction control the intended error rates?
**Not as written. Two corrections are needed.**
* *Sequence.* The protocol said a fixed sequence preserves the 5% family-wise rate. That is formally true only for a sequence of hypotheses tested in order with a stop at the first failure **of the same family**; here the sequence selects among **different methods** (accept S1, else S2, else S3), and the final claim is "some method is acceptable". If two methods are both unacceptable, each can pass at full level, so the chance of wrongly accepting some method can exceed 5% in the worst case (up to the number of methods times the level for independent tests). In my simulations with opposite-direction distortions (one method inflates by 0.139 probability, another deflates by 0.257, both at the margin) the sequence falsely accepted 0.3% to 0.9% of the time, Holm over methods 0.0% to 0.1%. So **the observed rate is far below 5%, but it is not proven to be controlled, and the protocol should say "Holm over methods" or restate the sequence claim honestly.**
* *Holm over leagues (screen).* When S1 is exactly right and sample sizes are small (1,158 matches), at least one of five leagues is wrongly flagged 8.7% of the time (2.7% at 4,321 matches); when S1 is at the margin boundary, flags occur 53% (1,158) to 100% (4,321). So the league screen is a heterogeneity check with power only at large n; it is not a 5% family test on small samples.
* **Recommendation (for your decision):** use Holm over methods, keep the sequence only as an order of preference, and report the league screen as descriptive.

### 4. Was CA untouched by earlier method development?
**Method development used only the five big leagues; CA outcomes have not been read in this stage.**
* The M2 benchmark and the Phase 3 backtests used the five leagues (fit window before 2024-07-01, evaluation from 2024-07-01), not CA's 47 leagues. The CA list was built without reading any score ("identifiers, dates and clubs only").
* **What I cannot certify:** (a) club v1 was trained and tested earlier in the project on all competitions then in the store; if its original test report scored CA matches of 2024-25, those matches were seen in that earlier evaluation of the match model (not of the scoreline methods, which are what Protocol v2 tests). The frozen v1 coefficients themselves were fitted before 2024-07-01. (b) Anyone who looked at those leagues' results informally.
* **Recommendation:** state this limitation in the protocol; if you want a stricter set, use CA2 (the seasons after v1's own test period) or freeze the list hash before any scoring.

### 5. Does CB have enough observations?
**No, not on its own and not soon.**
* CB (Bundesliga and La Liga after 2026-09-20) has 45 matches now and about 686 per full season (306 plus 380).
* Power for a correct method (equivalence margins 0.15 and 0.075, single method, level 0.05): 686 matches 14%; 1,158 about 60%; 1,800 about 91%; 2,606 about 98%. So **CB needs roughly 1,800 matches (about 2.6 seasons) to confirm a correct method with 90% power**; one season (686) detects nothing reliably.
* With margins 0.20 and 0.10 one season gives 62% power; with 0.10 and 0.05 even 4,321 matches give only 92%.
* **Recommendation:** treat CB as a long-running monitoring set (descriptive, no pass/fail) until it reaches about 1,800 matches; use CA for the pass/fail decision with the CB check as a consistency test.

### 6. Are the power calculations and acceptance rates reproducible?
**Yes, with a correction to the earlier planning numbers.**
* Same seed: stored and re-run results are identical (maximum absolute difference 0.0). With a different seed, differences are within Monte Carlo error: 296 acceptance rates compared, mean absolute difference 0.014, maximum 0.074; 97.3% within 2 standard errors; the largest standardised difference is 4.2 (one case, from rare-event cells with few repetitions).
* **Corrections found:** (1) the earlier sample-size table used a one-sided z-value and so **understated** the sample needed; the simulation-based power curve above replaces that table. (2) The statement that the fixed sequence preserves the 5% family-wise rate is replaced by item 3. (3) An earlier draft of the dynamic-strength design gave the Elo constants as K=30, home advantage 50; those belong to v2-r1's separate Elo. The v1 values are K=20, home advantage 60, and `PHASE3_DYNAMIC_STRENGTH_DESIGN.md` now says so. Corrections (1) and (2) are recorded in a banner at the top of `PHASE3_FINAL_VALIDATION_PROTOCOL.md`; the original text below the banner is kept unedited so the change is visible.

## What stays open (needs your decision)
Margins (0.15 and 0.075 versus a wider pair), CA as the decision set (and which part), Holm over methods versus the sequence, CB as monitoring only, and the CA limitation in item 4. None of these has been decided or run.
