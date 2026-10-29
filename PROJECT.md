# FootIQ — Global Football Data Engineering, Performance Analytics & Machine Learning Prediction Platform

**Document:** `PROJECT.md`  
**Version:** 2.0 (multi-competition master blueprint)  
**Date:** 20 October 2026  
**Status:** Repository baseline audited; expanded platform planned, not implemented  
**Existing project:** `world-cup-prediction-model`  
**Academic deliverables:** Data Engineering mini project; Machine Learning mini project; optional literature survey/research paper

> **Truth and scope legend:** **VERIFIED EXISTING** = inspected in this repository, with runtime verification stated explicitly where performed. **PARTIAL** = usable research functionality exists but does not satisfy the complete platform requirement. **PLANNED** = not implemented. **CONDITIONAL** = dependent on data access, permission, provider coverage, or experiment results. Earlier labels such as EXISTING (reported) describe inherited source documentation and must be read alongside the audit in section 2. Examples and performance targets are not measured outcomes. This update is documentation only: no implementation, algorithm/artifact changes, dependency installation, dataset download, migration, database modification, branch creation, staging, commit, merge, or push is authorized.

---

## 1. Executive summary

**FootIQ** is a planned multi-competition football intelligence system combining automated ingestion, data quality validation, a PostgreSQL analytical warehouse, time-safe features, supervised and unsupervised ML, separate international and club prediction models, player analysis, and tournament simulation. The target architecture is Football Data Sources → Extraction → Validation → Normalization → PostgreSQL → Feature Engineering → ML Models → FastAPI → React. React will use **JavaScript/JSX, not TypeScript**. Apache Airflow will orchestrate batch/incremental workflows, with Docker Compose providing reproducible infrastructure.

FootIQ **extends the existing Python World Cup prediction research pipeline**. Inspection and earlier runs in this chat verified the international 90-minute ensemble, confidence gates, separate goal-based World Cup simulator, datasets, scripts, tests, and CSV/Markdown reports. Preserve those original algorithms, artifacts, and outputs; build adapters and new components around them. Warehouse migration must establish parity before any future replacement is considered.

The same shared platform produces **two distinct assessed projects**:

1. **Data Engineering:** *Global Football Data Engineering & Analytics Pipeline* — extraction, validation, normalization, incremental upserts, PostgreSQL warehouse, Airflow DAGs, source freshness, quality monitoring, SQL analytics, and an operational dashboard.
2. **Machine Learning:** *Football Performance Analytics and Match Outcome Prediction Using Machine Learning* — leakage-safe match classification, calibrated ensemble predictions, player performance modeling (where reliable targets exist), player clustering/similarity, dimensionality reduction, evaluation dashboards, and World Cup simulation.
3. **Optional research paper:** *Comparative Analysis of Machine Learning and Ensemble Models for Football Match Outcome Prediction Using Leakage-Safe Feature Engineering* — controlled comparison of feature representations, algorithms, time splits, calibration, and confidence filtering.

**Primary scope:** international football and club football across domestic leagues, domestic cups, league cups, super cups, continental competitions, and global club tournaments. The first club pilot is England plus connected European fixtures, followed by the five major European leagues and their cups. A **separate club predictor is a core development deliverable**, with release gated on data access and independent evaluation. Worldwide is an extensibility goal, not a verified coverage claim. UEFA Nations League is a national-team competition; UEFA Champions League, Europa League, and Conference League are club competitions.

---

## 2. Background and existing assets

### 2.1 Original FootIQ concept (from the supplied PDF)

The original ML proposal, prepared for a three-member student team (Bhanu, Neilsen, Preeti), was a **Football Performance Analytics & Match Prediction System**, branded **FootIQ**. It proposed:

- Player performance analysis and prediction.
- Player similarity and clustering.
- Team performance analytics.
- Win/draw/loss match prediction.
- ML analytics dashboard for model comparisons, PCA/t-SNE/UMAP and clustering quality.
- React frontend and FastAPI backend, using Python/Pandas/scikit-learn/XGBoost.
- Supervised model comparison (Logistic Regression, KNN, SVM, Decision Tree, Random Forest, XGBoost), regression (Linear/Ridge/Lasso), clustering (K-Means, DBSCAN, hierarchical), and dimensionality reduction.
- A focused literature survey/research paper on **leakage-safe match outcome prediction**, not an overly broad paper claiming novelty across every module.

The PDF recommended separating match-level and player-level datasets; its suggestions included Football-Data.co.uk for club results and StatsBomb Open Data for player/event analysis. These are **design recommendations**, not verified current coverage or licensing.

### 2.2 Verified World Cup prediction baseline

| Existing asset | Verified repository detail (execution limits below) | Integration approach |
|---|---|---|
| Historical results | 49,296 international matches, Nov 1872–2 Jun 2026 | Preserve source snapshots; audit exact row count/schema |
| Training sample | 25,235 matches, 4 Jan 2000–2 Jun 2026 | Reproduce filter and chronological split |
| Match model | v2.7 weighted ensemble: 50% Gradient Boosting, 30% Elo, 20% Logistic Regression, 0% Poisson | Keep artifacts, feature contract, calibration |
| Public prediction filter | v2.7 agreement gate; v2.8 confidence gate | Preserve abstention/“Pass” logic |
| Tournament simulation | Goal-model-based Monte Carlo; 50,000 runs; v2.13 completed-result locking | Keep distinct from 1X2 ensemble |
| StatsBomb archive | Metadata and processed summaries for 128 World Cup matches from 2018/2022 | Do not assume full raw events/360 are present |
| World Cup fixtures | OpenFootball 2026 structure, 104 fixtures, 48 teams | Verify revision and competition rules |
| Supplemental data | Public squad profiles, rankings, GDP/population references, API-Football, Open-Meteo/NWS | Track source, timestamp, value, and availability |
| Output format | CSV/Markdown reports, manual Python script runs | Retain for reproducibility; add DB/API/UI |
| Tests | 28 tests passed earlier in this chat | Preserve evidence and re-run before future refactoring |

**Interpretation safeguards:** Archived group-stage validation (34/52) and knockout advancement validation (25/30) must **not** be presented as 1X2 match accuracy. A final retrain on all available history is **not** a new out-of-sample performance claim. The public confidence gate may choose “Pass” for every fixture; abstention is valid, not a failure.

### 2.3 Existing repository, inspected locally

```text
world-cup-prediction-model/
├── .venv/
├── data/
├── docs/
├── outputs/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── README_SHARE.md
├── requirements-share.txt
├── SHARE_MANIFEST.sha256
└── project reference PDFs
```

**Audit evidence:** [current-state report](docs/architecture/CURRENT_STATE.md), `README.md`, `README_SHARE.md`, `requirements-share.txt`, source scripts, five test modules, processed CSVs, model/config files, dataset inventory and existing project PDFs. `README.md`, `.gitattributes`, and `docs/architecture/CURRENT_STATE.md` also exist beyond the inherited tree above. No `backend/`, `frontend/`, `database/`, `pipelines/`, `airflow/`, or Docker Compose implementation exists. Prior PDFs remain historical documentation; they do not prove planned platform features exist.

#### Verified runtime and data evidence (20 October 2026, earlier in this chat)

- Python 3.12.14 environment; pinned direct model dependencies plus `tzdata`; **28 tests passed**, including a second run before the earlier repository upload. No new execution of output-writing scripts is needed for this documentation update.
- Counted 49,296 processed international matches, 1872-11-30 through 2026-06-02; 104 World Cup fixtures and 48 teams; 128 StatsBomb matches and 256 team-event summaries.
- v2.7 artifact loaded and scored eight saved fixtures; v2.7 returned eight Passes; v2.8 returned one Model Lean and seven Passes. Training metadata reports 25,235 rows, 2000-01-04 through 2026-06-02; full retraining was not repeated.
- v2.13 completed 50,000 simulations using archived results; it uses **v2.3 team power**, not the trained v2.7 classifier. Windows default encoding caused a team-name mismatch; `-X utf8` resolved execution.
- v2.14 reproduced 34/52 group best reads and 25/30 knockout advancement calls from included records. These results were not independently checked against external match reports in this audit and are distinct targets.
- StatsBomb raw match metadata and 128 lineup files exist; raw events/360 directories are absent. Processed summaries do not make the complete raw event pipeline reproducible.
- `api_football_client_v24.py` implements caching, budget ledger, key loading, timeouts and limited retry handling. No `.env` existed when inspected; subscription entitlements, live access and quotas were not verified.

#### Implementation boundaries

| Capability | Actual state | Next integration need |
|---|---|---|
| Elo/form, model training and inference | Verified code; inference executed | Frozen baseline, warehouse adapter and parity tests |
| Temperature calibration and publishing gates | Verified existing | Preserve thresholds/versioning; evaluate any future challenger separately |
| v2.11/v2.12 lineup/confidence layers | Partial shadow workflows | Broader identity coverage, historical availability and evaluation |
| Player impact | Heuristic squad-derived ratings | Do not describe as future player regression or per-90 scouting dataset |
| Matchday snapshots and provider mappings | Partial CSV workflows | Canonical IDs, immutable lineage, generalized reconciliation |
| Club coverage | Isolated legacy club reports exist | No systematic club-season ingestion, trained club model or coverage guarantee |
| Database/orchestration/API/UI | Planned | PostgreSQL, Airflow, Docker, FastAPI and React implementation |
| Player clustering/similarity | Planned | Valid appearances/minutes data, cohorts, fitting/evaluation |

Audit concerns: historical Elo/form inputs stop at June 2, 2026; fixture refresh does not update them automatically. Historical categorical design currently derives column vocabulary from concatenated train/calibration/test frames; future candidates need train-fitted preprocessing without modifying the frozen artifact. A history deque capped at 20 means its `matches_prior` feature is not total lifetime appearances. The original share manifest is not a current repository checksum. Source licenses and account-specific capabilities remain unverified.

### 2.4 Core integration decision

Maintain separate concepts for:

- **National-team matches** versus **club matches**.
- **90-minute outcome** versus **extra-time/penalty shootout advancement**.
- **Match 1X2 classifier** versus **goal model used by the tournament simulator**.
- **Historical feature availability** versus **information discovered after a match**.
- **Descriptive player score** versus **independently validated future player-performance prediction**.
- **Data refresh** versus **ML retraining**.

---

## 3. Problem statement

Football data is scattered across historical match archives, competition feeds, player-event repositories, squad records, rankings, and third-party APIs. The sources vary in format, update frequency, naming conventions, completeness, and rights of use. As a result, it is difficult to maintain reliable cross-source analytics, generate up-to-date team/player features, or produce reproducible and leakage-safe predictions. FootIQ addresses these challenges by building a documented, automated football data pipeline and warehouse, developing statistically sound ML components, and exposing source-aware analytics and predictions through a user-facing application.

### 3.1 Project objectives

**Data Engineering objectives**

1. Ingest historical and new match/player/fixture data from permitted sources.
2. Preserve raw source snapshots, retrieval timestamps, hashes, and provenance.
3. Normalize competitions, teams, players, match statuses, scores, and provider IDs.
4. Load curated data into PostgreSQL with idempotent upserts and correction history.
5. Schedule workflows with Airflow, retries, monitoring, and freshness reporting.
6. Generate SQL analytics and reproducible point-in-time feature datasets.
7. Demonstrate data quality, incremental processing, failure recovery, and operational observability.

**ML objectives**

1. Reproduce the existing international 1X2 ensemble and evaluate it on historical holdouts.
2. Compare supervised algorithms and football-specific feature representations.
3. Estimate calibrated match outcome probabilities and support confidence-based abstention.
4. Analyze player performance with normalized, position-aware statistics.
5. Build player clustering and nearest-neighbor similarity recommendations.
6. Train player regression only if an independent and temporally valid target exists.
7. Preserve and integrate the existing World Cup simulator.
8. Document leakage controls, dataset coverage, reproducibility, and model limitations.
9. Train and evaluate a separate club model using cross-competition histories, season-aware contexts and held-out league/cup slices.

**Application objectives**

