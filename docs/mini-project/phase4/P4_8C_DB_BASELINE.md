# Production store: two-part integrity baseline (adopted in Phase 4.8C)

Adopted 2026-10-27 at your instruction. The production file was **not** modified, restored or repaired. Tool: `app/store/baseline_hash.py` (read-only, SQLite `mode=ro`). Recorded values: `data/supervised/phase4/p48c/db_baseline_v2.json`. Tests: `tests/test_baseline_hash.py` (9). The integrity script (`phase4_integrity.py check`) now compares both parts.

## The two parts

| Part | What it is | What it detects |
|---|---|---|
| **Physical** | SHA-256 of the file's bytes | that *anything* wrote to the file: a log row, a WAL checkpoint, a VACUUM |
| **Logical** (`footiq-logical-v1`) | SHA-256 over the content of every table, with only the documented operational rows left out | that the *business data* (matches, fixtures, teams, aliases, quarantine, provenance, forecasts, simulations) changed |

**Recorded values (baseline v2):** physical `3641e4da47b3930cbb543499d393b2360f1e117481ad35349b082a4682073922` (228,655,104 bytes, journal mode WAL, integrity_check ok); logical `e32d759bddef1688116c1c91430cbf10384724e525971994f4e085312a96f29d`.
Superseded: the 2026-10-25 post-import physical hash `39ab9651…61f3` (kept as history) and the provisional logical value `b182836f…` used in the Phase 4.8B report, which came from a simpler draft of the algorithm.

## Logical algorithm, exactly

1. **Tables included:** every `sqlite_master` row with `type='table'` and a name not starting with `sqlite_`, in ascending name order. Today: competitions 162 rows, forecast_runs 0, forecasts 0, match_sources 224,519, matches 223,510, meta 2, quarantine 273, simulation_runs 0, source_snapshots 9, source_state 1, sync_errors 0, sync_runs 7 (of 8), team_aliases 7,447, teams 5,188.
2. **Schema:** the table's `sql` text with whitespace collapsed, hashed; a changed column or constraint changes the result.
3. **Columns:** all of them, in table order. Nothing is dropped.
4. **Normalisation of values:** NULL → `null`; integer → integer; text → text; float → the string `"f:"` + Python `repr`; blob → `"b:"` + hex. A row becomes the compact JSON array of its values (`ensure_ascii=False`, separators `,` `:`).
5. **Ordering:** the row strings are sorted lexicographically. This is a total order, so row order, rowid, insertion history, page layout, VACUUM and journal mode cannot change the result (tested).
6. **Table hash:** SHA-256 of `"<table>\n"` + schema hash + `"\n"` + each row string + `"\n"`.
7. **Combined hash:** SHA-256 of one line per table, `"<table>:<row count>:<table hash>\n"`.
8. **Exclusions — the only ones:** rows of `sync_runs` with `run_id > 7`. Runs 1–7 (baseline import, the 2026-10-25 live check and the two offline snapshot imports) **are** hashed. The excluded rows are listed in every report (today: run 8, `startup_check`, `skipped_live_disabled`, 2026-10-27T10:37:37Z), so nothing is hidden. No match, fixture, prediction, forecast, simulation, team, alias, quarantine, snapshot or source-state row is ever excluded; changing any of them, or a baseline-era log row, changes the logical hash (tested).

## Rules for using it

* A normal start of the application changes neither part (Phase 4.8B: 3 cold starts, bytes identical).
* Physical hash changed, logical unchanged → something wrote only operational log rows or file layout. Investigate, do not alarm.
* Logical hash changed → business data changed. Only an approved import may do that, and it creates **baseline v3** (new recorded pair, old pair kept); it is never an edit of this one.
* Compare on a **copy** if you must not even create empty `-wal`/`-shm` files.

```
.venv\Scripts\python.exe app\store\baseline_hash.py <copy-of-store.sqlite>
.venv\Scripts\python.exe data\supervised\phase4\phase4_integrity.py check
```

## Addendum (Phase 4.8D Stage 1): baseline v3

After the six approved production results (two Bundesliga, four La Liga; two separate transactions, each with its own verified backup and checkpoint) the current baseline is **v3**, recorded in `data/supervised/phase4/p48c/db_baseline_v3.json`:

| | Physical (file bytes) | Logical (`footiq-logical-v1`, cut-off run id) |
|---|---|---|
| v2 (history) | `3641e4da47b3930cbb543499d393b2360f1e117481ad35349b082a4682073922` | `e32d759bddef1688116c1c91430cbf10384724e525971994f4e085312a96f29d` (run ≤ 7) |
| after the Bundesliga import | `40f4475ce7f9276736db83880c2c60e2cb5347884c913a2b977f04dbdc0a309b` | `f66de9343abd43d7b7b4cba1dc7fc6342ce071c723d73f25348ea074c045ca07` (run ≤ 9) |
| **v3 (current, after La Liga)** | `1bfad5bd4663e70776ef9da35f5c89eeed11b1ed7274ee7fdb562e266a9cb278` | `b3dcf8c0d04aa4538da77f4dc21c267b6414bb7e3c61692ad24a0ec4c2c1d95f` (run ≤ 10) |

The algorithm is unchanged. Only the cut-off moves: v2 hashed `sync_runs` rows 1–7; v3 hashes rows 1–10 (the earlier diary row 8 and the two import runs 9 and 10 are now part of the frozen history), and any later row is an operational diary line that is listed in the report, not hashed. The integrity script checks v3 as current and v2 as history (v2 is expected to read "differs" now: the imports legitimately changed the data).
