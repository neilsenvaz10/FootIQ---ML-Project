# Demonstration script (3-5 minutes)

> **Final state (Phase 4.28):** FootIQ supports exactly six competitions (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, UEFA Champions League). This script replaces the earlier eleven-competition script; the earlier text is kept in the phase history. Authoritative description: `FINAL_SYSTEM_GUIDE.md`.

**Before (not part of the time).** From `D:\Foot IQ`: terminal 1 `.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000 --timeout-graceful-shutdown 5`; wait until `http://127.0.0.1:8000/api/health` shows `"club_prediction_ready":true`; terminal 2 `cd frontend; npm run dev`; open `http://localhost:5173` at desktop width. Optional: `.\.venv\Scripts\python.exe data\supervised\phase4\p427\final_verify.py` (67 checks). Do not press "Predict gameweek" or "Run simulation" unless you accept a new saved row in the database.

| Time | Screen and steps | Say |
|---|---|---|
| 0:00-0:30 | **Home** (`/`) | "FootIQ is a football analytics and prediction system on a local SQLite store and frozen models. Six competitions. The data is historical, refreshed once when the app starts, nothing is live; the freshness chips and the amber data-quality banner say so." |
| 0:30-1:10 | **Matches** (`/matches`): Premier League, status **Completed** (80 results), then **Upcoming** (300); open one card's match details | "Results and fixtures come from the stored data with the source of every row." |
| 1:10-1:50 | **Leagues** (`/analytics`): top of the table, switch to Serie A; open a club's form or head-to-head (**Compare**) | "Standings and team statistics are computed from verified stored results." |
| 1:50-2:30 | **Predict Match**: from a Premier League upcoming card press **Predict match** (the clubs are prefilled), or pick Chelsea FC v Manchester United FC (31 Oct) manually; press **Predict** | "Three models: Club v1 (validated), v2-r1 (experimental), Elo baseline. About 43% / 21% / 36%. Estimates, not certainties." |
| 2:30-3:10 | **Champions League** (`/matches?comp=UCL`): 54 completed + 90 upcoming league-phase fixtures; matchday filter 5 (18 fixtures); team filter Arsenal (8 matches). Then Predict Match, Champions League, Arsenal FC v Borussia Dortmund | "The prediction is labelled **Not validated (indicative only)**: the club models were evaluated on domestic leagues, not on the Champions League. The league table is provisional and the knockout rounds are not drawn." |
| 3:10-3:50 | **Simulations** (`/simulations`): the five domestic leagues are selectable and the Season dropdown shows only 2026-27; under **Saved simulation runs** open Run 1 **View** | "10,000 simulations, seed 1398654699, expected final points and ranges (lower and upper bounds). Final positions are disabled because no scoreline method passed our pre-declared criteria." |
| 3:50-4:30 | **Models** (`/models`) | "Sources (openfootball CC0, Wikipedia CC BY-SA, OpenLigaDB ODbL) are staged and cross-checked offline, then imported with a backup, a dry run, validation and quarantine into the SQLite store with per-row provenance, and served by the API to this React front end. The two club models are frozen and hash-checked; nothing is retrained." |

**If something goes wrong.** A prediction is refused for a fixture dated today: pick a later fixture. A clubs-not-prefilled situation: choose them in the two drop-downs. The backend lingers when stopping: close its terminal after 10 seconds. "Cannot reach the backend": the backend is down or an old dev server is running; restart both. Screenshots from earlier phases are in `docs/mini-project/phase4/p4.6/`.

**One-line close.** "Everything shown is computed from stored historical data with frozen, hashed models, and every limitation is visible in the interface."
