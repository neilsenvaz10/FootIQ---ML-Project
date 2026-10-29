# Startup-only data refresh (Phase 4.15): design, test results and migration procedure

Status: **implemented and tested on private copies; NOT applied to production.** The running backend (pid 6688) was not touched, `config/sync.json` is unchanged (still `periodic`), nothing was deleted, no Git operation, Bundesliga and La Liga keep syncing every six hours until you approve the migration.

## 1. Proposed simplified architecture
| | Today (periodic) | Proposed (startup) |
|---|---|---|
| When FootIQ refreshes | every 6 hours while the backend runs, forever | **once per backend launch**, a few seconds after the application is already serving |
| Background parts | Task Scheduler task, PowerShell supervisor, scheduler thread (always alive), scheduler lock held for the life of the backend, supervisor and backend logs | **only the backend.** A short-lived thread does the refresh and ends; the lock is released |
| Blocking | the check starts in its own thread | the same: `start()` returns at once; the refresh runs in a thread after `startup_delay_seconds` (5) |
| Duplicate refreshes | lock and per-league schedule | one refresh per launch; the frontend can never trigger one (no route calls the sync); a second backend started at the same moment refuses (lock); a relaunch within **15 minutes** of a league's last success skips that league |
| Provider down | league backs off 12/24 h | the refresh fails for that league only (no retry storm: one attempt per league, hard cap 3), local data is untouched, the app keeps working, the **next launch tries again** |
| What the user sees | "Scheduler: idle; next check ..." | "Sync: on, refreshes once each time FootIQ starts"; "Scheduler: startup refresh finished at ...: all leagues ok / errors in LALIGA"; per-league last successful check, last attempt, failed refreshes in a row and the **last error text**; "Next refresh: next time FootIQ starts" |
| Leagues | Bundesliga, La Liga | unchanged. PL/SA/FL1 stay in `PREPARED_PROVIDERS`, not in `APPROVED`: listing them in the config cannot make them run (tested) |

How it is built: one new setting, `sync_mode` (`"periodic"` is the default, so nothing changes until the config says `"startup"`), plus `startup_min_gap_minutes` (15). `SyncManager.start()` starts either the old loop or `_startup_once()`. `_startup_once` works out which leagues need asking (a league checked successfully less than the gap ago is skipped; a failed or never-checked one is always asked), calls the **same `check_once`** as before (same per-league isolation, same `_sync_openligadb`, same ingest), records the outcome, then releases the lock. Nothing in the reconciliation code changed.

## 2. Safeguards preserved (all exercised in `tests/test_startup_sync.py` on a private copy)
Team identity matching (same resolver); duplicate prevention (never two rows for a match, tested after repeated launches); score conflicts and date disputes quarantined and never applied (tested with a changed score and a moved date); provenance (`match_sources`, snapshot hash and URL); snapshot de-duplication (an identical launch stores no new file or row); API limits (one request per league per launch, cap 3 attempts, 15-minute gap, 3-second pause); integrity (`PRAGMA integrity_check` after a refresh, whole-table hashes unchanged after a failed one); frozen models and saved forecasts (not touched by any code path here; saved forecasts still 0).

