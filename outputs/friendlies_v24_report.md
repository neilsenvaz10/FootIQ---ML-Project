# International Friendlies v2.4 Test

This is an ad hoc v2.4 live-data run for Portugal-Chile and Germany-USA. It uses the same v2.3 match engine as the Road to 26 pilot, plus a small venue/weather context layer.

## Run Plan

- Use API-Football fixture feed for status, venue, and result tracking.
- Pull lineups/events/statistics only if the provider marks a match active or final.
- Pull Open-Meteo weather at match-hour coordinates.
- Apply venue edge at +1.5 power for the local/host-side context.
- Apply temperature/weather as a goal-tempo factor, not as a huge team-strength feature.
- If confirmed lineups exist, apply a capped player-impact adjustment where v2.1 player ratings match the starters.

## API Budget

- Requests counted today: 11 / 100.
- Remaining before local stop: 74.

## Picks

| Match | Status | Live score | Weather | Verdict | Confidence | Pick | Internal 1X2 | Lineup context |
|---|---|---|---|---|---|---|---|---|
| Portugal vs Chile | 1H | 0-0 | 21.4 C, factor 1.0 | No strong edge | Pass | team1_win | Portugal 0.47 / D 0.27 / Chile 0.26 | Portugal -0.20 (11/11), Chile +0.00 (0/11) |
| Germany vs USA | 1H | 0-0 | 24.3 C, factor 0.982 | No strong edge | Pass | team1_win | Germany 0.44 / D 0.28 / USA 0.28 | Germany -0.21 (11/11), USA -0.01 (9/11) |

## Weather Context

| Match | Venue | Temp C | Rain % | Wind km/h | Weather score | Note |
|---|---|---:|---:|---:|---:|---|
| Portugal vs Chile | Lisbon - Oeiras | 21.4 | 0.0 | 17.5 | 100.0 | Comfortable weather; no meaningful penalty. |
| Germany vs USA | Soldier Field | 24.3 | 5.0 | 9.3 | 95.46 | Comfortable weather; no meaningful penalty. |

## Honest Read

This is a genuine model run, but it is still not a confirmed-lineup model unless API-Football has lineups. If lineups are not available yet, player-level impact stays neutral and the model relies on team strength, recent form, venue, and weather context.

## Confirmed Starters

- Portugal (4-2-3-1): José Sá, Nélson Semedo, Rúben Dias, Renato Veiga, João Cancelo, Samú Costa, Bernardo Silva, Francisco Conceição, Bruno Fernandes, Rafael Leão, Cristiano Ronaldo
- Chile (4-4-2): Lawrence Vigouroux, Felipe Faúndez, Iván Román, Guillermo Maripán, Gabriel Suazo, Maximiliano Gutiérrez, Felipe Loyola, Vicente Pizarro, Darío Osorio, Gonzalo Tapia, Agustín Arce
- USA (4-2-3-1): Matthew Freese, Alexander Freeman, Miles Robinson, Tim Ream, Antonee Robinson, Weston McKennie, Tyler Adams, Sergiño Dest, Malik Tillman, Christian Pulišić, Folarin Balogun
- Germany (4-2-3-1): Oliver Baumann, Joshua Kimmich, Jonathan Tah, Nico Schlotterbeck, Nathaniel Brown, Felix Nmecha, Aleksandar Pavlović, Leroy Sané, Jamal Musiala, Florian Wirtz, Kai Havertz
