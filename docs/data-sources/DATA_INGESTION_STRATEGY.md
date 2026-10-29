# FootIQ Data Ingestion & Integration Strategy

**Document:** `DATA_INGESTION_STRATEGY.md`  
**Milestone:** Milestone 2 (Dataset Verification and Scope Finalization)  
**Date:** 20 October 2026  
**Status:** Architectural strategy defined; ready for Milestone 3 database schema design.  
**Baseline References:** `BASELINE_AUDIT.md`, `RISK_REGISTER.md` (Risks R01, R04, R07, R15).

---

## 1. Architectural Ingestion Framework

FootIQ implements a multi-tier ELT (Extract-Load-Transform) warehouse architecture across three logical data layers:

```
+--------------------------------------------------------------------------------------------------+
|                                    RAW / BRONZE LAYER (Landing)                                  |
|  - Immutable local file storage of raw CSVs, JSON responses, and API payloads                     |
|  - Stored with ingestion timestamp, provider tag, and SHA-256 payload hash                       |
+--------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+--------------------------------------------------------------------------------------------------+
|                                  SILVER LAYER (Harmonized Warehouse)                             |
|  - Normalized relational PostgreSQL schema                                                       |
|  - Canonical entity resolution (Teams, Players, Competitions, Venues)                             |
|  - Deduplication, timezone standardization (UTC), and score semantic decomposition               |
+--------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+--------------------------------------------------------------------------------------------------+
|                                   GOLD LAYER (Analytical / Feature Store)                         |
|  - Time-safe, point-in-time feature tables (Elo history, rolling form, head-to-head metrics)       |
|  - ML training datasets with zero look-ahead bias                                                 |
|  - Fast query views for FastAPI endpoints and React dashboard consumption                        |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Ingestion Matrix: Primary and Fallback Sources by Category

| Data Category | Primary Source | Fallback Source | Ingestion Format | Ingestion Protocol | Quota Impact |
|---|---|---|---|---|---|
| **International Match Results** | Mart Jansen (GitHub raw CSV) | Kaggle dataset API | CSV | Batch HTTP download / Git pull | Zero (Free/Open) |
| **Club League Results & Odds** | Football-Data.co.uk | Football-Data.org / API-Football | CSV | Scheduled batch download with headers | Zero (Free/Open) |
| **Club Domestic Cups (FA/EFL)**| OpenFootball (Historical) | API-Football (Current rounds) | CSV / JSON | Git pull (Hist) + API poll (Live) | 4-8 API calls/round |
| **European Club Competitions** | Football-Data.org (Free Tier) | API-Football / OpenFootball | JSON / REST | Token-authenticated REST API | ~10 API calls/matchday |
| **Event-Level Player Tracking**| StatsBomb Open Data (GitHub) | Local baseline archive | JSON / REST | `statsbombpy` / raw JSON download | Zero (Free/Open) |
| **Squad Rosters & Lineups** | API-Football (Fixture Lineups)| StatsBomb (Tournament rosters) | JSON / REST | Budget-governed API call | 1 call per fixture |
| **Tournament Fixtures (WC 2026)**| OpenFootball 2026 schedule | FIFA official publications | CSV | Static file verification | Zero (Free/Open) |

---

## 3. Entity Resolution & Data Harmonization

A core failure mode in multi-source football data pipelines is entity fragmentation—where the same physical team or player exists under multiple divergent strings across different data providers.

### 3.1 Canonical Team Identity System
Different providers use radically different naming conventions for identical clubs:
- *Football-Data.co.uk:* `"Man United"`, `"Wolves"`, `"Nott'm Forest"`, `"Ath Bilbao"`.
- *API-Football:* `"Manchester United"`, `"Wolverhampton Wanderers"`, `"Nottingham Forest"`, `"Athletic Club"`.
- *OpenFootball:* `"Manchester United FC"`, `"Wolverhampton Wanderers FC"`, `"Nottingham Forest FC"`.
- *Mart Jansen (International):* `"USA"`, `"Korea Republic"`, `"Côte d'Ivoire"`, `"Curaçao"`.

**Harmonization Strategy:**
1. FootIQ maintains a centralized `dim_team` table with a surrogate primary key `team_id` (UUID or integer).
2. A dedicated mapping table `dim_team_alias` maps any provider-specific name to the canonical `team_id`:
   ```sql
   -- Conceptual Schema (Milestone 3 target)
   CREATE TABLE dim_team_alias (
       alias_id SERIAL PRIMARY KEY,
       team_id INT REFERENCES dim_team(team_id),
       provider_name VARCHAR(50) NOT NULL,
       source_string VARCHAR(100) NOT NULL,
       is_verified BOOLEAN DEFAULT TRUE,
       UNIQUE (provider_name, source_string)
   );
   ```
3. Incoming records pass through an exact alias lookup. Unmatched team names trigger an automated quarantine record and raise an alert for manual administrator verification, preventing silent insertion of duplicate teams.

### 3.2 Character Encoding and Accent Normalization
Historical baseline audit revealed that default Windows character encoding (CP1252) caused team name decoding errors on names such as `Curaçao` or `Côte d'Ivoire` (Risk R12).
- **Mandatory Pipeline Rule:** All ingestion pipelines, CSV parsers, database connections, and file writers MUST explicitly enforce `utf-8` encoding.
- Text strings undergo Unicode NFKD normalization to strip diacritics for search indexing while retaining canonical UTF-8 accented strings for display.

