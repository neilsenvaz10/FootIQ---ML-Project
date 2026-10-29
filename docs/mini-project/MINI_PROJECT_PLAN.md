# FootIQ — 15-Mark Mini-Project: Simplified Scope and Plan

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

Status (Phase 4.28, 2026-10-28): the project is complete and in its final state with six competitions; see `docs/mini-project/final/FINAL_SYSTEM_GUIDE.md` and the phase reports in `docs/mini-project/phase4/`. The plan below is kept as history.

Original status: **APPROVED 2026-10-22 (FastAPI + simple HTML page, not Streamlit). Implemented in `app/`; see `app/README.md`. Nothing staged or committed.**
Prepared: 2026-10-22, branch `feat/club-ml-v2`. Based on inspection of the repository; numbers below were read from existing files or recomputed from existing CSVs (no model was retrained, no data was downloaded).

---

## 1. Updated mini-project scope document

**Title.** FootIQ — a football analytics dashboard with match-outcome prediction and World Cup simulation.

**Competitions (fixed, no expansion).**

| # | Group | Competitions |
|---|---|---|
| 1-5 | Domestic leagues | English Premier League, La Liga, Bundesliga, Serie A, Ligue 1 |
| 6 | Continental club | UEFA Champions League |
| ~~7-11~~ | *removed from the active scope in Phase 4.18 (data preserved)* | ~~FIFA World Cup, UEFA Europa League, UEFA Conference League, UEFA Nations League, Copa América~~ |

**Four modules.**
1. **Data**: ingest, clean and store historical match CSVs for the six supported competitions (the five removed ones stay in the data, outside the application), with source attribution.
2. **Dashboard**: standings, results, form, goals, home/draw/away rates, head-to-head, Elo trend.
3. **Prediction**: 1X2 probabilities from the **existing** trained models; each competition shows a *validation status badge*.
4. **World Cup simulation**: the existing simulator, run from a button/CLI, showing group and title probabilities.

**Honesty rules (apply everywhere in the UI and report).**
- No new model is trained per competition. No retraining at all is required.
- Every prediction page shows one of: `Validated`, `Partially validated`, `Not validated (indicative only)`.
- Historical metrics are quoted from the existing reports and labelled as *previously inspected* (see §4). They are not presented as new independent evidence.
- Missing data is shown as missing. Nothing is imputed or invented for display.

**Out of active scope** (archived, not deleted): see §9.

---

## 2. Simplified architecture

```
 raw CSVs (already in repo, CC0 / CC BY-SA)         existing frozen models
 data/raw/international_results/results.csv         FootIQ_Club_Model_Baseline_v1/artifacts/
 FootIQ_ML_Data_Readiness/04d_*.csv                 FootIQ_Club_Model_Development_v2/final_refit_v2_r1/artifacts/
            |                                       data/model_artifacts/v27/
            v                                                  |
  [1] prepare_data.py  -->  data/miniproject/matches.csv       |
      (filter 11 competitions, one schema,                     |
       source + licence columns, no imputation)                |
            |                                                  |
            +------------> [2] analytics.py (pandas) <---------+
            |              [3] predict.py  (loads pickles, builds features)
            |              [4] worldcup_sim.py (thin wrapper over scripts/simulate_live_tournament_v213.py)
            v
        [5] Streamlit app (5 pages)  — reads CSV + calls [2][3][4] in-process
```

Design choices, with reasons:
- **CSV, not a database.** `docs/architecture/CURRENT_STATE.md` confirms the PostgreSQL/Airflow/Docker platform was never built; the whole existing system is file-based and works. CSV is the least work. (If a SQL demonstration is wanted for the report, a 20-line script can load the same CSV into SQLite. Optional.)
- **No scheduler, no live polling.** Refresh = re-run `prepare_data.py` after manually dropping in an updated CSV.
- **No API layer** unless you want one (see §5, decision A).

---

## 3. Dataset coverage audit (11 competitions)

Counts recomputed from `FootIQ_ML_Data_Readiness/04d_COMBINED_CLUB_MATCHES_v1.0.csv` and `data/raw/international_results/results.csv`. Extraction date of the club snapshot: 2026-10-20.

