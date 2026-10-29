# Data sources, provenance and freshness

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

Verified on 2026-10-27 from `/api/meta`, `config/`, `data/` and the stored reports.

## 1. Datasets in use

| Dataset | Content | Origin and licence | Used for |
|---|---|---|---|
| Combined club matches (`FootIQ_ML_Data_Readiness/04d_COMBINED_CLUB_MATCHES_v1.0.csv`) and the openfootball club data | Club league and UEFA results and schedules, 2018-19 to 2026-27 for the five leagues | **openfootball**, CC0-1.0 (public domain) | League dashboards, standings, fixtures, club model history |
| Wikipedia (parts of the UEFA competition data) | Some UEFA competition results | **CC BY-SA 4.0**: attribution and share-alike required | Champions, Europa, Conference League results |
| `data/raw/international_results/results.csv` | National-team results (49,296 scored matches in the processed table) | **martj42/international_results**, CC0-1.0 | International Elo, Nations League, Copa América, World Cup history |
| 2026 World Cup results compiled in the repository | Verified group and knockout results, source URL stored per row | Licence **not asserted**; each row keeps its source URL | World Cup bracket and locked-result simulation |
| OpenLigaDB snapshot (Bundesliga, 55 rows of 2026-27 in the store) | Reviewed offline import | OpenLigaDB terms as recorded in the import report | Newer Bundesliga results (`source_system` shows it per row) |

Other third-party material in the repository (StatsBomb open data, API-Football samples) keeps its own terms; see `outputs/world_cup_data_inventory.md` and `World_Cup_Prediction_Model_Sources_and_Provenance.pdf`. The repository does not grant extra rights to third-party data.

## 2. Coverage in the results store

* `matches`: 223,510 rows, including 3,113 scheduled, 388 stored as awaiting a result, 205 awarded, 3 abandoned and 2,621 international rows; the five leagues have nine seasons each (2018-19 to 2026-27).
* All 2026-27 league seasons are **partial**. Ligue 1 2019-20 has 279 of 380 matches. Conference League has no 2026-27 rows. The Nations League ends at the 2025 finals. The 2026 World Cup final is not in the data.
* 273 rows that failed validation sit in a `quarantine` table instead of the results.

## 3. Provenance

Every match row stores its source system, licence, first-seen and last-changed time, change count and a content hash; `match_sources` links each row to the snapshot it came from. The production import (2026-10-25) and an earlier rehearsal are documented in `docs/mini-project/PRODUCTION_IMPORT_REPORT.md` and `OPENLIGADB_IMPORT_REHEARSAL.md`. The UI shows the source next to results and in the "About the data" section of the Models page.

## 4. Freshness limits (as of the stored data)

* Newest stored result: **2026-10-24** (Bundesliga). The dashboard says "Historical data, not live" everywhere.
* Four of the five leagues are reported **stale** by `/api/sync/status` (no approved source has confirmed them recently; matches whose date has passed have no verified result). The Home banner, Matches, Leagues and Predictions show this and mark affected forecasts **provisional**.
* Prediction history ends at 2026-10-24 for clubs (pooled; Serie A's newest verified result is 2026-09-20) and 2026-06-02 for internationals (`/api/meta` → `data_through`).

## 5. Synchronisation safeguards

* `config/sync.json`: `live_enabled: false`. With it off, the start-up check only writes a `sync_runs` row with outcome `skipped_live_disabled` and makes **no network request**.
* One approved source (OpenLigaDB, Bundesliga only), a contact string is required in `config/contact.local` (never displayed) before any request could be made, and a `stale_after_hours` of 72.
* Imported data would be validated, stored with provenance and logged; football-data.org is documentation only (no account, no key).
* Enabling live access needs a separate, explicit approval; none was given or used.
* **Observed side effect to know about:** before Phase 4.8B, starting the backend against the production store appended one `sync_runs` row (one on 2026-10-27) even with live access off. The file was already in WAL mode since the 2026-10-25 import. Fixed in 4.8B: a disabled sync now writes nothing; see `docs/mini-project/phase4/P4_8B_CHECKPOINT_REPORT.md` §2. No match data was altered.
