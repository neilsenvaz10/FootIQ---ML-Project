# World Cup Prediction Model Data Inventory

## Data Collected Now

This workspace now has a usable public-data foundation for a prototype model.

### Historical Match Results

Location: `data/raw/international_results/`

Files:

- `results.csv`
- `shootouts.csv`
- `goalscorers.csv`
- `former_names.csv`

Processed outputs:

- `data/processed/international_matches.csv` - 49,296 scored international matches
- `data/processed/team_elo_match_history.csv` - 98,592 team-match Elo history rows
- `data/processed/team_elo_latest.csv` - current prototype Elo table for 336 teams
- `data/processed/team_recent_form_latest.csv` - last-5 and last-10 form features for 336 teams

Use:

- base team strength
- prototype Elo
- recent form
- World Cup backtesting
- shootout modeling

Important note: this is a prototype Elo generated from match results, not an official Elo feed.

### StatsBomb Open Data

Location: `data/raw/statsbomb/`

Collected:

- 2018 FIFA World Cup match metadata
- 2022 FIFA World Cup match metadata
- events
- lineups
- 360 data where available

Download result:

- 128 World Cup matches
- 320 downloaded StatsBomb files
- 64 missing 360 files where open data does not expose that layer

Processed outputs:

- `data/processed/statsbomb_worldcup_matches.csv` - 128 match rows
- `data/processed/statsbomb_team_event_summary.csv` - 256 team-match tactical/event rows

Use:

- tactical profile prototyping
- shots and xG
- pressure counts
- passing profile
- dribble profile
- duel profile
- set-piece shot counts
- under-pressure event counts

Commercial note: StatsBomb open data is excellent for prototyping, but a sellable live product needs a licensed feed.

### World Cup 2026 Fixtures

Location: `data/raw/openfootball/worldcup_2026.json`

Processed outputs:

- `data/processed/worldcup_2026_matches.csv` - 104 fixtures
- `data/processed/worldcup_2026_teams.csv` - 48 teams

Use:

- group simulation
- knockout path simulation
- rest-day calculations
- venue/weather joins

### World Bank Macro Data

Location: `data/raw/worldbank/`

Files:

- `gdp_per_capita_all.json`
- `population_all.json`

Processed output:

- `data/processed/worldbank_macro_latest.csv`

Use:

- small Klement-style macro prior
- country-level long-term football ecosystem proxy

Recommended weight: low. This should not dominate match predictions.

### FIFA Ranking Page Snapshot

Location: `data/raw/fifa/men_rankings_page_id3.html`

Use:

- reference snapshot
- optional feature if we build a clean parser or obtain an official feed

Commercial note: use FIFA data carefully under their terms.

## Data Contracts Created

The model needs live/paid/manual feeds for the serious version. I created strict contract files so those feeds can be plugged in later without changing the model architecture.

Location: `data/contracts/`

Files:

- `player_availability_contract.csv`
- `squad_quality_contract.csv`
- `odds_snapshots_contract.csv`
- `weather_snapshots_contract.csv`
- `tactical_profile_contract.csv`
- `manual_overrides_contract.csv`

## Player Impact Logic

Injury impact should not be:

```text
 famous player missing = huge penalty
```

It should be:

```text
 injury penalty = player impact rating - replacement impact rating
```

Example:

```text
 Portugal missing Pedro Neto:
 small or medium impact if the replacement is similar quality

 Argentina missing Messi:
 large impact if the whole chance-creation system depends on him and the replacement gap is huge
```

The `player_availability_contract.csv` supports this directly with:

- `player_impact_rating`
- `replacement_player`
- `replacement_impact_rating`
- `replacement_gap`
- `expected_minutes`
- `confidence_score`

## What Is Still Missing For A Sellable Product

These are not in hand yet because they require licensed APIs, credentials, or manual analyst workflows.

### Live Injuries, Suspensions, And Lineups

Needed for:

- injury impact calculator
- confirmed lineup update
- pre-match dynamic reruns

Possible providers:

- Sportmonks
- API-Football
- Sportradar
- Opta
- Wyscout

### Player Quality / Squad Depth Feed

Needed for:

- squad quality layer
- replacement-gap modeling
- player role importance

Possible providers:

- Wyscout
- StatsBomb paid
- Opta/Sportradar
- Sportmonks/API-Football for simpler version

Avoid relying on scraped Transfermarkt data for a commercial product unless licensing is solved.

### Live Odds Feed

Needed for:

- odds movement tracker
- market comparison
- model-vs-market disagreement

Possible providers:

- The Odds API
- Sportmonks odds
- API-Football odds
- Sportradar
- Pinnacle/Betfair-style specialist feeds if available

### Weather Feed

Needed for:

- kickoff temperature
- humidity
- wind
- rain
- apparent temperature

Possible providers:

- Open-Meteo
- NOAA
- Visual Crossing

### Elite Tactical / Tracking Feed

Needed for the truly sharp tactical matchup layer:

- defensive line height
- off-ball runs
- pressure shape
- transition exposure
- sprint/physical data
- spacing

Possible providers:

- StatsBomb paid
- Wyscout
- SkillCorner
- Opta

## Current Readiness

Prototype model:

```text
 ready to start
```

Commercial-grade live product:

```text
 data architecture ready
 paid/live feed acquisition still required
```

