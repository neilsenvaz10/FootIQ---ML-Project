# 05 Team identity audit (generated 2026-10-20 22:32; nothing was merged or changed)

## Findings
* Mapping rows 6,741; status {'resolved_exact_alias': 2964, 'no_alias_match': 2308, 'no_country': 1466, 'ambiguous_multiple_clubs': 3}; duplicate keys **0**.
* Entities used in `04d`: 4,969; resolved to a canonical `CLUB:` id 1,656; **unresolved 3,313** (kept as source-scoped ids). Unresolved match sides: 98,878 of 286,110 (34.6%). Share by competition type: {'continental_club': 0.423, 'domestic_cup': 0.31, 'domestic_league': 0.345, 'global_club': 0.693, 'league_cup': 0.0}.
* Resolution rule (exact normalised alias match inside one country, `openfootball/clubs`, CC0) is name-based but curated; no similarity matching was used. Alias tables exist only for Europe, Israel and Kazakhstan, so South-American, North-American, African and Asian clubs are unresolved by construction.

## Same name, several entity ids (310 groups, 32,046 match records)
Two different situations are mixed in this list (`_evidence/identity_same_name_multiple_ids.csv`):
1. **Homonyms (correctly separate)**, e.g. `CLUB:ENG:liverpool-fc` vs `URU|Liverpool FC`; `River Plate` in ARG/PAR/URU.
2. **True splits of one club** across continental and domestic sources, e.g. `BRA|São Paulo FC` vs `south-america/brazil|São Paulo FC`, Mexican (`MEX|` vs `world/north-america|`) and US clubs. Elo/form of these clubs is split between continental and domestic ids.
Largest groups:
| nk | entity_ids | matches |
|---|---|---|
| liverpool fc | CLUB:ENG:liverpool-fc | URU|Liverpool FC | 417 |
| sao paulo fc | BRA|São Paulo FC | south-america/brazil|São Paulo FC | 400 |
| santos fc | BRA|Santos FC | south-america/brazil|Santos FC | 383 |
| cf america | MEX|CF América | world/north-america|CF América | 321 |
| uanl tigres | MEX|UANL Tigres | world/north-america|UANL Tigres | 319 |
| cf monterrey | MEX|CF Monterrey | world/north-america|CF Monterrey | 313 |
| cruz azul | MEX|Cruz Azul | world/north-america|Cruz Azul | 295 |
| ceara ce | BRA|Ceará CE | south-america/brazil|Ceará CE | 286 |
| club leon | MEX|Club León | world/north-america|Club León | 278 |
| seattle sounders | USA|Seattle Sounders | world/north-america|Seattle Sounders | 277 |

Impact: domestic league matches stay internally consistent. Continental and cup matches require both clubs `resolved`, so split clubs are *excluded* from cup / continental training rather than mis-linked. Their cross-competition history is lost (no leakage, but incomplete history).

## Possible splits of one club (candidate pairs, NOT merged): 80
| unresolved_entity | unresolved_name | resolved_entity | resolved_name | jaccard |
|---|---|---|---|---|
| URU|Nacional | Nacional | CLUB:POR:cd-nacional-madeira | CD Nacional | 1.0 |
| VEN|Zamora FC | Zamora FC | CLUB:ESP:zamora-cf | Zamora CF | 1.0 |
| PAR|Club Nacional | Club Nacional | CLUB:POR:cd-nacional-madeira | CD Nacional | 1.0 |
| ECU|Barcelona | Barcelona | CLUB:ESP:fc-barcelona | FC Barcelona | 1.0 |
| CHI|Everton | Everton | CLUB:ENG:everton-fc | Everton FC | 1.0 |
| FRA|Gazélec FC Ajaccio | Gazélec FC Ajaccio | CLUB:FRA:gfc-ajaccio | Gazélec Ajaccio | 1.0 |
| AUT|Austria Wien II | Austria Wien II | CLUB:AUT:fk-austria-wien | Austria Wien | 0.67 |
| AUT|SKN St. Pölten II | SKN St. Pölten II | CLUB:AUT:skn-st-polten | SKN St. Pölten | 0.75 |
| GER|SSV Jeddeloh II | SSV Jeddeloh II | CLUB:GER:ssv-jeddeloh | SSV Jeddeloh | 0.67 |
| ESP|Gimnàstic de Tarragona | Gimnàstic de Tarragona | CLUB:ESP:gimnastic-tarragona | Gimnàstic de Tarragona | 1.0 |
| URU|Liverpool | Liverpool | CLUB:ENG:liverpool-fc | Liverpool FC | 1.0 |
| WP:italy:Reggina 1914 | Reggina 1914 | CLUB:ITA:reggina-1914 | Reggina 1914 | 1.0 |
Some are homonyms (`URU|Liverpool` v `Liverpool FC`; `CHI|Everton` v `Everton FC`; `ECU|Barcelona` v `FC Barcelona`) and must stay separate; others (`Gazélec FC Ajaccio` / `GFC Ajaccio`, `Gimnàstic de Tarragona`, `Reggina 1914`) are the same club under a name the alias table does not list. **Manual review required.**