## 3. Files
Modified: `app/store/sync.py` (new settings, `_startup_once`, `_startup_targets`, status additions `mode` / `sync_mode` / per-league `last_error`, `describe_startup`; plus `FOOTIQ_SYNC_CONFIG` to read a private config file in trials and a byte-order-mark-tolerant config reader); `app/main.py` (the status endpoint reports this launch's startup state); `app/store/daily_audit.py` (startup mode expects no scheduler thread and judges freshness against the 72-hour staleness limit, not 13 hours; a stopped backend is information, not an alert); `frontend/src/components/SyncStatus.jsx` (wording, last error, "next launch").
New: `tests/test_startup_sync.py` (15 tests), one frontend test, trial scripts under `data/supervised/phase4/p415/`.
Not modified: `config/sync.json`, `scripts/ops/footiq_service.ps1` (kept as an optional tool), the Windows task, the models, adapters, schema, any data.

## 4. Test results
- Backend, targeted: **131 passed** (startup 15, scheduler, monitoring, La Liga, EPL, football-data, full-season, provenance, baseline hash). Frontend: **347 passed, 13 skipped** (including the new startup-mode panel test).
- Startup tests cover: one request per league then nothing in the background (thread ends, lock free, no `tick`/`next_due`); start returns while the provider is still blocked; frontend reloads trigger nothing (status calls plus a static check that no route calls the sync); restart inside the gap asks nothing and a later launch asks again; only a failed league is asked again; API down for both or one league (data untouched, error visible, other league completes, a later success clears the error); a crash inside the refresh is contained and releases the lock; conflicts, disputes, provenance, snapshot de-duplication; only Bundesliga and La Liga can be requested even if EPL/SA/FL1 are listed; off or `FOOTIQ_DISABLE_SYNC=1` starts nothing; a simultaneous second backend does not refresh; the shipped config and periodic mode are unchanged; the audit in startup mode.
- **Private end-to-end trial** (`private_launch_trial.ps1`; port 8124, private copy, private config with a long gap so no request is made): plain `uvicorn` launch healthy in **3 s**; status "startup refresh skipped: every league was refreshed less than ... minutes ago"; **0** scheduler threads, lock released, no next scheduled check; ten reloads changed nothing (`sync_runs` 14 to 14, provider ledger 7 to 7); a supervisor adopted that backend and, after the stop flag, **exited in about 12 s while the backend kept answering**. Production database hash, config hash, listener (6688) and supervisor were unchanged.
- One trial error was my own: PowerShell wrote the private config with a byte-order mark and the loader failed; the loader now accepts it.

## 5. Safe migration procedure (nothing below has been run; each step needs your approval)
Preparation: pick a moment when you are happy for the backend to be down for about ten seconds.
1. **Back up the config:** copy `config/sync.json` to `data/backups/sync.json.<date>`. (The database is not changed by this migration; the existing backups remain.)
2. **Edit `config/sync.json`:** add `"sync_mode": "startup"` (optionally `"startup_min_gap_minutes": 15`). `live_enabled`, `openligadb` leagues and the disabled `footballdata` block stay as they are. The running backend does not read the file again, so nothing changes yet.
3. **Retire the supervisor without touching the backend:** `Disable-ScheduledTask -TaskName FootIQ-Backend` (stops it re-launching at log-on; a running instance keeps running) and create `data\run\stop-8000.flag`; the supervisor, which only *adopts* the backend, exits within about 15 s and leaves it running (verified on the private port; check the same on production with `footiq_service.ps1 status`: "Supervisor NOT running, backend answering"). Remove the stop flag if one remains.
4. **One restart onto the new code (the only interruption):** stop the old backend (process tree of pid 6688), then start it the simple way from the project folder: `.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000`. It serves immediately; five seconds later it makes **one** refresh attempt (at most one request per league, none if a league succeeded within 15 minutes).
5. **Verify:** `/api/sync/status` shows `sync_mode: startup`, startup state `done` (or `skipped_recent`), 0 scheduler threads after the refresh, lock released, the provider ledger grew by at most 2 lines; `footiq_service.ps1 audit` (or `.venv\Scripts\python.exe app\store\daily_audit.py`) passes; the status panel reads "refreshes once each time FootIQ starts"; no new open findings besides any real ones.
6. **Optional, later:** `task-remove -Apply` removes the Windows task (reversible with `task-install -Apply`); the scripts stay in the repository, nothing is deleted. Update `docs/mini-project/final/SETUP_AND_RUN.md` to say "launching the backend refreshes the data once".
**Rollback:** remove the `sync_mode` line (or set `"periodic"`), `Enable-ScheduledTask FootIQ-Backend`, restart the backend; the six-hour scheduler is back. No data is involved either way.
**Daily workflow afterwards:** start the backend and the frontend (`npm run dev` in `frontend/`) as the README says; the data refreshes itself once; read the status panel for the last refresh time and any error.

## 6. Expected reduction
| | Periodic | Startup |
|---|---|---|
| Windows pieces to maintain | task, supervisor script, mutex, pid and stop files, supervisor log, liveness watcher | none required (script kept, optional) |
| Background threads | 1 scheduler thread alive for as long as the backend runs | 0 after the first seconds |
| Scheduler lock | held permanently | held for the few seconds of the refresh |
| Provider requests | 2 leagues x 4 a day = **8 a day** (up to 3 attempts each on failure), every day, whether or not anyone uses the app | **at most 2 per launch**, and at most 2 per 15 minutes; about **2 to 4 a day** for one or two launches |
| Logs | supervisor log, a backend stdout/stderr file pair per start, liveness log | the backend's own console only; no per-launch backup, no per-launch snapshot (identical responses reuse the last one), one cycle row and one row per league in `sync_runs` |
| Ways for sync to silently stop (supervisor killed, task not restarting) | present (Phase 4.14) | none: nothing runs in the background to stop |

## 6b. Evidence from this very session: why the periodic design is fragile on a laptop
The machine slept from about 19:15Z to 01:25Z (a 371-minute gap in the liveness log, matching the Kernel-Power sleep/resume events). The production scheduler's 23:00:36Z check did **not** run at wake-up: at 01:45Z the status still read "check overdue (was due 2026-10-27T23:00:36Z)", 0 failures, no request in the ledger. The scheduler thread sleeps on an in-process timer that does not count the time the computer was asleep, so after a night's sleep it waits out the remainder instead of checking at once. Nothing is broken and it will run later; it simply shows that a six-hour schedule on a machine that sleeps is unreliable, and that "refresh when FootIQ is launched" matches how the project is actually used. (I did not change the production scheduler for this; the migration retires it.)

## 7. Remaining risks and notes
- **Staleness is by design:** a backend left running for days does not refresh; the panel shows the last refresh and turns a league "stale" after 72 hours.
- **No manual "refresh now" button** (not requested; could be added later behind the same lock and gap).
- The Task Scheduler task stays installed until you choose to remove it; disabling it is enough.
- The date-dispute and permission blockers for PL/SA/FL1 are unchanged; this change does not affect them.
