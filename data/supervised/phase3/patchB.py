import json

p = "config/season_sim.json"
c = json.load(open(p, encoding="utf-8"))
c["points_only"] = {"enabled": True, "label": "Experimental — Points-only simulation", "approved": "2026-10-25 (option O5)", "scope": ["BUNDESLIGA", "LALIGA"]}
c["scoreline_validation"]["summary"] = ("No candidate (S1 conditional Poisson, S2 outcome-matched Poisson, S3 empirical bootstrap) met the predeclared criteria in every league. "
                                         "Not approved for unrestricted final-position prediction (your decision of 2026-10-25). See docs/mini-project/PHASE3_SCORELINE_BENCHMARK.md.")
with open(p, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(c, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

p = "app/seasonsim/eligibility.py"
s = open(p, encoding="utf-8").read()
old = "    return dict(out, state=state, reasons=reasons, notes=notes, blockers=blockers, can_simulate=not blockers,"
new = '''    po_cfg = cfg.get("points_only", {})
    po_blockers = []
    if not po_cfg.get("enabled"):
        po_blockers.append("points-only mode is switched off")
    if state == "not_eligible":
        po_blockers.append("data quality: Not eligible")
    if key not in po_cfg.get("scope", []):
        po_blockers.append("outside the approved scope of the points-only mode (Bundesliga and La Liga)")
    points_only = dict(label=po_cfg.get("label", "Experimental \\u2014 Points-only simulation"), can_run=not po_blockers, blockers=po_blockers,
                       note="Simulates win / draw / loss only (3 / 1 / 0 points). No tie-breaks, no scores and no finishing positions are involved.")
    return dict(out, points_only=points_only, state=state, reasons=reasons, notes=notes, blockers=blockers, can_simulate=not blockers,'''
assert old in s
open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new))

p = "app/seasonsim/service.py"
s = open(p, encoding="utf-8").read()
s = s.replace('    "A final decider (play-off, neutral-ground match, lots, fair play without card data) is simulated as a fair coin; how often it mattered is reported.",',
              '    "A final decider (play-off, neutral-ground match, lots, fair play without card data) is never simulated: such outcomes stay unresolved and the affected probabilities are withheld.",')
