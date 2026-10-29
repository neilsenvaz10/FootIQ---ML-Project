# Setup and run (Windows)

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

Tested on Windows 11 with Python 3.12.14, Node 24.13.1 and npm 11.8.0 on 2026-10-27. The repository already contains the data, the frozen models and a ready SQLite store, so nothing needs downloading.

## 1. Prerequisites

* Python **3.12** (the bundled model pickles need it) and Node.js with npm (Node 24 was used).
* Free disk space for the repository (the store is 228 MB) and a few GB of free RAM: the club history is loaded in memory.

## 2. Backend setup (once)

PowerShell, from the repository root (`D:\Foot IQ`):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-share.txt
.\.venv\Scripts\python.exe -m pip install -r app\requirements.txt
.\.venv\Scripts\python.exe -m pip install scipy==1.17.1
```

`scipy` is needed by the season simulator and is not in either requirements file (documented gap). The shipped `.venv` already has everything.

Optional rebuilds (only if a file is missing): `python -X utf8 app\prepare_data.py` (dashboard dataset, about 5 s) and `python -X utf8 app\store\build.py --fresh` (SQLite store).

## 3. Frontend setup (once)

```powershell
cd frontend
npm ci
cd ..
```

## 4. Start (two terminals)

Terminal 1, backend (`-X utf8` is required on Windows):

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000
```

Wait for `curl http://127.0.0.1:8000/api/health` to return `"club_prediction_ready":true` (20–30 s).

Terminal 2, frontend:

```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173**. The frontend talks to `http://127.0.0.1:8000` by default (`VITE_API_URL` overrides it; the backend's CORS list allows ports 5173, 5174 and 3000 on localhost and 127.0.0.1). Do not leave an old dev server running: a stale one keeps its old `VITE_API_URL` and shows "Cannot reach the backend".

**Protect the production store.** Starting the backend on `data/footiq.sqlite` appended a `sync_runs` row before Phase 4.8B (it no longer does while live sync is off). The store is in WAL mode, so `-wal` and `-shm` files sit beside it. To be extra safe, run on a private copy:

```powershell
copy data\footiq.sqlite data\demo.sqlite
$env:FOOTIQ_STORE_PATH = "D:\Foot IQ\data\demo.sqlite"
.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000
```

(The "Predict gameweek" and season-simulation buttons also write saved runs into whichever store the backend uses.)

## 5. Tests and build

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests -q          # backend, 260 tests, about 14 minutes
cd frontend
npx vitest run                                                  # 342 pass, 13 skipped (live contract tests)
$env:FOOTIQ_LIVE_API = "http://127.0.0.1:8000"; npx vitest run --no-file-parallelism   # all 355, backend running
npm run build                                                   # production bundle in frontend\dist
```

Use `pytest tests`, not bare `pytest` (duplicate copies under `docs/baseline` fail to collect). Run the live frontend tests against a private copy, and wait for `/api/health` to be ready first.

## 6. Cold-start checklist

1. No process on ports 8000 and 5173 (`Get-NetTCPConnection -LocalPort 8000,5173`).
2. Backend started; `/api/health` ready.
3. `npm run dev`; the Home page shows a featured match, no red banner.
4. `config\sync.json` still says `"live_enabled": false`.

## 7. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "Cannot reach the backend at …" | Backend not running, wrong port in `VITE_API_URL`, or a stale dev server; stop all, restart both |
| `No module named scipy` when running tests | Wrong Python on PATH; use `.\.venv\Scripts\python.exe` |
| Garbled club names, errors in the World Cup simulator | Missing `-X utf8` |
| First prediction slow | Club history still loading; wait for `club_prediction_ready` |
| Collection errors in `docs/baseline` | Run `pytest tests`, not bare `pytest` |
