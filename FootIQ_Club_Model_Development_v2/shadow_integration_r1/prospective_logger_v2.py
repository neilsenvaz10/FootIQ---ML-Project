"""Prospective logger v2 (shadow-capable). The existing official logger (_scripts/e4_prospective_logger.py) is NOT modified.

What it adds (draft protocol amendment A1, inactive):
  * merged OpenFootball (frozen universe) + approved OpenLigaDB snapshots, with STRICT retrieval-time filtering (only snapshots retrieved <= prediction timestamp are read);
  * exact UTC kickoff timestamps (sealing deadline = kickoff - 60 min), kickoff-snapshot freshness (<= 24 h), no backdating;
  * explicit 90-minute labels only, duplicate/conflict rejection, source-specific provenance on every record;
  * model-hash, snapshot-hash and universe-hash verification; deterministic reconstruction of a sealed prediction from the saved snapshots;
  * one history cutoff / one universe for all models (original v1, matched v1, frozen v2, v1 Elo);
  * fixture-change reassessment as a SIDE-CAR (sealed records are never edited or deleted);
  * namespaces: SHADOW (this module, counts_for_evaluation=False, Bundesliga 2026-27 only) and OFFICIAL (refuses unless the owner's approval file AND an active amendment file exist - neither exists).
"""
import hashlib, json, os, stat, sys, time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(V2, "source_adapters_r1")); sys.path.insert(0, os.path.join(V2, "_scripts"))
from footiq_sources import openligadb as ol
from footiq_sources.reconcile import build_resolver
import e4_prospective_logger as E          # imported for model loading / hash verification only; its files are not modified
import d11_prospective_logger as D
from v2_common import sha, PREP

COMP, SEASON, LEAGUE = "deutschland:1-bundesliga", "2026-27", ("bl1", "2026")
CUTOFF = "2026-09-20"                      # frozen training cutoff
STALE_DAYS, KICKOFF_SNAPSHOT_MAX_H, LEAD_MIN = 14, 24.0, 60
LOGIC_VERSION = "logger-v2.0-shadow"
V_PATH = os.path.join(PREP, "_build", "work", "V_universe.pkl")
SHADOW_DIR = os.path.join(HERE, "shadow_log", "SHADOW")
APPROVAL = os.path.join(V2, "matched_v1_prospective_r1", "OFFICIAL_LOGGING_APPROVED.json")
AMENDMENT_ACTIVE = os.path.join(V2, "matched_v1_prospective_r1", "PROTOCOL_AMENDMENT_ACTIVE.json")


class IntegrityError(RuntimeError):
    pass


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
    source: str = "openligadb"
    plan_sha256: str = ""


def load_snapshot(path: str, verify=True) -> Snap:
    """path = the raw response file; its .meta.json holds sha256 / retrieval time. The hash is verified before parsing."""
    meta = json.load(open(path + ".meta.json", encoding="utf-8"))
    body = open(path, "rb").read()
    if verify and hashlib.sha256(body).hexdigest() != meta["sha256"]:
        raise IntegrityError(f"snapshot hash mismatch: {os.path.basename(path)}")
    retrieved = ts(meta["saved_utc"])
    recs = ol.parse_payload(body, meta["saved_utc"], meta["snapshot_id"], retrieved.to_pydatetime(), COMP)
    return Snap(meta["snapshot_id"], path, meta["sha256"], retrieved, recs, plan_sha256=meta.get("plan_sha256", ""))


@dataclass
class Merged:
    universe: pd.DataFrame
    additions: pd.DataFrame
    fixtures: pd.DataFrame
    rejects: list
    conflict_clubs: set
    past_no_result_clubs: set
    state_sha256: str
    snapshots_used: list
    snapshots_excluded: list
    history_cutoff_date: str
    latest_result_by_comp: dict


