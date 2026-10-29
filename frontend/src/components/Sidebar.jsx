import { Link, useLocation } from "react-router-dom";
import { BrandMark, Wordmark } from "./Brand.jsx";
import Icon from "./Icon.jsx";
import { NAV, isActive } from "../lib/nav.js";

// Tablet (768 to 1023 px): a narrow rail, icon above label. Desktop (1024 px and up): the full sidebar, icon beside label.
export default function Sidebar() {
  const { pathname } = useLocation();
  return (
    <aside className="sticky top-0 hidden h-screen w-[5.5rem] shrink-0 flex-col border-r border-line bg-sidebar px-2 py-4 md:flex lg:w-64 lg:px-4 lg:py-5">
      <Link to="/" aria-label="FootIQ home" className="flex items-center justify-center gap-3 rounded-xl px-1 py-1 lg:justify-start lg:px-2">
        <BrandMark />
        <Wordmark className="hidden text-xl lg:block" />
      </Link>
      <p className="mt-2 hidden px-2 text-xs leading-snug text-mute lg:block">Football analytics &amp; match prediction</p>

      <nav aria-label="Main" className="mt-6">
        <ul className="flex flex-col gap-1">
          {NAV.map((item) => {
            const active = isActive(item, pathname);
            return (
              <li key={item.id}>
                <Link
                  to={item.to}
                  aria-current={active ? "page" : undefined}
                  className={`relative flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl px-1 text-xs font-semibold transition-colors lg:min-h-11 lg:flex-row lg:justify-start lg:gap-3 lg:px-3 lg:text-sm ${
                    active ? "bg-accent/15 text-accent" : "text-mute hover:bg-panel hover:text-ink"
                  }`}
                >
                  <Icon name={item.icon} className="h-5 w-5 shrink-0" />
                  <span>{item.label}</span>
                  {active && <span aria-hidden="true" className="absolute bottom-2.5 left-0 top-2.5 hidden w-[3px] rounded-full bg-accent lg:block" />}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <p className="mt-auto hidden rounded-card border border-line bg-panel p-3.5 text-xs leading-snug text-mute lg:block">College mini-project. Existing frozen models; historical data, not live.</p>
    </aside>
  );
}
