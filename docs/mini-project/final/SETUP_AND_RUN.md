> **Publication snapshot, 29 October 2026:** This clean release tree has no production SQLite database or old project Git history. The active application covers five domestic leagues and the UEFA Champions League. World Bank indicator files, archived StatsBomb-derived tactical aggregates and their selected downstream reports/workbooks are withheld while redistribution rights remain uncertain. Archived international rebuilding/examples therefore need separately authorised inputs. Club models, their evaluation reports and all eight approved LFS inputs are retained unchanged. Follow `docs/mini-project/final/SETUP_AND_RUN.md` section 4a to rebuild locally. Attested mode remains explicit and is labelled **not independently reproducible**. No source-code licence is granted. See `PUBLICATION_NOTES.md` for the exact migration limits.

# Setup and run (Windows)

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

Tested on Windows 11 with Python 3.12.14, Node 24.13.1 and npm 11.8.0 (last start and stop test 2026-10-28). This publication includes the approved data and frozen models through Git/Git LFS, but no SQLite store. Pull the LFS objects and rebuild a private store using section 4a before starting the backend.

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

`scipy==1.17.1` is included explicitly in `app/requirements.txt`; the additional install line above is redundant. In earlier snapshots it was not named in either requirements file; pip normally installs it as a dependency of scikit-learn, and the line above pins it explicitly (the submission package also contains `requirements-final.txt` with it). If `py -3.12` is not found (a Python 3.12 installed by another launcher), run `py -0` to list the installed versions and use the matching selector, for example `py -V:Astral/CPython3.12.12 -m venv .venv`, or call that `python.exe` directly. Clean-install result (Phase 4.32): a new virtual environment with the two requirements files plus `scipy==1.17.1` and `npm ci` started the backend (ready in about 20-30 s) and passed all 67 live checks.

**Files the prediction runtime needs besides `app/` and the database:** the frozen model folders, `FootIQ_Club_Model_Development_v2/_scripts/` and `FootIQ_ML_Training_Preparation/_build/*.py` (feature code), `FootIQ_Club_Model_Development_v2/source_adapters_r1/footiq_sources/` and `config/` (source adapters used by the data-quality checks), `config/*.json`. `config/contact.local` (a private contact string for the provider) is not needed when synchronisation is off.

Optional rebuilds (only if a file is missing): `python -X utf8 app\prepare_data.py` (dashboard dataset, about 5 s) and `python -X utf8 app\store\build.py --fresh` (SQLite store).

## 3. Frontend setup (once)

```powershell
cd frontend
npm ci
cd ..
```

## 4. Start (two terminals)

Updated in Phase 4.28 (see `FINAL_SYSTEM_GUIDE.md` section 8). Terminal 1, backend from the repository root (`-X utf8` is required on Windows; `--timeout-graceful-shutdown 5` makes stopping reliable):

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000 --timeout-graceful-shutdown 5
```

Wait for `curl http://127.0.0.1:8000/api/health` to return `"club_prediction_ready":true` (15-40 s). At start the backend refreshes the Bundesliga and La Liga once from OpenLigaDB (two requests, at least 15 minutes apart); set `FOOTIQ_DISABLE_SYNC=1` to switch that off (for example in tests or on a second instance).

Terminal 2, frontend:

```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173**. The frontend talks to `http://127.0.0.1:8000` by default (`VITE_API_URL` overrides it; CORS allows ports 5173, 5174 and 3000 on localhost and 127.0.0.1). Do not leave an old dev server running: a stale one keeps its old `VITE_API_URL` and shows "Cannot reach the backend".

**Stop:** one Ctrl-C in each terminal. If the backend prompt has not returned after 10 seconds, close that terminal window (safe: the SQLite store recovers; verified after every forced stop). Never run two backends on port 8000.

**Protect the production store.** The store is `data/footiq.sqlite` in WAL mode (`-wal` and `-shm` files sit beside it). The "Predict gameweek" and season-simulation buttons write saved runs into it. A verified backup is in `data/backups/p428_fresh_20261028/` (SHA-256 in `SHA256.txt`). To run on a private copy instead:

```powershell
copy data\footiq.sqlite data\demo.sqlite
$env:FOOTIQ_STORE_PATH = "D:\Foot IQ\data\demo.sqlite"
```

## 4a. Rebuilding the database from the repository (no production file needed)
Everything needed is in the repository; `V_universe.pkl` and seven large training CSVs come through **Git LFS** (`git lfs install` before cloning, `git lfs pull` after; 573.6 MiB in total, so budget about 0.6 GB of LFS bandwidth per full clone).

1. `python app/store/build.py --path data/footiq.sqlite` builds the **baseline** store (data through 2026-09-20, CC0 inputs only; about 10 s).
2. Choose one rebuild mode (each writes `<folder>/replay.sqlite`, takes about 30 s, and prints a comparison with `data/footiq.sqlite` when that file exists). Copy `replay.sqlite` over `data/footiq.sqlite`, or set `FOOTIQ_STORE_PATH`, to run the application on it.

