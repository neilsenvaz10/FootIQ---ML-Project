# Bundesliga source-promotion readiness report (2026-10-21)

Scope: OpenLigaDB as a controlled **Bundesliga-only** results provider. Validation only: no official predictions, no official logging, no polling schedule, no other leagues, no retraining, no database change, nothing staged or committed. Script `g1_bundesliga_promotion.py`, raw results `g1_results.json`, tables `01`–`05b`.

## 1. Pilot integrity
* **Raw responses and ledger preserved:** `source_adapters_r1/pilot/run_20261021T141224Z/` (6 snapshots + `.meta.json`, all read-only; ledger `request_ledger.jsonl`). Not modified.
* **Snapshots:** 6/6 sha256 and byte counts match their metadata; all carry the approved plan hash `d7c2169e…18bc9`, licence `ODbL-1.0` and the attribution line (`01_pilot_snapshot_integrity.csv`).
* **Ledger:** 6 requests, all HTTP 200, one host (`api.openligadb.de`), every URL within the approved plan, 0 retries.
* **Reproducible:** re-parsing the saved R3 snapshot with the adapter reproduces the pilot's `staging_records.csv` exactly (306 rows, 0 differing columns). The 14:12 snapshot equals the earlier 13:35 snapshot for all 306 matches (0 changed).
* **Result-type reporting fix:** the fix changed only the pilot's report line (the `/getresulttypes` field is named `kind`); parsed outcomes are identical before/after (staging records identical). R2 lists HalfTime, After90Minutes, AfterExtraTime, AfterPenalties and "Unknown" (the "after stoppage time" type), and the adapter uses only `After90Minutes`.
* **Internally consistent:** 306 matches / 306 unique IDs, 54 completed, 54 with explicit 90-minute type, every completed kickoff before the retrieval time, every record attributed.

## 2. Licence and attribution verification
ODbL 1.0 (official licence page, "Stand 31.08.2026"): free use including commercial; attribution "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0" for public use; share-alike only for a publicly redistributed adapted database; no revocation. API terms ("Stand 28.08.2026"): change-date polling, jitter, caching, back-off, descriptive User-Agent with contact, 60 requests/min/IP, no warranty. The pilot complied: 6 requests ~3 s apart, no match in play, contact in the User-Agent only (not in ledger, snapshots, reports or any scanned file — §7 of the Git check). Internal use only; no public redistribution has occurred, so share-alike is not triggered. Attribution is stored on every record; any published table must repeat it. Residual: data are unreviewed user entries → two-source confirmation or conflict checks remain required for labels (amendment A1.4).

## 3. Protocol amendment comparison
Full clause-by-clause table and the recommended final text: `02_PROTOCOL_AMENDMENT_COMPARISON.md`. Summary: the draft changes accepted sources, conflict handling (stricter and explicit), feature availability (as-of rule), regulation-time verification (explicit result type, two-source route), sealing deadline (source-stated UTC kickoff) and provenance; competition freshness (14 days) and the metrics/gates are unchanged. Gaps found and fixed in the recommended text: a canonical-record rule when sources agree, kickoff-rescheduling after sealing, kickoff-snapshot freshness, an explicit S2 scope (bl1/2026) and a source-terms compliance clause. **Not activated; the frozen protocol and its hash are unchanged.**

## 4. Isolated feature-state update (Bundesliga, 18 results)
* **Additions:** 18 verified results (2026-10-09 … 2026-10-18), 0 rejected; built from the raw R3 snapshot with provenance (`03_added_results_with_provenance.csv`: source matchID, snapshot id, retrieval time, kickoff UTC). Frozen universe (216,553 rows, sha prefix 1c4d758b…), models, preprocessing and datasets untouched; the updated universe exists only in memory/isolated pickle.
* **As-of filter:** the universe at a time before the retrieval (14:12:31Z) has 216,553 rows (identical to frozen); after, 216,571. Only results retrieved before the prediction time can enter.
* **Rejection tests (on copies, test inputs):** duplicate pair → `duplicate_pair_in_source`; unknown team → `identity_unresolved_exact`; a score differing from the frozen openfootball result → `CONFLICT_with_openfootball`. Nothing is resolved silently.
* **Same history for both model families:** v1 and v2 features come from one concatenated frame; prior-match counts and Elo agree for all 252 fixtures (`n_prior_equal`, `elo_equal` true), so original/matched v1 and frozen v2 see the same verified history.
* **Reproducibility:** predictions (in-memory dry run, not logged, not reported) computed three ways — from the live universe, rebuilt from the raw snapshot, and from the pilot's pickle — have identical hash `a44651ce5ee6bd1d`.
* **Feature differences vs the stale openfootball-only state** (`04_feature_differences_vs_stale_state.csv`): 55 of 62 v2 features and 24 of 25 v1 features change for the 252 fixtures. Every club gains 2 prior matches (mean +2.0); days of rest shorten by about 28 days (last match was 2026-09-20 in the stale state, now mid-October); Elo changes up to 27 (Elo1) and 42 points (Elo2); the 7 unchanged v2 features are static (tier, new-to-competition, cup flags, season-day, congestion). The frozen v2 probabilities shift by 0.016 on average, 0.079 at most.
* **Frozen coefficients/preprocessing:** unchanged (hash-verified, below).

