# FootIQ Source Evaluation — Football Data Providers & Feasibility Audit

**Document:** `SOURCE_EVALUATION.md`  
**Milestone:** Milestone 2 (Dataset Verification and Scope Finalization)  
**Date:** 20 October 2026  
**Status:** Complete provider evaluation; verified empirical findings and terms of service analysis.  
**Scope:** International football, domestic club leagues, domestic cups, continental competitions, global tournaments, and player analytics.

---

## 1. Executive Summary of Provider Landscape

FootIQ requires a multi-tier data architecture to support international match prediction, club match prediction, tournament simulation, and player analytics. A central objective of Milestone 2 is to avoid assuming that a provider supports a competition or analytics domain simply because it advertises football coverage.

Our empirical audit and terms-of-service verification reveal four foundational structural realities:

1. **No single provider satisfies all requirements for free:** Commercial APIs with broad coverage (e.g., API-Football) enforce restrictive free-tier daily call quotas (100 requests/day) and rate limits that make raw event ingestion and broad historical backfills infeasible without paid plans.
2. **StatsBomb Open Data is episodic and research-curated, NOT an ongoing league feed:** While offering world-class event-level spatiotemporal tracking data, StatsBomb Open Data is limited to 24 discrete competitions and 80 competition-season packages. Critically, for the English Premier League, it covers only two historical seasons (2003/2004 Arsenal "Invincibles" and 2015/2016 Leicester City title); it has **no ongoing or recent Premier League event data**.
3. **Football-Data.co.uk is the gold standard for historical club match results and betting odds, but lacks player data and cup competitions:** It provides comprehensive match-level results, divisional statistics (shots, shots on target, corners, fouls, cards), and multi-bookmaker odds for top European leagues back to 1993/94 in simple CSV format. However, it covers zero domestic cups (no FA Cup, EFL Cup, Copa del Rey) and zero player-level statistics.
4. **Scraping platforms (FBref / Transfermarkt / Understat) present acute legal and technical liabilities:** Direct scraping violates site Terms of Service, actively triggers Cloudflare bot mitigations, and violates platform anti-scraping policies. FootIQ must rely on legitimate open datasets, structured data dumps, or API interfaces with clear licensing.

---

## 2. In-Depth Provider Evaluations

### 2.1 Existing International Results Source (Mart Jansen / Kaggle / GitHub)

- **Official Source URL:** `https://github.com/martj42/international_results` / `https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017`
- **Data Categories:** Match results, goalscorers, penalty shootouts.
- **Available Competitions and Seasons:** Men's official and friendly international matches from November 30, 1872 to present.
- **Match-Level Statistics:** Match date, home team, away team, home score, away score, tournament, city, country, neutral venue flag.
- **Player-Level Statistics:** Basic goalscorer records (`scorer`, `minute`, `own_goal`, `penalty`). No lineups, minutes played, touches, passes, or defensive actions.
- **Fixture and Result Updates:** Semi-regular git repository commits and Kaggle dataset refreshes (typically monthly or post-international windows).
- **API Authentication:** None; direct raw CSV access via GitHub raw or Kaggle API.
- **Rate Limits and Quotas:** GitHub raw bandwidth limits (virtually unlimited for periodic batch pulls).
- **Free vs. Paid Access:** 100% Free / Public.
- **Data Licensing and ML Training Permissions:** Released under CC0: Public Domain. Unrestricted ML training, commercial use, and academic publication permitted.
- **Historical Availability:** 1872-11-30 to present (49,368 rows audited in local repository).
- **Reliability and Known Gaps:**
  - *Score Semantics Gap (Risk R04):* Historical scores do not differentiate between 90-minute regulation scores and 120-minute extra-time scores. For knockout matches that went to extra time, the recorded score is the final score after 120 minutes, not 90 minutes.
  - *Unscored Fixtures:* Contains 72 future or unscored rows (stored with string `'NA'` in score fields).
  - *No Live Match State:* Unsuitable for live in-play predictions; strictly a historical results archive.

---

### 2.2 StatsBomb Open Data

