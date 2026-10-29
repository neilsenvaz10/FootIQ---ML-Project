// What the Leagues page can honestly say about a table. Everything here is derived from the rows the API returned (standings computed by the backend from the stored,
// verified results), from /api/competitions/{key}/coverage and from /api/sync/status; nothing is guessed and no qualification or relegation rule is applied.

export const LEAGUE_KEYS = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"];

// Fewest and most matches played by the clubs of a table (equal when every club has played the same number).
export function playedSpread(rows = []) {
  if (!rows.length) return { min: 0, max: 0, even: true };
  const played = rows.map((r) => r.played);
  const min = Math.min(...played);
  const max = Math.max(...played);
  return { min, max, even: min === max };
}

// Teams that are level on points with the club above or below them: their order is a display order (goal difference, goals scored, name), not an official tie-break.
export function levelOnPoints(rows = []) {
  const level = new Set();
  rows.forEach((r, i) => {
    if ((i > 0 && rows[i - 1].points === r.points) || (i < rows.length - 1 && rows[i + 1].points === r.points)) level.add(r.team);
  });
  return level;
}

// The indicators for one league season. `coverage` is the season's row of /coverage, `sync` the league's entry of /sync/status (only meaningful for the newest season),
// `current` says whether the chosen season is the newest one.
export function seasonIndicators({ rows, coverage, sync, current }) {
  const spread = playedSpread(rows);
  const partial = coverage?.note === "incomplete or in progress";
  const out = [];
  if (partial) {
    out.push({
      key: "partial",
      tone: "warn",
      label: coverage.expected_matches ? `Partial season: ${coverage.rows_in_dataset} of ${coverage.expected_matches} matches in the data` : "Partial season",
      text: "The table covers only the matches stored so far; clubs may have played different numbers of matches.",
    });
  }
  if (!spread.even) out.push({ key: "uneven", tone: "info", label: `Clubs have played ${spread.min} to ${spread.max} matches`, text: "Points and positions are not comparable between clubs with different numbers of matches played." });
  if (current && sync) {
    if (sync.awaiting_result > 0) {
      out.push({ key: "missing", tone: "warn", label: `${sync.awaiting_result} fixture${sync.awaiting_result === 1 ? " has" : "s have"} no verified result`, text: "Matches whose date has passed but that have no verified result are not in the table." });
    }
    if (sync.state && sync.state !== "fresh") {
      out.push({ key: "stale", tone: "warn", label: `Data not fresh · newest verified result ${sync.latest_result ?? "unknown"}`, text: (sync.state_reasons ?? []).join(" ") || "No approved source has confirmed this league recently." });
    } else if (sync?.state === "fresh") {
      out.push({ key: "fresh", tone: "ok", label: `Data fresh · newest verified result ${sync.latest_result ?? "unknown"}`, text: "" });
    }
  }
  return out;
}

export const TABLE_NOTE =
  "Computed from verified stored results, 3 points for a win and 1 for a draw. Clubs level on points are ordered by goal difference, then goals scored, then name: a display order, not an official tie-break. No qualification or relegation positions are shown, because the applicable rules are not verified for this table.";
