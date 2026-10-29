# Viva preparation: 28 questions with short answers

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

All numbers are from the project's stored evaluation and the verified build (see `ML_MODELS.md`, `TESTING_REPORT.md`).

## A. Problem and scope

**1. What problem does FootIQ solve?** Football data is scattered and hard to trust. FootIQ puts match results, standings, comparisons, probability forecasts and simulations in one dashboard, and shows how fresh and how reliable each number is.

**2. What are the objectives?** (1) A clean results store with provenance; (2) dashboards for five domestic leagues; (3) match and gameweek probability forecasts from existing validated models; (4) Monte Carlo simulations; (5) honest labelling of every limitation.

**3. What is in scope and what is not?** In: five domestic leagues, UEFA and international results, club and international forecasts, a World Cup simulator, a points-only season simulator. Out: live data, retraining, player analytics, a scoreline model, deployment.

**4. Is this a prediction tool for betting?** No. Probabilities are estimates; accuracy is about 50% on three outcomes, and the app says so.

## B. Architecture and engineering

**5. Describe the architecture.** React frontend (Vite, Tailwind, Recharts) → FastAPI backend → SQLite results store, a pandas dashboard view and frozen model files. The frontend has no model logic.

**6. Why SQLite?** It is a single file, needs no server, supports indexes and transactions, and is enough for a 223,510-row, single-user store. PostgreSQL and Airflow are described as the long-term plan in `PROJECT.md`.

**7. How is the data stored and kept trustworthy?** Each match row keeps its source, licence, first-seen and last-changed time and a content hash; bad rows go to a quarantine table (273); corrections are logged, not overwritten.

**8. How do you keep queries fast?** Statements use the `(competition_key, season)` index, pages are bounded (at most 50 rows) with keyset pagination, and statement counts are tested. A planner hint in `team_form` made a gameweek page about 15 times faster (2.3 s to 0.16 s) with identical output.

**9. Why are some responses cached?** Home and Matches are cached for 60 s with an ETag, and the cache is cleared when new results are stored.

## C. Models

**10. Which algorithms are implemented?** Club v1: multinomial logistic regression (25 features). Club v2-r1: logistic regression (62 features, experimental). Elo-based mapping. International v2.7: an ensemble of gradient boosting (50%), Elo (30%) and logistic regression (20%), temperature-calibrated with a confidence gate. World Cup: a Monte Carlo engine.

**11. Why logistic regression for clubs?** Three ordered outcomes, interpretable coefficients, well-calibrated probabilities with limited features, and it beat the Elo-only baseline on log loss.

**12. What is Elo?** A rating that rises after a win and falls after a loss, by more when the result is surprising. The difference between two teams' ratings maps to win, draw and loss probabilities. It is the baseline and also a feature.

**13. What is an ensemble?** A weighted blend of several models. v2.7 averages gradient boosting, Elo and logistic regression because their errors differ.

**14. What are accuracy, log loss and Brier score?** Accuracy: share of matches where the most likely outcome was right. Log loss: penalises confident wrong probabilities (lower is better, the main score). Brier: mean squared error of the three probabilities.

**15. How good is club v1?** On 15,645 test matches: accuracy 50.2%, log loss 1.0073, Brier 0.6026, against 43.2% / 1.0758 / 0.6511 for "always home win". On a later 5,770-match forward holdout: 49.4% / 1.0071.

**16. Why only about 50%?** Football is high-variance; three outcomes with frequent draws; the model almost never predicts a draw. We report probabilities, not certainty.

**17. What is not validated?** Club v2-r1 (only development folds; it was refit on data that includes v1's test periods), UEFA competitions, and any per-competition figure for internationals.

**18. How did you prevent data leakage?** Features use only earlier matches; splits are chronological; forecasts use results strictly before the fixture's day; only unplayed fixtures are forecast; saved forecasts record the cut-off and whether they were made before kickoff.

**19. How do you know the speed-up did not change predictions?** Before applying it we compared old and new on 1,998 sampled calls, 7,008 exhaustive calls against an independent oracle, 171 whole gameweek payloads and 10 forecast runs (80 fixtures, 240 saved rows): all identical.

**20. Are the models frozen?** Yes. Their SHA-256 hashes are recorded and re-checked; nothing is trained or changed by the app.

## D. Simulation

**21. What is Monte Carlo simulation?** Repeating a random experiment many times and counting outcomes. The World Cup engine plays the tournament thousands of times; the share of runs a team wins is its title chance.

**22. Why seeds?** A fixed seed makes runs reproducible: the same seed and settings give the same result, which we test.

**23. What does the points-only season simulator do, and why not final positions?** It draws win/draw/loss for remaining fixtures from v1 probabilities and awards 3/1/0 points, giving ranges of final points (and lower/upper position bounds for two leagues). Exact positions need a scoreline model; none of three candidates passed our predeclared validation, so it is disabled.

**24. Is the World Cup result live?** No. "Current" mode uses an archived, almost complete tournament; the final is not in the data. Against the 2026 tournament the engine called 59 of 82 matches (72%, wide interval 61–81%).

## E. Data and honesty

**25. Where does the data come from?** openfootball (CC0), martj42 international results (CC0), Wikipedia for some UEFA data (CC BY-SA, attribution required), a compiled 2026 World Cup set with per-row source URLs, and a reviewed OpenLigaDB snapshot.

**26. How fresh is it?** Newest result 2026-10-24; four leagues are marked stale; live sync is disabled on purpose. Every page says "historical, not live" and flags provisional forecasts.

**27. What happens if a kickoff time zone is unknown?** The time is shown as stored with "time zone unconfirmed". It is never converted to UTC, and the match is never called live or finished from a clock.

**28. What are the main limitations and future work?** Stale data and partial seasons, v2-r1 unvalidated, no scoreline model, no player data. Future: approved live sync, a validated scoreline model, prospective evaluation, PostgreSQL/Airflow, deployment, full accessibility audit.
