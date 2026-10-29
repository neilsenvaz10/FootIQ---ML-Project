# 08 OpenLigaDB Bundesliga 2026-27 live pilot — results (2026-10-21 14:12 UTC)

Run folder: `pilot/run_20261021T141224Z/` (raw snapshots read-only with sha256; request ledger; reconciliation tables; isolated refreshed universe). Plan sha256 `d7c2169e117a02f3e72b0517f171f2b11fb7f3d609156619cfd7421615a18bc9` (approved). Executed once.

## Execution
6 requests, 6 HTTP attempts, all status 200, host `api.openligadb.de` only, about 3 s apart (R1 14:12:25 .. R6 14:12:39). Pre-checks passed: plan hash, contact configured (value not displayed; the contact file was read from the repo-root `config/contact.local` through `FOOTIQ_CONTACT_FILE`), contact not in tracked config, kickoff guard, host/competition/season/limits. No retries needed. The contact string does not appear in the ledger, snapshots, reports or run files (searched).

## Results
| Item | Result |
|---|---|
| League confirmed | leagueId 4937, `bl1`, season 2026, "1. Fußball-Bundesliga 2026/2027" |
| Matches | 306, 306 unique matchIDs, 0 duplicate matchIDs, 0 duplicate ordered pairs, 18 teams, 34 matchdays |
| Completed | 54 (all kickoffs before the retrieval time; all with explicit `After90Minutes`; 0 completed without a 90-minute type) |
| Overlap with openfootball | 36 matches; **36 exact score agreements, 36 date agreements, 0 conflicts** |
| **Newly recovered results** | **18** (dated 2026-10-09 .. 2026-10-18), exactly the 18 results openfootball lacked for the Bundesliga |
| Fixtures missing | 0 openfootball Bundesliga fixtures absent from OpenLigaDB; 0 OpenLigaDB fixtures absent from openfootball |
| Team identity errors | 0 unresolved, 0 ambiguous |
| Valid kickoff timestamps | 306 / 306 (UTC) |
| Polling probe | current matchday 7; change dates for matchdays 6 and 7 equal the max `lastUpdateDateTime` in the season snapshot (2026-10-18T19:23:40 and 2026-09-10T17:26:33), so a later poll would skip unchanged matchdays |
| Result types (R2) | HalfTime, After90Minutes, "after stoppage time" (Unknown), AfterExtraTime, AfterPenalties. The endpoint names the field `kind`; the pilot report printed `[null]` because the script looked for `resultTypeKind` (fixed in the script; the data are in the R2 snapshot). Adapter behaviour was unaffected: matches carry `resultTypeKind` and only `After90Minutes` is used. |

## Eligibility for prospective logging (isolated dry run, nothing logged, feature store untouched)
Of 252 upcoming Bundesliga fixtures, **18 would be primary-eligible** (the matchdays dated within 14 days of the latest result, 2026-10-18); 234 fail only the staleness rule and become eligible as later polls bring newer results. No other check fails.

## Remaining blockers
* Official logging remains unapproved (no approval JSON); the protocol amendment is a draft; nothing was changed in the logger or protocol.
* The 18 new results exist only in the isolated pilot output; incorporating them into any official feature state needs your approval and the amendment.
* Only the Bundesliga is covered: 233 of the 271 missing results in the other 14 in-season leagues remain unrecovered (Premier League's 20 only via Wikipedia, which is confirmation-only).
* The change-date poll is manual; no scheduler exists. OpenLigaDB gives no availability guarantee and its data are unreviewed user entries.
* Housekeeping: the contact file sits in the repo-root `config/` folder (git-ignored by its own `.gitignore`, which itself shows as untracked); keep it uncommitted.
