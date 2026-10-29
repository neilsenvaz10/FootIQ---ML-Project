import { ButtonLink, Chip, ErrorBox, Summary, TeamCrest } from "../ui.jsx";
import { dayLabel, flagChips, freshnessText, gameweekLink, isProvisional, kickoffText, shortDay, timingChip } from "../../lib/fixtures.js";
import { pct } from "../../lib/format.js";

// The Home page's focal point: the next scheduled fixture of the five domestic leagues, exactly as the results store holds it.
// Names, date, kickoff, matchday, freshness and reliability come from /api/featured-fixture; a forecast is shown only if one was already saved.
// Text on the gradient uses `ink` and `ink-2` (7:1 or better on its lightest stop); `mute` would fall below 4.5:1 there.

function PitchLines() {
  return (
    <svg aria-hidden="true" focusable="false" viewBox="0 0 800 320" preserveAspectRatio="xMidYMid slice" className="pointer-events-none absolute inset-0 h-full w-full text-white opacity-[0.07]" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="20" y="20" width="760" height="280" rx="6" />
      <line x1="400" y1="20" x2="400" y2="300" />
      <circle cx="400" cy="160" r="62" />
      <circle cx="400" cy="160" r="4" fill="currentColor" />
      <rect x="20" y="100" width="90" height="120" />
      <rect x="690" y="100" width="90" height="120" />
    </svg>
  );
}

const HERO = "hero relative overflow-hidden rounded-[1.75rem] p-4 shadow-card sm:p-8";

function Side({ team, label }) {
  return (
    <div className="flex min-w-0 flex-col items-center text-center">
      <TeamCrest name={team.name} size={60} className="shadow-glow" />
      <p className="mt-2 text-base font-extrabold leading-tight sm:mt-3 sm:text-2xl">{team.name}</p>
      <p className="mt-0.5 text-xs font-semibold uppercase tracking-wide text-ink-2 sm:mt-1">{label}</p>
    </div>
  );
}

// A saved forecast (made earlier with Predict gameweek), with the team names spelled out: never "1" and "2".
function ForecastStrip({ f }) {
  const p = f.forecast.predictions.primary;
  if (!p) return null;
  const parts = [
    { key: "home", label: `${f.home.name} win`, v: p.home, bar: "bg-home" },
    { key: "draw", label: "Draw", v: p.draw, bar: "bg-draw" },
    { key: "away", label: `${f.away.name} win`, v: p.away, bar: "bg-away" },
  ];
  const top = Math.max(...parts.map((x) => x.v));
  const when = f.forecast.created_utc.replace("T", " ").replace("Z", " UTC");
  return (
    <div className="mt-6 rounded-2xl border border-white/15 bg-black/25 p-4">
      <p className="text-xs font-bold uppercase tracking-wide text-ink-2">Saved forecast · club v1</p>
      <div className="mt-3 flex h-3 overflow-hidden rounded-full" role="img" aria-label={`Saved forecast: ${parts.map((x) => `${x.label} ${pct(x.v)}`).join(", ")}`}>
        {parts.map((x) => (
          <div key={x.key} className={x.bar} style={{ width: `${x.v * 100}%` }} />
        ))}
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2 text-xs tabular-nums">
        {parts.map((x, i) => (
          <p key={x.key} className={`${i === 1 ? "text-center" : i === 2 ? "text-right" : ""} ${x.v === top ? "font-extrabold text-ink" : "text-ink-2"}`}>
            <span className="block truncate">{x.label}</span>
            {pct(x.v)}
          </p>
        ))}
      </div>
      <p className="mt-2 text-xs text-ink-2">
        Saved {when} · history through {f.forecast.data_cutoff_date} · {f.forecast.made_before_kickoff === "yes" ? "saved before kickoff" : f.forecast.made_before_kickoff === "no" ? "saved after kickoff" : "kickoff timing unknown"}
      </p>
    </div>
  );
}

export function FeaturedLoading() {
  return (
    <section aria-label="Next match" aria-busy="true" className={`${HERO} min-h-[18rem]`}>
      <PitchLines />
      <div role="status" className="relative flex items-center gap-3 text-sm text-ink-2">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" aria-hidden="true" />
        Loading the next fixture…
      </div>
    </section>
  );
}

// An error is shown on a plain card, not on the gradient (the error colours need a solid surface to keep their contrast).
export function FeaturedError({ error, onRetry }) {
  return (
    <section aria-label="Next match" className="rounded-[1.75rem] border border-line bg-panel p-5 shadow-card sm:p-8">
      <h2 className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-mute">Next match</h2>
      <ErrorBox error={error} onRetry={onRetry} />
    </section>
  );
}

