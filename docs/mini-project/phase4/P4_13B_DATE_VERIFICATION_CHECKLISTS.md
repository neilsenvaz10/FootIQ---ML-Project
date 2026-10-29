# Date-verification checklists: 96 disputed fixtures (Phase 4.13B)

**LOCAL WORKING DOCUMENT. It contains fixture dates taken from football-data.org responses, whose storage and reuse permission is still unconfirmed: do not commit it to a public repository, zip it into a submission or share it until the provider has answered.**

Purpose: you check each fixture on the **official league site** and write the official date in the blank column. Nothing here changes any stored date; no decision is applied until you approve the decision-record design (`P4_13B_DECISION_RECORD_MIGRATION_DESIGN.md`) and a signed decision file exists.

How to read a row: *Stored date* is the pre-season schedule currently in the database (date only, no kick-off time). *Provider date* is the date and **local** kick-off time football-data.org shows (status TIMED = the provider has a confirmed time). *Second source* is OpenLigaDB's fixture date, available for the Premier League only (a user-entered feed, stale for results but its fixture dates are corroboration). *Shift* = provider minus stored. The same data as a spreadsheet: `P4_13B_DATE_VERIFICATION_SHEET.csv` (the same rows and blank columns).

Suggested spot-check (from the proposed rules): the two finished Ligue 1 matches individually; for PL 5 fixtures; for SA and FL1 10 fixtures each, including both directions of shift. Verify the **date and local kick-off time** the league publishes now, and note the page date so a later change by the league is not mistaken for an error.

Match ids: the full list with database record ids is in the CSV.

## Part 1. The two finished Ligue 1 matches (check these first, individually)

These are **played** matches. Their results are held back and are not in the database until the date is decided. Check the date, the kick-off time and the final score on ligue1.com or the club sites; record the score too.

| # | MD | Match | Stored date (openfootball) | Provider date and local time | Shift (days) | Second source (OpenLigaDB) | Provider status | **Official date (you fill in)** | **Official source / URL** | **Verdict: provider / stored / other** |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 8 | Toulouse FC v ES Troyes AC | Sat 24 Oct | Sun 25 Oct 17:15 | +1 | n/a | FINISHED | | | |
| 2 | 8 | Paris Saint-Germain FC v Olympique Lyonnais | Sun 25 Oct | Mon 26 Oct 20:30 | +1 | n/a | FINISHED | | | |

## Part 2. Premier League (PL): 31 fixtures (official site: premierleague.com (fixtures))

Evidence tier T2: two sources (provider and OpenLigaDB) agree on the new date in every row. Proposed: batch sign-off after you spot-check 5 rows.

