# FootIQ Player Data Feasibility Assessment

**Document:** `PLAYER_DATA_FEASIBILITY.md`  
**Milestone:** Milestone 2 (Dataset Verification and Scope Finalization)  
**Date:** 20 October 2026  
**Status:** Complete feasibility audit; empirical verification of player features and ML modeling targets.  
**Baseline References:** `BASELINE_AUDIT.md`, `DATASET_INVENTORY.md`, `RISK_REGISTER.md` (Risk R10).

---

## 1. Executive Summary

The original FootIQ proposal envisioned comprehensive player-level performance analytics, similarity clustering (PCA/t-SNE/UMAP, K-Means), and player outcome prediction alongside team match forecasting. 

Milestone 1 revealed that the inherited repository contains `player_impact_v21.csv` (1,246 rows), but established that these values are **static heuristic formula scores** (30% overall + 20% club level + 22% national role + 15% tactical fit + 10% form + 3% tournament experience) rather than empirical match-event metrics (Risk R10).

Our Milestone 2 audit evaluates the empirical availability of granular player data across open and accessible providers. We conclude:
1. **Player Clustering and Similarity is Fully Feasible on Curated Cohorts:** Using StatsBomb Open Data, high-dimensional player vectors (passing profiles, defensive pressures, progressive carries, xG contribution per 90) can be engineered for covered tournaments (e.g., 2018/2022 World Cups, 2020/2024 Euros, 2015/16 Premier League, 2023/24 Bundesliga).
2. **Universal, Real-Time Player Tracking Across All Modern Leagues is NOT Feasible on Free Feeds:** StatsBomb does not provide ongoing weekly Premier League data; Football-Data.co.uk provides zero player data; and API-Football's free tier (100 calls/day) caps ingestion at approximately 4-5 full match lineup/player-stat payloads per day.
3. **Target Formulation Requires Rigorous Separation:** Descriptive statistics (historical goals, past pass completion) and synthetic commercial metrics (e.g., EA Sports FIFA ratings, proprietary 1-10 match ratings) are **invalid future prediction targets**. Genuine ML prediction must focus on objective targets such as future availability/minutes or expected contribution rates per 90 minutes.

---

## 2. Granular Player Attribute Availability Audit

| Player Attribute Category | Specific Metric / Field | Mart Jansen (Intl) | Football-Data.co.uk | StatsBomb Open Data | API-Football (Free) | FootIQ Baseline (`player_impact_v21`) |
|---|---|---|---|---|---|---|
| **Identity & Membership** | Player ID, Full Name, DOB | Name only | None | Verified unique SB ID, DOB, country | Verified API ID, birth date, nationality | Name, Team, Position |
| **Club & Squad Affiliation**| Current Club, Squad Roster | National team only | None | National & Club at time of tournament | Complete club squad rosters | National squad affiliation |
| **Participation** | Appearances, Starts, Minutes | None | None | Exact minutes, start/sub timestamps | Minutes played per match & season | Synthetic role indicator |
| **Positional Data** | Primary position, tactical role | None | None | Exact starting XI formation coordinates & role | Broad position (G, D, M, F) | 4 broad categories (GK, DEF, MID, FWD) |
| **Goal Involvement** | Goals, Assists, Penalties | Goals, penalties, own goals | None | Goals, assists, shot assists (key passes), penalties | Goals, assists, penalties won/scored | Heuristic baseline score |
| **Shooting Metrics** | Shots, Shots on Target, xG | None | None | Shot coordinates, freeze frames, xG, shot technique | Shots total, on target, off target | Synthetic rating |
| **Passing & Progression** | Passes, Key Passes, Carries | None | None | Pass length, angle, recipient, progressive distance, carries | Passes total, key passes, pass accuracy % | None |
| **Defensive Actions** | Tackles, Interceptions, Blocks | None | None | Exact tackle outcome, interceptions, blocks, pressures | Tackles total, blocks, interceptions, fouls committed | None |
| **Duels & Physicality** | Aerial duels, Ground duels | None | None | Aerial duels won/lost, loose ball duels | Duels total, duels won, dribbles attempted/success | None |
| **Spatiotemporal Events** | (x, y) Event coordinates | None | None | Exact (x, y, z) pitch coordinates for every action | None | None |
| **Historical Continuity** | Multi-year season aggregates | Continuous (goals only) | None | Discontinuous (specific seasons only) | Continuous 2010–2026 (Quota constrained) | Single snapshot |

