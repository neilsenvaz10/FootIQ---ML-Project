# Report: supervised Bundesliga sync, source investigation, Phase 2 (gameweek predictions)

Date: 2026-10-25. Nothing is staged, committed or pushed. No frozen model, official-protocol file or research folder was modified. Three activities with separate approval boundaries:

| Activity | Approval used | Network |
|---|---|---|
| 1 Supervised Bundesliga sync | One supervised OpenLigaDB Bundesliga 2026-27 run | **1 request**, then live access returned to disabled |
| 2 Investigation of the other four leagues | Read-only, local evidence | **None** |
| 3 Phase 2, gameweek predictions | Offline implementation | **None** |

---

## 1. Supervised Bundesliga synchronisation

**Pre-flight (before any request)**
* `config/contact.local` exists, is Git-ignored (`config/.gitignore`), and the adapter reports it as a valid contact (22 characters; the value was never printed).
* **Defect found and fixed before the run:** the sync looked for the contact in the research adapters' own folder instead of the repo-root `config/contact.local`, so the configured contact would have been ignored. It now reads the repo-root file (or `FOOTIQ_CONTACT`/`FOOTIQ_CONTACT_FILE`). Regression test added.
* Host `https://api.openligadb.de`; licence ODbL 1.0; attribution "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0" (shown in the app); minimum 3 s between requests plus jitter, retries with back-off, documented limit 60 requests/min/IP; `bl1/2026` is the only league the adapter accepts.
* A belt-and-braces allow-list wrapped the connection for the run: HTTPS, host `api.openligadb.de`, paths `/getmatchdata/bl1/2026`, `/getcurrentgroup/bl1`, `/getlastchangedate/bl1/2026/*` only.
* Live access was enabled **programmatically for this one run**; `config/sync.json` was never edited (sha256 identical before and after), so `live_enabled` is still **false**.
* Before the run: SQLite backup copy and sha256 of the club v1, v2-r1 and v2.7 model files and of the sync config.

**Request ledger** (`data/snapshots/request_ledger.jsonl`, complete):

```
{"ts": "2026-10-25T08:38:29Z", "source": "openligadb", "url": "https://api.openligadb.de/getmatchdata/bl1/2026", "status": 200, "attempt": 0}
```

One request, HTTP 200. Snapshot `20261025T083829Z_bl1_2026_season.json`, 314,767 bytes, sha256 `5f5394c035e856b750d5dc67c3ce9342e610bb268c897a4b511fcda248a2b32d`, licence ODbL-1.0.

**Verification**

| Check | Result |
|---|---|
| The 18 missing results (2026-10-09 to 10-18) | **18 of 18 recovered**, source OpenLigaDB, with UTC kickoffs |
| Results that arrived after the 2026-10-21 pilot | 7 more (Matchday 7, up to 2026-10-24), so 25 results supplied in total |
| Bundesliga 2026-27 rows | 306 before and after; 0 duplicate pairings |
| Statuses | before: 36 completed, 18 awaiting, 252 scheduled; after: **61 completed, 245 scheduled, 0 awaiting** |
| Conflicts / unresolved team identities / quarantined | **0 / 0 / 0** |
| Baseline results already held | all 36 confirmed identical and untouched (`change_count` 0) |
| Kickoff UTC | 270 of 306 now known (the other 36 are baseline results that stay unchanged) |
| Freshness after the run | Bundesliga **fresh** (latest result 2026-10-24, last sync 2026-10-25 08:38:29 UTC, nothing awaiting) |
| Model and config hashes before and after | club v1 pickle and preprocessing, club v2-r1 pickle and feature contract, international v2.7 pickle, `config/sync.json`: **all identical** |
| Frozen-artifact integrity check | club v1 true, club v2-r1 true |

**One more defect found and fixed:** the provenance role of rows whose result OpenLigaDB supplied was recorded as "confirmation"; they are now "primary" (the 25 affected rows were repaired in place and the logic fixed; regression test added).

**Live access is disabled again** (`live_enabled: false`). Unattended synchronisation needs your separate approval.

---

## 2. Other four leagues: investigation (no new requests)

Full write-up: [SOURCE_INVESTIGATION.md](SOURCE_INVESTIGATION.md). Summary from the local OpenLigaDB league listing (retrieved 2026-10-21) and earlier research:

| League | OpenLigaDB 2026 listing | Status |
|---|---|---|
| Premier League | `pl` "Premier League 2026/2027" **and** `pl1` "Permier League England" (two entries) | exists; completeness, freshness, kickoff coverage and the canonical entry are **unknown** |
| La Liga | `la1` "LaLiga EA Sports 2026/2027" | exists; same unknowns |
| Serie A | none | **not available** on OpenLigaDB |
| Ligue 1 | none | **not available** on OpenLigaDB |

Licensing and rate limits are the same as for the Bundesliga (ODbL; fair-use polling; 60 requests/min/IP). The listing also contains user-created test and duplicate leagues, so a league existing proves nothing about quality. Wikipedia stays confirmation-only (Premier League page validated offline earlier; others never validated); football-data.org needs you to read its terms and create a key.

**Request plan awaiting your approval (not run):** 5 GET requests to `api.openligadb.de` once (`/getavailableleagues/2026`, `/getmatchdata/pl/2026`, `/getmatchdata/pl1/2026`, `/getmatchdata/la1/2026`, optionally `/getresulttypes`), analysis only, no ingestion, no scheduling.

---

## 3. Phase 2: gameweek predictions (offline)

