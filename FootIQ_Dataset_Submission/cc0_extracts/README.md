# CC0-only player extracts (Phase 4.37)

Row-level extracts of `04_Football_Players`, `05_Player_Match_Statistics`, `06_Teams`, `07_Competitions` and `08_Player_Team_Memberships` that contain **only rows whose recorded source is openfootball (CC0 1.0) or martj42/international_results (CC0 1.0)**.
Every row naming StatsBomb in any column was dropped (the StatsBomb Public Data User Agreement, section 1.2.1, forbids providing the data to third parties). The original tables stay on the maintainer's machine, unchanged.
`EXTRACT_MANIFEST.json` lists rows kept and dropped per table, SHA-256 of every extract and the integrity checks. Regenerate: `python scripts/build_cc0_player_extracts.py` (needs the original tables).
Credit: openfootball (github.com/openfootball) and Mart Jurisoo (github.com/martj42/international_results), both CC0 1.0; no attribution is required.
