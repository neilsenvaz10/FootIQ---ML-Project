# Bundesliga shadow prediction integration — report (2026-10-21)

Scope: logger v2 (shadow-capable) and an isolated Bundesliga 2026-27 shadow rehearsal. **No official logging, no `OFFICIAL_LOGGING_APPROVED.json`, no polling, no other competitions, no retraining, nothing staged or committed.** The existing official logger (`_scripts/e4_prospective_logger.py`), frozen models, datasets and the current protocol are unchanged (hash-verified, `MANIFEST.json`). New code: `prospective_logger_v2.py`; tests `tests/test_logger_v2.py`; run script `run_shadow_bundesliga.py`; amendment text `docs/04_...`.

## 1. Logger integration report
| Requirement | Implementation | Verified by |
|---|---|---|
| Merged OpenFootball + approved OpenLigaDB snapshots | `merged_asof()` = frozen universe + admitted S2 results (Bundesliga 2026-27 only) | shadow run, tests |
| Strict retrieval-time filtering | only snapshots with retrieval <= prediction timestamp are read; each added row carries its snapshot's retrieval time; result kickoff must precede retrieval | late-arriving test; leakage canary (a snapshot retrieved 1 h after T with an extra result left all 252 sealed records identical) |
| Exact UTC kickoff | sealing deadline = source-stated UTC kickoff − 60 min; legacy date-based deadline also recorded | deadline tests |
| Source-specific provenance | per record: input snapshot ids + sha256 + retrieval times, kickoff source, merged-state hash, frozen-universe hash, model hashes, logger code hash, attribution/licence, own record sha256 | shadow records |
| Explicit 90-minute labels | only `After90Minutes`; Unknown/ET/penalty-only finals never enter the state | unclassified-result test |
| Conflict and duplicate rejection | conflict between snapshots, vs openfootball score or date, duplicate ordered pair → quarantined, both clubs flagged `unresolved_conflict` (fixtures ineligible) | 4 tests |
| Model-, snapshot-, universe-hash verification | models vs FROZEN records before every prediction, snapshots re-hashed on load and before use, universe hash cached; any mismatch aborts | hash-failure and tamper tests |
| Deterministic reconstruction | `reconstruct_batch()` rebuilds a sealed batch from the named snapshots and its timestamp | all 252 records identical |
| One history cutoff for every model | one merged universe → one `state_sha256` and cutoff for original v1, matched v1, frozen v2 and v1 Elo | 1 state hash for 252 records |
| Never overwrite records | write-once read-only hash-chained batches; reassessment is a side-car referencing the original record's sha256 | immutability + side-car tests |

Official namespace: `predict_shadow(namespace="official")` raises unless the approval file and an active amendment file exist (neither does).

### Fixture-change handling (side-car `reassess`)
Rescheduled later → eligible, flagged (`rescheduled_later`; >= 7 days = `postponed_more_than_7_days`); moved earlier than the seal allowed → `ineligible_sealed_too_late_after_move`; fixture identity changed → ineligible; removed/cancelled in the newest snapshot → ineligible; missing result → flagged, ineligible after 7 days; conflicting results → ineligible; label status pending/confirmed (two snapshots >= 24 h apart, first >= 48 h after kickoff)/conflict. OpenLigaDB exposes no explicit postponed/cancelled flag, so these are inferred from kickoff changes, disappearance, or a missing result — a documented limitation.

## 2. Shadow-mode test results (`shadow_run_results.json`, `shadow_run.log`)
Prediction timestamp 2026-10-21 15:02:52 UTC, Bundesliga 2026-27, snapshot `20261021T141231Z_R3_getmatchdata_bl1_2026` (age 0.84 h).
* Fixtures genuinely future: 252, earliest kickoff 2026-10-23 18:30Z; all >= 60 min ahead; 0 rejected, nothing backdated.
* Freshness: kickoff snapshot within 24 h ✔; history cutoff 2026-10-18; 5 days to the first fixture.
* Hashes verified: frozen v2 `55c1e4c5…`, matched v1 `33bd80f6…`, original v1 `067426e8…`, snapshot `280f2e8d…`, universe `1c4d758b…`.
* Determinism: two independent runs gave identical record hashes (252/252); reconstruction from the saved snapshot: 252/252 identical.
* Sealing: earliest deadline 2026-10-23 17:30 UTC (50.5 h away); under the legacy date rule 2026-10-22 09:00 UTC; none passed.
* Immutability: batch `shadow_batch_20261021T150252Z.jsonl` read-only, chain valid, tampering detected, `counts_for_evaluation=false` and `namespace=shadow` on every record.
* Contact privacy: 0 occurrences in the shadow log, new folders and the previous step's folder (21 + files scanned); ignore rule intact.
* Leakage: canary excluded by retrieval time; 0 additions retrieved after T; 0 additions dated on/after the first fixture.
* No official artefacts: no approval JSON, no active-amendment file, no OFFICIAL log directory.

