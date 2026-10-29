# Production import report: OpenLigaDB Premier League and La Liga 2026-27

Date: 2026-10-25. Nothing is staged, committed or pushed. No network request was made (the ledgers still hold 4 investigation requests and 1 Bundesliga request). `live_enabled` is false. Phase 3 has not been started.

## Technical report

### Procedure and safeguards
1. No concurrent writers: no other Python process, nothing listening on port 8000, and an exclusive SQLite lock was granted.
2. Backup (SQLite online backup API): `data/supervised/production_import/footiq.20261025T142618Z.backup.sqlite`, 228,298,752 bytes, sha256 `1eb0a1223b778d1b69ef109f78596244d6c7607399dc636445ba8888104f3caa`. It opens, passes `integrity_check` ("ok"), has 0 foreign-key violations and every table fingerprint equals production.
3. Start state equals the rehearsal's start state: every table fingerprint identical; model, CSV, prospective-log and sync-config hashes identical to the rehearsal manifest.
4. Apply from the saved snapshots (sha256 re-verified), with date protection on, in `app/store/import_openligadb_production.py`. Any failed check after writing starts restores the backup.

**One failed attempt, rolled back.** The first run applied the import and every substantive check passed (586 rows, 30 results, field-level diff identical, all tables equal to the rehearsal), but my own integrity check compared database rows to plain tuples, so it reported a false failure and the script restored the backup automatically. I confirmed production was back to 223,510 / 223,816 / 5 / 7,442 / 5 / 216 rows, fixed the check, and re-ran the whole procedure from the start (new backup above, taken after the rollback). The rollback rewrote the file, which is why the production file's raw sha256 changed (`2c677ebf…` to `936beb3e…`) while every table's content hash stayed identical. Both backups are kept.

### Before and after (production)
| Table | Before | After |
|---|---|---|
| matches | 223,510 | 223,510 (586 rows updated, none added or removed) |
| match_sources | 223,816 | 224,519 (+703) |
| source_snapshots | 5 | 9 (+4) |
| team_aliases | 7,442 | 7,447 (+5) |
| quarantine | 216 | 273 (+55 DATE_DIFFERENCE, +1 CONFLICT, +1 CONTRADICTORY SOURCE RESULT) |
| sync_runs | 5 | 7 (+2, kind `offline_snapshot_import`; detail records the real import time 2026-10-25T14:28:02Z) |
| competitions, teams, meta, source_state, sync_errors, forecast_runs, forecasts, simulation_runs | | identical |

`matches` content hash `59384a7c692d093b…` to `d0862a54f5c279b8…` (equal to the rehearsal result). Run and quarantine stamps carry the snapshot retrieval time 2026-10-25T09:07:13Z so that the result is reproducible and comparable.

### Comparison with the approved rehearsal diff
* Field by field: the actual set of (record, field, before, after) changes equals the approved `import_diff_matches.csv` exactly (no extra, none missing).
* Every table except `sync_runs` has a content hash identical to the rehearsal's (`sync_runs` differs only in the run kind label and the added import time).
* 586 match rows updated; **30 results recovered (Premier League 10, La Liga 20)**; 0 existing completed scores changed; 0 fixture dates changed; 0 rows added or removed.
* The five held-back La Liga results were not imported (status and goals unchanged). Bournemouth v Brentford is still 2-2, Aston Villa v Nottingham Forest still 1-2, both quarantined.
* No duplicate record ids, no duplicate pairings in either league, `integrity_check` ok, 0 foreign-key violations, quarantine additions exactly 55 + 1 + 1.

### Verification
| Check | Result |
|---|---|
| Standings (both leagues) | identical to the rehearsal: Premier League 60 matches counted, Man City leads on 18; La Liga 89 matches, Barcelona leads on 27 |
| Freshness | Premier League newest result 2026-10-12, 15 awaiting (oldest 10-17); La Liga newest 2026-10-21, 1 awaiting (Rayo v Athletic) |
| Gameweek eligibility | identical to the rehearsal: Premier League Matchday 8 all provisional; La Liga Matchday 10 has 8 fully supported, 2 provisional |
| Backend, whole suite in one run | **101 passed** |
| Frontend with the live backend | **48 of 48 passed** (9 live-contract tests included), production build succeeds |
| Model, CSV, prospective-log and sync-config hashes (17 files) | identical before and after; `config/sync.json` sha256 `d0038d15…` unchanged, `live_enabled` false |
| Production store after tests and after the live run | table hashes still equal the post-import values |

Honest notes: in the first frontend run 4 of the live tests failed while the backend was still warming up; the same file passed 9 of 9 on its next run and the whole suite then passed 48 of 48, so I treat it as a cold-start timing issue, not a data problem. The live backend ran against a copy of the post-import database, so that its start-up check could not write to production.

### Outstanding risks
* Bournemouth v Brentford (stored 2-2, source 2-1) and Aston Villa v Nottingham Forest (stored 1-2, source contradictory) need an official match record.
* 55 date differences are held (49 harmless, 5 La Liga played games whose results are held, 1 postponement-like anomaly, Rayo v Athletic).
* Premier League data stays about 13 days behind the source's own latest result; both leagues are labelled stale in the app because no sync source is approved for them.
* 30 results come from a single community-edited source (it agreed with all 117 scores we already held).
* Recovered results become part of the history the frozen models read; the models themselves are unchanged.
* Ten Premier League Matchday 7 fixtures look "fully supported" but are already past, so a forecast saved now is not "made before kickoff".

## Simple explanation

**What was done.** FootIQ's stored results for the Premier League and La Liga were stuck at 20 September. A free football database (OpenLigaDB) had newer results, which we downloaded once and saved. After checking them offline on a private copy, today I added them to the real database: 30 new results, kickoff times for 586 matches, and five team-name links so the two databases agree who "Celta Vigo" or "Brentford F.C." is.

**Why.** Predictions use recent results as form. Without them the Premier League and La Liga forecasts were "provisional" and out of date.

**Problems and how they were handled.**
* The old import code would have overwritten fixture dates; I changed it to hold any date that disagrees (55 cases) and ask you.
* Two score disagreements (Bournemouth–Brentford, Villa–Forest) were put aside in a quarantine list; no score was overwritten.
* Two of your proposed team spellings are not stored names, so I linked them by team id and fixtures.
* My own safety check had a small bug during the first import. The script noticed a "failure" and put the database back automatically; I fixed the check and ran the import again from the start.

**What changed in FootIQ.** Both leagues have newer standings, La Liga's next gameweek now has mostly fully supported forecasts, and matches show kickoff times. Models, training data, fixture dates, old scores and live-sync settings are untouched.

**Still to do.** Check the two disputed scores against an official record; decide the 55 held dates; get a fresher Premier League source and decide whether to approve it for sync; then Phase 3 (simulations) after your review.

**Viva answer (30 seconds).** "Our results database was behind, so I added a second open data source. I never trusted it blindly: I downloaded it once, saved it with a checksum, rehearsed the import on a copy, and only then updated the real database after taking a backup. Where the source disagreed with our data (dates and two scores) I did not overwrite anything; I quarantined it for review. The prediction models were never retrained or changed, only the results they read are newer. Every step is logged with licence and source so it can be audited or undone."
