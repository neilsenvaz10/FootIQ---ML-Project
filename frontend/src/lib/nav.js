// The seven destinations of the app. `primary` ones sit in the phone's bottom bar; the rest live behind "More".
// Every destination is reachable from the sidebar (tablet and desktop) and from the bottom bar plus "More" (phone).
// Existing addresses keep working: /predict is the Predictions page and /predictions redirects to it.
export const NAV = [
  { id: "home", to: "/", label: "Home", icon: "home", primary: true },
  { id: "matches", to: "/matches", label: "Matches", icon: "calendar", primary: true },
  { id: "leagues", to: "/analytics", label: "Leagues", icon: "table", primary: true },
  { id: "compare", to: "/compare", label: "Compare", icon: "compare", primary: false },
  { id: "predictions", to: "/predict", label: "Predictions", icon: "target", primary: true, aliases: ["/predictions"] },
  { id: "simulations", to: "/simulations", label: "Simulations", icon: "trophy", primary: true },
  { id: "models", to: "/models", label: "Models", icon: "chart", primary: false },
];

export const PRIMARY = NAV.filter((n) => n.primary);
export const MORE = NAV.filter((n) => !n.primary);

const clean = (pathname) => pathname.replace(/\/+$/, "") || "/";

export function isActive(item, pathname) {
  const p = clean(pathname);
  if (item.to === "/") return p === "/";
  return [item.to, ...(item.aliases ?? [])].some((x) => p === x || p.startsWith(`${x}/`));
}

export function pageTitle(pathname) {
  if (import.meta.env.DEV && clean(pathname) === "/design") return "Design system";
  return NAV.find((n) => isActive(n, pathname))?.label ?? "Page not found";
}

export const documentTitle = (pathname) => `${pageTitle(pathname)} · FootIQ`;
