p = "frontend/src/pages/SeasonSimulator.jsx"
s = open(p, encoding="utf-8").read()
old = '''          <span className="mt-0.5 h-3 text-[9px] text-mute">{i % step === 0 ? d.first_points + i : ""}</span>'''
new = '''          <span className="relative mt-0.5 h-3 w-full text-[9px] text-mute">{i % step === 0 ? <span className="absolute left-1/2 -translate-x-1/2 whitespace-nowrap">{d.first_points + i}</span> : null}</span>'''
assert old in s
s = s.replace(old, new)
s = s.replace("const step = Math.max(1, Math.ceil(d.probabilities.length / 12));", "const step = Math.max(1, Math.ceil(d.probabilities.length / 6));")
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
