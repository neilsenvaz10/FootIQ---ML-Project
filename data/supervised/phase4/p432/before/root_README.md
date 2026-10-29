# FootIQ — Football Data Engineering, Analytics & Machine Learning Platform

FootIQ extends an existing international football prediction research pipeline into a planned data engineering and analytics platform.

The current repository contains historical datasets, feature builders, a trained international match ensemble, confidence gates, a separate World Cup simulator, tests, and generated reports. PostgreSQL, Airflow and player clustering remain planned and are not implemented. **FastAPI, React, a SQLite results store, club analytics and forecasts, a World Cup simulator and an experimental season simulator are implemented as the college mini-project.**

## FootIQ application (final mini-project state, Phase 4.28)

FootIQ is a local football analytics and prediction web application (FastAPI + SQLite + React) for **exactly six competitions**: Premier League, La Liga, Bundesliga, Serie A, Ligue 1 and the UEFA Champions League (league phase). It shows 2026-27 results, upcoming fixtures, standings, team statistics and match probabilities from frozen club models, plus an experimental points-only season simulator (five domestic leagues) with saved runs. Data is historical: the Bundesliga and La Liga are refreshed once from OpenLigaDB when the backend starts; the other competitions are static, imported only after verification. Champions League predictions are labelled "Not validated (indicative only)".

- **Start here:** [docs/mini-project/final/FINAL_SYSTEM_GUIDE.md](docs/mini-project/final/FINAL_SYSTEM_GUIDE.md) (coverage, limits, models, pipeline, sources and licences, start/stop, known gaps, demonstration)
- Run it: [docs/mini-project/final/SETUP_AND_RUN.md](docs/mini-project/final/SETUP_AND_RUN.md) (backend `uvicorn main:app --app-dir app --port 8000 --timeout-graceful-shutdown 5`, frontend `npm run dev` in `frontend/`)
- Full documentation set: [docs/mini-project/final/](docs/mini-project/final/); API: [docs/mini-project/API_REFERENCE.md](docs/mini-project/API_REFERENCE.md); latest verification: [docs/mini-project/phase4/P4_28_FINAL_CLEANUP_AND_READINESS.md](docs/mini-project/phase4/P4_28_FINAL_CLEANUP_AND_READINESS.md)

The sections below describe the original research pipeline (an earlier international World Cup baseline that is no longer part of the application).

## Start here

- [Project blueprint](PROJECT.md)
- [Implementation audit](docs/architecture/CURRENT_STATE.md)
- [Research snapshot documentation](README_SHARE.md)
- [Dataset inventory and provenance](outputs/world_cup_data_inventory.md)
- [Model comparison](outputs/model_v26_bakeoff_report.md)

## Run locally

Use Python 3.12 for compatibility with the included model artifact. In PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-share.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -X utf8 scripts/build_live_predictions_v27.py
.\.venv\Scripts\python.exe -X utf8 scripts/build_confidence_gate_v28.py
.\.venv\Scripts\python.exe -X utf8 scripts/simulate_live_tournament_v213.py
```

These commands use included snapshots; they do not fetch current football results. Outputs are written to `data/processed/` and `outputs/`. UTF-8 mode avoids Windows team-name encoding mismatches.

Live jobs require your own API-Football key, configured using `.env.example`. Do not commit `.env` or provider caches. Fixture refresh, historical feature refresh, and model retraining are separate operations.

## Current models

- Regulation-time match probabilities: 50% gradient boosting, 30% Elo, 20% logistic regression, with calibration and abstention rules.
- Tournament simulation: separate goal-based engine, 50,000 simulations, completed-result locking.
- The saved match artifact reports 25,235 training matches from January 2000 to June 2, 2026.

The baseline was run on October 20, 2026: 28 tests passed, eight saved fixtures scored, and the tournament simulator completed. Historical validation numbers and current implementation limitations are documented in the audit. Archived forecasts are not current live predictions.

## Data and rights

Third-party datasets retain their own terms and attribution requirements. See the data inventory and source/provenance documents before reuse or redistribution. This repository does not grant additional rights to third-party data. Predictions are probabilistic research outputs.

`SHARE_MANIFEST.sha256` is the original shared-archive manifest, not a checksum manifest for the evolving Git repository.
