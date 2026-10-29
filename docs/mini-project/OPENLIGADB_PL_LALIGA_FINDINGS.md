# OpenLigaDB investigation: Premier League and La Liga 2026-27

Date: 2026-10-25. Read-only. **No result was imported**; the production SQLite store was opened `mode=ro`. Nothing is staged, committed or pushed. Live access (`config/sync.json`, `live_enabled`) is still **false**; the investigation enabled it programmatically for this one run only.

Reproduce the analysis offline: `python app/store/investigate_openligadb.py --analyse` (reads the saved snapshots, no network). Machine-readable output: `data/snapshots/investigation/findings.json`.

## 1. Pre-flight (shown and checked before any request)

| Item | Value |
|---|---|
| Host | `api.openligadb.de` (HTTPS only) |
| Endpoints approved | `/getavailableleagues/2026`, `/getmatchdata/pl/2026`, `/getmatchdata/pl1/2026`, `/getmatchdata/la1/2026`; reserve `/getresulttypes` (only if an unseen result kind appeared) |
| Cap | 5 requests; an allow-list wrapper refused any other host, path or a sixth request |
| Rate limit | at least 3 s between requests plus 0-1.5 s jitter; documented limit 60/min/IP |
| Contact | configured in git-ignored `config/contact.local`, valid, never printed |
| Licence | ODbL 1.0, attribution text recorded with every snapshot |

## 2. Request ledger (`data/snapshots/investigation/request_ledger.jsonl`)

4 requests, all HTTP 200, no retries. The reserve request was not needed.

| UTC | Endpoint | Bytes | sha256 |
|---|---|---|---|
| 09:06:53 | `/getavailableleagues/2026` | 11,996 | `e9d62c3b0e62f87b26080a481ddb67ad89e5724d71fcfaf4f1e11ba422f2e73f` |
| 09:07:08 | `/getmatchdata/pl/2026` | 942,711 | `5bc7f2def9f9725461afae05ae8cc04038122291b3e6991bb7c678a0963bac9d` |
| 09:07:09 | `/getmatchdata/pl1/2026` | 2 (`[]`) | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| 09:07:13 | `/getmatchdata/la1/2026` | 449,114 | `a0fb7b7bde9a6ebcb6616df7a77407fc3cb7ff2c6f427280595e270ca5fbbae0` |

Response headers for every request are in `data/snapshots/investigation/run_summary.json`.

## 3. Which Premier League identifier is authoritative

