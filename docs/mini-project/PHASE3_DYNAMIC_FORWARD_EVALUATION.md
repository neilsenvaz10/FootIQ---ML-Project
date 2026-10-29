# Dynamic-strength mode: forward-evaluation design on 2026-27 (DESIGN ONLY, nothing started)

Date: 2026-10-26. **Status: a design for your approval of the procedure.** Nothing has been run, scheduled or recorded under it. Dynamic mode stays **disabled in production**: it is not imported by the service or the API (a test now checks this), has no setting, and no page can request it. No frozen model, no production table, no official prospective-evaluation file and `config/sync.json` (`live_enabled` false) are touched. **No unattended or scheduled monitoring** is proposed or started: every step below is a manual action by you or, on your request, by me.

Background: [PHASE3_DYNAMIC_STRENGTH_RESULTS.md](PHASE3_DYNAMIC_STRENGTH_RESULTS.md) (offline prototype, development seasons 2020-21 to 2023-24, one run on 2024-25 and 2025-26), [PHASE3_DYNAMIC_STRENGTH_DESIGN.md](PHASE3_DYNAMIC_STRENGTH_DESIGN.md).

## 1. The question and why a forward test
The offline evaluation used seasons that are already history, and the frozen model's data for 2024-25 and 2025-26 existed when the work was done. A *forward* evaluation asks: **do the dynamic-strength forecasts made now, before the outcomes exist, describe the final 2026-27 points better than the static forecasts the app already produces?** "Better" means better calibrated and not worse in CRPS. The forecasts are frozen and fingerprinted before any outcome is known, so nothing can be tuned afterwards.

## 2. What is frozen before the first forecast (no later change)
| Item | Value | Why |
|---|---|---|
| Static comparator | the production points-only simulation (frozen club v1 probabilities at the cut-off, static strengths, 3/1/0 points) | it is what users see today |
| Dynamic configuration | `kappa 0.5`, `tau 6`, tilt 1, Elo constants of frozen club v1 (K 20, home advantage 60, margin multiplier 1) | chosen on the 2020-21 to 2023-24 seasons by a rule written beforehand; the 2024-25 and 2025-26 results did **not** change it |
| Simulations / seed | 10,000 per forecast; seed `20261100 + 10 x cut-off number (1, 2, 3) + league number (BUNDESLIGA 0, LALIGA 1, then EPL 2, SERIEA 3, LIGUE1 4 if used)`; static and dynamic use the **same** random numbers | paired comparison, reproducible |
| Frozen models | club v1 artifacts, unchanged (their SHA-256 are recorded in every snapshot) | the dynamic mode only reads coefficients and training standard deviations |
| Reporting-only variants | K 10 and 30, home advantage 40 and 80, tilt 0.5 and 1.5, kappa 0 and 2 (the same set as the offline sensitivity table) | to show how sensitive the answer is; **never** used to choose a setting for this evaluation |
| Code | `app/seasonsim/dynamic.py` and the scoring code, fingerprinted (SHA-256) in the first snapshot | any edit after the first snapshot starts a new version |

**No retroactive tuning:** if, after seeing 2026-27 outcomes, anyone wants a different configuration, that is a **new version** (`dyn_v2`), evaluated only on forecasts made after it was written down (for example 2027-28). Results of this evaluation cannot be used to select it.

## 3. Scope, cut-offs and data
* **Leagues:** Bundesliga and La Liga (the approved scope, the only two with eligible data today). The Premier League, Serie A and Ligue 1 are a **pre-declared secondary set**: they enter only if the existing eligibility gate says Ready or Provisional at that cut-off, a rule that does not look at results. Their data are stale today (fresh results need a separate approval for live access, which has not been given).
* **Cut-offs:** 2026-11-01, 2027-01-01, 2027-03-01 (the same three as the offline evaluation). At each one the forecast is generated from the store **as it stands that day** and the date of generation is recorded. If no new results were imported since 2026-10-24 the state is the same as today's: that is still a legitimate forward forecast because every fixture after the newest stored result is simulated, and the forecast is fingerprinted before any newer result is imported.
* **Quantity forecast:** each club's **final points** of the 2026-27 league season (3/1/0 from the played results), the same quantity as the points-only page.
* **Skipped, not dropped:** a league-cut-off that is Not eligible (stale data, cancelled or abandoned fixture) is recorded as skipped with the reason. Clubs with an official points deduction (not in our data today) are flagged and reported with and without them.

## 4. What is stored at each cut-off (a snapshot, written once, never edited)
Directory `data/forward_eval_dynamic/2026-27/<cut-off date>/` (new, git-ignored, separate from every existing prospective-log directory):
* `forecast_static.json` and `forecast_dynamic.json`: for every club, mean, standard deviation, the 5th, 10th, 25th, 50th, 75th, 90th and 95th percentiles, and the full distribution of final points (counts per points value), plus the points already won and the matches left;
* `inputs.json`: league, cut-off, data cut-off date (newest stored result), number of fixtures and results, the input fingerprint the points-only mode already computes, SHA-256 of the frozen artifacts, of `config/season_sim.json`, of the code files, the configuration above;
* `MANIFEST.sha256` at the top level: one line per file (SHA-256, path) and for each snapshot the hash of the previous snapshot's manifest line (a simple chain).
To make the freeze verifiable by a third party, record the hash of each new `MANIFEST.sha256` somewhere that carries a date and that you control (for example an email to yourself, or a commit **you** make). I do not stage, commit or push anything.

