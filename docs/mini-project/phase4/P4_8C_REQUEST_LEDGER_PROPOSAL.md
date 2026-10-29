# Phase 4.8C: proposed external request ledger (for your approval; nothing has been sent)

Status 2026-10-27: **zero external requests have been made in Phase 4.8C.** This is the complete list I propose. Approve all, part, or none.

## A. OpenLigaDB (`api.openligadb.de`), GET only, no retries

Common safeguards (already built and tested): HTTPS only; host allow-list; each URL must equal one of the lines below or the request is refused; hard cap equal to the number approved; at least 3 s (plus up to 1.5 s random jitter) between requests; the adapter's contact string and user agent (value never printed; `contact_configured` verified true in `--plan`); a request-ledger line per call; the raw response saved unchanged as an immutable snapshot with its SHA-256 under `data/snapshots/p48c/` (licence ODbL 1.0, attribution recorded); `config/sync.json` stays `live_enabled: false` (the script enables the adapter in its own process only); production is **copied by file copy and never opened for writing**; the comparison runs on that private copy; nothing is imported.

| # | Stage | Exact URL | Purpose | Expected response |
|---|---|---|---|---|
| A1 | 1 (Bundesliga, approved source) | `https://api.openligadb.de/getmatchdata/bl1/2026` | One request for the whole 2026-27 season, to compare with production (223,510-row store) and with the snapshot of 2026-10-25 08:38 UTC | HTTP 200, JSON array of 306 matches (`matchID`, `matchDateTimeUTC`, `group`, `team1`/`team2`, `matchResults[]`, `matchIsFinished`, `lastUpdateDateTime`), about 315 kB; results up to the newest finished matchday |
| A2 | 2 (Premier League, needs your separate OK) | `https://api.openligadb.de/getmatchdata/pl/2026` | Same, to verify the existing endpoint still serves the data imported on 2026-10-25 and see what the provider changed since | HTTP 200, 380 matches, about 940 kB |
| A3 | 2 (La Liga, needs your separate OK) | `https://api.openligadb.de/getmatchdata/la1/2026` | Same | HTTP 200, 380 matches, about 450 kB |

**Request count: 1 for stage 1, 2 more for stage 2, 3 in total.** Stage 1 stops after A1 and I report before anything else is sent. No other endpoint (no current-group, last-change-date, league listing) is requested.

What I will do with the responses: compare them with the previous snapshots (what the provider changed), then replay them onto a *private copy* of production exactly as the importer would, with and without date protection, and report inserted/updated/unchanged/confirmed/quarantined counts and every field that would change. The two score conflicts and the 55 date disagreements are expected to stay quarantined; if the provider has corrected a score, that is reported as a *finding*, not applied. Nothing reaches production.

**Dry-run already rehearsed offline** with the 2026-10-25 snapshots standing in (`data/supervised/phase4/p48c/verify_standin_rehearsal.json`): with date protection the replay changes nothing (0 inserted, 0 updated, no new quarantine); **without** it the same replay would silently change 55 stored dates and 5 La Liga results. Because of that I made the live sync path use date protection (a differing date is held for a human), with a test.

## B. football-data.org: public documentation and terms pages only (HTML, GET, no login)

No account, no key, **no call to `api.football-data.org`**, no match-data endpoint. Read through the web-page reader, one GET per page, no crawling beyond these.

| # | URL | Purpose |
|---|---|---|
| B1 | `https://www.football-data.org/about` | terms and conditions (storage, redistribution, attribution, fair use) |
| B2 | `https://www.football-data.org/pricing` | plans, free-tier limits, update/delay statements |
| B3 | `https://www.football-data.org/coverage` | competitions and seasons covered (Serie A, Ligue 1) |
| B4 | `https://www.football-data.org/documentation/api` | API reference: limits, status values, headers |
| B5 | `https://docs.football-data.org/general/v4/` | v4 overview and the index of its sub-pages |
| B6–B9 | at most four sub-pages linked from B5: policies (rate limits, caching), lookup tables, match, overtime | request limits; cache/storage rules; score fields |

**Request count: at most 9 page reads.** I will compare the text with the repository's offline review of 2026-10-26 and report what changed, what is ambiguous and what the terms permit for a scheduled, cached, attributed read of two leagues. I will not approve or activate the provider.

## C. Not requested

Any other OpenLigaDB endpoint; any league other than Bundesliga, Premier League, La Liga; any Serie A / Ligue 1 data endpoint; any scheduled or repeated call; any call from the running application.
