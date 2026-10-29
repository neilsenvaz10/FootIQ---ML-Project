# Phase 4.18B: controlled backend restart checklist

Status: prepared, **not executed**. The production backend (port 8000) is stopped and must stay stopped until you approve.

## Before starting (read-only)
1. Confirm nothing listens on port 8000.
2. Confirm `data/footiq.sqlite` sha256 is `1501bfb128c716519dde7b770e7610b6f4eaa68253ac8ead8f00e19593f9282b` (or note any change) and `PRAGMA integrity_check` is ok.
3. Confirm `config/sync.json` is in startup mode (Bundesliga and La Liga only).
4. Confirm the rollback package exists: `data/backups/p418_rollback_20261028/` (manifest of 51 files).
5. Note the starting simulation count: 2 saved runs (Bundesliga, La Liga).
6. Full backend suite and frontend suite green (see the Phase 4.18B report).

## Start
Foreground in a visible terminal (so a stop is seen and the cause is not hidden):
`.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000`
Startup makes one refresh for Bundesliga and La Liga (at most 2 provider requests, OpenLigaDB, already approved). Do not use a detached WMI launch: detached processes have ended without any log of a cause.

## Verify
- `/api/competitions` returns exactly 6 keys; `/api/competitions/WC/teams` and `/api/worldcup/simulate` return 404.
- `/api/data-freshness`: Bundesliga and La Liga "startup_updated", others "historical_only".
- `/api/predict` works for each of the six.
- `/api/sync/status`: startup mode, 0 scheduler threads.
- Saved simulations still 2; database integrity ok.
- Frontend pages show only the six competitions.

## Stop conditions
Any 5xx on the checks above, any sync request to PL/SA/FL1, any database error: stop uvicorn (Ctrl+C) and tell me before changing anything.

## Rollback
Honest limit: there is no copy of the pre-4.18 code. `ACTIVE_KEYS` alone does not restore the old application (see `README_ROLLBACK.md`). Data needs no rollback (no data changed). Stopping the new backend is the only immediate safe action.
