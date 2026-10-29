"""Shared paths/helpers for the ML data-readiness pipeline (reads the original submission; never writes there)."""
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                       # FootIQ_ML_Data_Readiness
PROJECT = os.path.dirname(OUT)                    # D:\Foot IQ
SUB = os.path.join(PROJECT, "FootIQ_Dataset_Submission")
SUBWORK = os.path.join(SUB, "_build", "work")
RAW = os.path.join(SUB, "_raw_sources")
WORK = os.path.join(HERE, "work")
EXTERNAL = os.path.join(OUT, "raw_external")      # newly downloaded raw files
ENC = "utf-8-sig"
AS_OF = "2026-10-20"
os.makedirs(WORK, exist_ok=True)
os.makedirs(EXTERNAL, exist_ok=True)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# Competition families audited (competition_id in the submission -> family label, level)
FAMILY = {
    "england:1-premierleague": ("Premier League", "league"),
    "espana:1-liga": ("La Liga", "league"),
    "deutschland:1-bundesliga": ("Bundesliga", "league"),
    "italy:1-seriea": ("Serie A", "league"),
    "europe/france:fr1": ("Ligue 1", "league"),
    "champions-league:cl": ("UEFA Champions League", "uefa"),
    "champions-league:el": ("UEFA Europa League", "uefa"),
    "champions-league:conf": ("UEFA Conference League", "uefa"),
    "england:facup": ("FA Cup", "cup"),
    "england:eflcup": ("EFL Cup", "cup"),
    "espana:cup": ("Copa del Rey", "cup"),
    "deutschland:cup": ("DFB-Pokal", "cup"),
    "italy:cup": ("Coppa Italia", "cup"),
    "europe/france:frcup": ("Coupe de France", "cup"),
}
SEASONS = [f"{y}-{str(y + 1)[2:]}" for y in range(2018, 2026)]
