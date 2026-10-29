import { useApi } from "../lib/hooks.js";

// Competition-level data freshness, straight from /api/data-freshness. A competition is either "Updated when FootIQ starts" (refreshed once at each launch from an approved source)
// or "Historical only". Nothing here is ever labelled live. Warnings about missing coverage are shown as they come from the backend.
const TONE = { startup_updated: "bg-ok/15 text-ok", historical_only: "bg-mute/15 text-ink-2" };
const when = (v) => (v ? v.replace("T", " ").replace("Z", " UTC") : "none");
const ago = (d) => (d === null || d === undefined ? "" : d === 0 ? " (today)" : d === 1 ? " (1 day ago)" : ` (${d} days ago)`);

export function FreshnessBody({ f }) {
  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className={`rounded-full px-2.5 py-0.5 font-semibold ${TONE[f.data_status]}`}>{f.data_status_label}</span>
        <span>
          <span className="text-ink-2">Latest result:</span> {f.latest_result ?? "none"}
          {ago(f.days_since_latest_result)}
        </span>
        {f.data_status === "startup_updated" && (
          <span>
            <span className="text-ink-2">Last successful refresh:</span> {when(f.last_successful_refresh_utc)}
          </span>
        )}
      </div>
      <p className="text-mute">{f.update_note}</p>
      {f.warnings.length > 0 && (
        <ul className="space-y-0.5">
          {f.warnings.map((w) => (
            <li key={w.text} className={w.level === "warning" ? "font-semibold text-warn" : "text-mute"}>
              {w.level === "warning" ? "Missing coverage: " : ""}
              {w.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function CompetitionFreshness({ compKey }) {
  const { data } = useApi("/api/data-freshness");
  const f = Array.isArray(data) ? data.find((x) => x.key === compKey) : null;
  if (!f) return null; // unavailable or still loading: the page works without it
  return (
    <section role="group" aria-label={`Data freshness: ${f.name}`} className="rounded-xl border border-line bg-panel/70 px-3.5 py-2.5 text-xs text-ink">
      <FreshnessBody f={f} />
    </section>
  );
}

// All competitions at once (used in the data-status panel).
export function FreshnessTable() {
  const { data } = useApi("/api/data-freshness");
  if (!Array.isArray(data)) return null;
  return (
    <div className="mt-3 space-y-2" aria-label="Data freshness by competition">
      <h3 className="text-xs font-semibold text-ink-2">Every competition: latest result, update status and missing coverage</h3>
      <ul className="space-y-2 text-xs">
        {data.map((f) => (
          <li key={f.key} className="rounded-lg border border-line px-3 py-2" data-competition={f.key}>
            <div className="mb-1 font-semibold">{f.name}</div>
            <FreshnessBody f={f} />
          </li>
        ))}
      </ul>
    </div>
  );
}
