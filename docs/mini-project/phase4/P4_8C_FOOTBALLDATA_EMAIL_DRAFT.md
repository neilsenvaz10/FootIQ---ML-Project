# Email to football-data.org: FINAL DRAFT FOR YOUR REVIEW (NOT SENT)

Status: **not sent.** I have not registered an account, requested a key or contacted the provider, and the project makes no request to it. Send it yourself from your own address if you decide to. The address below is the one the provider's pricing page gives for "custom packages, additional coverage, or questions" (read on 2026-10-27; please re-check it on the page before sending). Serie A and Ligue 1 stay blocked from automatic synchronisation until the provider answers in writing and you approve.

**To:** daniel@football-data.org
**Subject:** Free-plan question from a student project: local storage of Serie A and Ligue 1 results

Dear football-data.org team,

I am a student at [college name] building a non-commercial, educational football analytics project called FootIQ as a college mini-project. It keeps match results in a local SQLite database and shows league tables and probability estimates for several European leagues. For Serie A (SA) and Ligue 1 (FL1) I would like to use your free plan, but your terms and documentation leave a few points open, and I would rather ask than assume. I have not registered and have not made any request to your API.

The intended use is small: about one read of the fixtures and results of those two leagues every six hours (a handful of requests per run, far below the free plan's 10 requests per minute), stored locally, shown with the wording "Football data provided by the Football-Data.org API", used only for this academic project. The API key would be kept in a local file that is not published or committed.

Could you please clarify the following?

1. **Local storage.** May a non-commercial, educational project periodically retrieve fixtures and results through the free plan and store them in a local SQLite database?
2. **Retention afterwards.** If I stop using the API or close the account, may the historical results already stored remain in the project (for example in the database that is submitted and shown to examiners), or do clause 4.6 (deletion of "stored and indexed data") and clause 9.1 (no referencing of the data after cancellation) require me to delete them?
3. **Coverage.** Does the free plan currently include the 2026-27 season's fixtures and results for Serie A and Ligue 1?
4. **Delay and attribution.** What delay applies to scores and schedules on the free plan (minutes, hours or days)? Are there any attribution or redistribution requirements beyond the wording in clause 7.1, in particular when the project and its database are submitted to examiners or shared as a zip file?

A short answer to each of the four points would be very helpful, and I will keep your reply with the project documentation. Thank you for offering the service.

Kind regards,
[Your full name]
[Course and year] · [College]
[Your email address]

---

*Notes for you, not part of the email:* the four questions map to the uncertainties in `P4_8C_CHECKPOINT_REPORT.md` §7 (storage, retention, coverage, delay). Fill the bracketed fields; the college name appears twice on purpose. Remove these notes before sending. If you prefer to keep the project fully self-contained, the alternative is to leave Serie A and Ligue 1 as "no approved provider", which is the current state.
