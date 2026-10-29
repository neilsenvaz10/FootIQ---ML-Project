# FootIQ architecture

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

Verified against the repository on 2026-10-27 (branch `feat/club-ml-v2`, HEAD `970f461`; the application work is uncommitted).

## 1. Overview

FootIQ is a local web application. A React single-page frontend talks to a FastAPI backend over HTTP and JSON. The backend reads one SQLite results store, a pandas view of the same data, and the project's **frozen** model files. Nothing is trained at run time, and no request leaves the machine unless live synchronisation is switched on (it is off).

```
 Browser (React 19, Vite, Tailwind 4, Recharts, React Router 7)         http://localhost:5173
        │   fetch() JSON, GET (POST only for two explicit "save" actions)
        ▼
 FastAPI backend  app/main.py  (uvicorn, port 8000, CORS allow-list)
   ├─ analytics.py      standings, form, head-to-head   ── pandas view built from the store
   ├─ featured.py       Home banner, upcoming fixtures, freshness, kickoff "timing"
   ├─ matches.py        Matches hub: filters + keyset pagination, bounded and indexed
   ├─ gameweeks.py      gameweek view, eligibility / reliability flags, team form
   ├─ forecast.py       "Predict gameweek": frozen models, saved only on an explicit action
   ├─ predict.py        manual head-to-head: club v1, club v2-r1, international v2.7
   ├─ worldcup_sim.py   wrapper over scripts/simulate_live_tournament_v213.py (Monte Carlo)
   ├─ bracket.py        real 2026 knockout bracket from verified result files
   ├─ seasonsim/        domestic season simulator: eligibility, rules, points-only, position bounds
   ├─ performance.py    model evaluation read from the repository's own report files
   ├─ integrity.py      SHA-256 check of frozen artifacts (shown by /api/meta)
   └─ store/            db.py (schema), build.py, baseline.py, views.py, sync.py (disabled)
        ▼
 data/footiq.sqlite  (operational store)   ·   frozen model files (pickles, JSON)   ·   config/*.json
```

## 2. Frontend (`frontend/`)

* React 19, React Router 7, Vite 8, Tailwind 4 (design tokens in `src/index.css`, dark-purple theme), Recharts 3, Inter font self-hosted from npm. No external CDN.
* Seven destinations (`src/lib/nav.js`): Home, Matches, Leagues (`/analytics`), Compare, Predictions (`/predict`), Simulations, Models. Pages are lazy-loaded chunks.
* `src/lib/api.js` is the only network client; `useApi` and `useMatchPages` hooks load data and keep loading, error and retry state per section.
* The frontend contains no prediction or statistics logic. It formats what the API returns.
* Responsive: sidebar (≥1024 px), icon rail (768–1023 px), bottom bar with a "More" sheet (<768 px).

## 3. Backend (`app/`)

* FastAPI 0.159, uvicorn 0.54. CORS allow-list in `app/main.py` (`DEFAULT_CORS`: localhost and 127.0.0.1 on ports 5173, 5174, 3000); `*` is refused.
* Endpoint reference: `docs/mini-project/API_REFERENCE.md`. Main groups: competitions and dashboards, `/api/featured-fixture`, `/api/matches`, `/api/gameweeks`, `/api/gameweek` (+ one `POST /api/gameweek/predict`), `/api/predict`, `/api/team`, `/api/worldcup/*`, `/api/season/*`, `/api/models/performance`, `/api/meta`, `/api/health`, `/api/sync/status`.
* Heavy club history (about 216 k matches) loads in a background thread after start-up; `/api/health` reports `club_prediction_ready`.
* Home and Matches responses are cached in process for 60 s with `ETag`; the caches are emptied when a synchronisation stores results.
* Query discipline: statements anchored on the `(competition_key, season)` index, a fixed statement count per request, bounded page sizes (tests assert plans and counts). `gameweeks.team_form` uses an `INDEXED BY` hint (a 15× speed-up measured in P4.3 with identical output).

## 4. SQLite store (`data/footiq.sqlite`)

Built offline by `app/store/build.py` from the repository baseline plus a reviewed OpenLigaDB snapshot import. Tables: `matches` (223,510 rows: club matches of all competitions in the model universe plus 2,621 international rows), `teams`, `team_aliases`, `match_sources`, `source_snapshots`, `sync_runs`, `quarantine` (273 rows that failed validation), `forecast_runs` and `forecasts` (saved only by the explicit "Predict gameweek" action), `simulation_runs` (saved only by an explicit simulation action). Indexes on `matches`: `(status, match_date)`, `(competition_id, season, home, away)`, `(competition_key, season)`, `(competition_id, season, match_date)`.

Every match row records its source system, licence, first-seen and last-changed time and content hash. Corrections are logged; nothing is silently overwritten.

## 5. Machine-learning components (all frozen)

| Component | Where | Used for |
|---|---|---|
| Club v1 (multinomial logistic regression, 25 features) | `FootIQ_Club_Model_Baseline_v1/artifacts/` | Primary club probabilities, gameweek forecasts, points-only simulation |
| Club v2-r1 (logistic regression, 62 features) | `FootIQ_Club_Model_Development_v2/final_refit_v2_r1/artifacts/` | Experimental candidate shown beside v1 |
| Elo-only mapping | part of the v1 artifacts | Baseline column |
| International v2.7 ensemble (50% gradient boosting, 30% Elo, 20% logistic regression, temperature-calibrated, with a confidence gate) | `data/model_artifacts/v27/` | Nations League, Copa América, World Cup single matches |
| World Cup tournament engine v2.3 / v2.13 | `scripts/` | Monte Carlo tournament simulation |

Details: `ML_MODELS.md`.

## 6. Simulation engines

* **World Cup (Monte Carlo):** `app/worldcup_sim.py` calls the repository's own v2.3 team-power engine. `pre_tournament` locks nothing; `current` locks the completed 2026 results from the archived state. 100 to 50,000 simulations, seedable (same seed, same result). Runs are serialised by a lock.
* **Domestic season simulator:** `app/seasonsim/`. Eligibility gate (Ready / Provisional / Not eligible from missing-result share and staleness), season rule profiles (`config/season_rules.json`, used only when verified), the **points-only** engine (win/draw/loss from club v1 probabilities, 3/1/0 points, no scores, no ranking) and **position ranges** (guaranteed and possible bounds, Bundesliga and La Liga only). The final-position simulator is disabled: `config/season_sim.json: scoreline_method = null` because no scoreline method passed its predeclared validation.

## 7. Data flow

1. **Offline:** source CSVs → `store/build.py` → SQLite store (+ `matches.csv` dashboard dataset from `prepare_data.py`).
2. **Request:** browser → FastAPI → SQLite / pandas / frozen model → JSON → React.
3. **Forecast save (explicit only):** button press → `POST /api/gameweek/predict` → `forecasts` rows with feature snapshot hash, data cut-off and artifact hashes.
4. **Synchronisation:** `store/sync.py` exists with an approved source list (OpenLigaDB for the Bundesliga) but `config/sync.json: live_enabled = false`; the start-up check only records `skipped_live_disabled`.

## 8. Safeguards built into the architecture

* Frozen artifacts hashed and checked (`/api/meta`, `app/integrity.py`).
* No forecast or simulation is computed or saved by looking at a page.
* Every forecast uses results dated strictly before the fixture's day (`forecast.py`); a kickoff with unknown time zone is never converted to UTC.
* Read-only endpoints open the store read-only; tests hash the store before and after.
