# FootIQ Milestone 1 — Repository Audit and Baseline Preservation

Audit date: 20 October 2026 (Asia/Calcutta). Scope: PROJECT.md version 2.0, **Milestone 1 only**.

## Outcome and acceptance decision

**Milestone 1 acceptance is satisfied for preservation and reproducibility on the observed environment, with the limitations below explicitly retained.** 522 original files (48,384,714 bytes) were hashed before/after; none changed and no new files appeared outside `docs/baseline/`. Existing tests passed on a byte-identical snapshot; archived predictions and a fixed-seed simulation reproduced exactly. This is not validation of source rights, official match results, complete raw rebuild, clean-machine installation or future predictive performance. Milestone 2 has not started.

## Safety and evidence boundaries

- All newly created evidence and audit helpers are under `docs/baseline/`. PROJECT.md, legacy scripts, trained artifact, raw data and original outputs are untouched.
- No datasets downloaded, packages installed/upgraded, databases touched, branches created or Git staging/commit/push/merge performed.
- Snapshot archive contains exact original project bytes, excluding runtime/caches/Git/secret variants and the audit directory. It is a local preservation copy, not a rights-cleared redistribution artifact.
- Output-writing legacy scripts ran only in new `capture_2026-10-20/isolated_execution/run1` and `run2` copies. Audit hooks blocked external writes, network and subprocess launches, plus writes to copied raw data/model/scripts/tests. Some optional library `nul`/subprocess probes were denied and caught internally; no provider call succeeded or was required. Traces preserve those events.
- Original and copied protected-file checks passed. `-B` prevents bytecode writes. Inference required the existing model, never used `--force-train`, and never executed training fallback.

## Repository inventory

- 34 source scripts and five original test modules inspected through AST/function/I/O maps and focused source review.
- 472 data/report assets: 174 CSV, 182 JSON, 10 XLSX, four HTML, one pickle and 101 Markdown reports. Zero profiling errors.
- Existing READMEs, project blueprint, current-state audit, data inventory/manifests, reports and model configs were inspected. Existing PDF documents were preserved by checksum; no new independent verification of their narratives is claimed.
- `backend/`, `frontend/`, `database/`, `pipelines/`, `airflow/` and Docker implementation are absent. Legacy one-off club reports are present, but a separate trained club model is absent.

## Verified algorithm and feature implementation

1. **Foundation Elo:** starts at 1500, adds 75 points home advantage for expectation unless neutral, and uses competition K factors (World Cup 60, selected continental competitions 50, qualifiers 40, Nations League 35, friendlies 20, other 30), with goal-difference multipliers. It is a repository-derived Elo, not an official feed.
2. **Features:** 22 numeric indicators plus six observed one-hot competition buckets (28 artifact columns). Include venue/neutral/competition flags, pre-match Elo levels/difference, last-five/ten points and goal differences, Elo changes, opponent strength, rest difference and logged prior-match counts. Historical features are assembled before updating each team's history. Live inputs come from current-in-snapshot Elo/form CSVs, not an as-of historical feature store.
3. **Supervised models:** v2.6 comparisons fit standardized, balanced Logistic Regression (`C=0.8`, `max_iter=1200`), Random Forest (350 trees, depth 10, minimum leaf 35), and Gradient Boosting (220 trees, learning rate 0.035, depth 3, subsample 0.85). Training seeds are 20260607. The shipped v2.7 artifact contains logistic and boosting models, not Random Forest. No fitting was executed in this audit.
4. **Elo probability component:** two-way Elo expectation with an additional 55-point non-neutral home offset and a bounded draw formula. This differs intentionally from the foundation Elo's 75-point update offset; preserve both as separate logic.
5. **Calibration/ensemble:** temperature scaling raises clipped probabilities to `1/T` and normalizes. v2.6 searches T=0.65..2.80 in 0.05 increments on calibration data; ensemble weight grid steps are 0.1. Saved final weights are 0.3 Elo + 0.2 logistic + 0.5 boosting + 0 Poisson-lite. Saved temperatures are Elo 0.85, logistic 0.9, boosting 1.0, ensemble 0.9. Poisson-lite remains a benchmark/goal path, not a weighted public 1X2 component.
6. **Gates:** v2.7 requires the ensemble and logistic non-Pass decisions to agree. Saved min-confidence 0.56, min-gap 0, draw-risk-min 0.27, draw-gap-max 0.04. v2.8 introduces Model Lean with a data-quality floor 50 and directional/draw thresholds; consensus can create Strong Pick before the lean data-quality check. v2.11 softens probabilities (T 1.15, draw multiplier 1.10) and adds explicit lineup/draw guardrails as a shadow challenger. v2.12 requires both confirmed XIs, >=90% player identity coverage, pre-kickoff timing and caps probability movement at 0.05; it cannot promote an inherited Pass.
7. **Tournament:** v2.3 power uses Elo 30%, squad 32%, recent form 10%, tactics 10%, availability 7%, static market 5%, ceiling 3%, manager 3%. Goals use bounded exponential power differences, Poisson scores, Gaussian match noise, then separate ET and penalties for knockout draws. v2.13 locks actual results and uses seed 20260625. It does not call the learned 1X2 ensemble. Tie-break and slot logic are research simplifications, not certified official rules.
8. **Player ratings:** heuristic impact = 30% overall + 20% club level + 22% national role + 15% tactical fit + 10% form/sharpness + 3% tournament experience. Not an independently trained future-performance predictor.

