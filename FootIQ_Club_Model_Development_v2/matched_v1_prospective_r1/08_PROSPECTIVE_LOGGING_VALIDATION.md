# 08 Prospective logging validation

Code: `_scripts/e4_prospective_logger.py` (logger), `_scripts/e5_logging_validation.py` (tests + dry run). Results: `08_prospective_logging_validation.csv` (13/13 pass), `08b_dry_run_rejected_fixtures.csv`, `08c_dry_run_eligibility_summary.csv`, dry-run chain in `prospective_log/DRY_RUN/`.

## What each record holds
fixture id; competition; season; home/away names and entity ids; scheduled kickoff (date + local time, `kickoff_time_known`); earliest possible kickoff UTC; prediction timestamp (UTC); feature availability cutoff text; input snapshot id and sha256; model versions and sha256 for original v1, matched v1, frozen v2 (plus the v1 Elo mapping); H/D/A probabilities for each; history depth; eligibility reasons and `primary_eligible`; coverage flags; feature-vector hash; mode and `counts_for_evaluation`; hash of the previous batch.

## Tests (all pass)
1. Dry run wrote an immutable (read-only), hash-chained batch: 416 predictions for domestic-league fixtures dated 2026-10-22 .. 2026-11-08.
2. Dry-run records are marked `counts_for_evaluation=False`; dry runs use a separate chain.
3. A fixture whose earliest possible kickoff is under 60 minutes away (today's date) is rejected; fixtures already completed in the snapshot (five real 2026-09-20 matches) are rejected — no backdating, no prediction for finished matches.
4. All four probability sets sum to 1 and are positive; v2 and original-v1 probabilities are identical to the earlier dry run of the same fixtures (296 common, max diff 3e-16); matched-v1 probabilities equal an independent numpy scorer built from the coefficient JSON (diff 0).
5. Model hashes stored in every record equal the artifacts on disk; `verify_models()` aborts if any frozen file changes.
6. Official mode refuses to run without the owner's `OFFICIAL_LOGGING_APPROVED.json` (absent) and without the pre-registration file; it also checks the approval's model hashes.
7. Editing a stored batch breaks the chain check; stored batches cannot be opened for writing.
8. A fixture involving a collision club is flagged `identity_collision_unresolved` and is not primary-eligible.

## Dry-run eligibility finding (important)
Of 416 fixtures, **0 are primary-eligible**: 404 fail because the club has an unresolved past-dated fixture and the competition's latest result is more than 14 days old; 12 additionally have too little history. The cause is the source: the approved upstream has no result after 2026-09-20 (report 06), while the 2026-27 season fixtures are already scheduled.

Not tested because it needs a real download/approval: the `fetch` command and a parse of a genuinely newer snapshot.
