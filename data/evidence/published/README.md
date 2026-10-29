# Published evidence for the domestic importers

This folder holds the evidence that FootIQ's two domestic importers (`app/store/league_results_import.py`, `app/store/reconcile_import.py`) use in their **published-evidence mode** (`--evidence published`). It contains only values from sources that may lawfully be redistributed: **Wikipedia** (CC BY-SA 4.0), **openfootball** (CC0 1.0) and **OpenLigaDB** (ODbL 1.0). Values from football-data.co.uk, FixtureDownload and football-data.org are **not** here (see `DATA_LICENSES.md`).

| File | What it is |
|---|---|
| `published_evidence_2026-10-28.csv` | one row per decision production took on 28 Oct 2026 (71 domestic results, 104 reconciliation proposals): teams, dates, result, the values and references of the redistributable sources, the production decision, the evidence classification, confidence, uncertainty, licence and provenance |
| `PUBLISHED_EVIDENCE_MANIFEST.json` | SHA-256, row counts per classification and action, the allowed sources, what was withheld, and the SHA-256 of the local inputs the decisions came from (hashes reveal no value) |
| `NOT_REPRODUCIBLE_FROM_PUBLISHED_EVIDENCE.csv` | the 114 stored records (83 results, 31 fixture-date corrections) that a rebuild from this evidence cannot reproduce, with teams, dates and status (no scores) |

**Rule (same as the standard mode, over redistributable sources only):** a result needs the same score from at least two distinct allowed sources, and a played day or corrected date the same date from at least two. A record that does not meet it is **not applied** (`insufficient_published_evidence`); it is never accepted on a single source. In the shipped file **all 175 records are classified `insufficient_redistributable_evidence`**: the second source of every one of those decisions was a restricted provider, and the redistributable sources do not cover them (openfootball's published results end on 20 Sep 2026, OpenLigaDB covers only the Bundesliga, La Liga and a lagging Premier League feed, Wikipedia's league grids carry no dates). Consequently a published-evidence rebuild reproduces the Bundesliga, La Liga (except 6 results) and the Champions League exactly and leaves 83 domestic results and 31 Premier League date corrections out.

Rebuild: `python scripts/rebuild_current_state.py <folder> published` (default). The maintainer's exact rebuild (`... local`) needs the restricted staging files and runs only on that machine. Regenerate this folder with `python scripts/build_published_evidence.py <replay.sqlite>`.
