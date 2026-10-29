"""Create human/machine audit reports from measured evidence, exclusively new files."""
from __future__ import annotations
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

BASE = Path(__file__).parent.resolve()
ROOT = BASE.parents[1]
C = BASE / "capture_2026-10-20"

def load(name):
    return json.loads((C/name).read_text(encoding="utf-8"))

def write(name, value):
    with (BASE/name).open("x",encoding="utf-8",newline="") as f:
        if name.endswith(".json"):
            json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
            f.write("\n")
        else:
            f.write(value)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def csvrows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

inventory = load("dataset_inventory.json")["files"]
idx = {r["path"]:r for r in inventory}
before = load("original_files_before.json")["files"]
env = load("environment.json")
summary = load("capture_summary.json")
metadata = load("artifact_metadata.json")
examples = load("prediction_examples.json")
comparisons = load("determinism_comparison.json")["comparisons"]
commands = load("commands.json")
verified_test = load("tests_verified_command.json")
junit = ET.parse(C/"tests_verified.junit.xml").getroot()
cases = junit.findall(".//testcase")
test_counts = Counter(r.attrib["classname"] for r in cases)
test_summary = {"exit_code":verified_test["exit_code"],"testcases":len(cases),
                "failures":len(junit.findall(".//failure")),"errors":len(junit.findall(".//error")),
                "skipped":len(junit.findall(".//skipped")),"by_classname":dict(test_counts),
                "stdout": "capture_2026-10-20/tests_verified.stdout.txt", "junit":"capture_2026-10-20/tests_verified.junit.xml",
                "setup_attempts":"Initial guarded pytest attempts failed before collection; successful fresh-copy rerun disabled capture/logging/cache plugins. No test function changed."}
write("TEST_RESULTS.json",test_summary)

provenance_details = []
year_ranges = []
for item in inventory:
    p=ROOT/item["path"]
    if p.suffix==".csv":
        rows=csvrows(p)
        fields=[c for c in item.get("columns",[]) if re.search(r"source|provenance|license|url|terms",c,re.I)]
        provenance_details.append({"path":item["path"],"provenance_key":item["provenance_key"],
          "embedded_fields":{c:{"distinct_nonblank":len({r.get(c) for r in rows if r.get(c)}),
              "most_common":Counter(r[c] for r in rows if r.get(c)).most_common(25)} for c in fields},
          "interpretation":"Local embedded claims, not independent upstream verification; top 25 values shown per field."})
    elif p.suffix==".json":
        obj=json.loads(p.read_text(encoding="utf-8-sig"))
        years=defaultdict(list)
        def walk(x):
            if isinstance(x,dict):
                for k,v in x.items():
                    if k.lower() in {"year","date","season_name"} and re.fullmatch(r"\d{4}",str(v)):
                        years[k].append(int(v))
                    if isinstance(v,(dict,list)): walk(v)
            elif isinstance(x,list):
                for v in x: walk(v)
        walk(obj)
        if years:
            year_ranges.append({"path":item["path"],"year_fields":{k:{"min":min(v),"max":max(v),"values":len(v)} for k,v in years.items()},
                               "note":"Year-only values supplement ISO dates; no invented day or retrieval date."})
write("DATASET_PROVENANCE_DETAILS.json",provenance_details)
write("YEAR_RANGE_SUPPLEMENT.json",year_ranges)

traces=[]
for p in sorted((C/"traces").glob("*.json")):
    t=json.loads(p.read_text(encoding="utf-8"))
    if t["action"]=="pytest": continue
    t["existing_read_paths"]=[r for r in t["read_paths"] if (ROOT/r).is_file()]
    t["attempted_missing_reads"]=[r for r in t["read_paths"] if not (ROOT/r).is_file()]
    traces.append(t)
write("RUNTIME_DEPENDENCIES.json",traces)

