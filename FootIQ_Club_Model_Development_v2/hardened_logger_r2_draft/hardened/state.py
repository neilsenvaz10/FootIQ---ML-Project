"""Source-integrity layer: scope-validated snapshots, order checks, and the merged match-history state with explicit integrity EVENTS.
Any event that makes a club's history incomplete or inconsistent blocks that club's fixtures from primary eligibility (draft protocol r2, clause 6)."""
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Optional

import pandas as pd

from . import artifacts

sys.path.insert(0, os.path.join(artifacts.V2, "source_adapters_r1")); sys.path.insert(0, os.path.join(artifacts.V2, "_scripts"))
from footiq_sources import openligadb as ol  # noqa

COMP, SEASON, LEAGUE, LEAGUE_SEASON = "deutschland:1-bundesliga", "2026-27", "bl1", "2026"
CUTOFF = "2026-09-20"
KICKOFF_SNAPSHOT_MAX_H = 24.0
SKEW_MAX_S = 120.0


class IntegrityError(RuntimeError): pass
class ScopeError(RuntimeError): pass
class OutOfOrderError(RuntimeError): pass


def ts(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


@dataclass
class Snap:
    snapshot_id: str
    path: str
    sha256: str
    retrieved: pd.Timestamp
    records: list = field(default_factory=list)
    raw: list = field(default_factory=list)
    clock_skew_s: Optional[float] = None
    plan_sha256: str = ""


def load_snapshot(path: str) -> Snap:
    meta = json.load(open(path + ".meta.json", encoding="utf-8"))
    body = open(path, "rb").read()
    if hashlib.sha256(body).hexdigest() != meta["sha256"]:
        raise IntegrityError(f"snapshot hash mismatch: {os.path.basename(path)}")
    raw = json.loads(body.decode("utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ScopeError("snapshot payload is not a non-empty list of matches")
    for m in raw:
        if m.get("leagueShortcut") != LEAGUE or str(m.get("leagueSeason")) != LEAGUE_SEASON:
            raise ScopeError(f"snapshot contains {m.get('leagueShortcut')}/{m.get('leagueSeason')}; only {LEAGUE}/{LEAGUE_SEASON} is in scope")
        if m.get("matchDateTimeUTC") and m["matchDateTimeUTC"][:10] <= CUTOFF and not m.get("matchIsFinished"):
            pass
    retrieved = ts(meta["saved_utc"])
    skew = None
    d = (meta.get("headers") or {}).get("Date")
    if d:
        skew = (retrieved - ts(parsedate_to_datetime(d))).total_seconds()
    recs = ol.parse_payload(body, meta["saved_utc"], meta["snapshot_id"], retrieved.to_pydatetime(), COMP)
    return Snap(meta["snapshot_id"], path, meta["sha256"], retrieved, recs, raw, skew, meta.get("plan_sha256", ""))


def check_order(snaps):
    """Snapshots must have strictly increasing retrieval times and monotone content (a newer snapshot may not carry an older lastUpdate for the same match)."""
    s = sorted(snaps, key=lambda x: x.retrieved)
    for a, b in zip(s, s[1:]):
        if b.retrieved <= a.retrieved:
            raise OutOfOrderError(f"snapshots {a.snapshot_id} and {b.snapshot_id} have identical retrieval times")
        old = {m["matchID"]: m.get("lastUpdateDateTime") or "" for m in a.raw}
        for m in b.raw:
            lu = m.get("lastUpdateDateTime") or ""
            if m["matchID"] in old and lu < old[m["matchID"]]:
                raise OutOfOrderError(f"{b.snapshot_id} (retrieved later) holds older content than {a.snapshot_id} for match {m['matchID']}")
    return s


@dataclass
class State:
    universe: pd.DataFrame
    additions: pd.DataFrame
    fixtures: pd.DataFrame
    events: list
    blocked_clubs: set
    competition_blocked: bool
    pnr_clubs: set
    state_sha256: str
    used: list
    excluded: list
    history_cutoff_date: str
    newest_snapshot_utc: Optional[str]


def merged_state(V, snaps, T, resolver, v_sha, pnr_of=None, s1_additions=None) -> State:
    T = ts(T)
    used = check_order([s for s in snaps if s.retrieved <= T])
    excluded = [s.snapshot_id for s in snaps if s.retrieved > T]
    events, blocked, comp_blocked = [], set(), False

    def ev(kind, mid, detail="", clubs=()):
        nonlocal blocked
        events.append(dict(kind=kind, match=str(mid), detail=detail)); blocked |= {c for c in clubs if c}

    frozen = V[(V.competition_id == COMP) & (V.season_corrected == SEASON)]
    fz = {(r.home_entity_id, r.away_entity_id): (int(r.gh), int(r.ga), str(r.match_date)) for r in frozen.itertuples()}
    versions = {}
    for s in used:
        seen = set()
        for r in s.records:
            if r.source_ref in seen:
                ev("duplicate_matchID_in_snapshot", r.source_ref, s.snapshot_id); continue
            seen.add(r.source_ref)
            versions.setdefault(r.source_ref, []).append((s, r))
    ids_latest = {r.source_ref for r in used[-1].records} if used else set()

    def ents(r):
        return resolver.resolve("openligadb", COMP, r.home_raw)[0], resolver.resolve("openligadb", COMP, r.away_raw)[0]
    add, pair_owner, latest_pairs = {}, {}, set()
    for mid, vs in versions.items():
        s_last, r_last = vs[-1]
        he, ae = ents(r_last)
        if mid not in ids_latest:
            ev("fixture_removed_in_newest_snapshot", mid, "present earlier, absent from the newest snapshot", (he, ae)); continue
        if he and ae: latest_pairs.add((he, ae))
        comp_versions = [(s, r) for s, r in vs if r.status == "completed"]
        if comp_versions and r_last.status != "completed":
            ev("withdrawn_result", mid, "completed in an earlier snapshot, not completed in the newest", (he, ae)); continue
        if r_last.status == "completed_unclassified_score":
            ev("played_match_no_explicit_90min_result", mid, r_last.result_type, (he, ae))
            if not he or not ae: comp_blocked = True
            continue
        if r_last.status != "completed":
            continue
        if len({(r.regulation_home, r.regulation_away) for s, r in comp_versions}) > 1:
            ev("corrected_result", mid, "score changed between snapshots", (he, ae)); continue
        if not he or not ae:
            ev("played_match_unresolved_identity", mid, f"{r_last.home_raw} / {r_last.away_raw}", (he, ae)); comp_blocked = True; continue
        if not r_last.label_eligible_90min:
            ev("played_match_no_explicit_90min_result", mid, r_last.result_type, (he, ae)); continue
        first_s, first_r = comp_versions[0]
        if first_r.kickoff_utc is None or ts(first_r.kickoff_utc) >= first_s.retrieved:
            ev("played_match_kickoff_not_before_retrieval", mid, "", (he, ae)); continue
        sc = (r_last.regulation_home, r_last.regulation_away); key = (he, ae)
        if key in pair_owner and pair_owner[key] != mid:
            ev("duplicate_ordered_pair", mid, f"also {pair_owner[key]}", (he, ae)); add.pop(key, None); continue
        pair_owner[key] = mid
        if key in fz:
            fsc = fz[key]
            if fsc[:2] != sc: ev("conflict_with_openfootball_score", mid, f"{fsc[:2]} vs {sc}", (he, ae))
            elif abs((ts(r_last.kickoff_utc).normalize() - ts(fsc[2]).normalize()).days) > 1: ev("conflict_with_openfootball_date", mid, "", (he, ae))
            continue
        if r_last.match_date <= CUTOFF:
            ev("result_before_cutoff_missing_in_frozen_universe", mid, r_last.match_date, (he, ae)); continue
        add[key] = dict(record_id="NEW:openligadb:" + mid, competition_id=COMP, season_corrected=SEASON, match_date=r_last.match_date, dt=pd.Timestamp(r_last.match_date), home_entity_id=he, away_entity_id=ae,
                        home_team_name=r_last.home_raw, away_team_name=r_last.away_raw, tier=1.0, competition_type="domestic_league", regular_round_robin_stage=True, rated=True, gh=float(sc[0]), ga=float(sc[1]),
                        provenance=f"OpenLigaDB matchID {mid} snapshot {first_s.snapshot_id}", retrieved_utc=first_s.retrieved.strftime("%Y-%m-%dT%H:%M:%SZ"), kickoff_utc=first_r.kickoff_utc, source="openligadb",
                        snapshot_id=first_s.snapshot_id, agreement="single_source")
    if used:
        for key, (h, a, d) in fz.items():
            if key not in latest_pairs:
                ev("known_match_missing_in_source", f"{key[0]}|{key[1]}", d, key)
    # newer OpenFootball (S1) results, supplied as a verified, hashed frame
    if s1_additions is not None and len(s1_additions):
        need = {"record_id", "match_date", "home_entity_id", "away_entity_id", "gh", "ga", "retrieved_utc", "snapshot_sha256"}
        if not need <= set(s1_additions.columns): raise IntegrityError("S1 additions frame lacks required columns")
        for r in s1_additions.itertuples():
            key = (r.home_entity_id, r.away_entity_id)
            if ts(r.retrieved_utc) > T: continue
            if str(r.match_date) <= CUTOFF: ev("s1_result_before_cutoff", r.record_id, "", key); continue
            if key in add:
                if (add[key]["gh"], add[key]["ga"]) != (float(r.gh), float(r.ga)):
                    ev("conflict_between_sources_score", r.record_id, f"S1 {(r.gh, r.ga)} vs S2 {(add[key]['gh'], add[key]['ga'])}", key); add.pop(key); continue
                if abs((ts(r.match_date) - ts(add[key]["match_date"])).days) > 1:
                    ev("conflict_between_sources_date", r.record_id, "", key); add.pop(key); continue
                row = dict(add[key]); row.update(record_id="NEW:openfootball:" + str(r.record_id), source="openfootball+openligadb", match_date=str(r.match_date), dt=pd.Timestamp(r.match_date), agreement="two_sources_agree",
                                                provenance=f"openfootball {r.record_id} sha {r.snapshot_sha256[:12]} + " + row["provenance"]); add[key] = row
            else:
                he_name = frozen[frozen.home_entity_id == r.home_entity_id].home_team_name.head(1).tolist() or [r.home_entity_id]
                add[key] = dict(record_id="NEW:openfootball:" + str(r.record_id), competition_id=COMP, season_corrected=SEASON, match_date=str(r.match_date), dt=pd.Timestamp(r.match_date), home_entity_id=r.home_entity_id,
                                away_entity_id=r.away_entity_id, home_team_name="", away_team_name="", tier=1.0, competition_type="domestic_league", regular_round_robin_stage=True, rated=True, gh=float(r.gh), ga=float(r.ga),
                                provenance=f"openfootball {r.record_id} sha {r.snapshot_sha256[:12]}", retrieved_utc=str(r.retrieved_utc), kickoff_utc=None, source="openfootball", snapshot_id=str(r.snapshot_sha256)[:16], agreement="single_source")
    ADD = pd.DataFrame(list(add.values()))
    if len(ADD):
        ADD = ADD.sort_values(["match_date", "record_id"]).reset_index(drop=True)
        assert (pd.to_datetime(ADD.retrieved_utc, utc=True) <= T).all()
    U = pd.concat([V, ADD], ignore_index=True) if len(ADD) else V
    fx, pnr = [], set()
    if used:
        for mid, vs in versions.items():
            s, r = vs[-1]
            if mid not in ids_latest: continue
            he, ae = ents(r)
            if r.status == "upcoming":
                if not he or not ae:
                    ev("fixture_unresolved_identity", mid, f"{r.home_raw} / {r.away_raw}", (he, ae)); comp_blocked = True; continue
                fx.append(dict(fixture_id="OL:" + mid, dt=pd.Timestamp(r.match_date), h=he, a=ae, comp=COMP, season=SEASON, tier=1.0, home_name=r.home_raw, away_name=r.away_raw, kickoff=r.kickoff_utc, kickoff_known=True,
                               kickoff_utc=r.kickoff_utc, kickoff_snapshot_id=s.snapshot_id, kickoff_snapshot_utc=s.retrieved.strftime("%Y-%m-%dT%H:%M:%SZ"), time_precision=r.time_precision, matchday=r.round, ol_match_id=mid))
            elif r.status == "past_date_no_result" and he and ae:
                pnr |= {he, ae}
    done = set(add)
    if pnr_of is not None:
        for x in pnr_of.itertuples():
            if (x.home_entity_id, x.away_entity_id) not in done: pnr |= {x.home_entity_id, x.away_entity_id}
    FX = pd.DataFrame(fx)
    comp_rows = U[U.competition_id == COMP]
    hist_cut = str(comp_rows.match_date.max())
    state = dict(v=v_sha, add=[(r.record_id, r.match_date, r.home_entity_id, r.away_entity_id, r.gh, r.ga, r.retrieved_utc, r.agreement) for r in ADD.itertuples()] if len(ADD) else [], snaps=[(s.snapshot_id, s.sha256) for s in used],
                 events=sorted((e["kind"], e["match"]) for e in events), blocked=sorted(blocked), comp_blocked=comp_blocked)
    return State(U, ADD, FX, events, blocked, comp_blocked, pnr, hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest(), used, excluded, hist_cut,
                 used[-1].retrieved.strftime("%Y-%m-%dT%H:%M:%SZ") if used else None)
