# Source-integrity report

## Rules enforced (state layer, `hardened/state.py`)
| Check | Behaviour |
|---|---|
| Snapshot hash | sha256 verified on load and again before each use |
| Scope | every record must be `bl1` / 2026; otherwise the whole snapshot is rejected (`ScopeError`) |
| Order | strictly increasing retrieval time; content monotone (`lastUpdateDateTime` may not decrease for a match) → `OutOfOrderError` |
| Retrieval-time filter | only snapshots retrieved at or before the prediction time are read; each added result carries its snapshot's retrieval time |
| Kickoff/results freshness | newest snapshot must be ≤ 24 h old or every fixture is rejected `stale_kickoff_snapshot` |
| Explicit regulation time | only `After90Minutes`; an unclassified final creates an incomplete-history event |
| Integrity events | `withdrawn_result`, `corrected_result`, `duplicate_ordered_pair`, `duplicate_matchID_in_snapshot`, `conflict_with_openfootball_score/date`, `played_match_unresolved_identity`, `played_match_no_explicit_90min_result`, `played_match_kickoff_not_before_retrieval`, `known_match_missing_in_source`, `fixture_removed_in_newest_snapshot`, `fixture_unresolved_identity`, `result_before_cutoff_missing_in_frozen_universe`, `conflict_between_sources_score/date`, `s1_result_before_cutoff` |
| Consequence | clubs involved → `incomplete_or_inconsistent_history` (not primary-eligible); unidentifiable club → `incomplete_history_competition_blocked` (whole competition) |
| Second source (OpenFootball updates) | `s1_additions` frame (required columns, retrieval-time filter, dated after the cutoff): agreement → one canonical S1 record `two_sources_agree`; any disagreement → conflict, pair quarantined |
| One history for all models | one merged universe, one `state_sha256` per batch; the v1 and v2 feature builders read the same frame |

## Results on the real Bundesliga snapshot (2026-10-21 14:12:31Z)
252 future fixtures, **0 integrity events**, 18 verified results added, 18 primary-eligible fixtures (matchdays 7–8), 234 ineligible only for competition freshness. Probabilities, eligibility and v2 feature hashes are identical to the sealed v2 shadow batch (max difference 0.0), so the hardening did not change predictions.

## Behaviour under attack (all unit-tested)
late-arriving results (excluded from earlier predictions) · conflicting snapshots and corrections · duplicates · withdrawals · rejected played matches · unknown team (competition-wide block) · removed fixtures · stale and out-of-order snapshots · wrong league/season · S1/S2 agreement and conflict.

## Remaining source-level limits
* The producer of the `s1_additions` frame (a newer OpenFootball snapshot converted to that format and hashed) is not built; the logger accepts and validates the frame, tested with synthetic frames only. Until then the pinned S1 universe is the only S1 input.
* OpenLigaDB has no explicit postponed/cancelled flag: these states are inferred from kickoff changes, disappearance from two consecutive snapshots, or a missing result.
* OpenLigaDB data are user-entered without editorial review; labels need two snapshots at least 24 h apart (or a second source).
