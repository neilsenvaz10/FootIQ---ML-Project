import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import { useApi } from "../lib/hooks.js";
import { Badge, Button, Card, ErrorBox, Field, Input, Notice, Select, Spinner, Tabs, TeamAvatar } from "../components/ui.jsx";

export const SEASON_LEAGUES = ["BUNDESLIGA", "LALIGA", "EPL", "SERIEA", "LIGUE1"];
export const SIM_ACTION = "simulate_season_button";

const STATE = {
  ready: { label: "Ready", tone: "ok", text: "Results are complete and recent enough for a simulation." },
  provisional: { label: "Provisional", tone: "warn", text: "Some results are missing or a little old. Treat every number as less reliable." },
  not_eligible: { label: "Not eligible", tone: "bad", text: "Too many results are missing or too old for a reliable simulation." },
};
const TONE = { ok: "bg-ok/15 text-ok", warn: "bg-warn/15 text-warn", bad: "bg-bad/15 text-bad" };

export function validateSims(value, limits) {
  const n = Number(value);
  if (!limits) return null;
  if (!Number.isInteger(n) || n < limits.min || n > limits.max) return `Simulations must be a whole number from ${limits.min.toLocaleString()} to ${limits.max.toLocaleString()}.`;
  return null;
}

const p1 = (v) => (v == null ? "–" : `${(v * 100).toFixed(1)}%`);
const pb = (t, k) => (t[k] != null ? p1(t[k]) : t[`${k}_low`] != null ? `${(t[`${k}_low`] * 100).toFixed(1)}–${(t[`${k}_high`] * 100).toFixed(1)}%` : "–"); // a withheld probability shows its bounds
export const POINTS_ACTION = "simulate_points_button";
export const POINTS_LABEL = "Experimental \u2014 Points-only simulation";
export const RANGES_LABEL = "Position ranges: lower and upper bounds, not exact probabilities";

// ---- position ranges (lower and upper bounds) -------------------------------------------------------------------------------------------------------------------------------
export const clamp01 = (v) => Math.min(1, Math.max(0, Number(v)));
export function fmtPct(v) {
  const x = clamp01(v);
  if (x === 0) return "0%";
  if (x === 1) return "100%";
  if (x < 0.0005) return "<0.1%";
  if (x > 0.9995) return ">99.9%";
  return `${(x * 100).toFixed(1)}%`;
}
/** "94.8\u201396.1%" (or one number when the lower and upper bound coincide). */
export function rangeText(v) {
  const lo = fmtPct(v.guaranteed);
  const hi = fmtPct(v.possible);
  return lo === hi ? lo : `${lo.replace(/%$/, "")}\u2013${hi}`;
}
/** Nothing is shown unless every value is a number between 0 and 1 and no lower bound exceeds its upper bound. */
export function rangesAreValid(pb) {
  if (!pb || pb.status !== "available" || !Array.isArray(pb.clubs) || !Array.isArray(pb.bands) || pb.bands.length === 0) return false;
  return pb.clubs.every((c) =>
    pb.bands.every((b) => {
      const v = c[b.id];
      return v && [v.guaranteed, v.possible, v.unresolved].every((x) => Number.isFinite(x) && x >= 0 && x <= 1) && v.guaranteed <= v.possible;
    }),
  );
}
const placesText = (b) => (b.positions[0] === b.positions[1] ? `place ${b.positions[0]}` : `places ${b.positions[0]}\u2013${b.positions[1]}`);
const BAR = { title: ["bg-pitch", "bg-pitch/35"], top4: ["bg-ok", "bg-ok/35"], relegation: ["bg-bad", "bg-bad/35"] };

