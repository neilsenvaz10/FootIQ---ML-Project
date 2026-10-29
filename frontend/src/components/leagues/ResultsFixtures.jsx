import { Link } from "react-router-dom";
import { useApi } from "../../lib/hooks.js";
import Kickoff from "../Kickoff.jsx";
import { Card, Empty, ErrorBox, MatchRow, Spinner, TeamCrest } from "../ui.jsx";
import { dayLabel, shortDay } from "../../lib/fixtures.js";

// Latest verified results and next scheduled fixtures of a league season, from /api/matches (bounded, indexed, read-only). Nothing is computed here.
const SHOWN = 8;

function More({ comp, season, status, children }) {
  const q = new URLSearchParams({ comp, status });
  if (season) q.set("season", season);
  return (
    <Link to={`/matches?${q.toString()}`} className="inline-flex min-h-11 items-center text-xs font-semibold text-accent hover:text-ink">
      {children} →
    </Link>
  );
}

export default function ResultsFixtures({ comp, season }) {
  const done = useApi("/api/matches", { comp, season, status: "completed", limit: SHOWN });
  const next = useApi("/api/matches", { comp, season, status: "upcoming", limit: SHOWN });
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Latest verified results" subtitle={season ? `Season ${season}, newest first` : "Newest first"} right={<More comp={comp} season={season} status="completed">All results</More>}>
        {done.loading && <Spinner label="Loading results…" />}
        {done.error && <ErrorBox error={done.error} />}
        {done.data && done.data.items.length === 0 && <Empty>No verified result is stored for this season.</Empty>}
        {done.data && done.data.items.length > 0 && (
          <ul className="-mx-4 -mb-4 sm:-mx-5 sm:-mb-5">
            {done.data.items.map((m) => (
              <li key={m.record_id}>
                <MatchRow date={m.date} label={m.status === "awarded" ? "AWD" : "FT"} home={m.home.name} away={m.away.name} homeGoals={m.result?.home_goals} awayGoals={m.result?.away_goals} note={[m.matchday_label, m.result?.source || m.source].filter(Boolean).join(" · ")} />
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card title="Next fixtures" subtitle="Scheduled, kickoff as stored" right={<More comp={comp} season={season} status="upcoming">All fixtures</More>}>
        {next.loading && <Spinner label="Loading fixtures…" />}
        {next.error && <ErrorBox error={next.error} />}
        {next.data && next.data.items.length === 0 && <Empty>No scheduled fixture is stored for this season.</Empty>}
        {next.data && next.data.items.length > 0 && (
          <ul className="divide-y divide-line/70">
            {next.data.items.map((m) => (
              <li key={m.record_id} className="grid grid-cols-[6.5rem_minmax(0,1fr)] items-center gap-3 py-2.5">
                <span className="text-xs">
                  <span className="block font-semibold text-ink-2">{dayLabel(m.date, next.data.today_utc) === shortDay(m.date) ? shortDay(m.date) : dayLabel(m.date, next.data.today_utc)}</span>
                  <Kickoff k={m.kickoff} />
                  {m.timing?.ambiguous && <span className="block text-warn">{m.timing.note}</span>}
                </span>
                <span className="flex min-w-0 flex-col gap-1.5">
                  {[m.home, m.away].map((t, i) => (
                    <span key={i} className="flex min-w-0 items-center gap-2">
                      <TeamCrest name={t.name} size={24} />
                      <span className="truncate text-sm font-semibold">{t.name}</span>
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
