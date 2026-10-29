"""Versioned, non-destructive fresh-results ingestion for the openfootball (CC0) league sources.

Nothing here runs on a schedule. Commands (all write only below matched_v1_prospective_r1/ingestion/):
  plan                         read-only: compare the pinned upstream commits of the frozen snapshot with the current upstream HEAD (git ls-remote, no file transfer)
  fetch --confirm-download     shallow-clone the listed repos into a NEW immutable snapshot directory (the original _raw_sources clones are never touched)
  parse --snapshot DIR         parse + validate a snapshot against the frozen universe -> run directory with new results / fixtures / conflicts / unresolved
  selftest                     parse the PINNED original clones read-only and prove the pipeline reproduces the frozen data (no new results expected)
Original training snapshot (V_universe.pkl, dataset v1.1, _raw_sources) is opened read-only and never written.
"""
import argparse, hashlib, json, os, re, stat, subprocess, sys, time
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from v2_common import P, PREP, OUT, sha  # noqa
sys.path.insert(0, os.path.join(P, "FootIQ_Dataset_Submission", "_build"))
import footballtxt as ft  # noqa
import build_club_matches as bcm  # noqa

ING = os.path.join(OUT, "matched_v1_prospective_r1", "ingestion")
RAWPINNED = os.path.join(P, "FootIQ_Dataset_Submission", "_raw_sources")
TRAIN_CUTOFF = "2026-09-20"
APPROVED_SOURCE = dict(name="openfootball (CC0 / public domain)", url_prefix="https://github.com/openfootball/")
LEAGUE_REPOS = ["austria", "belgium", "deutschland", "england", "espana", "europe", "italy", "south-america", "world"]
REG = re.compile(r"(Matchday \d+$)|(^\d+\. Round$)|(^Regular Season - \d+$)|(^\d+st Phase - \d+$)|(^Championship Round - \d+$)|(^Relegation Round - \d+$)|(^Fase (Campeón|Complementación), Gruppe \d+$)|(^Group [A-F]$)|(^Results( \(continuation\))?$)")
PROV = re.compile(r"^openfootball (\S+)@(\w+) (.+?):L(\d+)$")


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def frozen_reference():
    V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
    pv = V.provenance.str.extract(PROV.pattern)
    V = V.assign(src_repo=pv[0], src_commit=pv[1], src_file=pv[2], src_line=pv[3])
    fmap = V.groupby("src_file").agg(competition_id=("competition_id", "first"), season_corrected=("season_corrected", "first"), tier=("tier", "first"), competition_type=("competition_type", "first")).to_dict("index")
    ent = pd.concat([V[["competition_id", "home_team_name", "home_entity_id"]].set_axis(["c", "n", "e"], axis=1), V[["competition_id", "away_team_name", "away_entity_id"]].set_axis(["c", "n", "e"], axis=1)])
    ent["scoped"] = ent.e.str.startswith("SRCSCOPED|")
    ent = ent.sort_values("scoped").drop_duplicates(["c", "n"], keep="first")
    emap = {(r.c, r.n): r.e for r in ent.itertuples()}
    return V, fmap, emap


def classify(res, date, run_date):
    """returns (status, rated_label_ok, note)"""
    if res is None:
        return "unresolved", False, "no result field"
    st = res.get("status")
    note = (res.get("note") or "")
    low = note.lower()
    if st == "scored":
        if res.get("aet") or res.get("pen"):
            return "completed_extra_time_or_penalties", False, "extra time/penalties in a league row: 90-minute label ambiguous -> not used"
        if any(k in low for k in ("awd", "w/o", "abd", "awarded", "abandon")):
            return "awarded_or_abandoned", False, note
        return "completed", True, note
    if any(k in low for k in ("postp", "ppd")):
        return "postponed", False, note
    if any(k in low for k in ("cancel", "canc")):
        return "cancelled", False, note
    if st == "no_score_token":
        return "awarded_or_abandoned" if any(k in low for k in ("awd", "w/o", "abd")) else "unresolved", False, note
    if st == "unscored":
        return ("upcoming" if str(date) >= run_date else "past_date_no_result"), False, ""
    return "unresolved", False, note