### What was built
| Piece | Where |
|---|---|
| Gameweek listing, fixture status, form, reliability flags, saved forecasts, predicted-versus-actual | `app/gameweeks.py` |
| Forecast engine and explicit-save rule | `app/forecast.py` |
| Feature/scoring refactor with identical behaviour (fast cached state, exact day-by-day replay, scoring) | `app/predict.py` |
| API: `GET /api/gameweeks`, `GET /api/gameweek`, `POST /api/gameweek/predict` | `app/main.py` |
| UI: new **Predictions** page with **Gameweek** and **Manual head-to-head** tabs, fixture cards | `frontend/src/pages/Predictions.jsx`, `GameweekPredict.jsx`, `components/FixtureCard.jsx` |
| Store: `FOOTIQ_STORE_PATH` override (demo and test copies) | `app/store/db.py` |

### How each requirement is met
* **League, season, gameweek selection.** Five domestic leagues only, season selector, gameweek selector with date ranges, previous/next buttons and the next gameweek preselected. Gameweeks whose fixture dates are far from the rest (postponements; La Liga Matchday 6 spans 3 Sep to 21 Oct) are labelled "dates out of order" and each such fixture is flagged.
* **Every scheduled fixture shown.** Cards show date, kickoff (only when a source states it; otherwise "time not confirmed"), status (Scheduled / Date passed, no verified result / Full time), and results for finished matches.
* **Frozen models only.** Club v1 (validated) is primary; club v2-r1 is shown as experimental; the Elo-only baseline is kept as a reference. No model is retrained, loaded differently or modified; artifact sha256 values are recorded with every saved run and checked in tests.
* **Form, probability bars, timestamps, model versions.** Each card shows last-five form (only matches before that fixture's date), the probability bar, the save timestamp, the data cut-off and the model versions.
* **Stale history, missing earlier results, unknown kickoff are marked.** Reliability is `provisional` when the newest competition result is more than 14 days before the fixture, or either team has earlier matches that should have been played but have no verified result, or history is thin/unconnected. Fixtures with unplayed earlier fixtures are flagged but not downgraded. Provisional and fully supported fixtures look different.
* **No future or same-day leakage.** Every fixture is featurised from results dated strictly before its own date, so an unknown kickoff can never admit a same-day result. Fixtures dated after every result in the store use the cached state; any fixture dated on or before the newest result (postponed or back-dated) uses the project's day-by-day replay, so even a later result of another competition cannot reach it. Tested: the fast path equals the replay for a future fixture; after adding Bundesliga results dated the same day and later, a Premier League fixture's probabilities and feature hash are bit-identical. Only unplayed fixtures are ever forecast; finished matches are never predicted in hindsight.
* **Saved only on an explicit press.** `GET` endpoints never compute or save. `POST /api/gameweek/predict` requires `user_action = "predict_gameweek_button"` (wrong value: 422, nothing saved). Each press adds a new run (history is never overwritten). Verified in the live store: **0 forecast runs** exist after all testing; the browser check below used a private copy.
* **Honest "before kickoff" flag.** `made_before_kickoff` is `yes` only if a stated kickoff is in the future, or (kickoff unknown) the fixture's date has not started anywhere on Earth yet (UTC+14 rule); `no` when the whole date window has passed; otherwise `unknown`. Forecasts that are not certainly pre-kickoff are shown but **not counted** in the predicted-versus-actual summary.
* **Exact feature snapshot and cut-off saved** with every forecast row (`feature_snapshot_json` plus its sha256, data cut-off date and note, model ids, artifact hashes).
* **Predicted versus actual** appears once a verified result arrives: predicted outcome, actual outcome, probability given to the actual outcome, a correct/incorrect mark, and a summary (accuracy and mean log loss over counted fixtures) with the caveat that this is application history, not the official evaluation.
* **Separate from the official prospective evaluation.** Saved rows live only in the application store tables; nothing is written under any research or `prospective_log` folder (tested by fingerprinting those files before and after); no protocol or ledger is touched; every run is labelled "Application forecast history ... Not part of the official prospective evaluation".
* **Manual head-to-head prediction** is unchanged and available in its own tab, still for all 11 competitions.
* **Preserved:** World Cup simulator and bracket, all existing pages and endpoints (existing tests pass unchanged).

### Verification
Results of the final regression run are in the summary message of this phase. Browser check (on a private copy of the store, because the real store must only record presses made by you): the Predictions page opens on the next gameweek (Premier League Matchday 8) in the Gameweek tab, shows 10 fixture cards with status and reliability chips and "No forecast saved yet"; pressing Predict gameweek saved 10 forecasts in about 30 s (day-by-day replay needed for the two fixtures dated before the newest Bundesliga result) and showed the bars, timestamp, model versions, run history and per-fixture details; no horizontal overflow at 375 px.

### Current limits worth knowing
* Today every Premier League, La Liga, Serie A and Ligue 1 forecast is **provisional** (results are stale and 96 played matches have no result). Bundesliga fixtures can be fully supported.
* Forecasts for later gameweeks are built from the history at the cut-off (results of intervening gameweeks are unknown); the simulator (Phase 3) is where "what-if" rolling forecasts belong.
* The first press after start-up can take about 30 s when day-by-day replay is needed; the button waits for the model history to be ready.
* Kickoff times are known for most Bundesliga fixtures (UTC) but for few fixtures elsewhere.

### Blockers and decisions before Phase 3
1. Phase 3 needs per-league tie-break and qualification rules from official regulations (I will not use memory).
2. Premier League, La Liga, Serie A and Ligue 1 simulations would be built on stale results until fresh sources are approved. The request plan in section 2 is the quickest route for two of them.
3. A scoreline model for goal-based tie-breaks is an explicit assumption that needs your sign-off (Plan section 5.2).
