# Offline rehearsal: OpenLigaDB import for the Premier League and La Liga 2026-27

Date: 2026-10-25. **Rehearsal only, in a private copy.** No network request was made (the saved snapshots were replayed). The production database, the original CSV files, the frozen models, `config/sync.json` (`live_enabled: false`) and the official prospective-evaluation files were not changed. Nothing is staged, committed or pushed. Phase 3 and unattended synchronisation have not been started.

Reproduce: `python app/store/rehearse_openligadb.py` (about 2 minutes). Everything below is written to `data/supervised/rehearsal/` (git-ignored): `rehearsal_report.json`, `import_diff_matches.csv` (every changed field of every changed match), `date_comparison.csv` (the 55 date differences), `quarantine.csv`, and three SQLite copies (`footiq.before`, `footiq.rehearsal`, `footiq.rehearsal_repeat`).

## 1. Team identities (verified, not assumed)

Each proposal was checked against the canonical team table, 2026-27 membership of the competition, earlier use in the same competition, and fixture structure: with the five aliases in place, every source team's 38 fixtures pair with exactly one stored fixture, with the same matchday number each time. All five passed; none was written without passing. The fuzzy suggestions were never used (Brentford is explicitly forbidden from resolving to Arsenal, and a test proves a wrong target is rejected).

| Source name | Canonical entity (store) | Store display name | Evidence |
|---|---|---|---|
| `Brentford F.C.` | `CLUB:ENG:brentford-fc` | Brentford FC | member of 2026-27 PL; 38/38 fixtures and matchdays agree |
| `Celta Vigo` | `CLUB:ESP:rc-celta-vigo` | RC Celta de Vigo | member of 2026-27 La Liga; 38/38 |
| `Deportivo A Coruña` | `CLUB:ESP:rcd-la-coruna` | RC Deportivo La Coruña | 38/38. **Your proposed text "Deportivo de La Coruña" is not a stored name**; the entity is the same club, selected by id and fixtures, not by that spelling |
| `FC Villareal` (source typo) | `CLUB:ESP:villarreal-cf` | Villarreal CF | 38/38 |
| `Racing Santander` | `CLUB:ESP:real-racing-santander` | Real Racing Club de Santander | 38/38. **Your proposed text "Racing de Santander" is not a stored name**; same entity (the store also holds the older spelling "Racing Santander" for this entity in the second tier and the cup) |

Complete mapping after the aliases: Premier League 20 of 20 source teams to 20 of 20 store teams, one-to-one (17 exact, 2 normalised, 1 reviewed alias); La Liga 20 of 20, one-to-one (11 exact, 5 normalised, 4 reviewed aliases). **No unresolved identities.** The normalised matches are deterministic spelling normalisation, not fuzzy matching: `FC Arsenal`, `FC Liverpool`; `Deportivo Alaves`, `FC Getafe`, `FC Malaga`, `FC Sevilla`, `FC Valencia`. The full table is in `rehearsal_report.json` (`mapping`).

## 2. Results safely recoverable

| League | Recovered (rows that were awaiting a result) | Held back for a date decision | Still without a result |
|---|---|---|---|
| Premier League | **10** (all 10 are among the 20 awaiting rows; `primary` provenance) | 0 | 15 past-date fixtures: the source has no result for them (it lags) |
| La Liga | **20** | **5** (completed in the source on 23-24 Oct, stored one or two days later) | 1 (Rayo Vallecano v Athletic Club, see section 4) |

A recovered result changes only the result fields and kickoff; the stored fixture date is never altered. Every other fixture that agrees on date also receives its UTC kickoff (289 PL, 267 La Liga). Matches with an existing identical result are linked as confirmations (PL 48, La Liga 69 scores, all agree).

## 3. Conflicting and quarantined records (stored scores untouched)

| Record | Stored | Source | Quarantine reason |
|---|---|---|---|
| AFC Bournemouth v Brentford FC, 2026-09-12 | 2-2 (openfootball) | 2-1 (OpenLigaDB, half-time 0-0, updated 2026-09-12 18:52 UTC) | `CONFLICT` |
| Aston Villa v Nottingham Forest, 2026-09-12 | 1-2 (openfootball) | eight result rows: five half-time rows (all 0-0) and three final-score rows (1-2, 0-0, 0-0) | `CONTRADICTORY SOURCE RESULT`, not imported |
| 55 fixtures | stored date | different source date | `DATE_DIFFERENCE`, held untouched |

