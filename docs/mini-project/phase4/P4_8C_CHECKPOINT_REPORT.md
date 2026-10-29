# Phase 4.8C Checkpoint Report: Supervised Provider Verification, Stage 2 and Phase 4.8D Readiness

Date: 2026-10-27. **Live synchronisation stayed off, the six-hour scheduler stayed inactive, nothing was imported into production, no model or saved forecast was touched, the official prospective records were not touched, nothing was staged or committed (HEAD `970f461`). Phase 4.8D was prepared on paper only and was not implemented.**
Companion documents: `P4_8C_DB_BASELINE.md` (baseline algorithm), `P4_8C_REQUEST_LEDGER_PROPOSAL.md` (the ledger), `P4_8C_FOOTBALLDATA_EMAIL_DRAFT.md` (not sent), `P4_8D_ACTIVATION_PLAN.md` (league matrix, failure handling, monitoring, rollback). Evidence: `data/supervised/phase4/p48c/` and `data/snapshots/p48c/`.

## 1. Exact external requests made

| # | Kind | Target | Result |
|---|---|---|---|
| A1 | OpenLigaDB GET (Bundesliga) | `https://api.openligadb.de/getmatchdata/bl1/2026` | HTTP 200, 316,983 bytes, 2026-10-27T12:57:04Z |
| A2 | OpenLigaDB GET (Premier League) | `https://api.openligadb.de/getmatchdata/pl/2026` | HTTP 200, 942,711 bytes, 2026-10-27T13:01:07Z |
| A3 | OpenLigaDB GET (La Liga) | `https://api.openligadb.de/getmatchdata/la1/2026` | HTTP 200, 452,761 bytes, 2026-10-27T13:01:12Z |
| B1–B9 | football-data.org public pages, read with the web-page reader | `www.football-data.org/about`, `/pricing`, `/coverage`, `/documentation/api`; `docs.football-data.org/general/v4/`, `…/policies.html`, `…/lookup_tables.html`, `…/match.html`, `…/overtime.html` | 9 of the 9 approved reads |

**Total: 3 OpenLigaDB requests (exactly the approved ledger; A2 and A3 five seconds apart, no retries, no other endpoint) and 9 page reads.** None to `api.football-data.org`, no account, no key, no purchase, no further request after the ledger was completed. Ledger file: `data/snapshots/p48c/request_ledger.jsonl` (three lines, status 200 each). The page reads were summarised by the reader tool's small model, so clause numbers should be checked against the pages before anything is relied on legally.

## 2. Snapshots (read-only files, SHA-256 verified, metadata beside each)

| League | File | SHA-256 | Bytes | Licence |
|---|---|---|---|---|
| Bundesliga | `20261027T125704Z_p48c_bl1.json` | `b725c2f3e30a3320f75da9891a2cfd2b5b93aed231da16aab253cf81a6bd6b46` | 316,983 | ODbL-1.0 |
| Premier League | `20261027T130107Z_p48c_pl.json` | `5bc7f2def9f9725461afae05ae8cc04038122291b3e6991bb7c678a0963bac9d` | 942,711 | ODbL-1.0 |
| La Liga | `20261027T130112Z_p48c_la1.json` | `efe9e2a94ae06151f39947cbcb04e73e5c8e5f1534447bc96c5f3284afc11508` | 452,761 | ODbL-1.0 |

Each `.meta.json` holds URL, status, retrieval time, response headers, source, licence, attribution ("Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0") and adapter version. **The Premier League response is byte-for-byte identical to the 2026-10-25 snapshot** (same hash): the provider's feed has not changed in two days.

## 3. Bundesliga (A1) validation and reconciliation

All comparisons used a private copy of production (file copy; the original was never opened for writing).

| Check | Result |
|---|---|
| Schema and completeness | 306 matches = 34 matchdays × 9; 18 teams; same match IDs as the 2026-10-25 snapshot |
| Team identities | all resolve (0 unresolved) |
| Finished | 63, each with half-time and final results; none without a result |
| Change since the production-source snapshot | 2 matches, both newly finished; 0 date changes |
| Against production | 243 unchanged, 61 confirmed, **2 updated**, 0 inserted, 0 date differences, **0 score conflicts**, 0 quarantined; identical with and without date protection |

New verified results: **Hoffenheim 3–0 Leverkusen** and **Freiburg 1–3 Bayern München**, both Matchday 7, 2026-10-25. In the real store they are "scheduled", shown as "Awaiting verified result".

## 4. Premier League and La Liga (A2/A3): reconciliation

