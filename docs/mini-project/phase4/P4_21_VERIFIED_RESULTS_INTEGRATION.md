# Phase 4.21: verified results integration

Status: Part A (Champions League matchday 3) **imported into production**; Part B (domestic results importer) **built, tested, dry-run on production, NOT imported**; Part C (Champions League fixtures) **verified and staged, NOT imported**; Part D unchanged. No Git operation, no retraining, no deletion, no storage cleanup, no provider request in this phase, no change to the Bundesliga / La Liga startup-only synchronisation, no new sync provider.

## Part A: Champions League matchday 3
- **Records:** the 18 results of 20-21 October 2026 (`data/supervised/phase4/p420/staging/ucl_verified_results.csv`, matchday-3 rows), from Wikipedia revision 1381604353 (2026-10-23, CC BY-SA 4.0), each compared with UEFA's results page (18 of 18 equal on date, both clubs and score). Reuse: the same licence and attribution as the 36 rows already stored; UEFA's page is comparison only.
- **Checks before:** dry run 144 staged rows, 0 validation issues, 36 unchanged, **18 `insert_result`**, 0 conflicts, 90 fixtures not requested. Backend stopped cleanly (Ctrl-C, "Application shutdown complete"), full backup verified byte-identical (sha256 `bb4dec74...`, integrity ok, 223,528 matches) at `data/backups/p421_pre_import_20261028/`.
- **Outcome:** 18 inserted, 0 updated, 0 quarantined (sync run 31). Champions League 2026-27 rows **36 -> 54** (all seasons 1,158 -> 1,176). Integrity ok, 0 foreign-key problems; no duplicate pairing or same-day duplicate; no bad score; every club id exists; every other match row unchanged (hash); the 36 earlier Champions League rows unchanged; the two saved simulations unchanged; quarantine still 273. Provenance: snapshot `uefa-ucl-2026-27-staging-rev1381604353`, 18 `match_sources` rows.
- Backend restarted in the foreground terminal. The 15-minute rule of the startup refresh (last one 09:53 UTC) meant this restart made **no** provider request (request ledger unchanged at 17 lines).

## Part B: domestic results importer (`app/store/league_results_import.py`)
Imports the verified 2026-27 results the store lacks for the Premier League, Serie A and Ligue 1 (the leagues without a sync source), from the Phase 4.20 staging files. Dry run by default (store opened read-only); `--apply` writes in one transaction; production needs `--production` and a byte-identical `--backup`.
- **Validation:** only the three leagues and season 2026-27; two-source tier only; both clubs exist in `teams` and differ; ISO date inside the season and not after today; the staged date, the stored fixture date and the cross-check date equal; integer scores 0-15 and the three recorded scores (Wikipedia, cross-check, staged) identical; no duplicate record or pairing in the file.
- **Against the store:** only an open fixture (scheduled / awaiting result) gets its result, in place, keeping its stored date and record id (no row is created); an identical stored result is `unchanged`; a stored result that differs is **never overwritten** (quarantined with its reason); a different stored date, a postponed / cancelled match, a reversed or unknown pairing, a missing record and a fixture with a **disputed date** are quarantined, not resolved.
- **Row written:** status `completed`, goals, 90-minute goals, outcome, `confirmed` label, and, exactly as a result from an approved sync, `rated`, `regular`, `in_universe` and the model entities, so the frozen models see the result as history (no retraining, no artifact touched); source `wikipedia`, licence `CC BY-SA 4.0`; one `match_sources` row, one `source_snapshots` row per league (revision recorded) and a `sync_runs` row (`league_results_import`).
- **Repeatable:** a second run reports every row `unchanged` and writes nothing (tested and rehearsed).
- **Tests:** `tests/test_league_results_import.py`, 28 passed (each bad-row kind, duplicates, every conflict type, dry run changes nothing, apply, idempotence, other rows byte-identical, quarantine, production guard, the real staged files read-only against production).

### Dry-run findings for the 71 domestic results (production, read-only, database hash unchanged)
| League | Staged | `update_result` | Unchanged | Conflicts | Invalid |
|---|---|---|---|---|---|
| Premier League | 17 | 17 | 0 | 0 | 0 |
| Serie A | 29 | 29 | 0 | 0 | 0 |
| Ligue 1 | 25 | 25 | 0 | 0 | 0 |
| **Total** | **71** | **71** | 0 | 0 | 0 |
None of the 71 sits on one of the 96 disputed fixtures (checked by club pairing; the staged dates are 9-25 October, the disputes start 24 October for matches not yet played or held back). Rehearsal on a private copy of production: 71 updated, second run 71 unchanged; integrity ok, 0 foreign-key problems, 0 duplicates, simulations (2) untouched; the application on the copy shows Premier League 77 completed (was 60), Serie A 79 (was 50), Ligue 1 70 (was 45), past-date open fixtures 3 / 4 / 2 (were 20 / 33 / 27), standings and predictions work ("Validated").

