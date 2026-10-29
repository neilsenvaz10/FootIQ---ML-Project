# Phase 4.17: national-team and UEFA data completion (staging, evidence, proposals)

Status: **nothing was imported.** Production database, `data/miniproject/matches.csv`, `data/processed`, the frozen models and `config/sync.json` are unchanged; no Git operation; no storage cleanup; PL/SA/FL1 stay disabled; synchronisation stays startup-only. Two provider-neutral downloads were made (one per source, below). Everything staged lives in `data/supervised/phase4/p417/` (git-ignored).

## 1. Source evidence
| | national teams | UEFA clubs |
|---|---|---|
| Source | `martj42/international_results` | `openfootball/champions-league` |
| URL (one GET each, one redirect to codeload.github.com, no retry) | https://github.com/martj42/international_results/archive/refs/heads/master.zip | https://github.com/openfootball/champions-league/archive/refs/heads/master.zip |
| Retrieved | 2026-10-28T02:37:17Z | 2026-10-28T02:38:37Z |
| Archive | 1,300,320 bytes, SHA-256 `c4ce2d65...dc980d5`, zip test ok | 76,835 bytes, SHA-256 `a94e904c...c7c9ec`, zip test ok |
| Revision (zip comment) | `d5bd6de012c87e2f325de602ae77fe2f9ab61ef3` | `abfaeddc2ee3d14f99ecc163c9ddb46cb4d67cef` |
| Licence | the archive's own `LICENSE` is **CC0 1.0** (verified from the file) | `LICENSE.md` is **CC0 1.0** (verified) |
| Result | 49,945 rows to 2026-10-06 (local file: 49,368 to 2026-06-27) | **identical to the local clone** (34 of 34 files byte-equal, same commit); **no 2026-27 folder** |
Records: `*/evidence.json`. The two downloads are not in the request ledger (that file records provider API calls); `evidence.json` is their record.

