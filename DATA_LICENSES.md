> **Publication snapshot, 29 October 2026:** This clean release tree has no production SQLite database or old project Git history. The active application covers five domestic leagues and the UEFA Champions League. World Bank indicator files, archived StatsBomb-derived tactical aggregates and their selected downstream reports/workbooks are withheld while redistribution rights remain uncertain. Archived international rebuilding/examples therefore need separately authorised inputs. Club models, their evaluation reports and all eight approved LFS inputs are retained unchanged. Follow `docs/mini-project/final/SETUP_AND_RUN.md` section 4a to rebuild locally. Attested mode remains explicit and is labelled **not independently reproducible**. No source-code licence is granted. See `PUBLICATION_NOTES.md` for the exact migration limits.

# Data licences, attribution and provenance (PROPOSED FINAL, Phase 4.37)

This file lists every data source used by FootIQ, what its licence or terms allow, what is included in the repository, what is not, and how to obtain the excluded data yourself. It is a good-faith record, **not legal advice**.
The project's own source code has **no licence yet** (decision pending; this file does not grant one). A source is called CC0 here only where the upstream licence text was read; where a page could not be read, the entry says so and the source is treated as **restricted**.
Terms were re-checked on 2026-10-29 unless stated otherwise.

## 1. Sources included in the repository

| Source | What we use | Licence / permission | How it was verified | Obligations |
|---|---|---|---|---|
| **openfootball** (github.com/openfootball) | club and cup results and schedules 2018-19 to 2026-27 (`FootIQ_ML_Data_Readiness/04a-04d`, `08`, `FootIQ_Dataset_Submission/02, 03, 09`, `V_universe.pkl`), the CC0 player extracts | **CC0 1.0** | `LICENSE.md` of 16 of the 17 cloned repositories hashed and read (`FootIQ_ML_Data_Verification/08_SOURCE_AND_LICENSE_AUDIT.md`); the 17th is StatsBomb (section 2) | none; credit given anyway, commits pinned in `FootIQ_Dataset_Submission/RAW_SOURCES_MANIFEST.csv` |
| **martj42/international_results** | national-team results (archived international pipeline) | **CC0 1.0** | the repository's own `LICENSE` file | none; credit Mart Jurisoo |
| **Wikipedia (English)** | Champions League 2026-27 league phase, 2026-27 league results grids, ~1% of the club training rows (`source_system = wikipedia`), World Cup squad pages, wikitext cache | **CC BY-SA 4.0** | page title and revision id stored per row (`page_revid`, `wikipedia_revision`) | **attribution** (page, revision, authors via history) and **share-alike** for adaptations; files with Wikipedia-derived rows are offered under CC BY-SA 4.0 (scope question: section 6.1) |
| **OpenLigaDB** (openligadb.de) | Bundesliga and La Liga season feeds, saved Premier League / La Liga snapshots, 61 rows of the store | **ODbL 1.0**; the API page states: "Die ueber diese API bereitgestellten Daten stehen unter der Open Database License (ODbL)" (verified 2026-10-29) | statement on openligadb.de; the licence page `/lizenz` did not render its text, so the attribution wording below comes from the adapter (`footiq_sources/openligadb.py`) and was not re-read from the site | **attribution**: "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0"; share-alike for a derivative database |
| **World Bank Open Data** | GDP per capita and population (archived international model, `data/raw/worldbank`) | World Bank dataset terms: **CC BY 4.0 unless a dataset is labelled otherwise**, plus additional terms; some indicators are third-party data with their own limits (verified on the World Bank terms page 2026-10-29) | the labels of these two indicators (GDP per capita, total population) were **not** looked up | credit the World Bank and flag changes; do not imply endorsement or use its name or logo; confirm the two indicator labels (section 6.3) |
| **FootIQ's own work** | frozen models, evaluation reports, feature tables derived from the sources above, documentation, identity mappings, reviewed team aliases, sanitized evidence, CC0 extracts | no licence chosen | | derived datasets inherit the conditions of their sources |

## 2. Sources NOT redistributed

