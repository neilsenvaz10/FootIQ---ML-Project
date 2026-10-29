"""Competition-level data freshness (Phase 4.17). One honest record per competition: the latest result the application holds, whether the competition is refreshed when FootIQ starts or is historical
only, the last successful refresh, and warnings about missing coverage. Everything is computed from the data and the synchronisation status; nothing is ever called "live".

Two small tables of EXPECTATIONS are configuration, not computed facts, and are kept here in the open so they can be reviewed and updated:
  EXPECTED_EDITIONS  the edition a competition is currently expected to be playing (empty: all six are yearly club seasons);
  EXPECTED_MATCHES   the number of matches an edition has (so a missing match is a warning); here the Champions League 2026-27 league phase.
"""
from datetime import date
from typing import Optional

import config as C

EXPECTED_EDITIONS: dict = {}                           # no competition of the six has an edition label other than the club season
EXPECTED_MATCHES = {("UCL", "2026-27"): 144}           # the 36-team league phase: 36 x 8 / 2 matches
LEAGUE_PHASE_KEYS = ("UCL",)
STALE_AFTER_DAYS = 30

_LABELS = {"startup_updated": "Updated when FootIQ starts", "historical_only": "Historical only: no automatic updates"}


def _club_season(today: date) -> str:
    y = today.year if today.month >= 7 else today.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def build(df, sync_status: Optional[dict], active: list, live_enabled: bool, sync_mode: str, today: date) -> list:
    """df: the dashboard frame (competition_key, season, stage, date, home, away, home_goals, away_goals). sync_status: the dict of sync.status() (or None).
    active: the competitions the synchronisation refreshes (config). Returns one dict per competition of the approved scope, in scope order."""
    comps_sync = {c["competition_key"]: c for c in (sync_status or {}).get("competitions", [])}
    season_now = _club_season(today)
    out = []
    for comp in C.COMPETITIONS:
        k = comp["key"]
        d = df[df.competition_key == k]
        scored = d[d.home_goals.notna() & d.away_goals.notna()] if len(d) else d
        latest = str(scored.date.max()) if len(scored) else None
        days = (today - date.fromisoformat(latest)).days if latest else None
        updated = bool(live_enabled and k in active)
        s = comps_sync.get(k, {})
        warnings = []

        def warn(text, level="warning"):
            warnings.append(dict(level=level, text=text))

        if updated:
            note = f"Refreshed once each time FootIQ starts from {', '.join(s.get('approved_sources') or ['its approved source'])}; not a live feed."
            if s.get("awaiting_result"):
                warn(f"{s['awaiting_result']} fixture(s) are past their date and have no result in the data (oldest {s.get('oldest_awaiting')}).")
            if s.get("state") == "stale" and not s.get("awaiting_result"):
                warn("The last refresh is older than the staleness limit or failed: " + "; ".join(s.get("state_reasons") or []))
        elif comp["group"] == "Domestic league":
            note = "Automatic updates are not enabled for this league (the data provider's permission and disputed fixture dates are still being resolved)."
        else:
            note = "No update source is approved for this competition; the data is a saved snapshot."
        ongoing = True                                                                # every competition of the six is a yearly club season
        if not updated and ongoing and days is not None and days > STALE_AFTER_DAYS:
            warn(f"The latest result is {days} days old and this competition is not updated automatically.")
        if ongoing:
            want = EXPECTED_EDITIONS.get(k) or season_now
            started = today >= date(int(season_now[:4]), 8, 15)      # club seasons: only complain once the new season can have started
            if started and (not len(d) or int((d.season.astype(str) == want).sum()) == 0):
                warn(f"No matches of the {want} {'edition' if k in EXPECTED_EDITIONS else 'season'} are in the data.")
        for (kk, ed), total in EXPECTED_MATCHES.items():
            if kk != k:
                continue
            dd = d[d.season.astype(str) == ed]
            if k in LEAGUE_PHASE_KEYS:
                dd = dd[dd.stage.astype(str).str.contains(r"Matchday|League", case=False, regex=True) & ~dd.stage.astype(str).str.contains(r"play-?off|knockout|round of|final", case=False, regex=True)]
            have = len(dd.drop_duplicates(["date", "home", "away"])) if len(dd) else 0
            if 0 < have < total:
                warn(f"{ed}: {have} of {total} matches are in the data" + ".")
        if len(d):
            dup = int(d.duplicated(["season", "date", "home", "away"]).sum())
            if dup:
                warn(f"{dup} match(es) appear twice in the data (a known data-quality issue awaiting clean-up); counts and statistics for this competition may include them.")
        out.append(dict(key=k, name=comp["name"], group=comp["group"], latest_result=latest, days_since_latest_result=days, data_status="startup_updated" if updated else "historical_only", data_status_label=_LABELS["startup_updated" if updated else "historical_only"],
                        update_note=note, last_successful_refresh_utc=(s.get("last_successful_external_check_utc") if updated else None), sync_mode=sync_mode if updated else None,
                        has_warnings=any(w["level"] == "warning" for w in warnings), warnings=warnings))
    return out