s = s.replace("from . import eligibility, engine, rules, scoreline, settings", "from . import eligibility, engine, pointsonly, rules, scoreline, settings")
s = s.replace('EXPLICIT_ACTION = "simulate_season_button"', 'EXPLICIT_ACTION = "simulate_season_button"\nPOINTS_ACTION = "simulate_points_button"\nPOINTS_LABEL = "Experimental \\u2014 Points-only simulation"')
a = s.index("def list_runs")
b = s.index("def get_run")
new_list = '''def list_runs(key: str, season: str, db_path=None) -> list[dict]:
    conn = store_db.connect(db_path, readonly=True)
    try:
        out = []
        for r in conn.execute("SELECT simulation_run_id AS run_id, created_utc, n_simulations, seed, model_id, data_cutoff_date, assumptions_json FROM simulation_runs WHERE competition_key=? AND season=? ORDER BY simulation_run_id DESC", (key, season)):
            d = dict(r)
            d["mode"] = json.loads(d.pop("assumptions_json")).get("mode", "final_positions")
            out.append(d)
        return out
    finally:
        conn.close()


'''
s = s[:a] + new_list + s[b:]
s = s.replace('        st["limitations"] = LIMITATIONS\n', '        st["limitations"] = LIMITATIONS\n        st["points_only"]["limitations"] = POINTS_LIMITATIONS\n')
s += '''

POINTS_LIMITATIONS = LIMITATIONS[:1] + [
    "Only win, draw and loss are simulated (3 / 1 / 0 points). No score is generated and no tie-break is applied, so this mode says nothing about who finishes where.",
    "The clubs are listed by expected final points only. Equal or close points do not imply a league position.",
    "Fixtures whose date has passed but have no verified result are simulated like future fixtures.",
    "Backtest evidence (2024-25 and 2025-26, three cut-offs per season): the 10-90% intervals contained the real final points about 75% of the time instead of 80%, so they are somewhat too narrow.",
    "These are estimates from a modest model, not predictions of what will happen, and not betting advice.",
]


def run_points_only(key: str, season: str, n: Optional[int], seed: Optional[int], user_action: str, now: Optional[datetime] = None, today: Optional[date] = None, db_path=None) -> dict:
    """Experimental points-only simulation. Needs no scoreline method and no tie-break rules; saved only on the explicit user action."""
    if user_action != POINTS_ACTION:
        raise SimError("a points-only simulation runs only when the user explicitly presses Run points-only simulation")
    cfg = settings.load()
    n = int(n or cfg["default_simulations"])
    if not cfg["min_simulations"] <= n <= cfg["max_simulations"]:
        raise SimError(f"the number of simulations must be between {cfg['min_simulations']} and {cfg['max_simulations']}")
    now = now or datetime.now(timezone.utc)
    seed = int(seed) if seed is not None else secrets.randbits(31)
    conn = store_db.connect(db_path)
    try:
        st = eligibility.assess(conn, key, season, today)
        if not st["points_only"]["can_run"]:
            raise SimError("points-only simulation blocked: " + "; ".join(st["points_only"]["blockers"]))
        rows = _season_rows(conn, key, season)
        played = [r for r in rows if r["status"] in eligibility.COMPLETED and r["hg"] is not None]
        pid = {r["record_id"] for r in played}
        rem = [r for r in rows if r["record_id"] not in pid]
        probs, latest_model = live_probabilities(conn, key, season, rem)
        teams = sorted({r["h"] for r in rows} | {r["a"] for r in rows})
        idx = {t: i for i, t in enumerate(teams)}
        names = _names(conn, teams)
        base = np.zeros(len(teams), dtype=np.int64)
        for r in played:
            base[idx[r["h"]]] += 3 if r["hg"] > r["ag"] else 1 if r["hg"] == r["ag"] else 0
            base[idx[r["a"]]] += 3 if r["ag"] > r["hg"] else 1 if r["hg"] == r["ag"] else 0
        fh = np.array([idx[r["h"]] for r in rem], dtype=int)
        fa = np.array([idx[r["a"]] for r in rem], dtype=int)
        pr = probs.set_index("record_id").loc[[r["record_id"] for r in rem]][["p1_H", "p1_D", "p1_A"]].values
        points = pointsonly.simulate_points(base, fh, fa, pr, n, seed)
        remaining = np.bincount(np.concatenate([fh, fa]), minlength=len(teams)) if len(rem) else np.zeros(len(teams), dtype=int)
        summary = pointsonly.summarize_points(points, teams, [names.get(t, t) for t in teams], base, remaining, seed)
        import forecast

        ids, hashes = forecast.model_ids(), forecast.artifact_hashes()
        input_hash = hashlib.sha256(json.dumps([[r["record_id"], r["status"], r["hg"], r["ag"]] for r in rows] + probs[["p1_H", "p1_D", "p1_A"]].round(10).values.tolist(), default=str).encode()).hexdigest()
        assumptions = dict(
            mode="points_only", label=POINTS_LABEL, created_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), note=NOTE, user_action=user_action, simulations=n, seed=seed,
            models=dict(primary=ids["club_v1"]), artifact_sha256={"club_v1": hashes["club_v1"]}, probability_state="frozen club v1 features at the data cut-off, static during the simulation",
            points_rule="home win 3 points, draw 1 point each, away win 3 points; no scores, no tie-breaks, no positions",
            data_cutoff=dict(latest_result_in_competition=st["latest_result"], latest_result_in_model_history=str(latest_model.date())), freshness=_freshness(conn, key, season, rows),
            eligibility=dict(state=st["state"], reasons=st["reasons"], notes=st["notes"], counts=st["counts"], thresholds=st["thresholds"]), remaining_fixtures=len(rem), input_sha256=input_hash,
            limitations=POINTS_LIMITATIONS, standard_error_max=summary["standard_error_of_a_probability_max"])
        result_json = dict(mode="points_only", summary=summary)
        with conn:
            run_id = conn.execute("INSERT INTO simulation_runs(created_utc, competition_key, season, n_simulations, seed, model_id, data_cutoff_date, assumptions_json, result_json) VALUES (?,?,?,?,?,?,?,?,?)",
                                  (assumptions["created_utc"], key, season, n, seed, ids["club_v1"], st["latest_result"], json.dumps(assumptions), json.dumps(result_json))).lastrowid
        return dict(run_id=run_id, competition_key=key, season=season, assumptions=assumptions, result=result_json)
    finally:
        conn.close()
'''
open(p, "w", encoding="utf-8", newline="\n").write(s)

p = "app/main.py"
m = open(p, encoding="utf-8").read()
old = '@app.get("/api/season/runs")'
new = '''@app.post("/api/season/points")
def season_points(req: SeasonSimRequest):
    """Run and SAVE an Experimental points-only simulation (3/1/0 points, no tie-breaks, no positions). Only valid as the result of the user pressing Run points-only simulation."""
    _comp(req.key)
    if not store_db.exists():
        raise HTTPException(503, "the results store is not built yet (run: python app/store/build.py)")
    try:
        return season_sim.run_points_only(req.key, req.season, req.simulations, req.seed, req.user_action)
    except (season_sim.SimError, gameweeks.GameweekError) as exc:
        raise HTTPException(422, str(exc)) from exc


'''
assert old in m
open(p, "w", encoding="utf-8", newline="\n").write(m.replace(old, new + old, 1))
print("ok")
