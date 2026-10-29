from pathlib import Path
p = Path(__file__).resolve().parent / "evidence.py"
s = p.read_text(encoding="utf-8")
a = s.index('    names = {}\n    for m in re.finditer(r"\|\s*name_')
b = s.index("    ab = {}\n    for k, (tgt, disp) in names.items():")
block = s[a:b]
s = s[:a] + "    names, grid = parse_grid(w)\n" + s[b:]
fn = "def parse_grid(w):\n    \"\"\"The results grid of a Wikipedia league page: ({abbreviation: (link target, display name)}, {(home abbr, away abbr): (score or None, other text)}). A cell may hold a piped link.\"\"\"\n" + block + "    return names, grid\n\n\n"
s = s.replace("def wiki_scores(key, ent):", fn + "def wiki_scores(key, ent):", 1)
p.write_text(s, encoding="utf-8")
print("refactored")