- **Official Source URL:** `https://github.com/statsbomb/open-data`
- **Data Categories:** Match metadata, confirmed lineups, comprehensive event-level spatiotemporal data (x, y coordinates, event timestamps, freeze frames, shot clarity, pressure events), and 360 data (for select tournaments).
- **Available Competitions and Seasons:** Exactly 24 competitions across 80 competition-season pairs (audited from `competitions.json`). Notable holdings:
  - *FIFA World Cup:* 1958, 1962, 1970, 1974, 1986, 1990, 2018 (complete tournament, 64 matches), 2022 (complete tournament, 64 matches).
  - *UEFA Euro:* 2020, 2024.
  - *Copa América:* 2024.
  - *African Cup of Nations:* 2023.
  - *Premier League (England):* Only 2 seasons (2003/2004, 2015/2016).
  - *La Liga (Spain):* 2004/2005 through 2020/2021 (Lionel Messi complete career package). No post-2021 seasons.
  - *1. Bundesliga (Germany):* 2015/2016 and 2023/2024 (Bayer Leverkusen unbeaten season).
  - *Serie A (Italy):* 1986/1987 (Maradona) and 2015/2016.
  - *Ligue 1 (France):* 2015/2016, 2021/2022, 2022/2023 (Messi PSG tenure).
  - *Champions League:* 18 distinct seasons, primarily historical finals (1970s) or select knockout/Messi matches from 1999 to 2019.
  - *Women's Football:* FA WSL (4 seasons), NWSL (2 seasons), Women's World Cup (2019, 2023), UEFA Women's Euro (2022, 2025), Liga F (2023/2024), Serie A Women (2023/2024).
- **Match-Level Statistics:** In-depth xG, shot maps, passes, duels, pressure, goalkeeper metrics, possession value.
- **Player-Level Statistics:** Complete player event stream: touches, pass types/lengths, carries, pressures, tackles, aerial duels, shots, defensive blocks, positioning coordinates.
- **Fixture and Result Updates:** Static historical batches published periodically on GitHub. **No live or regular weekly updates**.
- **API Authentication:** None for Open Data repo; Python package `statsbombpy` wraps GitHub raw JSON endpoints.
- **Rate Limits and Quotas:** Subject only to standard GitHub raw rate limits.
- **Free vs. Paid Access:** Open Data is free. Full live commercial feeds require high-tier enterprise contracts.
- **Data Licensing and ML Training Permissions:**
  - *License:* StatsBomb Open Data is released under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)** license.
  - *Commercial Restriction:* Cannot be used for commercial products without a commercial license from StatsBomb.
  - *Attribution Requirement:* Must prominently display: *"This data was provided by StatsBomb"* and link to `https://statsbomb.com`.
  - *Academic / Research Use:* Strictly permitted for educational, academic, and non-commercial research projects (perfectly aligned with FootIQ academic requirements).
- **Historical Availability:** Highly discontinuous; excellent depth for specific curated tournaments, but zero continuity for ongoing league monitoring.
- **Reliability and Known Gaps:**
  - In local repository baseline, only 128 match files and 128 lineup files exist (World Cup 2018 & 2022); raw event directories (`events/` and `three-sixty/`) were not preserved in the baseline snapshot (Risk R02).

---

### 2.3 Football-Data.co.uk

- **Official Source URL:** `https://www.football-data.co.uk/` (Maintained by Joseph Buchdahl)
- **Data Categories:** Club match results, divisional match statistics, betting odds from multiple bookmakers (Bet365, Pinnacle, William Hill, Betfair, etc.).
- **Available Competitions and Seasons:**
  - *England:* Premier League (E0), Championship (E1), League 1 (E2), League 2 (E3), National League (EC) from 1993/1994 to present season.
  - *Scotland:* Premiership, Championship, League 1, League 2 (1994/95 to present).
  - *Germany:* 1. Bundesliga (D1), 2. Bundesliga (D2) from 1993/94 to present.
  - *Italy:* Serie A (I1), Serie B (I2) from 1993/94 to present.
  - *Spain:* La Liga (SP1), Segunda División (SP2) from 1993/94 to present.
  - *France:* Ligue 1 (F1), Ligue 2 (F2) from 1993/94 to present.
  - *Secondary Leagues:* Netherlands, Belgium, Portugal, Turkey, Greece (approx. 2000 to present).
  - *Americas / Rest of World:* Argentina, Brazil, USA MLS, China, Japan, Mexico (results and odds CSVs).
