# Bundesliga operational-pilot protocol (Stage 1 of proposed protocol r2) — DRAFT

Part of the proposed r2 (R2.1). Not active. The pilot tests the *operation* of prospective prediction (sourcing, sealing, reconciliation); it is **not** the scientific model comparison.

## Scope
Competition `deutschland:1-bundesliga`, season 2026-27, OpenLigaDB `bl1`/2026 (S2) with the pinned OpenFootball universe (S1). The first target is matchday 8 (earliest sealing deadline 2026-10-30 18:30 UTC), subject to all approvals; nothing is sealed before they exist.

## What the pilot does
Seal predictions of the three registered models (original v1, matched v1, frozen v2; v1 Elo descriptive) for eligible fixtures, reassess fixtures after every manual poll, confirm labels, and keep the ledger intact. Its sealed predictions and confirmed outcomes **count toward the pre-registered sample** (R2.1) and are analysed only when the scientific gates (≥ 5,000 eligible, ≥ 25 competitions, ≥ 3 months) are met.

## Permitted outputs (operational metrics only)
* Counts and rates: fixtures sealed / rejected (by reason), primary-eligible share, ineligibility reasons.
* Timeliness: minutes between sealing and deadline; snapshot age at sealing; clock-skew at poll.
* Data quality: integrity events (withdrawals, corrections, duplicates, rejected played matches, late-arriving results), conflicts and adjudications, rescheduled/postponed/removed fixtures.
* Label pipeline: confirmation rate and delay, unconfirmed counts.
* Ledger health: batches, anchors, recoveries, verification results.
* Integrity of probabilities (non-negative, sum to one) — no outcome involved.

## Prohibited outputs (no inferential model-comparison conclusions)
No paired score differences between models, no confidence intervals or p-values, no rankings, no statements that a model is better or worse, no calibration or accuracy tables by model, no early-stopping or promotion arguments. Outcomes are recorded and labels confirmed, but outcome-based scores are not computed in Stage 1 reports. A Bundesliga-only bootstrap (cluster = matchday) may be used **only** for operational rates, never for model comparison.

## Transition to Stage 2
Stage 2 starts only through an approved amendment that admits additional competitions with validated sources (≥ 99.5% exact agreement on overlap, 0 unexplained conflicts, 0 identity ambiguities, explicit result types). The 25-competition gate and all other scientific gates are unchanged.

## Pilot stop conditions
Stop sealing and report to the owner when: a ledger verification fails; an artifact-manifest mismatch occurs; the source terms change; a snapshot cannot be obtained within the freshness window repeatedly; or an unadjudicated conflict affects more than 20% of a matchday's fixtures.
