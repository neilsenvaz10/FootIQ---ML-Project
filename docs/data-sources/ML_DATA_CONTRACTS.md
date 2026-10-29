# FootIQ Machine Learning Data Contracts & Leakage Safeguards

**Document:** `ML_DATA_CONTRACTS.md`  
**Milestone:** Milestone 2 (Dataset Verification and Scope Finalization)  
**Date:** 20 October 2026  
**Status:** Formal ML data contracts established; temporal leakage and training/inference mismatches audited.  
**Baseline References:** `BASELINE_AUDIT.md`, `DEPENDENCY_MAP.md`, `RISK_REGISTER.md` (Risks R04, R05, R06, R07, R18).

---

## 1. Overview and Contract Governance Principles

Machine learning models in football analytics are extraordinarily susceptible to subtle data leakage, look-ahead bias, and training-serving skew. 

To enforce strict engineering discipline across both the Data Engineering and Machine Learning mini-projects, FootIQ establishes **five formal ML Data Contracts**. Each contract defines:
- **Feature Schema & Types:** Exact column names, data types, allowable value ranges, and nullability.
- **Target Semantics:** Mathematically and temporally unambiguous target labels.
- **Temporal Cutoff Guarantee (`known_at_utc`):** Strict verification that every feature value was measurable and known *prior* to the event's kickoff timestamp.
- **Serving Invariant:** Exact mathematical parity between offline historical training features and online/live inference inputs.

> **Strict Rule:** Existing baseline model scripts (`worldcup_predictor_v27.py`, `simulate_tournament_v213.py`, etc.), serialized pickle artifacts, and historical datasets remain **100% frozen and unmodified**. These contracts define the adapter interfaces and future warehouse feature views.

---

## 2. Contract 1: International Match Outcome Prediction (1X2 Ensemble)

### 2.1 Model Scope
Predicts regulation 90-minute outcome (Home Win `H`, Draw `D`, Away Win `A`) for international men's matches. Supports the frozen v2.7 ensemble (Gradient Boosting 50%, Elo 30%, Logistic Regression 20%) and future v3.0 warehouse-backed models.

### 2.2 Feature Contract Specifications (28 Feature Vector)

| Field Name | Type | Allowable Range | Nullable | Semantic Definition |
|---|---|---|---|---|
| `home_elo_pre` | Float | $[1000.0, 2400.0]$ | No | Home team pre-match Elo rating |
| `away_elo_pre` | Float | $[1000.0, 2400.0]$ | No | Away team pre-match Elo rating |
| `elo_diff` | Float | $[-1000.0, 1000.0]$| No | `home_elo_pre - away_elo_pre` |
| `neutral` | Int (0/1) | $\{0, 1\}$ | No | 1 if match is on neutral ground, 0 otherwise |
| `home_advantage` | Float | $[0.0, 75.0]$ | No | 75.0 if `neutral == 0`, else 0.0 |
| `home_points_l5` | Float | $[0.0, 15.0]$ | No | Total points earned by home team in prior 5 matches |
| `away_points_l5` | Float | $[0.0, 15.0]$ | No | Total points earned by away team in prior 5 matches |
| `home_gd_l5` | Float | $[-30.0, 30.0]$ | No | Goal difference of home team in prior 5 matches |
| `away_gd_l5` | Float | $[-30.0, 30.0]$ | No | Goal difference of away team in prior 5 matches |
| `home_points_l10` | Float | $[0.0, 30.0]$ | No | Total points earned by home team in prior 10 matches |
| `away_points_l10` | Float | $[0.0, 30.0]$ | No | Total points earned by away team in prior 10 matches |
| `home_gd_l10` | Float | $[-50.0, 50.0]$ | No | Goal difference of home team in prior 10 matches |
| `away_gd_l10` | Float | $[-50.0, 50.0]$ | No | Goal difference of away team in prior 10 matches |
| `home_elo_change_l5`| Float | $[-200.0, 200.0]$| No | Elo rating net change for home team over prior 5 matches |
| `away_elo_change_l5`| Float | $[-200.0, 200.0]$| No | Elo rating net change for away team over prior 5 matches |
| `home_opp_elo_l5` | Float | $[1000.0, 2400.0]$ | No | Average pre-match Elo of home team's last 5 opponents |
| `away_opp_elo_l5` | Float | $[1000.0, 2400.0]$ | No | Average pre-match Elo of away team's last 5 opponents |
| `rest_days_diff` | Float | $[-60.0, 60.0]$ | No | `min(home_rest, 30) - min(away_rest, 30)` |
| `matches_prior_home`| Float | $[0.0, 20.0]$ | No | Bounded prior match count (see Mismatch Audit below) |
| `matches_prior_away`| Float | $[0.0, 20.0]$ | No | Bounded prior match count (see Mismatch Audit below) |
| `is_world_cup` | Int (0/1) | $\{0, 1\}$ | No | 1 if FIFA World Cup finals, 0 otherwise |
| `is_competitive` | Int (0/1) | $\{0, 1\}$ | No | 1 if non-friendly competitive match, 0 otherwise |
| `tourn_wc` | Int (0/1) | $\{0, 1\}$ | No | One-hot encoded tournament category: World Cup |
| `tourn_qual` | Int (0/1) | $\{0, 1\}$ | No | One-hot encoded tournament category: Qualifier |
| `tourn_continental`| Int (0/1) | $\{0, 1\}$ | No | One-hot encoded tournament category: Euro/Copa/AFCON/Asian |
| `tourn_nations_league`| Int (0/1) | $\{0, 1\}$ | No | One-hot encoded tournament category: Nations League |
| `tourn_friendly` | Int (0/1) | $\{0, 1\}$ | No | One-hot encoded tournament category: Friendly |
| `tourn_other` | Int (0/1) | $\{0, 1\}$ | No | One-hot encoded tournament category: Other |

