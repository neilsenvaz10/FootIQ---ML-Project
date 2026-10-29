import { useEffect, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api.js";
import { axisProps, COLORS, tooltipStyle } from "../lib/chart.js";
import Bracket from "../components/Bracket.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { Badge, Button, Card, ErrorBox, Field, Input, Notice, SectionCard, Spinner, Tabs, TeamAvatar } from "../components/ui.jsx";

export const MIN_SIMS = 100;
export const MAX_SIMS = 50000;
export const MAX_SEED = 2147483647;
export const DEFAULT_SIMS = 1000; // small by default: results in about a second

export const WORLDCUP_GROUPS = {
  A: ["Czech Republic", "Mexico", "South Africa", "South Korea"],
  B: ["Bosnia & Herzegovina", "Canada", "Qatar", "Switzerland"],
  C: ["Brazil", "Haiti", "Morocco", "Scotland"],
  D: ["Australia", "Paraguay", "Turkey", "USA"],
  E: ["Curaçao", "Ecuador", "Germany", "Ivory Coast"],
  F: ["Japan", "Netherlands", "Sweden", "Tunisia"],
  G: ["Belgium", "Egypt", "Iran", "New Zealand"],
  H: ["Cape Verde", "Saudi Arabia", "Spain", "Uruguay"],
  I: ["France", "Iraq", "Norway", "Senegal"],
  J: ["Algeria", "Argentina", "Austria", "Jordan"],
  K: ["Colombia", "DR Congo", "Portugal", "Uzbekistan"],
  L: ["Croatia", "England", "Ghana", "Panama"],
};

const MODES = [
  { value: "pre_tournament", label: "Pre-tournament", help: "No real results used: what the model said before the 2026 World Cup started." },
  { value: "current", label: "Archived state", help: "Completed 2026 results are locked, so only the few remaining matches are simulated. Not live odds." },
];

// Rough time guide from the backend audit (5,000 simulations: about 1 s archived, about 8 s pre-tournament).
export function estimateSeconds(mode, sims) {
  return Math.max(1, Math.round((sims / 5000) * (mode === "pre_tournament" ? 8 : 1)));
}

export function validateInputs(sims, seed) {
  const n = Number(sims);
  if (!Number.isInteger(n) || n < MIN_SIMS || n > MAX_SIMS) return `Simulations must be a whole number from ${MIN_SIMS} to ${MAX_SIMS.toLocaleString()}.`;
  if (seed !== "" && (!/^\d+$/.test(seed) || Number(seed) > MAX_SEED)) return `Seed must be a whole number from 0 to ${MAX_SEED.toLocaleString()} (or empty for the default).`;
  return null;
}

function useElapsed(active) {
  const [s, setS] = useState(0);
  useEffect(() => {
    if (!active) return undefined;
    setS(0);
    const t = setInterval(() => setS((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, [active]);
  return s;
}

const TOP_N = 16;
const LINE_COLORS = ["#27d17f", "#8b7bff", "#f4c542", "#4f8cff", "#ff6b6b"];

function TournamentOverview() {
  const [showTeams, setShowTeams] = useState(false);
  const totalTeams = Object.values(WORLDCUP_GROUPS).reduce((acc, g) => acc + g.length, 0);

  return (
    <Card className="mb-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-pitch/15 px-2.5 py-0.5 text-xs font-bold text-pitch">Tournament</span>
            <h2 className="text-sm font-bold">FIFA World Cup 2026</h2>
          </div>
          <p className="mt-1 text-xs text-mute">
            United States, Canada &amp; Mexico · 48 Qualified Nations · 12 Groups (A–L)
          </p>
        </div>
        <Button
          variant="ghost"
          onClick={() => setShowTeams(!showTeams)}
          aria-expanded={showTeams}
          className="text-xs"
        >
          {showTeams ? "Hide qualified teams" : `View all ${totalTeams} qualified teams`}
        </Button>
      </div>

      {showTeams && (
        <div className="mt-4 border-t border-line/60 pt-4" data-testid="worldcup-teams-grid">
          <p className="mb-3 text-xs text-mute">
            All 48 qualified national teams entering the tournament. Top 2 from each group plus the 8 best 3rd-place finishers advance to the Round of 32 knockout stage.
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Object.entries(WORLDCUP_GROUPS).map(([group, teams]) => (
              <div key={group} className="rounded-xl bg-panel-2/60 p-2.5 text-xs">
                <span className="font-bold text-pitch">Group {group}</span>
                <ul className="mt-1.5 space-y-1">
                  {teams.map((t) => (
                    <li key={t} className="flex items-center gap-1.5 truncate">
                      <TeamAvatar name={t} size={16} />
                      <span className="truncate">{t}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

// Compact comparison of the five most likely champions, plus how far each is expected to progress. All values come from the backend response.
function TopFive({ odds }) {
  const live = odds.filter((t) => t.champion_pct > 0); // only teams that can still win (in the archived state most are eliminated)
  const top = (live.length ? live : odds).slice(0, 5);
  const hasQualify = top.some((t) => t.qualify_knockout_pct != null);
  const stages = [
    ...(hasQualify ? [["Knockout", "qualify_knockout_pct"]] : []),
    ["R16", "round_of_16_pct"],
    ["QF", "quarter_final_pct"],
    ["SF", "semi_final_pct"],
    ["Final", "final_pct"],
    ["Title", "champion_pct"],
  ];
  const progression = stages.map(([name, k]) => ({
    stage: name,
    ...Object.fromEntries(top.map((t) => [t.team, t[k] ?? 0])),
  }));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Top five contenders" subtitle={`Champion probability (%)${live.length && live.length < 5 ? ` · only ${live.length} team${live.length === 1 ? "" : "s"} can still win` : ""}`}>
        <div className="h-56">
          <ResponsiveContainer>
            <BarChart data={top} layout="vertical" margin={{ left: 0, right: 16 }}>
              <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" unit="%" {...axisProps} />
              <YAxis type="category" dataKey="team" width={96} {...axisProps} interval={0} />
              <Tooltip {...tooltipStyle} cursor={{ fill: "#181830" }} formatter={(v) => `${v}%`} />
              <Bar dataKey="champion_pct" name="Champion" fill={COLORS.pitch} radius={[0, 4, 4, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <Card title="Tournament progression" subtitle="Chance of reaching each stage (%)">
        <div className="h-56">
          <ResponsiveContainer>
            <LineChart data={progression} margin={{ left: -10, right: 12, top: 8 }}>
              <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
              <XAxis dataKey="stage" {...axisProps} interval={0} />
              <YAxis {...axisProps} unit="%" domain={[0, 100]} />
              <Tooltip {...tooltipStyle} formatter={(v) => `${v}%`} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {top.map((t, i) => (
                <Line key={t.team} type="monotone" dataKey={t.team} stroke={LINE_COLORS[i]} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}

function Leaderboard({ odds }) {
  const [all, setAll] = useState(false);
  const [filterGroup, setFilterGroup] = useState("ALL");
  const filtered = filterGroup === "ALL" ? odds : odds.filter((t) => t.group === filterGroup);
  const rows = all ? filtered : filtered.slice(0, TOP_N);
  const max = Math.max(...odds.map((t) => t.champion_pct), 1);
  const groups = Array.from(new Set(odds.map((t) => t.group).filter(Boolean))).sort();

  return (
    <SectionCard
      title="Title probabilities"
      subtitle={
        all
          ? `All ${filtered.length} teams${filterGroup !== "ALL" ? ` (Group ${filterGroup})` : ""}`
          : `Top ${Math.min(TOP_N, filtered.length)} by champion probability${filterGroup !== "ALL" ? ` (Group ${filterGroup})` : ""}`
      }
    >
      {groups.length > 1 && (
        <div className="flex flex-wrap items-center gap-1.5 border-t border-line/60 px-4 py-2 text-xs">
          <span className="mr-1 text-mute">Filter Group:</span>
          <button
            onClick={() => setFilterGroup("ALL")}
            className={`rounded-lg px-2 py-0.5 font-medium transition-colors ${
              filterGroup === "ALL" ? "bg-pitch text-black font-bold" : "bg-panel-2 text-mute hover:text-text"
            }`}
          >
            All
          </button>
          {groups.map((g) => (
            <button
              key={g}
              onClick={() => setFilterGroup(g)}
              className={`rounded-lg px-2 py-0.5 font-medium transition-colors ${
                filterGroup === g ? "bg-pitch text-black font-bold" : "bg-panel-2 text-mute hover:text-text"
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      )}
      {rows.map((t) => (
        <div key={t.team} className="border-t border-line/60 px-4 py-2.5">
          <div className="flex items-center gap-3">
            <span className="w-5 shrink-0 text-center text-xs tabular-nums text-mute">{t.rank}</span>
            <TeamAvatar name={t.team} size={26} />
            <span className="min-w-0 flex-1 truncate text-sm font-semibold">
              {t.team} <span className="text-[11px] font-normal text-mute">Grp {t.group}</span>
            </span>
            <span className="shrink-0 text-right text-sm font-extrabold tabular-nums">
              <span>{t.champion_pct}</span>
              <span className="text-mute">%</span>
            </span>
          </div>
          <div className="ml-[3.75rem] mt-1.5 h-1.5 overflow-hidden rounded-full bg-panel-2">
            <div className="h-full rounded-full bg-pitch" style={{ width: `${(t.champion_pct / max) * 100}%` }} />
          </div>
          <p className="ml-[3.75rem] mt-1 text-[11px] text-mute">
            {t.qualify_knockout_pct != null ? `Qualify ${t.qualify_knockout_pct}% · ` : ""}R16 {t.round_of_16_pct}% · QF {t.quarter_final_pct}% · SF {t.semi_final_pct}% · Final {t.final_pct}%
          </p>
        </div>
      ))}
      {filtered.length > TOP_N && (
        <button onClick={() => setAll(!all)} className="w-full border-t border-line/60 py-3 text-sm font-semibold text-pitch">
          {all ? "Show fewer" : `Show all ${filtered.length} teams`}
        </button>
      )}
    </SectionCard>
  );
}

export default function Simulator() {
  const [view, setView] = useState("simulate");
  const [mode, setMode] = useState("pre_tournament");
  const [sims, setSims] = useState(String(DEFAULT_SIMS));
  const [seed, setSeed] = useState("");
  const [run, setRun] = useState({ loading: false, error: null, result: null });
  const ctl = useRef(null);
  const elapsed = useElapsed(run.loading);
  const invalid = validateInputs(sims, seed);
  const est = estimateSeconds(mode, Number(sims) || 0);

  useEffect(() => () => ctl.current?.abort(), []);

  async function simulate() {
    ctl.current?.abort();
    ctl.current = new AbortController();
    setRun({ loading: true, error: null, result: null });
    try {
      const result = await api("/api/worldcup/simulate", { simulations: sims, seed, mode }, { signal: ctl.current.signal });
      setRun({ loading: false, error: null, result });
    } catch (error) {
      if (error.name !== "AbortError") setRun({ loading: false, error, result: null });
    }
  }

  function cancel() {
    ctl.current?.abort();
    setRun({ loading: false, error: null, result: null });
  }

  const r = run.result;
  return (
    <>
      <PageHeader title="World Cup simulator">Monte Carlo simulation of the 2026 World Cup with the project's existing simulator (v2.3 team-power engine). A separate engine from the match-prediction models; historical states only.</PageHeader>

      <Tabs
        label="World Cup views"
        value={view}
        onChange={setView}
        tabs={[
          { value: "simulate", label: "Simulation" },
          { value: "bracket", label: "2026 bracket (real results)" },
        ]}
      />
      {view === "bracket" && (
        <div className="mt-4">
          <Bracket />
        </div>
      )}
      <div className={view === "bracket" ? "hidden" : "mt-4"}>
        <TournamentOverview />

        <Card>
          <fieldset>
            <legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-mute">Simulation Mode</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {MODES.map((m) => (
                <label
                  key={m.value}
                  className={`flex cursor-pointer items-start gap-3 rounded-2xl p-3.5 text-sm transition-colors focus-within:ring-2 focus-within:ring-pitch ${
                    mode === m.value ? "bg-panel-2 ring-1 ring-inset ring-pitch" : "bg-panel-2/50 hover:bg-panel-2/80"
                  }`}
                >
                  <input
                    type="radio"
                    name="mode"
                    className="mt-0.5 h-5 w-5 shrink-0 cursor-pointer accent-[#8b7bff] focus:outline-none"
                    checked={mode === m.value}
                    onChange={() => setMode(m.value)}
                  />
                  <div className="min-w-0 flex-1">
                    <span className="block font-bold">{m.label}</span>
                    <span className="mt-1 block text-xs text-mute">{m.help}</span>
                  </div>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="mt-4 flex flex-wrap gap-3">
            <Field label="Simulations" hint={`${MIN_SIMS}–${MAX_SIMS.toLocaleString()}. Default ${DEFAULT_SIMS.toLocaleString()} for a quick answer.`}>
              <Input type="number" inputMode="numeric" min={MIN_SIMS} max={MAX_SIMS} step="100" value={sims} onChange={(e) => setSims(e.target.value)} aria-label="Simulations" />
            </Field>
            <Field label="Seed (optional)" hint="Same seed and settings give identical results. Empty = the project's default seed.">
              <Input type="text" inputMode="numeric" placeholder="default" value={seed} onChange={(e) => setSeed(e.target.value.trim())} aria-label="Seed" />
            </Field>
          </div>
          <div className="mt-4 flex gap-2">
            <Button onClick={simulate} disabled={Boolean(invalid) || run.loading} className="flex-1 sm:flex-none">
              {run.loading ? "Simulating…" : "Run simulation"}
            </Button>
            {run.loading && (
              <Button variant="ghost" onClick={cancel}>
                Cancel
              </Button>
            )}
          </div>
          <div className="mt-3 space-y-2">
            {invalid && <Notice tone="warn">{invalid}</Notice>}
            <p className="text-xs text-mute">
              Larger simulations take longer: estimated about {est} s for this setting. Pre-tournament mode is slower than archived-state mode (about 8 s versus about 1 s per 5,000 simulations).
            </p>
            {mode === "pre_tournament" && Number(sims) > 20000 && !invalid && <Notice tone="warn">More than 20,000 pre-tournament simulations can take over a minute.</Notice>}
          </div>
        </Card>

        <div className="mt-4 space-y-4">
          {run.loading && <Spinner label={`Simulating ${Number(sims).toLocaleString()} tournaments… ${elapsed}s elapsed (estimate about ${est}s)`} />}
          <ErrorBox error={run.error} />
          {!r && !run.loading && !run.error && (
            <p className="rounded-2xl border border-dashed border-line px-4 py-8 text-center text-sm text-mute">
              Choose simulation settings and press Run simulation.
            </p>
          )}

          {r && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge badge={r.mode === "pre_tournament" ? "Pre-tournament mode" : "Archived-state mode"} />
                <span className="rounded-full bg-panel-2 px-2.5 py-0.5 text-xs text-mute">
                  <b>{r.simulations.toLocaleString()}</b> simulations
                </span>
                <span className="rounded-full bg-panel-2 px-2.5 py-0.5 text-xs text-mute">
                  Seed: <b>{r.seed}</b>
                </span>
                <span className="rounded-full bg-panel-2 px-2.5 py-0.5 text-xs text-mute">
                  Time: <b>{r.seconds}s</b>
                </span>
                <span className="rounded-full bg-panel-2 px-2.5 py-0.5 text-xs text-mute">
                  Engine: <b>{r.engine}</b>
                </span>
              </div>
              <Notice tone="info" title={r.mode === "pre_tournament" ? "Pre-tournament mode." : "Archived-state mode."}>
                {r.note} Ran {r.simulations.toLocaleString()} simulations with seed {r.seed} in {r.seconds}s. Engine: {r.engine}.
              </Notice>
              <TopFive odds={r.title_odds} />
              <Leaderboard odds={r.title_odds} />
              {r.group_tables ? (
                <div className="space-y-3">
                  <h2 className="px-1 text-[15px] font-bold">Group tables</h2>
                  <p className="px-1 text-xs text-mute">Real results locked in this archived state</p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {Object.entries(r.group_tables).map(([g, rows]) => (
                      <SectionCard key={g} title={`Group ${g}`}>
                        {rows.map((t, i) => (
                          <div key={t.team} className="flex items-center gap-3 border-t border-line/60 px-4 py-2 text-sm">
                            <span className={`w-4 text-xs tabular-nums ${i === 0 ? "font-bold" : "text-mute"}`}>{i + 1}</span>
                            <TeamAvatar name={t.team} size={22} />
                            <span className="min-w-0 flex-1 truncate font-semibold">{t.team}</span>
                            <span className="w-8 text-right text-xs tabular-nums text-mute">{t.goal_diff > 0 ? `+${t.goal_diff}` : t.goal_diff}</span>
                            <span className="w-7 text-right font-extrabold tabular-nums">{t.points}</span>
                          </div>
                        ))}
                      </SectionCard>
                    ))}
                  </div>
                </div>
              ) : (
                <Notice tone="info">Group tables are only shown in archived-state mode (pre-tournament mode uses no real results). Match-by-match brackets are not shown because the backend does not provide them.</Notice>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
