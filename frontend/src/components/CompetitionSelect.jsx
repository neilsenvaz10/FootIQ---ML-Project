import { groupCompetitions } from "../lib/competitions.js";
import { CONTROL_EDGE } from "./ui.jsx";

// One dropdown for all competitions, grouped (Domestic leagues / the UEFA Champions League).
export default function CompetitionSelect({ comps, value, onChange, className = "" }) {
  return (
    <select
      aria-label="Competition"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={!comps?.length}
      className={`w-full rounded-control bg-panel-2 text-base font-bold ${CONTROL_EDGE} ${className}`}
    >
      {groupCompetitions(comps).map((g) => (
        <optgroup key={g.label} label={g.label}>
          {g.items.map((c) => (
            <option key={c.key} value={c.key}>
              {c.name}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