def merged_asof(V: pd.DataFrame, snaps, T, resolver, v_sha: str, pnr_of: Optional[pd.DataFrame] = None) -> Merged:
    """Frozen universe + OpenLigaDB results, using ONLY snapshots retrieved at or before T (strict)."""
    T = ts(T)
    used = sorted([s for s in snaps if s.retrieved <= T], key=lambda s: s.retrieved)
    excluded = [s.snapshot_id for s in snaps if s.retrieved > T]
    frozen = V[(V.competition_id == COMP) & (V.season_corrected == SEASON)]
    fz = {(r.home_entity_id, r.away_entity_id): (int(r.gh), int(r.ga), r.match_date) for r in frozen.itertuples()}
    first_seen, scores, rejects, conflict_clubs, add_rows = {}, {}, [], set(), {}
    latest_by_match = {}
    for s in used:
        seen_pairs = {}
        for r in s.records:
            he = resolver.resolve("openligadb", COMP, r.home_raw)[0]; ae = resolver.resolve("openligadb", COMP, r.away_raw)[0]
            mid = r.source_ref
            latest_by_match[mid] = (s, r, he, ae)
            if r.status != "completed":
                continue
            if not he or not ae:
                rejects.append((mid, "identity_unresolved")); continue
            if not r.label_eligible_90min:
                rejects.append((mid, "no_explicit_90min_result")); continue
            if r.kickoff_utc is None or ts(r.kickoff_utc) >= s.retrieved:
                rejects.append((mid, "kickoff_not_before_retrieval")); continue
            key = (he, ae); sc = (r.regulation_home, r.regulation_away)
            if key in seen_pairs and seen_pairs[key] != mid:                                   # same ordered pair twice in one snapshot
                rejects.append((mid, "duplicate_pair_in_snapshot")); conflict_clubs |= {he, ae}; add_rows.pop(key, None); scores[key] = ("DUP",); continue
            seen_pairs[key] = mid
            if scores.get(key) in (("CONFLICT",), ("DUP",)):
                continue                                                                      # already quarantined
            if key in scores and scores[key] != sc:                                            # later snapshot changes the score
                rejects.append((mid, "CONFLICT_between_snapshots")); conflict_clubs |= {he, ae}; add_rows.pop(key, None); scores[key] = ("CONFLICT",); continue
            if key in fz:
                if fz[key][:2] != sc:
                    rejects.append((mid, "CONFLICT_with_openfootball")); conflict_clubs |= {he, ae}; scores[key] = ("CONFLICT",)
                elif abs((ts(r.kickoff_utc).normalize() - ts(fz[key][2]).normalize()).days) > 1:
                    rejects.append((mid, "CONFLICT_date_with_openfootball")); conflict_clubs |= {he, ae}; scores[key] = ("CONFLICT",)
                continue                                                                      # identical and already in the frozen universe
            scores[key] = sc
            if key not in add_rows:
                first_seen[key] = s.retrieved
                add_rows[key] = dict(record_id="NEW:openligadb:" + mid, competition_id=COMP, season_corrected=SEASON, match_date=r.match_date, dt=pd.Timestamp(r.match_date), home_entity_id=he, away_entity_id=ae,
                                     home_team_name=r.home_raw, away_team_name=r.away_raw, tier=1.0, competition_type="domestic_league", regular_round_robin_stage=True, rated=True,
                                     gh=float(sc[0]), ga=float(sc[1]), provenance=f"OpenLigaDB matchID {mid} snapshot {s.snapshot_id}", retrieved_utc=s.retrieved.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                     kickoff_utc=r.kickoff_utc, source="openligadb", snapshot_id=s.snapshot_id)
    ADD = pd.DataFrame(list(add_rows.values()))
    if len(ADD):
        ADD = ADD.sort_values(["match_date", "record_id"]).reset_index(drop=True)
        assert (pd.to_datetime(ADD.retrieved_utc, utc=True) <= T).all()                       # strict: nothing retrieved after T
    U = pd.concat([V, ADD], ignore_index=True) if len(ADD) else V
    # fixtures = latest state of each match in the latest usable snapshot
    fx = []
    pnr = set()
    for mid, (s, r, he, ae) in latest_by_match.items():
        if r.status == "upcoming" and he and ae:
            fx.append(dict(fixture_id="OL:" + mid, dt=pd.Timestamp(r.match_date), h=he, a=ae, comp=COMP, season=SEASON, tier=1.0, home_name=r.home_raw, away_name=r.away_raw, kickoff=r.kickoff_utc,
                           kickoff_known=True, kickoff_utc=r.kickoff_utc, kickoff_snapshot_id=s.snapshot_id, kickoff_snapshot_utc=s.retrieved.strftime("%Y-%m-%dT%H:%M:%SZ"), time_precision=r.time_precision,
                           matchday=r.round, ol_match_id=mid))
        elif r.status == "past_date_no_result" and he and ae:
            pnr |= {he, ae}
    if pnr_of is not None:                                                                     # openfootball past-dated fixtures still without any result
        done = set(zip(ADD.home_entity_id, ADD.away_entity_id)) if len(ADD) else set()
        for x in pnr_of.itertuples():
            if (x.home_entity_id, x.away_entity_id) not in done:
                pnr |= {x.home_entity_id, x.away_entity_id}
    FX = pd.DataFrame(fx)
    comp_rows = U[(U.competition_id == COMP)]
    cutoff_date = str(comp_rows.match_date.max())
    state = dict(v=v_sha, add=[(r.record_id, r.match_date, r.home_entity_id, r.away_entity_id, r.gh, r.ga, r.retrieved_utc) for r in ADD.itertuples()] if len(ADD) else [],
                 snaps=[(s.snapshot_id, s.sha256) for s in used])
    state_sha = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    return Merged(U, ADD, FX, rejects, conflict_clubs, pnr, state_sha, [(s.snapshot_id, s.sha256, s.retrieved.strftime("%Y-%m-%dT%H:%M:%SZ")) for s in used], excluded, cutoff_date,
                  {COMP: cutoff_date})