## Part C: Champions League fixtures (staged, not imported)
- **Verification:** all 90 staged fixtures of matchdays 4-8 equal UEFA's own fixture list on matchday, date and both clubs (90 of 90; two UEFA lines carried a stray date, `Dortmund v AEK` 28/01 and `Sabah v Napoli` 20/01/2026, while every other line gives 27/01/2027 and 20/01/2027, so the matchday dates were used). Gate: `data/supervised/phase4/p421/ucl_verified_fixtures.csv`. The staging has 36 clubs, 8 matches each (4 home, 4 away), no repeated or reversed pairing, no club twice on a matchday, matchday dates in order.
- **Importer (`app/store/uefa_import.py`):** `--include-fixtures` now inserts only fixtures that are in the verified-fixtures gate (date and pairing), and only league-phase matchdays 1-8 are accepted, so **no knockout pairing can be created** (none is staged: the draw happens after matchday 8). A fixture dated before the as-of day would be stored as awaiting-result, never as upcoming; a pairing that already has a result is `unchanged`. 29 tests pass (4 new).
- **Production dry run (read-only):** 144 rows, 0 issues, 54 unchanged, **90 `insert_fixture`**.
- **Rehearsal on a private copy:** 90 inserted, second run 0 changes; Champions League rows 54 completed + 90 scheduled = 144 (matchdays 1-8 = 18 each); 0 duplicates, 0 non-league-phase rows, no completed match dated after today and no unplayed one dated before today. The **existing Matches hub** lists them: `upcoming 90`, `completed 54`, matchday and team filters work (Arsenal shows 5 upcoming), every item carries "Not validated (indicative only)"; predictions are unchanged and labelled indicative; the league-phase table still counts the 54 played results (its note "54 of 144 league-phase fixtures are in the data" counts results, not fixtures).

## Part D: synchronisation
Unchanged: startup-only, Bundesliga and La Liga (OpenLigaDB) only; Premier League, Serie A, Ligue 1 and the Champions League have no approved source. **La Liga:** 7 fixtures are still past their date without a result (6 were played, per Phase 4.20; 1 is the suspended match). This phase's restart made no refresh (15-minute rule), so nothing could be checked and none was forced. After the **next authorized startup refresh** run `data/supervised/phase4/p421/check_laliga_after_startup.py` (read-only): La Liga completed should go from 93 to up to 99 and the list shrink.

## Part E: validation and tests
- **Six competitions (live backend, GET only):** all six answer 200 for hub, dashboard (standings / league-phase table), team page, coverage and predictions (five leagues "Validated", Champions League "Not validated (indicative only)"); the five archived competitions are 404 / 422; exactly six in the selectors.
- **Integrity:** database integrity ok, 0 foreign-key problems; saved simulations unchanged (Bundesliga run 1, La Liga run 2, content hash `33fbf4af...`); frozen model hashes all match (club v1, club v2-r1, v2.7 archive); request ledger unchanged (17 lines).
- **Tests:** backend 189 passed in 3.5 min (domestic importer 28, UEFA importer 29, hub 46, API and prediction 32, scope, freshness, league phase, startup sync); frontend 358 passed, 13 skipped (live-API tests). The full 477-test regression was not re-run: no application code changed this phase (only the two offline importers and their tests); the database hash after the matchday-3 import is the only change to production data.

## Coverage of 2026-27 after Part A
| Competition | Completed | Latest result | Past date, no result | Staged, not imported |
|---|---|---|---|---|
| Premier League | 60 / 380 | 2026-10-12 | 20 | 17 results |
| La Liga | 93 / 380 | 2026-10-25 | 7 | none (route: next startup refresh) |
| Bundesliga | 63 / 306 | 2026-10-25 | 0 | none missing |
| Serie A | 50 / 380 | 2026-09-20 | 33 | 29 results |
| Ligue 1 | 45 / 306 | 2026-09-20 | 27 | 25 results |
| Champions League | **54 / 144** league phase (of 189 incl. knockouts) | 2026-10-21 | 0 | 90 fixtures |

## Date disputes (96)
33 resolved by evidence in Phase 4.20 (31 Premier League, 2 Ligue 1) and **still not applied**; **63 unresolved and quarantined** (39 Serie A, 24 Ligue 1): one source against one. Nothing in this phase changed any date.

## Exact approvals needed for the next production imports
1. **Domestic results:** import the 71 staged results with `app/store/league_results_import.py --apply --production --backup <fresh backup>` (17 Premier League, 29 Serie A, 25 Ligue 1), preceded by stopping the backend, the verified backup and a final dry run, followed by the integrity checks and a foreground restart. Decision needed: Wikipedia (CC BY-SA 4.0) as the stored source of these results (the cross-check source is not stored) and that they enter the model universe like synced results.
2. **Champions League fixtures:** import the 90 verified matchday 4-8 fixtures with `app/store/uefa_import.py --apply --production --include-fixtures --backup <fresh backup> --staging .../uefa_2026_27_staging_v2.csv --gate .../ucl_verified_results.csv`, same procedure. They will show as upcoming in the Matches hub; knockout fixtures stay absent until UEFA draws them.
Both can share one backend stop and one backup if you approve them together.