Proposed import = the live-path ingestion with date protection, replayed onto a private copy (`stage2_reconcile.py`, `stage2_reconciliation.json`, `stage2_proposed_diff.csv`). Production hash before and after: `3641e4da…3922`.

| | Premier League (A2) | La Liga (A3) |
|---|---|---|
| Total fixtures | 380 (38 matchdays, 20 teams) | 380 (38 matchdays, 20 teams) |
| Completed results in the source | 59, plus 1 contradictory record (Villa–Forest) = 60 flagged finished | 98 |
| **Newly available verified results** | **0** (feed unchanged since 25 Oct; newest result 2026-10-12) | **4** (below) |
| Missing results | 20 fixtures past their date with no result in the source or the store (oldest 2026-10-17) | 1 past its date (since 2026-10-10); plus 5 source results held back because their date disagrees |
| Team identity / alias | 0 unresolved; 18 exact + 2 normalised (includes the reviewed alias *Brentford F.C.*); no entity used twice | 0 unresolved; 15 exact + 5 normalised (includes the 4 reviewed aliases); no entity used twice |
| Fixture-date disagreements | 31 held (all already quarantined) | 24 held (all already quarantined) |
| Score conflicts | 1 (Bournemouth–Brentford, stored 2–2 vs 2–1) + 1 contradictory (Villa–Forest), both already quarantined, stored scores unchanged | 0 |
| Duplicate / contradictory records | 0 duplicate match IDs, 0 duplicate pairings; the 1 contradictory record above | 0 / 0 |
| Quarantined in this replay | 33 = 31 + 2, **0 new findings** | 24, **0 new findings** |
| Reconciliation | 0 inserted, 5 updated, 284 unchanged, 58 confirmed | 0 inserted, 4 updated, 263 unchanged, 89 confirmed |
| Repeat import | 0 changes (duplicate-free) | 0 changes |
| Freshness after the import | stale: no approved source; latest result 2026-10-12; 20 awaiting; "last import from a saved snapshot, not a live check" | stale: no approved source; latest result 2026-10-25; 1 awaiting; same label |

Quarantine overall: 273 before, 273 after, 0 new, 0 removed; 55 date disagreements and the two score conflicts unchanged. No score and no date is overwritten (0 and 0). Integrity of the copy: `PRAGMA integrity_check` ok, foreign-key check 0 problems, 223,510 matches before and after, 0 rows deleted.

**La Liga's four new results** (all 2026-10-25): Athletic Club 4–0 Getafe, FC Barcelona 1–2 Real Madrid, Celta 0–0 Betis, Real Sociedad 2–1 Levante. Resulting standings: eight teams change (played +1; Real Madrid 21 → 24 points, Real Sociedad 16 → 19, Athletic 9 → 12, Betis 19 → 20, Celta 11 → 12, Getafe, Levante and Barcelona unchanged on points). Recent form (last five, oldest first): Barcelona WWWWW → WWWWL, Real Madrid WWLWW → WLWWW, Getafe DLWLD → LWLDL, Levante LLDDW → LDDWL, Betis WWDWL → WDWLD, Real Sociedad WLWWW → LWWWW, Athletic WDDDL → DDDLW, Celta DDWDW → DWDWD. **Premier League: no standings or form change.**

## 5. Bundesliga two-result import rehearsal (private copy; `bundesliga_two_result_rehearsal.py`, `bundesliga_rehearsal.json`)

The copy's logical hash equalled the recorded baseline before starting.

