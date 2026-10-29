import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api.js";
import { useApi, useClubReady } from "../lib/hooks.js";
import { pct } from "../lib/format.js";
import { shortDate } from "../lib/team.js";
import CompetitionSelect from "../components/CompetitionSelect.jsx";
import FixtureCard from "../components/FixtureCard.jsx";
import { Badge, Button, CONTROL_EDGE, Card, ErrorBox, Notice, Spinner } from "../components/ui.jsx";

export const LEAGUE_KEYS = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"];
export const EXPLICIT_ACTION = "predict_gameweek_button";

const range = (g) => {
  const a = shortDate(g.first_date);
  const b = shortDate(g.last_date);
  return g.first_date === g.last_date ? a.day : `${a.day} – ${b.day}`;
};

export default function GameweekPredict() {
  const [params, setParams] = useSearchParams();
  const comps = useApi("/api/competitions");
  const club = useClubReady();
  const key = LEAGUE_KEYS.includes(params.get("comp")) ? params.get("comp") : "EPL";
  const [season, setSeason] = useState(params.get("season") ?? "");
  const [version, setVersion] = useState(0);
  const list = useApi("/api/gameweeks", { key, season });
  const gwNo = Number(params.get("gw")) || list.data?.next_gameweek || null;
  const data = useApi(list.data && gwNo ? "/api/gameweek" : null, { key, season: list.data?.season, matchday: gwNo, v: version });
  const sync = useApi("/api/sync/status");
  const [run, setRun] = useState({ loading: false, error: null, result: null });
  const req = useRef(0);

  useEffect(() => setRun({ loading: false, error: null, result: null }), [key, gwNo, season]);

  const leagues = comps.data?.filter((c) => LEAGUE_KEYS.includes(c.key));
  const comp = leagues?.find((c) => c.key === key);
  const g = list.data?.gameweeks.find((x) => x.matchday_no === gwNo);
  const setGw = (n) => setParams((p) => { const q = new URLSearchParams(p); q.set("mode", "gameweek"); q.set("comp", key); q.set("gw", String(n)); return q; });
  const idx = list.data ? list.data.gameweeks.findIndex((x) => x.matchday_no === gwNo) : -1;
  const league = sync.data?.competitions.find((c) => c.competition_key === key);
  const blocked = !club.ready;

  async function predict() {
    const id = ++req.current;
    setRun({ loading: true, error: null, result: null });
    try {
      const result = await api("/api/gameweek/predict", undefined, { method: "POST", body: { key, season: list.data.season, matchday: gwNo, user_action: EXPLICIT_ACTION } });
      if (id === req.current) {
        setRun({ loading: false, error: null, result });
        setVersion((v) => v + 1);
      }
    } catch (error) {
      if (id === req.current) setRun({ loading: false, error, result: null });
    }
  }

  const ev = data.data?.evaluation;
  const predictable = data.data?.fixtures.filter((f) => f.predictable).length ?? 0;
  const warningGroups = new Map();
  for (const f of data.data?.fixtures ?? []) {
    if (f.reliability !== "provisional" || !f.reasons?.length) continue;
    const key = JSON.stringify(f.reasons);
    const group = warningGroups.get(key) ?? { reasons: f.reasons, count: 0, id: `shared-provisional-${warningGroups.size}` };
    group.count += 1;
    warningGroups.set(key, group);
  }
  const saved = data.data?.fixtures.filter((f) => f.forecast).length ?? 0;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <CompetitionSelect comps={leagues} value={key} onChange={(v) => { setSeason(""); setParams({ mode: "gameweek", comp: v }); }} />
        {list.data && (
          <select aria-label="Season" value={list.data.season} onChange={(e) => { setSeason(e.target.value); setParams({ mode: "gameweek", comp: key }); }} className={`rounded-control bg-panel-2 px-4 font-bold ${CONTROL_EDGE}`}>
            {list.data.seasons.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        )}
      </div>
      {comp && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Badge badge={comp.badge} title={comp.basis} />
          <span className="text-mute">Club v1 is the validated model for this league. Club v2-r1 is shown only as an experimental candidate.</span>
        </div>
      )}
      {(comps.error || list.error || data.error) && <ErrorBox error={comps.error || list.error || data.error} />}
      {list.loading && <Spinner label="Loading gameweeks…" />}

      {list.data && (
        <Card title="Gameweek">
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => setGw(list.data.gameweeks[idx - 1].matchday_no)} disabled={idx <= 0} aria-label="Previous gameweek">‹</Button>
            <select aria-label="Gameweek" value={gwNo ?? ""} onChange={(e) => setGw(Number(e.target.value))} className={`min-w-0 flex-1 rounded-control bg-panel-2 font-bold ${CONTROL_EDGE}`}>
              {list.data.gameweeks.map((x) => (
                <option key={x.matchday_no} value={x.matchday_no}>
                  GW {x.matchday_no} · {range(x)}{x.order_issue ? " · dates out of order" : ""}{x.predictable === 0 ? " · played" : ""}
                </option>
              ))}
            </select>
            <Button variant="ghost" onClick={() => setGw(list.data.gameweeks[idx + 1].matchday_no)} disabled={idx < 0 || idx >= list.data.gameweeks.length - 1} aria-label="Next gameweek">›</Button>
          </div>
          {g && (
            <p className="mt-2 text-xs text-mute">
              {g.fixtures} fixtures · {g.completed} completed · {g.upcoming} upcoming · {g.awaiting_result} with the date passed and no verified result · {range(g)}
              {gwNo === list.data.next_gameweek ? " · next gameweek" : ""}
            </p>
          )}
          {g?.order_issue && <div className="mt-2"><Notice tone="warn">Some fixtures in this gameweek are dated far from the rest (probably rescheduled). Each is flagged on its card.</Notice></div>}
        </Card>
      )}

      {league && league.state === "stale" && (
        <Notice tone="warn" title={`${key} results are stale.`}>
          Newest verified result {league.latest_result ?? "unknown"}; {league.awaiting_result} played match(es) have no result in any approved source. Forecasts that depend on them are marked provisional.
        </Notice>
      )}

      {data.data && (
        <Card title={`${data.data.label} fixtures`} subtitle={`${data.data.season} · latest verified result in this competition: ${data.data.latest_result ?? "none"}`}
          right={<Button onClick={predict} disabled={blocked || run.loading || predictable === 0}>{run.loading ? "Predicting…" : "Predict gameweek"}</Button>}>
          <ul className="space-y-1 text-xs text-mute">
            <li>Forecasts are computed and saved <strong className="text-ink/80">only when you press Predict gameweek</strong>; looking at this page never saves anything. Only fixtures that have not been played are forecast.</li>
            <li>Every forecast uses results dated before that fixture's day only, never the same day or later. Saved forecasts are application history, not the official prospective evaluation.</li>
          </ul>
          {blocked && !club.error && <div className="mt-3"><Notice tone="info" title="Club models are warming up.">Waiting for <code>/api/health</code> to report the model history is ready (about 20 seconds after start-up).</Notice></div>}
          {club.error && <div className="mt-3"><Notice tone="bad" title="Backend not reachable.">{club.error.message}</Notice></div>}
          {predictable === 0 && <div className="mt-3"><Notice tone="info">No fixture of this gameweek can be forecast now: each is played, past its kickoff (awaiting a verified result), postponed or cancelled. Forecasts saved earlier stay visible.</Notice></div>}
          {run.loading && <Spinner label="Running the frozen models for every fixture… this can take up to 30 seconds when fixtures need a day-by-day history replay." />}
          <div className="mt-3"><ErrorBox error={run.error} /></div>
          {run.result && (
            <div className="mt-3">
              <Notice tone="info" title="Saved.">
                {run.result.saved_fixtures} fixtures forecast at {run.result.created_utc.replace("T", " ").replace("Z", " UTC")} (run #{run.result.forecast_run_id}), history through {run.result.data_cutoff_date}. Models: {Object.values(run.result.models).join("; ")}.
              </Notice>
            </div>
          )}
        </Card>
      )}

      {ev && ev.finished_with_forecast > 0 && (
        <Card title="Predicted versus actual" subtitle="Forecast saved before kickoff against the verified result">
          {ev.counted > 0 ? (
            <p className="text-sm">
              <strong>{ev.correct}</strong> of <strong>{ev.counted}</strong> finished fixtures called correctly ({pct(ev.accuracy, 0)}), mean log loss <strong>{ev.mean_log_loss.toFixed(3)}</strong>.
            </p>
          ) : (
            <p className="text-sm text-mute">No finished fixture has a forecast that is certainly from before kickoff.</p>
          )}
          {ev.excluded > 0 && <p className="mt-1 text-xs text-mute">{ev.excluded} finished fixture(s) with a forecast are shown but not counted (saved when it cannot be shown to be before kickoff).</p>}
          <p className="mt-1 text-xs text-mute">{ev.caveat}</p>
        </Card>
      )}

      {data.loading && !data.data && <Spinner label="Loading fixtures…" />}
      {data.data && (
        <>
          <p className="text-xs text-mute">
            {saved > 0 ? `${saved} of ${data.data.fixtures.length} fixtures have a saved forecast (latest run per fixture shown).` : "No forecast saved for this gameweek yet."} Dates are as published in the schedule; times shown only when a source states them.
          </p>
          {[...warningGroups.values()].filter((g) => g.count > 1).map((g) => <div key={g.id} id={g.id}><Notice tone="warn" title={`Why provisional: ${g.count} fixtures share these warnings.`}><ul>{g.reasons.map((r) => <li key={r}>{r}</li>)}</ul><p>Each affected fixture retains its provisional label and full explanation under Details.</p></Notice></div>)}
          <div className="grid gap-3 lg:grid-cols-2">
            {data.data.fixtures.map((f) => (
              <FixtureCard key={f.record_id} f={f} sharedWarningId={warningGroups.get(JSON.stringify(f.reasons))?.count > 1 && f.reliability === "provisional" ? warningGroups.get(JSON.stringify(f.reasons)).id : undefined} />
            ))}
          </div>
          {data.data.runs.length > 0 && (
            <Card title="Saved forecast runs for this gameweek" subtitle="Each press of Predict gameweek adds a run; earlier runs are never overwritten">
              <ul className="space-y-1 text-xs text-mute">
                {data.data.runs.map((r) => (
                  <li key={r.forecast_run_id}>
                    Run #{r.forecast_run_id} · {r.created_utc.replace("T", " ").replace("Z", " UTC")} · history through {r.data_cutoff_date} · {r.fixtures} fixtures
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
