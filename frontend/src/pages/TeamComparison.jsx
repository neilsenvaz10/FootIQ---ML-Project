import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useApi } from "../lib/hooks.js";
import { COLORS } from "../lib/chart.js";
import CompetitionSelect from "../components/CompetitionSelect.jsx";
import CompetitionFreshness from "../components/CompetitionFreshness.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { TeamPoolFilter, useTeamPool } from "../components/TeamPool.jsx";
import { Card, CompareRow, Empty, ErrorBox, FormChips, Kpi, MatchRow, Notice, SectionCard, Select, Spinner, TeamAvatar } from "../components/ui.jsx";

// Totals over the "last" array returned by the API (simple sums of fields the backend already provides).
function summarize(form) {
  const t = { W: 0, D: 0, L: 0, gf: 0, ga: 0 };
  for (const m of form.last) {
    t[m.result] += 1;
    t.gf += m.gf;
    t.ga += m.ga;
  }
  return t;
}

function FormCard({ form }) {
  const s = summarize(form);
  return (
    <Card title={form.team} right={<TeamAvatar name={form.team} size={30} />}>
      {form.played === 0 ? (
        <Empty>No matches for this team in the dataset.</Empty>
      ) : (
        <>
          <FormChips results={form.last} />
          <p className="mt-1.5 text-xs text-mute">Last {form.played} matches in this competition, oldest first. Hover a chip for details.</p>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Kpi label="Points (last 10)" value={form.points} />
            <Kpi label="W-D-L" value={`${s.W}-${s.D}-${s.L}`} />
            <Kpi label="Goals for" value={s.gf} />
            <Kpi label="Goals against" value={s.ga} />
          </div>
        </>
      )}
    </Card>
  );
}

function Slot({ label, name, children }) {
  return (
    <div className="min-w-0 flex-1 rounded-2xl bg-panel p-3 text-center">
      <div className="mb-2 flex justify-center">{name ? <TeamAvatar name={name} size={48} /> : <span className="grid h-12 w-12 place-items-center rounded-full border border-dashed border-line text-mute">?</span>}</div>
      <span className="mb-1 block text-xs font-medium text-mute">{label}</span>
      {children}
    </div>
  );
}