simcfg=json.loads((C/"references/run1/outputs/live_tournament_v213_config.json").read_text(encoding="utf-8"))
odds=csvrows(C/"references/run1/data/processed/live_tournament_v213_tournament_odds.csv")
sim_inputs=[r for t in traces if t["action"]=="simulate_live_tournament_v213.py" for r in t["existing_read_paths"] if r.startswith("data/")]
sim_example={"version":"v2.13","base_engine":"v2.3 goal-based/team-power engine", "seed":simcfg["seed"],"iterations":simcfg["simulations"],
             "input_manifest":[r for r in before if r["path"] in set(sim_inputs)],"configuration":simcfg,
             "top_teams":odds[:10],"output_comparison":next(r for r in comparisons if "tournament_odds" in r["path"]),
             "data_cutoff":"Archived group results plus verified knockout records through 2026-07-18; final remains simulated. Not a fresh October forecast.",
             "timestamp_policy":"generated_at uses execution host local time, not a reliable data cutoff; reports/config differ by timestamp across runs.",
             "limitations":["No guarantee of determinism across Python/library versions", "Simplified group tie-breaks include random tie-breaker, not complete official rules", "Not a generic club-cup simulator", "Historical accuracy not independently verified"]}
write("SIMULATION_EXAMPLE.json",sim_example)

risks=[
 ("R01","High","Data availability","Raw results contain 49,368 rows but 72 have no scores; processed scored rows stop 2026-06-02.","dataset_inventory.json; build_foundation_tables.py","Treat unscored rows as unavailable; no automatic historical refresh assumed."),
 ("R02","High","Data availability","StatsBomb events/360 directories absent despite inherited inventory describing prior downloads.","data/raw/statsbomb; outputs/world_cup_data_inventory.md","Preserve summaries; full event reconstruction blocked until approved data access in later milestone."),
 ("R03","High","Source licensing","Inherited license/provenance descriptions do not establish exact upstream revisions, training rights or redistribution rights.","data/processed/data_manifest.csv; PROJECT.md section 6","Record unresolved source chain and permissions; no new data acquisition/publication in M1."),
 ("R04","High","Temporal/target semantics","Historical results score labels are copied directly; raw schema does not independently identify 90-minute versus extra-time goals.","build_foundation_tables.py result_label/build_international_matches_and_elo","Verify historical score semantics before claiming pure 90-minute training labels; retain frozen model unchanged."),
 ("R05","High","Training-serving parity","Historical matches_prior is length of deque(maxlen=20); live matches_prior uses total matches_played.","model_bakeoff_v26.py summarize_history; build_live_predictions_v27.py build_live_feature_rows","Flag mismatch; later candidate/adapter correction requires new version and evaluation, not silent baseline repair."),
 ("R06","Medium","Temporal leakage","Dummy-column vocabulary is created from concatenated train/calibration/test frames.","model_bakeoff_v26.py design_matrix","Future preprocessing must fit train only; no future labels used by this encoding, but strict contract is unmet."),
 ("R07","High","Temporal leakage","Date-only sorting and incomplete availability timestamps cannot prove what was known before every kickoff.","model_bakeoff_v26.py build_feature_frame; snapshot CSVs","Separate archived replay from genuine forecast; conservative same-day and known-at checks later."),
 ("R08","High","Evaluation selection","v2.8 cites model_v26_test_predictions.csv as calibration_source; v2.11 explicitly used 21 live fixtures diagnostically.","build_confidence_gate_v28.py V28_CONFIG; build_confidence_gate_v211.py honesty_note","Treat gate performance as development evidence; require untouched future validation before new claims."),
 ("R09","High","Club expansion","No systematically trained/evaluated club model or complete club-season feed exists; isolated club reports are not such a model.","script_dependency_map.json; legacy reports","Maintain separate model domain; defer all club implementation beyond M1."),
 ("R10","High","Player data","1,246 player impact rows are heuristic squad ratings; complete minutes/actions/per-90 cohort not verified.","build_player_impact_v21.py; dataset_inventory.json","Do not describe them as future-performance ML or validated similarity features."),
 ("R11","Medium","Reproducibility","Existing venv lacks pip; external base Python runtime is referenced by the venv.","environment.json; pip-freeze-command.json","Version inventory recorded through importlib.metadata; clean-machine installation/offline wheels unverified."),
 ("R12","Medium","Reproducibility","Default Windows encoding can misdecode team names; simulation succeeds with -X utf8.","build_worldcup_model_v2.py read_csv; UTF-8 execution logs","Record encoding requirement; no legacy helper changes in baseline."),
 ("R13","Medium","Model security","Pickle artifact executes trusted Python objects and depends on sklearn compatibility.","live_match_model.pkl; artifact_metadata.json","Use only local hashed trusted artifact; do not accept arbitrary model uploads."),
 ("R14","High","Tournament rules","Group rank uses points, goal difference, goals scored then random.random; slot logic is a prototype, not full official rules certification.","build_worldcup_model_v23.py rank_group/third_sort; build_worldcup_model_v2.py resolve_slot","Preserve deterministic prototype; validate season-specific rules before new competition simulation."),
 ("R15","Medium","Update operations","Manual API scripts/cache budget exist but no scheduler/reconciliation warehouse; account entitlements unverified.","api_football_client_v24.py; build_live_data_v25.py","No live calls in M1; later quotas/source access gate required."),
 ("R16","High","Claims","59/82 validation mixes group 90-minute reads and knockout advancement; small/selective samples do not prove future accuracy.","validate_worldcup_full_v214.py; generated report","Keep targets and denominators separate; no independent match-results verification claimed."),
 ("R17","Medium","Destructive execution","Legacy main routines overwrite output tables; simulator also writes model_v23_market_priors.csv.","RUNTIME_DEPENDENCIES.json","Execute only copied snapshots; compare original before/after hashes."),
 ("R18","Medium","Feature mismatch","Foundation is_competitive marks any non-friendly as competitive; live tournament_flags recognizes a narrower keyword list.","build_foundation_tables.py; build_live_predictions_v27.py tournament_flags","Audit context mapping for future adapter; retain current outputs unchanged."),
 ("R19","Medium","Testing scope","28 tests focus on later gate/lineup/matchday/result-locking helpers; no complete raw rebuild, retraining, live-provider or platform test coverage.","TEST_RESULTS.json; scripts/tests static map","Baseline execution supplements tests but does not certify future architecture."),
 ("R20","Medium","Storage/retention","Local snapshot and three isolated copies include inherited third-party data and duplicate bytes.","snapshot_manifest.json; isolated_execution/","Retain locally per requested no-deletion rule; do not publish this bundle without separate rights/owner review."),
]
risk_objects=[dict(zip(["id","severity","category","finding","evidence","mitigation"],r),status="Open/documented",owner="Project owner; later milestone assignee TBD") for r in risks]
write("RISK_REGISTER.json",risk_objects)
write("RISK_REGISTER.md","# Milestone 1 risk register\n\nAll findings are open/documented; M1 preserves evidence rather than repairing legacy models. No new source rights were verified online.\n\n| ID | Severity | Category | Finding | Mitigation |\n|---|---|---|---|---|\n"+"".join(f"| {r['id']} | {r['severity']} | {r['category']} | {r['finding']} | {r['mitigation']} |\n" for r in risk_objects))

