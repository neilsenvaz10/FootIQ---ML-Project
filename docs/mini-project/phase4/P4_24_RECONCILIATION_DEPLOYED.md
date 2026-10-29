# Phase 4.24: strong-evidence reconciliation deployed (done)

Applied to production on 2026-10-28, exactly as approved: **43 changes** from `data/supervised/phase4/p423/staging/proposed_changes.csv` with `app/store/reconcile_import.py` (strong tier only; `--include-provider-assisted` and `--include-decisions` were not used). No Git operation, no retraining, no storage cleanup, no new provider, no archived competition touched.

- **Preflight (all passed):** database hash `afe71c44...` as recorded, integrity ok, 0 foreign-key problems; the proposals file hash `248e89c5...` equals the one recorded in the Phase 4.23 dry run; strong dry run = exactly 43 `apply`, 61 skipped (tier not enabled), 0 issues, 0 conflicts; all five frozen hashes match; both saved simulations present; one foreground uvicorn (tab).
- **Stop and backup:** Ctrl-C twice and then closing the tab ended the backend, which again hung idle in "Shutting down" with no connection and no write (the database file was byte-for-byte unchanged afterwards). Byte-identical backup **`data/backups/p424_pre_reconcile_20261028/`** (sha256 `afe71c445bfeddcb...`, integrity ok, 223,636 matches, 273 quarantine rows) is the rollback point: stop the backend, copy it over `data/footiq.sqlite` (no `-wal` / `-shm` leftovers), check the hash, restart in the foreground.
- **Apply:** one transaction, 43 updated, 0 inserted, 0 quarantined (sync run 37).
- **Verification against the backup:** exactly **43 rows changed and they are exactly the 43 strong proposals**; every one matches its proposal (result, played day, date, status; results enter the model universe as `wikipedia` / `CC BY-SA 4.0`; corrected fixtures lost only their stored kickoff time); the 61 other proposals (60 provider-assisted dates, the postponement) and the 3 single-source Serie A results are **untouched**; no row added or missing; no verified result overwritten; archived competitions unchanged; 0 duplicate pairings, 0 duplicate same-day matches, 0 orphan clubs, 0 completed matches without a score; the quarantine table is identical (273 rows, identical content); both saved simulations unchanged (content hash `33fbf4af...`); frozen hashes match; other tables unchanged apart from the 43 provenance rows, 1 snapshot and 1 sync-run record.
- **Restart:** foreground terminal tab, `/api/health` ok; startup-only synchronisation unchanged (OpenLigaDB for Bundesliga and La Liga, no scheduler). The authorized startup refresh (10:44 UTC, 2 requests) **changed no match row** (0 changed, 0 added): it only recorded its sync runs. For La Liga it reported 99 results confirmed (was 93) and 18 existing findings: the corrected stored dates now agree with the approved feed, and an earlier OpenLigaDB snapshot already shows four of the six La Liga results with the same score and day, an extra independent confirmation.

## Coverage of 2026-27 now
| Competition | Completed | Latest result | Past date without a result |
|---|---|---|---|
| Premier League | 80 / 380 | 2026-10-25 | 0 |
| La Liga | 99 / 380 | 2026-10-26 | 1 (Rayo Vallecano v Athletic Club, 10 Oct: postponement proposed, not applied) |
| Bundesliga | 63 / 306 | 2026-10-25 | 0 |
| Serie A | 80 / 380 | 2026-10-25 | 3 (Sassuolo-Lazio, Roma-Cagliari, Torino-Como of 27 Oct: one source) |
| Ligue 1 | 72 / 306 | 2026-10-26 | 0 |
| Champions League | 54 completed + 90 scheduled (of 144 league phase) | 2026-10-21 | 0 |

## Preserved for future review (not applied)
60 provider-assisted date corrections (Serie A 39, Ligue 1 21), the Rayo Vallecano v Athletic Club postponement, and the 3 single-source Serie A results, with their evidence, in `proposed_changes.csv`, `held_open16.csv` and `date_reconciliation.csv`.

## Application checks (live, GET only)
All six competitions answer 200 for hub, dashboard, standings, team page, coverage and predictions (five leagues "Validated", Champions League "Not validated (indicative only)"); standings count 80 / 99 / 63 / 80 / 72 games; the corrected Premier League fixtures show their new dates (Everton v Coventry 6 Nov, Crystal Palace v Liverpool and Sunderland v Chelsea 8 Nov) and the corrected results show their played day (for example Alavés 1-1 Málaga on 23 Oct, PSG 2-0 Lyon on 26 Oct); the 90 Champions League fixtures are visible (matchday and team filters work); archived competitions answer 404 / 422.

## Tests
Backend targeted regression after the deployment: **283 passed**, 0 failures, 0 skips, 1 warning (an httpx deprecation notice in the test client), 10 minutes: reconciliation 40, domestic importer 28, UEFA importer 29, hub 46, API and prediction 32, scope, freshness, league phase, startup sync, store and featured. Frontend: **358 passed, 13 skipped** (the live-API tests, by design). The full 477-test regression was not re-run: no application code changed.

## Readiness
Data: complete for the demonstration (every competition has current results, standings, fixtures and predictions; remaining gaps are listed above and in the preserved proposals). For storage optimization: `data/backups` holds 2.6 GB (five 219 MB database backups, p420 to p424), `data/supervised` 13 GB (staging, rehearsal copies, pytest temp folders). Keep `p424_pre_reconcile_20261028` (the current rollback point) and the pre-import backups you want as history; rehearsal copies under `data/supervised/phase4/*/rehearsal/` and `data/supervised/pytest_tmp/` are regenerable. Nothing was cleaned up in this phase.