def ensure_official_allowed():
    if not (os.path.exists(APPROVAL) and os.path.exists(AMENDMENT_ACTIVE)):
        raise PermissionError("OFFICIAL namespace is closed: needs OFFICIAL_LOGGING_APPROVED.json and an active, hashed protocol amendment (neither exists)")


def _hash_record(rec):
    return hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()


_SHA_CACHE = {}


def _universe_sha():
    st = os.stat(V_PATH); k = (st.st_mtime_ns, st.st_size)
    if k not in _SHA_CACHE:
        _SHA_CACHE[k] = sha(V_PATH)
    return _SHA_CACHE[k]


def predict_shadow(V, snaps, T, resolver, v_sha, pnr_of=None, namespace="shadow", scope_competitions=(COMP,), verify_universe=True):
    """Returns (records, rejected_fixtures, merged). Never writes. T is the prediction timestamp (sealing time)."""
    if namespace != "shadow":
        ensure_official_allowed()
    T = ts(T)
    hashes = E.verify_models()                                                                 # frozen model artifact hashes vs FROZEN records
    for s in snaps:                                                                            # snapshot hashes re-verified for every snapshot we may read
        if hashlib.sha256(open(s.path, "rb").read()).hexdigest() != s.sha256:
            raise IntegrityError("snapshot changed on disk: " + s.snapshot_id)
    if verify_universe and _universe_sha() != v_sha:
        raise IntegrityError("frozen universe hash changed")
    M = merged_asof(V, snaps, T, resolver, v_sha, pnr_of)
    rejected, keep = [], []
    for r in M.fixtures.itertuples():
        if r.comp not in scope_competitions:
            rejected.append((r.fixture_id, "out_of_scope_competition")); continue
        ko = ts(r.kickoff_utc)
        if r.time_precision != "utc":
            rejected.append((r.fixture_id, "kickoff_not_utc_stated")); continue
        deadline = ko - pd.Timedelta(minutes=LEAD_MIN)
        if deadline <= T:
            rejected.append((r.fixture_id, "sealing_deadline_passed_no_backdating")); continue
        if ts(r.kickoff_snapshot_utc) < T - pd.Timedelta(hours=KICKOFF_SNAPSHOT_MAX_H):
            rejected.append((r.fixture_id, "stale_kickoff_snapshot")); continue
        keep.append(r.fixture_id)
    if not keep:
        return [], rejected, M
    fx = M.fixtures[M.fixtures.fixture_id.isin(keep)].reset_index(drop=True)
    F2, F1 = D.features_for(M.universe, fx[["fixture_id", "dt", "h", "a", "comp", "season", "tier"]])
    F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
    v2, v1, v1prep, v1elo = D.load_models()
    P2 = v2["model"].predict_proba(v2["prep"].transform(F2, True)); P1 = D.v1_proba(v1, v1prep, F1); PM = E.matched_v1_proba(F1); PE = D.v1_elo_proba(v1elo, F1.elo_diff.values)
    bad_ent = {(e["competition_id"], e["entity_id"]) for e in E.EXCL["entities"]}
    code_sha = sha(os.path.abspath(__file__))
    recs = []
    for i, r in enumerate(fx.itertuples()):
        reasons = []
        nh, na = int(F2.home_n_prior.iloc[i]), int(F2.away_n_prior.iloc[i])
        if not (nh >= 5 and na >= 5 and bool(F1.pair_connected_asof.iloc[i])): reasons.append("history_lt5_or_elo_disconnected")
        if (r.comp, r.h) in bad_ent or (r.comp, r.a) in bad_ent: reasons.append("identity_collision_unresolved")
        if r.h in M.past_no_result_clubs or r.a in M.past_no_result_clubs: reasons.append("club_has_unresolved_past_fixture")
        if r.h in M.conflict_clubs or r.a in M.conflict_clubs: reasons.append("unresolved_conflict")
        gap = (pd.Timestamp(r.dt) - pd.Timestamp(M.history_cutoff_date)).days
        if gap > STALE_DAYS: reasons.append(f"stale_competition_results(gap_days={gap})")
        ko = ts(r.kickoff_utc)
        rec = dict(namespace=namespace, mode="shadow", counts_for_evaluation=False, logic_version=LOGIC_VERSION, fixture_id=r.fixture_id, ol_match_id=r.ol_match_id, competition_id=r.comp, season=r.season,
                   home_team=r.home_name, away_team=r.away_name, home_entity_id=r.h, away_entity_id=r.a, matchday=r.matchday,
                   scheduled_kickoff_utc=r.kickoff_utc, kickoff_time_precision=r.time_precision, kickoff_source=dict(source="openligadb", snapshot_id=r.kickoff_snapshot_id, retrieved_utc=r.kickoff_snapshot_utc),
                   sealing_deadline_utc=str(ko - pd.Timedelta(minutes=LEAD_MIN)), legacy_deadline_utc=str(pd.Timestamp(r.kickoff_utc[:10], tz="UTC") - pd.Timedelta(hours=14) - pd.Timedelta(minutes=60)),
                   prediction_timestamp_utc=T.strftime("%Y-%m-%dT%H:%M:%SZ"), sealed_before_deadline_by_minutes=round((ko - pd.Timedelta(minutes=LEAD_MIN) - T).total_seconds() / 60, 1),
                   history_cutoff_date=M.history_cutoff_date, state_sha256=M.state_sha256, frozen_universe_sha256=v_sha, input_snapshots=[dict(snapshot_id=a, sha256=b, retrieved_utc=c) for a, b, c in M.snapshots_used],
                   results_added_to_frozen_state=int(len(M.additions)), model_hashes=hashes, models=E.MODELS, logger_code_sha256=code_sha,
                   probs=dict(v2_frozen=dict(H=float(P2[i, 0]), D=float(P2[i, 1]), A=float(P2[i, 2])), v1_original=dict(H=float(P1[i, 0]), D=float(P1[i, 1]), A=float(P1[i, 2])),
                              v1_matched=dict(H=float(PM[i, 0]), D=float(PM[i, 1]), A=float(PM[i, 2])), v1_elo=dict(H=float(PE[i, 0]), D=float(PE[i, 1]), A=float(PE[i, 2]))),
                   home_n_prior=nh, away_n_prior=na, eligibility_reasons=reasons, primary_eligible=len(reasons) == 0, coverage_flags=["user_entered_source_no_editorial_review"],
                   attribution=ol.ATTRIBUTION, licence=ol.LICENCE, v2_feature_sha256=hashlib.sha256(np.ascontiguousarray(F2[v2["features"]].values.astype(float)[i]).tobytes()).hexdigest())
        rec["record_sha256"] = _hash_record(rec)
        recs.append(rec)
    return recs, rejected, M