- **Match-Level Statistics:** Date, Home/Away team, Full-Time Result (FTR), Full-Time Home/Away Goals (FTHG, FTAG), Half-Time Result (HTR), Half-Time Goals (HTHG, HTAG), Referee, Shots (HS, AS), Shots on Target (HST, AST), Hit Woodwork (HHW, AHW), Corners (HC, AC), Fouls Committed (HF, AF), Offsides (HO, AO), Yellow Cards (HY, AY), Red Cards (HR, AR).
- **Player-Level Statistics:** **None**. Zero player names, lineups, or player metrics.
- **Fixture and Result Updates:** Updated twice weekly during active seasons (Monday afternoons post-weekend, Friday mornings post-midweek).
- **API Authentication:** None. Direct static CSV downloads per season (e.g., `https://www.football-data.co.uk/mmz4281/2324/E0.csv`).
- **Rate Limits and Quotas:** No API limits; polite automated download with caching and user-agent headers required.
- **Free vs. Paid Access:** Free historical and current season CSVs.
- **Data Licensing and ML Training Permissions:**
  - *Usage Policy:* Data is made available for personal, non-commercial, and research use.
  - *Commercial Use:* Expressly prohibited without permission.
  - *Academic ML Use:* Permitted for research and academic evaluation.
- **Historical Availability:** Continuous 30+ year unbroken time-series for major European leagues.
- **Reliability and Known Gaps:**
  - **No Cup Competitions:** Does not cover FA Cup, EFL Cup, DFB-Pokal, Copa del Rey, or UEFA club competitions.
  - Team naming conventions vary across seasons (e.g., "Man United" vs "Man City" vs "Manchester United"). Requires explicit alias mapping dictionary.
  - Missing stats in earlier seasons (detailed match stats like shots/corners begin around 2000/2001; prior seasons contain only goals/scores).

---

### 2.4 OpenFootball (football.db / openfootball)

- **Official Source URL:** `https://github.com/openfootball` / `https://github.com/footballcsv`
- **Data Categories:** Match schedules, fixtures, and scores in plaintext / CSV / Markdown format.
- **Available Competitions and Seasons:**
  - *International:* World Cup, Euro, Copa América, Nations League, World Cup Qualifiers.
  - *Club:* Premier League, La Liga, Bundesliga, Serie A, Ligue 1, UEFA Champions League, UEFA Europa League, Copa Libertadores.
  - *Cups:* FA Cup (select seasons), DFB-Pokal (select seasons).
- **Match-Level Statistics:** Date, Team 1, Team 2, Score (full-time and half-time). No detailed in-match metrics (no shots, fouls, corners, xG).
- **Player-Level Statistics:** None (or occasional text mentions in match reports).
- **Fixture and Result Updates:** Maintained by open-source volunteers. Updates can be delayed by days or weeks; not guaranteed for real-time or automated operational pipelines.
- **API Authentication:** None; git clone or raw GitHub file retrieval.
- **Rate Limits and Quotas:** Standard GitHub limits.
- **Free vs. Paid Access:** 100% Free / Open Source.
- **Data Licensing and ML Training Permissions:** CC0 1.0 Universal (Public Domain). Fully permissive for all ML training and modeling.
- **Historical Availability:** Extensive historical club and international seasons, but schema changes between legacy `.txt` format and newer `.csv` format.
- **Reliability and Known Gaps:**
  - Volunteer-driven maintenance causes irregular update cadence.
  - Lacks in-match statistics needed for rich club feature engineering (shots, corners, odds).
  - Excellent for baseline fixture calendar structures (e.g., the 104-fixture 2026 World Cup schedule currently verified in FootIQ was sourced from OpenFootball).

---

### 2.5 API-Football (API-Sports.io)