function EligibilityBanner({ st }) {
  const s = STATE[st.state] ?? STATE.not_eligible;
  return (
    <div className="space-y-3" data-testid="eligibility-banner">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${TONE[s.tone]}`}>Data: {s.label}</span>
        <span className="text-mute">{s.text}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
        <Stat label="Newest result" value={st.latest_result ?? "none"} hint={st.days_since_latest_result != null ? `${st.days_since_latest_result} day(s) ago` : ""} />
        <Stat label="Results stored" value={st.counts?.completed ?? 0} hint={`of ${st.counts?.fixtures ?? 0} fixtures`} />
        <Stat label="Played, no result" value={st.counts?.missing_results ?? 0} hint={st.missing_share != null ? `${(st.missing_share * 100).toFixed(1)}% of played-date fixtures` : ""} />
        <Stat label="Still to simulate" value={st.counts?.remaining_to_simulate ?? 0} hint={`${st.counts?.postponed ?? 0} postponed`} />
      </div>
      {st.reasons?.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-xs text-mute">
          {st.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      {st.notes?.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-xs text-mute">
          {st.notes.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-2xl bg-panel-2 px-3 py-2">
      <div className="text-[11px] text-mute">{label}</div>
      <div className="text-base font-extrabold tabular-nums">{value}</div>
      {hint ? <div className="text-[11px] text-mute">{hint}</div> : null}
    </div>
  );
}

function RulesNotice({ rp }) {
  if (!rp) return null;
  return rp.usable ? (
    <Notice tone="info" title="League rules: verified for this season">
      Tie-breaks and relegation places come from {rp.sources?.map((s, i) => (
        <span key={s.url}>
          {i ? "; " : ""}
          <a className="font-semibold text-pitch underline" href={s.url} target="_blank" rel="noreferrer">
            {s.title.split(",")[0]}
          </a>
        </span>
      ))}
      .{rp.live_confirmation ? <span className="mt-1 block font-semibold text-warn">Live-document confirmation pending: the federation file has not been checked against its checksum yet.</span> : null}
    </Notice>
  ) : (
    <Notice tone="warn" title="League rules: blocked">
      {rp.reason}
    </Notice>
  );
}

function PositionBars({ team, bands }) {
  const probs = team.position_probabilities;
  const max = Math.max(...probs, 0.0001);
  const rel = new Set(bands?.relegation ?? []);
  const top = new Set(bands?.top4 ?? []);
  return (
    <div role="img" aria-label={`Finishing position probabilities for ${team.name}`} className="flex h-16 items-end gap-0.5">
      {probs.map((p, i) => (
        <div key={i} title={`Position ${i + 1}: ${p1(p)}`} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end">
          <div className={`w-full rounded-t ${rel.has(i + 1) ? "bg-bad" : top.has(i + 1) ? "bg-ok" : "bg-pitch"}`} style={{ height: `${Math.max((p / max) * 100, p > 0 ? 3 : 0)}%` }} />
          <span className="mt-0.5 text-[9px] text-mute">{i + 1}</span>
        </div>
      ))}
    </div>
  );
}

function Heatmap({ teams }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-0.5 text-[10px]" aria-label="Finishing position probability for every club">
        <caption className="sr-only">Rows are clubs, columns are final positions; darker means more likely.</caption>
        <thead>
          <tr>
            <th className="sticky left-0 bg-panel px-1 text-left font-semibold text-mute">Club</th>
            {teams[0].position_probabilities.map((_, i) => (
              <th key={i} className="px-0.5 font-medium text-mute">
                {i + 1}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {teams.map((t) => (
            <tr key={t.entity_id}>
              <th className="sticky left-0 max-w-[7rem] truncate bg-panel px-1 text-left font-semibold">{t.name}</th>
              {t.position_probabilities.map((p, i) => (
                <td key={i} title={`${t.name}, position ${i + 1}: ${p1(p)}`} className="h-5 min-w-[1.1rem] rounded-sm text-center tabular-nums" style={{ background: `rgba(139,123,255,${Math.min(p * 1.6, 1)})`, color: p > 0.35 ? "#fff" : "transparent" }}>
                  {p >= 0.1 ? Math.round(p * 100) : ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResultTable({ summary, bands }) {
  const [open, setOpen] = useState(null);
  const hasRel = summary.teams.some((t) => t.p_relegation != null);
  const hasPlay = summary.teams.some((t) => t.p_relegation_playoff != null);
  return (
    <div className="overflow-hidden rounded-2xl border border-white/5 bg-panel">
      <div className="grid grid-cols-[1.5rem_1fr_auto] items-center gap-x-2 border-b border-line/60 px-3 py-2 text-[11px] font-semibold text-mute sm:grid-cols-[1.5rem_1fr_9rem_4rem_4rem_4rem_4rem]">
        <span>#</span>
        <span>Club</span>
        <span className="hidden sm:block">Expected points (10–90%)</span>
        <span className="hidden text-right sm:block">Title</span>
        <span className="hidden text-right sm:block">Top 4</span>
        <span className="hidden text-right sm:block">{hasRel ? "Relegated" : ""}</span>
        <span className="hidden text-right sm:block">{hasPlay ? "Play-off" : "Exp. rank"}</span>
        <span className="text-right sm:hidden">Pts · Title</span>
      </div>
      {summary.teams.map((t, i) => (
        <div key={t.entity_id} className="border-b border-line/40 last:border-b-0">
          <button
            onClick={() => setOpen(open === t.entity_id ? null : t.entity_id)}
            aria-expanded={open === t.entity_id}
            className="grid w-full grid-cols-[1.5rem_1fr_auto] items-center gap-x-2 px-3 py-2 text-left text-sm sm:grid-cols-[1.5rem_1fr_9rem_4rem_4rem_4rem_4rem]"
          >
            <span className="text-xs tabular-nums text-mute">{i + 1}</span>
            <span className="flex min-w-0 items-center gap-2">
              <TeamAvatar name={t.name} size={24} />
              <span className="truncate font-semibold">{t.name}</span>
            </span>
            <span className="hidden tabular-nums sm:block">
              <b>{t.expected_points.toFixed(1)}</b> <span className="text-xs text-mute">({Math.round(t.points_p10)}–{Math.round(t.points_p90)})</span>
            </span>
            <span className="hidden text-right tabular-nums sm:block">{pb(t, "p_title")}</span>
            <span className="hidden text-right tabular-nums sm:block">{pb(t, "p_top4")}</span>
            <span className="hidden text-right tabular-nums sm:block">{hasRel ? pb(t, "p_relegation") : ""}</span>
            <span className="hidden text-right tabular-nums sm:block">{hasPlay ? pb(t, "p_relegation_playoff") : t.expected_rank == null ? "–" : t.expected_rank.toFixed(1)}</span>
            <span className="text-right text-xs tabular-nums sm:hidden">
              <b>{t.expected_points.toFixed(0)}</b> · {pb(t, "p_title")}
            </span>
          </button>
          {open === t.entity_id && (
            <div className="space-y-2 px-3 pb-3">
              <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                <Stat label="Title" value={pb(t, "p_title")} />
                <Stat label="Top four" value={pb(t, "p_top4")} />
                <Stat label="Relegation" value={hasRel ? pb(t, "p_relegation") : "not defined"} />
                <Stat label="Expected rank" value={t.expected_rank == null ? "unresolved" : t.expected_rank.toFixed(1)} hint={`${Math.round(t.rank_p10)}–${Math.round(t.rank_p90)} (10–90%)`} />
              </div>
              <PositionBars team={t} bands={bands} />
              <p className="text-[11px] text-mute">Bars: share of simulations finishing in each position (green top four, red relegation).</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Assumptions({ a, st, mode }) {
  const sc = a?.scoreline;
  return (
    <details open className="rounded-2xl border border-white/5 bg-panel p-4" data-testid="assumptions-panel">
      <summary className="cursor-pointer text-[15px] font-bold">Assumptions and limitations</summary>
      <div className="mt-3 space-y-3 text-sm text-mute">
        {a && (
          <dl className="grid gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
            <Row k="Run saved (UTC)" v={a.created_utc} />
            <Row k="Simulations / seed" v={`${a.simulations.toLocaleString()} / ${a.seed}`} />
            <Row k="Largest sampling error" v={`about ±${(a.standard_error_max * 196).toFixed(1)} percentage points`} />
            <Row k="Probability model" v={`${a.models.primary} (frozen, validated club model)`} />
            {a.models.experimental_comparison && <Row k="Experimental comparison" v={`${a.models.experimental_comparison} (development-validated only)`} />}
            {sc && <Row k="Scoreline method" v={`${sc.method}; validation: ${sc.validation?.status}`} />}
            {a.points_rule && <Row k="Points rule" v={a.points_rule} />}
            <Row k="Data cut-off" v={`${a.data_cutoff.latest_result_in_competition} (this league), ${a.data_cutoff.latest_result_in_model_history} (all model history)`} />
            <Row k="Last successful sync" v={a.freshness.last_sync_utc ?? "none recorded"} />
            <Row k="Result sources" v={Object.entries(a.freshness.completed_results_by_source).map(([k, v]) => `${k}: ${v}`).join(", ")} />
            <Row k="Remaining fixtures simulated" v={a.remaining_fixtures} />
            <Row k="Input fingerprint" v={`${a.input_sha256.slice(0, 16)}…`} />
          </dl>
        )}
        <div>
          <h3 className="mb-1 text-xs font-bold text-ink">How the simulation works</h3>
          <p className="text-xs">
            {(a ? a.mode === "points_only" : mode === "points")
              ? "For every match still to be played the frozen model gives home-win, draw and away-win chances; a result is drawn from them, 3, 1 or 0 points are added to each club, and this is repeated thousands of times. The spread of each club's final points is shown. No scores are invented and no tie is settled by chance: where clubs end level on points, the position ranges show what the league's tie-break rules settle for sure (lower bound) and what is still possible (upper bound)."
              : "For every match still to be played the frozen model gives home-win, draw and away-win chances; a result and a score are drawn from them, the table is rebuilt and ranked with the league's official tie-break rules, and this is repeated thousands of times. The counts become probabilities."}
          </p>
        </div>
        <div>
          <h3 className="mb-1 text-xs font-bold text-ink">Limitations</h3>
          <ul className="list-disc space-y-1 pl-5 text-xs">
            {(a?.limitations ?? (mode === "points" ? st?.points_only?.limitations : st?.limitations) ?? []).map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </div>
        {a?.rule_profile?.interpretation_notes?.length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-bold text-ink">Rule interpretations</h3>
            <ul className="list-disc space-y-1 pl-5 text-xs">
              {a.rule_profile.interpretation_notes.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </details>
  );
}

const Row = ({ k, v }) => (
  <div className="flex gap-2">
    <dt className="shrink-0 font-semibold text-ink">{k}:</dt>
    <dd className="min-w-0 break-words">{v}</dd>
  </div>
);

function PointsBars({ team }) {
  const d = team.distribution;
  const max = Math.max(...d.probabilities, 0.0001);
  const step = Math.max(1, Math.ceil(d.probabilities.length / 6));
  return (
    <div role="img" aria-label={`Distribution of final points for ${team.name}`} className="flex h-20 items-end gap-px">
      {d.probabilities.map((p, i) => (
        <div key={i} title={`${d.first_points + i} points: ${p1(p)}`} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end">
          <div className={`w-full rounded-t ${d.first_points + i >= team.points_p10 && d.first_points + i <= team.points_p90 ? "bg-pitch" : "bg-pitch/35"}`} style={{ height: `${Math.max((p / max) * 100, p > 0 ? 3 : 0)}%` }} />
          <span className="relative mt-0.5 h-3 w-full text-[9px] text-mute">{i % step === 0 ? <span className="absolute left-1/2 -translate-x-1/2 whitespace-nowrap">{d.first_points + i}</span> : null}</span>
        </div>
      ))}
    </div>
  );
}

function PointsResult({ summary }) {
  const [open, setOpen] = useState(null);
  return (
    <div className="space-y-2">
      <p className="px-1 text-xs text-mute">Clubs are listed by expected final points only. This is not a predicted table: no tie-breaks are applied and no finishing position is implied.</p>
      <div className="overflow-hidden rounded-2xl border border-white/5 bg-panel">
        <div className="grid grid-cols-[1fr_auto] items-center gap-x-2 border-b border-line/60 px-3 py-2 text-[11px] font-semibold text-mute sm:grid-cols-[1fr_4rem_4rem_9rem_5rem]">
          <span>Club</span>
          <span className="hidden text-right sm:block">Now</span>
          <span className="hidden text-right sm:block">Left</span>
          <span className="hidden sm:block">Expected final points (10–90%)</span>
          <span className="text-right">Exp. pts</span>
        </div>
        {summary.teams.map((t) => (
          <div key={t.entity_id} className="border-b border-line/40 last:border-b-0">
            <button onClick={() => setOpen(open === t.entity_id ? null : t.entity_id)} aria-expanded={open === t.entity_id} className="grid w-full grid-cols-[1fr_auto] items-center gap-x-2 px-3 py-2 text-left text-sm sm:grid-cols-[1fr_4rem_4rem_9rem_5rem]">
              <span className="flex min-w-0 items-center gap-2">
                <TeamAvatar name={t.name} size={24} />
                <span className="truncate font-semibold">{t.name}</span>
              </span>
              <span className="hidden text-right tabular-nums sm:block">{t.current_points}</span>
              <span className="hidden text-right tabular-nums sm:block">{t.remaining_fixtures}</span>
              <span className="hidden tabular-nums sm:block">
                {Math.round(t.points_p10)}–{Math.round(t.points_p90)}
              </span>
              <span className="text-right font-extrabold tabular-nums">{t.expected_points.toFixed(1)}</span>
            </button>
            {open === t.entity_id && (
              <div className="space-y-2 px-3 pb-3">
                <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                  <Stat label="Points now" value={t.current_points} hint={`${t.remaining_fixtures} matches left`} />
                  <Stat label="Expected final" value={t.expected_points.toFixed(1)} hint={`spread (sd) ${t.points_sd.toFixed(1)}`} />
                  <Stat label="Middle half" value={`${Math.round(t.points_p25)}–${Math.round(t.points_p75)}`} hint={`median ${Math.round(t.points_median)}`} />
                  <Stat label="Range seen" value={`${t.points_min}–${t.points_max}`} hint={`10–90%: ${Math.round(t.points_p10)}–${Math.round(t.points_p90)}`} />
                </div>
                <PointsBars team={t} />
                <p className="text-[11px] text-mute">Bars: share of simulations ending on each points total (bright bars are the 10–90% range).</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function RangeBar({ band, v }) {
  const [solid, soft] = BAR[band.id] ?? BAR.title;
  const lo = clamp01(v.guaranteed) * 100;
  const hi = clamp01(v.possible) * 100;
  return (
    <div aria-hidden="true" className="relative h-2 w-full overflow-hidden rounded-full bg-white/5">
      <div className={`absolute inset-y-0 left-0 ${solid}`} style={{ width: `${lo}%` }} />
      <div className={`absolute inset-y-0 ${soft}`} style={{ left: `${lo}%`, width: `${Math.max(hi - lo, 0)}%` }} />
    </div>
  );
}

function RangeCell({ band, v }) {
  return (
    <div className="min-w-0 space-y-1" data-range={`${band.id}:${clamp01(v.guaranteed)}:${clamp01(v.possible)}`}>
      <div aria-hidden="true" className="text-[10px] text-mute sm:hidden">{band.label}</div>
      <div className="text-xs font-bold tabular-nums sm:text-sm">
        <span aria-hidden="true">{rangeText(v)}</span>
        <span className="sr-only">{fmtPct(v.guaranteed) === fmtPct(v.possible) ? `${band.label}: ${fmtPct(v.guaranteed)}.` : `${band.label}: lower bound ${fmtPct(v.guaranteed)}, upper bound ${fmtPct(v.possible)}.`}</span>
      </div>
      <RangeBar band={band} v={v} />
    </div>
  );
}

function RangeDetail({ club, bands }) {
  return (
    <div className="space-y-2 px-3 pb-3" data-testid={`range-detail-${club.entity_id}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-xs" aria-label={`Range details for ${club.name}`}>
          <thead>
            <tr className="text-left text-mute">
              <th className="py-1 font-semibold">Outcome</th>
              <th className="text-right font-semibold">Lower bound (guaranteed)</th>
              <th className="text-right font-semibold">Upper bound (possible)</th>
              <th className="text-right font-semibold">Unresolved</th>
              <th className="text-right font-semibold">Sampling error</th>
            </tr>
          </thead>
          <tbody>
            {bands.map((b) => {
              const v = club[b.id];
              return (
                <tr key={b.id} className="border-t border-line/40">
                  <td className="py-1 font-semibold">
                    {b.label} <span className="font-normal text-mute">({placesText(b)})</span>
                  </td>
                  <td className="text-right tabular-nums">{fmtPct(v.guaranteed)}</td>
                  <td className="text-right tabular-nums">{fmtPct(v.possible)}</td>
                  <td className="text-right tabular-nums">{fmtPct(v.unresolved)}</td>
                  <td className="text-right tabular-nums">±{(196 * Math.max(v.se_guaranteed ?? 0, v.se_possible ?? 0)).toFixed(1)} pp</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-mute">Unresolved = upper bound minus lower bound: the part that only the unplayed scores (or a decider that is never simulated) could settle. Sampling error: 95% margin of the simulation itself, in percentage points.</p>
    </div>
  );
}

function RangesExplainer({ pb }) {
  const top = [...pb.clubs].sort((a, b) => b.title.possible - a.title.possible)[0];
  const gap = top ? top.title.possible - top.title.guaranteed : 0;
  return (
    <div className="space-y-2 rounded-2xl bg-panel-2 p-3 text-xs text-mute" data-testid="ranges-explainer">
      <h3 className="text-[13px] font-bold text-ink">How to read these ranges</h3>
      <p>
        We replay the rest of the season thousands of times using only wins, draws and losses. Clubs that end on the same points are separated by goals, and we do not invent goals, so for each club and each outcome (for example "wins the league") we give <b className="text-ink">two numbers instead of one</b>:
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          <b className="text-ink">Lower bound ("guaranteed").</b> The share of simulated seasons in which the club gets there <i>whatever</i> the unplayed scores turn out to be.
        </li>
        <li>
          <b className="text-ink">Upper bound ("possible").</b> The share of simulated seasons in which the club <i>could</i> get there if the scores fell its way.
        </li>
      </ul>
      <p>
        According to the model, the real chance lies somewhere in between. A narrow range means the points already settle the matter; a wide range means goal difference (or a decider that is never simulated) could swing it.
        {top ? (
          <>
            {" "}
            Example: {top.name} is shown at <b className="text-ink">{rangeText(top.title)}</b> for the title. In at least {fmtPct(top.title.guaranteed)} of the simulated seasons they win the league however the unplayed scores fall, and in up to {fmtPct(top.title.possible)} they could{gap > 0.0005 ? `; the ${(gap * 100).toFixed(1)} percentage-point gap is the part that only goals could decide` : "; the points leave almost nothing to goals"}.
          </>
        ) : null}
      </p>
      <p>These are ranges, not predictions and not exact probabilities. They leave out the model's own uncertainty, which is probably a little too small, and they say nothing about points deductions that are not in our data.</p>
    </div>
  );
}

function RangeTechnical({ pb }) {
  const maxSe = Math.max(0, ...pb.clubs.flatMap((c) => pb.bands.flatMap((b) => [c[b.id].se_guaranteed ?? 0, c[b.id].se_possible ?? 0])));
  const r = pb.rules;
  return (
    <details className="rounded-2xl border border-white/5 bg-panel p-3" data-testid="ranges-technical">
      <summary className="cursor-pointer text-[13px] font-bold">Method, rules used and limitations of the ranges</summary>
      <div className="mt-3 space-y-3 text-xs text-mute">
        <p>{pb.method}</p>
        <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-2">
          <Row k="Lower bound" v={pb.meaning.guaranteed} />
          <Row k="Upper bound" v={pb.meaning.possible} />
          <Row k="Unresolved" v={pb.meaning.unresolved} />
          <Row k="Largest sampling error" v={`about ±${(196 * maxSe).toFixed(1)} percentage points (${pb.monte_carlo.simulations.toLocaleString()} simulations, seed ${pb.monte_carlo.seed})`} />
          <Row k="Tie groups" v={`${pb.ties.tie_groups.toLocaleString()} groups of clubs level on points across the simulations; ${pb.ties.tie_groups_fully_decided.toLocaleString()} fully settled by the rules and the known results`} />
          <Row k="Rule profile" v={`${r.profile_id}, ${r.status}`} />
          <Row k="Two clubs level on points" v={r.criteria_used.two_clubs.map((c) => c.replace(/_/g, " ")).join(", then ")} />
          <Row k="Three or more clubs level" v={r.criteria_used.three_or_more_clubs.map((c) => c.replace(/_/g, " ")).join(", then ")} />
        </dl>
        {r.sources?.length > 0 && (
          <p>
            Sources:{" "}
            {r.sources.map((s, i) => (
              <span key={s.url}>
                {i ? "; " : ""}
                <a className="font-semibold text-pitch underline" href={s.url} target="_blank" rel="noreferrer">
                  {s.title.split(",")[0]}
                </a>
              </span>
            ))}
            .
          </p>
        )}
        <div>
          <h4 className="mb-1 text-xs font-bold text-ink">Limitations of the ranges</h4>
          <ul className="list-disc space-y-1 pl-5">
            {pb.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </div>
        {r.interpretation_notes?.length > 0 && (
          <div>
            <h4 className="mb-1 text-xs font-bold text-ink">Rule interpretations</h4>
            <ul className="list-disc space-y-1 pl-5">
              {r.interpretation_notes.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </details>
  );
}

function PositionRanges({ pb }) {
  const [open, setOpen] = useState(null);
  if (!pb) {
    return (
      <Notice tone="info" title="Position ranges:">
        this saved run has none (it was saved before position ranges were added).
      </Notice>
    );
  }
  if (pb.status !== "available") {
    return (
      <Notice tone="warn" title="Position ranges are not available for this run:">
        {pb.reason}
      </Notice>
    );
  }
  if (!rangesAreValid(pb)) {
    return (
      <Notice tone="bad" title="Position ranges hidden:">
        the values failed a consistency check (a lower bound above its upper bound, or a value outside 0–100%), so nothing is shown rather than something wrong.
      </Notice>
    );
  }
  const pending = pb.rules?.live_confirmation;
  return (
    <div className="space-y-3" data-testid="position-ranges">
      <Card title="Where could each club finish?" subtitle={`${RANGES_LABEL}. Experimental.`}>
        <div className="space-y-3">
          <RangesExplainer pb={pb} />
          {pending ? <Notice tone="warn" title="League rules:">live-document confirmation pending. The federation file has not been checked against its checksum yet, so these ranges rest on the archived copy of the rules.</Notice> : null}
          <div className="overflow-hidden rounded-2xl border border-white/5 bg-panel" role="list" aria-label="Position ranges for every club">
            <div className="hidden grid-cols-[minmax(8rem,1fr)_repeat(3,minmax(7rem,10rem))] items-center gap-x-3 border-b border-line/60 px-3 py-2 text-[11px] font-semibold text-mute sm:grid">
              <span>Club (listed by expected points)</span>
              {pb.bands.map((b) => (
                <span key={b.id} title={placesText(b)}>
                  {b.label} <span className="font-normal">({placesText(b)})</span>
                </span>
              ))}
            </div>
            {pb.clubs.map((c) => (
              <div key={c.entity_id} role="listitem" className="border-b border-line/40 last:border-b-0">
                <button
                  onClick={() => setOpen(open === c.entity_id ? null : c.entity_id)}
                  aria-expanded={open === c.entity_id}
                  title="Show or hide the details of these ranges"
                  className="grid w-full grid-cols-3 items-start gap-x-3 gap-y-1 px-3 py-2 text-left text-sm sm:grid-cols-[minmax(8rem,1fr)_repeat(3,minmax(7rem,10rem))]"
                >
                  <span className="col-span-3 flex min-w-0 items-center gap-2 sm:col-span-1">
                    <TeamAvatar name={c.name} size={24} />
                    <span className="truncate font-semibold">{c.name}</span>
                  </span>
                  {pb.bands.map((b) => (
                    <RangeCell key={b.id} band={b} v={c[b.id]} />
                  ))}
                </button>
                {open === c.entity_id && <RangeDetail club={c} bands={pb.bands} />}
              </div>
            ))}
          </div>
          <p className="text-[11px] text-mute">
            Bars: the solid part is the lower bound, the lighter part up to the upper bound is what only the unplayed scores could decide. Values are rounded to 0.1 percentage points; <b>{"<0.1%"}</b> means above zero but below 0.05%.
          </p>
        </div>
      </Card>
      <RangeTechnical pb={pb} />
    </div>
  );
}

export default function SeasonSimulator() {
  const [mode, setMode] = useState("points");
  const [key, setKey] = useState("BUNDESLIGA");
  const [season, setSeason] = useState("");
  const [sims, setSims] = useState("");
  const [seed, setSeed] = useState("");
  const [experimental, setExperimental] = useState(false);
  const [run, setRun] = useState({ loading: false, error: null, result: null });
  const [version, setVersion] = useState(0);
  const gws = useApi("/api/gameweeks", { key, season });
  const st = useApi("/api/season/status", { key, season: gws.data?.season ?? season, v: version });
  const runs = useApi(st.data ? "/api/season/runs" : null, { key, season: st.data?.season, v: version });
  const ctl = useRef(null);
  useEffect(() => () => ctl.current?.abort(), []);
  useEffect(() => setRun({ loading: false, error: null, result: null }), [key, season, mode]);

  const s = st.data;
  const limits = s?.limits;
  const simsValue = sims || (limits ? String(limits.default) : "");
  const invalid = validateSims(simsValue, limits) || (seed !== "" && !/^\d+$/.test(seed) ? "Seed must be a whole number (or empty)." : null);
  const points = mode === "points";
  const canRun = points ? s?.points_only?.can_run : s?.can_simulate;
  const blockers = points ? s?.points_only?.blockers : s?.blockers;

  async function simulate() {
    ctl.current?.abort();
    ctl.current = new AbortController();
    setRun({ loading: true, error: null, result: null });
    const body = { key, season: s.season, user_action: points ? POINTS_ACTION : SIM_ACTION, simulations: Number(simsValue), seed: seed === "" ? null : Number(seed), include_experimental: !points && experimental };
    try {
      const result = await api(points ? "/api/season/points" : "/api/season/simulate", undefined, { signal: ctl.current.signal, method: "POST", body });
      setRun({ loading: false, error: null, result });
      setVersion((v) => v + 1);
    } catch (error) {
      if (error.name !== "AbortError") setRun({ loading: false, error, result: null });
    }
  }

  async function load(id) {
    setRun({ loading: true, error: null, result: null });
    try {
      const result = await api("/api/season/run", { id });
      setMode(result.assumptions.mode === "points_only" ? "points" : "full");
      setRun({ loading: false, error: null, result });
    } catch (error) {
      setRun({ loading: false, error, result: null });
    }
  }

  const r = run.result;
  const shown = r && (r.assumptions.mode === "points_only") === points ? r : null;
  const labelOf = (k) => ({ BUNDESLIGA: "Bundesliga", LALIGA: "La Liga", EPL: "Premier League", SERIEA: "Serie A", LIGUE1: "Ligue 1" })[k];
  return (
    <div className="space-y-4" data-testid="season-simulator">
      <header className="px-1">
        <h1 className="text-xl font-extrabold">Season simulator</h1>
        <p className="mt-1 text-sm text-mute">Monte Carlo simulation of the rest of a league season from the frozen club model. Runs only when you press the button. Estimates, not certainties and not betting advice.</p>
      </header>

      <Card>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="League">
            <Select aria-label="League" value={key} onChange={(v) => { setKey(v); setSeason(""); setSims(""); }} options={SEASON_LEAGUES.map((k) => ({ value: k, label: labelOf(k) }))} />
          </Field>
          <Field label="Season">
            <Select aria-label="Season" value={gws.data?.season ?? ""} onChange={setSeason} options={(gws.data?.seasons ?? []).map((x) => ({ value: x, label: x }))} disabled={!gws.data} />
          </Field>
        </div>
        <div className="mt-4">
          {st.loading && <Spinner label="Checking data quality…" />}
          <ErrorBox error={st.error} />
          {s && <EligibilityBanner st={s} />}
        </div>
      </Card>

      <Tabs
        label="Simulation mode"
        value={mode}
        onChange={setMode}
        tabs={[
          { value: "points", label: "Points-only (experimental)" },
          { value: "full", label: "Final positions (disabled)" },
        ]}
      />

      {s && !points && <RulesNotice rp={s.rule_profile} />}

      {s && points && (
        <Notice tone="warn" title={POINTS_LABEL}>
          Simulates win, draw and loss only (3 / 1 / 0 points) and shows how many points each club may finish with. It does not predict a league table or exact chances. Title, top-four and relegation appear only as ranges (a lower and an upper bound), because ties on points are settled by goals and scores are not simulated.
        </Notice>
      )}

      {s && (
        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <Field label="Simulations" hint={limits ? `${limits.min.toLocaleString()}–${limits.max.toLocaleString()}, default ${limits.default.toLocaleString()}` : ""}>
              <Input type="number" inputMode="numeric" value={simsValue} onChange={(e) => setSims(e.target.value)} aria-label="Simulations" />
            </Field>
            <Field label="Seed (optional)" hint="Same seed and data give identical results.">
              <Input type="text" inputMode="numeric" placeholder="random" value={seed} onChange={(e) => setSeed(e.target.value.trim())} aria-label="Seed" />
            </Field>
            {!points && (
              <label className="flex cursor-pointer select-none items-center gap-2 pb-3 text-xs text-mute hover:text-text">
                <input
                  type="checkbox"
                  className="h-4 w-4 shrink-0 cursor-pointer rounded accent-[#8b7bff] focus:outline-none focus:ring-2 focus:ring-pitch"
                  checked={experimental}
                  onChange={(e) => setExperimental(e.target.checked)}
                />
                <span>Also show experimental club v2-r1 comparison</span>
              </label>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button onClick={simulate} disabled={!canRun || Boolean(invalid) || run.loading}>
              {run.loading ? "Simulating…" : points ? "Run points-only simulation" : "Run season simulation"}
            </Button>
            {canRun && !invalid && <span className="text-xs text-mute">Saves this run to the history below.</span>}
          </div>
          {!canRun && (
            <div className="mt-3 space-y-2" data-testid="blockers">
              <Notice tone="warn" title={points ? "Points-only simulation is disabled for this league" : "Final-position simulation is disabled"}>
                <ul className="list-disc space-y-1 pl-5">
                  {(blockers ?? []).map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </Notice>
            </div>
          )}
          {invalid && <div className="mt-2"><Notice tone="warn">{invalid}</Notice></div>}
        </Card>
      )}

      {run.loading && <Spinner label="Simulating… the first run can take about a minute while the model history loads." />}
      <ErrorBox error={run.error} />

      {shown && points && (
        <div className="space-y-4" data-testid="points-result">
          <Notice tone={shown.assumptions.eligibility.state === "ready" ? "info" : "warn"} title={`${POINTS_LABEL} · data quality: ${STATE[shown.assumptions.eligibility.state]?.label ?? shown.assumptions.eligibility.state}`}>
            Run {shown.run_id}, saved {shown.assumptions.created_utc} UTC, {shown.assumptions.simulations.toLocaleString()} simulations, seed {shown.assumptions.seed}, data through {shown.assumptions.data_cutoff.latest_result_in_competition}. {shown.assumptions.eligibility.reasons.join(" ")}
          </Notice>
          <div className="flex flex-wrap gap-2">
            <Badge badge="Validated club model v1 (probabilities)" title="Club v1 is the validated club model for this league" />
            <span className="rounded-full bg-warn/15 px-2 py-0.5 text-[11px] font-semibold text-warn">{POINTS_LABEL}</span>
            {shown.result.position_bounds?.status === "available" && <span className="rounded-full bg-warn/15 px-2 py-0.5 text-[11px] font-semibold text-warn">{RANGES_LABEL}</span>}
          </div>
          <h2 className="px-1 text-[15px] font-bold">Expected final points</h2>
          <PointsResult summary={shown.result.summary} />
          <PositionRanges pb={shown.result.position_bounds} />
          <Assumptions a={shown.assumptions} st={s} mode={mode} />
        </div>
      )}

      {shown && !points && (
        <div className="space-y-4" data-testid="season-result">
          <Notice tone={r.assumptions.eligibility.state === "ready" ? "info" : "warn"} title={`Data quality: ${STATE[r.assumptions.eligibility.state]?.label ?? r.assumptions.eligibility.state}`}>
            Run {r.run_id}, saved {r.assumptions.created_utc} UTC, {r.assumptions.simulations.toLocaleString()} simulations, seed {r.assumptions.seed}, data through {r.assumptions.data_cutoff.latest_result_in_competition}. {r.assumptions.eligibility.reasons.join(" ")}
          </Notice>
          <div className="flex flex-wrap gap-2">
            <Badge badge="Validated club model v1 (probabilities)" title="Club v1 is the validated club model for this league" />
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-mute">Scoreline: {r.assumptions.scoreline.method}</span>
            {r.assumptions.scoreline.validation?.approved_by_user ? null : <span className="rounded-full bg-bad/15 px-2 py-0.5 text-[11px] font-semibold text-bad">Scoreline method not approved: diagnostic output</span>}
            {r.result.summary.final_position_probabilities_supported === false && <span className="rounded-full bg-bad/15 px-2 py-0.5 text-[11px] font-semibold text-bad">Some probabilities withheld: unresolved ties</span>}
          </div>
          <h2 className="px-1 text-[15px] font-bold">Projected final standings</h2>
          <ResultTable summary={r.result.summary} bands={r.result.positions.bands} />
          <Card title="Finishing-position probabilities" subtitle="Share of simulations in which each club finishes in each position">
            <Heatmap teams={r.result.summary.teams} />
          </Card>
          {r.result.summary.tie_resolution && (
            <p className="px-1 text-xs text-mute">
              Ties: an unresolved tie (play-off or similar, never simulated) occurred in {(r.result.summary.tie_resolution.share_with_an_unresolved_tie * 100).toFixed(2)}% of simulations; affected probabilities are withheld and shown as bounds.
            </p>
          )}
          {r.result.experimental && <SectionExperimental ex={r.result.experimental} />}
          <Assumptions a={r.assumptions} st={s} mode={mode} />
        </div>
      )}

      {!shown && s && <Assumptions a={null} st={s} mode={mode} />}

      {runs.data?.length > 0 && (
        <Card title="Saved simulation runs" subtitle="Application history, separate from the official prospective evaluation">
          <ul className="divide-y divide-line/60 text-sm">
            {runs.data.map((x) => (
              <li key={x.run_id} className="flex items-center justify-between gap-3 py-2">
                <span className="text-xs text-mute">
                  Run {x.run_id} · {x.mode === "points_only" ? "points-only (experimental)" : "final positions"} · {x.created_utc} · {x.n_simulations.toLocaleString()} sims · seed {x.seed}
                </span>
                <Button variant="ghost" onClick={() => load(x.run_id)}>
                  View
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function SectionExperimental({ ex }) {
  return (
    <Card title="Experimental comparison" subtitle={ex.label}>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-mute">
              <th className="py-1">Club</th>
              <th className="text-right">Exp. points</th>
              <th className="text-right">Title</th>
              <th className="text-right">Top 4</th>
              <th className="text-right">Relegation</th>
            </tr>
          </thead>
          <tbody>
            {ex.teams.map((t) => (
              <tr key={t.name} className="border-t border-line/40">
                <td className="py-1 font-semibold">{t.name}</td>
                <td className="text-right tabular-nums">{t.expected_points.toFixed(1)}</td>
                <td className="text-right tabular-nums">{pb(t, "p_title")}</td>
                <td className="text-right tabular-nums">{pb(t, "p_top4")}</td>
                <td className="text-right tabular-nums">{pb(t, "p_relegation")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
