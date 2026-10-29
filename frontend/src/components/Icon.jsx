// One consistent icon set: 24 x 24, 1.8 px round strokes, drawn for this project (no icon library). Decorative: the visible label names the control.
const PATHS = {
  home: ["M3 11.5 12 4l9 7.5", "M5.5 10v9.5h4.5v-5h4v5h4.5V10"],
  calendar: ["M5 5.5h14a1 1 0 0 1 1 1V19a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6.5a1 1 0 0 1 1-1Z", "M8 3.5v4M16 3.5v4M4 10.5h16", "M8.5 14.5h.01M12 14.5h.01M15.5 14.5h.01M8.5 17.5h.01M12 17.5h.01"],
  table: ["M4 5h16M4 10h16M4 15h10M4 20h7"],
  compare: ["M7 7h13m0 0-3.5-3.5M20 7l-3.5 3.5", "M17 17H4m0 0 3.5-3.5M4 17l3.5 3.5"],
  target: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z", "M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"],
  trophy: ["M8 4h8v5a4 4 0 0 1-8 0V4Z", "M5 5h3m8 0h3", "M5 5c0 3 1 4 3 4m11-4c0 3-1 4-3 4", "M12 13v4m-3.5 3h7M10 17h4"],
  chart: ["M4 20V10m6 10V4m6 16v-7m4 7H3"],
  more: ["M5 12a1 1 0 1 0 2 0 1 1 0 0 0-2 0Z", "M11 12a1 1 0 1 0 2 0 1 1 0 0 0-2 0Z", "M17 12a1 1 0 1 0 2 0 1 1 0 0 0-2 0Z"],
  chevron: ["m9 6 6 6-6 6"],
  close: ["M6 6l12 12M18 6 6 18"],
  check: ["m5 12.5 4.5 4.5L19 7.5"],
  info: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M12 11v5.5", "M12 7.7h.01"],
  alert: ["M10.3 4.3 2.8 17.5A2 2 0 0 0 4.5 20.5h15a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z", "M12 9.5v4.5", "M12 17.2h.01"],
  clock: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M12 7.5V12l3 2"],
  // simplified football used as the brand mark: a circle, a central pentagon and five seams
  ball: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M12 8l3.8 2.76-1.45 4.48h-4.7L8.2 10.76 12 8Z", "M12 8V3.2M15.8 10.76l4.6-1.5M14.35 15.24l2.85 3.9M9.65 15.24l-2.85 3.9M8.2 10.76l-4.6-1.5"],
};

export const ICON_NAMES = Object.keys(PATHS);

export default function Icon({ name, className = "h-6 w-6" }) {
  const paths = PATHS[name] ?? [];
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true" focusable="false">
      {paths.map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}
