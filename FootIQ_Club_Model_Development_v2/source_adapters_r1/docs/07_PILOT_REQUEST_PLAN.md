# 07 OpenLigaDB Bundesliga pilot — request plan for your review (nothing has been sent)

Plan file: `pilot/request_plan_r1.json` — **plan sha256 `d7c2169e117a02f3e72b0517f171f2b11fb7f3d609156619cfd7421615a18bc9`**. The pilot runs only if you pass exactly this value (`python -I pilot_openligadb.py run --plan-sha256 <sha>`), a contact is configured, and no Bundesliga match is within 1 h before / 3 h after kickoff.

## Destination and nature
One host: `https://api.openligadb.de`, HTTP GET only, no body, no authentication, no cookies. Read-only.

| # | Request | Why | Size |
|---|---|---|---|
| R1 | `GET /getavailableleagues/2026` | confirm exact league id/shortcut/season (expected leagueId 4937, `bl1`, 2026, "1. Fußball-Bundesliga 2026/2027" from the stored snapshot) | < 100 KB |
| R2 | `GET /getresulttypes` | confirm result-type kinds (After90Minutes etc.) | < 10 KB |
| R3 | `GET /getmatchdata/bl1/2026` | the season: 306 matches (results, fixtures, UTC kickoff, ids, result types); **sent only if R1 confirmed the league** | ~0.3 MB |
| R4 | `GET /getcurrentgroup/bl1` | current matchday for the polling probe | < 2 KB |
| R5 | `GET /getlastchangedate/bl1/2026/{matchday-1}` | change-date probe, no match data | < 1 KB |
| R6 | `GET /getlastchangedate/bl1/2026/{matchday}` | change-date probe, no match data | < 1 KB |

**Request count: 6 planned; hard cap 12 HTTP attempts including retries** (at most 2 retries per request, exponential back-off, Retry-After honoured). Spacing >= 2 s + up to 1.5 s jitter → about 15–30 s in total, at most ~25 requests/min against the documented limit of 60/min/IP and the operator's "retrieve sparingly" request (one-off, outside match times). Any HTTP status other than 200/429/5xx, a different host, or an unconfirmed league aborts the run.

## User-Agent and contact
`FootIQ-ResultsAdapters-OpenLigaDBBot/1.0.0 (+local research project; <your FootIQ contact>)`. The contact is read from the environment variable `FOOTIQ_CONTACT` or the untracked file `config/contact.local` (listed in `config/.gitignore`); a `contact` key in `adapters.json` is ignored. It is never printed, never written to the request ledger, snapshot metadata, reports or exceptions (tests assert this; the rehearsal output was scanned). **No contact is configured yet, so the run is currently impossible** (verified: the command aborts before any request; no ledger file exists).

## What the run does with the answers
Stores each response as a write-once, read-only raw snapshot (sha256, retrieval time, plan sha, licence ODbL-1.0 and the attribution line); parses completed matches only with an explicit `After90Minutes` result; reconciles with openfootball (overlap, exact scores, conflicts, duplicates, ambiguous teams, missing fixtures, results newly recovered); checks that every completed match's kickoff precedes the retrieval timestamp; runs a **dry-run** eligibility check of the Bundesliga fixtures on an isolated copy of the universe. It does not update the official feature store, models, datasets, protocol or logger, creates no approval file, and sends no Wikipedia request.

## Dress rehearsal (local fake transport serving the stored 2026-10-21 snapshot; no network)
Sent-request sequence matched the plan (6 requests, R3 third). League confirmed 4937/bl1/2026; result-type kinds After90Minutes and HalfTime; 306 matches, 0 duplicate matchIDs or ordered pairs, 18 teams, 34 matchdays; 54 completed, all with kickoff before retrieval and explicit 90-minute type; 306/306 valid UTC kickoffs; 36/36 overlaps agree, 0 conflicts, **18 new verified results** (2026-09-2x..10-18, recovering all 18 missing), 0 team-mapping errors, 0 fixtures missing in either direction.

## Would Bundesliga fixtures become eligible for prospective logging?
Dry-run on the rehearsal data: **18 of 252 upcoming Bundesliga fixtures would be primary-eligible** (the two matchdays within the 14-day staleness window of the latest result, 2026-10-18); the other 234 fail only `stale_competition_results` and become eligible as later polls bring newer results. Nothing else blocks them (history, identity, unresolved past fixtures: all clear). This is an estimate from stored data; the live pilot would repeat it.
