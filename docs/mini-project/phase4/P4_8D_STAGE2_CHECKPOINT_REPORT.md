# Phase 4.8D Stage 2 Checkpoint Report: Supervised Live Synchronisation and Final Integration

Date: 2026-10-27. **Unattended synchronisation is not enabled (`live_enabled: false`). No production result was imported in this stage. Five external data requests were made in total, all to the approved Bundesliga endpoints (R1 earlier; R2–R5 in the polling follow-up, §3a). Frozen models, saved forecasts and the official prospective records were not touched. Nothing was staged, committed or pushed (HEAD `970f461`). Stage 3 was not started.**
Evidence: `data/supervised/phase4/p48d/`, `data/snapshots/p48d_trial/`. Related: `P4_8D_STAGE2_REQUEST_LEDGER.md`, `P4_8D_STAGE2_OFFICIAL_EVIDENCE_TABLE.md`, `P4_8C_FOOTBALLDATA_EMAIL_DRAFT.md` (final draft), `P4_8C_DB_BASELINE.md`.

## 1. Baseline v3 accepted

Recorded as the current approved production baseline (`data/supervised/phase4/p48c/db_baseline_v3.json`, unmodified in this stage):

* Physical SHA-256: `1bfad5bd4663e70776ef9da35f5c89eeed11b1ed7274ee7fdb562e266a9cb278`
* Logical SHA-256 (`footiq-logical-v1`, `sync_runs` rows ≤ 10): `b3dcf8c0d04aa4538da77f4dc21c267b6414bb7e3c61692ad24a0ec4c2c1d95f`

Baseline v2 (`3641e4da…3922` / `e32d759b…f29d`) is preserved as history, and so are the four verified backups in `data/backups/`. After everything in this stage, including an API restart, both v3 hashes still match (integrity script: `physical_sha256_matches: true`, `logical_sha256_matches: true`). Nothing was changed to make a test pass.

## 2. Saved forecast history investigation (read-only)

**Question:** earlier reports mention 27 saved forecasts, Stage 1 says production has none.

| Finding | Evidence |
|---|---|
| The **27** are 9 fixtures × 3 model variants (club v1, v2-r1, Elo) saved by my rehearsal scripts into **private temporary copies** of the store (the 4.8B refresh demo and the 4.8C Bundesliga rehearsal, matchday 8 as of 2026-10-19), to prove that a later refresh leaves saved rows unchanged | `refresh_effect_demo.json` (`forecast_runs_kept: 2`, `saved_rows_unchanged…: true`), `bundesliga_rehearsal.json`; those temporary files were deleted by the scripts after use. The 4.8C report text "the 27 rows saved before the import" referred to that copy, not production |
| **Production never held saved forecasts.** `forecasts` and `forecast_runs` have 0 rows in `data/footiq.sqlite`, in all four 2026-10-27 backups, in both 2026-10-25 pre-import backups, in `footiq.before-sync.sqlite`, `live_test_copy.sqlite` and the Phase 4.4 `preview.sqlite`; the table hashes inside baseline v2 and v3 are identical and are the hash of an empty table (`538f1380…`, `85056977…`) | counted read-only (`mode=ro`) |
| The only store file with forecasts is `data/supervised/demo.sqlite` (2026-10-25 08:52 UTC): 1 run (EPL matchday 8, 10 fixtures × 3 variants = **30 rows**, user action "predict gameweek button", cut-off 2026-10-24) from the supervised Phase 2 demonstration; it is intact | read-only query |
| **Nothing was lost.** No file in the production lineage ever had rows that later disappeared; the sidecar-free table hashes are unchanged since the first baseline, the demo file is intact, and the prospective-evaluation files are unchanged in the integrity manifest | integrity script, hash comparison |

Nothing was restored, recreated or overwritten. I made these findings before the production-facing changes in §4 and §7.

## 3. Real-network scheduler trial, Bundesliga only (private copy)

**Request ledger (cap: 5 GETs in total):**

| # | Time (UTC) | URL | Status | Bytes | SHA-256 | Result |
|---|---|---|---|---|---|---|
| R1 | 2026-10-27 15:11:04 | `https://api.openligadb.de/getmatchdata/bl1/2026` (the approved endpoint) | **200** | 316,983 | `b725c2f3…6b46` | scheduler cycle `ok`: 0 inserted, 0 updated, 243 unchanged, 63 confirmed, 0 quarantined |
| R2–R5 | see §3a | `getcurrentgroup/bl1`, `getlastchangedate/bl1/2026/6`, `…/7`, `getmatchdata/bl1/2026/7` | done in the follow-up | | | |

