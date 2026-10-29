# Phase 4.13: date-conflict review, score fields and activation readiness (PL, SA, FL1)

Status: **analysis only.** No request to any provider, no database write, no import, no scheduler change, no date corrected, nothing staged or committed. Evidence: `data/supervised/phase4/p412/report.json`, the three saved responses in `data/snapshots/footballdata/` (SHA-256 recorded in their `.meta.json`), and the new read-only tool `app/store/classify_date_disputes_p413.py`, whose output is `data/supervised/phase4/p413/date_disputes.csv` (all 96 rows) and `classification_summary.json`.

## 1. The 96 date disputes

All 96 are **fixtures that have not been played** (94) or two matches the provider shows as played (2). In every case the stored date comes from the static pre-season schedule (`openfootball`, CC0, for **96 of 96**; precision date_only 88, local_unknown_tz 8; **0 of 96 have a stored kick-off time**). The provider dates carry a kick-off time. None is a time-zone artefact: in all 96 the provider's **local** date equals its UTC date (no kick-off at or after 21:00 UTC), so UTC vs local never explains a difference. No provider placeholder (`SCHEDULED`, 00:00Z) is among them: those are ignored by the adapter (Phase 4.12 fix).

| League | Disputes | Provider status | Shift (days, provider minus stored) | Second source | Class |
|---|---|---|---|---|---|
| PL | 31 | 31 TIMED | -1: 3, +1: 25, +2: 3 | OpenLigaDB's 2026-10-27 fixture list holds the provider's date for **31 of 31** | C: provider corroborated |
| SA | 39 | 39 TIMED | -2: 5, -1: 24, +1: 10 | none available | E: probable reschedule, unverified |
| FL1 | 26 | 24 TIMED, **2 FINISHED** | -1: 6, +1: 19, +2: 1 | none available | E (24), A (2) |

Weekday pattern (all 96): Sat to Sun 42, Sun to Sat 20, Sun to Mon 9, Sat to Fri 8, Sun to Fri 5, Sat to Mon 4, Wed to Tue 4, Wed to Thu 3, Mon to Sun 1. Shifts of one or two days between neighbouring days, in both directions, with confirmed local times, are the usual signature of **broadcaster selection / schedule revision** of a pre-season fixture list. They are not the signature of a systematic offset (that would be one direction only).

Classes (a class is a hypothesis about the cause, never a verdict on which date is right):
- **A. finished match whose date differs (2).** Played, so the provider date is when it was played, unless the provider's record is wrong.
- **B. time-zone representation (0).** Nothing to resolve.
- **C. provider corroborated by an independent second source (31, all PL).** Two sources against the static schedule. OpenLigaDB is a user-entered, partly stale feed, so this is strong but not official evidence.
- **D. stored date corroborated by a second source (0).**
- **E. 1 to 3 day shift of a provider-timed fixture, single source (63: SA 39, FL1 24).** Probable rescheduling; no evidence says which date is current.
- **F. shift over 3 days (0).**
- **Provider discrepancy vs genuine reschedule:** nothing in these data shows a provider **discrepancy** (no fixture where the provider contradicts two sources, no inconsistent time). What cannot be excluded is that the provider's date is itself outdated for some fixtures; only an official league source can settle that.
- **Missing kick-off times / date-only records:** 96 of 96 stored records are date-only or local-unknown-zone. That is why the dispute exists: the stored date has no time and comes from the earlier schedule.

### The two finished Ligue 1 matches (held, with their results)
| Matchday | Match | Stored date | Provider UTC kick-off (local) | Provider status | Provider result held back |
|---|---|---|---|---|---|
| 8 | Toulouse FC v ES Troyes AC | 2026-10-24 (Sat) | 2026-10-25 16:15Z (17:15 Paris, Sun) | FINISHED, updated 2026-10-27 00:20Z | yes |
| 8 | Paris Saint-Germain FC v Olympique Lyonnais | 2026-10-25 (Sun) | 2026-10-26 19:30Z (20:30 Paris, Mon) | FINISHED, updated 2026-10-27 00:20Z | yes |
Both are plausible genuine reschedules (a Saturday-to-Sunday and a Sunday-to-Monday-evening move are normal broadcast slots). Their scores are **not** imported until the date is decided. Verify against the Ligue 1 website (official), not the provider.

