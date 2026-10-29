# Viva preparation: 29 questions with short answers

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

> **Phase 4.29:** the answers below were rewritten for the final six-competition application. Answers about the removed World Cup and international models now sit in the archive question at the end.

All numbers are from the project's stored evaluation and the verified build (see `ML_MODELS.md`, `TESTING_REPORT.md`).

## A. Problem and scope

**1. What problem does FootIQ solve?** Football data is scattered and hard to trust. FootIQ puts match results, standings, comparisons, probability forecasts and simulations in one dashboard, and shows how fresh and how reliable each number is.

**2. What are the objectives?** (1) A clean results store with provenance; (2) dashboards, results, fixtures and standings for six competitions (five domestic leagues and the Champions League); (3) match and gameweek probability forecasts from the frozen club models; (4) an experimental points-only Monte Carlo season simulation; (5) honest labelling of every limitation.

**3. What is in scope and what is not?** In: exactly six competitions (Premier League, La Liga, Bundesliga, Serie A, Ligue 1 and the Champions League league phase), club forecasts, a points-only season simulator for the five leagues. Out: live data, retraining, player analytics, a scoreline model, deployment, and the Europa League, Conference League, World Cup, Nations League and Copa America (removed in Phase 4.18, data kept but not served).

**4. Is this a prediction tool for betting?** No. Probabilities are estimates; accuracy is about 50% on three outcomes, and the app says so.

## B. Architecture and engineering

**5. Describe the architecture.** React frontend (Vite, Tailwind, Recharts) → FastAPI backend → SQLite results store, a pandas dashboard view and frozen model files. The frontend has no model logic.

**6. Why SQLite?** It is a single file, needs no server, supports indexes and transactions, and is enough for a 223,636-row, single-user store. PostgreSQL and Airflow are described as the long-term plan in `PROJECT.md`.

**7. How is the data stored and kept trustworthy?** Each match row keeps its source, licence, first-seen and last-changed time and a content hash; bad rows go to a quarantine table (273); corrections are logged, not overwritten.

**8. How do you keep queries fast?** Statements use the `(competition_key, season)` index, pages are bounded (at most 50 rows) with keyset pagination, and statement counts are tested. A planner hint in `team_form` made a gameweek page about 15 times faster (2.3 s to 0.16 s) with identical output.

**9. Why are some responses cached?** Home and Matches are cached for 60 s with an ETag, and the cache is cleared when new results are stored.

## C. Models

**10. Which algorithms are implemented?** Club v1: multinomial logistic regression (25 features). Club v2-r1: logistic regression (62 features, experimental). Elo-based mapping. The season simulator is a Monte Carlo over club-v1 probabilities. (Earlier research models for internationals are archived and not served.)

**11. Why logistic regression for clubs?** Three ordered outcomes, interpretable coefficients, well-calibrated probabilities with limited features, and it beat the Elo-only baseline on log loss.

**12. What is Elo?** A rating that rises after a win and falls after a loss, by more when the result is surprising. The difference between two teams' ratings maps to win, draw and loss probabilities. It is the baseline and also a feature.

**13. What is an ensemble?** A weighted blend of several models. The archived international model v2.7 averaged gradient boosting, Elo and logistic regression; the served club models are single logistic regressions.

**14. What are accuracy, log loss and Brier score?** Accuracy: share of matches where the most likely outcome was right. Log loss: penalises confident wrong probabilities (lower is better, the main score). Brier: mean squared error of the three probabilities.

**15. How good is club v1?** On 15,645 test matches: accuracy 50.2%, log loss 1.0073, Brier 0.6026, against 43.2% / 1.0758 / 0.6511 for "always home win". On a later 5,770-match forward holdout: 49.4% / 1.0071.

**16. Why only about 50%?** Football is high-variance; three outcomes with frequent draws; the model almost never predicts a draw. We report probabilities, not certainty.

**17. What is not validated?** Club v2-r1 (only development folds; it was refit on data that includes v1's test periods) and **every Champions League prediction**: the club models were evaluated on domestic leagues only, so the app labels Champions League probabilities "Not validated (indicative only)".

**18. How did you prevent data leakage?** Features use only earlier matches; splits are chronological; forecasts use results strictly before the fixture's day; only unplayed fixtures are forecast; saved forecasts record the cut-off and whether they were made before kickoff.

**19. How do you know the speed-up did not change predictions?** Before applying it we compared old and new on 1,998 sampled calls, 7,008 exhaustive calls against an independent oracle, 171 whole gameweek payloads and 10 forecast runs (80 fixtures, 240 saved rows): all identical.

**20. Are the models frozen?** Yes. Their SHA-256 hashes are recorded and re-checked; nothing is trained or changed by the app.

## D. Simulation

**21. What is Monte Carlo simulation?** Repeating a random experiment many times and counting outcomes. The season simulator plays the rest of a league season thousands of times (win, draw or loss for each unplayed match) and reports the spread of final points.

**22. Why seeds?** A fixed seed makes runs reproducible: the same seed and data give the same result, which we test. The number of simulations is 1,000 to 50,000, 10,000 by default.

**23. What does the points-only season simulator do, and why not final positions?** For the five domestic leagues it draws win/draw/loss for every remaining fixture from club v1 probabilities and awards 3/1/0 points, giving expected final points and a 10-90% range. Completed matches are never simulated again; fixtures past their date without a result are simulated and disclosed. Lower and upper position bounds (title, top four, relegation) exist only for the Bundesliga and La Liga, whose tie-break rules are verified. Exact positions need a scoreline model; none of three candidates passed our predeclared validation, so that mode is disabled. It is labelled experimental.

**24. Is any data live?** No. Only the Bundesliga and La Liga are refreshed, once, when the backend starts (OpenLigaDB, two requests, switchable off); the other four competitions are static data imported after verification.

## E. Data and honesty

**25. Where does the data come from?** openfootball (CC0) for history and schedules; Wikipedia (CC BY-SA 4.0, attribution and share-alike) for Champions League and verified league results; OpenLigaDB (ODbL, attribution) for the Bundesliga and La Liga start-up refresh. football-data.co.uk and FixtureDownload were used only to cross-check dates and results and are not stored. StatsBomb open data appears only in the separate dataset submission (credit required).

**26. How fresh is it?** The newest results are from 25-26 October 2026. Bundesliga and La Liga are "updated when FootIQ starts"; the other four competitions are "historical only" until a data provider approves automatic updates. Every page says "historical, not live" and flags provisional forecasts.

**27. What happens if a kickoff time zone is unknown?** The time is shown as stored with "time zone unconfirmed". It is never converted to UTC, and the match is never called live or finished from a clock.

**28. What are the main limitations and future work?** Four competitions without an update source and partial seasons, v2-r1 and Champions League predictions unvalidated, no Champions League knockout stage, no scoreline model, no player data. Future: provider-approved sync, a validated scoreline model, Champions League validation, prospective evaluation, PostgreSQL/Airflow, deployment, accessibility audit.

**29. (Archive) What happened to the World Cup and international models?** The earlier version of the project also had an international ensemble (v2.7) and a World Cup simulator. They were removed from the application in Phase 4.18 to focus on six club competitions; their code and data are preserved as research history and are not served.
