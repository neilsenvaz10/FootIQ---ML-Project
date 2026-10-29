# Phase 4.19: UEFA Champions League data completion

Status: **prepared and tested offline. Nothing was imported into production.** The production database, the running backend, the synchronisation settings and the six-competition scope were not touched; no provider request was made; nothing was deleted; no Git operation. Production database sha256 before and after this phase: `692903ece2513a87faab8b59497afc84cf60a31d22d67a8bc7ad99c1f444a0da` (the value left by the Phase 4.18C startup refresh).

Files: audit `data/supervised/phase4/p419/audit_ucl.py` -> `ucl_audit.json`, `ucl_coverage_by_season.csv`, `ucl_2026_27_missing_from_store.csv`; verification `verify_md2.py` -> `md2_verification.csv`, `md2_verified_results.csv`; importer `app/store/uefa_import.py`; rehearsal `rehearse_import.py` -> `rehearsal_report.json`; compatibility `compat_check.py`, `compat_extra.py`; tests `tests/test_uefa_import.py`.

## 1. Coverage report (production store, read-only)
| Season | Rows | Expected | Completed | Source | Duplicates | Bad dates / scores | Missing or unknown team id |
|---|---|---|---|---|---|---|---|
| 2018-19 | 125 | 125 | 125 | openfootball (CC0) | 0 | 0 | 0 |
| 2019-20 | 119 | 119 | 119 | openfootball | 0 | 0 | 0 |
| 2020-21 | 125 | 125 | 125 | openfootball | 0 | 0 | 0 |
| 2021-22 | 125 | 125 | 125 | openfootball | 0 | 0 | 0 |
| 2022-23 | 125 | 125 | 125 | openfootball | 0 | 0 | 0 |
| 2023-24 | 125 | 125 | 125 | openfootball | 0 | 0 | 0 |
| 2024-25 | 189 | 189 | 189 | openfootball | 0 | 0 | 0 |
| 2025-26 | 189 | 189 | 189 | openfootball | 0 | 0 | 0 |
| **2026-27** | **18** | 189 | 18 | Wikipedia (CC BY-SA 4.0) | 0 | 0 | 0 |

- **Complete:** eight historical seasons, 1,122 matches, match the expected counts (the 2019-20 count of 119 is the COVID-shortened format). The 2024-25 and 2025-26 league phases have 144 matches and 36 clubs with 8 matches each. No duplicate (same day and pairing), no date outside the season, no implausible score, no completed match without a score, no home = away, no missing or unknown team identifier, and the outcome column agrees with the score everywhere it can be compared.
- **Identity:** 94 distinct club identifiers; 25 clubs appear under several source spellings (for example `Slavia Prague` / `SK Slavia Praha`), all resolved by identifier, so nothing is split.
- **Not done:** the historical seasons come from a single source (openfootball), so there is no independent cross-source check of their dates and scores.
- **2026-27 league standings coverage:** the table endpoint shows 18 of 144 league-phase matches (matchday 1 only); the audit's "clubs with the wrong match count" flag for 2026-27 is just that partial coverage.

## 2. Missing 2026-27 fixtures and results (171 of 189)
| Part | Matches | In the store | Status in local data |
|---|---|---|---|
| Matchday 1 (8-10 Sep) | 18 | 18 | complete, identical to the staging file (0 differences) |
| Matchday 2 (13-14 Oct) | 18 | 0 | results staged and verified (section 3) |
| Matchday 3 (20-21 Oct) | 18 | 0 | fixtures staged; **played 7 days ago, no result in any local file** |
| Matchdays 4-8 (3 Nov - 27 Jan) | 90 | 0 | fixtures staged with dates; not yet played |
| Knockout phase | 45 (16 play-off, 16 round of 16, 8 quarter-final, 4 semi-final, 1 final) | 0 | pairings are only drawn when the league phase ends; no source can hold them yet |

The full list of the 126 league-phase matches missing from the store is `ucl_2026_27_missing_from_store.csv`. The staged file passes its structural checks: 36 clubs, 8 matches each (4 home, 4 away), no repeated or reversed pairing, no club twice in a matchday, matchday dates in order. This shows internal consistency, **not** that the matchday 3-8 pairings are right.

