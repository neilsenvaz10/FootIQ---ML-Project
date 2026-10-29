p = "docs/mini-project/PHASE3_VALIDATION_REVIEW.md"
s = open(p, encoding="utf-8").read()
reps = [
    ("About 3,100 matches would be needed for 90% power at ±0.10 goals, which is roughly 4.5 further seasons of the two leagues.",
     "About 3,100 matches would be needed for 90% power at ±0.10 goals; the two leagues produce only 686 matches a season, so confirmation data alone would take about 4.5 seasons."),
    ("results dated after 2026-09-20 accumulate (about 75 per week across the five leagues once the data sources are fresh)",
     "results dated after 2026-09-20 accumulate (about 45 per week across the five leagues once the data sources are fresh, about 13 per week for Bundesliga plus La Liga)"),
    ("The drift variance per remaining match is stable in size and grows with the number of matches left.",
     "The drift variance per remaining match grows with the number of matches left (0.06 with 12 or fewer left, 0.16, 0.30, and 0.39 with 29 to 40 left), so drift is larger than proportional to the horizon."),
]
for a, b in reps:
    assert a in s, a[:40]
    s = s.replace(a, b)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