1. Provide a responsive React interface and typed/documented FastAPI routes.
2. Show match predictions, team trends, player comparisons, simulations, and evaluation metrics.
3. Display data freshness, source coverage, model versions, and uncertainty.
4. Provide separate, clear demonstrations for the DE and ML academic evaluations.

---

## 4. Scope, priorities, and non-goals

### 4.1 Must-have MVP

- Historical international match backfill into PostgreSQL.
- Canonical teams, matches, competitions, source IDs, and ingestion run tables.
- Reliable incremental fixture/result updates for **supported** competitions.
- Data quality checks, correction handling, and Airflow DAGs.
- Existing international ensemble integrated with time-safe warehouse features.
- Existing World Cup simulator accessible through a documented interface.
- One country pilot covering league, domestic cups and linked continental fixtures; expand to all five target countries with declared coverage gaps.
- Separately trained club 90-minute model, released only after temporal validation; separate knockout advancement design.
- Competition explorer, standings, ties/brackets and cross-competition team analytics; viable player subset.
- Player clustering/similarity on a sufficiently complete and comparable cohort.
- JavaScript/JSX React/FastAPI app with the fourteen pages defined in section 13.
- Automated tests and reproducible setup/documentation.

### 4.2 Should-have

- Club-team analytics for all five named leagues.
- Position-aware player profiles with per-90 metrics and similarity explanations.
- Chronological comparison of multiple match classifiers.
- Calibration, abstention-coverage, and model evaluation dashboards.
- Independent player performance regression where a valid target is available.
- Source freshness alerts and historical correction replay.

### 4.3 Could-have, only if justified

- Additional independently evaluated club models or competition-specific simulation engines beyond the pilot.
- Apache Spark event-processing benchmark on sufficiently large event data.
- Player xG/xA, detailed tactical visualizations, and 360 data if permitted.
- Squad-aware pre-match features with reliable historical availability.
- Live match event streaming via Kafka if a true event feed and use case exist.
- Public hosting, mobile/PWA, multilingual UI, advanced model monitoring.

### 4.4 Explicit non-goals

- Guaranteed real-time coverage of every country, league, player, and competition.
- Fabricated or silently estimated missing player statistics.
- Guaranteed accurate predictions or gambling recommendations.
- Automatic retraining after every new match.
- Treating post-match statistics as pre-match model inputs.
- Implementing every syllabus algorithm as a separate production feature.
- Overwriting the current model/repository before its baseline is verified.

---

### 4.5 Detailed competition coverage and rollout

All entries below are **planned target coverage**, except the audited international archive and World Cup snapshot. Exact seasons, genders, levels, qualifiers and statistical depth must be recorded in a capability registry before enabling ingestion or a UI feature. Naming a competition is not proof of provider access.

| Domain/country | Competitions targeted | Rollout and acceptance boundary |
|---|---|---|
| International/global | FIFA World Cup, World Cup qualifiers, international friendlies | Preserve existing archive; verify each edition and result semantics before refreshing |
| International/Europe | UEFA European Championship, qualifiers, UEFA Nations League | Separate competition identities and editions; Nations League is not club football |
| International/Americas | Copa América and qualifiers where supported | Validate confederation/edition scope and source coverage |
| International/Africa and Asia | AFCON, AFC Asian Cup, associated qualifiers | Coverage verified per edition; other international competitions added through registry |
| England | Premier League, FA Cup, EFL Cup, Community Shield | First club pilot; lower-division opponents need identities and histories or explicit missing-history flags |
| Spain | La Liga, Copa del Rey, Supercopa de España | Expansion after pilot; rules and participants verified per season |
| Germany | Bundesliga, DFB-Pokal, domestic super cup | Same seasonal rules contract; no invented league-cup coverage |
| Italy | Serie A, Coppa Italia, domestic super cup | Same coverage and rule verification |
| France | Ligue 1, Coupe de France, domestic super cup | Historical league cups only for editions that actually existed and are covered |
| European clubs | UEFA Champions League, Europa League, Conference League, UEFA Super Cup | Full verified editions, not just five-country teams; include opponents/qualifiers or disclose exclusions |
| Global clubs | FIFA Club World Cup, FIFA Intercontinental Cup | Independent editions/formats and match-level access checks |
| Future South America | Copa Libertadores, Copa Sudamericana | Milestone 11, permission and data gated |
| Future Asia/Africa/other | AFC Champions League competitions, CAF club competitions, other continental/domestic tournaments | Provider and official rules verification; no blanket current coverage promise |

**Coverage levels:** L0 catalog-only, L1 fixtures/results, L2 team statistics/standings, L3 player appearances/statistics, L4 event analysis. Record each competition-season-source-metric capability independently. Predictive eligibility is a separate evaluated flag; L1 coverage does not automatically imply model readiness. Pilot historical season window is **TBD after source verification**, not a fabricated number of seasons.

**Extensibility:** register a new country/competition/season, approved source mapping and ruleset without modifying the core match schema. A new format may require a tested rules-engine plugin. Lower divisions, reserves/youth and women's teams must not collapse into similarly named senior men's clubs.

## 5. Users and functional requirements

### 5.1 Personas

- **Fan:** browses teams, players, fixtures, probabilities, and World Cup scenarios.
- **Student analyst:** compares model metrics, feature importance, and player clusters.
- **Data engineer:** inspects DAG status, source freshness, duplicates, and corrections.
- **Faculty evaluator:** runs repeatable DE and ML demonstrations, checks evidence and reports.
- **Maintainer/admin:** configures providers, runs backfills, reviews unresolved identities, promotes models.

### 5.2 User stories and acceptance

| ID | User story | Expected behavior |
|---|---|---|
| FR-01 | Search a national team or club | Show entity type, competition context, recent results and available metrics |
| FR-02 | Compare two teams | Use comparable windows and label missing statistics |
| FR-03 | View a match prediction | Show 1X2 probabilities, timestamp, model version, confidence/Pass |
| FR-04 | Inspect a player | Show appearances, minutes, per-90 statistics and source coverage |
| FR-05 | Find similar players | Return comparable-role neighbors, distances, cluster labels and caveats |
| FR-06 | Inspect tournament scenarios | Show locked results, simulation seed, runs, and advancement probabilities |
| FR-07 | Explore model evaluation | Show chronological splits, baselines, calibration and confusion matrix |
| FR-08 | Monitor ingestion | Show source status, DAG runs, freshness, row changes and errors |
| FR-09 | Re-run a historical batch | Produce no duplicate canonical facts; record a new audit run |
| FR-10 | Correct a historical result | Record the correction and rebuild affected downstream chronological features |
| FR-11 | Explore a competition edition | Filter country, domain, season, stage and coverage; display source/as-of metadata |
| FR-12 | View standings | Apply that edition's points/tie-break/deduction rules and identify official versus calculated tables |
| FR-13 | Inspect a knockout bracket | Separate leg scores, aggregate, penalties and advancing team; unresolved ties remain unresolved |
| FR-14 | Review a club across competitions | One canonical club identity; all-competition and competition-specific form/fixture views |
| FR-15 | Predict a club match | Use only an approved club model, with separate 90-minute and advancement targets |

### 5.3 Non-functional requirements and measurement

| Requirement | Planned acceptance evidence |
|---|---|
| Reproducibility | Snapshot hashes, exact dependency lock, seed and feature/model version reproduce fixed examples |
| Reliability | Interrupted import retries safely; failed provider fetch leaves last verified data available |
| Integrity | Unique source keys, FK constraints, transaction boundaries, correction revisions and quarantine tests |
| Temporal correctness | UTC storage with original precision/timezone retained; event time and availability time checked independently |
| Performance | Pagination and bounded queries; document measured latency/import time on a named machine and dataset; set budgets after pilot benchmarks |
| Maintainability | Shared testable Python ETL modules; Airflow only orchestrates; source adapters isolated from business rules |
| Observability | Run IDs, counts, source freshness, failure categories and actionable alerts; no credentials in logs |
| Usability | Responsive keyboard-accessible JSX interface, labeled charts, empty/error/stale states and no fabricated data |
| Portability/security | Documented Docker startup, isolated test/dev DBs, least privilege and admin protection |

---

## 6. Dataset strategy: historical, current, player, and context

### 6.1 Source inventory

| Source | Intended information | Current state | Update mechanism | Important limitation |
|---|---|---|---|---|
| Existing international results archive | Dates, teams, score, tournament, venue/context | **EXISTING (reported)** | One-time backfill + scheduled reconciliation | Confirm original license, data quality, and latest coverage |
| StatsBomb Open Data | Matches, lineups, events, selected 360 data | **PARTIAL EXISTING** (processed metadata); expansion planned | Release check and allowed JSON ingestion | Not complete across all competitions/players; attribution required |
| OpenFootball | Fixtures, results, competition structure | **EXISTING (reported)** | File/repository version diff | Coverage and corrections depend on maintainers |
| Football-Data.co.uk | Potential domestic results/statistics | **CONDITIONAL / permission gate** | No automated ingestion until approved | Current source page restricts automated/data-training use; see section 6.4 |
| API-Football | Fixtures, statuses, results, player stats, lineups, squads | **PARTIALLY USED (reported)**; expansion planned | API polling with quotas and cursors | Coverage, historical access, rate limits, pricing, and reuse rights vary |
| Public squad tables | Squad membership and basic profiles | **EXISTING (reported)** | Authorized feed or documented manual snapshot | Unreliable for automatic worldwide transfer coverage |
| FIFA rankings | National-team ranking snapshots | **EXISTING (reported)** | On official release | Historical snapshot must predate the prediction |
| Open-Meteo / NWS | Forecast/weather context | **EXISTING (reported)** | Fixture-based refresh | Forecast availability, venue coordinates, and temporal cutoff |
| World Bank indicators | Country-level context | **EXISTING (reported)** | Annual/as published | Experimental; avoid spurious or ethically questionable inference |
| Additional licensed player source | Club season/player stats where open data is insufficient | **CONDITIONAL** | Contract/provider-specific | Required for broad current player coverage |

**Source URLs for investigation (not blanket permission to redistribute):**

- StatsBomb Open Data: https://github.com/statsbomb/open-data
- OpenFootball: https://github.com/openfootball
- Football-Data.co.uk: https://www.football-data.co.uk/
- API-Football: https://www.api-football.com/
- Open-Meteo: https://open-meteo.com/
- FIFA: https://www.fifa.com/
- World Bank: https://data.worldbank.org/

### 6.2 Coverage strategy

**International layer:** retain worldwide national-team historical results, 2026 World Cup fixtures and results, and national-team match predictions. Label men's/women's, senior/youth, friendly/competitive, and regulation-time semantics correctly based on actual source coverage.

**Club layer:** England pilot across league/cups/European participation, followed by five-country and complete European-edition coverage. Include cross-border opponents and lower-tier cup participants; missing history must be measured rather than silently replaced with top-flight coverage. Preserve club and national identities separately. Club model development is required; release remains conditional on independent evaluation.

**Player layer:** StatsBomb events provide rich analysis for selected competitions, but not universal coverage. Where event-level data is absent, display available match/season aggregates only. Show source coverage by player, season, competition, and metric. A missing tackle count is **unknown**, not necessarily zero.

### 6.3 Provenance contract

Each dataset/provider must have a record of:

- Publisher, URL, access method, licensing/terms, attribution.
- Competition/season/gender/level coverage.
- Earliest/latest record and latest provider update.
- Retrieval timestamp, original file hash, schema version, API parameters.
- Redistribution and caching restrictions.
- Allowed update frequency, API quota and cost.
- Known missing fields, quirks, corrections, and quality tests.

**Never commit** credentials, personal tokens, proprietary provider payloads, or files whose redistribution is disallowed. Keep raw snapshots in appropriately ignored/local storage, with a reproducible manifest.

### 6.4 Dataset feasibility and detailed coverage matrix

**Evidence policy:** local facts are independently distinguishable from publisher descriptions and account-specific access. Provider pages were reviewed on 20 October 2026; this is not an account entitlement test or legal clearance. Never infer all-country, all-season or all-player coverage from a provider name. No new datasets were downloaded for this planning task.

