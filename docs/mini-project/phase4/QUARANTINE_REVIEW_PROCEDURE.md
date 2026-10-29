# Quarantine review procedure (for the human operator)

The synchronisation never resolves a disagreement by itself. When a provider's answer conflicts with what the store holds, the finding is written to the `quarantine` table, **the stored value stays in place**, and the status panel / `/api/sync/status` (`quarantine.warning`) shows how many findings need a person. Findings written by the baseline import (`baseline_data_quality_notes`) are notes about the original files, not sync findings.

## Kinds of finding

| Reason starts with | Meaning | What the store keeps |
|---|---|---|
| `CONFLICT: stored A-B vs source C-D` | a completed match has a different score at the provider | the stored score |
| `CONTRADICTORY SOURCE RESULT` | the provider record holds several different final scores | the stored value; nothing is imported from the record |
| `DATE_DIFFERENCE: stored D1 vs source D2` | the provider gives another date; a result for it is held back | the stored date (for prediction eligibility the **earlier** of the two dates restricts the fixture) |
| `unresolved team identity` | a provider team name matches no known club | the fixture is not imported |

## Who and how often
One named operator (the project owner) reviews the panel after every activation day and whenever the banner shows a number above zero. A finding stays open until a decision is recorded.

## Steps
1. List the open findings: `GET /api/sync/status` (`quarantine.by_kind`) and, on a **private copy** of the store, `SELECT id, source_ref, reason, created_utc FROM quarantine WHERE run_id NOT IN (SELECT run_id FROM sync_runs WHERE kind='baseline_import')`.
2. Find the authority: the competition's own record (the league's official fixtures/results page or match sheet), then the club's official page. A second provider is only a confirmation, **never** the deciding source, and "newest answer wins" is not a rule.
3. Write down the evidence: URL, date read, what it says, your confidence (format: `P4_8D_STAGE2_OFFICIAL_EVIDENCE_TABLE.md`).
4. Decide:
   * the provider is right → a reviewed one-row correction (step 5);
   * the store is right → record "rejected: store confirmed by <source>" and leave the row; the provider's value remains a known disagreement;
   * no authority reachable → leave it open; do not guess.
5. A correction is **never** made through the scheduler. Procedure: stop the API; make a SQLite online backup and record its hashes; apply the one-row change on a private copy first and check the standings and the baseline monitor report; then apply it to production in one transaction with the operator's name and the evidence recorded; run `python app/store/baseline_monitor.py report <store>` (expect an explained change) and approve the new checkpoint with `approve --label ... --by <name>`.
6. Record the decision in the evidence table. Do not delete quarantine rows: the baseline monitor treats a shrinking quarantine as an unexpected change.

## What the system will not do
Overwrite a verified score, change a played match's date, choose between sources by recency, or delete a finding.