## 5. Scoring (after the last league match of the season, expected May 2027; not before)
1. Realised final points of each club from the stored results (every fixture of the season completed). A league season with an unresolved cancelled or abandoned fixture is excluded and reported.
2. Per club and cut-off, for static and for dynamic: **CRPS** of the simulated distribution against the realised points (lower is better), whether the realised points fall in the 10-90%, 25-75% and 5-95% intervals, the standardised error `(realised - mean) / sd`, and the probability-integral-transform value.
3. Pooled over all club-cut-offs, and per league and per cut-off: the **paired difference** (dynamic minus static) in CRPS and in each coverage.

**Primary endpoint (declared now):** the pooled paired difference in CRPS. **Pre-declared reading:**
* *Supports dynamic mode* only if the pooled CRPS difference is below zero, its 95% interval (section 6) excludes zero, **and** the difference is below zero in each league and in at least five of the six league-cut-off blocks.
* *Contradicts it* if the pooled difference is above zero with an interval that excludes zero.
* *Inconclusive* otherwise (the expected outcome for two leagues; see section 6).
Secondary, descriptive: coverage of the 80% interval (closer to 0.80 is better; the static mode was 0.75 out of sample), standardised error (closer to 1), PIT histogram, sensitivity variants. No other comparison will be reported as a finding.

## 6. How informative one season of two leagues is (computed from the offline results, honest expectation)
* In the 2024-25 and 2025-26 evaluation seasons the mean CRPS change was -0.034 over five leagues, but only **-0.024** over the Bundesliga and La Liga alone (Bundesliga -0.015 and -0.035, La Liga -0.044 and -0.002 by season); the Premier League gained most (-0.075 and -0.088).
* The paired differences have a standard deviation of 0.18 per club-cut-off. For one season of the Bundesliga and La Liga there are 54 + 60 = 114 club-cut-offs, so even if the rows were independent the standard error would be about 0.017, giving **about 30% power** (two-sided 5%) to detect a true improvement of 0.024, and less once clubs in one league are allowed to be correlated. Adding the other three leagues (288 club-cut-offs, true effect -0.034, standard error about 0.0105) would give **about 90% power** if the rows were independent.
* The interval will be a **club-block bootstrap** (each club's cut-offs together), which ignores that clubs in one league share matches and a zero-sum table, so it is **optimistic**; the block counts (below zero in each league; in how many of the six blocks) are reported beside it.
* In the earlier data two random league-seasons were both better for dynamic 80% of the time, and by chance alone 25% of the time. So even a favourable result from two leagues is weak evidence.
**Consequence:** with the Bundesliga and La Liga alone the most likely honest conclusion is "inconclusive, consistent with a modest benefit". The options are to include the three other leagues when their data become eligible (needs your separate approval for data), and/or to treat 2027-28 as the confirmation season. **A result from this evaluation alone will not be used to enable dynamic mode.**

## 7. Procedure (every step manual, none unattended)
1. *You approve this design.* (Nothing runs until then.)
2. On each cut-off date, or the first day after it, you ask me to produce the snapshot (or run the single command I would write: an offline script on a **private copy** of the store, no network, no model change). I tell you the manifest hash.
3. You record the manifest hash somewhere dated.
4. After the season I score with the code whose hash is in the first snapshot, write the report with the tables of section 5, and give the reading it supports. No re-tuning, no re-running with other seeds to find a nicer result.
Not part of this design and not started: any scheduler, watcher or reminder; any data import or provider request; any change to the app, API or models.

## 8. Limitations to state with any result
* Only the Elo channel is modelled: the form features of the frozen model also react to results, and a hand-built check found the Elo shortcut reproduces about 76% of the real change in probabilities (exact change about 1.36 times the shortcut), so the amplitude `kappa` remains uncertain.
* No goal-margin multiplier is used (no scores).
* One season, few leagues; correlated observations; optimistic interval.
* The final points are those of the played results; official deductions or administrative results are outside the data.
* A forecast made while the live-access switch is off uses the data in the store at that date; fixtures played after the newest stored result are treated as future.

## 9. What I need from you
1. Approve or change the **procedure** above (frozen configuration, cut-offs, primary endpoint and reading).
2. Say whether the first snapshot should be taken on 2026-11-01 (or the first day after), and whether you want me to write the offline snapshot and scoring scripts now (they would be written, tested on a private copy with synthetic data, and **not run** on real forecasts until you say so).
3. Decide whether to approve, separately, fresher data for the Premier League, Serie A and Ligue 1 (which would make the evaluation informative); until then the evaluation is limited to the Bundesliga and La Liga.
