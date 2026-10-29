# 03 Feature engineering report

Code: `_scripts/v2_features.py` (single leak-safe state machine used for both training and inference). 98 columns, 62 model inputs in the full set. Table: `_work/features_v2_dev.pkl` (sha in the manifest).

| Group | Features | Notes |
|---|---|---|
| Elo (tuned Elo2) | `elo2_diff` | Grid-tuned K=30, HA=50, season regression 0 (`03b_ELO_PARAMETER_GRID.csv`), goal-difference multiplier |
| Elo extras | league-relative Elo per side, 5-match Elo momentum diff, history depth (log prior matches), new-to-competition flags | League-relative values avoid mixing Elo scales of disconnected competitions; unknown history -> NaN + missing indicator |
| Home advantage | league goal-difference HA, league home-win rate, recent-minus-long league HA, team HA (shrunk, prior weight 8) and diff | History only, shrunk toward league (prior 300) |
| Form | PPG 3/5/10, weighted PPG, venue PPG, form momentum, opponent-adjusted performance (perf10), 5-match GD diff | Decay 0.85 |
| Goal-based | attack/defence strengths (prior 4, decay 0.92), expected goals for/against (Poisson-style from **actual scores**, not xG), expected goal difference, Poisson H/D/A probabilities, 5-match goals for/against | |
| League context | tier, league draw rate, league goals per match, days into season, league depth, competition history depth | |
| Rest / congestion | days rest, matches in 7/14/30 days, congestion diff, cup/continental-recorded-in-365-days flag | Explicit coverage flags because cups/continental results are incomplete (see report 01) |

Not built: player/injury/lineup/xG/market features (no restricted or unavailable data).

Missing-value policy: unknown history stays NaN in the table; the modelling step adds a missing indicator and imputes with training medians. NaN share is under 0.1% for every column (largest: league-relative Elo 0.05%).

Excluded for leakage/availability: anything using the match's own score, final-table position, post-match data, odds. Brute-force/perturbation tests passed (report 02).

Unavailable at inference: nothing in the selected set requires data beyond fixture list + results history, but cup/continental coverage is incomplete, so rest features remain partly mis-measured; the coverage flags are included in the model.
