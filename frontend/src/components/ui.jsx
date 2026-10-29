import { useId, useRef } from "react";
import { Link } from "react-router-dom";
import { badgeTone } from "../lib/format.js";
import { shortDate } from "../lib/team.js";
import Icon from "./Icon.jsx";
import TeamCrest from "./TeamCrest.jsx";

export { Icon, TeamCrest };

// Shared building blocks. Colours come from the tokens in src/index.css; nothing here fetches or computes football data.

const TONES = {
  ok: "text-ok border-ok/40 bg-ok/10",
  warn: "text-warn border-warn/40 bg-warn/10",
  bad: "text-bad border-bad/40 bg-bad/10",
  info: "text-info border-info/40 bg-info/10",
};
const TONE_TEXT = { ok: "text-ok", warn: "text-warn", bad: "text-bad", info: "text-info" };
const NOTICE_ICON = { ok: "check", warn: "alert", bad: "alert", info: "info" };

export function Card({ title, subtitle, children, className = "", right }) {
  return (
    <section className={`min-w-0 rounded-card border border-line bg-panel p-4 shadow-card sm:p-5 ${className}`}>
      {(title || right) && (
        <header className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            {title && <h2 className="text-base font-bold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-mute">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

export function Badge({ badge, title }) {
  return (
    <span title={title} className={`inline-flex items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${TONES[badgeTone(badge)]}`}>
      {badge}
    </span>
  );
}

const CHIP_TONES = { ...TONES, neutral: "text-mute border-line bg-white/5", hero: "text-ink border-white/20 bg-black/25" }; // hero: on the gradient hero card, where mute would be under 4.5:1

// Small status label (fixture status, data-reliability flags). `neutral` is the quiet default.
export function Chip({ tone = "neutral", children, title }) {
  return (
    <span title={title} className={`inline-flex items-center whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-semibold ${CHIP_TONES[tone] ?? CHIP_TONES.neutral}`}>
      {children}
    </span>
  );
}

export function Notice({ tone = "info", children, title }) {
  return (
    <div role={tone === "bad" ? "alert" : "note"} className={`flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 text-[0.8125rem] leading-snug ${TONES[tone]}`}>
      <Icon name={NOTICE_ICON[tone] ?? "info"} className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0 text-ink-2">
        {title && <strong className={`mr-1 ${TONE_TEXT[tone] ?? ""}`}>{title}</strong>}
        {children}
      </div>
    </div>
  );
}

export function Spinner({ label = "Loading…" }) {
  return (
    <div role="status" className="flex items-center gap-3 py-8 text-sm text-mute">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line-strong border-t-accent" aria-hidden="true" />
      {label}
    </div>
  );
}

const reload = () => window.location.reload();

export function ErrorBox({ error, onRetry = reload }) {
  if (!error) return null;
  return (
    <div role="alert" className="rounded-card border border-bad/40 bg-bad/10 p-4 text-sm text-bad">
      <p className="font-semibold">Something went wrong</p>
      <p className="mt-1 break-words text-ink-2">{error.message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 inline-flex min-h-11 items-center rounded-full border border-bad/60 px-5 text-sm font-semibold text-bad hover:bg-bad/15">
          Try again
        </button>
      )}
    </div>
  );
}

export function Empty({ children }) {
  return <p className="rounded-card border border-dashed border-line-strong px-4 py-8 text-center text-sm text-mute">{children}</p>;
}

export function Kpi({ label, value, hint }) {
  return (
    <div className="min-w-0 rounded-card border border-line bg-panel px-4 py-3.5 shadow-card">
      <div className="text-xl font-extrabold tabular-nums text-ink">{value}</div>
      <div className="text-xs text-mute">{label}</div>
      {hint && <div className="mt-0.5 text-xs text-mute-2">{hint}</div>}
    </div>
  );
}

export function Field({ label, children, hint }) {
  return (
    <label className="flex min-w-[10rem] flex-1 flex-col gap-1.5 text-xs font-medium text-mute">
      {label}
      {children}
      {hint && <span className="text-xs font-normal text-mute-2">{hint}</span>}
    </label>
  );
}

// Controls: 44 px tall, edge 3:1 or more against every surface (--color-line-strong), accent edge on focus.
// CONTROL_EDGE is shared with the few screens that draw their own select; they add their own background, radius and width.
export const CONTROL_EDGE = "min-h-11 border border-line-strong px-3 text-sm text-ink placeholder:text-mute-2 hover:border-accent/70 focus:border-accent disabled:cursor-not-allowed disabled:opacity-50";
const CONTROL = `w-full rounded-control bg-panel-2 ${CONTROL_EDGE}`;

export function Select({ value, onChange, options, placeholder, disabled, ...rest }) {
  return (
    <select value={value ?? ""} onChange={(e) => onChange(e.target.value)} disabled={disabled} className={CONTROL} {...rest}>
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((o) => {
        const v = typeof o === "string" ? o : o.value;
        const l = typeof o === "string" ? o : o.label;
        return (
          <option key={v} value={v}>
            {l}
          </option>
        );
      })}
    </select>
  );
}

export function Input(props) {
  return <input className={CONTROL} {...props} />;
}

const BUTTON_BASE = "inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-full px-5 text-sm font-bold transition disabled:cursor-not-allowed";
const BUTTON_STYLES = {
  // white on both ends of the gradient: 5.2:1 and 7.2:1
  primary: "bg-gradient-to-r from-primary-hi to-primary-lo text-on-primary shadow-glow hover:brightness-110 active:brightness-95 disabled:bg-none disabled:bg-panel-2 disabled:text-mute-2 disabled:shadow-none",
  secondary: "border border-line-strong bg-panel-2 text-ink hover:bg-panel-3 disabled:opacity-50",
};
BUTTON_STYLES.ghost = BUTTON_STYLES.secondary; // the name used by existing screens
// on the gradient hero card: `light` is the call to action (dark text on near-white, 17:1), `glass` the quieter one (light text on darkened glass,
// with an edge that is at least 3:1 against every stop of the gradient, see tests/design-tokens.test.js)
BUTTON_STYLES.light = "bg-ink text-bg shadow-card hover:bg-white disabled:opacity-60";
BUTTON_STYLES.glass = "border border-white/50 bg-black/30 text-ink hover:bg-black/45 disabled:opacity-60";

export function Button({ children, variant = "primary", className = "", type = "button", ...rest }) {
  return (
    <button type={type} className={`${BUTTON_BASE} ${BUTTON_STYLES[variant] ?? BUTTON_STYLES.primary} ${className}`} {...rest}>
      {children}
    </button>
  );
}

// A link that looks like a button (navigation, never an action).
export function ButtonLink({ to, children, variant = "secondary", className = "", ...rest }) {
  return (
    <Link to={to} className={`${BUTTON_BASE} ${BUTTON_STYLES[variant] ?? BUTTON_STYLES.secondary} ${className}`} {...rest}>
      {children}
    </Link>
  );
}

/* ---------------------------------------------------------------- keyboard support for Pills and Tabs */

// Arrow keys, Home and End, counted from the control that has focus (the selected one when focus is elsewhere).
// `select` is called with the new index; the new item receives focus.
function arrowKeys(e, count, selected, refs, select) {
  const focused = refs.current.indexOf(document.activeElement);
  const from = focused >= 0 ? focused : selected;
  const target = { ArrowRight: from + 1, ArrowDown: from + 1, ArrowLeft: from - 1, ArrowUp: from - 1, Home: 0, End: count - 1 }[e.key];
  if (target === undefined || count === 0) return;
  e.preventDefault();
  const next = (target + count) % count;
  refs.current[next]?.focus();
  select(next);
}

const valueOf = (o) => (typeof o === "string" ? o : o.value);
const labelOf = (o) => (typeof o === "string" ? o : o.label);

// Single-choice pill filter (radio group). Arrow keys move and select; only the selected pill is a tab stop.
export function Pills({ options, value, onChange, label, wrap = false }) {
  const refs = useRef([]);
  const values = options.map(valueOf);
  const current = Math.max(0, values.indexOf(value)); // the one pill that is a tab stop (the first one when nothing matches)
  return (
    <div role="radiogroup" aria-label={label} onKeyDown={(e) => arrowKeys(e, values.length, current, refs, (i) => onChange(values[i]))} className={`no-scrollbar -mx-4 -my-1 flex gap-2 overflow-x-auto px-4 py-1 ${wrap ? "!mx-0 flex-wrap !overflow-visible !px-0" : ""}`}>
      {options.map((o, i) => {
        const on = valueOf(o) === value;
        return (
          <button
            key={valueOf(o)}
            ref={(el) => (refs.current[i] = el)}
            type="button"
            role="radio"
            aria-checked={on}
            tabIndex={i === current ? 0 : -1}
            onClick={() => onChange(valueOf(o))}
            className={`inline-flex min-h-11 shrink-0 items-center whitespace-nowrap rounded-full px-4 text-sm font-semibold transition-colors ${
              on ? "bg-gradient-to-r from-primary-hi to-primary-lo text-on-primary shadow-glow" : "border border-line-strong bg-panel-2 text-ink hover:bg-panel-3"
            }`}
          >
            {labelOf(o)}
          </button>
        );
      })}
    </div>
  );
}

// Underlined tab strip. Arrow keys, Home and End move focus; Enter or Space activates (manual activation: some panels load data).
// Pass `idBase` to link each tab to a <TabPanel idBase=... value=...> with aria-controls / aria-labelledby.
export function Tabs({ tabs, value, onChange, label = "Sections", idBase }) {
  const auto = useId();
  const base = idBase ?? auto;
  const refs = useRef([]);
  const values = tabs.map(valueOf);
  const current = Math.max(0, values.indexOf(value));
  return (
    <div role="tablist" aria-label={label} onKeyDown={(e) => arrowKeys(e, values.length, current, refs, () => {})} className="no-scrollbar -mx-4 flex gap-6 overflow-x-auto border-b border-line px-4 sm:mx-0 sm:px-0">
      {tabs.map((t, i) => {
        const v = valueOf(t);
        const on = v === value;
        return (
          <button
            key={v}
            ref={(el) => (refs.current[i] = el)}
            type="button"
            role="tab"
            id={`${base}-tab-${v}`}
            aria-selected={on}
            aria-controls={idBase ? `${idBase}-panel-${v}` : undefined}
            tabIndex={i === current ? 0 : -1}
            onClick={() => onChange(v)}
            className={`-mb-px inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center border-b-[3px] px-0.5 text-sm font-semibold transition-colors focus-visible:-outline-offset-2 ${on ? "border-accent text-ink" : "border-transparent text-mute hover:text-ink"}`}
          >
            {labelOf(t)}
          </button>
        );
      })}
    </div>
  );
}

// The panel is named by its tab, unless `label` gives it a name of its own (use that when the tab's name is also the name of a control inside the panel).
export function TabPanel({ idBase, value, label, children, className = "" }) {
  return (
    <div role="tabpanel" id={`${idBase}-panel-${value}`} aria-label={label} aria-labelledby={label ? undefined : `${idBase}-tab-${value}`} className={className}>
      {children}
    </div>
  );
}

// Summary line of a <details class="group"> disclosure: 44 px tall, with a chevron that turns when it is open.
// `onHero` is for the gradient card, where `accent` is under 4.5:1 and the text is `ink`; `large` is 14 px instead of 12 px.
export function Summary({ children, className = "", onHero = false, large = false }) {
  return (
    <summary className={`flex min-h-11 cursor-pointer select-none items-center gap-1.5 font-semibold [&::-webkit-details-marker]:hidden ${large ? "text-sm" : "text-xs"} ${onHero ? "text-ink hover:text-white" : "text-accent hover:text-ink"} ${className}`}>
      <Icon name="chevron" className="h-4 w-4 shrink-0 transition-transform group-open:rotate-90" />
      {children}
    </summary>
  );
}

// Badge for a team (see TeamCrest): a licensed crest when one is listed, otherwise generated letters on a name-based colour.
export const TeamAvatar = TeamCrest;

// League-style section header (competition header in score apps).
export function SectionCard({ avatar, title, subtitle, right, children }) {
  return (
    <section className="min-w-0 overflow-hidden rounded-card border border-line bg-panel shadow-card">
      <header className="flex items-center gap-3 px-4 py-3.5">
        {avatar}
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-base font-bold">{title}</h2>
          {subtitle && <p className="truncate text-xs text-mute">{subtitle}</p>}
        </div>
        {right}
      </header>
      {children}
    </section>
  );
}

// One finished match: date/status left, teams stacked, scores right. Winner is bold, loser muted.
export function MatchRow({ date, label, home, away, homeGoals, awayGoals, note, onClick }) {
  const d = shortDate(date);
  const hw = homeGoals > awayGoals;
  const aw = awayGoals > homeGoals;
  const Row = onClick ? "button" : "div";
  return (
    <Row onClick={onClick} {...(onClick ? {} : { role: "group", "aria-label": `${home} ${homeGoals}, ${away} ${awayGoals}` })} className="flex min-h-11 w-full items-center gap-3 border-t border-line/70 px-4 py-2.5 text-left">
      <div className="w-14 shrink-0 text-center text-xs leading-tight text-mute">
        <div className="font-semibold text-ink-2">{d.day}</div>
        <div>{d.year}</div>
        <div className="mt-0.5 text-xs font-semibold uppercase tracking-wide">{label || "FT"}</div>
      </div>
      <div className="min-w-0 flex-1 space-y-1.5">
        {[
          [home, hw, aw],
          [away, aw, hw],
        ].map(([name, win, lose]) => (
          <div key={name} className="flex items-center gap-2">
            <TeamCrest name={name} size={24} />
            <span className={`truncate text-sm ${win ? "font-bold text-ink" : lose ? "text-mute" : "text-ink"}`}>{name}</span>
          </div>
        ))}
        {note && <div className="text-xs text-mute">{note}</div>}
      </div>
      <div className="w-6 shrink-0 space-y-1.5 text-right text-sm tabular-nums">
        <div className={hw ? "font-bold" : aw ? "text-mute" : ""}>{homeGoals}</div>
        <div className={aw ? "font-bold" : hw ? "text-mute" : ""}>{awayGoals}</div>
      </div>
    </Row>
  );
}

export function DataTable({ columns, rows, empty = "No rows." }) {
  if (!rows?.length) return <Empty>{empty}</Empty>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs text-mute">
            {columns.map((c, ci) => (
              <th key={`${c.header}-${ci}`} scope="col" className={`whitespace-nowrap border-b border-line-strong/60 px-2 py-2.5 font-semibold ${c.num ? "text-right" : ""}`}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id ?? i} className="hover:bg-white/[0.03]">
              {columns.map((c, ci) => (
                <td key={`${c.header}-${ci}`} className={`whitespace-nowrap border-b border-line/70 px-2 py-2.5 ${c.num ? "text-right tabular-nums" : ""}`}>
                  {c.render ? c.render(r) : r[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FormChips({ results }) {
  const tone = { W: "bg-ok text-black", D: "bg-ink-2 text-black", L: "bg-bad text-black" };
  return (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label="recent results, oldest first">
      {results.map((r, i) => (
        <span key={i} title={`${r.date} ${r.venue === "H" ? "home" : "away"} vs ${r.opponent} ${r.gf}-${r.ga}`} className={`grid h-6 w-6 place-items-center rounded-full text-xs font-extrabold ${tone[r.result]}`}>
          {r.result}
        </span>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------- score-app style pieces */

// KPI card with a coloured bottom edge (season-review style).
export function StatCard({ value, label, hint, color = "var(--color-accent-strong)" }) {
  return (
    <div className="min-w-0 rounded-card border border-line bg-panel px-4 py-3.5 shadow-card" style={{ borderBottom: `3px solid ${color}` }}>
      <div className="text-2xl font-extrabold tabular-nums">{value}</div>
      <div className="text-xs font-semibold uppercase tracking-wide text-mute">{label}</div>
      {hint && <div className="mt-0.5 text-xs text-mute-2">{hint}</div>}
    </div>
  );
}

// Small round W / D / L dots for the last results (table "Form" column).
export function FormDots({ results, size = 20 }) {
  const tone = { W: "var(--color-ok)", D: "var(--color-ink-2)", L: "var(--color-bad)" };
  return (
    <span className="inline-flex gap-1" role="img" aria-label={`last ${results.length} results, oldest first: ${results.join(" ")}`}>
      {results.map((r, i) => (
        <span key={i} aria-hidden="true" style={{ width: size, height: size, background: tone[r], fontSize: Math.max(10, size * 0.55) }} className="grid place-items-center rounded-full font-extrabold text-black">
          {r}
        </span>
      ))}
    </span>
  );
}

// One head-to-head statistic: left value, centre label, right value, and a two-sided share bar.
export function CompareRow({ label, left, right, format = (v) => v, higherIsBetter = true, leftColor = "var(--color-home)", rightColor = "var(--color-info)" }) {
  const l = left ?? 0;
  const r = right ?? 0;
  const total = Math.abs(l) + Math.abs(r) || 1;
  const lw = (Math.abs(l) / total) * 100;
  const better = l === r ? null : (l > r) === higherIsBetter ? "l" : "r";
  return (
    <div className="py-2.5">
      <div className="grid grid-cols-3 items-baseline text-center text-sm">
        <span className={`text-left font-extrabold tabular-nums ${better === "l" ? "text-ink" : "text-mute"}`}>{left == null ? "–" : format(left)}</span>
        <span className="text-xs text-mute">{label}</span>
        <span className={`text-right font-extrabold tabular-nums ${better === "r" ? "text-ink" : "text-mute"}`}>{right == null ? "–" : format(right)}</span>
      </div>
      <div className="mt-1.5 flex h-1.5 gap-1" role="img" aria-label={`${label}: ${left == null ? "n/a" : format(left)} versus ${right == null ? "n/a" : format(right)}`}>
        <div className="flex flex-1 justify-end overflow-hidden rounded-full bg-panel-2">
          <div style={{ width: `${lw}%`, background: leftColor, opacity: better === "r" ? 0.45 : 1 }} className="rounded-full" />
        </div>
        <div className="flex flex-1 overflow-hidden rounded-full bg-panel-2">
          <div style={{ width: `${100 - lw}%`, background: rightColor, opacity: better === "l" ? 0.45 : 1 }} className="rounded-full" />
        </div>
      </div>
    </div>
  );
}

// Semi-circular gauge for a probability (0-1).
export function Gauge({ value, label, color, className = "w-28 sm:w-36" }) {
  const r = 52;
  const c = Math.PI * r;
  return (
    <div className={`text-center ${className}`}>
      <svg viewBox="0 0 120 70" width="100%" role="img" aria-label={`${label} ${(value * 100).toFixed(1)}%`}>
        <path d="M 8 62 A 52 52 0 0 1 112 62" fill="none" stroke="var(--color-panel-3)" strokeWidth="10" strokeLinecap="round" />
        <path d="M 8 62 A 52 52 0 0 1 112 62" fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" strokeDasharray={`${c * value} ${c}`} />
        <text x="60" y="56" textAnchor="middle" fontSize="20" fontWeight="800" fill="var(--color-ink)">
          {(value * 100).toFixed(1)}%
        </text>
      </svg>
      <div className="-mt-1 truncate text-xs text-mute">{label}</div>
    </div>
  );
}
