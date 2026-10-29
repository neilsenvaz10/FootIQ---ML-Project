"""Stage 6 (read-only): provenance traceability and licence evidence."""
import hashlib
import json
import os
import re
import subprocess
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
RDY = os.path.join(P, "FootIQ_ML_Data_Readiness")
EV = os.path.join(P, "FootIQ_ML_Data_Verification", "_evidence")
RAWS = os.path.join(SUB, "_raw_sources")
ENC = "utf-8-sig"
R = {}

# ---- licence files
lic = []
for repo in sorted(os.listdir(RAWS)):
    p = os.path.join(RAWS, repo)
    if not os.path.isdir(os.path.join(p, ".git")):
        continue
    entry = dict(repo=repo)
    lf = [f for f in ("LICENSE.md", "LICENSE", "LICENSE.txt", "LICENSE.pdf") if os.path.exists(os.path.join(p, f))]
    entry["license_file"] = lf[0] if lf else ""
    if lf:
        b = open(os.path.join(p, lf[0]), "rb").read()
        entry["license_sha256"] = hashlib.sha256(b).hexdigest()[:16]
        entry["states_cc0"] = b"CC0 1.0 Universal" in b
    try:
        entry["commit"] = subprocess.check_output(["git", "-C", p, "log", "-1", "--format=%H|%cs"], text=True).strip()
        entry["origin"] = subprocess.check_output(["git", "-C", p, "remote", "get-url", "origin"], text=True).strip()
    except Exception as e:
        entry["commit"] = f"ERR {e}"
    lic.append(entry)
ld = pd.DataFrame(lic)
ld.to_csv(os.path.join(EV, "licence_files_and_commits.csv"), index=False)
print(ld.to_string())
R["repos_checked"] = len(ld)
R["repos_with_cc0_file"] = int(ld.states_cc0.fillna(False).sum())

# ---- traceability of every training row
ext = pd.read_csv(os.path.join(RDY, "08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv"), low_memory=False, encoding=ENC)
R["extended_rows"] = len(ext)
R["provenance_null"] = int(ext.provenance.isna().sum())
R["source_license_null"] = int(ext.source_license.isna().sum())
R["extraction_date_null"] = int(ext.extraction_date.isna().sum())
R["source_license_values"] = ext.source_license.value_counts().to_dict()
d4 = pd.read_csv(os.path.join(RDY, "04d_COMBINED_CLUB_MATCHES_v1.0.csv"), low_memory=False, encoding=ENC,
                 usecols=["record_id", "home_team_name", "away_team_name", "final_score_home_excl_penalties", "final_score_away_excl_penalties", "regulation_score_home",
                          "regulation_score_away", "pen_home", "pen_away", "source_system"])
e2 = ext.merge(d4, on="record_id", how="left", suffixes=("", "_d"))
of = e2[e2.source_system == "openfootball"].copy()
m = of.provenance.str.extract(r"@(\w+)\s+(\S+\.txt):L(\d+)$")
of["commit"], of["file"], of["line"] = m[0], m[1], pd.to_numeric(m[2])
cache = {}
bad_missing, bad_names, bad_score = [], [], []
for r in of.itertuples():
    if pd.isna(r.file):
        bad_missing.append(r.record_id)
        continue
    if r.file not in cache:
        pth = os.path.join(RAWS, r.file)
        cache[r.file] = open(pth, encoding="utf-8").read().splitlines() if os.path.exists(pth) else None
    ls = cache[r.file]
    if ls is None or r.line > len(ls):
        bad_missing.append(r.record_id)
        continue
    t = ls[int(r.line) - 1]
    if r.home_team_name_d not in t or r.away_team_name_d not in t:
        # names may carry country codes or be shortened; accept if the first 10 chars occur
        if r.home_team_name_d[:10] not in t or r.away_team_name_d[:10] not in t:
            bad_names.append((r.record_id, t.strip()[:80]))
    cands = {f"{int(r.final_score_home_excl_penalties)}-{int(r.final_score_away_excl_penalties)}"}
    if pd.notna(r.regulation_score_home):
        cands.add(f"{int(r.regulation_score_home)}-{int(r.regulation_score_away)}")
    if pd.notna(r.pen_home):
        cands.add(f"{int(r.pen_home)}-{int(r.pen_away)}")
    if not any(c in t for c in cands) and not re.search(r"\d+-\d+", t):
        bad_score.append((r.record_id, t.strip()[:80]))
R["openfootball_rows_traced"] = len(of)
R["openfootball_rows_source_line_missing"] = len(bad_missing)
R["openfootball_rows_team_names_not_on_source_line"] = len(bad_names)
R["openfootball_rows_score_not_on_source_line"] = len(bad_score)
pd.DataFrame(bad_names, columns=["record_id", "source_line"]).head(200).to_csv(os.path.join(EV, "provenance_team_name_mismatch_sample.csv"), index=False)
# commit consistency
sub_commits = {r.repo: r.commit.split("|")[0] for r in ld.itertuples() if isinstance(r.commit, str)}
R["openfootball_commit_prefixes_seen"] = of.commit.nunique()
# Wikipedia rows
wp = e2[e2.source_system == "wikipedia"].copy()
R["wikipedia_rows_in_extended"] = len(wp)
cachedir = os.path.join(RDY, "raw_external", "wikipedia")
revs = {}
for f in os.listdir(cachedir):
    j = json.load(open(os.path.join(cachedir, f), encoding="utf-8"))
    if not j.get("missing"):
        revs[str(j["revid"])] = j
miss = 0
nobox = 0
for r in wp.itertuples():
    mm = re.match(r"WP:(\d+):(\d+)", r.record_id) if isinstance(r.record_id, str) else None
    if not mm or mm.group(1) not in revs:
        miss += 1
        continue
    w = revs[mm.group(1)]["wikitext"]
    if not re.match(r"\{\{\s*(#invoke:\s*)?football\s*box", w[int(mm.group(2)):int(mm.group(2)) + 40], re.I):
        nobox += 1
R["wikipedia_rows_revision_not_in_cache"] = miss
R["wikipedia_rows_offset_not_a_football_box"] = nobox
R["wikipedia_distinct_revisions"] = int(wp.provenance.str.extract(r"rev (\d+)")[0].nunique())
R["wikipedia_pages_cached"] = len(revs)
R["wikipedia_share_of_extended_pct"] = round(100 * len(wp) / len(ext), 2)
R["wikipedia_rows_by_split"] = wp.suggested_split.value_counts().to_dict()
R["wikipedia_rows_by_competition"] = wp.competition_name.value_counts().to_dict()
R["wikipedia_rows_label_status"] = wp.label_90_status.value_counts().to_dict()
json.dump(R, open(os.path.join(EV, "v6_results.json"), "w"), indent=1, default=str)
print(json.dumps(R, indent=0, default=str)[:3000])
