# v2.7 Known Fixture Validation

This validates the saved v2.7 live predictions against known API-Football fixture IDs.

## Summary

- Final fixtures validated: 7.
- Public non-pass picks available to score: 0.
- Internal ensemble leans correct: 6/7.
- Passes where the internal lean was correct: 6.
- Internal leans at or above 60% confidence: 4/4 correct.

## Fixture Results

| Match | Score | Actual | Public | Internal | Max prob | Internal correct |
|---|---|---|---|---|---:|---|
| Portugal vs Chile | 2-1 | team1_win | pass | team1_win | 64.21% | True |
| Germany vs USA | 1-2 | team1_win | pass | draw | 38.65% | False |
| Bolivia vs Scotland | 0-4 | team2_win | pass | team2_win | 44.60% | True |
| Brazil vs Egypt | 2-1 | team1_win | pass | team1_win | 60.04% | True |
| Argentina vs Honduras | 2-0 | team1_win | pass | team1_win | 76.36% | True |
| Morocco vs Norway | 1-1 | draw | pass | draw | 39.04% | True |
| Colombia vs Jordan | 2-0 | team1_win | pass | team1_win | 62.37% | True |
| Argentina vs Iceland |  | NS | pass | team1_win | 80.97% |  |

## Read

This sample is too small to recalibrate the model statistically, but it shows the current gate is probably too conservative for public product use: it passed fixtures where the internal ensemble lean was right. The right next step is not to remove Pass; it is to add a second confidence tier for strong internal leans that the logistic safety layer blocks mostly because the match is a friendly.

API budget after validation: 16/100 used.
