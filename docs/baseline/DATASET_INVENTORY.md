# Dataset inventory guide

Full per-file profiles: [JSON](capture_2026-10-20/dataset_inventory.json), [CSV overview](capture_2026-10-20/dataset_inventory.csv). Embedded source fields: [provenance details](DATASET_PROVENANCE_DETAILS.json). Year-only JSON fields: [supplement](YEAR_RANGE_SUPPLEMENT.json).

| File | Bytes | Rows | Columns | Missing-token cells | ISO date fields/ranges |
|---|---:|---:|---:|---:|---|
| `data/raw/international_results/results.csv` | 3,720,482 | 49,368 | 9 | 144 | date: 1872-11-30 to 2026-06-27 |
| `data/processed/international_matches.csv` | 8,206,008 | 49,296 | 25 | 0 | date: 1872-11-30 to 2026-06-02 |
| `data/processed/team_elo_match_history.csv` | 11,029,669 | 98,592 | 16 | 0 | date: 1872-11-30 to 2026-06-02 |
| `data/processed/team_elo_latest.csv` | 12,909 | 336 | 5 | 0 | last_match_date: 1923-02-25 to 2026-06-02 |
| `data/processed/team_recent_form_latest.csv` | 43,396 | 336 | 22 | 0 | last_match_date: 1923-02-25 to 2026-06-02 |
| `data/processed/statsbomb_worldcup_matches.csv` | 15,063 | 128 | 12 | 1 | match_date: 2018-06-14 to 2022-12-18 |
| `data/processed/statsbomb_team_event_summary.csv` | 28,329 | 256 | 23 | 0 | match_date: 2018-06-14 to 2022-12-18 |
| `data/processed/worldcup_2026_matches.csv` | 8,096 | 104 | 8 | 32 | date: 2026-06-11 to 2026-07-19 |
| `data/processed/worldcup_2026_teams.csv` | 575 | 48 | 2 | 0 | No ISO date field |
| `data/processed/player_impact_v21.csv` | 378,467 | 1,246 | 29 | 0 | No ISO date field |
| `data/processed/worldcup_matchday_v29_snapshots.csv` | 106,997 | 220 | 39 | 879 | snapshot_timestamp_et: 2026-06-11 to 2026-07-19; date: 2026-06-11 to 2026-07-19 |
| `data/processed/matchday_validation_v210.csv` | 48,303 | 103 | 47 | 287 | date: 2026-06-11 to 2026-07-18; snapshot_timestamp_et: 2026-06-11 to 2026-07-18 |
| `data/processed/worldcup_2026_knockout_results_verified.csv` | 3,715 | 31 | 8 | 27 | date: 2026-06-28 to 2026-07-18 |

## Interpretation and limits

- 174 CSVs, 182 JSONs, 10 workbooks, four HTMLs, one pickle and 101 Markdown reports are profiled as 472 data/report assets; no profiling errors. HTML/Markdown/pickle are non-tabular, so row/column missingness is not applicable. Nested JSON table counts overlap; never sum them as match counts. Workbooks are read-only and first-row-header assumptions are explicit per sheet.
- Missingness separately counts blanks/nulls and common textual missing tokens. Zero/False are valid values. Empty source-error, optional shootout or Pass-grade fields may be intentional; missing-cell totals are not defect counts. Formula cells are not recalculated, source retrieval dates are not inferred from filesystem mtimes, and no hidden future availability is invented.
- Raw results have 49,368 rows through 2026-06-27, with 72 missing home and away scores. The 49,296 scored processed records end 2026-06-02. This is a scored/unscored distinction, not evidence of a refreshed scored training set.
- The 336-team Elo table includes inactive/historical teams; some last-match dates are as early as 1923. A row called "latest" does not mean current worldwide coverage.
- Six data contracts, player availability overrides, v2.5 confirmed lineups and the latest v2.9 lineups CSV are header-only. Archived lineup data may exist elsewhere; header-only current tables do not establish general live coverage.
- Player impact has 1,246 rows without blank fields, but model-derived fallbacks can still produce fully populated heuristic values. Completeness does not establish measured player performance.
- Matchday validation has missing provider scores/results and nullable Pass grading; all per-column counts are retained. Original source records have not been externally reverified.
- Inherited inventory claims earlier StatsBomb event/360 downloads; this archive contains metadata/lineups and processed summaries, not the raw event/360 layers.
