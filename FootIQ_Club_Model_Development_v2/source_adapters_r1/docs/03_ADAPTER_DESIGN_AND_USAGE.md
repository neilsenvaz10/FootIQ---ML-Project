# 03 Adapter design, safeguards and usage

Code: `footiq_sources/` (standard library only; pandas is used only by `reconcile.py` and the runner, already installed). Version 1.0.0. Tests: `tests/test_adapters.py` (17 offline tests, all pass: `python -I -m unittest discover -s tests`).

| Module | Purpose |
|---|---|
| `common.py` | `StagingRecord` (source-independent schema), `AdapterConfig` (live off by default, real contact required), `HttpClient` (rate limit + jitter, retries with exponential back-off, Retry-After, request ledger, injectable transport for tests), `SnapshotStore` (write-once, read-only raw snapshots with sha256 + request metadata) |
| `identity.py` | Resolution against the frozen entity map: exact → normalised → reviewed alias; ambiguity reported, nothing guessed, no entity creation |
| `openligadb.py` | Parser + poller. Explicit `resultTypeKind`; regulation score only from `After90Minutes`; ET/penalty-only or unclassified finals are `completed_unclassified_score` and not label-eligible; statuses completed / upcoming / in_progress / past_date_no_result / unresolved; UTC kickoff, local time and time-zone id kept; source ids, `lastUpdateDateTime`, retrieval time, licence and attribution on every record. `poll()` = `getcurrentgroup` + `getlastchangedate` for the current and previous matchday, matchday data fetched only when the change date moved; `fetch_season()` = one request for a validated league-season. Only `bl1/2026` is on the validated list. |
| `wikipedia_matrix.py` | MediaWiki API client + matrix parser. Revision id/timestamp/permalink on every record; only clean `home–away` cells become results, annotated/odd cells stay `unresolved`; no dates or kickoff times are invented; `attach_schedule_dates` inherits a date from the openfootball schedule only when the (competition, season, home, away) fixture is unique, resolved by identity, and not later than the page's own update date, flags it `inherited_from_openfootball_schedule` and rejects ambiguous/unknown fixtures; `confirm_with_older_revision` requires the same score in a revision >= 24 h older; a page registry limits live fetches to the 15 reviewed titles (only the Premier League style is validated). |
| `reconcile.py` | Compares a source with the frozen openfootball universe: overlap, exact agreement, conflicts (reported only), recovered results, unresolved identities, missing kickoff times, summary |

## Safeguards
* Live access: `config/adapters.json` → `live_enabled:false`, `contact:null`. Any live call raises `LiveAccessDenied`. A contact string that is empty/"example"/"TODO" is rejected. No scheduler or background job exists.
* Isolation: snapshots go to `source_adapters_r1/snapshots/` only; the adapters never open the frozen universe, datasets, models or artifacts for writing (the reconciliation runner reads `V_universe.pkl` read-only).
* Retrieval limits: OpenLigaDB min. 2 s between requests (+1.5 s jitter) ≈ at most ~25/min vs the 60/min limit, change-date polling, no polling of matches in play more often than the terms allow (the poller is manual); Wikipedia ≥ 5 s apart, serial, `maxlag=5`.
* Never silent: any score disagreement is a `CONFLICT` row; ambiguous identities/fixtures are rejected with a reason.

## Usage (all manual, after the owner sets the contact and approves live use)
```
python -I run_offline_reconciliation.py            # offline, uses the stored snapshots (works today)
# live (blocked until config/adapters.json has a real contact and live_enabled=true):
OpenLigaDBAdapter().poll("bl1", "2026")            # change-date polling
WikipediaAdapter().revision_older_than(title); fetch_revision(title, revid)
```