| # | Competition | Dataset in repo | Seasons / span | Rows | Latest result | Source / licence | Gaps and caveats | Rating |
|---|---|---|---|---:|---|---|---|---|
| 1 | Premier League | 04d `england:1-premierleague` | 2018-19 → 2026-27 (partial) | 3,090 | 2026-09-20 | openfootball, CC0-1.0 | 8 full seasons × 380 + 50 of 380 for 2026-27 (in progress). 90-min labels all confirmed. | **Good** |
| 2 | La Liga | `espana:1-liga` | 2018-19 → 2026-27 | 3,109 | 2026-09-20 | openfootball, CC0-1.0 | 8 full seasons + 69 matches of 2026-27. | **Good** |
| 3 | Bundesliga | `deutschland:1-bundesliga` | 2018-19 → 2026-27 | 2,484 | 2026-09-20 | openfootball, CC0-1.0 | 8 × 306 + 36. One awarded match with unknown 90-min label. | **Good** |
| 4 | Serie A | `italy:1-seriea` | 2018-19 → 2026-27 | 3,090 | 2026-09-20 | openfootball, CC0-1.0 | 8 × 380 + 50. One awarded match, unknown label. | **Good** |
| 5 | Ligue 1 | `europe/france:fr1` | 2018-19 → 2026-27 | 2,762 | 2026-09-20 | openfootball, CC0-1.0 | **2019-20 has 279/380** (consistent with the season being curtailed in 2020); 2023-24 onward has 306 matches per season (18 teams). One awarded match. | **Good, one known gap** |
| 6 | FIFA World Cup | `results.csv` tournament = `FIFA World Cup` | 1930 → 2026 | 1,036 rows (964 scored) | 2022-12-18 in raw file | martj42 dataset, CC0 (per `docs/data-sources/SOURCE_EVALUATION.md`) | **Correction after implementation:** the 2026 rows in `results.csv` are fixtures without scores. 2026 results come from the repo's verified files (`matchday_validation_v210.csv`, `worldcup_2026_knockout_results_verified.csv`), giving 130 more rows to 2026-07-18 (final not included). Recorded scores include extra time, not 90 min (risk R04). | **Good** |
| 7 | Champions League | `champions-league:cl` | 2018-19 → 2026-27 | 1,140 | 2026-09-10 | openfootball (CC0) + Wikipedia (CC BY-SA 4.0 — needs attribution) | 865 confirmed / 275 inferred 90-min labels. Qualifying rounds are separate ids (`clq`) and not in this count. Coverage 100% vs expected. | **Good for results; labels partly inferred** |
| 8 | Europa League | `champions-league:el` | 2018-19 → 2026-27 | 1,424 | 2026-09-17 | same | 2021-22 is 139/141. 1,101 confirmed / 322 inferred / 1 unknown labels. | **Good (98.6%+)** |
| 9 | Conference League | `champions-league:conf` | 2021-22 → 2025-26 (competition began 2021) | 729 | 2026-05-27 | same | **No 2026-27 rows yet** (season just started). 195 inferred / 3 unknown labels. | **Good, complete since inception** |
| 10 | Nations League | `results.csv` tournament = `UEFA Nations League` | 2018-09 → 2025-06 | 658 | 2025-06-08 | martj42, CC0 | **Nothing after the 2025 finals** in the raw file, so the 2026-27 edition is missing from the base dataset. A 2026 matchday-1 prediction file exists (`data/processed/nations_league_2026_matchday_1_*`) but is not result data. | **Good through 2025; 2026-27 gap** |
| 11 | Copa América | `results.csv` tournament = `Copa América` | 1916 → 2024 | 869 | 2024-07-14 | martj42, CC0 | Complete through 2024 edition (next edition is 2028). No gap. Pre-1990 rows add little for modelling. | **Good** |

Files to treat as the **primary** inputs: `FootIQ_ML_Data_Readiness/04d_COMBINED_CLUB_MATCHES_v1.0.csv` (clubs), `data/raw/international_results/results.csv` + `shootouts.csv` + `former_names.csv` (internationals), `data/processed/team_elo_latest.csv` and `data/processed/international_matches.csv` (international features), `FootIQ_ML_Data_Readiness/05_CANONICAL_TEAM_IDENTITY_MAPPING.csv` (club names).

**What this audit means.** All 11 competitions already have clean historical CSVs. **No new downloading is needed to demo.** Two optional refreshes would close the visible gaps: the 2026-27 Nations League results, and newer results after 2026-09-20. Both are manual CSV drops.

**Audit caveat for the report.** The one thing I did *not* do is independently verify individual results against an external site; the repository's own validation scripts and coverage matrix are the evidence.

---

## 4. Reusable ML model inventory

Three models exist. None needs retraining. None is trained per competition.