Source call sites and saved parameters are captured in the AST dependency map and `artifact_metadata.json`; weather/lineup metadata do not make them trained v2.7 classifier features.


## Actual historical data and split reconstruction

The read-only feature builder reconstructed **25,235** training-eligible rows from the existing processed data. Actual observed split ranges/counts:

| Split | Count | First observed date | Last observed date |
|---|---:|---|---|
| Train | 18,164 | 2000-01-04 | 2018-12-31 |
| Calibration | 3,580 | 2019-01-02 | 2022-12-30 |
| Test | 3,491 | 2023-01-02 | 2026-06-02 |

Configured boundaries span broader calendar windows; do not confuse them with observed dates. Artifact training time is `2026-06-09T21:27:32.082855+00:00`; all-data retraining was not repeated and is not a new holdout score. The raw results include 72 additional unscored fixtures through June 27; scored features stop June 2. Raw historical score semantics lack a universal regulation/ET split, so pure 90-minute label integrity is an unresolved issue.

See [dataset inventory](DATASET_INVENTORY.md), full machine profiles and embedded provenance details. Missingness is measured per column, but optional blank fields and heuristic fallbacks require interpretation rather than blanket defect labels.

## Tests and commands actually executed

- Successful existing suite: **28 passed in 6.80s**, exit 0, five modules. Executed unchanged tests from a snapshot whose source hashes match originals. Options: `-q -s -p no:cacheprovider -p no:logging`, with JUnit output isolated. [Actual stdout](capture_2026-10-20/tests_verified.stdout.txt), [JUnit](capture_2026-10-20/tests_verified.junit.xml), [command](capture_2026-10-20/tests_verified_command.json).
- Predictor v2.7: two independent script processes, both exit 0; eight fixtures, zero non-Pass v2.7 picks.
- v2.8 gate: two processes, exit 0; seven Pass and one Model Lean.
- v2.13 simulator: two processes, exit 0; 50,000 runs each, seed 20260625; Spain 51.47%; all 72 group results and 31 recorded knockout results available for locking. These are archived pre-final inputs, not current live data.
- v2.14 validator: exit 0; reproduced group 34/52, published group 19/29, knockout advancement 25/30, combined 59/82 under mixed targets. No external truth revalidation.
- Full-precision component inference repeated without fitting: exact same arrays; finite probabilities in [0,1], maximum normalization error <=2.23e-16.
- Read-only artifact inspection/feature/split reconstruction: exit 0. `pip freeze --all`: exit 1 (pip absent); exact installed package versions recorded via importlib.metadata.

**Retained unsuccessful setup attempts:** initial OS temporary workspace creation was denied by sandbox permissions before legacy execution. First guarded pytest attempt failed during temporary capture initialization; second failed when its logging plugin tried to open the null device. A fresh-copy run with capture/logging/cache disabled succeeded. Failed setup traces/logs are retained; they are not counted as passed tests. No existing test or legacy code was changed.

## Deterministic prediction examples

All eight fixtures have complete reference feature rows, source Elo/form rows, model version/hash, training/date cutoffs, full-precision component outputs, exported rows, v2.7 decisions and v2.8 labels in `capture_2026-10-20/prediction_examples.json`.

| Fixture | Team 1 | Draw | Team 2 | v2.7 | v2.8 |
|---|---:|---:|---:|---|---|
| Portugal vs Chile | 64.214% | 28.774% | 7.012% | pass | Pass |
| Germany vs USA | 35.814% | 38.646% | 25.540% | pass | Pass |
| Bolivia vs Scotland | 20.208% | 35.189% | 44.603% | pass | Pass |
| Brazil vs Egypt | 60.044% | 30.839% | 9.117% | pass | Pass |
| Argentina vs Honduras | 76.363% | 19.790% | 3.848% | pass | Pass |
| Morocco vs Norway | 33.744% | 39.043% | 27.213% | pass | Pass |
| Colombia vs Jordan | 62.373% | 29.253% | 8.375% | pass | Pass |
| Argentina vs Iceland | 80.969% | 15.994% | 3.037% | pass | Model Lean |


Model artifact SHA-256: `0df37dd7c659e35b61a64b4178d19cddc2dd103f95a9967314321e8ff3784a1a`.

The model's class order is home/draw/away; displayed team1/team2 orientation can differ (Germany–USA has USA as model home). Reference packets preserve this explicitly. Feature/input snapshots are archived reconstructions. Historical source **availability** cutoffs are incomplete, so these are not newly proven pre-kickoff forecasts.

## Reproducible tournament example