export default function TeamComparison() {
  const comps = useApi("/api/competitions");
  const [params] = useSearchParams();
  const [key, setKey] = useState(params.get("comp") || "EPL");
  const [poolChoice, setPoolChoice] = useState("");
  const pool = useTeamPool(key, poolChoice);
  const teams = pool.teams;
  const [a, setA] = useState(params.get("a") ?? "");
  const [b, setB] = useState(params.get("b") ?? "");
  const preselected = useRef(Boolean(params.get("a") || params.get("b")));
  useEffect(() => {
    if (preselected.current) {
      preselected.current = false; // clubs chosen by a link from the Matches page stay selected on first load
      return;
    }
    setA("");
    setB("");
    setPoolChoice("");
  }, [key]);

  const same = a && a === b;
  const ready = a && b && !same;
  const main = useApi(ready ? "/api/team" : null, { key, team: a, opponent: b });
  const other = useApi(ready ? "/api/team" : null, { key, team: b });

  const f = main.data?.form;
  const g = other.data?.form;
  const h2h = main.data?.head_to_head;
  const opts = (exclude) => (teams.data ?? []).filter((t) => t !== exclude);
  return (
    <>
      <PageHeader title="Compare teams">Recent form and head-to-head for two teams in one competition. Club names use each club's most recent spelling; the backend matches clubs by id, so older spellings are handled.</PageHeader>
      <CompetitionSelect comps={comps.data} value={key} onChange={setKey} />
      <CompetitionFreshness compKey={key} />
      <TeamPoolFilter pool={pool} onChange={(v) => { setPoolChoice(v); setA(""); setB(""); }} />

      <div className="mt-4 flex gap-3">
        <Slot label="Team A" name={a}>
          <Select value={a} onChange={setA} options={opts(b)} placeholder="Select" disabled={!teams.data} aria-label="Team A" />
        </Slot>
        <div className="grid shrink-0 place-items-center text-xs font-extrabold text-mute">VS</div>
        <Slot label="Team B" name={b}>
          <Select value={b} onChange={setB} options={opts(a)} placeholder="Select" disabled={!teams.data} aria-label="Team B" />
        </Slot>
      </div>
      {(comps.error || teams.error) && <div className="mt-3"><ErrorBox error={comps.error || teams.error} /></div>}
      {same && <div className="mt-3"><Notice tone="warn">Choose two different teams.</Notice></div>}

      <div className="mt-4 space-y-4">
        {!ready && !same && <Empty>Select two teams to compare.</Empty>}
        {ready && (main.loading || other.loading) && <Spinner label="Loading comparison…" />}
        {(main.error || other.error) && <ErrorBox error={main.error || other.error} />}

        {f && g && h2h && (
          <>
            <Card title="Head-to-head" subtitle={`Meetings in this competition's dataset: ${h2h.meetings}. Scores are the recorded scores.`}>
              {h2h.meetings === 0 ? (
                <Empty>These teams have not met in this competition in the dataset.</Empty>
              ) : (
                <>
                  <div className="grid grid-cols-3 text-center">
                    <div><div className="text-3xl font-extrabold text-home">{h2h.a_wins}</div><div className="truncate text-xs text-mute">{a} wins</div></div>
                    <div><div className="text-3xl font-extrabold text-draw">{h2h.draws}</div><div className="text-xs text-mute">Draws</div></div>
                    <div><div className="text-3xl font-extrabold text-away">{h2h.b_wins}</div><div className="truncate text-xs text-mute">{b} wins</div></div>
                  </div>
                  <div className="mt-3 flex h-2 overflow-hidden rounded-full" role="img" aria-label={`${a} ${h2h.a_wins} wins, ${h2h.draws} draws, ${b} ${h2h.b_wins} wins`}>
                    <div style={{ width: `${(h2h.a_wins / h2h.meetings) * 100}%`, background: COLORS.home }} />
                    <div style={{ width: `${(h2h.draws / h2h.meetings) * 100}%`, background: COLORS.draw }} />
                    <div style={{ width: `${(h2h.b_wins / h2h.meetings) * 100}%`, background: COLORS.away }} />
                  </div>
                </>
              )}
            </Card>
            {h2h.meetings > 0 && (
              <SectionCard title="Previous meetings" subtitle={h2h.meetings > h2h.last.length ? `Showing the ${h2h.last.length} most recent of ${h2h.meetings}` : undefined}>
                {h2h.last.map((r, i) => (
                  <MatchRow key={`${r.date}-${i}`} date={r.date} label={r.season} home={r.home} away={r.away} homeGoals={r.home_goals} awayGoals={r.away_goals} />
                ))}
              </SectionCard>
            )}
            <Card title="Head to head: recent form" subtitle={`Last 10 matches each in this competition (${f.team} vs ${g.team})`}>
              {(() => {
                const sa = summarize(f);
                const sb = summarize(g);
                const pa = f.played || 1;
                const pb = g.played || 1;
                const A = "#8b7bff";
                const B = "#2dd4bf";
                const rows = [
                  ["Points", f.points, g.points, (v) => v, true],
                  ["Wins", sa.W, sb.W, (v) => v, true],
                  ["Draws", sa.D, sb.D, (v) => v, true],
                  ["Losses", sa.L, sb.L, (v) => v, false],
                  ["Goals scored per game", sa.gf / pa, sb.gf / pb, (v) => v.toFixed(1), true],
                  ["Goals conceded per game", sa.ga / pa, sb.ga / pb, (v) => v.toFixed(1), false],
                ];
                return (
                  <>
                    <div className="mb-2 grid grid-cols-[1fr_auto_1fr] items-center gap-2">
                      <div className="min-w-0"><FormChips results={f.last} /></div>
                      <span className="text-xs font-semibold text-mute">FORM</span>
                      <div className="flex min-w-0 justify-end"><FormChips results={g.last} /></div>
                    </div>
                    {rows.map(([label, l, r, fmt, hib]) => (
                      <CompareRow key={label} label={label} left={l} right={r} format={fmt} higherIsBetter={hib} leftColor={A} rightColor={B} />
                    ))}
                  </>
                );
              })()}
            </Card>
            <div className="grid gap-4 md:grid-cols-2">
              <FormCard form={f} />
              <FormCard form={g} />
            </div>
          </>
        )}
      </div>
    </>
  );
}
