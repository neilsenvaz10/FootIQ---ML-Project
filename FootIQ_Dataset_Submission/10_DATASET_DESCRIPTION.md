# FootIQ Dataset Submission - Dataset Description

Prepared 2026-10-20 (extraction date). Scope: data collection, verification, cleaning and export only. No application code, models, databases or git operations were touched. The Milestone 1 baseline files were read but never modified.

## 1. What is in this package

| dataset_file | records | earliest_date | latest_date |
|---|---|---|---|
| 01_Historical_International_Matches.csv | 49362 | 1872-11-30 | 2026-06-02 |
| 02_Historical_Club_Matches.csv | 223625 | 1888-09-08 | 2026-05-31 |
| 03_Recent_Match_Results.csv | 1482 | 2026-06-03 | 2026-10-06 |
| 04_Football_Players.csv | 25288 | 1958-06-24 | 2026-05-25 |
| 05_Player_Match_Statistics.csv | 180172 | 1958-06-24 | 2026-05-25 |
| 06_Teams.csv | 5729 | 1893-04-01 | 2027-05-30 |
| 07_Competitions.csv | 409 | 1892-04-30 | 2027-05-30 |
| 08_Player_Team_Memberships.csv | 34277 | 1958-06-24 | 2026-05-25 |
| 09_Upcoming_Fixtures.csv | 3793 | 2026-06-05 | 2027-05-30 |
| 14_StatsBomb_Match_Index.csv | 3961 | 1958-06-24 | 2025-07-27 |

Additional files: `14_StatsBomb_Match_Index.csv` (supplementary, referenced by 05), `QA_Reports/` (validation checks and the records excluded or flagged), `RAW_SOURCES_MANIFEST.csv` (commits and checksums of downloaded raw sources), `_build/` (the Python scripts that produced everything - re-runnable).
The raw downloads live in `_raw_sources/` next to the cleaned CSVs (not included in the ZIP because of size; the manifest lists exact repository commits).

### Not generated (reported unavailable - nothing was fabricated)

* UEFA Super Cup, domestic super cups and the FIFA Intercontinental Cup: no authorised open source containing them was found. The Club World Cup (2000, 2005-2023, 2025) is the only global club competition present.
* Historical player statistics (shots, passes, tackles, interceptions...) for Premier League, La Liga, Bundesliga, Serie A and Ligue 1: no authorised open source. Event-level statistics exist only for the StatsBomb open-data subset below.
* Paid APIs and sites that prohibit automated use were not used (see `13_SOURCE_COVERAGE_MATRIX.csv`).

## 2. Definitions used across files

* **Historical** = completed matches dated on or before 2026-06-02 (the last scored date of the Milestone 1 baseline). **Recent** = completed matches 2026-06-03 to 2026-10-20 (file 03). The two never overlap.
* **Latest dates of the sources (not the same as 2026-10-20):** international source latest completed match **2026-10-06**; club sources latest completed match **2026-09-20** (many competitions end earlier - see `latest_scored_match_date` in 07). Results after those dates are not in the sources (the latest openfootball commits, e.g. England on 2026-10-15, contain no later results).
* **Completed vs unscored:** an international record always has a score (the upstream file has no unscored rows). Club records without a result, cancelled/postponed matches and scheduled matches are never in 01/02/03; fixtures dated after 2026-06-02 are in `09_Upcoming_Fixtures.csv` (3793 rows; `fixture_status` says upcoming vs past-dated-without-result), earlier unscored club records are in `QA_Reports/QA_Club_Records_Not_Scored_Or_Nonstandard.csv`.
* **Score semantics.** International (01/03): score includes extra time and excludes penalties; penalty shootout winner is a separate column; regulation vs extra time cannot be separated. Club (02/03): `*_goals_regulation`, `*_goals_after_extra_time`, `*_penalties` are separate columns; `decided_in` is regulation / extra_time / penalties; `final_match_winner_side` is the winner of that single match (penalties > extra time > regulation) and is **not** two-legged-tie advancement, which the sources do not provide and which was not inferred.
* **Identifiers.** Source IDs are preserved where they exist (StatsBomb IDs, row/line numbers of every record). Where the sources have no IDs, team and player IDs are keys scoped to the source (`INT|name`, `ENG|Arsenal FC`, `OFP|team|name`). Teams/players that merely share a name are **not** merged; `name_match_key_hint` and `same_name_key_as_other_team_ids` in 06 only flag candidates for later manual resolution.
* Files are UTF-8 with BOM (opens correctly in Excel); dates are ISO-8601.

