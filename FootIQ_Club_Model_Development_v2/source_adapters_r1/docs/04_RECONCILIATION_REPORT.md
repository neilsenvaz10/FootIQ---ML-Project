# 04 Reconciliation report (offline, stored snapshots, 2026-10-21)

Run: `run_offline_reconciliation.py`; tables in `reports/`; summary `reports/reconciliation_summary.json`. Frozen openfootball universe read-only. No conflict was resolved by the code (none occurred).

| Measure | OpenLigaDB — Bundesliga 2026-27 | Wikipedia — Premier League 2026-27 (rev 1381300885) |
|---|---|---|
| Source records | 306 (54 completed, 252 upcoming) | 70 scored cells (+27 non-score cells, all link text "a", rejected) |
| Overlapping matches with openfootball (checked) | 36 | 50 |
| **Exact score agreements** | **36 / 36** | **50 / 50** |
| Conflicts | 0 | 0 |
| Date agreement | 36 / 36 (UTC date = openfootball date) | 50 / 50, but dates are inherited from the openfootball schedule, so this is not independent evidence |
| **Newly recovered results** (missing in openfootball) | **18 / 18** | **20 / 20** (dates inherited, flagged) |
| Results not in openfootball at all | 0 | 0 |
| Ambiguous fixtures | 0 | 0 |
| Unresolved team identities | 0 | 0 |
| Records without a source-stated kickoff time | 0 / 306 (UTC for all) | 70 / 70 (matrix has no times; none invented) |
| Regulation-time label | 54/54 explicit `After90Minutes` | league match, clean score; label eligibility withheld until the amendment's checks |
| Latest completed match | 2026-10-18 (source stamp 2026-10-18T19:23:40) | 2026-10-19 (page "update" date; revision 2026-10-21T12:50Z) |
| Freshness vs 2026-10-21 | 3 days | 2 days |

Other findings
* openfootball's own schedule carries a local kickoff time for only 17.6% of upcoming fixtures (no time zone); OpenLigaDB has UTC for all Bundesliga fixtures.
* Competition coverage (`reports/COMPETITION_COVERAGE.csv`): of the 15 in-season leagues, OpenLigaDB is validated for 1 (Bundesliga) and offered on the site for 2 more (Premier League, La Liga — not validated); the Wikipedia parser is validated offline for 1 (Premier League); the other 14 Wikipedia pages exist and were edited 2026-10-14..21, but their wikitext was not fetched (no contact configured), so their template style is **unverified** and the adapter will refuse to parse an unknown style.
* The cross-check OpenLigaDB vs Wikipedia for the same league (Bundesliga) was not possible for the same reason.
* Missing results still unrecovered in the 15 leagues: 271 − 18 (OpenLigaDB) − 20 (Wikipedia PL, dates inherited) = 233 until more pages are validated.