**Independent evidence needed to resolve the two scores** (this rehearsal cannot decide them and I have not guessed):
* Bournemouth v Brentford: the official Premier League match record (results page or match centre) or the clubs' match reports, ideally plus one more independent results provider. If it is 2-1, the stored row needs a reviewed one-row correction (the outcome changes from draw to home win, which moves the standings and the form of both teams); if 2-2, the stored row stands and the OpenLigaDB entry is the error.
* Aston Villa v Nottingham Forest: the same official record. If it shows 1-2, the stored score is confirmed and only the OpenLigaDB record stays rejected; otherwise the stored score needs a reviewed correction.
Until then both fixtures keep the stored openfootball score. Both are 2026-09-12 results that already feed team form.

## 4. Fixture-date differences (all 55 held; see `date_comparison.csv`)

31 Premier League, 24 La Liga: 28 are +1 day, 19 are -1, 3 are +2, 4 are -2, and one is **+232 days**. Every row lists the original date, the source UTC date, the kickoff timestamps (UTC and local), the matchday, stored and source status, whether it has been played, and the effect on prediction eligibility. 49 have no effect (future fixtures on both dates, no result of either team in between, so features and flags are identical). 6 do:

* 5 La Liga Matchday 10 fixtures (Atlético v Deportivo, Alavés v Málaga, Rayo v Elche, Racing v Espanyol, Valencia v Villarreal): the store says 25 Oct, scheduled; the source says played on 23-24 Oct with a result. Until you decide, they stay "scheduled" and their results are held.
* **The 233-day anomaly (reported as +232 days): Rayo Vallecano v Athletic Club, Matchday 8.** Stored 2026-10-10, status "awaiting result". The source places it at 2027-05-30 22:00 UTC (2027-05-31 00:00 local), the final-round date, status upcoming. The most likely reading is a postponement with a placeholder date, but that is an inference, not something the data states. If the source is right, the fixture has not been played, so the "missing result" flag for both teams (and for their later fixtures) is spurious. It stays held, and the store keeps flagging it as awaiting a result.

I did not overwrite any of the 55. A decision on them is part of the approval request below.

## 5. Standings and data freshness

Tables are computed from verified results only (3 points a win, 1 a draw; ordered by points, goal difference, goals for as an indication only, official tie-break rules are not applied), so teams have played different numbers of games.

| | Premier League before → after | La Liga before → after |
|---|---|---|
| Matches counted | 50 → 60 | 69 → 89 |
| Newest result | 2026-09-20 → 2026-10-12 | 2026-09-20 → 2026-10-21 (10-24 held) |
| Awaiting a result | 20 → 15 | 20 → 1 |
| Leader | Manchester City, 15 → 18 points | Barcelona, 21 → 27 points |
| Teams whose rank changed | 14 | 15 |
| Kickoff UTC known (unplayed fixtures) | 0 → 289 | 0 → 267 |

The Premier League stays stale: the source's newest completed fixture is 2026-10-12, so the 15 fixtures from 17-18 Oct onward have no result. The application's freshness label for both leagues will remain "stale: no approved fresh source" until `config/sync.json` approves them; this import only improves the stored data, it does not enable any sync.

## 6. Effect on gameweek prediction eligibility (as of 2026-10-25)

| | Unplayed fixtures predictable | Fully supported | Provisional | Kickoff time known |
|---|---|---|---|---|
| Premier League before | 330 | 0 | 330 | 0 |
| Premier League after | 320 | 10 | 310 | 289 |
| La Liga before | 311 | 0 | 311 | 0 |
| La Liga after | 291 | 17 | 274 | 267 |

The next gameweeks (Premier League Matchday 8, La Liga Matchday 10) are the ones that matter. Premier League Matchday 8 stays **provisional** (10 of 10): its fixtures lie more than 14 days after the newest Premier League result (2026-10-12), and 15 earlier played matches have no result. La Liga Matchday 10 becomes **8 fully supported, 2 provisional**. Caveat: the 10 "fully supported" Premier League fixtures are Matchday 7 games whose dates have already passed without a result, so a forecast pressed now would not be "made before kickoff" and would not be counted in the predicted-versus-actual summary. The frozen models, the forecast engine and the time-safety rules are unchanged: a result dated on or after a fixture never reaches that fixture's features.

## 7. Provenance and licence

* Four snapshots are registered in `source_snapshots`: league listing, `pl`, `pl1` (empty), `la1`, each with URL, saved path, sha256, byte size and retrieval time (hashes in [OPENLIGADB_PL_LALIGA_FINDINGS.md](OPENLIGADB_PL_LALIGA_FINDINGS.md)). Replay refuses a snapshot whose sha256 does not match the ledger.
* 703 new `match_sources` rows: PL 347 (337 confirmation, 10 primary), La Liga 356 (336 confirmation, 20 primary). Licence **ODbL-1.0** on every row. Attribution: "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0".
* Rows whose result OpenLigaDB supplied now show `source_system = openligadb`; all other rows keep their original source.

