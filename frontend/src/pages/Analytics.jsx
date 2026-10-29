import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api.js";
import { useApi } from "../lib/hooks.js";
import { int, num, pct } from "../lib/format.js";
import { axisProps, COLORS, tooltipStyle } from "../lib/chart.js";
import StandingsTable from "../components/leagues/StandingsTable.jsx";
import ResultsFixtures from "../components/leagues/ResultsFixtures.jsx";
import SourceDetails from "../components/SourceDetails.jsx";
import { LEAGUE_KEYS, seasonIndicators, TABLE_NOTE } from "../lib/leagues.js";
import { Pills, Chip, ButtonLink } from "../components/ui.jsx";
import CompetitionSelect from "../components/CompetitionSelect.jsx";
import CompetitionFreshness from "../components/CompetitionFreshness.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { Badge, CONTROL_EDGE, Card, Empty, ErrorBox, MatchRow, Notice, SectionCard, Spinner, StatCard, Tabs } from "../components/ui.jsx";

const TREND_SEASONS = 12;

// Outcome rates per season: one /dashboard call per season (newest TREND_SEASONS), straight from the backend.
function useTrend(key, seasons) {
  const [trend, setTrend] = useState(null);
  useEffect(() => {
    if (!seasons?.length) {
      setTrend(null);
      return undefined;
    }
    const ctl = new AbortController();
    setTrend(null);
    Promise.all(seasons.slice(0, TREND_SEASONS).map((s) => api(`/api/competitions/${key}/dashboard`, { season: s }, { signal: ctl.signal })))
      .then((ds) => setTrend(ds.map((d) => ({ season: d.season, ...d.summary })).reverse()))
      .catch(() => setTrend([]));
    return () => ctl.abort();
  }, [key, seasons]);
  return trend;
}

// Compact outcome label to prevent clipping on narrow viewports (e.g. 375px).
const pieLabel = ({ name, value }) => {
  const shortName = name === "Home win" ? "Home" : name === "Away win" ? "Away" : name;
  return `${shortName} ${pct(value, 0)}`;
};