def write_shadow_batch(recs, name, log_dir=SHADOW_DIR):
    assert all(r["namespace"] == "shadow" and r["counts_for_evaluation"] is False for r in recs)
    return D.append_batch(recs, log_dir, name)


def verify_chain(log_dir=SHADOW_DIR):
    return D.verify_chain(log_dir)


def reconstruct(rec, snaps_by_id, V, resolver, v_sha, pnr_of=None, verify_universe=True):
    """Re-derive a sealed prediction from the saved snapshots it names and its own prediction timestamp; returns (identical, diffs)."""
    used = [snaps_by_id[x["snapshot_id"]] for x in rec["input_snapshots"]]
    for s, x in zip(used, rec["input_snapshots"]):
        if s.sha256 != x["sha256"]:
            return False, ["snapshot hash differs from the sealed record"]
    recs, rej, M = predict_shadow(V, used, rec["prediction_timestamp_utc"], resolver, v_sha, pnr_of, verify_universe=verify_universe)
    new = {r["fixture_id"]: r for r in recs}.get(rec["fixture_id"])
    if new is None:
        return False, ["fixture not reproducible: " + str(dict(rej).get(rec["fixture_id"]))]
    diffs = [k for k in ("probs", "state_sha256", "eligibility_reasons", "v2_feature_sha256", "history_cutoff_date", "sealing_deadline_utc") if new[k] != rec[k]]
    return not diffs, diffs