## 3. Coverage actually delivered

### 3.1 International football (01 + 03)

| competition_category | matches | first | last |
|---|---|---|---|
| continental_or_regional_tournament | 6441 | 1916-07-02 | 2026-01-18 |
| friendly | 18102 | 1872-11-30 | 2026-06-02 |
| nations_league | 1080 | 2018-09-06 | 2025-06-08 |
| other_international_tournament | 6835 | 1884-01-26 | 2026-06-02 |
| qualification | 7169 | 1956-02-25 | 2026-03-31 |
| world_cup_finals | 964 | 1930-07-13 | 2022-12-18 |
| world_cup_qualification | 8771 | 1933-06-11 | 2026-03-31 |

* 01: 49,362 matches 1872-11-30 to 2026-06-02; 03 adds 583 matches 2026-06-03 to 2026-10-06.
* 688 historical matches have a recorded penalty shootout.
* The refreshed upstream file supersedes the local baseline snapshot: all 72 matches that were unscored in the baseline now have scores (World Cup 2026 group games from 2026-06-11), two further scores changed (Tahiti v New Caledonia, 1974-02-17), and the `China PR` -> `China` rename accounts for most of the 725 baseline-only keys. `in_local_baseline` shows which rows exist in the baseline.

### 3.2 Club football (02 + 03 + 09)

223,625 historical club matches from 160 competitions in 67 countries/regions (`07_Competitions.csv`). Key competitions:

| competition_name | first_season | last_season | n_seasons | n_scored | latest_scored_match_date |
|---|---|---|---|---|---|
| English Premier League | 1992-93 | 2026-27 | 35 | 13216 | 2026-09-20 |
| Spanish La Liga | 2012-13 | 2026-27 | 15 | 5389 | 2026-09-20 |
| German Bundesliga | 2010-11 | 2026-27 | 17 | 4932 | 2026-09-20 |
| Italian Serie A | 2013-14 | 2026-27 | 14 | 4990 | 2026-09-20 |
| French Ligue 1 | 2014-15 | 2026-27 | 13 | 4282 | 2026-09-20 |
| FA Cup | 2018-19 | 2024-25 | 7 | 981 | 2025-05-17 |
| EFL Cup (League Cup) | 2018-19 | 2024-25 | 7 | 646 | 2025-03-16 |
| Copa del Rey | 2020-21 | 2024-25 | 5 | 631 | 2025-04-26 |
| DFB-Pokal | 2018-19 | 2025-26 | 8 | 489 | 2025-10-29 |
| Coppa Italia | 2020-21 | 2024-25 | 5 | 259 | 2025-05-14 |
| French Coupe de France | 2024-25 | 2024-25 | 1 | 200 | 2025-05-24 |
| UEFA Champions League | 2011-12 | 2025-26 | 15 | 1997 | 2026-05-30 |
| UEFA Europa League | 2020-21 | 2024-25 | 5 | 815 | 2025-05-21 |
| UEFA Conference League | 2021-22 | 2024-25 | 4 | 576 | 2025-05-28 |
| FIFA Club World Cup | 2000 | 2025 | 21 | 225 | 2025-07-13 |
| Copa Libertadores | 2012 | 2026 | 15 | 2213 | 2026-05-28 |
| Copa Sudamericana | 2012 | 2025 | 14 | 1572 | 2025-04-24 |
| CONCACAF Champions Cup/League | 2010-11 | 2025 | 15 | 710 | 2025-05-01 |
| CAF Champions League | 2023-24 | 2024-25 | 2 | 284 | 2025-04-25 |
| Major League Soccer | 2005 | 2025 | 21 | 7063 | 2025-05-04 |