| Mode | Command | What it uses | Result |
|---|---|---|---|
| **Standard (published)** | `python scripts/rebuild_current_state.py <folder> published` | saved OpenLigaDB snapshots (ODbL), Wikipedia-derived Champions League inputs (CC BY-SA), and a result or date only when **two redistributable sources** agree | 83 domestic results and 31 Premier League date corrections are missing; Bundesliga and La Liga simulators are eligible, Premier League, Serie A and Ligue 1 are not |
| **Optional attested** | `python scripts/rebuild_current_state.py <folder> snapshot` | the published mode, then the opt-in `--evidence attested` pass | 80 results and 31 date corrections are added back; all five domestic simulators can run |
| Maintainer-exact | `... <folder> local` | restricted local staging files (not in the repository) | identical to the maintainer's store |

3. **The 80 attested results.** Attested mode accepts a result that Wikipedia (CC BY-SA 4.0) supports and that no redistributable source contradicts, together with the maintainer's statement that a private cross-check agreed. That statement is **not publicly verifiable**: the cross-check data is restricted and is not published. These records are therefore labelled "attested, NOT independently reproducible from public data" in `match_sources.provenance`, in the `sync_runs` source, and in `data/evidence/published/ATTESTED_RECORDS.csv` (80 results + 31 fixture-date corrections, with Wikipedia revision, evidence id and review decision). Attested mode is never the default; the importers still default to `--evidence restricted`.
4. **The three missing results.** One La Liga and two Ligue 1 results (listed in `data/evidence/published/UNSUPPORTED_RESULTS.csv`) have a played day that exists only in a restricted source. They are **not** added in any public mode and stay "scheduled".
5. **Five-league simulator eligibility after the attested rebuild:** Premier League ready, La Liga ready, Bundesliga ready, Serie A provisional, Ligue 1 provisional (production: Ligue 1 ready). The points-only Monte Carlo simulation runs for all five; the Champions League has no season simulator. After the standard (published) rebuild only the Bundesliga and La Liga are eligible.
6. **Licences and attribution.** `DATA_LICENSES.md` lists every source: openfootball and martj42 are CC0; Wikipedia is CC BY-SA 4.0 (attribute page and revision); OpenLigaDB is ODbL 1.0 ("Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0"); World Bank data is CC BY 4.0 by default. StatsBomb, API-Football, football-data.co.uk, FixtureDownload and football-data.org data are **not** distributed and the application does not need them.
7. **Known reproducibility limitations.** The 130 World Cup 2026 rows from provider and news sources are not in the published dashboard CSVs, so the archived World Cup 2026 results are absent; the three results above; Ligue 1 is "provisional" instead of "ready"; the 80 attested results cannot be re-verified independently; player statistics from StatsBomb are not published (CC0 extracts only: `FootIQ_Dataset_Submission/cc0_extracts`); the Bundesliga / La Liga start-up refresh needs your own contact string in `config/contact.local`. Three tests in `tests/` compare against the maintainer's exact store state; they pass on the rebuilt store after Phase 4.38.

## 5. Tests and build

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests -q          # backend; the full run takes about 24 minutes; 579 pass, 8 skipped
cd frontend
npx vitest run                                                  # 375 pass, 13 skipped (live contract tests), about 10 s
$env:FOOTIQ_LIVE_API = "http://127.0.0.1:8000"; npx vitest run --no-file-parallelism   # also runs the live contract tests, backend running
npm run build                                                   # production bundle in frontend\dist
```

Use `pytest tests`, not bare `pytest` (duplicate copies under `docs/baseline` fail to collect). Results of the last runs: `TESTING_REPORT.md` and `docs/mini-project/phase4/P4_28_FINAL_CLEANUP_AND_READINESS.md`. Read-only live check of all six competitions: `.\.venv\Scripts\python.exe data\supervised\phase4\p427\final_verify.py` (67 checks; pass another base URL as the first argument).

## 6. Cold-start checklist

1. No process on ports 8000 and 5173 (`Get-NetTCPConnection -LocalPort 8000,5173`).
2. Backend started; `/api/health` ready.
3. `npm run dev`; the Home page shows a featured match, no red banner.
4. `config\sync.json` says `"sync_mode": "startup"` with OpenLigaDB for BUNDESLIGA and LALIGA only.

## 7. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "Cannot reach the backend at ..." | Backend not running, wrong port in `VITE_API_URL`, or a stale dev server; stop all, restart both |
| `No module named scipy` when running tests | Wrong Python on PATH; use `.\.venv\Scripts\python.exe` |
| Garbled club names | Missing `-X utf8` |
| First prediction slow | Club history still loading; wait for `club_prediction_ready` |
| Collection errors in `docs/baseline` | Run `pytest tests`, not bare `pytest` |
| Backend lingers at "Shutting down" | Close the terminal window after 10 s (section 4) |
| Prediction refused for a fixture dated today | By design (kickoff time zone unverified); choose a later fixture |
