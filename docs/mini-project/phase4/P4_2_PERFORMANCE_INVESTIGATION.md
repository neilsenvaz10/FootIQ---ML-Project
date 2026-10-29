# P4.2: why `/api/gameweek` is slow, and what the Home banner uses instead

Written 2026-10-27 on branch `feat/club-ml-v2` (HEAD `970f461`). Question from the P4.1 checkpoint: `/api/gameweek` took about 3.7 s on 2026-10-26 and 10.5 s on 2026-10-27 with the same code. Nothing here changes a frozen model, a prediction, the evaluation protocol or `/api/gameweek` itself; the optimisation in section 5 is **a proposal, not applied**.

All measurements ran on private copies of the results store (`data/supervised/rehearsal/phase4_p42.sqlite` and `phase4_p42_exp.sqlite`, made by copying `data/footiq.sqlite`: 223,510 `matches` rows, 228,655,104 bytes; the copy the backend has open is no longer byte-identical, because opening it created WAL files and changed its header, which is why copies are used). The production store was only read and hashed (SHA-256 `39ab9651…61f3`, unchanged). The scripts and raw results are in `data/supervised/phase4/p42/` (git-ignored; list in section 8).

## 1. Result

| Question | Answer |
|---|---|
| Where does the time go? | In `gameweeks.team_form`, which runs **twice per fixture** (20 times for a 10-fixture gameweek): in the profiled run 5.906 s of the 5.949 s request (99%), and 25 `sqlite3.Connection.execute` calls account for 5.912 s. Timed on their own the 20 calls took 8.81 s against a mean request of 9.66 s (91%): the machine's speed changed between runs (section 3.3) |
| Why is one call slow? | The planner answers it from `idx_matches_status_date (status, match_date)`. Every call therefore visits **every completed match in the store dated before the fixture: 220,006 rows**, 16.6 times the 13,226 that belong to the competition, and filters competition and team afterwards. There is no index on (competition, team, date) and no planner statistics (`sqlite_stat1` does not exist) |
| Why 3.7 s one day and 10.5 s the next? | **Not the code and not the data:** the gameweek code and everything it reads were unchanged on both days (the backend sources were byte-identical to the pre-Phase-4 state at the P4.1 checkpoint) and the store has 223,510 rows and the same SHA-256 throughout. The request is **CPU-bound**: on an idle machine it takes 2.8 s, and with the CPU deliberately oversubscribed twofold (24 busy processes on 12 threads) the same request takes 5.8 s, then 2.8 s again when the load stops. One `team_form` call took 118 ms at best and 633 ms at worst today, so the same 20 calls take 2.4 s to 12.7 s, which contains both reported totals. 3.7 s and 10.5 s are the same work with different amounts of CPU available to the server; I did not record what else was running on the 26th and in the afternoon of the 27th (section 3.3) |
| Is there a fix? | Yes. Variants B and D were compared with the current statement row for row and end to end and are identical; C picks the same plan as B (section 4). The recommended one is a one-line planner hint in `team_form` (about **39 times faster**, no schema change); a composite-index variant is about 500 times faster but changes the store's schema. Proposal and test plan: section 5 |
| Home banner? | It does not call `/api/gameweek`. `GET /api/featured-fixture` uses a fixed number of indexed statements and answers in 46 ms uncached (first request), about 54 ms for a later uncached build and 27 ms from its cache (section 6) |

## 2. Method

1. **Profile** (`perf_gameweek_profile.py`): `gameweeks.gameweek_fixtures` for EPL matchday 9 (10 fixtures), three runs, with `cProfile` and with an SQLite trace callback that counts and times every statement.
2. **Plans and row counts** (`perf_store_inspect.py`): `EXPLAIN QUERY PLAN` of every statement the view issues, the size of every table and index, row counts, the indexes on `matches`, the journal and cache settings, and the number of rows the winning plan visits.
3. **Experiments on a second copy** (`perf_gameweek_experiments.py`): the same statement with (B) `INDEXED BY idx_matches_comp_season_date`, (C) after `ANALYZE`, (D) two composite indexes `(competition_id, home_entity_id, match_date)` and `(competition_id, away_entity_id, match_date)` with a `UNION ALL`. Timings are the median of nine repetitions over the 20 calls of the sample gameweek.
4. **Equivalence**: the three variants must return the same rows in the same order as the current statement. Checked for **7,008 calls** (both teams of every club fixture in the two newest seasons of the five leagues: every call a gameweek page could make for them): 0 differences for B and 0 for D. End to end, 10 gameweeks of three leagues were built with the current code and with each variant and the JSON payloads compared (187,124 bytes in total): identical (`perf_gameweek_endtoend.py`).
5. **Everything else the page does** (`perf_other_endpoints.py`) was timed to rule out other causes.

