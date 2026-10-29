# FootIQ: Football Analytics and Prediction System — Project Report

> **Final state (Phases 4.18-4.29):** FootIQ supports exactly **six competitions** (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, UEFA Champions League). This report was rewritten in Phase 4.29 so that it describes only the submitted application; the earlier eleven-competition version is in the project history (`data/supervised/phase4/p429/before/docs/`). Authoritative companion: `FINAL_SYSTEM_GUIDE.md`.

College mini-project. Repository: `D:\Foot IQ`. Verified 2026-10-28. Companion documents in this folder: `FINAL_SYSTEM_GUIDE.md`, `ARCHITECTURE.md`, `ML_MODELS.md`, `DATA_SOURCES.md`, `TESTING_REPORT.md`, `SETUP_AND_RUN.md`, `LIMITATIONS.md`, `DEMO_SCRIPT.md`, `VIVA_QA.md`, `SUBMISSION_CHECKLIST.md`.

## 1. Overview

FootIQ is a web application for exploring football results and probabilities for six competitions. It shows match results, upcoming fixtures, league tables, team comparisons, win/draw/loss forecasts and an experimental season simulation, always with a statement of how fresh and how trustworthy the data behind each screen is. It builds on an earlier research pipeline; the mini-project adds a results database with provenance, data-engineering importers, club-level analytics and forecasts, a backend API and a React interface, **without retraining any model**.

## 2. Problem statement

Football statistics are scattered across sources with different licences, formats and update delays; predictions are often shown without evidence of how well they work or how old their data is. The project asks: *can existing, honestly evaluated models be wrapped in a transparent, reproducible application that never overstates what it knows?*

## 3. Objectives

1. Store results with full provenance in one SQLite database.
2. Dashboards, results, fixtures and standings for the five domestic leagues, and results, fixtures and the league-phase table for the Champions League.
3. Probability forecasts for single matches and whole gameweeks from the frozen club models, saved only on an explicit user action.
4. One simulation: an experimental points-only Monte Carlo season simulation for the five domestic leagues.
5. Visible limitations: stale data, provisional forecasts, unvalidated predictions, disabled functions.
6. Reproducibility: tests, hashes, backups and documented commands.

## 4. Scope

**In scope:** the six competitions in `app/config.py`, season 2018-19 to 2026-27. Coverage of 2026-27 on 28 October 2026: Premier League 80 results and 300 fixtures, La Liga 99 and 280 (+1 awaiting result), Bundesliga 63 and 243, Serie A 80 and 297 (+3 awaiting result), Ligue 1 72 and 234, Champions League league phase 54 results and 90 fixtures. Data is historical: the Bundesliga and La Liga are refreshed once from OpenLigaDB when the backend starts; the other four competitions have no update source and are imported only after verification.
**Out of scope:** live data, retraining, player analytics, a scoreline model, a deployed multi-user service, the Europa League, Conference League, World Cup, Nations League and Copa America (removed in Phase 4.18; their data is preserved but not served). See `LIMITATIONS.md`.

## 5. Technologies

| Layer | Technology |
|---|---|
| Frontend | React 19, React Router 7, Vite, Tailwind 4, Recharts, self-hosted font; tests with Vitest and Testing Library |
| Backend | Python 3.12, FastAPI, uvicorn, pandas, NumPy, scikit-learn 1.5.1, SciPy 1.17.1 |
| Data | SQLite (229 MB store), CSV sources, pickled frozen models |
| Quality | pytest (backend suite) and Vitest (frontend suite); counts in section 9 |

## 6. Methodology

The work followed controlled stages, each ending with a written report and an explicit approval: data audit and import (Phase 1), analytics and gameweek forecasts (Phase 2), season-simulation research with predeclared validation (Phase 3), interface redesign (Phase 4.1-4.7), a controlled synchronisation design (4.8-4.15), scoping to six competitions (4.18), data completion and reconciliation through verified importers (4.19-4.24), storage clean-up (4.25-4.28) and final regression verification (4.29). Rules kept throughout: frozen models and prospective-evaluation records are never modified; production data is only changed through importers that default to a dry run and require a verified backup; nothing is fabricated; nothing is committed to Git without being asked.