def parse_snapshot(root, run_id, retrieval_ts, source_meta, run_date, cutoff=TRAIN_CUTOFF):
    V, fmap, emap = frozen_reference()
    if cutoff != TRAIN_CUTOFF:                      # replay mode: pretend the frozen universe ended earlier
        V = V[V.match_date <= cutoff].copy()
    rows, issues_all, files_seen = [], [], []
    for repo in LEAGUE_REPOS:
        for dp, dn, fn in os.walk(os.path.join(root, repo)):
            dn[:] = [d for d in dn if d != ".git"]
            for n in sorted(fn):
                full = os.path.join(dp, n); rel = os.path.relpath(full, root).replace("\\", "/")
                info = bcm.describe(rel)
                if info is None or info["std"][1] != "domestic_league":
                    continue
                known = fmap.get(rel)
                comp = known["competition_id"] if known else f"{info['ns']}:{info['code']}"
                text = open(full, "rb").read().decode("utf-8", "replace")
                title, matches, issues = ft.parse_text(text, int(info["season"][:4]))
                files_seen.append(dict(file=rel, sha256=hashlib.sha256(open(full, "rb").read()).hexdigest(), n_matches=len(matches), known_in_frozen=bool(known)))
                for ln, kind, txt in issues:
                    issues_all.append(dict(file=rel, line=ln, kind=kind, text=txt))
                for m in matches:
                    st, rated_ok, note = classify(m["res"], m["date"], run_date)
                    h, a = ft.split_team(m["team1"])[0], ft.split_team(m["team2"])[0]
                    season = known["season_corrected"] if known else info["season"]
                    he, ae = emap.get((comp, h)), emap.get((comp, a))
                    reg = bool(REG.search(m["stage"] or "")) and not re.search(r"play-?off", m["stage"] or "", re.I)
                    gh, ga = (m["res"]["main"] if (m["res"] and m["res"].get("main")) else (np.nan, np.nan))
                    probs = []
                    if not known: probs.append("competition_file_not_in_frozen_universe")
                    if he is None or ae is None: probs.append("team_not_resolved_to_entity")
                    if not reg: probs.append("not_regular_round_stage")
                    if m["date"] is None: probs.append("date_missing")
                    if st == "completed" and not (0 <= gh <= 25 and 0 <= ga <= 25): probs.append("implausible_score")
                    rows.append(dict(source_file=rel, source_line=m["line_no"], competition_id=comp, season=season, match_date=m["date"], kickoff_local=m["kickoff_local"], stage=m["stage"], home_team=h, away_team=a,
                                     home_entity_id=he, away_entity_id=ae, gh=gh, ga=ga, status=st, label_90_ok=rated_ok, regular_round=reg, tier=(known or {}).get("tier", info["std"][2]), problems=";".join(probs), note=note,
                                     source_commit=source_meta.get(rel.split("/")[0], {}).get("commit", ""), retrieved_utc=retrieval_ts, raw_text=m["raw_line"]))
    R = pd.DataFrame(rows)
    R["natural_key"] = R.competition_id + "|" + R.season.astype(str) + "|" + R.match_date.astype(str) + "|" + R.home_entity_id.fillna(R.home_team) + "|" + R.away_entity_id.fillna(R.away_team)
    # duplicates / conflicts inside the snapshot
    g = R.groupby("natural_key")
    dups = R[g.natural_key.transform("size") > 1].copy()
    conf_in = dups.groupby("natural_key").filter(lambda d: d[["gh", "ga"]].drop_duplicates().shape[0] > 1 or d.status.nunique() > 1)
    # comparison with the frozen universe
    Vk = V.assign(natural_key=V.competition_id + "|" + V.season_corrected.astype(str) + "|" + V.match_date.astype(str) + "|" + V.home_entity_id + "|" + V.away_entity_id)
    Vg = Vk.groupby("natural_key").agg(f_gh=("gh", "first"), f_ga=("ga", "first"), f_n=("gh", "size")).reset_index()
    M = R.merge(Vg, on="natural_key", how="left")
    old = M[(M.match_date.astype(str) <= cutoff)]
    hist_conflicts = old[(old.f_n.notna()) & (old.status == "completed") & ((old.gh != old.f_gh) | (old.ga != old.f_ga))]
    hist_missing = old[(old.f_n.isna()) & (old.status == "completed") & (old.problems == "")]
    new_c = M[(M.match_date.astype(str) > cutoff) & (M.status == "completed")]
    new_ok = new_c[(new_c.problems == "") & new_c.label_90_ok & new_c.regular_round & ~new_c.natural_key.isin(set(conf_in.natural_key))].copy()
    unresolved = M[(M.problems != "") | M.status.isin(["unresolved", "past_date_no_result", "postponed", "cancelled", "awarded_or_abandoned", "completed_extra_time_or_penalties"])]
    unresolved = unresolved[unresolved.match_date.astype(str) > cutoff]
    fixtures = M[(M.status == "upcoming") & (M.match_date.astype(str) >= run_date)]
    rd = os.path.join(ING, "runs", run_id); os.makedirs(rd, exist_ok=True)
    new_ok.drop(columns=["f_gh", "f_ga", "f_n"]).to_csv(os.path.join(rd, "new_results.csv"), index=False, encoding="utf-8-sig")
    fixtures.drop(columns=["f_gh", "f_ga", "f_n"]).to_csv(os.path.join(rd, "fixtures.csv"), index=False, encoding="utf-8-sig")
    unresolved.drop(columns=["f_gh", "f_ga", "f_n"]).to_csv(os.path.join(rd, "unresolved_or_non_completed.csv"), index=False, encoding="utf-8-sig")
    pd.concat([hist_conflicts.assign(kind="historical_score_differs_from_frozen"), conf_in.assign(kind="conflicting_rows_inside_snapshot")]).to_csv(os.path.join(rd, "conflicts.csv"), index=False, encoding="utf-8-sig")
    dups.to_csv(os.path.join(rd, "duplicates.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(issues_all).to_csv(os.path.join(rd, "parser_issues.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(files_seen).to_csv(os.path.join(rd, "files_hashed.csv"), index=False)
    # refreshed universe = frozen universe + new results (separate file; the frozen pickle is never modified)
    if len(new_ok):
        add = pd.DataFrame(dict(record_id="NEW:" + run_id + ":" + new_ok.source_file + ":L" + new_ok.source_line.astype(str), competition_id=new_ok.competition_id.values, season_corrected=new_ok.season.values,
                                match_date=new_ok.match_date.astype(str).values, dt=pd.to_datetime(new_ok.match_date).values, home_entity_id=new_ok.home_entity_id.values, away_entity_id=new_ok.away_entity_id.values,
                                home_team_name=new_ok.home_team.values, away_team_name=new_ok.away_team.values, tier=new_ok.tier.values, competition_type="domestic_league", regular_round_robin_stage=True,
                                rated=True, gh=new_ok.gh.values, ga=new_ok.ga.values, provenance=("openfootball " + new_ok.source_file + ":L" + new_ok.source_line.astype(str) + " retrieved " + retrieval_ts).values))
    else:
        add = V.iloc[0:0]
    refreshed = pd.concat([V.drop(columns=["src_repo", "src_commit", "src_file", "src_line"]), add], ignore_index=True)
    refreshed.to_pickle(os.path.join(rd, "results_universe_refreshed.pkl"))
    s = dict(run_id=run_id, run_date=run_date, retrieved_utc=retrieval_ts, snapshot_root=root, source=APPROVED_SOURCE, repos=source_meta, files_parsed=len(files_seen), rows_parsed=len(R),
             frozen_training_cutoff=cutoff, new_completed_results=int(len(new_ok)), latest_new_result_date=(str(new_ok.match_date.max()) if len(new_ok) else None),
             upcoming_fixtures=int(len(fixtures)), unresolved_or_non_completed_after_cutoff=int(len(unresolved)), historical_score_conflicts=int(len(hist_conflicts)),
             historical_rows_in_snapshot_not_in_frozen=int(len(hist_missing)), in_snapshot_conflicts=int(conf_in.natural_key.nunique()), duplicate_groups=int(dups.natural_key.nunique()),
             frozen_rows_matched=int(old.f_n.notna().sum()), refreshed_universe_sha256=sha(os.path.join(rd, "results_universe_refreshed.pkl")), parser_issue_rows=len(issues_all))
    json.dump(s, open(os.path.join(rd, "run_manifest.json"), "w"), indent=1, default=str)
    for f in os.listdir(rd):
        os.chmod(os.path.join(rd, f), stat.S_IREAD)
    return s


def cmd_plan(a):
    out = []
    for repo in LEAGUE_REPOS:
        d = os.path.join(RAWPINNED, repo)
        url = subprocess.run(["git", "-C", d, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
        pinned = subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        up = "" if a.offline else subprocess.run(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True, timeout=60).stdout.split("\t")[0]
        out.append(dict(repo=repo, url=url, pinned_commit=pinned, upstream_head=up or None, upstream_newer=(None if not up else up != pinned), approved=url.startswith(APPROVED_SOURCE["url_prefix"])))
    os.makedirs(os.path.join(ING, "plans"), exist_ok=True)
    p = os.path.join(ING, "plans", f"plan_{utc().replace(':', '')}.json")
    json.dump(dict(generated_utc=utc(), repos=out), open(p, "w"), indent=1); print(json.dumps(out, indent=1)); print(p)


def cmd_fetch(a):
    if not a.confirm_download:
        sys.exit("refusing to download without --confirm-download (explicit approval required)")
    sid = "snap_" + utc().replace(":", "").replace("-", "")
    root = os.path.join(ING, "snapshots", sid); os.makedirs(root)
    meta = {}
    for repo in (a.repos.split(",") if a.repos else LEAGUE_REPOS):
        url = f"{APPROVED_SOURCE['url_prefix']}{repo}.git"
        assert url.startswith(APPROVED_SOURCE["url_prefix"])
        t = utc()
        subprocess.run(["git", "clone", "--depth", "1", "--no-tags", url, os.path.join(root, repo)], check=True)
        c = subprocess.run(["git", "-C", os.path.join(root, repo), "log", "-1", "--format=%H|%cI"], capture_output=True, text=True).stdout.strip()
        meta[repo] = dict(url=url, commit=c.split("|")[0], commit_date=c.split("|")[1], retrieved_utc=t)
    json.dump(meta, open(os.path.join(root, "SNAPSHOT_MANIFEST.json"), "w"), indent=1)
    print(sid)


def cmd_parse(a):
    root = os.path.abspath(a.snapshot); meta = json.load(open(os.path.join(root, "SNAPSHOT_MANIFEST.json")))
    rid = "run_" + os.path.basename(root) + "_" + utc().replace(":", "").replace("-", "")
    ts = max(m["retrieved_utc"] for m in meta.values())
    print(json.dumps(parse_snapshot(root, rid, ts, meta, a.run_date or time.strftime("%Y-%m-%d")), indent=1, default=str))


def cmd_replay(a):
    """Pretend the frozen universe ended at --cutoff and re-ingest the later (already known) results from the pinned clones through the normal path."""
    meta = {}
    for repo in LEAGUE_REPOS:
        d = os.path.join(RAWPINNED, repo)
        c = subprocess.run(["git", "-C", d, "log", "-1", "--format=%H|%cI"], capture_output=True, text=True).stdout.strip()
        meta[repo] = dict(url=f"{APPROVED_SOURCE['url_prefix']}{repo}.git", commit=c.split("|")[0], commit_date=c.split("|")[1], retrieved_utc="replay of pinned original clone")
    nxt = (pd.Timestamp(a.cutoff) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    rid = f"replay_{a.cutoff}_" + utc().replace(":", "").replace("-", "")
    print(json.dumps(parse_snapshot(RAWPINNED, rid, "replay", meta, nxt, cutoff=a.cutoff), indent=1, default=str))


def cmd_selftest(a):
    meta = {}
    for repo in LEAGUE_REPOS:
        d = os.path.join(RAWPINNED, repo)
        c = subprocess.run(["git", "-C", d, "log", "-1", "--format=%H|%cI"], capture_output=True, text=True).stdout.strip()
        meta[repo] = dict(url=f"{APPROVED_SOURCE['url_prefix']}{repo}.git", commit=c.split("|")[0], commit_date=c.split("|")[1], retrieved_utc="2026-10-20 (pinned original clone, read-only)")
    rid = "selftest_" + utc().replace(":", "").replace("-", "")
    print(json.dumps(parse_snapshot(RAWPINNED, rid, "2026-10-20", meta, "2026-10-21"), indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    p1 = sp.add_parser("plan"); p1.add_argument("--offline", action="store_true"); p1.set_defaults(f=cmd_plan)
    p2 = sp.add_parser("fetch"); p2.add_argument("--confirm-download", action="store_true"); p2.add_argument("--repos"); p2.set_defaults(f=cmd_fetch)
    p3 = sp.add_parser("parse"); p3.add_argument("--snapshot", required=True); p3.add_argument("--run-date"); p3.set_defaults(f=cmd_parse)
    p4 = sp.add_parser("selftest"); p4.set_defaults(f=cmd_selftest)
    p5 = sp.add_parser("replay"); p5.add_argument("--cutoff", required=True); p5.set_defaults(f=cmd_replay)
    a = ap.parse_args(); sys.stdout.reconfigure(encoding="utf-8"); a.f(a)
