"""Stage 1 (READ-ONLY on all existing files): hashes, baseline integrity, ZIP comparison, dataset integrity, counts."""
import hashlib
import json
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd

P = r"D:\Foot IQ"
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
RDY = os.path.join(P, "FootIQ_ML_Data_Readiness")
OUT = os.path.join(P, "FootIQ_ML_Data_Verification")
EV = os.path.join(OUT, "_evidence")
os.makedirs(EV, exist_ok=True)
ENC = "utf-8-sig"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""):
            h.update(ch)
    return h.hexdigest()


# ------------------------------------------------------------------ 1. critical hashes
crit = []
for d, pat in ((SUB, None), (RDY, None)):
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p):
            crit.append(p)
for d in (os.path.join(SUB, "_build"), os.path.join(RDY, "_build"), os.path.join(SUB, "QA_Reports")):
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p):
            crit.append(p)
for d in (os.path.join(SUB, "_build", "work"), os.path.join(RDY, "_build", "work")):
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p) and os.path.getsize(p) < 400_000_000:
            crit.append(p)
for rel in ("FootIQ_Dataset_Submission.zip", "PROJECT.md", "docs/baseline/BASELINE_AUDIT.md", "docs/baseline/RISK_REGISTER.md",
            "docs/baseline/EVIDENCE_MANIFEST.json", "data/model_artifacts/v27/live_match_model.pkl",
            "data/raw/international_results/results.csv", "data/processed/international_matches.csv",
            "scripts/model_bakeoff_v26.py", "scripts/build_live_predictions_v27.py", "scripts/build_foundation_tables.py"):
    crit.append(os.path.join(P, rel))
rows = []
for p in crit:
    rows.append(dict(path=os.path.relpath(p, P), bytes=os.path.getsize(p), sha256=sha(p)))
for sub in ("FootIQ_Dataset_Submission/_raw_sources/martj42_refresh",):
    d = os.path.join(P, sub)
    for f in sorted(os.listdir(d)):
        if f.endswith(".csv"):
            rows.append(dict(path=f"{sub}/{f}", bytes=os.path.getsize(os.path.join(d, f)), sha256=sha(os.path.join(d, f))))
wpd = os.path.join(RDY, "raw_external", "wikipedia")
h = hashlib.sha256()
for f in sorted(os.listdir(wpd)):
    h.update(f.encode())
    h.update(open(os.path.join(wpd, f), "rb").read())
rows.append(dict(path="FootIQ_ML_Data_Readiness/raw_external/wikipedia/* (aggregate of %d cached pages)" % len(os.listdir(wpd)), bytes=0, sha256=h.hexdigest()))
pd.DataFrame(rows).to_csv(os.path.join(EV, "sha256_critical_inputs_outputs.csv"), index=False)
print("hashed", len(rows))

# ------------------------------------------------------------------ 2. baseline integrity
mism, missing, ok = [], [], 0
for line in open(os.path.join(P, "docs/baseline/capture_2026-10-20/original_files.sha256"), encoding="utf-8"):
    hh, rel = line.rstrip("\n").split("  ", 1)
    p = os.path.join(P, rel)
    if not os.path.exists(p):
        missing.append(rel)
    elif sha(p) != hh:
        mism.append(rel)
    else:
        ok += 1
base = dict(files_listed=ok + len(mism) + len(missing), matching=ok, modified=mism, missing=missing)
json.dump(base, open(os.path.join(EV, "baseline_integrity.json"), "w"), indent=1)
print("baseline", base["files_listed"], ok, len(mism), len(missing))

# ------------------------------------------------------------------ 3. ZIP vs directory
z = zipfile.ZipFile(os.path.join(P, "FootIQ_Dataset_Submission.zip"))
zrows = []
for i in z.infolist():
    rel = i.filename.replace("FootIQ_Dataset_Submission/", "", 1)
    p = os.path.join(SUB, rel)
    if i.is_dir():
        continue
    zh = hashlib.sha256(z.read(i)).hexdigest()
    zrows.append(dict(member=i.filename, in_dir=os.path.exists(p), same_hash=os.path.exists(p) and sha(p) == zh))
