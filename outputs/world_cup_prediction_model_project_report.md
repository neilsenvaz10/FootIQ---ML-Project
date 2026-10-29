# 2026 World Cup Prediction Model Project Report

Generated: June 4, 2026

## Executive Summary

We built a working World Cup prediction-model prototype from public/open data, then iterated it from a basic Elo/form model into a layered tournament simulator with player-impact ratings, manager/tactical layers, bracket simulation, draw-risk calibration, and historical backtesting.

The current best version is **World Cup Model v2.2**. It is a strong research prototype, but it is **not production-ready yet**. The biggest remaining gaps are live/verified player data, lineups, injuries/suspensions, more reliable manager and tactical data, market calibration, and exact tournament-path handling for all third-place knockout scenarios.

The model is deliberately not focused on exact score prediction. That was removed as a headline output because exact football scores are too noisy and usually wrong even when the match-winner read is good. The model instead focuses on title odds, qualification odds, match outcome probability, strongest pick, and draw-risk/no-edge warnings.

## Original Goal

The project started with the idea of studying Joachim Klement's public 2026 World Cup prediction, where he forecasts the Netherlands to win, and then building our own model inspired by that type of work without copying it.

The intended model should:

- Predict the 2026 World Cup winner and tournament path.
- Support match-level predictions without pretending exact scores are reliably knowable.
- Update dynamically as new data arrives.
- Handle player injuries and availability through replacement-gap logic.
- Include Elo/team strength, squad quality, manager impact, recent form, tactical fit, host advantage, weather/context, and market disagreement checks.
- Eventually become a sellable product, not just a school-style experiment.

## Klement Model Research

We researched the public information available about Joachim Klement's World Cup model.

What is public:

- Klement's 2026 note predicts the Netherlands as champion.
- He describes the model as a proprietary econometric model.
- The exact dataset, coefficients, simulation count, random seed, and match-probability method are not public.

Publicly described inputs:

- GDP per capita.
- Population size.
- Average temperature / climate fit.
- Host-country effect.
- FIFA ranking points.
- Luck/randomness.

Our decision:

- Do **not** copy the model.
- Do **not** overweight GDP or population in our model.
- Use Klement as a small outside-reference layer or disagreement audit, not as the core prediction engine.
- Treat his Netherlands pick as a useful challenge case, not as proof our model must force Netherlands to number one.

Created outputs:

- `klement_world_cup_model_readme.md`
- `klement_2026_group_top2_probabilities.csv`
- `klement_2026_knockout_path.csv`
- `world_cup_prediction_public_data_sources.csv`

## Data Collected And Prepared

### Historical International Match Data

We collected and processed international match results.

Processed outputs:

- `international_matches.csv`
- `team_elo_match_history.csv`
- `team_elo_latest.csv`
- `team_recent_form_latest.csv`

Scale:

- 49,296 scored international matches.
- Prototype Elo history for 336 teams.
- Recent-form features for 336 teams.

Use in model:

- Base team strength.
- Elo calculations.
- Recent form.
- Historical backtesting.
- Shootout and knockout simulation support.

### 2026 World Cup Fixtures

We collected the 2026 World Cup fixture structure.

Processed outputs:

- `worldcup_2026_matches.csv`
- `worldcup_2026_teams.csv`

Scale:

- 104 fixtures.
- 48 teams.

Use in model:

- Group simulation.
- Knockout bracket simulation.
- Group path and qualification logic.

Important caveat:

- The model handles the group stage and knockout bracket structure, including top-two qualification and third-place qualification logic. The exact third-place slot allocation matrix should still be hardened before production.

### StatsBomb Open Data

We collected open StatsBomb World Cup data for 2018 and 2022.

Scale:

- 128 World Cup matches.
- 320 downloaded StatsBomb files.
- 256 team-match tactical/event rows after processing.

Use in model:

- Tactical profile prototyping.
- Shots and xG.
- Pressure counts.
- Passing profile.
- Dribble profile.
- Duel profile.
- Set-piece shot counts.
- Under-pressure event counts.