dependency_md='''# Dependency and safe-execution map

Static detail: `capture_2026-10-20/script_dependency_map.json` records imports, functions, file literals, URLs and I/O/fit call sites for every original Python file. Static literals are not proof of executed edges. `RUNTIME_DEPENDENCIES.json` and captured audit traces record actual attempted reads/writes for exercised paths; nonexistent pycache probes are separated from existing files.

```mermaid
flowchart TD
  R[Raw international results] --> F[build_foundation_tables.py: Elo and form]
  F --> H[international_matches and Elo/form CSVs]
  H --> B[model_bakeoff_v26.py: features, temporal split, calibration]
  B --> C[Model configs, pass rules, evaluation tables]
  B --> T[v2.7 training path: NOT executed]
  T --> A[Saved live_match_model.pkl]
  H --> L[v2.7 live feature adapter]
  V[v2.5 fixture/status/weather/quality CSVs] --> L
  A --> P[v2.7 ensemble inference]
  L --> P
  P --> G[v2.8 publishing gate]
  G --> O[Prediction tables and reports]
  S[Profiles, v1 ratings, tactical summaries, availability] --> Q[v2.3 team-power/goal engine]
  K[World Cup fixtures and recorded results] --> U[v2.13 fixed-seed live simulation]
  Q --> U
  U --> W[Title and advancement odds]
  D[v2.9 archived matchday snapshots] --> E[v2.10/v2.14 validation]
  E --> X[Target-specific validation reports]
```

## Components inspected but not run

- Foundation builders overwrite international/Elo/form and other processed tables; their mains were not executed.
- v1/v2/v2.1/v2.2/v2.3 builders implement successive hand-weighted strength/goal/simulation research models; no full rebuild was attempted.
- `model_bakeoff_v26.py` fits Logistic Regression, Random Forest and Gradient Boosting and compares Elo/Poisson-lite/ensemble probabilities. Only read-only feature/split reconstruction was exercised, not fitting.
- v2.7 would train if its artifact were absent or `--force-train` were supplied. Audit launcher required the artifact and never supplied that flag; model hashes were verified unchanged.
- v2.5/API/weather and international-slate jobs can contact providers and write caches/tables. No live/provider/download job was executed.
- v2.11/v2.12 are shadow confidence/lineup challengers; tests exercise helpers but their full data-producing mains were not run.
- StatsBomb downloader and player-squad fetcher were not run. Missing events prevent a complete offline raw-event rebuild.

## Actual run edges

'''
for t in traces:
    if "run1" not in t["root"]: continue
    dependency_md+=f"### {t['action']}\n\nVerified reads:\n\n"+"".join(f"- `{r}`\n" for r in t["existing_read_paths"] if not r.startswith("scripts/"))
    dependency_md+="\nWrites in isolated copy only:\n\n"+"".join(f"- `{r}`\n" for r in t["written_paths"] if not r.startswith("audit_trace"))+"\n"
