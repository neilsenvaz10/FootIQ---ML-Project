import { useState } from "react";
import { useApi } from "../lib/hooks.js";
import Icon from "./Icon.jsx";
import { FreshnessTable } from "./CompetitionFreshness.jsx";

const PROVIDER = {
  approved_live_disabled: "Approved source; live checks are off",
  approved_live_enabled: "Approved source; live checks are on",
  prepared_offline: "Saved snapshots only; no live source approved",
  prepared_needs_token: "Provider adapter prepared offline; needs your account and API token",
  blocked_no_provider: "No approved provider",
};
const TONE = { fresh: "bg-ok/15 text-ok", stale: "bg-warn/15 text-warn" };

// "Last updated / Latest match result / Source" for every competition, straight from /api/sync/status.
// Stale data is shown as stale; nothing here is ever labelled live.
export default function SyncStatus() {
  const { data, error } = useApi("/api/sync/status");
  const [open, setOpen] = useState(false);
  if (error) {
    return error.status === 503 ? null : <div className="mb-4 rounded-xl border border-warn/40 bg-warn/10 px-3.5 py-2.5 text-xs text-warn">Data status unavailable: {error.message}</div>;
  }
  if (!data) return null;
  const newest = data.competitions.map((c) => c.latest_result).filter(Boolean).sort().at(-1);
  const sch = data.scheduler;
  const qr = data.quarantine;
  const lastCheck = data.competitions.map((c) => c.last_successful_external_check_utc).filter(Boolean).sort().at(-1);
  const when = (v) => (v ? v.replace("T", " ").replace("Z", " UTC") : "none");
  return (
    <section className="mb-5 rounded-card border border-line bg-panel/80" aria-label="Data freshness">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex min-h-11 w-full flex-wrap items-center gap-x-4 gap-y-1 rounded-card px-4 py-2.5 text-left text-xs text-mute">
        <Icon name="clock" className="h-4 w-4 shrink-0 text-accent" />
        <span>
          <span className="text-ink-2">Latest match result:</span> {newest ?? "unknown"}
        </span>
        <span>
          <span className="text-ink-2">Last successful source check:</span> {lastCheck ? when(lastCheck) : "none yet"}
        </span>
        <span>
          <span className="text-ink-2">Sync:</span> {!data.live_enabled ? "off (cached data only)" : data.sync_mode === "startup" ? "on, refreshes once each time FootIQ starts" : `on, checks about every ${data.periodic_minutes} min`}
        </span>
        {sch && (
          <span>
            <span className="text-ink-2">Scheduler:</span> {sch.status}
          </span>
        )}
        {sch?.live_enabled && (
          <span>
            <span className="text-ink-2">{data.sync_mode === "startup" ? "Failed refreshes in a row:" : "Failed cycles in a row:"}</span> {sch.consecutive_failed_cycles}
          </span>
        )}
        <span className="ml-auto inline-flex items-center gap-1 font-semibold text-accent">
          {open ? "Hide" : "Details"}
          <Icon name="chevron" className={`h-4 w-4 transition-transform ${open ? "-rotate-90" : "rotate-90"}`} />
        </span>
      </button>
      {open && (
        <div className="border-t border-line px-4 py-3">
          {sch && (
            <p className="mb-2 text-xs text-mute">
              <span className="text-ink-2">Last successful import:</span> {when(data.competitions.map((c) => c.last_successful_import_utc).filter(Boolean).sort().at(-1))} ·{" "}
              <span className="text-ink-2">{data.sync_mode === "startup" ? "Next refresh:" : "Next scheduled check:"}</span>{" "}
              {data.sync_mode === "startup" ? (sch.live_enabled ? "next time FootIQ starts" : "none (live checking is off)") : sch.next_scheduled_check_utc ? when(sch.next_scheduled_check_utc) : "none (live checking is off)"} ·{" "}
              <span className="text-ink-2">Quarantined findings needing review:</span> {qr?.needs_operator_review ?? 0}
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-mute">
                  <th scope="col" className="py-1.5 pr-3 font-semibold">Competition</th>
                  <th scope="col" className="py-1.5 pr-3 font-semibold">Status</th>
                  <th scope="col" className="py-1.5 pr-3 font-semibold">Latest result</th>
                  <th scope="col" className="py-1.5 pr-3 text-right font-semibold">Awaiting result</th>
                  <th scope="col" className="py-1.5 pr-3 text-right font-semibold">Scheduled</th>
                  <th scope="col" className="py-1.5 pr-3 font-semibold">Last source check</th>
                  <th scope="col" className="py-1.5 pr-3 font-semibold">Last import</th>
                  <th scope="col" className="py-1.5 pr-3 font-semibold">Last attempt</th>
                  <th scope="col" className="py-1.5 pr-3 font-semibold">Next check</th>
                  <th scope="col" className="py-1.5 pr-3 text-right font-semibold">Imported / held</th>
                  <th scope="col" className="py-1.5 font-semibold">Provider</th>
                </tr>
              </thead>
              <tbody>
                {data.competitions.map((c) => (
                  <tr key={c.competition_key} className="border-t border-line align-top">
                    <td className="py-2 pr-3 font-semibold">{c.competition_key}</td>
                    <td className="py-2 pr-3">
                      <span className={`rounded-full px-2.5 py-0.5 font-semibold ${TONE[c.state]}`}>{c.state}</span>
                      {c.state_reasons.map((r) => (
                        <div key={r} className="mt-0.5 max-w-[22rem] text-xs text-mute">
                          {r}
                        </div>
                      ))}
                      {c.feed_lag && <div className="mt-0.5 max-w-[22rem] text-xs font-semibold text-warn">{c.feed_lag.message}</div>}
                      {c.last_check_summary && <div className="mt-0.5 max-w-[22rem] text-xs text-mute">{c.last_check_summary}</div>}
                      {c.history_note && <div className="mt-0.5 max-w-[22rem] text-xs text-mute">{c.history_note}</div>}
                    </td>
                    <td className="py-2 pr-3 tabular-nums">{c.latest_result ?? "-"}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{c.awaiting_result || "-"}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{c.scheduled || "-"}</td>
                    <td className="py-2 pr-3 tabular-nums">{when(c.last_successful_external_check_utc)}</td>
                    <td className="py-2 pr-3 tabular-nums">{when(c.last_successful_import_utc)}</td>
                    <td className="py-2 pr-3 tabular-nums">{when(c.last_attempted_sync_utc)}</td>
                    <td className="py-2 pr-3 tabular-nums">
                      {data.sync_mode === "startup" ? (sch?.leagues?.[c.competition_key] ? "next launch" : "-") : sch?.leagues?.[c.competition_key] ? when(sch?.leagues?.[c.competition_key].next_check_utc) : "-"}
                      {sch?.leagues?.[c.competition_key]?.consecutive_failed_cycles > 0 && (
                        <div className="mt-0.5 text-xs font-semibold text-warn">
                          {sch?.leagues?.[c.competition_key].consecutive_failed_cycles} failed {data.sync_mode === "startup" ? "refresh(es) in a row; the stored data is unchanged" : "cycle(s) in a row, backing off"}
                        </div>
                      )}
                      {sch?.leagues?.[c.competition_key]?.last_error && (
                        <div className="mt-0.5 max-w-[16rem] text-xs text-warn">Last error ({when(sch.leagues[c.competition_key].last_error.at_utc)}): {sch.leagues[c.competition_key].last_error.error}</div>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">
                      {c.imported_records ?? 0} / {c.quarantined_records ?? 0}
                    </td>
                    <td className="py-2">
                      {c.approved_sources.length ? c.approved_sources.join(", ") : "baseline files only"}
                      <div className="mt-0.5 max-w-[16rem] text-xs text-mute">{PROVIDER[c.provider_readiness] ?? ""}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-mute">
            {data.note} {data.attribution.map((a) => `${a.text} (used for ${a.used_for.join(", ")}).`).join(" ")}
          </p>
          <FreshnessTable />
        </div>
      )}
    </section>
  );
}
