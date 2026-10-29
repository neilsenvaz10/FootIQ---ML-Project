# FootIQ — Football Data Engineering, Analytics & Machine Learning Platform

FootIQ extends an existing international football prediction research pipeline into a planned data engineering and analytics platform.

The current repository contains historical datasets, feature builders, a trained international match ensemble, confidence gates, a separate World Cup simulator, tests, and generated reports. PostgreSQL, Airflow and player clustering remain planned and are not implemented. **FastAPI, React, a SQLite results store, club analytics and forecasts, a World Cup simulator and an experimental season simulator are implemented as the college mini-project.**

## Mini-project: start here

- Final documentation set: [docs/mini-project/final/](docs/mini-project/final/) (project report, architecture, models, data sources, testing, setup, limitations, demo script, viva Q&A, submission checklist)
- Run it: [docs/mini-project/final/SETUP_AND_RUN.md](docs/mini-project/final/SETUP_AND_RUN.md) (backend `uvicorn main:app --app-dir app --port 8000`, frontend `npm run dev` in `frontend/`)
- API: [docs/mini-project/API_REFERENCE.md](docs/mini-project/API_REFERENCE.md). Live synchronisation is off; the application shows historical data only.

The sections below describe the original research pipeline.

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
