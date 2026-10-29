"""Build data/miniproject/matches.csv (+ data_audit.csv, season_coverage.csv) for the 11 mini-project competitions.

Reads only the CSVs already in the repository. Nothing is downloaded, imputed or fabricated: rows without a score are dropped
and reported in the audit. Refreshing = replace the source CSVs, then re-run this script.

    .venv\\Scripts\\python.exe -X utf8 app/prepare_data.py
"""
import sys

import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import config as C  # noqa: E402

ENC = "utf-8-sig"
LF = chr(10)   # always write LF (pandas would write CRLF on Windows and make Git report the generated files as modified)
COLUMNS = ["competition_key", "competition", "group", "season", "stage", "date", "home", "away", "home_entity_id", "away_entity_id",
           "home_goals", "away_goals", "home_source_name", "away_source_name", "score_basis", "outcome", "outcome_basis", "shootout_winner", "neutral", "source", "licence"]


def club_rows():
    raw = pd.read_csv(C.CLUB_SOURCE, encoding=ENC, low_memory=False)
    # the same club is spelled differently across seasons in the source ("Arsenal" vs "Arsenal FC"); the entity id is stable,
    # so show every club under the spelling from its most recent match. The original spelling is kept in home_source_name/away_source_name.
    ids = pd.concat([raw[["match_date", "home_entity_id", "home_team_name"]].set_axis(["d", "e", "n"], axis=1),
                     raw[["match_date", "away_entity_id", "away_team_name"]].set_axis(["d", "e", "n"], axis=1)]).dropna()
    canon = ids.sort_values("d").drop_duplicates("e", keep="last").set_index("e").n
    out = []
    for comp in (c for c in C.ALL_COMPETITIONS if c["kind"] == "club"):
        d = raw[raw.competition_id == comp["source_id"]]
        scored = d.final_score_home_excl_penalties.notna() & d.final_score_away_excl_penalties.notna() & d.match_status.isin(["completed", "awarded"])
        d = d[scored]
        out.append(pd.DataFrame({
            "competition_key": comp["key"], "competition": comp["name"], "group": comp["group"], "season": d.season.astype(str),
            "stage": d.stage, "date": d.match_date, "home": d.home_entity_id.map(canon).fillna(d.home_team_name), "away": d.away_entity_id.map(canon).fillna(d.away_team_name),
            "home_source_name": d.home_team_name, "away_source_name": d.away_team_name,
            "home_entity_id": d.home_entity_id, "away_entity_id": d.away_entity_id,
            "home_goals": d.final_score_home_excl_penalties.astype(int), "away_goals": d.final_score_away_excl_penalties.astype(int),
            "score_basis": "final score excluding penalties", "outcome": d.outcome_90min_1x2,
            "outcome_basis": "90 min (" + d.label_90_status.astype(str) + ")", "shootout_winner": "", "neutral": "",
            "source": d.source_system, "licence": d.source_license}))
    return pd.concat(out, ignore_index=True)


def intl_edition(tournament, date):
    d = pd.Timestamp(date)
    if tournament == "UEFA Nations League":
        y = d.year if d.month >= 8 else d.year - 1
        return f"{y}-{str(y + 1)[2:]}"
    return str(d.year)


def intl_rows():
    r = pd.read_csv(C.INTL_RESULTS)
    so = pd.read_csv(C.INTL_SHOOTOUTS)[["date", "home_team", "away_team", "winner"]]
    out = []
    for comp in (c for c in C.ALL_COMPETITIONS if c["kind"] == "intl"):
        d = r[r.tournament == comp["source_id"]].copy()
        d = d[d.home_score.notna() & d.away_score.notna()]
        d = d.merge(so, on=["date", "home_team", "away_team"], how="left")
        hg, ag = d.home_score.astype(int), d.away_score.astype(int)
        outcome = pd.Series("D", index=d.index).mask(hg > ag, "H").mask(hg < ag, "A")
        out.append(pd.DataFrame({
            "competition_key": comp["key"], "competition": comp["name"], "group": comp["group"],
            "season": [intl_edition(comp["source_id"], x) for x in d.date], "stage": "", "date": d.date,
            "home": d.home_team, "away": d.away_team, "home_entity_id": "", "away_entity_id": "", "home_goals": hg, "away_goals": ag,
            "score_basis": "recorded score (may include extra time)", "outcome": outcome,
            "outcome_basis": "recorded score; 90-min result not separable", "shootout_winner": d.winner.fillna(""),
            "neutral": d.neutral.astype(str), "source": "martj42/international_results", "licence": "CC0-1.0"}))
    out.append(worldcup_2026())
    return pd.concat(out, ignore_index=True)


