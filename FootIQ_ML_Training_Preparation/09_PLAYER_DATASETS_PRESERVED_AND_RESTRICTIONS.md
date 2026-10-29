# 09 Player datasets: preserved, with current restrictions

Nothing in `FootIQ_Dataset_Submission/` (files 04, 05, 08), `FootIQ_ML_Data_Verification/player_form_v1/` or the player audit files was modified or deleted in this task.

| Use | Status (from `11_ML_TRAINING_APPROVAL.md`) | Restrictions that still apply |
|---|---|---|
| Descriptive player analytics | APPROVED WITH RESTRICTIONS | keep StatsBomb event-level rows, openfootball appearance rows, men and women separate; minutes: StatsBomb derived, openfootball ESTIMATED; never merge players by name; credit StatsBomb |
| Player recent form | APPROVED WITH RESTRICTIONS | windows are the last N *observed* matches (30.6% of complete 5-match windows span >60 days); filter on `w*_span_days`; openfootball appearance windows treat non-appearance as unknown cause |
| Clustering / similarity | APPROVED WITH RESTRICTIONS | StatsBomb male player-seasons >= 900 derived minutes, position-specific cohorts, standardise within competition-season, no zero-filling, research use until the StatsBomb licence PDF is reviewed |
| Player-performance prediction | BLOCKED | discontinuous coverage, no lineups / injuries, no verified target beyond observed next-match stats; open items I-04, I-11, I-13..I-15 in `VERIFICATION_ISSUES.csv` |

The club league dataset of this folder uses **no player data**.
