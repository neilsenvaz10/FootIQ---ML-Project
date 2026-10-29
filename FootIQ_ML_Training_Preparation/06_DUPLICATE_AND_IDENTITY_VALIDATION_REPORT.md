# 06 Duplicate and identity validation report (v1.1, generated 2026-10-20 23:14)

## Duplicates
| Check | Result |
|---|---|
| Russian Premier League 2019-20 duplicate | `europe/russia/2019-20_ru2.txt` is titled "= Russia 1. Division 2019/20" but its body is **identical line for line** to `2019-20_ru1.txt` ("= Russia Premier League 2019/20"): 240 of 240 fixtures equal (date, teams, score); both files list the same 16 clubs; `body_lines_identical_after_title = True`. All 240 ru2 rows were removed (evidence: `evidence_russia_2019_20_duplicate.json`). The real second tier is not available for that season. |
| Same competition, same day, same pair (reversed orientation) | 8 rows excluded as unresolvable (`evidence_ambiguous_same_day_duplicates_excluded.csv`): e.g. Barrow v Boreham Wood and Boreham Wood v Barrow both dated 2016-03-08 in one National League file; two-leg Mexican play-off legs printed on one date |
| Duplicate record ids / (competition, season, date, home, away) / (date, pair, score) across competitions in the final dataset | 0 / 0 / 0 (tests in file 07) |

## Identity handling in the approved scope
* Canonical club id: exact normalised alias match inside one country against the curated `openfootball/clubs` tables. Share of match sides with a canonical id: 68.8%; the rest keep source-scoped ids, consistent inside each league.
* **Wrong merges found and withdrawn:** 12 (club, spelling) pairs had two spellings of one canonical club inside the same league-season (e.g. `CSKA Sofia` / `CSKA 1948 Sofia`, `FC Universitatea Craiova` / `CS Universitatea Craiova`, `Gazişehir Gaziantep FK` / `Gaziantep FK`, `FC Marchfeld Mannsdorf` / `Donauauen`). The canonical id was withdrawn for those spellings; they use source-scoped ids and are flagged `identity_review_flag` (rows touched: 795). Some pairs are really one renamed club (Gaziantep, Marchfeld): their history is therefore split (conservative, documented), not merged by name similarity. List: `identity_spelling_conflicts_unmerged.csv`.
* **Same-league split suspects** (an unresolved entity whose near-twin shares a competition; 14 pairs, e.g. `1.FC Slovácko` vs `1. FC Slovácko`): the unresolved entity is flagged; the resolved twin is flagged only when the two names are identical after removing punctuation and spaces. Most pairs are different clubs (reserve teams `II`, `FC United of Manchester`), so nothing was merged. Rows with a flag stay in training but are excluded from primary evaluation: 1,055 rows.
* Cross-border clubs: AS Monaco is one entity (`CLUB:MCO:as-monaco`) across Ligue 1 and cups; Cardiff, Swansea, Wrexham, Newport are single `CLUB:WAL:` entities across the English pyramid.
* Same-name clubs in different countries (e.g. `Liverpool`, `River Plate`) are separate entities by construction.

## Elo limitation caused by disconnected competitions
The rating graph (confirmed 90-minute results of all openfootball competitions) has 100 connected components; the largest holds 1,885 of 2,883 clubs and 71.5% of the final dataset rows (full-history count, informational). Leagues outside it (e.g. Brazil, MLS, Liga MX, Argentina, Japan, China, Nigeria) form islands, because their clubs never meet clubs from the main component in the verified data. Handling:
1. `elo_diff` is only produced when home and away are already connected in the graph (`pair_connected_asof`, required for eligibility; 6 rows removed).
2. Absolute `home_elo` / `away_elo` are comparable only inside a component: do not interpret them across islands; use `competition_id` (fitted on train) or train per league group, and report metrics per league group.
3. No league-strength adjustment was invented.