def worldcup_2026():
    """2026 World Cup results are blank in results.csv; take them from the repo's own verified result files (group stage + knockouts).
    Source URLs are kept per row. The licence of these compiled factual results is not asserted."""
    g = pd.read_csv(C.WC2026_GROUP, encoding=ENC)
    g = g[(g.is_final.astype(str).str.lower() == "true") & (g.needs_90min_review.astype(str).str.lower() != "true")].copy()
    sc = g.provider_score.str.extract(r"^\s*(\d+)\s*-\s*(\d+)\s*$").astype(float)
    g = g[sc[0].notna()]
    sc = sc[sc[0].notna()].astype(int)
    rows = pd.DataFrame({"date": g.date, "home": g.team1, "away": g.team2, "hg": sc[0], "ag": sc[1], "stage": "Group stage", "so": "",
                         "src": "worldcup 2026 matchday validation (provider final score)"})
    k = pd.read_csv(C.WC2026_KO)
    sc = k.score_after_extra_time.str.extract(r"^\s*(\d+)\s*-\s*(\d+)\s*$").astype(float)
    k, sc = k[sc[0].notna()], sc[sc[0].notna()].astype(int)
    ko = pd.DataFrame({"date": k.date, "home": k.team1, "away": k.team2, "hg": sc[0], "ag": sc[1], "stage": "Knockout",
                       "so": k.winner.where(k.shootout_score.notna(), ""), "src": k.verification_source})
    d = pd.concat([rows, ko], ignore_index=True)
    # the 2026 files spell some teams differently from each other and from the historical results ("USA" / "United States")
    import names

    canon = names.canon_intl
    d["home"], d["away"], d["so"] = d.home.map(canon), d.away.map(canon), d.so.map(lambda n: canon(n) if n else n)
    outcome = pd.Series("D", index=d.index).mask(d.hg > d.ag, "H").mask(d.hg < d.ag, "A")
    return pd.DataFrame({
        "competition_key": "WC", "competition": "FIFA World Cup", "group": "International", "season": "2026", "stage": d.stage, "date": d.date,
        "home": d.home, "away": d.away, "home_entity_id": "", "away_entity_id": "", "home_goals": d.hg, "away_goals": d.ag,
        "score_basis": "recorded score (knockouts: after extra time)", "outcome": outcome, "outcome_basis": "recorded score; 90-min result not separable for knockouts",
        "shootout_winner": d.so, "neutral": "", "source": d.src, "licence": "factual results compiled from the cited source; licence not asserted"})


def main():
    C.MINI_DIR.mkdir(parents=True, exist_ok=True)
    m = pd.concat([club_rows(), intl_rows()], ignore_index=True)[COLUMNS]
    m = m.sort_values(["competition_key", "date", "home"], kind="mergesort").reset_index(drop=True)
    dup = m.duplicated(["competition_key", "date", "home", "away", "stage"], keep=False)
    m.to_csv(C.MATCHES_CSV, index=False, encoding=ENC, lineterminator=LF)

    cov = pd.read_csv(C.CLUB_COVERAGE_MATRIX, encoding=ENC)
    audit = []
    for comp in C.ALL_COMPETITIONS:
        d = m[m.competition_key == comp["key"]]
        audit.append(dict(
            competition_key=comp["key"], competition=comp["name"], group=comp["group"], rows=len(d), seasons=d.season.nunique(),
            first_date=d.date.min(), last_date=d.date.max(), rows_with_outcome=int((d.outcome.fillna("") != "").sum()),
            duplicate_rows=int(dup[d.index].sum()), sources=" | ".join(sorted(d.source.unique())), licences=" | ".join(sorted(d.licence.unique())),
            validation_badge=comp["badge"]))
    pd.DataFrame(audit).to_csv(C.AUDIT_CSV, index=False, encoding=ENC, lineterminator=LF)

    sc = m.groupby(["competition_key", "season"]).size().rename("rows_in_dataset").reset_index()
    exp = cov[["competition_id", "season", "expected_matches", "coverage_pct"]].rename(columns={"expected_matches": "expected_matches"})
    id_to_key = {c["source_id"]: c["key"] for c in C.ALL_COMPETITIONS if c["kind"] == "club"}
    exp["competition_key"] = exp.competition_id.map(id_to_key)
    exp = exp.dropna(subset=["competition_key"]).drop(columns="competition_id")
    exp["season"] = exp.season.astype(str)
    sc = sc.merge(exp, on=["competition_key", "season"], how="left")
    sc["note"] = ""
    sc.loc[sc.expected_matches.notna() & (sc.rows_in_dataset < sc.expected_matches), "note"] = "incomplete or in progress"
    sc.loc[sc.expected_matches.isna(), "note"] = "no expected-count reference available"
    sc.to_csv(C.SEASON_COVERAGE_CSV, index=False, encoding=ENC, lineterminator=LF)

    print(pd.DataFrame(audit).drop(columns=["sources", "licences"]).to_string(index=False))
    print(f"\nwrote {C.MATCHES_CSV} ({len(m)} rows), {C.AUDIT_CSV}, {C.SEASON_COVERAGE_CSV}")


if __name__ == "__main__":
    main()
