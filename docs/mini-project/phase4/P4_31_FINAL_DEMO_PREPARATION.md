# Phase 4.31: final demonstration preparation

Materials only: no code change, no restart, no import, no database write, no cleanup, no Git operation. All values below were read on 2026-10-28 from the running application (GET requests; database hash unchanged at `d8962089...`) and from the Phase 4.29 / 4.30 verification. Nothing was run that saves data, and no screenshot was created or invented.

## 1. Exact demo sequence (about 4 min 45 s)
Open `http://localhost:5173`. Left menu: Home, Matches, Leagues, Compare, Predictions, Simulations, Models.

| Time | Page and action | Expected on screen (real values of 28 Oct 2026) |
|---|---|---|
| 0:00-0:35 | **Home** (`/`). Point at the next-match banner, league overview chips, the header "Historical data, refreshed once when FootIQ starts; nothing is live". | Featured fixture: Bundesliga, SV 07 Elversberg v 1. FSV Mainz 05, 30 Oct 20:30 (Matchday 8). Six competitions: Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Champions League. Freshness chips: Bundesliga "fresh", others "stale"; amber data-quality banner. |
| 0:35-1:10 | **Matches** -> Premier League -> status **Completed**, then **Upcoming**. | 80 completed (newest 25 Oct; the first card is Sunderland, 0-0), 300 upcoming; first upcoming 31 Oct Chelsea v Manchester United, Manchester City v Brighton, Bournemouth v Leeds. Card details show date and source. |
| 1:10-1:45 | **Leagues** -> Premier League table; switch to Serie A. Optionally **Compare** (Arsenal v Chelsea). | Premier League after 8 matches each: Manchester City 21 pts, Arsenal 21, Brighton 16. Serie A: Inter 22, Lazio 22, Roma 18; its banner explains partial season / data age. |
| 1:45-2:20 | **Matches** -> Premier League upcoming -> press **Predict match** on Chelsea v Manchester United (clubs are prefilled) -> **Predict**. | Club v1 (validated): about **43% / 21% / 36%** (home / draw / away); v2-r1 (experimental) 43 / 27 / 30; Elo baseline 40 / 29 / 31. Say "estimates, not certainties". If 31 Oct has passed use the next upcoming fixture. |
| 2:20-2:55 | **Matches** -> Champions League -> Upcoming -> Matchday 5 filter; then **Predict match** on Arsenal v Borussia Dortmund (24 Nov). | Champions League: 54 completed + 90 upcoming (144 league-phase matches); Matchday 5 has 18 fixtures. Prediction about **69 / 20 / 11** with the badge **"Not validated (indicative only)"**. League-phase table leader: Paris Saint-Germain (9 pts, GD +9, 3 played), then Aston Villa, Liverpool, Real Madrid. |
| 2:55-4:00 | **Simulations**. League **Premier League**, season **2026-27** (the only season offered), simulations **1000**, press **Run points-only simulation**. Then league **Serie A** and run again. | Premier League: ready banner (80 of 380 played, 300 left); result in about 5-6 s: Arsenal about **83 expected points (about 75-91 for 10-90%)**, Manchester City about 82 (73-90). Serie A: banner **Provisional**, "3 fixture(s) dated up to today have no verified result ... simulated like future fixtures"; it still runs (Inter about 89, Roma about 79). Ranges panel: only for Bundesliga and La Liga; for the others the page says why. **Final positions** tab is greyed out ("disabled"). Numbers differ slightly with another seed. |
| 4:00-4:25 | Same page, scroll to **Saved simulation runs** (league Bundesliga / La Liga / Premier League) -> **View**. Then **Predictions** -> Gameweek -> Premier League Matchday 9. | Saved runs: 1 Bundesliga (10,000 sims, seed 1398654699, Bayern about 85.6 points), 2 La Liga (seed 1499656622, Barcelona about 96.9), 3 Premier League (seed 1901326415, Arsenal about 83.1). Matchday 9 shows the saved forecast run of 28 Oct (10 fixtures, three models each = 30 rows). |
| 4:25-4:45 | **Models** page. | Sources and licences, frozen models with hash-checked status, club v1 evaluation (50.2% accuracy, log loss 1.0073 on 15,645 test matches), the Champions League warning. |

