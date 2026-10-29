# Adversarial regression report — hardened logger

Evidence: `../adversarial_regression_results.csv`, `../adversarial_regression.log`, `../tests_hardened_final.log`. Code under test: `hardened/` (artifacts, ledger, approval, state, engine) and `scripts/`.

## Result
**All 37 attack scenarios are PROTECTED** (0 defects): the 19 attacks of `official_readiness_audit_r1/adversarial_audit.py` (11 of them were defects before) and 18 new areas backed by the 40-test hardened suite (40/40 pass). Previously failing items and what changed:

| Earlier defect | Fix | Check |
|---|---|---|
| Duplicate sealing | ledger key (fixture_id, model_key); duplicates skipped, batch idempotent | re-seal of 3 fixtures: 0 sealed, 3 skipped |
| Non-atomic write / interrupted run | write-ahead intent → fsync temp → atomic rename → read-only → anchor line; pending intent, temp or unanchored batch fail verification; explicit `recover` (anchors a committed batch, discards partial ones) | crash after intent, mid-write, after temp, after rename |
| Tail truncation | external anchor file, contiguous batch numbering, prev-hash chain, header record hashes | newest batch deleted → detected; middle deletion, rename/reorder, record edit, missing anchor → detected |
| Caller-supplied timestamp | `seal_official` has no time parameter; system clock only; monotonic against the ledger; poll-time clock skew ≤ 120 s; snapshot not in the future | signature test; clock regression, skew, future snapshot refused |
| Wrong league/season snapshot | `ScopeError` at load; additions must be dated after 2026-09-20 | 2025 / bl2 snapshots rejected |
| Played match missing from the state | incomplete-history events (unresolved identity → competition blocked; no explicit 90-min type, missing known match, removed fixture → clubs blocked) | 55 fixtures of the affected clubs ineligible; competition-wide block for an unknown team |
| Retraction / correction undetected | version tracking across snapshots: `withdrawn_result`, `corrected_result` quarantine the pair and block clubs | additions fall from 18 to 17, clubs blocked |
| v1 preprocessing / Elo parameters / feature code not hashed | 34-entry artifact manifest (all model artifacts, v1 preprocessing and Elo parameters, Elo2 parameter file, feature contracts, preprocessing spec, feature code, adapters, logger code, frozen universe, exclusions); prediction aborts on mismatch; approval binds the manifest sha256 | tamper of each class detected on temp copies; prediction aborts with `IntegrityError` |
| Official gate opened by empty files | content validation: JSON object, required fields, mode, expiry, window, protocol version + sha256 of the protocol file, exact model hashes, manifest hash, competition/season/source scope, max fixtures; off by default (needs `--official` AND `FOOTIQ_OFFICIAL_MODE=1`) | empty, `{}`, malformed, expired, future and mismatched files all rejected |
| Side-car not persisted / late results undetected | `reassess` with a chained writer (`scripts/reassess_official.py --write`), `late_arriving_history_result` flag | reassessment tests |

## New attack areas tested
duplicate sealing; interrupted writes (4 crash points); missing newest batch (plus middle deletion, reorder, edit, missing anchor, stale lock); historical timestamp spoofing; empty/invalid approvals; source withdrawals; stale and out-of-order snapshots; missing played matches; corrected results; postponed/rescheduled fixtures (freshness re-check, two-snapshot rules); tampered feature code, preprocessing and Elo parameters; invalid protocol hashes; official mode off by default; late-arriving results; determinism and reconstruction; second-source agreement and conflict; scope validation.

## Other suites re-run after the change
Source adapters 19/19 · shadow logger v2 and parity suite 22/22 · official-logger validation (e5) 13/13 · parity versus the sealed v2 shadow batch: 252 fixtures, max probability difference 0.0, identical eligibility and v2 feature hashes (18 eligible).

## Limits of the evidence
* Checks 9, 12 and 13 of the 19 regression items are partly structural (existence of the hashing, the side-car writer and the flag); the behaviour is exercised by the unit tests listed beside them.
* The official sealing path was exercised **only in a sandbox inside the system temp directory** with synthetic approval files (namespace `official-sandbox`, `counts_for_evaluation=false`). No official ledger, anchor, approval file or official prediction exists in the project. The CLI scripts were run only in refusal or read-only modes (`seal_official.py` refused: official mode off).
* A stale lock file from a crashed process blocks writing until a person removes it (by design).
* Simulated crashes cover process interruption; they do not model disk or power failure beyond fsync and atomic rename.
