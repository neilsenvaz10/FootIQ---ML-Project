# FootIQ architecture

> **Final state (Phases 4.18-4.29):** FootIQ supports exactly **six competitions**: the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League (league phase). This file was rewritten in Phase 4.29 so that it describes only what the application does now; the earlier text, which described eleven competitions and an international model, is in the project history (`data/supervised/phase4/p429/before/docs/`). Overall description: `FINAL_SYSTEM_GUIDE.md`.

Verified against the repository on 2026-10-28 (branch `feat/club-ml-v2`; the application work is uncommitted).

## 1. Overview

FootIQ is a local web application. A React single-page front end talks to a FastAPI backend over HTTP and JSON. The backend reads one SQLite results store, a pandas view of the same data, and the project's **frozen** club-model files. Nothing is trained at run time. The only outbound request is the start-up refresh of the Bundesliga and La Liga from OpenLigaDB (two requests per start, `FOOTIQ_DISABLE_SYNC=1` switches it off); there is no scheduler and no other live source.

```
 Browser (React 19, Vite, Tailwind 4, Recharts, React Router 7)         http://localhost:5173
        |   fetch() JSON, GET (POST only for explicit "save" actions)
        v
 FastAPI backend  app/main.py  (uvicorn, port 8000, CORS allow-list)
   |- analytics.py      standings, form, head-to-head   (pandas view built from the store)
   |- featured.py       Home banner, upcoming fixtures, freshness, kickoff "timing"
   |- matches.py        Matches hub for all six competitions: filters + keyset pagination
   |- gameweeks.py      gameweek view, eligibility / reliability flags, team form
   |- forecast.py       "Predict gameweek": frozen models, saved only on an explicit action
   |- predict.py        manual head-to-head: club v1, club v2-r1, Elo baseline
   |- seasonsim/        domestic season simulator: eligibility, points-only engine, position ranges
   |- uefa_league_phase.py  Champions League league-phase table
   |- freshness.py      per-competition data-freshness indicator
   |- performance.py    model evaluation read from the repository's own report files
   |- integrity.py      SHA-256 check of frozen artifacts (shown by /api/meta)
   |- store/            db.py (schema), build.py, sync.py (OpenLigaDB start-up refresh), importers
        v
 data/footiq.sqlite  (operational store)   |   frozen model files (pickles, JSON)   |   config/*.json
```

## 2. Frontend (`frontend/`)

* React 19, React Router 7, Vite, Tailwind 4 (dark-purple theme tokens in `src/index.css`), Recharts, self-hosted font. No external CDN.
* Seven destinations (`src/lib/nav.js`): Home, Matches, Leagues, Compare, Predictions, Simulations, Models. Pages are lazy-loaded chunks.
* `src/lib/api.js` is the only network client; the `useApi` hook keeps loading, error and retry state per section.
* The front end contains no prediction or statistics logic; it formats what the API returns.
* Season simulator page: only seasons with unplayed fixtures are offered; the Predict Match page keeps clubs passed from the Matches page (also under React StrictMode).

## 3. Backend (`app/`)

* FastAPI, uvicorn. CORS allow-list: localhost and 127.0.0.1 on ports 5173, 5174, 3000.
* Endpoint reference: `docs/mini-project/API_REFERENCE.md`. Groups: competitions and dashboards, `/api/matches` (hub), `/api/gameweeks`, `/api/gameweek` (+ one `POST /api/gameweek/predict`), `/api/predict`, `/api/team`, `/api/competitions/UCL/league-phase`, `/api/season/*`, `/api/data-freshness`, `/api/models/performance`, `/api/meta`, `/api/health`, `/api/sync/status`.
* Heavy club history (about 216 k matches) loads in a background thread after start-up; `/api/health` reports `club_prediction_ready`.
* Archived competitions (Europa League, Conference League, World Cup, Nations League, Copa America) answer 404 or 422.

## 4. SQLite store (`data/footiq.sqlite`)

Tables: `matches` (223,636 rows; the six competitions plus preserved archived data), `teams`, `team_aliases`, `match_sources`, `source_snapshots`, `sync_runs`, `quarantine` (273 rows that failed validation), `forecast_runs` / `forecasts` (saved only by the explicit "Predict gameweek" action), `simulation_runs` (saved only by an explicit simulation action). Every match row records its source system, licence, first-seen and last-changed time and a content hash; corrections are logged and nothing is silently overwritten.

## 5. Machine-learning components (all frozen, none served beyond these)

| Component | Where | Used for |
|---|---|---|
| Club v1 (multinomial logistic regression, 25 features) | `FootIQ_Club_Model_Baseline_v1/artifacts/` | Primary probabilities (validated on domestic leagues), gameweek forecasts, points-only simulation |
| Club v2-r1 (logistic regression, 62 features) | `FootIQ_Club_Model_Development_v2/final_refit_v2_r1/artifacts/` | Experimental candidate shown beside v1 |
| Elo-only mapping | part of the v1 artifacts | Baseline column |

Champions League predictions use these same models and are labelled "Not validated (indicative only)". Details: `ML_MODELS.md`.

## 6. Simulation engine

**Domestic season simulator** (`app/seasonsim/`), for Premier League, La Liga, Bundesliga, Serie A and Ligue 1 (never the Champions League):
* an eligibility gate (Ready / Provisional / Not eligible from the missing-result share, staleness and data integrity; "Provisional" still runs and keeps its warning visible);
* the **points-only** engine: for every remaining fixture the outcome (home win, draw, away win) is drawn from the frozen club v1 probabilities and awarded 3 / 1 / 0 points. Completed fixtures are never simulated; postponed and past-dated fixtures without a result are simulated like future fixtures and disclosed. No score is invented, no tie-break is applied. Same seed and data give identical results;
* **position ranges** (guaranteed and possible bounds for title, top four and relegation): only for the Bundesliga and La Liga, whose tie-break rules are verified and validated. For the other three leagues the page says why they are not shown;
* the final-position simulator is disabled (`config/season_sim.json: scoreline_method = null`) because no scoreline method passed its pre-declared validation.

## 7. Data flow

1. **Offline:** verified source data goes through the importers (`app/store/uefa_import.py`, `league_results_import.py`, `reconcile_import.py`): dry run by default, a byte-identical backup for a production run, row validation, quarantine for failures.
2. **Request:** browser, FastAPI, SQLite / pandas / frozen model, JSON, React.
3. **Explicit saves only:** "Predict gameweek" writes `forecasts` rows (with feature snapshot hash, data cut-off and artifact hashes); a simulation button writes one `simulation_runs` row.
4. **Synchronisation:** at start, OpenLigaDB for the Bundesliga and La Liga only (`config/sync.json`: startup mode, 15-minute minimum gap). The Premier League, Serie A, Ligue 1 and the Champions League have no update source and are marked "historical only".

## 8. Safeguards

* Frozen artifacts hashed and checked (`/api/meta`, `app/integrity.py`).
* No forecast or simulation is computed or saved by looking at a page.
* Every forecast uses results dated strictly before the fixture's day; a kickoff with an unknown time zone is never converted to UTC, and a fixture dated today is not forecast.
* Read-only endpoints open the store read-only; tests hash the store before and after.

## 9. Archive (not part of the application)

The international v2.7 ensemble and the World Cup tournament engine (`data/model_artifacts/v27/`, `scripts/`) remain in the repository as research history only. They are not loaded, served or shown.