### 2.3 Target Label
- `result`: Categorical string $\in \{'H', 'D', 'A'\}$.
- **Strict Semantic:** 90-minute regulation result (+ stoppage time). Extra time and penalty shootouts are EXCLUDED from the 1X2 result label.

---

## 3. Contract 2: Club Match Outcome Prediction (1X2 Classification)

### 3.1 Model Scope
Predicts regulation 90-minute outcomes for domestic and European club matches. Operates as an independent model domain from the international predictor.

### 3.2 Feature Contract Specifications (Club Feature Vector)

| Field Name | Type | Allowable Range | Nullable | Semantic Definition |
|---|---|---|---|---|
| `club_elo_home_pre` | Float | $[1200.0, 2200.0]$ | No | Club Elo pre-match rating |
| `club_elo_away_pre` | Float | $[1200.0, 2200.0]$ | No | Club Elo pre-match rating |
| `club_elo_diff` | Float | $[-800.0, 800.0]$ | No | `club_elo_home_pre - club_elo_away_pre` |
| `home_venue_flag` | Int (0/1) | $\{0, 1\}$ | No | 1 for true home ground; 0 for neutral venue (e.g. cup finals)|
| `home_points_l6` | Float | $[0.0, 18.0]$ | No | Rolling points earned in last 6 league fixtures |
| `away_points_l6` | Float | $[0.0, 18.0]$ | No | Rolling points earned in last 6 league fixtures |
| `home_shots_ratio_l6`| Float | $[0.1, 0.9]$ | No | Rolling $\frac{\text{Shots For}}{\text{Shots For} + \text{Shots Against}}$ over last 6 matches |
| `away_shots_ratio_l6`| Float | $[0.1, 0.9]$ | No | Rolling $\frac{\text{Shots For}}{\text{Shots For} + \text{Shots Against}}$ over last 6 matches |
| `home_sot_ratio_l6` | Float | $[0.1, 0.9]$ | No | Rolling $\frac{\text{Shots on Target For}}{\text{Total Shots on Target}}$ over last 6 matches |
| `away_sot_ratio_l6` | Float | $[0.1, 0.9]$ | No | Rolling $\frac{\text{Shots on Target For}}{\text{Total Shots on Target}}$ over last 6 matches |
| `home_rest_days` | Float | $[1.0, 30.0]$ | No | Calendar days since previous competitive match (capped at 30)|
| `away_rest_days` | Float | $[1.0, 30.0]$ | No | Calendar days since previous competitive match (capped at 30)|
| `market_implied_prob_h`| Float | $[0.01, 0.99]$ | Yes | De-vigged Pinnacle/Bet365 implied probability for Home Win |
| `market_implied_prob_d`| Float | $[0.01, 0.99]$ | Yes | De-vigged Pinnacle/Bet365 implied probability for Draw |
| `market_implied_prob_a`| Float | $[0.01, 0.99]$ | Yes | De-vigged Pinnacle/Bet365 implied probability for Away Win |

