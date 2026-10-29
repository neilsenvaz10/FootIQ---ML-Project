# Archived research and deferred future work

Nothing here was deleted or moved. These folders hold the larger FootIQ research programme that is **outside the active 15-mark mini-project scope**
(see [../mini-project/MINI_PROJECT_PLAN.md](../mini-project/MINI_PROJECT_PLAN.md)). They stay on disk because the frozen model pickles and some scripts depend on their paths
(for example the v2 pickles load only with `FootIQ_Club_Model_Development_v2/_scripts` on `sys.path`).

| Topic | Location | Status |
|---|---|---|
| Official prospective evaluation, protocol r2, amendment approval | `FootIQ_Club_Model_Development_v2/10_PROSPECTIVE_EVALUATION_PLAN.md`, `final_refit_v2_r1/08_*`, `official_readiness_audit_r1/`, `hardened_logger_r2_draft/` | Archived, not run |
| Immutable prediction ledgers, shadow logs | `matched_v1_prospective_r1/`, `shadow_integration_r1/`, `final_refit_v2_r1/prospective_log/` | Archived (dry-run data only) |
| Live polling, schedulers, provider clients, daily match-day pipelines | `scripts/api_football_client_v24.py`, `build_live_data_v25.py`, `run_*_window_*.py`, `outputs/daily_*`, `outputs/matchday_*` | Archived, not used by the app |
| Multi-source reconciliation, adapters, freshness validation | `FootIQ_Club_Model_Development_v2/source_adapters_r1/`, `freshness_validation_r1/`, `fresh_results_source_research/`, `bundesliga_source_promotion_r1/`, `matched_v1_prospective_r1/ingestion/` | Archived |
| Player performance prediction and clustering | `FootIQ_ML_Data_Verification/player_form_v1/`, `scripts/build_player_impact_v21.py` | Future work (never implemented as a validated model) |
| PostgreSQL / Airflow / Docker / React platform blueprint | `PROJECT.md` | Superseded; kept as the full-vision document |
| Lineup-adjusted predictions, odds, weather, injuries | `scripts/build_lineup_impact_v212.py`, `data/contracts/` | Future work |
| 100+ other competitions (lower leagues, cups, MLS, ...) | `FootIQ_Dataset_Submission/`, other rows of `FootIQ_ML_Data_Readiness/04*_*.csv` | On disk, not surfaced |
| Dedicated models for UEFA club competitions | none | Future work; needs continental-aware ratings |
