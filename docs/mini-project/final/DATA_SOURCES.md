# Data sources, provenance and freshness

> **Final state (Phase 4.28):** FootIQ supports exactly six competitions (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, UEFA Champions League). This file was rewritten in Phase 4.28; the previous version is part of the phase history. Authoritative description: `FINAL_SYSTEM_GUIDE.md`.

Verified on 2026-10-28 from `/api/meta`, `config/` and the results store.

## 1. Sources in use

| Source | Content | Licence | Used for |
|---|---|---|---|
| openfootball | club league and Champions League results and schedules, 2018-19 to 2026-27 | CC0-1.0 | dashboards, standings, fixtures, club model history |
| Wikipedia | Champions League results and verified league results (newer matches) | CC BY-SA 4.0: attribution and share-alike required | results and fixtures imported after verification |
| OpenLigaDB | Bundesliga and La Liga, refreshed once at application start | ODbL: attribution required | newer results (`source_system` shows it per row) |
| football-data.co.uk, FixtureDownload | cross-check of dates and results | not stored or redistributed | offline verification only |
| StatsBomb open data | player datasets in `FootIQ_Dataset_Submission` only (not used by the application) | StatsBomb terms, credit required (`LICENSE.pdf` kept) | dataset submission; the raw clone was removed in Phase 4.28 (`FootIQ_Dataset_Submission/_raw_sources/STATSBOMB_RECONSTRUCTION.md`) |

The football-data.org API is not used and no token is stored. Archived competitions (Europa League, Conference League, World Cup, Nations League, Copa America) and their sources (martj42 international results, API-Football samples) are preserved on disk and not shown or served. Third-party data keeps its own terms; the repository grants no extra rights.

## 2. Coverage in the results store (2026-10-28)

| Competition | Completed | Upcoming | Awaiting result |
|---|---|---|---|
| Premier League | 80 | 300 | 0 |
| La Liga | 99 | 280 | 1 (postponed) |
| Bundesliga | 63 | 243 | 0 |
| Serie A | 80 | 297 | 3 (single-source results not applied) |
| Ligue 1 | 72 | 234 | 0 |
| Champions League, league phase | 54 | 90 | 0 |

The store holds 223,636 match rows (including archived competitions) and 273 quarantined rows. Every league has nine seasons (2018-19 to 2026-27).

## 3. Provenance

Every match row stores its source system, licence, first-seen and last-changed time, change count and a content hash; `match_sources` links rows to the snapshot they came from. Imports run through `app/store/uefa_import.py`, `league_results_import.py` and `reconcile_import.py`: dry run by default, a verified byte-identical backup for a production run, row validation, quarantine for failures. Reports: `docs/mini-project/phase4/P4_19` to `P4_24`.

## 4. Freshness

* The dashboard says "Historical data, refreshed once when FootIQ starts; nothing is live".
* `/api/data-freshness` gives per competition `startup_updated` (Bundesliga, La Liga) or `historical_only`, with the newest result date.
* Model history ends with the newest stored club result (26 October 2026).

## 5. Synchronisation safeguards

* `config/sync.json`: `sync_mode: startup`, OpenLigaDB for BUNDESLIGA and LALIGA only; one full-season request per league per start (two requests), at least 15 minutes between attempts; `FOOTIQ_DISABLE_SYNC=1` switches it off.
* football-data.org and the other leagues are not enabled; enabling them needs separate explicit approval and provider permission.
* A request ledger records every outbound request.
