# Phase 4.8B Checkpoint Report: Offline Implementation and Safety Rehearsal

Date: 2026-10-27. Scope: offline only. **No network request was made, live synchronisation stayed off (`live_enabled: false`), nothing was imported into production, no model, saved forecast or prospective record was touched, nothing was staged or committed (HEAD `970f461`), Phase 4.8C was not started.**
Evidence folder: `data/supervised/phase4/p48b/` (scripts and JSON), logs `data/supervised/phase4/p48b_backend_pytest.log`, `p48b_build.log`, `p48b/integrity_final.json`.

## 0. Corrections to my own earlier statements (found while investigating)

| Earlier statement | What the evidence shows | Where I said it |
|---|---|---|
| Phase 4.7: the 2026-10-27 backend start "switched the file to WAL mode" | **Wrong.** The production file was already in WAL mode (header version bytes = 2; a copy taken after the 2026-10-25 import is WAL too). Every writable `db.connect` call sets WAL, so the import tools did it on 2026-10-25. Only one `sync_runs` row and a WAL checkpoint changed the bytes | `TESTING_REPORT.md`, `LIMITATIONS.md`, `DATA_SOURCES.md`, `SETUP_AND_RUN.md`, `PROJECT_REPORT.md`, `SUBMISSION_CHECKLIST.md` (all six corrected in this phase) |
| Phase 4.8A table: Premier League and La Liga "older… not approved for production" | **Wrong.** Their OpenLigaDB snapshots *were* imported into production on 2026-10-25 (30 new results, 5 aliases, 586 kickoff times, runs 6 and 7 of `sync_runs`; `PRODUCTION_IMPORT_REPORT.md`). What is *not* approved is any **live** source for them | `P4_8_AUTOMATIC_REFRESH_PLAN.md` §2 and §3 (the plan file is left as written; this report supersedes those two rows) |

## 1. Exact files changed

