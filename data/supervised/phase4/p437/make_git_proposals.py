"""Phase 4.37: writes the PROPOSED .gitignore, .gitattributes, path lists, command sequence and commit message into out/. Nothing is applied or executed."""
import csv, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "out"
MIB = 1024 * 1024
def wr(path, text, encoding="utf-8"):
    with open(path, "w", encoding=encoding, newline=chr(10)) as fh:
        fh.write(text)


tot = json.load(open(OUT / "final_totals.json"))
plan = list(csv.DictReader(open(OUT / "restricted_removal_plan.csv", encoding="utf-8")))
inc = list(csv.DictReader(open(OUT / "final_inclusion_manifest.csv", encoding="utf-8")))
old = (ROOT / "data/supervised/phase4/p434/proposed.gitignore").read_text(encoding="utf-8").splitlines()
ign = [l for l in old if not l.startswith("# PROPOSED")]
add = ["", "# --- Phase 4.37: restricted originals that stay on the maintainer's machine (sanitized copies are in data/evidence/sanitized and the CC0 extracts)",
       "data/local_private/", "data/release_candidates/",
       "data/supervised/phase4/p413/date_disputes.csv", "data/supervised/phase4/p420/staging/date_dispute_resolution.csv", "data/supervised/phase4/p420/staging/held_*.csv", "data/supervised/phase4/p420/staging/staged_results_*.csv",
       "data/supervised/phase4/p4*/staging/raw/footballdatauk_*", "data/supervised/phase4/p4*/staging/raw/fixturedownload_*", "data/supervised/phase4/p4*/staging/raw/evidence.json", "data/supervised/phase4/p423/staging/date_reconciliation*.csv", "data/supervised/phase4/p423/staging/proposed_changes.csv",
       "data/supervised/phase4/p423/dryrun/", "data/supervised/phase4/p423/rehearsal/", "data/supervised/phase4/p424/apply/", "data/supervised/phase4/p424/final_dryrun/", "data/supervised/phase4/p424/preflight_dryrun/",
       "data/supervised/phase4/p412/report.json", "data/supervised/phase4/p413/classification_summary.json", "data/supervised/phase4/p416/audit_report.json", "data/supervised/phase4/p416/wc2026_dedup_proposal.csv",
       "docs/mini-project/phase4/P4_13B_DATE_VERIFICATION_SHEET.csv", "data/snapshots/request_ledger.jsonl", "FootIQ_ML_Data_Verification/12_PLAYER_STATISTICS_COVERAGE.csv",
       "# --- API-Football, StatsBomb-derived and media-sourced files (also removed from the index, see git_rm_paths_restricted.txt)",
       "data/processed/matchday_validation_v210*.csv", "data/processed/worldcup_matchday_v29_*.csv", "data/processed/worldcup_2026_knockout_results_verified.csv", "data/processed/worldcup_manual_results.csv",
       "data/processed/worldcup_full_validation_fixture_audit_*.csv", "data/processed/mls_*_snapshot_*.csv", "data/processed/psg_aston_villa_super_cup_snapshot_*.csv",
       "!data/evidence/sanitized/", "!FootIQ_Dataset_Submission/cc0_extracts/",
       "!FootIQ_ML_Training_Preparation/_build/work/build_summary.json", "!FootIQ_ML_Training_Preparation/_build/work/calendar_audit_files.csv", "!FootIQ_ML_Training_Preparation/_build/work/run1_hashes.json"]
wr(OUT / "proposed.gitignore", "# PROPOSED .gitignore (Phase 4.37). Not applied. Supersedes the Phase 4.34 proposal.\n" + "\n".join(ign + add) + "\n", encoding="utf-8")
ga = ["# PROPOSED .gitattributes (Phase 4.37). Not applied.", "*.py   text eol=lf", "*.js   text eol=lf", "*.jsx  text eol=lf", "*.json text eol=lf", "*.md   text eol=lf", "*.css  text eol=lf", "*.html text eol=lf", "*.ps1  text eol=crlf",
      "", "data/raw/** -text", "", "*.pkl  binary", "*.pdf  binary", "*.xlsx binary", "*.png  binary", "*.sqlite binary", "",
      f"# Git LFS: explicit files only ({tot['lfs_files']} files, {tot['lfs_bytes'] / MIB:.1f} MiB). The same list as Phase 4.34/4.35."]
