# Limitations and functional boundaries

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

Everything here was checked against the code or the running application on 2026-10-27. Items that the UI already states to the user are marked **(shown in the UI)**.

## 1. Data

* **Historical, not live.** The newest stored result is 2026-10-24. Live synchronisation is off by design (`config/sync.json`). **(shown in the UI)**
* **Stale leagues.** Four of the five leagues are reported stale; matches whose date has passed have no verified result. Banner chips, notices and the "provisional" labels say so. **(shown in the UI)**
* **Partial seasons.** All 2026-27 league seasons are incomplete; standings cover only stored matches and clubs may have played different numbers of games. **(shown in the UI)**
* About half of the scheduled fixtures (all of Serie A and Ligue 1) have no UTC kickoff, only a local time without a time zone, or no time. They are shown as stored and marked "time zone unconfirmed"; nothing is converted. A same-day match with an unconfirmed zone cannot be classed as started or finished. **(shown in the UI)**
* The UEFA, Nations League and Copa América data are less complete than the five leagues; Conference League has no 2026-27 rows; the 2026 World Cup final is not in the data.
* 273 source rows failed validation and are quarantined; historical source conflicts were not resolved.

## 2. Forecasts

* **Provisional forecasts.** A forecast is marked provisional when team history is stale or has gaps (missing results, earlier fixtures unplayed, little history, ratings not connected). The reasons are listed per fixture. **(shown in the UI)**
* Predictions use model history that ends 2026-10-24 (clubs, pooled) and 2026-06-02 (internationals); a league whose newest verified result is older (for example Serie A, 2026-09-20) gets stale-history flags.
* Club v1 is validated on pooled domestic leagues only; accuracy is about 50% on three outcomes and draws are almost never predicted. v2-r1 is an experimental candidate without an unbiased evaluation. UEFA club competitions are not validated. **(shown in the UI)**
* Saved forecasts are application history, not the official prospective evaluation. Only forecasts certainly saved before kickoff are counted in predicted-versus-actual. The API exposes the latest forecast per fixture and the run list, not older forecasts per fixture.
* No injuries, line-ups, weather, transfers or player data are modelled.

## 3. Simulations

* **Final-position (scoreline) season simulation is disabled** (`scoreline_method: null`): none of three candidate scoreline methods met its predeclared criteria in every league. The button is visibly blocked. **(shown in the UI)**
* The **points-only** season simulator is experimental, limited to the Bundesliga and La Liga, and gives distributions of final points and, for those two leagues, lower/upper **position ranges**, never exact title, top-four or relegation probabilities. Rule profiles are used only where verified; the La Liga rule confirmation is **pending** until its federation document checksum is checked. **(shown in the UI)**
* The **World Cup simulator** uses an archived near-complete 2026 tournament: `current` mode is almost entirely locked to real results and is not live odds; `pre_tournament` is the static pre-tournament model. Seeded runs are reproducible. **(shown in the UI)**
* Standings are computed from stored results (3/1/0 points) and ordered by points, goal difference, goals scored, name: a display order, not an official tie-break. No qualification or relegation places are shown. **(shown in the UI)**

## 4. Engineering

* **Production store side effect.** Starting the backend against `data/footiq.sqlite` recorded a `startup_check` row in `sync_runs` (the file was already in WAL mode since the 2026-10-25 import; an earlier version of this document wrongly said the backend switched it). Phase 4.8B stopped this write. It happened on 2026-10-27 (row 8, outcome `skipped_live_disabled`), so the file's SHA-256 is no longer the post-import value `39ab9651…61f3` recorded on 2026-10-25. The 223,510 match rows are unchanged (newest `last_changed_utc` is still the import time, row counts match the earlier inspection, `PRAGMA integrity_check` is `ok`). Use a private copy (`FOOTIQ_STORE_PATH`) for experiments.
* `README.md` at the repository root still describes the original research pipeline ("FastAPI and React are planned"); the mini-project documentation is under `docs/mini-project/` (a pointer is added by this phase).
* `scipy` is imported by the season simulator but is not listed in `requirements-share.txt` or `app/requirements.txt`; the bundled `.venv` has it (`scipy==1.17.1`).
* Season-simulator result tables still use 9–11 px text in places, and two radio inputs on the Simulations page are 20 × 20 px (their labels are larger). Both were recorded in earlier phases.
* Accessibility checks are automated probes plus targeted keyboard checks, not a full screen-reader audit or WCAG certification.
* A single-process, single-user application: no authentication, no deployment configuration, no continuous integration, no off-device backup of the evidence.
* A cold backend start takes about 20–30 s to load the club history; the first club prediction waits for it.
* The UI is English only.

## 5. Out of scope by decision

Live data ingestion, retraining, a scoreline model, player analytics and clustering, PostgreSQL/Airflow (described in `PROJECT.md` as the long-term plan), and a deployed multi-user service.
