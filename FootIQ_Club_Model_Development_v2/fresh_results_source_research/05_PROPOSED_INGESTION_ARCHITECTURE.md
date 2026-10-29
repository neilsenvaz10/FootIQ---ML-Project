# 05 Proposed ingestion architecture (design only)

Goal: one source-independent pipeline; each provider is a small adapter; new-source data never mixes with the frozen training data.

```
 per-source Fetcher -> raw snapshot (immutable) -> Parser -> staging records
        |                                                      |
   rate limiter / UA / licence tag                      Identity resolver (versioned alias table)
                                                               |
                                                   Validator (dates, scores, status, stage)
                                                               |
                                              Reconciler (cross-source, conflicts quarantined)
                                                               |
                          merged results snapshot  +  fixtures snapshot  +  coverage report
                                                               |
                      prospective logger (unchanged interface: results universe + fixtures + past-fixture list)
```

## Source adapter contract
Each adapter implements `fetch(competition_keys) -> RawSnapshot` and `parse(RawSnapshot) -> list[StagingRecord]`. Raw snapshot = original bytes, URL, HTTP status, retrieval UTC, source revision (git commit / Wikipedia revid / API lastUpdate), sha256, licence tag, User-Agent used; stored under `snapshots/<source>/<UTC>/` and set read-only; never overwritten.

**StagingRecord:** source, source_ref (file:line / revid:cell / matchID), competition_key, season, stage, round, kickoff_utc (nullable) + `time_precision` (utc / local_unknown_tz / date_only / schedule_derived), home_raw, away_raw, status (`completed`, `upcoming`, `postponed`, `cancelled`, `abandoned`, `awarded`, `unresolved`), score_90 (home, away) and extra-time/penalty fields when present, result_type (`after90`, `after_et`, `unknown`), retrieved_utc, source_revision, licence tag, raw text.

## Sources
| Tier | Adapter | Provides | Notes |
|---|---|---|---|
| T0 | openfootball (existing `e3_ingest_results.py`) | results + schedule dates (+ local time sometimes) | CC0 reference; fetch only when `plan` shows a new commit |
| T1 | OpenLigaDB | results with UTC time and result type | one request per league-season, 1 request/min politeness |
| T2 | Wikipedia | per-pair scores from the season page's results matrix/template, standings date, revid | serial requests >= 4 s, compliant User-Agent; only pages listed in a reviewed registry |
| (T3) | football-data.org / API-Football | only after the owner has read and accepted the terms and created a free key | optional second opinion for top leagues |

## Normalisation and reconciliation
* Canonical match key: `(competition_id, season, home_entity, away_entity, ordinal)`; `ordinal` is the meeting number for the pair (1/2 in a double round robin; date used where leagues have extra meetings such as Scotland's split).
* Dates: use the source's explicit date/UTC time; Wikipedia matrix results get `schedule_derived` date from the T0 schedule and a flag; if T0 and T1 disagree on a date, the pair is quarantined for review.
* Status handling: postponed/cancelled/abandoned/awarded are kept as their own states, never turned into results; a fixture past its date without a result stays `past_date_no_result` (this keeps the logger's `club_has_unresolved_past_fixture` check honest).
* Admission to the **feature state**: a result needs one approved source with a completed 90-minute score and no disagreeing approved source. Disagreement -> `conflicts.csv`, both quarantined, the competition's later fixtures flagged until a human adjudicates in a log; **nothing is resolved silently or by majority vote.**
* Admission as an **outcome label** for evaluation: either two approved sources agree, or one source shows the same score in two snapshots/revisions at least 24 h apart with the first >= 48 h after the match (this is a protocol amendment, see report 07).
* Wikipedia safeguards: use the latest revision at least 24 h old; record revid; diff against previous revision; flag any result that changed.

## Separation and preservation
Frozen items stay read-only: `V_universe.pkl`, dataset v1.1, `_raw_sources`, the three model artifacts, the previous training snapshots. New data lives in `fresh_sources/<source>/...` and in versioned merged outputs `merged/<run_id>/{results_universe_refreshed.pkl, fixtures.csv, conflicts.csv, unresolved.csv, coverage.csv, manifest.json}` (same format the logger already reads). Every merged row carries `source_list`, `agreement_level` (single / two-source), `date_provenance` and snapshot ids.

## Operations
Manual commands only: `plan` (read-only freshness of every source), `fetch --confirm`, `parse`, `reconcile`, `report`. No scheduler. Per-source politeness limits and a request ledger (the pattern already in the API-Football client).