ga += [f"{p:<90} filter=lfs diff=lfs merge=lfs -text" for p, b in tot["lfs"]]
wr(OUT / "proposed.gitattributes", "\n".join(ga) + "\n", encoding="utf-8")
rm = [r["path"] for r in plan if r["action"] == "git rm --cached" and r["git_state"] == "tracked" and r["category"] in "ABCDE"]
wr(OUT / "git_rm_paths_restricted.txt", "\n".join(rm) + "\n", encoding="utf-8")
opt = [r["path"] for r in plan if r["action"] == "git rm --cached" and r["git_state"] == "tracked" and r["category"] == "X"]
wr(OUT / "git_rm_paths_optional_regenerable.txt", "\n".join(opt) + "\n", encoding="utf-8")
wr(OUT / "git_add_paths.txt", "\n".join(sorted(r["publish_path"] for r in inc)) + "\n", encoding="utf-8")
wr(OUT / "proposed_commit_message.txt", """Publish reproducible FootIQ: six-competition store rebuild, frozen models, licence-clean datasets

- Rebuild the current store from repository inputs only (scripts/rebuild_current_state.py snapshot): openfootball (CC0), Wikipedia (CC BY-SA 4.0), OpenLigaDB (ODbL 1.0)
- Add published/attested evidence importer modes, sanitized evidence CSVs and CC0-only player extracts
- Add DATA_LICENSES.md with source, licence, verification and attribution for every dataset
- Stop tracking API-Football-derived, StatsBomb-derived and FIFA/news-sourced data files (forward-only; earlier commits still contain them)
- Replace data/miniproject dashboard CSVs by copies without the 130 provider/news-sourced World Cup 2026 rows
- Track the 8 large training files through Git LFS

No source-code licence is added by this commit.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
""", encoding="utf-8")
cmd = f"""# Phase 4.37 PROPOSED Git command sequence. NOTHING HERE HAS BEEN RUN. Review, then run step by step from D:\Foot IQ in Git Bash.
# 0. decisions needed first: see report section 8 (history exposure, source-code licence, Wikipedia/ODbL stance, LFS quota).
git status --short | head                                   # expect only the files reviewed in Phase 4.37
git switch -c release/github-publication                    # leave feat/club-ml-v2 untouched

# 1. sanitized replacements for the three dashboard CSVs (originals kept locally, git-ignored)
mkdir -p data/local_private/miniproject
cp data/miniproject/matches.csv data/miniproject/data_audit.csv data/miniproject/season_coverage.csv data/local_private/miniproject/
cp data/release_candidates/miniproject/*.csv data/miniproject/

# 2. ignore and attribute rules
cp data/supervised/phase4/p437/out/proposed.gitignore .gitignore
cp data/supervised/phase4/p437/out/proposed.gitattributes .gitattributes
git lfs install

# 3. forward-only removal from the index (files stay on disk; history is NOT rewritten)
git rm --cached --pathspec-from-file=data/supervised/phase4/p437/out/git_rm_paths_restricted.txt          # {len(rm)} tracked restricted files
# optional (regenerable / copyright PDFs, not a licence blocker for A-E): git rm --cached --pathspec-from-file=data/supervised/phase4/p437/out/git_rm_paths_optional_regenerable.txt   # {len(opt)} files

# 4. add exactly the reviewed set ({len(inc)} files, {tot['git_files']} Git + {tot['lfs_files']} LFS)
git add --pathspec-from-file=data/supervised/phase4/p437/out/git_add_paths.txt

# 5. verify before committing
git lfs ls-files | wc -l                                    # expect {tot['lfs_files']}
git diff --cached --name-only | wc -l
git diff --cached --name-only | grep -Ei 'statsbomb|footballdatauk|fixturedownload|matchday_validation_v210|data/raw/fifa|data/snapshots/footballdata' && echo STOP || echo clean
git diff --cached --stat | tail -1
.venv/Scripts/python.exe -X utf8 data/supervised/phase4/p437/final_manifest.py                              # re-scan: residual data files with markers must be label-only

# 6. commit (message in data/supervised/phase4/p437/out/proposed_commit_message.txt)
git commit -F data/supervised/phase4/p437/out/proposed_commit_message.txt

# 7. push (only after the history decision, report section 8)
git push -u origin release/github-publication
"""
wr(OUT / "git_commands.sh.txt", cmd, encoding="utf-8")
print(len(rm), "restricted rm paths;", len(opt), "optional;", len(inc), "add paths")
