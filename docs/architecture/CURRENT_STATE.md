# FootIQ implementation audit

Audit date: 20 October 2026. Target: `PROJECT.md` v1.0.

This audit distinguishes executable research functionality from the integrated platform required by the blueprint. The blueprint is a requirements document, not implementation evidence. No percentage completion is assigned because its requirements differ substantially in effort.

## Executive assessment

The repository contains a working international match-prediction research core and a separate World Cup simulator. It does not yet contain the PostgreSQL/Airflow data platform, FastAPI/React application, club analytics pipeline, or player clustering/similarity system. These are substantial new workstreams, not configuration tasks.

## Verified baseline

The following were executed during this chat using a local Python 3.12.14 virtual environment and the pinned direct dependencies in `requirements-share.txt`, plus `tzdata` for Windows:

- `python -m pytest -q`: 28 passed.
- `python scripts/build_live_predictions_v27.py`: eight saved fixtures scored, zero non-Pass v2.7 public picks.
- `python scripts/build_confidence_gate_v28.py`: one Model Lean and seven Passes.
- `python scripts/validate_worldcup_full_v214.py`: reproduced 34/52 group best reads, 19/29 group published calls, and 25/30 knockout advancement calls.
- `python -X utf8 scripts/simulate_live_tournament_v213.py`: completed; Spain 51.47%, all 72 recorded group results locked. This is an archived tournament state, not current live odds.

These checks establish artifact loading and inference, selected report generation, simulator execution, and existing test compatibility. Full model retraining, the entire backtest suite, independent verification of recorded football results, and live provider connectivity were not performed. Reported historical metrics are repository results, not a new independent validation.

## Implementation matrix

| Blueprint capability | Status | Evidence and remaining gap |
|---|---|---|
| Historical international archive | Implemented as files | 49,296 processed rows, 1872-11-30 to 2026-06-02; raw results, goalscorers, shootouts, and former names included. No warehouse import or scheduled reconciliation. |
| Elo and rolling form | Implemented as research scripts | `scripts/build_foundation_tables.py` and `scripts/model_bakeoff_v26.py`; pre-match feature construction exists. No transactional correction replay or warehouse feature snapshots. |
| International 1X2 ensemble | Implemented as research scripts | `scripts/build_live_predictions_v27.py`; saved artifact loads; 50% gradient boosting, 30% Elo, 20% logistic. Artifact reports 25,235 training rows, 2000-01-04 to 2026-06-02. |
| Calibration and abstention | Implemented | v2.6 temperature scaling/pass-rule selection; v2.7 consensus gate; v2.8 tiers. v2.11 is a shadow challenger, not a replacement production gate. |
| Matchday snapshots and validation | Implemented, file based | v2.9 snapshots, v2.10 pre-kickoff selection, v2.14 audit. Not a general immutable prediction/feature registry. |
| Confirmed lineup adjustment | Partial | v2.12 identity/timing checks and bounded adjustments exist; small shadow evaluation. Not a broad player availability/statistics ingestion platform. |
| World Cup simulation | Implemented as CLI | v2.3 goal-based model and v2.13 completed-result locking, 50,000 simulations. Separate from the v2.7 ensemble; no API or simulation-run database. |
| Live football connector | Partial | API-Football client has API-key loading, cache TTLs, quota ledger, timeouts, and limited rate-limit retries. No general scheduler, incremental watermarks, or broad competition discovery. No `.env` file was present during inspection. |
| Weather | Partial | Open-Meteo and NWS context paths exist. Weather context is not a trained feature in the v2.7 classifier's core feature list. |
| StatsBomb | Partial | 128 match metadata rows, 256 processed team-event summaries, 128 lineup JSON files. Raw events and 360 directories absent. Full event rebuild cannot be assumed from this archive alone. |
| Player ratings | Partial descriptive functionality | `scripts/build_player_impact_v21.py` derives heuristic ratings from squad profiles, caps, age, goals, club assumptions. Not validated future player-performance regression. |
| Normalization and provider mapping | Partial | Team aliases, fixture/provider matching, and lineup identity handling exist. No canonical entity-ID service, full mapping tables, or transfer history. |
| Provenance and quality | Partial | Dataset inventory, source audits, archive hash manifest, provider request logs, data-quality scores, and validation tests exist. No end-to-end lineage, quarantine, schema drift monitoring, or correction history. |
| Match model comparison | Partial versus blueprint | Logistic Regression, Random Forest, Gradient Boosting, Elo, Poisson-lite, and ensemble comparison exist. Chronological splits, log loss, Brier, calibration bins, draw metrics, and selective coverage exist. Requested full experiment matrix and dashboards do not. |
| PostgreSQL warehouse and SQL marts | Pending | No migrations, DB loader, schema implementation, transactional upserts, constraints, or SQL marts found. |
| Airflow orchestration | Pending | No DAGs or scheduled dependency chain found. All proposed cadences remain plans. |
| Docker Compose | Pending | No Compose stack or service Dockerfiles found. |
| Club datasets and analytics | Pending | No Football-Data.co.uk ingestion or club-season analytics pipeline found. Club names in squad profiles do not constitute club match coverage. |
| Player appearances/per-90 analytics | Pending | No validated cross-match minutes/actions dataset and role-aware aggregation pipeline found. Raw lineup metadata is not a complete player-statistics dataset. |
| Player clustering/similarity | Pending | No K-Means, DBSCAN, hierarchical clustering, nearest-player service, cohort evaluation, or cluster metrics found. |
| Player regression | Conditional, pending | Requires an independent future target before Linear/Ridge/Lasso experiments are meaningful. |
| Additional classifiers/features | Pending | No implemented KNN, SVM, standalone Decision Tree, XGBoost, PCA, t-SNE, or UMAP workflow found. These are candidates, not all mandatory production models. |
| FastAPI backend | Pending | No routes, service layer, request/response schemas, OpenAPI application, or admin authorization found. |
| React frontend | Pending | No frontend application or any of the eight proposed pages found. |
| Model registry | Partial artifact metadata only | Pickle artifact and JSON configs hold some training/model metadata. No candidate promotion, registry history, complete dataset/feature lineage, or rollback workflow. |
| Platform testing | Pending beyond existing research tests | No DB, extractor contract, Airflow, API, UI, clustering, or full end-to-end acceptance suite. Existing 28 tests are not coverage of the proposed platform. |
| Documentation and academic deliverables | Partial | Blueprint, model reports, inventory, and project PDFs exist. DE demonstration/report, integrated ML demonstration, complete operations runbook, and research experiment package remain. |

