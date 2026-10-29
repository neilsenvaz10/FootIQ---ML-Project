import { useState } from "react";
import { crestFor } from "../lib/crests.js";
import { crestColors, initials } from "../lib/team.js";

// Club badge. A licensed local crest is used only when src/data/crests.json lists it with its licence and the file exists;
// every other team gets a generated badge: letters from the name (never digits) on a colour that depends only on the name.
// Decorative by default because the team name is always written next to it; pass `decorative={false}` where it stands alone.
export default function TeamCrest({ name, size = 28, decorative = true, className = "", crest }) {
  const licensed = crest === undefined ? crestFor(name) : crest;
  const [broken, setBroken] = useState(false);
  const a11y = decorative ? { "aria-hidden": "true" } : { role: "img", "aria-label": `${name} badge` };
  const base = `inline-grid shrink-0 select-none place-items-center overflow-hidden rounded-full ${className}`;

  if (licensed && !broken) {
    return (
      <span {...a11y} style={{ width: size, height: size }} className={`${base} bg-white/95 p-[8%]`} data-crest="licensed">
        <img src={licensed.url} alt="" width={size} height={size} loading="lazy" decoding="async" onError={() => setBroken(true)} className="h-full w-full object-contain" />
      </span>
    );
  }

  const compact = size < 30;
  const { background, color } = crestColors(name);
  return (
    <span
      {...a11y}
      data-crest="generated"
      style={{ width: size, height: size, fontSize: Math.max(11, Math.round(size * (compact ? 0.44 : 0.33))), background, color }}
      className={`${base} font-bold leading-none tracking-tight ring-1 ring-inset ring-white/15`}
    >
      {initials(name, compact ? 2 : 3)}
    </span>
  );
}
