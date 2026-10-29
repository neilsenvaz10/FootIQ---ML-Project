# Score-validation safeguard for football-data.org results: proposal (Phase 4.13B)

Status: **documentation only.** The adapter (`app/store/footballdata.py`) and all production code are unchanged. Nothing was requested from the provider, imported or activated.

## 1. The question
`score.regularTime` was never present in the 232 finished matches seen on 2026-10-27. The adapter therefore reads `score.fullTime` as the 90-minute score when `duration` is REGULAR and flags every such result `fulltime_taken_as_regular_time_unconfirmed`. The provider's documentation describes `fullTime` as the running score and, at FINISHED, the final score, without stating the rule for extra time and penalties explicitly. For league matches (no extra time) the two coincide. What protects against a wrong or odd value today, and what would add protection?

## 2. What the current code already refuses (tested in `tests/test_footballdata_sync.py`)
- status other than FINISHED never yields a result; AWARDED, finished-without-usable-score, `duration` EXTRA_TIME or PENALTY_SHOOTOUT without an explicit `regularTime` are quarantined for a human, never scored;
- a score that is null, a string, a boolean or negative is not a score;
- a score that differs from a stored verified result is quarantined as CONFLICT and never overwrites;
- a differing date holds the whole record, result included (DATE_DIFFERENCE).

## 3. Evidence from the saved responses (all 232 finished matches: PL 80, SA 80, FL1 72)
| Check | Result |
|---|---|
| `duration` | REGULAR in 232 of 232 |
| score nodes present | `duration`, `fullTime`, `halfTime`, `winner` in 232 of 232; no `regularTime`, `extraTime`, `penalties` |
| `winner` consistent with `fullTime` | 232 of 232 |
| `halfTime` not above `fullTime` (both teams) | 232 of 232 |
| stage | REGULAR_SEASON in 232 of 232 |
| largest total goals | 8 |
| agreement with independently stored 90-minute results | 155 of 155 overlapping matches |

## 4. Proposed safeguard (not implemented): three internal-consistency checks before a result may be scored
Applied in `regular_score` / `parse_match`, only when the answer has no `regularTime`:
1. `score.winner` must agree with `fullTime` (HOME_TEAM if home > away, AWAY_TEAM if home < away, DRAW if equal). A contradiction means a corrupted or misread record.
2. `halfTime`, where both values are present, must not exceed `fullTime` for either team (a half-time score cannot be bigger than the final one).
3. The match must be in a league phase: `stage` REGULAR_SEASON (or absent for a domestic league) and no `extraTime` or `penalties` node. Any such node means `fullTime` may include extra-time or shoot-out goals, so the result is quarantined, not scored.

Outcome of a failed check: the record becomes `completed_unclassified_score` with a flag (`score_winner_mismatch`, `halftime_exceeds_fulltime`, `knockout_score_fields`), which the existing ingest quarantines as "completed without an explicit 90-minute result". It is never imported and never overwrites anything. The flag `fulltime_taken_as_regular_time_unconfirmed` stays on passing results until the provider confirms the semantics in writing.

Optional (needs your decision): a sanity ceiling, for example total goals above 12 goes to quarantine. Not recommended as a rule (it would reject a legitimate extreme result); alternatively report such a score in the dry-run summary only.

## 5. Tests to write when approved (all offline, mock payloads)
- winner contradicting `fullTime` is quarantined; the same data with a consistent `winner` is scored;
- `halfTime` above `fullTime` is quarantined; a null `halfTime` does not block a result that passes the other checks;
- a payload with `extraTime` or `penalties` nodes, or a non-league `stage`, is quarantined even with `duration` REGULAR;
- the 232 real finished matches (from the saved snapshots) all pass, so the safeguard changes nothing there;
- a present `regularTime` still takes precedence, and the three checks apply to it only for `winner` consistency when `fullTime` is present;
- existing 24 adapter tests stay green; Bundesliga and La Liga code paths are not touched.

## 6. Cost and risk
About 25 lines in the football-data.org adapter and about 6 tests; no schema change, no change to other providers. The safeguard can only turn a result into a quarantined finding; it cannot create or change data. A false rejection would show as a visible finding and delay one result.

## 7. Decision needed from you
Approve the three checks (and say whether to add the goals-ceiling report), after which the change is made together with the other pre-activation work. Until then the current behaviour, listed in section 2, stays in force.
