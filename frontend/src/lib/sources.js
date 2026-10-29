// The backend returns sources as one " | "-joined string; for the 2026 World Cup it contains a long list of URLs.
// Short summary for the card, full list for the "View sources" disclosure. Nothing is dropped.
export function parseSources(text = "") {
  const items = [...new Set(text.split(" | ").map((s) => s.trim()).filter(Boolean))];
  const labelOf = (s) => {
    try {
      return new URL(s).hostname.replace(/^www\./, "");
    } catch {
      return s;
    }
  };
  const labels = [...new Set(items.map(labelOf))];
  const summary = labels.length <= 2 ? labels.join(" + ") : `${labels.slice(0, 2).join(", ")} + ${labels.length - 2} more`;
  return { items, summary, isLong: items.length > 2 || items.some((i) => i.length > 40) };
}
