# Protocol amendment A1 — final proposed text (NOT ACTIVE, NOT HASHED)

Amends: `matched_v1_prospective_r1/09_PROSPECTIVE_EVALUATION_PROTOCOL.md` (r1). Effective only if the owner approves this exact text, after which it is issued as protocol r2 with a new hash and a new pre-registration **before the first official batch**; it never applies retroactively and never to shadow runs. Unchanged: models and comparators, metrics, minimum sample, stopping rules, success criteria, the 14-day competition freshness rule, the identity-collision exclusions. Rule numbers below are implemented (and tested) in `prospective_logger_v2.py` unless marked "manual".

## A1.1 Accepted sources and competition scope
1. **S1 openfootball** (CC0, pinned repository commits): results and schedule for every competition in the frozen universe.
2. **S2 OpenLigaDB** (ODbL 1.0): results, fixtures and UTC kickoff times for **league `bl1`, season 2026 (Bundesliga 2026-27) only**. Any further league or season needs a validation run (>= 99.5% exact score agreement on overlap, 0 unexplained conflicts, 0 identity ambiguities, explicit result types) and the owner's approval of a new amendment.
3. **S3 Wikipedia** (CC BY-SA 4.0): independent **confirmation only**; never the sole source of a result, never in the feature state, never a source of dates or kickoff times; unused until the owner approves the licensing document.
4. No other source. All retrieval follows the source's current terms (OpenLigaDB: change-date polling, <= 60 requests/min, jitter, back-off, descriptive User-Agent with contact; Wikimedia policies). Polling is manual unless the owner approves a schedule (manual).

## A1.2 Canonical records when sources agree
Both source records are kept. The canonical **score and match date** are S1's if S1 holds the match, otherwise S2's; the canonical **kickoff time and result type** are S2's. A canonical record is never built from a pair that is in conflict.

## A1.3 Score and status conflicts
1. A conflict is any disagreement between two admitted sources, or between two snapshots of one source, on (a) the regulation score, (b) completed vs not completed, (c) the match date by more than one calendar day after UTC conversion.
2. Conflicts are never resolved automatically: no majority, no source ranking. Both records are quarantined; the fixture is excluded from the primary evaluation; every later fixture of both clubs carries `unresolved_conflict` and is not primary-eligible until a human adjudication is recorded in an append-only log (manual). An adjudication restores eligibility of later fixtures only; it never changes a sealed prediction or a model.
3. Duplicate records (same ordered pair twice in one snapshot) are treated as conflicts for the clubs involved.

## A1.4 Regulation-time outcome labels
A fixture has a confirmed 90-minute label only if all hold: (1) the result type is explicit regulation time — S2 `resultTypeKind = After90Minutes`; S1 per the v1.1 label rules; (2) status completed (not awarded, abandoned, postponed, cancelled, unclassified); (3) the same score is reported by two admitted sources (at least one of S1/S2), or by one S1/S2 source in two snapshots at least 24 h apart with the first retrieved at least 48 h after the kickoff; (4) no admitted source disagrees at any time. A final score typed Unknown, after stoppage time, after extra time or after penalties is never a label. Excluded fixtures are counted by reason.

## A1.5 Source retrieval timestamps and feature freshness
1. Every snapshot has a retrieval timestamp (UTC) and a sha256, verified before each use.
2. A result may enter a prediction's features only if its snapshot was retrieved **at or before the prediction timestamp** and its kickoff precedes that retrieval; snapshots retrieved later are not read.
3. A result enters the feature state only if it is a completed explicit 90-minute result from S1 or S2 without an unresolved conflict. No S3 value enters the feature state.
4. One merged history (frozen universe + admitted S2 results) and one cutoff date are used for **all models** (original v1, matched v1, frozen v2, v1 Elo); the merged-state hash is stored in each record.
5. Unchanged: the competition's latest completed result must be no more than 14 days before the fixture date; clubs with an unresolved past-dated fixture are not primary-eligible.
6. The frozen training snapshot, datasets, models and preprocessing are never modified.

## A1.6 Kickoff snapshots and rescheduled fixtures
1. The kickoff used for sealing is the UTC kickoff stated by S2 (`time_precision = utc`), taken from a snapshot **retrieved no more than 24 h before the prediction timestamp**; otherwise the fixture is not sealed.
2. If a fixture lacks a source-stated UTC kickoff, the existing rule applies (match date 00:00 UTC − 14 h) and the legacy deadline is recorded.
3. If admitted sources disagree on the kickoff time by more than 30 minutes, the earlier time applies.
4. After sealing, a sealed record is never edited or deleted. A side-car reassessment records changes:
   * kickoff moved **later**: eligible, flagged `rescheduled_later` (moved by 7 days or more: `postponed_more_than_7_days`, reported as a separate stratum);
   * kickoff moved **earlier** so that the sealing time is later than the new kickoff − 60 min: ineligible (`ineligible_sealed_too_late_after_move`);
   * fixture identity (either club) changed: ineligible (`ineligible_identity_changed`);
   * fixture missing from the newest snapshot (cancelled/removed): ineligible (`ineligible_fixture_removed`);
   * no result 7 days after kickoff: ineligible (`ineligible_no_result_after_7_days`); result conflicting between snapshots: ineligible until adjudicated;
   * all reassessments are separate hash-chained records referencing the original record's sha256.

## A1.7 Prediction sealing
1. A prediction is sealed (written, hashed and chained, read-only) at least 60 minutes before the kickoff stated in A1.6; the deadline is recorded in the record. A fixture whose deadline has passed, or whose result is already in the snapshot, is rejected and never logged: no backdating.
2. Sealing uses the UTC system clock; the record stores the prediction timestamp, the minutes remaining to the deadline, model sha256s, snapshot ids and sha256s, merged-state hash, frozen-universe hash, logger code hash and its own sha256.
3. A sealed prediction must be exactly reconstructible from the saved snapshots and its own timestamp (tested for every record); a mismatch invalidates the record for evaluation.
4. Shadow records live in a separate namespace and never count; the OFFICIAL namespace refuses unless the owner's approval file and the active amended protocol both exist.

## A1.8 Evaluation eligibility
Registered conditions (a)–(g) of protocol r1 and additionally: both clubs resolve through the frozen identity map without ambiguity; no identity-collision club; the competition has an admitted source with a passed validation (S2 only for the A1.1 scope); no `unresolved_conflict` for either club; the kickoff snapshot was fresh at sealing (A1.6.1); the outcome is a confirmed 90-minute label (A1.4); the side-car reassessment does not make the fixture ineligible. Reports state label source mix (single/two-source) and include sensitivity analyses excluding S2-dependent predictions and labels confirmed with S3.

## A1.9 Attribution and provenance
Every record carries the S2 attribution "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0" and licence ODbL-1.0; S1 records carry repository, commit and file/line; S3-derived confirmations carry page title, revision id, permalink and the CC BY-SA 4.0 notice. Published tables must repeat the attributions. Contact information is never written to records, snapshots, ledgers, reports or tracked files.

## A1.10 Activation
Inactive until: (1) the owner approves this exact text and the Wikipedia confirmation-only use; (2) the protocol r2 hash and a new `PREREGISTRATION` are written; (3) the owner creates `OFFICIAL_LOGGING_APPROVED.json`; (4) the logger changes are accepted as the production logger (they currently exist only as the shadow module).