The scheduler's normal polling path uses endpoints other than R1, so I stopped there as instructed. R1 ran through the real scheduler code (`SyncManager.tick`) with `max_retries` 0 (new setting, default unchanged), a strict URL allow-list and request cap, an isolated snapshot folder, `live_enabled` true only in that process, and production opened read-only for a consistent copy.

What the **real-network** cycle showed: the provider's season file was byte-identical to the one fetched 2 hours earlier (same hash), so a cycle produces no change; every one of the six imported results kept its **primary** link and its own snapshot (the new confirming snapshot did not downgrade or rewrite anything); no data table changed except the registered snapshot and the source-state record; next check due in exactly 6 hours.

What was **replayed** (saved response, network blocked, labelled as such): restart inside the interval (not due, 0 requests); a cycle after 6 h (5 replayed polling requests, 0 changes); duplicate import (no table changed, 0 duplicate record ids); a provider that is down (error, **no data table changed**, back-off 12 h, `PRAGMA integrity_check` ok); a provider that contradicts the store (4 rows quarantined, stored scores and dates unchanged). Not yet validated against the real network: the polling endpoints themselves and a real failure. Production file hash identical before and after.

### 3a. Polling follow-up (R2–R5, approved later the same day)

| # | Time (UTC) | URL | Status | Bytes | SHA-256 |
|---|---|---|---|---|---|
| R2 | 16:03:39 | `…/getcurrentgroup/bl1` | 200 | 60 | `5c9cada4…c1c7` (current matchday = **7**, so the run continued) |
| R3 | 16:03:43 | `…/getlastchangedate/bl1/2026/6` | 200 | 24 | `79111978…c6f6` |
| (replay) | | `…/getmatchdata/bl1/2026/6` served from the saved A1 snapshot, not the network | | 17,792 | `0598f661…1f68` |
| R4 | 16:03:52 | `…/getlastchangedate/bl1/2026/7` | 200 | 24 | `2ef2fa67…1277` |
| R5 | 16:03:55 | `…/getmatchdata/bl1/2026/7` | 200 | 15,878 | `6776eeb5…962d` (snapshot `20261027T160356Z_bl1_2026_md7.json`) |

Four real requests (at least 3 s apart, no retries, strict allow-list, stop-on-malformed and stop-unless-matchday-7 guards in the opener), 5 real requests in total with R1. The scheduler cycle ended `ok`: 0 inserted, 0 updated, **18 confirmed**, 0 quarantined; the only tables that changed in the private copy were the snapshot register and the source-state record; all six imported results kept their primary links; next check due +6 h; production hash unchanged, `live_enabled` false.

**Is polling reliable?** For what it covers, yes; as the only mechanism, no.
* The "last change" dates (R3, R4) are exactly the newest `lastUpdateDateTime` inside each matchday of the full-season file (verified by hash), and the matchday-7 payload (R5) equals the full-season file's matchday 7 (9 matches, same ids, all finished, no field differs): the change signal and the data agree.
* It reliably catches new results, corrections and re-timings **inside the current and the previous matchday**, and it identifies the latest matchday.
* It cannot see an older matchday. The provider keeps a postponed match in its original matchday, so when such a match is finally played its result appears in a matchday the poller never asks about. In the stored season two results were updated 3.9 and 4.9 days after kickoff; a correction that arrives after the matchday has moved on by more than one round would be missed. (No Bundesliga match is postponed right now: every matchday spans 2 days.)
* It is **not cheaper in requests**: one cycle needs 3 requests (current group and two change dates) plus up to 2 matchdays, against **one** request for the whole season (317 kB, 306 matches). The full-season request is idempotent and already tested.

**Periodic full-season reconciliation is therefore still necessary**; in fact the simplest reliable design is to make the full-season request the routine cycle (1 request every 6 hours) and drop polling, or keep polling only as an optional extra. This needs a small code change (the scheduler uses the polling path once a source-state record exists); not made here.

**Problems discovered:** (1) after the first full fetch the scheduler switches to polling for ever, which has the blind spot above; (2) the polling cycle costs more requests than a full fetch. No malformed or contradictory response occurred.

