import { Link } from "react-router-dom";
import { Card, Chip, Empty, MatchRow, Notice, TeamCrest } from "../ui.jsx";
import Kickoff from "../Kickoff.jsx";
import { dayLabel, gameweekLink, groupByDate, isProvisional, SHORT_LEAGUE } from "../../lib/fixtures.js";

// Upcoming fixtures and latest verified results of the five domestic leagues, from /api/featured-fixture. Every row is a stored match; nothing is added.

const LINK = "inline-flex min-h-11 items-center text-xs font-semibold text-accent hover:text-ink";

function Teams({ f }) {
  return (
    <span className="flex min-w-0 flex-col gap-1.5">
      {[f.home, f.away].map((t, i) => (
        <span key={i} className="flex min-w-0 items-center gap-2">
          <TeamCrest name={t.name} size={24} />
          <span className="truncate text-sm font-semibold">{t.name}</span>
          {i === 0 && <span className="sr-only">versus</span>}
        </span>
      ))}
    </span>
  );
}

function FixtureRow({ f, showProvisional }) {
  const provisional = showProvisional && isProvisional(f);
  const unmatched = !f.home.resolved || !f.away.resolved;
  return (
    <li>
      <Link to={gameweekLink(f)} className="grid min-h-14 grid-cols-[4.75rem_minmax(0,1fr)] items-center gap-x-3 gap-y-1.5 rounded-xl px-2 py-2.5 hover:bg-panel-2 sm:grid-cols-[6rem_minmax(0,1fr)_auto]">
        <Kickoff k={f.kickoff} />
        <Teams f={f} />
        <span className="col-span-2 flex flex-wrap items-center gap-1.5 sm:col-span-1 sm:justify-end">
          <Chip>{SHORT_LEAGUE[f.competition_key] ?? f.competition}</Chip>
          {provisional && <Chip tone="warn">Provisional</Chip>}
          {unmatched && <Chip>Club not matched</Chip>}
        </span>
      </Link>
    </li>
  );
}

export function UpcomingFixtures({ data, limit = 6 }) {
  const items = data.upcoming.slice(0, limit);
  const lead = data.featured ?? items[0];
  const allProvisional = items.length > 0 && items.every(isProvisional); // say it once instead of on every row
  return (
    <Card
      title="Next fixtures"
      subtitle="Scheduled, from the five domestic leagues"
      right={
        lead && (
          <Link to={gameweekLink(lead)} className={LINK}>
            Gameweek predictions →
          </Link>
        )
      }
    >
      {items.length === 0 ? (
        <Empty>No further scheduled fixtures are stored.</Empty>
      ) : (
        <div className="space-y-3">
          {allProvisional && (
            <Notice tone="warn" title="Provisional.">
              The stored history behind every fixture below is stale or has gaps. Open one to see why; a forecast for it would be provisional.
            </Notice>
          )}
          {groupByDate(items).map((g) => (
            <div key={g.date}>
              <h3 className="mb-1 text-xs font-bold uppercase tracking-wide text-mute">{dayLabel(g.date, data.today_utc)}</h3>
              <ul>
                {g.items.map((f) => (
                  <FixtureRow key={f.record_id} f={f} showProvisional={!allProvisional} />
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function RecentResults({ data, limit = 6 }) {
  const items = data.recent_results.slice(0, limit);
  return (
    <Card title="Latest verified results" subtitle="Final scores in the stored data">
      {items.length === 0 ? (
        <Empty>No verified results are stored for these leagues yet.</Empty>
      ) : (
        <ul className="-mx-4 -mb-4 sm:-mx-5 sm:-mb-5 md:grid md:grid-cols-2 xl:grid-cols-3">
          {items.map((r) => (
            <li key={r.record_id}>
              <MatchRow date={r.date} label={r.status === "awarded" ? "AWD" : "FT"} home={r.home.name} away={r.away.name} homeGoals={r.home_goals} awayGoals={r.away_goals} note={SHORT_LEAGUE[r.competition_key] ?? r.competition} />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
