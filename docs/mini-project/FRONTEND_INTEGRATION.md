# Frontend integration guide (React)

> **Scope update (Phase 4.18): FootIQ now supports exactly SIX competitions** - the five domestic leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1) and the UEFA Champions League. The Europa League, Conference League, World Cup, Nations League and Copa America were removed from the active scope (their data is preserved, nothing in the application shows or predicts them). Anything below that describes them is history. Authoritative description: `docs/mini-project/phase4/P4_18_SIX_COMPETITION_SCOPE.md`.

Reference for every endpoint: [API_REFERENCE.md](API_REFERENCE.md). The existing `app/static/index.html` is a working example of every call.

## Setup

1. Run the backend: `.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000` (needs `data/miniproject/matches.csv`; build it with `app/prepare_data.py`).
2. Vite dev server on port 5173 (or CRA on 3000) works directly: CORS already allows those origins. For another origin set `FOOTIQ_CORS_ORIGINS=https://your.origin`. Alternative with no CORS at all: a Vite proxy `server.proxy['/api'] = 'http://127.0.0.1:8000'` and call relative `/api/...` URLs.
3. Base URL from an env var (`VITE_API_URL`), not hard-coded.

## Suggested screens -> endpoints

| Screen | Calls |
|---|---|
| Home (dashboard) | `/api/featured-fixture` (one request for the featured match, the next fixtures, the latest results, freshness and eligibility; cached 60 s) + `/api/competitions/{key}/seasons` -> `/coverage` and `/dashboard?season=` for the league overview |
| Matches | `/api/matches` only (filters, pages by cursor, counts, facets, freshness); links onward to `/predict?mode=gameweek&comp=&season=&gw=`, `/predict?mode=manual&comp=&home=&away=` and `/compare?comp=&a=&b=` |
| About the data (a section of Models) | `/api/competitions`, `/api/meta` (attribution, limitations, data cutoffs) |
| Competition dashboard | `/api/competitions/{key}/seasons` -> `/dashboard?season=` (+ `/coverage` for the "season incomplete" banner) |
| Team & head-to-head | `/api/competitions/{key}/teams` -> `/api/team?key=&team=&opponent=` |
| Predict a match | `/teams` for both selectors -> `/api/predict` |
| Data freshness per competition | `/api/data-freshness` |
| Season simulator (experimental, points-only) | `/api/gameweeks` (seasons) -> `GET /api/season/status` (eligibility, gates, rules) -> `POST /api/season/points` only on the user's button press -> `/api/season/runs`, `/api/season/run?id=` (history) |

## Rules the UI must follow on the Home page

1. **One request feeds the banner and both lists: `/api/featured-fixture`.** Do not use `/api/gameweek` for it (about 4 to 10 s on the current store, see [phase4/P4_2_PERFORMANCE_INVESTIGATION.md](phase4/P4_2_PERFORMANCE_INVESTIGATION.md)). The response is cached for 60 s and has an `ETag`; the page needs no polling.
2. **Never create a forecast from Home.** Show `featured.forecast` only when it is not `null` (it was saved earlier with *Predict gameweek*); otherwise say that none is saved. Home sends no `POST` and no `/api/predict` request.
3. **Show the kickoff as `kickoff.state` says:** `utc` as a UTC time, `local_without_time_zone` as a local time with "time zone not stated", `unknown` as "time not confirmed". Never convert or guess a time; `matchday_label` can be `null`.
4. **Show freshness and reliability next to the fixture:** `freshness.competitions[competition_key]` (state and newest verified result) and `eligibility.reliability` (`provisional` is labelled as such, with `reasons[]` available).
5. **`featured: null`** is a normal answer: show `empty_state.message` and the staleness of the leagues, not a made-up fixture. A club with `resolved: false` is shown by name and marked "Club not matched".
6. **Each part fails alone.** The banner, the league table and the lists have their own loading, error and retry states; a failed request never blanks the page.

## Rules the UI must follow for the season simulator

Full field list: [API_REFERENCE.md](API_REFERENCE.md); what exists today: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

