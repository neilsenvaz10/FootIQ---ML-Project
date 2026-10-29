import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api.js";
import { useApi, useClubReady } from "../lib/hooks.js";
import { int, nextDay, pct } from "../lib/format.js";
import { axisProps, COLORS, tooltipStyle } from "../lib/chart.js";
import { useMeta } from "../components/MetaContext.jsx";
import CompetitionSelect from "../components/CompetitionSelect.jsx";
import CompetitionFreshness from "../components/CompetitionFreshness.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { TeamPoolFilter, useTeamPool } from "../components/TeamPool.jsx";
import ProbBar from "../components/ProbBar.jsx";
import { Badge, Button, Card, CompareRow, ErrorBox, Field, Gauge, Input, Notice, Select, Spinner, Tabs, TeamAvatar } from "../components/ui.jsx";

const MODEL_LABELS = { primary: "Primary model", secondary: "Club v2-r1 (candidate)", elo_only: "Elo-only baseline" };
const CLUB_MODEL_LABELS = { primary: "Club v1 · validated", secondary: "Club v2-r1 · experimental", elo_only: "Elo-only baseline" };

export function isClubCompetition(comp) {
  return comp?.group === "Domestic league" || comp?.group === "Continental club";
}

function Slot({ label, name, children }) {
  return (
    <div className="min-w-0 flex-1 rounded-2xl bg-panel-2 p-3 text-center">
      <div className="mb-2 flex justify-center">{name ? <TeamAvatar name={name} size={48} /> : <span className="grid h-12 w-12 place-items-center rounded-full border border-dashed border-line text-mute">?</span>}</div>
      <span className="mb-1 block text-xs font-medium text-mute">{label}</span>
      {children}
    </div>
  );
}

