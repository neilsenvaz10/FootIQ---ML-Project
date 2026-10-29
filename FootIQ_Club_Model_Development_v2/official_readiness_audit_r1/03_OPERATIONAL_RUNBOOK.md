# 03 Runbook — first authorized Bundesliga official prediction batch (target: matchday 8)

Status: **template. Not executable today.** Steps marked `[EXISTS]` run now; `[TO IMPLEMENT]` are the logger fixes of report 02 (official writer/gate, idempotency, atomic write, anchor, scope validation, incomplete-history flag, clock check, side-car writer). No scheduler or automatic polling is authorized: every step is started by a person.

## 0. Required approvals (all explicit, in chat, before step 1)
| # | Approval | Owner action |
|---|---|---|
| A | Amendment A1 **revised** per report 01 (exact text) and issued as protocol r2 | approve text; protocol r2 file + sha256 + `PREREGISTRATION_r2.json` are then written (the r1 files stay) |
| B | Logger v2.1 (fixes) accepted as the production logger after re-test and a new shadow rehearsal | approve code hashes |
| C | Live OpenLigaDB retrieval plan for each poll (host, requests, cap, plan sha256) | approve plan sha |
| D | Stage-1 statement (Bundesliga batches count toward the r1 sample; gates unchanged) | acknowledge |
| E | `OFFICIAL_LOGGING_APPROVED.json` | **created by the owner**, containing the three model sha256s, protocol r2 sha256, logger code sha256, scope `bl1/2026`; this runbook never creates it |

## 1. Environment (each session)
* Python: `D:\Foot IQ\.venv\Scripts\python.exe -I` (no installs).
* Contact: file `D:\Foot IQ\config\contact.local` exists and is git-ignored; `FOOTIQ_CONTACT_FILE` points to it. Never print it.
* Clock: system time synchronised (Windows time service). The sealing tool compares it with the HTTP `Date` header of the newest poll (skew <= 120 s) `[TO IMPLEMENT]`.
* Git: nothing staged; `git status` shows no tracked changes; `config/contact.local` ignored (`git check-ignore`).
* Integrity gate `[EXISTS]`: `python -I -m unittest discover -s source_adapters_r1/tests` and `shadow_integration_r1/tests` must pass; `official_readiness_audit_r1/adversarial_audit.py` must show 0 DEFECT after the fixes.

## 2. Freshness and poll (manual; at most three times for a matchday)
Matchday 8 timeline (UTC): matchday 7 kicks off 10-23 … 10-25; matchday 8 first kickoff **2026-10-30 19:30** (deadline 18:30), last 11-01 16:30.
* **P1 (optional, 10-26 after matchday 7)**: look for the matchday-7 results (state freshness; not required for eligibility, since the 14-day window already covers matchday 8).
* **P2 (mandatory, 10-29 or 10-30 early, within 24 h before sealing)**: the snapshot that supplies kickoffs and results.
* Poll plan: approved plan sha256 (C). `[EXISTS]` `python -I source_adapters_r1/pilot_openligadb.py run --plan-sha256 <approved sha>` performs the bounded six-request retrieval into a new run folder; the plan (host `api.openligadb.de`, <= 6 requests, <= 12 attempts, >= 2 s apart) and its sha are shown to the owner first (`... plan`). A leaner "change-date poll" plan (getcurrentgroup + 2 x getlastchangedate, full season only if changed) is `[TO IMPLEMENT]` and needs its own approval.
* Pass criteria for a poll: all HTTP 200, league confirmed 4937/bl1/2026, snapshot hash recorded, 0 conflicts, 0 identity errors, 0 rejected completed records, kickoffs UTC, no match in progress during the poll (the guard refuses within 1 h before / 3 h after a Bundesliga kickoff).

## 3. Eligibility verification (before sealing) `[EXISTS for shadow; official entry TO IMPLEMENT]`
Run the logger in shadow mode on the P2 snapshot (`run_shadow_bundesliga.py` pattern) and check: 252 future fixtures, all deadlines in the future, matchday-8 fixtures primary-eligible (9 expected), reasons for others listed, `reconstruct_batch` 100% identical, deterministic twice, canary test passes. Stop if any check fails.

## 4. Sealing (official) `[TO IMPLEMENT: seal_official.py]`
Expected shape: `python -I shadow_integration_r1/seal_official.py --approval <path to OFFICIAL_LOGGING_APPROVED.json> --snapshot <P2 R3 path> --matchday 8`. The tool must: read the system clock only; validate the approval content; verify all hashes; refuse fixtures already in the chain (idempotent); write temp → fsync → rename; append the chain line; set read-only; print the new chain hash to be stored by the owner in the external ledger.
Seal **all matchday-8 fixtures in one batch before 2026-10-30 18:30 UTC** (earliest deadline). Never seal a fixture whose deadline has passed; never re-seal.

## 5. Immutable-record verification (right after sealing)
Chain valid; batch read-only; record count equals the fixtures sealed; every record `namespace=official`, model hashes equal the approval; reconstruct every record from the saved snapshot (100%); external ledger entry made; `git status` unchanged; contact string search over the new files = 0.

## 6. After the matches: reassessment and reconciliation
* Poll again >= 48 h after the last matchday-8 kickoff (>= 2026-11-03 16:30) and once more >= 24 h later (label confirmation). Each poll follows section 2.
* Run the side-car reassessment (`reassess`, with a chained writer `[TO IMPLEMENT]`): kickoff moves, removals, identity changes, missing results, conflicts, late-arriving history, label status.
* Reconcile results against S1 when a newer S1 snapshot exists (`e3 plan`, then fetch only if approved).
* No metric is computed before the r1 gates are reached; only descriptive coverage reports.

## 7. Failure and rollback
| Situation | Action |
|---|---|
| Poll fails or hash mismatch | do not seal; keep the previous snapshot unused; retry within the approved attempt cap; if the 24 h window cannot be met, skip the batch (fixtures stay unpredicted, counted) |
| Conflict, retraction or incomplete-history event | do not seal fixtures of the clubs involved; log the event; the adjudication log is owner-only |
| Interrupted sealing | startup recovery checks temp/orphan files; never edit a sealed batch; an unsealed temp file is deleted and the run repeated with a new timestamp (idempotency prevents duplicates) |
| Wrong batch sealed | sealed records are never deleted: mark them `superseded` in a new chained record, explain in the audit log; evaluation uses the first valid seal per fixture |
| Anchor/ledger mismatch | stop all logging, investigate, report to the owner |
| Source terms change (OpenLigaDB announces registration/quotas) | stop; re-verify terms and re-approve the plan |
There is no rollback of sealed predictions; only supersession entries.

## 8. Attribution and audit logging
Every record carries `Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0`; any published table repeats it. Audit log (append-only, owner-readable): date/time, operator, approval references, plan sha, snapshot ids/hashes, batch name and hash, ledger entry, checks passed/failed, deviations.
