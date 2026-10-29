# Phase 4.8D Stage 1 Checkpoint Report: Safe Results Import and Supervised Scheduler Trial

Date: 2026-10-27. **Six results were imported into production, exactly as approved, nothing else. `live_enabled` is false, the production scheduler is disabled and no unattended synchronisation exists. No network request was made in this stage (all work used the saved, SHA-256-verified snapshots of 2026-10-27). Frozen models, saved forecasts and the official prospective records were not touched. Nothing was staged, committed or pushed (HEAD `970f461`).** Stage 2 was not started.
Evidence: `data/supervised/phase4/p48d/` (checkpoints, reports, JSON), `data/backups/`, `data/supervised/phase4/p48c/db_baseline_v3.json`. Related documents: `P4_8C_DB_BASELINE.md` (addendum: baseline v3), `P4_8D_CONFLICT_EVIDENCE_TABLE.md`, `P4_8D_ACTIVATION_PLAN.md`.

## 1. Provenance fix and regression results

**The bug (found in the 4.8C rehearsal):** `match_sources` keeps one row per `(source, source_ref)`. After the 25 October import each OpenLigaDB row was a *confirmation* pointing at the 25 October snapshot; when a later snapshot supplied the result, the "insert or ignore" kept the old row, so the result named the wrong snapshot.

**The fix (`app/store/sync.py::_link_source`):** the provenance model supports exactly one row per source reference, so history is kept inside it: no row → insert; a *confirmation* row of the same match whose result is now supplied by a different snapshot → upgrade to *primary*, point at the new snapshot and time, and **append** the old role, snapshot and time to the `provenance` text; every other case (same state again, a later confirmation, a row of another match, an existing primary) is left untouched. No row is deleted or created by the upgrade; other sources' links are never touched.

| Regression test | Result |
|---|---|
| initial import writes a link to the supplying snapshot | passes |
| confirmation → primary upgrade keeps its history and leaves unrelated rows byte-identical | passes |
| repeated import changes nothing; a later confirmation never downgrades | passes |
| updated source: an existing primary is not rewritten; a different match is never repointed | passes |
| rollback restores the old link exactly | passes |
| real replay path: newly completed results point at the live snapshot, keep the earlier provenance text, other sources unchanged (`test_refresh_integration.py`) | passes |

