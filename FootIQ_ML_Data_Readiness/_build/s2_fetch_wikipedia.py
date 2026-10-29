"""Fetch the Wikipedia pages (CC BY-SA 4.0) used to fill the audited gaps and to cross-validate overlaps."""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
from wiki_fetch import fetch  # noqa

D = "–"
PAGES = []


def add(comp, season, title, role):
    PAGES.append((comp, season, title, role))


for s, role in (("2025", "fill"), ("2024", "validate")):
    y2 = str(int(s) + 1)[2:]
    for comp, fam in (("UEFA Europa League", "UEFA Europa League"), ("UEFA Conference League", "UEFA Conference League")):
        add(fam, f"{s}-{y2}", f"{s}{D}{y2} {comp} league phase", role)
        add(fam, f"{s}-{y2}", f"{s}{D}{y2} {comp} knockout phase", role)
add("UEFA Champions League", "2025-26", f"2025{D}26 UEFA Champions League league phase", "validate")
add("UEFA Champions League", "2025-26", f"2025{D}26 UEFA Champions League knockout phase", "validate")
for s in ("2018", "2019"):
    y2 = str(int(s) + 1)[2:]
    add("UEFA Europa League", f"{s}-{y2}", f"{s}{D}{y2} UEFA Europa League group stage", "fill")
    add("UEFA Europa League", f"{s}-{y2}", f"{s}{D}{y2} UEFA Europa League knockout phase", "fill")
cups = {"FA Cup": "FA Cup", "EFL Cup": "EFL Cup", "Copa del Rey": "Copa del Rey", "Coppa Italia": "Coppa Italia",
        "Coupe de France": "Coupe de France", "DFB-Pokal": "DFB-Pokal"}
for fam, t in cups.items():
    add(fam, "2025-26", f"2025{D}26 {t}", "fill")
for fam, t in (("FA Cup", "FA Cup"), ("Copa del Rey", "Copa del Rey"), ("Coppa Italia", "Coppa Italia"),
               ("Coupe de France", "Coupe de France"), ("DFB-Pokal", "DFB-Pokal"), ("EFL Cup", "EFL Cup")):
    add(fam, "2024-25", f"2024{D}25 {t}", "validate")
for y in range(2018, 2024):
    y2 = str(y + 1)[2:]
    for fam in ("Copa del Rey", "Coppa Italia", "Coupe de France"):
        add(fam, f"{y}-{y2}", f"{y}{D}{y2} {fam}", "fill" if not (fam != "Coupe de France" and y >= 2020) else "validate")

# 2026-27 (completed matches before 2026-10-01 only are kept later, by date)
for fam, t in (("UEFA Champions League", "UEFA Champions League league phase"), ("UEFA Europa League", "UEFA Europa League league phase"),
               ("UEFA Conference League", "UEFA Conference League league phase")):
    add(fam, "2026-27", f"2026{D}27 {t}", "fill")
for fam in ("FA Cup", "EFL Cup", "Copa del Rey", "Coppa Italia", "Coupe de France", "DFB-Pokal"):
    add(fam, "2026-27", f"2026{D}27 {fam}", "fill")

if __name__ == "__main__":
    rows = []
    for comp, season, title, role in PAGES:
        try:
            r = fetch(title)
        except Exception as e:  # noqa
            print("ERR", title, e, flush=True)
            continue
        rows.append(dict(competition=comp, season=season, role=role, title=title,
                         missing=r.get("missing", False), revid=r.get("revid"), revision_timestamp=r.get("timestamp"),
                         url=r.get("url"), retrieved=r.get("retrieved"), chars=len(r.get("wikitext", ""))))
        print(len(rows), "of", len(PAGES), title, flush=True)
    with open(os.path.join(WORK, "wikipedia_pages.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
