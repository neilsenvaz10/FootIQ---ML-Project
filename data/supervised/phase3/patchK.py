p = "docs/mini-project/PHASE3_VALIDATION_REVIEW.md"
s = open(p, encoding="utf-8").read()
a = "About 3,100 matches would be needed for 90% power at ±0.10 goals; the two leagues produce only 686 matches a season, so confirmation data alone would take about 4.5 seasons."
b = "About 2,600 matches are needed for 90% power at ±0.10 goals (measured in `m2_confirmation_planning.py`; an earlier rough figure of 3,100 here was too high); the two leagues produce only 686 matches a season, so confirmation data from them alone would take about 3.8 seasons."
assert a in s
s = s.replace(a, b)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
