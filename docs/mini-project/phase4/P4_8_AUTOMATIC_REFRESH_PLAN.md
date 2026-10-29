# Phase 4.8A: Automatic Refresh, Source Reconciliation and Form-Aware Prediction Plan

Status: **plan only** (audit, design, documentation). Written 2026-10-27. Nothing was implemented, no network request was made, no key was registered, no data was imported, the production store, frozen models and configuration were not touched. Every claim below was read from code or stored reports in this repository; items I could not verify are marked **UNVERIFIED**.

## 1. What exists today (audit)

| Area | Finding | Evidence |
|---|---|---|
| Sync framework | `SyncManager` in `app/store/sync.py` already has a start-up check and a periodic loop (`periodic_minutes`, default 60, minimum wait 60 s) in its own thread, started from the FastAPI lifespan (`app/main.py:64-70`) | code |
| Switch | `config/sync.json`: `live_enabled: false`, `startup_check: true`, `periodic_minutes: 60`, `stale_after_hours: 72`; only `openligadb` / `BUNDESLIGA` is configured | file |
| Approved provider map | `APPROVED` holds **one** entry: Bundesliga via OpenLigaDB (`bl1`, season 2026) | `sync.py:37` |
| With the switch off | A check records one `sync_runs` row (`skipped_live_disabled`), makes no request, marks data stale where applicable. This is also the cause of the production-store change found in Phase 4.7 (one row per start; WAL mode) | `sync.py:283-285`, Phase 4.7 testing report |
| Safeguards in the framework | Idempotent upsert; played-match dates protected; conflicts go to quarantine; one transaction per run; request ledger; snapshots in `data/snapshots`; `source_state`; contact string required by the adapter | `sync.py` header, `OPENLIGADB_PL_LALIGA_FINDINGS.md` |
| After new results | `_after_sync_change` reloads the analytics view, clears the Home and Matches caches, and rebuilds the club prediction *history* (not the model weights) | `main.py:50-56` |
| Freshness | `sync.status` calls data stale after 72 h, "awaiting results" when fixtures are past, "no approved source" for leagues outside `APPROVED` | `sync.py:209-240` |
| Adapters | Exist for OpenLigaDB under `FootIQ_Club_Model_Development_v2/source_adapters_r1`; a Premier League / La Liga import was rehearsed on private copies only | findings and rehearsal reports |

**Conclusion of the audit:** the *mechanism* for periodic refresh already exists and is switched off. Phase 4.8 is therefore mostly about (a) deciding sources, (b) hardening reconciliation, (c) making the schedule and its state visible, not about writing a scheduler from nothing. The one side effect to fix first is that a disabled sync still writes a `sync_runs` row on each check and the first open switches the file to WAL (see 4.8B item 1).

## 2. Why the data is old, in one table

| League | Newest result in store | Why | Approved automatic source |
|---|---|---|---|
| Bundesliga | freshest (2026-10-24) | A reviewed OpenLigaDB snapshot was imported (Phase 1/2) | OpenLigaDB, in `APPROVED`, but live access OFF |
| Premier League | older | Only the openfootball (CC0) history was available; OpenLigaDB coverage was investigated and rehearsed but not approved for production | **Not approved** (candidate: OpenLigaDB, see §3) |
| La Liga | older | Same; La Liga verification still pending | **Not approved** (candidate only) |
| Serie A | older | No tested free source | **BLOCKED** |
| Ligue 1 | older | No tested free source | **BLOCKED** |

(Exact newest dates per league are shown by `/api/competitions` and the Home chips; I did not hard-code them here so this table cannot go stale.)

## 3. Provider matrix

