"""Hardened prospective logger engine (draft; implements the proposed protocol r2). The existing official logger and the v2 shadow module are not modified.

Public entry points
  predict_core(...)        pure computation with an EXPLICIT prediction time - used for shadow runs and reconstruction only
  seal_official(...)       the only sealing path: takes NO timestamp (system clock), requires official switch + valid approval + intact artifact manifest + intact ledger
  reassess(...)            fixture-change / late-result / label side-car classification (written to its own chained ledger by the script)
  reconcile_results(...)   outcome reconciliation
  status_report(...)       operational status
"""
import hashlib
import json
import os
import sys
import tempfile
from datetime import timedelta

import numpy as np
import pandas as pd

from . import approval as appr
from . import artifacts, ledger
from .state import (COMP, SEASON, CUTOFF, KICKOFF_SNAPSHOT_MAX_H, SKEW_MAX_S, IntegrityError, OutOfOrderError, ScopeError, Snap, State, check_order, load_snapshot, merged_state, ts)

sys.path.insert(0, os.path.join(artifacts.V2, "_scripts"))
import d11_prospective_logger as D  # noqa: E402
import e4_prospective_logger as E   # noqa: E402

LOGIC_VERSION = "logger-v3.0-draft"
STALE_DAYS, LEAD_MIN = 14, 60
CANON_LEDGER = os.path.join(artifacts.ROOT, "official_ledger")
CANON_ANCHOR = os.path.join(artifacts.P, "ledger_anchor_official", "anchor.jsonl")
LATE_DAYS_PENDING = 7


class ClockError(RuntimeError): pass


def _now() -> pd.Timestamp:
    """Authoritative execution-time clock (UTC). Tests may patch this function; nothing else may supply a sealing time."""
    return pd.Timestamp.now(tz="UTC").floor("s")


def model_key(hashes: dict) -> str:
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:16]


def _hash_record(rec) -> str:
    return hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()


