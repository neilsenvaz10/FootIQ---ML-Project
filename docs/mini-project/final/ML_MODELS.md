# Machine-learning models in FootIQ

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

> **Phase 4.29 update:** this file now describes the models the application actually serves: frozen club v1 (validated on pooled domestic leagues), club v2-r1 (experimental, no unbiased test) and the Elo baseline. **Champions League predictions use these models but were never validated on that competition and are always labelled "Not validated (indicative only)".** The international v2.7 ensemble and the World Cup engine are not served any more; their description and figures are kept in the clearly marked archive section 7. Nothing was retrained in Phases 4.18-4.29.

Everything below is taken from the repository's artifacts, `app/predict.py`, `app/forecast.py`, `app/performance.py` and the stored evaluation reports (read on 2026-10-27). **No model was trained or changed for the mini-project**: the application only loads frozen files and reports their stored evaluation.

## 1. Models actually implemented

| Model | Algorithm | Inputs | Output | Status |
|---|---|---|---|---|
| **Club v1** | Multinomial logistic regression (scikit-learn) with a fixed, train-fitted preprocessing (medians, means, standard deviations, missing-value indicators) | 25 pre-match features: Elo ratings of both clubs and their difference, number of prior matches, points per game over the last 5 and 10 matches, goals for and against over 5 and 10 matches, home/away-venue points per game, goal-difference form, days of rest, league tier | Home, draw, away probabilities | **Validated** on domestic leagues; the primary club model |
| **Elo-only mapping** | Ordered-logit mapping of the Elo difference to three outcomes | Elo difference | Home, draw, away | Baseline shown next to v1 |
| **Club v2-r1** | Logistic regression with a richer feature set | 62 features (66 model input columns including 4 missing-value indicators): second-generation Elo and relative Elo, Elo momentum, form, rest and more | Home, draw, away | **Experimental candidate**: development-validated only; no unbiased test exists |
| **Points-only season simulation** | Monte Carlo over the remaining fixtures of a domestic league, outcomes drawn from club v1 probabilities, 3/1/0 points (completed matches are never re-simulated) | Stored table and remaining fixtures | Distribution of final points per club for the **five domestic leagues**; position ranges (lower/upper bounds) for Bundesliga and La Liga only | **Experimental**; no exact finishing-position probability; not for the Champions League |

Not implemented: neural networks, player-level models, player clustering, live in-play prediction, a scoreline (goals) model for the final-position simulator.

## 2. Training and evaluation methodology (as recorded)

* **Club v1:** fitted on 59,356 training rows; evaluated chronologically on a **test season (2024-07-01 to 2025-06-30, 15,645 matches)** and a **forward holdout (2025-07-01 to 2026-09-30, 5,770 matches)**, pooled over about 100 domestic competitions.
* **Club v2-r1:** chosen on three chronological folds (2021-22 to 2023-24, 36,881 matches). The final candidate was then refit on data that includes v1's test and holdout periods, so **no unbiased evaluation of v2-r1 exists**.
* Scores reported: accuracy, **log loss** (the main score; lower is better) and **Brier score**. Baseline: "always predict a home win".

## 3. Measured performance (stored values, not recomputed)

| Club models, pooled leagues | Matches | Accuracy | Log loss | Brier |
|---|---|---|---|---|
| Always home win (test season) | 15,645 | 43.2% | 1.0758 | 0.6511 |
| Elo-only mapping (test season) | 15,645 | 50.0% | 1.0097 | 0.6042 |
| **Club v1 (test season)** | 15,645 | **50.2%** | **1.0073** | **0.6026** |
| Always home win (forward holdout) | 5,770 | 43.8% | 1.0753 | 0.6504 |
| Elo-only mapping (forward holdout) | 5,770 | 49.6% | 1.0112 | 0.6058 |
| **Club v1 (forward holdout)** | 5,770 | **49.4%** | **1.0071** | **0.6032** |

Per league (club v1, test season / forward holdout, accuracy and log loss): Premier League 52.1% / 46.5% and 0.990 / 1.044; La Liga 55.3% / 51.9% and 0.978 / 0.976; Bundesliga 49.5% / 54.1% and 1.018 / 0.964; Serie A 52.4% / 53.0% and 0.974 / 0.991; Ligue 1 54.8% / 51.0% and 0.967 / 1.006. In every league and period the log loss is below the always-home baseline for that league. Samples of 300 to 450 matches are small, so single-league differences are noisy.

Club v2-r1 (development folds only): accuracy 49.5%, log loss 1.0146 against 1.0176 for v1 on the same folds, a gain of about 0.003 that was measured on the folds used to choose its settings. It is shown only as an experimental candidate.

