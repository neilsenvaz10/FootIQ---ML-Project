# Bundesliga unattended synchronisation: activation checklist (NOT YET ACTIVATED)

Nothing below has been done. `live_enabled` is false. Each step needs the operator's go-ahead on the day.

## 0. Preconditions (already true)
Full-season refresh (1 GET per 6-hour cycle, at most 3 attempts, `max_retries` 2); byte-identical answers reuse the latest verified snapshot; malformed or contradictory answers are rejected before saving and not retried; back-off 12/24 h; locking and restart rules; quiet start with sync off; status panel with scheduler state, failed cycles and quarantine warning; baseline monitor; the 3-cycle real-network trial passed.

## 1. Backup and restore (first)
1. Stop the API.
2. Back up with SQLite's online-backup API from a read-only connection to `data/backups/footiq.<UTC>.pre-activation.sqlite` (the pattern used by `app/store/import_p48d_stage1.py`).
3. `python app/store/baseline_hash.py <backup> 10` must equal the baseline v3 logical hash; `PRAGMA integrity_check` ok.
4. Restore test: copy the backup elsewhere, open it, count matches, compare the logical hash.

## 2. Production baseline verification
`python data/supervised/phase4/phase4_integrity.py check`: baseline v3 physical and logical `true`, `integrity_check` ok, nothing staged. `python app/store/baseline_monitor.py report data/footiq.sqlite`: `NO_CHANGE` (checkpoint 1 is baseline v3).

## 3. Configuration (the only edit)
`config/sync.json`: `"live_enabled": true`. Keep `periodic_minutes` 360, `max_retries` 2, `startup_check` true, competitions `["BUNDESLIGA"]`, default `refresh_mode`. `config/contact.local` present (never committed). Add no other league.

## 4. API restart and first supervised production cycle
1. Start the API. It is restart-aware: the first check runs about 5 seconds after start only if the last real attempt is older than six hours.
2. Watch `/api/sync/status`: `scheduler.status` goes "running a check now", then "idle; next check …".
3. Expect 1 request, HTTP 200, `last_successful_external_check_utc` set, and "returned no new results" or the new verified results.
4. Run the baseline monitor report: `EXPECTED_LOG_ONLY` (nothing new) or `IMPORT_EXPLAINED` (new results); never `UNEXPECTED`.
5. If `IMPORT_EXPLAINED`, read the changed rows, then `approve --label "first production cycle" --by <name>`.

## 5. Monitoring
Daily: `python app/store/baseline_monitor.py report data/footiq.sqlite` (writes `data/supervised/phase4/baselines/reports/<date>.json`); the status panel's scheduler line, failed-cycle count, last-check summary and quarantine warning; `data/snapshots/request_ledger.jsonl` (about four lines a day). Review quarantine per `QUARANTINE_REVIEW_PROCEDURE.md`.

## 6. Rollback
1. Set `"live_enabled": false` and restart the API: the scheduler is inert again (no thread, no writes).
2. If data are in doubt: stop the API, replace `data/footiq.sqlite` with the pre-activation backup (remove stale `-wal`/`-shm`), verify the logical hash equals baseline v3, restart.
3. Note it in the report. Checkpoints are append-only, so v3 and later checkpoints stay available.

## 7. Failure escalation
| Signal | Action |
|---|---|
| `consecutive_failed_cycles` 1 | none; back-off 12 h |
| 2 or more (back-off 24 h) | operator checks the provider's site and the request ledger; no manual retries |
| 3 or more, or `UNEXPECTED` in the daily report | switch sync off (step 6.1), keep the evidence, investigate on a private copy |
| quarantine warning above zero | review per the procedure; never resolve through the scheduler |
| `integrity_check` not ok | stop the API, restore the backup (step 6.2) |

---

## Status after activation (Phase 4.8E, 2026-10-27)

* **Active:** Bundesliga only, `config/sync.json` `live_enabled: true`, every 360 minutes, `max_retries` 2 (hard cap 3 attempts), `refresh_mode` full_season, one scheduler thread inside the API process (shown in `/api/sync/status` → `scheduler.active_scheduler_threads`). The scheduler lives **inside the API process**: it only runs while the API is running, and a restart does not cause an early request (restart-aware).
* **Baseline:** checkpoint 2 (physical `2f5126ef…2f67`, logical `28902313…5706`, cut-off run 12) is the current reference; checkpoint 1 (baseline v3) and all backups are preserved. Future checkpoints are approved by a person only (`baseline_monitor.py approve`), never automatically.
* **Daily audit owner: the project owner** (assigned 2026-10-27, recorded in `config/operations.json`). Daily: `powershell -File scripts/ops/footiq_service.ps1 audit` (read-only; it never approves anything) and read the status panel's quarantine warning.
* **Throw-away backends and tests** must set `FOOTIQ_DISABLE_SYNC=1` (the test suite does this in `tests/conftest.py`); otherwise a backend started on a copy with the shipped config would schedule real requests.

### Disable immediately (unexpected changes, an `UNEXPECTED` report, a failed integrity check, or any doubt)
1. Edit `config/sync.json`: `"live_enabled": false`.
2. Stop and restart the API (the scheduler thread is not started when sync is off; verify `scheduler.active_scheduler_threads` is 0 and `scheduler.status` starts with "off").
3. Optional hard stop without editing: start the API with the environment variable `FOOTIQ_DISABLE_SYNC=1`.
4. Keep the evidence (`data/snapshots/request_ledger.jsonl`, the latest `baselines/reports/*.json`); do not delete rows; restore a backup only after a verified failure and with the owner's approval (section 6).


---

## Persistent running (Phase 4.8F): prepared, NOT yet set up

* **Why:** the scheduler lives inside the API process. The API started by the editor's preview server stops when that session ends. `scripts/ops/footiq_service.ps1` runs the API under a small supervisor instead.
* **Commands:** `powershell -File scripts/ops/footiq_service.ps1 start | stop | restart | status | logs | audit | task-plan`. Logs: `logs/supervisor.log` and `logs/backend-<time>.out.log` / `.err.log`; pid and stop files: `data/run/`.
* **One backend, one scheduler:** the supervisor refuses a second copy (mutex) and refuses to start when the port is taken; and a machine-wide lock file (`data/run/scheduler.lock`) means a second backend of any kind (a preview server on another port, a script) cannot start a second scheduler. The operating system releases the lock if the holder crashes.
* **Crash and restart:** the supervisor restarts the backend after a crash (waits 5, 10, 20, 40, 60 s; gives up after ten quick exits in a row). A restart makes no early provider request (the next check is computed from the run history).
* **After Windows login:** `task-plan` shows a "FootIQ-Backend" task (at log on, current user, no password, restart on failure); `task-install -Apply` creates it, `task-remove -Apply` removes it. It is NOT created yet.
* **Overrides:** `FOOTIQ_DISABLE_SYNC=1` still prevents any scheduler; `FOOTIQ_PORT`, `FOOTIQ_STORE_PATH` and the like let tests run on a private copy.
* **Today's running API** (started by the editor's preview) was started before the lock existed and holds no lock. To switch to the supervised one: stop the preview server, then `footiq_service.ps1 start`.
