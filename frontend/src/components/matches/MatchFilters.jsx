import { useId, useState } from "react";
import { Card, Field, Pills, Select } from "../ui.jsx";
import { HUB_LEAGUE } from "../../lib/fixtures.js";
import { int } from "../../lib/format.js";

// The four filters of the Matches hub. They live in the address (comp, season, matchday, status) so a view can be shared and the back button works; this component only reports changes.

export const LEAGUE_OPTIONS = [{ value: "", label: "All leagues" }, ...Object.entries(HUB_LEAGUE).map(([value, label]) => ({ value, label }))];

const STATUS_LABELS = { upcoming: "Upcoming", awaiting_result: "Awaiting result", completed: "Completed", other: "Postponed or cancelled", all: "All" };

export function statusOptions(counts, selected) {
  return Object.entries(STATUS_LABELS)
    .filter(([value]) => value !== "other" || value === selected || (counts?.other ?? 0) > 0)
    .map(([value, label]) => ({ value, label: counts ? `${label} · ${int(counts[value])}` : label }));
}

export default function MatchFilters({ comp, season, matchday, team, status, facets, counts, onChange }) {
  const [expanded, setExpanded] = useState(false);
  const filtersId = useId();
  const seasons = facets?.seasons ?? [];
  const matchdays = facets?.matchdays ?? [];
  const seasonOptions = [{ value: "", label: "Newest season" }, ...(season && !seasons.includes(season) ? [season] : []), ...seasons];
  const matchdayOptions = [{ value: "", label: "All matchdays" }, ...(matchday && !matchdays.map(String).includes(String(matchday)) ? [{ value: String(matchday), label: `Matchday ${matchday}` }] : []), ...matchdays.map((n) => ({ value: String(n), label: `Matchday ${n}` }))];
  const teams = facets?.teams ?? [];
  const teamOptions = [{ value: "", label: "All teams" }, ...(team && !teams.some((t) => t.entity === team) ? [{ value: team, label: team }] : []), ...teams.map((t) => ({ value: t.entity, label: t.name }))];
  return (
    <Card title="Find matches" subtitle="Five domestic leagues and the Champions League, from the results store">
      <div className="space-y-4">
        <Pills label="League" value={comp} onChange={(v) => onChange({ comp: v, matchday: "", team: "" })} options={LEAGUE_OPTIONS} wrap />
        <button type="button" className="min-h-11 rounded-control border border-line-strong px-3 text-sm text-ink sm:hidden" aria-expanded={expanded} aria-controls={filtersId} onClick={() => setExpanded(!expanded)}>{expanded ? "Hide" : "Show"} season, matchday and team filters{season || matchday || team ? " (active)" : ""}</button>
        <div id={filtersId} className={`${expanded ? "grid" : "hidden"} grid-cols-2 gap-3 pt-1 sm:grid [&>label]:min-w-0`}>
          <Field label="Season">
            <Select value={season} onChange={(v) => onChange({ season: v, matchday: "", team: "" })} options={seasonOptions} aria-label="Season" />
          </Field>
          <Field label="Matchday">
            <Select value={matchday ? String(matchday) : ""} onChange={(v) => onChange({ matchday: v })} options={matchdayOptions} aria-label="Matchday" />
          </Field>
          {comp && (
            <Field label="Team">
              <Select value={team ?? ""} onChange={(v) => onChange({ team: v })} options={teamOptions} aria-label="Team" />
            </Field>
          )}
        </div>
        <Pills label="Status" value={status} onChange={(v) => onChange({ status: v })} options={statusOptions(counts, status)} wrap />
      </div>
    </Card>
  );
}