| League | Candidate | Licence / terms | Key needed | Status | What blocks it |
|---|---|---|---|---|---|
| Bundesliga | OpenLigaDB | Community data, attribution; contact string required by our adapter | No (UNVERIFIED for rate limits; none read) | **READY after approval** | Only your approval to flip `live_enabled` and a real contact string |
| Premier League | OpenLigaDB (if it carries the league) | As above | No | **CONDITIONAL**: the rehearsal found mismatches (e.g. the Bournemouth v Brentford case) | Resolve the quarantined items; approve aliases and date rules |
| La Liga | OpenLigaDB (if it carries the league) | As above | No | **CONDITIONAL / PENDING** | `LALIGA_VERIFICATION.md` open items |
| Serie A | football-data.org free tier is the obvious candidate | Free tier is rate-limited; terms must be read; **I have not read them** | Yes (registration) | **BLOCKED** | Needs your explicit authorisation to register or to read terms; see `FOOTBALL_DATA_ORG_CHECKLIST.md` |
| Ligue 1 | Same as Serie A | Same | Yes | **BLOCKED** | Same |

Rule: a league without an approved provider stays "no approved source" in the UI. We do **not** scrape sites and we do **not** copy Google or any website's standings.

## 4. Refresh design (what will happen every 6 hours)

Proposed default `periodic_minutes: 360` (your suggestion; the loop already supports it). Each cycle, per approved league only:

1. Read `source_state` (last successful fetch, last season/round fetched).
2. Request only what is needed: the current season's current and next matchday, plus any stored fixture that is past its date without a result. Never the whole history.
3. Save the raw response as a snapshot and write the request ledger row *before* parsing.
4. Parse and normalise into candidate rows (source id, kickoff as given, status, score, source URL).
5. Reconcile each candidate against the stored match (see §5). Each outcome is one of: `insert_new_fixture`, `add_result_to_unplayed_fixture`, `unchanged`, `quarantine_conflict`.
6. Apply the accepted rows in **one transaction** together with the `sync_runs` row; if anything raises, roll back everything.
7. Only if rows changed: reload the standings view, clear the Home and Matches caches and rebuild the form history (existing `_after_sync_change`). Forecasts already saved are never rewritten.
8. Expose the result at `/api/sync/status` and in the UI (§8).

Network failure: the cycle ends with state `failed_network`, nothing is written except the `sync_runs` row, the app keeps serving stored data, marks it stale after 72 h, and retries at the next interval with a simple back-off (no tight retry loop). The app must start and work with no internet.

## 5. Reconciliation rules (strict)

* **Identity** is by an alias table that *you* approve (source team id → our team key). **No fuzzy matching ever approves an import.** An unknown name goes to quarantine as `unmapped_team`.
* A fixture matches only on competition, season, home team, away team and either matchday or a date within an approved window.
* **Add result to an unplayed fixture:** allowed automatically when the match is identified exactly and the source marks it finished with a full-time score.
* **Existing verified score differs from the source:** **never overwritten.** The candidate is quarantined as `score_conflict` with both values, both source URLs and times; a human decides.
* **No "newest wins".** Recency is never a tie-breaker.
* **Played-match date** is never changed without evidence from a second approved source or a human decision.
* **Postponed / moved fixtures** (unplayed): the date may be updated only when the source states the new date explicitly; the old date is kept in a history column.
* **Two sources disagree:** both are kept as candidates; the match is shown as "disputed" in the Matches hub with no score used in standings or form until resolved.
* A source that returns fewer rows than before never causes deletions.

## 6. Failure and safety cases

| Case | Behaviour |
|---|---|
| No internet / DNS failure | Cycle logged `failed_network`; app works; freshness chip says "Last successful update … (check failed)" |
| Provider returns 429 or 5xx | Back off to the next interval; never retry immediately; ledger row recorded |
| Provider returns malformed data | Whole payload rejected, snapshot kept, `failed_parse`, zero rows written |
| Source revokes or changes terms | Remove the entry from `APPROVED`; league reverts to "no approved source" |
| App stopped for days | First cycle after start catches up using the "past-date without result" rule |
| Two app instances | A lock row in the store prevents overlapping runs (to be added in 4.8B) |
| Disabled sync writing to production | Fix in 4.8B: when `live_enabled` is false, skip writing the `sync_runs` row and avoid forcing WAL on read-only use |
| Clock wrong on the machine | Freshness uses UTC and shows the timestamps; no decision is made from the browser clock |

## 7. Recent-form-aware predictions: audit

