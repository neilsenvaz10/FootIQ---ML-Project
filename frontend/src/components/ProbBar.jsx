import { pct } from "../lib/format.js";
import { TeamAvatar } from "./ui.jsx";

// "Win probability" block: one coloured bar (home green / draw amber / away red, as in score apps) plus 1 / X / 2 tiles.
// Values are 0-1 probabilities from the backend; nothing is computed here.
export default function ProbBar({ probs, homeLabel = "Home", awayLabel = "Away", homeName, awayName }) {
  const segs = [
    { k: "home", sign: "1", label: homeLabel, v: probs.home, grad: "linear-gradient(160deg,#27d17f,#1fa968)", text: "text-home" },
    { k: "draw", sign: "X", label: "Draw", v: probs.draw, grad: "linear-gradient(160deg,#f7d060,#e6b030)", text: "text-draw" },
    { k: "away", sign: "2", label: awayLabel, v: probs.away, grad: "linear-gradient(160deg,#ff8585,#ee5252)", text: "text-away" },
  ];
  const top = Math.max(...segs.map((s) => s.v));
  return (
    <div>
      <div className="relative flex h-28 w-full overflow-hidden rounded-2xl text-black" role="img" aria-label={segs.map((s) => `${s.label} ${pct(s.v)}`).join(", ")}>
        {segs.map((s) => (
          <div key={s.k} style={{ width: `${s.v * 100}%`, background: s.grad }} className="relative flex min-w-[2px] flex-col justify-end overflow-hidden px-2 pb-2">
            {s.v >= 0.2 && (
              <>
                {s.k === "draw" && <span className="text-xs font-bold opacity-80">Draw</span>}
                <span className="whitespace-nowrap text-xl font-extrabold leading-none sm:text-2xl">{pct(s.v)}</span>
              </>
            )}
          </div>
        ))}
        {homeName && (
          <span className="absolute left-2 top-2 rounded-full bg-white/80 p-0.5">
            <TeamAvatar name={homeName} size={30} />
          </span>
        )}
        {awayName && (
          <span className="absolute right-2 top-2 rounded-full bg-white/80 p-0.5">
            <TeamAvatar name={awayName} size={30} />
          </span>
        )}
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {segs.map((s) => (
          <div key={s.k} className={`min-w-0 rounded-2xl px-2 py-3 text-center ${s.v === top ? "bg-panel-2 ring-1 ring-inset ring-pitch/70" : "bg-panel-2/60"}`}>
            <div className={`text-xs font-bold ${s.text}`}>{s.sign}</div>
            <div className="text-xl font-extrabold tabular-nums">{pct(s.v)}</div>
            <div className="truncate text-xs text-mute" title={s.label}>
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