[SIMULATION_EXAMPLE.json](SIMULATION_EXAMPLE.json) pins input hashes, rules/config, seed, iterations and top-team outputs. The stable odds CSV has exact SHA-256 `41bd8d6aa1f43152789f7ddc8a5886143c33682d4a4c2c5cd7ba55f718225d0e` in both runs and the original. Generated report/config timestamps differ by design; numeric outputs are deterministic in the observed environment. `generated_at` uses host-local time, not a data cutoff. Archive results extend through July 18; the final is still simulated.

No change to random-seed logic, iteration count or tournament algorithm was needed. Determinism across other Python/library versions and official-rule fidelity remain unproven. World Cup prediction probabilities and tournament advancement outputs remain different products.

## Preservation checksums and packaged references

- Before/after manifests: `original_files_before.json`, `original_files_after.json`; portable checksum list: `original_files.sha256` under the capture directory.
- Selected stable CSVs (v2.7 features/probabilities/picks, v2.8 picks, v2.13 odds): **5/5 exact matches** between two processes and original files; see `determinism_comparison.json`.
- Original and copied raw/model/script/test integrity: zero mismatches. The trained artifact was not written.
- Local `reference_snapshot.zip`: 9,771,091 bytes, SHA-256 `2aedd13dd08a5df8d044c39ff62951af6c7dd1fe8dc9b3f8bfa3b9464b83d182`. Original 522-file content manifest is bundled separately.
- Generated reference outputs are preserved under `capture_2026-10-20/references/run1/` and `run2/`; all isolated copies remain because no deletion was authorized.

## Environment and reproducibility limits

[ENVIRONMENT.md](ENVIRONMENT.md) records all installed packages, CPython 3.12.14, Windows AMD64, base-runtime path and UTF-8 requirements. Direct versions include NumPy 1.26.4, pandas 2.2.1, scikit-learn 1.5.1, openpyxl 3.1.2, lxml 5.4.0 and pytest 8.4.2. No environment variables/credentials were dumped. The version file captures transitives too; pip is absent from the venv, and no offline wheels or clean-machine rebuild was tested.

## Dependency map and risk register

[DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) combines a high-level graph with actual read/write edges; AST and runtime JSON maps retain call-site evidence. [RISK_REGISTER.md](RISK_REGISTER.md) and its JSON contain 20 open findings covering source availability/rights, ET label semantics, training/live feature mismatches, temporal leakage, gate selection bias, simulator rules, environment portability, club expansion and player coverage. These are documented findings, not silent model fixes.

## Files created and navigation

- `BASELINE_AUDIT.md` — this report.
- `DATASET_INVENTORY.md`, `DATASET_PROVENANCE_DETAILS.json`, `YEAR_RANGE_SUPPLEMENT.json` — human summary and complementary source/year profiles.
- `DEPENDENCY_MAP.md`, `RUNTIME_DEPENDENCIES.json` — component graph and observed I/O.
- `ENVIRONMENT.md`, `TEST_RESULTS.json`, `SIMULATION_EXAMPLE.json`, `RISK_REGISTER.md`, `RISK_REGISTER.json`.
- `capture_baseline.py`, `isolated_runner.py`, `resume_capture.py`, `verify_tests.py`, `export_examples.py`, `finalize_audit.py` — audit-only capture/recovery/report helpers; no original source replacements.
- `capture_2026-10-20/` — manifests, full profiles, environment lock, snapshot ZIP, artifact metadata, examples, raw logs/JUnit/traces, generated references, integrity and determinism evidence, retained isolated workspaces.
- A final `FINAL_VERIFICATION.json` and `EVIDENCE_MANIFEST.json` will record the closing original-file check and evidence checksums. They are descriptive inventories, not a cryptographic signature or protection from malicious edits.

## Acceptance checklist

| Milestone 1 criterion | Status | Evidence |
|---|---|---|
| Repository/data/model/source audit | Satisfied | Inventory, focused inspection, static/runtime maps |
| Dataset sizes/rows/schema/ranges/missingness/provenance | Satisfied with explicit non-tabular/unverified fields | Full inventory + provenance/year supplements |
| Original preservation | Satisfied | 522 pre/post SHA-256 matches |
| Exact observed environment | Satisfied | Metadata version inventory; pip absence documented |
| Actual existing tests | Satisfied | 28 passed, exit 0, JUnit and stdout |
| Fixed prediction inputs/outputs/cutoffs | Satisfied for archived replay | Eight packets + full-precision checks; missing known-at provenance documented |
| Fixed-seed simulation | Satisfied on observed environment | Two 50,000-run results and exact CSV comparison |
| Integration/risk documentation | Satisfied | Dependency map and 20 open risks |
| No original code/data/artifact changes | Satisfied | Integrity manifests and guarded isolated execution |
| Clean-machine build/full raw retrain/source-rights verification | Not claimed; outside completed verification | Explicit limitations, later approval required |

**Stop:** Milestone 1 only is complete. No source selection/verification implementation, database design implementation, club model or Milestone 2 work has begun. Further work requires approval.
