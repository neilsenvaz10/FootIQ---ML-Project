// Display grouping for the competition dropdown (keys are the backend's competition keys).
export const COMPETITION_GROUPS = [
  { label: "Domestic leagues", keys: ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"] },
  { label: "UEFA competition", keys: ["UCL"] },
];

export function groupCompetitions(input) {
  const comps = input ?? []; // null while the list is still loading
  const byKey = Object.fromEntries(comps.map((c) => [c.key, c]));
  const groups = COMPETITION_GROUPS.map((g) => ({ label: g.label, items: g.keys.map((k) => byKey[k]).filter(Boolean) })).filter((g) => g.items.length);
  const listed = new Set(COMPETITION_GROUPS.flatMap((g) => g.keys));
  const rest = comps.filter((c) => !listed.has(c.key)); // never hide a competition the backend returns
  return rest.length ? [...groups, { label: "Other", items: rest }] : groups;
}