## 8. Fingerprints (before → after)

| Table | Rows | Fingerprint |
|---|---|---|
| matches | 223,510 → 223,510 | changed (586 rows: 556 kickoff and/or status only, 30 with a recovered result) |
| match_sources | 223,816 → 224,519 (+703) | changed |
| source_snapshots | 5 → 9 (+4) | changed |
| team_aliases | 7,442 → 7,447 (+5) | changed |
| quarantine | 216 → 273 (+57 = 55 + 1 + 1) | changed |
| sync_runs | 5 → 7 (+2 `offline_rehearsal`) | changed |
| competitions, teams, meta, source_state, sync_errors, forecast_runs, forecasts, simulation_runs | unchanged | identical |

`matches` sha256 before `59384a7c692d093b73dabe91cb0432946c1964320899d18a0502d44bfdbfcfe9`, after `d0862a54f5c279b8e994bb5f436e46a9644227412f9f5065021a988642dc4d7c` (every table's hash is in `rehearsal_report.json`). A second, independent copy ends with identical hashes on every table (deterministic), and a second pass over the same copy changes nothing (idempotent).

**Untouched (sha256 before = after, 17 files):** the production store (`data/footiq.sqlite` `2c677ebf74da6203d380b0c43d04c52f843d79edb8eb1ef12b42c19cb4bf5d3b`), `data/miniproject/matches.csv`, `09_Upcoming_Fixtures.csv`, `04d_COMBINED_CLUB_MATCHES_v1.0.csv`, `V_universe.pkl`, club v1 pickle and preprocessing, club v2-r1 pickle and feature contract, international v2.7 pickle, `config/sync.json`, both prospective loggers and both `prospective_log/DRY_RUN` ledgers (`CHAIN.jsonl`, batch files).

## 9. Code changes made for the rehearsal (not applied to any data)

* `app/store/sync.py`: optional `protect_dates` (hold a fixture whose stored date differs, quarantine it as `DATE_DIFFERENCE`); quarantine records the same finding once however often a payload is replayed; contradictory source results get their own reason; `replay_payload` accepts a per-league spec and snapshot id/path (default behaviour unchanged, so the Bundesliga path is as before). The Bundesliga approval list is unchanged.
* `app/store/rehearse_openligadb.py` (new) and `tests/test_rehearsal.py` (new, 9 tests).

## 9b. Test results

* Backend, whole suite in one run: **101 passed** (92 earlier + 9 new rehearsal tests). A first full run had 1 failure caused by my own change (a new quarantine label also caught the ordinary "no explicit 90-minute result" case); it was fixed and the whole suite re-run from scratch.
* Frontend: 39 passed, 9 live-API tests skipped in this run (they need the backend running; they passed 48 of 48 earlier today and no API or frontend code changed since); production build succeeds.

## 10. Proposed production import (awaiting your approval; nothing below has been run)

Applied to `data/footiq.sqlite` from the saved snapshots only (no request), after a file backup:

1. Insert 5 `team_aliases` rows (table in section 1).
2. Register 4 snapshots in `source_snapshots`.
3. Update 586 `matches` rows: kickoff UTC and precision on all 586 (556 only that, 30 also with a recovered result); status `scheduled → awaiting_result` on 5 PL fixtures; the 30 recovered results (PL 10, La Liga 20) each with `source_system = openligadb`, ODbL licence and outcome/rating flags as for the Bundesliga import. The exact before/after value of every field is in `import_diff_matches.csv`.
4. Insert 703 `match_sources` rows and 57 `quarantine` rows; add 2 `sync_runs` rows (`offline_snapshot_import`).
5. Change nothing else: no match date, no stored score, no row added or deleted, `live_enabled` stays false, no `sync.json` change, no scheduling.
6. Afterwards: re-run the fingerprint and file-manifest comparison, the full test suite, and the gameweek eligibility check against the production file, and report.

**Decisions I need from you before step 1:**
* (a) Confirm the five canonical mappings above. Note two proposed spellings are not stored names.
* (b) The 55 date differences: leave all held (recommended until the source's dates can be corroborated, because the 5 La Liga Matchday 10 rows then keep their results held), or allow the source's date to replace the stored date for a defined subset, for example the 5 played La Liga fixtures only.
* (c) Bournemouth v Brentford and Aston Villa v Nottingham Forest: leave quarantined with stored scores until an official record is checked (recommended).
* (d) A separate approval is still needed for any live request, for adding `EPL`/`LALIGA` to `config/sync.json`, and for Phase 3.
