import { kickoffParts } from "../lib/fixtures.js";

// A kickoff cell: the time exactly as the store has it and, when its time zone is not verified, a visible note. Nothing is converted, and no clock decides anything here.
export default function Kickoff({ k, className = "" }) {
  const p = kickoffParts(k);
  return (
    <span className={`block leading-tight ${className}`} title={p.note ? "Published as a local time without a time zone; it is shown as stored and not converted" : undefined}>
      <span className="block text-xs font-semibold text-ink-2">{p.time}</span>
      {p.note && <span className="block text-xs text-mute">{p.note}</span>}
    </span>
  );
}