**Question:** if a team has just lost, or results are missing, do the forecasts react?

| Model | Uses recent form? | How |
|---|---|---|
| Elo-only baseline | Indirectly | The rating is updated after every match, so a defeat lowers it by an amount that depends on how surprising it was |
| Club v1 (25 features) | **Yes** | Elo difference plus form windows counted by *number of matches* over rated matches (points, goals for/against per match, results over the last 5 and 10 games), rest days, and history depth. Its coefficients were read from the stored v1 JSON |
| Club v2-r1 (62 features, 66 inputs) | **Yes, more** | Adds an opponent-adjusted performance rating over 10 matches (`perf10`) and counts of how many results are known in the last 7, 14 and 30 days (`n_known_7/14/30`), so a gap in data is visible to the model |
| Streak features | **None** in either model | There is no "lost 4 in a row" variable; a streak only matters through the window averages and the Elo drop |

**Effect of stale or missing results.** Missing matches are *absent*, not treated as losses or draws. So a team whose last three results are not in the store is described by its older results: the 5- and 10-match windows reach further back. The forecast is then "based on an older picture of the team". v2-r1 can see the gaps (`n_known_*`); v1 cannot. This is why Home and Predictions already flag "provisional history".

**How new results reach the inputs.** After an accepted import the form history is rebuilt in date order, Elo is replayed, and every later forecast uses the longer history. Previously saved forecasts keep their original cutoff and are not changed.

**Leakage rules (must hold in any change).** Only results strictly before the fixture's day are used; fixtures are forecast day by day; a saved forecast records its cutoff and `made_before_kickoff`.

### Worked example (hypothetical numbers, not real teams or results)

Two sides, A (home) and B (away), identical in rating. B's last five matches are five defeats in the stored data, A's are mixed.
* Using the frozen v1 coefficients with those hypothetical inputs, the home-win probability moves up and the away-win probability moves down relative to the no-form case, by a few percentage points (I computed this read-only from the stored coefficients; the exact digits depend on the invented inputs and are illustrative only).
* The same input, but B's last two results *missing* (store stale) gives B's form from older, better matches and the forecast does **not** reflect the recent slump.

### Why a bad streak does not guarantee another defeat

Football outcomes are noisy; even the best model is right about half the time on three outcomes. A weak run is evidence, not a rule: it nudges the probabilities and the draw and upset chances stay. We do not hand-reduce any team's probability, and we do not invent results for missing matches.

### Leakage-safe evaluation plan (only if a change is wanted)

1. Freeze the question: does adding "streak" or "points in last 3" features improve log loss over v1?
2. Use the existing chronological splits; features from matches before each fixture's day only.
3. Predeclare the metric (log loss, then Brier), the margin that counts as an improvement, and the leagues; do not tune on the test years.
4. Compare to v1 and v2-r1 on the same rows with a paired bootstrap, as in the v1 report.
5. Prospective check: log forecasts before kickoff and score them later; the existing prospective records stay untouched.

### Experimental-model proposal (decision, not implementation)

My assessment: **no new model is needed now.** The existing features already encode recent form; the larger problem is *stale inputs*, which automatic refresh solves. A "form-extended" candidate (adds last-3 points, a loss-streak count and days-since-last-known-result) would be justified only if, after refresh is running, v2-r1's `n_known_*` gaps still show a measurable loss on the evaluation above. It would be a **new, separately named experimental model** with its own files and hashes; v1, v2-r1 and the saved predictions would not be altered.

### UI fields proposed

On each forecast card: "Form window: last N known results (date range)", "Known results in last 30 days: n" with a warning when low, "Data newest: date · last refresh: time", and the existing provisional chip. Wording: *"This forecast uses results up to <date>. Newer results are not yet in the system."*

## 8. UI plan for refresh status

Footer or Home chip: "Last checked <time> · last new result <date> · next check in <h>". Per league: Fresh / Stale / Awaiting results / No approved source / Update failed (network). A quarantined-items counter links to a read-only list ("3 results need review"). No button triggers an import; a manual "check now" may be offered in 4.8C only if approved.

