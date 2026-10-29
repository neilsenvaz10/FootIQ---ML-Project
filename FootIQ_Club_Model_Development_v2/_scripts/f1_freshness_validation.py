"""Freshness validation (read-only on all frozen data and models): competition coverage, fixture identity matching, kickoff-time safety, replay of result incorporation,
historical eligibility simulation, throughput estimate and the current eligible-fixture count."""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e4_prospective_logger as E
import d11_prospective_logger as D
from v2_models import *  # noqa
sys.stdout.reconfigure(encoding="utf-8")
OUTD = os.path.join(OUT, "freshness_validation_r1"); os.makedirs(OUTD, exist_ok=True)
ING = os.path.join(E.NEW, "ingestion", "runs")
selfrun = sorted(glob.glob(os.path.join(ING, "selftest_*")))[-1]
replay = sorted(glob.glob(os.path.join(ING, "replay_2026-08-31_*")))[-1]
res = {}
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
Vsha = sha(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
RUN = "2026-10-21"
# ---------------------------------------------------------------- 2/3 competition coverage
L = V[V.competition_type == "domestic_league"]
last = L.groupby("competition_id").agg(last_result=("match_date", "max"), n_results=("match_date", "size"), tier=("tier", "first"), country=("competition_country", "first"))
cur_season = L.sort_values("match_date").groupby("competition_id").season_corrected.last().rename("latest_season")
fx = pd.read_csv(os.path.join(selfrun, "fixtures.csv"), encoding="utf-8-sig", low_memory=False)
un = pd.read_csv(os.path.join(selfrun, "unresolved_or_non_completed.csv"), encoding="utf-8-sig", low_memory=False)
fx["problems"] = fx.problems.fillna(""); un["problems"] = un.problems.fillna("")
pnr = un[un.status == "past_date_no_result"]
cov = last.join(cur_season)
cov["upcoming_fixtures_in_source"] = fx.groupby("competition_id").size().reindex(cov.index).fillna(0).astype(int)
cov["next_fixture_date"] = fx.groupby("competition_id").match_date.min().reindex(cov.index)
cov["past_dated_without_result"] = pnr.groupby("competition_id").size().reindex(cov.index).fillna(0).astype(int)
cov["earliest_missing_result_date"] = pnr.groupby("competition_id").match_date.min().reindex(cov.index)
cov["other_unresolved_after_cutoff"] = un[un.status != "past_date_no_result"].groupby("competition_id").size().reindex(cov.index).fillna(0).astype(int)
cov["days_last_result_to_run_date"] = (pd.Timestamp(RUN) - pd.to_datetime(cov.last_result)).dt.days
def cat(r):
    if r.upcoming_fixtures_in_source == 0 and r.past_dated_without_result == 0:
        return "no_fixtures_in_source (off-season or not published)"
    if r.past_dated_without_result > 0:
        return "in_season_results_missing_after_cutoff"
    if r.days_last_result_to_run_date <= 14:
        return "current"
    return "fixtures_published_but_no_recent_results"
cov["status"] = cov.apply(cat, axis=1)
cov.reset_index().to_csv(os.path.join(OUTD, "02_competition_coverage.csv"), index=False)
res["competitions_total"] = int(len(cov)); res["competition_status_counts"] = cov.status.value_counts().to_dict()
res["competitions_with_a_result_after_2026-09-20"] = int((cov.last_result > "2026-09-20").sum())
res["latest_result_date_overall"] = str(cov.last_result.max())
res["competitions_with_result_in_last_14d_before_cutoff"] = int((cov.last_result >= "2026-09-06").sum())
res["past_dated_fixtures_without_result_total"] = int(len(pnr)); res["past_dated_without_result_competitions"] = int(pnr.competition_id.nunique())
res["past_dated_without_result_date_range"] = [str(pnr.match_date.min()), str(pnr.match_date.max())]
res["past_dated_without_result_by_month"] = pnr.match_date.astype(str).str[:7].value_counts().sort_index().to_dict()
print(cov.status.value_counts())

# ---------------------------------------------------------------- 5 fixture identity matching
ent = pd.concat([V[["competition_id", "home_team_name", "home_entity_id"]].set_axis(["competition_id", "n", "e"], axis=1), V[["competition_id", "away_team_name", "away_entity_id"]].set_axis(["competition_id", "n", "e"], axis=1)]).drop_duplicates()
amb = ent.groupby(["competition_id", "n"]).e.nunique(); amb = amb[amb > 1]
res["ambiguous_name_to_entity_mappings"] = int(len(amb))
fu = fx[fx.status == "upcoming"].copy()
fu["h_ok"] = fu.home_entity_id.notna(); fu["a_ok"] = fu.away_entity_id.notna()
res["upcoming_fixtures_in_source"] = int(len(fu)); res["both_teams_resolved"] = int((fu.h_ok & fu.a_ok).sum())
bad = fu[~(fu.h_ok & fu.a_ok)]
bad[["competition_id", "season", "match_date", "home_team", "away_team", "problems"]].to_csv(os.path.join(OUTD, "05_unresolved_fixture_teams.csv"), index=False)
res["fixtures_with_unresolved_team"] = int(len(bad)); res["unresolved_team_names_distinct"] = int(pd.concat([bad.home_team[~bad.h_ok], bad.away_team[~bad.a_ok]]).nunique())
res["fixtures_dropped_for_non_regular_stage"] = int((~fu.regular_round).sum()); res["fixtures_with_other_problems"] = {k: int(v) for k, v in fu.problems.str.split(";").explode().value_counts().items() if k}
res["scoped_entities_in_fixtures"] = int(fu.home_entity_id.fillna("").str.startswith("SRCSCOPED|").sum() + fu.away_entity_id.fillna("").str.startswith("SRCSCOPED|").sum())
# cross-check against the project's own upcoming fixtures file and the earlier dry-run list
u09 = pd.read_csv(os.path.join(P, "FootIQ_Dataset_Submission", "09_Upcoming_Fixtures.csv"), low_memory=False)
u09 = u09[(u09.competition_type == "domestic_league") & (u09.fixture_status == "upcoming")]
k1 = set(zip(u09.competition_id, u09.match_date, u09.home_team, u09.away_team)); k2 = set(zip(fu.competition_id, fu.match_date.astype(str), fu.home_team, fu.away_team))
res["upcoming_in_09_file"] = len(k1); res["upcoming_in_reparse"] = len(k2); res["in_both"] = len(k1 & k2); res["only_in_09_file"] = len(k1 - k2); res["only_in_reparse"] = len(k2 - k1)
# history depth of fixture clubs
cnt = pd.concat([L.groupby("home_entity_id").size(), L.groupby("away_entity_id").size()], axis=1).fillna(0).sum(axis=1)
fu["h_hist"] = fu.home_entity_id.map(cnt).fillna(0); fu["a_hist"] = fu.away_entity_id.map(cnt).fillna(0)
res["fixtures_with_a_club_under_5_prior_rated_matches"] = int(((fu.h_hist < 5) | (fu.a_hist < 5)).sum())

# ---------------------------------------------------------------- 6 kickoff-time safety
ko = fu.kickoff_local.notna()
kt = fu.groupby("competition_id").apply(lambda g: pd.Series(dict(fixtures=len(g), kickoff_time_known_share=float(g.kickoff_local.notna().mean()))), include_groups=False)
kt.reset_index().to_csv(os.path.join(OUTD, "06_kickoff_time_coverage.csv"), index=False)
res["kickoff_time_known_share"] = float(ko.mean())
# earliest-possible-kickoff rule: a fixture on date D is loggable if sealed before D-1 09:00 UTC. Loggable share by lead time from "today"
fu["dt"] = pd.to_datetime(fu.match_date)
now = pd.Timestamp("2026-10-21 14:00", tz="UTC")
fu["latest_seal_utc"] = fu.dt.dt.tz_localize("UTC") - pd.Timedelta(hours=14) - pd.Timedelta(minutes=60)
fu["hours_available_from_now"] = (fu.latest_seal_utc - now).dt.total_seconds() / 3600
res["fixtures_sealable_if_sealed_now"] = int((fu.hours_available_from_now > 0).sum())
res["fixtures_dated_before_2026-10-23"] = int((fu.match_date.astype(str) < "2026-10-23").sum())
res["min_lead_rule"] = "match date 00:00 UTC - 14 h - 60 min (needed because local kickoff time zones are not stored); costs 15-39 h of lead, never makes pre-match logging unsafe, only conservative"
res["alternative_if_tz_mapping_approved"] = "competition-country time zone table would shorten the lead to kickoff time - 60 min where the local time is known (only %.0f%% of fixtures)" % (100 * ko.mean())

# ---------------------------------------------------------------- 4 replay: incorporation of ingested results leaves features identical
ref = pd.read_pickle(os.path.join(replay, "results_universe_refreshed.pkl"))
man = json.load(open(os.path.join(replay, "run_manifest.json")))
Vc = V[V.match_date <= "2026-08-31"]
fu_ids = fu[(fu.problems == "") & fu.h_ok & fu.a_ok & (fu.match_date.astype(str) >= "2026-10-24")].head(600)
fxd = pd.DataFrame(dict(fixture_id=("F" + fu_ids.competition_id + fu_ids.match_date.astype(str) + fu_ids.home_team).values, dt=pd.to_datetime(fu_ids.match_date).values, h=fu_ids.home_entity_id.values, a=fu_ids.away_entity_id.values,
                        comp=fu_ids.competition_id.values, season=fu_ids.season.values, tier=fu_ids.tier.values)).drop_duplicates("fixture_id")
Fa, F1a = D.features_for(V, fxd); Fb, F1b = D.features_for(ref, fxd)
cols = D.load_models()[0]["features"]
Fa, Fb = Fa.loc[fxd.fixture_id], Fb.loc[fxd.fixture_id]
d2 = float(np.nanmax(np.abs(Fa[cols].values.astype(float) - Fb[cols].values.astype(float))))
d1 = float(np.nanmax(np.abs(F1a.loc[fxd.fixture_id][["elo_diff", "home_ppg5", "away_ppg5", "home_days_rest"]].values.astype(float) - F1b.loc[fxd.fixture_id][["elo_diff", "home_ppg5", "away_ppg5", "home_days_rest"]].values.astype(float))))
res["replay"] = dict(cutoff="2026-08-31", results_reingested=man["new_completed_results"], expected=int(((V.match_date > "2026-08-31") & (V.competition_type == "domestic_league") & V.rated).sum()),
                     historical_score_conflicts=man["historical_score_conflicts"], fixtures_compared=len(fxd), v2_feature_max_abs_diff_vs_full_frozen_state=d2, v1_feature_max_abs_diff=d1,
                     note="state = frozen universe truncated at 2026-08-31 + results re-ingested through the normal parse/validate path; features for later fixtures equal those from the full state; model files untouched")
print(res["replay"])

# ---------------------------------------------------------------- 7 eligibility checker: (a) current state, (b) simulation when results are current
v2f = E.verify_models()
fx_main = pd.DataFrame(dict(fixture_id=fu.record_id if "record_id" in fu else (fu.competition_id + "|" + fu.match_date.astype(str) + "|" + fu.home_team).values, dt=fu.dt.values, h=fu.home_entity_id.values, a=fu.away_entity_id.values,
                            comp=fu.competition_id.values, season=fu.season.values, tier=fu.tier.values, home_name=fu.home_team.values, away_name=fu.away_team.values,
                            kickoff=(fu.match_date.astype(str) + " " + fu.kickoff_local.fillna("00:00")).values, kickoff_known=ko.values))
fx_main = fx_main[fu.h_ok.values & fu.a_ok.values & (fu.problems == "").values & (fu.dt >= "2026-10-24").values].drop_duplicates("fixture_id").reset_index(drop=True)
pnr_f = pnr.dropna(subset=["home_entity_id", "away_entity_id"]).assign(comp=lambda d: d.competition_id, h=lambda d: d.home_entity_id, a=lambda d: d.away_entity_id)[["comp", "h", "a"]]
recs, rej = E.predict(fx_main, V, past_no_result=pnr_f, snapshot_id="frozen_universe_2026-10-20 (pinned openfootball commits)", snapshot_sha=Vsha, mode="dry_run", now=pd.Timestamp("2026-10-21 14:00", tz="UTC"))
R = pd.DataFrame(recs)
res["current_state"] = dict(fixtures_checked=len(fx_main), logged_dry_run=len(R), rejected=len(rej), primary_eligible=int(R.primary_eligible.sum()))
reasons = R.eligibility_reasons.explode().astype(str).str.replace(r"\(gap_days=\d+\)", "", regex=True).value_counts()
res["current_state"]["fixtures_failing_each_check"] = reasons.to_dict()
only_other = R[R.eligibility_reasons.apply(lambda x: all(r.startswith(("stale", "club_has_unresolved")) for r in x))]
res["current_state"]["would_be_eligible_if_results_were_current"] = int(len(only_other))
res["current_state"]["fail_for_history_or_identity_regardless"] = int(len(R) - len(only_other))
R[["fixture_id", "competition_id", "scheduled_kickoff", "primary_eligible", "eligibility_reasons", "coverage_flags"]].astype(str).to_csv(os.path.join(OUTD, "07_current_eligibility_per_fixture.csv"), index=False)
# (b) simulation: as-of 2026-09-13 (cutoff 09-12), fixtures = matches that were really played 09-15..09-20 (used only as schedule rows; no outcome is read or used)
Vs = V[V.match_date <= "2026-09-12"]
sim = V[(V.match_date >= "2026-09-15") & (V.match_date <= "2026-09-20") & (V.competition_type == "domestic_league")]
fxs = pd.DataFrame(dict(fixture_id=sim.record_id.values, dt=pd.to_datetime(sim.match_date).values, h=sim.home_entity_id.values, a=sim.away_entity_id.values, comp=sim.competition_id.values, season=sim.season_corrected.values,
                        tier=sim.tier.values, home_name=sim.home_team_name.values, away_name=sim.away_team_name.values, kickoff=(sim.match_date + " 00:00").values, kickoff_known=False))
rs, _ = E.predict(fxs, Vs, past_no_result=pnr_f.iloc[0:0], snapshot_id="sim", snapshot_sha="sim", mode="dry_run", now=pd.Timestamp("2026-09-13 12:00", tz="UTC"))
S = pd.DataFrame(rs)
res["simulation_when_results_are_current"] = dict(asof="2026-09-13", fixtures=len(fxs), logged=len(S), primary_eligible=int(S.primary_eligible.sum()), eligible_share=float(S.primary_eligible.mean()),
                                                  reasons=S.eligibility_reasons.explode().astype(str).str.replace(r"\(gap_days=\d+\)", "", regex=True).value_counts().to_dict(),
                                                  competitions_with_eligible=int(S[S.primary_eligible].competition_id.nunique()), note="outcomes not read; schedule rows only; no unresolved past fixtures assumed")

# ---------------------------------------------------------------- throughput estimate (historical weekly volume, 2025-08..2026-05)
H = L[(L.match_date >= "2025-08-01") & (L.match_date <= "2026-05-31")].copy()
H["wk"] = pd.to_datetime(H.match_date).dt.to_period("W")
wk = H.groupby("wk").size()
share = res["simulation_when_results_are_current"]["eligible_share"]
res["throughput"] = dict(median_matches_per_week=float(wk.median()), p25=float(wk.quantile(.25)), p75=float(wk.quantile(.75)), assumed_eligible_share=share,
                         weeks_to_5000_eligible_at_median=float(5000 / (wk.median() * share)), weeks_to_5000_eligible_at_p25=float(5000 / (wk.quantile(.25) * share)),
                         competitions_active_per_month_median=float(H.groupby(pd.to_datetime(H.match_date).dt.to_period("M")).competition_id.nunique().median()),
                         caveat="volume taken from 2025-26 in-season weeks; summer break / international breaks reduce it; eligible share from the Sep-2026 simulation")
json.dump(res, open(os.path.join(OUTD, "freshness_results.json"), "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str)[:6000])
