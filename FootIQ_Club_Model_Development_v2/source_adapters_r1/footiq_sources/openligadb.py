"""OpenLigaDB adapter (api.openligadb.de).

Verified terms (official pages read 2026-10-21, see docs/01_SOURCE_PERMISSIONS.md):
  data: ODbL 1.0, free incl. commercial, attribution "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0", share-alike only for publicly distributed modified databases;
  API: no auth, 60 requests/min/IP (swagger), "please retrieve sparingly": poll getlastchangedate, full data only on change, outside live matches only a few polls per day, jitter,
  local caching, exponential back-off on 429/5xx, descriptive User-Agent with contact; no accuracy guarantee (user-entered data, no editorial review).
Result types are taken from the explicit `resultTypeKind` (After90Minutes / AfterExtraTime / AfterPenalties / HalfTime / Unknown); a final score is never assumed to be a 90-minute score.
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from .common import AdapterConfig, HttpClient, SnapshotStore, StagingRecord, utc_now

BASE = "https://api.openligadb.de"
SOURCE = "openligadb"
LICENCE = "ODbL-1.0"
ATTRIBUTION = "Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0"
MATCH_DURATION_PAD_H = 3.0                      # a match is "in progress" for this long after kickoff when not finished
# only league/season pairs whose behaviour was verified; others must be added after a validation run
VERIFIED_LEAGUES = {("bl1", "2026"): "German Bundesliga 2026-27 (deutschland:1-bundesliga)"}
COMPETITION_MAP = {"bl1": "deutschland:1-bundesliga"}


def _parse_utc(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def regulation_score(match: dict):
    """Returns (home, away, result_type, label_eligible, flags). Never infers 90-minute from a bare final score."""
    results = match.get("matchResults") or []
    after90 = [r for r in results if r.get("resultTypeKind") == "After90Minutes"]
    kinds = {r.get("resultTypeKind") for r in results}
    if len(after90) == 1:
        r = after90[0]
        return r["pointsTeam1"], r["pointsTeam2"], "after90_explicit", True, []
    if len(after90) > 1:
        return None, None, "none", False, ["multiple_after90_results"]
    if kinds & {"AfterExtraTime"}:
        return None, None, "after_et", False, ["only_after_extra_time_result"]
    if kinds & {"AfterPenalties"}:
        return None, None, "after_pens", False, ["only_after_penalties_result"]
    if results:
        return None, None, "unclassified_final", False, ["final_result_without_explicit_90min_type"]
    return None, None, "none", False, []


def parse_match(m: dict, retrieved_utc: str, snapshot_id: str, now_utc: Optional[datetime] = None, competition_key: Optional[str] = None) -> StagingRecord:
    now = now_utc or datetime.now(timezone.utc)
    ko = _parse_utc(m.get("matchDateTimeUTC"))
    flags = ["user_entered_source_no_editorial_review"]
    h, a, rtype, label_ok, f2 = regulation_score(m)
    flags += f2
    finished = bool(m.get("matchIsFinished"))
    if finished and h is not None:
        status = "completed"
    elif finished:
        status = "completed_unclassified_score"
    elif ko is None:
        status = "unresolved"
        flags.append("no_kickoff_in_source")
    elif ko + timedelta(hours=MATCH_DURATION_PAD_H) < now:
        status = "past_date_no_result"
    elif ko <= now:
        status = "in_progress"
    else:
        status = "upcoming"
    if status != "completed":
        h = a = None
        label_ok = False if status != "completed" else label_ok
    grp = m.get("group") or {}
    t1, t2 = m.get("team1") or {}, m.get("team2") or {}
    return StagingRecord(
        source=SOURCE, source_ref=str(m.get("matchID")), competition_key=competition_key or m.get("leagueShortcut") or "", season=str(m.get("leagueSeason")),
        stage=grp.get("groupName"), round=str(grp.get("groupOrderID")) if grp.get("groupOrderID") is not None else None,
        home_raw=t1.get("teamName", ""), away_raw=t2.get("teamName", ""), status=status,
        kickoff_utc=ko.strftime("%Y-%m-%dT%H:%M:%SZ") if ko else None, kickoff_local=m.get("matchDateTime"), time_zone=m.get("timeZoneID"),
        time_precision="utc" if ko else "none", match_date=ko.strftime("%Y-%m-%d") if ko else None, date_provenance="source_stated" if ko else "none",
        regulation_home=h, regulation_away=a, result_type=rtype, label_eligible_90min=bool(label_ok and status == "completed"),
        source_ids=dict(matchID=m.get("matchID"), leagueId=m.get("leagueId"), leagueShortcut=m.get("leagueShortcut"), team1Id=t1.get("teamId"), team2Id=t2.get("teamId"), groupId=grp.get("groupID")),
        retrieved_utc=retrieved_utc, source_revision=str(m.get("lastUpdateDateTime") or ""), snapshot_id=snapshot_id, licence=LICENCE, attribution=ATTRIBUTION, flags=flags)


def parse_payload(payload: bytes, retrieved_utc: str, snapshot_id: str, now_utc: Optional[datetime] = None, competition_key: Optional[str] = None) -> list:
    data = json.loads(payload.decode("utf-8"))
    if isinstance(data, dict):
        data = [data]
    return [parse_match(m, retrieved_utc, snapshot_id, now_utc, competition_key) for m in data]


class OpenLigaDBAdapter:
    """Live use needs config live_enabled + real contact. Use plan()/poll() manually; no scheduler is created."""

    def __init__(self, cfg: Optional[AdapterConfig] = None, client: Optional[HttpClient] = None, state_path: Optional[str] = None):
        self.cfg = cfg or AdapterConfig.load()
        self.client = client or HttpClient(self.cfg, SOURCE, min_interval_s=2.0, jitter_s=1.5)   # <= ~25 requests/min, limit is 60/min/IP
        self.store = SnapshotStore(self.cfg.snapshot_dir)
        self.state_path = state_path or os.path.join(self.cfg.snapshot_dir, "openligadb_state.json")

    def _state(self):
        if not os.path.exists(self.state_path):
            return {}
        with open(self.state_path, encoding="utf-8") as fh:
            return json.load(fh)

    def _save_state(self, st):
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=1)

    def _snap(self, name, body, meta):
        return self.store.save(SOURCE, name, body, dict(meta, source=SOURCE, licence=LICENCE, attribution=ATTRIBUTION))

    def fetch_season(self, league: str, season: str, now_utc=None):
        """One request: whole league-season. Stores a raw snapshot and returns staging records."""
        if (league, season) not in VERIFIED_LEAGUES:
            raise ValueError(f"{league}/{season} has not been validated; add it after a reconciliation run")
        body, meta = self.client.get(f"{BASE}/getmatchdata/{league}/{season}")
        info = self._snap(f"{league}_{season}_season", body, meta)
        st = self._state()
        st.setdefault(f"{league}/{season}", {})["last_full_fetch_utc"] = utc_now()
        self._save_state(st)
        return parse_payload(body, info["saved_utc"], info["snapshot_id"], now_utc, COMPETITION_MAP.get(league)), info

    def poll(self, league: str, season: str, now_utc=None):
        """Change-date polling: current matchday and the previous one only; full matchday data is requested only when its last-change date moved."""
        if (league, season) not in VERIFIED_LEAGUES:
            raise ValueError(f"{league}/{season} has not been validated")
        cur_body, _ = self.client.get(f"{BASE}/getcurrentgroup/{league}")
        cur = json.loads(cur_body)["groupOrderID"]
        st = self._state()
        key = f"{league}/{season}"
        recs, infos = [], []
        for g in sorted({max(1, cur - 1), cur}):
            body, _ = self.client.get(f"{BASE}/getlastchangedate/{league}/{season}/{g}")
            changed = json.loads(body)
            if st.get(key, {}).get(str(g)) == changed:
                continue
            mbody, meta = self.client.get(f"{BASE}/getmatchdata/{league}/{season}/{g}")
            info = self._snap(f"{league}_{season}_md{g}", mbody, dict(meta, last_change_date=changed))
            recs += parse_payload(mbody, info["saved_utc"], info["snapshot_id"], now_utc, COMPETITION_MAP.get(league))
            infos.append(info)
            st.setdefault(key, {})[str(g)] = changed
        self._save_state(st)
        return recs, infos