## 3. Verification of the 18 matchday-2 results
Per-match table: `md2_verification.csv`. For each of the 18 matches, all of the following held: date, home and away club, final score and competition/season agree with the transcription of UEFA's results page (read 2026-10-28 in Phase 4.17B); both club identifiers exist in the store and differ; the source revision is recorded (Wikipedia revision 1380990679 of 2026-10-19 08:23 UTC); the match is not in the store, nor is its reverse. Result: **18 of 18 verified, 18 of 18 new** (name variants bridged: `Slavia Prague` = `Slavia Praha`).

Limits you should know: the UEFA side is my own transcription from the earlier fetch, not a second independent fetch, and I did not re-read UEFA's page this phase (no external request).

**Permission to store and use:**
- **Wikipedia (the stored source):** the text is CC BY-SA 4.0, which allows storage and reuse with attribution and share-alike. The project already stores 18 Wikipedia rows of this competition, and `/api/meta` already shows the attribution. Match results are facts, but I am not giving a legal opinion; the decision to treat this as acceptable for the college project is yours.
- **uefa.com:** used only to compare, nothing from it is stored. I did not read its terms of use, so it is **not** a source to store from. Public availability is not treated as permission.

## 4. Approved-source and licensing assessment
| Source | What it offers for 2026-27 | Licence / permission | Update frequency | Authorization needed |
|---|---|---|---|---|
| Local Wikipedia snapshot (rev. 2026-10-19) | all 144 league-phase fixtures, results to matchday 2 | CC BY-SA 4.0, attribution shown | frozen | none (already local) |
| Wikipedia page, newer revision | would add matchday 3 results (and later ones) | CC BY-SA 4.0 | volunteers, usually within a day | **yes: one external request (MediaWiki API), your approval** |
| openfootball `champions-league` | CC0; the copy downloaded 2026-10-28 has no 2026-27 folder | CC0-1.0 | irregular, volunteers | request needed to check again |
| football-data.org | its free plan is understood to include the Champions League (not re-checked this phase) | same unresolved question as PL/SA/FL1: written permission to store and use for model work | live | **yes: permission, and your approval** |
| OpenLigaDB | Champions League coverage not checked | ODbL for the data it has | live | request needed to check |
| UEFA.com | results readable on the web | terms not reviewed, no feed | live | not usable for storage without terms |

**Assessment:** the only legally usable local source today is the saved Wikipedia revision, and it ends at matchday 2. Matchday 3 onward needs a new source request from you.

