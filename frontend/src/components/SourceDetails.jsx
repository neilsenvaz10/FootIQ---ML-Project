import { parseSources } from "../lib/sources.js";
import { Summary } from "./ui.jsx";

// Short source line + collapsible full list. `licences` is shown in the disclosure too (attribution stays reachable).
export default function SourceDetails({ sources, licences }) {
  const s = parseSources(sources);
  const lic = parseSources(licences);
  return (
    <div className="text-xs leading-snug text-mute">
      <p>
        Source: {s.summary} · Licence: {lic.items.length > 2 ? `${lic.items.slice(0, 2).join(" | ")} …` : lic.items.join(" | ")}
      </p>
      {(s.isLong || lic.items.length > 2) && (
        <details className="group mt-1">
          <Summary>View sources</Summary>
          <ul className="mt-1 list-disc space-y-0.5 pl-4 [overflow-wrap:anywhere]">
            {s.items.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
          <p className="mt-1">
            <span className="text-ink/80">Licences:</span> {lic.items.join(" | ")}
          </p>
        </details>
      )}
    </div>
  );
}