* Seasons shown are the seasons that exist in the open source, **not** the full history of the competition. For example the five major leagues are only present from the 2010s (England from 1992-93), and the domestic cups only from about 2018-19 to 2020-21 (Coupe de France: 2024-25 only). Earlier seasons are not included.
* 54 competition-seasons for 2025-26/2026-27 contain scheduled matches without results in the source (the open repositories lag, especially in lower tiers); those are in `QA_Reports/` and `09_Upcoming_Fixtures.csv`.
* "Worldwide" coverage is **not** claimed: coverage is whatever the CC0 openfootball repositories contain (Europe is strongest; Africa, Asia, Oceania and the Americas are partial; many countries have only a few recent seasons).

### 3.3 Player data (04, 05, 08)

* **StatsBomb Open Data** (event-level, 3,961 matches, 113,623 player-match rows, including 38,686 rows from women's competitions - filter on `competition_gender`):

| competition_name | competition_gender | seasons | matches |
|---|---|---|---|
| 1. Bundesliga | male | 2015/2016, 2023/2024 | 68 |
| African Cup of Nations | male | 2023 | 52 |
| Champions League | male | 1970/1971, 1971/1972, 1972/1973, 1999/2000, 2003/2004, 2004/2005, 2006 | 18 |
| Copa America | male | 2024 | 32 |
| Copa del Rey | male | 1977/1978, 1982/1983, 1983/1984 | 3 |
| FA Women's Super League | female | 2018/2019, 2019/2020, 2020/2021, 2023/2024 | 457 |
| FIFA U20 World Cup | male | 1979 | 1 |
| FIFA World Cup | male | 1958, 1962, 1970, 1974, 1986, 1990, 2018, 2022 | 147 |
| Frauen Bundesliga | female | 2023/2024 | 132 |
| Indian Super league | male | 2021/2022 | 115 |
| La Liga | male | 1973/1974, 2004/2005, 2005/2006, 2006/2007, 2007/2008, 2008/2009, 2009 | 867 |
| Liga F | female | 2023/2024 | 240 |
| Liga Profesional | male | 1981, 1997/1998 | 2 |
| Ligue 1 | male | 2015/2016, 2021/2022, 2022/2023 | 435 |
| Major League Soccer | male | 2023 | 6 |
| NWSL | female | 2018, 2023 | 173 |
| North American League | male | 1977 | 1 |
| Premier League | male | 2003/2004, 2015/2016 | 418 |
| Serie A | male | 1986/1987, 2015/2016 | 381 |
| Serie A Women | female | 2023/2024 | 130 |
| UEFA Euro | male | 2020, 2024 | 102 |
| UEFA Europa League | male | 1988/1989 | 3 |
| UEFA Women's Euro | female | 2022, 2025 | 62 |
| Women's World Cup | female | 2019, 2023 | 116 |

* **openfootball lineups (appearances, estimated minutes, goals, own goals, penalty goals, cards only; all other metric columns intentionally blank):**

| competition_name | season | player_match_rows | matches |
|---|---|---|---|
| Austrian Bundesliga | 2025-26 | 5935 | 195 |
| English Premier League | 2025-26 | 11469 | 380 |
| FIFA Club World Cup | 2000 | 384 | 14 |
| FIFA Club World Cup | 2005 | 188 | 7 |
| FIFA Club World Cup | 2006 | 195 | 7 |
| FIFA Club World Cup | 2007 | 187 | 7 |
| FIFA Club World Cup | 2008 | 218 | 8 |
| FIFA Club World Cup | 2009 | 219 | 8 |
| FIFA Club World Cup | 2010 | 217 | 8 |
| FIFA Club World Cup | 2011 | 217 | 8 |
| FIFA Club World Cup | 2012 | 221 | 8 |
| FIFA Club World Cup | 2013 | 223 | 8 |
| FIFA Club World Cup | 2014 | 220 | 8 |
| FIFA Club World Cup | 2015 | 222 | 8 |
| FIFA Club World Cup | 2016 | 224 | 8 |
| FIFA Club World Cup | 2017 | 223 | 8 |
| FIFA Club World Cup | 2018 | 176 | 8 |
| FIFA Club World Cup | 2019 | 176 | 8 |
| FIFA Club World Cup | 2020 | 205 | 7 |
| FIFA Club World Cup | 2021 | 244 | 8 |
| FIFA Club World Cup | 2022 | 210 | 7 |
| FIFA Club World Cup | 2023 | 221 | 7 |
| FIFA Club World Cup | 2025 | 1989 | 63 |
| French Ligue 1 | 2025-26 | 9392 | 306 |
| German Bundesliga | 2025-26 | 9541 | 306 |
| Italian Serie A | 2025-26 | 11904 | 380 |
| Spanish La Liga | 2025-26 | 11929 | 380 |

* 08 combines match-lineup memberships with squad lists (Club World Cup squads, selected 2014-15 / 2023-24 league squads, Euro 2021/2024 and Copa America 2021/2024 squads).
* Player identity limitation: StatsBomb players have source IDs that persist across teams; openfootball players do not, so the same person can appear several times (`id_scope` column). Nothing was merged by name alone.
* Minutes for openfootball rows are estimates (substitution and red-card minutes inside a 90-minute frame); StatsBomb minutes are derived from lineup position intervals.

## 4. Processing and cleaning rules

1. Raw files are kept unmodified in `_raw_sources/`; every output row carries `source_file` and a line/row reference (club rows also keep the original `source_text`).
2. Dates were parsed from partial strings (no year) using the weekday printed in the source to select the correct year; a season file whose folder name disagreed with its title (Belgium folder 2021-22 holding 2020/21) was relabelled from the title and logged.
3. Column names, date format and outcome codes (H/D/A, home/away/draw) are standardised across files; competition names are standardised for the main competitions and otherwise taken from the source title.
4. Duplicates, invalid scores, half-time/full-time inconsistencies, date ranges and referential integrity (every ID in 05/08 exists in 04/06) were checked - see section 5 and the data dictionary (`11_DATA_DICTIONARY.csv`, 275 documented columns).
5. Missing values are left blank, never filled with 0 or inferred. Where a value is derivable with certainty (a 0-0 score after extra time implies 0-0 in regulation) it is derived and nothing else is.

## 5. Verification results

| dataset | check | passed | detail |
|---|---|---|---|
| 01 | no duplicate match_id | True |  |
| 01 | no duplicate (date,home,away) | False | 2 rows share a (date,home,away) key |
| 01 | scores are non-negative integers | True |  |
| 01 | dates parse and are not in the future (<= 2026-06-02) | True |  |
| 01 | home team != away team | True |  |
| 01 | no score above 15 (flag only) | False | 44 extreme-score rows retained, listed in QA file |
| 02 | no duplicate match_id | True |  |
| 02 | no duplicate (competition,season,date,home,away,stage) | True | 0 rows |
| 02 | regulation goals are non-negative | True |  |
| 02 | half-time goals <= regulation goals | False | 2 rows (source inconsistency, retained) |
| 02 | no regulation score above 15 (flag only) | True | 0 rows retained |
| 02 | dates <= 2026-06-02 | True |  |
| 02 | home != away team id | True |  |
| 02 | extra-time status known when penalties were played (flag only) | False | 436 penalty-decided matches where the source does not state whether extra time was played |
| 03 | no duplicate match_id | True |  |
| 03 | dates between 2026-06-03 and 2026-10-20 | True |  |
| 03/01/02 | no match_id overlap between 01, 02 and 03 | True |  |
| 05 | unique player_match_id | True |  |
| 05 | one row per (match, player, team) | True | 0 rows |
| 05 | minutes within 0-130 | True | max=127.6 |
| 05 | StatsBomb passes_completed <= passes | True |  |
| 05 | StatsBomb shots_on_target <= shots | True |  |
| 05 | openfootball per-player goals (+opponent own goals) sum to match score (informational) | True | 99.0% of 2170 full-lineup matches reconcile exactly; remainder listed in QA (ET goals, name mismatches, no goal list) |
| 04 | unique player_id | True |  |
| 08 | unique membership_id | True |  |
| 08 | all player_ids exist in 04 | True |  |
| 05 | all player_ids exist in 04 | True |  |
| 06 | unique team_id | True |  |
| 05/06 | all 05 team_ids exist in 06 (StatsBomb + openfootball-linked) | True |  |
| 07 | unique competition_id | True |  |
| 02/07 | all 02 competition_ids exist in 07 | True |  |
| 09 | no scored match in fixtures | True |  |

Failed rows above are informational flags on retained source data, not silent drops: 4 flagged check(s) - no duplicate (date,home,away); no score above 15 (flag only); half-time goals <= regulation goals; extra-time status known when penalties were played (flag only). Per-dataset record counts, date ranges, missing-value statistics, duplicate statistics, source URLs, extraction date and limitations are in `12_DATASET_SUMMARY.csv`; source coverage and licence status are in `13_SOURCE_COVERAGE_MATRIX.csv`.

## 6. Licensing and permitted use

| Source | Licence evidence | Analytics / ML use |
|---|---|---|
| martj42/international_results | CC0-1.0 (GitHub licence metadata) | **Confirmed** |
| openfootball repositories | CC0 1.0 Universal (LICENSE.md in each cloned repository, checked) | **Confirmed** |
| StatsBomb Open Data | README: free for research and analysis, credit StatsBomb and use their logo if you publish | **Limited / partly unverified**: research and educational use with attribution is stated; commercial use and ML-model redistribution are not confirmed (LICENSE.pdf could not be machine-read in this session) |
| Football-Data.co.uk | Site text: private use only, not data-training products using bots/scrapers/AI | **Prohibited - not used** |
| FBref, Opta, Transfermarkt, paid APIs | Not reviewed / paid | **Not used** |

If StatsBomb-derived rows are published or shown in a report, credit **StatsBomb**. Check the licence terms again before any commercial use.

## 7. Known limitations (summary)

* Source gaps: see section 1 and 3; the club sources stop at 2026-09-20 and the international source at 2026-10-06; no results exist in the sources for 2026-10-07 to 2026-10-20.
* Regulation/extra-time split is unavailable for internationals and for 133 historical club extra-time matches whose bracket gives only one value.
* 436 penalty-decided club matches do not state whether extra time was played.
* Team/player entity resolution across sources is intentionally not performed.
* Women's competitions appear only in the StatsBomb subset; the international source states men's full internationals only; the openfootball files carry no gender label, men's competitions are assumed from the competition names and no women's competition was identified, but this was not exhaustively verified.
* Cross-validation against an independent provider was not possible (no second authorised source); internal consistency checks were run instead (for example 99% of 2025-26 lineup goal attributions reconcile exactly with the recorded scores).

## 8. Reproducibility

Run in this order from the project root with the existing virtual environment (no extra packages required): `_build/build_club_matches.py`, `_build/build_players_openfootball.py`, `_build/build_players_statsbomb.py`, `_build/assemble_matches.py`, `_build/assemble_players.py`, `_build/validate_and_document.py`, `_build/write_description.py`. Source URLs and download date (2026-10-20) are in `13_SOURCE_COVERAGE_MATRIX.csv` and `RAW_SOURCES_MANIFEST.csv`.
