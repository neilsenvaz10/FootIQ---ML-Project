# 08 Source and licence audit (generated 2026-10-20 22:32)

## Evidence inspected
* 17 cloned repositories, licence file text hashed (16 contain the CC0 1.0 Universal text; StatsBomb ships `LICENSE.pdf`, which could **not** be machine-read here). Commits and origins:
| repo | license_file | states_cc0 | commit | origin |
|---|---|---|---|---|
| austria | LICENSE.md | True | 627ba1b3ebddc5a513420239356f490bef2453ec|2026-10-01 | https://github.com/openfootball/austria.git |
| belgium | LICENSE.md | True | 1166d3c9c5725aec01e1bbeaa20f6467e39ddbb8|2026-08-09 | https://github.com/openfootball/belgium.git |
| champions-league | LICENSE.md | True | abfaeddc2ee3d14f99ecc163c9ddb46cb4d67cef|2026-07-02 | https://github.com/openfootball/champions-league.git |
| club-worldcup | LICENSE.md | True | c8793fc548718d5ac56bee7b0d15ba2cb74f0600|2026-10-20 | https://github.com/openfootball/club-worldcup.git |
| clubs | LICENSE.md | True | ae3800227c449447b3a337fc0aac79a8f02f4c8b|2025-01-03 | https://github.com/openfootball/clubs.git |
| copa-america | LICENSE.md | True | 902e4c51c282244ab924676b3bc471b4040de39a|2026-05-29 | https://github.com/openfootball/copa-america.git |
| deutschland | LICENSE.md | True | c34532ab6950aa0089ef1c736ffdb8c818c3356f|2026-09-21 | https://github.com/openfootball/deutschland.git |
| england | LICENSE.md | True | 9ee7a0c351805c99cc334478a9bf04b7d0432fec|2026-10-15 | https://github.com/openfootball/england.git |
| espana | LICENSE.md | True | 80035a93dd4920985af52aa097a54a6fb888563b|2026-10-15 | https://github.com/openfootball/espana.git |
| euro | LICENSE.md | True | 88d150a6c8db43925ea327b87e990f653c999b11|2026-06-26 | https://github.com/openfootball/euro.git |
| europe | LICENSE.md | True | 63df627f3c87ce71708f016522ea236cf74332c3|2026-10-15 | https://github.com/openfootball/europe.git |
| italy | LICENSE.md | True | 48954d163c312aa705efacb64f771267031fe6eb|2026-09-21 | https://github.com/openfootball/italy.git |
| leagues | LICENSE.md | True | 500b3eb4958e57849f93f816261149e0286e25c4|2025-12-04 | https://github.com/openfootball/leagues.git |
| players | LICENSE.md | True | 125d20f7cc06cac7e758b40df535a7695632680a|2024-06-17 | https://github.com/openfootball/players.git |
| south-america | LICENSE.md | True | f51b2dcf5e0fab9f0abd5206ab8c24a413e67277|2026-10-20 | https://github.com/openfootball/south-america.git |
| statsbomb_open_data | LICENSE.pdf | False | 4b73468fc5b0f1950f9f66fada70ad3a4f9327cb|2026-09-07 | https://github.com/statsbomb/open-data.git |
| world | LICENSE.md | True | 42df8203e73e922cdfa36104e3acee3aea1f2bc0|2026-09-23 | https://github.com/openfootball/world.git |
* Traceability of the 129,829 extended training rows: null provenance **0**, null licence **0**, null extraction date **0**. 128,101 openfootball rows point to `file:line`; the line exists for all (**0 missing**), contains both team names (**0 failures**) and a score (**0 failures**). 1,571 Wikipedia rows point to a revision id: all revisions exist in the local cache (**0 missing**) and each offset starts a football-box template (**0 failures**).
* Provenance hashes use the first 12 characters of the repository commit; every training row can be traced to a file/line or page revision.

## Licence position
| Source | Rows in extended set | Licence | Educational / ML use | Attribution | Share-alike / redistribution |
|---|---|---|---|---|---|
| openfootball | 128,258 | CC0 1.0 (file text verified) | Permitted | Not required | None |
| martj42 international results (files 01/03, not in club training) | - | CC0-1.0 (GitHub licence metadata read 2026-10-20; the repo's own file was not cloned) | Permitted | Not required | None |
| Wikipedia (English) | 1,571 (1.21%) | CC BY-SA 4.0 + GFDL | Reuse permitted under licence | **Required** (page + revision) | **Required** for adaptations; unresolved whether extracted scores are adaptations of expression or uncopyrightable facts; EU database right not assessed |
| StatsBomb Open Data (player files) | - | README terms: free for research; credit StatsBomb; LICENSE.pdf unread | Research/education only (ML terms not explicit) | Required if published | Not stated |
| Football-Data.co.uk | 0 | Private use only, no automated/AI use | **Prohibited** | - | - |

## Wikipedia-derived rows
1,571 extended rows by split {'forward_holdout': 830, 'train': 697, 'validation': 44} and competition {'UEFA Europa League': 549, 'Coupe de France': 243, 'EFL Cup': 165, 'UEFA Conference League': 153, 'Copa del Rey': 152, 'Coppa Italia': 148, 'FA Cup': 104, 'DFB-Pokal': 39, 'UEFA Champions League': 18}. They are **all confirmed-label rows**, i.e. Wikipedia supplies 90-minute evidence (goal minutes) that openfootball lacks. No domestic-league row is Wikipedia-derived, so a league-only training set is CC0-only.

## Unresolved permissions / flags
1. Share-alike scope for the 1,571 Wikipedia rows and anything derived from them (features, trained artefacts) - legal review needed before redistribution; no NOTICE/attribution file ships with the training CSV (attribution is only in the `provenance` column).
2. The Wikimedia API client sent no contact address (policy asks for one); requests were serial and rate limited.
3. StatsBomb licence PDF not read; ML-training permission unverified.
4. The 06/07 teams and competitions tables mix CC0 and StatsBomb names.
5. `raw_external/wikipedia` caches full wikitext (CC BY-SA); do not redistribute the cache without the licence notice.
