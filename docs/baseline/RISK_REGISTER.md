# Milestone 1 risk register

All findings are open/documented; M1 preserves evidence rather than repairing legacy models. No new source rights were verified online.

| ID | Severity | Category | Finding | Mitigation |
|---|---|---|---|---|
| R01 | High | Data availability | Raw results contain 49,368 rows but 72 have no scores; processed scored rows stop 2026-06-02. | Treat unscored rows as unavailable; no automatic historical refresh assumed. |
| R02 | High | Data availability | StatsBomb events/360 directories absent despite inherited inventory describing prior downloads. | Preserve summaries; full event reconstruction blocked until approved data access in later milestone. |
| R03 | High | Source licensing | Inherited license/provenance descriptions do not establish exact upstream revisions, training rights or redistribution rights. | Record unresolved source chain and permissions; no new data acquisition/publication in M1. |
| R04 | High | Temporal/target semantics | Historical results score labels are copied directly; raw schema does not independently identify 90-minute versus extra-time goals. | Verify historical score semantics before claiming pure 90-minute training labels; retain frozen model unchanged. |
| R05 | High | Training-serving parity | Historical matches_prior is length of deque(maxlen=20); live matches_prior uses total matches_played. | Flag mismatch; later candidate/adapter correction requires new version and evaluation, not silent baseline repair. |
| R06 | Medium | Temporal leakage | Dummy-column vocabulary is created from concatenated train/calibration/test frames. | Future preprocessing must fit train only; no future labels used by this encoding, but strict contract is unmet. |
| R07 | High | Temporal leakage | Date-only sorting and incomplete availability timestamps cannot prove what was known before every kickoff. | Separate archived replay from genuine forecast; conservative same-day and known-at checks later. |
| R08 | High | Evaluation selection | v2.8 cites model_v26_test_predictions.csv as calibration_source; v2.11 explicitly used 21 live fixtures diagnostically. | Treat gate performance as development evidence; require untouched future validation before new claims. |
| R09 | High | Club expansion | No systematically trained/evaluated club model or complete club-season feed exists; isolated club reports are not such a model. | Maintain separate model domain; defer all club implementation beyond M1. |
| R10 | High | Player data | 1,246 player impact rows are heuristic squad ratings; complete minutes/actions/per-90 cohort not verified. | Do not describe them as future-performance ML or validated similarity features. |
| R11 | Medium | Reproducibility | Existing venv lacks pip; external base Python runtime is referenced by the venv. | Version inventory recorded through importlib.metadata; clean-machine installation/offline wheels unverified. |
| R12 | Medium | Reproducibility | Default Windows encoding can misdecode team names; simulation succeeds with -X utf8. | Record encoding requirement; no legacy helper changes in baseline. |
| R13 | Medium | Model security | Pickle artifact executes trusted Python objects and depends on sklearn compatibility. | Use only local hashed trusted artifact; do not accept arbitrary model uploads. |
| R14 | High | Tournament rules | Group rank uses points, goal difference, goals scored then random.random; slot logic is a prototype, not full official rules certification. | Preserve deterministic prototype; validate season-specific rules before new competition simulation. |
| R15 | Medium | Update operations | Manual API scripts/cache budget exist but no scheduler/reconciliation warehouse; account entitlements unverified. | No live calls in M1; later quotas/source access gate required. |
| R16 | High | Claims | 59/82 validation mixes group 90-minute reads and knockout advancement; small/selective samples do not prove future accuracy. | Keep targets and denominators separate; no independent match-results verification claimed. |
| R17 | Medium | Destructive execution | Legacy main routines overwrite output tables; simulator also writes model_v23_market_priors.csv. | Execute only copied snapshots; compare original before/after hashes. |
| R18 | Medium | Feature mismatch | Foundation is_competitive marks any non-friendly as competitive; live tournament_flags recognizes a narrower keyword list. | Audit context mapping for future adapter; retain current outputs unchanged. |
| R19 | Medium | Testing scope | 28 tests focus on later gate/lineup/matchday/result-locking helpers; no complete raw rebuild, retraining, live-provider or platform test coverage. | Baseline execution supplements tests but does not certify future architecture. |
| R20 | Medium | Storage/retention | Local snapshot and three isolated copies include inherited third-party data and duplicate bytes. | Retain locally per requested no-deletion rule; do not publish this bundle without separate rights/owner review. |
