"""Maintainer tool (Phase 4.36): builds the PUBLISHED evidence file of the domestic importers from the local Phase 4.20 / 4.23 files, WITHOUT copying any restricted provider value.

    python scripts/build_published_evidence.py <replay.sqlite> [output_folder]

The local staging files carry columns from football-data.co.uk, FixtureDownload and football-data.org. They are read here only to know WHICH records production applied; none of their values is written.
For every record the output keeps: competition, season, teams, dates, result, the values recorded by the REDISTRIBUTABLE sources (Wikipedia, openfootball, OpenLigaDB), the original source references,
the production decision, the evidence classification, the confidence and the uncertainty, the licence and the provenance. The classification is computed with the same rule the importer applies in published mode
(`app/store/published_evidence.py`): the same value from at least two distinct redistributable sources. Records that do not meet it are listed with classification `insufficient_redistributable_evidence`
and are NOT applied by the published mode.
<replay.sqlite> is a private store produced by scripts/rebuild_current_state.py; it supplies the OpenLigaDB results the store held back for a date disagreement (never published as such: only their score, date and match id)."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "data" / "supervised" / "phase4" / "p420"))
import stage_helpers as H  # noqa: E402
from store import published_evidence as PE  # noqa: E402

REPLAY = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "evidence" / "published"
OUT.mkdir(parents=True, exist_ok=True)
P4 = ROOT / "data" / "supervised" / "phase4"
COMP_ID = {"EPL": "england:1-premierleague", "LALIGA": "espana:1-liga", "SERIEA": "italy:1-seriea", "LIGUE1": "europe/france:fr1", "BUNDESLIGA": "deutschland:1-bundesliga"}
RESTRICTED = ("footballdatauk_score", "footballdatauk_date", "fixturedownload_score", "fixturedownload_date", "provider_date")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def nn(v) -> bool:
    return not (v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "")


# OpenLigaDB finished matches (values of an ODbL source): the ones the store holds and the ones it held back for a date disagreement
c = sqlite3.connect(f"file:{REPLAY.as_posix()}?mode=ro", uri=True)
oldb = []
for reason, payload in c.execute("SELECT reason, payload FROM quarantine WHERE source='openligadb'"):
    p = json.loads(payload)
    if p.get("result_type") not in (None, "none") and p.get("regulation_home") is not None:
        oldb.append(dict(comp=p.get("competition_key"), home=p.get("home_raw"), away=p.get("away_raw"), date=p.get("match_date"), score=f"{p['regulation_home']}-{p['regulation_away']}", ref=str(p.get("source_ref"))))
for r in c.execute("SELECT m.competition_id, m.home_name, m.away_name, m.match_date, m.home_goals_90, m.away_goals_90, COALESCE((SELECT source_ref FROM match_sources s WHERE s.record_id=m.record_id AND s.source='openligadb' LIMIT 1),'') "
                   "FROM matches m WHERE m.source_system='openligadb' AND m.status='completed'"):
    oldb.append(dict(comp=r[0], home=r[1], away=r[2], date=r[3], score=f"{r[4]}-{r[5]}", ref=str(r[6])))


def oldb_for(comp_key, home, away):
    for o in oldb:
        if o["comp"] == COMP_ID[comp_key] and H.alike(o["home"], home) and H.alike(o["away"], away):
            return o
    return None


rows = []


def add(importer, action, eid, r, comp, record_id, home, away, home_entity, away_entity, exp_status, exp_date, new_date, hg, ag, wscore, wrev, ofdate, olddate, tier, used_restricted, text):
    o = oldb_for(comp, home, away) if action != "set_postponed" else None
    row = dict(evidence_id=eid, importer=importer, action=action, competition_key=comp, season="2026-27", record_id=record_id, home_entity=home_entity, away_entity=away_entity, home=home, away=away,
               expected_store_status=exp_status, expected_store_date=exp_date, new_date=new_date, home_goals=hg, away_goals=ag, wikipedia_score=wscore, wikipedia_revision=wrev, wikipedia_date=None,
               openligadb_score=(o["score"] if o and action in ("add_result", "add_result_with_date", "update_result") else None), openligadb_date=(o["date"] if o else (olddate if nn(olddate) else None)),
               openligadb_ref=(f"matchID {o['ref']}" if o else None), openfootball_score=None, openfootball_date=ofdate, production_tier=tier)
    target = None if hg is None or (isinstance(hg, float) and pd.isna(hg)) else f"{int(hg)}-{int(ag)}"
    need_score = action in ("add_result", "add_result_with_date", "update_result")
    need_date = action in ("update_result", "add_result_with_date", "correct_date")
    ns = type("R", (), {k: v for k, v in row.items()})()
    ok, issues = PE.assess(ns, need_score, need_date, target, new_date)
    if action == "set_postponed":
        ok = False
    why = "; ".join(d for _, d in issues) if issues else ""
    row.update(evidence_classification=PE.TWO if ok else PE.INSUFFICIENT, restricted_cross_check_used_in_production="true" if used_restricted else "false",
               review_decision=(f"{text} | published evidence {'sufficient: reproducible from redistributable sources' if ok else 'NOT sufficient: the production decision also relied on sources whose values cannot be published; not applied by the published mode'}"),
               confidence=("verified_two_redistributable_sources" if ok else "single_or_unverified_in_published_evidence"),
               uncertainty=("" if ok else (why or "decision depends on restricted evidence")), licence="; ".join(f"{k}: {v}" for k, v in PE.ALLOWED_SOURCES.items()),
               provenance=f"Wikipedia revision {int(wrev)} (CC BY-SA 4.0)" + (f"; OpenLigaDB {row['openligadb_ref']} (ODbL 1.0)" if row["openligadb_ref"] else "") + "; store date from openfootball (CC0 1.0)" if nn(wrev) else "openfootball (CC0 1.0); OpenLigaDB (ODbL 1.0)")
    rows.append(row)


for f in sorted((P4 / "p420" / "staging").glob("staged_results_*.csv")):
    d = pd.read_csv(f, encoding="utf-8-sig")
    for r in d.itertuples():
        add("league_results", "update_result", f"LR-{r.record_id.split(':')[-1]}-{r.competition_key}", r, r.competition_key, r.record_id, r.home, r.away, r.home_entity, r.away_entity, r.store_status, r.store_date, str(r.date),
            r.home_goals, r.away_goals, r.wikipedia_score, r.wikipedia_revision, r.store_date, None, r.tier, True, "applied in production 2026-10-28 (Phase 4.21/4.22 domestic results import)")
prop = pd.read_csv(P4 / "p423" / "staging" / "proposed_changes.csv", encoding="utf-8-sig")
for r in prop.itertuples():
    used = any(nn(getattr(r, k, None)) for k in RESTRICTED)
    applied = "applied in production 2026-10-28 (Phase 4.24, strong tier)" if r.tier == "strong" else f"not applied in production (tier {r.tier})"
    add("reconcile", r.action, f"RC-{r.change_id}", r, r.competition_key, r.record_id, r.home, r.away, r.home_entity, r.away_entity, r.expected_store_status, r.expected_store_date, None if not nn(r.new_date) else str(r.new_date),
        r.home_goals if nn(r.home_goals) else None, r.away_goals if nn(r.away_goals) else None, r.wikipedia_score if nn(r.wikipedia_score) else None, r.wikipedia_revision if nn(r.wikipedia_revision) else None,
        r.openfootball_date if nn(r.openfootball_date) else None, r.openligadb_date if nn(r.openligadb_date) else None, r.tier, used, applied)
df = pd.DataFrame(rows)[PE.COLUMNS]
for col in ("home_goals", "away_goals", "wikipedia_revision"):
    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
out = OUT / "published_evidence_2026-10-28.csv"
df.to_csv(out, index=False, encoding="utf-8-sig")
assert not PE.forbidden_columns(df.columns)
manifest = dict(file=out.name, sha256=sha(out), rows=len(df), by_importer_action=df.groupby(["importer", "action"]).size().to_dict().__repr__(), by_classification=df.evidence_classification.value_counts().to_dict(),
                columns=PE.COLUMNS, allowed_sources=PE.ALLOWED_SOURCES, withheld="values of football-data.co.uk, FixtureDownload and football-data.org (scores, dates, provider dates and raw copies)",
                derived_from_local_inputs_sha256={f.name: sha(f) for f in sorted((P4 / "p420" / "staging").glob("staged_results_*.csv"))} | {"proposed_changes.csv": sha(P4 / "p423" / "staging" / "proposed_changes.csv")},
                note="hashes identify the local (unpublished) inputs the decisions come from; they reveal no provider value")
(OUT / "PUBLISHED_EVIDENCE_MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps({k: manifest[k] for k in ("rows", "by_classification", "sha256")}, indent=1))
print(df.groupby(["importer", "action", "evidence_classification"]).size().to_string())
