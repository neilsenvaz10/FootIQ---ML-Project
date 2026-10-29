import { shortDate } from "../lib/team.js";
import { useApi } from "../lib/hooks.js";
import { Card, ErrorBox, Notice, Spinner, TeamAvatar } from "./ui.jsx";

const SLOT_H = 100; // px of vertical space per first-round match; every later round is centred between its two feeders

function Side({ name, score, shootout, won, lost }) {
  return (
    <div className={`flex items-center gap-2 px-2.5 py-1.5 ${won ? "bg-pitch/15" : ""}`}>
      {name ? <TeamAvatar name={name} size={20} /> : <span className="h-5 w-5 rounded-full border border-dashed border-line" />}
      <span className={`min-w-0 flex-1 truncate text-[13px] ${won ? "font-extrabold text-ink" : lost ? "text-mute" : name ? "text-ink" : "text-mute"}`}>{name ?? "To be decided"}</span>
      {score != null && (
        <span className={`text-sm tabular-nums ${won ? "font-extrabold" : "text-mute"}`}>
          {score}
          {shootout != null && <sup className="ml-0.5 text-xs text-mute">({shootout})</sup>}
        </span>
      )}
    </div>
  );
}

function MatchBox({ m, highlight }) {
  const played = m.status === "played";
  const w = m.winner;
  const d = shortDate(m.date);
  return (
    <div className={`w-44 overflow-hidden rounded-xl border bg-panel-2 ${highlight ? "border-draw/60 shadow-lg shadow-draw/10" : "border-white/5"}`} title={`${m.round}, ${m.venue}`}>
      <Side name={m.team1} score={m.score?.team1} shootout={m.shootout?.team1} won={played && w === m.team1} lost={played && w && w !== m.team1} />
      <div className="border-t border-line/60" />
      <Side name={m.team2} score={m.score?.team2} shootout={m.shootout?.team2} won={played && w === m.team2} lost={played && w && w !== m.team2} />
      <div className="flex justify-between border-t border-line/60 bg-black/20 px-2.5 py-1 text-xs text-mute">
        <span>
          {d.day} {d.year}
        </span>
        <span>{played ? (m.shootout ? "pens" : "FT") : "no result in data"}</span>
      </div>
    </div>
  );
}

function Column({ round }) {
  const ms = round.matches;
  const pairs = [];
  for (let i = 0; i < ms.length; i += 2) pairs.push(ms.slice(i, i + 2));
  const single = ms.length === 1;
  const height = SLOT_H * 16;
  return (
    <div className="shrink-0">
      <h3 className="mb-2 text-center text-xs font-bold uppercase tracking-wide text-mute">{round.name}</h3>
      <div className="flex w-44 flex-col" style={{ height }}>
        {single ? (
          <div className="flex flex-1 items-center">
            <MatchBox m={ms[0]} highlight />
          </div>
        ) : (
          pairs.map((p, i) => (
            <div key={i} className="relative flex flex-1 flex-col justify-around">
              {p.map((m) => (
                <MatchBox key={m.id} m={m} />
              ))}
              {p.length === 2 && (
                <>
                  <span className="pointer-events-none absolute -right-4 bottom-[25%] top-[25%] w-4 rounded-r-md border-y border-r border-line" />
                  <span className="pointer-events-none absolute -right-8 top-1/2 w-4 border-t border-line" />
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// Real 2026 knockout bracket from /api/worldcup/bracket (results in the repository; never simulated).
export default function Bracket() {
  const { data, loading, error } = useApi("/api/worldcup/bracket");
  if (loading) return <Spinner label="Loading bracket…" />;
  if (error) return <ErrorBox error={error} />;
  const final = data.rounds[data.rounds.length - 1].matches[0];
  return (
    <div className="space-y-4">
      <Notice tone="info" title="Real results, not a simulation.">
        {data.note}
      </Notice>
      <Card title="2026 knockout bracket" subtitle="Scroll sideways. A bold name with a tinted row won; a small number beside a score is the penalty shoot-out score.">
        <div className="no-scrollbar -mx-2 overflow-x-auto px-2 pb-3">
          <div className="flex gap-8" style={{ minWidth: "fit-content" }}>
            {data.rounds.map((r) => (
              <Column key={r.name} round={r} />
            ))}
          </div>
        </div>
      </Card>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card title="Final" subtitle={`${shortDate(final.date).day} ${shortDate(final.date).year} · ${final.venue}`}>
          <div className="flex items-center justify-center gap-4 py-2">
            {[final.team1, final.team2].map((t, i) => (
              <div key={i} className="flex flex-col items-center gap-1.5">
                {t ? <TeamAvatar name={t} size={52} /> : <span className="h-[52px] w-[52px] rounded-full border border-dashed border-line" />}
                <span className="text-sm font-bold">{t ?? "To be decided"}</span>
              </div>
            ))}
          </div>
          <p className="text-center text-xs text-mute">{final.status === "played" ? "Result recorded." : "The result of the final is not in the dataset, so no champion is shown."}</p>
        </Card>
        {data.third_place && (
          <Card title="Third-place match" subtitle={`${shortDate(data.third_place.date).day} ${shortDate(data.third_place.date).year}`}>
            <MatchBox m={data.third_place} />
          </Card>
        )}
      </div>
    </div>
  );
}