**Targeted tests run (no full suites; no application code changed in this follow-up):** scheduler, provenance, baseline-hash and store/sync/reconciliation tests (`test_sync_scheduler`, `test_provenance_link`, `test_baseline_hash`, `test_store`): **54 passed**; integrity script clean (baseline v3 physical and logical `true`, `integrity_check` ok, nothing staged, HEAD unchanged).

**Ready for the next supervised trial?** Yes for a supervised multi-cycle trial **after one change**: make the 1-request full-season fetch the routine cycle (keep polling optional). Real-network evidence now exists for the full-season fetch, the polling path and the safeguards; failure handling and quarantine are proven in replay.

## 4. Date-only handling: league time zones with the evidence floor, now in the application

`kickoff.made_before_kickoff(now, date, kickoff_utc, competition_key, alt_dates)` is the single rule used by the gameweek page and list, the gameweek forecast, the manual head-to-head prediction, Home and Matches. A stated UTC kickoff is used as it stands. For the five domestic leagues, a fixture without one is judged in the league's zones (Europe/London, Madrid + Canary Islands, Berlin, Rome, Paris; daylight saving from the date's own offset) with the floor (Premier League 10:30, La Liga 12:00, Bundesliga 13:30 local; none for Serie A and Ligue 1), and the **earliest** of any disputed dates (read from the quarantine, read-only, `app/disputes.py`). Any other competition keeps the strict global rule; an unreadable date blocks; no kickoff is ever created. Saved forecasts keep the label they were saved with and are never rewritten.

| Check | Result |
|---|---|
| Time-zone module tests | 20 (boundaries, DST in Madrid and Berlin, Canary Islands, floors, disputes, unreadable dates, fallbacks, a safety property: "yes" never after a zone reached the floor, all five leagues through the production entry point) |
| Gameweek page and forecast, real store | a date-only Premier League fixture is predictable one minute before its floor (where the old rule had blocked it since 10:00 UTC the day before) and refused one minute after; the forecast saves it as "before kickoff" in the first case and lists it as skipped in the second; rows saved earlier are byte-identical afterwards |
| Individual (manual) prediction | allowed just before the floor, refused just after ("Kickoff time unconfirmed…") |
| Home/Matches | agree with the page; the 4.8C test that expected a same-day La Liga fixture with a local time and no zone to be blocked at 10:00 UTC now expects it to be allowed (11:00 Madrid, before the 12:00 floor) and blocked at 11:30 UTC; I changed that expectation on purpose |
| Disputed date | a dispute only stricter: at the earlier candidate's floor the fixture becomes "unknown"/not predictable; the quarantine is not written |
| Past fixtures | never predictable in any league (tests for Premier League, La Liga, Bundesliga; played matchdays refused) |
| Old versus new on 190 unplayed fixtures at six instants | identical for every fixture with a stated kickoff; no past fixture opened; gains only near the old rule's blocking window (Serie A 22 → 27 at 15:00 UTC today, Serie A 12 → 17 and Ligue 1 9 → 12 at 11:00 UTC on 31 Oct); stricter only for a disputed La Liga fixture (`timezone_comparison.json`) |

Behaviour change you should know about: a same-day fixture whose time is known only as an unzoned local time (La Liga, Serie A, Ligue 1) is treated like a date-only fixture and stays predictable until the league floor (none for Serie A/Ligue 1, so until local midnight).

## 5. Official conflict evidence (`P4_8D_STAGE2_OFFICIAL_EVIDENCE_TABLE.md`)

Official competition pages could not be read (Premier League site is a script shell, BBC not fetchable here, 11v11 returned 403); every finding is **third-party** and nothing was resolved or changed.

