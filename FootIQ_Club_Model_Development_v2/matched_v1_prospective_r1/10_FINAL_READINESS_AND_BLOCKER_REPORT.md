# 10 Final readiness and blocker report

Date: 2026-10-21. Branch `feat/club-ml-v2`. Nothing staged, committed, pushed or merged; no deployment; v1, the frozen v2-r1 candidate and the World Cup model unmodified (hash-verified); no database or dependency changes; no recurring job started.

## What is done
| Item | Status |
|---|---|
| Frozen v2 hash `55c1e4c5...3e56c` and associated artifacts verified | ✔ (report 01) |
| Identity defects audited, proposals written, collision fixtures made ineligible | ✔ (report 02) — corrections themselves **not applied** |
| Matched v1 refit (same 116,854 rows, cutoff 2026-09-20, original v1 recipe) frozen as a separate read-only artifact `33bd80f6...ec34` | ✔ (reports 03, 04 artifacts) |
| Training-data equivalence | ✔ identical ids, targets, cutoff, eligibility, class definition (report 05) |
| Ingestion workflow (plan / fetch / parse / selftest), provenance and conflict policy | ✔ built; parse path validated by the self-test (reports 06, 07); `fetch` implemented but **not executed** |
| Logger for original v1, matched v1, frozen v2 with backdating guards, immutability, gating | ✔ 13/13 tests (report 08) |
| Pre-registered evaluation protocol and hash | ✔ (report 09, `PREREGISTRATION_r1.json`) |
| Any evaluation of prospective outcomes | not started, by design |

## Is the system ready to begin genuine pre-match prediction logging?
**The tooling is ready; genuine, evaluable logging cannot start yet. Blockers:**
1. **No fresh results exist upstream.** The read-only `plan` check shows every approved openfootball repository still at the commit used for training; the newest result anywhere is dated 2026-09-20 and 2026-27 fixtures are already scheduled. Consequence in the dry run: **0 of 416 upcoming fixtures are primary-eligible** (stale competition results, clubs with unresolved past-dated fixtures). Until the source publishes newer results (or you approve another source), the primary population stays empty. When it does: `plan` -> `fetch --confirm-download` (needs your explicit go-ahead; it downloads nine repositories) -> `parse` -> official batch.
2. **Owner approval is required to start official logging:** `OFFICIAL_LOGGING_APPROVED.json` (with the three model hashes) must be created by you; the logger refuses without it. Dry runs never count.
3. **Kickoff timing is coarse.** ~82% of fixtures have no kickoff time and no time zone, so the logger conservatively requires batches to be sealed before match date 00:00 UTC minus 14 h minus 60 min (i.e. at least ~15 h before the calendar day in UTC). Predictions for tomorrow's matches would be rejected.

## Unresolved issues (not blockers for the tooling)
* Identity collisions (257 training rows) and zw1 2021-22 dates (259 rows) remain in the frozen training data; correcting them needs a dataset v1.2 plus new model versions (v2-r2 and a new matched v1) and a new evaluation. Until then affected fixtures are excluded/flagged.
* `fetch` and the parse of a genuinely newer snapshot are untested end to end.
* Immutability is local (read-only files plus hash chain); external anchoring of `CHAIN.jsonl` would need a commit/tag that you have not allowed.
* The earlier development tables still predate the Elo bug fix (see the previous report).
* Evaluation power: the minimum design needs 5,000 eligible, outcome-confirmed fixtures from 25+ competitions over 3+ months; with sparse upstream updates this may take longer than planned.

## Decisions requested from you
1. Allow the one-off `fetch` of newer openfootball snapshots when `plan` shows upstream has moved (or tell me to run `plan` again later)?
2. Approve a dataset v1.2 with the identity/date corrections (leads to v2-r2 + new matched v1, restarting the evaluation clock)?
3. When ready, create `OFFICIAL_LOGGING_APPROVED.json` to start official logging.
