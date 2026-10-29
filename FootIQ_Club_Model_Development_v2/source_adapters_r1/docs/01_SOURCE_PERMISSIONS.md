# 01 Source permissions (read 2026-10-21)

Pages were read in the built-in browser or fetched; the OpenLigaDB licence and terms pages are Blazor-rendered and were read through the browser. Quotes are short; German originals are paraphrased in English. This is a factual summary, not legal advice.

## OpenLigaDB
### Data licence — https://www.openligadb.de/lizenz (dated "Stand 31.08.2026") — VERIFIED
* Sports data are under the **Open Database License (ODbL) 1.0**. "Sie dürfen die Daten kostenfrei nutzen, kopieren, verändern und weiterverbreiten – auch kommerziell", subject to three conditions:
  1. **Attribution** when the data are used publicly: *"Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0"* (a notice at a findable place, e.g. footer/source page).
  2. **Share-alike** applies when a **modified version of the database is publicly redistributed**; merely displaying data (table, chart, app view) creates a derived work that needs only attribution.
  3. **No technical restrictions** on a redistributed database (a parallel open version is allowed).
* Not covered by the licence: images/logos referenced via `TeamIconUrl`, club names/crests/logos (third-party trademark rights remain). We store no icon URLs' content.
* Licence is not revoked retroactively; later API access changes do not affect data already retrieved.
* Data origin: entered by registered users, **no editorial review; no warranty for correctness, completeness or timeliness**.
* The licence page states that API access is governed separately by the Terms.

### API terms — https://www.openligadb.de/nutzungsbedingungen (dated "Stand 28.08.2026") — VERIFIED
* Privately run project; **no availability guarantee**; outages and interface changes without notice → catch failures, use cached data.
* Data may contain delays, gaps, errors "especially during running matches"; do not use for purposes where an error can cause damage.
* **Fair use:** use `getlastchangedate` as the cheap poll and fetch full data only on change; during live matches at most one request per 30–60 s per league (not per user/widget/club); outside live matches far less (usually a few per day); **add jitter**; cache locally; on 429/5xx **back off exponentially**; serve many users from one central fetch.
* **User-Agent:** "aussagekräftiger User-Agent mit Anwendungsname und einer Kontaktmöglichkeit" (app name + contact), e.g. `MyApp/1.2 (+https://example.org/myapp; contact@example.org)`.
* The operator may throttle/block clients; access is currently free without registration but may later require registration/keys/quotas (restrictions announced >= 4 weeks ahead); liability excluded; own risk.
* Swagger description (api.openligadb.de): **60 requests per minute per IP**, "please retrieve sparingly"; completed seasons no longer change; result types exposed by `resultTypeKind` = HalfTime | After90Minutes | AfterExtraTime | AfterPenalties | Unknown.

### Unresolved / residual
* The terms do not mention machine learning; the ODbL licence permits use, copying and modification including commercially, so model training and feature generation are covered by the licence; a trained model is not a database. If we ever **publicly redistribute** an extract or an adapted database, share-alike and attribution apply.
* Accuracy is explicitly not guaranteed → two-source confirmation or conflict checks are required before a result becomes a label (see amendment proposal).
* Contact information in the User-Agent is required by the terms: **not yet configured** (see below).

## Wikimedia / Wikipedia
* **Content licence** (Terms of Use, "Reusing Wikipedia content"): text under **CC BY-SA 4.0 and GFDL**. Reuser duties: attribute (link/URL of the page, a stable copy, or list of authors), give a licence notice naming CC BY-SA with a link, indicate changes; **modified/added material must be released under CC BY-SA 4.0 or later**. The reuse page does not define "adaptation" and does not address databases or facts — **the effect on a derived results table or a model is not settled by the sources read** (see 02).
* **API access:** Terms of Use incorporate the User-Agent policy, Robot policy and API Etiquette; abusive/unapproved automated use and undue burden are prohibited.
* **User-Agent policy:** descriptive string with client name/version and **contact information**, include the word "bot" for automated clients, do not use generic "curl/python-urllib" strings or browser strings; non-compliant clients may be blocked without notice.
* **Robot policy (wikitech):** Action API unauthenticated: **1 concurrent request, below 5 per second; if a request takes more than 1 second wait 5 seconds before the next**; honour robots.txt; on 429 wait for Retry-After; prefer dumps for bulk; do not crawl non-canonical URLs or old revisions through REST URLs.
* **API:Etiquette:** serial requests, batch titles with `|`, use `maxlag` for non-interactive tasks, cache, GET for reads, back off on `ratelimited`.
* The Wikipedia adapter follows these: serial, >= 5 s apart (+ jitter), `maxlag=5`, batching available, exponential back-off, Retry-After honoured, permalinks to revisions only for attribution.

## Contact string (required, still missing)
Both sources require real contact information in the User-Agent. The owner chose to supply a different contact but none has been provided, so `config/adapters.json` has `contact: null` and `live_enabled: false`; the clients raise `LiveAccessDenied` for any live request. **Disclosure:** during the previous research step I sent one request to OpenLigaDB (bl1/2026) and three to Wikipedia with User-Agent strings that were not compliant for Wikipedia (curl, no "bot") and, for OpenLigaDB, contained the account email address; no further live requests were made in this step.

## Verdict by source
| Source | Terms verified | Live ingestion |
|---|---|---|
| OpenLigaDB | licence + API terms read in full | permitted in principle (ODbL, fair-use rules above); **restricted until a contact string is configured and you approve live use** |
| Wikipedia | licence, UA, robot and etiquette policies read | permitted for polite API use; **restricted until contact configured, and Wikipedia-derived records stay out of the official feature store until the licensing document (02) is approved** |
