# football-data.org access checklist (Phase 4.11)

Status: **adapter prepared and tested offline; nothing is active.** No request was made to football-data.org, no account exists, no token exists, PL/SA/FL1 are not in `sync.APPROVED` and `config/sync.json` lists none of them (`footballdata.enabled=false`).
Facts below come from the provider's public pages read on 2026-10-26 (details and clause numbers: `docs/mini-project/FOOTBALL_DATA_ORG_CHECKLIST.md`). They were **not re-read in this phase** (no network access was allowed), and the terms are dated 2018: re-check them on the day you register.

## A. Verified from the provider's pages (as read 2026-10-26)
| Item | Fact |
|---|---|
| Free plan | 0 EUR; 12 competitions including **Premier League, Serie A and Ligue 1** (and Bundesliga, La Liga); "scores and schedules delayed"; fixtures and tables |
| Request limit | **10 requests per minute** on the free plan; HTTP 429 when exceeded; 100 requests per 24 h unauthenticated (competition and area lists only) |
| Authentication | header `X-Auth-Token`; response headers `X-RequestsAvailable`, `X-RequestCounter-Reset` |
| Attribution | visible wording **"Football data provided by the Football-Data.org API"** (footer, about section or another visible place) |
| Key handling | one key per application; keep it confidential; must not sit in open-source code repositories (terms 6.1) |
| After you stop | you may not reference or publish football data obtained through the API (terms 9.1); cancelling a paid month deletes the account's stored data (4.6) |
| Fair use | "continually excessive" use can be cancelled; no number is given |

## B. NOT verified: only the provider (or your account) can settle these
- [ ] **Storage and reuse.** The terms are silent on keeping results in our own database, on using them to fit or evaluate a model, and on redistribution. **Do not assume a free key allows unrestricted storage or model training.** FootIQ records the licence of every imported row as "storage and reuse permissions unconfirmed" until you have an answer.
- [ ] **Free use for a college mini-project** (the pages do not restrict the free plan to non-commercial use, but do not mention it either).
- [ ] **Which seasons the free plan serves.** Coverage lists competitions, not seasons: whether 2026-27 is included is only visible after registering.
- [ ] **How long "delayed" is.** No duration is published. The first supervised read must show whether results older than a few hours are present.
- [ ] **What the real payload looks like.** The adapter follows the v4 documentation. Open points it flags on each record: `fullTime` taken as the 90-minute score when `duration` is REGULAR and `regularTime` is absent (`fulltime_taken_as_regular_time_unconfirmed`); the meaning of AWARDED/SUSPENDED/POSTPONED/CANCELLED (held for a human, never scored); whether `resultSet.count` is always present (without it the response is rejected as incomplete).
- [ ] **Whether the token format is 32 characters** (the adapter only requires 16-128 printable characters without spaces).
- [ ] **Team names.** Exact and normalised-name matching only. Any club name the store does not know is quarantined, never guessed; the first supervised read prints an identity report so aliases can be reviewed before import.

## C. Exact steps for you (nothing here was done for you)
1. Read https://www.football-data.org/about (terms) and https://www.football-data.org/pricing again; note the date.
2. Decide whether to e-mail the provider (address on their documentation site) with the three questions in B: storage in a local database, use for a university mini-project and for fitting/evaluating a model, season coverage. I have not written to them.
3. Register a free account yourself at https://www.football-data.org/client/register (your name and e-mail; accepting the terms is your decision). Use your own account: one key, this application only.
4. Open the account page and check the competitions list shows PL, SA and FL1, and whether season 2026 is offered.
5. Put the token in a **user environment variable**, never in a file of the project, chat, screenshot or Git:
   ```powershell
   [Environment]::SetEnvironmentVariable('FOOTBALL_DATA_API_TOKEN', (Read-Host 'Paste token'), 'User')
   ```
   Then **sign out and back in** (the `FootIQ-Backend` task inherits the environment from log-on) or restart the backend from a new terminal.
6. Check that it is set without printing it:
   ```powershell
   [bool]$env:FOOTBALL_DATA_API_TOKEN
   ```
7. Tell me "token ready". The next phase (needs your explicit approval) is one supervised read of the three leagues: three requests at least 7 s apart, saved snapshots with SHA-256, an identity report, a dry-run diff against production on a private copy. No import and no activation before you review it.
8. Activation, much later and only after review: add the three keys to `sync.APPROVED` (moved from `PREPARED_PROVIDERS`) and to `config/sync.json` (`footballdata.enabled=true`), controlled production cycle with backup, restart. Each league then keeps its own six-hour schedule and back-off inside the existing scheduler.

## D. What to expect from the first real import (read before approving)
- The adapter adds **kick-off times** (the store holds none for Serie A and Ligue 1 and for part of the Premier League): rows are "updated" by that enrichment, scores and dates stay as stored.
- A fixture whose date differs from the stored one is held as DATE_DIFFERENCE; a differing score as CONFLICT; both wait for you.
- The free tier's delay means results may appear hours late; the status panel will show "lagging" if fixtures stay without results for 3+ days.
- Attribution text appears in the status panel only for leagues that are approved; add it to any public page that shows this data.

## E. Where it lives
Adapter `app/store/footballdata.py`; scheduler wiring `app/store/sync.py` (`PREPARED_PROVIDERS`, `_sync_footballdata`); tests `tests/test_footballdata_sync.py` (23, no network). The token is read from the variable named in `config/sync.json` (`footballdata.token_env`), is redacted from every stored error, and a missing or malformed token stops the league before any request.