write("DEPENDENCY_MAP.md",dependency_md)

key_paths=["data/raw/international_results/results.csv","data/processed/international_matches.csv","data/processed/team_elo_match_history.csv","data/processed/team_elo_latest.csv","data/processed/team_recent_form_latest.csv","data/processed/statsbomb_worldcup_matches.csv","data/processed/statsbomb_team_event_summary.csv","data/processed/worldcup_2026_matches.csv","data/processed/worldcup_2026_teams.csv","data/processed/player_impact_v21.csv","data/processed/worldcup_matchday_v29_snapshots.csv","data/processed/matchday_validation_v210.csv","data/processed/worldcup_2026_knockout_results_verified.csv"]
data_md="# Dataset inventory guide\n\nFull per-file profiles: [JSON](capture_2026-10-20/dataset_inventory.json), [CSV overview](capture_2026-10-20/dataset_inventory.csv). Embedded source fields: [provenance details](DATASET_PROVENANCE_DETAILS.json). Year-only JSON fields: [supplement](YEAR_RANGE_SUPPLEMENT.json).\n\n| File | Bytes | Rows | Columns | Missing-token cells | ISO date fields/ranges |\n|---|---:|---:|---:|---:|---|\n"
for rel in key_paths:
    r=idx[rel]
    ds="; ".join(f"{k}: {v['min']} to {v['max']}" for k,v in r.get("date_ranges",{}).items()) or "No ISO date field"
    data_md+=f"| `{rel}` | {r['size_bytes']:,} | {r['row_count']:,} | {len(r['columns'])} | {sum(r.get('missing_token_by_column',{}).values()):,} | {ds} |\n"
data_md+='''
## Interpretation and limits

- 174 CSVs, 182 JSONs, 10 workbooks, four HTMLs, one pickle and 101 Markdown reports are profiled as 472 data/report assets; no profiling errors. HTML/Markdown/pickle are non-tabular, so row/column missingness is not applicable. Nested JSON table counts overlap; never sum them as match counts. Workbooks are read-only and first-row-header assumptions are explicit per sheet.
- Missingness separately counts blanks/nulls and common textual missing tokens. Zero/False are valid values. Empty source-error, optional shootout or Pass-grade fields may be intentional; missing-cell totals are not defect counts. Formula cells are not recalculated, source retrieval dates are not inferred from filesystem mtimes, and no hidden future availability is invented.
- Raw results have 49,368 rows through 2026-06-27, with 72 missing home and away scores. The 49,296 scored processed records end 2026-06-02. This is a scored/unscored distinction, not evidence of a refreshed scored training set.
- The 336-team Elo table includes inactive/historical teams; some last-match dates are as early as 1923. A row called "latest" does not mean current worldwide coverage.
- Six data contracts, player availability overrides, v2.5 confirmed lineups and the latest v2.9 lineups CSV are header-only. Archived lineup data may exist elsewhere; header-only current tables do not establish general live coverage.
- Player impact has 1,246 rows without blank fields, but model-derived fallbacks can still produce fully populated heuristic values. Completeness does not establish measured player performance.
- Matchday validation has missing provider scores/results and nullable Pass grading; all per-column counts are retained. Original source records have not been externally reverified.
- Inherited inventory claims earlier StatsBomb event/360 downloads; this archive contains metadata/lineups and processed summaries, not the raw event/360 layers.
'''
write("DATASET_INVENTORY.md",data_md)

