export const pct = (x, d = 1) => (x == null ? "-" : `${(x * 100).toFixed(d)}%`);
export const num = (x, d = 0) => (x == null || x === "" ? "-" : Number(x).toFixed(d));
export const int = (x) => (x == null ? "-" : Number(x).toLocaleString("en-US"));
export const nextDay = (iso) => {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
};

// validation badge -> visual tone (the backend's badge text is shown unchanged)
export function badgeTone(badge = "") {
  if (badge.startsWith("Validated")) return "ok";
  if (badge.startsWith("Partially")) return "warn";
  return "bad";
}
