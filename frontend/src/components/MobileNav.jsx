import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import Icon from "./Icon.jsx";
import { MORE, PRIMARY, isActive } from "../lib/nav.js";

const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

// "More" sheet: a modal dialog that lists the destinations that do not fit in the bottom bar.
// Escape, the close button, the backdrop and choosing a destination all close it; Tab stays inside while it is open.
function MoreSheet({ pathname, onClose, onDismiss }) {
  const ref = useRef(null);
  useEffect(() => ref.current?.querySelector(FOCUSABLE)?.focus(), []); // focus moves into the dialog once, when it opens
  useEffect(() => {
    document.body.classList.add("overflow-hidden");
    const onKey = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onDismiss();
      } else if (e.key === "Tab") {
        const items = [...ref.current.querySelectorAll(FOCUSABLE)];
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("overflow-hidden");
    };
  }, [onDismiss]);

  return (
    <div className="fixed inset-0 z-50 md:hidden">
      <div className="absolute inset-0 bg-black/70" onClick={onDismiss} aria-hidden="true" />
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby="more-title" id="more-sheet" className="absolute inset-x-0 bottom-0 rounded-t-3xl border-t border-line-strong bg-panel px-4 pt-2 shadow-card" style={{ paddingBottom: "calc(1rem + env(safe-area-inset-bottom))" }}>
        <div className="mx-auto mb-1 h-1 w-10 rounded-full bg-line-strong" aria-hidden="true" />
        <div className="flex items-center justify-between py-1">
          <h2 id="more-title" className="text-base font-bold">
            More
          </h2>
          <button type="button" onClick={onDismiss} aria-label="Close menu" className="grid h-11 w-11 place-items-center rounded-full text-mute hover:bg-panel-2 hover:text-ink">
            <Icon name="close" className="h-5 w-5" />
          </button>
        </div>
        <ul className="mt-1 flex flex-col gap-1">
          {MORE.map((item) => {
            const active = isActive(item, pathname);
            return (
              <li key={item.id}>
                <Link to={item.to} onClick={onClose} aria-current={active ? "page" : undefined} className={`flex min-h-12 items-center gap-3 rounded-xl px-3 text-sm font-semibold ${active ? "bg-accent/15 text-accent" : "text-ink hover:bg-panel-2"}`}>
                  <Icon name={item.icon} className="h-5 w-5 shrink-0" />
                  <span className="flex-1">{item.label}</span>
                  <Icon name="chevron" className="h-4 w-4 text-mute" />
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

// Phone navigation: five primary destinations and "More" in a bottom bar; tablet and desktop use the sidebar instead.
export default function MobileNav() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const moreRef = useRef(null);
  const moreActive = MORE.some((item) => isActive(item, pathname));

  useEffect(() => setOpen(false), [pathname]);
  const dismiss = useCallback(() => {
    setOpen(false);
    moreRef.current?.focus(); // closing without choosing a destination returns focus to the control that opened the sheet
  }, []);

  // Cells are sized by their label (flex-auto), then share the spare width: with six equal columns "Predictions" and "Simulations" (66 and 68 px at 12 px) do not fit side by side at 375 px.
  const cell = "flex h-16 w-full flex-col items-center justify-center gap-1 whitespace-nowrap px-1 text-xs font-semibold transition-colors";
  return (
    <>
      <nav aria-label="Main mobile" className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-sidebar/95 backdrop-blur md:hidden" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        <ul className="mx-auto flex max-w-xl">
          {PRIMARY.map((item) => {
            const active = isActive(item, pathname);
            return (
              <li key={item.id} className="min-w-11 flex-auto">
                <Link to={item.to} aria-current={active ? "page" : undefined} className={`${cell} ${active ? "text-accent" : "text-mute"}`}>
                  <Icon name={item.icon} className="h-6 w-6" />
                  {item.label}
                </Link>
              </li>
            );
          })}
          <li className="min-w-11 flex-auto">
            <button ref={moreRef} type="button" aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? "more-sheet" : undefined} onClick={() => setOpen(!open)} className={`${cell} ${moreActive || open ? "text-accent" : "text-mute"}`}>
              <Icon name="more" className="h-6 w-6" />
              More
            </button>
          </li>
        </ul>
      </nav>
      {open && <MoreSheet pathname={pathname} onClose={() => setOpen(false)} onDismiss={dismiss} />}
    </>
  );
}