| Check | Result |
|---|---|
| Row-level changes | exactly **2 rows** of 223,510 (`…:2026-27:L110` Hoffenheim–Leverkusen, `…:L111` Freiburg–Bayern); per row: status scheduled → completed, goals 3–0 and 1–3 (final and 90-minute), outcome H and A, `label_90_status` confirmed, `rated`/`regular`/`in_universe` set, model entity ids filled, `source_system` openfootball → openligadb, `licence` CC0-1.0 → ODbL-1.0. No date, kickoff, team or other row changes |
| Tables that change | `matches` (2 rows) and `source_snapshots` (+1: the A1 snapshot with its hash); the diary `sync_runs` gains one row (run 9, 0 requests, 2 updated) |
| **Provenance finding** | the two OpenLigaDB `match_sources` links already exist (role *confirmation*, pointing at the **2026-10-25** snapshot), and the insert is "ignore if present", so **no link to the new snapshot is written**. The match row says the result came from OpenLigaDB, but its source link names the older snapshot and role "confirmation". This is an audit gap, not a data error; fix before the production import (§8) |
| Standings (Bundesliga) | Bayern 14 → 17 points, rank 2 → 1; Hoffenheim 6 → 9, rank 14 → 10; Leverkusen 13, rank 4 (unchanged, GD 4); Freiburg 13, rank 3; Dortmund 17, rank 1 → 2; Paderborn, Frankfurt, Köln, Hamburg each drop one place |
| Recent form (last five) | Hoffenheim LWLLW → WLLWW; Leverkusen WDWWW → DWWWL; Freiburg WWDWL → WDWLL; Bayern DWWDW → WWDWW |
| Prediction features | Matchday 8 (9 fixtures) forecast before and after on the copy. For the 4 fixtures involving these teams, v1 inputs changed 11–13 of 25, v2-r1 35–39 of 62; both schemas identical. Example: Leverkusen v Stuttgart, v1 home/draw/away 56.7/19.2/24.0 % → 52.5/19.5/28.0 %; Werder v Hoffenheim 39.2/23.6/37.3 % → 35.6/24.0/40.4 % |
| Saved forecast immutability | the 27 rows saved before the import are byte-for-byte unchanged after the import and after the second run; both runs kept (cutoff 2026-10-24 → 2026-10-25) |
| Repeat import | 0 inserted / 0 updated / 63 confirmed; no table changes; 0 duplicate record ids; 0 duplicate source links |
| Integrity | `integrity_check` ok; foreign-key check 0 |
| Rollback | (a) a transaction that applies the 2 updates and is rolled back leaves the logical hash identical; (b) restoring the pre-import backup file gives the recorded baseline logical hash again |

## 6. Exact proposed production diff (nothing applied)

| Step | League | Rows | Change |
|---|---|---|---|
| 1 (recommended) | Bundesliga | 2 | Hoffenheim 3–0 Leverkusen and Freiburg 1–3 Bayern, 2026-10-25: fields as in §5; plus snapshot `b725c2f3…6b46` registered; plus one `sync_runs` row |
| 2 (optional) | La Liga | 4 | Athletic 4–0 Getafe, Barcelona 1–2 Real Madrid, Celta 0–0 Betis, Real Sociedad 2–1 Levante (all 2026-10-25): status scheduled → completed, goals, outcome, `rated`/`regular`/`in_universe`, entity ids, `source_system` openligadb, `licence` ODbL-1.0; snapshot `efe9e2a9…1508` registered |
| (skip recommended) | Premier League | 5 | status-only: Liverpool–Brighton, Crystal Palace–Newcastle, Man United–Bournemouth, Hull–Brentford, Sunderland–Leeds (all 2026-10-25) scheduled → awaiting_result. The app already shows them that way, so this adds no information; no results to import |
| never in this step | all | 0 | no date, no existing score, no quarantine row, no team or alias, no Serie A or Ligue 1 |

Full field-level list: `stage2_proposed_diff.csv` (61 field changes) and `bundesliga_rehearsal.json`. After the Bundesliga step the logical baseline becomes **v3** (a new recorded pair; v2 is kept).

## 7. football-data.org: provider and licensing findings (Serie A, Ligue 1)

**Technically suitable, legally not established.** Serie A (`SA`, 2019) and Ligue 1 (`FL1`, 2015) are in the free list; 10 calls/minute; `dateFrom`/`dateTo`, `status` and `lastUpdated` support a light refresh; statuses include AWARDED and POSTPONED; 90-minute score documented as `score.regularTime`; a 6-hourly read of two leagues needs a few requests per cycle.

| Uncertainty | Detail |
|---|---|
| Free-plan delay | "Scores and schedules are delayed", no duration stated anywhere |
| Seasons | no season coverage stated; 2026-27 availability unknown until an account exists |
| Storage | terms silent on caching/storing; 4.6 deletes "stored and indexed data" on cancellation |
| After you stop | 9.1: no referencing of the data on your own service after cancellation (a real risk for a stored database and for submitting it) |
| Redistribution, commercial use | silent; the word "commercial" does not appear |
| Fair use | "excessive" use undefined |
| Attribution | required wording "Football data provided by the Football-Data.org API" |
| Terms age and consistency | last updated 2018-06-01; pricing and docs disagree on call limits and header names; older and newer status lists differ |

**Draft email prepared and not sent:** `P4_8C_FOOTBALLDATA_EMAIL_DRAFT.md` (to the address on the pricing page) asks the four points you listed. The provider is **not approved or activated**; I recommend waiting for the written answer.

## 8. Findings that need a decision

