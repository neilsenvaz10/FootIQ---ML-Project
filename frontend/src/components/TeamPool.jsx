import { useApi } from "../lib/hooks.js";
import { CONTROL_EDGE } from "./ui.jsx";

// Season-aware team list: defaults to the newest season's participants; "All seasons" shows every club in the dataset (including relegated or defunct ones).
export const ALL = "all";

export function useTeamPool(key, choice) {
  const seasons = useApi(`/api/competitions/${key}/seasons`);
  const latest = seasons.data?.[0];
  const season = choice || latest || "";
  const scope = season === ALL ? undefined : season || undefined;
  const teams = useApi(seasons.data ? `/api/competitions/${key}/teams` : null, { season: scope });
  return { seasons, season, latest, teams };
}

export function TeamPoolFilter({ pool, onChange }) {
  const { seasons, season, latest, teams } = pool;
  if (!seasons.data?.length) return null;
  const historical = season === ALL;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-mute">
      <label className="flex items-center gap-2">
        Teams from
        <select aria-label="Team pool" value={season} onChange={(e) => onChange(e.target.value)} className={`rounded-full bg-panel-2 text-xs font-semibold ${CONTROL_EDGE}`}>
          {seasons.data.map((s) => (
            <option key={s} value={s}>
              {s}
              {s === latest ? " (latest)" : ""}
            </option>
          ))}
          <option value={ALL}>All seasons (historical)</option>
        </select>
      </label>
      <span>
        {teams.data ? `${teams.data.length} teams` : ""}
        {historical ? " · includes clubs that have since left the competition" : ""}
      </span>
    </div>
  );
}
