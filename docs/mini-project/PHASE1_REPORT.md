# Phase 1 report: SQLite store, offline baseline import, sync framework

Date: 2026-10-25. Scope: Phase 1 of [UPGRADE_PLAN.md](UPGRADE_PLAN.md) under your approved decisions. **No network request was made at any point in this phase**: the sync system ships with live access OFF, and every test replays the read-only OpenLigaDB pilot snapshot (retrieved 2026-10-21) that was already in the repository. Nothing is staged, committed or pushed. No frozen model, research folder or CSV baseline was modified.

## 1. What was implemented

| Piece | Where | Notes |
|---|---|---|
| SQLite schema (13 tables) | `app/store/db.py` | `matches`, `match_sources` (provenance), `source_snapshots` (sha256), `teams`, `team_aliases`, `competitions`, `sync_runs`, `sync_errors`, `quarantine`, `source_state`, and **empty** `forecast_runs`, `forecasts`, `simulation_runs` for Phases 2-3. Status vocabulary is enforced by a CHECK constraint: `completed, awarded, abandoned, scheduled, awaiting_result, postponed, cancelled`. |
| Offline baseline import | `app/store/baseline.py`, `app/store/build.py` | `python app/store/build.py [--fresh]`. 15 s. Idempotent. Input files are read-only; their sha256 is stored. |
| Read views | `app/store/views.py` | Dashboard frame (identical to `matches.csv`), model-universe frame (identical to the frozen pickle), per-competition freshness. |
| Sync framework | `app/store/sync.py`, `config/sync.json` | Ingestion with identity resolution, conflict quarantine and provenance; start-up check (non-blocking thread, 5 s delay) and low-frequency periodic check (60 min); status computation; stale fallback. **`live_enabled` is false.** |
| App wiring | `app/main.py`, `analytics.py`, `predict.py` | The app uses the store when `data/footiq.sqlite` exists and falls back to the CSV and the pickle when it does not (`FOOTIQ_USE_STORE=0` forces the old path). New endpoint `GET /api/sync/status`. After a sync that changed data, derived views and the prediction *history* (not the model weights) are rebuilt in the background. |
| UI | `frontend/src/components/SyncStatus.jsx` | A bar on every page: Latest match result, Last updated, Sync on/off, number of stale leagues, expandable per-competition table with reasons and source attribution. Never says "live". |
| Tests | `tests/test_store.py` (20), plus 2 new frontend tests | See section 2. |

Design choices worth knowing:
* **`model_home_entity` / `model_away_entity`.** The frozen universe uses identity-corrected club ids that differ from the dashboard source in 795 baseline rows (for example `SRCSCOPED|...` ids in lower leagues). The store keeps both so that the dashboard and the models each see exactly what they saw before.
* **`awaiting_result`** is a new status for matches whose date has passed with no result in any approved source. It replaces the plan's `live_unknown` so that nothing can be mistaken for "live".
* Baseline rows are never rewritten by a source that merely agrees with them: agreement adds a `confirmation` row in `match_sources`; a disagreement goes to `quarantine` and changes nothing.
* A single switch (`live_enabled` in `config/sync.json`) enables live access; a real contact string is additionally required by the adapter safeguards. The older `adapters.json` flag stays false and is untouched.

## 2. What was verified

| Check | Result |
|---|---|
| Baseline import | 219,954 matches (216,553 model-universe rows, 780 dashboard-only, 2,621 international), plus 3,556 fixtures; 216 fixtures quarantined for review (174 with team names that do not resolve to a known club, 42 that duplicate an already completed match). The imported universe has the exact sha256 recorded in `FROZEN.json` (`1c4d758b...`). |
| Dashboard parity | The store view equals `data/miniproject/matches.csv`: 20,449 rows, all 21 columns, byte for byte. Audit and season-coverage computed from the store equal the CSV files. |
| Model-universe parity | `universe_frame` from the store equals the frozen pickle's (`DataFrame.equals`). |
| Prediction parity | Club v1 and v2-r1 probabilities and the feature hash from a store-built state equal those from the frozen pickle for Premier League and Serie A fixtures. The existing 29 app tests also pass on the store-backed path. |
| Provenance | Every match has at least one `match_sources` row with a licence; every snapshot has a 64-character sha256. |
| Idempotency | Re-running the baseline import: 0 inserted, 0 updated, 219,954 unchanged, `change_count` unchanged. Replaying the same OpenLigaDB payload twice: second run 0 inserted, 0 updated, 0 quarantined, no duplicate rows, one `match_sources` row per match. |
| Pilot replay | 306 records: 36 confirmed identical to the baseline, **18 missing Bundesliga results recovered** (2026-10-09 to 2026-10-18), 0 conflicts, 0 unresolved identities. This reproduces the pilot's recorded outcome. Only those 18 rows changed; the 36 baseline rows are untouched. |
| Chronology / leakage | After replaying the 18 new results, the probabilities and feature hash for a fixture on 2026-10-09 are unchanged (results dated that day or later are not used); a fixture on 2026-10-19 does change. |
| Conflict, unresolved team, missing 90-minute type | Each goes to `quarantine`; stored data is not overwritten. |
| Safety | With live access off, `check_once` records `skipped_live_disabled` and makes zero requests. With a fake network, the live path requests only `api.openligadb.de` endpoints for `bl1/2026` (1 request on the first run, then at most 5 per check: current group, change dates, changed matchdays), spaced by the rate limiter, and a repeat finds nothing to change. A 503 leaves cached data untouched, records an error and marks the league stale. No contact string means no request. |
| Frozen artifacts | Hashes of club v1, club v2-r1 files match `FROZEN.json` (the six JSON files are compared allowing the known line-ending difference) before and after all tests. |
| Real server | The backend starts and answers immediately; the start-up check runs in its own thread and logged `skipped_live_disabled` with 0 requests; `data/snapshots/` was not created (no payload was fetched). |