def predict_core(V, snaps, T, resolver, expected_manifest, *, pnr_of=None, s1_additions=None, namespace="shadow", scope=(COMP,), manifest_paths=None):
    """Returns (records, rejected[(fixture_id, reason)], State). T is explicit: callers outside shadow/reconstruction must not use this function directly."""
    T = ts(T)
    problems = artifacts.verify(expected_manifest, manifest_paths)
    if problems:
        raise IntegrityError("artifact manifest mismatch: " + "; ".join(problems[:5]))
    hashes = E.verify_models()
    mf = artifacts.manifest(manifest_paths)
    msha = artifacts.manifest_sha(mf)
    for s in snaps:
        if hashlib.sha256(open(s.path, "rb").read()).hexdigest() != s.sha256:
            raise IntegrityError("snapshot changed on disk: " + s.snapshot_id)
    S = merged_state(V, snaps, T, resolver, mf["universe"], pnr_of, s1_additions)
    rejected, keep = [], []
    newest_age_h = (T - ts(S.newest_snapshot_utc)).total_seconds() / 3600 if S.newest_snapshot_utc else None
    for r in S.fixtures.itertuples() if len(S.fixtures) else []:
        if r.comp not in scope: rejected.append((r.fixture_id, "out_of_scope_competition")); continue
        if r.time_precision != "utc": rejected.append((r.fixture_id, "kickoff_not_utc_stated")); continue
        ko = ts(r.kickoff_utc)
        if ko - pd.Timedelta(minutes=LEAD_MIN) <= T: rejected.append((r.fixture_id, "sealing_deadline_passed_no_backdating")); continue
        if ts(r.kickoff_snapshot_utc) < T - pd.Timedelta(hours=KICKOFF_SNAPSHOT_MAX_H): rejected.append((r.fixture_id, "stale_kickoff_snapshot")); continue
        keep.append(r.fixture_id)
    if not keep:
        return [], rejected, S
    fx = S.fixtures[S.fixtures.fixture_id.isin(keep)].reset_index(drop=True)
    F2, F1 = D.features_for(S.universe, fx[["fixture_id", "dt", "h", "a", "comp", "season", "tier"]])
    F2, F1 = F2.loc[fx.fixture_id], F1.loc[fx.fixture_id]
    v2, v1, v1prep, v1elo = D.load_models()
    P2 = v2["model"].predict_proba(v2["prep"].transform(F2, True)); P1 = D.v1_proba(v1, v1prep, F1); PM = E.matched_v1_proba(F1); PE = D.v1_elo_proba(v1elo, F1.elo_diff.values)
    bad_ent = {(e["competition_id"], e["entity_id"]) for e in E.EXCL["entities"]}
    mkey = model_key(hashes)
    ev_counts = pd.Series([e["kind"] for e in S.events]).value_counts().to_dict() if S.events else {}
    recs = []
    for i, r in enumerate(fx.itertuples()):
        reasons = []
        nh, na = int(F2.home_n_prior.iloc[i]), int(F2.away_n_prior.iloc[i])
        if not (nh >= 5 and na >= 5 and bool(F1.pair_connected_asof.iloc[i])): reasons.append("history_lt5_or_elo_disconnected")
        if (r.comp, r.h) in bad_ent or (r.comp, r.a) in bad_ent: reasons.append("identity_collision_unresolved")
        if r.h in S.pnr_clubs or r.a in S.pnr_clubs: reasons.append("club_has_unresolved_past_fixture")
        if S.competition_blocked: reasons.append("incomplete_history_competition_blocked")
        if r.h in S.blocked_clubs or r.a in S.blocked_clubs: reasons.append("incomplete_or_inconsistent_history")
        gap = (pd.Timestamp(r.dt) - pd.Timestamp(S.history_cutoff_date)).days
        if gap > STALE_DAYS: reasons.append(f"stale_competition_results(gap_days={gap})")
        ko = ts(r.kickoff_utc)
        rec = dict(namespace=namespace, mode="shadow" if namespace == "shadow" else namespace, counts_for_evaluation=False, logic_version=LOGIC_VERSION, fixture_id=r.fixture_id, ol_match_id=r.ol_match_id, competition_id=r.comp,
                   season=r.season, home_team=r.home_name, away_team=r.away_name, home_entity_id=r.h, away_entity_id=r.a, matchday=r.matchday, scheduled_kickoff_utc=r.kickoff_utc, kickoff_time_precision=r.time_precision,
                   kickoff_source=dict(source="openligadb", snapshot_id=r.kickoff_snapshot_id, retrieved_utc=r.kickoff_snapshot_utc), sealing_deadline_utc=str(ko - pd.Timedelta(minutes=LEAD_MIN)),
                   prediction_timestamp_utc=T.strftime("%Y-%m-%dT%H:%M:%SZ"), sealed_before_deadline_minutes=round((ko - pd.Timedelta(minutes=LEAD_MIN) - T).total_seconds() / 60, 1),
                   history_cutoff_date=S.history_cutoff_date, state_sha256=S.state_sha256, newest_snapshot_age_hours=round(newest_age_h, 2),
                   input_snapshots=[dict(snapshot_id=s.snapshot_id, sha256=s.sha256, retrieved_utc=s.retrieved.strftime("%Y-%m-%dT%H:%M:%SZ")) for s in S.used],
                   results_added_to_frozen_state=int(len(S.additions)), integrity_events=ev_counts, model_hashes=hashes, model_key=mkey, artifact_manifest_sha256=msha, models=E.MODELS,
                   probs=dict(v2_frozen=dict(H=float(P2[i, 0]), D=float(P2[i, 1]), A=float(P2[i, 2])), v1_original=dict(H=float(P1[i, 0]), D=float(P1[i, 1]), A=float(P1[i, 2])),
                              v1_matched=dict(H=float(PM[i, 0]), D=float(PM[i, 1]), A=float(PM[i, 2])), v1_elo=dict(H=float(PE[i, 0]), D=float(PE[i, 1]), A=float(PE[i, 2]))),
                   home_n_prior=nh, away_n_prior=na, eligibility_reasons=reasons, primary_eligible=len(reasons) == 0, coverage_flags=["user_entered_source_no_editorial_review"],
                   attribution="Daten von OpenLigaDB (www.openligadb.de), lizenziert unter ODbL 1.0", licence="ODbL-1.0",
                   v2_feature_sha256=hashlib.sha256(np.ascontiguousarray(F2[v2["features"]].values.astype(float)[i]).tobytes()).hexdigest())
        rec["record_sha256"] = _hash_record(rec)
        recs.append(rec)
    return recs, rejected, S