| # | MD | Match | Stored date (openfootball) | Provider date and local time | Shift (days) | Second source (OpenLigaDB) | Provider status | **Official date (you fill in)** | **Official source / URL** | **Verdict: provider / stored / other** |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 10 | Brighton & Hove Albion FC v Brentford FC | Sat 07 Nov | Sun 08 Nov 14:00 | +1 | Sun 08 Nov | TIMED | | | |
| 4 | 10 | Crystal Palace FC v Liverpool FC | Sat 07 Nov | Sun 08 Nov 14:00 | +1 | Sun 08 Nov | TIMED | | | |
| 5 | 10 | Everton FC v Coventry City FC | Sat 07 Nov | Fri 06 Nov 20:00 | -1 | Fri 06 Nov | TIMED | | | |
| 6 | 10 | Ipswich Town FC v AFC Bournemouth | Sat 07 Nov | Sun 08 Nov 14:00 | +1 | Sun 08 Nov | TIMED | | | |
| 7 | 10 | Manchester United FC v Aston Villa FC | Sat 07 Nov | Sun 08 Nov 16:30 | +1 | Sun 08 Nov | TIMED | | | |
| 8 | 10 | Sunderland AFC v Chelsea FC | Sat 07 Nov | Sun 08 Nov 14:00 | +1 | Sun 08 Nov | TIMED | | | |
| 9 | 11 | Brentford FC v Everton FC | Sat 21 Nov | Mon 23 Nov 20:00 | +2 | Mon 23 Nov | TIMED | | | |
| 10 | 11 | Hull City AFC v Brighton & Hove Albion FC | Sat 21 Nov | Sun 22 Nov 14:00 | +1 | Sun 22 Nov | TIMED | | | |
| 11 | 11 | Liverpool FC v Manchester United FC | Sat 21 Nov | Sun 22 Nov 16:30 | +1 | Sun 22 Nov | TIMED | | | |
| 12 | 12 | Arsenal FC v Manchester City FC | Sat 28 Nov | Sun 29 Nov 16:30 | +1 | Sun 29 Nov | TIMED | | | |
| 13 | 12 | Brighton & Hove Albion FC v Newcastle United FC | Sat 28 Nov | Sun 29 Nov 14:05 | +1 | Sun 29 Nov | TIMED | | | |
| 14 | 12 | Crystal Palace FC v Hull City AFC | Sat 28 Nov | Sun 29 Nov 14:05 | +1 | Sun 29 Nov | TIMED | | | |
| 15 | 12 | Everton FC v Liverpool FC | Sat 28 Nov | Sun 29 Nov 12:00 | +1 | Sun 29 Nov | TIMED | | | |
| 16 | 12 | Fulham FC v AFC Bournemouth | Sat 28 Nov | Sun 29 Nov 14:05 | +1 | Sun 29 Nov | TIMED | | | |
| 17 | 12 | Nottingham Forest FC v Chelsea FC | Sat 28 Nov | Fri 27 Nov 20:00 | -1 | Fri 27 Nov | TIMED | | | |
| 18 | 12 | Sunderland AFC v Tottenham Hotspur FC | Sat 28 Nov | Sun 29 Nov 14:05 | +1 | Sun 29 Nov | TIMED | | | |
| 19 | 13 | Coventry City FC v Ipswich Town FC | Wed 02 Dec | Tue 01 Dec 20:00 | -1 | Tue 01 Dec | TIMED | | | |
| 20 | 13 | Tottenham Hotspur FC v Fulham FC | Wed 02 Dec | Thu 03 Dec 20:00 | +1 | Thu 03 Dec | TIMED | | | |
| 21 | 14 | Everton FC v Fulham FC | Sat 05 Dec | Sun 06 Dec 14:00 | +1 | Sun 06 Dec | TIMED | | | |
| 22 | 14 | Newcastle United FC v Sunderland AFC | Sat 05 Dec | Sun 06 Dec 14:00 | +1 | Sun 06 Dec | TIMED | | | |
| 23 | 14 | Tottenham Hotspur FC v Arsenal FC | Sat 05 Dec | Sun 06 Dec 16:30 | +1 | Sun 06 Dec | TIMED | | | |
| 24 | 15 | Arsenal FC v AFC Bournemouth | Sat 12 Dec | Sun 13 Dec 14:00 | +1 | Sun 13 Dec | TIMED | | | |
| 25 | 15 | Brighton & Hove Albion FC v Everton FC | Sat 12 Dec | Sun 13 Dec 14:00 | +1 | Sun 13 Dec | TIMED | | | |
| 26 | 15 | Coventry City FC v Aston Villa FC | Sat 12 Dec | Sun 13 Dec 16:30 | +1 | Sun 13 Dec | TIMED | | | |
| 27 | 15 | Crystal Palace FC v Manchester United FC | Sat 12 Dec | Sun 13 Dec 19:00 | +1 | Sun 13 Dec | TIMED | | | |
| 28 | 15 | Hull City AFC v Tottenham Hotspur FC | Sat 12 Dec | Mon 14 Dec 20:00 | +2 | Mon 14 Dec | TIMED | | | |
| 29 | 15 | Sunderland AFC v Nottingham Forest FC | Sat 12 Dec | Sun 13 Dec 14:00 | +1 | Sun 13 Dec | TIMED | | | |
| 30 | 16 | Arsenal FC v Manchester United FC | Sat 19 Dec | Sun 20 Dec 16:30 | +1 | Sun 20 Dec | TIMED | | | |
| 31 | 16 | Brighton & Hove Albion FC v Ipswich Town FC | Sat 19 Dec | Sun 20 Dec 14:00 | +1 | Sun 20 Dec | TIMED | | | |
| 32 | 16 | Chelsea FC v Aston Villa FC | Sat 19 Dec | Mon 21 Dec 20:00 | +2 | Mon 21 Dec | TIMED | | | |
| 33 | 16 | Sunderland AFC v Crystal Palace FC | Sat 19 Dec | Sun 20 Dec 14:00 | +1 | Sun 20 Dec | TIMED | | | |

