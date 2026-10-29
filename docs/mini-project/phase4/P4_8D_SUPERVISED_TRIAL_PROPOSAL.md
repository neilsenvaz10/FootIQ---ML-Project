# Supervised 3-cycle real-network trial of the full-season Bundesliga refresh (proposal and RESULTS)

Status: approved and **executed 2026-10-27** (results at the end). Production untouched, `live_enabled` false.

## Exact network requests needing your approval

**At most 3 HTTPS GET requests, all to the same, already approved endpoint, one per cycle:**

1. `https://api.openligadb.de/getmatchdata/bl1/2026` (cycle 1)
2. `https://api.openligadb.de/getmatchdata/bl1/2026` (cycle 2)
3. `https://api.openligadb.de/getmatchdata/bl1/2026` (cycle 3)

No other URL, no retries (`max_retries` 0), at least 60 s of real time between cycles (the client's own 3 s minimum applies inside a cycle), a hard cap of 3 and a strict URL allow-list in the opener. Expected answer each time: HTTP 200, a JSON array of 306 matches (34 matchdays × 9, 18 teams), about 317 kB.

## Method

* **Clock:** the requests are real; the six-hour spacing uses the mocked clock. Cycle 1 runs at real "now"; before cycle 2 the clock is advanced to +5 h 59 min (expect "not due", 0 requests), then to +6 h 01 min (due, request); the same for cycle 3. A new `SyncManager` (restart) is created between cycles 2 and 3.
* **Private database:** a consistent copy of `data/footiq.sqlite` made with SQLite's backup API from a read-only connection; production's physical and logical hashes are recorded before and after (baseline v3). The scheduler runs with `live_enabled` true in that process only, an isolated snapshot/ledger folder (`data/snapshots/p48d_trial2/`), and `config/sync.json` untouched.
* **Script:** the existing `real_network_trial.py` pattern, extended to three cycles with the guards below.

## Expected database changes (private copy only)

* Per cycle: +1 `startup_check`/`periodic_check` row and +1 `sync` row in `sync_runs` (`requests` = 1), +1 registered snapshot with its SHA-256, the source-state record refreshed.
* `matches`, `match_sources`, `quarantine`, aliases: **no change** if the provider's file is unchanged (as in the last two fetches). If the provider has changed something, the exact row differences are listed and compared with the rules (new result imported; changed score or date quarantined, never applied).

## Safeguards

* Opener halts the trial on a non-200 answer, malformed JSON, or a payload that is not 306 matches of league `bl1` in matchdays 1–34.
* Each import is one transaction; a failed or malformed cycle leaves every data table unchanged (tested); next check backs off 12 h.
* Locking, duplicate protection and date/score quarantine as tested in `test_full_season_refresh.py`.
* Rollback: the private copy is discarded; nothing needs undoing in production. Any unexpected difference stops the trial.

## Success criteria

1. Exactly 3 real requests, all HTTP 200, snapshots saved read-only with hashes recorded in the ledger.
2. Cycles 2 and 3 are "not due" at +5 h 59 min and run at +6 h 01 min; the restart makes no extra request.
3. Every cycle ends `ok` with `requests` = 1; no duplicate rows; no data table changes beyond the explained ones.
4. No unexpected quarantine entries; any provider change is reported field by field.
5. Production physical and logical hashes are identical before and after; `live_enabled` false; nothing staged.
6. If all pass: the Bundesliga is ready for you to decide on a Bundesliga-only schedule with daily review; if any fails, stop and report.


---

## RESULTS (executed 2026-10-27, `real_network_trial3.py`, evidence in `data/supervised/phase4/p48d/real_network_trial3.json`)

**Before:** production equalled baseline v3 (physical and logical), `integrity_check` ok, `live_enabled` false; the private copy (SQLite backup API, `trial3_work/trial.sqlite`) equalled the v3 logical hash, differs from production, the manager was given that path and an isolated snapshot folder (`data/snapshots/p48d_trial2/`), and the trial reads no settings from `config/sync.json`.

| Cycle | Mocked clock | Real request (UTC) | Status / bytes / SHA-256 | Inserted / updated / unchanged / confirmed / quarantined | Data tables changed | Next due |
|---|---|---|---|---|---|---|
| 1 (due at start; last real attempt was 2026-10-25) | +0 | 16:35:15 | 200 / 316,983 / `b725c2f3…6b46` | 0 / 0 / 243 / 63 / 0 | none (snapshot register, source state) | +6 h |
| 2 | +6 h 01 min (at +5 h 59 min: `not_due`, 0 requests) | 16:36:28 (73 s later) | 200 / 316,983 / `b725c2f3…6b46` | 0 / 0 / 243 / 63 / 0 | none | +12 h 01 |
| 3 (new `SyncManager` after a restart; at +6 h 30 min: `not_due`, 0 requests, file unchanged) | +12 h 02 min | 16:37:41 (73 s later) | 200 / 316,983 / `b725c2f3…6b46` | 0 / 0 / 243 / 63 / 0 | none | +18 h 02 |

* **Requests: exactly 3**, one per cycle, all to `https://api.openligadb.de/getmatchdata/bl1/2026`, HTTP 200, no retries, ≥ 73 s apart; the opener validated each answer (306 matches of `bl1`, matchdays 1–34 × 9, unique ids) before the importer saw it.
* **Six-hour interval respected** (mocked clock): not due at +5 h 59, due at +6 h 01; the restart did not trigger an early request; each cycle's next due time is exactly +6 h.
* **Provider unchanged:** all three answers are byte-identical to each other and to the approved response of 12:57 UTC, so **no new result occurred** in this trial; the new-result path is covered by the saved-snapshot tests (`test_full_season_refresh.py`).
* **No duplicate imports, no unnecessary writes:** per cycle only `sync_runs` (+2 rows), `source_snapshots` (+1) and `source_state` changed; no `matches`, `match_sources`, `quarantine`, alias row; 0 duplicate record ids; `PRAGMA integrity_check` ok after every cycle; production physical hash unchanged after every cycle.
* **Provenance and freshness:** the six imported results kept their primary links and original snapshots; after each cycle the league reads "fresh" with `last_successful_external_check_utc` = that cycle's (mocked) time, `last_import` unchanged (an unchanged answer is a check, not an import), 0 awaiting results.
* **Failure injection (saved response, network blocked, never against the live provider):** provider down → `error`, one attempt, no data change, back-off 12 h; malformed body → `error`, no data change, back-off 24 h; recovery → `ok`, next due +6 h; tampered answer → 2 quarantine rows (score conflict, date difference), stored values unchanged; a recent `running` row → `skipped_already_running`, 0 requests.
* **After:** production physical `1bfad5bd…cb278` and logical `b3dcf8c0…c1d95f` unchanged, `integrity_check` ok, `live_enabled` false; nothing staged. The snapshot folder holds 5 files: 3 real answers and 2 produced by the replay phase (the last one, `…163817Z`, is the injected tampered payload, **not provider data**).
* **Targeted tests re-run:** full-season refresh, scheduler, provenance and baseline-hash tests: **43 passed**; integrity script clean. (No application code changed in this step; full suites not run.)

**Problems discovered:** (1) every cycle saves and registers a new 317 kB snapshot even when the answer is byte-identical (about 1.3 MB and 8 diary rows per day at four cycles): harmless, but worth skipping duplicates; (2) the default `max_retries` of 4 would allow up to 5 requests in a failing cycle (back-off waits 5–300 s): too many for a courtesy limit; (3) no visible counter of consecutive failures; (4) an unattended import writes to the production file by design, so the baseline hashes will move with every real import (a baseline policy is needed).

**Is unattended Bundesliga synchronisation ready?** Technically yes: three real cycles, restart, locking, back-off, quarantine and failure safety all behaved. It is not switched on, and I recommend the changes below first.

**Exact changes required for activation (not made):**
1. `config/sync.json`: `"live_enabled": true`; add `"max_retries": 2`; keep `"periodic_minutes": 360`, `"startup_check": true`, `refresh_mode` default `full_season`, competitions `["BUNDESLIGA"]` only.
2. Keep `config/contact.local` (already configured; never committed).
3. Take a SQLite-backup copy of production and record its hashes immediately before activation; then start (or restart) the API: the scheduler starts inside it and runs only when due.
4. Adopt a baseline policy for imports done by the scheduler (record physical and logical hashes daily; accept change only when `sync_runs` explains it).
5. Before or soon after activation: skip registering identical snapshots, show consecutive failures and the quarantine count in the status panel, and name a person who reviews quarantined items.
6. Premier League, La Liga, Serie A and Ligue 1 stay out of `APPROVED`: no change needed.
