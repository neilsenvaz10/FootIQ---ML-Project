# Phase 4.30: final backend restart and live verification

One controlled restart of the backend on port 8000, then verification. No Git operation, no retraining, no import or provider, no cleanup, no code change, no archived-competition change. No simulation was saved to production by this phase (all simulation runs used a private copy).

## 1. Preflight
- Production database integrity ok. Its hash was **`1d6d2ebc2c0caaebcc7eae83d0e27f421a4bbd50bb8bb765b00cee1ad28d7f44`**, not the Phase 4.28 hash `410d9fe1...`. **Reason (not caused by this phase, a user-triggered save):** the database holds a third saved simulation, run 3: Premier League 2026-27, 10,000 simulations, seed 1901326415, created 2026-10-28 13:43:24 UTC through the **Run points-only simulation** button, i.e. you ran it in the live application shortly before this phase. That also shows the running backend already accepted the five-league scope (the configuration is read on each request).
- Everything else matched the verified Phase 4.28 backup: `matches` table identical, runs 1 and 2 identical (content hash `33fbf4af...`), the 30 forecast rows identical (Premier League Matchday 9, run 1 with 10 fixtures x 3 models), quarantine 273, five frozen model hashes true, Phase 4.28 backup hash `410d9fe1...` valid.
- Process check: one backend (process 28640, port 8000), no test, import or simulation running, no duplicate backend.
- Because the state differed from the last backup only by the legitimate run 3, I made one more verified backup before restarting: `data/backups/p430_pre_restart_20261028/` (hash `1d6d2ebc...`, SHA256.txt). This is a copy, not a cleanup.

## 2. Restart
- Stop: one Ctrl-C in the backend's terminal tab ("FootIQ backend"); it shut down cleanly ("Application shutdown complete"); port 8000 was free; the database was byte-identical after the stop.
- Start (same tab, visible foreground): `.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000 --timeout-graceful-shutdown 5`. Ready (`club_prediction_ready: true`) in about 21 s. One backend only.
- Port 8000 serves the updated configuration (section 4).

## 3. Startup synchronisation (authorised refresh; startup-only mode unchanged)
`sync_runs` 41: startup check, outcome ok, **2 requests** (Bundesliga 1, La Liga 1), snapshots reused, **0 inserted, 0 updated, 0 quarantined** (Bundesliga 243 unchanged / 63 confirmed; La Liga 263 unchanged / 99 confirmed / 18 already quarantined). Two further bookkeeping rows (42 and 43, outcome ok, 1 request each) and an updated `source_state`. Only `sync_runs` (40 to 43 rows) and `source_state` changed; no match, forecast or simulation row changed. This is why the hash is now `d8962089b30d2517a02bd4a5df364274dfa82c0c674743bd95dc2b9a04703809`. Configuration unchanged: `sync_mode: startup`, OpenLigaDB for BUNDESLIGA and LALIGA only.

## 4. Live simulation eligibility (GET on port 8000)
| League | State | Points-only button | Remaining | Missing results | Ranges |
|---|---|---|---|---|---|
| Premier League | ready | enabled | 300 | 0 | unavailable, reason shown |
| La Liga | ready | enabled | 281 | 1 | available |
| Bundesliga | ready | enabled | 243 | 0 | available |
| Serie A | **provisional** | enabled | 300 | 3 | unavailable, reason shown |
| Ligue 1 | ready | enabled | 234 | 0 | unavailable, reason shown |
Champions League: the status request is refused (HTTP 422), so it stays excluded. Final-position simulation: `can_simulate` false for all five, and a direct final-position request is refused ("outside the approved initial scope... no scoreline method has passed the predeclared acceptance criteria"). The unavailable-ranges reason: "position ranges are available for the Bundesliga and La Liga only: they need verified tie-break settings for the league, which the other leagues do not have yet".

## 5. Simulation verification (private database copy on ports 8001 / 5174, so production was not written)
API, 1,000 simulations, seed 430, all passed (club counts, remaining count, expected points between current + 2R and current + 3R, no finishing positions):

| League | Run time | Top club, expected points (10-90%) | Ranges |
|---|---|---|---|
| Premier League | 6.4 s | Arsenal 83.3 (75-91) | unavailable + reason |
| La Liga | 4.8 s | Barcelona 97.2 (91-103); title bound 0.901-0.908 | available |
| Bundesliga | 3.8 s | Bayern 86.0 (80-92); title bound 0.974-0.980 | available |
| Serie A (3 missing results) | 5.2 s | Inter 89.1 (81-97) | unavailable + reason |
| Ligue 1 | 3.5 s | Paris Saint-Germain 74.6 (67-82) | unavailable + reason |

Real UI (browser, private stack): the league list shows the five domestic leagues only; each league has 2026-27 as the only and selected season; the button is enabled for all five; a 1,000-simulation run completed for each and displayed "Expected final points" with the 10-90% column; the Serie A banner reads Provisional with "no verified result" and still ran; the position-range panel appeared for La Liga and Bundesliga and the "available for the Bundesliga and La Liga only" explanation for the other three; the Final positions tab is labelled disabled. The test stack was stopped afterwards.

## 6. Application verification (port 8000)
`final_verify.py`: **67 of 67 checks passed** after the restart: six dashboards, results, upcoming fixtures, standings (or league-phase table), team pages, predictions with labels (five leagues "Validated"), freshness indicators, saved simulations 1 and 2, archived competitions excluded (404 / 422), synchronisation startup-only. Champions League: 54 completed + 90 scheduled (144), prediction Arsenal v Dortmund 69.4 / 19.3 / 11.3 labelled "Not validated (indicative only)". Saved simulations 1 (Bundesliga, seed 1398654699), 2 (La Liga, 1499656622) and 3 (Premier League, 1901326415) retrievable; the Premier League Matchday 9 forecast run (10 fixtures, 30 rows) is listed in `/api/gameweek`.

## 7. Production integrity after the verification
Integrity ok, 0 foreign-key problems; `matches` unchanged; runs 1 and 2 identical to the Phase 4.28 backup; run 3 (yours) present; forecast rows identical; frozen model hashes all true; both backups intact; hash `d8962089...` (changed only by the startup refresh's `sync_runs` and `source_state` rows).

## 8. Remaining issues
1. Position ranges stay Bundesliga and La Liga only (no verified tie-break settings for the others).
2. Four competitions have no update source; 3 Serie A results unapplied, 1 La Liga postponement and 60 date corrections held.
3. `data/supervised/pytest_tmp/p429` (220 MB) still present (no cleanup was authorised in this phase).
4. Occasional slow shutdown (use the documented procedure); `scipy` missing from requirements files; `/worldcup` alias.
5. Uncommitted changes; the frontend dev server (5173) was left running as before.

## 9. Verdict
**Ready for the college demonstration.** The backend runs once on port 8000 with the five-league Season Simulator active; all five leagues simulate (Serie A with its provisional warning), the Champions League and final-position prediction remain excluded, the six-competition application passes 67 of 67 checks, and the saved simulations, forecast and frozen models are intact. Back up point if needed: `data/backups/p430_pre_restart_20261028/`.