### 3.3 Target Label
- `result_90`: String $\in \{'H', 'D', 'A'\}$.
- Drawn matches that progress to extra time (e.g. FA Cup replays/knockouts) are recorded strictly as `'D'`.

---

## 4. Contract 3: Player Performance Regression (Next-Match Expectations)

### 4.1 Model Scope
Predicts player expected playing time and expected goal contribution for the subsequent match ($T+1$).

### 4.2 Feature Contract Specifications

| Field Name | Type | Semantic Definition |
|---|---|---|
| `player_id` | Integer / UUID | Persistent canonical player identifier |
| `team_id` | Integer / UUID | Current club / national squad identifier |
| `role_category` | Categorical | Positional group: `GK`, `DEF_CENTRAL`, `DEF_FULLBACK`, `MID_CENTRAL`, `MID_ATTACKING`, `FWD` |
| `minutes_ratio_l5` | Float $[0.0, 1.0]$ | Ratio of available minutes played over team's last 5 matches |
| `starts_l5` | Integer $[0, 5]$ | Number of matches started in team's last 5 fixtures |
| `rest_days` | Float $[1.0, 30.0]$ | Days since player's last on-pitch appearance |
| `npxg_per_90_l10` | Float $\ge 0.0$ | Rolling non-penalty xG per 90 over prior 10 appearances |
| `xa_per_90_l10` | Float $\ge 0.0$ | Rolling expected assists per 90 over prior 10 appearances |
| `opp_def_rating` | Float | Pre-match defensive strength rating of upcoming opponent |

### 4.3 Target Labels
- **Sub-Model A (Availability/Minutes):** `minutes_played_t1` $\in [0, 120]$.
- **Sub-Model B (Goal Involvement Rate):** `goal_involvement_rate_t1` (Non-penalty xG + xA in fixture $T+1$).

---

## 5. Contract 4: Player Clustering & Dimensionality Reduction

### 5.1 Model Scope
Unsupervised representations (PCA, t-SNE, UMAP, K-Means) mapping multi-dimensional playing styles into low-dimensional latent spaces.

### 5.2 Feature Contract Specifications (StatsBomb Standardized Vector)

| Feature Category | Metrics (All Rate-Normalized Per 90 Minutes) | Preprocessing Constraint |
|---|---|---|
| **Passing Volume & Range** | `passes_attempted_p90`, `pass_completion_pct`, `progressive_pass_distance_p90`, `long_pass_ratio` | Standardized ($\mu=0, \sigma=1$) |
| **Chance Creation** | `open_play_key_passes_p90`, `passes_into_box_p90`, `crosses_p90` | Standardized ($\mu=0, \sigma=1$) |
| **Ball Progression** | `progressive_carries_p90`, `dribbles_completed_p90`, `dispossessed_p90` | Standardized ($\mu=0, \sigma=1$) |
| **Shooting Profile** | `shots_p90`, `npxg_per_shot`, `shot_distance_mean` | Standardized ($\mu=0, \sigma=1$) |
| **Defensive Intensity**| `pressures_p90`, `counterpressures_p90`, `tackles_won_p90`, `interceptions_p90`, `blocks_p90` | Standardized ($\mu=0, \sigma=1$) |
| **Aerial Presence** | `aerial_duels_contested_p90`, `aerial_win_pct` | Standardized ($\mu=0, \sigma=1$) |

### 5.3 Sample Filter Contract
- `minutes_played >= 450` for tournament datasets; `minutes_played >= 900` for full-season league datasets.
- Zero-variance features within position cohort are pruned prior to dimensionality reduction.

---

## 6. Contract 5: Tournament Simulation (Monte Carlo Engine)

### 6.1 Model Scope
Simulates multi-stage tournaments (group stage round-robin followed by single-elimination knockout bracket). Governed by the frozen v2.13 engine and future warehouse simulator adapters.

### 6.2 Simulation State Contract
- **Team Power Vector:** Float rating $P_i \in [0.0, 100.0]$ derived from team Elo, squad depth, recent form, and tactical profile.
- **Goal Distribution:** Expected goals $\lambda_{ij} = \exp(\beta_0 + \beta_1(P_i - P_j) + \text{HFA})$. Actual goals sampled via Poisson:
  $$G_i \sim \text{Poisson}(\lambda_{ij}), \quad G_j \sim \text{Poisson}(\lambda_{ji})$$
