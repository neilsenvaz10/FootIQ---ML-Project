# 06 Identity reconciliation plan

**Canonical identities** are the entity ids in the frozen universe (e.g. `CLUB:...`, `world/...|name`, `SRCSCOPED|...`). New sources never create entities automatically.

## Resolution ladder per (source, competition)
1. **Exact name in the same competition** from the frozen (competition, name) -> entity map (this resolved 3,168/3,168 openfootball fixtures).
2. **Normalised name** (diacritics, FC/AFC/SV/VfB... tokens, punctuation) within the competition — worked for 18/18 Bundesliga names from OpenLigaDB with no manual alias (checked in this research: 36/36 overlapping results matched by team pair and date).
3. **Reviewed alias table** (`alias_v1.csv`: source, competition, source_name, entity_id, method, reviewer, date). Seeds: openfootball `clubs` repo aliases, Wikipedia `name_XXX` template (abbreviation -> display name; for the Premier League page 20/20 names resolved after normalisation), OpenLigaDB `teamId`/`shortName`.
4. **Suggestions only:** fuzzy/token candidates are listed for review and never accepted automatically.
5. **Unknown clubs** (promoted/new): result is `unresolved`, the fixture is excluded from the primary population and listed; a new entity is created only through an approved entity-creation step.

## Rules
* Resolution is scoped by **competition and country folder**, not by name alone, so the Police FC / Vision FC collisions cannot spread: the resolver keys `world/africa/<country>|name` for those names, but the **frozen entity ids are not changed** (dataset v1.2 deferred); fixtures of those clubs stay ineligible via `eligibility_exclusions_r1.json`.
* Source-scoped (`SRCSCOPED|`) ids remain as they are (26 fixture slots today); results for them are accepted only if the same source-scoped name appears.
* Cross-source agreement is checked on the **resolved** (competition, season, home, away, ordinal) key, never on raw strings.
* Name changes or rebrands: handled by alias rows with validity dates.
* Zimbabwe: no 2026 fixtures; the 2021-22 date anomaly stays a flagged history issue.

## Acceptance thresholds before a source is used for a competition
>= 99% of the competition's fixtures and results auto-resolved by steps 1-3, 100% of the rest listed with a reviewer decision, zero entity ambiguity (one name -> two entities) inside the competition.
