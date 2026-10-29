# Limitations and functional boundaries

> **Final state (Phase 4.28):** FootIQ supports exactly six competitions (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, UEFA Champions League). The Europa League, Conference League, World Cup, Nations League and Copa America are not in the application (their data is preserved, nothing shows or predicts them). This file was rewritten in Phase 4.28; the previous version is part of the phase history. Authoritative description: `FINAL_SYSTEM_GUIDE.md`.

Checked against the running application on 2026-10-28. Items the interface already states are marked **(shown in the UI)**.

## 1. Data

* **Historical, not live.** The newest stored results are from 25-26 October 2026. At start the backend refreshes only the Bundesliga and La Liga once from OpenLigaDB (two requests); there is no scheduler and no other live source. **(shown in the UI)**
* **No update source** for the Premier League, Serie A, Ligue 1 and the Champions League: their data is static and was imported only after verification. Their freshness chips say "historical only". **(shown in the UI)**
* **Partial seasons.** All 2026-27 seasons are incomplete; standings cover only stored matches. **(shown in the UI)**
* **Open data issues.** Three Serie A results rest on a single source and were not applied; one La Liga match is postponed; 60 provider-assisted date corrections are held; 273 source rows failed validation and sit in quarantine.
* About half of the scheduled fixtures have a local kickoff time without a time zone (or no time); they are marked "time zone unconfirmed" and nothing is converted. A fixture dated today is not forecast.
* **Champions League:** only the league phase (matchdays 1-8, 144 matches, 54 played) is stored; the 36-club table is provisional; the knockout rounds are not drawn and not in the data. **(shown in the UI)**

## 2. Forecasts

* Club v1 is validated on pooled domestic leagues only: about 50% accuracy on three outcomes, draws almost never predicted. Club v2-r1 is an experimental candidate with no unbiased evaluation. **Champions League predictions are not validated** and are always labelled "Not validated (indicative only)". **(shown in the UI)**
* A forecast is marked provisional when team history is stale or has gaps; the reasons are listed per fixture. **(shown in the UI)**
* Saved forecasts are application history, not the official prospective evaluation.
* No injuries, line-ups, weather, transfers or player data are modelled.

## 3. Simulations

* Only the domestic **points-only** season simulation is approved (experimental), for the five domestic leagues; it is not available for the Champions League. It simulates win, draw and loss only, invents no scores and gives no exact finishing positions. Lower and upper bounds for title, top four and relegation exist only for the Bundesliga and La Liga (their tie-break rules are verified); for the Premier League, Serie A and Ligue 1 the page says they are not available. A "Provisional" data state (for example Serie A with three fixtures past their date and no result) still runs, with the warning visible. The "Final positions" mode is disabled. **(shown in the UI)**
* The Season drop-down offers only seasons with unplayed fixtures; if none exist the page says "No season to simulate".
* Simulations run only on request and a run is saved to the database.

## 4. Engineering

* `scipy==1.17.1` is imported by the season simulator but is missing from `requirements-share.txt` and `app/requirements.txt` (the bundled `.venv` has it).
* The backend sometimes stays at "Shutting down" after Ctrl-C; close its terminal after 10 seconds (the database stays intact).
* No authentication, single user, local only. Not hardened for public hosting.
* `App.jsx` still routes `/worldcup` to the Simulations page (leftover alias).
* Third-party data keeps its own licence and attribution terms (see `DATA_SOURCES.md`).
