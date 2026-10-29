# FootIQ final system guide (Phase 4.28)

This is the current, authoritative description of the submitted application. It was written and checked against the running application on 2026-10-28. Older phase reports are kept unchanged as history; where one of them disagrees with this guide, this guide is right.

## 1. What FootIQ is

A local football analytics and prediction web application for a college mini-project: a FastAPI backend over a SQLite results store, frozen scikit-learn club models, and a React front end. It shows results, fixtures, standings, team statistics and match probabilities for **exactly six competitions**. All numbers come from stored data; nothing is live, and nothing is trained when you use it.

## 2. The six competitions and current-season coverage (2026-27)

| Competition | Completed matches | Upcoming fixtures | Update source | Prediction label |
|---|---|---|---|---|
| Premier League | 80 | 300 | none (static data, imported after verification) | Validated |
| La Liga | 99 | 280 (+1 awaiting result) | OpenLigaDB, once at start | Validated |
| Bundesliga | 63 | 243 | OpenLigaDB, once at start | Validated |
| Serie A | 80 | 297 (+3 awaiting result) | none (static data, imported after verification) | Validated |
| Ligue 1 | 72 | 234 | none (static data, imported after verification) | Validated |
| Champions League (league phase) | 54 | 90 | none (static data, imported after verification) | **Not validated (indicative only)** |

* Each league shows results, upcoming fixtures, standings, team pages (form, head-to-head), predictions and a freshness indicator, from season 2018-19 to 2026-27.
* The Champions League shows the 36-club league-phase table (provisional until all 144 matches are played), the 144 league-phase fixtures (matchdays 1-8) in the Matches hub with matchday and team filters, and predictions. The knockout rounds are not drawn yet and are not in the data.
* Europa League, Conference League, World Cup, Nations League and Copa America were removed from the application in Phase 4.18. Their data is preserved on disk but not shown, served or predicted (their routes answer 404 or 422).

## 3. Prediction limits (read this before presenting numbers)

* Each match prediction shows three models: **Club v1** (25 features, validated on pooled domestic leagues: about 50% accuracy on three outcomes, log loss 1.007 against 1.076 for always predicting a home win, on 15,645 test matches), **Club v2-r1** (62 features, experimental; it has no unbiased test) and an **Elo baseline**. Draws are almost never the most likely outcome.
* **Champions League predictions use the same club models but were never validated on Champions League matches.** They are always labelled "Not validated (indicative only)". Do not describe them as validated.
* No injuries, line-ups, weather, transfers or player data are used. Probabilities are estimates, not certainties and not betting advice.
* A fixture dated today is not forecast (its kickoff time zone is unverified); pick a later fixture.

## 4. Frozen machine-learning models

The two club models and the Elo baseline are frozen files whose SHA-256 hashes are checked when the backend starts and again in the final verification. Nothing is retrained by the application or by Phase 4.28. Archived international models (v2.7 and the World Cup engine) remain in the repository as history and are not served.

## 5. Saved simulations and forecasts

* Season simulator (**experimental, points-only**), for all five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1; never the Champions League): choose a league, 2026-27, 1,000-50,000 simulations (10,000 by default) and an optional seed, then press **Run points-only simulation**. For every unplayed fixture it draws win/draw/loss from the frozen club v1 probabilities and awards 3/1/0 points; completed matches are never simulated again, and fixtures past their date without a verified result (for example three in Serie A) are simulated like future fixtures and disclosed in the data-quality banner. It shows expected final points with a 10-90% range per club. Lower/upper bounds for title, top four and relegation are shown only for the Bundesliga and La Liga (verified tie-break rules); the other leagues show why they are not available. The "Final positions" mode is disabled because no scoreline method passed the pre-declared acceptance criteria. Simulation runs only when you press the button, and the run is saved to the database.
* The Season dropdown lists only seasons that still have unplayed fixtures (in practice the current season, 2026-27). If a league had none, the page says "No season to simulate".
* Two saved simulations exist and must stay unchanged: run 1 (Bundesliga, seed 1398654699) and run 2 (La Liga, seed 1499656622), each 10,000 simulations. Open them with **View** under "Saved simulation runs".
* One saved Premier League Matchday 9 forecast run (30 rows) exists from the Predictions page. "Predict gameweek" and "Run simulation" save new rows to the database; do not press them during a demo unless you accept that.

## 6. Data engineering pipeline

Sources are staged and cross-checked offline, then imported into the store only by importers that default to a dry run, require a verified byte-identical backup for a production run, validate every row, keep per-row provenance (source, licence, first-seen, content hash) and send failures to a quarantine table (273 rows). Scripts: `app/store/uefa_import.py` (Champions League results and fixtures, each behind a verification gate), `app/store/league_results_import.py` (domestic results), `app/store/reconcile_import.py` (date and result corrections in evidence tiers). Date disputes that lack strong evidence are held, never applied automatically. Phase reports 4.9-4.24 in `docs/mini-project/phase4/` record each step.

At startup the backend refreshes the Bundesliga and La Liga **once** from OpenLigaDB (two requests, 15-minute minimum gap; `FOOTIQ_DISABLE_SYNC=1` switches it off). There is no scheduler and no live data.

## 7. Sources, licences and attribution

| Source | Used for | Licence |
|---|---|---|
| openfootball | club league and Champions League history and schedules | CC0-1.0 |
| Wikipedia | Champions League and verified league results | CC BY-SA 4.0 (attribution and share-alike) |
| OpenLigaDB | Bundesliga and La Liga startup refresh | ODbL (attribution) |
| football-data.co.uk, FixtureDownload | cross-checking only; never stored | not redistributed |
| StatsBomb open data | only the separate dataset submission (player CSVs) | StatsBomb licence, credit required (`FootIQ_Dataset_Submission/_raw_sources/statsbomb_open_data/LICENSE.pdf`) |

The football-data.org API is not used and no token is stored. The Models and About pages show the attribution list from `/api/meta`.

## 8. Start and stop

From `D:\Foot IQ` (PowerShell).

Backend, terminal 1:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000 --timeout-graceful-shutdown 5
```

Wait until `http://127.0.0.1:8000/api/health` shows `"club_prediction_ready":true` (15-40 seconds).

Frontend, terminal 2:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. Optional check: `.\.venv\Scripts\python.exe data\supervised\phase4\p427\final_verify.py` (67 read-only checks).

**Stop:** press Ctrl-C once in each terminal. If the backend prompt has not returned after 10 seconds, close that terminal window; the database is safe (verified after every forced stop). Never run two backends on port 8000.

## 9. Known data gaps and issues

* Premier League, Serie A, Ligue 1 and the Champions League have no update source; their newest results are those imported after verification (25-26 October 2026).
* Three Serie A results rest on a single source and were not applied; one La Liga match is postponed; 60 provider-assisted date corrections are held for a decision.
* Roughly half of the scheduled fixtures have a local kickoff time without a time zone; they are shown as stored and marked "time zone unconfirmed".
* Champions League: league table provisional, knockout stage absent, predictions not validated.
* The Python environment needs `scipy==1.17.1`, which is missing from the requirements files.
* The backend sometimes lingers at "Shutting down" after Ctrl-C (use the stop procedure above).
* `App.jsx` still routes `/worldcup` to the Simulations page (leftover alias, harmless).

## 10. How to demonstrate (3-5 minutes)

See `DEMO_SCRIPT.md`: dashboard, competition results, standings and team statistics, a Premier League prediction, the Champions League hub and its "Not validated" prediction, a saved simulation, then the data pipeline and frozen models.
