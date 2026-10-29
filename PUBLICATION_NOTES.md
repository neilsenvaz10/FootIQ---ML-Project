# FootIQ clean publication snapshot — 29 October 2026

This tree was prepared separately from the maintainer's original project. No original Git history, production database, backup, credentials, installed environments or dependency caches are part of the publication.

## Current scope and reconstruction

The active application supports Premier League, La Liga, Bundesliga, Serie A, Ligue 1 and UEFA Champions League. UCL retains “Not validated (indicative only)”. Domestic Monte Carlo remains points-only. Only Bundesliga and La Liga expose the supported position bounds; no scoreline/final-position method is enabled by this migration.

Run `scripts/rebuild_current_state.py <new-private-folder> published` for the default public-evidence reconstruction, or explicitly choose `snapshot` for the optional attested reconstruction. The last prior Phase 4.38 verification reported 17,300/17,303 six-competition rows reproduced in attested mode, 80 attested results plus 31 attested fixture-date corrections, three unsupported results omitted, and all five domestic simulators usable (Serie A/Ligue 1 provisional). Those prior runtime results are not presented as a new full-suite execution during this publication preflight. Attestation is not independent public verification.

## Additional exclusions in this publication

World Bank raw indicator payloads and their processed macro table are omitted because indicator-specific rights were not confirmed. Archived international tactical rating tables and downstream predictions, simulation reports and workbooks tied to StatsBomb aggregates are also omitted while their redistribution status remains unresolved. Two archived international PDFs are conservatively withheld pending document-specific review. No excluded file is needed by the active six-competition club-model runtime/rebuild path. Historic international examples and older audit commands may reference these withheld files and cannot be reproduced from this tree alone.

The exact withheld paths/reasons are in the external preflight audit's `additional_exclusions.csv`. The original Phase 4.38 excluded set remains excluded. Code and historical reports that merely discuss a source or record its hash are not that source's raw data. Prior audit reports describe their original trees and are historical evidence, not a promise that every named file is in this publication.

CC0, CC BY-SA 4.0 and ODbL attribution is retained in `DATA_LICENSES.md` and row-level provenance. No mixed SQLite database or new source-code licence is supplied. The original public repository's historical exposure is unaffected by creating this repository.

## Git workflow

Destination: https://github.com/neilsenvaz10/FootIQ---ML-Project.git

The destination already has a README-only commit on `main`. Publication is prepared as an independent `release/footiq-publication` branch. Its approved future push creates that branch and leaves `main` unchanged. The original project's remotes and Git history are unchanged. No commit or push is authorised until the user approves the final preflight.
