# FootIQ: Football Analytics and Prediction System — Project Report

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

College mini-project. Repository: `D:\Foot IQ`. Verified 2026-10-27. Companion documents in this folder: `ARCHITECTURE.md`, `ML_MODELS.md`, `DATA_SOURCES.md`, `TESTING_REPORT.md`, `SETUP_AND_RUN.md`, `LIMITATIONS.md`, `DEMO_SCRIPT.md`, `VIVA_QA.md`, `SUBMISSION_CHECKLIST.md`.

## 1. Overview

FootIQ is a web application for exploring football results and probabilities. It shows match results, league tables, team comparisons, win/draw/loss forecasts and two kinds of simulation, always with a statement of how fresh and how trustworthy the data behind each screen is. It was built on an earlier research pipeline that already contained a trained international match model and a World Cup simulator; the mini-project adds a results database, club-level analytics and forecasts, a backend API and a React interface, **without retraining any model**.

## 2. Problem statement

Football statistics are scattered across sources with different licences, formats and update delays; predictions are often shown without any evidence of how well they work or how old their data is. The project asks: *can existing, honestly evaluated models be wrapped in a transparent, reproducible application that never overstates what it knows?*

## 3. Objectives

1. Store results with full provenance in one SQLite database.
2. Dashboards for five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA and international competitions.
3. Probability forecasts for single matches and whole gameweeks from the frozen models, saved only on an explicit user action.
4. Simulations: a World Cup Monte Carlo and an experimental domestic points-only season simulation.
5. Visible limitations: stale data, provisional forecasts, unvalidated models, disabled functions.
6. Reproducibility: tests, hashes and documented commands.

## 4. Scope

**In scope (final, Phase 4.18):** the six competitions in `app/config.py` (five leagues and the Champions League; the Europa League, Conference League, World Cup, Nations League and Copa América were removed from the scope, their data preserved); historical and periodically synchronised data (synchronisation disabled); forecasts and simulations listed above.
**Out of scope:** live data, retraining, player analytics, a scoreline model, a deployed multi-user service. See `LIMITATIONS.md`.

## 5. Technologies

| Layer | Technology (verified versions) |
|---|---|
| Frontend | React 19, React Router 7, Vite 8, Tailwind 4, Recharts 3, Inter font (self-hosted); tests with Vitest 5 and Testing Library |
| Backend | Python 3.12, FastAPI 0.159, uvicorn 0.54, pandas 2.2.1, NumPy 1.26.4, scikit-learn 1.5.1, SciPy 1.17.1 |
| Data | SQLite (228 MB store), CSV sources, pickled frozen models |
| Quality | pytest 8 (260 tests), Vitest (355 tests), headless-Chrome probes for layout and contrast |

## 6. Methodology

The work followed controlled stages, each ending with a written report and an explicit approval: data audit and import (Phase 1), analytics and gameweek forecasts (Phase 2), season-simulation research with predeclared validation (Phase 3), and a redesign of the interface in seven steps (Phase 4: design system, dashboard, matches and predictions, leagues, simulations, integration, final documentation). Rules kept throughout: frozen models and prospective-evaluation records are never modified; production data is never overwritten by experiments (private copies are used); nothing is fabricated; no live data without approval; nothing is committed to Git without being asked.

## 7. Architecture (summary)

React frontend → FastAPI backend → SQLite store, pandas view and frozen models. The backend has read-only endpoints for data and two explicit write actions (save a gameweek forecast, save a season simulation). A diagram and the full module list are in `ARCHITECTURE.md`.

## 8. Implementation

| Module | What it does | Where |
|---|---|---|
| Home | Featured next fixture (a fresh league is preferred when one is close in date), upcoming fixtures, latest results, league overview, freshness and provisional chips | `frontend/src/pages/Overview.jsx`, `app/featured.py` |
| Matches | Upcoming / awaiting-result / completed matches with league, season, matchday and status filters, paged and bounded | `Matches.jsx`, `app/matches.py` |
| Leagues | Standings from stored results, partial-season and stale-data notices, results and fixtures, statistics, historical seasons | `Analytics.jsx`, `app/analytics.py` |
| Compare | Head-to-head and recent form for two teams | `TeamComparison.jsx`, `/api/team` |
| Predictions | Gameweek forecasts (explicit save), predicted-versus-actual, manual head-to-head with club v1, v2-r1 and Elo | `Predictions.jsx`, `app/forecast.py`, `app/predict.py` |
| World Cup | Seeded Monte Carlo, archived-state mode, real bracket | `Simulator.jsx`, `app/worldcup_sim.py`, `app/bracket.py` |
| Season simulator | Eligibility gate, points-only simulation, position ranges for the Bundesliga and La Liga; final positions disabled | `SeasonSimulator.jsx`, `app/seasonsim/` |
| Models | Evaluation, caveats, provenance read from stored reports | `Models.jsx`, `app/performance.py` |

Two engineering results worth noting: the gameweek page was made about 15 times faster (2.3 s to 0.16 s idle) by one query hint, after proving identical output on 171 gameweek payloads and 10 forecast runs; and kickoff times of unknown time zone are shown as stored and never converted or classed as live.

## 9. Testing (summary; details in `TESTING_REPORT.md`)

*Figures in this section are the Phase 4.7 results. Later phases added tests and re-ran the suites (4.8B: 284 backend; 4.8C offline part: 299 backend, 357 frontend with a live backend); see `TESTING_REPORT.md`.*

Backend 260 tests; frontend 355 tests (342 run without a backend, 13 live-contract tests need a running backend and all 355 pass with one); production build succeeds; 33 end-to-end workflow assertions pass; the 17 core endpoints respond 200 after a cold start; probes at 1440, 820 and 375 px show no horizontal overflow, no contrast failure and no error banner on any page.

## 10. Results

* **Club v1** (validated): 50.2% accuracy, log loss 1.0073, Brier 0.6026 on 15,645 test matches; 49.4% / 1.0071 on a 5,770-match forward holdout; better log loss than "always home win" (1.0758) and than the Elo-only mapping (1.0097).
* **International v2.7 ensemble:** 60.9% accuracy, log loss 0.8565 on 3,491 test matches; its confident picks (46.7% of matches) are right 76.8% of the time.
* **World Cup engine:** 59 of 82 matches called correctly in 2026 (71.9%; 95% interval 61.4–80.5%).
* **Club v2-r1:** log loss 1.0146 versus 1.0176 for v1 on development folds; experimental, no unbiased evaluation.
* **Scoreline simulation:** no candidate passed the predeclared criteria; final-position simulation remains disabled.

These are the stored evaluation figures. They were inspected during development and are history, not new independent evidence.

## 11. Limitations

Historical-only and partly stale data; provisional forecasts; unvalidated v2-r1 and UEFA predictions; disabled final-position simulation; archived World Cup state; accuracy near 50% on three outcomes; a documented side effect (before Phase 4.8B the backend start-up check added one log row to the production store and so changed its byte hash; fixed, with a logical content hash recorded). Full list: `LIMITATIONS.md`.

## 12. Future scope

Approved live synchronisation with the existing safeguards; a validated scoreline model to enable final-position simulation; prospective evaluation of v2-r1; player-level data and clustering; PostgreSQL and a scheduler; deployment, authentication and continuous integration; a full accessibility audit and an off-device backup.

## 13. Conclusion

FootIQ delivers a working, tested analytics and forecasting application on frozen models and a provenance-tracked store. Its main contribution is not a higher accuracy but transparency: every screen states what the data is, how old it is, and what the model has and has not been validated on.
