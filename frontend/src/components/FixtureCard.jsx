import { useState } from "react";
import { pct } from "../lib/format.js";
import { FLAG_LABELS, kickoffOf, kickoffText } from "../lib/fixtures.js";
import { shortDate } from "../lib/team.js";
import { Chip, FormDots, TeamAvatar } from "./ui.jsx";

const STATUS = { scheduled: ["Scheduled", "info"], awaiting_result: ["Awaiting verified result", "warn"], completed: ["Full time", "ok"], awarded: ["Awarded", "info"], postponed: ["Postponed", "warn"], cancelled: ["Cancelled", "bad"] };

const BAR = { home: "bg-home", draw: "bg-draw", away: "bg-away" };

// Three outcomes as one bar with the actual team names under it. `experimental` draws the club v2-r1 candidate thinner, with a dashed edge, so it cannot be mistaken for the validated v1.
function MiniProb({ p, home, away, experimental = false }) {
  const segs = [
    ["home", p.home, `${home} win`],
    ["draw", p.draw, "Draw"],
    ["away", p.away, `${away} win`],
  ];
  const top = Math.max(p.home, p.draw, p.away);
  return (
    <div>
      <div className={`flex overflow-hidden rounded-full ${experimental ? "h-1.5 opacity-80 outline outline-1 outline-dashed outline-line-strong" : "h-3"}`} role="img" aria-label={segs.map((s) => `${s[2]} ${pct(s[1])}`).join(", ")}>
        {segs.map((s) => (
          <div key={s[0]} className={BAR[s[0]]} style={{ width: `${s[1] * 100}%` }} />
        ))}
      </div>
      <div className="mt-1.5 grid grid-cols-3 gap-1 text-xs tabular-nums">
        {segs.map((s, i) => (
          <span key={s[0]} className={`min-w-0 ${i === 1 ? "text-center" : i === 2 ? "text-right" : ""} ${s[1] === top ? "font-extrabold text-ink" : "text-mute"}`}>
            <span className="block truncate">{s[0] === "draw" ? "Draw" : s[0] === "home" ? home : away}</span>
            {pct(s[1], 0)}
          </span>
        ))}
      </div>
    </div>
  );
}

// One fixture of a gameweek: teams, date/kickoff knowledge, status, data-reliability flags, saved forecast and predicted-versus-actual.
export default function FixtureCard({ f, sharedWarningId }) {
  const [open, setOpen] = useState(false);
  const d = shortDate(f.date);
  const fc = f.forecast;
  const [statusLabel, statusTone] = STATUS[f.status] ?? [f.status, "info"];
  const flagChips = [...new Map(f.flags.map((x) => [FLAG_LABELS[x]?.[0] ?? x, FLAG_LABELS[x]?.[1] ?? "info"])).entries()];
  const time = kickoffText(kickoffOf(f));
  const ev = f.evaluation;
  return (
    <article className="min-w-0 rounded-card border border-line bg-panel p-4 shadow-card" aria-label={`${f.home} v ${f.away}`} aria-describedby={sharedWarningId}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-mute">
        <span className="font-semibold text-ink/80">
          {d.day} {d.year}
        </span>
        <span>{time}</span>
        <Chip tone={statusTone}>{statusLabel}</Chip>
        {f.reliability === "full" && f.predictable && <Chip tone="ok">Fully supported history</Chip>}
      </div>
      {!sharedWarningId && f.reliability === "provisional" && f.reasons?.length > 0 && <p className="mt-2 rounded-lg border border-warn/40 bg-warn/10 px-2.5 py-1.5 text-xs text-ink-2">Why provisional: {f.reasons[0]}</p>}

      <div className="mt-3 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <TeamAvatar name={f.home} size={34} />
          <span className="truncate text-sm font-bold">{f.home}</span>
        </div>
        <div className="text-center">
          {f.result ? <span className="text-lg font-extrabold tabular-nums">{f.result.home} – {f.result.away}</span> : <span className="text-xs font-bold text-mute">vs</span>}
        </div>
        <div className="flex min-w-0 items-center justify-end gap-2">
          <span className="truncate text-right text-sm font-bold">{f.away}</span>
          <TeamAvatar name={f.away} size={34} />
        </div>
      </div>

      {fc && (
        <div className="mt-3">
          <MiniProb p={fc.predictions.primary} home={f.home} away={f.away} />
          <p className="mt-1.5 text-xs text-mute">
            Saved {fc.created_utc.replace("T", " ").replace("Z", " UTC")} · club v1 (validated) · history through {fc.data_cutoff_date}
          </p>
          {fc.predictions.secondary && (
            <div className="mt-3 rounded-lg border border-dashed border-line-strong p-2">
              <p className="mb-1 text-xs font-semibold text-mute">Experimental candidate · club v2-r1</p>
              <MiniProb p={fc.predictions.secondary} home={f.home} away={f.away} experimental />
            </div>
          )}
        </div>
      )}

      {ev && (
        <p className={`mt-2 rounded-lg px-2.5 py-1.5 text-xs font-semibold ${ev.correct ? "bg-ok/15 text-ok" : "bg-bad/15 text-bad"}`}>
          Predicted {ev.predicted === "H" ? "home win" : ev.predicted === "A" ? "away win" : "draw"}, actual {ev.actual === "H" ? "home win" : ev.actual === "A" ? "away win" : "draw"} {ev.correct ? "✓" : "✗"} · probability given to the actual outcome {pct(ev.p_actual, 0)}
          {!ev.counted && <span className="block font-normal text-mute">{ev.note}</span>}
        </p>
      )}

      {flagChips.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {flagChips.map(([label, tone]) => (
            <Chip key={label} tone={tone}>{label}</Chip>
          ))}
        </div>
      )}

      <button onClick={() => setOpen(!open)} aria-expanded={open} className="mt-2 inline-flex min-h-11 min-w-11 items-center text-xs font-semibold text-accent">
        {open ? "Hide details" : "Details"}
      </button>
      {open && (
        <div className="mt-2 space-y-3 border-t border-line/60 pt-3 text-xs text-mute">
          {[["home", f.home], ["away", f.away]].map(([side, name]) => (
            <div key={side} className="flex flex-wrap items-center gap-2">
              <span className="w-32 truncate font-semibold text-ink/80">{name}</span>
              {f.form[side].length ? <FormDots results={f.form[side].map((m) => m.result)} size={18} /> : <span>no earlier results in the data</span>}
              <span className="text-xs">last {f.form[side].length}, only matches before this date</span>
            </div>
          ))}
          {fc && (
            <div className="space-y-0.5">
              {[["primary", "Club v1 (validated)"], ["secondary", "Club v2-r1 (experimental, development-validated only)"], ["elo_only", "Elo-only baseline"]].map(([k, label]) =>
                fc.predictions[k] ? (
                  <p key={k}>
                    <span className="text-ink/80">{label}:</span> home {pct(fc.predictions[k].home)}, draw {pct(fc.predictions[k].draw)}, away {pct(fc.predictions[k].away)}
                  </p>
                ) : null,
              )}
              <p>
                Saved before kickoff: <strong className="text-ink/80">{fc.made_before_kickoff}</strong> · models {Object.values(fc.models).join("; ")}
              </p>
            </div>
          )}
          {f.reasons.map((r) => (
            <p key={r}>• {r}</p>
          ))}
        </div>
      )}
    </article>
  );
}