1. **Never run on page load.** The simulation is saved when the user presses *Run points-only simulation*; send `user_action: "simulate_points_button"` and show the backend's 422 `detail` as-is.
2. **Keep the label** "Experimental — Points-only simulation" next to every result. The points table has no position field; do not add a rank column or a "predicted table".
3. **Position ranges** come only from `result.position_bounds`. Show them only when `status === "available"` **and** every `guaranteed`, `possible`, `unresolved` is a number in [0, 1] with `guaranteed <= possible`; otherwise show a notice and **no numbers**. When `status === "unavailable"` show `reason`. A saved run without `position_bounds` predates the feature: say so.
4. **Never show a range as one probability.** Render `lower–upper%` (one number only when both are equal), label them lower and upper bounds, and keep the sentence "not exact probabilities" visible. Values below 0.05% show as `<0.1%`, values above 99.95% as `>99.9%`; clamp to 0-100% before formatting.
5. **Explain in plain words** (what lower and upper mean, what a wide range means) and render `limitations[]`, `rules.criteria_used`, `rules.sources` and the sampling error (`1.96 x max(se_guaranteed, se_possible)`).
6. **Pending rules:** when `rules.live_confirmation` is set (La Liga until the federation file's checksum is verified) show a visible warning; do not call that league's rules "confirmed".
7. **Relegation** is direct relegation only (`bands[].positions`); the Bundesliga's 16th-place play-off is not simulated and not part of it.

## Rules the UI must follow

1. **Always show `validation_badge`** beside predictions, with `validation_basis` available on hover or expansion. UEFA club competitions are `Not validated (indicative only)`; do not style them like validated ones.
2. **Render `notes[]`** from prediction responses (low history, far-future date, rating cut-off, venue assumption).
3. **Show `primary` first**; show `secondary` (club v2-r1) as "candidate, development-validated only"; `elo_only` as a baseline. Draw the three probabilities as one stacked bar (they sum to 1).
4. **Never invent a team name**: fill selectors from `/teams`. Names are exact strings; URL-encode them (`encodeURIComponent`). Do not offer a team list from one competition for another.
5. **Date picker for `/predict`** is optional. Pre-fill from `/api/meta` -> `data_through` (clubs: min = day after `club_results`; internationals: min = `international_ratings`) and let the server's 422 message handle the rest.
6. **Neutral/home toggle** only for `group == "International"` (default neutral; Nations League default home).
7. **Season incomplete banner** when the matching `/coverage` row has `note == "incomplete or in progress"`. International competitions have no expected counts (`""`).
8. **Null handling:** `standings` is `null` for cups/internationals; `home_win_rate` etc. can be `null`; `group_tables` is `null` in `pre_tournament` mode.
9. **Footer:** render `attribution[]` (Wikipedia-derived UEFA data is CC BY-SA 4.0 and needs attribution).

## Loading and errors

- **Club-prediction warm-up:** after backend start, `/api/health` returns `club_prediction_ready: false` for about 20 s. Poll it every 2-3 s, disable the Predict button (or show "loading model history") until `true`. A request sent earlier still succeeds but may take about 20 s.
- **Simulator:** default 5,000 simulations: about 1 s (`current`) or 8 s (`pre_tournament`). Show a spinner; disable the button while running; avoid more than 20,000 simulations in `pre_tournament` mode from the UI (50,000 takes about 80 s). Passing a fixed `seed` makes results repeatable (useful for demos).
- **Errors:** read `await res.json()` -> `detail` (string, always). Show it as-is; 404 means a stale selection, 422 means correct the input.

## Minimal client

```ts
const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
export async function api<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T> {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)]));
  const res = await fetch(`${API}${path}?${q}`);
  if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail);
  return res.json();
}
// api("/api/predict", { key: "EPL", home: "Arsenal FC", away: "Chelsea FC" })
```

## Known data limits to surface in the UI (also in `/api/meta`)

- Club data and club-model history end 2026-09-20; international ratings end 2026-06-02. 2026-27 league seasons are partial; Ligue 1 2019-20 has 279/380; Conference League has no 2026-27 rows; Nations League ends at the 2025 finals; the 2026 World Cup final is not in the data.
- International scores include extra time; there is no 90-minute result for them.