zdf = pd.DataFrame(zrows)
zdf.to_csv(os.path.join(EV, "zip_vs_directory.csv"), index=False)
print("zip members", len(zdf), "same", int(zdf.same_hash.sum()))

# ------------------------------------------------------------------ 4. dataset integrity
SPEC = {
    "SUB/01_Historical_International_Matches.csv": dict(id="match_id", date="match_date", comp="competition_id", season=None, scores=["home_score_incl_extra_time", "away_score_incl_extra_time"], nat=["match_date", "home_team", "away_team", "tournament"]),
    "SUB/02_Historical_Club_Matches.csv": dict(id="match_id", date="match_date", comp="competition_id", season="season", scores=["home_goals_regulation", "away_goals_regulation", "home_goals_after_extra_time", "away_goals_after_extra_time", "home_penalties", "away_penalties"], nat=["match_date", "home_team_id", "away_team_id", "competition_id", "stage"]),
    "SUB/03_Recent_Match_Results.csv": dict(id="match_id", date="match_date", comp="competition_id", season="season", scores=["home_goals_regulation", "away_goals_regulation", "home_score_incl_extra_time", "away_score_incl_extra_time"], nat=["match_date", "home_team_id", "away_team_id", "competition_id"]),
    "SUB/04_Football_Players.csv": dict(id="player_id", date="last_seen_date", comp=None, season=None, scores=[], nat=["player_id"]),
    "SUB/05_Player_Match_Statistics.csv": dict(id="player_match_id", date="match_date", comp="competition_name", season="season", scores=["goals", "assists", "shots", "minutes_played"], nat=["match_id", "player_id", "team_id"]),
    "SUB/06_Teams.csv": dict(id="team_id", date="last_match_date", comp=None, season=None, scores=[], nat=["team_id"]),
    "SUB/07_Competitions.csv": dict(id="competition_id", date="last_match_date", comp="competition_id", season="last_season", scores=[], nat=["competition_id"]),
    "SUB/08_Player_Team_Memberships.csv": dict(id="membership_id", date="last_match_date", comp="competition_or_event", season="season", scores=[], nat=["player_id", "team_id", "competition_or_event", "season", "membership_basis"]),
    "SUB/09_Upcoming_Fixtures.csv": dict(id="match_id", date="match_date", comp="competition_id", season="season", scores=[], nat=["match_date", "home_team_id", "away_team_id", "competition_id"]),
    "RDY/04a_LEAGUE_RESULTS_v1.0.csv": dict(id="record_id", date="match_date", comp="competition_id", season="season", scores=["final_score_home_excl_penalties", "final_score_away_excl_penalties", "regulation_score_home", "regulation_score_away", "pen_home", "pen_away"], nat=["competition_id", "season", "match_date", "home_entity_id", "away_entity_id", "stage"]),
    "RDY/04b_DOMESTIC_CUP_RESULTS_v1.0.csv": dict(id="record_id", date="match_date", comp="competition_id", season="season", scores=["final_score_home_excl_penalties", "final_score_away_excl_penalties", "regulation_score_home", "regulation_score_away", "pen_home", "pen_away"], nat=["competition_id", "season", "match_date", "home_entity_id", "away_entity_id", "stage"]),
    "RDY/04c_CONTINENTAL_AND_GLOBAL_RESULTS_v1.0.csv": dict(id="record_id", date="match_date", comp="competition_id", season="season", scores=["final_score_home_excl_penalties", "final_score_away_excl_penalties", "regulation_score_home", "regulation_score_away", "pen_home", "pen_away"], nat=["competition_id", "season", "match_date", "home_entity_id", "away_entity_id", "stage"]),
    "RDY/04d_COMBINED_CLUB_MATCHES_v1.0.csv": dict(id="record_id", date="match_date", comp="competition_id", season="season", scores=["final_score_home_excl_penalties", "final_score_away_excl_penalties", "regulation_score_home", "regulation_score_away", "pen_home", "pen_away"], nat=["competition_id", "season", "match_date", "home_entity_id", "away_entity_id", "stage"]),
    "RDY/04e_UNDATED_LEAGUE_RESULTS_2025-26_v1.0.csv": dict(id=None, date="match_date", comp="competition_id", season="season", scores=["final_home", "final_away"], nat=["competition_id", "home_entity_id", "away_entity_id"]),
    "RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_strict.csv": dict(id="record_id", date="match_date", comp="competition_id", season="season", scores=[], nat=["competition_id", "season", "match_date", "home_entity_id", "away_entity_id", "stage"]),
    "RDY/08_TRAINING_READY_MATCH_DATASET_v1.0_extended.csv": dict(id="record_id", date="match_date", comp="competition_id", season="season", scores=[], nat=["competition_id", "season", "match_date", "home_entity_id", "away_entity_id", "stage"]),
    "RDY/05_CANONICAL_TEAM_IDENTITY_MAPPING.csv": dict(id=None, date=None, comp=None, season=None, scores=[], nat=["source_system", "source_team_key", "country_folder"]),
}
integ = []
for key, sp in SPEC.items():
    base_dir = SUB if key.startswith("SUB/") else RDY
    fn = key.split("/", 1)[1]
    df = pd.read_csv(os.path.join(base_dir, fn), low_memory=False, encoding=ENC)
    d = {}
    d.update(file=key, rows=len(df), columns=df.shape[1])
    if sp["date"]:
        dt = pd.to_datetime(df[sp["date"]], errors="coerce", format="%Y-%m-%d")
        nn = df[sp["date"]].notna()
        d.update(date_min=str(dt.min().date()) if dt.notna().any() else "", date_max=str(dt.max().date()) if dt.notna().any() else "",
                 invalid_dates=int((nn & dt.isna()).sum()), null_dates=int((~nn).sum()))
    d["unique_ids"] = int(df[sp["id"]].nunique()) if sp["id"] else None
    d["duplicate_ids"] = int(df[sp["id"]].duplicated().sum()) if sp["id"] else None
    d["duplicate_natural_key_rows"] = int(df.duplicated(sp["nat"]).sum()) if sp["nat"] else None
    d["unique_matches_natural_key"] = int(len(df.drop_duplicates(sp["nat"]))) if sp["nat"] else None
    d["competitions"] = int(df[sp["comp"]].nunique()) if sp["comp"] else None
    d["seasons"] = int(df[sp["season"]].astype(str).nunique()) if sp["season"] else None
    inv = 0
    for c in sp["scores"]:
        s = pd.to_numeric(df[c], errors="coerce")
        bad = ((s < 0) | (s != s.round())) & s.notna()
        if c != "minutes_played":
            bad |= s > 25
        else:
            bad = (s < 0) | (s > 130)
        inv += int(bad.sum())
    d["invalid_scores_or_values"] = inv
    d["missing_cell_pct"] = round(100 * df.isna().sum().sum() / df.size, 2)
    obj_numeric = [c for c in df.columns if df[c].dtype == object and df[c].notna().sum() > 0 and pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.95]
    d["object_columns_that_look_numeric"] = ";".join(obj_numeric)
    d["top_missing_columns"] = "; ".join(f"{c}={100 * v:.0f}%" for c, v in df.isna().mean().sort_values(ascending=False).head(4).items() if v > 0)
    integ.append(d)
    print(key, len(df), df.shape[1], d.get("date_min"), d.get("date_max"))
pd.DataFrame(integ).to_csv(os.path.join(EV, "dataset_integrity_metrics.csv"), index=False)
