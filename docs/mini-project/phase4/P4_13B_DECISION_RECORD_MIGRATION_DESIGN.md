# Decision-record migration: design (Phase 4.13B)

Status: **design only, for your review.** Nothing in this document has been implemented, run or applied. No table exists, no code was changed, no date was corrected, no database was touched, no request was made. Implementation needs your separate written approval, and the provider's answer comes first (see `P4_13_DATE_REVIEW_AND_ACTIVATION_READINESS.md`).

## 1. Purpose
A `DATE_DIFFERENCE` finding in `quarantine` has no "resolved" state: the 57 findings open today and the 96 football-data.org findings can only be left open or hand-edited. This design lets **you** resolve a dispute with an auditable, reversible record, and lets the system keep treating every unresolved dispute exactly as it does now. Nothing resolves a dispute by itself.

Principles: additive only (new tables, no change to existing tables or rows by the migration itself); append-only audit tables; one transaction per batch; a verified backup before anything is written; every changed field recorded with its old and new value; a tested rollback; the sync, forecasts and models are not touched.

## 2. What exists today (facts checked in the code)
- `quarantine(id, run_id, source, source_ref, reason, payload, created_utc)`; a finding is written once per (source, source_ref, reason); the same text is never inserted twice, so a resolved finding keeps suppressing its own repetition.
- `app/disputes.py` reads every `DATE_DIFFERENCE` row to give the kick-off rule the candidate dates (the earliest wins). `sync._quarantine_view` counts rows as "needing review". `baseline_monitor` and `daily_audit` treat any unexplained change of a `matches` row as UNEXPECTED (ALERT).
- `db.init` (which runs the schema script) is called only by `app/store/build.py`, not at application start-up, so adding tables to `SCHEMA` would **not** migrate production silently. The migration must therefore be an explicit tool.
- `baseline_hash.logical` hashes **every** table; adding tables changes the combined logical hash. A new baseline checkpoint (v4) is needed after the migration; per-table hashes of existing tables stay comparable.
- `meta('schema_version')` is `1`.

## 3. Schema changes (version 1 to 2; all new tables, none altered)
```sql
CREATE TABLE decision_batches (
  batch_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  created_utc     TEXT NOT NULL,
  reviewer        TEXT NOT NULL,                 -- the person signing, e.g. the project owner
  signed_utc      TEXT NOT NULL,                 -- when the decision file was signed
  file_name       TEXT NOT NULL,
  file_sha256     TEXT NOT NULL,                 -- hash of the signed decision file (kept with the project)
  backup_path     TEXT NOT NULL,                 -- verified pre-apply backup
  backup_sha256   TEXT NOT NULL,
  applied_utc     TEXT,                          -- NULL until the batch commits
  run_id          INTEGER REFERENCES sync_runs(run_id),   -- the 'date_decision' run that applied it
  summary_json    TEXT
);
CREATE TABLE date_decisions (
  decision_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id        INTEGER NOT NULL REFERENCES decision_batches(batch_id),
  quarantine_id   INTEGER NOT NULL REFERENCES quarantine(id),
  record_id       TEXT NOT NULL REFERENCES matches(record_id),
  decision        TEXT NOT NULL CHECK (decision IN ('accept_provider','keep_stored','set_other')),
  old_date        TEXT NOT NULL, new_date TEXT NOT NULL,                 -- new_date = old_date for keep_stored
  old_kickoff_utc TEXT, new_kickoff_utc TEXT,
  evidence_tier   TEXT NOT NULL CHECK (evidence_tier IN ('T0','T1','T2','T3')),
  evidence_url    TEXT NOT NULL, evidence_checked_on TEXT NOT NULL, evidence_note TEXT,
  official_score_home INTEGER, official_score_away INTEGER,              -- required for a finished match
  provider_snapshot_id TEXT,                                             -- the saved response the provider date came from
  decided_utc     TEXT NOT NULL,
  UNIQUE (batch_id, record_id)
);
CREATE TABLE quarantine_events (            -- state of a finding = its newest event; the quarantine row itself is never edited
  event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  quarantine_id   INTEGER NOT NULL REFERENCES quarantine(id),
  event           TEXT NOT NULL CHECK (event IN ('resolved','reopened')),
  decision_id     INTEGER REFERENCES date_decisions(decision_id),
  at_utc          TEXT NOT NULL, by_reviewer TEXT NOT NULL, note TEXT
);
CREATE TABLE match_field_history (          -- every field a decision changed, old and new
  history_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id       TEXT NOT NULL REFERENCES matches(record_id),
  field           TEXT NOT NULL CHECK (field IN ('match_date','kickoff_utc','time_precision','status','home_goals_90','away_goals_90')),
  old_value TEXT, new_value TEXT, decision_id INTEGER NOT NULL REFERENCES date_decisions(decision_id), changed_utc TEXT NOT NULL
);
-- append-only: no update or delete on the four tables
CREATE TRIGGER no_update_decision_batches BEFORE UPDATE OF created_utc, reviewer, signed_utc, file_sha256, backup_sha256 ON decision_batches BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER no_update_date_decisions BEFORE UPDATE ON date_decisions BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER no_delete_date_decisions BEFORE DELETE ON date_decisions BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER no_update_quarantine_events BEFORE UPDATE ON quarantine_events BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER no_delete_quarantine_events BEFORE DELETE ON quarantine_events BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER no_update_match_field_history BEFORE UPDATE ON match_field_history BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER no_delete_match_field_history BEFORE DELETE ON match_field_history BEGIN SELECT RAISE(ABORT, 'append-only'); END;
UPDATE meta SET value='2' WHERE key='schema_version';        -- the only write to an existing table by the migration itself
```
`decision_batches.applied_utc`, `run_id` and `summary_json` may be set once, inside the applying transaction (the trigger protects the signed fields). No existing column, table or row is changed by the migration; the `meta` value is the single exception and is recorded in the report.