def reconstruct_batch(recs, snaps_by_id, V, resolver, expected_manifest, **kw):
    groups = {}
    for r in recs:
        groups.setdefault((r["prediction_timestamp_utc"], tuple((x["snapshot_id"], x["sha256"]) for x in r["input_snapshots"])), []).append(r)
    ok, fails = 0, []
    for (t, sn), rs in groups.items():
        used = [snaps_by_id[i] for i, h in sn]
        if any(u.sha256 != h for u, (i, h) in zip(used, sn)):
            fails += [(r["fixture_id"], ["snapshot hash differs"]) for r in rs]; continue
        new, _, _ = predict_core(V, used, t, resolver, expected_manifest, namespace=rs[0]["namespace"], **kw)
        by = {x["fixture_id"]: x for x in new}
        for r in rs:
            n = by.get(r["fixture_id"])
            d = ["not reproducible"] if n is None else [k for k in ("probs", "state_sha256", "eligibility_reasons", "v2_feature_sha256", "artifact_manifest_sha256", "sealing_deadline_utc", "record_sha256") if n[k] != r[k]]
            if d: fails.append((r["fixture_id"], d))
            else: ok += 1
    return ok, fails


# ------------------------------------------------------------------------------------------------ official sealing
def _inside_temp(p):
    t = os.path.realpath(tempfile.gettempdir())
    return os.path.realpath(p).startswith(t)


