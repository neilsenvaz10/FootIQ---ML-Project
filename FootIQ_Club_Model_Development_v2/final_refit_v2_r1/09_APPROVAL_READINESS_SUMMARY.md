# 09 Approval-readiness summary — Club ML v2-r1

Status: **frozen prospective candidate created and verified. Not deployed, not integrated, v1 not replaced, nothing staged/committed/pushed/merged.**

## Frozen facts
* Candidate: multinomial LR, 62 features, C=0.01, no calibration — `artifacts/club_v2_lr_final_candidate.pkl`, sha256 `55c1e4c53bcfefd39d5e90a1ce60a75bc697668f7894e425305bdc9a65b3e56c`.
* Freeze timestamp 2026-10-21 17:45:33 +05:30. **Training cutoff: last match date 2026-09-20** (snapshot extracted 2026-10-20). **Matches used: 116,854** (2018-08-01..2026-09-20, 115 competitions, 2,198 clubs; H 50,967 / D 30,907 / A 34,980).
* Seed 20261021; scikit-learn 1.5.1-class environment recorded in `FROZEN.json`.

## Pre-refit issues
| Issue | Outcome |
|---|---|
| 582 Zimbabwe Elo mismatches | Resolved: lost same-day Elo update in the v2 generator (fixed); triggered by a duplicate-date source anomaly in zw1 2021-22. Report 01. |
| Leakage and parity checks | Re-run, all pass (report 02 files). |
| 0.0030 vs 1.0189/1.0163 | Reconciled: 0.0026 fold-mean, 0.0030 pooled (report 03). |
| Dev results after the fix | Unchanged to < 6e-6 log loss. |

## Evidence level (unchanged)
Development-validated only: gain of 0.0026-0.0030 log loss over v1 LR (about 0.3%), 0.0057-0.0062 over the Elo mapping, in 3 yearly folds; accuracy gain vs v1 LR about 0.1 pp. **There is no unbiased evaluation of v2-r1**: the refit consumed the previously inspected v1 test/holdout periods as training data.

## Unresolved issues / decisions needed from you
1. **Prospective logging is built and verified, but not ready to run officially.** The results snapshot ends 2026-09-20; official batches need results through ~48 hours before prediction time, ingested via the v1.1 pipeline (no ingestion routine was built or run — outside this task's scope). Until then only the `DRY_RUN` batch exists and it is not counted.
2. **Comparator decision:** the protocol fixes the original frozen v1 LR as primary. A same-data v1 refit (v1-R) for a fairer attribution is not created; approve it before the first official batch if you want it.
3. **Known data defects, unchanged:** Police FC and Vision FC identity collisions (~259 rows), Zimbabwe 2021-22 duplicate-date rows, incomplete cup/continental coverage (45 of 93 development competitions with no cup data), calendar-year leagues. Candidates for a dataset v1.2 with approval.
4. Kickoff times are missing for ~82% of upcoming fixtures; the protocol treats unknown kickoff as 00:00 on the match day (conservative).
5. Immutability is by read-only files + hash chain on this machine; for stronger guarantees, anchor `CHAIN.jsonl` hashes outside the machine (e.g. a committed tag) once you permit commits.
6. Older development tables (`04`, `05`, `08`, candidate pickles in the parent folder) predate the Elo fix; they are retained as historical records.

## Checklist
Frozen spec ✔ · artifact hashes ✔ · independent scorer parity ✔ · inference/training feature parity ✔ · leakage tests ✔ · logger dry run ✔ · v1/World Cup/original datasets untouched ✔ · no DB changes ✔ · no installs ✔ · no Git staging/commit/push ✔ · fresh-results ingestion ✘ (pending) · comparator sign-off ✘ (pending).