| Model | Location | What it is | Evidence available | Use in mini-project |
|---|---|---|---|---|
| **Club v1** | `FootIQ_Club_Model_Baseline_v1/artifacts/multinomial_logreg.pkl` (+ `preprocessing_train_fitted.json`, `FROZEN.json`) | Multinomial logistic regression, 25 features (Elo + form + rest + context), domestic-league 90-min 1X2 | Locked test set and forward holdout, **executed once** (`EVALUATION_LOCK.json`). Pooled test log loss 1.0073 vs 1.0759 for always-home. | **Primary club predictor** for the 5 leagues |
| **Club v2-r1 (frozen)** | `FootIQ_Club_Model_Development_v2/final_refit_v2_r1/artifacts/club_v2_lr_final_candidate.pkl` (+ `feature_contract_v2_final.json`, `FROZEN.json`) | Multinomial LR, 62 features, C=0.01, refit through 2026-09-20 | Development evidence only: 3 chronological folds, log loss 1.0163 vs 1.0189 for v1 LR (−0.0030, CI −0.0044…−0.0016). **No unbiased evaluation**; refit consumed the earlier test/holdout. | **Optional "v2 candidate" toggle**, always labelled "development-validated only". Show v1 and v2 side by side. |
| **International v2.7 ensemble** | `data/model_artifacts/v27/live_match_model.pkl`; code `scripts/build_live_predictions_v27.py`, `model_bakeoff_v26.py` | 50% gradient boosting + 30% Elo + 20% logistic, with temperature calibration and a "Pass" gate | v2.6 bake-off, chronological: train 2000-2018, calibrate 2019-22, test 2023-26 (3,491 matches). Ensemble log loss 0.8565, accuracy 60.9%. Pooled across all internationals incl. friendlies, **not per competition**. | Predictor for Nations League, Copa América, World Cup single matches |
| **World Cup simulator (v2.3 team-power + v2.13 result locking)** | `scripts/simulate_live_tournament_v213.py`, `build_worldcup_model_v23.py`, `build_worldcup_model_v2.py` | Goal-based team-power Monte Carlo, 50,000 sims, locks completed results | `data/processed/worldcup_full_validation_summary_2026-07-19.csv`: group best-read 34/52 (65.4%), knockout advancement 25/30 (83.3%); Euro 2024 backtest in `outputs/euro_nations_model_v23_test_report.md` | World Cup simulation page. Note: this is *not* the v2.7 ensemble (stated in `CURRENT_STATE.md`); say so in the report. |

**Per-competition validation status (what the UI badge will say).**

| Competition | Model used | Badge | Basis |
|---|---|---|---|
| Premier League, La Liga, Bundesliga, Serie A, Ligue 1 | Club v1 (v2-r1 optional) | **Validated** (test + forward holdout, previously inspected) | Per-league rows in `FootIQ_Club_Model_Baseline_v1/06a_LEAGUE_WISE_METRICS.csv`. Test log loss (v1 LR): PL 0.990, La Liga 0.978, Bundesliga 1.018, Serie A 0.974, Ligue 1 0.967, all better than always-home (1.05-1.09). Forward holdout: PL 1.044, La Liga 0.976, Bundesliga 0.964, Serie A 0.991, Ligue 1 1.006. PL and Ligue 1 holdout are slightly *worse* than their test; report that. |
| World Cup | International v2.7 for single matches; v2.3 simulator for tournament | **Validated (tournament-specific)** | Full 2026 tournament validation file above |
| Nations League, Copa América | International v2.7 | **Partially validated** | Model validated on pooled internationals 2023-26 and on the 2025 UNL finals bracket (4 teams); no competition-specific accuracy figure exists |
| Champions League, Europa League, Conference League | Club v1/v2 features (Elo is within-league) | **Not validated (indicative only)** | v1 was evaluated on domestic leagues only; v2 reports no continental-competition metric (checked `08_LEAGUE_GROUP_PERFORMANCE.csv`); repo notes cross-league Elo "islands" make clubs from different countries not comparable; labels partly inferred. |

**Rule for the report:** v1 test and forward-holdout numbers were examined during development, and v2-r1 was refit on them. They are quoted as "historical evaluation results," not as new independent evidence.

---

## 5. Minimal backend and frontend plan

**Recommended: one Python app (Streamlit).** Backend and frontend are the same process; no REST API, no React, no Docker. This is the least work and is easy to demo. It adds one dependency (`streamlit`) to `requirements-share.txt`; the current `.venv` has pandas/numpy/scikit-learn only.