## 2. Proposed conflict-resolution rules (for your approval; none is implemented)
1. **Never automatic.** A stored date changes only through a signed decision record (match ids, old date, new date, evidence, reviewer, UTC time), applied by a one-shot tool after a verified backup. The quarantine row is then marked resolved; nothing is deleted.
2. **Evidence tiers.** T1 official league source (individual or batch); T2 two independent sources agree (PL 31); T3 single provider, status TIMED (SA 39, FL1 24); T0 FINISHED at provider (2 FL1): individual check against the official site.
3. **Batch sign-off.** T2 may be signed as one batch after you spot-check 5 fixtures on the official site; T3 per league after you spot-check 10 including both directions; T0 one by one.
4. **Review thresholds.** A shift over 3 days, a status other than TIMED/FINISHED, or a fixture already forecast is always reviewed individually.
5. **While undecided.** The stored date stays, the provider's result (if any) is not imported, and the existing kick-off rule already takes the **earlier** of the candidate dates, so a dispute can only make forecasts stricter.
6. **Later changes.** A provider date that changes again for the same fixture is a new finding (it is quarantined once per distinct text), never an update to the decision.
7. **Placeholders.** `SCHEDULED` with 00:00Z is ignored (done in code); it never opens a dispute or writes a kick-off.
8. **Needs a decision first:** the quarantine table has no "resolved" state, so rule 1 needs a small schema addition (a resolutions table). That is a **migration**: not done, and it needs your approval.

## 3. Score fields: `fullTime` vs `regularTime`
- **Documentation** (Phase 4.11 checklist): v4 added `regularTime` = goals in the first 90 minutes; `fullTime` = running score and the final score at FINISHED; `duration` says REGULAR, EXTRA_TIME or PENALTY_SHOOTOUT. The one documented example puts penalty goals into `fullTime`, but no rule is stated.
- **Saved responses (232 finished matches: PL 80, SA 80, FL1 72):** every one has `duration` REGULAR and the same four score nodes (`duration`, `fullTime`, `halfTime`, `winner`); **none has `regularTime`, `extraTime` or `penalties`**; all are `REGULAR_SEASON`; the `winner` matches `fullTime` in 232 of 232; `halfTime` never exceeds `fullTime`; the largest total is 8 goals.
- **Against production:** the 155 results that exist in both (PL 60, SA 50, FL1 45) agree **155 of 155** with the independently stored 90-minute scores. That is direct empirical support for reading `fullTime` as the 90-minute score in these leagues.
- **Interpretation:** for a league match with `duration` REGULAR, `fullTime` is the 90-minute score (a league match has no extra time). The adapter already refuses every other duration (held for review) and flags `fulltime_taken_as_regular_time_unconfirmed` on each such result. It stays "unconfirmed" until the provider says so in writing (question 5 of the email).
- **Proposed extra safeguard (not implemented):** reject a finished match whose `winner` contradicts `fullTime` or whose `halfTime` exceeds `fullTime`. It would have changed nothing in these 232 matches.