export default function Predict() {
  const [params, setParams] = useSearchParams();
  const comps = useApi("/api/competitions");
  const meta = useMeta();
  const club = useClubReady();
  const key = params.get("comp") || "EPL";
  const comp = comps.data?.find((c) => c.key === key);
  const isClub = isClubCompetition(comp);
  const [poolChoice, setPoolChoice] = useState("");
  const pool = useTeamPool(key, poolChoice);
  const teams = pool.teams;

  const [home, setHome] = useState(params.get("home") ?? "");
  const [away, setAway] = useState(params.get("away") ?? "");
  const lastKey = useRef(key); // the competition the current selection belongs to
  const [date, setDate] = useState("");
  const [venue, setVenue] = useState("neutral");
  const [model, setModel] = useState("primary");
  const [run, setRun] = useState({ loading: false, error: null, result: null });
  const req = useRef(0);

  useEffect(() => {
    // Reset only when the competition really changes. Comparing with the previous key (not a one-shot flag) keeps clubs chosen by a Matches link on first load, also when React StrictMode runs the effect twice in development.
    if (lastKey.current === key) return;
    lastKey.current = key;
    setHome("");
    setAway("");
    setDate("");
    setVenue("neutral");
    setModel("primary");
    setPoolChoice("");
    setRun({ loading: false, error: null, result: null });
  }, [key]);

  const minDate = meta.data ? nextDay(meta.data.data_through.club_results) : undefined;
  const dateTooEarly = date && minDate && date < minDate;
  const same = home && home === away;
  const clubBlocked = isClub && !club.ready;
  const canRun = home && away && !same && !dateTooEarly && !clubBlocked && !run.loading;

  async function predict() {
    const id = ++req.current;
    setRun({ loading: true, error: null, result: null });
    try {
      const result = await api("/api/predict", { key, home, away, date, venue: isClub ? undefined : venue });
      if (id === req.current) {
        setRun({ loading: false, error: null, result });
        setModel("primary");
      }
    } catch (error) {
      if (id === req.current) setRun({ loading: false, error, result: null });
    }
  }

  const r = run.result;
  const available = r ? ["primary", "secondary", "elo_only"].filter((m) => r[m]) : [];
  const shown = r?.[model] ?? r?.primary;
  const chartData = r
    ? [
        { outcome: `${r.home} win`, ...Object.fromEntries(available.map((m) => [m, +(r[m].home * 100).toFixed(1)])) },
        { outcome: "Draw", ...Object.fromEntries(available.map((m) => [m, +(r[m].draw * 100).toFixed(1)])) },
        { outcome: `${r.away} win`, ...Object.fromEntries(available.map((m) => [m, +(r[m].away * 100).toFixed(1)])) },
      ]
    : [];
  const barColors = { primary: COLORS.pitch, secondary: COLORS.home, elo_only: COLORS.draw };

  return (
    <>
      <p className="mb-3 text-[13px] text-mute">Home / draw / away probabilities for any two teams of a competition, from the project's existing frozen models. Nothing is saved.</p>
      <CompetitionSelect comps={comps.data} value={key} onChange={(v) => setParams({ comp: v })} />
      <CompetitionFreshness compKey={key} />
      <TeamPoolFilter pool={pool} onChange={(v) => { setPoolChoice(v); setHome(""); setAway(""); setRun({ loading: false, error: null, result: null }); }} />

      {(comps.error || teams.error) && <div className="mt-4"><ErrorBox error={comps.error || teams.error} /></div>}

      <Card className="mt-4">
        <div className="flex gap-3">
          <Slot label={isClub ? "Home team" : "Team 1"} name={home}>
            <Select value={home} onChange={setHome} options={teams.data ?? []} placeholder="Select" disabled={!teams.data} aria-label="Home team" />
          </Slot>
          <div className="grid shrink-0 place-items-center text-xs font-extrabold text-mute">VS</div>
          <Slot label={isClub ? "Away team" : "Team 2"} name={away}>
            <Select value={away} onChange={setAway} options={(teams.data ?? []).filter((t) => t !== home)} placeholder="Select" disabled={!teams.data} aria-label="Away team" />
          </Slot>
        </div>
        <div className="mt-3 flex flex-wrap gap-3">
          <Field label="Prediction date (optional)" hint={minDate ? `On or after ${minDate}. Empty = earliest allowed.` : undefined}>
            <Input type="date" value={date} min={minDate} onChange={(e) => setDate(e.target.value)} aria-label="Prediction date" />
          </Field>
          {comp && !isClub && (
            <Field label="Venue">
              <Select
                value={venue}
                onChange={setVenue}
                options={[
                  { value: "neutral", label: "Neutral ground" },
                  { value: "home", label: "Team 1 at home" },
                ]}
                aria-label="Venue"
              />
            </Field>
          )}
        </div>
        <div className="mt-4">
          <Button onClick={predict} disabled={!canRun} className="w-full sm:w-auto">
            {run.loading ? "Predicting…" : "Predict"}
          </Button>
        </div>
        <div className="mt-3 space-y-2">
          {same && <Notice tone="warn">Choose two different teams.</Notice>}
          {dateTooEarly && <Notice tone="warn">The date must be on or after {minDate}: predictions only use history up to that point.</Notice>}
          {comp && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge badge={comp.badge} />
              <span className="text-mute">{comp.basis}</span>
            </div>
          )}
          {isClub && club.error && <Notice tone="bad" title="Backend not reachable.">{club.error.message}</Notice>}
          {isClub && !club.error && !club.ready && (
            <Notice tone="info" title="Club models are warming up.">
              The backend is loading match history (about 20 seconds after start-up). Checking <code>/api/health</code> every few seconds; Predict unlocks when ready.
            </Notice>
          )}
          {isClub && club.ready && <p className="text-xs text-ok">Club models ready.</p>}
        </div>
      </Card>

      <div className="mt-4">
        <Notice tone="warn" title="Estimates, not guaranteed results.">
          These are statistical estimates from historical data. Football outcomes are uncertain and a high probability is not a promise. Data is historical, not live.
        </Notice>
      </div>

      <div className="mt-4 space-y-4">
        {run.loading && <Spinner label="Running the model…" />}
        <ErrorBox error={run.error} />
        {!r && !run.loading && !run.error && <p className="rounded-2xl border border-dashed border-line px-4 py-8 text-center text-sm text-mute">Pick a competition and two teams, then press Predict.</p>}

        {r && shown && (
          <>
            <section className="hero rounded-3xl p-4 sm:p-6">
              <h2 className="sr-only">{`${r.home} vs ${r.away}`}</h2>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-bold">{r.competition}</span>
                <Badge badge={r.validation_badge} title={r.validation_basis} />
              </div>
              <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                <div className="flex min-w-0 flex-col items-center gap-2 text-center">
                  <TeamAvatar name={r.home} size={72} />
                  <span className="max-w-full truncate text-base font-extrabold sm:text-lg">{r.home}</span>
                  <span className="text-xs uppercase tracking-wide text-white/75">{isClub || venue === "home" ? "Home" : "Team 1"}</span>
                </div>
                <div className="text-center">
                  <div className="text-xs font-extrabold text-white/60">VS</div>
                  <div className="mt-1 text-xs text-white/80">{r.date}</div>
                </div>
                <div className="flex min-w-0 flex-col items-center gap-2 text-center">
                  <TeamAvatar name={r.away} size={72} />
                  <span className="max-w-full truncate text-base font-extrabold sm:text-lg">{r.away}</span>
                  <span className="text-xs uppercase tracking-wide text-white/75">{isClub || venue === "home" ? "Away" : "Team 2"}</span>
                </div>
              </div>
              <p className="mt-4 text-center text-xs text-white/75">Estimate from history through {r.data_through}. Not a guaranteed result.</p>
            </section>

            <Card title="Win probability" subtitle={shown.model}>
              <Tabs label="Model" value={model} onChange={setModel} tabs={available.map((m) => ({ value: m, label: (isClub ? CLUB_MODEL_LABELS : MODEL_LABELS)[m] }))} />
              {isClub && model === "secondary" && <div className="mt-3"><Notice tone="warn" title="Experimental.">Club v2-r1 is a candidate with development-fold evidence only; no unbiased evaluation exists. The validated model is club v1.</Notice></div>}
              <div className="mt-4">
                <ProbBar probs={shown} homeLabel={`${r.home} win`} awayLabel={`${r.away} win`} homeName={r.home} awayName={r.away} />
              </div>
              <div className="mt-5 flex items-end justify-center gap-1 sm:gap-8">
                <Gauge value={shown.home} label={`${r.home} win`} color={COLORS.home} />
                <div className="shrink-0 pb-4 text-center">
                  <div className="whitespace-nowrap text-lg font-extrabold tabular-nums sm:text-xl">{pct(shown.draw)}</div>
                  <div className="text-xs text-mute">Draw</div>
                </div>
                <Gauge value={shown.away} label={`${r.away} win`} color={COLORS.away} />
              </div>
              {r.gate && (
                <p className="mt-3 text-xs text-mute">
                  Project confidence gate: <strong className="text-ink">{r.gate.public_pick}</strong>. {r.gate.meaning}.
                </p>
              )}
            </Card>

            {r.inputs && (
              <Card title="What the model saw" subtitle="The inputs behind the estimate, as of the data cut-off">
                <div className="mb-1 grid grid-cols-2 text-xs font-bold">
                  <span className="flex items-center gap-2 text-home"><TeamAvatar name={r.home} size={20} />{r.home}</span>
                  <span className="flex items-center justify-end gap-2 text-right text-away">{r.away}<TeamAvatar name={r.away} size={20} /></span>
                </div>
                <CompareRow label="Strength rating (Elo)" left={r.inputs.home.elo} right={r.inputs.away.elo} format={(v) => Math.round(v)} leftColor={COLORS.home} rightColor={COLORS.away} />
                <CompareRow label="Points per game, last 5" left={r.inputs.home.ppg5} right={r.inputs.away.ppg5} format={(v) => v.toFixed(2)} leftColor={COLORS.home} rightColor={COLORS.away} />
                <CompareRow label="Goal difference per game, last 5" left={r.inputs.home.gd5} right={r.inputs.away.gd5} format={(v) => (v > 0 ? `+${v.toFixed(2)}` : v.toFixed(2))} leftColor={COLORS.home} rightColor={COLORS.away} />
                <CompareRow label="Days since last match" left={r.inputs.home.days_rest} right={r.inputs.away.days_rest} format={(v) => Math.round(v)} higherIsBetter={false} leftColor={COLORS.home} rightColor={COLORS.away} />
                <CompareRow label="Earlier matches in the data" left={r.inputs.home.prior_matches} right={r.inputs.away.prior_matches} format={(v) => int(v)} leftColor={COLORS.home} rightColor={COLORS.away} />
                <p className="mt-2 text-xs text-mute">These are the model's inputs, not match statistics. Elo is the club v1 rating; form uses the last five matches.</p>
              </Card>
            )}
            <div className="grid gap-4 lg:grid-cols-2">
              <Card title="Models compared" subtitle="Percent probability by outcome">
                <div className="h-64">
                  <ResponsiveContainer>
                    <BarChart data={chartData} margin={{ left: -15, right: 8, top: 8 }}>
                      <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
                      <XAxis dataKey="outcome" {...axisProps} />
                      <YAxis {...axisProps} unit="%" />
                      <Tooltip {...tooltipStyle} cursor={{ fill: "#181830" }} formatter={(v) => `${v}%`} />
                      <Legend wrapperStyle={{ fontSize: 12 }} formatter={(v) => MODEL_LABELS[v]} />
                      {available.map((m) => (
                        <Bar key={m} dataKey={m} fill={barColors[m]} radius={[4, 4, 0, 0]} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <ul className="mt-2 space-y-0.5 text-xs text-mute">
                  {available.map((m) => (
                    <li key={m}>
                      <span className="text-ink/80">{MODEL_LABELS[m]}:</span> {r[m].model} (home {pct(r[m].home)}, draw {pct(r[m].draw)}, away {pct(r[m].away)})
                    </li>
                  ))}
                </ul>
              </Card>
              <Card title="Data and model limitations">
                <div className="space-y-2">
                  {r.notes.map((n) => (
                    <Notice key={n} tone={n.includes("NOT validated") ? "bad" : "warn"}>
                      {n}
                    </Notice>
                  ))}
                  <p className="text-xs text-mute">
                    <span className="text-ink/80">Validation basis:</span> {r.validation_basis}
                  </p>
                  <p className="text-xs text-mute">
                    <span className="text-ink/80">Data cut-off:</span> history through {r.data_through}. Earlier matches used: {r.home} {r.history.home_prior_matches}, {r.away} {r.history.away_prior_matches}.
                  </p>
                  <p className="text-xs text-mute">The v2-r1 candidate has only development-fold evidence; no unbiased evaluation exists for it.</p>
                </div>
              </Card>
            </div>
          </>
        )}
      </div>
    </>
  );
}