*Decision A (yours):* Streamlit, or FastAPI + a plain HTML/JS page if your course requires a "backend + frontend" split. FastAPI would add roughly 1-2 days.

**New code (all under a new `app/` folder; existing scripts untouched):**

| File | Purpose | Size |
|---|---|---|
| `app/prepare_data.py` | Read the two source CSV sets, filter 11 competitions, write one `data/miniproject/matches.csv` with columns `competition, season, date, home, away, hg, ag, outcome_90, source, licence`; write a `data_audit.csv`. No imputation. | ~150 lines |
| `app/analytics.py` | Standings, form table, goals/H-D-A rates, head-to-head, Elo series | ~150 lines |
| `app/predict.py` | Build pre-match features from history (reuse `_scripts/v2_features.py` and the club v1 feature code; reuse the v2.7 loader) and return H/D/A probabilities + status badge | ~200 lines, **the only risky piece** (feature parity; see roadmap) |
| `app/worldcup_sim.py` | Call the existing v2.13 simulation function, return group/title tables | ~60 lines |
| `app/app.py` | 5 Streamlit pages | ~250 lines |

**Pages.**
1. **Overview** — the 11 competitions, row counts, latest date, data source and licence (the audit table).
2. **Competition dashboard** — pick competition and season: table, results, goals, H/D/A bar, top form.
3. **Team / head-to-head** — form, Elo trend, last meetings.
4. **Predict a match** — pick competition + two teams + date; show probabilities, validation badge, model used, and the caution text for unvalidated competitions.
5. **World Cup simulator** — group tables, title odds, button to re-run with N simulations.

**Tests.** Reuse the 28 existing pytest tests (already passing per `CURRENT_STATE.md`); add ~5: schema of `matches.csv`, no duplicate matches, probabilities sum to 1, badge returned for each of the 11 competitions, v1 prediction equals the frozen-evaluation prediction for one known fixture.

---

## 6. Simple demonstration workflow (8-10 minutes)

1. `python app/prepare_data.py` → shows the audit table (11 rows, sources, licences). *(Module 1)*
2. Open the app → Overview page. *(Module 1)*
3. Dashboard: Premier League 2025-26 table, goals, H/D/A. Switch to Champions League. *(Module 2)*
4. Predict: Arsenal vs Chelsea → probabilities + "Validated" badge with the PL test log loss. *(Module 3)*
5. Predict: a Champions League fixture → same, but badge says **Not validated — indicative only**. *(Shows the honesty rule.)*
6. Predict: a Copa América / Nations League fixture → "Partially validated".
7. World Cup page → run simulation, show title odds. *(Module 4)*
8. Close with the validation slide: model, evidence, limitations.

---

## 7. Short implementation roadmap (about 7-9 working days)

| Step | Work | Output | Days |
|---|---|---|---|
| 0 | Approval of this plan; tag legacy material as archived (move/label only, no deletion) | `docs/archive/README.md` index | 0.5 |
| 1 | `prepare_data.py` + data audit + schema tests | `matches.csv`, `data_audit.csv` | 1.5 |
| 2 | `analytics.py` + dashboard pages | pages 1-3 | 1.5 |
| 3 | `predict.py`: load v1, reproduce one frozen prediction, add status badges; then v2-r1 toggle; then v2.7 for internationals | page 4, parity test | 2.5 |
| 4 | `worldcup_sim.py` wrapper (note: simulator needed `python -X utf8` on Windows) | page 5 | 0.5 |
| 5 | Report and slides from existing reports; README with run steps | report, README | 1.5 |

**Main risk:** `predict.py`. The club pickles expect specific engineered features, and the repo already documents a feature-parity requirement. Mitigation: step 3's parity test against stored frozen predictions before any UI work depends on it. If v2-r1 parity proves expensive, ship v1 only and keep v2-r1 as a documented extra.

---

## 8. Existing components that can be reused

