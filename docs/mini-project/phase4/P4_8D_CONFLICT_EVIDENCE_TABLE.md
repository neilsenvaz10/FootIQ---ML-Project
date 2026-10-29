# Evidence needed to resolve the quarantined conflicts (nothing is resolved)

Prepared 2026-10-27 (Phase 4.8D Stage 1). All 57 items are still quarantined in production (273 quarantine rows in total, unchanged by the imports). No provider response was used to overwrite anything. Machine-readable versions: `data/supervised/phase4/p48d/score_conflicts_evidence_table.json` and `date_disagreements_evidence_table.csv` (55 rows with every field below).

## A. Score conflicts (2)

| # | Match | Stored | Source claim | Authoritative source required | Independent confirmation | Rule |
|---|---|---|---|---|---|---|
| 217 | AFC Bournemouth v Brentford FC, Premier League matchday 4, 2026-09-12 | 2–2 (openfootball, CC0) | OpenLigaDB 2–1 (half-time 0–0, updated 2026-09-12 18:52 UTC) | The Premier League's official match page / match centre for that fixture, and both clubs' official match reports | A second results provider that is neither OpenLigaDB nor openfootball | Keep 2–2 and the quarantine until a person reads the official record. If the official score is 2–1, correct this one row in a reviewed change with a backup (the outcome changes from draw to home win, which moves both teams' standings and form); if 2–2, the OpenLigaDB entry is the error |
| 218 | Aston Villa FC v Nottingham Forest FC, Premier League matchday 4, 2026-09-12 | 1–2 (openfootball, CC0) | OpenLigaDB holds several differing final scores for the match (a corrupt record, not a result) | Same as above | Same as above | Keep 1–2 and the quarantine; the source record is unusable until corrected by the provider; do not import anything from it |

## B. Fixture-date disagreements (55): `date_disagreements_evidence_table.csv`

| League | Items | Difference (source − stored) | Of which a source result is held back |
|---|---|---|---|
| Premier League | 31 | ±1–2 days | 0 |
| La Liga | 24 | mostly ±1–2 days | 5 (matchday-10 results below) |
| Together | 55 | +1: 28, −1: 19, ±2: 7, **+232: 1** | 5 |

* **Held results (La Liga, stored 2026-10-25, source 2026-10-23/24):** Atlético 1–0 Deportivo La Coruña; Alavés 1–1 Málaga; Rayo 0–3 Elche; Racing Santander 2–1 Espanyol; Valencia 1–2 Villarreal. They enter the table only after the date is settled **and** the official score equals the provider's.
* **Outlier:** Rayo Vallecano v Athletic Club (matchday 8): stored 2026-10-10, still awaiting a result; the provider now lists it for **2027-05-30** (a postponement of 232 days). This is the "1 La Liga fixture without a result since 10 Oct". Only La Liga's official calendar or a club announcement can confirm a postponement of that length; until then the stored row stays as it is and it is not predictable.

| Competition | Authoritative source required for each date | Independent confirmation | Rule |
|---|---|---|---|
| Premier League | premierleague.com official fixtures list (and the club's official fixture page for televised moves) | a second results provider | change a stored date only if the official body publishes the source's date; never because OpenLigaDB says so |
| La Liga | laliga.com official calendar (and the match sheet for a played match) | a second results provider or the club's page | same; a held result is imported only after the date is settled and the official final score equals the provider's |

## C. What does not count as evidence

A newer OpenLigaDB response; a response from a provider that copies OpenLigaDB; the age of a record; "most recent wins". Disputes can only make the application stricter (a disputed fixture is not offered for new predictions under the proposed time-zone rule), never decide the value.
