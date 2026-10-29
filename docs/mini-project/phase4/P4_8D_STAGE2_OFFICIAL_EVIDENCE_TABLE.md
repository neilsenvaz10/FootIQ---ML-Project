# Evidence research on the quarantined conflicts (Phase 4.8D Stage 2, read-only)

Researched 2026-10-27 with public web search and page reads only (no scraping at scale, no restricted services, no account). **Nothing was changed in production and no quarantined item was resolved.** The recommendations below are suggestions for a person to confirm.

## How far the research could go (honest limits)

| Source type | Result |
|---|---|
| Premier League official site (`premierleague.com/en/matches…`) | opened, but the page is a script shell: navigation only, no scores or fixtures (so no official Premier League evidence could be read) |
| BBC Sport | not fetchable from this environment |
| 11v11 match pages | HTTP 403; their content was seen **only as search-engine summaries**, not read by me on the page |
| LaLiga official site / club sites | appeared in search results (one LaLiga statement is quoted by news outlets); I could not read an official LaLiga fixtures page |
| News and aggregator pages (El Gol Digital, Diario de León, Primicias, ToffeeWeb, RTVC, Vavel, SoccerNews, football-listing sites) | readable or summarised; all are **third-party**, not the competition body |

So every finding below is **third-party evidence, not official**; confidence is rated accordingly (High needs the competition body's own record; none was reachable).

## A. Score conflicts

| Item | Stored | Provider claim | What third-party sources say | Confidence | Suggested action (not applied) |
|---|---|---|---|---|---|
| AFC Bournemouth v Brentford, 2026-09-12 (PL matchweek 4) | 2–2 (openfootball) | OpenLigaDB 2–1, half-time 0–0 | Search summaries of [11v11](https://www.11v11.com/matches/afc-bournemouth-v-brentford-12-september-2026-394429/), [SoccerNews](https://www.soccernews.com/matches/afc-bournemouth-vs-brentford-fc-premier-league-2026-27-560576/) and [Vavel](https://www.vavel.com/en/data/afc-bournemouth/results/) agree on **2–2**, half-time 1–1, scorers Kluivert 38', Tavernier 52' (Bournemouth), Schade 34', 56' (Brentford) | **Medium**: three independent third-party pages agree with the stored score; none is official | Keep 2–2; the OpenLigaDB 2–1 looks wrong. Close only after a person reads the Premier League match page |
| Aston Villa v Nottingham Forest, 2026-09-12 | 1–2 (openfootball) | OpenLigaDB record holds several different final scores | Summaries of [11v11](https://www.11v11.com/matches/aston-villa-v-nottingham-forest-12-september-2026-394430/) and [futboltotal](https://futboltotal.futbol/partido/aston-villa-vs-nottingham-forest-premier-league-2026-09-12) say **Forest won 2–1 away** (Delap 46', Alysson 74' for Villa, Igor Jesus 88'); some listing pages still show 0–0 from before kickoff | **Medium**: the stored 1–2 (home 1, away 2) is the same result | Keep 1–2 and the quarantine (the provider record is corrupt, nothing to import); confirm on the Premier League match page |

## B. The Rayo Vallecano v Athletic Club anomaly (matchday 8)

| Fact | Evidence | Confidence |
|---|---|---|
| The match of **2026-10-10 was suspended** by the referee in the 25th minute after paper planes and rubber balls were thrown from the stands | [El Gol Digital](https://www.elgoldigital.com/futbol/rayo-vallecano/rayo-vallecano-athletic-suspendido-protesta-martin-presa-jornada-8/) (read), [La Tribuna](https://www.latribuna.hn/2026/10/10/suspende-juego-rayo-athletic/), [Diario de León](https://www.diariodeleon.es/deportes/261010/2099883/han-suspendido-partido-rayo-vallecano-athletic-club-bilbao.html), [Primicias](https://www.primicias.ec/deportes/futbol/suspende-partido-rayo-vallecano-athletic-protestas-hinchas-aviones-papel-cancha-134617/) and others agree; one source gives 0–0 at the stop, El Gol Digital gives no score | **High** that it was suspended (many independent outlets); score at the stop: low |
| LaLiga said the new date and time would be announced | quoted by the search summaries of several outlets; **no new date found** | Medium |
| OpenLigaDB's **2027-05-30** | no source supports it | **Unverified: do not use** |

Consequences (not applied): the stored row (date 2026-10-10, "awaiting result") is not a postponement but a **suspended, unfinished match**; it must not receive a result or a new date until LaLiga announces how it is completed. Under the new eligibility rule it is not predictable (its stored date is past; the provider's date is a dispute).

## C. Fixture-date disagreements checked (3 of 55)

| Fixture | Stored date | Provider date | Third-party evidence | Confidence | Pointing to |
|---|---|---|---|---|---|
| Everton v Coventry City (PL matchweek 10) | 2026-11-07 (date only) | 2026-11-06 20:00 UTC | [ToffeeWeb](https://www.toffeeweb.com/season/26-27/news/three-everton-fixtures-in-november-moved-for-live-tv-broadcast/) (21 Sep 2026): moved for live TV to **Friday 6 Nov, 20:00 GMT**; Onside lists Fri 6 Nov 20:00; older listings still say Sat 7 Nov 15:00 | Medium (club-fan site quoting the broadcast move; no official page read) | the **provider** |
| Atlético de Madrid v Deportivo La Coruña (matchday 10) | 2026-10-25 | 2026-10-24 | [RTVC](https://rtvc.es/atletico-de-madrid-vs-deportivo-la-coruna-j10-laliga-ea-sports-26-27/): Saturday **24 October**, 20:00 (Canary time); the result was not found | Medium | the **provider** (date); the 1–0 result stays held until a person confirms |
| Valencia v Villarreal (matchday 10) | 2026-10-25 | 2026-10-24 | listing pages disagree (one lists 24 Oct, another 25 Oct, one 18:30 Spanish time); no final score found | Low | **unresolved** |

The other **52** disagreements were not researched: no official page was reachable and a search per fixture would be scraping at scale. They stay quarantined with the evidence requirements of `P4_8D_CONFLICT_EVIDENCE_TABLE.md`.

## D. What this means

* The two score conflicts lean toward the **stored** values; the date disagreements checked lean toward the **provider's** dates. Neither direction is applied: a person must confirm each with the official body (Premier League and LaLiga fixture lists or match pages).
* Confidence summary: Bournemouth–Brentford medium, Villa–Forest medium, Rayo–Athletic suspension high, Rayo–Athletic new date unverified, Everton–Coventry medium, Atlético–Deportivo medium, Valencia–Villarreal low.