- **Official Source URL:** `https://www.api-football.com/` / `https://api-sports.io/`
- **Data Categories:** Live scores, fixtures, standings, team squads, lineups, in-match statistics, player season statistics, player match ratings, betting odds, injuries, coach profiles.
- **Available Competitions and Seasons:** Over 1,000 football leagues and cups worldwide:
  - English Premier League, Championship, League One, League Two, FA Cup, EFL Cup, Community Shield.
  - Spanish La Liga, Segunda, Copa del Rey, Supercopa.
  - German Bundesliga, 2. Bundesliga, DFB-Pokal, DFL-Supercup.
  - Italian Serie A, Serie B, Coppa Italia, Supercoppa.
  - French Ligue 1, Ligue 2, Coupe de France, Trophée des Champions.
  - UEFA Champions League, Europa League, Conference League, Super Cup.
  - FIFA World Cup, Qualifiers, Euro, Copa América, Nations League, Club World Cup.
- **Match-Level Statistics:** Shots on goal, shots off goal, total shots, blocked shots, shots inside box, shots outside box, fouls, corner kicks, offsides, ball possession, yellow/red cards, goalkeeper saves, total passes, accurate passes, pass accuracy %.
- **Player-Level Statistics:**
  - Per season & per match: Minutes played, position, rating (algorithmically computed), shots total/on, goals, assists, passes total/key/accuracy, tackles total/blocks/interceptions, duels total/won, dribbles attempts/success/past, fouls drawn/committed, cards, penalties won/commited/scored/missed/saved.
- **Fixture and Result Updates:** Real-time live websocket / REST polling (updated within 15 seconds of match events).
- **API Authentication:** API Key via `x-apisports-key` or RapidAPI header.
- **Rate Limits and Quotas (Verified 2026 Plans):**
  - *Free Tier:* **100 requests per day**, rate-limited to 10 requests/minute.
  - *Pro Tier (€39/month):* 7,500 requests/day, 300 requests/minute.
  - *Mega Tier (€99/month):* 75,000 requests/day.
- **Free vs. Paid Access:** Free tier is strictly limited. 100 requests/day allows monitoring daily active fixtures (e.g. 10 fixtures * 5 requests = 50 calls), but **prohibits bulk historical backfills**. Historical backfilling of an entire 380-match Premier League season with full player/fixture statistics requires over 400 API calls per season, exhausting the free tier in hours.
- **Data Licensing and ML Training Permissions:**
  - Commercial terms prohibit reselling or redistributing raw API data.
  - Using API data to train internal ML models and presenting aggregated predictions/analytics is standard and permitted under developer terms.
- **Historical Availability:** Complete coverage from 2010 to present for major leagues; partial coverage back to 2000.
- **Reliability and Known Gaps:**
  - Free tier daily quota exhaustion stops all ingestion immediately.
  - Player ratings provided by API-Football are proprietary synthetic numbers, not ground-truth athletic measurements.

---

### 2.6 Football-Data.org (Daniel Bhandari API)

- **Official Source URL:** `https://www.football-data.org/`
- **Data Categories:** Fixtures, results, standings, head-to-head records, top scorers.
- **Available Competitions (Free Tier - 12 Competitions):**
  - Premier League (England), Championship (England), Bundesliga (Germany), Serie A (Italy), La Liga (Spain), Ligue 1 (France), Eredivisie (Netherlands), Primeira Liga (Portugal), Brasileirão (Brazil), UEFA Champions League, European Championship, World Cup.
- **Match-Level Statistics:** Scores (full-time, half-time, extra-time, penalties). Detailed in-match stats (shots, fouls, corners) are only available on paid tiers.
- **Player-Level Statistics:** Top scorers list (player name, team, goals, assists). No detailed player match events or per-90 metrics on free tier.
- **Fixture and Result Updates:** Real-time and post-match updates.
- **API Authentication:** API Token via `X-Auth-Token` header.
- **Rate Limits and Quotas:**
  - *Free Tier:* **10 requests per minute**, unlimited daily total calls within rate limit.
- **Free vs. Paid Access:** Free tier allows full season schedule, standings, and match scores. Paid tiers (€15-€40/month) unlock historical depth and additional leagues.
- **Data Licensing and ML Training Permissions:** Free tier permits personal and educational use; commercial use requires paid subscription.
- **Historical Availability:** Free tier provides current season and previous season (last 2-3 seasons). Historical backfills beyond 3 years require paid subscription.
- **Reliability and Known Gaps:**
  - Excellent for automated fixture scheduling and current league standings.
  - Not suitable for deep historical feature engineering (lacks 20-year history on free tier) or player event analytics.

