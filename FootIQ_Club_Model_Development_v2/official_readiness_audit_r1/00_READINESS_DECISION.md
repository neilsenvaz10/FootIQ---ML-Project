# Final Bundesliga official-logging readiness decision (2026-10-21)

Audit only. Nothing official was created: no `OFFICIAL_LOGGING_APPROVED.json`, no official records, no polling or scheduler, no new competition. Frozen models, datasets and protocol r1 are unchanged (hash-verified). Nothing staged or committed. Reports: `01_AMENDMENT_A1_AUDIT.md`, `02_LOGGER_V2_AUDIT.md`, `03_OPERATIONAL_RUNBOOK.md`; evidence `adversarial_audit_results.csv`.

## Decisions
| Question | Decision |
|---|---|
| Is amendment A1 suitable for approval? | **Not as written.** 12 checks: 5 must-fix issues (sample-size gates and bootstrap clusters are incompatible with a Bundesliga-only run; no S1-update/de-duplication path; rejected or unresolved completed results are not treated as conflicts; sealing rules clash with r1 condition (f) and allow re-sealing; late-arriving and missing-result treatment undefined; rescheduled-later fixtures skip the staleness re-check). 14 concrete edits (AA-1…AA-14) fix them; none changes models, metrics or comparators. |
| Is logger v2 suitable for official use? | **No.** Adversarial audit: 6 protected, 11 defects, 1 partial, 1 gap. Defects include duplicate sealing, non-atomic writes and tail truncation, caller-controlled timestamps, an official gate that opens for empty files and no official writer, unvalidated snapshot scope (a 2025 snapshot adds results), played matches silently missing from the state without flagging the clubs, unhashed v1 preprocessing/Elo parameters and feature code. Strengths confirmed: strict retrieval-time filtering, UTC deadlines, stale-snapshot refusal, snapshot/model/universe hashes, determinism, exact reconstruction, single history for all models, contact privacy. Estimated fix + re-test: 3–4 working days. |
| Is matchday 8 still a feasible first target? | **Feasible but tight.** Earliest matchday-8 deadline **2026-10-30 18:30 UTC** (Elversberg–Mainz, kickoff 19:30); 9 fixtures are primary-eligible now and stay so (latest result 2026-10-18 is within 14 days of 10-30…11-01). A fresh poll must fall within 24 h before sealing (10-29/30). Needs: amendment revised + approved + hashed, logger fixes + shadow re-run, your approvals A–E, all by about **2026-10-28**. If not met, fall back to matchday 9 (first kickoff 11-06 19:30 UTC; eligible if matchday 7 results are in the state, i.e. latest result >= 10-25 within 14 days of 11-06…08). Matchday 7 (deadline 10-23 17:30) is not feasible. |

## Steps that require your explicit authorization
1. Approve the revised A1 text (including the Stage-1 statement that Bundesliga batches count toward the r1 sample and r1's gates are not met by one league) → protocol r2 hash and pre-registration.
2. Authorise implementation of the logger fixes (report 02) and acceptance of the resulting version as production logger.
3. Approve each live OpenLigaDB poll plan (host, requests, attempt cap, plan sha256) — the P2 poll on 10-29/30 and the later label-confirmation polls.
4. Create `OFFICIAL_LOGGING_APPROVED.json` yourself (model hashes, protocol r2 hash, logger hash, scope).
5. Authorise the sealing run itself and the external ledger entry.
6. (Optional) Wikipedia confirmation-only use; new S1 fetches (`e3 fetch --confirm-download`) if openfootball publishes new commits.

## Remaining blockers
* Amendment text edits and approval; protocol r2 not yet written.
* Logger v2.1 not yet built; no official writer exists.
* Manual polling cadence and operator (polls on 10-29/30, then >= 48 h and >= 72 h after matchday-8 kickoffs).
* Single-league sample: r1's 5,000 results / 25 competitions cannot be reached; evaluation would stay descriptive until other competitions are added by amendment.
* OpenLigaDB has no explicit postponed/cancelled status and no accuracy guarantee.
* OpenLigaDB terms may change (registration/quotas announced with >= 4 weeks' notice).

## Exact command sequence after approval (template; `[TO IMPLEMENT]` = does not exist yet)
```
# 0  precondition checks (run now, and again right before sealing)
python -I -m unittest discover -s source_adapters_r1/tests
python -I -m unittest discover -s shadow_integration_r1/tests
python -I official_readiness_audit_r1/adversarial_audit.py            # must show 0 DEFECT after fixes
git -C "D:\Foot IQ" check-ignore -q config/contact.local ; git -C "D:\Foot IQ" diff --cached --name-only   # ignored; nothing staged
# 1  environment (do not print the value)
set FOOTIQ_CONTACT_FILE=D:\Foot IQ\config\contact.local
# 2  show the approved poll plan, then run it once (P2, within 24 h before sealing)
python -I source_adapters_r1/pilot_openligadb.py plan
python -I source_adapters_r1/pilot_openligadb.py run --plan-sha256 <approved plan sha256>
# 3  shadow rehearsal on the new snapshot (eligibility, determinism, reconstruction)
python -I shadow_integration_r1/run_shadow_bundesliga.py              # [adapt to the new run folder]
# 4  official sealing (all matchday-8 fixtures, one batch, before 2026-10-30 18:30 UTC)  [TO IMPLEMENT]
python -I shadow_integration_r1/seal_official.py --approval matched_v1_prospective_r1/OFFICIAL_LOGGING_APPROVED.json --snapshot <new R3 snapshot> --matchday 8
# 5  verification  [TO IMPLEMENT: verify_official.py]
python -I shadow_integration_r1/verify_official.py                    # chain, read-only, hashes, reconstruction, ledger, contact scan
# 6  label confirmation polls and side-car (>= 2026-11-03 16:30 UTC, then >= 24 h later)  [side-car writer TO IMPLEMENT]
python -I source_adapters_r1/pilot_openligadb.py run --plan-sha256 <approved plan sha256>
python -I shadow_integration_r1/reassess_official.py
```
Until items marked `[TO IMPLEMENT]` exist and pass their tests, no official batch can be created.

## Bottom line
The data pipeline, source terms, eligibility logic and shadow rehearsal are sound for the Bundesliga, but **neither amendment A1 nor logger v2 is ready for approval as they stand**. With a text revision of A1, the logger fixes (about 3–4 days) and your approvals by about 2026-10-28, matchday 8 remains achievable; otherwise matchday 9.
