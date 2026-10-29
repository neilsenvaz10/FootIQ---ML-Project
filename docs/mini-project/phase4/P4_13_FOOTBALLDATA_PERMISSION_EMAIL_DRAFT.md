# Email to football-data.org: DRAFT FOR YOUR REVIEW (NOT SENT)

Status: **not sent.** Send it yourself from the e-mail address of your football-data.org account. The address below is the one their pricing page gave in the Phase 4.8C review (read 2026-10-27); check it on the page before sending. Fill the bracketed fields and delete these notes. Until you have a written answer, FootIQ records every football-data.org row as "storage and reuse permissions unconfirmed" and imports nothing.

**To:** daniel@football-data.org
**Subject:** Free-plan permission request from a student project: local storage, reuse and model training (PL, SA, FL1)

Dear football-data.org team,

I am a student at [college name] and I hold a free account with you (registered with [account e-mail]). I am building a non-commercial, educational football analytics mini-project, FootIQ, which keeps league results in a local SQLite database, shows league tables and fixture lists, and evaluates a statistical match-prediction model. I would like to use your free plan for the Premier League (PL), Serie A (SA) and Ligue 1 (FL1), season 2026-27, and I would rather ask for written permission than assume it.

Planned use: about one request per competition every six hours (three requests per cycle, at least seven seconds apart, so roughly twelve a day and well inside the 10 per minute limit), the token kept only in a local environment variable, your attribution "Football data provided by the Football-Data.org API" shown in the application, no resale, no commercial use. I have so far made exactly three test requests (one per competition) and nothing else.

Could you please confirm in writing:

1. **Storage.** May a non-commercial educational project retrieve fixtures and results through the free plan and store them, including the raw JSON responses, in a local database?
2. **Model use.** May the stored results be used as inputs to evaluate and train a statistical prediction model for the project, and may probabilities derived from them be displayed with the attribution?
3. **Submission and retention.** May the project, including a database that contains these results, be submitted to examiners and kept as part of the project record (for example as a zip file) after the project ends or the account is closed, or must the data be deleted (terms 4.6 and 9.1)?
4. **Redistribution.** Is any sharing of the stored data outside the project (for example a public repository) not allowed? I do not plan any, and I would keep the data out of the repository.
5. **Score fields.** For league matches with `duration` REGULAR, is `score.fullTime` the score after 90 minutes (plus stoppage time)? In the responses I received `regularTime` is not present. Do awarded or abandoned matches use the same field?
6. **Schedule fields.** Fixtures with status SCHEDULED carry `utcDate` at 00:00:00Z: is that a placeholder for "date and time not yet set"? And does a TIMED fixture's `utcDate` always show the currently confirmed kick-off?
7. **Free-plan delay.** What delay applies to scores and schedules on the free plan?

Short answers to each point would be very helpful; I will keep your reply with the project documentation. Thank you for offering the service.

Kind regards,
[Your full name]
[Course and year] · [College]
[Your email address]

---
*Notes for you, not part of the email:* questions 1 to 4 are the permissions question the Phase 4.12 report marked as the blocker; 5 and 6 come from what the real responses showed (no `regularTime`; 330 provisional 00:00Z fixtures); 7 is still unpublished. Do not attach any data file, and never put the token in an e-mail.
