"""90-minute label semantics, shared by the completeness, label-validation and feature steps."""
import re

import pandas as pd

LEAGUE_PHASE = re.compile(r"league, matchday|group|matchday|league phase|regular season", re.I)
KNOCKOUT = re.compile(r"knockout|play-?off|round of|final|quarter|semi|round \d|round$|qualifying|preliminary|replay|"
                      r"first round|second round|third round|fourth round|fifth round|last 16|1/\d", re.I)
CONFIRMED_BASES = {"derived_from_goal_minutes", "goalless_no_extra_time_flag",
                   "source_bracket_regulation_score_with_aet_marker", "league_or_group_phase_no_extra_time_possible", "confirmed_by_wikipedia_goal_minutes"}


def phase_kind(competition_type, stage):
    st = str(stage or "")
    if competition_type == "domestic_league":
        return "knockout" if re.search(r"play-?off", st, re.I) else "league"
    if competition_type in ("domestic_cup", "league_cup"):
        return "knockout"
    if LEAGUE_PHASE.search(st) and not re.search(r"knockout|play-?off|round of|final|quarter|semi", st, re.I):
        return "league_phase"
    return "knockout"


def label_status(row):
    """-> (status, reason). status in confirmed / inferred_no_marker / unknown / not_completed"""
    if row["match_status"] not in ("completed", "awarded"):
        return "not_completed", "match status " + str(row["match_status"])
    if row["match_status"] == "awarded":
        return "unknown", "awarded result is not a played 90-minute result"
    if pd.isna(row["reg_home"]) or pd.isna(row["reg_away"]):
        # the only case where a missing regulation score is still safe: league phase / league match, final score is the 90-minute score
        pk = phase_kind(row["competition_type"], row["stage"])
        if pk in ("league", "league_phase") and pd.notna(row["final_excl_pens_home"]) and row["extra_time_played"] != "yes":
            return "confirmed", "league/group-phase match: no extra time exists in the format"
        return "unknown", "regulation score not stated (" + str(row["reg_basis"]) + ")"
    pk = phase_kind(row["competition_type"], row["stage"])
    if pk in ("league", "league_phase"):
        return "confirmed", "league/group-phase match: no extra time exists in the format"
    b = row["reg_basis"]
    if b in CONFIRMED_BASES:
        return "confirmed", "90-minute score stated or derived from goal minutes (" + b + ")"
    if b == "source_plain_score_no_extra_time_marker" or b == "unknown_knockout_score_not_verified_as_90min":
        return "inferred_no_marker", "knockout match with no extra-time/penalty marker; 90-minute status inferred from the absence of a marker"
    return "unknown", "ambiguous: " + str(b)
