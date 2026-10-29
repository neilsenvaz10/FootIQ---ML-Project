# 07 Integration and validation test plan

## A. Validating a new provider against openfootball (before any use)
| # | Test | Method | Pass rule |
|---|---|---|---|
| 1 | Exact score agreement | all completed league results of 2025-26 and 2026-27 that both sources hold, keyed by resolved (competition, season, home, away, ordinal) | >= 99.5% identical on overlap and **100% for 2026-27**; every difference listed individually and adjudicated by a human; none resolved by majority or by choosing a source |
| 2 | Competition/season matching | provider league id/page -> frozen competition_id and corrected season label | 100% of in-scope pages mapped; unmapped = not used |
| 3 | Identity matching | resolution ladder (report 06) | >= 99% auto-resolved, rest reviewed, 0 ambiguities |
| 4 | Kickoff normalisation | provider UTC / local time vs openfootball date | date agreement 100% where both exist (observed so far: OpenLigaDB 36/36); matrix-derived dates compared with OpenLigaDB for the Bundesliga as a calibration of the schedule-derived method |
| 5 | Coverage | results vs expected played fixtures (schedule dates before the run date) per in-season competition | >= 98% else the competition is "single-source / limited"; the missing ones listed |
| 6 | Missing-result detection | fixtures past date with no result in any source | reported, keeps `club_has_unresolved_past_fixture` flag |
| 7 | Historical availability | for 3 past seasons per competition, does the provider still expose results (Wikipedia revisions of season pages; OpenLigaDB seasons) | needed only for replay tests and alias building |
| 8 | Status handling | postponed/abandoned/awarded in the sources | classified, never counted as results |
| 9 | Replay | truncate the frozen universe at a past date, re-ingest later results through the new adapter (as done for openfootball: 427/427) | identical features and identical v2/matched-v1/v1 probabilities for later fixtures |
| 10 | Conflict handling | feed a clearly marked **test copy** of one record with a changed score (test input, never data) | conflict file populated, record quarantined, no merged output change |
| 11 | Provenance | every merged row has source list, snapshot id, revision, retrieval time, licence tag | 100% |
| 12 | Wikipedia edit stability | compare latest vs previous revision of each page | changed result -> flag; use only revisions >= 24 h old |
| 13 | Logger dry run on the merged snapshot | `e5`-style dry run | primary-eligible share >= 90% for competitions that passed 1-6 (benchmark: 97.8% simulated) |
| 14 | Frozen artefacts | hash check before/after | unchanged |

## B. Logger/protocol changes needed (not implemented; the official logger is not to be modified or run yet)
1. **Input snapshot:** the logger takes a *merged* results universe plus fixtures list and an unresolved-past-fixture list from the reconciler (same file formats as today), so `e4_prospective_logger.py` needs small changes only: accept a merged-snapshot id, record `result_sources` and `agreement_level` per fixture's clubs, compute staleness from the merged universe.
2. **Eligibility:** add per-competition source status (admitted / single-source / not admitted). Fixtures in non-admitted competitions are logged but not primary-eligible.
3. **Outcome confirmation (protocol amendment, owner approval, before the first official batch):** replace "same score in two successive openfootball snapshots >= 24 h apart" with "either two approved sources agree, or one source shows the same score in two revisions/snapshots >= 24 h apart, the first >= 48 h after the match, with no disagreeing source".
4. **Attribution/licence:** Wikipedia-derived rows carry "Match data adapted from English Wikipedia (CC BY-SA 4.0)", revid and retrieval date; OpenLigaDB rows carry ODbL attribution once the terms are confirmed.
5. **Pre-registration:** the stale threshold (14 days), 60-minute lead rule, metrics and gates stay as registered; the source list and confirmation rule are the only amendments, and the protocol hash is recomputed before approval.
6. **Frozen items:** v2-r1 (`55c1e4c5...`), matched v1 (`33bd80f6...`), original v1 (`067426e8...`), preprocessing, training snapshots and the evaluation protocol (apart from item 3 and 5) are untouched. Fresh results update pre-match features and later verification only; no retraining, tuning or calibration.

## C. Acceptance for starting official logging (still needs your explicit approval)
Tests A1-A14 pass for at least the admitted competitions, the amendment (B3, B5) is approved, the dry-run eligible count is > 0, and you create the approval file.