---

### 2.7 Web Scraping Platforms (FBref, Transfermarkt, Understat) — Feasibility & Compliance

- **Platforms:** FBref (Sports Reference LLC), Transfermarkt (Axel Springer SE), Understat.
- **Data Available on Web:** Comprehensive player scouting reports, advanced xG/xA stats, player market values, transfer histories, contracts.
- **Legal and Operational Assessment:**
  - *Terms of Service:* Explicitly forbid automated web scraping, data extraction bots, and systematic harvesting.
  - *Technical Mitigations:* Protected by Cloudflare Bot Management, IP rate-limiting, CAPTCHA challenges, and dynamic DOM rendering. Scraping libraries (such as `worldfootballR` or custom scrapers) frequently break and face IP blacklisting.
  - *Reproducibility & Stability Risk:* Building an engineering pipeline on scrapers violates data reliability engineering principles and academic ethics.
- **Verdict:** **Strictly Prohibited for Core Pipeline.** FootIQ will not build production Airflow DAGs or warehouse ingestion pipelines that rely on scraping these protected web surfaces.

---

## 3. Provider Comparison Matrix

| Evaluation Dimension | Mart Jansen (Intl) | StatsBomb Open Data | Football-Data.co.uk | OpenFootball | API-Football | Football-Data.org |
|---|---|---|---|---|---|---|
| **Primary Domain** | International (1872-pres) | Curated Tournaments | Club Leagues (1993-pres) | Multi-league Results | Global Club & Intl | Top European Leagues |
| **Historical Breadth** | 154 years (49,368 rows) | Selected 80 seasons | 33 years continuous | 10-20 years | 15 years | 2-3 years (Free tier) |
| **Match Detail** | Score, venue, tourney | Full Event x,y Stream | Shots, fouls, cards, odds | Score, date | Full match stats | Scores, standings |
| **Player Statistics** | Goalscorers only | Micro-events, passes, duels | None | None | Comprehensive match stats | Top scorers only |
| **Cup Competitions** | All intl cups | Select finals/tourneys | None | Select FA Cup | FA Cup, EFL, all cups | None on free tier |
| **Update Frequency** | Monthly / batch CSV | Static historical | Twice weekly CSV | Irregular GitHub pull | Real-time / Live API | Real-time / Live API |
| **Authentication** | None | None | None | None | API Key header | API Token header |
| **Rate Limit / Quota** | None | None | Polite download | None | 100 calls/day (Free) | 10 calls/min (Free) |
| **License / Terms** | CC0 Public Domain | CC BY-NC-SA 4.0 | Free research / non-comm | CC0 1.0 Universal | Dev terms / no raw resale | Free educational / dev |
| **ML Training Rights** | Fully Permitted | Permitted (Non-commercial)| Permitted (Research) | Fully Permitted | Permitted (Derivative ML)| Permitted (Educational) |
| **FootIQ Role** | Foundation International | Deep Event/Player ML | Foundation Club League | Schedule Reference | Pilot Cups & Live Pilot | Operational Standings |

---

## 4. Key Findings and Verification Decisions

1. **Club League Match Modeling:** Football-Data.co.uk is the verified optimal primary source for historical domestic league match outcomes. It provides over 30 seasons of uninterrupted, time-consistent results, divisional performance metrics (shots, shots on target), and historical closing odds for England, Spain, Germany, Italy, and France.
2. **Cup Competitions Strategy:** Domestic and European cups (FA Cup, EFL Cup, Champions League) are completely omitted by Football-Data.co.uk. For the English pilot, cup schedules and results must be ingested via OpenFootball (historical) and targeted, budget-governed API-Football calls (current seasons).
3. **Player Analytics Constraints:** StatsBomb Open Data provides the necessary event granularity for advanced player clustering and similarity modeling, but only for specific covered cohorts (e.g. World Cup 2018/2022, La Liga 2004-2021). Regular ongoing player statistics across all modern Premier League squads cannot be ingested via StatsBomb and are severely quota-constrained under API-Football's free tier.
4. **License Compliance:** FootIQ's academic and research architecture complies with StatsBomb CC BY-NC-SA 4.0 (attribution required, non-commercial) and Football-Data.co.uk personal/research usage policies.