## 2. Monte Carlo talking points (Part B)
- Choose Premier League, 2026-27, type **1000** (the default is 10,000: do not use it live, it takes longer and saves a bigger run). Press the button once.
- **Expected final points**: the average over 1,000 imagined endings of the season. **10-90% range**: in 8 of 10 simulated seasons the club finishes inside it (for example Arsenal about 75-91).
- How it works: every unplayed match is drawn as win / draw / loss from the frozen model's probabilities, awarding 3 / 1 / 0 points; played matches are never redone. Same seed and data give the same answer.
- Switch to **Serie A** to show **provisional data can still run**: 3 fixtures are past their date without a verified result; they are simulated like future fixtures and the warning stays visible. It is not hidden.
- **Why no exact final positions**: that needs a goals model to break ties, and none of the three candidates we tested passed our pre-declared validation, so the tab is disabled. Title / top-four / relegation **bounds** (lower and upper, not probabilities) exist only for Bundesliga and La Liga, whose tie-break rules were verified.
- **Warning for the live run: every press of Run saves a record to the database** (it is a user action). To keep the production database untouched during rehearsals and the demo, use the private-copy start in section 4 (optional).

## 3. Speaking script (about 4 min 30 s, roughly 620 words)
**Problem (30 s).** "Football data is spread over many websites, in different formats and with different licences, and predictions are usually shown without any evidence of how good they are or how old the data is. Our project, FootIQ, asks one question: can we wrap honest, already-evaluated models in an application that never overstates what it knows? It covers six competitions: the Premier League, La Liga, Bundesliga, Serie A, Ligue 1 and the Champions League."

**Data engineering (60 s).** "Everything starts as open data: openfootball, Wikipedia and OpenLigaDB, each with its licence recorded. We never load data straight into the app. New results are first staged and cross-checked against a second source. A validated importer then loads them: it runs as a dry run first, needs a verified backup, validates every row, and sends anything suspicious to a quarantine table, 273 rows so far. Every match keeps its source, licence and a content hash. The result is one SQLite database of about 223,000 matches, served by a FastAPI backend to this React interface. Only the Bundesliga and La Liga refresh, once, when the application starts; the other competitions are static, and the screen says so."

**Machine learning (45 s).** "We did not train anything for the demo. The model is a frozen logistic regression, 'club v1', that turns ratings and recent form of both clubs into three probabilities: home win, draw, away win. On 15,645 test matches it is right about 50 percent of the time, which is normal for football, and its log loss, 1.007, beats always guessing a home win, 1.076. A second, richer model is shown as experimental, and an Elo rating is the baseline. The model files are hashed and checked."

**Predictions (45 s).** "Here is Chelsea against Manchester United: about 43 percent home, 21 draw, 36 away. These are probabilities, not certainties. For the Champions League the same model is used, but it was never validated on that competition, so every prediction carries the label 'Not validated, indicative only'."

**Monte Carlo (75 s).** "Predicting one match is useful, but fans ask who will win the league. So we replay the rest of the season. I choose the Premier League, 1,000 simulations, and press Run. For each unplayed match the computer draws win, draw or loss using the model's probabilities and awards three, one or zero points. After 1,000 seasons we see that Arsenal finishes on about 83 points, usually between 75 and 91. For Serie A three results are missing, so the data is marked provisional; the simulation still runs, but the warning stays. We deliberately do not claim an exact league table, because that would need a scoreline model that did not pass our own validation tests."

**Results and limitations (40 s).** "What works: six competitions, results, fixtures, standings, predictions, a reproducible simulator, saved runs, and 579 backend and 375 frontend tests passing. The limitations are visible in the app: four competitions have no update source, so they are historical; the Champions League knockout rounds are not in the data; v2-r1 and Champions League predictions are not validated; and there are no injuries or line-ups in the model."

**Conclusion (15 s).** "FootIQ's contribution is not higher accuracy, it is transparency: every screen says what the data is, how old it is, and what the model has and has not been validated on. Thank you."

## 4. Startup and recovery checklist (Part C)
**Before the demo (10 minutes early)**
1. Network: not required to run the demo. Internet is needed only for the start-up refresh of the Bundesliga and La Liga; if offline, start the backend with `$env:FOOTIQ_DISABLE_SYNC = "1"` first (that variable switches the refresh off; behaviour without internet and without it was not tested).
2. Backend (terminal 1, `D:\Foot IQ`): `.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000 --timeout-graceful-shutdown 5`. Ready when `http://127.0.0.1:8000/api/health` shows `"club_prediction_ready":true` (15-40 s).
3. Frontend (terminal 2): `cd frontend` then `npm run dev`; open `http://localhost:5173`. Only one backend and one front end; nothing else on ports 8000 / 5173.
4. Verify (optional, read-only, about 1 minute): `.\.venv\Scripts\python.exe data\supervised\phase4\p427\final_verify.py` -> "67 of 67 checks passed".
5. Database integrity: run `.\.venv\Scripts\python.exe data\supervised\phase4\p418b\verify_production.py` -> `integrity_check: ok`, five frozen-model hashes `true`, `db_file_unchanged_by_this_check: true`.
6. Pages: Home (no red banner), Matches > Premier League (80 / 300), Leagues, Predictions, Champions League (54 + 90), Simulations (five leagues, only 2026-27), saved runs 1-3 visible, Models.
7. **Optional safer demo stack (keeps the production database from receiving new saved runs):** `copy data\footiq.sqlite data\demo.sqlite`, then in the backend terminal `$env:FOOTIQ_STORE_PATH = "D:\Foot IQ\data\demo.sqlite"` before the uvicorn command. The copy contains saved runs 1-3 and the Matchday 9 forecast.
8. Do not press **Predict gameweek**; press Run only on the simulator, once or twice, with 1,000 simulations.

