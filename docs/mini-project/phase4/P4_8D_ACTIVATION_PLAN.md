# Phase 4.8D: activation plan and readiness assessment (PLAN ONLY, nothing implemented or enabled)

Prepared 2026-10-27 after Phase 4.8C Stage 2. `live_enabled` is false, no scheduler is active, production is unchanged (physical `3641e4da…3922`, logical `e32d759b…f29d`). Every step below needs your separate approval.

## 1. League-by-league matrix

| | Bundesliga | Premier League | La Liga | Serie A | Ligue 1 |
|---|---|---|---|---|---|
| **Approved provider** | OpenLigaDB (approved; live off) | none for live; OpenLigaDB snapshot verified read-only | none for live; OpenLigaDB snapshot verified read-only | none | none |
| **Newest stored result** | 2026-10-24 | 2026-10-12 | 2026-10-21 | 2026-09-20 | 2026-09-20 |
| **Source (A1–A3, 2026-10-27)** | 306 fixtures, 63 finished, newest 25 Oct | 380 fixtures, 60 finished, newest 12 Oct; feed byte-identical to 25 Oct (provider lags) | 380 fixtures, 98 finished, newest 25 Oct | not queried | not queried |
| **Remaining data gaps after the proposed import** | 0 awaiting | 20 fixtures past date with no result in store or source (since 17 Oct) | 1 awaiting (since 10 Oct) and 5 results held for date disagreement | 20 awaiting; no source | 18 awaiting; no source |
| **Outstanding conflicts** | none | Bournemouth–Brentford (2–2 vs 2–1); Villa–Forest (contradictory); 31 date disagreements | 24 date disagreements | none known | none known |
| **Proposed production import** | 2 results (Hoffenheim 3–0 Leverkusen, Freiburg 1–3 Bayern); 2 rows change | 5 status-only rows (scheduled → awaiting result); **no results** | 4 results (Athletic 4–0 Getafe, Barcelona 1–2 Real Madrid, Celta 0–0 Betis, Real Sociedad 2–1 Levante); 4 rows change | nothing | nothing |
| **Ready for production import?** | **Yes**, after your approval, with backup and baseline v3 | Low value (no new results); the 5 status rows add nothing the app does not already show; recommend **skip** | **Yes, optional**, same procedure; dates and the 5 held results stay untouched | No | No |
| **Ready for automatic 6-hour refresh?** | **Candidate**, supervised trial first (see §3) | **No**: no approved live source; feed lags 15 days; conflicts open | **No**: no approved live source; 24 date disagreements open | **No**: no provider | **No**: no provider |
| **Failure handling** | §4 | not scheduled | not scheduled | n/a | n/a |
| **Monitoring** | §5 | manual verification only | manual verification only | n/a | n/a |
| **Rollback** | §6 | §6 (same) | §6 (same) | n/a | n/a |

## 2. Preconditions that already hold

Restart-aware 6-hour schedule with back-off (mocked-clock tests); store-level run lock; no writes when live sync is off; date-protected ingestion (a differing date is held, never applied); honest freshness fields; shared kickoff rule; two-part integrity baseline; offline rehearsal on private copies reproducing production exactly; snapshots with SHA-256; request ledger with an exact-URL allow-list.

## 3. Proposed 4.8D sequence (each step separately approved)

1. **Bundesliga two-result import into production** (rehearsed): copy `data/footiq.sqlite` with its sidecars to a timestamped backup, record its physical and logical hashes, import from the A1 snapshot only (no network), expected diff exactly the two rows in the report §6, verify logical-hash differences are limited to `matches` (2 rows), `match_sources`, `source_snapshots`, `sync_runs`; record **baseline v3**; clear the Home and Matches caches by restarting the API.
2. **Optional La Liga four-result import** with the same procedure (separate approval).
3. **Supervised live trial, Bundesliga only, on a private copy** (not production): `live_enabled` true in the copy's process only, 3 cycles with a short interval overridden for the trial (not 6 h), contact configured, request ledger reviewed after each, expected requests per cycle about 2–3 (current group, last change date, changed matchdays). Pass criteria: zero errors, no row outside the Bundesliga changes, back-off and lock behave, freshness fields correct.
4. **Decision gate:** only then consider enabling the 6-hour schedule for the Bundesliga in the real configuration (`live_enabled: true`, one league). Premier League, La Liga, Serie A and Ligue 1 remain out of `APPROVED` and therefore can never be requested by the scheduler.
5. Serie A / Ligue 1: no step until football-data.org answers in writing (draft email prepared, not sent).

## 4. Failure handling

| Failure | Behaviour (already implemented unless marked *new*) |
|---|---|
| No internet / DNS / timeout | run ends `error`, snapshot not written, no data change; back-off 12 h then 24 h (cap); app keeps serving stored data and marks it stale after 72 h |
| HTTP 429 / 5xx | same; never an immediate retry |
| Malformed or unexpected payload | whole payload rejected, nothing ingested, error recorded |
| Provider changes a date | held in quarantine (`DATE_DIFFERENCE`), not applied |
| Provider contradicts a stored score | quarantined (`CONFLICT`), stored score kept |
| Unknown team name | quarantined (unresolved identity), no fuzzy match |
| Two runs at once | store-level lock refuses the second; a crashed run's lock expires after 30 min |
| Process killed mid-import | the import is one transaction: all or nothing |
| Provider withdraws / terms change | remove the league from `APPROVED` (one line), back to "no approved source" |
| *New, proposed:* alert after 3 consecutive failures | status field `consecutive_failures` and a visible notice on the Leagues status panel |

## 5. Monitoring

`/api/sync/status` already reports per league: latest verified result, last successful source check, last import, last attempt and outcome, provider status, imported and held counts, history note, and `recent_checks`. Proposed additions for 4.8D: consecutive-failure count, quarantine count by reason, next scheduled check time, and a one-page log view of `sync_runs`/`sync_errors`. Review the request ledger (`data/snapshots/*/request_ledger.jsonl`) after each supervised cycle; compare logical hashes before and after every import.

## 6. Rollback procedure

* **Before any production import:** backup the three files (`footiq.sqlite`, `-wal`, `-shm`) after a `PRAGMA wal_checkpoint(TRUNCATE)` on a copy, and store the backup's physical and logical hashes beside the baseline.
* **Transaction level:** an import that fails part-way rolls back automatically (tested: logical hash identical after a rolled-back transaction).
* **File level:** stop the API, replace `data/footiq.sqlite` (and remove stale `-wal`/`-shm`) with the backup; verify the logical hash equals the recorded baseline (tested on a private copy: equal). Restart; the app rebuilds its history from the store.
* **Configuration:** set `live_enabled` back to false; the scheduler is inert again with no further action.
* **Record:** note the rollback in the checkpoint report; a rolled-back import never changes baseline v2.

## 7. Readiness assessment

| Question | Answer |
|---|---|
| Ready to import the 2 Bundesliga results into production? | **Yes** (verified against the live feed and rehearsed on a private copy), pending your approval |
| Ready to import La Liga's 4 results? | Technically yes; optional; same approval path |
| Ready to enable the 6-hour refresh for the Bundesliga? | **Not yet**: needs the supervised live trial on a copy first |
| Ready for any other league? | **No** |
| Biggest remaining risks | provider feed lag (Premier League 15 days), unresolved date disagreements (55) and score conflicts (2), football-data.org terms unanswered, the scheduler never exercised against the real network |
