import json

p = "config/season_rules.json"
s = open(p, encoding="utf-8").read()
old = '"LALIGA|2026-27": {\n      "league": "La Liga", "season": "2026-27", "clubs": 20,'
assert old in s
s = s.replace(old, old + '\n      "live_confirmation": "PENDING: the text was read from the Internet Archive capture of the federation URL (2026-07-14); it has NOT been confirmed against the live federation file. Compare the SHA-256 of the live file with 35b0a9e4a011325a5dd1144b790cf986bdcdb33a2c2b1c4cf6fed7872d6146ac (instructions: docs/mini-project/LALIGA_VERIFICATION.md).",')
json.loads(s)
open(p, "w", encoding="utf-8", newline="\n").write(s)

p = "app/seasonsim/rules.py"
s = open(p, encoding="utf-8").read()
s = s.replace('sources=p.get("sources", []), notes=p.get("interpretation_notes", []),', 'sources=p.get("sources", []), live_confirmation=p.get("live_confirmation"), notes=p.get("interpretation_notes", []),')
open(p, "w", encoding="utf-8", newline="\n").write(s)

p = "frontend/src/pages/SeasonSimulator.jsx"
s = open(p, encoding="utf-8").read()
old = "      .\n    </Notice>\n  ) : ("
assert old in s
s = s.replace(old, "      .{rp.live_confirmation ? <span className=\"mt-1 block font-semibold text-warn\">Live-document confirmation pending: the federation file has not been checked against its checksum yet.</span> : null}\n    </Notice>\n  ) : (", 1)
open(p, "w", encoding="utf-8", newline="\n").write(s)

p = "tests/test_seasonsim_engine.py"
s = open(p, encoding="utf-8").read()
s += '''

def test_la_liga_profile_carries_a_pending_live_confirmation_and_the_others_do_not():
    assert "PENDING" in rules.profile_info("LALIGA", "2026-27")["live_confirmation"]
    assert "35b0a9e4a011325a5dd1144b790cf986bdcdb33a2c2b1c4cf6fed7872d6146ac" in rules.profile_info("LALIGA", "2026-27")["live_confirmation"]
    assert rules.profile_info("BUNDESLIGA", "2026-27")["live_confirmation"] is None
'''
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
