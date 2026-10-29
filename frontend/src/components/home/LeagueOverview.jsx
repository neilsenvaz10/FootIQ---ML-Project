import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, Chip, Empty, ErrorBox, FormDots, Pills, Spinner, TeamCrest } from "../ui.jsx";
import { useApi } from "../../lib/hooks.js";
import { freshnessText, SHORT_LEAGUE } from "../../lib/fixtures.js";
import { int } from "../../lib/format.js";

// Compact table of the newest season of a domestic league, computed by the backend from the matches stored so far. A partial season is labelled as partial.

const LEAGUES = Object.entries(SHORT_LEAGUE).map(([value, label]) => ({ value, label }));

export default function LeagueOverview({ freshness }) {
  const [key, setKey] = useState("EPL");
  const [retrySeasons, setRetrySeasons] = useState(0);
  const [retryTable, setRetryTable] = useState(0);
  const seasons = useApi(`/api/competitions/${key}/seasons`, undefined, { retry: retrySeasons });
  const season = seasons.data?.[0] ?? null;
  const cov = useApi(season ? `/api/competitions/${key}/coverage` : null, undefined, { retry: retryTable });
  const dash = useApi(season ? `/api/competitions/${key}/dashboard` : null, { season }, { retry: retryTable });
  const err = seasons.error || cov.error || dash.error;
  const again = () => (seasons.error ? setRetrySeasons((n) => n + 1) : setRetryTable((n) => n + 1));
  const d = dash.data;
  const row = cov.data?.find((r) => String(r.season) === season);
  const fresh = freshnessText(freshness?.competitions?.[key]);
  const top = d?.standings?.slice(0, 6) ?? [];
  const label = SHORT_LEAGUE[key];
  return (
    <Card title="League overview" subtitle={season ? `${label} ${season}: newest season in the data` : "Newest season in the data"}>
      <Pills label="League" value={key} onChange={setKey} options={LEAGUES} wrap />
      {err && (
        <div className="mt-4">
          <ErrorBox error={err} onRetry={again} />
        </div>
      )}
      {!err && (seasons.loading || dash.loading || cov.loading) && <Spinner label="Loading the table…" />}
      {!err && seasons.data && !season && <Empty>No season is stored for this league.</Empty>}
      {d && (
        <div className="mt-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {fresh && <Chip tone={fresh.tone}>{fresh.text}</Chip>}
          </div>
          {top.length === 0 ? (
            <Empty>No results are stored for this season yet.</Empty>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <caption className="sr-only">
                  {label} {season}: the top {top.length} clubs by points, from the matches in the data
                </caption>
                <thead>
                  <tr className="text-left text-xs text-mute">
                    <th scope="col" className="w-8 border-b border-line-strong/60 py-2 pr-2 font-semibold">
                      #
                    </th>
                    <th scope="col" className="border-b border-line-strong/60 py-2 pr-2 font-semibold">
                      Club
                    </th>
                    <th scope="col" className="border-b border-line-strong/60 px-2 py-2 text-right font-semibold">
                      P
                    </th>
                    <th scope="col" className="hidden border-b border-line-strong/60 px-2 py-2 text-right font-semibold sm:table-cell">
                      GD
                    </th>
                    <th scope="col" className="border-b border-line-strong/60 px-2 py-2 text-right font-semibold">
                      Pts
                    </th>
                    <th scope="col" className="hidden border-b border-line-strong/60 py-2 pl-3 text-right font-semibold md:table-cell">
                      Form
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {top.map((t) => (
                    <tr key={t.team}>
                      <td className={`border-b border-line/70 py-2.5 pr-2 tabular-nums ${t.pos === 1 ? "font-extrabold text-draw" : "text-mute"}`}>{t.pos}</td>
                      <td className="max-w-[11rem] border-b border-line/70 py-2.5 pr-2">
                        <span className="flex min-w-0 items-center gap-2">
                          <TeamCrest name={t.team} size={24} />
                          <span className="truncate font-semibold">{t.team}</span>
                        </span>
                      </td>
                      <td className="border-b border-line/70 px-2 py-2.5 text-right tabular-nums">{t.played}</td>
                      <td className="hidden border-b border-line/70 px-2 py-2.5 text-right tabular-nums sm:table-cell">{t.gd > 0 ? `+${t.gd}` : t.gd}</td>
                      <td className="border-b border-line/70 px-2 py-2.5 text-right font-extrabold tabular-nums">{t.points}</td>
                      <td className="hidden border-b border-line/70 py-2.5 pl-3 text-right md:table-cell">
                        <FormDots results={t.form ?? []} size={18} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-x-4">
            <p className="text-xs text-mute">Computed from the {int(d.summary.matches)} matches in the data, 3 points for a win and 1 for a draw.</p>
            <Link to={`/analytics?comp=${key}`} className="inline-flex min-h-11 items-center text-xs font-semibold text-accent hover:text-ink">
              Full table →
            </Link>
          </div>
        </div>
      )}
    </Card>
  );
}
