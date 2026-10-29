# 08 Recommended source(s)

## Recommendation (subject to your approval and the licence questions in report 10)
1. **Keep openfootball (CC0) as the reference and schedule source.** Poll with the read-only `plan`; fetch only when a repository has a new revision.
2. **Add OpenLigaDB as the first new adapter** for the competitions it covers (Bundesliga 1/2, 3. Liga, German cup, UEFA competitions, and — to be verified — Premier League and LaLiga). Reasons: measured fresh (3 days), UTC timestamps, explicit 90-minute result type, 36/36 exact agreement with openfootball, structured JSON, intended for automated use. Condition: read its licence and terms pages and confirm ODbL attribution/share-alike obligations.
3. **Add Wikipedia season pages (results matrices) + openfootball schedule dates as the broad gap-filler for the 15 in-season leagues.** Reasons: measured fresh (0–7 days), covers every currently active competition at page level, Premier League check 50/50 identical and 20/20 missing results present, and Wikipedia is already an approved, documented source in this project (CC BY-SA 4.0, attribution recorded). Conditions: schedule-derived dates are flagged; two revisions >= 24 h apart before use; owner decision on the share-alike scope.
4. **Optional later:** football-data.org free tier (12 top competitions, UTC timestamps) as an independent confirmation source for top leagues, **only after you read its terms and choose to create a free key**; API-Football likewise. Not recommended: paid plans, TheSportsDB free, Sportmonks free, any scraper.
5. **Do not use:** football-data.co.uk (prohibited), FBref, official sites, undocumented endpoints.

## Why not a single source
No one source is both broad and structured: OpenLigaDB is narrow, Wikipedia is broad but date-less and volunteer-edited, openfootball is clean but stale. Two-source agreement is available for the Bundesliga (OpenLigaDB + Wikipedia + openfootball) and, for other leagues, Wikipedia + openfootball schedule with a revision-stability rule; the protocol's confirmation rule (report 07, B3) is written for exactly that.

## Expected result if approved
The 271 missing results in the 15 in-season competitions could be recovered immediately for the leagues whose pages pass tests A1-A6, restoring a primary-eligible share near the simulated ~98% for those leagues, and keeping the pipeline current thereafter without depending on openfootball's release cadence.