## Milestone assessment

| PROJECT.md milestone | Current status | Exit work remaining |
|---|---|---|
| 1. Audit and freeze baseline | Substantially advanced, not fully closed | This audit and runtime checks exist. Create a dedicated immutable baseline bundle with fresh hashes, exact environment lock, parity fixtures, license/coverage review, and risk register. |
| 2. Scope, datasets, contracts | Partial design | Blueprint and CSV contracts exist. Select actual club seasons/player cohort; verify source access/rights and quotas; finalize IDs, dictionary, ERD, and API shapes. |
| 3. PostgreSQL warehouse | Pending | Implement schema/migrations, staging/import, constraints, repeat-import tests, and reconciliation. |
| 4. Incremental ETL and quality | Partial reusable research logic | Build reusable connector/normalization/load/reconciliation modules, quarantine, watermarks, correction replay, and recovery tests. |
| 5. Airflow and Docker | Pending | Compose services, DAGs, retries, logs, freshness checks, and failure demonstration. |
| 6. Analytics warehouse/player dataset | Pending; existing form CSVs reusable | SQL marts, head-to-head queries, valid player appearances/per-90 cohort, coverage report. |
| 7. ML integration and expansion | Core models exist; platform integration pending | Warehouse feature adapter, fixed-input parity tests, persisted predictions, simulator interface, player similarity. |
| 8. Experiments and research | Partial | Existing bakeoff/backtests reusable. Add fixed experimental datasets, train-only feature transformations, ablations/PCA/selection, complete class metrics and experiment registry. |
| 9. FastAPI and React | Pending | Entire integrated application and page/API acceptance tests. |
| 10. Final validation/demos | Partial legacy documentation only | Reproducible release setup, platform tests, two academic reports/demos, source appendix; paper only if required. |

## Priority order

1. Freeze the runnable baseline and exact environment without overwriting original datasets or model artifacts.
2. Select a small supported source/competition/player cohort and resolve source access and contracts.
3. Implement PostgreSQL schema and international historical import; prove reruns produce no duplicates.
4. Add one incremental fixture/result connector, correction logging, chronological feature replay, and quality checks.
5. Orchestrate that working vertical slice with Docker/Airflow and expose freshness/run records.
6. Adapt the existing match model and simulator to warehouse inputs with parity tests and versioned outputs.
7. Build FastAPI and React views against real persisted outputs.
8. Add club result analytics and a valid player per-90 dataset, then clustering/similarity.
9. Extend controlled experiments, academic reports, and end-to-end demonstrations.

Player regression, separately trained club predictions, Spark, Kafka, and public hosting should follow their conditional/optional status in PROJECT.md rather than block the core platform.

## Integration risks to resolve

- Historical strength inputs stop at June 2, 2026. Updating fixture statuses alone does not refresh Elo/form or retrain the model.
- Several old CSV helpers rely on the OS default encoding. The simulator failed under the Windows default but succeeded with `-X utf8`.
- Date-ordered historical features and separate calibration/test periods exist, but a platform-wide observation/availability-time contract and automated leakage rejection do not.
- `model_bakeoff_v26.design_matrix` creates dummy-column vocabulary from concatenated train/calibration/test frames. It does not use future labels for encoding, but must be changed to train-fitted preprocessing to satisfy the blueprint's strict contract.
- `matches_prior` in `summarize_history` is the length of a deque capped at 20; review whether the intended feature is total prior appearances or the available rolling-history length.
- The simulator uses the older team-power engine; integration must preserve this explicitly rather than describe it as consuming the selected 1X2 ensemble.
- Injury and odds tables include placeholders; static market priors are not a live odds movement feed.
- The historical validation scores were reproduced from included records, not independently verified against external match sources in this audit.
- `.gitignore` currently does not exclude `.venv/`, `__pycache__/`, or generated Python cache files. Add exclusions before any future staging; no staging/committing was performed.

## Conclusion

The international prediction and simulation research foundation is usable. The Data Engineering platform and full-stack/player-analytics portions of FootIQ remain largely unimplemented. Start with baseline preservation, data contracts, and an idempotent warehouse import rather than replacing the functioning models.
