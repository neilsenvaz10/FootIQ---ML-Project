# Real-network scheduler trial (Bundesliga): request ledger

Rule from your approval: at most **five** explicitly logged GET requests in total, Bundesliga only, a private copy of production, no retries, rate limits respected, and **no request beyond the previously approved endpoint until you approve its exact URL**.

## Stage A: done (1 request)

| # | Time (UTC) | URL | Status | Bytes | SHA-256 | Outcome |
|---|---|---|---|---|---|---|
| R1 | 2026-10-27 15:11:04 | `https://api.openligadb.de/getmatchdata/bl1/2026` (the previously approved endpoint) | **200** | 316,983 | `b725c2f3e30a3320f75da9891a2cfd2b5b93aed231da16aab253cf81a6bd6b46` | scheduler first-fetch path: `ok`, 0 inserted, 0 updated, 243 unchanged, 63 confirmed, 0 quarantined; the snapshot is byte-identical to the A1 snapshot of 12:57 UTC (the provider's season file did not change in 2 hours); saved as `data/snapshots/p48d_trial/openligadb/20261027T151107Z_bl1_2026_season.json` |

Single attempt (`max_retries` 0), strict URL allow-list and hard cap in the opener, the contact string never printed, `config/sync.json` untouched (`live_enabled: false`), production file hash identical before and after (`1bfad5bd…cb278`).

## Stage B: **needs your approval before anything is sent**

The scheduler's normal (polling) path, which is what an unattended six-hour run would use, asks for the current matchday and for "last change" dates, and fetches a matchday only when it changed. These are different endpoints from the one already approved, so I have **not** called them. Proposed exact requests (4 real GETs; with R1 that makes **5 in total**, the cap):

| # | Exact URL | Purpose | Expected answer |
|---|---|---|---|
| R2 | `https://api.openligadb.de/getcurrentgroup/bl1` | which matchday is current | HTTP 200, a small JSON object with `groupOrderID` (expected 7 or 8) |
| R3 | `https://api.openligadb.de/getlastchangedate/bl1/2026/6` | when matchday 6 last changed | HTTP 200, one JSON date-time string |
| R4 | `https://api.openligadb.de/getlastchangedate/bl1/2026/7` | when matchday 7 last changed | HTTP 200, one JSON date-time string |
| R5 | `https://api.openligadb.de/getmatchdata/bl1/2026/7` | the 9 matches of matchday 7 (fetched because the private copy has no per-matchday change record yet) | HTTP 200, a JSON array of 9 matches (about 10 kB) |

* **Matchday 6** would also be fetched by the same polling logic; to stay within five requests I will answer that one call from the saved A1 snapshot (labelled "replayed, no network" in the ledger), so it is not a sixth network request.
* **If R2 does not return 7**, the later URLs change. I will then stop and ask you for the new exact URLs rather than adapt on my own.
* Requests are at least 3 s apart (plus jitter), no retries, strict allow-list, a private copy of production with no write to production, snapshots saved with SHA-256, config unchanged.
* Everything else the trial must show (restart, back-off, duplicate import, quarantine, failure safety) is already demonstrated in replay on the Stage A copy; Stage B adds only the live polling path.

Command prepared (not run): `real_network_trial.py --stage B --urls <R2> <R3> <R4> <R5> --replay-group 6`.
