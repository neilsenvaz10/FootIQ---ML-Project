# Competition completion audit (Phase 4.16)

Status: audit and offline preparation only. No provider request, no import, no change to the running backend, `config/sync.json`, the production database, the models or the datasets (`data/miniproject/matches.csv` and every other data file were only read). No storage cleanup, no Git operation. Evidence: `data/supervised/phase4/p416/` (`audit_competitions.py`, `audit_report.json`, `domestic_e2e_check.py`, `wc2026_duplicates_proposal.py`, `wc2026_dedup_proposal.csv`, test output) and the machine-readable matrix `P4_13`-style registry `P4_16_COMPETITION_CAPABILITY_REGISTRY.csv`.

## 1. The exact competitions, and a discrepancy I need you to resolve
Your brief says five domestic and **five** international competitions. The documents do not say that:
- `docs/mini-project/MINI_PROJECT_PLAN.md` section 1 (APPROVED 2026-10-22, "fixed, no expansion") and `app/config.py` define **11**: five domestic leagues (rows 1-5) and **six** international/continental (rows 6-11).
- `PROJECT.md` (the blueprint) never lists "five international competitions". Its section 4.5 *targets* many more (World Cup, qualifiers, friendlies, Euros, Nations League, Copa America, AFCON, AFC Asian Cup, domestic cups, continental and global club events) and says they are "planned target coverage", not a fixed set. AFCON, the Asian Cup and the Euros are **not** in the approved mini-project scope and have no data in the project.

| # | Key | Competition | Group in the code |
|---|---|---|---|
| 1-5 | EPL, LALIGA, BUNDESLIGA, SERIEA, LIGUE1 | Premier League, La Liga, Bundesliga, Serie A, Ligue 1 | Domestic league |
| 6 | WC | FIFA World Cup | International (national teams) |
| 7 | UCL | UEFA Champions League | Continental club |
| 8 | UEL | UEFA Europa League | Continental club |
| 9 | UECL | UEFA Conference League | Continental club |
| 10 | UNL | UEFA Nations League | International (national teams) |
| 11 | COPA | Copa America | International (national teams) |

I audited all six, did not drop or add one, and did not substitute. **Decision for you:** keep the six; or tell me which one of them you consider out of the five (for example, if "international" means national-team competitions only, there are three: WC, UNL, COPA, and the UEFA club competitions are a separate group of three). A test now pins the 11-competition scope so it cannot change silently.

## 2. Completion matrix (historical coverage is separate from live synchronisation)
Legend: **Live now** = refreshed automatically when FootIQ starts. Latest result = newest result the application can show today.

