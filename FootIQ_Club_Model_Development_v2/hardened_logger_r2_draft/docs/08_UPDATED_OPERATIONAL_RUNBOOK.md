# Updated operational runbook — first authorised Bundesliga official batch (target: matchday 8)

Template. **Nothing here has been run in official mode.** No scheduler, no automatic polling. Every step is started by a person. Commands run from `D:\Foot IQ\FootIQ_Club_Model_Development_v2\hardened_logger_r2_draft` with `D:\Foot IQ\.venv\Scripts\python.exe -I`.

## 0. Approvals required (each explicit, in chat)
1. Protocol r2 text (`docs/01_PROPOSED_PROTOCOL_R2_DRAFT.md`) approved → file frozen, sha256 recorded, new pre-registration written (not yet done).
2. Logger version accepted: the owner records the artifact-manifest sha256 printed by `scripts/pin_manifest.py` (any later code change changes it and invalidates the approval).
3. Live OpenLigaDB poll plan approved (host, requests, attempt cap, plan sha256) for each poll.
4. The owner creates `matched_v1_prospective_r1\OFFICIAL_LOGGING_APPROVED.json` (fields in `hardened/approval.py`: approval_version, approved_by, approved_utc, expires_utc, mode=official, protocol{version r2, sha256, path}, models{three sha256}, artifact_manifest_sha256, competition_id, season, source_scope{openligadb bl1/2026}, sealing_window, max_fixtures, optional matchdays).
5. Authorisation of the sealing run itself.

## 1. Environment (each session)
`set FOOTIQ_CONTACT_FILE=D:\Foot IQ\config\contact.local` (never print it) · system clock synchronised · `git status`: nothing staged · official switch off until step 5.

## 2. Preconditions (read-only)
```
python -I scripts\pin_manifest.py                       # prints the manifest sha256 to compare with the approval (draft pin only)
python -I -m unittest discover -s tests                 # whole hardened suite
python -I tests\adversarial_regression.py               # every attack PROTECTED
python -I scripts\verify_ledger.py                      # no ledger yet -> ok; later: chain + anchor
python -I scripts\validate_approval.py                  # exits 1 until a valid approval exists
```

## 3. OpenLigaDB freshness and manual poll
* P2 (mandatory): within 24 h before sealing, after the authorised plan hash is supplied: `python -I ..\source_adapters_r1\pilot_openligadb.py run --plan-sha256 <approved plan sha256>` (≤ 6 requests, ≥ 2 s apart, ≤ 12 attempts; refuses within 1 h before / 3 h after a Bundesliga kickoff). Note the new R3 snapshot path in the run folder.
* Pass criteria: all HTTP 200; league 4937/bl1/2026; snapshot hash recorded; poll clock skew ≤ 120 s; no integrity events (preflight below).

## 4. Preflight (read-only)
```
python -I scripts\preflight.py --snapshot <R3 snapshot path>
```
Must print `passed: true`. It checks model artifacts, manifest pin, approval, ledger and anchor, snapshot hash/scope/order/age/skew, contact file git-ignored (value not shown), nothing staged.

## 5. Sealing (official; owner-authorised only)
```
set FOOTIQ_OFFICIAL_MODE=1
python -I scripts\seal_official.py --official --snapshot <R3 snapshot path>
```
The tool takes the system clock only, validates the approval (protocol hash, model hashes, manifest, scope, window, max fixtures, matchdays), refuses on any ledger/anchor problem, skips fixtures already sealed, writes the batch atomically, anchors it, and prints the batch hash. **The owner copies the printed batch hash into the owner-held ledger and clears the switch (`set FOOTIQ_OFFICIAL_MODE=`).** Seal all matchday-8 fixtures in one batch before **2026-10-30 18:30 UTC**.

## 6. Verification right after sealing
```
python -I scripts\verify_ledger.py                      # chain, anchor, no pending intents
python -I scripts\status_report.py --snapshot <R3 snapshot path>
```
Check: records = fixtures sealed, every record `namespace=official`, model hashes equal the approval, the anchor file (outside the ledger folder) lists the batch, no contact string in new files.

## 7. After the matches (manual polls ≥ 48 h and ≥ 72 h after the last kickoff)
```
python -I scripts\reassess_official.py --snapshot <old R3> --snapshot <new R3> --write   # chained side-car: reschedules, removals, identity, late history, labels
python -I scripts\reconcile_results.py                                                    # confirmed labels, conflicts for adjudication
python -I scripts\reassess_official.py --snapshot ... --checkpoint                        # at an analysis checkpoint only
```

## 8. Failure handling
| Situation | Action |
|---|---|
| Poll fails / stale snapshot / skew > 120 s | do not seal; fixtures stay unpredicted and are counted; retry only within the approved plan |
| Integrity event (withdrawn, corrected, rejected played match) | affected clubs' fixtures are logged ineligible; adjudication log (owner) |
| Interrupted sealing (`verify_ledger` reports pending intent / unanchored batch) | `python -I scripts\verify_ledger.py --recover`, then verify again, then re-run sealing (idempotent) |
| Deleted batch / anchor mismatch | stop all logging, report to the owner, do not repair silently |
| Wrong batch sealed | never delete; a superseding record is written by the owner-authorised procedure; evaluation uses the first valid seal |
| Artifact or protocol hash mismatch | sealing refuses; re-approval required |

## 9. Attribution and audit
Attribution string on every record. Audit log (append-only, owner-readable): date/time, operator, approvals, plan sha, snapshot ids/hashes, batch hash and ledger entry, preflight output, deviations.