1. **Provenance gap (§5):** when an existing OpenLigaDB link has role "confirmation", an import that now supplies the result does not add a "primary" link to the new snapshot. Proposed fix for 4.8D: upsert the link (role → primary, snapshot id and retrieval time → the new snapshot), covered by a test. Not implemented.
2. **Premier League feed lag:** the provider has no Premier League result after 12 October. Treat OpenLigaDB as unsuitable for Premier League freshness; keep it out of the scheduler.
3. **Bundesliga freshness label:** "fresh" until 2026-10-28 08:38 UTC (72 hours after its real 25 October check).

## 9. Date-only fixtures: tested time-zone proposal (production unchanged)

`app/kickoff_tz.py` (not imported by any endpoint; `app/kickoff.py` remains the production rule) with 9 tests. It never returns or assumes a kickoff; it answers only yes / unknown / no.

| Question | Proposal |
|---|---|
| Stated UTC kickoff | unchanged: ahead of now → yes, otherwise no (daylight saving cannot matter) |
| Date-only fixture | yes until the date starts in the **easternmost** verified zone of the league (Europe/London, Madrid + Canary Islands, Berlin, Rome, Paris); no only after it ends in the **westernmost** zone; otherwise unknown. Example: Premier League fixture dated 2026-10-31 stays predictable until 2026-10-31 00:00 UTC instead of being blocked from 2026-10-30 10:00 UTC (14 hours earlier); Spain until 2026-10-30 23:00 UTC |
| Daylight saving | zoneinfo uses the date's own offset: Madrid 2026-10-25 starts 22:00 UTC the day before, 2026-10-26 at 23:00 UTC; Berlin on the spring change day (2026-03-29) starts 23:00 UTC and ends 22:00 UTC (tested) |
| Unknown venue / zone / competition | falls back to the strict global rule, never a guess |
| Same-day with no kickoff | never predictable (unknown); an optional "evidence floor" uses the earliest local hour observed in stored UTC kickoffs (Premier League 12:30, La Liga 14:00, Bundesliga 15:30; no data for Serie A/Ligue 1) and is **off by default** because it rests on one season's sample |
| Postponements | status blocks as today; a forecast saved before a date moved keeps its saved label and probabilities |
| UTC calendar-day differences | OpenLigaDB's `match_date` is the **UTC** date of the kickoff; openfootball's is the local date. In today's stored data no kickoff crosses midnight between zone and UTC (0 of 856), but the proposal never relies on that and uses the stored instant whenever there is one |
| Disputed date | every candidate date is considered and the earliest decides: a dispute can only make the answer stricter |
| Historical cutoffs | unchanged: features use results strictly before the fixture's date |
| Safety property (tested) | whenever the proposal says yes, the date has not started in any of the league's zones |

Impact if adopted: the cutoff moves from about 10:00 UTC to about 23:00–24:00 UTC the day before for date-only fixtures. Serie A (30 of 30 next-14-day fixtures) and Ligue 1 (18 of 18) have no UTC kickoffs at all, so they gain most.

## 10. Freshness logic (kept from the offline part)

Reported separately per league: latest verified result; last successful source check; last import (live or offline, labelled); last attempt; provider status; imported and held counts; a note when a check cannot prove completeness. Offline imports never count as checks. Shown in the Leagues status panel (frontend test included).

## 11. Database integrity evidence

Physical `3641e4da47b3930cbb543499d393b2360f1e117481ad35349b082a4682073922` and logical `e32d759bddef1688116c1c91430cbf10384724e525971994f4e085312a96f29d` match the recorded baseline v2 after A1, A2, A3 and every rehearsal (integrity script: both `true`, excluded row ids `[8]`); `PRAGMA integrity_check` ok; `simulation_runs` 0; `live_enabled` false; `scoreline_method` null; frozen model and prospective-evaluation files unchanged (only `config/sync.json` differs from the frozen list, your approved 6-hour interval); backend-source differences are the expected list; nothing staged. The 55 date disagreements, the two score conflicts and the five reviewed aliases are untouched. All private copies were deleted.

## 12. Tests and build (final run, after the last code change)

| Suite | Result |
|---|---|
| Backend, full (`pytest tests`) | **308 passed**, 0 failed, 1 existing warning, 16 min 44 s (4.7: 260; 4.8B: 284; 4.8C offline part: 299; +9 time-zone proposal tests) |
| Frontend, no backend | **344 passed, 13 skipped** (unchanged from the 4.8C offline part) |
| Frontend, live backend | 357 of 357 in the 4.8C offline run; **not re-run** since: no API or frontend code changed afterwards (the only new backend code, `kickoff_tz.py`, is imported by nothing but its tests) |
| Production build | passed, 648 modules |
| Integrity script | physical and logical baseline `true`, expected backend differences only, nothing staged, HEAD unchanged, `live_enabled` false |

