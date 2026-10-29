"""Cross-source reconciliation against the frozen openfootball universe (read-only). Conflicts are reported, never resolved."""
import pandas as pd

from .identity import IdentityResolver


def build_resolver(V: pd.DataFrame, alias_rows=()) -> IdentityResolver:
    pairs = list(zip(V.competition_id, V.home_team_name, V.home_entity_id)) + list(zip(V.competition_id, V.away_team_name, V.away_entity_id))
    return IdentityResolver(set(pairs), alias_rows)


def reconcile_source(records, source: str, competition_id: str, season_label: str, V: pd.DataFrame, missing_openfootball: pd.DataFrame, resolver: IdentityResolver, run_date: str):
    """records: StagingRecord list for ONE competition-season. V: frozen universe. missing_openfootball: openfootball fixtures dated <= run_date without result (columns home_entity_id, away_entity_id, match_date).
    Returns dict of DataFrames: overlap, conflicts, recovered, new_not_in_openfootball, unresolved_identities, missing_kickoff, summary."""
    of = V[(V.competition_id == competition_id) & (V.season_corrected == season_label)][["match_date", "home_entity_id", "away_entity_id", "gh", "ga"]].copy()
    of["of_key"] = of.home_entity_id + "|" + of.away_entity_id
    of_by_pair = {}
    for r in of.itertuples():
        of_by_pair.setdefault(r.of_key, []).append(r)
    miss = {}
    for r in missing_openfootball.itertuples():
        miss.setdefault(r.home_entity_id + "|" + r.away_entity_id, []).append(r)
    rows, unres, nokick = [], [], []
    for r in records:
        he, hm = resolver.resolve(source, competition_id, r.home_raw)
        ae, am = resolver.resolve(source, competition_id, r.away_raw)
        if not he or not ae:
            unres.append(dict(source_ref=r.source_ref, home=r.home_raw, away=r.away_raw, home_method=hm, away_method=am, status=r.status))
            continue
        if r.kickoff_utc is None and r.status in ("completed", "upcoming", "past_date_no_result"):
            nokick.append(dict(source_ref=r.source_ref, home=r.home_raw, away=r.away_raw, status=r.status, date_provenance=r.date_provenance))
        key = he + "|" + ae
        cand = of_by_pair.get(key, [])
        base = dict(source_ref=r.source_ref, home=r.home_raw, away=r.away_raw, status=r.status, src_date=r.match_date, src_h=r.regulation_home, src_a=r.regulation_away, result_type=r.result_type)
        if r.status != "completed":
            continue
        if r.match_date and cand:
            cand2 = [c for c in cand if c.match_date == r.match_date] or cand
        else:
            cand2 = cand
        if len(cand2) == 1:
            c = cand2[0]
            same = (int(c.gh), int(c.ga)) == (r.regulation_home, r.regulation_away)
            rows.append(dict(base, outcome="agree" if same else "CONFLICT", of_date=c.match_date, of_h=int(c.gh), of_a=int(c.ga), date_equal=(r.match_date == c.match_date) if r.match_date else None))
        elif len(cand2) > 1:
            rows.append(dict(base, outcome="ambiguous_multiple_openfootball_matches"))
        else:
            m = miss.get(key, [])
            rows.append(dict(base, outcome="recovered_missing_in_openfootball" if m else "not_in_openfootball_at_all", of_date=(m[0].match_date if m else None)))
    df = pd.DataFrame(rows)
    out = dict(all=df, unresolved_identities=pd.DataFrame(unres), missing_kickoff=pd.DataFrame(nokick))
    if len(df):
        out["conflicts"] = df[df.outcome == "CONFLICT"]
        out["recovered"] = df[df.outcome == "recovered_missing_in_openfootball"]
        out["not_in_openfootball"] = df[df.outcome.isin(["not_in_openfootball_at_all", "ambiguous_multiple_openfootball_matches"])]
    n = len(df)
    vc = df.outcome.value_counts().to_dict() if n else {}
    comp = [r for r in records if r.status == "completed"]
    out["summary"] = dict(source=source, competition_id=competition_id, season=season_label, source_records=len(records), source_completed=len(comp), openfootball_rows=len(of),
                          overlapping_checked=int(vc.get("agree", 0) + vc.get("CONFLICT", 0)), exact_score_agreements=int(vc.get("agree", 0)), conflicts=int(vc.get("CONFLICT", 0)),
                          date_agreements=int(df.get("date_equal", pd.Series(dtype=bool)).eq(True).sum()) if n else 0, date_disagreements=int(df.get("date_equal", pd.Series(dtype=bool)).eq(False).sum()) if n else 0,
                          newly_recovered=int(vc.get("recovered_missing_in_openfootball", 0)), not_in_openfootball=int(vc.get("not_in_openfootball_at_all", 0)),
                          ambiguous=int(vc.get("ambiguous_multiple_openfootball_matches", 0)), unresolved_team_identities=len(unres), records_without_kickoff_time=len(nokick),
                          latest_completed_date=max([r.match_date for r in comp if r.match_date], default=None), run_date=run_date)
    return out