| Item | Finding | Confidence |
|---|---|---|
| Bournemouth v Brentford | three independent match pages agree on **2–2** (half-time 1–1; Kluivert, Tavernier / Schade ×2): supports the stored score; OpenLigaDB's 2–1 looks wrong | medium |
| Aston Villa v Nottingham Forest | **Forest won 2–1 away**: the same result as the stored 1–2; the provider record is corrupt | medium |
| Rayo Vallecano v Athletic (matchday 8) | the match on 2026-10-10 was **suspended in the 25th minute** after paper planes and rubber balls from the stands; LaLiga said a new date would be announced; **no new date found**; OpenLigaDB's 2027-05-30 has no support | suspension high; new date unverified |
| Everton v Coventry (provider 6 Nov, stored 7 Nov) | a club-news report of the live-TV move says **Friday 6 Nov, 20:00 GMT** | medium, favours the provider |
| Atlético v Deportivo (provider 24 Oct, stored 25 Oct) | public broadcaster preview: **Saturday 24 Oct** | medium, favours the provider |
| Valencia v Villarreal (provider 24 Oct, stored 25 Oct) | listings disagree | low |
| The other 52 date disagreements | not researched (no official page reachable; per-fixture searching would be scraping) | none |

## 6. football-data.org

The email is finalised in `P4_8C_FOOTBALLDATA_EMAIL_DRAFT.md` (four questions: local SQLite storage, retention after the service ends, 2026-27 Serie A/Ligue 1 coverage on the free plan, delay and attribution/redistribution). It is **not sent**; no account, no key, no request. Serie A and Ligue 1 stay blocked from automatic synchronisation.

## 7. Controlled API restart and verification

| Step | Result |
|---|---|
| Before | no API, test or import process running; production physical and logical hashes equal baseline v3; `integrity_check` ok; WAL mode; `live_enabled` false; nothing staged (`restart_precheck.json`) |
| Restart | started the real API on `data/footiq.sqlite` (ready in under 10 s; model history 20,510 rows = the previous 20,504 + 6 imported results) |
| After | production physical hash unchanged (`1bfad5bd…cb278`), `sync_runs` still 10 rows (**no start-up diary row**: the 4.8B fix verified on production for the first time), `forecasts` 0, integrity script clean |
| Bundesliga standings (API and browser) | 1 Bayern München 7 played, 17 points, GD +19, form W W D W W; 2 Dortmund 17 (GD +8); 3 Freiburg 13; 4 Leverkusen 13; 10 Hoffenheim 9 (form W L L W W); the page says "Partial season: 63 of 306" and "Data fresh · newest verified result 2026-10-25" |
| La Liga standings | 1 Barcelona 27 (form WWWWL), **2 Real Madrid 24** (WLWWW), 3 Atlético 22, 4 Betis 20, 5 Real Sociedad 19, 7 Athletic 12, 15 Getafe 9; "Partial season: 93 of 380"; "Data not fresh · … imported from a saved snapshot; that was not a check of a live source; 1 played match without a result since 2026-10-10" |
| Eligibility | Bundesliga matchday 7 all completed and not predictable; matchday 8 fixtures "yes" and predictable; the featured fixture is Elversberg v Mainz (2026-10-30) |
| Sync status | `live_enabled` false; Bundesliga fresh (real check 2026-10-25 08:38 UTC); Premier League feed lagging (newest result 2026-10-12, 15 days); La Liga lag line refers to the suspended Rayo–Athletic match; Serie A and Ligue 1 lagging and blocked. The panel's wording "Results lagging" for La Liga's single suspended match is blunt: a wording improvement for later |
| Left running | the API is running now on port 8000 (production store, read-only use); the Vite dev server was stopped |

## 8. Tests, build and integrity

| Suite | Result |
|---|---|
| Backend, full | **332 passed**, 0 failed, 1 existing warning, 16 min 28 s (Stage 1: 321; +11: 6 zone-rule tests, 3 Home/disputed/past-fixture tests, 1 real-store individual+gameweek test, 1 scheduler `max_retries` test) |
| Frontend, no backend | **344 passed, 13 skipped** |
| Frontend, live backend on a private copy of production | **357 passed, 0 skipped** |
| Production build | passed, 648 modules |
| Integrity script (`p48d/integrity_stage2.json`) | baseline v3 physical and logical `true`; `integrity_check` ok; `live_enabled` false; frozen models and prospective-evaluation files unchanged; backend-source differences exactly the expected list; nothing staged |

Existing tests changed on purpose (each reflects an approved behaviour change): the 4.8C Home test for a same-day La Liga fixture; the wording check in a 4.8B test ("league time zone, or a disputed date"). No test was deleted. The Phase 4.7 `TESTING_REPORT.md` regression table now lists the 4.8D rows; its original figures are untouched.

## 9. Remaining blockers

