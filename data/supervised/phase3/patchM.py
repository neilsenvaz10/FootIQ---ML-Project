p = "docs/mini-project/DATA_FRESHNESS_OPTIONS.md"
s = open(p, encoding="utf-8").read()
a = "OpenLigaDB covers the Premier League and La Liga but **not** Serie A or Ligue 1. openfootball (public domain / CC0) has 2026-27 folders for England, Italy and the \"europe\" repository (which holds Ligue 1), but its own help page promises no update schedule, and the three stale competitions show that it is not being kept current."
b = "OpenLigaDB covers the Premier League and La Liga but **not** Serie A or Ligue 1. openfootball (public domain / CC0) has 2026-27 folders for England and Italy (its \"europe\" repository, which holds Ligue 1, shows no season list on the page I read), but its own help page promises no update schedule, and our stale Serie A and Ligue 1 data show that it is not being kept current."
assert a in s
open(p, "w", encoding="utf-8", newline="\n").write(s.replace(a, b))
print("ok")
