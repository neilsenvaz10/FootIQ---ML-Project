# 10 Remaining blockers and decisions

| # | Blocker | Why it matters | Needed from |
|---|---|---|---|
| 1 | **Wikipedia share-alike scope.** CC BY-SA 4.0 requires attribution and share-alike. Scores are facts, but whether rows extracted from season pages and models trained or evaluated on them carry share-alike duties is not settled here. | Legal suitability of the broadest source | Owner / legal view (prior phases treated Wikipedia-derived rows as CC BY-SA with attribution) |
| 2 | **OpenLigaDB terms.** Only the ODbL statement on the front page was read; terms/licence/privacy pages did not load usable text. ML/commercial use and attribution wording are UNKNOWN. | Cannot be used until confirmed | I can retry reading the terms or you can read them |
| 3 | **football-data.org and API-Football terms** could not be read (404 / 403). Both need accounts; creating even a free account was out of scope. | Optional second-opinion sources stay unassessed | Owner decision whether to pursue; owner to read terms / create free key |
| 4 | **Coverage unknown beyond 15 leagues.** Wikipedia page existence/format for ~107 other competitions, and OpenLigaDB for Premier League/LaLiga, not checked. | Evaluation needs 25+ competitions over 3+ months | Phase 2 study after approval |
| 5 | **Matrix has no dates/times.** Schedule-derived dates are an approximation if matches are rescheduled; OpenLigaDB gives UTC for few leagues. | Feature ordering and the 60-minute lead rule | Accept flagged schedule dates; time-zone table optional |
| 6 | **Volunteer-edited data.** Vandalism or late corrections on Wikipedia. | Wrong scores would corrupt features/labels | Revision-stability rule (>= 24 h old, two revisions) and conflict quarantine are designed, not built |
| 7 | **Protocol amendment** (confirmation rule, source list) needed before the first official batch; changes the pre-registration hash. | Keeps the evaluation honest | Owner approval |
| 8 | **Implementation not started** (~4-5 weeks core). | No fresh data until built | Owner approval to implement |
| 9 | openfootball may update by itself; if it does, the existing path (`plan` -> `fetch` -> `parse`) still works and some of the above becomes optional. | Cheap insurance | Keep running `plan` manually |
| 10 | Existing blockers unchanged: official logging not approved, dataset v1.2 deferred (Police FC / Vision FC fixtures stay ineligible, Zimbabwe flagged), `fetch` untested end to end. | | |

## Requested approvals
1. Approve implementing the OpenLigaDB adapter first (after I re-read its terms) and, in a second step, the Wikipedia matrix adapter for the 15 in-season leagues?
2. Decide on blocker 1 (share-alike) — or tell me to treat Wikipedia as confirmation-only (never the sole source for a result that enters features).
3. Approve the protocol amendment text in report 07 (B3, B5) in principle.
4. Optional: tell me whether to look into football-data.org / API-Football (needs you to read their terms and create free keys).
