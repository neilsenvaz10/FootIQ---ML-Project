# Fresh results for the Premier League, Serie A and Ligue 1: options and what you would need to do

Date: 2026-10-25. **Research only.** I read public documentation, pricing and terms pages; I made **no request to any provider's data API**, created no account, obtained no credential, enabled no synchronization and imported nothing. Where a page could not be read, that is stated, and the item is marked "to be verified by you".

## 1. Where we stand

| League | Newest verified result in the store | Played-date fixtures without a result | Source of what we have |
|---|---|---|---|
| Premier League | 2026-10-12 | 15 | OpenLigaDB (10 results imported 2026-10-25); the source itself lags about 13 days |
| Serie A | 2026-09-20 | 20 (+5 past-dated) | openfootball snapshot only |
| Ligue 1 | 2026-09-20 | 18 (+3) | openfootball snapshot only |

OpenLigaDB covers the Premier League and La Liga but **not** Serie A or Ligue 1. openfootball (public domain / CC0) has 2026-27 folders for England and Italy (its "europe" repository, which holds Ligue 1, shows no season list on the page I read), but its own help page promises no update schedule, and our stale Serie A and Ligue 1 data show that it is not being kept current.

## 2. Options compared

| Option | Covers PL / SA / L1 | Documented API | Rate limit | Licence and conditions (from public pages) | Fit |
|---|---|---|---|---|---|
| **football-data.org v4, free tier** | **Yes**: its coverage page lists Premier League, Serie A, Ligue 1, La Liga and Bundesliga among 12 free competitions ("Access to data of these leagues & cups is free. Forever.") | Yes (REST, JSON, `X-Auth-Token`) | **10 requests per minute** for registered free clients (100 per 24 h unauthenticated) | Needs a free **account and API key**; scores and schedules **delayed** on the free plan (acceptable for final results); the General Terms (page dated 2018, found through search; the live page could not be read) require the attribution "Football data provided by the Football-Data.org API" and say the key belongs to **one application** and must **not be stored in an open-source repository**; a blog post says the API is free for **non-commercial** use only; team logos belong to their owners | **Best match.** One source for all three leagues |
| API-Football (api-sports.io) | Yes, but the free plan is "limited in terms of available seasons"; whether the **current** season is included was not confirmed | Yes | 100 requests per day on the free plan | Account required; multiple accounts forbidden; storage/caching rules not found (terms not fully readable); pricing pages disagree on paid tiers | Second choice, only if its coverage tab shows the current season |
| TheSportsDB | Partly | Yes | 30 per minute (free key `123` is public) | Free `eventsseason` is capped at **15 results**; the full schedule endpoint is premium; terms and attribution not read | Not practical |
| football-data.co.uk (CSV) | PL, Serie A, Ligue 1 and more; updated at least twice a week (Sunday and Wednesday nights) | CSV downloads | n/a | **"Intended for private individuals only"**; excludes commercial use, data-training products and **automated bots, scrapers or AI** | Not suitable for an application that ingests automatically; the earlier decision "do not use" stands |
| OpenLigaDB | Premier League and La Liga only | Yes | fair use (about 60/min) | ODbL 1.0 with attribution; already approved and in use | Keeps the Premier League partly fresh; cannot help Serie A or Ligue 1 |
| openfootball (GitHub) | Yes, as text files | none | n/a | CC0, public domain | Free but not reliably updated; not a freshness solution |
| Wikipedia result matrices | Yes | no | n/a | CC BY-SA | Already approved only as **confirmation**, never as the primary source |
| Official league sites, Sofascore, FotMob, FBref | Yes | no public API | n/a | Terms prohibit scraping | Excluded |
| Manual import (a CSV you export from a source you are entitled to use) | Yes | none | n/a | Depends on your source | Possible stop-gap with the same provenance checks |

Not evaluated in this session: Sportmonks and other paid APIs.

## 3. Most practical route

**football-data.org free tier**, used through the same pipeline as OpenLigaDB, for the three stale competitions (and as an independent cross-check for the Bundesliga, La Liga and Premier League):

* **Load:** 3 requests per refresh (one season listing per league), at least 6 seconds apart (10 per minute is the limit), so even an hourly check uses a fraction of the quota.
* **Provenance:** every raw response is saved with its sha256, URL, retrieval time and licence text in the request ledger, exactly as for OpenLigaDB; attribution shown in the app; the key stays in a git-ignored file and is never printed.
* **Safety:** team names go through the same identity ladder (exact, normalised, reviewed alias; never fuzzy); results are recognised as 90-minute league results; postponed, suspended, cancelled or awarded matches are quarantined, not guessed; date disagreements are held; conflicts with existing results are quarantined; the first import is a **rehearsal on a private copy** with a full diff before any production change, and production is backed up first, as for the Premier League and La Liga import.
* **What it fixes and what it does not:** it would bring Serie A and Ligue 1 results (and Premier League results) up to date, so the data-quality gate would classify them as Ready or Provisional. It does **not** unblock the final-position simulator (scoreline method), and it does not by itself widen the points-only mode beyond the Bundesliga and La Liga: that scope extension would need your separate approval, and Serie A and Ligue 1 would also need their rules settled for any position-based output.

Unverified points to settle at the first supervised read (not assumed): which fields v4 gives for the regular-time score; exact status names for postponed or suspended matches; how soon after full time a result appears on the free plan; the live General Terms wording.

## 4. What you would need to do

1. **Read the live football-data.org terms** (General Terms and the FAQ/pricing page) and decide whether using the free tier for this college project, shown with the required attribution, is acceptable. Pay particular attention to non-commercial use, to storing results in a database, and to the "key not in an open-source repository" rule.
2. **Create an account and obtain a free API key** yourself (I will not).
3. **Save the key** in a local, git-ignored file, for example `config/footballdata.key` (I will create the ignore rule and the loader; the key never goes in chat, logs or the repository).
4. **Give separate approvals**, in order: (a) building and testing the adapter offline against saved sample payloads; (b) one supervised read of the three leagues with a request cap (about 3 requests), a ledger and live access switched on only for that run; (c) a rehearsal import on a private copy and its diff; (d) a production import; (e) any unattended or hourly synchronization, and (f) any widening of the points-only scope to the Premier League, Serie A or Ligue 1.

If you prefer not to use football-data.org, the alternatives are API-Football's free plan (confirm in its coverage tab that the current season is included; no multiple accounts) or a manual CSV import of results from a source you are entitled to use.

## 5. Risks
Terms may not permit database storage or may change; the free plan may delay results; team-name mapping needs a one-off review for each league (as with Brentford, Celta, Deportivo, Villarreal and Racing); a single source cannot catch its own mistakes (the Bournemouth-Brentford and Aston Villa-Nottingham Forest conflicts show why a second source or an official record matters); and a refresh that is not automatic leaves the data as old as your last supervised run, which the freshness gate will show.
