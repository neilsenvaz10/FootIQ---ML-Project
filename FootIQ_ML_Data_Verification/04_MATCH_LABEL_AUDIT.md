# 04 Match-label audit - 90-minute 1X2 (generated 2026-10-20 22:32)

Target: result after 90 minutes plus stoppage time, excluding extra time and shoot-outs.

## 1. Strict / extended consistency
* Strict rows 125,858; extended 129,829; strict is a subset of extended: **True**; the 3,971 extra rows are all `inferred_no_marker`: **True**.
* Label status inside strict: {'confirmed': 125858}. Inside extended: {'confirmed': 125858, 'inferred_no_marker': 3971}. **No inferred label is present in the strict file.**
* Independent re-derivation of the 1X2 outcome from the score columns reproduced every label: mismatches **0**; outcomes without a label status **0**; label statuses without outcome **0**.

## 2. Raw-source verification of the label classes
* `inferred_no_marker` openfootball rows checked against the original source line: 7,873 rows, containing an `a.e.t.` or `pen.` marker: **0** (the inference rule - "no marker, therefore decided in 90 minutes" - is applied correctly; it is still an inference).
* Confirmed knockout rows resting on a source bracket (1,553 rows): rows whose raw line lacks the marker or the two-value bracket: **0**.
* Wikipedia-derived confirmed rows (2,791): regulation score recomputed from the stored goal minutes (<= 90') : mismatches **0**.
* Strict knockout rows: 2,287; basis: {'derived_from_goal_minutes': 1042, 'confirmed_by_wikipedia_goal_minutes': 745, 'source_bracket_regulation_score_with_aet_marker': 487, 'goalless_no_extra_time_flag': 11, 'league_or_group_phase_no_extra_time_possible': 2}. Strict rows with unknown regulation score outside league/league-phase matches: **0**.

## 3. Extra time and penalties
* Strict rows with extra time played: 624; of these 240 have regulation = final (goalless extra time) and 106 have a non-draw 90-minute result (second legs where the aggregate, not the leg, was tied).
* Strict rows with a penalty shoot-out: 419; 90-minute outcome is the regulation result, never the shoot-out winner (0 rows labelled with the shoot-out winner); 49 have a non-draw 90-minute result (same second-leg / aggregate situation: e.g. EFL Cup semi-final, Liga MX and MLS two-legged playoffs). These cannot be proved from the rows alone because the aggregate of the tie is not stored: **unverified, probably legitimate**.
* Awarded results (202) are labelled `unknown`; abandoned matches (3) are `not_completed`; neither is in the training files.

## 4. Selection bias introduced by the label filter
| phase | set | n | labelled | draw_rate | home_rate |
|---|---|---|---|---|---|
| league | all_results | 127791 | 127610 | 0.2631 | 0.4436 |
| league | strict | 121523 | 121523 | 0.2631 | 0.4433 |
| league | extended | 121523 | 121523 | 0.2631 | 0.4433 |
| league_phase | all_results | 3060 | 3058 | 0.2233 | 0.4797 |
| league_phase | strict | 1891 | 1891 | 0.2115 | 0.4765 |
| league_phase | extended | 1891 | 1891 | 0.2115 | 0.4765 |
| knockout | all_results | 12204 | 11641 | 0.1962 | 0.4102 |
| knockout | strict | 2287 | 2287 | 0.307 | 0.3861 |
| knockout | extended | 6258 | 6258 | 0.2066 | 0.4369 |

The strict knockout sample (draw rate 30.7%) is **not representative** of all knockout results (19.6%) or of the extended sample (20.7%): knockout rows qualify as `confirmed` mainly because the source printed an extra-time / penalty bracket - i.e. the match was level after 90 minutes - or because Wikipedia goal minutes were available, while plain-score knockouts are `inferred` and left out. That is selection on the target (draws over-represented). Strict knockouts are only 2,287 of 125,858 rows (1.8%), so a league-only model is unaffected; any cup / continental model trained on the strict set would be biased towards draws. Knockout matches whose regulation score cannot be verified at all (563 results, 374 penalty-decided) are excluded from both sets.

## 5. Breakdown by competition and season
Full table: `_evidence/label_breakdown_by_competition_season.csv` (confirmed / inferred / unknown / not_completed per competition-season).

## 6. Reproducible manual sample (36 knockout matches, seed 20261020)
Each row is printed with its raw source line (openfootball) so it can be read against the labels: `_evidence/label_manual_sample.csv`. First rows:
| group | competition | season | date | home | away | final_excl_pens | regulation | pens | label_status | outcome90 | raw_source_line |
|---|---|---|---|---|---|---|---|---|---|---|---|
| penalties | Coupe de France | 2019-20 | 2020-01-05 | Trélissac FC | Olympique de Marseille | 1.0-1.0 | 1.0-1.0 | 2.0-4.0 | confirmed | D |  |
| penalties | UEFA Conference League (qualifying) | 2024-25 | 2024-07-31 | FK Mornar | FK Radnički 1923 | 2.0-1.0 | 2.0-1.0 | 4.0-3.0 | confirmed | H | 20:45  FK Mornar (MNE)         v FK Radnički 1923 (SRB)   4-3 pen. 2-1 a.e.t. (2-1, 1-0) |
| penalties | FA Cup | 2020-21 | 2021-01-10 | Newport County | Brighton & Hove Albion | 1.0-1.0 | 1.0-1.0 | 3.0-4.0 | confirmed | D | 19:45  Newport County          v Brighton & Hove Albion   3-4 pen. 1-1 a.e.t. (1-1, 0-0) |
| penalties | FA Cup | 2023-24 | 2024-02-07 | Nottingham Forest | Bristol City | 1.0-1.0 | 1.0-1.0 | 5.0-3.0 | confirmed | D | 19:45  Nottingham Forest       v Bristol City             5-3 pen. 1-1 a.e.t. (1-1, 1-1) |
| penalties | French Coupe de France | 2024-25 | 2024-11-17 | FC Hettange Grande | Luneville | 3.0-3.0 | 3.0-3.0 | 2.0-3.0 | unknown |  | 14:00  FC Hettange Grande      v Luneville                2-3 pen. (3-3, 1-2) |
| penalties | Coupe de France | 2021-22 | 2021-11-13 | Les Herbiers VF | Olympique Saumur FC | 1.0-1.0 | 1.0-1.0 | 9.0-8.0 | confirmed | D |  |
| penalties | Coupe de France | 2020-21 | 2021-02-06 | US Orléans | Bourges 18 | 2.0-2.0 | 2.0-2.0 | 6.0-5.0 | confirmed | D |  |
| penalties | Copa Libertadores | 2024 | 2024-02-13 | Defensor SC | Academia Puerto Cabello | 1.0-0.0 | 1.0-0.0 | 2.0-4.0 | unknown |  | 21:30  Defensor SC (URU)       v Academia Puerto Cabello (VEN)  2-4 pen. (1-0, 1-0) |
| penalties | UEFA Conference League | 2023-24 | 2024-04-18 | Fenerbahçe | Olympiakos Piraeus | 1.0-0.0 | 1.0-0.0 | 2.0-3.0 | confirmed | H | Fenerbahçe (TUR)        v Olympiakos Piraeus (GRE)  2-3 pen. 1-0 a.e.t. (1-0, 1-0) |
| penalties | Copa del Rey | 2021-22 | 2021-12-01 | Linares Deportivo | Gimnàstic de Tarragona | 0.0-0.0 | 0.0-0.0 | 6.0-5.0 | confirmed | D | Linares Deportivo        6-5 pen. 0-0 a.e.t. (0-0)  Gimnàstic de Tarragona |
| penalties | CAF Champions League | 2024-25 | 2024-09-20 | CR Bélouizdad | AS Douanes | 1.0-0.0 | 1.0-0.0 | 4.0-3.0 | unknown |  | 20:00  CR Bélouizdad (ALG)     v AS Douanes (BFA)         4-3 pen. (1-0, 1-0) |
| penalties | FA Cup | 2024-25 | 2025-01-11 | Coventry City | Sheffield Wednesday | 1.0-1.0 | 1.0-1.0 | 4.0-3.0 | confirmed | D | 18:00  Coventry City           v Sheffield Wednesday      4-3 pen. 1-1 a.e.t. (1-1, 1-0) |
| extra_time_no_pens | FA Cup | 2019-20 | 2020-06-27 | Norwich City | Manchester United | 1.0-2.0 | 1.0-1.0 | nan-nan | confirmed | D | 17:30  Norwich City            v Manchester United        1-2 a.e.t. (1-1, 0-0) |
| extra_time_no_pens | FA Cup | 2023-24 | 2024-02-27 | AFC Bournemouth | Leicester City | 0.0-1.0 | nan-nan | nan-nan | unknown |  | 19:30  AFC Bournemouth         v Leicester City           0-1 a.e.t. (0-0) |
| extra_time_no_pens | Copa del Rey | 2019-20 | 2020-01-29 | CD Badajoz | Granada CF | 2.0-3.0 | 2.0-2.0 | nan-nan | confirmed | D |  |
| extra_time_no_pens | DFB-Pokal | 2021-22 | 2021-08-08 | Hansa Rostock | 1. FC Heidenheim 1846 | 3.0-2.0 | 1.0-1.0 | nan-nan | confirmed | D | Hansa Rostock            3-2 a.e.t. (1-1, 0-1)  1. FC Heidenheim 1846 |
| extra_time_no_pens | DFB-Pokal | 2022-23 | 2022-07-31 | 1. FC Kaiserslautern | SC Freiburg | 1.0-2.0 | 1.0-1.0 | nan-nan | confirmed | D | 1. FC Kaiserslautern     1-2 a.e.t. (1-1, 1-0)  SC Freiburg |
| extra_time_no_pens | Türkiye Kupasi | 2024-25 | 2024-12-03 | Bandırmaspor | Karacabey Belediyespor | 2.0-3.0 | 2.0-2.0 | nan-nan | confirmed | D | 13:30  Bandırmaspor            v Karacabey Belediyespor   2-3 a.e.t. (2-2, 0-1) |

## 7. International dataset
`01_Historical_International_Matches.csv` has only an extra-time-inclusive score (`full-time score including extra time, excluding penalty shootout; regulation/extra-time split not provided`), no regulation-time column ([]) and 688 shoot-out matches. Tournament knockouts therefore cannot be given a verified 90-minute label: **international 90-minute labels are unverifiable**.
