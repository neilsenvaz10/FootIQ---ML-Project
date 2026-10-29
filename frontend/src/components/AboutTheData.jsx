import { Link } from "react-router-dom";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "../lib/hooks.js";
import { int } from "../lib/format.js";
import { groupCompetitions } from "../lib/competitions.js";
import { axisProps, COLORS, tooltipStyle } from "../lib/chart.js";
import { useMeta } from "./MetaContext.jsx";
import SourceDetails from "./SourceDetails.jsx";
import { Badge, Card, ErrorBox, Icon, SectionCard, Spinner, TeamAvatar } from "./ui.jsx";

// "About the data" (moved from the old Home page, stage P4.2): what the dataset covers and how each competition is validated.
// The data and behaviour are unchanged: the same /api/competitions response, the same two charts, the same competition cards with their sources.

const SHORT = { EPL: "Premier L.", LALIGA: "La Liga", BUNDESLIGA: "Bundesliga", SERIEA: "Serie A", LIGUE1: "Ligue 1", UCL: "Champions L." };
const TONE = { Validated: COLORS.ok, "Partially validated": COLORS.draw, "Not validated (indicative only)": COLORS.loss };

function CompetitionCard({ c }) {
  return (
    <div className="min-w-0 border-t border-line/70 px-4 py-3">
      <Link to={`/analytics?comp=${c.key}`} className="flex min-h-11 items-center gap-3">
        <TeamAvatar name={c.name} size={36} />
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-bold leading-tight">{c.name}</h3>
          <p className="truncate text-xs text-mute">
            {int(c.rows)} matches · {c.seasons} seasons · to {c.last_date}
          </p>
        </div>
        <Icon name="chevron" className="h-5 w-5 shrink-0 text-mute" />
      </Link>
      <div className="mt-2 flex flex-wrap items-center gap-2 pl-12">
        <Badge badge={c.badge} title={c.basis} />
        <Link className="inline-flex min-h-11 items-center rounded-full bg-panel-2 px-4 text-xs font-semibold text-accent hover:bg-panel-3" to={`/predict?comp=${c.key}`}>
          Predict
        </Link>
      </div>
      <div className="mt-2 pl-12">
        <SourceDetails sources={c.sources} licences={c.licences} />
      </div>
    </div>
  );
}

export default function AboutTheData() {
  const { data: comps, loading, error } = useApi("/api/competitions");
  const meta = useMeta();
  return (
    <section aria-labelledby="about-data-title" className="mt-10">
      <h2 id="about-data-title" className="text-xl font-extrabold tracking-tight">
        About the data
      </h2>
      {loading && <Spinner label="Loading competitions…" />}
      {error && (
        <div className="mt-3">
          <ErrorBox error={error} />
        </div>
      )}
      {comps && <Body comps={comps} through={meta.data?.data_through.club_results} />}
    </section>
  );
}

function Body({ comps, through }) {
  const total = comps.reduce((s, c) => s + c.rows, 0);
  const matchesChart = [...comps].sort((a, b) => b.rows - a.rows).map((c) => ({ name: SHORT[c.key] ?? c.name, rows: c.rows }));
  const counts = comps.reduce((m, c) => ({ ...m, [c.badge]: (m[c.badge] ?? 0) + 1 }), {});
  const pie = Object.entries(counts).map(([name, value]) => ({ name, value, fill: TONE[name] ?? COLORS.draw }));
  return (
    <>
      <p className="mt-1 max-w-2xl text-sm text-mute">
        {comps.length} competitions, {int(total)} matches, data through {through ?? "…"}. Historical results only; the validation badge says how far each competition's predictions can be trusted.
      </p>

      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <Card title="Matches by competition" subtitle="Rows in the historical dataset" className="lg:col-span-3">
          <div className="h-72" role="img" aria-label="Bar chart of the number of stored matches per competition; the same figures are listed in the competition cards below">
            <ResponsiveContainer>
              <BarChart data={matchesChart} layout="vertical" margin={{ left: 0, right: 12 }}>
                <XAxis type="number" {...axisProps} tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : v)} />
                <YAxis type="category" dataKey="name" width={104} {...axisProps} interval={0} />
                <Tooltip {...tooltipStyle} cursor={{ fill: "var(--color-panel-2)" }} formatter={(v) => int(v)} />
                <Bar dataKey="rows" name="Matches" fill={COLORS.pitch} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Prediction validation" subtitle="Competitions by status" className="lg:col-span-2">
          <div className="h-44" role="img" aria-label={`Donut chart of competitions by validation status: ${pie.map((p) => `${p.name} ${p.value}`).join(", ")}`}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={pie} dataKey="value" nameKey="name" innerRadius={42} outerRadius={70} paddingAngle={3} stroke="none">
                  {pie.map((p) => (
                    <Cell key={p.name} fill={p.fill} />
                  ))}
                </Pie>
                <Tooltip {...tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-2 space-y-1 text-xs">
            {pie.map((p) => (
              <li key={p.name} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: p.fill }} aria-hidden="true" />
                <span className="flex-1">{p.name}</span>
                <span className="font-bold tabular-nums">{p.value}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="mt-4 space-y-4">
        {groupCompetitions(comps).map((g) => (
          <SectionCard key={g.label} title={g.label} subtitle={`${g.items.length} competitions`}>
            <div className="grid sm:grid-cols-2 sm:gap-x-2">
              {g.items.map((c) => (
                <CompetitionCard key={c.key} c={c} />
              ))}
            </div>
          </SectionCard>
        ))}
      </div>
    </>
  );
}
