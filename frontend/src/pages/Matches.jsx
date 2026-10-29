import { useRef } from "react";
import { useSearchParams } from "react-router-dom";
import PageHeader from "../components/PageHeader.jsx";
import MatchCard from "../components/matches/MatchCard.jsx";
import MatchFilters from "../components/matches/MatchFilters.jsx";
import { Button, Chip, ErrorBox, Spinner, Summary } from "../components/ui.jsx";
import { competitionFreshness, dayLabel, fullDay, groupByDate, HUB_LEAGUE } from "../lib/fixtures.js";
import { int } from "../lib/format.js";
import { useMatchPages } from "../lib/matches.js";

// Matches hub (stage P4.3, Champions League added in Phase 4.20): fixtures and results of the five domestic leagues and the Champions League, filtered by league, season, matchday, team and status, a page at a time.
// Every row is a stored match from /api/matches (bounded, indexed queries; the browser never holds the match table). Nothing is forecast here, kickoffs are shown as stored
// with their time zone marked unconfirmed when it is, and "live" does not exist: the data is historical and synchronised periodically.

const STATUSES = ["upcoming", "awaiting_result", "completed", "other", "all"];
const LEAGUES = Object.keys(HUB_LEAGUE);
const TEAM_ID = /^[A-Za-z0-9:_.-]{3,120}$/;
const WHAT = { upcoming: "upcoming matches", awaiting_result: "matches awaiting a result", completed: "completed matches", other: "postponed or cancelled matches", all: "matches" };

function readFilters(params) {
  const comp = LEAGUES.includes(params.get("comp")) ? params.get("comp") : "";
  const season = /^\d{4}-\d{2}$/.test(params.get("season") ?? "") ? params.get("season") : "";
  const md = Number(params.get("matchday"));
  const matchday = Number.isInteger(md) && md >= 1 && md <= 60 ? String(md) : "";
  const status = STATUSES.includes(params.get("status")) ? params.get("status") : "upcoming";
  const team = comp && TEAM_ID.test(params.get("team") ?? "") ? params.get("team") : "";
  return { comp, season, matchday, team, status };
}

function Freshness({ freshness, comp }) {
  const entries = Object.entries(freshness.competitions).filter(([k]) => !comp || k === comp);
  const stale = entries.filter(([, c]) => c.state !== "fresh").length;
  const one = entries.length === 1 ? competitionFreshness(entries[0][0], entries[0][1]) : null;
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        {one ? <Chip tone={one.tone}>{one.text}</Chip> : stale === 0 ? <Chip tone="ok">{`Data fresh in all ${entries.length} competitions`}</Chip> : null}
        <span className="text-xs text-mute">Historical data, synchronised periodically. Nothing here is live.</span>
      </div>
      {!one && stale === 0 && (
        <details className="group">
          <Summary>Data freshness by competition</Summary>
          <ul className="space-y-1 pb-2 pl-5 text-xs text-ink-2">
            {entries.map(([k, c]) => (
              <li key={k}>
                <span className="font-semibold text-ink">{HUB_LEAGUE[k]}</span> · {competitionFreshness(k, c)?.text}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

export default function Matches() {
  const [params, setParams] = useSearchParams();
  const f = readFilters(params);
  const m = useMatchPages({ comp: f.comp || undefined, season: f.season || undefined, matchday: f.matchday || undefined, team: f.team || undefined, status: f.status });
  const stable = useRef({ facets: null, counts: null }); // the filter controls keep their options while a new selection loads
  if (m.first) stable.current = { facets: m.first.facets, counts: m.counts };
  const change = (patch) =>
    setParams((p) => {
      const q = new URLSearchParams(p);
      for (const [k, v] of Object.entries(patch)) {
        if (v && !(k === "status" && v === "upcoming")) q.set(k, v);
        else q.delete(k);
      }
      return q;
    });
  const reset = () => setParams(new URLSearchParams());

  const today = m.first?.today_utc;
  const total = m.counts?.[f.status] ?? 0;
  const groups = groupByDate(m.items);
  const heading = (d) => {
    const rel = dayLabel(d, today);
    return rel === "Today" || rel === "Tomorrow" ? `${rel} · ${fullDay(d)}` : fullDay(d);
  };
  const otherCount = m.counts ? m.counts.all - total : 0;

  return (
    <div className="space-y-5">
      <PageHeader title="Matches">Fixtures and results of the five domestic leagues and the Champions League, from the stored results.</PageHeader>
      <MatchFilters {...f} facets={stable.current.facets} counts={stable.current.counts} onChange={change} />

      {m.first && <Freshness freshness={m.first.freshness} comp={m.first.scope.competitions.length === 1 ? m.first.scope.competitions[0] : ""} />}

      <section aria-labelledby="matches-results" aria-busy={m.loading}>
        <h2 id="matches-results" className="sr-only">
          Matches
        </h2>
        {m.loading && <Spinner label="Loading matches…" />}
        {m.error && <ErrorBox error={m.error} onRetry={m.retry} />}
        {m.error && (
          <div className="mt-3">
            <Button variant="secondary" onClick={reset}>
              Reset filters
            </Button>
          </div>
        )}

        {m.first && (
          <p role="status" className="mb-3 text-sm text-ink-2">
            Showing {int(m.items.length)} of {int(total)} {WHAT[f.status]} · {f.comp ? HUB_LEAGUE[f.comp] : "all six competitions"} · {f.season ? `season ${f.season}` : "newest season"}
            {f.matchday ? ` · matchday ${f.matchday}` : ""}
            {f.team ? ` · ${m.first.facets.teams?.find((t) => t.entity === f.team)?.name ?? "one team"}` : ""}
          </p>
        )}

        {m.first && m.items.length === 0 && (
          <div className="rounded-card border border-dashed border-line-strong px-4 py-8 text-center">
            <p className="text-sm text-ink">No {WHAT[f.status]} for this selection.</p>
            {otherCount > 0 && <p className="mt-1 text-xs text-mute">The same selection has {int(otherCount)} matches in other statuses; choose All to see them.</p>}
            <div className="mt-4 flex justify-center gap-2">
              {otherCount > 0 && f.status !== "all" && (
                <Button variant="secondary" onClick={() => change({ status: "all" })}>
                  Show all statuses
                </Button>
              )}
              <Button variant="secondary" onClick={reset}>
                Reset filters
              </Button>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {groups.map((g) => (
            <div key={g.date}>
              <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wide text-mute">{heading(g.date)}</h3>
              {g.date === today && g.items.some((i) => i.timing?.ambiguous) && (
                <p className="mb-2 text-xs leading-relaxed text-ink-2">
                  Some matches today have no verified kickoff time zone (or no time), so it cannot be known whether they have started. Times are shown exactly as stored and are never converted.
                </p>
              )}
              <ul className="divide-y divide-line/70 overflow-hidden rounded-card border border-line bg-panel shadow-card">
                {g.items.map((x) => (
                  <MatchCard key={x.record_id} m={x} showLeague={!f.comp} />
                ))}
              </ul>
            </div>
          ))}
        </div>

        {m.first && m.items.length > 0 && (
          <div className="mt-5 flex flex-col items-center gap-2">
            <p className="text-xs text-mute">
              {int(m.items.length)} of {int(total)} shown
            </p>
            {m.hasMore && (
              <Button variant="secondary" onClick={m.loadMore} disabled={m.more.loading}>
                {m.more.loading ? "Loading…" : "Show more matches"}
              </Button>
            )}
            {m.more.error && <ErrorBox error={m.more.error} onRetry={m.loadMore} />}
          </div>
        )}
      </section>
    </div>
  );
}
