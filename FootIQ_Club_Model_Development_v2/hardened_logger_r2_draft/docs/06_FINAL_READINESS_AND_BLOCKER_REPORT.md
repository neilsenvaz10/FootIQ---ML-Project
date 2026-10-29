# Final readiness and blocker report — protocol r2 draft and hardened logger (2026-10-21)

Draft work only. Protocol r2 is **not** active or hashed; no approval file, official ledger, official prediction, live request, polling, scheduling, retraining or Git staging/commit took place. Frozen models, datasets and protocol r1 are unchanged (hash-verified in `05_REPRODUCIBILITY_MANIFEST.json`); no contact string appears in this folder (0 occurrences, 34 files scanned); `config/contact.local` is git-ignored.

## Direct answers
| Question | Answer |
|---|---|
| Does the logger pass every adversarial test? | **Yes: 37/37 PROTECTED** (the 19 earlier attacks, 11 of which were defects, plus 18 new areas), 40/40 hardened unit tests, and the earlier adapter (19), logger-v2/parity (22) and official-logger validation (13) suites still pass. Predictions are unchanged versus the sealed v2 shadow batch (max diff 0.0). Caveats: official-path tests ran only in a temp-directory sandbox with synthetic approvals; three of the 19 re-run checks are partly structural (see report 03). |
| Is protocol r2 ready for your final review? | **Yes, as a draft.** `01_PROPOSED_PROTOCOL_R2_DRAFT.md` incorporates AA-1…AA-14 (matrix in `02`), keeps every scientific requirement of r1 (primary log loss, the three comparators, 5,000 results / 25 competitions / 3 months, bootstrap and calibration method), separates the Bundesliga operational pilot (`07`) from the scientific evaluation, and replaces only r1 condition (f). |

## Decisions that are yours before r2 can be finalised
1. **Stage definition (R2.1):** Bundesliga results count toward the pre-registered sample, no inferential comparison in Stage 1, and the 12-month/15,000 limits start with Stage 2. Confirm or change.
2. **Missing results (R2.13):** pending until an analysis checkpoint (no rolling 7-day exclusion). Confirm.
3. **Late-arriving results (R2.12):** flagged and eligible with a sensitivity analysis. Confirm.
4. **Wikipedia:** confirmation-only and unused until its licensing document is approved. Confirm.
5. **Anchor location:** the default anchor file is `D:\Foot IQ\ledger_anchor_official\anchor.jsonl`, outside the ledger folder but on the same drive; choose a location on another drive or medium and keep your own copy of each printed batch hash.
6. **How labels are confirmed in practice (R2.7):** requires manual polls at ≥ 48 h and ≥ 72 h after each matchday; confirm you accept that duty.

## Remaining blockers
1. Your approvals: final r2 text (then hashing and a new pre-registration), acceptance of the logger version (its artifact-manifest sha256 is bound into the approval), each live poll plan, the approval file you create, and the sealing run.
2. The `s1_additions` producer (newer OpenFootball snapshot → hashed frame) is not built; until then only the pinned S1 universe is used.
3. OpenLigaDB gives no explicit postponed/cancelled status and no accuracy guarantee; both are handled conservatively but remain inferences.
4. A fresh OpenLigaDB poll (≤ 24 h before sealing) and the manual poll duties around each matchday; none is scheduled.
5. Scientific power: one league cannot reach the r1 gates; Stage 2 needs additional validated competitions by amendment.
6. The pilot-runner `pilot_openligadb.py` plan (r1) is the only authorised retrieval plan; a lighter change-date poll plan is not built.

## Is matchday 8 still feasible?
Yes, but tight: first matchday-8 sealing deadline **2026-10-30 18:30 UTC** (Elversberg–Mainz). Needed in order: your review and approval of r2 (and its hash), your acceptance of the logger manifest, a live poll plan approval, the approval file, a poll ≤ 24 h before sealing, preflight `passed: true`, then sealing — all by 2026-10-30. If the approvals slip past about 2026-10-28, matchday 9 (first kickoff 2026-11-06 19:30 UTC) is the fallback.

## Exact command sequence after approval (from `08_UPDATED_OPERATIONAL_RUNBOOK.md`)
```
cd "D:\Foot IQ\FootIQ_Club_Model_Development_v2\hardened_logger_r2_draft"
python -I scripts\pin_manifest.py                              # manifest sha256 must equal the one in your approval file
python -I -m unittest discover -s tests ; python -I tests\adversarial_regression.py
set FOOTIQ_CONTACT_FILE=D:\Foot IQ\config\contact.local
python -I ..\source_adapters_r1\pilot_openligadb.py run --plan-sha256 <approved plan sha256>      # P2 poll, within 24 h of sealing
python -I scripts\preflight.py --snapshot <new R3 snapshot path>                                   # must print passed: true
set FOOTIQ_OFFICIAL_MODE=1
python -I scripts\seal_official.py --official --snapshot <new R3 snapshot path>                    # prints the batch hash for your records
set FOOTIQ_OFFICIAL_MODE=
python -I scripts\verify_ledger.py ; python -I scripts\status_report.py --snapshot <new R3 snapshot path>
# later, after manual polls >= 48 h and >= 72 h after the last kickoff:
python -I scripts\reassess_official.py --snapshot <old R3> --snapshot <new R3> --write ; python -I scripts\reconcile_results.py
```
Do not run any `seal_official` command before you have approved r2, created the approval file and authorised the run.
