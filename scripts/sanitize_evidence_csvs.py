"""Phase 4.37 maintainer tool: writes SANITIZED copies of the 11 Phase 4.13 / 4.20 / 4.23 evidence CSVs that carry values of restricted providers (football-data.co.uk, FixtureDownload, football-data.org).
Reads the local originals (never changed), writes data/evidence/sanitized/<name> and SANITIZATION_MANIFEST.json.
Rules: (1) only whitelisted columns survive; every provider column and every column DERIVED from a provider value (e.g. diff_days = provider date - stored date) is dropped;
(2) a date or score cell survives only when a REDISTRIBUTABLE source in the same row (Wikipedia, openfootball, OpenLigaDB, the stored fixture) carries the same value, otherwise it is blanked and counted;
(3) free-text columns survive only when they contain no restricted-provider name or value; otherwise they are dropped. Removing a column is NOT treated as proof of redistribution rights: the check is by value."""
import hashlib, json, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P4 = ROOT / "data" / "supervised" / "phase4"
OUT = ROOT / "data" / "evidence" / "sanitized"
RESTRICT = re.compile(r"football-?data|footballdata|fixturedownload|fixture download|api-?football|provider|statsbomb", re.I)
FILES = {   # path -> (kept columns, {column: allowed-source columns that must carry the same value})
    "p413/date_disputes.csv": (["league", "matchday", "home", "away", "stored_date", "stored_kickoff_utc", "stored_time_precision", "stored_weekday", "stored_status", "stored_source"], {}),
    "p420/staging/date_dispute_resolution.csv": (["league", "matchday", "home", "away", "store_date", "openfootball_now", "openligadb_date", "record_id", "resolved_date"], {"resolved_date": ["openfootball_now", "openligadb_date", "store_date"]}),
    "p420/staging/held_EPL.csv": (["competition_key", "season", "record_id", "home_entity", "away_entity", "home", "away", "store_status", "store_date", "wikipedia_score", "wikipedia_revision", "wikipedia_revision_time"], {}),
    "p420/staging/held_LALIGA.csv": (["competition_key", "season", "record_id", "home_entity", "away_entity", "home", "away", "store_status", "store_date", "wikipedia_score", "wikipedia_revision", "wikipedia_revision_time", "openfootball_date"], {}),
    "p420/staging/held_LIGUE1.csv": (["competition_key", "season", "record_id", "home_entity", "away_entity", "home", "away", "store_status", "store_date", "wikipedia_score", "wikipedia_revision", "wikipedia_revision_time", "openfootball_date"], {}),
    "p420/staging/held_SERIEA.csv": (["competition_key", "season", "record_id", "home_entity", "away_entity", "home", "away", "store_status", "store_date", "wikipedia_score", "wikipedia_revision", "wikipedia_revision_time"], {}),
    "p420/staging/staged_results_EPL.csv": (["competition_key", "season", "record_id", "home_entity", "away_entity", "home", "away", "store_status", "store_date", "wikipedia_score", "wikipedia_revision", "wikipedia_revision_time", "tier", "date", "home_goals", "away_goals"], {"date": ["store_date"]}),
    "p420/staging/staged_results_LIGUE1.csv": (["competition_key", "season", "record_id", "home_entity", "away_entity", "home", "away", "store_status", "store_date", "wikipedia_score", "wikipedia_revision", "wikipedia_revision_time", "tier", "date", "home_goals", "away_goals"], {"date": ["store_date"]}),
    "p420/staging/staged_results_SERIEA.csv": (["competition_key", "season", "record_id", "home_entity", "away_entity", "home", "away", "store_status", "store_date", "wikipedia_score", "wikipedia_revision", "wikipedia_revision_time", "tier", "date", "home_goals", "away_goals"], {"date": ["store_date"]}),
    "p423/staging/date_reconciliation.csv": (["league", "matchday", "home", "away", "record_id", "store_status", "store_date", "openfootball_now", "openligadb", "action", "proposed_date"], {"proposed_date": ["openfootball_now", "openligadb", "store_date"]}),
    "docs/mini-project/phase4/P4_13B_DATE_VERIFICATION_SHEET.csv": (["order", "league", "matchday", "home", "away", "database_record_id", "stored_date", "stored_weekday", "second_source_openligadb_date", "official_date", "official_kickoff_local", "official_score_if_played",
                                                                  "official_source_url", "page_checked_on", "verdict_provider_stored_other", "reviewer_initials", "notes"], {}),
    "p423/staging/proposed_changes.csv": (["change_id", "record_id", "competition_key", "home", "away", "home_entity", "away_entity", "action", "tier", "expected_store_status", "expected_store_date", "new_date", "home_goals", "away_goals", "wikipedia_score", "wikipedia_revision", "openfootball_date", "openligadb_date"],
                                          {"new_date": ["expected_store_date", "openfootball_date", "openligadb_date"]}),
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = dict(rule=__doc__.split("\n")[1:6], files={})
    for rel, (keep, rules) in FILES.items():
        src = ROOT / rel if rel.startswith("docs/") else P4 / rel
        df = pd.read_csv(src, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        dropped = [c for c in df.columns if c not in keep]
        out = df[[c for c in keep if c in df.columns]].copy()
        out = out.rename(columns={"verdict_provider_stored_other": "verdict_stored_or_other"})     # the column NAME mentions the provider; it holds the reviewer's verdict (empty in the sheet)
        withheld = {}
        for col, allowed in rules.items():
            for i, v in out[col].items():
                if v and not any(df.at[i, a] == v for a in allowed if a in df.columns and df.at[i, a]):
                    out.at[i, col] = ""
                    withheld[col] = withheld.get(col, 0) + 1
        # a goals pair must equal the Wikipedia score of the same row
        if "home_goals" in out.columns and "wikipedia_score" in out.columns:
            for i, r in out.iterrows():
                if r["home_goals"] != "":
                    out.at[i, "home_goals"], out.at[i, "away_goals"] = str(int(float(r["home_goals"]))), str(int(float(r["away_goals"])))
                    r = out.loc[i]
                if r["home_goals"] != "" and f"{r['home_goals']}-{r['away_goals']}" != str(r["wikipedia_score"]).replace(" ", ""):
                    out.at[i, "home_goals"] = out.at[i, "away_goals"] = ""
                    withheld["goals"] = withheld.get("goals", 0) + 1
        if "tier" in out.columns:                                               # the tier NAME mentions the word provider; the value carries no provider data
            out["tier"] = out["tier"].replace({"provider_assisted": "needed_restricted_source"})
        # free text kept columns must be clean
        for c in out.columns:
            bad = out[c].astype(str).str.contains(RESTRICT).sum()
            if bad:
                raise SystemExit(f"{rel}: kept column {c} still mentions a restricted provider in {bad} cells")
        name = Path(rel).name if rel.startswith("docs/") else rel.replace("/", "__")
        out.to_csv(OUT / name, index=False, encoding="utf-8-sig")
        manifest["files"][name] = dict(source=rel if rel.startswith("docs/") else f"data/supervised/phase4/{rel}", source_sha256=sha(src), rows=len(out), kept_columns=list(out.columns), dropped_columns=dropped, values_withheld=withheld, sha256=sha(OUT / name))
    (OUT / "SANITIZATION_MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: dict(rows=v["rows"], dropped=len(v["dropped_columns"]), withheld=v["values_withheld"]) for k, v in manifest["files"].items()}, indent=1))


main()