## Part 3. Serie A (SA): 39 fixtures (official site: legaseriea.it (calendario))

Evidence tier T3: provider only. Proposed: per-league batch sign-off after you spot-check 10 rows, covering both directions of shift (the largest are -2 days).

| # | MD | Match | Stored date (openfootball) | Provider date and local time | Shift (days) | Second source (OpenLigaDB) | Provider status | **Official date (you fill in)** | **Official source / URL** | **Verdict: provider / stored / other** |
|---|---|---|---|---|---|---|---|---|---|---|
| 34 | 12 | Juventus FC v Venezia FC | Mon 23 Nov | Sun 22 Nov 12:30 | -1 | n/a | TIMED | | | |
| 35 | 13 | Cagliari Calcio v AC Milan | Sun 29 Nov | Mon 30 Nov 20:45 | +1 | n/a | TIMED | | | |
| 36 | 13 | FC Internazionale Milano v Genoa CFC | Sun 29 Nov | Sat 28 Nov 20:45 | -1 | n/a | TIMED | | | |
| 37 | 13 | Frosinone Calcio v Parma Calcio 1913 | Sun 29 Nov | Sat 28 Nov 15:00 | -1 | n/a | TIMED | | | |
| 38 | 13 | Torino FC v SS Lazio | Sun 29 Nov | Sat 28 Nov 18:00 | -1 | n/a | TIMED | | | |
| 39 | 13 | US Lecce v Atalanta BC | Sun 29 Nov | Mon 30 Nov 18:30 | +1 | n/a | TIMED | | | |
| 40 | 13 | Venezia FC v Bologna FC 1909 | Sun 29 Nov | Fri 27 Nov 20:45 | -2 | n/a | TIMED | | | |
| 41 | 14 | AC Monza v Como 1907 | Sun 06 Dec | Sat 05 Dec 15:00 | -1 | n/a | TIMED | | | |
| 42 | 14 | ACF Fiorentina v Cagliari Calcio | Sun 06 Dec | Mon 07 Dec 20:45 | +1 | n/a | TIMED | | | |
| 43 | 14 | Bologna FC 1909 v AS Roma | Sun 06 Dec | Fri 04 Dec 20:45 | -2 | n/a | TIMED | | | |
| 44 | 14 | Frosinone Calcio v FC Internazionale Milano | Sun 06 Dec | Sat 05 Dec 18:00 | -1 | n/a | TIMED | | | |
| 45 | 14 | SSC Napoli v US Lecce | Sun 06 Dec | Sat 05 Dec 20:45 | -1 | n/a | TIMED | | | |
| 46 | 14 | Venezia FC v US Sassuolo Calcio | Sun 06 Dec | Mon 07 Dec 18:30 | +1 | n/a | TIMED | | | |
| 47 | 15 | Atalanta BC v Genoa CFC | Sun 13 Dec | Mon 14 Dec 18:30 | +1 | n/a | TIMED | | | |
| 48 | 15 | Cagliari Calcio v Venezia FC | Sun 13 Dec | Sat 12 Dec 15:00 | -1 | n/a | TIMED | | | |
| 49 | 15 | Como 1907 v Bologna FC 1909 | Sun 13 Dec | Sat 12 Dec 20:45 | -1 | n/a | TIMED | | | |
| 50 | 15 | Juventus FC v AC Monza | Sun 13 Dec | Mon 14 Dec 20:45 | +1 | n/a | TIMED | | | |
| 51 | 15 | US Lecce v US Sassuolo Calcio | Sun 13 Dec | Sat 12 Dec 18:00 | -1 | n/a | TIMED | | | |
| 52 | 15 | Udinese Calcio v Frosinone Calcio | Sun 13 Dec | Fri 11 Dec 20:45 | -2 | n/a | TIMED | | | |
| 53 | 16 | AC Milan v Como 1907 | Sun 20 Dec | Sat 19 Dec 18:00 | -1 | n/a | TIMED | | | |
| 54 | 16 | AS Roma v Juventus FC | Sun 20 Dec | Sat 19 Dec 20:45 | -1 | n/a | TIMED | | | |
| 55 | 16 | Frosinone Calcio v SS Lazio | Sun 20 Dec | Fri 18 Dec 18:30 | -2 | n/a | TIMED | | | |
| 56 | 16 | US Lecce v FC Internazionale Milano | Sun 20 Dec | Fri 18 Dec 20:45 | -2 | n/a | TIMED | | | |
| 57 | 16 | US Sassuolo Calcio v Parma Calcio 1913 | Sun 20 Dec | Sat 19 Dec 15:00 | -1 | n/a | TIMED | | | |
| 58 | 17 | AC Monza v AC Milan | Sun 03 Jan | Sat 02 Jan 20:45 | -1 | n/a | TIMED | | | |
| 59 | 17 | ACF Fiorentina v SS Lazio | Sun 03 Jan | Sat 02 Jan 15:00 | -1 | n/a | TIMED | | | |
| 60 | 17 | AS Roma v Frosinone Calcio | Sun 03 Jan | Sat 02 Jan 18:00 | -1 | n/a | TIMED | | | |
| 61 | 17 | Cagliari Calcio v Genoa CFC | Sun 03 Jan | Sat 02 Jan 12:30 | -1 | n/a | TIMED | | | |
| 62 | 17 | Torino FC v Venezia FC | Sun 03 Jan | Sat 02 Jan 15:00 | -1 | n/a | TIMED | | | |
| 63 | 18 | AC Milan v ACF Fiorentina | Wed 06 Jan | Tue 05 Jan 20:45 | -1 | n/a | TIMED | | | |
| 64 | 18 | Genoa CFC v AC Monza | Wed 06 Jan | Tue 05 Jan 18:30 | -1 | n/a | TIMED | | | |
| 65 | 18 | SSC Napoli v Cagliari Calcio | Wed 06 Jan | Thu 07 Jan 20:45 | +1 | n/a | TIMED | | | |
| 66 | 18 | US Sassuolo Calcio v Udinese Calcio | Wed 06 Jan | Thu 07 Jan 18:30 | +1 | n/a | TIMED | | | |
| 67 | 18 | Venezia FC v AS Roma | Wed 06 Jan | Tue 05 Jan 18:30 | -1 | n/a | TIMED | | | |
| 68 | 19 | AC Monza v Frosinone Calcio | Sun 10 Jan | Sat 09 Jan 15:00 | -1 | n/a | TIMED | | | |
| 69 | 19 | AS Roma v AC Milan | Sun 10 Jan | Sat 09 Jan 18:00 | -1 | n/a | TIMED | | | |
| 70 | 19 | Bologna FC 1909 v Genoa CFC | Sun 10 Jan | Sat 09 Jan 20:45 | -1 | n/a | TIMED | | | |
| 71 | 19 | Cagliari Calcio v US Sassuolo Calcio | Sun 10 Jan | Mon 11 Jan 18:30 | +1 | n/a | TIMED | | | |
| 72 | 19 | Udinese Calcio v SSC Napoli | Sun 10 Jan | Mon 11 Jan 20:45 | +1 | n/a | TIMED | | | |

