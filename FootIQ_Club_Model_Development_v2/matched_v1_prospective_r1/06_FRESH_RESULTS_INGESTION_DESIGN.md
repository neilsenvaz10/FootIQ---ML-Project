# 06 Fresh-results ingestion design

Script: `_scripts/e3_ingest_results.py` (reuses the project's own openfootball parser `FootIQ_Dataset_Submission/_build/footballtxt.py` and file registry). **Manual, one-shot commands only; no scheduler, no recurring job.** All output is under `ingestion/` in this folder.

## Source policy
Only the approved source of the training data: openfootball (CC0 / public domain), the nine league repositories already used (`austria, belgium, deutschland, england, espana, europe, italy, south-america, world`), fetched from `https://github.com/openfootball/<repo>.git` by a read-only `git clone --depth 1` (public, unauthenticated). The code asserts the URL prefix; other hosts are rejected. No scraping of other sites, no APIs, no paid or restricted data.

## Commands
| Command | What it does | Network | Writes |
|---|---|---|---|
| `plan` | compares the pinned commit of each original clone with the upstream HEAD (`git ls-remote`, hashes only) | read-only query | a plan JSON |
| `fetch --confirm-download` | clones the repos into a **new** snapshot folder `snapshots/snap_<UTC>/<repo>`, records URL, commit, commit date, retrieval UTC in `SNAPSHOT_MANIFEST.json`; refuses to run without the flag | downloads | new folder only |
| `parse --snapshot DIR` | parses every league file, validates, compares with the frozen universe, writes a run folder | none | `runs/<run_id>/` |
| `selftest` | runs the same parse on the **pinned original clones** (read-only) | none | `runs/selftest_*` |

## Run outputs (each file made read-only)
`new_results.csv` (completed, regular-round, 90-minute-clean results dated after 2026-09-20), `fixtures.csv`, `unresolved_or_non_completed.csv`, `conflicts.csv`, `duplicates.csv`, `parser_issues.csv`, `files_hashed.csv` (sha256 of every source file), `run_manifest.json`, and `results_universe_refreshed.pkl` = frozen universe + new results as a **separate** file (`NEW:<run>:<file>:L<line>` record ids). `V_universe.pkl`, dataset v1.1, the clones in `_raw_sources` and the training snapshot are never written.

## Validation rules
* Competition: a file must exist in the frozen universe (or is reported `competition_file_not_in_frozen_universe` and not used); season from the frozen file map (the corrected season label).
* Teams: resolved only through the frozen (competition, team name) -> entity map; unknown names are `team_not_resolved_to_entity` — never guessed or auto-created.
* Dates: required, parsed by the project parser (explicit year/weekday); stage must be a regular round-robin stage.
* Scores: integers 0-25; 90-minute result only — rows with extra time or penalties in a league file, awarded/walkover/abandoned rows are classified separately and not used.
* Status classes: `completed`, `completed_extra_time_or_penalties`, `awarded_or_abandoned`, `postponed`, `cancelled`, `upcoming` (no score, date >= run date), `past_date_no_result` (no score, date earlier than the run date), `unresolved`. Nothing is inferred or fabricated; missing results stay missing.
* Duplicates: identical (competition, season, date, home, away) key appearing more than once. Conflicts: the same key with different scores/status inside a snapshot, or a result dated <= 2026-09-20 whose score differs from the frozen data (reported, never applied).
* Rows dated <= 2026-09-20 are only compared, never imported.

## Self-test on the pinned original snapshot (`ingestion/runs/selftest_*`)
675 league files, 221,754 rows parsed; **201,850 frozen results re-found (all frozen domestic-league rows), 0 score conflicts, 0 new completed results, 2 historical rows in the source that are not in the frozen universe, 24 duplicate groups, 28 parser-issue rows, 3,168 upcoming and 271 unresolved/non-completed fixtures after the cutoff.** The pipeline therefore reproduces the frozen data exactly and finds nothing newer than 2026-09-20 in the original snapshot.

## Plan result (read-only, 2026-10-21)
`git ls-remote` shows the upstream HEAD of all nine repositories **equals the pinned commit** — the approved source has published nothing newer than the training snapshot. Running `fetch` now would download the same content. See the readiness report: this is the main blocker for eligible predictions.
