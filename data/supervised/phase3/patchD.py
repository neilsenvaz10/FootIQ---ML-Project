p = "frontend/src/pages/SeasonSimulator.jsx"
s = open(p, encoding="utf-8").read()

# ---- probabilities that may be withheld (unresolved ties): show the bounds instead
s = s.replace('const p1 = (v) => (v == null ? "–" : `${(v * 100).toFixed(1)}%`);',
              'const p1 = (v) => (v == null ? "–" : `${(v * 100).toFixed(1)}%`);\nconst pb = (t, k) => (t[k] != null ? p1(t[k]) : t[`${k}_low`] != null ? `${(t[`${k}_low`] * 100).toFixed(1)}–${(t[`${k}_high`] * 100).toFixed(1)}%` : "–"); // a withheld probability shows its bounds\n'
              'export const POINTS_ACTION = "simulate_points_button";\nexport const POINTS_LABEL = "Experimental \\u2014 Points-only simulation";')
for k in ("p_title", "p_top4", "p_relegation"):
    s = s.replace("p1(t.%s)" % k, "pb(t, \"%s\")" % k)
s = s.replace("{hasPlay ? p1(t.p_relegation_playoff) : t.expected_rank.toFixed(1)}", "{hasPlay ? pb(t, \"p_relegation_playoff\") : t.expected_rank == null ? \"–\" : t.expected_rank.toFixed(1)}")
s = s.replace('<Stat label="Expected rank" value={t.expected_rank.toFixed(1)}', '<Stat label="Expected rank" value={t.expected_rank == null ? "unresolved" : t.expected_rank.toFixed(1)}')

# ---- assumptions panel: tolerate points-only runs
s = s.replace('''            <Row k="Experimental comparison" v={`${a.models.experimental_comparison} (development-validated only)`} />
            <Row k="Scoreline method" v={`${sc.method}; validation: ${sc.validation?.status}`} />''',
              '''            {a.models.experimental_comparison && <Row k="Experimental comparison" v={`${a.models.experimental_comparison} (development-validated only)`} />}
            {sc && <Row k="Scoreline method" v={`${sc.method}; validation: ${sc.validation?.status}`} />}
            {a.points_rule && <Row k="Points rule" v={a.points_rule} />}''')
s = s.replace('''            For every match still to be played the frozen model gives home-win, draw and away-win chances; a result and a score are drawn from them, the table is rebuilt and ranked with the league's official tie-break rules, and this is repeated thousands of times. The counts become probabilities.''',
              '''            {a?.mode === "points_only"
              ? "For every match still to be played the frozen model gives home-win, draw and away-win chances; a result is drawn from them, 3, 1 or 0 points are added to each club, and this is repeated thousands of times. The spread of each club's final points is shown. No scores, tie-breaks or table positions are involved."
              : "For every match still to be played the frozen model gives home-win, draw and away-win chances; a result and a score are drawn from them, the table is rebuilt and ranked with the league's official tie-break rules, and this is repeated thousands of times. The counts become probabilities."}''')
s = s.replace("(a?.limitations ?? st?.limitations ?? [])", "(a?.limitations ?? (mode === \"points\" ? st?.points_only?.limitations : st?.limitations) ?? [])")
s = s.replace("function Assumptions({ a, st }) {", "function Assumptions({ a, st, mode }) {")
s = s.replace("<Assumptions a={r.assumptions} st={s} />", "<Assumptions a={r.assumptions} st={s} mode={mode} />").replace("<Assumptions a={null} st={s} />", "<Assumptions a={null} st={s} mode={mode} />")

