import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "../lib/hooks.js";
import { int, pct } from "../lib/format.js";
import { axisProps, COLORS, tooltipStyle } from "../lib/chart.js";
import AboutTheData from "../components/AboutTheData.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { Badge, Card, DataTable, ErrorBox, Kpi, Notice, Spinner, Summary, Tabs } from "../components/ui.jsx";

const f3 = (x) => x.toFixed(3);

function ModelTable({ models, highlight }) {
  return (
    <DataTable
      columns={[
        { header: "Model", key: "label", render: (m) => <span className={m.model === highlight ? "font-bold text-pitch" : ""}>{m.label}</span> },
        { header: "Accuracy", key: "accuracy", num: true, render: (m) => pct(m.accuracy) },
        { header: "Log loss", key: "log_loss", num: true, render: (m) => f3(m.log_loss) },
        { header: "Brier", key: "brier", num: true, render: (m) => f3(m.brier) },
      ]}
      rows={models}
    />
  );
}

export default function Models() {
  const { data: p, loading, error } = useApi("/api/models/performance");
  const [set, setSet] = useState("0");
  if (loading) return <Spinner label="Loading evaluation results…" />;
  if (error) return <ErrorBox error={error} />;

  const v1 = p.club_v1;
  const ev = v1.evaluation[Number(set)];
  const v1Test = v1.evaluation[0].models.find((m) => m.model === "multinomial_logreg");
  const leagueChart = v1.per_league.map((l) => ({ name: l.competition.replace("English ", "").replace("Premier League", "Premier L."), Test: +(l.test.accuracy * 100).toFixed(1), "Forward holdout": +(l.forward_holdout.accuracy * 100).toFixed(1) }));
  const v2 = p.club_v2_r1.development;

  return (
    <>
      <PageHeader title="Model performance">Evaluation results the project already produced, read from its report files. Nothing is retrained or recomputed here.</PageHeader>

      <div className="grid grid-cols-2 gap-2.5">
        <Kpi label="Club v1 accuracy (test season)" value={pct(v1Test.accuracy)} hint={`${int(v1Test.n)} matches, 3 outcomes`} />
        <Kpi label="Club v2-r1" value="Dev only" hint="no unbiased test" />
      </div>

      <div className="mt-4 space-y-4">
        <Notice tone="warn" title="Read these as history.">
          {p.caveats[0]} {p.caveats[1]}
        </Notice>

        <Card title="Club v1" subtitle={v1.role} right={<Badge badge="Validated" title={v1.status} />}>
          <Tabs tabs={v1.evaluation.map((e, i) => ({ value: String(i), label: i === 0 ? "Test season" : "Forward holdout" }))} value={set} onChange={setSet} label="Evaluation set" />
          <p className="mb-2 mt-3 text-xs text-mute">
            {ev.period} · {int(ev.n)} matches across all domestic leagues
          </p>
          <ModelTable models={ev.models} highlight="multinomial_logreg" />
          <p className="mt-3 text-xs text-mute">{v1.notes[1]}</p>
        </Card>

        <Card title="Club v1 in the five leagues" subtitle="Accuracy by league (about 300–450 matches each, so differences between leagues are noisy)">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={leagueChart} margin={{ left: -15, right: 8, top: 8 }}>
                <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" />
                <XAxis dataKey="name" {...axisProps} />
                <YAxis {...axisProps} unit="%" domain={[30, 60]} />
                <Tooltip {...tooltipStyle} cursor={{ fill: "#181830" }} formatter={(v) => `${v}%`} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Test" fill={COLORS.pitch} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Forward holdout" fill={COLORS.home} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3">
            <DataTable
              columns={[
                { header: "League", key: "competition" },
                { header: "Test n", key: "tn", num: true, render: (l) => l.test.n },
                { header: "Acc.", key: "ta", num: true, render: (l) => pct(l.test.accuracy) },
                { header: "Log loss", key: "tl", num: true, render: (l) => f3(l.test.log_loss) },
                { header: "Holdout n", key: "hn", num: true, render: (l) => l.forward_holdout.n },
                { header: "Acc.", key: "ha", num: true, render: (l) => pct(l.forward_holdout.accuracy) },
                { header: "Log loss", key: "hl", num: true, render: (l) => f3(l.forward_holdout.log_loss) },
              ]}
              rows={v1.per_league}
            />
          </div>
          <p className="mt-2 text-xs text-mute">Always predicting a home win scores a log loss of about 1.07–1.09 in these leagues; lower is better.</p>
        </Card>

        <Card title="Club v2-r1 (candidate)" subtitle={p.club_v2_r1.role} right={<Badge badge="Partially validated" title={p.club_v2_r1.status} />}>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            <Kpi label="Accuracy (dev folds)" value={pct(v2.accuracy)} hint={`${int(v2.n)} matches`} />
            <Kpi label="Log loss v2" value={f3(v2.log_loss_v2)} />
            <Kpi label="Log loss v1" value={f3(v2.log_loss_v1_lr)} />
            <Kpi label="Difference" value={v2.delta_vs_v1_lr.toFixed(4)} hint="log loss, lower is better" />
          </div>
          <p className="mt-3 text-xs text-mute">{v2.period}.</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-[13px] text-mute">
            {p.club_v2_r1.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </Card>

        <Notice tone="bad" title="The UEFA Champions League is not validated.">
          {p.uefa_club.note}
        </Notice>

        <Card title="How to read this">
          <ul className="list-disc space-y-1 pl-5 text-[13px] text-mute">
            <li>
              <strong className="text-ink">Accuracy</strong> is how often the single most likely outcome was right. With three outcomes (home, draw, away), a coin-flip baseline is about 33–43%.
            </li>
            <li>
              <strong className="text-ink">Log loss</strong> scores the probabilities themselves; lower is better and it rewards honest uncertainty.
            </li>
            <li>
              <strong className="text-ink">Brier</strong> is the squared error of the probabilities; lower is better.
            </li>
            {p.caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          <details className="group mt-3 text-xs text-mute">
            <Summary>Evaluation files used</Summary>
            <ul className="mt-1 list-disc space-y-0.5 pl-5">
              {p.sources.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </details>
        </Card>
      </div>

      <AboutTheData />
    </>
  );
}
