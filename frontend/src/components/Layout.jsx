import { useEffect, useRef, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { BrandMark, Wordmark } from "./Brand.jsx";
import MobileNav from "./MobileNav.jsx";
import { useMeta } from "./MetaContext.jsx";
import Sidebar from "./Sidebar.jsx";
import SyncStatus from "./SyncStatus.jsx";
import { crestAttributions } from "../lib/crests.js";
import { documentTitle, pageTitle } from "../lib/nav.js";

function Attribution() {
  const { data, loading, error } = useMeta();
  const crests = crestAttributions();
  return (
    <footer className="mt-12 border-t border-line pt-5 text-xs leading-relaxed text-mute">
      <p className="mb-1 font-semibold text-ink-2">Data sources and licences</p>
      {loading && <p>Loading attribution…</p>}
      {error && <p className="text-bad">Attribution could not be loaded: {error.message}</p>}
      {data && (
        <>
          <ul className="list-disc space-y-0.5 pl-5">
            {data.attribution.map((a) => (
              <li key={a.source}>
                {a.source} — <span className="text-ink-2">{a.licence}</span>
                {a.requirement ? ` (${a.requirement})` : ""}
              </li>
            ))}
          </ul>
          <p className="mt-2">
            Historical data only (club results through {data.data_through.club_results}). Nothing on this site is live.
          </p>
        </>
      )}
      {crests.length > 0 && <p className="mt-2">Club crests: {crests.join(" · ")}</p>}
    </footer>
  );
}

// Per navigation: the tab title names the page, a polite announcement tells screen-reader users where they are,
// and focus moves to the page area so the next Tab starts at the content (not back in the menu).
function useRouteEffects(mainRef) {
  const { pathname } = useLocation();
  const previous = useRef(pathname);
  const [announcement, setAnnouncement] = useState("");
  useEffect(() => {
    document.title = documentTitle(pathname);
    if (previous.current === pathname) return; // first render, or a re-render of the same page
    previous.current = pathname;
    setAnnouncement(pageTitle(pathname));
    window.scrollTo(0, 0);
    mainRef.current?.focus({ preventScroll: true });
  }, [pathname, mainRef]);
  return announcement;
}

export default function Layout() {
  const mainRef = useRef(null);
  const announcement = useRouteEffects(mainRef);
  const skip = (e) => {
    e.preventDefault();
    mainRef.current?.focus();
  };
  return (
    <div className="min-h-screen md:flex">
      <a
        href="#main"
        onClick={skip}
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[100] focus:rounded-full focus:bg-primary focus:px-5 focus:py-3 focus:text-sm focus:font-bold focus:text-on-primary focus:shadow-glow"
      >
        Skip to main content
      </a>
      <Sidebar />

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex min-h-14 items-center justify-between gap-3 border-b border-line bg-sidebar/90 px-4 backdrop-blur md:hidden">
          <Link to="/" aria-label="FootIQ home" className="flex min-h-11 items-center gap-2.5">
            <BrandMark className="h-8 w-8" />
            <Wordmark />
          </Link>
          <span className="rounded-full border border-line bg-panel-2 px-3 py-1 text-xs font-semibold text-mute">Historical data</span>
        </header>

        <main id="main" ref={mainRef} tabIndex={-1} className="pb-tabbar px-4 pt-4 [overflow-wrap:anywhere] sm:px-6 md:pt-8 lg:px-10">
          <div className="mx-auto w-full max-w-6xl">
            <SyncStatus />
            <Outlet />
            <Attribution />
          </div>
        </main>
      </div>

      <MobileNav />
      <div role="status" aria-live="polite" className="sr-only">
        {announcement}
      </div>
    </div>
  );
}
