# Fresh-result sources for the other four leagues: read-only investigation

Date: 2026-10-25. Scope you approved: documentation and **existing local evidence only**. **No new request was made** for these leagues; nothing was enabled; no provider other than the approved Bundesliga use of OpenLigaDB is active. Wikipedia and every other provider stay off as production sources.

Evidence used (all already in the repository): the OpenLigaDB league listing retrieved during the 2026-10-21 pilot (`pilot/run_20261021T141224Z/snapshots/openligadb/..._getavailableleagues_2026.json`, 81 entries), the verified OpenLigaDB licence and API terms summary (`source_adapters_r1/docs/01_SOURCE_PERMISSIONS.md`), the earlier source research (`fresh_results_source_research/`), the readiness table, and today's supervised Bundesliga run.

## 1. Coverage of the four leagues (what the local evidence shows)

| League | In the OpenLigaDB 2026 league listing? | Evidence | Verdict |
|---|---|---|---|
| **Premier League** | **Yes, twice**: `pl` "Premier League 2026/2027" (id 5996) and `pl1` "Permier League England" (id 5993, misspelt) | listing only | Exists, but two competing entries; which one is complete and canonical is **unknown** |
| **La Liga** | **Yes**: `la1` "LaLiga EA Sports 2026/2027" (id 4936) | listing only | Exists; completeness **unknown** |
| **Serie A** | **No entry** | listing has no Italian league | **Not available** from OpenLigaDB as of the 2026-10-21 listing |
| **Ligue 1** | **No entry** | listing has no French league | **Not available** from OpenLigaDB |

The same listing shows why entries cannot be trusted by name alone: it also contains user-created test leagues (`bl1test`, `blclaude`, `tst1`), a second Bundesliga entry (`bl12026`) and duplicate Champions League entries (`ucl` and `ucl2026`). OpenLigaDB is a community platform where registered users enter the data ("no editorial review, no warranty", terms of 2026-08-28), so a league existing does not mean it is maintained.

For comparison, the one league that **was** verified and is now live-tested:

| Bundesliga `bl1/2026` | Measured today (supervised run) |
|---|---|
| Fixtures | 306 of 306, 0 duplicates, 0 unresolved team names |
| Kickoff times | UTC for 306 of 306 |
| Result type | explicit `After90Minutes` field |
| Freshness | newest result 2026-10-24, fetched 2026-10-25 08:38 UTC (about 1 day) |
| Agreement with the baseline | 36 of 36 identical scores; 18 missing results recovered plus 7 newer ones |

## 2. What is not known for the Premier League and La Liga on OpenLigaDB (needs a request)

Result freshness, fixture completeness (380 expected each), kickoff availability, result-type labelling, which Premier League entry is real, whether matchday labels follow the real calendar, and how the team names map to our club ids. None of this can be answered from local files. These are the checks in the request plan below.

## 3. Other options, from existing research (not re-measured)

| Source | Status | Notes |
|---|---|---|
| **Wikipedia season pages** (CC BY-SA 4.0) | Premier League page validated offline earlier: 50 of 50 identical to the baseline, recovered 20 of 20 missing results. The other three leagues' pages were never validated. | Stays **confirmation-only**, not enabled. Dates are inherited from the schedule (no kickoff times); volunteer-edited; share-alike scope for derived data unresolved (your decision). Each additional league needs its own stored page and validation first. |
| **football-data.org** (free tier, "12 competitions") | Terms page unreadable earlier (404); needs an account and API key; free scores delayed per its pricing page. Which competitions the free tier covers is **not verified**. | Needs you to read the terms and create a key. The only candidate that might cover Serie A and Ligue 1 in one place. |
| **API-Football** | Terms unread (403); client exists; free quota 100 calls per day; no key. | Same condition. |
| football-data.co.uk, FBref, Sofascore/FotMob endpoints, official league sites | Prohibited or not permitted by default | Do not use. |

## 4. Licensing, rate limits, identity risks

* **OpenLigaDB licence** (verified earlier): data under ODbL 1.0, free including commercial use; attribution "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0" (already shown in the app); share-alike only if a modified database is publicly redistributed; club names, crests and logos are **not** covered (trademarks), so no icon URLs are used.
* **OpenLigaDB API terms:** no availability guarantee; descriptive User-Agent with contact required; use `getlastchangedate` and fetch full data only on change; at most about one request per 30-60 s per league during live matches, far fewer otherwise; 60 requests per minute per IP; the operator may throttle, block or require registration later (announced at least 4 weeks ahead). Our client keeps at least 3 s between requests and checks hourly.
* **Same terms apply to every league** on OpenLigaDB, so no new licence question arises for `pl` and `la1`; the open questions are data quality and maintenance.
* **Identity mapping risks:** OpenLigaDB team names can be German or English variants; promoted clubs (for example Coventry City in the 2026-27 Premier League) and clubs with long names need alias rows; two Premier League entries could use different spellings. The existing resolver never guesses: unresolved or ambiguous names go to quarantine. For Serie A and Ligue 1 the baseline already holds the club ids, but no source supplies results.
* **Trust risk:** because anyone can enter data, results from OpenLigaDB for a new league should be accepted only after a validation run against the baseline (as was done for the Bundesliga) and ideally a second source for conflicts.

## 5. Recommendation

1. **Premier League and La Liga:** run one small, read-only verification of OpenLigaDB (plan below). If the data are complete and consistent with the baseline, they can be added exactly as the Bundesliga was (one league at a time, supervised first run).
2. **Serie A and Ligue 1:** OpenLigaDB cannot help. They need a different approved source. The realistic candidate is football-data.org (free key), which requires you to read and accept its terms; Wikipedia could serve as confirmation only.
3. Until then these leagues stay marked stale, which the app already shows.

## 6. Request plan for your approval (nothing below has been run)

All to `https://api.openligadb.de`, GET only, unauthenticated, descriptive User-Agent with the configured contact, at least 3 s apart, snapshots saved with sha256, ledger kept, **total 5 requests, one time, no scheduling, no ingestion into the store** (analysis only, written to a separate report):

| # | Request | Why |
|---|---|---|
| 1 | `/getavailableleagues/2026` | refresh the 4-day-old listing, confirm `pl`, `pl1`, `la1` still exist and that no Serie A or Ligue 1 entry has appeared |
| 2 | `/getmatchdata/pl/2026` | Premier League 2026-27: fixture count (380?), completed results, kickoff UTC coverage, result types, team names |
| 3 | `/getmatchdata/pl1/2026` | decide whether the misspelt entry is a duplicate or a different competition |
| 4 | `/getmatchdata/la1/2026` | La Liga: same checks (380 fixtures?) |
| 5 | `/getresulttypes` | already known (5 types); skipped unless the payload shows a new kind |

Comparison done offline afterwards against the store: score and date agreement for the matches the baseline already holds (Premier League 50, La Liga 69), recovery of the 20 missing results in each league, team-name resolution report, kickoff availability, duplicates, last update timestamps (freshness). The output is a report; **no ingestion and no live enablement for these leagues without a separate approval**.

I will not run this plan until you approve it.
