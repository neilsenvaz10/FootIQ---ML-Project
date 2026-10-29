// Shared Recharts styling. Colours are the design tokens in src/index.css (CSS variables work in SVG attributes and inline styles).
export const COLORS = {
  home: "var(--color-home)",
  draw: "var(--color-draw)",
  away: "var(--color-away)",
  win: "var(--color-home)",
  loss: "var(--color-away)",
  grid: "var(--color-line)",
  text: "var(--color-mute)",
  pitch: "var(--color-accent-strong)",
  ok: "var(--color-ok)",
  blue: "var(--color-info)",
};

export const tooltipStyle = {
  contentStyle: { background: "var(--color-panel-2)", border: "1px solid var(--color-line-strong)", borderRadius: 12, color: "var(--color-ink)", fontSize: 12 },
  labelStyle: { color: "var(--color-ink)" },
  itemStyle: { color: "var(--color-ink-2)" },
};

export const axisProps = { stroke: COLORS.text, tick: { fill: COLORS.text, fontSize: 12 } };
