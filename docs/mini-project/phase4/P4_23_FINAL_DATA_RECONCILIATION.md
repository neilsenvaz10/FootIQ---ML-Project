# Phase 4.23: final data reconciliation (staged and dry-run only)

Status: **nothing was applied to production.** The production database, the running backend (not stopped or restarted), the synchronisation settings, the saved simulations and the frozen models were not touched; no provider was activated; no file was deleted; no Git operation. The production database hash was identical before and after this phase (`afe71c44...`), the request ledger is unchanged (19 lines). New files: `data/supervised/phase4/p423/` (evidence, staging, rehearsal), `app/store/reconcile_import.py`, `tests/test_reconcile_import.py`.

## Sources (one request each, no account or key; files and hashes in `staging/raw/evidence.json`)
| Source | Used for | Terms |
|---|---|---|
| Wikipedia league pages and results-grid templates (revisions of 25-28 Oct) | scores | CC BY-SA 4.0 (storable, attribution shown) |
| openfootball (today's five files) | fixture dates and results | CC0-1.0 (storable); today's files are the same as at the previous download: no newer result, so it is ONE vote together with the stored date |
| football-data.co.uk results CSVs and `fixtures.csv` | scores and the played day (cross-check) | no explicit licence: never stored |
| fixturedownload.com feeds (new this phase) | an independent schedule: date and time (UTC, converted to the league's local date) and scores | no explicit licence: cross-check only |
| The store's own OpenLigaDB findings (approved feed, ODbL) | the moved date for the Premier League disputes and for the La Liga postponement | already stored |
| football-data.org dates from the private Phase 4.13 comparison | counted only in the "provider-assisted" tier, always flagged | storage terms unconfirmed |
UEFA / league / BBC pages could not be read (script-rendered or blocked) and web search does not reach this period, so **no official page confirms the domestic results**; they rest on independent aggregators agreeing.

A bug of my own from Phase 4.20 was found and fixed: the Wikipedia grid parser dropped scores written as piped derby links (`[[Chelsea F.C.-Tottenham Hotspur F.C. rivalry|0-2]]`), so 5 of the 16 open matches had looked like "single source". With the parser fixed, **all 382 stored completed results (77 / 79 / 70 / 63 / 93) were re-audited against Wikipedia, football-data.co.uk and FixtureDownload: 0 score differences and 0 date differences.** The staged results are unaffected otherwise.

## The 16 fixtures past their date without a result
| Competition | Fixtures | Verified result (2+ sources agree) | Still open |
|---|---|---|---|
| Premier League | 3 | **3** (Leeds 1-1 Man United, Brighton 5-0 Crystal Palace, Chelsea 0-2 Tottenham): Wikipedia + football-data.co.uk + FixtureDownload | 0 |
| La Liga | 7 | **6** (Rayo 0-3 Elche, Alavés 1-1 Málaga, Sevilla 2-0 Osasuna, Valencia 1-2 Villarreal, Atlético 1-0 Deportivo, Racing 2-1 Espanyol): the played day 23-26 Oct is given by football-data.co.uk and FixtureDownload; the stored 25 Oct was a matchday placeholder | 1 **postponed**: Rayo Vallecano v Athletic Club (10 Oct) |
| Bundesliga | 0 | - | 0 |
| Serie A | 4 | **1** (Napoli 3-3 Roma) | 3 (Sassuolo 2-6 Lazio, Roma 4-2 Cagliari, Torino 1-3 Como, 27 Oct): the score is on Wikipedia only; the other sources have no result yet. Held, not verified |
| Ligue 1 | 2 | **2** (Toulouse 0-0 Troyes played 25 Oct, PSG 2-0 Lyon played 26 Oct): the stored dates (24 / 25 Oct) were a day early | 0 |
**12 results verified, 3 held (single source), 1 postponed.** Postponement evidence for Rayo-Athletic: no result in any of five sources 18 days after its date; the approved OpenLigaDB feed holds it unfinished with its date moved to a placeholder (30 May 2027, updated 17 Oct, already in the store's quarantine, finding 273); FixtureDownload still lists the old date without a score. I could not find an official statement, so the postponement is a **decision** for you, not automatic.

## The 96 disputed dates
Rule: a date is resolved when at least two independent sources give it (the stored date and today's openfootball count once). FixtureDownload, new this phase, agrees with the provider's date in **93 of 96** cases and with the stored date in the other 3. Per-dispute evidence: `staging/date_reconciliation.csv`.
| Result | Count | Evidence |
|---|---|---|
| **Strong**, change the date | 31 (Premier League) | OpenLigaDB + FixtureDownload (the provider agrees too) against the openfootball snapshot of 15 Oct |
| **Strong**, keep the stored date | 3 (Ligue 1) | FixtureDownload + openfootball agree; the provider alone differs |
| **Provider-assisted**, change the date | 62 (Serie A 39, Ligue 1 23) | FixtureDownload + football-data.org agree against openfootball; no second source without the provider |
| Unresolved | 0 | |
Of the 23 Ligue 1 provider-assisted, 2 are the finished matches above (their date is corrected together with their result). So the **proposed date changes are 91** (31 strong + 60 provider-assisted) plus the 2 played-day corrections. Honest caveat: FixtureDownload and football-data.org may draw on the same league schedule; that is why the 60 are a separate tier you can decline. A corrected fixture loses its stored kickoff time (it belonged to the old date; only 8 of the 96 had one); no time is invented.

## Proposed database changes (`staging/proposed_changes.csv`, 104 rows)
| Change | Rows | Tier |
|---|---|---|
| `add_result` (stored date right) | 4 (Premier League 3, Serie A 1) | strong |
| `add_result_with_date` (result + played day) | 8 (La Liga 6, Ligue 1 2) | strong |
| `correct_date` (unplayed fixture) | 91 (Premier League 31 strong; Serie A 39 and Ligue 1 21 provider-assisted) | strong / provider-assisted |
| `set_postponed` (status only) | 1 (La Liga) | decision |
Effect (rehearsed on a private copy, all tiers): completed 77 / 93 / 79 / 70 -> **80 / 99 / 80 / 72** (Premier League / La Liga / Serie A / Ligue 1); fixtures past their date without a result **16 -> 3** (Serie A only); one postponed match (hub "Postponed or cancelled"); 104 rows changed, 0 added, 0 duplicates, integrity ok, 0 foreign-key problems, quarantine still 273, saved simulations untouched.

## Importer (`app/store/reconcile_import.py`)
Dry run by default; `--apply` needs `--production` and a byte-identical `--backup`; tiers are opt-in (`--include-provider-assisted`, `--include-decisions`). Every row states the status and date it was prepared against and is quarantined if the store has changed; a stored result is never overwritten; a played match's date changes only with its result; shifts over 4 days, past-dated corrections, missing evidence, one-source scores, duplicates, reversed pairings and unknown clubs are rejected; changes already in place are `unchanged` (a second run changes nothing); provenance (`match_sources`, `source_snapshots`, a `sync_runs` row) records each change's evidence and the store's previous value; no quarantine row is deleted.

## Dry run against production (read-only, database hash unchanged)
- strong tier only: **43 `apply`** (12 results, 31 Premier League dates), 61 skipped as not enabled; 0 validation issues, 0 conflicts;
- all tiers: **104 `apply`**, 0 issues, 0 conflicts.

## Tests
`tests/test_reconcile_import.py` 40 passed (validation of every rule, classification and conflicts, dry run changes nothing, repeatable apply without duplicates, row-level effects, postponed handling in the Matches hub, a failure mid-apply rolls back and a backup restores the exact file, production guard, the real proposals read-only, the grid parser and the club mapping). Targeted regression: backend 229 passed in 3.7 min (reconciliation 40, domestic importer 28, UEFA importer 29, hub 46, API and prediction 32, scope, freshness, league phase, startup sync), 0 failures, 0 skips; frontend 358 passed, 13 skipped (the live-API tests). The full 477-test regression was not re-run: no application code changed.

## Exact approval needed to apply to production
1. **Strong tier (43 changes):** 12 verified results (the model-universe entry works as for the previous 71 results) and 31 Premier League date corrections.
2. **Provider-assisted tier (60 date corrections):** Serie A 39, Ligue 1 21: yes or no.
3. **Postponement (1):** mark Rayo Vallecano v Athletic Club `postponed`: yes or no.
4. The 3 Serie A results of 27 Oct stay open until a second source has them.
Procedure on approval: stop the backend, verified byte-identical backup, final dry run, `reconcile_import.py --apply --production --backup ... [--include-provider-assisted] [--include-decisions]`, verification against the backup, foreground restart.
