# 06 Readiness by source (2026-10-21)

| Source | Permissions | Code + offline tests | Offline validation vs openfootball | Status |
|---|---|---|---|---|
| **OpenLigaDB** (Bundesliga 2026 only) | Licence ODbL 1.0 and API terms read in full; attribution, fair-use, UA-contact and rate rules implemented | `openligadb.py`, 17-test suite incl. change-date polling, back-off, explicit result types | 36/36 exact + date agreement, 0 conflicts, recovers 18/18 missing, 306/306 UTC kickoffs, 0 unresolved identities | **READY FOR APPROVAL** of live use for the validated league once you set a contact string. Other leagues: not validated → blocked. |
| **Wikipedia** (Premier League validated; 14 other pages unverified) | Policies read; licence consequences documented, legal scope of share-alike unsettled | `wikipedia_matrix.py`, tests incl. schedule-date inheritance, rejections, revision stability | 50/50 exact, 0 conflicts, recovers 20/20 (dates inherited, flagged, no kickoff times) | **RESTRICTED**: live use blocked by missing contact; feature-store promotion blocked until you approve `02_WIKIPEDIA_LICENSING_AND_USE.md`; each further league needs a stored page fixture and validation first. |
| openfootball | CC0 | existing `e3_ingest_results.py` | reference | unchanged; no new upstream revision as of today |
| football-data.org, API-Football | not verified | none | none | deferred by decision |

## Not done / still required
* A real contact string in `config/adapters.json` (you chose to supply one; none was received). Until then every live call is refused by the code.
* Owner approval for live OpenLigaDB ingestion, for the Wikipedia option (A/B/C), and for the exact amendment text (`05`).
* Page-fixture validation of the other 14 Wikipedia leagues and OpenLigaDB's Premier League / La Liga coverage (needs live reads).
* Integration into the official logger (not touched, per instruction); the amendment lists the changes needed.
* Frozen v2 `55c1e4c5…`, matched v1 `33bd80f6…`, original v1 `067426e8…`, the evaluation protocol and its pre-registration hash are unchanged (checked in `MANIFEST.json`); no approval JSON exists; nothing staged, committed or pushed.