## 4. Saved raw responses and snapshots: delete or retain?
- **Facts:** `data/snapshots/` and `data/supervised/` are listed in `.gitignore`, so the six provider files, the reports and the private copies are **not** in Git and are not pushed. Production holds **no** football-data.org row yet (nothing imported; its hash was unchanged).
- **Recommendation: retain locally, do not delete, do not redistribute, pending the provider's answer.** They are the audit trail (SHA-256, URL, status) for the validation you approved; they are small (about 0.7 MB); nothing in the terms forbids keeping them while the account is active, but nothing permits sharing them either. Exclude `data/snapshots/footballdata/` and `data/supervised/phase4/p412/` from any zip or submission.
- **Delete without loss** if you prefer the cautious side: `data/supervised/phase4/p412/private_copy.sqlite*` (a throw-away copy holding provider-derived rows; the snapshots can recreate it).
- **Delete everything provider-derived** if the provider refuses or the account is closed (terms 4.6 and 9.1): the three snapshots, the p412/p413 evidence, any imported rows. The importer must therefore tag provider rows (it does: `source_system` and `match_sources.source` = footballdata) so they can be removed or archived precisely.

## 5. Provider permission email
Separate file: `P4_13_FOOTBALLDATA_PERMISSION_EMAIL_DRAFT.md` (not sent; replaces the 4.8C draft, which predates registration and covered only SA and FL1).

## 6. Proposed safe-import plan (nothing runs before your approval and the provider's written answer)
Preconditions: P1 provider permission in writing (or your explicit decision to proceed at your own risk, recorded); P2 you approve this plan; P3 verified backup and private restore; P4 integrity ok; P5 Bundesliga and La Liga schedule untouched.
1. **Dry run again on a private copy** with the saved snapshots (no request): expected from the corrected parser: PL 20, SA 30, FL1 25 new results imported (**75**); 96 fixtures held; 0 verified results or dates altered; 101 (SA) and 95 (FL1) kick-off times added to undisputed rows.
2. **Controlled import (one cycle, one league at a time, PL first)** from the already saved snapshots, so no new request is needed: undisputed results and kick-offs only; disputed fixtures and the 2 finished FL1 matches stay quarantined with their text; stored dates unchanged.
3. **Verify after each league:** only `matches` rows of that league changed (new results plus kick-offs), `quarantine` gained only DATE_DIFFERENCE rows, provenance rows point at the saved snapshot, integrity ok, saved forecasts 0 and models untouched, Bundesliga/La Liga rows byte-identical.
4. **Status panel:** the 96 appear as "date disagreement" findings next to the 57 already open (153 in all). They need your review; the importer never resolves them.
5. **Only then** (separate approval) move the league from `PREPARED_PROVIDERS` to `APPROVED` and list it in `config/sync.json`. The first scheduled cycle would make 3 requests (7 s apart, under the 10 per minute limit), 12 a day.
6. **Decision on kick-off enrichment:** it only adds information to date-only rows and matches the provider's own times, but it is a change to 196 stored rows; say if you want results only.

## 7. Production activation readiness checklist
| # | Condition | Status |
|---|---|---|
| 1 | Adapter and tests (24, offline) | done |
| 2 | Real access validated for PL, SA, FL1 (HTTP 200, 2026 served, 10 requests per minute) | done |
| 3 | Identity: 58 of 58 clubs resolved exactly | done |
| 4 | Score conflicts | 0 of 155 overlapping results |
| 5 | Freshness (newest results 10-25 / 10-25 / 10-26; provider update 10-27) | pass |
| 6 | Placeholder kick-off defect | fixed and tested |
| 7 | **Storage, reuse and model-training permission** | **OPEN: blocker** |
| 8 | **`fullTime` as 90-minute score** | open (empirically supported, written confirmation pending) |
| 9 | **96 date disputes** | open: need your decision (section 2) |
| 10 | Resolution mechanism (decision records, "resolved" state) | not built; needs a migration approval |
| 11 | Retention decision for raw files | proposed: retain locally, not distributed |
| 12 | Backup and restore for the import | to do at import time |
| 13 | Attribution wording in any public view | built into the status panel; add to the app footer before submission |
| 14 | Bundesliga and La Liga unaffected; models and forecasts untouched | verified this phase (no change) |
Overall: **not ready to import or activate** until rows 7 and 9 are decided; rows 8 and 10 should be settled with them.
