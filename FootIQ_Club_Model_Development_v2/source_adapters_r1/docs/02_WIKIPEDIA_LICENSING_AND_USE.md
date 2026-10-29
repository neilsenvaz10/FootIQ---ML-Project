# 02 Wikipedia: licensing, attribution and redistribution obligations (for owner approval)

Status: **documentation for decision. Wikipedia-derived records are NOT promoted to the official prediction feature store.** Not legal advice.

## What the sources say (verified)
1. Wikipedia text is licensed CC BY-SA 4.0 (and GFDL).
2. Reusers must attribute, give a licence notice, indicate changes, and release **modified or added material** under CC BY-SA 4.0 or later.
3. The reuse guidance does not define "adaptation" and says nothing about databases or about factual data such as scores.
4. Automated access must follow the User-Agent, Robot and API Etiquette policies.

## Open legal question (UNKNOWN)
Whether a score extracted from a results matrix is protected expression (share-alike applies) or an uncopyrightable fact, and whether a feature table or model built from such scores is an "adaptation", is not answered by the pages read. Conservative handling is therefore designed so the answer does not matter for internal research use.

## Obligations adopted by design (conservative)
| Topic | Rule implemented / proposed |
|---|---|
| Attribution | Every Wikipedia record carries page title, revision id, revision timestamp and a stable permalink with the text "Match data adapted from English Wikipedia, '<title>', revision <revid> (<timestamp>), CC BY-SA 4.0: <permalink>". Reports and any published table must reproduce it. |
| Licence notice | The adapter writes `licence = "CC BY-SA 4.0 (+GFDL)"` on each record and snapshot metadata. |
| Indication of changes | Records state that scores were extracted from the matrix, dates were inherited from openfootball (flagged), and unparsed cells were dropped. |
| Redistribution | Raw Wikipedia snapshots and Wikipedia-derived rows are **internal only**. They are not included in any shared dataset, ZIP, API, frontend or backend output. If the owner ever publishes a dataset containing them it must be released under CC BY-SA 4.0 or later with the attribution above. |
| Separation | Stored in their own snapshot folder and staging tables; never merged into `V_universe.pkl`, dataset v1.1 or the training data. |
| Models | Frozen models were not trained on Wikipedia data. Prospective features may only use a Wikipedia-derived result after (a) owner approval of this document and the amendment, (b) a stable-revision check (>= 24 h old, same score in two revisions), (c) a clean conflict check, (d) a flag `derived_from_cc_by_sa` carried into the prediction log. |
| Sensitivity | Reports must include a run excluding all Wikipedia-derived inputs, so conclusions never depend on the unsettled licence question. |
| Alternatives | If the owner prefers zero share-alike exposure: use Wikipedia only to **confirm** results from CC0/ODbL sources (never as sole source), or not at all. |

## Decision requested
Approve one of: (A) Wikipedia as an internal-use source with the controls above, (B) confirmation-only, (C) not used. Until then: adapter available offline, feature-store promotion disabled.