No schema or historical-data inconsistency appeared (the logical hash includes every table's schema text and it is unchanged apart from the data; 224,519 links before and after; 0 links point at a missing match). **A second defect was found by the scheduler trial and fixed with a test:** 'skipped_live_disabled' diary rows (3 exist in production history) were counted as failed attempts by `next_due`, which would have postponed the first real check by 24 hours; they are now ignored.

## 2. Preconditions, backup and restore verification (both imports)

| Check | Bundesliga (run 9) | La Liga (run 10) |
|---|---|---|
| Production path and size | `data/footiq.sqlite`, 228,655,104 bytes | 228,659,200 bytes |
| Physical hash equals the recorded state | yes (`3641e4da…3922`, baseline v2) | yes (`40f4475c…309b`, Bundesliga checkpoint) |
| Logical hash equals the recorded state | yes (`e32d759b…f29d`) | yes (`f66de934…ca07`) |
| `PRAGMA integrity_check` | ok | ok |
| Git | nothing staged, HEAD `970f461` | same |
| `live_enabled` | false | false |
| Concurrent writers | no app/test process; an exclusive lock could be taken | same |
| Snapshot hash equals the approved one | `b725c2f3…6b46` | `efe9e2a9…1508` |
| Backup (SQLite online-backup API from a read-only connection) | `data/backups/footiq.20261027T141608Z.pre-bundesliga.sqlite`, integrity ok, logical hash equals production | `…T141855Z.pre-laliga.sqlite`, same |
| Restore to a private database | opened: integrity ok, 223,510 matches, logical hash equal | same |
| Reconciliation on the restored copy before touching production | exactly 2 records, 0 problems | exactly 4 records, 0 problems |
| Import | one transaction, post-condition checked inside, then commit | separate transaction and checkpoint |

(Each step also created one earlier "check" backup; four backups exist. A backup file has a different byte layout from the live file, so its physical hash differs while its logical hash equals production's.)

## 3. Exact production row changes

Only the allow-listed source records were ingested (not the other 304 Bundesliga or 376 La Liga records), with date protection on; a run in each case ended `inserted 0, updated N, unchanged 0, confirmed 0, quarantined 0`.

| Run | Match (stored record) | Before → after |
|---|---|---|
| 9 | Hoffenheim v Leverkusen, 2026-10-25 (`…bundesliga:2026-27:L110`) | scheduled → **completed 3–0**, outcome H |
| 9 | Freiburg v Bayern München, 2026-10-25 (`…L111`) | scheduled → **completed 1–3**, outcome A |
| 10 | Athletic Club v Getafe, 2026-10-25 (`espana:1-liga:2026-27:L179`) | scheduled → **completed 4–0**, outcome H |
| 10 | FC Barcelona v Real Madrid, 2026-10-25 (`…L182`) | scheduled → **completed 1–2**, outcome A |
| 10 | Celta de Vigo v Real Betis, 2026-10-25 (`…L184`) | scheduled → **completed 0–0**, outcome D |
| 10 | Real Sociedad v Levante, 2026-10-25 (`…L185`) | scheduled → **completed 2–1**, outcome H |

Fields changed per row (and no others): status, home/away goals (final and 90-minute), `label_90_status` confirmed, outcome, `rated`, `regular`, `in_universe`, the two model entity ids, `source_system` openfootball → openligadb, `licence` CC0-1.0 → ODbL-1.0. Other tables: `source_snapshots` +1 per run (the snapshot, with its hash), `sync_runs` +1 per run (runs 9 and 10, 0 requests), and **six `match_sources` links upgraded in place** (confirmation → primary, new snapshot, history appended). Unchanged: 223,510 matches (0 deleted), 273 quarantine rows, 7,447 aliases, 224,519 links, forecast tables empty, simulation runs 0. The five date-disputed La Liga results, the 55 date disagreements, the two score conflicts and the five Premier League status rows were **not** touched.

## 4. Updated standings and recent form (production now)

**Bundesliga (7 matches played each):** Bayern 14 → 17 points, rank 2 → 1 (form DWWDW → WWDWW); Dortmund 17, rank 1 → 2; Hoffenheim 6 → 9, rank 14 → 10 (LWLLW → WLLWW); Leverkusen 13, rank 4 (WDWWW → DWWWL); Freiburg 13, rank 3 (WWDWL → WDWLL); Paderborn, Köln, Frankfurt, Hamburg each drop one place.
**La Liga:** Real Madrid 21 → 24, rank 3 → 2 (WWLWW → WLWWW); Real Sociedad 16 → 19, rank 5 (WLWWW → LWWWW); Athletic 9 → 12, rank 13 → 7 (WDDDL → DDDLW); Betis 19 → 20, rank 4 (WWDWL → WDWLD); Celta 11 → 12, rank 8 (DDWDW → DWDWD); Barcelona 27, rank 1 (WWWWW → WWWWL); Getafe 9, rank 15 (DLWLD → LWLDL); Levante 10, rank 11 → 12 (LLDDW → LDDWL). Several other clubs move one place only because of these results.
The Leagues, Matches and Compare pages read the same store, so they show these results after the API restarts (its caches are cleared on start); the page tests in `test_refresh_integration.py` cover this path.

## 5. Before/after predictions (private copies, same clock 2026-10-27 15:00 UTC, frozen models)

Frozen model files: club v1 `067426e8…c5b9`, v2-r1 `55c1e4c5…e65c` (unchanged; the integrity script re-verifies them). Feature schemas identical before and after (v1 25 inputs, v2-r1 62). Data cut-off moves 2026-10-24 → 2026-10-25. Production still holds **0** saved forecasts and no forecast was saved there.

| Fixture (affected team) | v1 home / draw / away before → after | v2-r1 before → after | What changed |
|---|---|---|---|
| Bayern München v Dortmund, 2026-10-31 | 69.6 / 16.7 / 13.7 → 70.4 / 16.5 / 13.0 % | 68.9 / 18.3 / 12.8 → 69.8 / 17.8 / 12.4 % | Bayern's last result is now a 3–1 win at Freiburg |
| Werder Bremen v Hoffenheim, 2026-10-31 | 39.2 / 23.6 / 37.3 → 35.6 / 24.0 / 40.4 % | 40.9 / 26.3 / 32.8 → 36.5 / 27.5 / 36.0 % | Hoffenheim: `ppg5` 1.2 → 1.8, Elo 1723 → 1745, 571 prior matches (+1), rest days 13 → 6 |
| Leverkusen v Stuttgart, 2026-10-31 | 56.7 / 19.2 / 24.0 → 52.5 / 19.5 / 28.0 % | 53.8 / 24.4 / 21.8 → 49.5 / 25.3 / 25.3 % | Leverkusen lost 0–3 |
| Getafe v Sevilla, 2026-11-01 | 42.0 / 29.1 / 28.9 → 38.9 / 28.5 / 32.7 % | 43.3 / 30.6 / 26.1 → 41.5 / 29.6 / 28.9 % | Getafe: `ppg5` 1.0 → 0.8, Elo 1636 → 1623, rest days 13 → 7 |
| Athletic v Real Sociedad, 2026-11-01 | 42.5 / 28.0 / 29.5 → 46.0 / 26.7 / 27.3 % | 46.9 / 28.4 / 24.7 → 49.7 / 27.8 / 22.5 % | both sides gained a result (Athletic 4–0, Sociedad 2–1) |

Of 9 Bundesliga and 10 La Liga fixtures, 4 and 7 have changed inputs (v1 8–18 of 25, v2-r1 33–48 of 62); the largest probability move is 4.3 points (Bundesliga) and 3.7 points (La Liga). A fixture's inputs use only results before its date; missing results stay absent (never a loss). **Past fixtures:** Bundesliga matchday 7 and La Liga matchday 10 (played 25 October) are refused for any new pre-match forecast ("no fixture that can still be forecast before kickoff"). No arbitrary streak penalty exists and no model was trained.

## 6. Scheduler trial (**replayed-snapshot trial; no real network request was made**)

Setup: a private copy of production *as it was before the imports*, an isolated snapshot/ledger folder, a mocked clock, the approved A1 snapshot served by an in-process stand-in for OpenLigaDB, and **all socket connections blocked** during the trial (0 attempts occurred, 29 replayed requests). The real scheduler and `config/sync.json` (`live_enabled: false`) were not used or changed. This is **not** validation against the live network.

| Behaviour | Evidence |
|---|---|
| Disabled scheduler | no thread, `skipped_live_disabled` returned, database file hash and every table hash unchanged, 0 requests |
| Due logic | with no real check in the last 6 h the first check was due immediately (the real last check was 2026-10-25 08:38Z); after one cycle the next due time is exactly +6 h; 5 h 59 min → not due, 6 h 01 min → runs |
| One supervised cycle | 5 replayed requests (current matchday, change dates, matchdays 6 and 7); the same 2 Bundesliga results imported; change callback fired once; the two source links upgraded to primary |
| Idempotency | the next cycle made 3 requests (no changed matchday), 0 changes |
| Restart | a new manager inside the interval: not due, 0 requests, file unchanged |
| Concurrency lock | a 10-minute-old `running` row → `skipped_already_running`; 30 minutes later it is marked `abandoned` and the cycle runs |
| Failure back-off | provider down: failure → next check +12 h; second failure → +24 h; recovery → +6 h; failures changed no data; both errors in `sync_errors` |
| Quarantine | a provider that contradicts what is stored (one changed score, one moved date in each of two matchdays): 4 new quarantine rows (2 `CONFLICT`, 2 `DATE_DIFFERENCE`), stored scores and dates unchanged |
| Logging | 15 `sync_runs` rows with outcomes and request counts, 2 `sync_errors`, a request ledger of 29 lines, 8 snapshot files |

## 7. Date-only fixture eligibility (isolated tests only; production rule unchanged)

Implemented in `app/kickoff_tz.py` (not imported by any endpoint): league time zones (Europe/London, Madrid + Canary Islands, Berlin, Rome, Paris) with daylight saving from the date's own offset; the **conservative evidence floor** = earliest local kickoff hour seen in stored UTC kickoffs minus 2 hours (Premier League 10:30, La Liga 12:00, Bundesliga 13:30; none for Serie A/Ligue 1, which have no UTC kickoffs); disputed dates use the earliest candidate; an unreadable date gives "unknown"; unknown competitions fall back to the global rule; it never returns or assumes a kickoff; a stated kickoff is used as it stands. 14 tests (floor, boundaries, DST, disputes, past fixtures, safety property).

Comparison on all 190 unplayed 2026-27 fixtures up to 10 November (EPL 40, La Liga 27, Bundesliga 18, Serie A 60, Ligue 1 45; 24 with a disputed date) at six clock instants (`timezone_comparison.json`):

* **Invariants hold at every instant:** a fixture with a stated UTC kickoff gets the identical answer under both rules; no past fixture ever becomes predictable.
* **Gains** appear only where the old rule blocks without need: e.g. at 2026-10-27 15:00 UTC Serie A 22 → 27 predictable (5 fixtures dated the next day, blocked since 10:00 UTC today); at 2026-10-31 11:00 UTC La Liga 14 → 15 (disputed ones excluded), Serie A 12 → 17, Ligue 1 9 → 12. Analytically a date-only Premier League fixture gains about 24 hours of eligibility (old: blocked from 10:00 UTC the day before; new: until 10:30 on the day).
* **Stricter only for a disputed fixture:** one La Liga fixture (Villarreal v Espanyol, matchday 11, `L192`, which has a date dispute) is predictable under the old rule but "unknown" under the proposal at two instants. Nothing else is stricter.
* Serie A and Ligue 1 gain the most from the zone rule alone but remain blocked from automatic refresh and still have no UTC kickoffs.

Recommendation: adopt only after you have reviewed this table; the rule stays inactive.

## 8. Baseline v3 (`P4_8C_DB_BASELINE.md` addendum, `db_baseline_v3.json`)

| | Physical | Logical (`footiq-logical-v1`) |
|---|---|---|
| v2 (history) | `3641e4da47b3930cbb543499d393b2360f1e117481ad35349b082a4682073922` | `e32d759bddef1688116c1c91430cbf10384724e525971994f4e085312a96f29d` (rows ≤ 7) |
| after Bundesliga | `40f4475ce7f9276736db83880c2c60e2cb5347884c913a2b977f04dbdc0a309b` | `f66de9343abd43d7b7b4cba1dc7fc6342ce071c723d73f25348ea074c045ca07` (rows ≤ 9) |
| **v3 (current)** | `1bfad5bd4663e70776ef9da35f5c89eeed11b1ed7274ee7fdb562e266a9cb278` | `b3dcf8c0d04aa4538da77f4dc21c267b6414bb7e3c61692ad24a0ec4c2c1d95f` (rows ≤ 10) |

The algorithm is unchanged; only the cut-off run id moves, and no business table is ever excluded. Journal mode WAL, `-wal` empty after a TRUNCATE checkpoint, `integrity_check` ok.

## 9. Feed lag and other freshness changes

`/api/sync/status` now carries `feed_lag` per league, judged by the **newest verified match date and the fixtures still missing results**, not by when the provider was last asked. With production now: Premier League "newest verified result 2026-10-12 (15 days ago); 20 fixtures past their date have no verified result (oldest 2026-10-17)"; Serie A and Ligue 1 likewise; La Liga 1 fixture (the Rayo–Athletic postponement, below). The Premier League provider note records the observation that its feed was byte-identical on 25 and 27 October. The Leagues status panel shows the lag line and the previous provider/import/attempt columns. Bundesliga: no lag (0 awaiting), but "fresh" only until 2026-10-28 08:38 UTC because its last real check was on 2026-10-25.

## 10. Conflicts, providers and blockers

* **Conflicts (all still quarantined, 273 rows):** Bournemouth–Brentford (stored 2–2, provider 2–1), Villa–Forest (provider record corrupt), 55 date disagreements (31 Premier League, 24 La Liga; five of the La Liga ones hold results back). Evidence needed for each: `P4_8D_CONFLICT_EVIDENCE_TABLE.md` and `date_disagreements_evidence_table.csv` — the official competition body's fixture list or match centre plus an independent second provider; no provider response alone resolves anything.
* **New observation:** the provider now lists Rayo Vallecano v Athletic Club (stored 2026-10-10, no result) for **2027-05-30**, a 232-day postponement. Not applied; needs La Liga's official calendar.
* **football-data.org:** the clarification email stays a draft (`P4_8C_FOOTBALLDATA_EMAIL_DRAFT.md`); no account, key or request; Serie A and Ligue 1 remain blocked from refresh.
* **Premier League:** the five status-only rows were not imported; its provider feed lags; no automatic synchronisation.

## 11. Tests, build and integrity

| Suite | Result |
|---|---|
| Backend, full (`pytest tests`) | **321 passed**, 0 failed, 1 existing warning, 16 min 21 s (4.8C: 308; +13 new: 5 provenance, 1 provenance integration, 2 scheduler/feed-lag, 5 time-zone floor). A first full run found **5 failures** in `test_seasonsim_service.py`: those tests start from a copy of the production store and pin its remaining-fixture counts (Bundesliga 245, La Liga 291); the approved imports legitimately lowered them to 243 and 287, so I updated those expected numbers (and nothing else) and re-ran the whole suite |
| Frontend, no backend | **344 passed, 13 skipped** (357 tests) |
| Frontend, live backend on a private copy of the post-import store | **357 passed, 0 skipped** |
| Production build | passed, 648 modules |
| Integrity script (`p48d/integrity_final.json`) | baseline v3: physical `true`, logical `true`; v2 reads `false` as expected; production `integrity_check` ok, `simulation_runs` 0; `live_enabled` false; `scoreline_method` null; frozen model files and prospective-evaluation files unchanged (only `config/sync.json`, your approved 6-hour interval, differs from the frozen list); backend-source differences are exactly the expected list; nothing staged |
| Production file after everything | `1bfad5bd…cb278`, modified only by the two imports (its `-wal` is empty) |

All private copies I created were deleted; the four backups in `data/backups/` were kept.

## 12. Readiness for Stage 2

**Ready:** the guarded import tool, backups and baseline procedure are proven on two real imports; the scheduler logic is proven in a replayed trial. **Not ready for unattended production sync.** Before enabling the Bundesliga schedule I recommend: (1) a supervised **real-network** cycle for the Bundesliga only (about 3–5 requests, on a private copy first), which needs your separate approval; (2) a decision on the time-zone rule; (3) a monitoring addition (consecutive-failure count visible in the panel); (4) restarting the API so Home and Matches pick up the new results (their caches are cleared on start). Premier League, La Liga, Serie A and Ligue 1 stay out of the scheduler.

## 13. Decisions requiring your approval

1. Approve a supervised real-network scheduler cycle for the Bundesliga on a private copy (about 3–5 requests; the replayed trial does not validate the network).
2. Accept baseline v3 as the production baseline (or request changes).
3. Adopt, adopt with the floor, or keep the old rule for date-only fixtures after reviewing §7.
4. Whether to send the football-data.org email (draft ready) — you send it.
5. Authority to seek the official evidence for the two score conflicts and the Rayo–Athletic postponement (a person reading the official sites; nothing from a provider alone).
6. Whether to restart the API now so the application shows the new results.

---

## What We Did, Problems Faced, and How We Solved Them — Explained Simply

**The small bug first.** Each result in our database has a note saying where it came from. When the new results arrived, the note still pointed at the *old* download, like a receipt that names the wrong shop. We changed the rule: when a new download supplies a result that an old one had only "confirmed", the note now points to the new download and keeps the old line written underneath, so nothing is lost. We tested it five ways, including making sure a failed import leaves the old note exactly as it was.

**Before touching the real database.** We checked that its fingerprint matched what we had recorded, that nothing else was using it, and that Git had nothing waiting. Then we made a safe copy using SQLite's own backup tool, proved the copy was identical in content, opened it in a private place, and practised the import on that copy first. Only when the practice gave *exactly* the two expected changes did we do it for real, as one all-or-nothing step. Then we did the same, separately, for La Liga's four results.

**What changed.** Six games got their scores: Hoffenheim 3–0 Leverkusen, Freiburg 1–3 Bayern, Athletic 4–0 Getafe, Barcelona 1–2 Real Madrid, Celta 0–0 Betis, Real Sociedad 2–1 Levante. Bayern are now top of the Bundesliga table; Real Madrid are second in La Liga. We did not touch the five games with disputed dates, the two disputed scores, or the Premier League.

**Do the predictions react?** Yes, a little, as they should. For example, Hoffenheim's recent form went from 1.2 to 1.8 points per game, and the chance of Hoffenheim winning at Werder rose from 37% to 40%. The predictions we saved before stayed exactly the same, and games that have already started cannot get a new "before the match" prediction.

**A bug the practice run caught.** We tested the automatic checker on a copy, with the internet switched off and an imitation of the data service. It worked: it ran once, imported the results, waited six hours before checking again, waited longer after failures, refused to run twice at once, and put contradictory data in the "needs a human" list instead of overwriting. But it also showed that three old "I was switched off" diary lines made the checker think it had failed, so it would have waited 24 hours for no reason. We fixed that and added a test. We are clear that this was a *pretend* trial: no real internet check has been made yet.

**Time zones.** If we do not know when a match starts, the app currently stops predicting about 14 hours before the date. We wrote and tested a smarter version that uses each league's real time zone and the earliest start time ever seen in that league (minus two hours of safety). It never guesses a start time and is stricter when dates are disputed. We compared it with the old rule on 190 upcoming games: it never changes a game that has a known start time, never makes a past game predictable, and only opens a longer window. It is not switched on.

**What we did not do.** No internet requests, no automatic production sync, no changes to models, saved predictions or the disputed data, and no account with football-data.org.

**30–60 second viva summary.** "We first fixed a provenance bug so an imported result names the snapshot that supplied it and keeps its history. We then imported six verified results into production in two separate, all-or-nothing transactions, each preceded by checks of the database hashes, Git state and concurrent writers, and a SQLite online backup that we restored and verified. Only the six approved rows changed; standings, recent form and the next predictions updated, saved forecasts stayed identical, and we recorded a new two-part baseline. A replayed scheduler trial on a private copy, with the network blocked, validated the six-hour logic, restarts, locking, back-off and quarantine, and revealed a bug with legacy diary rows that we fixed. The time-zone rule was implemented and compared in isolation only. The disputed scores and dates stay quarantined until official evidence is read, and the real-network scheduler trial is the next step."