## 5. Offline ingestion procedure and dry-run results
`app/store/uefa_import.py` (offline, no network): normalises club identifiers (from the project's identity mapping), validates dates and scores, matches rows on the natural key (competition + season + home + away) so a repeat import adds nothing, keeps provenance (source snapshot with sha256, Wikipedia revision, licence, `match_sources` row per match), writes a sync-run record, and **quarantines** any row that disagrees with a stored row instead of overwriting it. A result is imported only if it is in the verified gate (`md2_verified_results.csv`). Fixtures need `--include-fixtures`. Default is a dry run; writing to production needs `--production` and a `--backup` that is a byte-identical copy.

Dry run on production (read-only, hash unchanged): 144 staged rows, 0 validation issues -> **18 unchanged (matchday 1), 18 `insert_result` (matchday 2), 108 fixtures skipped** (or inserted with `--include-fixtures`).

Rehearsal on private copies of the store (`rehearsal_report.json`):
- results only: 18 inserted; running it again changed nothing (0 inserts, 0 updates, 36 unchanged);
- with fixtures: 126 inserted (144 UCL rows: 36 completed, 18 `awaiting_result` for matchday 3, 90 `scheduled`); again 0 on the second run;
- all other match rows identical before and after (hash), 2 saved simulations and 273 quarantine rows untouched, integrity ok, 0 foreign-key problems;
- conflict case: a stored matchday-1 score altered to 9-0 stays 9-0 and is quarantined with its reason; a fixture imported earlier is completed in place by its verified result (18 updates, no second row);
- production guard: writing without `--production`, without a backup, or with a non-matching backup is refused.

## 6. Application compatibility (checked on the rehearsal copies with the application's own code, sync disabled)
| View | After import | Note |
|---|---|---|
| Competition list / selectors | six competitions | unchanged |
| Results (dashboard) | 36 matches, newest 2026-10-14 | works |
| League-phase standings | 36 clubs, 2 played each, "provisional, criteria 1-5", note "36 of 144 fixtures in the data" | works; top five on 2 played: see compat_with_fixtures.json (Aston Villa 3rd, Stuttgart 4th, Liverpool 5th) |
| Team page / form | works (`Liverpool FC`) | works |
| Data freshness | latest result 2026-10-14, "Historical only", warning "36 of 144 matches in the data" | honest |
| Prediction | 200, "Not validated (indicative only)" label and note, repeat call identical | frozen club models, ratings unchanged (imported rows are outside the model universe) |
| Sync status | UCL "stale: no approved fresh source; results were last imported from a saved snapshot; 18 played matches without a result since 2026-10-20" (only when fixtures are imported) | accurate but noisy |
| **Fixtures list / Matches hub / Gameweeks** | **not available for the Champions League** | by design these are domestic-only; importing the 108 fixtures does not make them visible. It would only let a prediction recognise a stored fixture |

Frozen models: nothing was retrained, no artifact touched.

## 7. Exact production import plan (not executed; needs your approval)
Recommended scope: **Option A, the 18 verified matchday-2 results only.** Option B adds the 108 fixtures; I advise waiting until matchday 3 results are also available, because otherwise matchday 3 appears as 18 overdue matches.
1. **Approval** from you for option A or B.
2. **Stop the backend** (Ctrl+C in the "FootIQ backend" terminal tab). This is needed because the running backend caches the match frame in memory and a writer should not run beside it.
3. **Backup:** copy `data/footiq.sqlite` to `data/backups/p419_pre_import_<timestamp>/footiq.sqlite` (the WAL file is empty after a clean stop), record both sha256 values and confirm they are identical.
4. **Dry run on production** (read-only): `.venv\Scripts\python.exe -X utf8 app\store\uefa_import.py --as-of <today>`. Expect 18 `insert_result`, 18 `unchanged`, 0 issues. Stop if not.
5. **Apply:** `.venv\Scripts\python.exe -X utf8 app\store\uefa_import.py --apply --production --backup <backup path> --as-of <today> --report-dir data\supervised\phase4\p419\prod_apply` (add `--include-fixtures` for option B). One transaction; it rolls back on any error.
6. **Verify:** integrity ok and 0 foreign-key problems; UCL 2026-27 = 36 rows (144 with fixtures); every other match row unchanged (hash); 2 saved simulations unchanged; quarantine still 273 (plus 0 new).
7. **Restart** in the foreground terminal as before. Note the startup refresh skips if less than 15 minutes since the last one; it makes at most 2 OpenLigaDB requests, Bundesliga and La Liga only.
8. **Check** `/api/competitions/UCL/league-phase?season=2026-27` (36 played, 2 each), `/api/data-freshness` (latest 2026-10-14), a Champions League prediction (label "Not validated (indicative only)"), and the six-competition scope.
- **Rollback:** stop the backend, copy the backup file back over `data/footiq.sqlite` (no `-wal`/`-shm` leftovers), confirm the sha256 equals the recorded value, restart. The import changes only Champions League 2026-27 rows plus provenance, snapshot, quarantine and run-log rows, so restoring the file is exact. Deleting individual rows is not needed.

## 8. Tests
- `tests/test_uefa_import.py`: 25 passed (validation of each bad-row kind, duplicate and reverse detection, the verified gate, conflicts and quarantine, dry run changes nothing, repeatable apply, fixtures completed in place, production guard, competition and season mapping, league-phase table from the 36 results).
- `tests/test_uefa_league_phase.py`, `tests/test_freshness.py`, `tests/test_competition_coverage.py` (six-competition scope, archived five refused, startup-only sync, Champions League has no update source): 39 passed.
- `tests/test_miniproject.py` (API, prediction compatibility, scope): 32 passed (API routes, prediction for all six including the Champions League label, six-competition scope).
- No full regression run: no application code changed, only a new offline module and tests were added.

## 9. Remaining blockers needing your approval
1. Approve the import (option A or B) and the stop/restart of the backend it needs.
2. Choose a source for matchday 3 onward (the saved page ends at matchday 2): a newer Wikipedia revision (one request), a re-check of openfootball (CC0), or the football-data.org permission route. Until then the Champions League stays at matchday 2 at best.
3. Confirm Wikipedia (CC BY-SA 4.0) is acceptable as the stored source for this competition, and that uefa.com is used for comparison only.
4. Decide whether the application should show Champions League fixtures (not shown today anywhere); that is a code change I have not made.