## 3. Findings

### 3.1 Time by part (EPL matchday 9, 10 fixtures, current code)

| Part | Calls per request | Time |
|---|---|---|
| `team_form` (home and away team of each fixture) | 20 | **5.906 s of 5.949 s** in the profiled run (0.295 s each, 99%) |
| `_fixture_rows` (the gameweek's fixtures) | 1 | 4 to 7 ms (24 ms cumulative in the profile) |
| `seasons()` | 1 | 2 to 8 ms |
| `competition_latest_result` | 1 | 0.1 to 2 ms |
| `assess` (reliability rules, pure Python) | 10 | 5 ms in total |
| Saved-forecast lookups (`SELECT forecasts`) | about 2 | negligible (the `forecasts` table is empty on the copy) |

The profiled run made 25 `execute` calls (the 20 `team_form` statements and 5 others) and spent 5.912 s in them. The three timed requests of the same script took 7.19 s, 11.04 s and 10.74 s, the profiled one 5.95 s, and the 20 `team_form` calls timed one by one afterwards took 193 ms at best, 512 ms in the median, 633 ms at worst and 8.81 s in total, all within about two minutes (10:23): the same work at very different speeds.

### 3.2 The statement and its plan

```
SELECT ... FROM matches m LEFT JOIN teams t1 ... LEFT JOIN teams t2 ...
WHERE m.competition_id=? AND (m.home_entity_id=? OR m.away_entity_id=?)
  AND m.status IN ('completed','awarded') AND m.match_date<? AND m.home_goals_final IS NOT NULL
ORDER BY m.match_date DESC, m.record_id DESC LIMIT 5

SEARCH m USING INDEX idx_matches_status_date (status=? AND match_date<?)
SEARCH t1 USING INDEX sqlite_autoindex_teams_1 (entity_id=?) LEFT-JOIN
SEARCH t2 USING INDEX sqlite_autoindex_teams_1 (entity_id=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```

* Rows the plan visits per call: **220,006** (all completed matches of all competitions dated before the fixture) for 5 rows returned; 13,226 of them are in the competition (ratio 16.6).
* The store: 223,510 `matches` rows of about 452 bytes (the table is 100.9 MB, its indexes `idx_matches_pair` 22.1 MB, `idx_matches_comp_season_date` 11.9 MB, `idx_matches_status_date` 7.3 MB, `idx_matches_key` 4.3 MB), `match_sources` 44 MB. SQLite's page cache is the default 2 MB (`cache_size = -2000`), so a walk of that size is served from the operating system's file cache on every call.
* The planner has no statistics (`sqlite_stat1` is absent), so it cannot see that `competition_id` is far more selective than `status`, and it picks the (status, match_date) index because the date range looks selective. After `ANALYZE` it picks `idx_matches_comp_season_date` by itself (variant C).
* The other statements of the page use `idx_matches_key` and take milliseconds.

### 3.3 The 3.7 s and 10.5 s observations

Same statement, same store, same code, measured at different moments of 2026-10-27:

| Measurement | One `team_form` call | The gameweek request (20 calls) |
|---|---|---|
| 10:21, plan inspection, five calls | 210 to 269 ms | about 4.2 to 5.4 s (20 calls) |
| 10:23, profile script: three timed requests, a profiled request, then 20 single calls | 193 to 633 ms, median 512 ms (the single calls) | **7.2, 11.0 and 10.7 s**, then 5.9 s for the profiled request (measured) |
| 10:28, experiment copy, current statement, nine repetitions | 376 to 523 ms, median 509 ms | about 7.5 to 10.5 s (20 calls); 10:47, end-to-end comparison of 10 gameweeks: **9.5 to 12.3 s** (measured) |
| 11:19, ten repeated calls while the backend test suite was running | 119 to 125 ms, median 122 ms | about 2.4 s (20 calls) |
| 11:26, ten repeated calls, machine idle | 118 to 123 ms, median 119 ms | **2.9 s** (measured over HTTP, `http_timing.py`) |
| 11:27, same HTTP request, three times idle, then three times with **24 busy processes on the 12-thread CPU**, then three times idle | | **2.80 to 2.85 s, then 5.77 to 5.89 s, then 2.80 to 2.90 s** (`perf_cpu_contention.py`) |

What this shows:

* The request is CPU-bound: 20 full walks of a 220,000-row range, nothing waits on a lock or the network. Giving its process half the CPU (24 busy processes on 12 threads) doubles its time (2.83 s to 5.81 s), and it returns to 2.8 s when the load stops.
* One call costs about 120 ms on an idle machine and up to 630 ms on the busy one, so the same 20 calls take 2.4 s to 12.7 s. **3.7 s is 20 calls of about 185 ms; 10.5 s is 20 calls of about 525 ms**: both lie inside that span. The difference between the two days is how much CPU the server could use (at the P4.1 checkpoint other servers and several browsers were running), not the code and not the data.
* What I cannot say is exactly what was running on 2026-10-26 and in the afternoon of 2026-10-27; I did not record it at the time. The idle figure (2.8 s) is not good news either: it is still 20 store-wide walks for one page.

### 3.4 What else is not the cause

| Candidate | Evidence |
|---|---|
| Code change | The backend sources were byte-identical to the pre-Phase-4 state at the P4.1 checkpoint (integrity manifest). P4.2 later added `app/featured.py` and one endpoint to `app/main.py`; `app/gameweeks.py` was not touched |
| Data growth | `data/footiq.sqlite` was last written on 2026-10-25 at 20:02 by the production import; 223,510 `matches` rows and the same SHA-256 (`39ab9651…`) throughout |
| Lock or writer | Read-only connections and no writer during the measurements; the time scales with available CPU (section 3.3) |
| Other endpoints | `/api/sync/status` 22 ms (11 competitions), `views.freshness` 20 ms, `standings` 7 ms, `recent_results` 8 ms, `season_coverage` 29 ms, `analytics.audit()` 183 ms; the first dashboard request loads the 20.5 k-row frame once (1.4 s) and is then cached |
| Saved forecasts | `forecasts` is empty on the copies |

## 4. Experiments (current statement and three candidates)

| Variant | Plan | One call (median of the 20-call sample) | One gameweek, end to end (10 gameweeks) |
|---|---|---|---|
| **A** current | `idx_matches_status_date (status, match_date)` | 509 ms | 10.1 s median, 12.3 s max |
| **B** `INDEXED BY idx_matches_comp_season_date` (no schema change) | `idx_matches_comp_season_date (competition_id)` | 32.3 ms | 0.261 s median, 0.329 s max |
| **C** `ANALYZE` (writes `sqlite_stat1` into the store) | the planner picks `idx_matches_comp_season_date` by itself | 30.9 ms | not run (same plan as B) |
| **D** two composite indexes and `UNION ALL` | `ix_exp_home` and `ix_exp_away`, `MERGE (UNION ALL)`, no table walk | 0.4 ms | 0.020 s median, 0.027 s max |

The experiment copy grew from 228.7 MB to 258.0 MB with the two indexes of variant D (+29.4 MB, +13%). Payloads of all 10 gameweeks were byte-identical in A, B and D.

## 5. Proposed optimisation (not applied; needs your decision)

**Recommended: variant B, then D if more speed is ever needed.**

| Option | Change | Effect | Cost and risk |
|---|---|---|---|
| **B** planner hint | `INDEXED BY idx_matches_comp_season_date` in the one statement of `team_form` (`app/gameweeks.py`, one line) | 10 s to 0.26 s per gameweek (39 times) | No schema change, no write to the store. The statement raises an error if that index is missing; `store/build.py` creates it and a test can assert it exists |
| **D** composite indexes | Two indexes on `matches` and a `UNION ALL` statement | 10 s to 0.02 s (about 500 times) | Changes the store's schema (+29 MB) and needs a rebuild or migration step, so it touches the production store and its recorded hash: requires an explicit decision |
| **C** `ANALYZE` | Run once at the end of `store/build.py` and after an import | Same plan as B for every statement, not only this one | Writes `sqlite_stat1` into the store (changes its hash); other plans may change too, so every endpoint would need re-testing |
| Fewer statements | Fetch the form of all teams of a gameweek in one statement | Removes the N + 1 pattern entirely | Larger change to `gameweeks.py`; not needed once B is in |

Test plan for B (when approved): (1) a test that builds a store like the real one and asserts `EXPLAIN QUERY PLAN` of `team_form` names `idx_matches_comp_season_date` and contains no `idx_matches_status_date`; (2) the equivalence check above as a permanent test on a store with several seasons (same rows, same order, for every fixture); (3) the existing gameweek tests unchanged; (4) a speed guard of the same kind as `tests/test_featured.py` (a gameweek page of 10 fixtures builds in well under a second on the 223 k-row copy). No model, feature, probability or evaluation file is involved: `team_form` only reads the last five results shown as "form" next to a fixture.

## 6. What the Home banner uses instead: `GET /api/featured-fixture`

* **Fixed statement count**: 5 newest-season lookups, 5 upcoming, 5 results, at most 5 season reads (only for leagues with a shown fixture), 1 saved-forecast lookup, plus about 35 small freshness statements (about 20 ms, the same ones `/api/sync/status` runs). The count does not grow with the number of fixtures; `tests/test_featured.py` asserts that the statement count stays at or below 60 and varies by at most five (one season read per league shown) while the number of fixtures grows from 40 to 1,500, and that the lists are bounded.
* **Plans**: every query is anchored on `idx_matches_key (competition_key, season)`. A unary plus on `status` and `kind` (`+m.status='scheduled'`) stops the planner from choosing the store-wide (status, match_date) index, which is exactly the trap of section 3.2. Tests assert `SEARCH ... idx_matches_key`, no `SCAN`, and no `idx_matches_status_date` in any statement.
* **No N + 1**: eligibility and reliability come from one season read per league involved and pure Python (`gameweeks.assess`), not from one query per team.
* **Cache**: 60 s per `(comp, upcoming, results, UTC date)`, dropped when the store file changes (size and mtime fingerprint, checked at lookup and after a build) or a synchronisation stores results; `ETag` and `Cache-Control: private, max-age=60`; `If-None-Match` gives `304` with no body.
* **Read-only**: opened with `mode=ro`; the test hashes the store before and after. No model is imported or called; `gameweeks.latest_forecasts` only reads forecasts that already exist.

Measured over HTTP against the running backend on the private copy, new connection per request (`http_timing.py`, `2026-10-27 05:56 UTC, machine idle`):

| Request | Time | Notes |
|---|---|---|
| `GET /api/featured-fixture`, first request | 46 ms | `X-FootIQ-Cache: miss`, 13,010 bytes |
| uncached builds (15 different parameter pairs) | median 54 ms, min 37, max 81 | each its own cache key |
| repeated request, cache hit (30) | median 27 ms, max 32 | |
| conditional request, `304` (30) | median 15 ms | no body |
| the league overview: `seasons` / `coverage` / `dashboard` (EPL) | 31 / 45 / 47 ms (medians) | the other three requests of the Home page |
| for comparison: `GET /api/gameweek` (EPL matchday 9, one request) | 2,878 ms | what the banner would have cost |

A request for the 91-byte `seasons` list takes 31 ms in this client, so about 27 to 30 ms of every figure above is the cost of a new connection and the client, not of the endpoint: a cached answer is at that floor and an uncached build adds roughly 25 ms to it. A browser reuses its connection. Earlier today, in-process with the test client on a busier machine, an uncached build took about 110 ms and the very first request after the server started 269 ms (cold file cache, first build); the byte counts are 8,250 for `upcoming=1`, 13,010 for the default `upcoming=8` and 15,747 for `upcoming=12` (no compression is configured).

## 7. The live contract test and its timeout

The live test `gameweek endpoints` in `tests/live-api.test.js` is unchanged. It calls `/api/gameweek` once and fails on vitest's default 5 s timeout whenever the endpoint takes longer, as it did at the P4.1 checkpoint (10.5 s) and as it would under the CPU load of section 3.3 (5.8 s). On a quiet machine the request takes about 2.9 s, so the whole live suite passes with default timeouts: on 2026-10-27, with the backend idle, **297 of 297 tests passed** (`--no-file-parallelism`, no timeout flag) and that test took 2.5 s. That is luck about the machine, not a fix: raising the timeout (`--testTimeout=40000`) would only let a slow endpoint pass, and this report does not count it as a performance remedy. With variant B (0.26 s) or D (0.02 s) the default timeout would be safe again. The new live test for the Home endpoint has a latency guard (first request under 2 s, cached request under 0.5 s; it took 266 ms in total, including the ten read requests that prove nothing was saved) so that a move to a slow query is caught at once.

## 8. Reproduction (all read-only; private copies only)

| Script (`data/supervised/phase4/p42/`) | What it does |
|---|---|
| `perf_store_inspect.py` | sizes, indexes, plans and timings of every statement of the gameweek view |
| `perf_gameweek_profile.py` | cProfile and statement trace of `gameweek_fixtures` |
| `perf_gameweek_experiments.py` | variants A to D, rows visited, equivalence on 7,008 calls |
| `perf_gameweek_endtoend.py` | 10 gameweeks end to end with each variant, payload comparison |
| `perf_other_endpoints.py` | the other endpoints, for completeness |
| `perf_load_sensitivity.py` | one `team_form` call repeated, labelled by what else the machine was doing |
| `perf_cpu_contention.py` | the same `/api/gameweek` request idle, with 24 busy processes, and idle again (the busy processes are always terminated) |
| `featured_check.py`, `featured_profile.py`, `featured_http_check.py`, `http_timing.py` | the new endpoint: correctness on the copy, where its time goes, HTTP behaviour, HTTP timings |

Run them with `FOOTIQ_STORE_PATH=data/supervised/rehearsal/phase4_p42.sqlite .venv/Scripts/python.exe -X utf8 <script>`. Each script refuses to run unless the path is inside a `rehearsal` folder.
