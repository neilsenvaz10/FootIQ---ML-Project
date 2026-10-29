# 02 Production-logger audit — `prospective_logger_v2.py` (candidate)

Method: code review + 19 adversarial tests (`adversarial_audit.py`, results `adversarial_audit_results.csv`, log `audit_run.log`). No official records were produced; the module and all frozen items were not modified. Result: **6 protected, 11 defects, 1 partial, 1 gap**. Verdict: **not suitable for official use until the fixes below are made and re-tested.**

| Area | Attack / check | Result | Evidence | Fix required |
|---|---|---|---|---|
| Idempotent batch creation | seal the same fixtures in two batches | **DEFECT** | 6 records for 3 fixtures, chain valid | refuse/skip any fixture already in the chain; deterministic batch name from fixture set; first seal wins |
| Atomic writes / interrupted run | crash after file write, before chain line | **DEFECT** | orphan batch file not detected; no temp+rename, no fsync, no recovery | write temp → fsync → rename → fsync chain line; startup check that fails on orphan/partial files and reconciles |
| Hash-chain integrity | delete newest batch + chain line | **DEFECT** | chain verifies; tail truncation invisible | external anchor: after each batch write the latest chain hash to an owner-held ledger (outside the folder; no Git needed) |
| Model / preprocessing integrity | tamper with v1 preprocessing JSON / Elo parameters | **DEFECT** | `verify_models` hashes v2 and matched-v1 artifacts and the v1 pickle, but not `preprocessing_train_fitted.json` or `baseline_parameters.json`, both used at prediction time | hash all prediction-time artifacts (CRLF-normalised JSON) |
| Code integrity | change the feature generator | **DEFECT** | only the logger file's hash is stored; v2_features.py, feature_contract.py, v2_models.py, d11, e4 are not | store hashes of all code dependencies |
| Snapshot integrity | append a byte | PROTECTED | IntegrityError | — |
| Snapshot scope | feed a 2025 snapshot of the same league | **DEFECT** | 18 results added with 2025 dates | validate leagueShortcut/season/date > 2026-09-20 |
| Completeness | played match without explicit 90-min type | **DEFECT** | 4 of 55 fixtures of the affected clubs stay eligible with a match missing from their history | incomplete-history flag (amendment AA-4) |
| Identity | completed result with unresolvable team | **DEFECT** | 2 eligible fixtures of the opponent remain | same flag |
| Conflict rules | result withdrawn in a later snapshot | **DEFECT** | 18 additions retained | newest snapshot authoritative; retraction quarantines pair |
| Source availability | only a 25 h old snapshot exists | PROTECTED | 252 rejected `stale_kickoff_snapshot`, 0 records | — |
| Source availability | truncated JSON body | PROTECTED | JSONDecodeError, no batch | — |
| Kickoff changes after sealing | moved/postponed/removed | **PARTIAL** | `reassess()` classifies correctly (tests) but nothing persists it in a chain, schedules it or feeds an eligibility table | `write_reassessment_batch` + verifier; run at every poll |
| Late-arriving results | history result appears after sealing | **GAP** | no detection | side-car flag (amendment AA-12) |
| Clock / timezone | explicit earlier `T` | **DEFECT** | records stamped with a past time accepted; no wall-clock or server-Date check | official entry point reads the system clock only, validates it against the newest HTTP `Date` (stored in snapshot meta; the pilot's offset was about 2 s), rejects explicit `T` |
| Retrospective predictions | seal after the first deadline | PROTECTED | rejected `sealing_deadline_passed_no_backdating` | — |
| Reconstruction | alter a sealed probability | PROTECTED | mismatch detected | — |
| Shadow/official separation | satisfy the official gate with empty `{}` files | **DEFECT** | gate only tests file existence; no official writer/directory exists; `write_shadow_batch` asserts shadow | gate validates content (model hashes, protocol r2 sha256, logger code hash, scope, approval timestamp); separate official writer and directory |
| Contact privacy | scan 252 records | PROTECTED | no email-like string; logger never reads the contact | — |

## Other review observations
* The S1 past-dated-fixture list (`pnr_of`) is read from a `selftest` run folder path; official use needs it produced by a dated ingestion run recorded in the batch.
* The universe hash check is tied to the pinned universe; the S1-update path (amendment AA-2) needs a merged-universe hash.
* `predict_shadow` rebuilds the full 216,571-row state per call (about 40 s): acceptable for a manual batch, not for per-record reconstruction (the batch reconstructor groups by timestamp).
* Positive findings: strict retrieval-time filtering, UTC deadline logic, stale-kickoff-snapshot refusal, hash verification of snapshots/models/universe, deterministic output, exact reconstruction of all 252 shadow records, one history for all four models, no contact leakage.

## Estimated work to make the logger production-ready
About 3–4 working days including tests: official writer + gate (1), idempotency/atomicity/anchor (1), validation and incomplete-history flags (1), side-car writer and clock check (0.5–1), full re-run of tests and a new shadow rehearsal (0.5).
