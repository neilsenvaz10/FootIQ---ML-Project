import { FormDots, TeamAvatar } from "../ui.jsx";
import { levelOnPoints } from "../../lib/leagues.js";

// League table. From 640 px: # club P W D L GF GA GD Pts form. On a phone: # club P GD Pts, with W-D-L, goals and form in a second line under the club name, so nothing needs sideways scrolling.
const TH = "border-b border-line-strong/60 whitespace-nowrap px-2 py-2.5 text-right font-semibold";
const TD = "border-b border-line/70 px-2 py-3 whitespace-nowrap text-right tabular-nums";
const WIDE = "hidden sm:table-cell";

export default function StandingsTable({ rows, caption }) {
  const level = levelOnPoints(rows);
  return (
    <div className="overflow-x-auto">
      <table className="w-full table-fixed border-collapse text-sm sm:table-auto">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="sticky top-0 bg-panel text-xs text-mute">
            <th scope="col" className="w-10 border-b border-line-strong/60 py-2.5 pl-3 pr-1 text-left font-semibold">#</th>
            <th scope="col" className="border-b border-line-strong/60 px-2 py-2.5 text-left font-semibold">Club</th>
            <th scope="col" className={`${TH} w-8 sm:w-auto`}><abbr title="Played">P</abbr></th>
            <th scope="col" className={`${TH} ${WIDE}`}><abbr title="Won">W</abbr></th>
            <th scope="col" className={`${TH} ${WIDE}`}><abbr title="Drawn">D</abbr></th>
            <th scope="col" className={`${TH} ${WIDE}`}><abbr title="Lost">L</abbr></th>
            <th scope="col" className={`${TH} ${WIDE}`}><abbr title="Goals for">GF</abbr></th>
            <th scope="col" className={`${TH} ${WIDE}`}><abbr title="Goals against">GA</abbr></th>
            <th scope="col" className={`${TH} w-11 sm:w-auto`}><abbr title="Goal difference">GD</abbr></th>
            <th scope="col" className={`${TH} w-10 pr-3 sm:w-auto`}><abbr title="Points">Pts</abbr></th>
            <th scope="col" className={`${TH} ${WIDE} pr-3`}>Form</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.team}>
              <td className={`border-b border-line/70 whitespace-nowrap py-3 pl-2 pr-1 text-left align-top tabular-nums ${r.pos === 1 ? "font-extrabold text-draw" : "text-mute"}`}>
                {r.pos}
                {level.has(r.team) && (
                  <span title="Level on points with a neighbouring club: the order between them is a display order">
                    <span aria-hidden="true">=</span>
                    <span className="sr-only"> (level on points)</span>
                  </span>
                )}
              </td>
              <td className="border-b border-line/70 px-2 py-3">
                <span className="flex min-w-0 items-center gap-2.5">
                  <TeamAvatar name={r.team} size={28} />
                  <span className="min-w-0">
                    <span className="block break-words font-semibold">{r.team}</span>
                    <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-mute sm:hidden">
                      <span>
                        W {r.won} · D {r.drawn} · L {r.lost}
                      </span>
                      <span>
                        GF {r.gf} · GA {r.ga}
                      </span>
                      {r.form?.length ? <span aria-label={`last ${r.form.length} results, oldest first: ${r.form.join(" ")}`}>Form {r.form.join(" ")}</span> : null}
                    </span>
                  </span>
                </span>
              </td>
              <td className={`${TD} align-top`}>{r.played}</td>
              <td className={`${TD} ${WIDE}`}>{r.won}</td>
              <td className={`${TD} ${WIDE}`}>{r.drawn}</td>
              <td className={`${TD} ${WIDE}`}>{r.lost}</td>
              <td className={`${TD} ${WIDE}`}>{r.gf}</td>
              <td className={`${TD} ${WIDE}`}>{r.ga}</td>
              <td className={`${TD} align-top`}>{r.gd > 0 ? `+${r.gd}` : r.gd}</td>
              <td className={`${TD} pr-3 align-top font-extrabold`}>{r.points}</td>
              <td className={`border-b border-line/70 py-3 pl-2 pr-3 text-right ${WIDE}`}>{r.form?.length ? <FormDots results={r.form} size={22} /> : null}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