Automated tests: **22 new tests pass** (`tests_final_new_suite.log`): late-arriving results, conflicting snapshots, conflict with openfootball, duplicate matches, unclassified results, deadlines/no-backdating/stale kickoff snapshot, rescheduled later / postponed / moved earlier, identity change, removal, missing result, label confirmation and conflict, side-car never alters sealed records, exact reconstruction and tamper detection, model-hash failure, historical feature parity, cross-model history parity, official namespace closed, immutability + no email-like string in records, Bundesliga-only scope. Existing suites re-run: source adapters 19/19, official-logger validation (`e5`) 13/13 (it regenerated its own dry-run folder, which is not a frozen artefact).

## 3. Feature-state parity
* **Historical parity:** Bundesliga fixtures of 2026-09-11..13 (9) computed from the merged universe — both with a per-date truncated state and with all later rows including the 18 new results present — equal the stored training features of the frozen v2 table (62 features, tolerance 1e-9).
* **Prefix invariance** (previous step): scrambling every Bundesliga score dated 2026-10-16 or later and deleting later rows leaves earlier fixtures' features identical (max diff 0).
* **Cross-model parity:** v1 contract and v2 prior-match counts and Elo agree for all 252 fixtures; one merged frame feeds every model.
* **Difference vs the stale state:** 55/62 v2 and 24/25 v1 features change (clubs +2 prior matches, rest days −28, Elo up to 27/42 points); frozen v2 probabilities shift by 0.016 on average, 0.079 max.

## 4. Revised protocol amendment
`docs/04_REVISED_PROTOCOL_AMENDMENT_A1_FINAL_PROPOSED.md`: sources and competition scope, canonical records, conflicts, regulation-time labels, retrieval timestamps and feature freshness, kickoff snapshot freshness and rescheduled fixtures, sealing, eligibility, attribution/provenance, activation. Not activated and not hashed; the existing protocol and its pre-registration are unchanged.

## 5. Updated eligible-fixture count
Of 252 future Bundesliga fixtures, **18 are primary-eligible** (matchdays 7 and 8: 9 each), 234 are ineligible solely for `stale_competition_results` (matchday 9 onwards, from 2026-11-06, > 14 days after the latest result 2026-10-18). Stale openfootball-only state: 0.

## 6. Official logging readiness checklist
| Item | Status |
|---|---|
| Source licensed, terms verified, pilot validated | ✔ |
| Frozen models/protocol/datasets unchanged | ✔ |
| Merged state, as-of filtering, explicit labels, conflict rejection | ✔ (logger v2) |
| Sealing deadlines from UTC kickoff, no backdating | ✔ |
| Deterministic reconstruction of every record | ✔ |
| Immutable chained storage, shadow/official separation | ✔ |
| Fixture-change side-car | ✔ (limitations above) |
| Contact privacy and git hygiene | ✔ |
| Shadow rehearsal passes | ✔ |
| Amendment text approved and hashed (protocol r2 + pre-registration) | ✘ pending owner |
| Logger v2 accepted as the production logger and reviewed | ✘ pending owner (it is currently a shadow module) |
| `OFFICIAL_LOGGING_APPROVED.json` | ✘ not created, by instruction |
| Fresh Bundesliga results polled again after each matchday (staleness window) | ✘ manual process not started |
| Wikipedia confirmation use approved (optional) | ✘ pending |
| Sample size toward the protocol minimum | ✘ Bundesliga alone ~306 matches/season |

## 7. Remaining blockers
1. Owner approvals above (amendment text and hash, logger acceptance, approval file).
2. A repeatable manual polling routine: the 14-day staleness rule means the Bundesliga must be re-polled after matchday 7 (due before 2026-11-06 for matchday 9). Without it, only matchdays 7–8 are ever eligible.
3. Kickoff-snapshot freshness (24 h) means a fresh poll is also needed within 24 h before each sealing run; the 2026-10-21 snapshot expires for sealing at 14:12 UTC on 2026-10-22.
4. OpenLigaDB exposes no explicit postponed/cancelled flag; those cases are inferred.
5. Evaluation power: one league cannot reach 5,000 eligible results from 25 competitions; other leagues remain stale/unrecovered (233 results) and were not touched.
6. Known data issues (Police FC / Vision FC, Zimbabwe) do not affect the Bundesliga.

## Is the Bundesliga technically ready for a future official pre-match batch?
**Technically yes for the Bundesliga alone**: the shadow rehearsal passed every check on 252 fixtures (18 eligible), is deterministic, reconstructible, immutable, leak-free and privacy-clean. It is **not authorised and not procedurally ready**: the amendment must be approved and hashed, the logger accepted, the approval file created by you, and a fresh poll done within 24 h before sealing. Earliest realistic sealing: matchday 7 by 2026-10-23 17:30 UTC (needs a poll after 2026-10-22 14:12 UTC and the approvals), otherwise matchday 8 (deadline 2026-10-30 18:30 UTC).
