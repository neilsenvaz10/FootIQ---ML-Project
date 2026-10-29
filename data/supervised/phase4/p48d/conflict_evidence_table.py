"""Phase 4.8D Stage 1: evidence table for the quarantined conflicts (2 score conflicts, 55 fixture-date disagreements). Read-only on a private copy of production. Nothing is resolved."""
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "app"))
from store import sync  # noqa: E402

OUT = ROOT / "data" / "supervised" / "phase4" / "p48d"
SRC = {"england:1-premierleague": ("EPL", "Premier League", "premierleague.com official fixtures/results and match centre"), "espana:1-liga": ("LALIGA", "La Liga", "laliga.com official calendar and match sheet (acta)")}


def main():
    import shutil
    cp = OUT / "ev_copy.sqlite"
    for e in ("", "-wal", "-shm"):
        Path(str(cp) + e).unlink(missing_ok=True)
        if Path(str(ROOT / "data" / "footiq.sqlite") + e).exists():
            shutil.copyfile(str(ROOT / "data" / "footiq.sqlite") + e, str(cp) + e)
    c = sqlite3.connect(cp)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    resolver = sync.build_resolver(c)
    rows, scores = [], []
    for q in c.execute("SELECT id, source, source_ref, reason, payload FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%' OR reason LIKE 'CONFLICT%' OR reason LIKE 'CONTRADICTORY%' ORDER BY id"):
        pl = json.loads(q["payload"]) if q["payload"] else {}
        comp = pl.get("competition_key")
        he, _ = resolver.resolve("openligadb", comp, pl.get("home_raw", "")) if comp else (None, None)
        ae, _ = resolver.resolve("openligadb", comp, pl.get("away_raw", "")) if comp else (None, None)
        m = re.match(r"DATE_DIFFERENCE: stored (\d{4}-\d\d-\d\d) vs source (\d{4}-\d\d-\d\d)", q["reason"])
        st = None
        if he and ae:
            cand = c.execute("SELECT m.record_id, m.competition_key, m.matchday_no, m.match_date, m.status, m.kickoff_utc, m.home_goals_final gh, m.away_goals_final ga, t1.display_name hn, t2.display_name an FROM matches m "
                             "JOIN teams t1 ON t1.entity_id=m.home_entity_id JOIN teams t2 ON t2.entity_id=m.away_entity_id WHERE m.competition_id=? AND m.season='2026-27' AND m.home_entity_id=? AND m.away_entity_id=?", (comp, he, ae)).fetchall()
            st = cand[0] if len(cand) == 1 else None
        label = SRC.get(comp, ("?", "?", "?"))
        if m and st:
            diff = (__import__("datetime").date.fromisoformat(m.group(2)) - __import__("datetime").date.fromisoformat(m.group(1))).days
            held = "result" if pl.get("status") == "completed" else "none"
            rows.append(dict(quarantine_id=q["id"], kind="DATE_DIFFERENCE", competition=label[1], matchday=st["matchday_no"], home=st["hn"], away=st["an"], stored_date=m.group(1), source_date=m.group(2), difference_days=diff,
                             source_kickoff_utc=pl.get("kickoff_utc"), stored_status=st["status"], source_status=pl.get("status"), source_result_held_back=("%s-%s" % (pl.get("regulation_home"), pl.get("regulation_away"))) if held == "result" else "",
                             stored_kickoff_utc=st["kickoff_utc"] or "", effect_on_app="dispute makes the fixture stricter for new predictions and keeps a verified result out of the table" if held == "result" else "dispute makes the fixture stricter for new predictions under the proposed rule",
                             authoritative_source_required=f"{label[2]} (fixture date and, for a held result, the final score)", independent_confirmation="a second independent results provider or the club's official fixture page",
                             resolution_rule="change the stored date only if the official body publishes the source's date; import a held result only after its date is settled AND the official final score equals the provider's; otherwise keep the stored values and the quarantine"))
        elif q["reason"].startswith(("CONFLICT", "CONTRADICTORY")) and st is not None:
            scores.append(dict(quarantine_id=q["id"], kind=q["reason"].split(":")[0], competition=label[1], matchday=st["matchday_no"], home=st["hn"], away=st["an"], date=st["match_date"], stored_score=f"{st['gh']}-{st['ga']}", stored_origin="openfootball (CC0)",
                               source_claim=q["reason"][:160], authoritative_source_required=f"{label[2]}; plus the clubs' official match reports", independent_confirmation="a second results provider (not OpenLigaDB, not openfootball)",
                               resolution_rule="keep the stored score and the quarantine until the official record is read by a person; correct the row only in a reviewed one-row change with a backup"))
    c.close()
    for f in (cp, Path(str(cp) + "-wal"), Path(str(cp) + "-shm")):
        f.unlink(missing_ok=True)
    with open(OUT / "date_disagreements_evidence_table.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["competition"], r["matchday"] or 0, r["home"])))
    (OUT / "score_conflicts_evidence_table.json").write_text(json.dumps(scores, indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print(len(rows), Counter(r["competition"] for r in rows), Counter(r["difference_days"] for r in rows), "held results:", sum(1 for r in rows if r["source_result_held_back"]))
    print(json.dumps(scores, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