---

## 3. Provider Feasibility for Player Analytics

### 3.1 StatsBomb Open Data: The Scientific Gold Standard (Cohort-Restricted)
- **Strengths:** 
  - Industry-leading spatiotemporal event stream with verified tactical rigor.
  - Granular event definitions (e.g., differentiation between counter-pressing actions, regular pressures, clearances under pressure, progressive carries).
  - High-confidence player identification with persistent IDs across tournaments.
  - Standardized pitch coordinates (120 x 80 yards), allowing direct spatial clustering (heatmaps, action zones).
- **Feasibility Assessment:**
  - **Clustering / Similarity:** **100% FEASIBLE.** FootIQ can build state-of-the-art unsupervised player representations (e.g. modern central midfielders clustered by progressive passing vs. defensive pressing volume).
  - **Prediction:** Highly suitable for cross-sectional regression (e.g. relationship between pressing efficiency and turnover generation).
  - **Limitation:** Cannot serve as a live weekly player tracker for the current Premier League season due to coverage discontinuity.

### 3.2 API-Football: The Operational Breadth Source (Quota-Constrained)
- **Strengths:**
  - Standardized season-by-season aggregates for over 10,000 active players.
  - Standard per-match stats: minutes, shots, passes, tackles, dribbles, duels.
- **Feasibility Assessment:**
  - Free-tier rate limit (100 calls/day) severely constrains ingestion. Ingestion of 20 Premier League squads (approx. 500 players) with individual player statistics requires 20-30 days of continuous quota allocation if queried individually.
  - Solution: Ingest player season statistics only for top-flight pilot teams (e.g., top 6 Premier League clubs) or rely on match-lineup bulk endpoints (`/fixtures/lineups` returns both starting XIs and benches in a single API call).
  - **Player Ratings Warning:** API-Football provides an algorithmic `rating` (e.g., 7.42). This is a proprietary composite calculation, not a measured empirical quantity. FootIQ will not treat this rating as ground truth.

### 3.3 Football-Data.co.uk: Zero Player Data
- Football-Data.co.uk contains strictly team-level match scores, match stats, and odds. It provides zero player names, lineups, or statistics.

### 3.4 Mart Jansen International Results: Scorer-Only Data
- Contains 47,601 goalscorer rows (verified in Milestone 1 baseline audit).
- Useful exclusively for calculating historical national team scoring rates and all-time top scorer records. Cannot support multidimensional player profiling.

---

## 4. Player Clustering and Similarity Feasibility Analysis

### 4.1 Methodology and Mathematical Validity
To perform mathematically valid player clustering and dimensionality reduction (PCA, t-SNE, UMAP, K-Means), features must be:
1. **Rate-Normalized (Per 90 Minutes):** Absolute count metrics (e.g., 45 tackles) inherently bias towards players with more minutes. All counting features must be transformed to $\text{Metric per } 90 = \frac{\text{Metric}}{\text{Minutes Played}} \times 90$.
2. **Sample-Gated:** Players with fewer than a minimum minutes threshold (e.g., 450 minutes for a tournament, 900 minutes for a domestic season) must be excluded to prevent small-sample extreme rate artifacts (e.g., a substitute who plays 10 minutes and makes 2 tackles producing an unrepresentative rate of 18 tackles per 90).
3. **Positionally Stratified:** Clustering forwards, goalkeepers, and center-backs in a single feature space produces trivial clusters that simply reflect broad pitch zones. FootIQ must cluster within tactical cohorts:
   - Central Defenders & Full-backs
   - Central & Defensive Midfielders
   - Attacking Midfielders & Wingers
   - Central Strikers

### 4.2 Proposed Feature Vector for Player Clustering (StatsBomb Cohort)

```
Feature Vector X_player = [
    # Passing & Creation (per 90)
    pass_completion_rate,
    progressive_passes_per_90,
    open_play_key_passes_per_90,
    passes_into_penalty_area_per_90,
    pass_length_mean,
    
    # Ball Carrying & Progression (per 90)
    progressive_carries_per_90,
    dribble_success_rate,
    dispossessed_per_90,
    
    # Shooting & Goal Threat (per 90)
    shots_per_90,
    xg_per_shot,
    shot_touch_ratio,
    
    # Defensive Work Rate & Intensity (per 90)
    pressures_per_90,
    counterpressures_per_90,
    interceptions_per_90,
    tackles_won_per_90,
    aerial_win_rate
]
```