New since the last report: `tests/test_kickoff_tz.py` (9). The rehearsal and reconciliation scripts are evidence tools, not part of the suite; their outputs are the JSON/CSV files named above.

## 13. Phase 4.8D readiness assessment (`P4_8D_ACTIVATION_PLAN.md`)

* **Import the 2 Bundesliga results:** ready, with a backup, a baseline v3 record and the provenance fix of §8.1.
* **La Liga 4 results:** ready, optional; **Premier League:** nothing to import (skip).
* **Six-hour refresh, Bundesliga only:** not yet; needs a supervised live trial on a private copy first. All other leagues: not ready (no approved live provider, feed lag or open conflicts).
* League matrix with provider, gaps, conflicts, import and refresh readiness, failure handling, monitoring and rollback: see the plan.

## 14. Remaining blockers

1. Provenance fix (§8.1). 2. football-data.org written answer (email not sent). 3. 55 date disagreements and 2 score conflicts need independent or official evidence. 4. Premier League has no live source and a 15-day lag. 5. The scheduler has never run end-to-end against the real network. 6. A real contact string is needed only for the future trial; it is already configured for supervised requests.

## 15. Decisions requiring your approval

1. Approve the Bundesliga two-result production import (with backup, baseline v3 and the provenance fix), or hold.
2. Also import La Liga's four results? Skip the five Premier League status rows?
3. Approve the supervised live trial of the scheduler for the Bundesliga on a private copy (3 cycles)?
4. Send the football-data.org email yourself (draft ready), or change it?
5. Adopt the time-zone proposal for date-only fixtures, adopt it with the evidence floor, or keep the global rule?
6. Resolution rule for the two score conflicts and the 55 date disagreements (waiting for official evidence is the safe default).

---

## What We Did, Problems Faced, and How We Solved Them — Explained Simply

**What we did.** We asked the free data service three questions, one for each league: Bundesliga, Premier League and La Liga. Each answer was saved exactly as received, like a photocopy that is then locked, with a fingerprint written down. We compared each answer with a *photocopy of our own database*, never the real one.

**What we found.**
* **Bundesliga:** everything agreed, plus two new results (Hoffenheim 3–0 Leverkusen and Freiburg 1–3 Bayern).
* **La Liga:** everything agreed, plus four new results, including Barcelona 1–2 Real Madrid. Five more results are held back because the other service gives a different date.
* **Premier League:** the service sent the *exact same file* as two days ago. It is simply behind: nothing after 12 October. So no new results, and the rule of "do not trust the date it gives us" is still protecting 31 matches.

**A problem we found while rehearsing.** We practised adding the two Bundesliga results to a copy. The numbers, tables and predictions all updated correctly: Bayern moved to first place, and the predictions for the next round changed by a few percentage points, while the predictions we had saved earlier stayed exactly as they were. But we noticed a small bookkeeping gap: the "where did this result come from" note still pointed to the older download instead of the new one. Nothing wrong with the scores, but an auditor would want the note to be right, so we recorded it as something to fix before the real import. We also proved we can undo an import two ways: a failed import leaves nothing behind, and we can put back the pre-import copy and it matches the original fingerprint.

**Kickoff times.** Right now, if we do not know the start time of a match, we assume the worst: it might already have started anywhere in the world, so we stop predicting about 14 hours before the date begins. We wrote and tested a smarter rule that uses each league's real time zone (including clock changes) and never guesses a start time. It is only a proposal; the app still uses the strict rule.

**Serie A and Ligue 1.** The football-data.org terms are old, do not say if we may keep the data in our own database, and say we may not use the data after we stop using the service. We wrote a polite email asking four clear questions, but we did not send it and did not sign up for anything.

**What we did not do.** We did not change the real database, turn on automatic updates, touch the prediction models or the saved predictions, or make any request beyond the three approved ones.

**30–60 second viva summary.** "After the Bundesliga check we made two more supervised requests, for the Premier League and La Liga, saved them as locked, hash-verified snapshots and reconciled them against a private copy of production. La Liga had four new results, the Premier League feed was unchanged and two weeks behind, and nothing conflicted with what we hold; the known score and date disagreements stay quarantined. We rehearsed importing the two new Bundesliga results end to end: only two rows change, standings and recent form update, the next predictions shift while saved forecasts stay identical, repeat imports add nothing, and we can roll back. The rehearsal exposed a provenance gap that we will fix before importing. We also drafted a clarification email to football-data.org instead of assuming its terms allow storage, tested a time-zone-based kickoff proposal without changing production, and wrote the 4.8D activation plan. Production's physical and logical hashes are unchanged and live sync is still off."
