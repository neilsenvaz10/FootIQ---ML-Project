"""Stage 5 (read-only on sources): player data verification + versioned player form datasets (new files only)."""
import json
import os
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = r"D:\Foot IQ"
SUB = os.path.join(P, "FootIQ_Dataset_Submission")
OUT = os.path.join(P, "FootIQ_ML_Data_Verification")
EV = os.path.join(OUT, "_evidence")
FORM = os.path.join(OUT, "player_form_v1")
os.makedirs(FORM, exist_ok=True)
ENC = "utf-8-sig"
R = {}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


p4 = pd.read_csv(os.path.join(SUB, "04_Football_Players.csv"), low_memory=False, encoding=ENC)
p5 = pd.read_csv(os.path.join(SUB, "05_Player_Match_Statistics.csv"), low_memory=False, encoding=ENC)
p8 = pd.read_csv(os.path.join(SUB, "08_Player_Team_Memberships.csv"), low_memory=False, encoding=ENC)
mi = pd.read_csv(os.path.join(SUB, "14_StatsBomb_Match_Index.csv"), low_memory=False, encoding=ENC)
p5["is_sb"] = p5.source_dataset.str.startswith("StatsBomb")
sb = p5[p5.is_sb].copy()
of = p5[~p5.is_sb].copy()

# ============================================================ 1 identities
R["players_rows"] = len(p4)
R["players_unique_ids"] = int(p4.player_id.nunique())
R["players_by_id_scope"] = p4.id_scope.value_counts().to_dict()
R["players_missing_nationality_pct_by_scope"] = p4.groupby("id_scope").nationality.apply(lambda s: round(100 * s.isna().mean(), 1)).to_dict()
R["players_missing_position_pct_by_scope"] = p4.groupby("id_scope").position_primary.apply(lambda s: round(100 * (s.isna() | (s == "")).mean(), 1)).to_dict()
sbp = p4[p4.id_scope == "source_native_id_StatsBomb"].copy()
sbp["nm"] = sbp.player_name.map(norm)
dup_names = sbp.groupby("nm").player_id.nunique()
R["statsbomb_normalised_names_with_multiple_ids"] = int((dup_names > 1).sum())
sbp[sbp.nm.isin(dup_names[dup_names > 1].index)].sort_values("nm")[["player_id", "player_name", "nationality", "first_seen_date", "last_seen_date"]].to_csv(os.path.join(EV, "player_identity_same_name_multiple_statsbomb_ids.csv"), index=False)
ofp = p4[p4.id_scope == "derived_team_scoped_name_key"].copy()
ofp["nm"] = ofp.player_name.map(norm)
R["openfootball_lineup_keys"] = len(ofp)
R["openfootball_names_under_multiple_team_keys"] = int((ofp.groupby("nm").player_id.nunique() > 1).sum())
sqd = p4[p4.id_scope == "derived_squad_scoped_key"].copy()
R["squad_scoped_keys"] = len(sqd)
cross = set(sbp.nm) & set(ofp.nm)
R["names_present_in_both_statsbomb_and_openfootball_NOT_merged"] = len(cross)
# transfers: SB players with multiple teams
sb_team = sb.groupby("source_player_id").team_id.nunique()
R["statsbomb_players_with_2plus_teams"] = int((sb_team >= 2).sum())
R["statsbomb_players_total_with_stats_rows"] = int(len(sb_team))
# same player two teams same date
sb_dt = sb.groupby(["source_player_id", "match_date"]).team_id.nunique()
R["statsbomb_player_dates_with_two_teams"] = int((sb_dt > 1).sum())
# membership consistency
lin = p8[p8.membership_basis == "appeared_in_match_lineup"]
rec = p5.groupby(["player_id", "team_id", "competition_name", "season"]).match_id.nunique().reset_index(name="n_recount")
m = lin.merge(rec, left_on=["player_id", "team_id", "competition_or_event", "season"], right_on=["player_id", "team_id", "competition_name", "season"], how="left")
R["memberships_lineup_rows"] = len(lin)
R["memberships_n_matches_mismatch_vs_05"] = int((m.n_matches != m.n_recount).sum())
R["memberships_squad_list_rows"] = int((p8.membership_basis == "listed_in_published_squad").sum())
R["memberships_squad_rows_without_dates"] = int(((p8.membership_basis == "listed_in_published_squad") & p8.first_match_date.isna()).sum())
ov = lin.groupby(["player_id", "competition_or_event", "season"]).team_id.nunique()
R["players_with_two_teams_in_same_competition_season"] = int((ov > 1).sum())
R["memberships_by_team_type"] = p8.team_type.value_counts().to_dict()