**If the backend stops during the demo** (red "Cannot reach the backend" banner)
1. Look at terminal 1. If it shows an error or has exited, press Ctrl-C once, and run the same start command again; wait for `/api/health` (15-40 s), then reload the browser page. No data is lost: saved runs are in the database.
2. If Ctrl-C does not return the prompt within 10 seconds, close that terminal window and open a new one; then start again (safe: verified after every forced stop).
3. If port 8000 is "in use": `Get-NetTCPConnection -LocalPort 8000` shows the owner; stop that process (never run two backends) and start again.
4. If a page still fails, continue with another page and say the limitation aloud; the recorded screenshots (section 6) are the fallback.
5. If the database ever looks wrong, do not improvise: stop the backend and use the verified backups `data/backups/p430_pre_restart_20261028/` (hash in `SHA256.txt`) or `p428_fresh_20261028/` by copying the file over `data/footiq.sqlite` while the backend is stopped, then restart.

## 5. Known limitations to mention (Part A-D)
- Data is historical. Only the Bundesliga and La Liga refresh, once per start; Premier League, Serie A, Ligue 1 and the Champions League have no update source (the chips read "historical only" or "stale" as days pass; this is the safeguard working).
- Champions League: league phase only (matchdays 1-8), table provisional, knockout rounds not in the data, predictions never validated.
- Club v2-r1 has no unbiased evaluation; accuracy about 50% on three outcomes; draws are almost never the top pick.
- Simulator: points-only and experimental; exact final positions disabled; ranges only for Bundesliga and La Liga; Serie A provisional (3 fixtures past their date without a result); one La Liga match postponed.
- A fixture dated today cannot be forecast (kickoff time zone unverified): pick a later one. Roughly half of the fixtures have a local time without a time zone, shown as stored.
- No injuries, line-ups, weather or player data. Single user, local only, no authentication.

## 6. Screenshot and recording checklist (to be captured from the live application; none exist yet for the final version)
The screenshots in `docs/mini-project/phase4/p4.6/` come from an earlier version of the interface and must not be used as evidence of the final six-competition application.
1. Home with the six competitions, next-match banner, freshness chips (desktop 1440 px).
2. Matches: Premier League, Completed tab (80) and Upcoming tab (300).
3. Leagues: Premier League table; Serie A table with its banner.
4. Compare: Arsenal v Chelsea head-to-head (optional).
5. Predict Match: Chelsea v Manchester United with three model tabs, including the clubs prefilled from a Matches card.
6. Matches > Champions League: 54 + 90 counts, Matchday 5 filter; league-phase table.
7. Champions League prediction showing the "Not validated (indicative only)" badge.
8. Simulations: Premier League with 1,000 simulations, the result table (expected points, 10-90%).
9. Simulations: Serie A showing the Provisional banner and a completed result.
10. Simulations: the Final positions tab disabled; La Liga or Bundesliga range panel; a Premier League page showing the "available for the Bundesliga and La Liga only" reason.
11. Saved simulation runs list with runs 1-3 and one opened run.
12. Predictions > Gameweek: Premier League Matchday 9 with the saved forecast run.
13. Models page: evaluation and caveats.
14. Terminal evidence: `final_verify.py` output "67 of 67 checks passed"; `verify_production.py` integrity ok; pytest summary lines (579 passed, 8 skipped) and the Vitest summary (375 passed, 13 skipped).
15. Optional 4-5 minute screen recording of section 1 as backup. Capture each item on the day, from the real app; do not edit the numbers.

## 7. Final readiness verdict
**Ready for the demonstration.** As of 28 Oct 2026 the backend (port 8000) and front end (port 5173) are running, `final_verify.py` passes 67 of 67 checks, the five-league simulator is live, the saved simulations and the Premier League forecast are intact, and the frozen model hashes match. Two things to remember on the day: the simulator's Run button saves a record (use 1,000 simulations, or the private-copy stack in checklist item 7), and the screenshots in section 6 have still to be captured by you from the running application.