function StatsTab({ summary, trend }) {
  const known = summary.home_win_rate != null;
  const pie = known
    ? [
        { name: "Home win", value: summary.home_win_rate, fill: COLORS.home },
        { name: "Draw", value: summary.draw_rate, fill: COLORS.draw },
        { name: "Away win", value: summary.away_win_rate, fill: COLORS.away },
      ]
    : [];
  return (
    <div className="space-y-4">
      <Card title="Win / draw / loss split" subtitle={`This season. ${summary.outcome_basis}`}>
        {known ? (
          <div className="h-60">
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={pie}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={46}
                  outerRadius={74}
                  paddingAngle={2}
                  stroke="none"
                  isAnimationActive={false}
                  label={pieLabel}
                >
                  {pie.map((p) => (
                    <Cell key={p.name} fill={p.fill} />
                  ))}
                </Pie>
                <Tooltip {...tooltipStyle} formatter={(v) => pct(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <Empty>No match outcomes are known for this season.</Empty>
        )}
      </Card>
      <Card title="Outcome rates by season" subtitle={`Newest ${TREND_SEASONS} seasons or editions`}>
        {!trend ? (
          <Spinner label="Loading trend…" />
        ) : trend.length < 2 ? (
          <Empty>Not enough seasons for a trend.</Empty>
        ) : (
          <div className="h-60">
            <ResponsiveContainer>
              <LineChart data={trend} margin={{ left: -12, right: 8, top: 8 }}>
                <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
                <XAxis dataKey="season" {...axisProps} />
                <YAxis {...axisProps} tickFormatter={(v) => pct(v, 0)} domain={[0, "auto"]} />
                <Tooltip {...tooltipStyle} formatter={(v) => pct(v)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="home_win_rate" name="Home win" stroke={COLORS.home} dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="draw_rate" name="Draw" stroke={COLORS.draw} dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="away_win_rate" name="Away win" stroke={COLORS.away} dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
    </div>
  );
}

// Truncate long team names for the Y-axis tick of the bar chart; full name is still in the tooltip.
const MAX_TEAM_LABEL = 16;
function teamTick(name) {
  if (typeof name !== "string") return name;
  return name.length > MAX_TEAM_LABEL ? name.slice(0, MAX_TEAM_LABEL - 1).trimEnd() + "…" : name;
}

function SeasonStats({ comp, seasons, summary, rows }) {
  const trend = useTrend(comp, seasons);
  const rowHeight = 30;
  return (
    <>
      <StatsTab summary={summary} trend={trend} />
      {rows?.length > 0 && (
        <Card title="Team performance" subtitle="Wins, draws and losses per team">
          <div style={{ height: Math.max(280, rows.length * rowHeight) }}>
            <ResponsiveContainer>
              <BarChart data={rows} layout="vertical" margin={{ left: 0, right: 12 }}>
                <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" {...axisProps} />
                <YAxis
                  type="category"
                  dataKey="team"
                  width={110}
                  {...axisProps}
                  interval={0}
                  tick={{ fill: COLORS.text, fontSize: 11 }}
                  tickFormatter={teamTick}
                />
                <Tooltip {...tooltipStyle} cursor={{ fill: "#181830" }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="won" name="Won" stackId="r" fill={COLORS.win} isAnimationActive={false} />
                <Bar dataKey="drawn" name="Drawn" stackId="r" fill={COLORS.draw} isAnimationActive={false} />
                <Bar dataKey="lost" name="Lost" stackId="r" fill={COLORS.loss} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
    </>
  );
}

function SeasonDashboard({ comp, season, seasons }) {
  const [tab, setTab] = useState(comp.group === "Domestic league" ? "table" : "matches");
  const [retry, setRetry] = useState(0);
  const dash = useApi(`/api/competitions/${comp.key}/dashboard`, { season }, { retry });
  const cov = useApi(`/api/competitions/${comp.key}/coverage`, undefined, { retry });
  const sync = useApi(LEAGUE_KEYS.includes(comp.key) ? "/api/sync/status" : null, undefined, { retry });
  const coverage = cov.data?.find((r) => String(r.season) === season);
  const current = season === seasons[0];
  const league = sync.data?.competitions.find((c) => c.competition_key === comp.key);
  if (dash.loading) return <Spinner label="Loading season…" />;
  if (dash.error) return <ErrorBox error={dash.error} onRetry={() => setRetry(retry + 1)} />;
  if (!dash.data) return <Empty>No season data available.</Empty>;
  const d = dash.data;
  const indicators = seasonIndicators({ rows: d.standings ?? [], coverage, sync: league, current });
  const tabs = [...(d.standings ? [{ value: "table", label: "Table" }] : []), { value: "matches", label: "Matches" }, { value: "stats", label: "Stats" }];
  return <div className="mt-4 space-y-4">
    {comp.badge && <p className="text-xs text-mute">Prediction model coverage: <Badge badge={comp.badge} title={comp.basis} /></p>}
    <div className="flex flex-wrap gap-2">
      <Chip>{current ? "Newest stored season" : "Historical season"}</Chip>
      {coverage?.note !== "incomplete or in progress" && coverage?.expected_matches && coverage.rows_in_dataset === coverage.expected_matches ? <Chip tone="info">Expected match count present</Chip> : null}
    </div>
    {indicators.map((n) => <Notice key={n.key} tone={n.tone} title={n.label}>{n.text}</Notice>)}
    {(cov.error || sync.error) && <ErrorBox error={cov.error || sync.error} onRetry={() => setRetry(retry + 1)} />}
    {!coverage && !cov.loading && !cov.error && <Notice tone="warn">No season coverage reference is available. Completeness cannot be confirmed.</Notice>}
    {cov.loading && <p role="status" className="text-xs text-mute">Checking season coverage…</p>}
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatCard label="Stored results" value={int(d.summary.matches)} />
      <StatCard label="Goals / match" value={num(d.summary.goals_per_match, 2)} />
      <StatCard label="Home wins" value={pct(d.summary.home_win_rate)} />
      <StatCard label="Draws" value={pct(d.summary.draw_rate)} />
    </div>
    <Tabs tabs={tabs} value={tab} onChange={setTab} label="Competition sections" />
    {tab === "table" && d.standings && <Card title="League table" subtitle={`${comp.name} · ${season} · computed standings`}>
      <p className="mb-4 text-xs leading-relaxed text-mute">{TABLE_NOTE} Administrative points adjustments are not included. Clubs with no stored result are absent.</p>
      {d.standings.length ? <StandingsTable rows={d.standings} caption={`${comp.name} ${season}: computed standings, not official positions`} /> : <Empty>No verified results are available to calculate a table.</Empty>}
    </Card>}
    {tab === "matches" && (LEAGUE_KEYS.includes(comp.key) ? <ResultsFixtures comp={comp.key} season={season} /> : <SectionCard title="Recent recorded results" subtitle={`${comp.name} ${season} · newest 30 results`}>
      {d.results.length ? d.results.map((r, i) => <MatchRow key={`${r.date}-${i}`} date={r.date} label={r.stage || "FT"} home={r.home} away={r.away} homeGoals={r.home_goals} awayGoals={r.away_goals} note={r.shootout_winner ? `Penalties: ${r.shootout_winner} won` : null} />) : <Empty>No results.</Empty>}
    </SectionCard>)}
    {tab === "stats" && <SeasonStats comp={comp.key} seasons={seasons} summary={d.summary} rows={d.standings} />}
    {LEAGUE_KEYS.includes(comp.key) && <div className="flex flex-wrap gap-3">
      <ButtonLink to={`/matches?${new URLSearchParams({ comp: comp.key, season, status: "completed" })}`}>League results</ButtonLink>
      <ButtonLink to={`/matches?${new URLSearchParams({ comp: comp.key, season, status: "upcoming" })}`}>League fixtures</ButtonLink>
    </div>}
    <Card title="Data provenance" subtitle={`Selected season: ${d.summary.first_date ?? "unknown"} to ${d.summary.last_date ?? "unknown"}`}>
      <p className="mb-2 text-xs text-mute">Competition-wide source inventory; individual result sources are available in Matches. Stored data, not a live feed.</p>
      <SourceDetails sources={comp.sources} licences={comp.licences} />
    </Card>
  </div>;
}

function CompetitionSeason({ comp, requested, onSeason }) {
  const [retry, setRetry] = useState(0);
  const seasons = useApi(`/api/competitions/${comp.key}/seasons`, undefined, { retry });
  if (seasons.loading) return <Spinner label="Loading seasons…" />;
  if (seasons.error) return <ErrorBox error={seasons.error} onRetry={() => setRetry(retry + 1)} />;
  if (!seasons.data?.length) return <Empty>No stored seasons for this competition.</Empty>;
  const selected = requested || seasons.data[0];
  const valid = seasons.data.includes(selected);
  return <>
    <div className="hero mt-4 flex flex-wrap items-center gap-4 rounded-3xl p-5">
      <div className="min-w-0 flex-1"><h2 className="text-xl font-extrabold">{comp.name}</h2><p className="mt-1 text-sm">Historical results and stored season coverage</p></div>
      <label className="flex min-w-0 flex-col gap-1 text-sm font-semibold">Season
        <select aria-label="Season" value={valid ? selected : ""} onChange={(e) => onSeason(e.target.value)} className={`w-full rounded-control bg-panel-2 ${CONTROL_EDGE}`}>
          {!valid && <option value="">Choose a stored season</option>}
          {seasons.data.map((s) => <option key={s}>{s}</option>)}
        </select>
      </label>
    </div>
    {valid ? <SeasonDashboard key={`${comp.key}/${selected}`} comp={comp} season={selected} seasons={seasons.data} /> : <Notice tone="warn">The requested season is not available. Choose a stored season above.</Notice>}
  </>;
}

export default function Analytics() {
  const [params, setParams] = useSearchParams();
  const [retry, setRetry] = useState(0);
  const comps = useApi("/api/competitions", undefined, { retry });
  const key = params.get("comp") || "EPL";
  const comp = comps.data?.find((c) => c.key === key);
  const changeCompetition = (value) => setParams({ comp: value });
  const changeSeason = (season) => setParams({ comp: key, season });
  return <>
    <PageHeader title="Leagues & cups" />
    {comps.loading && <Spinner label="Loading competitions…" />}
    {comps.error && <ErrorBox error={comps.error} onRetry={() => setRetry(retry + 1)} />}
    {comps.data && <div className="space-y-4">
      <Pills label="Domestic league" value={key} onChange={changeCompetition} options={comps.data.filter((c) => LEAGUE_KEYS.includes(c.key)).map((c) => ({ value: c.key, label: c.name }))} wrap />
      <CompetitionSelect comps={comps.data} value={key} onChange={changeCompetition} />
      <CompetitionFreshness compKey={key} />
      {comp ? <CompetitionSeason key={key} comp={comp} requested={params.get("season")} onSeason={changeSeason} /> : <Notice tone="warn">Unknown competition. Choose a competition above.</Notice>}
    </div>}
  </>;
}