def reconstruct_batch(recs, snaps_by_id, V, resolver, v_sha, pnr_of=None, verify_universe=True):
    """Reconstruct every record of a batch that shares one prediction timestamp and one snapshot set with a single state build. Returns (n_identical, failures)."""
    groups = {}
    for r in recs:
        groups.setdefault((r["prediction_timestamp_utc"], tuple((x["snapshot_id"], x["sha256"]) for x in r["input_snapshots"])), []).append(r)
    ok, fails = 0, []
    for (t, sn), rs in groups.items():
        used = [snaps_by_id[i] for i, h in sn]
        if any(u.sha256 != h for u, (i, h) in zip(used, sn)):
            fails += [(r["fixture_id"], ["snapshot hash differs"]) for r in rs]; continue
        new_recs, rej, M = predict_shadow(V, used, t, resolver, v_sha, pnr_of, verify_universe=verify_universe)
        by = {x["fixture_id"]: x for x in new_recs}
        for r in rs:
            n = by.get(r["fixture_id"])
            d = ["not reproducible"] if n is None else [k for k in ("probs", "state_sha256", "eligibility_reasons", "v2_feature_sha256", "history_cutoff_date", "sealing_deadline_utc", "record_sha256") if n[k] != r[k]]
            if d: fails.append((r["fixture_id"], d))
            else: ok += 1
    return ok, fails