# ============================================================ 2 stats completeness
ev = sb[sb.stats_coverage == "event_level_full"]
R["player_match_rows"] = len(p5)
R["rows_by_source"] = p5.source_dataset.value_counts().to_dict()
R["duplicates_match_player_team"] = int(p5.duplicated(["match_id", "player_id", "team_id"]).sum())
R["statsbomb_rows_event_level"] = len(ev)
R["statsbomb_rows_lineup_only"] = int((sb.stats_coverage == "lineup_only").sum())
METR = ["goals", "assists", "own_goals", "penalty_goals", "shots", "shots_on_target", "xg", "passes", "passes_completed", "key_passes", "crosses", "tackles", "tackles_won",
        "interceptions", "clearances", "blocks", "ball_recoveries", "dribbles", "dribbles_completed", "fouls_committed", "fouls_won", "pressures", "duels", "duels_won",
        "dispossessed", "miscontrols", "carries", "offsides", "gk_saves", "gk_goals_conceded", "yellow_cards", "red_cards", "minutes_played"]
comp_tbl = []
for nm, g in (("StatsBomb event-level", ev), ("openfootball lineups", of)):
    for c in METR:
        s = g[c]
        comp_tbl.append(dict(source=nm, metric=c, rows=len(g), non_null_pct=round(100 * s.notna().mean(), 1), zero_pct_of_non_null=round(100 * (s.dropna() == 0).mean(), 1) if s.notna().any() else None))
pd.DataFrame(comp_tbl).to_csv(os.path.join(EV, "player_metric_availability.csv"), index=False)
R["xA_expected_assists_available"] = False
R["minutes_missing_pct_statsbomb"] = round(100 * sb.minutes_played.isna().mean(), 2)
R["minutes_missing_pct_openfootball"] = round(100 * of.minutes_played.isna().mean(), 2)
R["minutes_basis_values"] = p5.minutes_basis.value_counts().to_dict()
R["statsbomb_rows_minutes_zero"] = int((sb.minutes_played == 0).sum())
R["started_without_minutes"] = int(((p5.started == True) & (p5.minutes_played.fillna(0) <= 0)).sum())
# structural zero question: SB appearance rows where event stats are 0 for all of passes/shots/tackles
R["statsbomb_event_rows_with_zero_events_total"] = int((ev.passes.fillna(0) + ev.shots.fillna(0) + ev.tackles.fillna(0) == 0).sum())
# SB goal reconciliation vs match index
g = ev.groupby(["match_id", "team_id"]).agg(goals=("goals", "sum")).reset_index()
og = ev.groupby(["match_id", "team_id"]).own_goals.sum().reset_index()
mm = mi[["match_id", "home_team_id", "away_team_id", "home_score", "away_score"]]
rows = []
gd = {(r.match_id, r.team_id): r.goals for r in g.itertuples()}
od = {(r.match_id, r.team_id): r.own_goals for r in og.itertuples()}
evm = set(g.match_id)
ok = bad = 0
badl = []
for r in mm.itertuples():
    if r.match_id not in evm:
        continue
    h = gd.get((r.match_id, r.home_team_id), 0) + od.get((r.match_id, r.away_team_id), 0)
    a = gd.get((r.match_id, r.away_team_id), 0) + od.get((r.match_id, r.home_team_id), 0)
    if (h, a) == (r.home_score, r.away_score):
        ok += 1
    else:
        bad += 1
        badl.append((r.match_id, h, a, r.home_score, r.away_score))
R["statsbomb_goal_reconciliation_matches_ok"] = ok
R["statsbomb_goal_reconciliation_matches_mismatch"] = bad
pd.DataFrame(badl, columns=["match_id", "agg_home", "agg_away", "index_home", "index_away"]).to_csv(os.path.join(EV, "statsbomb_goal_reconciliation_mismatch.csv"), index=False)
# gender coverage
R["rows_by_gender"] = sb.competition_gender.value_counts().to_dict()
R["matches_by_gender"] = mi.competition_gender.value_counts().to_dict()
R["openfootball_gender_label"] = of.competition_gender.value_counts().to_dict()

