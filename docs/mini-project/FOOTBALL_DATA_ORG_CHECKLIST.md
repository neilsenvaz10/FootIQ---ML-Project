# football-data.org: terms and documentation checklist before you approve any use (updated 2026-10-26)

Status: **documentation review only.** No account was created, no API key requested, **no call was made to the data API** (`api.football-data.org` was never contacted), nothing was ingested or imported, and `live_enabled` stays false. I read the provider's public web pages and its public documentation site (pages only). Third-party blog posts that came up in a search (comparison sites) were **not** used as facts.

Pages read: General Terms and Conditions `https://www.football-data.org/about`; plans `https://www.football-data.org/pricing`; competitions `https://www.football-data.org/coverage`; API reference `https://www.football-data.org/documentation/api`; documentation site v4 `https://docs.football-data.org/general/v4/` (overview, policies, lookup tables, match, overtime).

## 1. What the provider's own pages say

| Topic | What it says | Where |
|---|---|---|
| Acceptance | signing up means accepting the terms "in full, without any reservation" | Terms 1.1 |
| Description | "a free Football-Data API (with upgrade options) to the world wide development community" | Terms |
| One key, one application | an API key applies to a single application | Terms 2.3 |
| Fair use | "continually excessive" use may lead to cancellation; no number is given | Terms 3.3 |
| Cancellation | takes effect when the paid month ends and **deletes the account and its stored data** (the provider's account data) | Terms 4.6 |
| Credentials | keep confidential; "may not be stored in code repositories of open source projects" | Terms 6.1 |
| Attribution | the visible wording "Football data provided by the Football-Data.org API" (footer, about section or another visible place) | Terms 7.1 |
| After you stop | you may not reference or publish football data obtained through the API on your own site or service | Terms 9.1 |
| Logos and photos | belong to their owners | Terms 9.2 |
| Version | "Last updated: June 1, 2018"; effective 1 June 2018 | Terms 12.1 |
| Free plan | 12 competitions; scores and schedules **delayed**; fixtures; league tables; 10 calls per minute; price 0 | Pricing |
| Other plans | Free with livescores 12 euro/month (20 calls/min); ML Pack Light 29; Free + Deep Data 29 (30 calls/min); Standard 49 (60 calls/min, 30 competitions); Advanced 99; Pro 199; add-ons for odds and statistics | Pricing |
| Free-tier competitions | Champions League, Primeira Liga, Premier League, Eredivisie, Bundesliga, Ligue 1, Serie A, La Liga, Championship, Brasileirão Série A, World Cup, European Championship (12) | Coverage |
| Rate limits (docs) | unauthenticated: 100 requests per 24 hours, only area and competition lists; registered: **10 per minute free, 30 per minute Standard, 60 per minute higher plans**; HTTP 429 when exceeded | Docs, policies |
| Headers | `X-Auth-Token` to authenticate; response headers `X-RequestsAvailable` and `X-RequestCounter-Reset` (the older API page names `X-Requests-Available-Minute`); `X-Authenticated-Client`; `X-API-Version` | Docs, lookup tables |
| Match status values (v4 lookup tables) | SCHEDULED, TIMED, IN_PLAY, PAUSED, EXTRA_TIME, PENALTY_SHOOTOUT, FINISHED, SUSPENDED, POSTPONED, CANCELLED, **AWARDED**; LIVE is a filter that combines IN_PLAY and PAUSED; the meanings of SUSPENDED, POSTPONED, CANCELLED and AWARDED are **not defined** | Docs |
| Score fields (v4) | `score.duration` (REGULAR, EXTRA_TIME, PENALTY_SHOOTOUT); `regularTime` = goals in the first 90 minutes (added in v4); `halfTime`; `extraTime` and `penalties` (optional nodes counting only those goals); `fullTime` = running score, final score at FINISHED; in the one example `fullTime` includes the shootout goals, but the text does not say so as a rule | Docs, overtime |

## 2. What the documents do NOT say (you must verify; I could not settle these from the pages)
- [ ] **Commercial or non-commercial use of the free plan.** The terms and the pricing page do **not** restrict the free plan to non-commercial use and do not mention it at all. A college mini-project is almost certainly fine, but only the provider can say. The documentation gives a contact e-mail for questions; **I have not written to them** (sending a message is your decision).
- [ ] **Storing results in our own database.** Not addressed while subscribed. Clause 9.1 bars referencing the data after you stop, and clause 4.6 deletes the account's stored data on cancellation: decide whether that affects results already imported (for example, would they have to be deleted when the project ends?).
- [ ] **Redistribution.** The repository or a zip of the project may be shared; the terms are silent on redistribution of stored results. Clause 6.1 forbids publishing the key.
- [ ] **How long "delayed" is.** The free plan says "Scores delayed" and "Schedules delayed" and gives no duration anywhere I could read.
- [ ] **Which seasons the free plan covers.** The coverage page names competitions but **no seasons**: it does not say whether 2026-27 is included. This can only be settled after registering (the competitions list of an account), which needs your approval.
- [ ] **Which "regular result" to use.** For a league match use `regularTime` when present, otherwise `fullTime` when `duration` is REGULAR. Confirm with a sample payload before trusting it.
- [ ] **What AWARDED, SUSPENDED, POSTPONED and CANCELLED mean and how they are scored.** Listed, not defined; FootIQ treats cancelled and abandoned fixtures as blocking anyway (decision D7).
- [ ] **Terms date.** The terms are dated 2018. Check the live page again on the day you decide.
- [ ] **The two rate-limit statements disagree.** The pricing page gives Standard 60 and Advanced 100 calls per minute; the policies page gives 30 per minute for Standard and 60 for all higher plans. Irrelevant for the free plan (10 per minute on both), but a sign the pages are not kept in step.
- [ ] **The two status lists disagree.** The older API reference page lists eight statuses without AWARDED; the v4 lookup tables list eleven with it. Design the adapter to accept any status and map unknown ones to "blocking".
- [ ] **Where the key may live.** Only in a local, git-ignored file (for example `config/footballdata.key`), never in the repository, chat or logs (clause 6.1).
- [ ] **Account ownership.** The account must be yours; one key for one application (this project).
- [ ] **Attribution wording.** Use exactly "Football data provided by the Football-Data.org API" and decide where it appears.

## 3. What I would do after your separate approval (nothing started)
(a) Build and test an adapter offline against saved sample payloads written from the documentation (statuses and score fields above); (b) one supervised read of three leagues (three requests, at least six seconds apart) with a request ledger and live access enabled only for that run; (c) rehearsal import in a private copy with a full diff; (d) production import with backup; (e) any scheduled synchronisation or widening of the points-only scope are separate approvals.