* **`pl`** ("Premier League 2026/2027", id 5996): 380 fixtures, 20 teams, 38 matchdays of 10, every team plays 38, no duplicate pairings, 380 of 380 with a UTC kickoff. **Authoritative.**
* **`pl1`** ("Permier League England", id 5993, the typo is the source's): returns an empty list for 2026. Not usable.
* The two share no fixtures (380 only in `pl`, 0 only in `pl1`).

## 4. Comparison with the existing data

"Strict" means only exact, normalised or alias team-name matches (no guessing). "With suggested aliases" assumes each unresolved name is its single best suggestion, pending your review; this was a what-if only and no alias was written.

| Measure | Premier League (`pl`) | La Liga (`la1`) |
|---|---|---|
| Fixtures in source / store | 380 / 380 | 380 / 380 |
| Teams resolved strictly | 19 of 20 | 16 of 20 |
| Fixtures matched, strict / with suggested aliases | 342 / 380 | 240 / 380 |
| Matchday number agreement | 380 of 380 | 380 of 380 |
| Date agreement (with aliases) | 349 of 380; 31 differ by 1-2 days | 356 of 380; 24 differ |
| Completed in source | 59 (one unusable, see below) | 94 |
| Completed in store | 50 | 69 |
| Score agreement where both completed | 48 agree, **1 conflict** | **69 of 69 agree** |
| Store rows awaiting a result that the source has (recoverable in principle) | 10 of 20 | 20 (one other awaiting row stays missing) |
| Completed in source, store date not yet reached | 0 | 5 (store date is a day later than the source) |
| Kickoff UTC available | 380 of 380 | 380 of 380 |
| Latest completed fixture | 2026-10-12 | 2026-10-24 |
| Source `lastUpdate` range | to 2026-10-20 04:16 | to 2026-10-25 10:01 |
| Result kinds seen | HalfTime, After90Minutes only | HalfTime, After90Minutes only |
| Result labelled 90-minute for every completed match | yes (59 of 59 explicit) | yes (94 of 94) |

### Conflicting scores and unusable records
* **AFC Bournemouth v Brentford, 2026-09-12:** source 2-1, store 2-2 (store origin: `openfootball`). Nothing here says which is right. It would need a second independent source; the store row must not be overwritten silently.
* **Aston Villa v Nottingham Forest, 2026-09-12:** the source holds five half-time and four full-time result rows with contradictory scores (1-2, 0-0, 0-0). The adapter correctly classifies this as `completed_unclassified_score` and would not ingest it. The store has a score for it, so no recovery is lost.

### Team-name mapping issues (all would need your review before any alias is written)
| Source name | Store name | Note |
|---|---|---|
| `Brentford F.C.` | `Brentford FC` | not resolved by exact or normalised matching; one suggestion is wrong (Arsenal FC), so it must not be auto-accepted |
| `Celta Vigo` | `RC Celta de Vigo` | |
| `Deportivo A Coruña` | `RC Deportivo La Coruña` | second suggestion (Alavés) is wrong |
| `FC Villareal` (source typo) | `Villarreal CF` | second suggestion (FC Barcelona) is wrong |
| `Racing Santander` | `Real Racing Club de Santander` | |

Resolved by normalisation: `FC Arsenal`, `FC Liverpool` (Premier League); `Deportivo Alaves`, `FC Getafe`, `FC Malaga`, `FC Sevilla`, `FC Valencia` (La Liga). The source also uses German-style prefixes, so each new season needs the same review.

### Date differences
The store dates for 31 (Premier League) and 24 (La Liga) fixtures are a day or two away from the source's UTC kickoff date, mostly one day. One La Liga fixture is 233 days apart (likely a postponed or rescheduled game). The source carries a stated UTC kickoff, which the store mostly lacks, so the source is the better date reference, but this must be treated as a change to fixture dates and approved explicitly.

### Freshness
* La Liga: fresh, newest completed fixture 2026-10-24, updated today.
* Premier League: **about 13 days behind**. The newest completed fixture is 2026-10-12; 15 fixtures dated in the past have no result in the source. It is better than the store (newest result 2026-09-20) but does not close the gap.

## 5. Verification that nothing else changed

| Check | Result |
|---|---|
| Production store | row counts identical before and after (matches 223,510; sources 223,816; sync runs 5; snapshots 5; forecast runs 0; quarantine 216). The file's last write (08:51:39 UTC) is before the first investigation request (09:06:53 UTC) |
| Frozen models and sync config | sha256 of club v1 pickle and preprocessing, club v2-r1 pickle and feature contract, international v2.7 pickle, and `config/sync.json` identical to the values taken before the run |
| `live_enabled` | false |
| Staged files | none; no commit or push |
| Official prospective evaluation, evaluation protocol, unattended sync | not touched |

## 6. Recommendation

**La Liga: suitable, with conditions.** Complete 380-fixture calendar, all kickoffs in UTC, current within a day, 69 of 69 shared results agree, explicit 90-minute results. Needs four alias decisions and a decision on the 24 date differences.

**Premier League: suitable only as a partial improvement.** Use `pl` and ignore `pl1`. The data are complete and consistent in structure, but it lags about 13 days, has one score conflict and one corrupted record, and needs one alias. It would recover 10 of the 20 missing results, not all.

**Serie A and Ligue 1:** not on OpenLigaDB; still need another approved source.

Neither league should be ingested until you have reviewed the alias, date and conflict decisions above.

## 7. Separate approval request: production ingestion (not started)

If you approve, I would do the following in order, stopping after each step:

1. Add the five alias rows above to the store (a reviewed, reversible change) and extend the adapter allow-list to `pl` and `la1`, only `pl` for the Premier League.
2. Replay the **saved snapshots** into a private copy of the store with no network access and show the diff: results added, date changes, the Bournemouth conflict quarantined, Aston Villa v Forest rejected.
3. After your review of that diff, apply the same import to the production store from the saved snapshots (no new request).
4. Only if you separately approve, run one supervised live request per league (`pl`, `la1`) through the same ledger, then return `live_enabled` to false.

Decisions I need from you: (a) accept or change each alias; (b) whether source dates may replace store dates for the 55 differing fixtures; (c) how to resolve Bournemouth v Brentford (keep the store 2-2, or hold both until a second source confirms); (d) whether to proceed to step 4 at all.

No unattended synchronisation, model change, evaluation change or Phase 3 work is part of this request.
