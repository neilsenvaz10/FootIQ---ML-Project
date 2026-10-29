import { Link } from "react-router-dom";
import { Icon } from "../ui.jsx";

const ACTIONS = [
  { to: "/predict?mode=manual", title: "Match predictions", text: "Home, draw and away estimates for any two teams", icon: "target" },
  { to: "/predict?mode=gameweek", title: "Gameweek predictions", text: "Every fixture of a gameweek, saved only when you ask", icon: "calendar" },
  { to: "/compare", title: "Compare teams", text: "Recent form and head-to-head records", icon: "compare" },
  { to: "/simulations", title: "Simulations", text: "League-season simulator", icon: "trophy" },
];

export default function QuickActions() {
  return (
    <section aria-label="Quick access">
      <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {ACTIONS.map((a) => (
          <li key={a.to}>
            <Link to={a.to} className="flex h-full min-h-[4.5rem] items-start gap-3 rounded-card border border-line bg-panel p-3.5 shadow-card transition-colors hover:border-line-strong hover:bg-panel-2 sm:p-4">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent/15 text-accent">
                <Icon name={a.icon} className="h-5 w-5" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-bold leading-tight">{a.title}</span>
                <span className="mt-1 hidden text-xs leading-snug text-mute sm:block">{a.text}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
