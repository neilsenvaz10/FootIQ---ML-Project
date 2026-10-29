# 07 Source provenance and conflict handling

## Provenance kept for every ingested row
source name and licence (openfootball, CC0); repository URL; commit sha and commit date of the snapshot; retrieval timestamp (UTC); file path and line number; raw source text; sha256 of the source file (`files_hashed.csv`); run id and parser version (script hash in the run manifest); competition id / season / entity ids as resolved, with the rule that produced them. Record ids of new results are `NEW:<run_id>:<file>:L<line>` so they cannot be mistaken for training records.

## Immutability
Snapshots (`ingestion/snapshots/snap_*`) and run folders are written once; run files are set read-only; the training snapshot (`V_universe.pkl`, dataset v1.1, `_raw_sources`) is opened read-only only. A new retrieval always creates a new snapshot folder; it never updates a clone in place.

## Conflict policy
| Situation | Handling |
|---|---|
| Result dated <= 2026-09-20 whose score differs from the frozen data | Written to `conflicts.csv`; **never applied**; frozen models/training data untouched; the owner decides whether a data-correction version is needed |
| Same fixture twice in one snapshot with different score or status | Both rows excluded from `new_results.csv`, listed in `conflicts.csv`; fixture cannot be evaluated until resolved |
| Same fixture duplicated with identical content | Listed in `duplicates.csv`, one copy kept |
| Result for a fixture changes between two snapshots | Not "confirmed" (needs identical score in two snapshots >= 24 h apart); the fixture is excluded from evaluation and counted |
| Unknown team name / competition file / non-regular stage / implausible score | `unresolved_or_non_completed.csv`; not imported; never guessed |
| Postponed, cancelled, abandoned, awarded | Classified, excluded from results and from scoring, counted in coverage reports |
| Past-dated fixture with no result | `past_date_no_result`; any club with such a fixture is `club_has_unresolved_past_fixture` and its later fixtures leave the primary population |
| Upstream silent about recent matches (current situation) | `stale_competition_results` flag when the competition's latest result is > 14 days before the fixture date |
| Result appears for a match that was already predicted | Attached to the prediction by fixture id only after the batch is sealed; a result can never create or alter a prediction |

No result is ever fabricated, interpolated or copied from another competition. Differences between snapshots are tracked by file hash.