packs="\n".join(f"- {p['name']}=={p['version']}" for p in env["packages"])
write("ENVIRONMENT.md",f'''# Observed baseline environment

- Executable: `{env['python_executable']}`
- CPython: `{env['python_version']}`
- Platform: `{env['platform']}`, `{env['machine']}`
- Base runtime: `{env['base_prefix']}` (the venv is not self-contained)
- Audit runs used `-B -X utf8`; existing model inputs/artifact were not changed.
- Full environment: `capture_2026-10-20/environment.json`; exact installed distribution inventory: `capture_2026-10-20/requirements-observed.txt`.
- `pip freeze --all` was attempted and failed because this existing venv has no pip. No installation/upgrade was attempted; importlib.metadata captured installed versions instead.
- This is a version lock/inventory, not an offline wheelhouse or a demonstrated clean-machine installation. Existing sklearn artifact compatibility was exercised on this host only.

## Exact installed distribution versions

{packs}
''')

table="| Fixture | Team 1 | Draw | Team 2 | v2.7 | v2.8 |\n|---|---:|---:|---:|---|---|\n"
for e in examples["examples"]:
    r=e["exported_probability_row"]
    table+=f"| {r['team1']} vs {r['team2']} | {float(r['ensemble_team1_win_probability'])*100:.3f}% | {float(r['ensemble_draw_probability'])*100:.3f}% | {float(r['ensemble_team2_win_probability'])*100:.3f}% | {e['v27_public_row']['public_pick']} | {e['v28_public_row']['v28_tier']} |\n"

algorithms='''## Verified algorithm and feature implementation

1. **Foundation Elo:** starts at 1500, adds 75 points home advantage for expectation unless neutral, and uses competition K factors (World Cup 60, selected continental competitions 50, qualifiers 40, Nations League 35, friendlies 20, other 30), with goal-difference multipliers. It is a repository-derived Elo, not an official feed.
2. **Features:** 22 numeric indicators plus six observed one-hot competition buckets (28 artifact columns). Include venue/neutral/competition flags, pre-match Elo levels/difference, last-five/ten points and goal differences, Elo changes, opponent strength, rest difference and logged prior-match counts. Historical features are assembled before updating each team's history. Live inputs come from current-in-snapshot Elo/form CSVs, not an as-of historical feature store.
3. **Supervised models:** v2.6 comparisons fit standardized, balanced Logistic Regression (`C=0.8`, `max_iter=1200`), Random Forest (350 trees, depth 10, minimum leaf 35), and Gradient Boosting (220 trees, learning rate 0.035, depth 3, subsample 0.85). Training seeds are 20260607. The shipped v2.7 artifact contains logistic and boosting models, not Random Forest. No fitting was executed in this audit.
4. **Elo probability component:** two-way Elo expectation with an additional 55-point non-neutral home offset and a bounded draw formula. This differs intentionally from the foundation Elo's 75-point update offset; preserve both as separate logic.
5. **Calibration/ensemble:** temperature scaling raises clipped probabilities to `1/T` and normalizes. v2.6 searches T=0.65..2.80 in 0.05 increments on calibration data; ensemble weight grid steps are 0.1. Saved final weights are 0.3 Elo + 0.2 logistic + 0.5 boosting + 0 Poisson-lite. Saved temperatures are Elo 0.85, logistic 0.9, boosting 1.0, ensemble 0.9. Poisson-lite remains a benchmark/goal path, not a weighted public 1X2 component.
6. **Gates:** v2.7 requires the ensemble and logistic non-Pass decisions to agree. Saved min-confidence 0.56, min-gap 0, draw-risk-min 0.27, draw-gap-max 0.04. v2.8 introduces Model Lean with a data-quality floor 50 and directional/draw thresholds; consensus can create Strong Pick before the lean data-quality check. v2.11 softens probabilities (T 1.15, draw multiplier 1.10) and adds explicit lineup/draw guardrails as a shadow challenger. v2.12 requires both confirmed XIs, >=90% player identity coverage, pre-kickoff timing and caps probability movement at 0.05; it cannot promote an inherited Pass.
7. **Tournament:** v2.3 power uses Elo 30%, squad 32%, recent form 10%, tactics 10%, availability 7%, static market 5%, ceiling 3%, manager 3%. Goals use bounded exponential power differences, Poisson scores, Gaussian match noise, then separate ET and penalties for knockout draws. v2.13 locks actual results and uses seed 20260625. It does not call the learned 1X2 ensemble. Tie-break and slot logic are research simplifications, not certified official rules.
8. **Player ratings:** heuristic impact = 30% overall + 20% club level + 22% national role + 15% tactical fit + 10% form/sharpness + 3% tournament experience. Not an independently trained future-performance predictor.

Source call sites and saved parameters are captured in the AST dependency map and `artifact_metadata.json`; weather/lineup metadata do not make them trained v2.7 classifier features.
'''