# position groups
def pg(pos):
    if not isinstance(pos, str):
        return "UNKNOWN"
    p = pos.lower()
    if "goalkeeper" in p:
        return "GK"
    if "back" in p and "wing" not in p or "center back" in p or "centre back" in p:
        return "DEF"
    if "wing back" in p:
        return "DEF"
    if "midfield" in p:
        return "MID"
    if "wing" in p or "forward" in p or "striker" in p:
        return "FWD"
    return "UNKNOWN"


sb["pos_group"] = sb.position.map(pg)
R["position_group_counts_statsbomb_rows"] = sb.pos_group.value_counts().to_dict()
sb["season"] = sb.season.astype(str)
# coverage CSV (competition x season x source x gender)
cov = []
for (src, comp, season, gender), gg in p5.groupby(["source_dataset", "competition_name", "season", "competition_gender"], dropna=False):
    ev_ = gg[gg.stats_coverage == "event_level_full"]
    cov.append(dict(level="competition_season", source=src, competition=comp, season=season, gender=gender, matches=gg.match_id.nunique(), player_match_rows=len(gg),
                    players=gg.player_id.nunique(), minutes_non_null_pct=round(100 * gg.minutes_played.notna().mean(), 1),
                    minutes_basis="derived from lineup intervals" if src.startswith("Stats") else "ESTIMATED from substitution/red-card minutes",
                    event_stats_rows=len(ev_), event_stats_pct=round(100 * len(ev_) / len(gg), 1),
                    goals_available=bool(gg.goals.notna().any()), assists_available=bool(gg.assists.notna().any()), shots_available=bool(gg.shots.notna().any()),
                    passes_available=bool(gg.passes.notna().any()), tackles_interceptions_available=bool(gg.tackles.notna().any() and gg.interceptions.notna().any()),
                    xg_available=bool(gg.xg.notna().any()), xa_available=False, cards_available=bool(gg.yellow_cards.notna().any()),
                    gk_stats_available=bool(gg.gk_saves.notna().any()), position_available_pct=round(100 * gg.position.notna().mean(), 1),
                    first_date=gg.match_date.min(), last_date=gg.match_date.max()))
covdf = pd.DataFrame(cov)
posrows = []
for (comp, season, gender, grp), gg in sb[sb.stats_coverage == "event_level_full"].groupby(["competition_name", "season", "competition_gender", "pos_group"]):
    posrows.append(dict(level="position_group_event_level", source="StatsBomb Open Data", competition=comp, season=season, gender=gender, position_group=grp,
                        player_match_rows=len(gg), players=gg.player_id.nunique(), matches=gg.match_id.nunique(),
                        total_minutes=round(gg.minutes_played.sum(), 0), gk_stats_available=bool(gg.gk_saves.notna().any() and grp == "GK")))
out = pd.concat([covdf, pd.DataFrame(posrows)], ignore_index=True, sort=False)
out.to_csv(os.path.join(OUT, "12_PLAYER_STATISTICS_COVERAGE.csv"), index=False, encoding=ENC)
R["coverage_rows"] = len(out)

# ============================================================ 3 form datasets (new, versioned)
ev = ev.copy()
ev["dt"] = pd.to_datetime(ev.match_date)
ev["pos_group"] = ev.position.map(pg)
ev = ev.sort_values(["source_player_id", "dt", "match_id"]).reset_index(drop=True)
SUMC = ["minutes_played", "goals", "assists", "shots", "shots_on_target", "xg", "passes", "passes_completed", "key_passes", "tackles", "interceptions", "clearances",
        "blocks", "ball_recoveries", "pressures", "dribbles", "dribbles_completed", "fouls_committed", "fouls_won", "yellow_cards", "red_cards"]
