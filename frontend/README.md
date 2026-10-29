# FootIQ frontend

React (JavaScript + JSX) + Vite + Tailwind CSS v4 + React Router + Recharts, talking to the existing FastAPI backend in `../app`.
It only displays what the API returns: **no prediction, statistics or simulation logic lives here.** Everything is historical data, never labelled live.

API contract: [../docs/mini-project/API_REFERENCE.md](../docs/mini-project/API_REFERENCE.md) · integration rules: [../docs/mini-project/FRONTEND_INTEGRATION.md](../docs/mini-project/FRONTEND_INTEGRATION.md).

## Run

Terminal 1, the backend (from the repository root):

```bash
.venv/Scripts/python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8000
```

Terminal 2, the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The backend's default CORS list already allows `http://localhost:5173` (and `127.0.0.1:5173`, `:3000`). For another origin start the backend with `FOOTIQ_CORS_ORIGINS=https://your.origin` (exact origins, never `*`).

### Backend URL

`VITE_API_URL` (default `http://127.0.0.1:8000`). Copy `.env.example` to `.env.local` to change it. **If port 8000 is already in use**, start the backend on another port (for example `--port 8001`) and set `VITE_API_URL=http://127.0.0.1:8001`, then restart `npm run dev` (Vite reads env files at start-up).

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server on port 5173 |
| `npm run build` | Production build into `dist/` (route-level code splitting) |
| `npm run preview` | Serve the build locally (add `http://localhost:4173` to `FOOTIQ_CORS_ORIGINS`) |
| `npm test` | 206 component and unit tests (mocked API, design tokens, navigation, keyboard, team badges); the 11 live-contract tests are skipped |
| `FOOTIQ_LIVE_API=http://127.0.0.1:8000 npm test` | Also runs the 11 live tests against a running backend: 9 contract tests (field names, probabilities sum to 1, badges, error shape, seeded simulator; read-only, the live suite never presses Predict gameweek) and 2 that run the team-badge generator over every real team name. Run them with `--no-file-parallelism` (the gameweek endpoint takes about 4 s) |

## Look and feel

Dark-purple football dashboard (Phase 4, stage P4.1): near-black indigo canvas with violet accents, spacious rounded cards, Inter (self-hosted from the `@fontsource-variable/inter` npm package, SIL OFL 1.1, no font CDN), a sidebar on tablet and desktop and a bottom bar with a "More" sheet on phones. Everything is built from the tokens and shared components described under "Design system" below. Pages not yet redesigned (Home, Leagues, Predictions, Simulations, Models) inherit the new tokens and components; their layouts change in the later Phase 4 stages. The data has no crest images, player photos or live feeds and none are used: team badges are generated (letters on a colour that depends only on the name) unless a licensed crest is listed in `src/data/crests.json`. No logos or brand assets of other apps are used. The comparison bars show the model's own inputs (Elo, form, rest days), not match statistics such as xG or possession, which the data does not contain.

## Pages

| Route | Page | Endpoints |
|---|---|---|
| `/matches` | Matches hub for all six competitions (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Champions League league phase): status, season, matchday and team filters, paged results and fixtures; each upcoming card links to Predict match with the clubs prefilled | `/api/matches` |
| `/` | Home: next fixture, upcoming fixtures, latest results, league overview with freshness chips | `/api/featured-fixture`, `/api/competitions`, `/api/data-freshness` |
| `/analytics?comp=` | Leagues & cups (grouped competition dropdown): season selector, KPIs, win/draw/loss pie, outcome-rate trend, league table, W/D/L bars, recent results, incomplete-season banner | `/seasons`, `/dashboard`, `/coverage` |
| `/compare` | Team comparison: two different teams, last-10 form, comparison chart, head-to-head | `/teams`, `/api/team` |
| `/predict?mode=gameweek&comp=&gw=` (also `/predictions`, which redirects here and keeps the query) | **Predictions, Gameweek tab** (five domestic leagues): season and gameweek selectors, every fixture with status, kickoff knowledge, provisional/fully-supported history flags, form, saved forecast bars with timestamps and model versions, predicted-versus-actual; forecasts are computed and saved only when **Predict gameweek** is pressed | `/api/gameweeks`, `/api/gameweek`, `POST /api/gameweek/predict`, `/api/sync/status` |
| `/predict?mode=manual&comp=` | Predictions, Manual tab: head-to-head for the six competitions (clubs passed from the Matches page stay selected). Champions League predictions carry the badge "Not validated (indicative only)" | `/api/predict` |
| `/simulations` | Simulations: the season simulator (see next row); `/worldcup` is a leftover alias of the same page | none |
| `/simulations?tab=season` | Simulations, Season simulator tab: the **experimental points-only** simulation of the rest of a domestic league season (all five domestic leagues, never the Champions League; only seasons with unplayed fixtures are offered; every press of Run saves a record) (win, draw and loss only; 3 / 1 / 0 points) with **position ranges** shown as lower and upper bounds, not exact probabilities; the data-quality and league-rules eligibility banner decides whether a run is allowed; final-position simulation stays disabled; a run starts only when the button is pressed | `/api/season/status`, `/api/season/runs`, `/api/season/run`, `POST /api/season/points` |
| `/models` | Model performance: club v1 accuracy, log loss and sample sizes, per-league results, club v2-r1 development-only status, the Champions League "not validated" warning, how to read the metrics | `/api/models/performance`, `/api/meta` |

