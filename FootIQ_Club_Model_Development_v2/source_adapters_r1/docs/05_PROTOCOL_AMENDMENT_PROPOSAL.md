# 05 Proposed amendment A1 to the prospective evaluation protocol — DRAFT FOR REVIEW, NOT ACTIVE

Applies to: `matched_v1_prospective_r1/09_PROSPECTIVE_EVALUATION_PROTOCOL.md` (sha256 recorded in `PREREGISTRATION_r1.json`). **The frozen protocol, its hash, the models and the logger are unchanged.** If approved, the amendment would be issued as protocol r2 with a new hash and a new pre-registration file **before the first official batch**; it never applies retroactively. Everything not listed below (models, comparators, primary metric, secondary metrics, gates, minimum sample, stopping rules, 14-day staleness rule, 60-minute lead rule, 14-hour time-zone allowance, identity-collision exclusions) stays as registered.

## A1.1 Accepted result sources
1. **S1 openfootball** (CC0; pinned commit): accepted for results and schedule.
2. **S2 OpenLigaDB** (ODbL 1.0), only for league-seasons on the validated list (`VERIFIED_LEAGUES`; at present Bundesliga 2026): accepted for results, fixtures, kickoff times.
3. **S3 Wikipedia** (CC BY-SA 4.0), only for pages in the reviewed registry whose template style has been validated: accepted **only after the owner approves `02_WIKIPEDIA_LICENSING_AND_USE.md`** (option A: internal-use source; option B: confirmation-only; option C: not used). Under option B, S3 can confirm but never be the sole source of a result.
No other source may be used. Adding a source or league requires a new amendment.

## A1.2 Source-specific provenance (stored with every prediction's input snapshot and every outcome)
* S1: repository, commit sha and commit date, file path and line, retrieval timestamp.
* S2: matchID, leagueId/shortcut, season, group, `lastUpdateDateTime`, snapshot id and sha256, retrieval UTC, `resultTypeKind` used, ODbL attribution string.
* S3: page title, revision id and revision timestamp, permalink, cell reference, retrieval UTC, attribution string, flag `date_inherited_from_openfootball_schedule`, flag `derived_from_cc_by_sa`.
* All: adapter version, snapshot sha256, request ledger entry, staging record id.

## A1.3 Conflict resolution
1. A **conflict** is any disagreement between two admitted sources, or between two revisions/snapshots of one source, on (a) the regulation score, (b) the fixture status (completed vs not), or (c) the match date by more than one calendar day after UTC conversion.
2. Conflicts are **never resolved automatically** (no majority vote, no source ranking). Both records are quarantined in `conflicts.csv`.
3. A quarantined fixture is **excluded from the primary evaluation**; every later fixture of either club is flagged `unresolved_conflict` and is not primary-eligible until the conflict is adjudicated.
4. Adjudication is a human decision recorded in an append-only log (decision, evidence reference, date, person). A decision can only restore eligibility of later fixtures; it cannot change a prediction or a frozen model. Fixtures whose label stays in dispute are reported as a count.

## A1.4 Regulation-time label verification
A result is a **confirmed 90-minute label** only if all hold:
1. The result type is explicit regulation time: S2 `resultTypeKind = After90Minutes`; S1 per the v1.1 label rules (`reg_basis`, no extra time/penalties); S3 only for a regular-season league fixture whose cell is a clean `home–away` score without annotation (no extra time exists in the competition format).
2. Status is completed — not awarded, abandoned, postponed, cancelled or unclassified.
3. **Confirmation:** the same score is reported by (i) two admitted sources, or (ii) one source in two snapshots/revisions at least 24 h apart, the first at least 48 h after the match; and no admitted source disagrees at any time.
4. Scores with extra-time/penalty-only or unclassified final types (`completed_unclassified_score`) are never labels.
Matches failing these are excluded and counted by reason.

## A1.5 Feature freshness requirements
1. Features for a prediction use only results dated **before the fixture date** that are present in the merged input snapshot retrieved **before the prediction timestamp**; the snapshot id and sha256 are logged.
2. A result enters the feature state only if it is a completed 90-minute result with no unresolved conflict; S3-derived results additionally require the stable-revision rule (A1.4 item 3 (ii)) and, if option A is chosen, carry `derived_from_cc_by_sa` into the log.
3. Inherited dates (S3) are used for chronological ordering only and are flagged; if the date source later changes, the affected predictions are not rewritten but the fixture is flagged.
4. Unchanged: the competition's latest completed result must be no older than 14 days before the fixture date; clubs with an unresolved past-dated fixture lose primary eligibility; the frozen feature generator, models and preprocessing are used unchanged.
5. Evaluation reports must include a sensitivity analysis excluding every prediction whose features or label depend on S3 or S2.

## A1.6 Prediction timestamp rules
1. Unchanged: each prediction is written, hashed and chained before the fixture's **earliest possible kickoff minus 60 minutes**, taken from the UTC system clock at sealing.
2. Earliest possible kickoff = the **source-stated UTC kickoff** when an admitted source states one (S2); otherwise match date 00:00 UTC − 14 h (unchanged rule).
3. If sources disagree on the kickoff time by more than 30 minutes, the earlier time applies.
4. A fixture already completed in the input snapshot, or already past its earliest possible kickoff, is rejected and never logged; no backdating.

## A1.7 Prospective evaluation eligibility
A fixture is primary-eligible only if the registered conditions (a)–(g) hold and additionally: (h) both clubs resolve through the frozen identity map without ambiguity; (i) no club is on the identity-collision exclusion list; (j) the competition has at least one admitted source with a passed validation run and the staleness condition is met by an admitted source; (k) there is no `unresolved_conflict` for either club; (l) the outcome is a confirmed 90-minute label under A1.4. Reports state the share of labels by source mix (single-source / two-source) and the sensitivity run of A1.5.5.

## A1.8 Activation
This amendment is inactive. It becomes effective only if the owner (1) approves the exact text above, (2) decides the Wikipedia option (A1.1 item 3), (3) configures a real contact for live ingestion, and (4) a new protocol hash and pre-registration are written before the first official batch.