- **Data:** `FootIQ_ML_Data_Readiness/04d_COMBINED_CLUB_MATCHES_v1.0.csv`, `05_CANONICAL_TEAM_IDENTITY_MAPPING.csv`, `01_COMPETITION_SEASON_COVERAGE_MATRIX.csv` (ready-made audit input); `data/raw/international_results/*`; `data/processed/international_matches.csv`, `team_elo_latest.csv`, `team_elo_match_history.csv`, `team_recent_form_latest.csv`, `worldcup_2026_matches.csv`, `worldcup_2026_teams.csv`.
- **Club models:** v1 pickle and preprocessing JSON; v2-r1 pickle and `feature_contract_v2_final.json`; feature code in `FootIQ_Club_Model_Development_v2/_scripts/v2_features.py`, `v2_common.py`.
- **International models:** `data/model_artifacts/v27/live_match_model.pkl`; `scripts/build_live_predictions_v27.py`, `build_confidence_gate_v28.py`, `build_foundation_tables.py`.
- **Simulation:** `scripts/simulate_live_tournament_v213.py` and its `build_worldcup_model_v2/v23` dependencies.
- **Validation material for the report:** `FootIQ_Club_Model_Baseline_v1/` reports 01-08 and CSVs; `FootIQ_Club_Model_Development_v2/12_FINAL_V2_DEVELOPMENT_REPORT.md`; `outputs/model_v26_bakeoff_report.md`; `outputs/worldcup_full_validation_report_2026-07-19.md`; `outputs/euro_nations_model_v23_test_report.md`; project PDFs in the repo root.
- **Provenance:** `docs/data-sources/SOURCE_EVALUATION.md`, `World_Cup_Prediction_Model_Sources_and_Provenance.pdf`.
- **Tests:** `tests/` (28 passing), `requirements-share.txt` (pinned env).
- **Docs worth keeping as-is:** `docs/architecture/CURRENT_STATE.md`, `docs/baseline/*` (baseline audit, risk register).

---

## 9. Deferred to future work / archived (preserved, not deleted)

| Item | Where it lives now | Treatment |
|---|---|---|
| Official prospective evaluation, protocol r2, amendment approval | `FootIQ_Club_Model_Development_v2/10_PROSPECTIVE_EVALUATION_PLAN.md`, `final_refit_v2_r1/08_*`, `official_readiness_audit_r1/`, `hardened_logger_r2_draft/` | Archive; cite as "future validation plan" |
| Immutable prediction ledgers, shadow logs | `matched_v1_prospective_r1/`, `shadow_integration_r1/`, `final_refit_v2_r1/prospective_log/` | Archive |
| Live polling, schedulers, API-Football client, daily match-day pipelines | `scripts/api_football_client_v24.py`, `build_live_data_v25.py`, `run_*_window_*.py`, `outputs/daily_*`, `matchday_*` | Archive; not run |
| Multi-source reconciliation, adapters, freshness validation | `source_adapters_r1/`, `freshness_validation_r1/`, `fresh_results_source_research/`, `bundesliga_source_promotion_r1/`, `matched_v1_prospective_r1/ingestion/` | Archive |
| Player performance prediction, player clustering/similarity | `FootIQ_ML_Data_Verification/player_form_v1/`, `scripts/build_player_impact_v21.py`, player sections of `PROJECT.md` | Future work (none was ever implemented per `CURRENT_STATE.md`) |
| PostgreSQL, Airflow, Docker, React, FastAPI platform | `PROJECT.md` blueprint (113 KB) | Superseded by this plan; keep as the "full vision" document |
| Production monitoring and deployment | blueprint only | Future work |
| 100+ other competitions (lower leagues, cups, MLS, etc.) | `FootIQ_Dataset_Submission/`, rest of 04a-04d | Left on disk, not surfaced |
| Lineup-adjusted predictions, odds, weather, injuries | `build_lineup_impact_v212.py`, weather/odds contracts | Future work |
| Trained models for UEFA club competitions | none | Future work, needs continental-aware ratings |

Proposed mechanism (needs your OK before I do it): add `docs/archive/README.md` that indexes these folders as "archived research," rather than moving large folders around. Moving risks breaking pickle paths (the v2 pickles need `_scripts` on the path).

---

## Known issues to be aware of before approval

1. **Streamlit is not installed** in `.venv`; adding it is a new dependency.
2. **The v2 pickles unpickle only with `_scripts` on `sys.path`** (noted in the v2 README). `predict.py` must add it.
3. **Windows encoding:** the simulator failed under the default encoding and passed with `python -X utf8`; the wrapper should set UTF-8.
4. **Historical team-strength inputs for internationals stop at 2026-06-02** (`CURRENT_STATE.md`); World Cup 2026 outcomes after that are loaded from separate files. The international model is therefore not refreshed for results after that date unless features are rebuilt.
5. **`.gitignore` does not exclude `.venv/` or `__pycache__/`**; fix before the first commit.
6. **Ligue 1 2019-20 incomplete (279/380) and 2026-27 seasons are partial**; the dashboard should show "season in progress / incomplete" explicitly.
7. **Wikipedia-sourced UEFA rows are CC BY-SA 4.0**: the app and report need an attribution line.
