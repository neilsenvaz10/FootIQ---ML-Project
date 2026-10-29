# FootIQ fresh-data pipeline validation — report (2026-10-21)

Scope: read-only freshness check and validation of the ingestion/logging path. **No download was made, no frozen model or snapshot touched, nothing trained/tuned/calibrated, no official logging, no dataset v1.2, no Git staging/commit, no background job.** Script: `_scripts/f1_freshness_validation.py`; data in this folder; run folders under `matched_v1_prospective_r1/ingestion/runs/`.

## 1. Upstream freshness status and source revision changes
`plan` (git ls-remote, hashes only; run twice today, 13:08 and 13:29 UTC): **all nine approved openfootball repositories (austria, belgium, deutschland, england, espana, europe, italy, south-america, world) are at exactly the commit used for the training snapshot — zero repositories changed.**
Your fetch condition ("at least one approved repository has a newer revision") is therefore **not met, so no fetch was executed** and there is no download size to report. Source licence unchanged (CC0 / public domain, same host). Pinned commits and commit dates: england 2026-10-15, espana 2026-10-15, europe 2026-10-15, south-america 2026-10-20, austria 2026-10-01, deutschland 2026-09-21, italy 2026-09-21, world 2026-09-23, belgium 2026-08-09. Plan files: `matched_v1_prospective_r1/ingestion/plans/`.

## 2/3. Which competitions have current results, which are missing after 2026-09-20
* 122 domestic-league competitions in the frozen universe. **0 have a completed result after 2026-09-20** (latest anywhere: 2026-09-20).
* **15 competitions are in season in the source** (Austria 1, Bundesliga, Premier League, Championship, La Liga, Czech 1, Ligue 1, Greece 1, Eredivisie, Portugal 1, Scotland 1, Switzerland 1, Turkey 1, Serie A, Brazil Série A). Every one has fixtures scheduled from 2026-10-21..25 on **and past-dated fixtures with no result: 271 fixtures dated 2026-10-02 .. 2026-10-20** (6–37 per competition; Brazil 32, Championship 37). Their last result is 2026-09-20 (Turkey: 2026-09-07).
* The other 107 competitions have no fixtures published in the source (off-season or not published; last results mostly 2025-11, 2026-05/06).
* So the source is not just slightly behind; it lacks every result since the matchdays after 2026-09-20 even though its newest commits are dated 2026-10-15/20. Table: `02_competition_coverage.csv`.

## 4. Can newly available results be incorporated without touching frozen models? — Yes (replay test)
Replay (`e3_ingest_results.py replay --cutoff 2026-08-31`): the frozen universe was truncated at 2026-08-31 and the later results were re-ingested from the pinned clones through the normal parse/validate path. Re-ingested **427 results = exactly the 427 expected**, 0 historical score conflicts, 0 in-snapshot conflicts. Features for 600 upcoming fixtures computed from "truncated + re-ingested" equal those from the full frozen state (v2 max difference 0.0; v1 contract features 0.0). The refreshed universe is a separate file; model files, preprocessing and training data are not read for writing. Newly fetched results will update pre-match features and later result verification only.

## 5. Fixture identity matching
Upcoming league fixtures in the source: **3,168**; re-parse equals the project's `09_Upcoming_Fixtures.csv` (3,168 in both, 0 differing). **100% have both teams resolved** to entity ids (no unresolved names, no non-regular stages, no implausible rows). Notes: 26 team slots map to source-scoped (flagged-unmerged) ids; the only name-to-multiple-entity ambiguities (2) are the River Plate clubs of Argentina/Uruguay/Paraguay in the continental cups, outside the league universe; 95 fixtures involve a club with < 5 prior rated matches; no fixture involves Police FC or Vision FC today.

## 6. Missing kickoff times
Kickoff time is present for only **17.6%** of fixtures and never with a time zone. This does **not** make pre-match logging unsafe: the logger assumes the earliest possible kickoff (match date 00:00 UTC − 14 h) and requires sealing ≥ 60 min before that, i.e. 15–39 h before the match day begins. With today's schedule 3,167 of 3,168 fixtures could still be sealed (only the 2026-10-21 La Liga fixture could not). Cost: predictions are made without the previous day's results (recorded in the log). An optional refinement (competition-country time-zone table) would help only the 17.6% with known times and has not been implemented.

## 7/8. Eligibility re-check and updated eligible count
No verified results update exists, so the checks were re-run on the unchanged snapshot (3,159 fixtures dated ≥ 2026-10-24, dry-run only):
| Check | Fixtures failing |
|---|---|
| club has an unresolved past-dated fixture | 3,159 |
| competition results older than 14 days | 3,159 |
| < 5 prior matches / Elo-disconnected | 95 |
| identity collision (Police FC / Vision FC) | 0 |
| **Primary-eligible for official prospective evaluation** | **0** |
If results were current, 3,064 of 3,159 would pass (the remaining 95 fail on history). Simulation of the checker as of 2026-09-13 on the matches actually scheduled 2026-09-15..20 (schedule rows only, outcomes not read): 136 of 139 eligible (97.8%) across 14 competitions — the rules do not over-exclude when results flow normally.

## Remaining blockers
1. **Source latency (decisive):** no upstream revision, 271 missing results in the 15 in-season competitions, none after 2026-09-20.
2. Official logging not approved (`OFFICIAL_LOGGING_APPROVED.json` absent, by your instruction).
3. `fetch` and the parse of a genuinely newer snapshot remain untested end to end (the replay covers the parse/merge/feature path).
4. Dataset v1.2 deferred: Police FC / Vision FC fixtures stay ineligible; Zimbabwe fixtures stay flagged (no current Zimbabwe fixtures).
5. Evaluation horizon: at roughly 170 eligible matches a week (autumn volume; 14–15 active competitions), 5,000 eligible results need about 30–35 weeks, and the protocol's ≥ 25-competition requirement needs more leagues to start (calendar-year leagues mostly from Feb–Mar 2027). Expect the first analysis checkpoint around mid-2027. Any change to those minimums must be made before the first official batch.

## Recommendation: when can official logging safely begin?
Not yet. Begin only when all hold: (a) `plan` shows a newer approved revision and, after you approve that fetch, the isolated parse shows new completed results with 0 score conflicts; (b) the dry-run eligible count is > 0 and roughly matches the simulated ~98% for the in-season competitions (i.e. the 271 past-dated fixtures have results); (c) you create `OFFICIAL_LOGGING_APPROVED.json`. Re-running `plan` is cheap and read-only; I suggest running it manually every few days rather than scheduling it. Because the evaluation needs months of accumulation, starting as soon as (a)–(c) hold is worth more than waiting for a larger fixture pool.
