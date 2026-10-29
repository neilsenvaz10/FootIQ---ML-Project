# 01 Fresh-results source research report (2026-10-21)

Research and planning only. No provider was implemented, no account created, nothing purchased, no large download (the evidence below is three small API queries: one Wikipedia revision-timestamp query for 17 pages, one Wikipedia page, one OpenLigaDB league-season of 308 KB), no model/dataset/database change, no Git action, official logging not activated, nothing retrained. Files: `evidence/`.

**Verified facts are marked VERIFIED (read or measured today or in an earlier phase with a file in the project); anything I could not read is UNKNOWN and is treated as not permitted.**

## Where we stand
The approved source (openfootball, CC0) has no revision newer than the training snapshot; its 15 in-season competitions lack 271 results dated 2026-10-02..20. The question is whether another source can fill that gap legally and reliably.

## What was found
1. **Two permitted-looking sources are fresh and agree exactly with openfootball where they overlap.**
   * **Wikipedia season pages (CC BY-SA 4.0, MediaWiki API).** VERIFIED today: all 15 in-season league pages exist, last edited 2026-10-14..21. For the Premier League the results matrix holds 70 scored cells = the 50 results openfootball has (all 50 identical) + all 20 results openfootball is missing. Limits: the matrix carries scores but no dates or kickoff times (dates would be taken from openfootball's published schedule, flagged as schedule-derived); volunteer-edited; share-alike licence.
   * **OpenLigaDB (ODbL per site statement).** VERIFIED today: Bundesliga 2026 has 54 finished matches, latest 2026-10-18T15:30Z, UTC timestamps, explicit "After90Minutes" result type, per-match last-update stamps; the 36 matches openfootball has agree 36/36 on score and date; the 18 openfootball is missing are all present. Limits: only a handful of competitions (Bundesliga 1/2, 3. Liga, German cup, UEFA competitions, Premier League and LaLiga listed on its front page, not queried); its licence/terms pages could not be read.
2. **Not usable:** football-data.co.uk (VERIFIED prohibited: "NOT commercial or data training products using automated bots/scrapers/AI", private individuals only); FBref/Sports-Reference, official league sites, ESPN/Sofascore/FotMob endpoints (no verifiable permission → not permitted by default).
3. **Cannot be assessed without owner action:** football-data.org (free tier 12 competitions, 10 calls/min, delayed scores — VERIFIED from the pricing page; terms page 404, policy page silent on use/caching/ML → UNKNOWN; needs a free API key, I did not create an account) and API-Football (terms page 403; free 100 requests/day per third-party pages; existing unused client in `scripts/api_football_client_v24.py`, no key present).
4. **Free-tier APIs that do not fit:** TheSportsDB free key returns 1 past/next event per league and 15 per season query (official docs) — unusable; Sportmonks free plan = Danish Superliga and Scottish Premiership only.

## Conclusion
A two-source arrangement is feasible and legal on the evidence read so far: **OpenLigaDB** (structured, UTC, narrow) and **Wikipedia matrices + openfootball schedule** (broad for top leagues, share-alike licence), with openfootball remaining the CC0 reference whenever it updates. Both would need an owner decision on licence scope first (blockers 1-2 in report 10). Coverage of competitions outside the 15 in-season leagues is UNKNOWN. Details: reports 02-10.

## Process notes (disclosure)
* My three first Wikipedia queries used a User-Agent that included "curl" and no "bot"; the Wikimedia User-Agent policy asks for a descriptive string with contact details and "bot", and says generic strings like curl may be blocked. They were not blocked, and later requests used a compliant string; a proper client must follow the policy.
* Page fetches of football-data.org terms, API-Football terms and Sports-Reference policy failed (404/403/403); I did not try to work around that.
