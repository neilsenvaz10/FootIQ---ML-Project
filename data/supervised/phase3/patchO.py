p = "docs/mini-project/PHASE3_DYNAMIC_STRENGTH_DESIGN.md"
s = open(p, encoding="utf-8").read()
reps = [
    ("(Elo with K = 30, home advantage 50, from the frozen v2 feature metadata)",
     "(the project's v1 Elo state: start 1500, K = 20, home advantage 60, with a goal-margin multiplier; read from `feature_contract.py`; the separate Elo used by v2-r1 has K = 30 and home advantage 50)"),
    ("update the two clubs' offsets with the frozen Elo rule (K = 30, home advantage 50; optional goal-margin multiplier only if a scoreline method is approved)",
     "update the two clubs' offsets with the frozen v1 Elo rule (K = 20, home advantage 60); the rule's goal-margin multiplier (1.0 for a one-goal margin, 1.5 for two, then (11 + margin) / 8) needs scores, so it is set to 1.0 until a scoreline method is approved, which slightly under-states the update after big wins"),
    ("no new fitted parameter is needed apart from an optional amplitude factor κ (default 1) to check that K = 30 is the right strength of reaction.",
     "no new fitted parameter is needed apart from an optional amplitude factor κ (default 1) to check that K = 20 is the right strength of reaction."),
    ("ordinary season-long changes in an Elo system with K = 30", "ordinary season-long changes in an Elo system with K = 20"),
    ("K may not suit", "K may not suit the strength of reaction"),
]
for a, b in reps:
    assert a in s, a[:50]
    s = s.replace(a, b)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
