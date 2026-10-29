# Confirmed-Lineup Impact v2.12

Frozen for lineup shadow evaluation: 2026-06-22T16:37:45-04:00

V2.12 adjusts frozen v2.11 probabilities only when both confirmed starting XIs pass identity and timing checks.

## Guardrails

- Both teams require 11 starters and at least 90% player-identity coverage.
- Only lineup snapshots captured at or before kickoff can enter evaluation.
- A team adjustment is capped in log-odds space and final probability movement is capped at five percentage points.
- V2.12 can preserve or downgrade a v2.11 call; it cannot create a pick from a v2.11 Pass.

## Identity Audit

- Provider starters inspected: 44.
- Matched to Player Impact Rating v2.1: 43/44 (97.73%).
- Controlled fuzzy matches: 1.

| Team | Formation | Matched | Baseline XI | Confirmed XI | Delta | Missing expected starters |
|---|---|---:|---:|---:|---:|---|
| France | 4-2-3-1 | 11/11 | 85.06 | 84.20 | -0.86 | Aurélien Tchouaméni; Lucas Hernandez; Ibrahima Konaté; N'Golo Kanté |
| Iraq | 4-2-3-1 | 11/11 | 63.12 | 59.67 | -3.46 | Mohanad Ali; Jalal Hassan; Ali Al-Hamadi; Manaf Younis; Rebin Sulaka |
| Ivory Coast | 4-1-4-1 | 11/11 | 77.33 | 74.34 | -2.99 | Amad Diallo; Seko Fofana; Simon Adingra; Evan Ndicka; Wilfried Singo; Ousmane Diomande |
| Norway | 4-3-3 | 10/11 | 81.81 | 82.13 | +0.32 | Kristian Thorstvedt; Leo Østigård; Marcus Holmgren Pedersen |

## Frozen Lineup Shadow Results

- Completed lineup-eligible fixtures: 2.
- Public picks scored: 1.
- Correct public picks: 1.
- Accuracy: 100.00%.

## Lineup-Eligible Shadow Calls

| Match | Kickoff | Result | v2.11 | v2.12 | Base 1/X/2 | Adjusted 1/X/2 | Lineup deltas |
|---|---:|---|---|---|---|---|---|
| France vs Iraq | 2026-06-22 17:00 | 3-0 | Model Lean: team1_win | Model Lean: team1_win | 68.2/25.5/6.3 | 68.1/26.2/5.8 | -0.86 / -3.46 |
| Ivory Coast vs Norway | 2026-06-30 13:00 | 1-2 | Pass: pass | Pass: pass | 15.4/32.2/52.3 | 14.0/32.6/53.4 | -2.99 / +0.32 |

## Honest Read

V2.12 has no accuracy claim yet. Its first job is reliable player identity, pre-kickoff timing, bounded probability movement, and an auditable comparison against v2.11 on the same fixtures.