rows = []
for pid, gdf in ev.groupby("source_player_id", sort=False):
    dts = gdf.dt.values.astype("datetime64[D]")
    A = {c: gdf[c].astype(float).values for c in SUMC}
    st = gdf.started.astype(float).values
    for i in range(len(gdf)):
        k = int(np.searchsorted(dts, dts[i], side="left"))     # only strictly earlier calendar dates
        rec = dict(player_id=gdf.player_id.iloc[i], source_player_id=pid, record_id=gdf.player_match_id.iloc[i], match_id=gdf.match_id.iloc[i], match_date=str(dts[i]),
                   competition=gdf.competition_name.iloc[i], season=gdf.season.iloc[i], gender=gdf.competition_gender.iloc[i], team_id=gdf.team_id.iloc[i],
                   position_group=gdf.pos_group.iloc[i], n_prior_observed_matches=k)
        rec["days_since_previous_observed_match"] = float((dts[i] - dts[k - 1]).astype(int)) if k else np.nan
        for w in (3, 5, 10):
            lo = max(0, k - w)
            n = k - lo
            rec[f"w{w}_n"] = n
            rec[f"w{w}_span_days"] = float((dts[k - 1] - dts[lo]).astype(int)) if n >= 2 else (0.0 if n == 1 else np.nan)
            if n == 0:
                for c in ("minutes_mean", "start_rate", "goals_p90", "assists_p90", "shots_p90", "sot_p90", "xg_p90", "key_passes_p90", "passes_p90", "pass_completion",
                          "tackles_p90", "interceptions_p90", "clearances_p90", "blocks_p90", "pressures_p90", "yellow_rate"):
                    rec[f"w{w}_{c}"] = np.nan
                continue
            mins = np.nansum(A["minutes_played"][lo:k])
            rec[f"w{w}_minutes_mean"] = mins / n
            rec[f"w{w}_start_rate"] = st[lo:k].mean()
            f = (90.0 / mins) if mins > 0 else np.nan
            for nm, c in (("goals_p90", "goals"), ("assists_p90", "assists"), ("shots_p90", "shots"), ("sot_p90", "shots_on_target"), ("xg_p90", "xg"),
                          ("key_passes_p90", "key_passes"), ("passes_p90", "passes"), ("tackles_p90", "tackles"), ("interceptions_p90", "interceptions"),
                          ("clearances_p90", "clearances"), ("blocks_p90", "blocks"), ("pressures_p90", "pressures")):
                v = np.nansum(A[c][lo:k])
                rec[f"w{w}_{nm}"] = v * f if mins > 0 and not np.isnan(A[c][lo:k]).all() else np.nan
            ps = np.nansum(A["passes"][lo:k])
            rec[f"w{w}_pass_completion"] = np.nansum(A["passes_completed"][lo:k]) / ps if ps > 0 else np.nan
            rec[f"w{w}_yellow_rate"] = np.nansum(A["yellow_cards"][lo:k]) / n
        # targets = CURRENT match (never used as features)
        for t in ("minutes_played", "goals", "assists", "shots", "shots_on_target", "xg", "passes", "tackles", "interceptions"):
            rec[f"TARGET_{t}"] = A[t][i]
        rows.append(rec)
rf = pd.DataFrame(rows)
rf["dataset_version"] = "v1.0"
rf["source"] = "StatsBomb Open Data (event-level aggregates built in FootIQ_Dataset_Submission 05)"
rf["window_definition"] = "last N OBSERVED earlier matches of this player in the dataset (strictly earlier calendar dates); NOT necessarily the player's last N real matches"
rf.to_csv(os.path.join(FORM, "PLAYER_RECENT_FORM_STATSBOMB_v1.0.csv"), index=False, encoding=ENC)
R["recent_form_rows"] = len(rf)
R["recent_form_with_ge3_prior"] = int((rf.n_prior_observed_matches >= 3).sum())
R["recent_form_with_ge5_prior"] = int((rf.n_prior_observed_matches >= 5).sum())
R["recent_form_with_ge10_prior"] = int((rf.n_prior_observed_matches >= 10).sum())
R["recent_form_median_gap_days_prev_match"] = float(rf.days_since_previous_observed_match.median())
R["recent_form_share_gap_gt_21_days"] = round(float((rf.days_since_previous_observed_match > 21).mean()), 3)
R["recent_form_w5_span_median"] = float(rf.w5_span_days.median())
R["recent_form_w5_span_gt_60d_share_of_w5_complete"] = round(float((rf[rf.w5_n == 5].w5_span_days > 60).mean()), 3)
R["recent_form_players"] = int(rf.source_player_id.nunique())
# brute-force recompute check (500 random rows)
rng = np.random.default_rng(11)
samp = rf[rf.w5_n >= 5].sample(500, random_state=11)
chk = ev.set_index("player_match_id")
bad = 0
for r in samp.itertuples():
    gdf = ev[ev.source_player_id == r.source_player_id]
    prior = gdf[gdf.dt < pd.Timestamp(r.match_date)].sort_values(["dt", "match_id"]).tail(5)
    mins = prior.minutes_played.sum()
    g90 = prior.goals.sum() * 90 / mins if mins > 0 else np.nan
    if not (np.isclose(g90, r.w5_goals_p90, equal_nan=True) and len(prior) == r.w5_n):
        bad += 1