def reassess(sealed, snaps, T_eval, resolver):
    """Fixture-change side-car. Never edits sealed records. Returns list of dicts (one per sealed record)."""
    T_eval = ts(T_eval)
    used = sorted([s for s in snaps if s.retrieved <= T_eval], key=lambda s: s.retrieved)
    out = []
    for rec in sealed:
        mid = rec["ol_match_id"]
        hist = []
        for s in used:
            for r in s.records:
                if r.source_ref == mid:
                    hist.append((s, r))
        flags, elig, label = [], "eligible", "pending"
        if not hist:
            out.append(dict(fixture_id=rec["fixture_id"], original_record_sha256=rec["record_sha256"], flags=["fixture_removed_or_not_in_any_snapshot"], evaluation_eligibility="ineligible_fixture_removed", label_status="none", assessed_utc=T_eval.isoformat())); continue
        s, r = hist[-1]
        if not any(x.source_ref == mid for x in used[-1].records):                             # present earlier, absent from the newest snapshot
            out.append(dict(fixture_id=rec["fixture_id"], original_record_sha256=rec["record_sha256"], flags=["fixture_removed_or_cancelled_in_newest_snapshot"], evaluation_eligibility="ineligible_fixture_removed",
                            label_status="none", assessed_utc=T_eval.isoformat(), latest_snapshot=used[-1].snapshot_id)); continue
        he = resolver.resolve("openligadb", COMP, r.home_raw)[0]; ae = resolver.resolve("openligadb", COMP, r.away_raw)[0]
        if (he, ae) != (rec["home_entity_id"], rec["away_entity_id"]):
            flags.append("fixture_identity_changed"); elig = "ineligible_identity_changed"
        if r.kickoff_utc and ts(r.kickoff_utc) != ts(rec["scheduled_kickoff_utc"]):
            new_ko, old_ko = ts(r.kickoff_utc), ts(rec["scheduled_kickoff_utc"])
            if new_ko < old_ko:
                flags.append("kickoff_moved_earlier")
                if ts(rec["prediction_timestamp_utc"]) > new_ko - pd.Timedelta(minutes=LEAD_MIN):
                    elig = "ineligible_sealed_too_late_after_move"
            else:
                flags.append("rescheduled_later" if (new_ko - old_ko) < pd.Timedelta(days=7) else "postponed_more_than_7_days")
                if elig == "eligible": elig = "eligible_flagged_rescheduled"
        res_hist = [(x, y) for x, y in hist if y.status == "completed"]
        scores = {(y.regulation_home, y.regulation_away) for _, y in res_hist}
        if len(scores) > 1:
            flags.append("result_conflict_between_snapshots"); label = "conflict"; elig = "ineligible_unresolved_conflict"
        elif res_hist:
            last = res_hist[-1][1]
            if not last.label_eligible_90min:
                label = "unclassified_result"; elig = "ineligible_no_explicit_90min"
            else:
                first_t, last_t = res_hist[0][0].retrieved, res_hist[-1][0].retrieved
                ko = ts(last.kickoff_utc)
                if first_t >= ko + pd.Timedelta(hours=48) and last_t - first_t >= pd.Timedelta(hours=24):
                    label = "confirmed"
                else:
                    label = "pending_confirmation"
        else:
            if r.status == "past_date_no_result":
                flags.append("missing_result"); label = "missing"
                if T_eval - ts(r.kickoff_utc) > pd.Timedelta(days=7):
                    elig = "ineligible_no_result_after_7_days"
            elif r.status == "in_progress":
                label = "in_progress"
        out.append(dict(fixture_id=rec["fixture_id"], original_record_sha256=rec["record_sha256"], flags=flags, evaluation_eligibility=elig, label_status=label, assessed_utc=T_eval.isoformat(),
                        latest_snapshot=s.snapshot_id))
    return out