## 4. Decision file (the only way a decision enters the system)
A CSV or JSON produced from `P4_13B_DATE_VERIFICATION_SHEET.csv` after **your** verification, one row per record: `record_id, decision, old_date, new_date, evidence_tier, evidence_url, evidence_checked_on, official_score_home/away (finished only), note`, plus a header with `reviewer`, `signed_utc`. Its SHA-256 is stored in `decision_batches`. The tool refuses a file that is unsigned, edited after signing, or contains a row that fails any rule below.

Validation rules (every one is a hard refusal, nothing partial): the record exists and belongs to a league named in the file's scope; `old_date` equals the date **now** stored (a stale decision is refused); every decision matches an **open** `DATE_DIFFERENCE` finding whose quarantined payload carries the proposed `new_date`, except `set_other`, which needs a note and tier T1; evidence url and date present; a shift above 3 days, a non-TIMED/FINISHED provider status or a match with a saved forecast is allowed only as a single-row batch with tier T0/T1; a finished match needs the official score and it must equal the provider's saved score, otherwise the result stays held; one decision per record; `keep_stored` changes nothing but still resolves the finding.

## 5. What applying a batch does (one transaction, `BEGIN IMMEDIATE`)
1. Check preconditions (section 7); take the run lock the scheduler uses (`_begin_run`) so no sync cycle overlaps; insert a `sync_runs` row of kind `date_decision`.
2. For each `accept_provider`/`set_other`: update `matches.match_date` (and, if the decision says so, `kickoff_utc` and `time_precision` from the saved provider response) through the same upsert the importer uses, so `content_hash`, `change_count` and `last_changed_utc` stay correct; write one `match_field_history` row per changed field.
3. Insert the `date_decisions` rows and one `quarantine_events('resolved')` row per finding. The `quarantine` rows are never modified or deleted.
4. For a finished match whose date was accepted, **do not** write the result in this tool: the held result is imported by the normal reconciliation (the saved snapshot or the next sync) after the date matches, so the score goes through the same safeguards as every other result. (If you prefer, the tool can run that one reconciliation inside the same transaction from the saved snapshot; this is an option to decide at implementation.)
5. Update `decision_batches` (`applied_utc`, `run_id`, `summary_json`), commit; any error rolls the whole batch back.
Effects on the rest of FootIQ (code changes needed, all small and each with a test): `disputes.by_record` and `sync._quarantine_view` must ignore findings whose latest event is `resolved`; `baseline_monitor` and `daily_audit` must recognise a `date_decision` run as an explained change (otherwise they raise ALERT, correctly, for an unrecognised change); the status panel shows resolved counts. Saved forecasts are immutable and untouched; a date moved after a forecast was saved never rewrites it (existing rule).