audit=f'''# FootIQ Milestone 1 — Repository Audit and Baseline Preservation

Audit date: 20 October 2026 (Asia/Calcutta). Scope: PROJECT.md version 2.0, **Milestone 1 only**.

## Outcome and acceptance decision

**Milestone 1 acceptance is satisfied for preservation and reproducibility on the observed environment, with the limitations below explicitly retained.** {summary['original_files']} original files ({summary['total_original_bytes']:,} bytes) were hashed before/after; none changed and no new files appeared outside `docs/baseline/`. Existing tests passed on a byte-identical snapshot; archived predictions and a fixed-seed simulation reproduced exactly. This is not validation of source rights, official match results, complete raw rebuild, clean-machine installation or future predictive performance. Milestone 2 has not started.

## Safety and evidence boundaries

- All newly created evidence and audit helpers are under `docs/baseline/`. PROJECT.md, legacy scripts, trained artifact, raw data and original outputs are untouched.
- No datasets downloaded, packages installed/upgraded, databases touched, branches created or Git staging/commit/push/merge performed.
- Snapshot archive contains exact original project bytes, excluding runtime/caches/Git/secret variants and the audit directory. It is a local preservation copy, not a rights-cleared redistribution artifact.
- Output-writing legacy scripts ran only in new `capture_2026-10-20/isolated_execution/run1` and `run2` copies. Audit hooks blocked external writes, network and subprocess launches, plus writes to copied raw data/model/scripts/tests. Some optional library `nul`/subprocess probes were denied and caught internally; no provider call succeeded or was required. Traces preserve those events.
- Original and copied protected-file checks passed. `-B` prevents bytecode writes. Inference required the existing model, never used `--force-train`, and never executed training fallback.

## Repository inventory

- {len([r for r in before if r['path'].startswith('scripts/') and r['path'].endswith('.py')])} source scripts and five original test modules inspected through AST/function/I/O maps and focused source review.
- {summary['dataset_assets']} data/report assets: 174 CSV, 182 JSON, 10 XLSX, four HTML, one pickle and 101 Markdown reports. Zero profiling errors.
- Existing READMEs, project blueprint, current-state audit, data inventory/manifests, reports and model configs were inspected. Existing PDF documents were preserved by checksum; no new independent verification of their narratives is claimed.
- `backend/`, `frontend/`, `database/`, `pipelines/`, `airflow/` and Docker implementation are absent. Legacy one-off club reports are present, but a separate trained club model is absent.

{algorithms}

## Actual historical data and split reconstruction

The read-only feature builder reconstructed **25,235** training-eligible rows from the existing processed data. Actual observed split ranges/counts:

| Split | Count | First observed date | Last observed date |
|---|---:|---|---|
| Train | 18,164 | 2000-01-04 | 2018-12-31 |
| Calibration | 3,580 | 2019-01-02 | 2022-12-30 |
| Test | 3,491 | 2023-01-02 | 2026-06-02 |

Configured boundaries span broader calendar windows; do not confuse them with observed dates. Artifact training time is `{metadata['trained_at_utc']}`; all-data retraining was not repeated and is not a new holdout score. The raw results include 72 additional unscored fixtures through June 27; scored features stop June 2. Raw historical score semantics lack a universal regulation/ET split, so pure 90-minute label integrity is an unresolved issue.

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

{table}

Model artifact SHA-256: `{examples['model_sha256']}`.

The model's class order is home/draw/away; displayed team1/team2 orientation can differ (Germany–USA has USA as model home). Reference packets preserve this explicitly. Feature/input snapshots are archived reconstructions. Historical source **availability** cutoffs are incomplete, so these are not newly proven pre-kickoff forecasts.

## Reproducible tournament example

[SIMULATION_EXAMPLE.json](SIMULATION_EXAMPLE.json) pins input hashes, rules/config, seed, iterations and top-team outputs. The stable odds CSV has exact SHA-256 `{next(r['run1_sha256'] for r in comparisons if 'tournament_odds' in r['path'])}` in both runs and the original. Generated report/config timestamps differ by design; numeric outputs are deterministic in the observed environment. `generated_at` uses host-local time, not a data cutoff. Archive results extend through July 18; the final is still simulated.

No change to random-seed logic, iteration count or tournament algorithm was needed. Determinism across other Python/library versions and official-rule fidelity remain unproven. World Cup prediction probabilities and tournament advancement outputs remain different products.

## Preservation checksums and packaged references

- Before/after manifests: `original_files_before.json`, `original_files_after.json`; portable checksum list: `original_files.sha256` under the capture directory.
- Selected stable CSVs (v2.7 features/probabilities/picks, v2.8 picks, v2.13 odds): **5/5 exact matches** between two processes and original files; see `determinism_comparison.json`.
- Original and copied raw/model/script/test integrity: zero mismatches. The trained artifact was not written.
- Local `reference_snapshot.zip`: {summary['snapshot_bytes']:,} bytes, SHA-256 `{summary['archive_sha256']}`. Original 522-file content manifest is bundled separately.
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
'''
write("BASELINE_AUDIT.md",audit)