1. A real failure of the provider (not just a replayed one) has not been observed; the routine cycle still has to be switched to the 1-request full-season fetch (§3a). 2. The 55 date disagreements and 2 score conflicts need an official source read by a person (§5). 3. The suspended Rayo–Athletic match is stored as an unplayed 2026-10-10 fixture and is shown as a missing result. 4. football-data.org has not answered (email unsent); Serie A/Ligue 1 have no provider. 5. Premier League results feed lags 15 days. 6. "Results lagging" wording for a single suspended match. 7. Bundesliga "fresh" label expires at 2026-10-28 08:38 UTC without a new real check.

## 10. Readiness for unattended six-hour synchronisation

**Not ready for unattended running; ready for a supervised multi-cycle trial once the routine cycle is the full-season fetch.** Proven: due-time logic, restart, locking, back-off, quarantine, idempotency, failure safety, provenance, the quiet start-up, and (real network) both the full-season fetch and the polling path. Missing: (a) the routine-cycle change; (b) a short multi-cycle supervised trial; (c) a decision to monitor consecutive failures visibly; (d) a human on call for quarantine items. Suggested path: approve R2–R5, then a 2–3 cycle supervised trial, then a Bundesliga-only schedule with you reviewing the first days.

## 11. Decisions required

1. Approve changing the routine cycle to the 1-request full-season fetch and then a 2–3 cycle supervised trial? 2. Who confirms the conflicts with official sources, and should Rayo–Athletic get a "suspended" status label? 3. Send the email (you)? 4. Is the new same-day behaviour for unzoned local times acceptable? 5. Keep the API running on production now?

---

## What We Did, Problems Faced, and How We Solved Them — Explained Simply

**The "missing 27 predictions".** An earlier report said we had saved 27 predictions, and a later one said the real database has none. We checked every copy of the database. The 27 were saved only in practice copies that my test scripts made and then threw away (nine matches, three predictions each). The real database never had any, in every backup. Nothing was lost.

**Asking the internet, carefully.** The automatic checker has two ways to ask: "send me the whole season" or a lighter way that asks "which round is it? did it change?" You had approved only the first. We tried the checker for real once, on a copy of the database, with strict rules: one allowed address, no retries, and a hard limit. The answer was the same as two hours earlier, so nothing changed, and the six results we had already imported kept their notes about where they came from. For the lighter way we need four more addresses, so we wrote them down for your approval and stopped. Everything else (restarts, failures, contradicting data) was shown with saved answers, and we say clearly which parts were real and which were replays.

**Match start times.** For matches where we only know the date, the app used to stop predicting 14 hours before the day began anywhere on Earth. Now it uses the league's own clock, including clock changes, and only allows predictions before the earliest time a match in that league has ever started (minus two hours). If a date is disputed, it uses the earlier date, so it can only get stricter. It never makes up a start time and it cannot predict a match that has already started. We tested all five leagues, the manual predictor and the weekly one.

**Checking the disputed results.** We looked for proof of the disputed scores and dates. The official league websites would not show us scores (they load with scripts or block us), so we used news and match-report pages. Bournemouth–Brentford really was 2–2 and Villa–Forest really was Forest 2–1, as our database says. The Rayo–Athletic game was stopped after 25 minutes because fans threw paper planes, and no new date exists yet, so the provider's "30 May 2027" is just a placeholder. We changed nothing; a person must confirm with the league itself.

**Restarting the app.** Before restarting we checked nothing else was using the database and its fingerprint matched. After restarting we checked the fingerprint again, that no "I was switched off" note was added, and the pages: Bayern top of the Bundesliga, Real Madrid second in La Liga, with the right recent results.

**30–60 second viva summary.** "We confirmed that the 27 forecasts were only in throw-away rehearsal copies: production never held a saved forecast, and every backup agrees. We ran one real, tightly limited scheduler cycle against the approved Bundesliga endpoint on a private copy: HTTP 200, identical data, no change and correct provenance, and we paused before the extra polling endpoints for approval. We integrated league time zones with an evidence-based earliest-kickoff floor into one shared rule used by the weekly forecast, the single-match predictor and the pages, with daylight saving, disputed-date strictness and past-fixture blocking tested across all five leagues. Public evidence supports our stored scores for the two Premier League conflicts and shows the Rayo–Athletic match was suspended, but nothing was resolved without an official source. After a controlled restart the standings, form and freshness are correct and the database fingerprint matches baseline v3."
