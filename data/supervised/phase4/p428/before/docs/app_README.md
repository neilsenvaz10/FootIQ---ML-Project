# FootIQ mini-project app

FastAPI backend + one static HTML page. Reads CSVs; runs the **existing** frozen models. Nothing is trained, no database, no scheduler.
Scope and rationale: [docs/mini-project/MINI_PROJECT_PLAN.md](../docs/mini-project/MINI_PROJECT_PLAN.md). API: [API_REFERENCE.md](../docs/mini-project/API_REFERENCE.md); React guide: [FRONTEND_INTEGRATION.md](../docs/mini-project/FRONTEND_INTEGRATION.md).

## Results store (Phase 1)

`data/footiq.sqlite` (git-ignored, rebuildable) is the operational store. Build it once, offline, from the repository baseline:

```bash
.venv/Scripts/python.exe -X utf8 app/store/build.py --fresh
```

When the file exists the app reads dashboard data and the model history from it (identical to the CSV/pickle path, tested); without it the app falls back to the CSV and pickle. Synchronisation is configured in `config/sync.json` and is **off** (`live_enabled: false`); see `docs/mini-project/PHASE1_REPORT.md`.

## Run

```bash
# one-time: install the two extra packages (pandas, numpy, scikit-learn, scipy are already in .venv)
.venv/Scripts/python.exe -m pip install -r app/requirements.txt

# 1. build the dataset from the CSVs already in the repo (about 5 s)
.venv/Scripts/python.exe -X utf8 app/prepare_data.py

# 2. start the app, then open http://127.0.0.1:8000
.venv/Scripts/python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000

# tests (51 = 28 existing + 23 new, about 65 s)
.venv/Scripts/python.exe -X utf8 -m pytest tests -q
```

`-X utf8` is required on Windows: the existing World Cup simulator reads CSVs with the default encoding otherwise.
Use `pytest tests`, not bare `pytest`: duplicate test copies under `docs/baseline/capture_*` fail to collect (pre-existing).
After start-up the club-prediction history (216k matches) loads in the background for about 20-30 s; later predictions take milliseconds.

## Files

| File | Role |
|---|---|
| `config.py` | The six supported competitions (and the five archived ones, kept for the data-building code), source ids, validation badge and its basis |
| `prepare_data.py` | Filters the source CSVs to all 11 stored competitions (the archive included; the application shows six) into `data/miniproject/matches.csv`, plus `data_audit.csv` and `season_coverage.csv`. No imputation; unscored rows dropped |
| `analytics.py` | Standings, summary rates, form, head-to-head |
| `predict.py` | Club v1 and v2-r1 via the project's own feature code; international v2.7 ensemble. Parity with the original inference code is tested |
| `worldcup_sim.py` | Wrapper over `scripts/simulate_live_tournament_v213.py` (writes nothing) |
| `main.py`, `static/index.html` | API and page |

## Refreshing data

Replace or extend the source CSVs (`FootIQ_ML_Data_Readiness/04d_COMBINED_CLUB_MATCHES_v1.0.csv`, `data/raw/international_results/results.csv`), re-run `prepare_data.py`, restart the app.
Note: **predictions use the frozen models' own history files** (`FootIQ_ML_Training_Preparation/_build/work/V_universe.pkl` for clubs, `data/processed/team_elo_latest.csv` and `team_recent_form_latest.csv` for internationals), which end on 2026-09-20 and 2026-06-02. Updating the dashboard CSV does not move those dates.

## Known limitations (shown in the UI where relevant)

- Champions, Europa and Conference League predictions are indicative only: no continental-competition validation exists.
- Nations League and Copa América: model validated on pooled internationals, not per competition.
- World Cup simulation shows the archived 2026 state (almost everything locked to real results). It is a different engine from the v2.7 match model.
- International scores are the recorded scores (knockouts include extra time); 90-minute results are not separable there.
- Club v1 test and forward-holdout metrics were inspected during development, and v2-r1 was refit on them: they are history, not new independent evidence.
- 2026 World Cup results come from the repo's own verified result files (source URL per row); the final (2026-07-19) is not in them.
