"""Phase 4.20 part C: one-off edit script for the Matches hub frontend (kept as a record of exactly what changed)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "frontend" / "src"


def rep(s, old, new):
    assert s.count(old) == 1, f"expected exactly one: {old[:80]!r} (found {s.count(old)})"
    return s.replace(old, new)


# ---- lib/fixtures.js
p = SRC / "lib" / "fixtures.js"
s = p.read_text(encoding="utf-8")
s = rep(s, 'export const SHORT_LEAGUE = { EPL: "Premier League", LALIGA: "La Liga", BUNDESLIGA: "Bundesliga", SERIEA: "Serie A", LIGUE1: "Ligue 1" };',
        '''export const SHORT_LEAGUE = { EPL: "Premier League", LALIGA: "La Liga", BUNDESLIGA: "Bundesliga", SERIEA: "Serie A", LIGUE1: "Ligue 1" };
// The Matches hub also lists the Champions League (Phase 4.20); the other pages keep the five domestic leagues above.
export const HUB_LEAGUE = { ...SHORT_LEAGUE, UCL: "Champions League" };

// Freshness chip text for one competition of the hub. The Champions League has no automatic update source: it is "historical only" and changes only through approved imports.
export function competitionFreshness(key, fresh) {
  if (!fresh) return null;
  if (key === "UCL") {
    const latest = fresh.latest_result ? `newest verified result ${fresh.latest_result}` : "no verified result stored";
    return { tone: "warn", text: `Historical only · ${latest} · not updated automatically` };
  }
  return freshnessText(fresh);
}''')
p.write_text(s, encoding="utf-8")

# ---- components/matches/MatchFilters.jsx
p = SRC / "components" / "matches" / "MatchFilters.jsx"
s = p.read_text(encoding="utf-8")
s = rep(s, 'import { SHORT_LEAGUE } from "../../lib/fixtures.js";', 'import { HUB_LEAGUE } from "../../lib/fixtures.js";')
s = rep(s, "...Object.entries(SHORT_LEAGUE).map(", "...Object.entries(HUB_LEAGUE).map(")
s = rep(s, "export default function MatchFilters({ comp, season, matchday, status, facets, counts, onChange }) {",
        "export default function MatchFilters({ comp, season, matchday, team, status, facets, counts, onChange }) {")
s = rep(s, "  return (\n    <Card title=\"Find matches\" subtitle=\"Five domestic leagues, from the results store\">",
        '''  const teams = facets?.teams ?? [];
  const teamOptions = [{ value: "", label: "All teams" }, ...(team && !teams.some((t) => t.entity === team) ? [{ value: team, label: team }] : []), ...teams.map((t) => ({ value: t.entity, label: t.name }))];
  return (
    <Card title="Find matches" subtitle="Five domestic leagues and the Champions League, from the results store">''')
s = rep(s, 'onChange={(v) => onChange({ comp: v, matchday: "" })} options={LEAGUE_OPTIONS}', 'onChange={(v) => onChange({ comp: v, matchday: "", team: "" })} options={LEAGUE_OPTIONS}')
s = rep(s, '{expanded ? "Hide" : "Show"} season and matchday filters{season || matchday ? " (active)" : ""}', '{expanded ? "Hide" : "Show"} season, matchday and team filters{season || matchday || team ? " (active)" : ""}')
s = rep(s, '<Select value={season} onChange={(v) => onChange({ season: v, matchday: "" })}', '<Select value={season} onChange={(v) => onChange({ season: v, matchday: "", team: "" })}')
s = rep(s, '''            <Select value={matchday ? String(matchday) : ""} onChange={(v) => onChange({ matchday: v })} options={matchdayOptions} aria-label="Matchday" />
          </Field>''', '''            <Select value={matchday ? String(matchday) : ""} onChange={(v) => onChange({ matchday: v })} options={matchdayOptions} aria-label="Matchday" />
          </Field>
          {comp && (
            <Field label="Team">
              <Select value={team ?? ""} onChange={(v) => onChange({ team: v })} options={teamOptions} aria-label="Team" />
            </Field>
          )}''')
p.write_text(s, encoding="utf-8")

# ---- pages/Matches.jsx
p = SRC / "pages" / "Matches.jsx"
s = p.read_text(encoding="utf-8")
s = rep(s, 'import { dayLabel, freshnessText, fullDay, groupByDate, SHORT_LEAGUE } from "../lib/fixtures.js";', 'import { competitionFreshness, dayLabel, fullDay, groupByDate, HUB_LEAGUE } from "../lib/fixtures.js";')
s = rep(s, "// Matches hub (stage P4.3): fixtures and results of the five domestic leagues, filtered by league, season, matchday and status, a page at a time.",
        "// Matches hub (stage P4.3, Champions League added in Phase 4.20): fixtures and results of the five domestic leagues and the Champions League, filtered by league, season, matchday, team and status, a page at a time.")
s = rep(s, "const LEAGUES = Object.keys(SHORT_LEAGUE);", "const LEAGUES = Object.keys(HUB_LEAGUE);\nconst TEAM_ID = /^[A-Za-z0-9:_.-]{3,120}$/;")
s = rep(s, '''  const status = STATUSES.includes(params.get("status")) ? params.get("status") : "upcoming";
  return { comp, season, matchday, status };''', '''  const status = STATUSES.includes(params.get("status")) ? params.get("status") : "upcoming";
  const team = comp && TEAM_ID.test(params.get("team") ?? "") ? params.get("team") : "";
  return { comp, season, matchday, team, status };''')
s = rep(s, "const one = entries.length === 1 ? freshnessText(entries[0][1]) : null;", "const one = entries.length === 1 ? competitionFreshness(entries[0][0], entries[0][1]) : null;")
s = rep(s, '{stale === 0 ? "Data fresh in all five leagues" : `Data not fresh in ${stale} of ${entries.length} leagues`}',
        '{stale === 0 ? `Data fresh in all ${entries.length} competitions` : `Data not fresh in ${stale} of ${entries.length} competitions`}')
s = rep(s, "<Summary>Data freshness by league</Summary>", "<Summary>Data freshness by competition</Summary>")
s = rep(s, '<span className="font-semibold text-ink">{SHORT_LEAGUE[k]}</span> · {freshnessText(c).text}', '<span className="font-semibold text-ink">{HUB_LEAGUE[k]}</span> · {competitionFreshness(k, c).text}')
s = rep(s, "const m = useMatchPages({ comp: f.comp || undefined, season: f.season || undefined, matchday: f.matchday || undefined, status: f.status });",
        "const m = useMatchPages({ comp: f.comp || undefined, season: f.season || undefined, matchday: f.matchday || undefined, team: f.team || undefined, status: f.status });")
s = rep(s, '<PageHeader title="Matches">Fixtures and results of the five domestic leagues, from the stored results.</PageHeader>',
        '<PageHeader title="Matches">Fixtures and results of the five domestic leagues and the Champions League, from the stored results.</PageHeader>')
s = rep(s, '{f.comp ? SHORT_LEAGUE[f.comp] : "all five leagues"}', '{f.comp ? HUB_LEAGUE[f.comp] : "all six competitions"}')
s = rep(s, '            {f.matchday ? ` · matchday ${f.matchday}` : ""}', '            {f.matchday ? ` · matchday ${f.matchday}` : ""}\n            {f.team ? ` · ${m.first.facets.teams?.find((t) => t.entity === f.team)?.name ?? "one team"}` : ""}')
p.write_text(s, encoding="utf-8")

# ---- components/matches/MatchCard.jsx
p = SRC / "components" / "matches" / "MatchCard.jsx"
s = p.read_text(encoding="utf-8")
s = rep(s, 'import { Link } from "react-router-dom";', 'import { useState } from "react";\nimport { Link } from "react-router-dom";')
s = rep(s, 'import { compareLink, gameweekLink, manualLink, MATCH_STATUS, SHORT_LEAGUE, timingChip } from "../../lib/fixtures.js";', 'import { compareLink, gameweekLink, HUB_LEAGUE, manualLink, MATCH_STATUS, timingChip } from "../../lib/fixtures.js";')
s = rep(s, "export default function MatchCard({ m, showLeague }) {\n", '''function Details({ m, finished }) {
  const rows = [
    ["Competition", `${m.competition} · season ${m.season}`],
    ["Stage", m.matchday_label ?? "not stated"],
    ["Date", m.date],
    ["Result", finished ? (m.result ? `${m.home.name} ${m.result.home_goals}-${m.result.away_goals} ${m.away.name} (final score, penalties excluded)` : "not stored") : "not played yet"],
    ["Source", m.source || "not stated"],
    ...(m.validation_badge ? [["Predictions", m.validation_badge]] : []),
  ];
  return (
    <dl className="mt-1 grid gap-x-3 gap-y-1 text-xs sm:grid-cols-[7rem_minmax(0,1fr)]">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="font-semibold text-mute">{k}</dt>
          <dd className="text-ink-2">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function MatchCard({ m, showLeague }) {
  const [open, setOpen] = useState(false);
  const unvalidated = Boolean(m.validation_badge?.startsWith("Not validated"));
''')
s = rep(s, "{showLeague && <Chip>{SHORT_LEAGUE[m.competition_key] ?? m.competition}</Chip>}", "{showLeague && <Chip>{HUB_LEAGUE[m.competition_key] ?? m.competition}</Chip>}")
s = rep(s, '            {!resolved && <Chip>Club not matched</Chip>}', '            {unvalidated && !finished && <Chip tone="warn" title="The club models were evaluated on domestic leagues only">Predictions: {m.validation_badge}</Chip>}\n            {!resolved && <Chip>Club not matched</Chip>}')
s = rep(s, '''              <Link to={gameweekLink(m, { season: true })} className={ACTION} aria-label={`Gameweek ${m.matchday_no ?? ""} predictions and forecast history: ${name}`.replace("  ", " ")}>
                Gameweek
              </Link>''', '''              {m.competition_key !== "UCL" && (
                <Link to={gameweekLink(m, { season: true })} className={ACTION} aria-label={`Gameweek ${m.matchday_no ?? ""} predictions and forecast history: ${name}`.replace("  ", " ")}>
                  Gameweek
                </Link>
              )}''')
s = rep(s, '''                Compare teams
              </Link>
            </div>
          )}
        </div>
      </article>''', '''                Compare teams
              </Link>
              <button type="button" className={ACTION} aria-expanded={open} aria-label={`Match details: ${name}`} onClick={() => setOpen(!open)}>
                {open ? "Hide details" : "Match details"}
              </button>
            </div>
          )}
          {open && <Details m={m} finished={finished} />}
        </div>
      </article>''')
p.write_text(s, encoding="utf-8")
print("frontend patched")