## 6. Audit trail
Who (reviewer name), when (signed and applied UTC), why (tier, evidence URL, page date, note), what (old and new value of every field), which file (SHA-256 of the signed decision file), which backup (path and SHA-256), which run (`sync_runs` row, `detail` with counts). A report file `data/supervised/phase4/p413/decision_batch_<id>.json` is written at apply time. Nothing in the audit tables can be edited or deleted without dropping a trigger, which would itself appear in the schema hash.

## 7. Backup requirements (before the migration and again before every batch)
1. SQLite online-backup API copy of `data/footiq.sqlite` into `data/backups/footiq.<UTC>.pre-<migration|batch-N>.sqlite` (works with the running backend and its WAL).
2. Verify the copy: `PRAGMA integrity_check` = ok; per-table logical hash equal to production; row counts equal; physical SHA-256 recorded.
3. Restore test: copy the backup to a private file, open it, check integrity and `matches` row count (the existing helper does this); keep the restored copy until the batch is verified.
4. Preconditions to apply: production integrity ok; scheduler idle and the next Bundesliga/La Liga check not due within 30 minutes (or the run lock held); exclusive write lock obtainable; no forecast written for an affected fixture unless it is a T0/T1 single-row batch; Git has nothing staged by the tool.

## 8. Rollback procedure
- **Before commit:** the transaction rolls back; nothing changed.
- **After commit, a wrong decision:** `revert_date_batch --batch N` (a second one-shot tool, also dry-run by default) writes the old values back from `match_field_history`, adds new history rows and `quarantine_events('reopened')`, and records a `date_decision` run; the findings are open again and every audit row stays. A reverted batch cannot be re-applied; a new decision file is needed.
- **Worst case:** stop the backend (`footiq_service.ps1 stop`), copy the verified pre-batch backup over `data/footiq.sqlite` (and remove `-wal`/`-shm`), verify its hash against `decision_batches.backup_sha256` (kept in the backup's own report), restart. Anything the sync wrote after the backup is lost and is re-fetched at the next cycle; this is the reason the apply step takes the run lock and happens right after the backup.
- **Removing the schema** is never needed (the tables are inert); if ever wanted, export them first, then drop in reverse order of creation.

## 9. Restore-test and test plan (all on private copies, before any real use)
1. Copy production to a private file. Run the migration. Check: only the new tables, triggers and `schema_version` differ; every existing table's row hash is unchanged; integrity ok.
2. Apply a **synthetic** decision file (invented ids in the copy) covering `accept_provider`, `keep_stored`, `set_other`, a finished match, a stale `old_date`, a shift above 3 days, an unsigned file, a tampered file, a duplicate record: assert each refusal is whole-batch and each accepted batch matches its file.
3. Revert the batch: logical hash of `matches` and `quarantine` equals the pre-batch hash; resolved findings are open again.
4. Restore from the pre-batch backup into a second private copy: integrity ok, row counts equal, hash equals the recorded backup hash.
5. Run the targeted existing tests against the migrated copy (sync, monitoring, scheduler, La Liga, disputes, kick-off tests) and confirm the Bundesliga and La Liga rows are byte-identical to the pre-migration copy.
6. Compatibility: the **current** code (unaware of the tables) runs against a migrated copy and behaves as today; the **new** code runs against an unmigrated copy and treats "no tables" as "no resolutions".
7. Triggers: an UPDATE/DELETE on each append-only table aborts.
8. Concurrency: a sync cycle started during an apply is refused by the run lock; an apply while a cycle runs refuses.
9. Baseline: after the migration, a new baseline checkpoint (v4) is proposed by the monitor and approved by you; the daily audit passes with the new run kinds.

## 10. Order of work after your approval
(a) implement migration tool and tests on private copies only; (b) review report; (c) run on production with backup, no decisions yet (empty tables); (d) checkpoint v4; (e) later, apply decision batches one league at a time after your verification (PL T2 first). Each step stops for your review. The tool for applying decisions is not written until (c) is accepted.

## 11. Explicitly out of scope
No automatic decision; no editing of `quarantine`; no change to the sync, adapters, models, forecasts, Bundesliga or La Liga behaviour; no provider request; no activation of PL, SA or FL1.