Accuracy near 50% on three outcomes is typical for football. The club models almost never predict a draw; the probabilities, not the single pick, are the product.

## 4. Leakage prevention

* **Time-ordered features:** every feature of a match uses only matches dated before it (Elo, form, rest days).
* **Chronological splits:** training, calibration, test and forward-holdout periods never overlap in time for v1 and v2.7.
* **Forecast cut-off:** `forecast.py` featurises each fixture from results dated **strictly before the fixture's day**, so a same-day result can never leak in, whatever the kickoff time. Fixtures dated before the newest stored result use a day-by-day history replay so that no later result of any competition reaches them.
* **Only unplayed fixtures are forecast**; finished matches are never "predicted in hindsight".
* **Saved forecasts record** the data cut-off, the feature snapshot hash, the artifact hashes and whether the forecast was certainly saved before kickoff (`yes` / `no` / `unknown`); only `yes` forecasts are counted in the predicted-versus-actual summary.
* **Preserved records:** frozen artifacts and the official prospective-evaluation files are hashed; the application never writes to them.
* **Parity evidence (P4.3):** the gameweek speed-up was checked to leave form, flags, probabilities, feature hashes and saved rows identical (10 gameweeks, 80 fixtures, 240 saved rows).

## 5. Limitations of the models

* v1 test and holdout figures were inspected during development; they are history, not new independent evidence.
* v2-r1 has no unbiased evaluation. The Champions League has none for any model: the app labels its predictions "Not validated (indicative only)" and they must never be presented as validated.
* Predictions use the model history held in the results store, which ends with the newest stored club result (26 October 2026; the Premier League, Serie A, Ligue 1 and Champions League have no update source, so their newest results are the verified imports of 25-26 October). A prediction date must be after the cut-off; a fixture dated today is not forecast.
* The ratings are the project's own Elo, not an official feed. No injuries, line-ups, weather or transfers are modelled.
* Probabilities are estimates, not guarantees.

## 6. Frozen-artifact hashes (SHA-256, verified 2026-10-28)

| File | SHA-256 |
|---|---|
| `FootIQ_Club_Model_Baseline_v1/artifacts/multinomial_logreg.pkl` | `067426e83d2d5f66aaf6c4aef933ac58e17f04d911ae55ede336c1bad3c0c5b9` |
| `FootIQ_Club_Model_Baseline_v1/artifacts/preprocessing_train_fitted.json` | `b74a529844dc52bf92d2d6f2f980dc5977e1ff145d55e9263d80dedd0a6cddee` |
| `FootIQ_Club_Model_Development_v2/final_refit_v2_r1/artifacts/club_v2_lr_final_candidate.pkl` | `55c1e4c53bcfefd39d5e90a1ce60a75bc697668f7894e425305bdc9a65b3e56c` |
| `FootIQ_Club_Model_Development_v2/final_refit_v2_r1/artifacts/feature_contract_v2_final.json` | `cfe09547bdbbe1506271c7b4703d65c0e93d16b08896a4b2c6b94cdafbaf94cb` |

All four hashes were re-checked in Phase 4.29 and are unchanged.

## 7. Archive: models that are NOT part of the application (kept as research history)

These were used by the earlier eleven-competition version and are no longer loaded, served or shown. Their figures are history only.

| Model | Algorithm | Status |
|---|---|---|
| **International v2.7 ensemble** | 50% gradient boosting, 30% Elo formula, 20% logistic regression, temperature-calibrated, plus a confidence gate that withholds weak picks | Team Elo, recent form and match context | Home, draw, away (neutral or home venue) | Validated on pooled internationals; used for the Nations League, Copa América and World Cup single matches |
| **World Cup tournament engine (v2.3, locked-result v2.13)** | Monte Carlo simulation driven by team-power ratings | Team strengths, group structure, bracket rules | Stage-reach and title percentages | Validated against the 2026 tournament on a small sample |

* International v2.7: 18,164 training, 3,580 calibration and 3,491 test matches (chronological). Stored figures: accuracy 60.9%, log loss 0.8565, Brier 0.5043, ECE 0.030; with its confidence gate it picked 46.7% of matches and was right 76.8% of the time on those.
* World Cup engine: 59 of 82 matches correct against the 2026 tournament (71.9%, 95% interval 61.4% to 80.5%), final not included.
* Artifact `data/model_artifacts/v27/live_match_model.pkl` (SHA-256 `0df37dd7c659e35b61a64b4178d19cddc2dd103f95a9967314321e8ff3784a1a`) is preserved unchanged.