## 2. National teams: comparison with what FootIQ holds
- **World Cup 2026:** the dataset has all **104** fixtures scored, to 2026-07-19. The **final** is `2026-07-19 Spain 1-0 Argentina` (the repository's own verified files stop at fixture 103, "final excluded"). It is the dataset's claim with **no second source**: not imported.
- **The 27 duplicated knockout matches:** the dataset agrees with the **Knockout** row in **27 of 27**, including the **four conflicts** (Belgium-Senegal 3-2 vs 2-2, Argentina-Cape Verde 3-2 vs 1-1, Argentina-Switzerland 3-1 vs 1-1, Norway-England 1-2 vs 1-1). The lower "Group stage" twin scores look like regulation-time scores (a hypothesis, unverified); the dataset carries no 90-minute score.
- **Nations League 2026-27:** **104** matches, 2026-09-24 to 2026-10-06, all scored (total 762 vs 658).
- **Beyond the local cutoff:** 583 rows after 2026-06-02 (World Cup 104, Nations League 104, friendlies 161, CONCACAF Nations League 73, AFCON qualifying 48, others). Copa America: no change (complete to 2024).
- **Other differences and conflicts:** 1,540 rows only in the new file and 963 only in the old. Of the old-only rows, 239 are the same match under a renamed tournament or team and the rest are almost all **one upstream rename: "China PR" became "China"** (and "Ticino" became "Canton Ticino"). 74 rows differ in score: 72 are the World Cup fixtures that now have scores and 2 are the two same-day Tahiti v New Caledonia 1974 matches listed in swapped order in both files. A new team, "Rouet-Provence", has no rating row. **Identity action needed:** map "China" to "China PR" and "Canton Ticino" to "Ticino" before any import (done in the private ratings run).

## 3. UEFA club competitions
- openfootball upstream has **nothing newer** than the local clone, so there is nothing to import from it.
- The **Wikipedia snapshots already saved locally** (retrieved 2026-10-20, revisions of 2026-10-19/20; CC BY-SA 4.0, attribution and share-alike apply) hold the complete 2026-27 league phase: 144 + 144 + 108 matches. Parsed with the project's own parser and identity mapping (no network), they add the results the dataset left out because of its 2026-10-01 cutoff:

| | in the dataset now | staged | new results | fixtures with dates still to play |
|---|---|---|---|---|
| Champions League 2026-27 | 18 of 144 (matchday 1) | 36 played (matchday 2, 13-14 Oct) | **+18** | 108 |
| Europa League 2026-27 | 18 of 144 | 36 played (matchday 2, 15 Oct) | **+18** | 108 |
| Conference League 2026-27 | 0 of 108 | 18 played (matchday 1, 15 Oct) | **+18** | 90 |
- Structural checks, all passed: 36 teams in each, 8 (6 for the Conference League) matches per team, home and away balanced, no duplicate pairing, every match dated, no implausible score, the 18 + 18 matches already in the dataset reproduced. **One unresolved identity:** NK Celje (Europa League). These are **single-source** (Wikipedia): validated structurally, not imported.
- **League-phase table** (new, offline): `app/uefa_league_phase.py`, `GET /api/competitions/{key}/league-phase?season=`. Ranking by points, goal difference, goals scored, away goals, wins, away wins and (only once the phase is complete) the opponents' points, goal difference and goals scored; criteria 9 (discipline) and 10 (UEFA coefficient) are not in the data, so a surviving tie is shown as a shared rank, never guessed. Zones: 1-8 direct to the round of 16, 9-24 play-offs, 25-36 out. Rules provenance: the Wikipedia article's "Tiebreakers" section citing the UEFA 2026/27 regulations; **the primary UEFA document was not re-read**. Seasons before 2024-25 had group stages and are refused. The 2024-25 leaders reproduce the real result (Liverpool 21 points, Lazio 19, Chelsea 18); all six completed 2024-25 and 2025-26 league phases pass structural checks; the current phase is labelled provisional.

## 4. Prediction readiness (private copies only)
- **Team identity:** every team of WC, UNL and COPA has a rating row (0 missing); the 5 leagues and the 3 UEFA competitions have club ids on every row; "China" and "Canton Ticino" need the two mappings above.
- **Pipeline parity:** the project's own builder (`scripts/build_foundation_tables.py`) run privately on the local raw file reproduces `international_matches.csv`, `team_elo_latest.csv`, `team_elo_match_history.csv` and `team_recent_form_latest.csv` **byte for byte**.
- **Chronology:** on the refreshed table, dates are in order, the first rating of each team is 1500, and **0** matches use a pre-match rating that is not the team's previous post-match rating (no future information). (151 same-team-same-date rows exist in the history; they are old and also in production.)
- **Stale ratings:** production ratings end **2026-06-02**. The private refresh ends **2026-10-06** (+649 matches, 337 teams): Spain +128, England +128, Turkey -116, Tunisia -112. Six sample predictions (WC, UNL, COPA), before then after: all succeed; probabilities move visibly (France v England 32.8/39.4/27.8 becomes 21.1/40.7/38.1 for France/draw/England). The frozen model artifact is unchanged; only the ratings path was redirected in-process.
- **Support:** all six non-domestic competitions predict; UEFA remain "Not validated", Nations League and Copa America "Partially validated".

## 5. UI: competition-level freshness
`GET /api/data-freshness` and a component on the Leagues, Predict and Compare pages and in the status panel: latest result (with age), **"Updated when FootIQ starts"** (Bundesliga, La Liga only) or **"Historical only: no automatic updates"**, the last successful refresh (only for the former), and **missing-coverage warnings** computed from the data (missing edition, matches present out of expected, duplicates, past-date fixtures without results, ratings older than the latest result, stale age). Nothing is labelled live. Two small expectation tables (expected edition, expected match counts) are kept in the open in `app/freshness.py`.

## 6. Before / after coverage matrix (after = staged or private, NOT in production)
| Competition | Production now | If the staged data were imported | Status |
|---|---|---|---|
| Bundesliga | latest 2026-10-25, updated at start | unchanged | active |
| La Liga | latest 2026-10-25, updated at start | unchanged | active |
| Premier League | latest 2026-10-12, historical only | unchanged (provider permission, 31 date disputes) | blocked |
| Serie A | latest 2026-09-20 | unchanged (39 date disputes) | blocked |
| Ligue 1 | latest 2026-09-20 | unchanged (26 date disputes) | blocked |
| World Cup | 1,094 rows; 103 of 104 fixtures; 27 duplicates; no final | 104 of 104 scored incl. the final (single source); 27 duplicates removable | proposal |
| Champions League | 2026-27: 18 of 144 results | 36 of 144 + 108 dated fixtures + league-phase table | proposal |
| Europa League | 2026-27: 18 of 144 | 36 of 144 + 108 dated fixtures + table | proposal |
| Conference League | 2026-27: 0 of 108 | 18 of 108 + 90 dated fixtures + table | proposal |
| Nations League | 658 rows to 2025-06-08; no 2026-27 | 762 rows to 2026-10-06 (+104) | proposal |
| Copa America | 869 rows, complete to 2024 | unchanged | complete |
Predictions in production still use ratings that end 2026-06-02 until the refreshed ratings are approved and installed.

## 7. Tests
- Backend, ML inference and data (targeted, 18 files): **322 passed, 4 skipped, 1 error**. The error is `OSError: No space left on device` during one test's setup (it passes alone, 4 of 4): see section 8. Frontend: **351 passed, 13 skipped**. New this phase: 24 league-phase and freshness tests, 5 evidence tests, 4 frontend tests.
- Two of my own mistakes were corrected on the way: two synthetic test cases in the league-phase tests were wrong (the module was right), and the status-panel tests broke when the panel gained a second endpoint (the freshness components now tolerate a malformed answer).

## 8. Storage warning (no cleanup done)
`C:` has **9.4 GB free of 344 GB**. The cause is the test runs: **46.8 GB** of leftover pytest folders in `C:\Users\DELL\AppData\Local\Temp\pytest-of-DELL` (9 session folders; many tests copy the 230 MB production-size database). Production data is on `D:` (392 GB free) and was not affected. This is the storage question you postponed; I did not delete anything.

## 9. Proposed next steps (each needs your approval)
1. Import the **54** staged UEFA results and the dated 2026-27 fixtures into a private copy for a diff, then production (Wikipedia attribution on screen); map NK Celje.
2. Import the national-team additions (Nations League 104, World Cup knockouts and final, friendlies) after the two name mappings; decide whether to accept the single-source final.
3. Remove the 27 World Cup duplicate rows (keep the Knockout row).
4. Install the refreshed international ratings (changes `data/processed`; no retraining), and re-check predictions.
5. Wire the league-phase table into the Analytics page for UEFA competitions (API exists).
6. Storage: remove the pytest temporary folders and redirect pytest's temp directory to `D:`.
7. PL/SA/FL1 remain as before: provider's written permission, then the 96 date decisions.