## 5. Chronological leakage checks
* All added results are dated before the first future fixture (2026-10-23).
* Every completed result's kickoff precedes its retrieval time; the as-of universe excludes all new rows before retrieval.
* **Prefix invariance:** scrambling every Bundesliga score dated 2026-10-16 or later and deleting all later rows leaves the features of the 10 earlier-or-same-day fixtures identical (v2 and v1; max difference 0.0).

## 6. Fixture eligibility (isolated state, dry run, nothing logged)
| Measure | Value |
|---|---|
| Future Bundesliga fixtures | 252 (matchdays 7–34) |
| **Eligible** | **18** (matchdays 7 and 8, kickoffs 2026-10-23T18:30Z … 2026-11-01T16:30Z) |
| Ineligible | 234, all for the same reason: the competition's latest result (2026-10-18) is more than 14 days before the fixture (matchday 9 onward, from 2026-11-06). No history, identity, or unresolved-fixture problems. |
| Stale openfootball-only state | 0 eligible |
| Missing historical results after the update | 0 (openfootball's 18 past-dated Bundesliga fixtures without result are all recovered) |
| Earliest sealing deadline, existing rule (date 00:00 UTC − 14 h − 60 min) | **2026-10-22 09:00 UTC** (for the 2026-10-23 18:30Z kickoff) |
| Earliest sealing deadline, amendment rule (UTC kickoff − 60 min) | **2026-10-23 17:30 UTC** |
`05_bundesliga_fixture_eligibility.csv`, `05b_eligibility_by_matchday.csv`. Matchday 9 becomes eligible when results of matchdays 7–8 are polled in (due after 2026-11-01).

## 7. Git hygiene
`config/contact.local` is ignored (`git check-ignore` true) and its ignore rule (`config/.gitignore`: `contact.local`) is intact; `source_adapters_r1/config/.gitignore` also exists. 584 tracked files scanned plus 0 staged files: **the contact address occurs in none**; 210 untracked work-product files (reports, snapshots, ledger, logs, scripts) scanned: **0 occurrences**. Nothing staged, committed or pushed.

## 8. Remaining blockers and recommendation
**Blockers**
1. Official logging is not approved (no approval JSON, by instruction); the amendment is a draft and must be approved as exact text with a new protocol hash and pre-registration before the first official batch.
2. The official logger is unchanged and cannot yet use this source: it needs a merged-snapshot input with the as-of filter, source-stated UTC kickoff handling, the extra provenance fields and kickoff-moved handling (listed in `02`). The isolated test code is not the logger.
3. Polling is manual. To keep staleness ≤ 14 days the Bundesliga must be polled after each matchday (about every 7–10 days); unsupervised polling needs your approval.
4. Evaluation power: the Bundesliga alone adds ~306 matches a season; the protocol minimum (5,000 eligible results from 25 competitions over 3 months) cannot be met by one league. The other 14 in-season leagues still lack 233 results; no expansion was done.
5. Wikipedia stays confirmation-only and unused; its licensing document is still unapproved.
6. Known data issues unchanged (Police FC / Vision FC collisions, Zimbabwe 2021-22 dates; none touches the Bundesliga).

**Recommendation:** OpenLigaDB is validated and attributable as a Bundesliga-only provider. It is **ready for your decision on the amendment** and could support a Bundesliga **dry-run (shadow) period** today. Official logging should **not** start yet: it needs (1) your approval of the final amendment text, (2) the logger changes in blocker 2 implemented and tested, and (3) the approval file. Timing: matchday 7 (kickoffs from 2026-10-23 18:30Z) has sealing deadlines of 2026-10-22 09:00 UTC under the existing rule and 2026-10-23 17:30 UTC under the amendment, which is too soon for the approvals and logger changes above; matchday 8 (kickoffs from 2026-10-30) is the realistic first target, provided the Bundesliga is polled again after matchday 7 so the 14-day window still covers it.
