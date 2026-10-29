# FootIQ Competition Coverage Matrix

**Document:** `COMPETITION_COVERAGE_MATRIX.md`  
**Milestone:** Milestone 2 (Dataset Verification and Scope Finalization)  
**Date:** 20 October 2026  
**Status:** Complete coverage matrix; verified across primary and fallback sources.  
**Machine-Readable Companion:** [`COMPETITION_COVERAGE_MATRIX.json`](COMPETITION_COVERAGE_MATRIX.json)

---

## 1. Coverage Philosophy and Verification Tiers

To prevent premature claims of "worldwide coverage", FootIQ classifies all football competitions into four distinct verification and support statuses:

1. **TIER 1 — VERIFIED IN PILOT (Core Production):** Full historical results (10+ seasons), match-level divisional statistics (shots, shots on target, corners), closing odds, and automated ingestion verified without cost or API quota exhaustion.
2. **TIER 2 — VERIFIED WITH CONSTRAINTS (Expanded Support):** High-quality historical and live match results available, but missing either detailed in-match statistics (e.g. domestic cups absent from Football-Data.co.uk) or constrained by API quotas (API-Football 100 calls/day).
3. **TIER 3 — HISTORICAL / EPISODIC (Specialized Analytics):** Rich event-level or tracking data available exclusively for specific archived seasons (e.g. StatsBomb Open Data tournament packages), but no continuous ongoing data.
4. **TIER 4 — DEFERRED / CONDITIONAL (Extensibility Goals):** Secondary leagues, global club tournaments, or youth competitions requiring paid feeds, custom scrapers (strictly avoided), or external vendor partnerships.

---

## 2. English Football Pilot & European Club Competitions

England serves as FootIQ's initial club engineering pilot. Every domestic tier, domestic cup, and connected European competition has been rigorously audited.