# ---- new points-only components and the main component
a = s.index("export default function SeasonSimulator() {")
b = s.index("function SectionExperimental")
new_main = r'''function PointsBars({ team }) {
  const d = team.distribution;
  const max = Math.max(...d.probabilities, 0.0001);
  const step = Math.max(1, Math.ceil(d.probabilities.length / 12));
  return (
    <div role="img" aria-label={`Distribution of final points for ${team.name}`} className="flex h-20 items-end gap-px">
      {d.probabilities.map((p, i) => (
        <div key={i} title={`${d.first_points + i} points: ${p1(p)}`} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end">
          <div className={`w-full rounded-t ${d.first_points + i >= team.points_p10 && d.first_points + i <= team.points_p90 ? "bg-pitch" : "bg-pitch/35"}`} style={{ height: `${Math.max((p / max) * 100, p > 0 ? 3 : 0)}%` }} />
          <span className="mt-0.5 h-3 text-[9px] text-mute">{i % step === 0 ? d.first_points + i : ""}</span>
        </div>
      ))}
    </div>
  );
}

function PointsResult({ summary }) {
  const [open, setOpen] = useState(null);
  return (
    <div className="space-y-2">
      <p className="px-1 text-xs text-mute">Clubs are listed by expected final points only. This is not a predicted table: no tie-breaks are applied and no finishing position is implied.</p>
      <div className="overflow-hidden rounded-2xl border border-white/5 bg-panel">
        <div className="grid grid-cols-[1fr_auto] items-center gap-x-2 border-b border-line/60 px-3 py-2 text-[11px] font-semibold text-mute sm:grid-cols-[1fr_4rem_4rem_9rem_5rem]">
          <span>Club</span>
          <span className="hidden text-right sm:block">Now</span>
          <span className="hidden text-right sm:block">Left</span>
          <span className="hidden sm:block">Expected final points (10–90%)</span>
          <span className="text-right">Exp. pts</span>
        </div>
        {summary.teams.map((t) => (
          <div key={t.entity_id} className="border-b border-line/40 last:border-b-0">
            <button onClick={() => setOpen(open === t.entity_id ? null : t.entity_id)} aria-expanded={open === t.entity_id} className="grid w-full grid-cols-[1fr_auto] items-center gap-x-2 px-3 py-2 text-left text-sm sm:grid-cols-[1fr_4rem_4rem_9rem_5rem]">
              <span className="flex min-w-0 items-center gap-2">
                <TeamAvatar name={t.name} size={24} />
                <span className="truncate font-semibold">{t.name}</span>
              </span>
              <span className="hidden text-right tabular-nums sm:block">{t.current_points}</span>
              <span className="hidden text-right tabular-nums sm:block">{t.remaining_fixtures}</span>
              <span className="hidden tabular-nums sm:block">
                {Math.round(t.points_p10)}–{Math.round(t.points_p90)}
              </span>
              <span className="text-right font-extrabold tabular-nums">{t.expected_points.toFixed(1)}</span>
            </button>
            {open === t.entity_id && (
              <div className="space-y-2 px-3 pb-3">
                <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                  <Stat label="Points now" value={t.current_points} hint={`${t.remaining_fixtures} matches left`} />
                  <Stat label="Expected final" value={t.expected_points.toFixed(1)} hint={`spread (sd) ${t.points_sd.toFixed(1)}`} />
                  <Stat label="Middle half" value={`${Math.round(t.points_p25)}–${Math.round(t.points_p75)}`} hint={`median ${Math.round(t.points_median)}`} />
                  <Stat label="Range seen" value={`${t.points_min}–${t.points_max}`} hint={`10–90%: ${Math.round(t.points_p10)}–${Math.round(t.points_p90)}`} />
                </div>
                <PointsBars team={t} />
                <p className="text-[11px] text-mute">Bars: share of simulations ending on each points total (bright bars are the 10–90% range).</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SeasonSimulator() {
  const [mode, setMode] = useState("points");
  const [key, setKey] = useState("BUNDESLIGA");
  const [season, setSeason] = useState("");
  const [sims, setSims] = useState("");
  const [seed, setSeed] = useState("");
  const [experimental, setExperimental] = useState(false);
  const [run, setRun] = useState({ loading: false, error: null, result: null });
  const [version, setVersion] = useState(0);
  const gws = useApi("/api/gameweeks", { key, season });
  const st = useApi("/api/season/status", { key, season: gws.data?.season ?? season, v: version });
  const runs = useApi(st.data ? "/api/season/runs" : null, { key, season: st.data?.season, v: version });
  const ctl = useRef(null);
  useEffect(() => () => ctl.current?.abort(), []);
  useEffect(() => setRun({ loading: false, error: null, result: null }), [key, season, mode]);

  const s = st.data;
  const limits = s?.limits;
  const simsValue = sims || (limits ? String(limits.default) : "");
  const invalid = validateSims(simsValue, limits) || (seed !== "" && !/^\d+$/.test(seed) ? "Seed must be a whole number (or empty)." : null);
  const points = mode === "points";
  const canRun = points ? s?.points_only?.can_run : s?.can_simulate;
  const blockers = points ? s?.points_only?.blockers : s?.blockers;

  async function simulate() {
    ctl.current?.abort();
    ctl.current = new AbortController();
    setRun({ loading: true, error: null, result: null });
    const body = { key, season: s.season, user_action: points ? POINTS_ACTION : SIM_ACTION, simulations: Number(simsValue), seed: seed === "" ? null : Number(seed), include_experimental: !points && experimental };
    try {
      const result = await api(points ? "/api/season/points" : "/api/season/simulate", undefined, { signal: ctl.current.signal, method: "POST", body });
      setRun({ loading: false, error: null, result });
      setVersion((v) => v + 1);
    } catch (error) {
      if (error.name !== "AbortError") setRun({ loading: false, error, result: null });
    }
  }

  async function load(id) {
    setRun({ loading: true, error: null, result: null });
    try {
      const result = await api("/api/season/run", { id });
      setMode(result.assumptions.mode === "points_only" ? "points" : "full");
      setRun({ loading: false, error: null, result });
    } catch (error) {
      setRun({ loading: false, error, result: null });
    }
  }

  const r = run.result;
  const shown = r && (r.assumptions.mode === "points_only") === points ? r : null;
  const labelOf = (k) => ({ BUNDESLIGA: "Bundesliga", LALIGA: "La Liga", EPL: "Premier League", SERIEA: "Serie A", LIGUE1: "Ligue 1" })[k];
  return (
    <div className="space-y-4" data-testid="season-simulator">
      <header className="px-1">
        <h1 className="text-xl font-extrabold">Season simulator</h1>
        <p className="mt-1 text-sm text-mute">Monte Carlo simulation of the rest of a league season from the frozen club model. Runs only when you press the button. Estimates, not certainties and not betting advice.</p>
      </header>

      <Card>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="League">
            <Select aria-label="League" value={key} onChange={(v) => { setKey(v); setSeason(""); setSims(""); }} options={SEASON_LEAGUES.map((k) => ({ value: k, label: labelOf(k) }))} />
          </Field>
          <Field label="Season">
            <Select aria-label="Season" value={gws.data?.season ?? ""} onChange={setSeason} options={(gws.data?.seasons ?? []).map((x) => ({ value: x, label: x }))} disabled={!gws.data} />
          </Field>
        </div>
        <div className="mt-4">
          {st.loading && <Spinner label="Checking data quality…" />}
          <ErrorBox error={st.error} />
          {s && <EligibilityBanner st={s} />}
        </div>
      </Card>

      <Tabs
        label="Simulation mode"
        value={mode}
        onChange={setMode}
        tabs={[
          { value: "points", label: "Points-only (experimental)" },
          { value: "full", label: "Final positions (disabled)" },
        ]}
      />

      {s && !points && <RulesNotice rp={s.rule_profile} />}

      {s && points && (
        <Notice tone="warn" title={POINTS_LABEL}>
          Simulates win, draw and loss only (3 / 1 / 0 points) and shows how many points each club may finish with. It does not predict league positions, titles, top-four places or relegation, because those depend on tie-breaks and scores that are not yet validated.
        </Notice>
      )}

      {s && (
        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <Field label="Simulations" hint={limits ? `${limits.min.toLocaleString()}–${limits.max.toLocaleString()}, default ${limits.default.toLocaleString()}` : ""}>
              <Input type="number" inputMode="numeric" value={simsValue} onChange={(e) => setSims(e.target.value)} aria-label="Simulations" />
            </Field>
            <Field label="Seed (optional)" hint="Same seed and data give identical results.">
              <Input type="text" inputMode="numeric" placeholder="random" value={seed} onChange={(e) => setSeed(e.target.value.trim())} aria-label="Seed" />
            </Field>
            {!points && (
              <label className="flex items-center gap-2 pb-3 text-xs text-mute">
                <input type="checkbox" className="accent-[#8b7bff]" checked={experimental} onChange={(e) => setExperimental(e.target.checked)} />
                Also show experimental club v2-r1 comparison
              </label>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button onClick={simulate} disabled={!canRun || Boolean(invalid) || run.loading}>
              {run.loading ? "Simulating…" : points ? "Run points-only simulation" : "Run season simulation"}
            </Button>
            {canRun && !invalid && <span className="text-xs text-mute">Saves this run to the history below.</span>}
          </div>
          {!canRun && (
            <div className="mt-3 space-y-2" data-testid="blockers">
              <Notice tone="warn" title={points ? "Points-only simulation is disabled for this league" : "Final-position simulation is disabled"}>
                <ul className="list-disc space-y-1 pl-5">
                  {(blockers ?? []).map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </Notice>
            </div>
          )}
          {invalid && <div className="mt-2"><Notice tone="warn">{invalid}</Notice></div>}
        </Card>
      )}

      {run.loading && <Spinner label="Simulating… the first run can take about a minute while the model history loads." />}
      <ErrorBox error={run.error} />

      {shown && points && (
        <div className="space-y-4" data-testid="points-result">
          <Notice tone={shown.assumptions.eligibility.state === "ready" ? "info" : "warn"} title={`${POINTS_LABEL} · data quality: ${STATE[shown.assumptions.eligibility.state]?.label ?? shown.assumptions.eligibility.state}`}>
            Run {shown.run_id}, saved {shown.assumptions.created_utc} UTC, {shown.assumptions.simulations.toLocaleString()} simulations, seed {shown.assumptions.seed}, data through {shown.assumptions.data_cutoff.latest_result_in_competition}. {shown.assumptions.eligibility.reasons.join(" ")}
          </Notice>
          <div className="flex flex-wrap gap-2">
            <Badge badge="Validated club model v1 (probabilities)" title="Club v1 is the validated club model for this league" />
            <span className="rounded-full bg-warn/15 px-2 py-0.5 text-[11px] font-semibold text-warn">{POINTS_LABEL}</span>
          </div>
          <h2 className="px-1 text-[15px] font-bold">Expected final points</h2>
          <PointsResult summary={shown.result.summary} />
          <Assumptions a={shown.assumptions} st={s} mode={mode} />
        </div>
      )}

      {shown && !points && (
        <div className="space-y-4" data-testid="season-result">
          <Notice tone={r.assumptions.eligibility.state === "ready" ? "info" : "warn"} title={`Data quality: ${STATE[r.assumptions.eligibility.state]?.label ?? r.assumptions.eligibility.state}`}>
            Run {r.run_id}, saved {r.assumptions.created_utc} UTC, {r.assumptions.simulations.toLocaleString()} simulations, seed {r.assumptions.seed}, data through {r.assumptions.data_cutoff.latest_result_in_competition}. {r.assumptions.eligibility.reasons.join(" ")}
          </Notice>
          <div className="flex flex-wrap gap-2">
            <Badge badge="Validated club model v1 (probabilities)" title="Club v1 is the validated club model for this league" />
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-mute">Scoreline: {r.assumptions.scoreline.method}</span>
            {r.assumptions.scoreline.validation?.approved_by_user ? null : <span className="rounded-full bg-bad/15 px-2 py-0.5 text-[11px] font-semibold text-bad">Scoreline method not approved: diagnostic output</span>}
            {r.result.summary.final_position_probabilities_supported === false && <span className="rounded-full bg-bad/15 px-2 py-0.5 text-[11px] font-semibold text-bad">Some probabilities withheld: unresolved ties</span>}
          </div>
          <h2 className="px-1 text-[15px] font-bold">Projected final standings</h2>
          <ResultTable summary={r.result.summary} bands={r.result.positions.bands} />
          <Card title="Finishing-position probabilities" subtitle="Share of simulations in which each club finishes in each position">
            <Heatmap teams={r.result.summary.teams} />
          </Card>
          {r.result.summary.tie_resolution && (
            <p className="px-1 text-xs text-mute">
              Ties: an unresolved tie (play-off or similar, never simulated) occurred in {(r.result.summary.tie_resolution.share_with_an_unresolved_tie * 100).toFixed(2)}% of simulations; affected probabilities are withheld and shown as bounds.
            </p>
          )}
          {r.result.experimental && <SectionExperimental ex={r.result.experimental} />}
          <Assumptions a={r.assumptions} st={s} mode={mode} />
        </div>
      )}

      {!shown && s && <Assumptions a={null} st={s} mode={mode} />}

      {runs.data?.length > 0 && (
        <Card title="Saved simulation runs" subtitle="Application history, separate from the official prospective evaluation">
          <ul className="divide-y divide-line/60 text-sm">
            {runs.data.map((x) => (
              <li key={x.run_id} className="flex items-center justify-between gap-3 py-2">
                <span className="text-xs text-mute">
                  Run {x.run_id} · {x.mode === "points_only" ? "points-only (experimental)" : "final positions"} · {x.created_utc} · {x.n_simulations.toLocaleString()} sims · seed {x.seed}
                </span>
                <Button variant="ghost" onClick={() => load(x.run_id)}>
                  View
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

'''
s = s[:a] + new_main + s[b:]
s = s.replace('import { Badge, Button, Card, ErrorBox, Field, Input, Notice, Select, Spinner, TeamAvatar } from "../components/ui.jsx";', 'import { Badge, Button, Card, ErrorBox, Field, Input, Notice, Select, Spinner, Tabs, TeamAvatar } from "../components/ui.jsx";')
# expected_rank may be null in the table header sort stats
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