def seal_official(*, approval_path, snapshot_paths, ledger_root, anchor_path, V, resolver, official_flag=False, sandbox=False, pnr_of=None, s1_additions=None, batch_id=None):
    """The sealing path. There is deliberately NO timestamp parameter. `sandbox=True` (tests only) requires every path to be inside the system temp directory."""
    if not appr.official_mode_enabled(official_flag):
        raise PermissionError("official mode is disabled (needs --official AND FOOTIQ_OFFICIAL_MODE=1)")
    if sandbox:
        if not all(_inside_temp(p) for p in (approval_path, ledger_root, anchor_path)):
            raise PermissionError("sandbox mode only works inside the temp directory")
    elif (os.path.realpath(approval_path) != os.path.realpath(appr.CANONICAL_APPROVAL) or os.path.realpath(ledger_root) != os.path.realpath(CANON_LEDGER) or os.path.realpath(anchor_path) != os.path.realpath(CANON_ANCHOR)):
        raise PermissionError("production paths must be the canonical approval, ledger and anchor locations")
    now = _now()
    hashes = E.verify_models()
    mf = artifacts.manifest(); msha = artifacts.manifest_sha(mf)
    a = appr.validate_approval(approval_path, now, expected_models=hashes, expected_manifest_sha=msha, competition_id=COMP, season=SEASON)
    led = ledger.ChainedLedger(ledger_root, anchor_path)
    v = led.verify()
    if not v["ok"]:
        raise ledger.LedgerError("ledger verification failed: " + "; ".join(v["errors"][:4]))
    prev = led.records()
    if prev:
        last = max(ts(r["prediction_timestamp_utc"]) for r in prev)
        if now < last:
            raise ClockError("system clock is earlier than the last sealed prediction: non-monotonic time")
    snaps = [load_snapshot(p) for p in snapshot_paths]
    check_order(snaps)
    newest = max(snaps, key=lambda s: s.retrieved)
    if newest.retrieved > now:
        raise ClockError("newest snapshot is dated in the future relative to the system clock")
    if newest.clock_skew_s is None or abs(newest.clock_skew_s) > SKEW_MAX_S:
        raise ClockError("clock skew at poll time unknown or above 120 s")
    recs, rejected, S = predict_core(V, snaps, now, resolver, mf, pnr_of=pnr_of, s1_additions=s1_additions, namespace="official" if not sandbox else "official-sandbox")
    if "matchdays" in a:
        recs = [r for r in recs if int(r["matchday"]) in set(a["matchdays"])]
    if len(recs) > a["max_fixtures"]:
        raise PermissionError(f"batch has {len(recs)} fixtures; approval allows {a['max_fixtures']}")
    if not recs:
        return dict(sealed=0, skipped=0, rejected=rejected, note="no authorised fixtures to seal")
    approval_sha = artifacts.digest_file(approval_path)
    for r in recs:
        r["counts_for_evaluation"] = not sandbox
        r["sandbox"] = bool(sandbox)
        r["approval_sha256"] = approval_sha
        r["protocol_sha256"] = a["protocol"]["sha256"]
        r.pop("record_sha256", None); r["record_sha256"] = _hash_record(r)
    bid = batch_id or "seal_" + now.strftime("%Y%m%dT%H%M%SZ")
    res = led.append_batch(recs, bid, header_extra=dict(artifact_manifest=mf, approval_sha256=approval_sha, state_sha256=S.state_sha256, system_time_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ")))
    res["rejected"] = rejected
    res["owner_ledger_entry"] = dict(batch_sha256=res.get("sha256"), batch_seq=res.get("batch_seq"), note="copy this anchor line into your own records")
    return res


# ------------------------------------------------------------------------------------------------ reassessment and reconciliation
def reassess(records, snaps, T_eval, resolver, analysis_checkpoint=False):
    """Side-car classification of each sealed record. Never edits records. Rules follow draft r2 clauses 7-10."""
    T_eval = ts(T_eval)
    used = check_order([s for s in snaps if s.retrieved <= T_eval])
    out = []
    for rec in records:
        mid = rec["ol_match_id"]; t_seal = ts(rec["prediction_timestamp_utc"])
        flags, elig, label = [], "eligible", "pending"
        hist = [(s, r) for s in used for r in s.records if r.source_ref == mid]
        if not used or not hist:
            out.append(_assess(rec, T_eval, ["not_found_in_any_snapshot"], "pending_fixture_not_found", "none", None)); continue
        in_last = any(r.source_ref == mid for r in used[-1].records)
        in_prev = len(used) > 1 and any(r.source_ref == mid for r in used[-2].records)
        if not in_last:
            if len(used) >= 2 and not in_prev and used[-2].retrieved > t_seal:
                out.append(_assess(rec, T_eval, ["fixture_removed_two_consecutive_snapshots"], "ineligible_fixture_removed", "none", used[-1].snapshot_id)); continue
            out.append(_assess(rec, T_eval, ["possibly_removed_awaiting_second_snapshot"], "pending_possible_removal", "none", used[-1].snapshot_id)); continue
        s, r = hist[-1]
        he = resolver.resolve("openligadb", COMP, r.home_raw)[0]; ae = resolver.resolve("openligadb", COMP, r.away_raw)[0]
        if (he, ae) != (rec["home_entity_id"], rec["away_entity_id"]):
            prev_ok = len(hist) >= 2 and (resolver.resolve("openligadb", COMP, hist[-2][1].home_raw)[0], resolver.resolve("openligadb", COMP, hist[-2][1].away_raw)[0]) == (he, ae)
            flags.append("fixture_identity_changed" if prev_ok else "identity_change_awaiting_confirmation")
            if prev_ok: elig = "ineligible_identity_changed"
        if r.kickoff_utc and ts(r.kickoff_utc) != ts(rec["scheduled_kickoff_utc"]):
            new_ko, old_ko = ts(r.kickoff_utc), ts(rec["scheduled_kickoff_utc"])
            if new_ko < old_ko:
                flags.append("kickoff_moved_earlier")
                if t_seal > new_ko - pd.Timedelta(minutes=LEAD_MIN): elig = "ineligible_sealed_too_late_after_move"
            else:
                flags.append("rescheduled_later" if (new_ko - old_ko) < pd.Timedelta(days=7) else "postponed_7_days_or_more")
                gap = (new_ko.tz_localize(None).normalize() - pd.Timestamp(rec["history_cutoff_date"])).days
                if gap > STALE_DAYS: elig = "ineligible_stale_after_reschedule"
                elif elig == "eligible": elig = "eligible_flagged_rescheduled"
        # late-arriving history: matches already played at sealing time, reported only afterwards, involving either club
        first_seen = {}
        for s2 in used:
            for r2 in s2.records:
                if r2.status == "completed" and r2.source_ref not in first_seen: first_seen[r2.source_ref] = s2.retrieved
        clubs = {rec["home_entity_id"], rec["away_entity_id"]}
        for m2, t2 in first_seen.items():
            if t2 > t_seal:
                rr = next(x for s2 in used for x in s2.records if x.source_ref == m2)
                e1 = resolver.resolve("openligadb", COMP, rr.home_raw)[0]; e2 = resolver.resolve("openligadb", COMP, rr.away_raw)[0]
                if clubs & {e1, e2} and rr.kickoff_utc and ts(rr.kickoff_utc) < t_seal and rr.match_date < rec["scheduled_kickoff_utc"][:10]:
                    flags.append("late_arriving_history_result"); break
        comp_v = [(x, y) for x, y in hist if y.status == "completed"]
        if comp_v and hist[-1][1].status != "completed":
            flags.append("withdrawn_result"); label = "conflict"; elig = "ineligible_unresolved_conflict"
        elif len({(y.regulation_home, y.regulation_away) for _, y in comp_v}) > 1:
            flags.append("corrected_result"); label = "conflict"; elig = "ineligible_unresolved_conflict"
        elif comp_v:
            last = comp_v[-1][1]
            if not last.label_eligible_90min:
                label = "unclassified_result"; elig = "ineligible_no_explicit_90min"
            else:
                first_t, last_t = comp_v[0][0].retrieved, comp_v[-1][0].retrieved; ko = ts(last.kickoff_utc)
                label = "confirmed" if (first_t >= ko + pd.Timedelta(hours=48) and last_t - first_t >= pd.Timedelta(hours=24)) else "pending_confirmation"
        else:
            if r.status == "past_date_no_result":
                flags.append("missing_result"); label = "missing"
                if analysis_checkpoint and T_eval - ts(r.kickoff_utc) > pd.Timedelta(days=LATE_DAYS_PENDING): elig = "ineligible_no_confirmed_result_at_checkpoint"
            elif r.status == "in_progress": label = "in_progress"
        if analysis_checkpoint and label in ("pending_confirmation", "pending"):
            elig = "ineligible_unconfirmed_at_checkpoint" if elig.startswith("eligible") else elig
        score = (comp_v[-1][1].regulation_home, comp_v[-1][1].regulation_away) if comp_v and label in ("confirmed", "pending_confirmation") else None
        out.append(_assess(rec, T_eval, flags, elig, label, used[-1].snapshot_id, score))
    return out


def _assess(rec, T_eval, flags, elig, label, snap_id, score=None):
    key = hashlib.sha256(json.dumps([rec["record_sha256"], flags, elig, label, snap_id], sort_keys=True).encode()).hexdigest()[:20]
    return dict(fixture_id=rec["fixture_id"], model_key=rec["model_key"], assessment_key=key, original_record_sha256=rec["record_sha256"], flags=flags, evaluation_eligibility=elig, label_status=label,
                score_90min=score, latest_snapshot=snap_id, assessed_utc=T_eval.strftime("%Y-%m-%dT%H:%M:%SZ"))


def reconcile_results(assessments, s1_results=None):
    """Outcome table: confirmed labels only. Optional S1 frame (home_entity_id, away_entity_id, gh, ga) is compared; disagreement is reported, never resolved."""
    out = []
    s1 = {}
    if s1_results is not None:
        for r in s1_results.itertuples(): s1[(r.home_entity_id, r.away_entity_id)] = (int(r.gh), int(r.ga))
    for a in assessments:
        if a["label_status"] == "confirmed":
            out.append(dict(fixture_id=a["fixture_id"], score_90min=a["score_90min"], sources="openligadb(two snapshots)", s1_check="not_available"))
        elif a["label_status"] == "conflict":
            out.append(dict(fixture_id=a["fixture_id"], score_90min=None, sources="conflict", s1_check="adjudication_required"))
    return out


def status_report(ledger_root, anchor_path, snaps=None, now=None, approval_path=appr.CANONICAL_APPROVAL):
    now = ts(now) if now is not None else _now()
    led = ledger.ChainedLedger(ledger_root, anchor_path)
    v = led.verify() if os.path.isdir(ledger_root) else dict(ok=True, errors=[], batches=0, records=0)
    out = dict(time_utc=str(now), ledger_exists=os.path.isdir(ledger_root), ledger_ok=v["ok"], ledger_errors=v["errors"], batches=v["batches"], records=v["records"],
               approval_file_exists=os.path.exists(approval_path), official_mode_env=os.environ.get("FOOTIQ_OFFICIAL_MODE") == "1")
    if snaps:
        n = max(snaps, key=lambda s: s.retrieved)
        out.update(newest_snapshot=n.snapshot_id, newest_snapshot_age_hours=round((now - n.retrieved).total_seconds() / 3600, 2), poll_clock_skew_s=n.clock_skew_s)
        up = sorted([r for r in n.records if r.status == "upcoming"], key=lambda r: r.kickoff_utc)
        if up:
            out["next_fixture_kickoff_utc"] = up[0].kickoff_utc
            out["next_sealing_deadline_utc"] = str(ts(up[0].kickoff_utc) - pd.Timedelta(minutes=LEAD_MIN))
    return out