| Competition Name | Category / Level | Historical Seasons Available | In-Match Statistics | Player Statistics | Primary Provider | Fallback Provider | Update Cadence / Method | Verification Status |
|---|---|---|---|---|---|---|---|---|
| **Premier League** | Domestic League (Tier 1) | 1993/94 – present (33 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | Top Scorers (API/FB); Event (SB 03/04, 15/16 only) | Football-Data.co.uk | Football-Data.org / API-Football | Twice weekly batch CSV | **TIER 1 (Verified in Pilot)** |
| **EFL Championship** | Domestic League (Tier 2) | 1993/94 – present (33 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | None | Football-Data.co.uk | OpenFootball | Twice weekly batch CSV | **TIER 1 (Verified in Pilot)** |
| **EFL League One** | Domestic League (Tier 3) | 1993/94 – present (33 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | None | Football-Data.co.uk | OpenFootball | Twice weekly batch CSV | **TIER 1 (Verified in Pilot)** |
| **EFL League Two** | Domestic League (Tier 4) | 1993/94 – present (33 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | None | Football-Data.co.uk | OpenFootball | Twice weekly batch CSV | **TIER 1 (Verified in Pilot)** |
| **FA Cup** | Domestic Cup (Primary) | 2000 – present (Scores); 2015 – pres (API) | Score & Date only (OpenFootball); Full (API-Football) | Lineups & Match stats (API-Football) | OpenFootball (Hist) / API-Football (Live) | RSSSF archives | Post-round API poll / Git pull | **TIER 2 (Verified with Constraints)** |
| **EFL Cup (Carabao Cup)** | Domestic League Cup | 2005 – present (Scores); 2016 – pres (API) | Score & Date only (OpenFootball); Full (API-Football) | Lineups & Match stats (API-Football) | OpenFootball (Hist) / API-Football (Live) | FlashScore / RSSSF | Post-round API poll | **TIER 2 (Verified with Constraints)** |
| **FA Community Shield** | Super Cup | 1990 – present (Annual single match) | Score, penalties (API-Football / OpenFootball) | Lineups & basic stats (API-Football) | API-Football | OpenFootball | Annual single match ingestion | **TIER 2 (Verified with Constraints)** |
| **UEFA Champions League** | Continental Club (Elite) | 1999 – pres (Results/API); Select (SB events) | Full (API-Football); Scores/Standings (FD.org) | Event-level (SB 18 seasons); Match stats (API) | Football-Data.org (Scores) / API-Football | OpenFootball | Post-matchday API poll | **TIER 2 (Verified with Constraints)** |
| **UEFA Europa League** | Continental Club (Tier 2)| 2009 – present (API / OpenFootball) | Full (API-Football); Scores/Standings (OpenFootball) | Match stats (API-Football) | OpenFootball (Hist) / API-Football (Live) | Football-Data.org | Post-matchday API poll | **TIER 2 (Verified with Constraints)** |
| **UEFA Conference League**| Continental Club (Tier 3)| 2021/22 – present (Inaugural to pres) | Full (API-Football); Scores/Standings (OpenFootball) | Match stats (API-Football) | OpenFootball (Hist) / API-Football (Live) | UEFA official records | Post-matchday API poll | **TIER 2 (Verified with Constraints)** |
| **UEFA Super Cup** | Continental Super Cup | 1998 – present (Annual single match) | Score, ET/PSO, match stats (API-Football) | Match stats (API-Football) | API-Football | OpenFootball | Annual single match ingestion | **TIER 2 (Verified with Constraints)** |

*Audit note on English Cups:* Because Football-Data.co.uk excludes the FA Cup and EFL Cup, the English club predictor pipeline must train its primary league dynamics on Football-Data.co.uk and incorporate cup fixtures via the secondary normalized cup schema (using OpenFootball for backfills and budget-capped API-Football calls for current-season rounds).

---

## 3. Major European Leagues Expansion (Big Four: Spain, Germany, Italy, France)

Following the English pilot, FootIQ expands to the remaining four major European football leagues and their respective cup structures.

| Country | Competition Name | Level | Historical Seasons | In-Match Statistics | Player Statistics | Primary Source | Secondary Source | Verification Status |
|---|---|---|---|---|---|---|---|---|
| **Spain** | **La Liga (Primera División)** | League (D1) | 1993/94 – pres (33 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | Event-level (StatsBomb 2004–2021); Season (API) | Football-Data.co.uk | StatsBomb / API-Football | **TIER 1 (Verified)** |
| **Spain** | **Segunda División** | League (D2) | 1996/97 – pres (30 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | None | Football-Data.co.uk | OpenFootball | **TIER 1 (Verified)** |
| **Spain** | **Copa del Rey** | Domestic Cup | 2000 – pres (Results); 2016 – pres (API) | Scores (OpenFootball); Full (API-Football) | Match stats (API); Select finals (SB 77/78, 82/83, 83/84) | OpenFootball / API-Football | RSSSF | **TIER 2 (Verified with Constraints)** |
| **Spain** | **Supercopa de España** | Super Cup | 2010 – pres (Final Four format) | Full match stats (API-Football) | Match stats (API-Football) | API-Football | OpenFootball | **TIER 2 (Verified with Constraints)** |
| **Germany** | **1. Bundesliga** | League (D1) | 1993/94 – pres (33 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | Event-level (SB 15/16, 23/24); Season (API) | Football-Data.co.uk | StatsBomb / Football-Data.org | **TIER 1 (Verified)** |
| **Germany** | **2. Bundesliga** | League (D2) | 1993/94 – pres (33 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | None | Football-Data.co.uk | OpenFootball | **TIER 1 (Verified)** |
| **Germany** | **DFB-Pokal** | Domestic Cup | 2002 – pres (Results); 2015 – pres (API) | Scores (OpenFootball); Full (API-Football) | Match stats (API-Football) | OpenFootball / API-Football | DFB official | **TIER 2 (Verified with Constraints)** |
| **Germany** | **DFL-Supercup** | Super Cup | 2010 – pres (Annual match) | Full match stats (API-Football) | Match stats (API-Football) | API-Football | OpenFootball | **TIER 2 (Verified with Constraints)** |
| **Italy** | **Serie A** | League (D1) | 1993/94 – pres (33 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | Event-level (SB 86/87, 15/16); Season (API) | Football-Data.co.uk | Football-Data.org / API-Football | **TIER 1 (Verified)** |
| **Italy** | **Serie B** | League (D2) | 1996/97 – pres (30 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | None | Football-Data.co.uk | OpenFootball | **TIER 1 (Verified)** |
| **Italy** | **Coppa Italia** | Domestic Cup | 2005 – pres (Results); 2016 – pres (API) | Scores (OpenFootball); Full (API-Football) | Match stats (API-Football) | OpenFootball / API-Football | Lega Serie A | **TIER 2 (Verified with Constraints)** |
| **Italy** | **Supercoppa Italiana** | Super Cup | 2010 – pres (Single / Final Four) | Full match stats (API-Football) | Match stats (API-Football) | API-Football | OpenFootball | **TIER 2 (Verified with Constraints)** |
| **France** | **Ligue 1** | League (D1) | 1993/94 – pres (33 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | Event-level (SB 15/16, 21/22, 22/23); Season (API) | Football-Data.co.uk | Football-Data.org / API-Football | **TIER 1 (Verified)** |
| **France** | **Ligue 2** | League (D2) | 1996/97 – pres (30 seasons) | Full (Shots, SOT, Corners, Fouls, Cards, Odds) | None | Football-Data.co.uk | OpenFootball | **TIER 1 (Verified)** |
| **France** | **Coupe de France** | Domestic Cup | 2005 – pres (Results); 2016 – pres (API) | Scores (OpenFootball); Full (API-Football) | Match stats (API-Football) | OpenFootball / API-Football | FFF official | **TIER 2 (Verified with Constraints)** |
| **France** | **Trophée des Champions** | Super Cup | 2010 – pres (Annual match) | Full match stats (API-Football) | Match stats (API-Football) | API-Football | OpenFootball | **TIER 2 (Verified with Constraints)** |

---

## 4. Secondary European Leagues, Americas & Global Club Competitions

| Competition Name | Region / Level | Historical Coverage | In-Match Statistics | Primary Provider | Verification Status | Notes / Limitations |
|---|---|---|---|---|---|---|
| **Eredivisie (Netherlands)** | Europe (D1) | 2000 – pres (26 seasons) | Full match stats & odds | Football-Data.co.uk | **TIER 1 (Verified)** | Continuous CSV coverage. |
| **Primeira Liga (Portugal)** | Europe (D1) | 2000 – pres (26 seasons) | Full match stats & odds | Football-Data.co.uk | **TIER 1 (Verified)** | Continuous CSV coverage. |
| **Scottish Premiership** | Europe (D1) | 1994/95 – pres (32 seasons) | Full match stats & odds | Football-Data.co.uk | **TIER 1 (Verified)** | Full coverage including SP1 to SP3. |
| **Brasileirão Série A** | South America (D1) | 2012 – pres (Football-Data.co.uk/API) | Scores, odds, match stats | Football-Data.co.uk / API-Football | **TIER 2 (Verified with Constraints)** | South America match data in CSV format. |
| **Liga Profesional (Argentina)** | South America (D1) | 2012 – pres (FD.co.uk); SB (1981, 97/98) | Scores, odds, match stats | Football-Data.co.uk / API-Football | **TIER 2 (Verified with Constraints)** | Format changes (Apertura/Clausura vs League). |
| **Major League Soccer (USA)** | North America (D1) | 2012 – pres (FD.co.uk); SB (2023) | Scores, odds, match stats | Football-Data.co.uk / StatsBomb | **TIER 2 (Verified with Constraints)** | Conference & Playoff structure. |
| **CONMEBOL Copa Libertadores** | Continental Club | 2015 – pres (API-Football / OpenFootball)| Scores, lineups, match stats | API-Football | **TIER 2 (Verified with Constraints)** | Quota intensive during group stages. |
| **CONMEBOL Copa Sudamericana**| Continental Club | 2016 – pres (API-Football) | Scores, match stats | API-Football | **TIER 2 (Verified with Constraints)** | Secondary South American club cup. |
| **AFC Champions League** | Asia (Continental Club) | 2017 – pres (API-Football) | Scores, match stats | API-Football | **TIER 2 (Verified with Constraints)** | Split East/West zones until final. |
| **CONCACAF Champions Cup** | North/Central America | 2018 – pres (API-Football) | Scores, match stats | API-Football | **TIER 2 (Verified with Constraints)** | Knockout tournament format. |
| **FIFA Club World Cup (Annual)** | Global Club | 2000, 2005 – 2023 (Annual 7-team) | Scores, full match stats | API-Football / Wikipedia / RSSSF | **TIER 2 (Verified with Constraints)** | Historical tournament concluded in 2023. |
| **FIFA Club World Cup 2025+** | Global Club (Expanded 32-team)| 2025 – future | Real-time live & match stats | API-Football / Official FIFA | **TIER 4 (Deferred / Scheduled)** | Inaugural 32-team tournament format. |
| **FIFA Intercontinental Cup** | Global Club (Annual 6-team) | 2024 – future | Real-time live & match stats | API-Football / Official FIFA | **TIER 4 (Deferred / Scheduled)** | Annual confederation champions cup. |

---

## 5. International Football (National Teams)

International football is the core operational domain inherited from FootIQ's verified baseline.

| Competition Name | Federation | Historical Span | Match Detail | Player Detail | Primary Source | Secondary Source | Verification Status |
|---|---|---|---|---|---|---|---|
| **FIFA World Cup (Finals)** | FIFA (Global) | 1930 – 2022 (All 22 tournaments); 2026 sched | Score, ET/PSO, venue, city | Scorers (Jansen); Full Events (SB 2018, 2022, 1958-1990) | Mart Jansen / StatsBomb | OpenFootball (2026 schedule) | **TIER 1 (Verified Baseline)** |
| **FIFA World Cup Qualifiers** | FIFA / All Confederations | 1934 – 2026 (8,771 verified matches) | Score, date, neutral flag | Goalscorers only | Mart Jansen | API-Football | **TIER 1 (Verified Baseline)** |
| **UEFA European Championship (Euro)** | UEFA (Europe) | 1960 – 2024 (388 verified matches) | Score, ET/PSO, venue | Scorers (Jansen); Full Events (SB 2020, 2024) | Mart Jansen / StatsBomb | Football-Data.org / API | **TIER 1 (Verified Baseline)** |
| **UEFA Euro Qualifiers** | UEFA (Europe) | 1960 – 2024 (2,824 verified matches) | Score, date, venue | Goalscorers only | Mart Jansen | API-Football | **TIER 1 (Verified Baseline)** |
| **UEFA Nations League (UNL)** | UEFA (Europe) | 2018 – 2026 (658 verified matches) | Score, date, venue | Goalscorers only | Mart Jansen | API-Football | **TIER 1 (Verified Baseline)** |
| **Copa América** | CONMEBOL (South America) | 1916 – 2024 (869 verified matches) | Score, ET/PSO, venue | Scorers (Jansen); Full Events (SB 2024) | Mart Jansen / StatsBomb | API-Football | **TIER 1 (Verified Baseline)** |
| **Africa Cup of Nations (AFCON)** | CAF (Africa) | 1957 – 2024 (845 finals matches; 2,327 qual) | Score, ET/PSO, venue | Scorers (Jansen); Full Events (SB 2023) | Mart Jansen / StatsBomb | API-Football | **TIER 1 (Verified Baseline)** |
| **AFC Asian Cup** | AFC (Asia) | 1956 – 2024 (421 finals matches; 829 qual) | Score, ET/PSO, venue | Goalscorers only | Mart Jansen | API-Football | **TIER 1 (Verified Baseline)** |
| **CONCACAF Gold Cup & Nations League**| CONCACAF (North/Central) | 1963 – 2025 (420 Gold Cup; 422 Nations League)| Score, ET/PSO, venue | Goalscorers only | Mart Jansen | API-Football | **TIER 1 (Verified Baseline)** |
| **International Friendlies** | Global | 1872 – 2026 (18,291 verified matches) | Score, date, venue, neutral | Goalscorers only | Mart Jansen | None required | **TIER 1 (Verified Baseline)** |

---

## 6. Synthesis: Recommended Competition Scope for Implementation

Based on our empirical audit, FootIQ will implement its multi-competition data warehouse and ML platform across four clear developmental waves:

```
+-----------------------------------------------------------------------------------------+
| WAVE 1: VERIFIED CORE FOUNDATION                                                        |
| - International Men's Matches (49,296 scored matches; Mart Jansen dataset)              |
| - English Pilot: Premier League, Championship, League One, League Two (Football-Data)   |
| - English Pilot Cups: FA Cup, EFL Cup, Community Shield (OpenFootball + API-Football)   |
| - World Cup 2026 Tournament Simulator (104 fixtures; OpenFootball)                      |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| WAVE 2: EUROPEAN BIG FOUR EXPANSION                                                     |
| - Spain (La Liga, Segunda, Copa del Rey)                                                |
| - Germany (1. Bundesliga, 2. Bundesliga, DFB-Pokal)                                     |
| - Italy (Serie A, Serie B, Coppa Italia)                                                |
| - France (Ligue 1, Ligue 2, Coupe de France)                                            |
| - Primary Provider: Football-Data.co.uk (leagues); OpenFootball/API-Football (cups)     |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| WAVE 3: EUROPEAN CONTINENTAL CLUB COMPETITIONS                                          |
| - UEFA Champions League, UEFA Europa League, UEFA Conference League, UEFA Super Cup     |
| - Primary Provider: Football-Data.org (standings/results); API-Football (match stats)   |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| WAVE 4: GLOBAL EXTENSION & TOURNAMENT SPECIALS                                          |
| - Secondary Leagues (Eredivisie, Primeira Liga, Scottish Premiership, MLS, Brasileirao) |
| - Copa Libertadores, AFC Champions League, FIFA Club World Cup                          |
| - StatsBomb Curated Cohorts (Messi career, World Cup 2018/2022, Euros, AFCON)           |
+-----------------------------------------------------------------------------------------+
```
