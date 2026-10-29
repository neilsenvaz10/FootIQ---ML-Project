# AA-1 … AA-14 resolution matrix (proposed protocol r2 and hardened logger)

Source of the AA items: `official_readiness_audit_r1/01_AMENDMENT_A1_AUDIT.md`. "Logger" = `hardened/` modules; tests in `tests/test_hardened.py` (names abbreviated).

| AA | Required edit | Protocol r2 clause | Logger implementation | Test evidence |
|---|---|---|---|---|
| AA-1 | Bundesliga batches form a stage of the pre-registered sample; gates unchanged; clock and bootstrap clusters defined | **R2.1**, A.4, A.5, Part C; separate `07_BUNDESLIGA_OPERATIONAL_PILOT_PROTOCOL.md` | competition/season/source scope enforced (`predict_core(scope=…)`, `ScopeError`, approval scope check) | `test_wrong_league_or_season_snapshot_is_rejected`, approval scope cases |
| AA-2 | Newer OpenFootball snapshots enter via a hashed merged frame and are de-duplicated against S2 | **R2.3** | `merged_state(s1_additions=…)`: required columns, retrieval-time filter, agreement / conflict | `test_second_source_openfootball_agreement_and_conflict` |
| AA-3 | Ordering date: S1 date if present else S2 UTC date; 1-day difference logged, > 1 day conflict | **R2.4** | canonical record rule in `merged_state` (S1 row replaces S2 add; date conflict event) | same test; date conflict event |
| AA-4 | Incomplete-history events for any rejected played match; withdrawals/corrections quarantined | **R2.5, R2.6**, R2.8 | events + `blocked_clubs` / `competition_blocked`; reasons `incomplete_or_inconsistent_history`, `incomplete_history_competition_blocked` | withdrawn, corrected, duplicate, unclassified, unknown-team, missing-known-match, removed-fixture tests |
| AA-5 | Snapshot scope validation (league, season) and cut-off | **R2.2** | `load_snapshot` raises `ScopeError`; additions must be dated after 2026-09-20 | wrong league/season test |
| AA-6 | Label confirmation deadline and polling duty | **R2.7** | `reassess` label states pending/confirmed/conflict; checkpoint exclusion | `test_label_confirmation_correction_and_withdrawal` |
| AA-7 | Results snapshot = fresh kickoff snapshot; earliest kickoff rule only for S2 snapshots | **R2.9** | newest snapshot ≤ 24 h or all fixtures rejected `stale_kickoff_snapshot`; one payload supplies both | stale-snapshot test |
| AA-8 | A1.7 supersedes r1 condition (f) | **R2.10**, A.6(f) | deadline = UTC kickoff − 60 min; legacy rule no longer used | deadline tests (also from the v2 suite) |
| AA-9 | One evaluated seal per fixture and model | **R2.10** | ledger uniqueness key (fixture_id, model_key), idempotent skip | duplicate-sealing tests |
| AA-10 | Authoritative system clock; skew check; no caller timestamps | **R2.10** | `seal_official` has no time parameter; `engine._now()`; monotonic vs ledger; poll skew ≤ 120 s | signature test, clock-regression/skew tests |
| AA-11 | Reschedule staleness re-check; removal needs two snapshots; inferred statuses disclosed | **R2.11** | `reassess` rules | reschedule/postpone/identity/removal tests |
| AA-12 | Late-arriving history flagged, eligible, sensitivity analysis | **R2.12** | `late_arriving_history_result` flag | late-arriving history test |
| AA-13 | Missing result pending until the checkpoint | **R2.13** | `missing_result` flag; exclusion only with `analysis_checkpoint=True` | missing-result test |
| AA-14 | Provenance hashes for all prediction-time artefacts and code | **R2.14** | `artifacts.py` manifest (34 entries incl. v1 preprocessing, Elo parameters, feature code, contracts, adapters, logger code); manifest sha in each record; approval binds it | artifact tamper tests |

## The 14 topics requested for r2
| Topic | Clause |
|---|---|
| 1 Canonical records across agreeing sources | R2.3, R2.4 |
| 2 Newer OpenFootball snapshots | R2.3 |
| 3 Withdrawn and corrected results | R2.5 |
| 4 Rejected played matches | R2.6 |
| 5 Late-arriving results | R2.12 |
| 6 Rescheduled fixtures | R2.11 |
| 7 Missing results | R2.13 |
| 8 Duplicate sealing | R2.10, R2.15 |
| 9 Prediction timestamp requirements | R2.10 |
| 10 Kickoff snapshot freshness | R2.9 |
| 11 Regulation-time outcome labels | R2.7 |
| 12 Source-specific licensing and attribution | R2.2, R2.14 |
| 13 Competition-specific source scope | R2.1, R2.2 |
| 14 Preservation of the original statistical gates | Part A (A.1–A.6), R2.1 |

## Preserved scientific content (checked against r1)
Primary log loss; the three comparators and contrasts; secondary metrics and calibration method; cluster bootstrap (competition × month, 2,000, seed 20261021); 5,000 results / 25 competitions / 3 months; 10,000 second checkpoint; harm monitor; success criteria; r1 eligibility conditions (a)–(e), (g). The only substantive change to r1 text is condition (f), replaced by R2.10 (explicitly flagged).