Attribution and licences (`/api/meta`) are shown in the footer of every page.

## Behaviour worth knowing

- **Readiness check, not live polling:** after backend start-up club predictions need about 20 s of warm-up. The prediction page checks `/api/health` every 3 s until `club_prediction_ready` is true, then stops. It does nothing else periodically.
- **Team names** come from `/teams` and are sent verbatim. Club names appear in each club's most recent spelling; the backend matches by club id, so older spellings (for example "Arsenal" vs "Arsenal FC") are handled server-side.
- **Client-side checks mirror the server:** two different teams, prediction date on or after the data cut-off (`/api/meta` → `data_through`), simulation count 100-50,000, seed 0-2,147,483,647. The server's `{detail}` message is shown for anything else.
- **Errors:** every failed request shows the backend's message (or "Cannot reach the backend") with a reload button. Loading, empty and error states are consistent across pages.
- **Responsive shell:** 1024 px and up a full sidebar; 768 to 1023 px a narrow rail (icon above label); below 768 px a top bar and a bottom bar with five primary destinations (Home, Matches, Leagues, Predictions, Simulations) and a More button that opens a sheet with the other two (Compare, Models). All seven destinations are reachable at every size. Tables scroll inside their cards; checked for horizontal overflow at 375, 820 and 1440 px on every route.

## Design system

- **Tokens** live in one place, the `@theme` block of `src/index.css`: surfaces (`bg`, `sidebar`, `panel`, `panel-2`, `panel-3`), borders (`line` for decoration, `line-strong` for the edge of anything you operate), text (`ink`, `ink-2`, `mute`, `mute-2`), brand (`accent` for text and focus, `primary` for solid action fills), status (`ok`, `warn`, `bad`, `info`), match outcomes (`home`, `draw`, `away`), radii and shadows. `tests/design-tokens.test.js` reads that block and fails if a text pair falls below 4.5:1, a control edge or the focus ring below 3:1, or a stylesheet asks an external host for a font. Old names (`pitch`) still work and point at the new tokens.
- **Shared components** are exported from `src/components/ui.jsx`: Card, SectionCard, Kpi, StatCard, Badge, Chip, Notice, Button, ButtonLink, Field, Select, Input, Pills, Tabs and TabPanel (arrow keys, Home and End; roving tab stop), DataTable, MatchRow, FormDots, FormChips, CompareRow, Gauge, Spinner, ErrorBox, Empty, Icon and TeamCrest. Controls are at least 44 px tall.
- **Navigation** is defined once in `src/lib/nav.js` (seven destinations, five primary). The shell sets a descriptive page title per route, announces the page to screen readers, moves focus to the page area after a navigation, and offers a "Skip to main content" link as the first Tab stop.
- **Team badges** (`TeamCrest`, `src/lib/team.js`): three letters from the name (`Manchester City` is MCI, `1. FC Köln` is KOL; never digits or punctuation; two letters in badges under 30 px) on one of 24 colours chosen by a hash of the name, so a team looks the same everywhere. A licensed crest replaces the generated badge only when `src/data/crests.json` lists it with `file`, `licence` and `source` and the file exists in `src/assets/crests/` (see the README there). Nothing is downloaded or hotlinked.
- **`/design`** (development server only, absent from the production build) shows the tokens and components. `/design?only=controls` shows one section.

## Structure

```
src/
  main.jsx, App.jsx           router, lazy routes, /predictions redirect, development-only /design
  index.css                   design tokens (@theme), base styles, reduced-motion rules
  data/crests.json            licensed crest manifest (empty)
  assets/crests/              licensed crest files (empty; README explains how to add a pack)
  lib/api.js, hooks.js        fetch client (VITE_API_URL, ApiError), useApi, useClubReady
  lib/format.js, chart.js     formatting and the Recharts theme (CSS variables)
  lib/nav.js                  the seven destinations, active-page rules, page titles
  lib/team.js, crests.js      badge letters and colours, crest manifest checks
  lib/contrast.js             WCAG arithmetic used by the tests and the design page
  components/                 Layout, Sidebar, MobileNav, Brand, Icon, TeamCrest, ui.jsx (shared pieces), SyncStatus, PageHeader, CompetitionSelect, TeamPool, FixtureCard, ProbBar, Bracket, SourceDetails, MetaContext
  pages/                      Overview, Matches, Analytics, TeamComparison, Predictions (Gameweek and Manual tabs), Simulations (Season simulator), Models, DesignSystem (development only)
tests/                        app, redesign, gameweek, season (mocked API); design-tokens, crest, shell (P4.1); live-api and crest-live (opt-in, need the backend)
```

## Limitations

- Charts and tables use only fields the API returns. Team "form" is the last 10 matches in the selected competition; no season-level team statistics exist for cups or international competitions (the API returns no league table for them).
- Champions League predictions are not validated (always badged "Not validated (indicative only)"); the backend's notes are always shown.
- A 1,000-simulation season run takes about 4-6 s and a 10,000-simulation run about 5-35 s depending on the league; cancelling in the UI stops waiting but the backend finishes the run.
- If the backend stops after the prediction page has marked the club models ready, the next prediction shows "Cannot reach the backend".
- Data cut-off: club results through 26 October 2026 (28 October 2026 coverage in `docs/mini-project/final/FINAL_SYSTEM_GUIDE.md`); the data is historical and never labelled live.