- **Knockout Stage Resolution:** If $G_i = G_j$ in regulation, extra-time goals are sampled with halved expectation. If still tied, penalty shootout probability is assigned via logistic function of team penalty rating or equal odds ($p = 0.50$).
- **Result-Locking Contract:** A persistent lookup table `worldcup_locked_results` stores verified match scores. The simulation engine MUST check:
  ```python
  if fixture_id in locked_results:
      return locked_results[fixture_id]
  else:
      return sample_monte_carlo_outcome(team1, team2)
  ```
- **Reproducibility Guarantee:** Random number generators must accept an explicit fixed integer seed (e.g. `20260625` in baseline).

---

## 7. Deep Audit of Baseline Leakage Risks & Feature Mismatches

Our Milestone 2 audit inspected the exact code lines and mathematical transformations in the inherited baseline scripts, revealing four critical discrepancies that future warehouse pipelines must resolve without modifying legacy artifacts:

### 7.1 Risk R05: Training vs. Serving Feature Mismatch (`matches_prior`)
- **The Historical Training Code (`scripts/feature_builder_v26.py`):**
  ```python
  # Historical feature construction used a rolling deque capped at 20:
  team_match_history[team] = deque(maxlen=20)
  ...
  matches_prior = len(team_match_history[team])
  ```
  In historical training, `matches_prior` was bounded in $[0, 20]$. For any team that had played 20 or more matches since 2000, `matches_prior` was permanently equal to `20`.
- **The Live Inference Code (`scripts/worldcup_predictor_v27.py`):**
  ```python
  # Live predictor read matches_prior directly from team_recent_form_latest.csv:
  home_matches = float(home_form.get('matches_played', 20))
  ```
  In `team_recent_form_latest.csv`, `matches_played` is an unbounded cumulative integer reflecting total matches played (often exceeding 100).
- **Impact:** When a live fixture was evaluated, the trained model received an out-of-distribution feature value (e.g. `matches_prior = 142` instead of a value in $[0, 20]$).
- **Warehouse Adapter Remedy:** The FootIQ warehouse feature view will explicitly compute:
  $$\text{matches\_prior\_bounded} = \min(\text{total\_prior\_matches}, \; 20)$$
  This guarantees exact mathematical parity between the feature distributions seen during training and those supplied at serving time.

### 7.2 Risk R06: Categorical Dummy Leakage Across Splits
- **The Historical Defect:** In `feature_builder_v26.py`, `pd.get_dummies()` was called on the *concatenated* dataframe containing training, calibration, and test sets combined.
- **The Risk:** While tournament names in international football are generally fixed, fitting categorical encoders or scalers on holdout data violates strict temporal segregation principles.
- **Warehouse Adapter Remedy:** In the PostgreSQL / dbt feature pipeline, one-hot category dictionaries and any numeric scalers will be computed exclusively on the `train` partition ($Dates \le 2018\text{-}12\text{-}31$) and applied as static projection matrices onto calibration and test sets.

### 7.3 Risk R07: Date-Only Ordering and Same-Day Temporal Leakage
- **The Historical Defect:** In `results.csv`, matches have a `date` string (e.g. `2026-06-11`), but no kickoff time (`time` is absent in `results.csv` and only present in `worldcup_2026_matches.csv`).
- **The Risk:** When multiple international matches occurred on the same calendar day, Elo updates were applied sequentially based on the arbitrary row ordering in the CSV file. If Match A and Match B occurred concurrently, Match B's pre-match Elo spuriously incorporated the outcome of Match A.
- **Warehouse Adapter Remedy:** The Silver warehouse introduces `kickoff_timestamp_utc` with full date-time granularity. Same-day fixtures with identical timestamps update Elo in isolated parallel batches, guaranteeing point-in-time causal validity:
  $$\text{Feature Snapshot Time} = \text{kickoff\_timestamp\_utc} - 1\text{ second}$$

### 7.4 Risk R18: Competition Category Keyword Inconsistency
- In the baseline, `is_competitive` was defined as `tournament != 'Friendly'`.
- In live inference script `worldcup_predictor_v27.py`, `tournament_flags` checked a restricted keyword list (`'world cup'`, `'qualif'`, `'euro'`, `'copa'`, `'nations league'`), causing minor official tournaments (e.g. Gulf Cup, SAFF Cup) to be classified as non-competitive in live scoring despite being marked competitive in historical training.
- **Warehouse Adapter Remedy:** The canonical competition dimension (`dim_competition`) will explicitly declare `is_competitive` as a verified boolean flag, eliminating ad-hoc string parsing in prediction scripts.
