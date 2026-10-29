# Player Impact Rating v2.1

Version 2.1 populates World Cup squad player names and generates a transparent, model-derived impact rating. It does not copy EA, FIFA, Transfermarkt, or a paid provider rating.

## Formula

`impact_score = 30% overall + 20% club level + 22% national role + 15% tactical fit + 10% form/sharpness + 3% tournament experience`

Replacement gap is calculated within each team's positional unit and is kept separate from base ability so injuries can move the model dynamically.

## Current Limitations

- Club level is a heuristic prior, not a licensed provider feed.
- Recent minutes are inferred from club level, role, age, and caps until a real minutes feed is attached.
- National role is inferred from caps, captaincy, and goals; it should be upgraded with recent starting XI/minute data.
- Ratings are suitable for model development and analyst review, not as a claimed official player-rating product.

## Top 25 Player Impact Scores

| Rank | Player | Team | Pos | Club | Impact | Role | Replacement gap |
|---:|---|---|---|---|---:|---|---:|
| 1 | Kylian Mbappé | France | FW | Real Madrid | 96.43 | Starter | 13.84 |
| 2 | Ferran Torres | Spain | FW | Barcelona | 93.89 | Starter | 4.02 |
| 3 | Harry Kane | England | FW | Bayern Munich | 93.61 | Starter | 9.70 |
| 4 | Rodri | Spain | MF | Manchester City | 92.56 | Starter | 6.94 |
| 5 | Erling Haaland | Norway | FW | Manchester City | 91.97 | Starter | 4.79 |
| 6 | Achraf Hakimi | Morocco | DF | Paris Saint-Germain | 91.82 | Starter | 13.01 |
| 7 | Alexander Sørloth | Norway | FW | Atlético Madrid | 91.43 | Starter | 2.80 |
| 8 | Dani Olmo | Spain | FW | Barcelona | 91.37 | Starter | 1.50 |
| 9 | Christian Pulisic | USA | FW | Milan | 91.36 | Starter | 12.75 |
| 10 | Mohamed Salah | Egypt | FW | Liverpool | 90.82 | Starter | 9.65 |
| 11 | Marcus Rashford | England | FW | Barcelona | 90.56 | Starter | 1.50 |
| 12 | Alexander Isak | Sweden | FW | Liverpool | 90.18 | Starter | 5.03 |
| 13 | Martin Ødegaard | Norway | MF | Arsenal | 90.09 | Starter | 10.70 |
| 14 | Kai Havertz | Germany | FW | Arsenal | 90.07 | Starter | 10.96 |
| 15 | Cody Gakpo | Netherlands | FW | Liverpool | 90.05 | Starter | 4.62 |
| 16 | Luis Díaz | Colombia | FW | Bayern Munich | 89.75 | Starter | 11.09 |
| 17 | Hakan Çalhanoğlu | Turkey | MF | Inter Milan | 89.53 | Starter | 12.87 |
| 18 | Joshua Kimmich | Germany | DF | Bayern Munich | 89.40 | Starter | 7.35 |
| 19 | Jonathan David | Canada | FW | Juventus | 89.26 | Starter | 9.81 |
| 20 | Lautaro Martínez | Argentina | FW | Inter Milan | 89.21 | Starter | 5.97 |
| 21 | Romelu Lukaku | Belgium | FW | Napoli | 88.70 | Starter | 9.98 |
| 22 | Alphonso Davies | Canada | DF | Bayern Munich | 88.51 | Starter | 12.61 |
| 23 | Marquinhos | Brazil | DF | Paris Saint-Germain | 88.37 | Starter | 10.61 |
| 24 | Mikel Merino | Spain | MF | Arsenal | 88.37 | Starter | 1.50 |
| 25 | Mikel Oyarzabal | Spain | FW | Real Sociedad | 88.28 | Starter | 1.50 |

## Source

- Squad names/positions/clubs/caps/goals: https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads
- Rating methodology: local Player Impact Rating v2.1 heuristic built for this project.