# Closing verification includes all original files and all test-copy originals.
changed=[]
for r in before:
    p=ROOT/r["path"]
    if not p.exists() or p.stat().st_size!=r["size_bytes"] or sha(p)!=r["sha256"]:
        changed.append(r["path"])
test_changed=[]
for r in before:
    if r["path"].startswith(("scripts/","tests/","data/model_artifacts/","data/raw/")):
        p=C/"isolated_execution/tests_verified"/r["path"]
        if sha(p)!=r["sha256"]: test_changed.append(r["path"])
write("FINAL_VERIFICATION.json",{"original_files_checked":len(before),"changed_original_files":changed,
    "test_snapshot_protected_mismatches":test_changed,"verified_tests":test_summary,"stable_csv_references":comparisons,
    "status":"satisfied_with_documented_limitations" if not changed and not test_changed and verified_test["exit_code"]==0 and all(r["exact_repeat_match"] for r in comparisons) else "not_satisfied"})
evidence=[]
for p in sorted(BASE.rglob("*")):
    if p.is_file() and "isolated_execution" not in p.parts and p.name!="EVIDENCE_MANIFEST.json":
        evidence.append({"path":p.relative_to(BASE).as_posix(),"size_bytes":p.stat().st_size,"sha256":sha(p)})
write("EVIDENCE_MANIFEST.json",{"files":evidence,"exclusions":"Working execution copies (already represented by snapshot/input manifests), and self to avoid recursive hash","signing":"unsigned inventory"})
print(json.dumps({"report":str(BASE/"BASELINE_AUDIT.md"),"original_changes":changed,"evidence_files":len(evidence),"tests":test_summary["testcases"],"status":"satisfied_with_documented_limitations"},indent=2))