**Test totals:** backend 77 passed (28 existing research tests + 29 app tests + 20 new store/sync tests); frontend 39 passed with the live contract tests (31 without), including 2 new tests for the freshness bar; production build passes.

## 3. Which leagues remain stale

State today (from `GET /api/sync/status`):

| Competition | Latest result in the store | Played but missing | Scheduled | State | Why |
|---|---|---|---|---|---|
| Bundesliga | 2026-09-20 | 18 (since 2026-10-09) | 252 | stale | OpenLigaDB is approved, but live access is off, so it has not synced yet |
| Premier League | 2026-09-20 | 20 (since 2026-10-10) | 310 | stale | no approved fresh source |
| La Liga | 2026-09-20 | 20 (since 2026-10-09) | 291 | stale | no approved fresh source |
| Serie A | 2026-09-20 | 20 (since 2026-10-10) | 310 | stale | no approved fresh source |
| Ligue 1 | 2026-09-20 | 18 (since 2026-10-09) | 243 | stale | no approved fresh source |
| UEFA competitions, Nations League, Copa America, World Cup | their last historical dates | n/a | none | stale / historical | no fixtures or fresh source |

After you enable live access, the Bundesliga is expected to become fresh (the replay shows the 18 results arrive). The other four leagues stay stale until a source is approved.

## 4. Sources that would be contacted, and the approval check

Nothing is contacted today. If you set `live_enabled: true` in `config/sync.json` (and the contact string in `config/contact.local` or `FOOTIQ_CONTACT` is the one you want sent in the User-Agent), the application would contact **exactly one host**:

| Host and endpoints | Purpose | Frequency | Within your approvals? |
|---|---|---|---|
| `https://api.openligadb.de/getmatchdata/bl1/2026` | first sync: the whole 2026-27 Bundesliga season | once (1 request) | Yes: item 1, Bundesliga only |
| `https://api.openligadb.de/getcurrentgroup/bl1`, `/getlastchangedate/bl1/2026/{n}` (current and previous matchday) | cheap freshness check | per check: 3 requests | Yes |
| `https://api.openligadb.de/getmatchdata/bl1/2026/{n}` | only for a matchday whose change date moved | at most 2 per check | Yes |

Limits applied: at least 3 s between requests (plus jitter), retries with exponential back-off honouring `Retry-After`, a descriptive User-Agent with your contact, snapshots saved with sha256, request ledger in `data/snapshots/`, one start-up check (after a 5 s delay, in a background thread) and one check per 60 minutes while the app runs. The OpenLigaDB documentation asks for sparing use (poll the change date, fetch data only on change), which this follows; the 60 requests/minute limit is far above what is used. Attribution shown in the UI: "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0".

Not contacted and not wired: Wikipedia (confirmation-only, no adapter is connected in Phase 1), football-data.org, API-Football, any other provider. Premier League, La Liga, Serie A and Ligue 1 therefore have no network source at all.

## 5. What needs your approval next

1. **Enable live access for the Bundesliga**: set `live_enabled` to true in `config/sync.json` and confirm the contact string. I would then run one supervised check, show you the request ledger, and verify that the 18 results arrive.
2. **Source discovery for the other four leagues** (your priority item): I can run a *read-only verification pass* that makes a small number of requests to OpenLigaDB to see whether it carries `pl`/`bl1`-style shortcuts for the Premier League, La Liga, Serie A and Ligue 1 for 2026, and compare any results with the baseline. This needs your explicit go-ahead because it is a request beyond the Bundesliga approval. Other candidates (football-data.org free tier, others) need you to read their terms first.
3. Whether to proceed to **Phase 2 (gameweek predictions)** now, using the store and the existing schedule, with clear "provisional" flags because the three non-synced leagues miss earlier results.

## 6. Known limitations of Phase 1

* The store is 228 MB (git-ignored, rebuilt by one command). Provenance text could be slimmed later.
* The sync adds new Bundesliga rows only when OpenLigaDB team names resolve through the baseline alias table; unknown names are quarantined for review, not guessed.
* Kickoff times stay unknown for most baseline fixtures; OpenLigaDB supplies UTC times for the Bundesliga once synced.
* International predictions still use the existing rating CSVs; they are not store-backed in this phase.
* Matchday labels from the source can be out of chronological order (seen in La Liga); Phase 2 handles this in the gameweek selector.
