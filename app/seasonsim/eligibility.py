"""Data-quality gate for a season simulation: Ready / Provisional / Not eligible, with reasons. Reads the store only."""
import json
import sqlite3
from datetime import date
from typing import Optional

import gameweeks as gw

from . import rules, settings

COMPLETED = ("completed", "awarded")
BLOCKING_STATUSES = ("cancelled", "abandoned")        # decision D7 (how to treat them) is unresolved: any such fixture blocks the simulation


def assess(conn: sqlite3.Connection, key: str, season: str, today: Optional[date] = None) -> dict:
    gw.check_league(key)
    cfg = settings.load()
    th = cfg["eligibility"]
    today = today or gw.today_utc()
    rows = [dict(r) for r in conn.execute("SELECT record_id, match_date, status, home_entity_id, away_entity_id, kickoff_utc FROM matches WHERE competition_key=? AND season=? AND kind='club'", (key, season))]
    info = rules.profile_info(key, season)
    out = dict(competition_key=key, season=season, today_utc=today.isoformat(), rule_profile=info, scoreline=dict(method=cfg.get("scoreline_method"), validation=cfg.get("scoreline_validation")),
               thresholds=th, in_initial_scope=key in cfg["initial_scope"])
    if not rows:
        return dict(out, state="not_eligible", can_simulate=False, reasons=[f"no fixtures stored for {key} {season}"], counts={})
    done = [r for r in rows if r["status"] in COMPLETED]
    eff = [gw.effective_status(r["status"], r["match_date"], today) for r in rows]
    missing = [r for r, e in zip(rows, eff) if e == "awaiting_result"]
    postponed = [r for r in rows if r["status"] == "postponed"]
    blocking = [r for r in rows if r["status"] in BLOCKING_STATUSES]
    no_identity = [r for r in rows if not r["home_entity_id"] or not r["away_entity_id"]]
    latest = max((r["match_date"] for r in done), default=None)
    stale = (today - date.fromisoformat(latest)).days if latest else None
    denominator = len(done) + len(missing)
    share = len(missing) / denominator if denominator else 1.0
    held = conn.execute("SELECT COUNT(*) FROM quarantine WHERE reason LIKE 'DATE_DIFFERENCE%' AND json_extract(payload, '$.competition_key')=(SELECT competition_id FROM matches WHERE competition_key=? AND season=? LIMIT 1)", (key, season)).fetchone()[0]
    reasons, notes = [], []
    state = "ready"
    if not done:
        state, reasons = "not_eligible", ["no verified result stored for this season yet"]
    else:
        if share > th["provisional_max_missing_share"] or stale > th["provisional_max_stale_days"]:
            state = "not_eligible"
        elif share > th["ready_max_missing_share"] or stale > th["ready_max_stale_days"]:
            state = "provisional"
        if len(missing):
            reasons.append(f"{len(missing)} fixture(s) dated up to today have no verified result ({share:.1%} of played-date fixtures); they are simulated like future fixtures")
        if stale is not None and stale > th["ready_max_stale_days"]:
            reasons.append(f"the newest verified result is {stale} days old ({latest})")
    if blocking:
        state = "not_eligible"
        reasons.append(f"{len(blocking)} cancelled or abandoned fixture(s): their treatment is an open decision (D7), so the simulation is blocked")
    if no_identity:
        state = "not_eligible"
        reasons.append(f"{len(no_identity)} fixture(s) have an unresolved team identity")
    if postponed:
        notes.append(f"{len(postponed)} postponed fixture(s) are simulated as remaining matches whatever their stored date")
    if held:
        notes.append(f"{held} source date disagreement(s) are held for review in this competition (the stored dates are used)")
    blockers = []
    if state == "not_eligible":
        blockers.append("data quality: Not eligible")
    if not info["usable"]:
        blockers.append(f"league rules blocked: {info['reason']}")
    if key not in cfg["initial_scope"]:
        blockers.append("outside the approved initial scope (Bundesliga and La Liga); needs your approval")
    if not cfg.get("scoreline_method"):
        blockers.append("final-position predictions are disabled: no scoreline method has passed the predeclared acceptance criteria")
    po_cfg = cfg.get("points_only", {})
    po_blockers = []
    if not po_cfg.get("enabled"):
        po_blockers.append("points-only mode is switched off")
    if state == "not_eligible":
        po_blockers.append("data quality: Not eligible")
    if key not in po_cfg.get("scope", []):
        po_blockers.append("outside the approved scope of the points-only mode (the five domestic leagues)")
    pb_cfg = po_cfg.get("position_bounds", {})
    pb_blockers = []
    if not pb_cfg.get("enabled"):
        pb_blockers.append("position ranges are switched off")
    if key not in pb_cfg.get("scope", []):
        pb_blockers.append("position ranges are available for the Bundesliga and La Liga only: they need verified tie-break settings for the league, which the other leagues do not have yet")
    if not info["usable"]:
        pb_blockers.append(f"league rules blocked: {info['reason']}")
    elif not info.get("bounds_ready"):
        pb_blockers.append("the rule profile has no verified settings for position ranges")
    points_only = dict(label=po_cfg.get("label", "Experimental \u2014 Points-only simulation"), can_run=not po_blockers, blockers=po_blockers,
                       note="Simulates win / draw / loss only (3 / 1 / 0 points). No score is invented and no tie is settled by chance. Title, top-four and relegation appear only as lower and upper bounds, never as exact probabilities.",
                       position_bounds=dict(available=not pb_blockers, blockers=pb_blockers, bands=["title", "top4", "relegation"]))
    return dict(out, points_only=points_only, state=state, reasons=reasons, notes=notes, blockers=blockers, can_simulate=not blockers,
                counts=dict(fixtures=len(rows), completed=len(done), missing_results=len(missing), postponed=len(postponed), cancelled_or_abandoned=len(blocking), held_date_disagreements=held,
                            remaining_to_simulate=len(rows) - len(done), kickoff_known=sum(1 for r in rows if r["kickoff_utc"])),
                latest_result=latest, days_since_latest_result=stale, missing_share=share)