| Competition | Historical coverage (local) | Latest local result | Cleaning and features | ML prediction | Backend API | Frontend | Live now |
|---|---|---|---|---|---|---|---|
| Bundesliga | 9 seasons 2018-19 to 2026-27; 2,484 rows (+306 fixtures in the store) | **2026-10-25** (63 played) | clean: 0 duplicates, club ids 100%, 90-min labels confirmed | Validated badge; v1 + v2-r1 + Elo; next fixture predicted | all routes 200 | table, matches hub, gameweek, analytics, predictor, home | **YES** (OpenLigaDB, startup refresh 2026-10-28 01:52Z) |
| La Liga | same; 3,109 rows | **2026-10-25** (93 played; 7 past-date without result) | clean; 24 date disagreements held | Validated; works | all 200 | all | **YES** |
| Premier League | same; 3,090 rows | 2026-10-12 (60 played; 20 past-date without result) | clean | Validated; works | all 200 | all | no |
| Serie A | same; 3,090 rows | 2026-09-20 (50 played; 33 past-date) | clean | Validated; works (today's fixture refused: kick-off unconfirmed, intended) | all 200 | all | no |
| Ligue 1 | same; 2,762 rows (2019-20 curtailed: 279/380) | 2026-09-20 (45 played; 27 past-date) | clean | Validated; works | all 200 | all | no |
| World Cup | 23 editions 1930-2026; 1,094 rows | 2026-07-18 | **defects:** 27 knockout matches stored twice (once labelled Group stage; 4 with different scores); 103 of 104 fixtures: **the final is missing**; knockout scores include extra time, so 90-minute results are not separable | international v2.7 + gate; Validated; works but ratings and form are **as of 2026-06-02** (before the tournament) | all 200; no standings (by design) | all except standings | no (static; tournament over) |
| Champions League | 9 seasons; 1,140 rows | 2026-09-10 | clean ids; 275 inferred 90-min labels | club models, **Not validated** badge, indicative only; works | all 200; no league-phase table | matches tab, predictor | no |
| Europa League | 9 seasons; 1,424 rows | 2026-09-17 | 2021-22 has 139/141; 322 inferred labels | same, Not validated | same | same | no |
| Conference League | 5 seasons 2021-22 to 2025-26; 729 rows | 2026-05-27 | 195 inferred, 3 unknown labels; **no 2026-27 rows** | same, Not validated | same | same | no |
| Nations League | 6 season labels 2018-19 to 2024-25; 658 rows | 2025-06-08 | clean; all 55 teams have a rating row; **the 2026-27 edition is absent** | international v2.7; Partially validated; ratings as of 2026-06-02 | all 200 | all except standings | no |
| Copa America | 48 editions 1916-2024; 869 rows | 2024-07-14 | clean; complete (next edition 2028) | international v2.7; Partially validated; works | all 200 | all except standings | no (none needed) |

Team identity: the five leagues and the three UEFA competitions have **0** rows without a stored club entity id. The national-team competitions identify teams by name (this is the existing design, `former_names` handled upstream): all 86 / 55 / 20 distinct names resolve to a rating row (0 missing). Match normalisation of the domestic leagues is exercised by the sync (the same reconciliation); for the other competitions it is a static CSV.

Feature pipeline: club models take features from the combined club history (all competitions), so UEFA fixtures are scoreable but outside what the models were validated on (hence the badge). The international model reads `team_elo_latest.csv` / `international_matches.csv`, which end at **2026-06-02**; the raw results file runs to 2026-06-27 and holds 72 unscored World Cup rows. Predictions for the 2026 World Cup knockouts and the 2026-27 Nations League therefore do not reflect the World Cup, and every international response says so in its notes. No retraining is needed to fix that, only a re-run of the existing data pipeline on newer results.

## 3. Domestic leagues end to end
- **Bundesliga and La Liga** (checked on the running local backend, GET only): dashboard and table (18 and 20 teams, 63 and 93 played), matches hub (counts consistent with the store), gameweeks, featured fixture (a Bundesliga match), prediction of the next scheduled fixture (three model views), sync status (startup mode, 0 scheduler threads, both leagues OK at the launch refresh). Complete.
- **Premier League, Serie A, Ligue 1**: history and all application features work on stale 2026-27 data. The football-data.org adapter is built and validated read-only (PL 20, SA 30, FL1 25 new results available; 58 of 58 clubs matched; 0 score conflicts). **Still blocked** by (1) the provider's written storage, reuse and model-training permission, and (2) 96 date disputes (31 PL, 39 SA, 26 FL1, two finished Ligue 1 matches held) that need your verification. All conflict, date, provenance and quarantine safeguards are intact and tested. Nothing was imported or activated.

## 4. International and continental: what exists, what is missing
- **Historical data:** present for all six; counts above. Gaps are listed in the registry and pinned by `tests/test_competition_coverage.py` ("known-gap registry"), so a refresh that changes one fails loudly.
- **World Cup:** (a) 27 duplicated knockout matches, a proposed clean-up is in `wc2026_dedup_proposal.csv` (keep the Knockout row; the Group-stage twin of 4 matches has a lower score, e.g. Argentina v Cape Verde 1-1 vs 3-2, which looks like the 90-minute score; **a hypothesis to verify**, not a label to import); (b) the final is absent from every local file (the repository's own validation summary says "final excluded"); I have not invented it.
- **Live updates and legality:**
  - Nations League, Copa America: no provider verified; a newer snapshot of the CC0 international-results dataset is the natural source, but fetching it needs a download you have not approved.
  - Champions League: the football-data.org free tier lists it (not requested); same permission blocker. Europa and Conference League are **not** on that free-tier list; no permitted provider is identified.
  - World Cup: finished; only the final result is missing.
- **Fixtures and tables:** the application has fixtures, gameweeks and standings only for the five leagues. International and UEFA competitions show results, form, head-to-head and predictions, with no standings or league-phase table (a feature gap, not a data error).

## 5. Offline work completed in this phase
1. `tests/test_competition_coverage.py` (19 tests): the 11-competition scope; scored rows everywhere; domestic nine seasons, no duplicates, 100% club ids and 90-minute basis; the known-gap registry (Ligue 1 2019-20, Europa 2021-22, Conference 2026-27, UEFA latest dates, Nations League and Copa latest dates, the 27 World Cup duplicates, 103 of 104 fixtures); every national team has a rating row and the rating cutoff (2026-06-02) is pinned; **a prediction for each of the 11 competitions** uses the requested competition and carries its validation badge and caveats (international: the rating-cutoff note); a team from another competition is refused; startup-only synchronisation with only Bundesliga and La Liga active, PL/SA/FL1 prepared but not approved, and no thread-starting code anywhere except the one-shot model warm-up and `sync.py` (no scheduler can be reintroduced unnoticed).
2. Fixed three tests that had gone stale (La Liga activation, startup migration, and one that read the real clock: the featured-fixture endpoint test now freezes time). No production code changed for them.
3. Read-only audit tools and the capability registry (CSV), and the World Cup duplicate proposal (not applied).

## 6. Tests
Backend and ML inference, targeted (miniproject, matches, gameweeks, featured, kick-off rules, form hints, preserved benchmark, startup/scheduler/monitoring/store, La Liga, EPL and football-data.org offline suites, and the new coverage tests): **294 passed, 4 skipped, 0 failed** (`data/supervised/phase4/p416/pytest_final.txt`). Frontend (`npx vitest run`): **347 passed, 13 skipped**. The first run of the same set had 3 failures: two stale config assertions and one test that read the real clock; all three were test fixes, none a code regression.

## 7. Proposed next steps (each needs your approval)
1. **Confirm the competition list** (six non-domestic, or which five).
2. **One download of the CC0 international-results file** (private folder, dry-run diff only first): would bring Nations League 2026-27, any missing World Cup knockout results including the final, and later friendlies; then re-run the existing feature/rating pipeline into a private copy so international predictions reflect them. No retraining; changing `data/processed` or `matches.csv` is a separate approval.
3. **World Cup clean-up** (apply the dedupe in a rebuilt private `matches.csv` after you review the 4 differing scores).
4. **UEFA club data refresh** from the CC0 openfootball repository (one download, private diff) for the October matchdays and Conference League 2026-27; and, offline, a league-phase table for the three UEFA competitions (no network needed; a provisional ranking labelled as such).
5. **PL/SA/FL1:** wait for the provider's written answer; then the decision-record migration, your verification of the 96 dates, a safe import and activation, each as its own approval.
6. **Optional UI:** a per-competition "data through" and "not live" label next to every competition, so stale coverage is never mistaken for a live feed.