## Possible wrong merges (canonical ids fed by dissimilar source names): 208
Listed in `_evidence/identity_possible_wrong_merges_review.csv` for review (alias lists contain legitimate former names, so many are fine). Reserve/youth canonical entities used: 35 (kept separate from senior teams by the alias table).

## Cross-border clubs
| search | entity_ids | competitions | matches | seasons |
|---|---|---|---|---|
| AS Monaco | CLUB:MCO:as-monaco | champions-league:cl | champions-league:el | europe/france:fr1 | europe/france:frcup | 354 | 2018-19..2026-27 |
| Monaco | CLUB:MCO:as-monaco | champions-league:cl | champions-league:el | europe/france:fr1 | europe/france:frcup | 354 | 2018-19..2026-27 |
| Cardiff City | CLUB:WAL:cardiff-city-fc | england:1-premierleague | england:2-championship | england:3-league1 | england:eflcup | england:facup | 385 | 2018-19..2026-27 |
| Swansea City | CLUB:WAL:swansea-city-afc | england:2-championship | england:eflcup | england:facup | 409 | 2018-19..2026-27 |
| Wrexham | CLUB:WAL:wrexham-afc | england:2-championship | england:3-league1 | england:4-league2 | england:5-nationalleague | england:eflcup | england:facup | 387 | 2018-19..2026-27 |
| Newport County | CLUB:WAL:newport-county-afc | england:4-league2 | england:eflcup | england:facup | 380 | 2018-19..2026-27 |
| Merthyr | CLUB:WAL:merthyr-town-fc | england:facup | 1 | 2022-23..2022-23 |
| Barry Town | CLUB:WAL:barry-town-afc | europe/wales:wal1 | 65 | 2023-24..2024-25 |
| The New Saints | CLUB:WAL:the-new-saints-fc | champions-league:clq | champions-league:conf | champions-league:confq | champions-league:elq | europe/wales:wal1 | 82 | 2023-24..2025-26 |
| Bala Town | CLUB:WAL:bala-town-fc | champions-league:confq | europe/wales:wal1 | 67 | 2023-24..2024-25 |

* **AS Monaco** is a single entity `CLUB:MCO:as-monaco` across Ligue 1, the French cup, Champions League and Europa League (explicit fallback rule france -> monaco): **verified**.
* **Cardiff, Swansea, Wrexham, Newport** are single `CLUB:WAL:` entities across the English league pyramid and cups: **verified**. (Merthyr Town, Barry Town, TNS and Bala resolve consistently.)

## National teams
337 national-team names in 01; none of the 36 former-name rules produces rows under both the current and former name (0). Historic names (Czechoslovakia, Yugoslavia...) stay separate entities by design, so no history is linked across state successions.

## Effect on features
Elo / form are computed per entity id; split entities therefore carry partial histories. This is conservative (cold-start entities fail the >=5-prior-matches rule) but reduces data and can understate strength for continental participants outside Europe.