**New (backend):** `app/kickoff.py` (the one kickoff rule), `tests/test_sync_scheduler.py` (10 tests), `tests/test_refresh_integration.py` (8 tests).
**Modified (backend):** `app/store/db.py`, `app/store/sync.py`, `app/gameweeks.py`, `app/forecast.py`, `app/predict.py`, `app/featured.py`, `app/matches.py`, `app/main.py`, `config/sync.json` (`periodic_minutes` 60 → 360 only), `tests/test_store.py` (one test updated to the new rule), `tests/test_gameweeks.py` (+5 tests, one test's clock adjusted), `tests/test_featured.py` (parity test given the same clock, +1 test).
**Modified (frontend, label only):** `frontend/src/components/FixtureCard.jsx` ("Awaiting verified result"), `frontend/src/pages/GameweekPredict.jsx` (empty-state sentence), `frontend/tests/gameweek.test.jsx`.
**Tools and evidence (untracked, `data/supervised/phase4/`):** `phase4_integrity.py` (expected-differences list extended), `p48b/db_startup_audit.py`, `db_logical_hash.py`, `offline_rehearsal.py`, `refresh_effect_demo.py` and their JSON outputs.
**Documents corrected:** six files in `docs/mini-project/final/` (section 0). Their test counts (260 / 342 / 355) still describe the Phase 4.7 state; I did not renumber them (decision 8 in §14).
**Not touched:** frozen model files, `config/season_sim.json`, prospective-evaluation files, `data/footiq.sqlite`, historical CSVs, adapters.

## 2. Database startup-write investigation

**Question:** why does the production hash differ from the recorded baseline, and is it only expected metadata?

| Evidence (all from private copies; the production file was only read) | Result |
|---|---|
| Recorded post-import SHA-256 | `39ab9651…61f3` |
| Current SHA-256 | `3641e4da…3922` (unchanged throughout this phase) |
| Table-by-table comparison of production against a copy taken after the import (`preview.sqlite`, 2026-10-27 14:26, before the 10:37 UTC start wrote row 8) | **13 of 14 tables identical** (matches 223,510 rows, match_sources 224,519, quarantine 273, team_aliases 7,447, teams, competitions, source_snapshots 9, source_state, forecast tables empty, …). Only `sync_runs` differs |
| `sync_runs` | production rows 1–7 equal the copy's rows 1–7; production has one extra row: id 8, `startup_check`, `skipped_live_disabled`, 2026-10-27T10:37:37Z |
| Newest `matches.last_changed_utc` | `2026-10-25T09:07:13Z`, the import time: no match was modified afterwards |
| `PRAGMA integrity_check`, journal mode | `ok`, `wal` (already WAL since the import) |
| Header | change counter 6, page count 55,824 (same as the post-import copy) |
| Why the bytes changed | the row insert, then a WAL checkpoint into the main file when the last connection closed. Reproduced by running the old start-up statements on a private copy: main-file SHA changed (`3641e4da…` → `e3b9fc1e…`) and a row was added |

**Cause in code (before):** `SyncManager.check_once` always opened a writable connection and inserted a `sync_runs` row, even with `live_enabled` false; the loop repeated that hourly. `db.connect` ran `PRAGMA journal_mode=WAL` on every writable connection.

**Connection audit** (every `store_db.connect` site): every read-only site uses `mode=ro` (analytics, predict, the API endpoints, the season-simulation read paths and the research scripts): they cannot modify the file; on a WAL database they may create *empty* `-wal`/`-shm` files if none exist (observed, main file unchanged). Writable sites: explicit user actions only (`forecast.predict_gameweek`, season-simulation save), the live sync path, and the build/import tools.

**Fixes (4.8B):** (a) `check_once` and `tick` return `skipped_live_disabled` before opening any connection; (b) `start()` creates no thread when live access is off; (c) `db.connect` asks for the journal mode first and sets WAL only if it is not already WAL.

**Repeated cold starts (private copy of production, real uvicorn, 3 starts, 7 read endpoints each, 12 s idle past the 5 s start-up delay, clean stop):** main-file SHA before = after for all three (`3641e4da47b3`), `sync_runs` added 0, every endpoint HTTP 200, ready in 34–37 s; sidecars `-wal` 0 bytes and `-shm` 32,768 bytes (as already beside the production file). Production file unchanged by the audit. (`p48b/db_startup_audit.json`)

**Logical baseline.** `db_logical_hash.py` hashes every table and excludes only `sync_runs` rows after the import (id > 7). Production and the post-import copy give the same value: `b182836f2a2b1e18fb71890511c60dde9b08790ccbdaa34b7a951aefb54bf81e`.

**Recommended baseline decision (yours to take; I changed nothing):**
1. Do **not** restore an older file: none with the old bytes survives, the difference is one log row, and restoring would only create new bytes.
2. Do **not** accept the new hash "blindly": accept it **with its explanation**: record two values, the *byte* hash `3641e4da…3922` (current, now stable across starts) and the *logical* hash `b182836f…bf81e`. Future integrity checks should compare the logical hash for content and the byte hash for "nothing wrote".
3. Row 8 may stay: it is a true record of a start-up check. Deleting it would be a production write that I was not authorised to do.

## 3. Before / after scheduler behaviour

| | Before 4.8B | After 4.8B |
|---|---|---|
| Live off, backend start | thread starts; after 5 s a writable connection inserts and updates a `sync_runs` row; WAL checkpoint changes the file | no thread, no connection, no write |
| Live off, every hour | another row (the 11-row preview copy shows rows at 07:36, 08:36, 08:51, 08:56 UTC) | nothing |
| Interval | `periodic_minutes` 60, floor 60 s | 360 (6 h), floor 30 min so a bad value cannot hammer a provider |
| Restart | check on every start | check only if due (last attempt + interval); a restart inside the interval makes no request and no row |
| Failure | next check after the normal interval | back-off ×2 then ×4 (6 h → 12 h → 24 h cap); success resets |
| Two runners | in-process lock only | plus a store-level lock: a `running` row younger than 30 min blocks a second run; an older one is marked `abandoned` |
| Leagues | `APPROVED` has Bundesliga only | unchanged; a config edit cannot add a league |

## 4. Six-hour refresh design (implemented and tested offline; switched off)

`SyncManager.tick(kind)`: if live is off → inert. Else `next_due()` reads the newest check row from `sync_runs` read-only: none → due now; else `started_utc + 6 h × backoff`. `tick` runs `check_once` only when due. The loop sleeps until the due time (at least 60 s, at most one period) and stops promptly on shutdown. The existing source path (`_sync_openligadb`: snapshot, request ledger, adapter safeguards, one-transaction ingest, quarantine) is reused unchanged. Mocked-clock tests cover: first check, not due at 5 h 59 min, due at 6 h, restart inside the interval, failure back-off 12 h / 24 h / cap / reset, run lock, abandoned lock, interval floor, shipped config (6 h, live off). No scheduler was activated and no request was made.

## 5. Per-league readiness (also exposed as `provider_readiness` in `/api/sync/status`)

| League | Newest stored result | Awaiting result | Provider status | Production ingestion |
|---|---|---|---|---|
| Bundesliga | 2026-10-24 | 0 | `approved_live_disabled` (OpenLigaDB) | live off; one-time import done 2026-10-25 |
| Premier League | 2026-10-12 | 15 | `prepared_offline` | snapshot imported once on 2026-10-25; no live source approved; snapshot replay is idempotent (§10) |
| La Liga | 2026-10-21 | 1 | `prepared_offline` | same; 5 matchday-10 results still held (date disagreements) |
| Serie A | 2026-09-20 | 20 | `blocked_no_provider` | nothing |
| Ligue 1 | 2026-09-20 | 18 | `blocked_no_provider` | nothing |

Serie A and Ligue 1: from the repository's offline review (`FOOTBALL_DATA_ORG_CHECKLIST.md`, 2026-10-26) the free tier lists both, with delayed scores and 10 calls/minute, an account and key are required, attribution wording is prescribed, terms dated 2018 leave storing/redistribution unclear, and the covered seasons are unknown until an account exists. **I did not go online.** Reading the current terms requires your separate authorisation. No account, key or provider was created or activated.

## 6. Alias verification

Re-run on a copy of the **pre-import** backup, using the saved snapshots (`offline_rehearsal.py`): all five proposals pass every check — entity exists in `teams`; is a 2026-27 member of the competition; was seen in that competition before; was unresolved before the alias; is not the forbidden fuzzy target (Brentford ≠ Arsenal); is not already used by another source name; is among the unmatched store teams; and all 38 source fixtures pair with exactly one stored fixture with the same matchday.

| Source name | Canonical entity | Passes | In production now |
|---|---|---|---|
| Brentford F.C. | `CLUB:ENG:brentford-fc` (Brentford FC) | yes | yes, same entity |
| Celta Vigo | `CLUB:ESP:rc-celta-vigo` (RC Celta de Vigo) | yes | yes |
| Deportivo A Coruña | `CLUB:ESP:rcd-la-coruna` (RC Deportivo La Coruña) | yes | yes |
| FC Villareal (typo in source) | `CLUB:ESP:villarreal-cf` (Villarreal CF) | yes | yes |
| Racing Santander | `CLUB:ESP:real-racing-santander` (Real Racing Club de Santander) | yes | yes |

Notes: your texts "Deportivo de La Coruña" and "Racing de Santander" are not stored names; the mapping is by entity id and fixture structure, not by those spellings. **Reproduction check:** aliases + snapshot replay on the pre-import copy yields `matches` (223,510), `quarantine` (273), `team_aliases` (7,447) and `match_sources` (224,519) **identical** to production. They remain "proposed and verified"; production already holds them from the 2026-10-25 import you approved.

## 7. Unresolved score and fixture conflicts (preserved)

| Item | Stored | Source | State |
|---|---|---|---|
| AFC Bournemouth v Brentford FC, 2026-09-12 | 2-2 (openfootball) | 2-1 (OpenLigaDB) | `CONFLICT`, quarantined, stored score unchanged (verified again: 2-2) |
| Aston Villa v Nottingham Forest | 1-2 | source holds several differing final scores | `CONTRADICTORY SOURCE RESULT`, not imported, stored score unchanged (1-2) |
| Date disagreements | 55 fixtures (31 Premier League, 24 La Liga by the earlier findings) | | quarantined as `DATE_DIFFERENCE`; stored dates, kickoffs and matchdays held; completed source results for them are held back |

Replaying all snapshots again on a copy of production: 0 inserted, 0 updated, quarantine and match tables identical, no second finding written. An official record or a second independent provider is still needed to resolve the two scores.

## 8. Recent-form model audit (no model trained or changed)

| Question | Finding | Evidence |
|---|---|---|
| Do v1 / v2-r1 use recent verified results? | Yes. v1: Elo plus points, goals for/against over the last 5 and 10 **rated** matches, venue form, rest days. v2-r1 adds opponent-adjusted performance and counts of known results in the last 7/14/30 days | `feature_contract.py`, v2 feature contract |
| Are the form windows and Elo computed correctly? | Yes. For a real Bundesliga fixture, `n_prior`, `ppg5` and `ppg10` equal an independent recomputation from the stored rated results (strictly before the fixture's day) for both teams | `test_form_and_elo_features_equal_an_independent_calculation…` |
| Are missing results ever a loss or a draw? | No. A missing result is absent; windows reach further back. A team with no history has `n_prior` 0 and `ppg5` = NaN, not 0. `form` lists never contain a null score | same test; `test_recent_form_and_head_to_head…` |
| Is the frozen schema preserved? | Yes. Every column of the v2 contract is still produced; no column added; v2 `n_known` gap counters present | `test_the_v2_gap_counters…` |
| Chronological cutoff / leakage? | Results on or after the fixture's day never reach a forecast (existing tests re-run and passing) | `test_later_or_same_day_results_never_change_a_forecast` |
| Do refreshed results move new predictions and leave saved ones alone? | Yes. Bundesliga matchday 8 forecast as of 2026-10-19 (cutoff 2026-10-18) and again as of 2026-10-25 after the refresh (cutoff 2026-10-24): teams that played gain exactly +1 prior match; Elo and `ppg5` move; probabilities move by up to **2.8 percentage points**; the first run's 27 saved rows (9 fixtures × 3 model variants) are byte-for-byte unchanged and both runs are kept | `refresh_effect_demo.json`, `test_new_results_move_the_prediction_inputs…` |

Example from that run (real data, a model output, not a claim of accuracy): Borussia Mönchengladbach v SC Paderborn: home `ppg5` 0.0 → 0.6 and Elo 1612 → 1629 after one more result; club v1 home/draw/away 39.4/23.0/37.6% → 39.0/24.1/36.9%. Even with zero points in five games the home side keeps ≈39%: form is one input among Elo and home advantage.

**Adequacy.** The evidence shows the inputs respond correctly. I found no defect in how recent results enter, so **I propose nothing now**. Adding streak penalties or team adjustments is excluded. If a later *prospective* check shows systematic under-reaction (for example, calibration by recent-form band worse than Elo-only), the separate experimental model of the 4.8A plan (named, separately hashed, evaluated with predeclared criteria) would be the route; that needs your approval.

## 9. Past-fixture prediction safeguards

One rule, `app/kickoff.py`: a new pre-match prediction is allowed only when `made_before_kickoff == "yes"` — stated UTC kickoff still ahead, or (no time known) the date has not started anywhere on Earth (before 00:00 in UTC+14). Equality counts as passed. `"unknown"` (date possibly under way) is treated as **blocked**.

| Workflow | Behaviour now |
|---|---|
| Gameweek forecast (`POST /api/gameweek/predict`) | only fixtures with state "yes" are forecast; others are listed in `skipped`; if none can be forecast → 422 with a clear message; nothing is saved for blocked fixtures (not even a flagged forecast, which the old code allowed) |
| Gameweek page (`/api/gameweek`, `/api/gameweeks`) | such fixtures show `status: awaiting_result` ("Awaiting verified result"), `kickoff_state`, `predictable: false` and the reason; counts use the same rule; real clock used by the endpoints |
| Manual head-to-head (`/api/predict`) | if the pair matches a stored unplayed fixture on that date whose kickoff has passed or cannot be shown to be ahead → refused (422, "Awaiting verified result…"); a pairing with no stored fixture on a past date gets the note "hypothetical matchup, not a forecast of a scheduled match" |
| Home and Matches (`eligibility.predictable`) | use the same rule, so they never offer what the forecast would refuse |
| Saved forecasts | still returned with the fixture (creation time, data cutoff, made-before-kickoff, models); never recalculated or overwritten (test: forecasts table identical after the kickoff passed and after a refused run) |

Boundary tests (to the second): 14:59:59 yes, 15:00:00 no for a 15:00Z kickoff; 09:59:59 yes / 10:00:00 unknown for a date-only fixture on the following day; 12:00:01 after the date's end → no. **Consequence to be aware of:** a date-only fixture becomes non-predictable from 10:00 UTC the day before. Fixtures with a stored UTC kickoff are unaffected until kickoff. This is deliberately conservative; relaxing it is a decision for you.

## 10. Offline rehearsal and integration results

| Check | Result |
|---|---|
| Snapshot replay onto the pre-import copy reproduces production's `matches`, `quarantine`, `team_aliases`, `match_sources` | identical (row counts and content hashes) |
| Replay onto a production copy (EPL, La Liga) | EPL 0 inserted / 0 updated / 289 unchanged / 58 confirmed / 33 quarantined; La Liga 0 / 0 / 267 / 89 / 24; tables identical afterwards |
| Standings after a safe Bundesliga import (state A → B, 7 results added) | the table equals an independent count from stored results for every team; points moved by exactly what the new results are worth; total games +2 per result |
| Recent form and head-to-head | the newest result is the last form entry; head-to-head meetings +1 |
| Matches hub and gameweek page | new results appear under Completed and no longer under Awaiting/Upcoming |
| Team comparison | uses the updated history (above) |
| Prediction inputs | only results before the fixture's day; see §8 |
| Simulation compatibility | points-only simulation (1,000 runs, private copy) runs on the refreshed data, cutoff 2026-10-24; the source copy has 0 simulation rows; final-position simulation remains disabled |
| Warnings preserved | Premier League fixture flags (`stale_history`, missing results) identical before and after the Bundesliga refresh; EPL, La Liga, Serie A and Ligue 1 stay "stale / no approved fresh source" |

## 11. Test results (all executed in this phase)

| Suite | Command | Result |
|---|---|---|
| Backend, full | `.venv\Scripts\python.exe -B -X utf8 -m pytest tests -q -p no:cacheprovider` | **284 passed, 0 failed, 1 warning** (the existing Starlette/httpx notice) in 16 min 42 s. 260 earlier + 24 new (10 scheduler, 5 past-fixture, 8 integration, 1 Home safeguard) |
| Frontend, no backend | `npx vitest run` | **342 passed, 13 skipped** (same as Phase 4.7) |
| Frontend, live backend on a private store copy | `FOOTIQ_LIVE_API=http://127.0.0.1:8000 npx vitest run --no-file-parallelism` | **355 passed, 0 failed, 0 skipped** |
| Production build | `npm run build` | succeeded, 648 modules |
| Cold starts | `db_startup_audit.py 3` | 3/3 ready, files unchanged (§2) |

Three existing tests had to change because they asserted the old behaviour, which was the request: `test_store` (a disabled sync now writes no row), `test_gameweeks` chronology test (it forecast a back-dated fixture "now"; it now uses a clock before that date), `test_featured` parity test (compared two pages at different clocks; both now use the same one). No test was deleted or loosened otherwise. The 13 skipped frontend tests are the live-API contract tests described in Phase 4.7; they pass with a backend.

## 12. Production integrity verification

`phase4_integrity.py check` (`p48b/integrity_final.json`): frozen model files and the prospective-evaluation files in the manifest unchanged; only two protected differences, both explained — `config/sync.json` (your approved 6 h interval) and `data/footiq.sqlite` (the pre-existing row-8 difference, bytes stable since); the backend-source differences are exactly the expected list; `PRAGMA integrity_check` ok; `simulation_runs` 0; `live_enabled` false; `scoreline_method` null; nothing staged, HEAD unchanged. Production byte hash before and after this phase: `3641e4da…3922`; main-file modified time still 2026-10-27 16:07 (the `-shm` file's timestamp moves whenever any process opens the database read-only). All private copies I made were deleted.

## 13. Remaining blockers

1. Baseline decision (§2). 2. No live source for Serie A / Ligue 1; reading the current football-data.org terms needs your authorisation; no key exists. 3. A real contact string for the adapter is not configured (live stays impossible, as designed). 4. Premier League / La Liga live refresh needs approved providers; 5 La Liga results are still held for date disagreements. 5. The two score conflicts need an official record. 6. The live path has never run against the real network in this phase (by instruction); the mocked-clock and recorded-snapshot tests are the only evidence. 7. Freshness counts the 2026-10-25 *offline* import as a "successful sync" (Bundesliga shows "fresh" until 72 h pass); intended earlier, but worth a decision. 8. The 4.7 documents' test counts are stale.

## 14. Decisions required for Phase 4.8C

1. Adopt the two-value baseline (byte + logical) from §2, or choose another remedy.
2. Approve 4.8C (UI): freshness line ("last checked / next check"), per-league readiness, quarantined-items count, form-window fields on forecast cards.
3. Is the conservative "date-only fixture blocked from the day before 10:00 UTC" rule acceptable, or should unknown kickoffs be allowed until 00:00 UTC of the match date?
4. Should offline imports keep counting as a "successful sync" for freshness?
5. Provider approvals; authorise (or not) reading the football-data.org terms online.
6. Resolution rule for the two score conflicts and the 55 date disagreements.
7. Whether you ever want the form-extended experimental model (my view: not now).
8. Refresh the numbers in the `final/` documents after 4.8C, or now.

---

## What We Did, Problems Faced, and How We Solved Them — Explained Simply

**The problem we found.** Our app has a "robot" that is supposed to check for new results. We had switched the robot *off* so the app never goes on the internet. But every time the app started, the robot still walked into the database and wrote one line in its diary: "I did not check, because I am off". That is like a night guard who is told not to patrol, yet signs the logbook every hour. The signature changed the database file, so the fingerprint (hash) we had saved no longer matched. We worried the football data had changed.

**How we checked.** We made a private photocopy of the database and compared it, table by table, with a photocopy taken just after the real import. Thirteen tables were identical. Only the diary table had one extra line. So no match, score or team had changed. We also found that I had earlier said the file was "switched to a different mode"; that was wrong, it was already in that mode, and I corrected my own documents.

**How we fixed it.** Now, if the robot is off, it does nothing at all: it does not even open the database. We started the app three times on a copy and the fingerprint never moved. When the robot is eventually turned on, it follows a calendar: one check every 6 hours, but not again if the app is only restarted, and it waits longer after failures (6 h, then 12 h, then 24 h). If a second robot tries to run at the same time, a "do not disturb" sign stops it.

**Matches that have already kicked off.** Imagine a match started at 3 pm and it is now 4 pm. The result is not in our database yet. It would be unfair to predict it "before the game" now. So the app says **"Awaiting verified result"** and refuses to create a new prediction. A prediction saved earlier stays exactly as it was, with the time it was made and the date of the newest result it knew about. If we do not know the kickoff time, we assume the worst: the match might already have started.

**Proving that new results really help.** We loaded the real Bundesliga results up to 24 October into a copy and asked: do the predictions change? Yes. Borussia Mönchengladbach had 0 points from its last five games in the old data and 0.6 after one more result. The home-win chance moved from 39.4% to 39.0%, a small change, because the model also weighs team strength and home advantage. An old saved prediction did not change by a single digit. And a team with no data is never treated as "lost every game"; it simply has no form number.

**Team names.** The other database spells "Celta Vigo" differently from ours. We checked five name links against the clubs' IDs, their fixture lists and their league seasons. All five were right, and they were already in the production database. Two score disagreements (Bournemouth–Brentford and Villa–Forest) stay locked until a second reliable source confirms the true score. We never pick a winner between two scores by guessing.

**What we did not do.** We did not go on the internet, did not create accounts or keys, did not change the real database, and did not touch the models.

**30–60 second viva summary.** "Our sync robot was switched off but still wrote a log line into the production database at every start, which changed its file hash. We proved by table-by-table comparison on private copies that no football data changed, then fixed the code so a disabled sync writes nothing, and verified it with repeated cold starts. We reused the existing scheduler, set it to a 6-hour interval with back-off and a run lock, and tested it with a mocked clock and saved snapshots, with live access still off. We added one conservative kickoff rule so a match that has started never gets a new pre-match prediction, while old predictions stay unchanged. We showed that newly imported results change the next predictions through form and Elo, and never treat missing results as losses. Conflicting scores and date disagreements stay quarantined for human review. The models stayed frozen."