### 3.3 Natural Composite Key for Duplicate Match Detection
When ingesting the same competition from multiple sources (e.g. comparing Football-Data.co.uk league matches against API-Football records):
$$\text{Natural Match Key} = \text{Date (UTC)} \;\|\; \text{Canonical Home Team ID} \;\|\; \text{Canonical Away Team ID} \;\|\; \text{Competition ID}$$
If an incoming record matches an existing `Natural Match Key`, the ingestion pipeline executes an **upsert** (updating missing statistics, such as referee or odds, without duplicating the match record).

### 3.4 Player Identity Resolution and Deduplication
1. For StatsBomb datasets, the immutable integer `player_id` is preserved as `statsbomb_player_id`.
2. For API-Football datasets, the integer `player_id` is preserved as `api_football_player_id`.
3. In the unified `dim_player` table, cross-provider matching requires:
   - Normalized Full Name match (Jaro-Winkler similarity $\ge 0.92$) AND
   - Matching Date of Birth (exact day/month/year) OR
   - Matching Nationality + Verified Club Roster membership.

---

## 4. Match Semantics and Edge Case Protocols

### 4.1 Decomposing Extra Time and Penalty Shootouts (Resolving Risk R04)
Historical international results stored in `results.csv` lump regular time and extra-time goals into a single scoreline without differentiation. This corrupts 90-minute ML prediction models (Risk R04).

**Harmonized Match Score Data Contract:**
Every completed match record in the Silver warehouse must decompose scoring into unambiguous components:
- `score_regular_home`: Home goals scored in regulation 90 minutes (+ stoppage).
- `score_regular_away`: Away goals scored in regulation 90 minutes (+ stoppage).
- `score_extra_home`: Home goals scored in extra time (minutes 91–120; NULL for league matches).
- `score_extra_away`: Away goals scored in extra time (minutes 91–120; NULL for league matches).
- `penalties_home`: Goals scored in penalty shootout (NULL if no shootout occurred).
- `penalties_away`: Goals scored in penalty shootout (NULL if no shootout occurred).
- `match_outcome_90`: **Home Win (H)**, **Draw (D)**, or **Away Win (A)** strictly based on regulation 90 minutes.

### 4.2 Handling Postponed, Rescheduled, and Abandoned Fixtures
Football fixtures frequently change dates due to weather, cup replays, or broadcast rescheduling.
- Match status must transition through a strict state machine:
  `SCHEDULED` $\rightarrow$ `TIMED` $\rightarrow$ `IN_PLAY` $\rightarrow$ `FINISHED`  
  Alternative branches: `POSTPONED`, `CANCELLED`, `ABANDONED`, `SUSPENDED`.
- **Date Changes:** When a fixture is postponed, its `scheduled_date` is updated, but its unique fixture ID remains invariant.
- **Abandoned Matches:** If a match is abandoned before 90 minutes, it is flagged as `ABANDONED`. If a replay is scheduled, a new fixture record is generated with a reference pointer `replayed_by_fixture_id`.
- **Unscored / Future Rows:** The 72 unscored rows in `results.csv` (June 2026 World Cup) will be tagged as `SCHEDULED` with NULL scores, cleanly separating them from completed training data.