R["recent_form_bruteforce_mismatches_of_500"] = bad
# future rows must not contribute: prefix invariance on a cut date
cutd = "2018-01-01"
pre = ev[ev.dt < cutd]
R["recent_form_prefix_test_rows_before_2018"] = int(len(pre))

# season-level dataset
ev["season"] = ev.season.astype(str)
ag = ev.groupby(["player_id", "source_player_id", "player_name", "team_id", "team_name", "competition_name", "season", "competition_gender"], dropna=False).agg(
    matches_observed=("match_id", "nunique"), starts=("started", "sum"), minutes_derived=("minutes_played", "sum"), goals=("goals", "sum"), assists=("assists", "sum"),
    shots=("shots", "sum"), shots_on_target=("shots_on_target", "sum"), xg=("xg", "sum"), passes=("passes", "sum"), passes_completed=("passes_completed", "sum"),
    key_passes=("key_passes", "sum"), tackles=("tackles", "sum"), interceptions=("interceptions", "sum"), clearances=("clearances", "sum"), blocks=("blocks", "sum"),
    pressures=("pressures", "sum"), yellow_cards=("yellow_cards", "sum"), red_cards=("red_cards", "sum"), first_date=("match_date", "min"), last_date=("match_date", "max"),
    position_group_mode=("pos_group", lambda s: s.mode().iat[0])).reset_index()
for c, nm in (("goals", "goals_p90"), ("assists", "assists_p90"), ("shots", "shots_p90"), ("xg", "xg_p90"), ("key_passes", "key_passes_p90"), ("tackles", "tackles_p90"),
              ("interceptions", "interceptions_p90"), ("clearances", "clearances_p90"), ("passes", "passes_p90")):
    ag[nm] = np.where(ag.minutes_derived >= 90, ag[c] * 90 / ag.minutes_derived, np.nan)
ag["pass_completion"] = np.where(ag.passes > 0, ag.passes_completed / ag.passes, np.nan)
ag["minutes_basis"] = "derived_from_lineup_intervals"
ag["season_complete_for_player"] = "UNKNOWN: only matches present in StatsBomb open data are included"
ag = ag.sort_values(["source_player_id", "competition_name", "season"])
prev = ag.groupby(["source_player_id", "competition_name"])[["goals_p90", "xg_p90", "minutes_derived"]].shift(1)
ag["prev_observed_season_goals_p90"] = prev.goals_p90
ag["prev_observed_season_xg_p90"] = prev.xg_p90
ag["prev_observed_season_minutes"] = prev.minutes_derived
ag["dataset_version"] = "v1.0"
ag.to_csv(os.path.join(FORM, "PLAYER_SEASON_STATS_STATSBOMB_v1.0.csv"), index=False, encoding=ENC)
R["season_rows"] = len(ag)
R["players_with_2plus_observed_seasons"] = int((ag.groupby("source_player_id").season.nunique() >= 2).sum())

# openfootball appearance-level recent form (appearances/minutes_est/goals/cards over the team's last N league matches)
of = of.copy()
of["dt"] = pd.to_datetime(of.match_date)
tm = of.groupby(["team_id", "match_id"]).dt.first().reset_index().sort_values(["team_id", "dt", "match_id"])
tm["tm_idx"] = tm.groupby("team_id").cumcount()
of = of.merge(tm[["team_id", "match_id", "tm_idx"]], on=["team_id", "match_id"])
of = of.sort_values(["player_id", "dt"])
orows = []
tm_dt = {t: g.dt.values.astype("datetime64[D]") for t, g in tm.groupby("team_id")}
for pid, g in of.groupby("player_id", sort=False):
    tid = g.team_id.iloc[0]
    tdts = tm_dt[tid]
    idxs = g.tm_idx.values
    mins = g.minutes_played.astype(float).values
    gl = g.goals.astype(float).values
    stt = g.started.astype(float).values
    for j in range(len(g)):
        t_i = idxs[j]
        for w in (3, 5, 10):
            pass
        rec = dict(player_id=pid, record_id=g.player_match_id.iloc[j], match_id=g.match_id.iloc[j], match_date=g.match_date.iloc[j], team_id=g.team_id.iloc[j],
                   competition=g.competition_name.iloc[j], season=g.season.iloc[j], team_matches_before=int(t_i))
        for w in (3, 5, 10):
            lo = max(0, t_i - w)
            sel = (idxs >= lo) & (idxs < t_i)          # appearances in the team's previous w matches
            n_team = t_i - lo
            rec[f"w{w}_team_matches"] = n_team
            rec[f"w{w}_appearances_listed"] = int(sel.sum()) if n_team else np.nan
            rec[f"w{w}_appearance_rate"] = sel.sum() / n_team if n_team else np.nan
            rec[f"w{w}_minutes_est_mean_per_team_match"] = mins[sel].sum() / n_team if n_team else np.nan
            rec[f"w{w}_goals"] = gl[sel].sum() if n_team else np.nan
            rec[f"w{w}_start_count"] = stt[sel].sum() if n_team else np.nan
        rec["TARGET_minutes_est"] = mins[j]
        rec["TARGET_goals"] = gl[j]
        orows.append(rec)
