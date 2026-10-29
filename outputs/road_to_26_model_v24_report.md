# Road to 26 Model v4 Test

This is the first provider-connected test slice for the World Cup model. It uses the v2.3 match engine, cached API-Football fixture data where available, and global Elo/recent-form fallback ratings for teams outside the 48-team World Cup field.

## API Budget

- Daily limit configured: 100.
- Reserve kept untouched: 15.
- Requests counted today: 4.
- Remaining before local stop: 81.

## Provider Coverage

- Fixtures in Road to 26 test slate: 6.
- API-Football fixture matches found: 5.
- Finished fixtures available for scoring: 0.

## Model Picks

| Date | Match | Public verdict | Confidence | Pick | Provider status | Actual | Correct |
|---|---|---|---|---|---|---|---|
| 2026-06-06 16:00 ET | Bolivia vs Scotland | Draw lean | Low-medium | draw | NS |  |  |
| 2026-06-06 18:00 ET | Brazil vs Egypt | Brazil avoid defeat | Medium-low | team1_win | NS |  |  |
| 2026-06-06 20:00 ET | Argentina vs Honduras | Argentina win lean | Medium | team1_win | NS |  |  |
| 2026-06-07 15:00 ET | Morocco vs Norway | Draw risk / no strong edge | Pass | draw | NS |  |  |
| 2026-06-07 19:00 ET | Colombia vs Jordan | Colombia win lean | Medium | team1_win | NS |  |  |
| 2026-06-09 20:30 ET | Argentina vs Iceland | Argentina win lean | Medium | team1_win | not fetched/found |  |  |

## How To Use This

- Run before kickoff to get the model pick and provider fixture ID.
- Run again after full time to capture the actual result and update the accuracy columns.
- Keep details fetch enabled on matchday; lineups/events/statistics are only requested when API-Football marks the fixture active or final.

## Caveat

Friendlies are noisier than competitive matches because teams rotate squads, test shapes, and manage minutes. For that reason, v4 caps public confidence at Medium even when the raw model likes a favorite strongly.