| Source | What the terms say (as read) | Status | What we derived from it | How to obtain it yourself |
|---|---|---|---|---|
| **StatsBomb Open Data** | the Public Data User Agreement (`FootIQ_Dataset_Submission/_raw_sources/statsbomb_open_data/LICENSE.pdf`) forbids to "edit, distort, distribute, reproduce, sell or in any way provide the data to any external or third party" (1.2.1), forbids commercial exploitation (1.2.2) and requires the StatsBomb logo on published analysis (1.4) | **restricted** | player and player-match statistics (`FootIQ_Dataset_Submission/04, 05, 06, 07, 08, 14` full tables, `player_form_v1/*STATSBOMB*`), `data/raw/statsbomb`, tactical adjustments in archived international model tables | `git clone https://github.com/statsbomb/open-data.git`, commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`; rebuild with `FootIQ_Dataset_Submission/_build/build_players_statsbomb.py` |
| **API-Football (api-sports.io)** | the terms page returned HTTP 403 to automated reading on 2026-10-29, so the terms were **not read**; search results only show that resale of its data without permission is not permitted | **restricted (unverified)** | lineups, odds, fixture identifiers and statuses, snapshots for the archived World Cup / friendlies pipeline (`data/processed/*` files listed in `data/supervised/phase4/p437/out/restricted_removal_plan.csv`), 99+9 World Cup 2026 rows in the dashboard CSV (removed from the published copy) | own key in `.env` (`API_FOOTBALL_KEY`), `scripts/api_football_client_v24.py` |
| **football-data.co.uk** | "its use is intended for private individuals only"; excludes commercial use and "data training products using automated bots/scrapers/AI"; no redistribution grant (data.php, read 2026-10-29) | **restricted** | cross-check scores and dates used by the importers in standard mode; raw copies (local only) | download the season CSVs yourself for private use |
| **FixtureDownload** | content may not be distributed, reproduced or stored on another site except personal printing / download and personal copies to individuals with credit; commercial use needs written permission (terms, read 2026-10-29) | **restricted** | cross-check dates and scores (local only) | fixturedownload.com, for private use |
| **football-data.org API** | the terms page (`/terms`) returned HTTP 404 on 2026-10-29; terms **not read**; permission requested by e-mail was not granted (`docs/mini-project/phase4/P4_8C_FOOTBALLDATA_EMAIL_DRAFT.md`); token never stored | **restricted (unverified)** | provider dates used for the Phase 4.13 date investigation (local only) | register at football-data.org and set `FOOTBALL_DATA_API_TOKEN` |
| **League regulation documents** (Premier League Handbook, LFP, FIGC, RFEF, DFL) | copyrighted public documents | not redistributed | verified rule profiles `config/season_rules.json` (URL and SHA-256 per document) | URLs and hashes in `config/season_rules.json` |
| **FIFA ranking page copy**, **news articles** (Guardian, AP, others) | no redistribution permission verified | not redistributed | 22 + 2 World Cup 2026 result rows in the dashboard CSV (removed from the published copy); one HTML copy `data/raw/fifa` | original sites |
| **RSSSF pages** | own terms | not redistributed | `_raw_sources/*/rsssf` | original site |

Removing a column from a restricted source is **not** treated as granting redistribution rights: every sanitized file below was checked by value (section 3).

## 3. What the repository contains for each data category

| Category | In the repository | Basis |
|---|---|---|
| openfootball-based datasets and the baseline store inputs | yes (8 large files through Git LFS; 04d and the training files derived from it also carry 2,969 Wikipedia rows, so they are offered under CC BY-SA 4.0 for those rows; `V_universe.pkl`, `02`, `04a` are openfootball-only; all 8 checked: no restricted-source marker) | CC0, plus CC BY-SA 4.0 for the Wikipedia rows |
| Wikipedia-derived rows (UCL league phase, 2026-27 results, training rows) | yes, labelled `CC BY-SA 4.0` per row | CC BY-SA 4.0 |
| Saved OpenLigaDB snapshots | yes, `data/snapshots/openligadb`, `p48c`, `investigation` | ODbL 1.0 |
| Published evidence (`data/evidence/published`) | yes | Wikipedia, openfootball, OpenLigaDB values only; classification `insufficient_redistributable_evidence` for all 175 rows |
| **Attested lists** (`data/evidence/published/ATTESTED_RECORDS.csv`, `UNSUPPORTED_RESULTS.csv`) | yes | 80 results + 31 fixture-date corrections that depend on the opt-in attested mode, each marked `independently_reproducible = false`, with Wikipedia revision, evidence id and review decision; and the 3 results that stay missing. The private cross-check behind the attestation is **not** public evidence and no restricted value is included |
| **Sanitized evidence CSVs** (`data/evidence/sanitized`, 12 files) | yes | only whitelisted columns; a date or score survives only if a redistributable source in the same row carries it; derived columns (`diff_days`, `shift_days`) dropped; free text with provider names dropped; manifest with SHA-256 and withheld counts |
| **CC0 player extracts** (`FootIQ_Dataset_Submission/cc0_extracts`) | yes | row-level provenance: only rows whose source is openfootball or martj42; zero StatsBomb cells; originals unchanged |
| Dashboard CSVs `data/miniproject/*` | yes, **sanitized copies** (130 World Cup 2026 provider / news / FIFA rows removed) | the World Cup 2026 rows were not redistributable |
| Frozen models, evaluation reports, documentation | yes | own work; derived-data conditions above |
| Original restricted staging, raw provider copies, API-Football and StatsBomb data, regulation PDFs, FIFA copy | **no** | section 2 |
| The production SQLite store | **no** | a single file mixing ODbL and CC BY-SA rows has no licence that satisfies both share-alike clauses (section 6.2); it rebuilds in about 30 s from the repository instead |

## 4. How to rebuild
- **Baseline store** (data to 2026-09-20): `python app/store/build.py`.
- **Current six-competition state, from the repository alone:** `python scripts/rebuild_current_state.py <folder> snapshot` replays the OpenLigaDB snapshots, the Wikipedia-derived Champions League inputs and the published evidence, then applies the **attested** Wikipedia results (see 4a). Compared with the maintainer's store: 17,300 of 17,303 six-competition rows identical; **3 results (1 La Liga, 2 Ligue 1) are not reproduced** because their played day came only from a restricted source; the 130 World Cup 2026 rows are absent by design. All five domestic simulators can run (Premier League, La Liga, Bundesliga ready; Serie A, Ligue 1 provisional).
- `... published` applies only results confirmed by two redistributable sources: 83 results and 31 Premier League date corrections are then missing and three simulators are not eligible.
- `... local` needs the maintainer's local restricted staging and reproduces the store exactly.
- The application refreshes the Bundesliga and La Liga from OpenLigaDB once per start (`config/sync.json`; needs a contact string in `config/contact.local`; `FOOTIQ_DISABLE_SYNC=1` runs offline).

### 4a. Attested evidence
`--evidence attested` is an explicit, never-default mode used only by the snapshot rebuild. It accepts a result when Wikipedia (CC BY-SA 4.0) supports it, no redistributable source disagrees, the date is the stored fixture date or is carried by a redistributable source, and the row carries the maintainer's attestation (`restricted_cross_check_used_in_production = true`) that a private cross-check agreed. Every such row is stored with the provenance text "attested snapshot evidence ... NOT independently reproducible from public data". No restricted value is stored or distributed.

## 5. Attribution to show
- Wikipedia contributors, English Wikipedia (CC BY-SA 4.0), with page title and revision id as recorded in the data.
- openfootball (CC0 1.0), Mart Jurisoo / martj42 (CC0 1.0): no attribution required, given as courtesy.
- "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0".
- World Bank Open Data (CC BY 4.0), no endorsement implied.

## 6. Unresolved questions
1. **Wikipedia share-alike scope:** whether extracted scores are adaptations (CC BY-SA applies) or uncopyrightable facts was not decided; files with Wikipedia rows are treated as CC BY-SA 4.0 (cautious reading).
2. **ODbL and CC BY-SA in one database:** no single licence satisfies both share-alike clauses for a mixed SQLite file, so none is published.
3. **World Bank indicators:** confirm that the two indicators carry the default CC BY 4.0 label.
4. **StatsBomb-derived aggregates:** archived team-rating tables carry only the label "statsbomb_..." (no StatsBomb rows) but their tactical adjustments were computed from StatsBomb events; whether such aggregates are covered by section 1.2.1 is unresolved.
5. **API-Football and football-data.org terms** could not be read (403 / 404); treated as restricted until read and, if needed, permission is obtained.
6. **Files already in the public Git history:** 68 API-Football-derived files, 134 StatsBomb files, 1 FIFA page copy and 1 news-compiled file (commit `edb6e0a`), and the unsanitized dashboard CSVs (`c3a6fb1`) are in commits already on the remote; removal going forward does not remove them from history.
7. **Source-code licence:** not chosen.