### 4.3 Evaluation Metrics for Clustering Quality
In compliance with the academic mini-project criteria, FootIQ will evaluate clustering using:
- **Silhouette Score** (measuring cluster tightness and separation).
- **Davies-Bouldin Index** (measuring cluster similarity).
- **Calinski-Harabasz Index** (ratio of between-cluster to within-cluster dispersion).
- **2D/3D Visualization:** PCA explained variance plots alongside non-linear manifold embeddings (t-SNE and UMAP).

---

## 5. Descriptive Statistics vs. Valid Future-Prediction Targets

A major flaw in naive sports analytics is the conflation of descriptive summaries with legitimate predictive machine learning targets.

```
+----------------------------------------------------------------------------------------------------+
|                                      TARGET VALIDITY SPECTRUM                                      |
+----------------------------------------------------------------------------------------------------+
| INVALID / ILL-POSED TARGETS               | MARGINAL / HEURISTIC TARGETS | VALID PREDICTIVE TARGETS|
| - Synthetic EA Sports FIFA Card Ratings   | - Subjective match ratings   | - Next-match availability|
| - Commercial 1-10 Match Ratings           | - "Man of the Match" votes   | - Expected minutes played|
| - Retrospective descriptive stats as labels|                             | - Future goal involvement|
|   (e.g., using match goals to predict     |                             |   rate (Poisson/NegBinom)|
|    match performance in the same match)   |                             | - Out-of-sample xG rate  |
+----------------------------------------------------------------------------------------------------+
```

### 5.1 Invalid Prediction Targets (Explicitly Excluded)
1. **Commercial Match Ratings (e.g. WhoScored, SofaScore, API-Football 1-10 rating):** These numbers are generated by proprietary, unvalidated weighted formulas. Predicting a black-box formula score is an exercise in reverse-engineering proprietary arithmetic, not modeling underlying athletic performance.
2. **Video Game Ratings (FIFA / EA Sports FC attributes):** Subjective, marketing-driven static values updated manually by scouts. They do not constitute scientific ground truth.
3. **Contemporaneous Descriptive Labels:** Using statistics recorded *during* Match $T$ as features to predict performance in Match $T$ introduces complete temporal circularity.

### 5.2 Valid Machine Learning Predictive Targets for FootIQ

1. **Target 1: Next-Match Participation & Minutes Prediction (Classification & Regression)**
   - *Problem:* Predict whether a squad member will start, feature as a substitute, or not play in fixture $T+1$, conditional on historical rest, recent starts, injury status, and squad rotation patterns.
   - *Formulation:* Ordinal classification (Did Not Play, Substitute [1-45 min], Starter [46-90+ min]) or hurdle regression model.
2. **Target 2: Future Expected Goal Involvement Rate ($\lambda_{t+1}$)**
   - *Problem:* Predict a player's goal or assist contribution rate over their next $N$ appearances ($T+1$ through $T+N$).
   - *Formulation:* Poisson or Negative Binomial Generalized Linear Model (GLM) / Gradient Boosting regressor predicting future non-penalty xG + xA per 90, trained strictly on features known prior to match $T$.
3. **Target 3: Tournament Outperformance vs. Historical Baseline ($\Delta_{\text{perf}}$)**
   - *Problem:* In tournament simulation, model the residual between a player's tournament contribution and their 3-year baseline club rate, conditioned on tactical fit, age trajectory, and opposition defensive strength.

---

## 6. Implementation Scope and Phasing for Player Analytics

To ensure high academic rigor and flawless execution within project constraints, player analytics will be implemented in three structured phases:

1. **Phase 1 (Academic Mini-Project Core):** Unsupervised player clustering, similarity engine, and dimensional reduction (PCA, t-SNE, UMAP) built on the complete StatsBomb tournament and league cohorts (World Cup 2018/2022, Euros 2020/2024, La Liga Messi dataset, Bundesliga 2023/24).
2. **Phase 2 (Pilot Player Regression):** Supervised prediction of future minutes and xG contribution per 90 for top European players using time-split historical cohorts.
3. **Phase 3 (Operational Lineup Ingestion):** Ingesting matchday confirmed lineups and player participation via API-Football fixture endpoints for the English Premier League pilot.