### 4.3 Retrospective Score Adjustments and Disciplinary Overturns
On rare occasions, a competition governing body awards a 3-0 forfeit win due to ineligible players.
- FootIQ employs **Slowly Changing Dimensions (SCD Type 2)** or an append-only audit log:
  - The on-pitch result is retained with `is_on_pitch_result = TRUE`.
  - The administrative result is recorded with `is_administrative_result = TRUE` and an `effective_timestamp`.
  - ML feature generation uses on-pitch performance metrics for team strength estimation, not artificial 3-0 administrative forfeits.

---

## 5. Ingestion Engine Resilience & API Governance

### 5.1 Call Budgeting and Quota Enforcement (Preventing API Overruns)
To operate reliably within the API-Football free-tier limit (100 requests/day, 10 requests/minute):
1. **Persistent Call Ledger:** Every API call is logged to a local SQLite/PostgreSQL table `api_call_ledger` tracking `timestamp`, `endpoint`, `params`, `status_code`, and `response_time_ms`.
2. **Hard Daily Gate:** The pipeline checks:
   $$\sum \text{Calls in last 24 hours} < 90$$
   A 10-call safety buffer is permanently reserved for emergency pipeline health checks. If the quota reaches 90, non-critical ingestion jobs sleep automatically until the quota window resets.
3. **Adaptive Rate Limiting:** A token bucket limiter guarantees calls are separated by at least 6.5 seconds, preventing the 10 calls/minute burst cap from triggering HTTP 429 errors.

### 5.2 Exponential Backoff and Circuit Breaking
Network requests wrap an exponential backoff retry loop with randomized jitter:
$$t_{\text{wait}} = \min(t_{\text{max}}, \; t_{\text{base}} \times 2^{\text{attempt}}) + \text{jitter}$$
- HTTP 429 (Rate Limit): Read `Retry-After` header; if absent, pause for 60 seconds.
- HTTP 500, 502, 503, 504: Retry up to 3 times before failing the step.
- Circuit Breaker: If 5 consecutive requests fail, the circuit trips open, aborting the task and alerting the system.

### 5.3 Local Disk-Backed Raw Caching
All external HTTP responses are immediately serialized to disk in `data/raw/<provider>/<date>/<hash>.<ext>` prior to any parsing. Re-running a downstream parsing or normalization DAG never calls the external API again; it reads directly from the raw disk cache.

---

## 6. Operational Ingestion Schedules (Airflow DAG Design)

```
+-------------------------------------------------------------------------------------------------------+
| INGESTION CADENCE SCHEDULE                                                                            |
+-------------------------------------------------------------------------------------------------------+
| SCHEDULE          | PIPELINE / DAG NAME            | ACTIONS & TARGETS                                |
+-------------------------------------------------------------------------------------------------------+
| Daily at 04:00 UTC| `dag_daily_fixture_sync`       | Sync upcoming schedules, kickoff times, venue   |
|                   |                                | changes, and postponement flags for next 7 days. |
+-------------------------------------------------------------------------------------------------------+
| Mondays 12:00 UTC | `dag_weekend_results_ingest`   | Ingest weekend club league results & match stats |
|                   |                                | from Football-Data.co.uk; update league standings|
+-------------------------------------------------------------------------------------------------------+
| Fridays 10:00 UTC | `dag_midweek_results_ingest`   | Ingest midweek European & league cup fixtures    |
|                   |                                | (Champions League, EFL Cup rounds).              |
+-------------------------------------------------------------------------------------------------------+
| Tuesdays 02:00 UTC| `dag_player_stats_pilot_sync`  | Ingest confirmed lineups and match statistics    |
|                   |                                | for English Premier League pilot fixtures.       |
+-------------------------------------------------------------------------------------------------------+
| 1st of each Month | `dag_intl_results_monthly_sync`| Ingest updated international results CSV from    |
|                   |                                | Mart Jansen GitHub repo; re-calculate Elo table. |
+-------------------------------------------------------------------------------------------------------+
```