| Provider | Competition scope and historical seasons | Match statistics | Player statistics | Fixtures/live | Access/quota and licensing | Planned ingestion | DE suitability | ML suitability/status |
|---|---|---|---|---|---|---|---|---|
| Existing international archive | Local 49,296 scored matches, 1872-11-30–2026-06-02; edition/competition breakdown to audit | Score, date, teams, tournament, neutral/context; not a complete shot/xG feed | Separate goalscorers/shootouts files; no universal minutes/actions | Static snapshot; no confirmed automated upstream sync | Original publisher chain/license needs verification; no network quota for local backfill | One initial import, then approved source reconciliation | Strong pilot for validation, identity, idempotence and chronological replay | Existing model foundation; score semantics/date precision still require audit |
| StatsBomb Open Data | Locally 2018/2022 World Cup metadata/lineups; remote competition-season catalog must be checked for every new cohort | Processed 256 team-match event summaries locally; remote selected-match events possible | Lineups local; rich event-derived player features depend on permitted event access and minutes reconstruction | Release snapshots, not a guaranteed live feed | Publisher repository describes selected competition data and attribution; inspect full license; no invented quota | Weekly revision check; selective allowlisted imports | Nested JSON/event normalization and provenance | Selected cohort analysis/clustering; not universal live player coverage |
| OpenFootball | Local 2026 World Cup, 104 fixtures/48 teams; other repos/seasons unverified | Results/schedules where published; do not presume advanced stats | No broad player-statistics capability verified | File/repository revisions; not promised real-time | Check exact repository license, revision and hosting limits | Weekly diff plus pre-event checks where permitted | Useful fixture/result adapter | Result history if validated; insufficient alone for player ML |
| Football-Data.co.uk | Publisher describes historical European domestic league files; specific pilot seasons and cup coverage NOT verified | Publisher describes results, selected match stats and odds with varying availability | Player-level dataset not verified | Historical/current files; no verified live service entitlement | Current page limits intended use to private individuals and excludes automated/data-training products. **Blocked for assumed ML/automated ingestion until permission or suitable terms confirmed**; free access is not blanket reuse permission | No scheduled ingestion until permission; then approved frequency only | Potential seasonal CSV exercises if permitted | Do not choose as default training source without clearance; alternative required if denied |
| API-Football | Existing code queries selected fixtures; requested leagues/cups/continents and seasons must be probed using the actual account | Fixture/status/score code exists; per-league statistics flags require validation | Lineup code exists; appearance/statistics/transfers depth and history unverified | Planned primary candidate for fixtures/statuses, conditional on account access | Personal key and subscription/coverage check required. Current scripts' 100/day limit with 15 reserved is a local policy, **not verified account quota** | Fixtures ~6h; matchday 15–30m only within measured budget; final reconciliation next day | Main candidate for quota-aware incremental/correction workflow | Club results/history and optional player features only after capability verification |
| Public squad/player snapshots | Local 2018/2022/2026 squad HTML snapshots; not a complete league-season appearance archive | Squad context rather than full match stats | Names, caps, age/club/goals where parsed; heuristic ratings, not licensed future targets | No reliable worldwide live transfer lifecycle | Verify page/source terms and attribution; prefer approved stable feeds | Manual/release-based snapshots or licensed refresh | Identity and membership examples | Descriptive prior only; not sufficient for per-90 prediction/clustering claims |
| FIFA ranking snapshots | Local ranking HTML reference; historical release series unverified | National-team rank context only | None established | Ranking releases, not fixtures/live | Official terms and reliable history/access must be checked | On approved release | Provenance/release-time exercise | Optional national-team pre-match feature only if known at cutoff; not club ranking |
| Open-Meteo/NWS weather | Existing fixture-coordinate integration; historical forecast availability and geographic suitability unverified | Weather context, no football match stats | None | Forecast refresh; not football updates | Confirm service terms, attribution, request policy and historical forecast access; no quota assumed | ~1h near supported fixture within permitted budget | External enrichment/fallback example | Conditional; archived forecast must predate prediction; observed weather cannot substitute silently |
| World Bank WDI | Local GDP/population JSON; country/year coverage to reconcile | Macro context only | None | Annual/as released | Preserve indicator metadata and applicable attribution; verify dataset-specific terms | Annual/release-based | Optional batch enrichment | Low-priority macro prior; not a club-strength substitute |
| Additional approved club/player feed | Provider, competitions and seasons TBD if above sources cannot meet scope | Must verify score semantics/statistical definitions | Must verify minutes, roles, completeness and use rights | Contract-specific | Cost, retention, model-training rights and display rights must be approved before use | Contract-specific | Conditional gap filler | Required if player/club training cohorts otherwise insufficient |