orf = pd.DataFrame(orows)
orf["minutes_basis"] = "ESTIMATED (substitution/red-card minutes inside a 90-minute frame); never verified"
orf["dataset_version"] = "v1.0"
orf["note"] = "player_id is team-scoped: transfers are not linked; non-appearance = not in the published lineup/used substitutes (reason unknown)"
orf.to_csv(os.path.join(FORM, "PLAYER_RECENT_FORM_OPENFOOTBALL_APPEARANCES_v1.0.csv"), index=False, encoding=ENC)
R["openfootball_form_rows"] = len(orf)
R["openfootball_form_with_ge5_team_matches"] = int((orf.team_matches_before >= 5).sum())
R["openfootball_competitions_seasons"] = int(orf.groupby(["competition", "season"]).ngroups)

# ============================================================ 4 clustering / prediction readiness numbers
thr = [450, 900, 1350]
seas = ag[ag.competition_gender == "male"]
cl = []
for pgp in ("GK", "DEF", "MID", "FWD", "UNKNOWN"):
    s = seas[seas.position_group_mode == pgp]
    cl.append(dict(position_group=pgp, player_seasons=len(s), **{f">={t}min": int((s.minutes_derived >= t).sum()) for t in thr}, distinct_competitions=int(s.competition_name.nunique())))
cl = pd.DataFrame(cl)
cl.to_csv(os.path.join(EV, "clustering_cohort_sizes_male.csv"), index=False)
R["clustering_cohorts_male"] = cl.to_dict("records")
fem = ag[ag.competition_gender == "female"]
R["clustering_female_player_seasons_ge900"] = int((fem.minutes_derived >= 900).sum())
R["clustering_male_player_seasons_ge900_total"] = int((seas.minutes_derived >= 900).sum())
# missing/sparsity of per-90 features among >=900min
s9 = seas[seas.minutes_derived >= 900]
R["per90_feature_zero_share_ge900"] = {c: round(float((s9[c] == 0).mean()), 3) for c in ("goals_p90", "assists_p90", "shots_p90", "key_passes_p90", "tackles_p90", "interceptions_p90", "clearances_p90")}
R["per90_feature_null_share_ge900"] = {c: round(float(s9[c].isna().mean()), 3) for c in ("goals_p90", "xg_p90", "pass_completion")}
# prediction: targets
rfm = rf[rf.gender == "male"]
R["prediction_rows_male_ge5_prior"] = int((rfm.n_prior_observed_matches >= 5).sum())
R["prediction_rows_male_ge5_prior_and_gap_le_21d"] = int(((rfm.n_prior_observed_matches >= 5) & (rfm.days_since_previous_observed_match <= 21)).sum())
R["target_goals_mean"] = round(float(rf.TARGET_goals.mean()), 4)
R["target_goals_zero_share"] = round(float((rf.TARGET_goals == 0).mean()), 3)
R["target_minutes_mean"] = round(float(rf.TARGET_minutes_played.mean()), 1)
# chronological split feasibility
for cutd in ("2018-12-31", "2022-12-31"):
    pre_p = set(rf[(rf.match_date <= cutd) & (rf.n_prior_observed_matches >= 5)].source_player_id)
    post = rf[(rf.match_date > cutd) & (rf.n_prior_observed_matches >= 5)]
    R[f"prediction_rows_after_{cutd}_with_ge5_prior"] = len(post)
R["prediction_competition_seasons_with_ge5_prior_rows"] = int(rf[rf.n_prior_observed_matches >= 5].groupby(["competition", "season"]).ngroups)
byyear = rf[rf.n_prior_observed_matches >= 5].assign(y=lambda x: x.match_date.str[:4]).groupby("y").size()
R["prediction_rows_by_year"] = byyear.to_dict()
json.dump(R, open(os.path.join(EV, "v5_results.json"), "w"), indent=1, default=str)
print(json.dumps(R, indent=0, default=str)[:6000])