## Part 4. Ligue 1 (FL1): 24 fixtures (official site: ligue1.com (calendrier))

Evidence tier T3: provider only (24 fixtures; the 2 finished ones are in Part 1). Proposed: batch sign-off after you spot-check 10 rows, both directions.

| # | MD | Match | Stored date (openfootball) | Provider date and local time | Shift (days) | Second source (OpenLigaDB) | Provider status | **Official date (you fill in)** | **Official source / URL** | **Verdict: provider / stored / other** |
|---|---|---|---|---|---|---|---|---|---|---|
| 73 | 9 | FC Lorient v Stade Brestois 29 | Sat 31 Oct | Mon 02 Nov 20:45 | +2 | n/a | TIMED | | | |
| 74 | 9 | OGC Nice v Stade Rennais FC 1901 | Sat 31 Oct | Fri 30 Oct 19:00 | -1 | n/a | TIMED | | | |
| 75 | 9 | Olympique Lyonnais v Angers SCO | Sat 31 Oct | Sun 01 Nov 17:15 | +1 | n/a | TIMED | | | |
| 76 | 13 | ES Troyes AC v Olympique Lyonnais | Sat 05 Dec | Sun 06 Dec 15:00 | +1 | n/a | TIMED | | | |
| 77 | 13 | Olympique de Marseille v OGC Nice | Sat 05 Dec | Sun 06 Dec 20:45 | +1 | n/a | TIMED | | | |
| 78 | 13 | Stade Rennais FC 1901 v Stade Brestois 29 | Sat 05 Dec | Sun 06 Dec 17:15 | +1 | n/a | TIMED | | | |
| 79 | 13 | Toulouse FC v Paris Saint-Germain FC | Sat 05 Dec | Fri 04 Dec 20:45 | -1 | n/a | TIMED | | | |
| 80 | 14 | AJ Auxerre v Toulouse FC | Sat 12 Dec | Fri 11 Dec 20:45 | -1 | n/a | TIMED | | | |
| 81 | 14 | FC Lorient v Lille OSC | Sat 12 Dec | Sun 13 Dec 15:00 | +1 | n/a | TIMED | | | |
| 82 | 14 | Stade Rennais FC 1901 v AS Monaco FC | Sat 12 Dec | Sun 13 Dec 17:15 | +1 | n/a | TIMED | | | |
| 83 | 15 | Le Mans FC v Olympique Lyonnais | Sat 02 Jan | Sun 03 Jan 15:00 | +1 | n/a | TIMED | | | |
| 84 | 15 | Lille OSC v RC Strasbourg Alsace | Sat 02 Jan | Sun 03 Jan 17:15 | +1 | n/a | TIMED | | | |
| 85 | 16 | AS Monaco FC v Stade Brestois 29 | Sat 16 Jan | Sun 17 Jan 17:15 | +1 | n/a | TIMED | | | |
| 86 | 16 | Olympique Lyonnais v FC Lorient | Sat 16 Jan | Sun 17 Jan 20:45 | +1 | n/a | TIMED | | | |
| 87 | 16 | Olympique de Marseille v Lille OSC | Sat 16 Jan | Fri 15 Jan 20:45 | -1 | n/a | TIMED | | | |
| 88 | 16 | Paris FC v Toulouse FC | Sat 16 Jan | Sun 17 Jan 15:00 | +1 | n/a | TIMED | | | |
| 89 | 17 | ES Troyes AC v AS Monaco FC | Sat 23 Jan | Fri 22 Jan 20:45 | -1 | n/a | TIMED | | | |
| 90 | 17 | FC Lorient v Olympique de Marseille | Sat 23 Jan | Sun 24 Jan 17:15 | +1 | n/a | TIMED | | | |
| 91 | 17 | Le Havre AC v Stade Rennais FC 1901 | Sat 23 Jan | Sun 24 Jan 15:00 | +1 | n/a | TIMED | | | |
| 92 | 17 | RC Strasbourg Alsace v Olympique Lyonnais | Sat 23 Jan | Sun 24 Jan 20:45 | +1 | n/a | TIMED | | | |
| 93 | 18 | Olympique Lyonnais v Lille OSC | Sat 30 Jan | Sun 31 Jan 20:45 | +1 | n/a | TIMED | | | |
| 94 | 18 | Olympique de Marseille v ES Troyes AC | Sat 30 Jan | Sun 31 Jan 17:15 | +1 | n/a | TIMED | | | |
| 95 | 18 | Stade Brestois 29 v RC Strasbourg Alsace | Sat 30 Jan | Fri 29 Jan 20:45 | -1 | n/a | TIMED | | | |
| 96 | 18 | Stade Rennais FC 1901 v FC Lorient | Sat 30 Jan | Sun 31 Jan 15:00 | +1 | n/a | TIMED | | | |

## Totals

Part 1: 2 · PL: 31 · SA: 39 · FL1 timed: 24 · **all: 96**.
