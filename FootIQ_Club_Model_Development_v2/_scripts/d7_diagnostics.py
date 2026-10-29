"""Phase 1 structural diagnostics (development data only): Elo connectivity, identity flags, cup/continental coverage vs rest-day features, league home advantage."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_models import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
V = pd.read_pickle(os.path.join(PREP, "_build", "work", "V_universe.pkl"))
V = V[V.match_date <= DEV_END]
F = load_dev()
F = F[F.match_date <= DEV_END]
out = {}

# 1. connectivity of the team graph (edges = any recorded match, any competition type)
par = {}


def find(x):
    while par.setdefault(x, x) != x:
        par[x] = par[par[x]]; x = par[x]
    return x


for h, a in zip(V.home_entity_id, V.away_entity_id):
    par[find(h)] = find(a)
roots = pd.Series({t: find(t) for t in par})
comp_sizes = roots.value_counts()
out["entities"] = int(len(roots)); out["connected_components"] = int(len(comp_sizes))
out["largest_component_entities"] = int(comp_sizes.iloc[0]); out["largest_component_share"] = float(comp_sizes.iloc[0] / len(roots))
# league-only graph (rated league matches only): which competitions are isolated Elo islands
lg = V[V.rated]
par.clear()
for h, a in zip(lg.home_entity_id, lg.away_entity_id):
    par[find(h)] = find(a)
r2 = pd.Series({t: find(t) for t in par})
cs2 = r2.value_counts()
out["rated_graph_components"] = int(len(cs2)); out["rated_graph_largest_share"] = float(cs2.iloc[0] / len(r2))
comp_root = lg.assign(root=lg.home_entity_id.map(r2)).groupby("competition_id").root.nunique()
out["competitions_total"] = int(lg.competition_id.nunique())
out["competitions_in_own_island_(share of rated matches that are in a component of its own competition only)"] = None
# share of rated matches whose component never meets a team from another competition
ent_comps = pd.concat([lg[["home_entity_id", "competition_id"]].rename(columns={"home_entity_id": "e"}), lg[["away_entity_id", "competition_id"]].rename(columns={"away_entity_id": "e"})]).drop_duplicates()
ent_comps["root"] = ent_comps.e.map(r2)
ncomp_per_root = ent_comps.groupby("root").competition_id.nunique()
single = set(ncomp_per_root[ncomp_per_root == 1].index)
lg2 = lg.assign(root=lg.home_entity_id.map(r2))
out["share_rated_matches_in_single_competition_islands"] = float(lg2.root.isin(single).mean())
out["n_single_competition_islands"] = int(len(single))
comp_island = ent_comps[ent_comps.root.isin(single)].groupby("root").competition_id.first().value_counts()
out["multi_competition_components"] = int((ncomp_per_root > 1).sum())

# 2. identity flags in the development window
Fd = F[F.dev_primary | F.dev_secondary]
out["dev_rows"] = int(len(F))
out["dev_primary_rows"] = int(F.dev_primary.sum())
out["dev_secondary_rows_calendar_year"] = int(F.dev_secondary.sum())

# 3. cup / continental coverage vs rest features
types = V.competition_type.value_counts().to_dict()
out["universe_competition_type_counts"] = {str(k): int(v) for k, v in types.items()}
out["share_dev_rows_with_any_cup_recorded_365d_home"] = float((F.home_cup_recorded_365 > 0).mean())
out["share_dev_rows_with_any_cup_recorded_365d_away"] = float((F.away_cup_recorded_365 > 0).mean())
cov = F.groupby("competition_id").agg(n=("y", "size"), cup_cov=("home_cup_recorded_365", lambda s: float((s > 0).mean())), median_rest=("home_days_rest", "median"),
                                       p90_rest=("home_days_rest", lambda s: float(s.quantile(0.9)))).reset_index()
cov.to_csv(os.path.join(WORK, "cup_coverage_by_competition.csv"), index=False)
out["competitions_with_zero_cup_coverage"] = int((cov.cup_cov == 0).sum()); out["competitions_total_dev"] = int(len(cov))
out["share_dev_rows_in_zero_cup_coverage_competitions"] = float(cov[cov.cup_cov == 0].n.sum() / cov.n.sum())
out["share_rest_gt_14_days"] = float((F.home_days_rest > 14).mean())

# 4. league-specific home advantage and draw rates
ha = F[F.dev_primary].groupby("competition_id").apply(lambda g: pd.Series(dict(n=len(g), home_win=(g.y == 0).mean(), draw=(g.y == 1).mean(), away_win=(g.y == 2).mean())), include_groups=False)
ha = ha[ha.n >= 600].sort_values("home_win")
ha.to_csv(os.path.join(WORK, "league_home_advantage.csv"))
out["home_win_rate_range_competitions_n>=600"] = [float(ha.home_win.min()), float(ha.home_win.max())]
out["draw_rate_range_competitions_n>=600"] = [float(ha.draw.min()), float(ha.draw.max())]
out["n_competitions_n>=600"] = int(len(ha))

# 5. new-to-competition / cold-start shares
out["share_rows_a_side_under_10_prior"] = float((F[["home_n_prior", "away_n_prior"]].min(axis=1) < 10).mean())
json.dump(out, open(os.path.join(WORK, "structural_diagnostics.json"), "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
print(ha.head(5).to_string()); print(ha.tail(5).to_string())
