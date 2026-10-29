"""Phase 4.33: documentation link check (read-only). Checks relative markdown links and backticked project paths in README.md, app/README.md, frontend/README.md, docs/mini-project/**/*.md.
Reports links whose target is missing and whether the target was removed by this cleanup (approved_manifest.csv)."""
import csv
import os
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
deleted = {r["path"] for r in csv.DictReader(open(HERE / "approved_manifest.csv", encoding="utf-8"))}
deleted_dirs = {os.path.dirname(p) for p in deleted}
files = [ROOT / "README.md", ROOT / "app" / "README.md", ROOT / "frontend" / "README.md"] + sorted((ROOT / "docs" / "mini-project").rglob("*.md")) + sorted((ROOT / "docs" / "architecture").rglob("*.md")) + sorted((ROOT / "docs" / "data-sources").rglob("*.md"))
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
PATHTOK = re.compile(r"`((?:app|docs|data|config|frontend|tests|scripts|FootIQ_[A-Za-z_0-9]+)/[A-Za-z0-9_./\-]+\.[A-Za-z0-9]+)`")
broken_links, broken_tokens, total_links, total_tokens = [], [], 0, 0
for f in files:
    s = f.read_text(encoding="utf-8", errors="ignore")
    for m in LINK.finditer(s):
        t = m.group(1)
        if t.startswith(("http", "mailto", "/")) or t.startswith("#"):
            continue
        total_links += 1
        target = (f.parent / unquote(t)).resolve()
        if not target.exists():
            rel = target.relative_to(ROOT).as_posix() if ROOT.resolve() in target.parents else str(target)
            broken_links.append((f.relative_to(ROOT).as_posix(), t, rel in deleted))
    for m in PATHTOK.finditer(s):
        t = m.group(1)
        total_tokens += 1
        if not (ROOT / t).exists() and "*" not in t and "<" not in t:
            broken_tokens.append((f.relative_to(ROOT).as_posix(), t, t in deleted))
print(f"markdown links checked: {total_links}; broken: {len(broken_links)}; pointing to files removed by this cleanup: {sum(1 for b in broken_links if b[2])}")
for b in broken_links[:12]:
    print("   link", b)
rem = [b for b in broken_tokens if b[2]]
print(f"backticked project paths checked: {total_tokens}; missing: {len(broken_tokens)}; missing because removed by this cleanup: {len(rem)}")
for b in rem[:15]:
    print("   removed:", b[0], "->", b[1])
