# 09 Estimated implementation effort (one developer, working days; estimates, not commitments)

| Work package | Days | Notes |
|---|---|---|
| Staging schema, adapter interface, snapshot store, provenance, request ledger | 2 | reuses patterns from `e3_ingest_results.py` and the API-Football client ledger |
| OpenLigaDB adapter + tests | 1.5 | JSON, UTC, result types; league/season registry |
| Wikipedia adapter (matrix/template parsers for the page styles of the 15 leagues, revid handling, alias seed from `name_XXX`) | 4-6 | page styles differ (e.g. `match_ABC_DEF` cells vs other templates); highest risk item |
| Identity resolver + alias table + review report | 2-3 | most names resolve by normalisation |
| Reconciler (conflicts, agreement levels, schedule-derived dates, past-fixture list) | 3 | no silent resolution; adjudication log |
| Validation suite A1-A14 incl. 3-season history checks and replay | 3-4 | needs reading ~3 seasons of pages per league |
| Logger/protocol changes (merged-snapshot input, per-competition source status, confirmation rule, attribution) + dry-run validation | 2-3 | official logger remains untouched until approved |
| Documentation, licence review notes, runbook | 1 | |
| Coverage study of the other ~107 competitions (page discovery, formats) | 3-5 | optional second phase |
| **Total core (15 leagues)** | **~19-26 days** | about 4-5 working weeks |
| Optional football-data.org adapter | 1.5-2 | only after terms review |

Effort grows with every extra competition format; the Premier League style is verified, others are not.