Caveat:

- StatsBomb open data is excellent for prototyping, but a commercial live product would need licensed live data.

### World Bank Macro Data

Collected:

- GDP per capita.
- Population.

Use in model:

- Small Klement-style macro reference.
- Country-level ecosystem proxy.

Decision:

- Macro data should stay low-weight because national-team quality is mostly driven by actual players, squad depth, coaching, and current football performance.

### FIFA Ranking Snapshot

Collected:

- FIFA ranking page snapshot.

Use:

- Potential feature source.
- External sanity check.

Caveat:

- FIFA data must be used carefully under their terms.

### 2026 Squad And Player Data

We populated the player layer from public squad tables.

Scale:

- 1,246 players.

Created outputs:

- `player_impact_v21.csv`
- `model_v21_team_profiles_from_players.csv`
- `model_v21_team_profiles.csv`
- `world_cup_player_impact_v21.xlsx`
- `world_cup_player_impact_v21_summary.md`

The player ratings are **model-derived**, not copied from EA, FIFA, Transfermarkt, or a paid ratings provider.

## Player Impact Rating v2.1

We created a custom player-impact rating instead of buying or copying a ratings feed.

Formula:

```text
impact_score =
30% overall ability
+ 20% club level
+ 22% national role
+ 15% tactical fit
+ 10% form/sharpness
+ 3% tournament experience
```

Replacement gap is separate from base ability:

```text
injury impact = missing player impact - replacement player impact
```

This matters because not every missing player should move the model equally.

Examples:

- Argentina missing Messi should create a major model shock because of role, chance creation, and replacement gap.
- Portugal missing Pedro Neto may have a smaller impact if the replacement is close in quality and tactical role.

Current limitation:

- Recent minutes and sharpness are still inferred, not pulled from a live licensed minutes feed.

## Model Version History

### Model v1

Purpose:

- First working MVP prediction engine.

Main inputs:

- Prototype international Elo.
- Recent form.
- Championship-ceiling adjustment.
- Host advantage.
- StatsBomb open tactical/event adjustment where available.
- Optional player-availability override support.

Important product decision:

- Exact scores are not a headline output.
- Internal goal simulation is used only to build probabilities, group tables, and tournament paths.

Top title odds:

| Rank | Team | Champion % |
|---:|---|---:|
| 1 | Spain | 22.98% |
| 2 | Argentina | 17.39% |
| 3 | France | 13.41% |
| 4 | England | 6.47% |
| 5 | Brazil | 5.21% |

Backtest:

| Year | Brier | Log loss | Favorite accuracy |
|---:|---:|---:|---:|
| 2018 | 0.1849 | 0.9415 | 58.33% |
| 2022 | 0.2096 | 1.0685 | 47.92% |

Champion test:

- France 2018 ranked 5th.
- Argentina 2022 ranked 2nd.

Main issue:

- Brazil and other top sides could become too dominant.
- The public match-pick layer had no real pass/no-edge behavior.

### Model v2

Purpose:

- Reduce Elo dominance by converting feature layers into normalized 0-100 scores before combining.

Weights:

| Layer | Weight |
|---|---:|
| Elo / team strength | 30% |
| Squad quality | 25% |
| Manager quality | 15% |
| Recent form | 10% |
| Tactical score | 10% |
| Championship ceiling | 5% |
| Availability | 5% |

Top title odds:

| Rank | Team | Champion % |
|---:|---|---:|
| 1 | France | 21.21% |
| 2 | Argentina | 15.06% |
| 3 | Spain | 12.95% |
| 4 | Brazil | 9.89% |
| 5 | England | 8.20% |

Improvement:

- Better balanced team-strength composition.
- Added manager and squad layers structurally.

Limitation:

- Squad and manager values were still partly seed/proxy values.

### Model v2.1

Purpose:

- Replace seed squad inputs with the custom Player Impact Rating v2.1 layer.

Player layer:

- 1,246 players populated.
- Squad, expected XI, and bench scores derived from player-impact scores.
- Ratings are transparent and model-derived.

Weights stayed:

| Layer | Weight |
|---|---:|
| Elo / team strength | 30% |
| Squad + player impact | 25% |
| Manager quality | 15% |
| Recent form | 10% |
| Tactical score | 10% |
| Championship ceiling | 5% |
| Availability | 5% |

Top title odds:

| Rank | Team | Champion % |
|---:|---|---:|
| 1 | France | 18.25% |
| 2 | Argentina | 13.98% |
| 3 | Spain | 13.54% |
| 4 | Brazil | 8.95% |
| 5 | England | 7.01% |
| 6 | Germany | 6.09% |
| 7 | Colombia | 5.68% |
| 8 | Japan | 3.61% |
| 9 | Portugal | 3.43% |
| 10 | Morocco | 2.89% |
| 11 | Turkey | 2.80% |
| 12 | Netherlands | 2.41% |

Audit findings:

- Germany ranked above Portugal because of stronger recent-form, tactical, and manager layers.
- Colombia ranked above Portugal because it had a stronger Group K first-place profile in our model.
- Japan ranked above Portugal mostly because of recent-form and Group F path effects.
- Netherlands ranked low because of weaker recent-form/manager/tactical layers and group-path risk.

Historical backtest:

| Year | Brier | Log loss | Favorite accuracy |
|---:|---:|---:|---:|
| 2018 | 0.1766 | 0.9066 | 58.33% |
| 2022 | 0.2195 | 1.1356 | 45.83% |

Champion test:

- France 2018 ranked 5th with 7.10% title probability.
- Argentina 2022 ranked 3rd with 16.66% title probability.

Important caveat:

- The historical backtest used historical public squad metadata, not 2026 player data.
- That avoided the data-leak issue of testing 2018/2022 using 2026 players.

### Model v2.2

Purpose:

- Fix the issue where the model almost never predicted draws.
- Make draw-risk a first-class match state.

What changed:

- Base goal rate lowered from 1.18 to 1.15.
- Power-to-goal scale widened from 43 to 62.0.
- Draw-risk thresholds added.
- Public draw language became conservative.

What did not change:

- The team-strength weights stayed the same as v2.1.

Configuration:

| Setting | Value |
|---|---:|
| Simulations | 50,000 |
| Base goal rate | 1.15 |
| Power goal scale | 62.0 |
| Draw decision minimum | 0.28 |
| Draw gap maximum | 0.12 |
| Draw favorite maximum | 0.42 |
| Firm draw gap maximum | 0.04 |
| Firm draw favorite maximum | 0.38 |

Current weights:

| Layer | Weight |
|---|---:|
| Elo / team strength | 30% |
| Squad + player impact | 25% |
| Manager quality / tactical control | 15% |
| Recent form | 10% |
| Tactical matchup layer | 10% |
| Championship ceiling | 5% |
| Availability / injury impact | 5% |

Top title odds:

| Rank | Team | Champion % | Final % | Semi % |
|---:|---|---:|---:|---:|
| 1 | France | 14.47% | 22.67% | 34.38% |
| 2 | Argentina | 11.89% | 20.01% | 32.97% |
| 3 | Spain | 11.59% | 19.65% | 33.08% |
| 4 | Brazil | 8.15% | 14.51% | 24.54% |
| 5 | England | 6.71% | 12.75% | 22.93% |
| 6 | Germany | 6.14% | 12.03% | 21.29% |
| 7 | Colombia | 5.66% | 11.41% | 22.28% |
| 8 | Japan | 4.20% | 8.68% | 16.75% |
| 9 | Portugal | 3.84% | 8.39% | 17.63% |
| 10 | Morocco | 3.42% | 7.50% | 14.82% |
| 11 | Turkey | 3.20% | 7.19% | 16.09% |
| 12 | Netherlands | 3.06% | 6.93% | 14.10% |

Draw output:

- 14 group-stage 90-minute draw picks.
- 3 public draw leans.
- 11 draw-risk/no-strong-edge calls.

Backtest:

| Year | Brier | Log loss | Pick accuracy | Draw picks | Draw pick accuracy | Actual draws |
|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 0.1785 | 0.9153 | 47.92% | 9 | 0.00% | 9 |
| 2022 | 0.2117 | 1.0738 | 45.83% | 9 | 22.22% | 10 |

v2.2 vs v2.1:

| Year | Metric | v2.1 | v2.2 | Delta |
|---:|---|---:|---:|---:|
| 2018 | Brier | 0.1766 | 0.1785 | +0.0019 |
| 2018 | Log loss | 0.9066 | 0.9153 | +0.0087 |
| 2018 | Pick accuracy | 58.33% | 47.92% | -10.41 |
| 2022 | Brier | 0.2195 | 0.2117 | -0.0078 |
| 2022 | Log loss | 1.1356 | 1.0738 | -0.0618 |
| 2022 | Pick accuracy | 45.83% | 45.83% | 0.00 |

Interpretation:

- v2.2 improves probability calibration on the combined 2018/2022 test.
- Hard draw picks are still unreliable.
- Draw should be presented as "draw risk" or "no strong edge" most of the time, not as a confident betting-style draw call.

## Key Product Decisions Made

### 1. Do Not Headline Exact Score Prediction

We decided not to make exact score prediction a major output.

Reason:

- Exact football scores are extremely hard to predict.
- Even the most likely exact score is usually a low-probability event.
- A model can be good at match direction and still be terrible at exact scores.

Current model stance:

- Use goals internally.
- Output winner lean, draw risk, qualification odds, and title odds.
- Avoid selling "correct score" as a serious edge.

### 2. Use Percentages Internally, But Do Not Make The Product Feel Like Generic Betting Odds

The model can calculate probabilities such as:

```text
Team A win: 42%
Draw: 28%
Team B win: 30%
```

But the product should not simply show that and call it an edge.

Better product output:

- Strong pick.
- Lean.
- No strong edge.
- Draw risk.
- Model-market disagreement.
- Path advantage/disadvantage.
- Injury or lineup shock impact.

### 3. Treat Draws As Risk, Not A Main Target

Draws matter because they affect group standings and betting-style predictions, but they are difficult to call confidently.

Current decision:

- Keep draw probabilities.
- Keep draw-risk labels.
- Avoid obsessing over confident hard draw picks.

### 4. Injury Impact Must Use Replacement Gap

A player missing should not automatically cause a huge penalty.

Correct logic:

- How important is the player?
- How many minutes was he expected to play?
- How unique is his tactical role?
- Who replaces him?
- How large is the replacement gap?

This is already designed into the player-impact and availability contracts.

## Sensitive Ranking Discussion

We specifically investigated why teams like Colombia, Japan, and Germany ranked above Portugal, and why the Netherlands ranked only 12th in v2.1/v2.2.

### Portugal

Portugal has a strong squad score, but the model currently penalizes Portugal through:

- Lower recent-form score.
- Lower manager/tactical score.
- Group K pressure from Colombia.
- A less favorable path when Portugal does not win the group.

This does **not** mean Portugal are bad.

It means our current model is meaningfully lower on Portugal than the betting market and public perception. That is a red-flag audit item for v2.3.

### Colombia

Colombia ranks above Portugal because:

- Colombia is in the same group as Portugal.
- The model currently gives Colombia a better chance of winning Group K.
- Winning the group gives a cleaner knockout lane.

### Germany

Germany ranks above Portugal because:

- Higher power score.
- Better recent-form/tactical/manager profile in the current model.
- Cleaner group-winner path.

### Japan

Japan ranks just above Portugal because:

- Strong recent-form score.
- Favorable Group F winner path.
- Slight path advantage in the simulation.

### Netherlands

Netherlands are below the Klement forecast because:

