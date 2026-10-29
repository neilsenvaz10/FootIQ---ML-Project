import { useState } from "react";
import { Link } from "react-router-dom";
import { Chip, TeamCrest } from "../ui.jsx";
import Kickoff from "../Kickoff.jsx";
import { compareLink, gameweekLink, HUB_LEAGUE, manualLink, MATCH_STATUS, timingChip } from "../../lib/fixtures.js";

// One match of the Matches hub: when (or the final score), both clubs, what is known and unknown about it, and where to go next.
// Everything shown is a stored value or a flag from /api/matches; nothing is computed here and no forecast is made.

const ACTION = "inline-flex min-h-11 items-center rounded-full px-3 text-xs font-semibold text-accent hover:bg-panel-3 hover:text-ink";

function Side({ team, goals, win, lose }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <TeamCrest name={team.name} size={28} />
      <span className={`min-w-0 flex-1 truncate text-sm ${win ? "font-extrabold text-ink" : lose ? "text-mute" : "font-semibold text-ink"}`} title={team.name}>
        {team.name}
      </span>
      {goals != null && <span className={`w-7 shrink-0 text-right text-base tabular-nums ${win ? "font-extrabold text-ink" : lose ? "text-mute" : "font-bold text-ink"}`}>{goals}</span>}
    </div>
  );
}

function Details({ m, finished }) {
  const rows = [
    ["Competition", `${m.competition} · season ${m.season}`],
    ["Stage", m.matchday_label ?? "not stated"],
    ["Date", m.date],
    ["Result", finished ? (m.result ? `${m.home.name} ${m.result.home_goals}-${m.result.away_goals} ${m.away.name} (final score, penalties excluded)` : "not stored") : "not played yet"],
    ["Source", m.source || "not stated"],
    ...(m.validation_badge ? [["Predictions", m.validation_badge]] : []),
  ];
  return (
    <dl className="mt-1 grid gap-x-3 gap-y-1 text-xs sm:grid-cols-[7rem_minmax(0,1fr)]">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="font-semibold text-mute">{k}</dt>
          <dd className="text-ink-2">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function MatchCard({ m, showLeague }) {
  const [open, setOpen] = useState(false);
  const unvalidated = Boolean(m.validation_badge?.startsWith("Not validated"));
  const finished = m.status === "completed" || m.status === "awarded";
  const unplayed = m.status === "scheduled" || m.status === "awaiting_result";
  const [statusLabel, statusTone] = MATCH_STATUS[m.status] ?? [m.status, "neutral"];
  const when = timingChip(m.timing);
  const provisional = m.eligibility?.reliability === "provisional";
  const resolved = m.home.resolved && m.away.resolved;
  const hg = m.result?.home_goals;
  const ag = m.result?.away_goals;
  const name = `${m.home.name} v ${m.away.name}`;
  return (
    <li>
      <article aria-label={name} className="grid gap-x-4 gap-y-2.5 px-3 py-3.5 sm:grid-cols-[6.5rem_minmax(0,1fr)_15rem] sm:px-4">
        <div>
          {finished ? <span className="block text-xs font-semibold text-ink-2">{m.status === "awarded" ? "Awarded" : "Full time"}</span> : <Kickoff k={m.kickoff} />}
        </div>

        <div className="min-w-0 space-y-2">
          <Side team={m.home} goals={hg} win={hg > ag} lose={hg < ag} />
          <Side team={m.away} goals={ag} win={ag > hg} lose={ag < hg} />
          {finished && !m.result && <p className="text-xs text-mute">Final score not stored for this match.</p>}
          {finished && m.result && (
            <span className="sr-only">
              Final score: {m.home.name} {hg}, {m.away.name} {ag}.
            </span>
          )}
          {m.timing?.ambiguous && <span className="sr-only">{m.timing.note}</span>}
        </div>

        <div className="flex min-w-0 flex-col gap-1.5 sm:items-end">
          <div className="flex flex-wrap gap-1.5 sm:justify-end">
            {showLeague && <Chip>{HUB_LEAGUE[m.competition_key] ?? m.competition}</Chip>}
            {m.matchday_label && <Chip>{m.matchday_label}</Chip>}
            {!finished && <Chip tone={statusTone}>{statusLabel}</Chip>}
            {when && <Chip tone={when[1]}>{when[0]}</Chip>}
            {unplayed && provisional && (
              <Chip tone="warn" title="The stored history behind this match is stale or has gaps">
                Provisional history
              </Chip>
            )}
            {unvalidated && !finished && <Chip tone="warn" title="The club models were evaluated on domestic leagues only">Predictions: {m.validation_badge}</Chip>}
            {!resolved && <Chip>Club not matched</Chip>}
            {m.saved_forecast_runs > 0 && <Chip tone="info">Gameweek forecast saved</Chip>}
            <Chip title="Where this row comes from in the results store">Source: {m.source || "not stated"}</Chip>
          </div>
          {resolved && (
            <div role="group" aria-label={`Next steps for ${name}`} className="-mx-1 flex flex-wrap sm:justify-end">
              {m.competition_key !== "UCL" && (
                <Link to={gameweekLink(m, { season: true })} className={ACTION} aria-label={`Gameweek ${m.matchday_no ?? ""} predictions and forecast history: ${name}`.replace("  ", " ")}>
                  Gameweek
                </Link>
              )}
              {unplayed && (
                <Link to={manualLink(m)} className={ACTION} aria-label={`Predict ${name} manually`}>
                  Predict match
                </Link>
              )}
              <Link to={compareLink(m)} className={ACTION} aria-label={`Compare ${m.home.name} and ${m.away.name}`}>
                Compare teams
              </Link>
              <button type="button" className={ACTION} aria-expanded={open} aria-label={`Match details: ${name}`} onClick={() => setOpen(!open)}>
                {open ? "Hide details" : "Match details"}
              </button>
            </div>
          )}
          {open && <Details m={m} finished={finished} />}
        </div>
      </article>
    </li>
  );
}