export function FeaturedEmpty({ data }) {
  const empty = data.empty_state;
  const stale = Object.entries(data.freshness.competitions).filter(([, c]) => c.state !== "fresh").length;
  return (
    <section aria-labelledby="featured-title" className={HERO}>
      <PitchLines />
      <div className="relative">
        <h2 id="featured-title" className="text-xs font-bold uppercase tracking-[0.18em] text-ink-2">
          Next match
        </h2>
        <p className="mt-4 text-2xl font-extrabold leading-tight sm:text-3xl">No upcoming fixture to feature</p>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-2">{empty?.message}</p>
        {stale > 0 && <p className="mt-2 max-w-2xl text-sm text-ink-2">{stale} of the five leagues do not have fresh data, so the stored schedule may be out of date.</p>}
        <div className="mt-6 flex flex-col gap-2 sm:flex-row">
          <ButtonLink to="/analytics" variant="light">
            Browse leagues
          </ButtonLink>
          <ButtonLink to="/predict?mode=gameweek" variant="glass">
            Gameweek predictions
          </ButtonLink>
        </div>
      </div>
    </section>
  );
}

export default function FeaturedMatch({ data }) {
  const f = data.featured;
  const e = f.eligibility;
  const fresh = freshnessText(data.freshness.competitions[f.competition_key]);
  const rel = isProvisional(f);
  const chips = flagChips(e.flags);
  const rel_day = dayLabel(f.date, data.today_utc);
  const date = shortDay(f.date);
  const when = timingChip(f.timing);
  return (
    <section aria-labelledby="featured-title" className={HERO}>
      <PitchLines />
      <div className="relative">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="featured-title" className="mr-1 text-xs font-bold uppercase tracking-[0.18em] text-ink-2">
            Next match
          </h2>
          <Chip tone="hero">{f.competition}</Chip>
          <Chip tone="hero">{f.matchday_label ?? `Season ${f.season}`}</Chip>
        </div>

        <div className="mt-4 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] gap-x-2 gap-y-3 sm:mt-6 sm:gap-y-5 [grid-template-areas:'home_vs_away'_'when_when_when'] sm:gap-x-6 sm:[grid-template-areas:'home_when_away']">
          <div className="[grid-area:home]">
            <Side team={f.home} label="Home" />
          </div>
          <span aria-hidden="true" className="self-center rounded-full border border-white/25 px-2.5 py-1 text-xs font-bold uppercase tracking-widest text-ink-2 [grid-area:vs] sm:hidden">
            vs
          </span>
          <div className="flex flex-col items-center text-center [grid-area:when] sm:min-w-[12rem] sm:pt-4">
            <p aria-hidden="true" className="mb-1 hidden rounded-full border border-white/25 px-2.5 py-0.5 text-xs font-bold uppercase tracking-widest text-ink-2 sm:block">
              vs
            </p>
            <p className="text-xl font-extrabold leading-tight sm:text-3xl">{rel_day}</p>
            {rel_day !== date && <p className="text-sm text-ink-2">{date}</p>}
            {kickoffText(f.kickoff) ? <p className="mt-1 text-sm font-semibold sm:text-base">{kickoffText(f.kickoff)}</p> : null}
          </div>
          <div className="[grid-area:away]">
            <Side team={f.away} label="Away" />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 sm:mt-6">
          {when && <Chip tone="hero">{when[0]}</Chip>}
          {fresh && <Chip tone={fresh.tone}>{fresh.text}</Chip>}
          {rel ? <Chip tone="warn">Provisional history</Chip> : <Chip tone="ok">Fully supported history</Chip>}
        </div>

        {f.timing?.ambiguous && <p className="mt-3 text-sm leading-relaxed text-ink-2">{f.timing.note}</p>}

        <div className="mt-4 grid grid-cols-2 gap-2 sm:mt-5 sm:flex sm:flex-wrap">
          <ButtonLink to={gameweekLink(f)} variant="light" className="col-span-2">
            Open gameweek predictions
          </ButtonLink>
          <ButtonLink to={`/predict?mode=manual&comp=${f.competition_key}`} variant="glass" className="px-3 sm:px-5">
            Predict a match
          </ButtonLink>
          <ButtonLink to="/compare" variant="glass" className="px-3 sm:px-5">
            Compare teams
          </ButtonLink>
        </div>

        {f.forecast ? (
          <ForecastStrip f={f} />
        ) : (
          <p className="mt-5 text-sm text-ink-2">
            No forecast is saved for this fixture. Forecasts are created only when you press <strong className="text-ink">Predict gameweek</strong>.
          </p>
        )}

        {(e.reasons.length > 0 || chips.length > 0) && (
          <details className="group mt-4 rounded-xl border border-white/15 bg-black/20 px-4 text-sm text-ink-2">
            <Summary onHero large>
              Notes on this fixture&apos;s data ({e.reasons.length || chips.length})
            </Summary>
            <div className="flex flex-wrap gap-2 pb-3">
              {chips.map(([label, tone]) => (
                <Chip key={label} tone={tone === "info" ? "hero" : tone}>
                  {label}
                </Chip>
              ))}
            </div>
            <ul className="list-disc space-y-1.5 pb-3 pl-5 leading-relaxed">
              {e.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </details>
        )}
        <p className="mt-4 text-xs leading-relaxed text-ink-2">
          Fixture source: {f.source || "not stated"}. The date is as published; a time is shown only when the source states it. Historical and periodically synchronised data, not live.
        </p>
      </div>
    </section>
  );
}
