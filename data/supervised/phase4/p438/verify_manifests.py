"""Phase 4.38 gate: checks the FINAL inclusion / exclusion manifests (read-only). Exit 1 if any check fails. Writes out/manifest_gate.json"""
import csv, json, re, sys
from pathlib import Path
ROOT = Path("D:/Foot IQ")
O = ROOT / "data/supervised/phase4/p437/out"
inc = list(csv.DictReader(open(O / "final_inclusion_manifest.csv", encoding="utf-8")))
exc = {r["path"]: r["reason"] for r in csv.DictReader(open(O / "final_exclusion_manifest.csv", encoding="utf-8"))}
paths = [r["publish_path"] for r in inc]
srcs = [r["path"] for r in inc]
res = {}
FORBID_PATH = re.compile(r"statsbomb|footballdatauk_|fixturedownload|\.sqlite|\.db$|__pycache__|\.pyc$|(^|/)\.env($|\.local)|data/backups/|data/raw/fifa/|data/snapshots/footballdata/|data/local_private/|data/release_candidates/|pytest_tmp|data/run/|\.pem$|\.key$|contact\.local|matchday_validation_v210|worldcup_matchday_v29_|data/provider_cache", re.I)
res["forbidden_path_hits"] = [p for p in paths if FORBID_PATH.search(p) and "cc0_extracts" not in p and not p.startswith(("outputs/", "tests/"))]       # outputs/ reports and tests only NAME the archived pipelines (reviewed: no provider field)
res["reviewed_outputs_named_after_archived_pipelines"] = sum(1 for p in paths if FORBID_PATH.search(p) and p.startswith("outputs/"))
ORIG = ["p413/date_disputes.csv", "date_dispute_resolution.csv", "held_EPL.csv", "held_LALIGA.csv", "held_LIGUE1.csv", "held_SERIEA.csv", "staged_results_EPL.csv", "staged_results_LIGUE1.csv", "staged_results_SERIEA.csv",
        "p423/staging/date_reconciliation.csv", "p423/staging/proposed_changes.csv", "P4_13B_DATE_VERIFICATION_SHEET.csv"]
res["unsanitized_evidence_csv_included"] = [p for p in srcs if any(p.endswith(o) for o in ORIG) and not p.startswith("data/evidence/sanitized/")]
res["sanitized_evidence_files_included"] = sum(p.startswith("data/evidence/sanitized/") and p.endswith(".csv") for p in paths)
# data files: restricted words in CSV headers
RW = re.compile(r"football-?data|footballdata|fixturedownload|api-?football|provider_|statsbomb", re.I)
hdr = []
for r in inc:
    p = ROOT / r["path"]
    if p.suffix.lower() == ".csv" and p.stat().st_size < 200_000_000:
        with open(p, encoding="utf-8-sig", errors="replace") as fh:
            h = fh.readline()
        if RW.search(h) and "docs/" not in r["path"] and "p425" not in r["path"] and "p433" not in r["path"] and "p426" not in r["path"] and "p432" not in r["path"] and "FootIQ_Dataset_Submission/1" not in r["path"] and "fresh_results_source_research" not in r["path"]:
            hdr.append((r["path"], RW.search(h).group(0)))
res["csv_headers_with_restricted_words"] = hdr
# dashboard files: provider / news rows
import pandas as pd
m = pd.read_csv(ROOT / "data/release_candidates/miniproject/matches.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
res["dashboard_rows_not_from_allowed_sources"] = int((~m.source.isin({"openfootball", "martj42/international_results", "wikipedia", "openligadb"})).sum())
res["published_miniproject_publish_paths"] = sorted(r["publish_path"] for r in inc if r["publish_path"].startswith("data/miniproject/"))
res["miniproject_originals_excluded"] = all(p in exc for p in ("data/miniproject/matches.csv", "data/miniproject/data_audit.csv", "data/miniproject/season_coverage.csv"))
# credentials in included text files
SEC = re.compile(r"(api[_-]?key|token|secret|password|authorization)[\"']?\s*[:=]\s*[\"']?(?!<|\$|your|xxx|changeme|example|none|null|true|false|\{)[A-Za-z0-9_\-]{24,}", re.I)
sec = []
for r in inc:
    p = ROOT / r["path"]
    if p.suffix.lower() in (".py", ".js", ".jsx", ".json", ".md", ".txt", ".ps1", ".html", ".yml", ".yaml", ".example", ".csv", "") and p.stat().st_size <= 5_000_000:
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for mm in SEC.finditer(t):
            if "TESTTOKEN" in mm.group(0).upper():
                continue                                               # dummy token of a unit test
            sec.append((r["path"], mm.group(1)))
res["credential_pattern_hits"] = sec[:20]
res["personal_contact_file_included"] = any("contact.local" in p for p in paths)
res["lfs_files"] = [r["path"] for r in inc if r["decision"] == "LFS"]
res["counts"] = dict(included=len(inc), git=sum(r["decision"] == "GIT" for r in inc), lfs=sum(r["decision"] == "LFS" for r in inc), excluded=len(exc))
res["excluded_by_legal_reason"] = sum(1 for v in exc.values() if re.search("tatsbomb|API-Football|football-data|FixtureDownload|FIFA|copyright|restricted category", v, re.I))
fail = bool(res["forbidden_path_hits"] or res["unsanitized_evidence_csv_included"] or res["csv_headers_with_restricted_words"] or res["dashboard_rows_not_from_allowed_sources"] or res["credential_pattern_hits"]
            or res["personal_contact_file_included"] or not res["miniproject_originals_excluded"] or res["sanitized_evidence_files_included"] != 12 or res["counts"]["lfs"] != 8)
res["gate"] = "FAIL" if fail else "PASS"
json.dump(res, open(ROOT / "data/supervised/phase4/p438/out/manifest_gate.json", "w"), indent=1)
print(json.dumps(res, indent=1)[:3500]); sys.exit(1 if fail else 0)