Publisher references: [StatsBomb Open Data](https://github.com/statsbomb/open-data) (currently redirects to Hudl's repository), [Football-Data source page](https://www.football-data.co.uk/data.php), [API-Football documentation](https://www.api-football.com/documentation-v3), [OpenFootball repositories](https://github.com/openfootball). API documentation was not machine-readable in this review; precise endpoint capabilities remain unverified. FIFA/weather/World Bank rights and live access were not newly verified.

### 6.5 Verification work package and source decision gate

For every proposed competition-season, record provider competition/season IDs, min/max dates, expected/received fixtures, stage coverage, final-score semantics, player/statistic field availability, null rates, timestamp precision, rights, revision/hash and tested access date. Distinguish qualifying rounds from main stages and full seasons from selected matches.

Use a small permitted sample first. Test pagination, malformed payloads, timeout/429 handling and actual account limits. Estimate daily calls as discovery + active-fixture polls + details/lineups + reconciliation + reserve; configure scheduler concurrency from that budget. Store credentials only locally. Mark each source **approved**, **restricted**, **unverified**, or **rejected** with reasons. If coverage or permission fails, substitute an approved source or display unavailable; do not fabricate or scrape around restrictions.

---

## 7. Automatic data updates: exact behavior

### 7.1 Proposed schedule (not yet deployed)

| Job | Suggested cadence | Outcome |
|---|---|---|
| Fixture discovery | Every 6 hours | New, postponed, rescheduled, and changed fixtures |
| Matchday status | Every 15–30 minutes, within provider quota | Kickoff/live/final status and score |
| Final-result reconciliation | On confirmed final + next day | Official 90-minute result and corrections |
| Player match statistics | After final and next-day recheck | New appearance/event records |
| Squad/transfer refresh | Daily or weekly | Effective-dated player-team memberships |
| Public repository updates | Weekly | Newly released match/event/fixture files |
| Elo/form feature rebuild | After accepted result changes | Updated team ratings and rolling features |
| Player profile aggregates | Daily | Per-90 and season aggregates |
| Clustering refresh | Weekly or after adequate new sample | New cluster/similarity version |
| Prediction refresh | On fixture/feature changes | Future-match probabilities and gate decisions |
| Model candidate retraining | Monthly/manual, evaluation-gated | Candidate artifact, never automatic blind promotion |
| World Cup simulations | After relevant confirmed results/rules changes | New versioned simulation snapshot |
| Data quality monitor | Daily and after ingestion | Freshness, missingness, duplicates, anomalies |

Actual cadence must be reconciled with API plan quotas, costs, and provider terms before deployment.

### 7.2 Match lifecycle example

1. Airflow queries a fixture source and receives a provider-specific fixture ID.
2. The extractor saves the raw response, retrieval timestamp, provider, hash, and run ID.
3. The normalizer converts date/time to UTC, maps competition and team IDs, and records match status.
4. Validation checks score format, status, identities, season, and duplicates.
5. The loader upserts the canonical fixture; a retry does not create a second match.
6. On official **final** status, regulation-time result becomes eligible for match-outcome facts.
7. Any extra time, penalties, and advancement winner are stored **separately**.
8. Chronological Elo/form features are updated. A correction to an older result triggers replay of dependent later features.
9. Future fixture predictions are regenerated with the current **pre-kickoff-available** feature snapshot.
10. The dashboard displays result, model version, feature timestamp, source, and last refresh.
11. A follow-up reconciliation detects amended scores/statistics and records change history.

### 7.3 Player lifecycle example

1. Resolve player using stable canonical ID and source-ID mapping; never rely on name alone.
2. Fetch match appearance, minutes, role/position, and available actions.
3. Validate against match/team context; insert/update appearance and event facts.
4. Recompute player season and per-90 aggregates with minutes thresholds.
5. Preserve transfer history using `valid_from`/`valid_to` membership records.
6. Refresh similarity/clustering on a controlled cadence; version resulting profiles.
7. Mark unavailable event metrics as unavailable rather than inventing them.

### 7.4 Reliability and correction policy

- **Idempotency:** unique provider/source keys and deterministic canonical mappings.
- **Retries:** exponential backoff and API quota awareness; no uncontrolled retry storms.
- **Quarantine:** unresolved entities and malformed records do not silently contaminate gold tables.
- **Correction log:** track previous/new values, source, retrieval time, affected features.
- **Watermarks:** incremental extraction cursors per provider and competition.
- **Late data:** bounded lookback windows and replay jobs.
- **Freshness:** separate `source_updated_at`, `fetched_at`, `processed_at`, `data_as_of`.
- **Failure behavior:** retain last verified values, display staleness, and do not claim live status.
- **Reproducibility:** historical source snapshots must support reconstructing what was known at prediction time.

---

### 7.5 Incremental state, corrections and prediction immutability

Track a watermark per source/competition/season/endpoint. Prefer provider update cursors when supported; otherwise use bounded date lookbacks and periodic seasonal reconciliation. Advance watermarks only after successful transactional loads. Hashes permit no-op detection; retries record attempts without duplicating facts. Use bounded exponential backoff with jitter and provider retry guidance; budget exhaustion produces a visible deferred run.

Postponed/cancelled/abandoned/awarded fixtures are distinct statuses. A changed kickoff does not create a new match when stable source identity persists; ambiguous reschedules require identity review. Awards, replays and void matches follow a season ruleset and explicit training eligibility policy. Unknown regulation scores remain null rather than being inferred from final-after-penalties totals.

Keep append-only fact revisions with event time and availability/known time. Historical corrections trigger chronological replay from the earliest affected match for both sides and downstream opponent features. Distinguish **as-known** reconstruction from **latest-corrected** retrospective analysis. Late backfills were not necessarily known to the original forecaster. Published predictions remain immutable; new revisions link to old ones. Date-only matches retain their precision; apply conservative same-day exclusion rather than inventing kickoff times.

Player appearances and transfers are separate workflows. Support concurrent club/national-team membership with effective dates and membership type. Aggregate only verified minutes/actions; preserve definitions/source versions. Identity corrections rebuild affected aggregates/cohorts.

## 8. High-level system architecture

```text
Historical CSV/JSON    StatsBomb/OpenFootball    Club CSV feeds    Football APIs    Weather
       \                     |                      |               |              /
        +--------------------+----------------------+---------------+-------------+
                                             |
                                  Apache Airflow DAGs
                                             |
                       Extract -> Validate -> Normalize -> Resolve IDs
                                             |
                            Raw snapshots + ingestion manifests
                                             |
                              PostgreSQL staging / silver
                                             |
                       Canonical matches / teams / players / events
                                             |
                             Gold analytics + feature snapshots
                               /                |               \
                         SQL analytics    ML inference/train   World Cup simulator
                               \                |               /
                                +----------- FastAPI ---------+
                                              |
                                         React FootIQ
                                              |
                              Fans / Analysts / DE and ML demos
```

**Environment:** Docker Compose for PostgreSQL, Airflow, backend, and optional Streamlit pipeline-monitoring app; React/Vite development server. Airflow metadata must be isolated from football analytical schemas/databases.

**Design boundary:** Airflow orchestrates reusable Python modules; ETL business logic must be independently callable and testable without Airflow.

---

## 9. Data warehouse and schema design

### 9.1 Layers

- **Bronze/raw:** immutable or versioned provider files/responses with checksums and extraction metadata.
- **Silver/staging:** typed normalized rows, validated identities, deduplicated records, provider mappings, quality flags.
- **Gold/marts:** analytics-ready facts/dimensions, historical ratings, player per-90 aggregates, model feature snapshots, predictions.

These are **logical** layers; they may be implemented as PostgreSQL schemas plus raw files/object storage.

### 9.2 Proposed tables

| Table | Fields (illustrative) | Constraint/usage |
|---|---|---|
| `sources` | `source_id, name, url, license, terms_checked_at` | Provenance |
| `ingestion_runs` | `run_id, source_id, start_at, end_at, status, counts, error` | Operations |
| `raw_objects` | `object_id, source_id, external_key, fetched_at, sha256, storage_uri` | Versioned raw snapshots |
| `competitions` | `competition_id, name, type, country, gender, level` | National/club and competition scope |
| `seasons` | `season_id, competition_id, label, start_at, end_at` | Competition seasons |
| `teams` | `team_id, name, team_type, country_code` | National vs club |
| `players` | `player_id, display_name, birth_date_nullable, nationality_nullable` | Stable player identity |
| `provider_entity_ids` | `source_id, entity_type, external_id, canonical_id, confidence` | Provider mapping |
| `player_team_memberships` | `player_id, team_id, valid_from, valid_to, source_id` | Effective-dated transfer history |
| `matches` | `match_id, competition_id, season_id, kickoff_utc, side_a_id, side_b_id, status, venue_id` | Canonical match |
| `match_results` | `match_id, regulation_a/b, extra_time_a/b, penalties_a/b, advancing_team_id` | Do not mix score semantics |
| `team_match_stats` | `match_id, team_id, shots, possession, passes, fouls, ...` | Nullable if not covered |
| `player_appearances` | `match_id, player_id, team_id, minutes, position, goals, assists, ...` | Unique appearance |
| `player_events` | `source_event_id, match_id, player_id, event_type, time, x, y, payload` | Conditional event coverage |
| `team_ratings_history` | `team_id, match_id, elo_before, elo_after, rating_version` | Replayable chronology |
| `team_feature_snapshots` | `team_id, cutoff_utc, feature_version, rolling_form, rest_days, ...` | Point-in-time features |
| `player_feature_snapshots` | `player_id, cutoff_utc, scope, feature_version, per90_metrics` | Player analytics/ML |
| `predictions` | `fixture_id, predicted_at, model_version, p_a, p_draw, p_b, decision` | Sum to 1; audit |
| `simulation_runs` | `run_id, created_at, seed, iterations, model_version, fixture_snapshot` | Reproducible tournaments |
| `model_registry` | `version, dataset_hash, train_cutoff, metrics_uri, artifact_uri, status` | Model lineage |
| `quality_checks` | `run_id, table_name, check_name, passed, details` | Quality history |

### 9.2.1 Competition-aware extensions (planned)

| Table/module | Additional contract |
|---|---|
| `countries`, `confederations`, `venues` | Geographic context separate from identity; neutral venues do not imply home advantage |
| `competition_editions` | Competition + season + gender/level + pinned format/rules version |
| `edition_participants` | Team membership and entry/exit stage; cup participants need not be top-division clubs |
| `stages`, `rounds`, `groups`, `group_memberships` | Ordered, edition-scoped relationships; league, league-phase, group and knockout formats |
| `competition_rulesets` | Immutable version/hash, official source, points/tie-breaks, legs, ET/penalty policy and qualification slots |
| `knockout_ties`, `tie_legs` | Participants, stage/round, leg order, matches, aggregate and advancement state; explicit byes/replays/awards |
| `progression_edges` | Winner/runner-up/seed source slot → destination slot; unresolved slots are not fake teams |
| `standings_snapshots`, `standings_rows`, `points_adjustments` | Edition/stage/group/as-of/ruleset; official versus calculated origin; deductions with provenance |
| `fact_revisions`, `field_provenance` | Old/new values, effective/known timestamps, source priority and conflict resolution reason |
| `ingestion_watermarks`, `quarantine_records` | Resume state, last success, reviewable invalid/unresolved records |
| `source_capabilities`, `metric_definitions` | Provider/edition/season/metric availability, precision, rights, freshness and definitions |
| `feature_builds`, `prediction_revisions` | Snapshot hashes, availability cutoff, domain/target; immutable superseding records |
| `simulation_results`, `pipeline_task_runs` | Team/stage probabilities; per-task attempts, counts, errors, duration |

Extend `matches` with edition/stage/round/group references, kickoff precision, neutral flag and optional tie-leg link. Define regulation as 90 minutes including stoppage; store extra-time goals separately, shootout scores separately, and match winner separately from tie qualifier. Retain original provider fields for audit. Aggregate scores are derived using the pinned ruleset and reconciled against authoritative advancement facts.

**Canonical identity:** Liverpool has one club ID across Premier League, FA Cup, EFL Cup and Champions League, but separate edition participation, standings and progression. IDs are opaque/stable; names alone are insufficient. Keep aliases/provider ID revisions. Provider mapping must enforce canonical entity reference integrity, not an unconstrained polymorphic ID.

**Rules:** verify official rules for each season, including historical away-goal policies where applicable, leg structure, replays, deductions and multi-team tie-breakers. League standings and knockout advancement are separate projections. Label provider-official versus calculated tables. Unknown rules block unsupported calculations instead of silently defaulting to current rules.

### 9.3 Analytics marts/views

- `mart_team_form`: rolling 5/10 results, goals, strength of opposition, cutoff.
- `mart_team_head_to_head`: dated prior meetings, explicitly descriptive.
- `mart_player_per90`: goals/assists/shots/passes/defensive actions, minutes thresholds.
- `mart_competition_results`: league/tournament statistics, with competition semantics.
- `mart_prediction_performance`: versioned prediction versus observed 90-minute outcome.
- `mart_source_freshness`: last successful sync, lag, quality, and source coverage.
- `mart_team_cross_competition`: all-competition/competition-specific form, rest and congestion with coverage flags.
- `mart_standings`: league/group/league-phase standings with pinned rules, deductions and cutoff.
- `mart_knockout_progression`: ties, legs, aggregate, penalties and unresolved qualifiers.

### 9.4 Database integrity rules

- Provider source keys unique per entity type; canonical match identity resolved carefully.
- Team A and Team B must differ; valid competition/season foreign keys.
- Nonnegative score integers; nullable scores before completion.
- Player minutes nonnegative and consistent with competition/match type.
- Preserve corrections instead of silently rewriting historical provenance.
- Index competition/season, kickoff, team-match, player-match, external IDs, and feature cutoff.
- Use `EXPLAIN ANALYZE` and realistic benchmark datasets before claiming index speedups.

---

## 10. Airflow DAGs and ETL modules

### 10.1 Proposed DAGs

| DAG | Core tasks | Trigger |
|---|---|---|
| `historical_backfill` | discover → fetch → hash → parse → validate → map → load → audit | Manual/batch |
| `fixture_refresh` | API poll → snapshot → normalize → upsert → QA | 6-hour schedule |
| `result_reconciliation` | final-score fetch → corrections → upsert → feature replay | Matchdays |
| `player_stats_refresh` | fetch appearances/events → validate → load → aggregates | Daily/post-match |
| `open_data_sync` | source revision diff → allowed downloads → parse → load | Weekly |
| `feature_snapshot_build` | select cutoff → rolling features → leakage tests → publish | Data-dependent |
| `prediction_refresh` | load approved model → features → infer → calibrate → gate → persist | Fixture/feature-dependent |
| `quality_monitor` | freshness → duplicates → coverage → anomalies → alert | Daily |
| `candidate_model_training` | snapshot → split → train → evaluate → register | Manual/monthly gated |
| `membership_refresh` | approved squads/transfers → identity → effective dates → reconcile | Daily/weekly, coverage gated |
| `competition_projection_refresh` | results/rules → standings/ties → compare official snapshot | Relevant result/correction |
| `player_aggregate_refresh` | verified appearances → per-90/season/role cohorts → coverage | Daily/post-match |
| `similarity_refresh` | cohort → scale/cluster/neighbors → evaluate → version | Weekly/sample threshold |
| `simulation_refresh` | results/rules → pinned simulator → new run | Relevant result/rules changes |

### 10.2 Quality checks

- Required keys, valid dates/time zones, expected status values.
- Duplicate canonical fixtures and provider IDs.
- Score and match status consistency; shootout separation.
- Missing values and schema drift by provider/season.
- Unresolved player/team identity and conflicting provider data.
- API quota errors, stale data, and unexpected row-count changes.
- Feature observation time and **availability time** not later than prediction cutoff.
- Probability outputs finite, each in `[0,1]`, summing approximately to 1.
- Deterministic backfill/replay results and correction lineage.

### 10.3 Proposed ETL package layout

```text
pipelines/
├── extract/           # provider adapters, pagination, caching, quotas
├── normalize/         # timezones, score semantics, units, schemas
├── validate/          # required fields, ranges, schemas
├── identity/          # team/player/provider ID resolution
├── load/              # transactions, staging, upserts
├── reconcile/         # amended scores and late-arriving facts
├── features/          # cutoff-aware team/player features
└── quality/           # tests, freshness, completeness
```

---

## 11. Machine Learning design

### 11.1 International match prediction

**Task:** predict regulation-time 1X2: Side A win, draw, Side B win. For neutral fixtures, do not incorrectly label Side A as a home team. Penalty-shootout winners and extra-time advancement are separate outcomes.

**Verified existing ensemble:** 50% Gradient Boosting + 30% Elo-derived probabilities + 20% Logistic Regression. Code applies component temperature scaling, weighted blending and ensemble temperature scaling; v2.7 and v2.8 publishing gates are separate layers. Preserve current artifact, calibration and decisions. Weather and player-event summaries are not part of the core trained classifier feature list.

**Pre-match features (subject to availability):**

- Elo before kickoff, Elo difference.
- Rolling last 5/10 results and goal statistics, computed only from earlier matches.
- Opponent-strength-adjusted form and competition context.
- Rest days and neutral/home context.
- Prior head-to-head information (with caution about sample size).
- Squad availability only from timestamped pre-match sources.
- Forecast weather only as known before prediction; never observed post-match weather for historical pre-match inference.

**Candidate comparison models:** frequency baseline, Elo-only, Logistic Regression, KNN, SVM, Decision Tree, Random Forest, Gradient Boosting, XGBoost. Optional Naive Bayes and AdaBoost for syllabus experiments. Do not claim all are currently trained.

**Evaluation:** chronological train/validation/test; optionally rolling-origin backtests; train-only imputation, scaling, encoding, PCA/feature selection, hyperparameter tuning, and calibration. Metrics: accuracy, balanced accuracy, macro F1, class precision/recall, confusion matrix, multiclass log loss, Brier score, calibration plots, and abstention coverage/selective risk.

**Confidence:** preserve “Pass” as a legitimate output; report both full-fixture performance and published-pick performance with their different denominators.

### 11.2 Club match prediction — separate track

Build a **separate club model** under `ml/match/club/`; preserve the international algorithms/artifact unchanged. Club pages provide analytics until an independently evaluated club model is approved.

**Eligible training rows:** verified regulation scores, canonical club/edition mapping, chronological availability and approved source rights. Define handling of promoted clubs, lower-division cup opponents, unseen clubs, neutral finals, awards, abandoned games and date-only records. Flag incomplete histories and evaluate abstention.

**Features:** pre-match Elo/strength, recent form and goals scored/conceded, home/away/neutral context, opponent strength, rest days, fixture congestion over declared windows, cross-competition histories, competition type, stage/leg and pre-second-leg aggregate position. Maintain all-competition and competition-specific windows. Missing cup history must not produce falsely complete workload metrics. Cross-country Elo comparability, bridging fixtures, league priors and cold starts require held-out tests.

**Candidates:** frequency and Elo baselines; Logistic Regression, SVM, Decision Tree, Random Forest, Gradient Boosting and XGBoost where appropriate. KNN remains an optional academic comparison. Fit imputation/scaling/encoding/PCA on training only; tune using forward/rolling-origin folds, calibrate on past calibration data and freeze the future test set.

**Targets:** predict 90-minute 1X2 separately from knockout advancement. Advancement needs verified tie state and ET/penalty semantics. Do not renormalize 1X2 outputs and describe them as a validated qualifier model. Disable unsupported targets.

**Evaluation:** accuracy, macro F1, class precision/recall, confusion matrix, log loss, Brier, calibration, selective risk/coverage and uncertainty. Slice by league/country, season, domestic cup, continental stage, neutral venue and unseen-team history. Release requires reproducibility, no temporal/target leakage, comparable baselines and approved validation evidence; no arbitrary accuracy guarantee. Never silently route clubs to the international model.

### 11.3 Player performance analytics and regression

**Descriptive metrics:** minutes, starts, goals, assists, shots, passing, defensive actions, xG/xA when available, and per-90 versions. Filter or flag players below a minimum minutes threshold; normalize by role and competition context.

**Regression decision gate:** only train a performance predictor after selecting a defensible, independently observed and temporally separated target (e.g., a provider rating for a future match, future multi-match contributions, or future minutes). A hand-crafted same-match weighted score is a **descriptive index**, not independently validated predictive ML.

**Candidate regression models:** Linear Regression, Ridge, Lasso; compare to historical-average baseline. Metrics: MAE, RMSE, residual analysis, time/season holdouts, and role-specific error.

### 11.4 Player clustering and similarity

- Construct player feature vectors from sufficiently complete comparable statistics.
- Use per-90 metrics, minimum playing time, role-specific cohorts, missingness policies.
- Scale features appropriately and inspect correlation/outliers.
- Compare K-Means, DBSCAN, optional hierarchical clustering.
- Evaluate silhouette, Davies–Bouldin, stability, and football interpretability.
- Use PCA for component analysis; t-SNE or UMAP for **visualization**, not proof that clusters are objectively real.
- Recommend nearest players using scaled-feature distance/cosine similarity within comparable cohorts; a shared cluster alone is not a complete similarity measure.
- Label archetypes such as “attacking creator” as analyst interpretations, not ground truth.

### 11.5 World Cup simulation

Keep the existing separate goal-based Monte Carlo simulator, verified at 50,000 runs. Support completed-result locking, competition rules, groups, knockout brackets, advancement and champion probabilities. Store simulation seed, iterations, model version, fixture snapshot, ruleset, and cutoff. Do not equate advancement success with match 1X2 accuracy.

The verified v2.3/v2.13 engine is not a generic competition simulator. Future league run-ins, group/league phases and domestic/continental brackets need rules-engine adapters and tests for seeding, tie-breaks and two legs. Preserve the World Cup baseline. A 1X2 classifier alone cannot generate scorelines needed for goal-difference tie-breaks; new simulation formats need an evaluated score model or documented alternative.

### 11.6 Feature refresh versus retraining

**New result → data update → Elo/form refresh → prediction refresh** using the currently approved model. **Retraining** happens only on a controlled schedule or manual request, producing a candidate artifact that is evaluated against the current model and promoted only if justified. Maintain rollback support and artifact hashes.

### 11.7 Model registry

Record model version, feature version, dataset snapshot/hash, training cutoff, code revision, hyperparameters, preprocessing pipeline, calibration method, metrics, serialization format, and deployment state. Never compare scores from different test periods without stating the differences.

---

## 12. Research and literature survey plan

**Working title:** *Comparative Analysis of Machine Learning and Ensemble Models for Football Match Outcome Prediction Using Leakage-Safe Feature Engineering*.

**Central research question:** How do football-specific feature engineering, dimensionality reduction/selection, and ensemble learning influence out-of-time football 1X2 prediction performance?

**Subquestions:**

- RQ1: Do pre-match engineered football features outperform basic pre-match statistics?
- RQ2: Does PCA improve or harm prediction relative to the full engineered feature set?
- RQ3: Which classifiers produce the best calibrated probabilities, not just top-1 accuracy?
- RQ4: How do chronological and random splits differ, and what leakage risks arise?
- RQ5: How does abstention affect coverage and selective accuracy?
- RQ6: Does cross-competition form/congestion improve club forecasts versus league-only histories, and what is the effect of missing cup history?

**Experiment matrix:**

| Experiment | Feature representation | Evaluation |
|---|---|---|
| E1 | Minimal pre-match baseline | Same chronological holdout |
| E2 | E1 + Elo/form/opposition/rest | Same chronological holdout |
| E3 | E2 + train-fitted PCA | Same chronological holdout |
| E4 | E2 + train-fitted feature selection | Same chronological holdout |
| E5 | Club league-only versus cross-competition form/rest/congestion | Same club future holdout; league/cup slices |

Freeze international and club datasets separately, including source revisions, exclusion counts, season boundaries and availability policy. Compare identical holdouts/tuning budgets. Report uncertainty and calibration, not just accuracy. Random-split comparisons are leakage sensitivity demonstrations, not production headline evidence. New literature verification remains future work.

Compare a controlled subset of Logistic Regression, KNN/SVM, Decision Tree, Random Forest, Gradient Boosting/XGBoost, and Elo baseline using the same time splits and tuning budgets. Record confidence intervals where feasible, calibration, data cutoffs, and ablation effects.

**Literature survey outline:** football prediction problem; Elo/Poisson statistical models; classification and ensembles; football-specific features; player/event data; PCA/feature selection; temporal leakage; calibration and abstention; limitations of public datasets; identified research gap.

**Research integrity:** original PDF citations are leads, not a verified bibliography. Check primary papers and accurate bibliographic metadata before final submission. Do not claim novelty merely from combining common tools; emphasize reproducible comparative evidence.

---

## 13. Backend and frontend

### 13.1 Technology stack

| Layer | Recommended tools | Why |
|---|---|---|
| Frontend | React + Vite + JavaScript/JSX, React Router | No TypeScript; actual API data and explicit coverage states |
| Backend | Python FastAPI + Pydantic | Native integration with Python ML/ETL |
| Database | PostgreSQL | SQL joins, indexes, constraints, analytics |
| ORM/DB access | SQLAlchemy / psycopg | Transactions, typed access |
| Data transforms | Pandas + NumPy | Practical for current scale |
| Orchestration | Apache Airflow | DAGs, retries, scheduling, logs |
| Visualization | Plotly/Recharts | Trends, calibration, clusters, comparisons |
| DE demo | Optional Streamlit + Plotly | Quick independent ETL/SQL demonstration |
| ML | scikit-learn + existing dependencies; XGBoost if selected | Experiments and deployment |
| Infrastructure | Docker Compose | Reproducible local multi-service environment |
| Testing | pytest, SQL tests, API tests, frontend tests | Functional and regression safety |
| Optional | Spark | Only for meaningful event-data benchmark |
| Deferred | Kafka | Only if actual streaming is implemented |

### 13.2 Planned application pages

| Page / planned JSX module | Actual data and interaction contract |
|---|---|
| 1. Overview Dashboard / `OverviewPage.jsx` | Supported competitions, coverage counts, recent/upcoming fixtures, last successful sync |
| 2. Competition Explorer / `CompetitionsPage.jsx` | Country/domain/edition filters, stages, coverage and available seasons |
| 3. Fixtures and Results / `FixturesPage.jsx` | Date/status/team filters, kickoff precision, postponements, regulation/ET/penalty labels |
| 4. League Standings / `StandingsPage.jsx` | Edition/stage/group, rules version, deductions, official/calculated origin |
| 5. Cup and Tournament Brackets / `BracketsPage.jsx` | Tie legs, aggregate, progression and unresolved slots; no invented qualifiers |
| 6. Team Profiles / `TeamPage.jsx` | Canonical club/nation identity, all-competition and filtered form, workload and history |
| 7. Team Comparison / `TeamComparisonPage.jsx` | Comparable windows, opponent/context filters, head-to-head and missingness |
| 8. Player Profiles / `PlayerPage.jsx` | Identity, effective memberships, appearances and metric coverage |
| 9. Player Performance Analysis / `PlayerPerformancePage.jsx` | Verified minutes/per-90 metrics; descriptive index clearly distinct from future prediction |
| 10. Similar Players / `SimilarPlayersPage.jsx` | Role/minutes cohort, distances, feature explanation and PCA/t-SNE/UMAP view |
| 11. Match Outcome Predictor / `PredictorPage.jsx` | Domain-routed approved model, 1X2, Pass, model version/cutoff; separate supported advancement |
| 12. World Cup Simulator / `WorldCupPage.jsx` | Locked results, stage/title odds, seed, iterations, snapshot and rules |
| 13. ML Analytics Dashboard / `MLAnalyticsPage.jsx` | Splits, baselines, confusion/calibration/class metrics, experiment and cohort versions |
| 14. Data Engineering Pipeline Dashboard / `PipelinePage.jsx` | Runs/tasks/errors, freshness, counts, quarantine and DAG links |

All routes/components are planned. Build a read-only competition/team/results slice first, then inference and operations views. Player pages integrate only when Milestone 10 supplies genuine data. Mock/synthetic values belong only in visibly labeled development fixtures and tests, never as production statistics.

**UI principle:** never display illustrative scores or unavailable stats as genuine results; mark demo/synthetic values visibly. Display “data unavailable” rather than inventing a number.

### 13.3 Proposed API routes

```text
GET  /api/health
GET  /api/data/sources
GET  /api/data/freshness
GET  /api/competitions
GET  /api/competitions/{competition_id}/seasons
GET  /api/editions/{edition_id}/stages
GET  /api/editions/{edition_id}/coverage
GET  /api/editions/{edition_id}/standings?stage_id=&group_id=&as_of=
GET  /api/editions/{edition_id}/bracket
GET  /api/ties/{tie_id}
GET  /api/teams?query=&type=
GET  /api/teams/{team_id}/matches
GET  /api/teams/{team_id}/analytics
GET  /api/teams/compare?team_a_id=&team_b_id=&from=&to=&scope=
GET  /api/players?query=&competition_id=
GET  /api/players/{player_id}
GET  /api/players/{player_id}/similar
GET  /api/players/{player_id}/performance
GET  /api/fixtures?from=&to=&competition_id=
GET  /api/predictions/{fixture_id}
POST /api/predictions/preview
GET  /api/world-cup/simulations/latest
POST /api/world-cup/simulations          # authenticated/admin
GET  /api/ml/experiments
GET  /api/ml/models
GET  /api/pipeline/runs
GET  /api/pipeline/quality
POST /api/admin/ingestion/run            # authenticated/admin
GET  /api/pipeline/quarantine            # authenticated/admin
GET  /api/jobs/{job_id}                  # access checked
```

For all API responses, include appropriate `as_of`, `source`, `coverage`, and `model_version` metadata. Protect expensive operations, credentials, admin endpoints, and provider licensing. Document API response shapes and error codes in OpenAPI.

**API contract details:** define Pydantic response schemas and version the API before a breaking release. Lists use bounded pagination and validated date/edition filters. Distinguish entity-not-found, unsupported coverage, stale-but-available and temporary provider/service failure. Metadata includes `fetched_at`, `data_as_of`, `known_at`, score semantics, ruleset and feature/model versions where applicable. Unknown values remain nullable with a reason. Prediction preview uses persisted, cutoff-safe features and does not train or make uncontrolled provider calls. Enqueue expensive simulations/backfills, return a job ID, bound iterations and enforce admin permissions; no synchronous full training from a public endpoint. Test CORS, error handling and SQL parameterization.

---

## 14. Proposed additive repository structure

**Do not move or delete existing directories until Milestone 1 audit and regression tests finish.**

```text
world-cup-prediction-model/
├── .venv/                         # existing; gitignored
├── data/                          # existing data/model artifacts
├── scripts/                       # existing research/model/simulation scripts
├── outputs/                       # existing reports
├── tests/                         # existing tests; extend
├── docs/
│   ├── architecture/
│   ├── data-sources/
│   ├── experiments/
│   ├── operations/
│   └── demos/
├── pipelines/
│   ├── extract/
│   ├── normalize/
│   ├── validate/
│   ├── identity/
│   ├── load/
│   ├── reconcile/
│   ├── features/
│   └── quality/
├── airflow/
│   └── dags/
├── database/
│   ├── migrations/
│   ├── seeds/
│   ├── sql/
│   └── tests/
├── ml/
│   ├── match/
│   │   ├── international/          # adapter around preserved research engine
│   │   └── club/                   # new training/features/inference; separate artifacts
│   ├── players/
│   ├── clustering/
│   ├── evaluation/
│   └── registry/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   └── schemas/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/                  # .jsx components, no .tsx
│   │   ├── components/
│   │   ├── api/
│   │   └── charts/
│   └── public/
├── dashboard/                     # optional Streamlit DE demo
├── config/
├── infra/
├── .env.example
├── docker-compose.yml
├── requirements-de.txt
├── PROJECT.md
└── README.md
```

**Migration strategy:** build adapters around existing script functions; compare old versus new predictions on fixed snapshots; refactor only after parity is demonstrated. Keep original CSV/Markdown reports as regression artifacts and a fallback.

**Additional planned modules:** `config/competitions.yaml`, `config/source_capabilities.yaml`, `pipelines/rules/`, `pipelines/analytics/`, `database/sql/standings.sql`, `database/sql/cross_competition_form.sql`, `ml/simulation/`, `docs/data-sources/COVERAGE.md`, `docs/operations/RECOVERY.md`, `docs/experiments/PROTOCOL.md`. These paths are design targets, not files created in this planning task. Preserve the legacy dependency environment; new API/ETL/ML dependencies should be isolated and locked during implementation.

---

## 15. Detailed twelve-milestone implementation roadmap

All work below is **planned**. Existing evidence reduces discovery work but does not waive acceptance tests. No implementation begins during this documentation task. Paths identify future files/modules to create or extend, not files already created.

**Dependency adjustments:** preserve the requested twelve-stage order. Milestone 3 uses a minimal standalone international importer; Milestone 4 generalizes it into adapters rather than waiting for a complete ETL framework. PostgreSQL must be available for Milestone 3 (a minimal local/dev container may be approved then); the full multi-service Compose/Airflow integration remains Milestone 8. International inference/simulator adapters are integrated alongside Milestone 7 to protect parity before the UI. Milestone 9 delivers the core app; player routes/pages become functional in Milestone 10. Evaluation protocols begin in Milestones 1–2 and tests run throughout, while Milestone 12 consolidates research and release evidence. Milestone 11 expansion is bounded by approved coverage; unsupported worldwide competitions remain catalog-only rather than blocking an honest pilot release.

### Milestone 1 — Repository audit and baseline preservation

- **Objective:** turn the verified research snapshot into a reproducible, non-destructive reference.
- **Existing dependencies:** scripts, raw/processed snapshots, v2.7 artifact, configs, five test modules, README and current-state audit; compatible local Python 3.12 environment already exists.
- **Files/modules:** extend `docs/architecture/CURRENT_STATE.md`; create `docs/architecture/BASELINE.md`, `docs/architecture/DEPENDENCIES.md`, `docs/operations/RISKS.md`, and a new dated manifest/dependency lock under `docs/baseline/`. Keep original share manifest unchanged.
- **Tasks:** inventory source/artifact/data files excluding secrets/caches; hash originals; capture exact dependency versions and command outputs; save small fixed inference/simulation fixtures and reference probabilities in a new location; map input/output dependencies; record default-encoding and preprocessing concerns without altering the frozen algorithms.
- **Technologies:** Python standard library, existing pytest/scikit-learn environment, SHA-256 and Markdown.
- **Tests:** existing 28 tests; artifact load/probability normalization; deterministic reference inference; simulator seed and locked-result checks. Run output-writing scripts only against a safe copied baseline when needed.
- **Deliverables:** baseline report, hashes, environment lock, regression examples, integration map and blocker register.
- **Acceptance:** originals unchanged by hash; baseline runs reproduce declared outputs/tolerances; current limitations and external verification gaps explicit.
- **Risks:** missing raw events, OS encoding, dependency mismatch, stale data, confusing repository metrics with independently verified results.
- **Gate to M2:** reproducible baseline or exact documented blocker; no model/data rewrite and no Git operation without separate authorization.

### Milestone 2 — Dataset verification and scope finalization

- **Objective:** approve a feasible country/competition/season/player scope and data contracts.
- **Dependencies:** M1 inventory; owner-provided account access if API verification is needed; current provider permission/coverage review.
- **Files/modules:** `docs/data-sources/COVERAGE.md`, `docs/data-sources/SOURCE_REGISTER.md`, `docs/architecture/DATA_DICTIONARY.md`, `docs/architecture/ERD.md`, `docs/experiments/PROTOCOL.md`, proposed `config/competitions.yaml` and `config/source_capabilities.yaml`.
- **Tasks:** verify small permitted samples; document score semantics, IDs, season depth, lower-tier cup opponents, qualifying rounds, player minutes, field missingness, account quota and training/display/redistribution rights; choose England pilot and exact historical window; approve source priority; specify entity and temporal contracts and season-specific rule evidence. Resolve Football-Data restrictions before selection.
- **Technologies:** publisher documentation, small JSON/CSV inspection, coverage tables and schema diagrams; no broad backfill before approval.
- **Tests:** sample parser contracts, field/season coverage, source-ID stability, page/response schema; quota-budget calculation and permission gate review.
- **Deliverables:** approved/unverified/rejected source matrix, scoped coverage levels, versioned contracts, ERD draft and experiment protocol.
- **Acceptance:** every enabled pilot capability has a confirmed source and rights or is visibly conditional; no guessed API quotas, season ranges or player metrics.
- **Risks:** inadequate cup/player history, licensing restrictions, API cost, partial editions and disconnected league ratings.
- **Gate to M3:** accepted canonical/score/time contracts and at least one permitted historical results source; deferred capabilities recorded.

### Milestone 3 — PostgreSQL schema and historical import

- **Objective:** establish a validated warehouse and safe historical international backfill.
- **Dependencies:** M1 baseline; M2 schema/source contracts; separately approved isolated dev/test PostgreSQL service.
- **Files/modules:** `database/migrations/`, `database/seeds/`, `database/tests/`, `database/sql/`, `pipelines/load/international_backfill.py`, DB configuration templates and data dictionary updates.
- **Tasks:** implement sources/runs/raw objects, canonical entities and provider mappings, editions/stages/ties/rules, matches/results/revisions; FK/unique/check constraints; staging-to-curated transactions; import existing international archive without editing it; preserve legacy IDs and reject/quarantine invalid records. Instantiate the competition-aware schema even if some tables are initially empty.
- **Technologies:** PostgreSQL, SQL, Python/Pandas, SQLAlchemy or psycopg; select and lock migration tooling during implementation.
- **Tests:** fresh schema creation, constraints, rollback, same-source rerun, concurrent duplicate attempts, source-to-staging-to-accepted/quarantine count reconciliation, UTF-8 names and score semantics.
- **Deliverables:** migrations, importer, seed metadata, count/reject audit and SQL smoke queries.
- **Acceptance:** repeated identical imports create zero duplicate canonical facts; accepted plus quarantined/excluded rows reconcile to inputs; original datasets/artifact unchanged.
- **Risks:** wrong score interpretation, name collisions, date precision, non-transactional partial loads.
- **Gate to M4:** stable schema, repeatable import and fixture-backed database tests.

### Milestone 4 — ETL pipelines and data validation

- **Objective:** generalize the importer into reusable adapters and ingest the club pilot.
- **Dependencies:** M2 approved samples/coverage, M3 warehouse and identity contracts.
- **Files/modules:** `pipelines/extract/`, `normalize/`, `validate/`, `identity/`, `load/`, `quality/`; adapter fixtures under `tests/pipelines/`; capability/competition configuration.
- **Tasks:** implement approved historical/public/API adapters; parse pagination and metadata; preserve raw hashes; normalize UTC/precision, regulation/ET/penalty fields and club IDs; load England league/cups and linked European histories with explicit gaps; quarantine unresolved teams, schema drift and invalid records; keep transformations callable without Airflow.
- **Technologies:** Python/Pandas, approved HTTP client, PostgreSQL and reusable schema validation.
- **Tests:** malformed JSON/CSV, pagination, renamed teams, accented names, missing fields, cross-source duplicates, lower-division opponent identity, status/score consistency and partial file failure.
- **Deliverables:** reusable adapter package, pilot dataset, quality/coverage reports and run lineage.
- **Acceptance:** each imported row traceable to source and run; invalid rows isolated; safe reruns; no false assertion of complete cup/player coverage.
- **Risks:** schema drift, mixed team levels, incomplete opponent history, source-field definition mismatch.
- **Gate to M5:** tested club pilot import and source-key/canonical identity resolution.

### Milestone 5 — Incremental updates and reconciliation

- **Objective:** make updates, late arrivals and corrections safe and replayable.
- **Dependencies:** M3 transactions/revisions, M4 adapters and accepted source quota.
- **Files/modules:** `pipelines/reconcile/`, `pipelines/features/`, watermark and revision loaders; `tests/pipelines/test_incremental.py`, correction/replay tests, `docs/operations/RECOVERY.md`.
- **Tasks:** maintain cursors/lookbacks; handle upcoming, rescheduled, postponed, cancelled and completed fixtures; append corrections; reconcile next-day finals; preserve last verified data on failure; replay chronological Elo/form from affected points; create immutable feature/prediction revisions. Implement skeleton membership/statistics update contracts for M10.
- **Technologies:** Python, PostgreSQL transactions, structured logging and source-budget policy.
- **Tests:** interrupted load before/after commit, duplicate events, older result correction, changed kickoff/provider mapping, out-of-order results, 429/network failure, date-only cutoff and late backfill availability.
- **Deliverables:** executable incremental/reconciliation CLI, revision history, safe replay, recovery runbook and freshness metrics.
- **Acceptance:** reruns are idempotent; watermarks advance only on committed loads; corrected downstream features reconcile; original published predictions remain unchanged; provider failure does not corrupt curated data.
- **Risks:** replay fan-out, false fixture merges, quota exhaustion, retrospective leakage.
- **Gate to M6:** demonstrable new-result/correction/recovery flow with temporal checks.

### Milestone 6 — Cross-competition analytics

- **Objective:** query club/national histories, standings and cup progression correctly.
- **Dependencies:** M4 pilot coverage, M5 verified result revisions, M2 edition rules evidence.
- **Files/modules:** `database/sql/cross_competition_form.sql`, `standings.sql`, `head_to_head.sql`, `knockout_progression.sql`; `pipelines/analytics/`, `pipelines/rules/`; rule fixtures/tests.
- **Tasks:** implement all-competition and filtered form, goals, home/away, rest/congestion and prior head-to-head; edition standings, deductions, tie-breaks, leg aggregates and qualifiers; compare calculated tables with authoritative snapshots; retain incomplete-history flags and unresolved paths.
- **Technologies:** SQL views/materialized views as justified, Python rules adapters, PostgreSQL indexes.
- **Tests:** one Liverpool identity across four competitions; two-leg draw resolved by applicable ET/penalty rules; historical rules variation; points deduction; postponed fixture; multi-team tie; incomplete lower-tier history.
- **Deliverables:** tested marts, rules adapters, sample queries, rules/coverage documentation and measured query performance.
- **Acceptance:** expected tables/brackets match fixed authoritative or explicitly synthetic test examples; standings remain distinct from progression; unsupported rules yield unavailable status.
- **Risks:** ambiguous tie-break ordering, mixing aggregate and match goals, overstated workload completeness.
- **Gate to M7:** validated time-safe club feature inputs and competition projections.

### Milestone 7 — Club model and preserved international integration

- **Objective:** train a separate club candidate and expose stable model interfaces without changing the legacy model.
- **Dependencies:** M1 fixed references, M2 experimental/rights contract, M5 snapshots, M6 cross-competition features.
- **Files/modules:** `ml/match/club/{features,train,evaluate,predict}.py`, `ml/match/international/adapter.py`, `ml/evaluation/`, `ml/registry/`, `ml/simulation/worldcup_adapter.py`, new artifact directory separate from v2.7 and parity tests.
- **Tasks:** freeze chronological datasets/folds; implement baselines and candidate classifiers; fit preprocessing on training only; evaluate league/cup slices, calibration, uncertainty and abstention; test cross-competition feature ablations; register approved model with domain/target; integrate unchanged international artifact/gates and World Cup engine through adapters. Advancement is a separate evaluated path or remains disabled.
- **Technologies:** existing scikit-learn, NumPy/Pandas; optional XGBoost only if selected and approved; PostgreSQL snapshots.
- **Tests:** no feature/availability cutoff violations, season split integrity, cold-start/unseen categories, probability sums, domain routing, legacy prediction parity within declared tolerance, simulator fixed-seed/locked-result parity.
- **Deliverables:** club training/evaluation report, candidate artifact/metadata, inference interface, preserved international/simulation integration and experiment records.
- **Acceptance:** reproducible temporal holdout and baseline comparison; no club routing to international model; no artifact overwrite; only validated targets released. If candidates fail release criteria, preserve analytics and publish failure evidence rather than inventing confidence.
- **Risks:** sparse draws/cups, domain shift, incomplete history, preprocessing leakage, score-model requirements for simulations.
- **Gate to M8:** callable inference/ETL interfaces and honest model approval status.

### Milestone 8 — Airflow and Docker integration

- **Objective:** schedule and observe already-tested modules in a reproducible local stack.
- **Dependencies:** M3–M7 standalone workflows, source quotas, Docker availability and isolated Airflow metadata storage.
- **Files/modules:** `docker-compose.yml`, `infra/`, `airflow/dags/`, environment templates, health checks, `docs/operations/SETUP.md` and DAG tests.
- **Tasks:** configure PostgreSQL and Airflow services/volumes; schedule discovery/reconciliation/features/predictions/quality and permitted membership/statistics jobs; set pools/concurrency/retries; separate secrets and databases; add freshness alerts and manual candidate training with approval/promotion gate.
- **Technologies:** Docker Compose, Airflow, Python modules and structured logs.
- **Tests:** DAG import/dependency order, container health/startup, retry/backfill, budget exhaustion, provider outage, restart recovery and stale-source visibility.
- **Deliverables:** local orchestration stack, operational dashboard records, DAG graph and runbooks.
- **Acceptance:** scheduled pilot chain completes and injected failure is visible/recoverable without duplicate facts or blind model promotion.
- **Risks:** Windows resources, service version conflicts, quota multiplication by retries, metadata isolation errors.
- **Gate to M9:** stable data/model interfaces, run status and reproducible stack startup.

### Milestone 9 — FastAPI backend and React frontend

- **Objective:** expose real warehouse/model outputs through the planned application.
- **Dependencies:** M6 analytics, M7 inference/registry, M8 infrastructure and jobs, approved API contracts.
- **Files/modules:** `backend/app/{api,services,models,schemas}/`, backend tests; `frontend/src/{pages,components,api,charts}/` with `.js`/`.jsx`, router and UI tests.
- **Tasks:** implement bounded read APIs, typed Python schemas/OpenAPI, pagination, coverage/freshness metadata and domain routing; build overview, competition explorer, results, standings, brackets, teams/comparison, predictor, World Cup, ML and pipeline pages; protect admin jobs. Provide genuine unavailable states for player capabilities awaiting M10.
- **Technologies:** FastAPI/Pydantic, DB access layer, React/Vite JavaScript/JSX, React Router and selected chart library; no TypeScript.
- **Tests:** API schemas/errors/permissions, injection-resistant queries, stale/empty states, UI filters/navigation/accessibility, job limits and database-to-page smoke tests.
- **Deliverables:** runnable core application, API docs, screenshots and frontend/backend test evidence.
- **Acceptance:** displayed statistics trace to persisted sources; no illustrative numbers masquerade as facts; correct league/cup/90-minute/advancement labels; deferred player features transparent.
- **Risks:** expensive synchronous work, silent missingness, admin exposure, mismatched frontend/backend contracts.
- **Gate to M10:** reusable player API/page contracts and functioning core stack.

### Milestone 10 — Player analytics and ML clustering

- **Objective:** complete the player cohort, per-90 analytics, clustering and similarity pages.
- **Dependencies:** M2 approved player source/minutes cohort; M3 memberships/appearances; M4–M5 ingestion; M8 scheduling; M9 UI/API.
- **Files/modules:** player/statistics adapters, `database/sql/player_per90.sql`, `ml/players/`, `ml/clustering/`, cohort/version tests, player JSX pages and API services.
- **Tasks:** load verified appearances/actions/minutes and effective memberships; normalize role/context; enforce minimum minutes and missingness; compare K-Means/DBSCAN and optional hierarchical clustering; assess silhouette, Davies–Bouldin and stability; produce PCA and t-SNE/UMAP visualizations; compute scaled-distance/cosine neighbors with feature explanations. Investigate future-target Linear/Ridge/Lasso only after the target gate passes.
- **Technologies:** Pandas, SQL, scikit-learn, optional UMAP dependency if selected, React charts.
- **Tests:** nonnegative minutes, per-90 denominators, transfer overlap semantics, same-name players, role cohorts, reproducibility, distances/self-exclusion, missing metrics and target leakage.
- **Deliverables:** cohort coverage report, player feature/similarity versions, cluster evaluation, four functional player-related views and conditional regression decision report.
- **Acceptance:** meaningful supported cohort, no fabricated metrics, comparable-role neighbors and explained distances; clustering failure/insufficient data remains explicit. Regression is not claimed complete without independent future-target validation.
- **Risks:** sparse/incomparable data, tiny clusters, noisy labels, proxy targets, biased scouting claims.
- **Gate to M11:** proven player workflow or documented coverage blocker with bounded supported subset.

### Milestone 11 — Worldwide competition expansion

- **Objective:** scale the proven architecture to the five-country target and broader competitions without a schema rewrite.
- **Dependencies:** M2 source/rights gates, M4 adapters, M6 rules, M7 model validation, M8 quota planning, M9 coverage UI.
- **Files/modules:** competition/source/rule configuration, new source adapters only where needed, edition rule fixtures, coverage docs and held-out evaluation slices.
- **Tasks:** add Spain/Germany/Italy/France league/cups/super cups; complete verified European editions beyond English participants; add global club events; extend international editions including Nations League; evaluate Libertadores/Sudamericana/AFC/CAF and other countries as access permits. Register new competition/rulesets; reconcile cross-border teams; assess history and model domain shift before predictive enablement.
- **Technologies:** same warehouse/ETL/rules/API stack; configuration-driven onboarding and temporal evaluation.
- **Tests:** new edition backfill/rerun, foreign opponents, calendars/rule changes, query filters, quota scaling and per-competition predictive calibration.
- **Deliverables:** published capability registry, validated competition additions, updated model coverage and expansion runbook.
- **Acceptance:** new competition can be added through registry/adapters/rules without redesigning canonical matches; unsupported features remain catalog-only/unavailable; no complete-worldwide claim.
- **Risks:** licensing/cost, disconnected strength scales, incomplete qualifying rounds, provider naming conflicts and deployment capacity.
- **Gate to M12:** freeze the release coverage; unmet expansion targets explicitly deferred instead of silently represented as supported.

### Milestone 12 — Testing, documentation, research and demonstrations

- **Objective:** produce an evaluator-runnable release with distinct DE/ML evidence.
- **Dependencies:** all enabled prior capabilities; exact frozen release scope; optional paper requirement confirmed.
- **Files/modules:** `docs/demos/`, academic reports, API/ERD/architecture docs, experiment reports, source appendix, README/setup/operations updates and end-to-end tests.
- **Tasks:** execute full import/update/correction/feature/prediction/UI chain; validate setup on a clean environment; benchmark with methodology; rehearse quota failure/recovery; audit claims/rights, accessibility and security; reproduce classifier/PCA/selection/cross-competition ablations and clustering evidence; prepare two demonstrations and optional focused paper.
- **Technologies:** pytest, DB/API/UI/DAG suites, Docker, SQL and reproducible experiment tooling.
- **Tests:** legacy parity plus integration, concurrency, backup/restore, quotas, temporal leakage, source freshness and full demo smoke tests.
- **Deliverables:** reproducible release candidate, DE report/demo, ML report/demo, source/rights register, measured evaluation and optional paper with verified primary references.
- **Acceptance:** independent evaluator can run documented demos and trace every claim to dataset/code/model/rules/test evidence; no conflation of match accuracy and advancement; unavailable scope explicit. Hosting and Git publication require separate authorization.
- **Risks:** unrepeatable environments, overstated metrics, academic scope creep, unverified rights and team contribution ambiguity.
- **Next prerequisite:** owner acceptance before deployment/publication; record remaining backlog and maintenance ownership.

---

## 16. Testing and acceptance plan

### 16.1 Testing layers

| Layer | Tests |
|---|---|
| Extractors | Response parsing, pagination, rate limit, auth failures, malformed payloads |
| Validation | Required fields, score/status consistency, schema drift, missingness |
| Identity | Provider ID resolution, duplicate names, transfer history, manual review |
| Warehouse | Constraints, migrations, upsert idempotence, indexes, correction history |
| Features | Chronological ordering, time cutoff, Elo replay, no post-match leakage |
| Models | Artifact load, probability normalization, calibration, regression parity |
| Clustering | Scaling, reproducibility, role cohort, minimum minutes, missing data |
| Tournament | Fixed results, bracket rules, deterministic seed, probability ranges |
| Competition rules | Edition-specific points/tie-breaks/deductions, group/league phases, two-leg aggregates, replays, awards, extra time and shootouts |
| Cross-competition features | Same canonical club across competitions; chronology, congestion, missing-history flags and disconnected-league strength policy |
| API | Schema, errors, pagination, security, freshness metadata |
| UI | Search, filters, empty states, stale-data labels, responsive behavior |
| Airflow | DAG import, retries, backfill, partial failures, dependency ordering |
| End-to-end | Historical import → update → feature → prediction → UI |

### 16.2 Proposed measurable criteria (targets, not achieved)

- **Idempotence:** duplicate canonical match count remains zero after repeated identical imports.
- **Traceability:** every displayed match prediction links to feature/model versions and data cutoff.
- **Leakage safety:** automated checks reject future-dated feature observations or availability timestamps.
- **Recovery:** failed source fetch does not corrupt previously verified gold tables.
- **Freshness:** stale sources visibly labeled with last successful sync.
- **ML evidence:** full test sample counts, split dates, class metrics, calibration, and baseline comparison documented.
- **Coverage honesty:** no player statistics fabricated for unsupported leagues/seasons.
- **Reproducibility:** documented Docker setup and fixed-snapshot experiments work on another development machine.
- **Coverage correctness:** every enabled competition-season-metric has verified capability evidence; a competition listed in the catalog alone does not enable unsupported predictions.
- **Correction safety:** old published forecasts remain immutable while a corrected analytical view and downstream feature version are rebuilt.
- **Domain separation:** club requests never silently use the international model; regulation and advancement probabilities retain separate target metadata.

Do not set arbitrary “90% football prediction accuracy” as a pass criterion. Football outcome prediction is uncertain; assess against baselines, calibration, reproducibility, and credible holdouts.

---

## 17. Operational setup and deployment

### 17.1 Local environment

- Python 3.12.14 was used successfully for the existing artifact; freeze the exact environment and validate future service versions separately.
- Node.js/npm for React.
- Docker Desktop + Compose for services.
- PostgreSQL with separate development/test databases.
- Airflow configured with an isolated metadata database/schema.
- Environment variables for DB credentials, API keys, optional provider limits, model paths, logging, and feature flags.

### 17.2 Example environment variable names (values intentionally omitted)

```dotenv
DATABASE_URL=
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=
API_FOOTBALL_KEY=
API_FOOTBALL_BASE_URL=
FOOTIQ_RAW_DATA_DIR=
FOOTIQ_MODEL_ARTIFACT_DIR=
FOOTIQ_DEFAULT_TIMEZONE=UTC
FOOTIQ_ENABLE_CLUB_PREDICTIONS=false
FOOTIQ_ENABLE_PLAYER_REGRESSION=false
FOOTIQ_LOG_LEVEL=INFO
```

Do not use this example as a claim about the current `.env.example`; it is a proposed future configuration. Never put actual secrets in the document or Git.

### 17.3 Security and reliability

- Use `.gitignore`, least-privilege DB accounts, parameterized SQL, API request timeouts.
- Separate public read endpoints from admin-only ingestion/training/simulation actions.
- Validate API inputs and protect expensive computations with quotas/rate limits.
- Sanitize logs; do not log provider tokens or unnecessary personal data.
- Back up schema and critical curated data; maintain source manifests and migration history.
- Make provider licensing and attribution visible in documentation and UI where required.
- Do not promise 24/7 operation if the project runs on a local student machine.

### 17.4 Source rights, retention and operational controls

Maintain source-specific training, display, redistribution, cache and retention decisions with checked dates and evidence. A public Git repository or free download does not automatically permit every use. The existing inventory's historical license descriptions are leads to verify, not newly granted rights. Review existing redistributed snapshots too; this planning task does not remove or republish them. Restricted raw responses stay outside public artifacts; permitted lineage manifests can reference hashes without including payloads. Do not attach an umbrella code license as if it relicensed third-party data. Provider terms changes can disable an adapter/feature without damaging stored audit history.

Plan backup/restore tests, migration rollbacks, health checks, DB role separation, redacted logs and bounded public queries. Authentication guards admin ingestion, promotion and expensive simulations. Airflow metadata and analytics credentials must be isolated. Raw pickle models are trusted local artifacts only; never accept arbitrary uploaded pickle files. Public hosting, broader redistribution and production credentials are separate future decisions.

---

## 18. Team work allocation (proposed, not assigned)

The original PDF suggested Bhanu for match prediction/backend, Neilsen for player performance/feature engineering, and Preeti for clustering/visualization. With the added Data Engineering scope, a revised balanced proposal is:

| Workstream | Lead suggestion | Shared responsibilities |
|---|---|---|
| Match prediction, ensemble evaluation, backend inference | Bhanu | Testing, ML report, integration |
| Data ingestion, PostgreSQL, feature engineering, Airflow | Neilsen | Source review, integration, DE report |
| Player analytics/clustering, visualizations, frontend analytics | Preeti | Dataset quality, evaluation, UI integration |
| Shared | All | Literature survey, architecture, documentation, demo, QA |

Finalize based on actual skills, schedules, and faculty requirements. Ensure each mini-project has a distinct contribution and presentation; confirm institutional policy on reusing datasets or code across courses.

---

## 19. Academic deliverables and demonstration scripts

### 19.1 Data Engineering demonstration (suggested 5–8 minutes)

1. Show raw source sample and provider provenance.
2. Run an Airflow DAG and show task dependencies/logs.
3. Show validation and a deliberately quarantined malformed record.
4. Query PostgreSQL tables and an analytics mart.
5. Re-run the same batch to prove no duplicate canonical match.
6. Simulate a new final match or correction and show downstream feature changes.
7. Open pipeline dashboard showing freshness and row-count metrics.

**Report evidence:** ERD, DAG graph, ETL architecture, SQL queries, source matrix, test results, sample row counts, performance measurements with methodology.

### 19.2 Machine Learning demonstration (suggested 5–8 minutes)

1. Show the historical training dataset and chronological split.
2. Explain Elo/form features and leakage prevention.
3. Compare baseline and candidate classifier metrics and calibration.
4. Predict a fixture, show three probabilities and confidence/Pass logic.
5. Show player similarity/clusters and feature-based explanations.
6. Show World Cup simulation with seed, run count, and locked results.
7. Discuss limitations, missing data, and why model accuracy differs from simulation validation.

The expanded ML demo also shows a separate club model, one club's cross-competition history and league-versus-cup holdout metrics. The DE demo includes a postponed fixture, a corrected result, a duplicate-safe rerun and a two-leg tie or rules-aware standing. Use small clearly labeled synthetic fixtures only for failure/rule demonstrations; never present them as real football results.

**Report evidence:** preprocessing, features, algorithms, splits, metrics, confusion matrix, calibration, clustering evaluation, ablations, reproducibility.

### 19.3 Research paper structure

Abstract → Introduction → Literature Review → Research Gap → Data and Provenance → Leakage-Safe Methodology → Experiments → Results → Discussion → Limitations → Conclusion → References.

---

## 20. Risks, dependencies, and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Player data coverage is incomplete | Player ML may not generalize | Pilot on confirmed competitions; show coverage; defer invalid models |
| API costs/rate limits | Updates may be delayed | Cache, incremental fetch, quota budget, public-data fallback |
| Cross-source entity collisions | Duplicate/wrong matches and players | Stable IDs, mapping table, review queue, provenance |
| Historical corrections | Incorrect Elo and form | Versioned facts, chronological replay, audit logs |
| Temporal leakage | Inflated ML evaluation | Point-in-time snapshots, availability timestamps, chronological splits |
| Domain shift international → club | Misleading club predictions | Separate models and held-out validation |
| Research scope too broad | Unfinished academic work | Focus paper on match prediction; prioritize MVP |
| Airflow/Docker complexity | Setup delays | Start with standalone ETL then orchestrate; documented Compose |
| Data licensing | Redistribution or usage violations | Source terms review, attribution, controlled raw storage |
| Old model artifacts fail to load | Baseline broken | Environment freeze, hashes, compatibility test, rollback |
| Missing provider data | UI misleading | Coverage badges, nullable fields, stale/unavailable states |
| Confidence gate produces no picks | Demo appears empty | Show abstention as model behavior; use archived reproducible examples |
| Domestic cups involve missing lower-tier clubs | Biased form and congestion features | Onboard opponent identities/history where permitted; expose incomplete-history indicators |
| Competition format changes | Wrong standings/qualifiers | Pin official rules by edition; test historical and new formats independently |
| Incomplete cross-border histories | Incomparable club strengths | Validate bridge data/priors and report country/competition slices |
| Source excludes automated or training use | Planned data source unusable | Permission gate and approved alternative; no bypass scraping |
| Final score includes ET/penalties | Wrong 90-minute labels | Preserve score components and exclude ambiguous labels from training |
| Date-only or late-discovered history | Retrospective leakage | Availability-aware snapshots, date precision and conservative same-day cutoffs |

---

## 21. Decision log and unresolved questions

### 21.1 Agreed architectural direction (from prior discussion)

- Reuse the World Cup prediction model rather than start over.
- Create **two separate academic deliverables** from one shared platform.
- Use Python/Pandas, PostgreSQL, Apache Airflow, Docker, SQL, and a dashboard.
- Use React JavaScript/JSX + FastAPI; do not introduce TypeScript.
- Include player analysis/clustering and model comparisons from the original PDF.
- Prefer public historical datasets plus permitted API updates.
- Keep Spark optional and avoid Kafka until there is real streaming.
- Preserve the working model and evaluate new pipelines before switching.
- Cover domestic leagues/cups/super cups, continental and global club events using season-versioned rules; add competitions through a capability registry.
- Develop separate international and club inference paths; player regression remains conditional.

### 21.2 Decisions to confirm after audit

1. Exact current dataset source(s), schemas, licenses, and checksum manifests.
2. Available API-Football subscription, coverage, quota, and budget.
3. Which club seasons and StatsBomb competitions contain enough player data.
4. Whether a defensible player regression target exists.
5. Exact club pilot seasons and release criteria; club model development is now in scope, not an optional scope decision.
6. Exact Docker/Python versions and model serialization compatibility.
7. Frontend design/theme, hosting preference, and authentication needs.
8. Timeline, faculty assessment criteria, and team member allocation.
9. Whether research paper is required or optional.
10. Data retention, raw-data sharing, and public deployment restrictions.

---

## 22. Immediate next steps — exact first work package

**Current task boundary:** this revision changes `PROJECT.md` only. It does not authorize implementation, new dependencies/datasets, DB work, branches or any Git write/publication action. Stop after documentation review; the owner must approve implementation separately.

**Next milestone to execute after approval: Milestone 1 — Repository audit and baseline preservation.** Its initial audit is already advanced, but the immutable reproducibility bundle is not complete.

1. Inventory only project source, datasets, artifacts, tests and documentation; exclude `.venv/`, `.git/`, caches and secrets. Avoid an unfiltered `tree /F` that captures environment noise.
2. Record SHA-256 hashes and sizes of original raw/processed inputs, model artifact and configs in a new dated baseline manifest. Keep `SHARE_MANIFEST.sha256` as the historical archive manifest.
3. Freeze the working Python 3.12 environment and exact installed versions; record baseline commands/platform and encoding requirements without installing a new stack.
4. Preserve the earlier 28-test evidence and fixed inference examples. If reruns are necessary, isolate output-writing commands so original files/artifacts cannot be overwritten. Define probability parity tolerances before building adapters.
5. Finish the input/output integration map, missing-source register, score/time semantics audit and risk register; retain independent-result verification as pending unless actually performed.
6. Present the baseline evidence and unresolved blockers for review. Then proceed to Milestone 2 source/coverage verification before warehouse implementation.

**Milestone 1 completion evidence:** immutable baseline manifest, exact dependency lock, fixed prediction/simulation references, tests/command evidence and architecture/risk notes; original artifact/data hashes unchanged. No PostgreSQL migration or feature implementation belongs in this first work package.

**Development rule:** no staging, commit, push, merge, new branch or Git history modification without separate explicit owner instruction. Do not delete or overwrite original datasets/model artifacts. Implementation and destructive operations need the appropriate later authorization; retain backups and parity tests.

---

## 23. Definition of done

FootIQ's **Data Engineering deliverable** is complete when a documented pipeline can ingest supported historical/new football records into a validated, queryable PostgreSQL warehouse; Airflow can run and monitor repeatable incremental jobs; corrections and duplicates are handled safely; and SQL/dashboard outputs have source provenance and freshness indicators.

FootIQ's **Machine Learning deliverable** is complete when the existing international match model is reproducibly integrated, historical out-of-time evaluation and calibration are documented, player clustering/similarity operates on a valid dataset, tournament simulation remains reproducible, and a working interface displays predictions with uncertainty and coverage. A separately trained club predictor must have documented temporal evaluation before release. Player regression remains conditional on a defensible target and independent validation.

The **optional research paper** is complete when it reports a clearly framed research question, verified literature, fixed experimental design, leakage-safe time splits, reproducible metrics, limitations, and conclusions that follow from measured results.

**Final principle:** FootIQ should be evaluated for data integrity, reproducibility, sound ML methodology, and usable analytics—not for the number of frameworks listed or unsupported claims of prediction accuracy.


---

## 24. Future expansion and scope gates

The schema supports global football, while the release capability registry determines actual support. After the validated England pilot, expand to the other four target countries, full covered European editions, global club events and approved additional international editions. Then onboard South American, Asian, African and other domestic/continental competitions through the same source, identity, rules, quality and evaluation gates.

For each addition: verify source rights and edition coverage; register competition/team/provider IDs; pin official rules; backfill and reconcile; test projections and temporal features; evaluate predictive eligibility; expose coverage in API/UI; estimate quota and infrastructure cost. Config-only onboarding is preferred, but genuinely new formats may require a tested rules plugin. New countries do not automatically inherit a validated club model.

Richer event/tactical analysis, historical forecast enrichment, advanced player prediction, additional tournament simulators and public hosting remain conditional. Spark requires a meaningful measured workload; Kafka requires a real permitted streaming feed/use case. Neither is needed simply to list more technologies in the academic reports. The optional paper remains focused on leakage-safe comparative match prediction, with separate international and club evidence.

**Stop condition for this planning task:** documentation delivered and reviewed. No implementation begins without the owner's approval.