## 9. Checkpoints (each needs your separate approval)

| Step | Scope | Output | Touches |
|---|---|---|---|
| **4.8A** (this document) | Audit, design, plan | This file | Docs only |
| **4.8B** | Offline implementation on a **private copy**: reconciliation rules with an offline fixture of recorded responses, run lock, quiet disabled mode (no `sync_runs` write, no forced WAL), freshness states, status API fields, tests. No network | Code + tests + report | `app/store/*`, tests |
| **4.8C** | UI for refresh status, quarantine count and form-window fields | Frontend + tests + screenshots | `frontend/` |
| **4.8D** | Controlled live trial for **one approved league** (Bundesliga) on a private copy, 6 h interval, then your decision on production | Trial report | Config on the copy; production only if you approve |

## 10. Decisions I need from you

1. Approve 4.8B (offline implementation).
2. Accept the changed production store hash (WAL + one log row) or choose another remedy.
3. Interval 6 h (default proposed).
4. Provider approvals per league; permission (or not) to read the football-data.org terms for Serie A and Ligue 1.
5. Alias list and the Bournemouth v Brentford resolution rule.
6. Whether a form-extended experimental model is wanted at all (my recommendation: not yet).

## 11. What stays untouched

Frozen models and hashes; the prospective-evaluation records; saved forecasts; `config/season_sim.json` (`scoreline_method: null`); `live_enabled: false` until you approve 4.8D; no commits.

## 12. What We Did, Problems Faced, and How We Plan to Solve Them — In Simple Words

**Why are the standings old?** The app was built from files of past results. It stores them in its own database and has no permission to look at the internet yet, so it only knows matches up to the day we last loaded data.

**Why is the Bundesliga fresher?** For that league we found a free community source, checked it carefully and loaded it. The other leagues have no checked source yet, and for Serie A and Ligue 1 we have not found an approved one.

**How will automatic refresh work?** A small background job wakes every 6 hours, asks an approved source only for matches that might have changed, saves what it received, compares it with what we already have, and adds only results it can match exactly.

**What is an API?** A way for one program to ask another program for data in a fixed format, like a waiter taking an order to the kitchen. Our app would ask the source's API "what are the results of this matchday?"

**What happens every 6 hours?** Check, save the raw reply, compare, add new results, update the table, show "last checked" on screen. If the internet is down, it just says so and tries again later.

**How do new scores update the table?** The standings are calculated from stored results, so when a result is added the table is recalculated. Forecasts also use the longer history afterwards.

**What if two sources disagree?** We do not pick the newest and we do not guess. The disagreement is set aside for a person to check, and that match is not counted until it is resolved. A score we have already verified is never silently overwritten.

**What if there is no internet?** The app keeps working with stored data and warns that it may be old.

**Why not copy Google's standings?** Copying a website is not allowed by most terms, can break, and we could not prove where each number came from. We keep an approved, recorded source for every result.

**Why do the models stay frozen?** The models are tested on past data. Changing them every time a result arrives would make the test scores meaningless. Only their *inputs* (the latest results) refresh; their rules do not change.

**Does recent form matter?** Yes: both club models look at how a team did in its last matches. A bad run lowers the estimate a little, but it never guarantees another loss, because football is unpredictable. If recent results are missing, the model uses older ones, so keeping data fresh is the real fix.

**Work done / remaining.** Done: stored database, safe sync framework (switched off), freshness warnings, tests. Remaining: choose sources, build the safe 6-hour job on a copy, show refresh status, trial with one league.

**30–60 second viva explanation.** "Our data is historical because live access is off by design. We already built a safe sync framework with snapshots, a request log, quarantine for conflicts and one-transaction imports. For automatic refresh we would turn it on only for approved sources, starting with the Bundesliga, every six hours. Results are added only when teams and fixtures match exactly; a conflicting score is never overwritten, it is set aside for review. The models are frozen and keep their test scores, but they read the latest results as inputs, so predictions reflect recent form once the data is fresh. If the internet fails the app keeps working and says its data may be old."