## 7. Architecture (summary)

React front end, FastAPI backend, SQLite store, pandas view and frozen club models. The backend has read-only endpoints for data and explicit write actions (save a gameweek forecast, save a season simulation). A diagram and the module list are in `ARCHITECTURE.md`.

## 8. Implementation

| Module | What it does | Where |
|---|---|---|
| Home | Featured next fixture, upcoming fixtures, latest results, league overview, freshness chips | `Overview.jsx`, `app/featured.py` |
| Matches | Results, awaiting-result and upcoming fixtures for all six competitions with league, season, matchday, team and status filters | `Matches.jsx`, `app/matches.py` |
| Leagues | Standings from stored results, partial-season and stale-data notices, statistics, historical seasons; Champions League league-phase table | `Analytics.jsx`, `app/analytics.py`, `app/uefa_league_phase.py` |
| Compare | Head-to-head and recent form for two teams | `TeamComparison.jsx`, `/api/team` |
| Predictions | Gameweek forecasts (explicit save), predicted-versus-actual, manual head-to-head with club v1, v2-r1 and Elo; Champions League labelled "Not validated (indicative only)" | `Predictions.jsx`, `Predict.jsx`, `app/forecast.py`, `app/predict.py` |
| Season simulator | Eligibility gate, points-only simulation for the five domestic leagues, position ranges for the Bundesliga and La Liga, final positions disabled | `SeasonSimulator.jsx`, `app/seasonsim/` |
| Models | Evaluation, caveats, provenance read from stored reports | `Models.jsx`, `app/performance.py` |
| Data engineering | Verified importers with dry run, backup, quarantine and reconciliation | `app/store/uefa_import.py`, `league_results_import.py`, `reconcile_import.py` |

Engineering results worth noting: the gameweek page was made about 15 times faster by one query hint after proving identical output; kickoff times of unknown time zone are shown as stored and never converted; a fixture dated today is not forecast; every production import was preceded by a byte-identical verified backup.

## 9. Testing (summary; details in `TESTING_REPORT.md`)

Final regression (Phase 4.29, 2026-10-28): backend 579 passed, 8 skipped, 0 failed (full regression); frontend 375 passed and 13 skipped (the live-API contract tests, by design); production build succeeds; a read-only live verification script checks 67 conditions across the six competitions (all pass); the frozen model hashes, the database integrity and both saved simulations were re-verified.

## 10. Results

* **Club v1** (validated on pooled domestic leagues): 50.2% accuracy, log loss 1.0073, Brier 0.6026 on 15,645 test matches; 49.4% / 1.0071 on a 5,770-match forward holdout; better log loss than "always home win" (1.0758) and than the Elo-only mapping (1.0097).
* **Club v2-r1:** log loss 1.0146 versus 1.0176 for v1 on development folds only; experimental, no unbiased evaluation.
* **Champions League:** the club models are applied but were never validated on that competition; every Champions League prediction is labelled "Not validated (indicative only)".
* **Season simulation:** points-only, experimental, five domestic leagues; position ranges only for the Bundesliga and La Liga. No scoreline candidate passed the predeclared criteria, so final-position simulation remains disabled.

These are stored evaluation figures. They were inspected during development and are history, not new independent evidence.

## 11. Limitations

Historical data only (two leagues refreshed once at start); four competitions without an update source; provisional forecasts where history has gaps; unvalidated v2-r1 and Champions League predictions; no knockout stage for the Champions League; disabled final-position simulation; accuracy near 50% on three outcomes. Full list: `LIMITATIONS.md`.

## 12. Future scope

Provider-approved synchronisation for the remaining leagues; a validated scoreline model to enable final-position simulation and ranges for all leagues; Champions League validation and knockout rounds; prospective evaluation of v2-r1; player-level data; PostgreSQL and a scheduler; deployment, authentication and continuous integration.

## 13. Conclusion

FootIQ delivers a working, tested analytics and forecasting application for six competitions on frozen models and a provenance-tracked store. Its main contribution is not a higher accuracy but transparency: every screen states what the data is, how old it is, and what the model has and has not been validated on.