- Our model gives them weaker recent-form, manager, and tactical scores.
- Their group/path positioning is less friendly.
- The Klement model uses a macro/econometric structure that we chose not to copy or overweight.

## Is The Model Production-Ready?

No. It is not production-ready yet.

It is a serious prototype with good architecture, but production readiness requires:

- Verified live squads.
- Confirmed and expected lineups.
- Injuries and suspensions.
- Real player minutes and role data.
- Better manager/formation data.
- Market calibration.
- Exact third-place bracket allocation hardening.
- Monitoring and versioned data refreshes.
- Legal/licensed data sources for any commercial product.
- A product interface and explainability layer.

## Data Provider Recommendation

The current recommendation is to start small and practical.

Best first paid data target:

- **API-Football Pro**, around $19/month based on the researched pricing page.

Why:

- Fixtures.
- Squads.
- Players.
- Coaches.
- Injuries.
- Lineups.
- Team statistics.
- Odds endpoints.
- Enough breadth to improve the model without jumping to enterprise pricing.

Upgrade path:

- API-Football Ultra around $29/month only if request volume becomes a problem.
- Sportmonks if API-Football coverage or data quality is not enough.
- Expensive event/tracking providers only later, after the model/product proves demand.

Skip for now:

- Expensive Opta/Sportradar/Wyscout/SkillCorner-style enterprise data.
- Odds-only APIs as the first purchase.
- Paid tracking data before the product has users or revenue.

## Recommended v2.3 Direction

Version 2.3 should not be a random weight tweak. It should focus on the model's most obvious current risks.

Recommended v2.3 work:

1. Add a provider-ready data ingestion layer.
2. Add a market sanity layer without blindly copying betting odds.
3. Run a Portugal-specific audit.
4. Improve player-role and manager/tactical scoring.
5. Harden the group-third-place knockout allocation logic.
6. Add dynamic refresh logic for injuries, lineups, and post-match updates.
7. Create a versioned workbook/report comparing v2.2 and v2.3.

Suggested v2.3 weight test:

| Layer | Weight |
|---|---:|
| Elo / team strength | 25% |
| Squad + player impact | 25% |
| Manager / tactical control | 15% |
| Recent form | 10% |
| Tactical matchup | 10% |
| Championship ceiling | 5% |
| Availability / injury impact | 5% |
| Market sanity layer | 5% |

The market sanity layer should not force the model to agree with bookmakers. It should flag and soften extreme disagreements, especially cases like Portugal.

## Current Deliverables

Main user-facing files created:

- `world_cup_model_data_pack.xlsx`
- `world_cup_model_v1_predictions.xlsx`
- `world_cup_model_v1_summary.md`
- `world_cup_model_v1_backtest.xlsx`
- `world_cup_model_v1_backtest_report.md`
- `world_cup_model_v2_predictions.xlsx`
- `world_cup_model_v2_summary.md`
- `world_cup_player_impact_v21.xlsx`
- `world_cup_player_impact_v21_summary.md`
- `world_cup_model_v21_predictions.xlsx`
- `world_cup_model_v21_summary.md`
- `world_cup_model_v21_audit_backtest.xlsx`
- `world_cup_model_v21_audit_backtest_report.md`
- `world_cup_model_v22.xlsx`
- `world_cup_model_v22_summary.md`
- `world_cup_model_v22_backtest_report.md`
- `klement_world_cup_model_readme.md`
- `klement_2026_group_top2_probabilities.csv`
- `klement_2026_knockout_path.csv`
- `world_cup_prediction_public_data_sources.csv`

## Bottom Line

We now have a real model architecture:

- Public-data foundation.
- Elo and form engine.
- Player-impact layer.
- Manager/tactical layer.
- Tournament simulator.
- Backtesting.
- Draw-risk calibration.
- Klement comparison.
- Production data-provider plan.

But the model is not yet sellable as-is. The next serious step is v2.3: connect better live data, audit Portugal and other market disagreements, improve player-role/manager inputs, and make the model dynamic enough to react to new tournament information.
