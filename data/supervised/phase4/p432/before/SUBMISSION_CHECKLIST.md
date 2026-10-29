# Submission checklist

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

> **Phase 4.28 note:** Test counts and the `live_enabled: false` checks below are the Phase 4.7 record and are superseded: `config/sync.json` now shows `sync_mode: startup` with OpenLigaDB for BUNDESLIGA and LALIGA only; the latest results are in `TESTING_REPORT.md` and `docs/mini-project/phase4/P4_28_FINAL_CLEANUP_AND_READINESS.md`.

Status on 2026-10-27. **Done** = exists and was checked in this phase. **Pending** = needs an action or a decision. M = mandatory for submission, O = optional improvement.

## A. Deliverables

| # | Item | M/O | Status | Location / note |
|---|---|---|---|---|
| 1 | Project report | M | Done | `docs/mini-project/final/PROJECT_REPORT.md` |
| 2 | Source code (backend, frontend, models, tests) | M | Done, **uncommitted** | `app/`, `frontend/`, `tests/`, `scripts/`, frozen model folders. The work is in the working tree only (HEAD `970f461`); committing, tagging or zipping is **pending your decision** (nothing was staged or committed) |
| 3 | README | M | Done | root `README.md` now points to the mini-project docs; `app/README.md` has the run commands (it still says "51 tests", pre-dating the final suite) |
| 4 | Architecture description and diagram | M | Done as a text diagram | `ARCHITECTURE.md` §1. A drawn image (draw.io or a slide) is **optional** |
| 5 | ML models, data sources, testing, limitations documents | M | Done | `ML_MODELS.md`, `DATA_SOURCES.md`, `TESTING_REPORT.md`, `LIMITATIONS.md` |
| 6 | Installation and run instructions | M | Done | `SETUP_AND_RUN.md`; cold start verified |
| 7 | Demo script (2.5–3 min) | M | Done | `DEMO_SCRIPT.md`; **pending: one timed rehearsal by you** |
| 8 | Viva Q&A (25–30 questions) | M | Done (28) | `VIVA_QA.md`; **pending: read aloud once** |
| 9 | Screenshots | M | Done | 17 full-page screenshots at three widths in `docs/mini-project/phase4/p4.6/`, plus per-phase sets in `p4.1`–`p4.5`. Retaking them is optional |
| 10 | Dataset attribution and licences | M | Done | `DATA_SOURCES.md`, the in-app footer and "About the data", `/api/meta` |
| 11 | Final verification evidence | M | Done | `TESTING_REPORT.md` and `data/supervised/phase4/` logs |
| 12 | Phase 4.7 checkpoint report | M | Done | delivered in the chat reply (and summarised in the documents above) |

## B. Verification (all executed in this phase)

*The table below is the Phase 4.7 record. Later regression results (4.8B: backend 284, frontend 342 + 13 skipped / 355 live; 4.8C offline part: backend 299, frontend 344 + 13 skipped / 357 live; build passing) are in `TESTING_REPORT.md`, "Which numbers are which".*

| Item | Result |
|---|---|
| Backend tests | **260 passed, 0 failed, 1 warning (existing Starlette/httpx notice) in 15 min 30 s** |
| Frontend tests | 342 passed, 13 skipped intentionally; 355 of 355 with a live backend |
| Production build | passes |
| Cold start, 17 core endpoints, 10 workflows (33 assertions) | pass |
| 24 responsive views | no overflow, contrast failure or error banner |
| Frozen model hashes, integrity check, `live_enabled` false, scoreline disabled | verified |

## C. Open issues, in priority order

| # | Issue | M/O | Proposed action |
|---|---|---|---|
| 1 | **Production store hash differs from the recorded value** (one `sync_runs` row from a 2026-10-27 backend start and the resulting WAL checkpoint; the file was already in WAL mode; no match data changed; cause fixed in Phase 4.8B; evidence and a baseline recommendation are in `P4_8B_CHECKPOINT_REPORT.md` §2) | M: you decide, then record it | Either accept it and record the new hash in the integrity notes, or restore a pre-start copy (none with the old hash survives, so the old bytes cannot be reproduced exactly). Always use `FOOTIQ_STORE_PATH` on a private copy for demos |
| 2 | Nothing is committed to Git | M if the submission is a repository | Your call: commit to the branch or submit a zip of the folder |
| 3 | `scipy` is missing from the requirements files | O (documented in `SETUP_AND_RUN.md`) | Add `scipy==1.17.1` to `app/requirements.txt` |
| 4 | Season-simulator result tables use 9–11 px text; two 20 × 20 px radio inputs | O | Fix in a later UI pass |
| 5 | Drawn architecture diagram | O | Make one slide from `ARCHITECTURE.md` §1 |
| 6 | Full screen-reader accessibility audit | O | Out of scope for the mini-project |
| 7 | Backup copy of the project off this drive | O (recommended) | Copy the folder (excluding `.venv` and `node_modules`) to external storage |

## D. Day-of checklist

1. Private store copy and `FOOTIQ_STORE_PATH` set; no old dev server running.
2. Backend ready (`club_prediction_ready: true`); frontend open on Home without a red banner.
3. `config\sync.json` shows `sync_mode: startup` (OpenLigaDB, Bundesliga and La Liga only).
4. Demo script and fallback open; screenshots tab ready.
5. Know the three honest answers: data is historical and partly stale; v2-r1 and UEFA are unvalidated; final-position simulation is disabled on purpose.
