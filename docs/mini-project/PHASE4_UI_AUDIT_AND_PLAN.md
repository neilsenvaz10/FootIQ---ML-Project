# Phase 4: premium UI redesign. Audit and implementation plan (for your approval)

Date: 2026-10-26. **Status: audit finished, plan only. No frontend source file, test, backend file, model, production data or setting was changed.** Everything below was measured on the running application (private copy of the database, in-app browser at 1440, 820 and 375 px) and by reading all 3,592 lines of `frontend/src`. Nothing is staged, committed or pushed. **I stop here until you approve the plan (section 5).**

Screenshots of the current state are in `docs/mini-project/phase4/audit/` (index in section 8).

**Update 2026-10-27:** the eight decisions in section 5 were approved on 2026-10-26 (visual reference = the dark-purple description in `UPGRADE_PLAN.md`, self-hosted Inter, one read-only featured-fixture endpoint in P4.2, a `/matches` hub, five-plus-More mobile navigation, TeamCrest with a licensed local manifest, Home charts moved to Models, checkpoints after P4.1, P4.3 and P4.7). **P4.0 and P4.1 are done**; the technical report, test results and screenshots are in [phase4/P4_1_CHECKPOINT_REPORT.md](phase4/P4_1_CHECKPOINT_REPORT.md), and the baseline and recovery procedure in [phase4/RECOVERY.md](phase4/RECOVERY.md). Work stopped at that checkpoint. You then approved it and authorised P4.2 only. **P4.2 (Home dashboard) is done** (2026-10-27): the Home redesign, the read-only `GET /api/featured-fixture` endpoint, the `/api/gameweek` slowdown investigation (optimisation proposed, not applied) and the tests, build and browser checks are in [phase4/P4_2_CHECKPOINT_REPORT.md](phase4/P4_2_CHECKPOINT_REPORT.md) and [phase4/P4_2_PERFORMANCE_INVESTIGATION.md](phase4/P4_2_PERFORMANCE_INVESTIGATION.md). Work stopped again at that checkpoint. You approved it and authorised P4.3, which is done too (the `team_form` optimisation, unconfirmed time-zone rules, the Matches hub and the Predictions redesign): [phase4/P4_3_CHECKPOINT_REPORT.md](phase4/P4_3_CHECKPOINT_REPORT.md). Work stopped at checkpoint 3; P4.4 to P4.7 have not been started. The status line above describes the document as first written.

## 0. Summary

**What exists.** The frontend is not a blank slate. An earlier phase already delivered a dark-violet theme (14 colour tokens, gradient hero cards, KPI tiles), a left sidebar from 768 px and a bottom tab bar below it, a freshness bar, fixture cards with reliability chips, a league table with form dots, probability bars and gauges, the World Cup simulator, the Season simulator with position ranges, and 65 tests. Phase 4 is therefore a **consolidation and upgrade** of that base (a real design system, a dashboard, better match and prediction components, tablet support), not a rewrite.

**What is missing against your brief** (details in section 2.11):
1. **No featured upcoming-match banner and no fixtures or results on Home.** Home shows the *previous* complete Premier League season, a dataset-size bar chart and a pie chart.
2. **No design system.** About 65 hard-coded colours outside the theme, an `Inter` font that is never loaded (so every device falls back to a different system font), a fragmented type scale (99 uses of `text-xs`, 44 of a 11 px size, sizes down to 9 px), duplicate components, and "info" messages coloured green like "OK".
3. **Club identity is initials only and inconsistent**: `SV 07 Elversberg` renders as **"0E"**, `SC Paderborn 07` as **"P0"**, `1. FSV Mainz 05` as **"1M"**, some clubs get two letters and some three.
4. **Tablet is the weakest width**: from 768 px the full 240 px sidebar stays open (29% of an 820 px screen), hero buttons break words ("Compa-re teams") and team names truncate to "Arsena…".
5. **Accessibility gaps**: primary-button text fails contrast at the gradient's blue end (3.2:1, needs 4.5:1), control borders are 1.3:1, touch targets below 44 px on every page (tabs and pills are 36 px), tabs and pills without keyboard arrow support, a static page title, no skip link.
6. **The Gameweek prediction page works but is a long single column** with controls far from results and 1 / X / 2 labels instead of team names.

**What is already good and must be kept**: honest copy (never "live"), explicit-action rules (Predict gameweek, Run simulation), provisional and stale chips, the eligibility gates and experimental labels of the simulators, no horizontal overflow at 375 px on any page, text contrast above 4.5:1 everywhere measured, one `h1` per page and no unnamed controls.

**Proposal.** Seven incremental phases (section 4), each ending in a checkpoint where all tests, the build and the integrity checks pass. A baseline snapshot of `frontend/` is taken first because the folder is untracked in git and could not otherwise be reverted.

**Decisions I need** (section 5): the visual reference (**I could not find the image**), the font, whether to add one small read-only backend endpoint for the featured fixture, a `/matches` page, the crest policy, and mobile navigation.

## 1. Scope, constraints and the visual reference

### 1.1 Your restrictions (all respected by this audit and by the plan)
No change to the frozen models, production football data, official prospective-evaluation files or live-synchronisation settings; **nothing staged, committed or pushed**; no invented scores, player statistics or fixtures; no unlicensed player imagery; the UI must work when data is missing or stale; existing API integrations, prediction calculations, the World Cup simulator, the experimental points-only and position-range simulations, the freshness warnings, provisional flags and eligibility restrictions are preserved. During the audit the production database was only read: after it, its hash, integrity check, manifest of 17 protected files, `simulation_runs` = 0 and `live_enabled` = false were re-verified unchanged.

### 1.2 The "previously approved dark-purple dashboard" reference
**I cannot see it.** The repository holds no image or mock-up of it (no `png`, `jpg` or `svg` anywhere in `frontend/`). The only record is the text of `docs/mini-project/UPGRADE_PLAN.md` section 6: *"the dark-purple dashboard from your earlier reference set (sidebar, spacious cards, club-crest hero, two-column home) as the primary style"*, plus two layout images from that message (a data-flow diagram and a fixture-predictions layout) that are not stored either. This plan is therefore built from that description and from your Phase 4 brief. **Please re-attach the reference (or confirm that the description is enough) before I start section 4, phase P4.1.** I will treat it as inspiration, not a copy: FootIQ branding, our own copy and colours.

## 2. Audit

### 2.1 Inventory
| Area | What is there |
|---|---|
| Stack | React 19.3, React Router 7, Recharts 3, Tailwind CSS 4.3 (CSS-first `@theme`), Vite 8, Vitest 5 with Testing Library and jsdom. No icon, font, animation or state library. |
| Size | 3,592 lines in `src` (pages 2,373, components 968, lib 169, CSS 37, app 45) and 1,124 in tests. |
| Routes | `/` Home, `/analytics?comp=` Leagues, `/compare`, `/predict?mode=gameweek|manual`, `/simulations?tab=worldcup|season` (also `/worldcup`), `/models`, `*` (a one-line "Page not found"). All route components are lazy-loaded. |
| Shell | `Layout.jsx`: left rail 240 px from `md` (768 px), slim top bar and fixed bottom tab bar below; `SyncStatus` freshness bar and an attribution footer on every page; `MetaContext` loads `/api/meta` once. |
| Pages | `Overview` 217 lines, `Analytics` 251, `TeamComparison` 164, `Predictions` 34 (tab host) with `GameweekPredict` 173 and `Predict` 271, `Simulations` 38 (tab host) with `Simulator` 259 (World Cup) and `SeasonSimulator` 793, `Models` 173. |
| Components | `ui.jsx` 375 lines (Card, Badge, Notice, Spinner, ErrorBox, Empty, Kpi, Field, Select, Input, Button, Pills, Tabs, TeamAvatar, SectionCard, MatchRow, DataTable, FormChips, Icon with 6 icons, StatCard, FormDots, CompareRow, Gauge), `FixtureCard`, `ProbBar`, `Bracket`, `SyncStatus`, `SourceDetails`, `TeamPool`, `CompetitionSelect`, `PageHeader`. |
| Lib | `api.js` (fetch client, `ApiError`), `hooks.js` (`useApi`, `useClubReady`), `format`, `team` (initials, hue, short date), `chart` (Recharts theme), `competitions`, `sources`. |
| Tests | **65**: 56 with a mocked API (`app` 17, `gameweek` 8, `redesign` 14, `season` 17) and 9 live-contract tests (opt-in, read-only). |

### 2.2 API integration map (the contract that must not change)
| Page | Endpoints used |
|---|---|
| Shell | `GET /api/meta`, `GET /api/sync/status` |
| Home | `/api/competitions`; snapshot: `/api/competitions/{key}/seasons`, `/coverage`, `/dashboard?season=` |
| Leagues | `/api/competitions`, `/seasons`, `/dashboard` (plus up to 12 more `/dashboard` calls for the trend chart), `/coverage` |
| Compare | `/api/competitions`, `/seasons`, `/teams`, `/api/team` (twice) |
| Predictions, gameweek | `/api/competitions`, `GET /api/health` (polled until the club models are ready), `/api/gameweeks`, `/api/gameweek`, **`POST /api/gameweek/predict`** (only on the button), `/api/sync/status` |
| Predictions, manual | `/api/competitions`, `/api/health`, `/teams`, `/api/predict` |
| Simulations, World Cup | `/api/worldcup/simulate`, `/api/worldcup/bracket` |
| Simulations, season | `/api/gameweeks` (seasons), `/api/season/status`, `/runs`, `/run`, **`POST /api/season/points`** (only on the button); `POST /api/season/simulate` is never enabled |
| Models | `/api/models/performance` |

**Measured latencies (private copy, idle machine):** `/api/gameweeks` 0.23 s; `/api/sync/status` 0.26 s; **`/api/gameweek` 3.6 to 3.8 s per call**; points-only simulation about 7 s; club-model warm-up about 20 to 30 s after start-up. The slow call matters for a Home banner (section 3.4): its per-fixture "form" queries each scan about 220,000 completed matches (0.37 s a query, two per fixture).

### 2.3 Features that must not regress (the do-not-break contract)
| Feature | Where | Guarded by |
|---|---|---|
| Data-freshness bar: latest result, last update, "Sync: off (cached data only)", "N leagues stale", per-league detail table, never "live"; hidden on 503, warning on other errors | `SyncStatus` | `redesign.test` (2) |
| Attribution and licences on every page; "Historical data only ... Nothing on this site is live" | `Layout` | `app.test` Overview |
| Gameweek forecasts saved **only** on **Predict gameweek**; disabled until the club models are ready; stale-league warning; provisional / fully-supported chips; reason flags; predicted-versus-actual; saved runs list | `GameweekPredict`, `FixtureCard` | `gameweek.test` (8) |
| Manual prediction: ready gate, two different teams, date not before the data cut-off, venue only for international, model tabs, badge, notes, disclaimer, "NOT validated" notes | `Predict`, `ProbBar` | `app.test` (5) |
| World Cup simulator: modes, simulations 100 to 50,000, seed, estimate, cancel, top-five and progression charts, leaderboard, group tables only when provided, **real** bracket that never claims a champion | `Simulator`, `Bracket` | `app.test` (4), `redesign.test` (3) |
| Season simulator: eligibility banner (Ready / Provisional / Not eligible), rule notice with the **La Liga pending warning**, points-only run on the button only, **position ranges** (lower and upper bounds, validity guard, details, rule limitations), saved-run history, disabled final-position tab, assumptions panel | `SeasonSimulator` | `season.test` (17) |
| Leagues: incomplete-season notice, international extra-time note, table, matches, stats | `Analytics` | live contract (response shapes) only; **no component test exists** (a gap the redesign will close) |
| Models: v1 accuracy, v2-r1 "dev only", international gate, UEFA "not validated" warning | `Models` | `redesign.test` (2) |
| All request paths, parameters and error handling (`{detail}` message shown as is) | `api.js` | `app.test` (3), live contract (9) |

### 2.4 Design-system audit
| # | Finding | Evidence |
|---|---|---|
| D1 | **Tokens cover colour only** (14 tokens). No spacing, radius, shadow, z-index or type tokens. About **65 hard-coded hex values** outside the token definitions (80 hex values in the source in total: `index.css` 18 of which 14 are the tokens themselves, `chart.js` 15, `ui.jsx` 13, `Simulator` 7, `Overview` 7, `Analytics` 6, `ProbBar` 6, `FixtureCard` 3, others 5). |
| D2 | **Font never loaded.** `--font-sans` names Inter but there is no `@font-face`, link or package, so Windows shows Segoe UI, macOS San Francisco, Android Roboto: typography differs per device. |
| D3 | **Fragmented type scale:** `text-xs` 99 times, `text-sm` 41, then arbitrary sizes `11px` 44 times, `13px` 11, `15px` 8, `10px` 5, `9px` 2. Text at 9 to 10 px is below a comfortable minimum. |
| D4 | **Semantic colour clash.** `info` messages are green (`text-home`), the same green as "OK", "Validated" and "home win"; the probability bar uses green / amber / red, so an **away win looks like an error**. |
| D5 | **Contrast.** Text tokens pass (ink 17.0:1, muted 6.9:1, accent 5.7:1 on the card colour). **Primary button: white on the gradient is 3.86:1 at its violet end and 3.22:1 at its blue end** (14 px bold text needs 4.5:1). **Control borders are 1.28:1** (the 3:1 non-text rule for input boundaries). |
| D6 | **Duplicate or overlapping components:** `Slot` defined twice (`Predict`, `TeamComparison`), `Kpi` and `StatCard`, `Chip` (FixtureCard) and `Badge`, `FormChips` and `FormDots`, `Card` and `SectionCard`. `ui.jsx` mixes primitives with domain widgets. |
| D7 | **Loading and error states:** a spinner only (no skeletons); the error "Try again" button reloads the whole page. |
| D8 | **Icons:** six inline paths, used only in the navigation and four hero buttons; none in cards, statuses or empty states. |
| D9 | **Unused CSS:** `.glass` is defined and never used; `.hero` is used three times. |
| D10 | **Initials defects** (`lib/team.js`): the algorithm strips punctuation *before* checking its noise list, so `1.` becomes `1` and survives; numbers survive. Seen in the app: `SV 07 Elversberg` **0E**, `SC Paderborn 07` **P0**, `1. FSV Mainz 05` **1M**, `SC Freiburg` **FRE** but `Borussia Dortmund` **BD**. Colours come from a string hash, so they are stable but arbitrary. |

### 2.5 Page-by-page visual audit
| Page | What works | Problems |
|---|---|---|
| **Home** ([desktop](phase4/audit/desktop-home.jpg), [tablet](phase4/audit/tablet-home.png), [mobile](phase4/audit/mobile-home.jpg)) | Clear hero, quick actions, freshness bar, league pills, KPI tiles with coloured edges, form dots | No featured fixture, no upcoming fixtures, no latest results. The snapshot shows the **previous** season (Premier League 2025-26, Arsenal 85 points) although current-season data exist. Two dataset charts (rows per competition, validation pie) pull the 352 kB chart chunk for little user value. Content is a 896 px column in a 1,200 px area, no second column. |
| **Leagues** ([desktop](phase4/audit/desktop-leagues-table.png)) | Competition hero, tabs, "Incomplete season" notice (61 of 306 matches), table with form dots and a leader accent | No sticky header; no position-zone markers (and the API has none, see 2.9); club names never truncate (`whitespace-nowrap`), so long names can make the table scroll sideways inside its card on phones (read from the code, not screenshotted); stats tab is two plain charts. |
| **Compare** ([desktop](phase4/audit/desktop-compare.png)) | Head-to-head bar, previous meetings, form comparison | Initials badges only; "Team A / Team B" slots are plain selects; the empty state is a dashed box. |
| **Predictions, gameweek** ([desktop](phase4/audit/desktop-predictions-gameweek.png), [tablet, cropped](phase4/audit/tablet-predictions-gameweek-bundesliga.png), [mobile fixtures](phase4/audit/mobile-predictions-fixtures.jpg), [mobile forecasts](phase4/audit/mobile-predictions-forecast-cards.jpg)) | Honest and complete: real fixtures with UTC kickoff, status, provisional and stale warnings, saved-forecast bar with timestamp and model | Controls (league, season, gameweek, notes, button) form a long column before the first fixture; the forecast bar labels sides **"1" and "2"** instead of team names; team names truncate at 375 px ("SV 07 Elvers…"); many chips compete; the gameweek counts are small grey text; away win drawn in red. |
| **Predictions, manual** | VS hero, probability bar with 1 / X / 2 tiles, gauges, model comparison chart, input bars | Long page; hero uses 72 px initials; chart and gauges repeat the same three numbers. |
| **Simulations, World Cup** ([desktop](phase4/audit/desktop-simulations-worldcup.png)) | Complete: modes, validation, estimate, charts, leaderboard, real bracket | Dense; the "archived state" notice is green (D4); charts are default Recharts. |
| **Simulations, season** ([controls](phase4/audit/desktop-simulations-season-controls.png), [ranges](phase4/audit/desktop-simulations-season-ranges.png)) | Eligibility banner (today Bundesliga is **Provisional**: 2 fixtures without result), rule notice, explicit run, ranges with explanation | Very long page; two explanatory blocks before any number; the 793-line component mixes tables, ranges, assumptions and history. |
| **Models** ([desktop](phase4/audit/desktop-models.png)) | Clean KPI row, honest "Read these as history" notice, tables | Mostly text and tables; fine as a reference page. |

### 2.6 Responsive audit
| Width | Result |
|---|---|
| **375 px (phone)** | **No horizontal overflow on any of the six pages measured.** Bottom tab bar with six items fits. The freshness bar takes about four lines above the content. |
| **820 px (tablet)** | The 240 px sidebar stays open (29% of the screen). Hero action tiles wrap mid-word ("Compa-re teams", "Model perfor-mance"); snapshot cards truncate names to "Arsena…", "Manch…"; form dots are clipped. |
| **1440 px (desktop)** | Content is a centred 896 px column (`max-w-4xl`); about 38% of the area is empty margin; `xl` breakpoint never used (`sm` 72 uses, `md` 17, `lg` 7). |

### 2.7 Accessibility audit (measured in the browser and read in the code)
| Check | Result |
|---|---|
| Text contrast (every visible text node on six routes, alpha blended) | **0 failures** at 375 px; theme tokens in 2.4 D5 |
| Headings | one `h1` per page; no skipped levels |
| Landmarks | `main`, `nav` ("Main", two variants, only one displayed), `aside`, `footer`, `header`; **no skip link**; `lang="en"` set |
| Names | no unnamed buttons, links, selects or inputs on the six routes |
| **Touch targets below 44 px** (phone width) | Home 29, Predictions 15, World Cup 9, Leagues 4, Compare 3, Models 2: tabs and pills are 36 px high, prev/next 40 to 45 px, inline links 16 px |
| **Keyboard** | `Tabs` use `role="tab"` without arrow-key movement, `aria-controls` or `tabpanel`; `Pills` use `role="radio"` without arrow keys or roving focus; focus ring is defined globally (good) |
| Page title | the same static title on every route; no focus move on route change |
| Motion | spinner only; no `prefers-reduced-motion` rule (low risk) |
| Charts | Recharts SVG without text alternatives (the numbers are repeated in text in most places) |

### 2.8 Performance audit
Production build (gzip where printed): entry JS 283 kB (**90 kB gzip**), CSS 39.6 kB, **Recharts bar-chart chunk 352 kB (102 kB gzip)**, season simulator 37 kB, predictions 27.8 kB, world cup 14.5 kB, leagues 9.5 kB, home 9.4 kB, models 7.8 kB. Home and Leagues both load the large chart chunk. No data cache: every route change refetches `/api/competitions`; `ErrorBox` retry reloads the page.

### 2.9 Data honesty, licensing, missing and stale data
* **Everything displayed comes from the API**; the frontend contains no football data. The only hard-coded football-adjacent copy is "11 competitions" in the Home hero and the footer note "historical data, not live".
* **Crests:** none exist in the repository and no licensed crest source is available. Football-data.org's own terms (clause 9.2) say logos belong to their owners; Wikipedia / Commons crests are generally non-free. **Initials are therefore the default**, and a crest may appear only from a local, licensed pack with a manifest (section 3.5). **No hotlinking, no scraping.**
* **Player imagery and statistics:** none in the product and none in the data; none will be added.
* **Fixtures are real and available.** Next gameweek per league today: Bundesliga GW8 (30 Oct to 1 Nov, 9 fixtures, **fresh**, latest result 24 Oct), La Liga GW11 (1 Nov, 10, stale, 21 Oct), Premier League GW9 (31 Oct to 2 Nov, 10, **stale**, 12 Oct), Serie A GW9 (27 to 29 Oct, 10, **stale since 20 Sep, 20 played matches without result**), Ligue 1 GW9 (30 Oct to 1 Nov, 9, **stale since 20 Sep**). Kickoff times in UTC are present for the fixtures I saw (Bundesliga and Premier League), and the UI already shows "time not confirmed" for a fixture without one. A featured banner must therefore carry the freshness and provisional state of its league, and the default should be the freshest league.
* **No competition position zones in the API** (no "Champions League places"): the redesign will not draw any, to avoid inventing information. Only facts the API gives (leader, form, the verified bands of the simulators) are drawn.
* **Missing, stale and ineligible states today:** loading, empty and error exist on every page; stale and provisional are chips and notices; "Not eligible" disables the simulators with reasons. The redesign keeps all of them and adds skeleton loaders and a retry that refetches.

### 2.10 Test coverage audit
65 tests protect text, accessible names, request bodies and gates (section 2.3). **Gaps:** no component test for the **Leagues** page; no tests for the shell and navigation, the freshness bar's layout, initials, responsive behaviour, keyboard operation or colour contrast; no visual regression; no automated accessibility check. Existing tests select mostly by accessible name and `data-testid`, so a restyle that keeps those names does not break them.

### 2.11 Gap analysis against your brief
| Brief item | Today | Gap |
|---|---|---|
| Premium dark-purple theme | Dark violet theme exists | Needs a real token system, one font, semantic colours, elevation, consistent components (D1 to D9) |
| Modern sidebar navigation | Sidebar from 768 px, bottom bar below | Collapsed rail on tablet, grouped items, freshness chip in the shell, keyboard and ARIA polish; new item(s) if `/matches` is approved |
| Featured upcoming match banner, real fixture data | **Absent** | New component; data source decision (3.4) |
| Crests where licensed, otherwise consistent initials | Initials, inconsistent and defective (D10) | `TeamCrest` with manifest and a fixed initials algorithm |
| Modern match cards, standings, prediction visualisations | Present but basic and uneven | One `MatchCard` family, `StandingsTable`, `ProbabilityBar` with team names, skeletons |
| Improved gameweek prediction interface | Works, long single column | Redesign (3.3, P4.3) |
| Consistent typography, spacing, icons, responsive layouts | Inconsistent (D1 to D3, D8), tablet weak | Tokens, font, 20+ icons, breakpoints, grids |
| Desktop, tablet, mobile | Phone good, desktop narrow, tablet weak | Per-width layouts (3.2) |
| Preserve integrations, calculations, simulators, warnings, gates | All present | Contract list 2.3 becomes the regression gate |
| Work when data missing or stale | Mostly | State matrix (3.6), skeletons, non-reloading retry |

## 3. Implementation plan

### 3.1 Principles and guardrails
1. **Presentation only.** No change to `api.js` request shapes, to any request path or parameter, to prediction or simulation code, to copy that carries a safety meaning (estimates not certainties, experimental labels, "not live", pending confirmation), or to the explicit-action rules. Where I restyle a sentence that carries such a meaning, its words stay.
2. **Accessible names and `data-testid`s are part of the contract.** The 65 tests stay as they are; if a test must change because a visible word legitimately changes, I list it and ask.
3. **Incremental and always green:** each phase ends with all frontend tests, the production build and the integrity checks passing; the old and new components coexist until each page is migrated.
4. **Only real data.** No placeholder scores, fixtures, players or crests in the product; mocks live in tests only. Unknown values show "unknown", "time not confirmed" or an explicit empty state.
5. **Private data for every run.** Visual and live checks use a private copy of the store; the production database is only ever read.
6. **Step 0 (before any change):** take a dated baseline snapshot of `frontend/src` and `frontend/tests` (the folder is untracked, so git cannot restore it) and baseline screenshots of every route at 1440, 820 and 375 px.

### 3.2 Target design (specification, not pixels)
* **Shell.** Sidebar 256 px from 1024 px with the FootIQ mark, grouped items (Overview, Analyse, Predict) and a persistent **data-freshness chip** ("Data through 24 Oct · 4 leagues stale", opens the existing detail table); **72 px icon rail** from 768 to 1023 px; bottom tab bar below 768 px with five primary items and a "More" sheet if a seventh item is approved. Content area max 1,280 px on a 12-column grid with xl breakpoints; document title and focus move on route change; skip link.
* **Tokens** (CSS variables in `@theme`): surfaces (canvas, panel, raised, overlay), borders (subtle, control), text (primary, muted, subtle), accent (violet scale), **semantic** colours (success, warning, danger, **info = violet/blue, never green**), outcome colours kept for H / D / A but marked as data colours, radii (control 12, card 20, hero 28), spacing scale (4 px base), type scale (12, 13, 14, 16, 20, 24, 32, 40) with weights, shadows (card, hero), motion durations with reduced-motion fallback. **Primary button** darkened to meet 4.5:1; **control borders** raised to 3:1.
* **Typography.** One family everywhere; no text below 12 px; tabular numerals for scores, percentages and points.
* **Icons.** An inline SVG set (about 25: navigation, calendar, clock, alert, info, check, lock, refresh, chevron, arrows, ball, whistle, table, chart, target, trophy, sliders, flag, database, sparkle for "experimental"); no dependency.
* **Core components** (new or consolidated): `AppShell`, `SidebarNav`, `FreshnessChip`, `PageHeader`, `Card` / `Panel`, `StatTile`, `Chip` (one component for statuses, flags, badges), `Banner` (semantic tones), `Button`, `Tabs` and `SegmentedControl` (keyboard-correct), `Select` / `Input`, `Skeleton`, `EmptyState`, `ErrorState` (refetch retry), `TeamCrest` (crest or initials), `MatchCard` (three densities), `ProbabilityBar` (team names, accessible text, colour-independent labels), `FormDots`, `StandingsTable`, `ChartCard` (themed Recharts, lazy).
* **Home (desktop two-column, phone single column).** (1) **Featured fixture banner**: next fixture of a chosen league (default: the freshest league), real teams, date and kickoff (UTC) or "time not confirmed", competition and matchday, the league's freshness and provisional chips, the saved forecast bar **only if one was saved**, otherwise a button to the gameweek page (never an automatic prediction); league pills to change league. (2) **Upcoming fixtures** of that gameweek. (3) **Latest results** (from the existing dashboard results). (4) **Standings snapshot of the current season** with the "incomplete season" notice. (5) **Simulation entry cards** showing eligibility ("Provisional", "Not eligible", reasons) and the "Experimental" label. (6) **Model status** badge row linking to Models. The two dataset charts move to Models under "About the data" (nothing is deleted).
* **Matches and Predictions.** Gameweek header with stepper, date range and counts; filter chips (All, Upcoming, Played, Needs attention); `MatchCard` with crest or initials, kickoff, status, flags, and the probability bar labelled with **team names** and a "Draw" segment; the Predict button stays an explicit action and becomes sticky; predicted-versus-actual as a summary band; saved runs in a drawer. Manual predictor keeps every gate; hero, bar and the "what the model saw" bars are re-laid out, the redundant gauges become optional detail.
* **Leagues and Standings.** `StandingsTable` with sticky header, compact mobile mode (position, club, P, GD, Pts, form), leader marker, form dots with accessible text; results list as `MatchCard` compact; stats tab with themed charts.
* **Simulations.** Card-based layout; the World Cup page keeps all controls and outputs; the Season simulator is reorganised in three clear blocks (eligibility, the points table, the position ranges) with explanations collapsed behind "How to read this" by default **but kept one click away**, and every label ("Experimental", "lower and upper bounds, not exact probabilities", "Live-document confirmation pending", the eligibility reasons) stays visible and unchanged.
* **Responsive rules.** Phone: single column, bottom bar, 44 px touch targets, cards instead of wide tables; tablet: icon rail, two-column grids where width allows; desktop: sidebar plus 12-column content.

### 3.3 Phases (each ends with tests, build and integrity checks green, and a short checkpoint report)
| Phase | Work | Main files | New tests | Done when |
|---|---|---|---|---|
| **P4.0** Baseline | Snapshot `frontend/src` and `tests`; screenshots of all routes at three widths; run the 65 tests and the live-contract tests on a private copy | none changed | none | Baseline stored; 65 of 65 pass |
| **P4.1** Foundations and shell | Tokens, font, icon set, consolidated primitives, `AppShell` with sidebar / rail / bottom bar, `FreshnessChip`, skip link, route titles, `TeamCrest` with the fixed initials algorithm and crest manifest support, skeleton and retry states | `index.css`, `components/*`, `Layout.jsx`, `lib/team.js` | initials (every Bundesliga and Premier League name, no digits), crest fallback, nav (roles, current page, collapse widths), skeletons, retry does not reload | All existing tests pass unchanged; every page renders in the new shell |
| **P4.2** Dashboard | Home redesign with the featured fixture, upcoming, results, standings snapshot, simulation entry cards; chart move | `pages/Overview.jsx`, new `FeaturedFixture`, `MatchCard` | featured fixture states (fresh, stale, provisional, no fixture, no kickoff time, saved forecast present or absent, backend error), no automatic predict call | Home shows only API data; stale and provisional visible; `app.test` Overview tests still pass |
| **P4.3** Matches and Predictions | `MatchCard` family, gameweek page redesign, `ProbabilityBar`, optional `/matches` hub, manual predictor re-layout | `GameweekPredict`, `FixtureCard` (replaced), `Predict`, `ProbBar` | probability bar text and sums, filter chips, sticky Predict only enabled when allowed, unchanged request bodies | `gameweek.test` and `app.test` prediction tests pass unchanged |
| **P4.4** Leagues and Standings | `StandingsTable`, results list, stats charts, competition hero | `Analytics`, `ui.jsx` | table semantics (caption, headers), compact mode, incomplete-season notice kept | Leagues tests pass; table readable at 375 px with no sideways scroll |
| **P4.5** Simulations | Re-lay both simulators with the new components; no logic change | `Simulations`, `Simulator`, `SeasonSimulator`, `Bracket` | existing 17 season tests and 4 + 4 World Cup tests pass unchanged; new test that every experimental / pending / eligibility label is still present | All labels and gates verified; the position ranges unchanged in content |
| **P4.6** Responsive and accessibility | Breakpoint pass (320, 375, 768, 820, 1024, 1280, 1440), touch targets, keyboard (tabs, pills, sheet), focus order, reduced motion, contrast and overflow probes on every route, screenshots | all | a11y checks as tests where possible (names, roles, headings, labels) | Acceptance list in 3.6 met on every route |
| **P4.7** Verification and documentation | Full frontend suite, live-contract tests, backend integration tests, production build, integrity checks, documentation (`frontend/README.md` is out of date: it still says 39 tests and omits the season simulator), final report with screenshots | docs | none | Report with screenshot matrix, test counts, contract confirmation |

### 3.4 The featured fixture: data options (needs your decision)
| Option | How | Cost | Risk |
|---|---|---|---|
| **A. Reuse only existing endpoints** | `/api/gameweeks?key=` (0.23 s) finds the next gameweek, `/api/gameweek` supplies the fixtures | **3.6 to 3.8 s** for one league, loaded after the rest of the page (skeleton meanwhile) | Slow first paint of the banner; nothing in the backend changes |
| **B. One new read-only endpoint** `GET /api/fixtures/upcoming?key=&limit=` (fixtures, status, kickoff, freshness; no per-fixture form, no model calls) | additive; about 50 ms; tests in `tests/test_gameweeks.py` | Touches `app/main.py` and `app/gameweeks.py` (not a model, not production data, not a sync setting); needs your approval because you asked to preserve the API | None to existing contracts; it only adds |
| **C. Make `/api/gameweek` fast with a database index** | `CREATE INDEX` on the entity column | would speed every page | **Changes the production database file**: not proposed |

**Recommendation: B** (and use A as the fallback if you prefer no backend change). In both cases the banner never calls a model: a forecast appears only if one was **saved** by the user pressing Predict gameweek.

### 3.5 Crest and imagery policy
`TeamCrest` renders an image **only** if `frontend/public/crests/manifest.json` lists the club with a licence and source field **and** the file exists; otherwise it renders the improved initials badge. No crest files exist today, so everything shows initials. No remote image URLs are ever loaded; no player imagery is used or possible. If you later supply a licensed pack, dropping the files and the manifest in place is enough. Initials follow one rule (strip legal-form tokens, numbers and years; two or three letters; deterministic colour); a small override table fixes names the rule handles badly (for example Borussia Mönchengladbach).

### 3.6 Verification strategy and acceptance criteria
* **Automated:** all 65 existing frontend tests unchanged and passing at every checkpoint; new component tests (section 3.3); live-contract tests on a private copy (9); backend integration tests relevant to anything touched (`tests/test_gameweeks.py`, `tests/test_seasonsim_service.py`, and the new endpoint tests under option B); production build; frozen-hash, manifest, database-integrity, `live_enabled` and git-index checks.
* **Responsive matrix** (in-app browser, private copy): 320, 375, 768, 820, 1024, 1280, 1440 px for every route and for the main states (loading, empty, error, stale, provisional, ineligible); screenshots stored in `docs/mini-project/phase4/`.
* **Acceptance criteria:** no horizontal overflow at any width; text contrast at least 4.5:1 and control and focus boundaries at least 3:1 (measured by the same probe as the audit); primary touch targets at least 44 by 44 px below 768 px; one `h1` and no skipped headings; every control named; tabs, pills and the navigation operable with the keyboard alone; document title per route; `prefers-reduced-motion` respected; initial JS not larger than today's 90 kB gzip plus 15 kB, charts lazy-loaded.
* **State matrix** (each module must define all of): loading (skeleton), empty (message), error (message and refetch), stale (chip with the dates), provisional (chip with the reason), not eligible (reason). Tested with mocks; never with invented production data.

### 3.7 Risks and mitigations
| Risk | Mitigation |
|---|---|
| The reference image is unknown (1.2) | Ask before P4.1; design from the text description; checkpoint screenshots for early correction |
| Scope creep into data we lack (a risk already named in the upgrade plan) | Only widgets backed by an endpoint; "not drawn" list stays (no scorers, xG, possession, live, momentum, transfers, player stats) |
| Slow `/api/gameweek` | Option B, or progressive loading with skeletons; never block the page |
| Test brittleness | Names and test ids are the contract; any unavoidable test change is listed for approval |
| Font download | Decision 2 below (a new dependency or system fonts) |
| Mobile navigation with a seventh item | Decision 5 |
| Regression of simulator labels | Dedicated test of every experimental, pending and eligibility label (P4.5) |
| Untracked frontend (no git rollback) | P4.0 snapshot |

### 3.8 Effort and order
About **seven working sessions** (P4.1 and P4.3 the largest). Order: P4.0, P4.1, P4.2, P4.3, P4.4, P4.5, P4.6, P4.7. I propose checkpoint reports after P4.1, P4.3 and P4.7, and I stop at any checkpoint you want to review.

## 4. What I will not do
Change a model, production football data, an official prospective-evaluation file or any synchronisation setting; call a provider; add player imagery; invent fixtures, scores or statistics; hotlink or scrape crests; stage, commit or push; run any simulation or prediction automatically; remove an existing feature or experimental label.

## 5. Decisions I need from you
1. **Visual reference.** Re-attach the dark-purple dashboard (and the two layout images) or confirm that the text description in 1.2 is enough.
2. **Font.** (a) Add the open-licence Inter variable font as a self-hosted npm package (`@fontsource-variable/inter`: a new dependency that needs `npm install`, recommended for identical typography on every device) or (b) keep the system font stack (no dependency, typography varies by device).
3. **Featured fixture data.** Option B (one small read-only endpoint, recommended) or option A (existing endpoints only, slower banner).
4. **A `/matches` page.** Add a fixtures-and-results hub (recommended, matches your "Matches and Predictions" step and the upgrade plan), or fold match cards into Leagues and Predictions only. And whether to rename the "Predict" menu item to "Predictions".
5. **Mobile navigation.** If `/matches` is added there are seven items: bottom bar with five plus "More" (recommended) or keep six and place Matches inside Predictions.
6. **Crests.** Initials only for now (recommended) with the manifest mechanism ready, or will you supply a licensed pack?
7. **Home charts.** Move "Matches by competition" and "Prediction validation" to the Models page under "About the data" (recommended) or keep them on Home.
8. **Checkpoints.** Review after P4.1, P4.3 and P4.7 (recommended), or after every phase.

## 6. Appendix A: measurements
| Item | Value |
|---|---|
| Contrast, text on card colour | ink 17.04:1, muted 6.89:1, accent 5.71:1, success 9.42:1, warning 11.57:1, danger 6.78:1 |
| Contrast, failures | white on primary-button gradient 3.86:1 and 3.22:1; control border on card 1.28:1; accent-dim on card 3.01:1 |
| Build, gzip printed | entry 90.05 kB, bar-chart chunk 102.36 kB |
| Endpoint latency | `/api/gameweeks` 0.23 s, `/api/sync/status` 0.26 s, `/api/gameweek` 3.65 to 3.77 s |
| Why `/api/gameweek` is slow | two form queries per fixture, each about 0.37 s (query plan: index on status and date, then filtering by club over the whole history) |
| Tests | 65 (56 mocked, 9 live-contract); backend suite 182 |

## 7. Appendix B: method
Source read in full; live pages driven in the in-app browser on a **private copy** of the store (a Bundesliga points-only run and a Bundesliga gameweek forecast were saved in that copy only, then the copy was deleted); accessibility probe run in the page (contrast of every visible text node with alpha blending, touch-target sizes, headings, landmarks, names, overflow); contrast of tokens computed with the WCAG formula; bundle sizes from `vite build`; latencies with `curl`; the query plan from SQLite on the production file opened **read-only**. Final integrity check: all hashes, the manifest, database integrity, `simulation_runs` 0, `live_enabled` false, nothing staged.

## 8. Appendix C: screenshot index (`docs/mini-project/phase4/audit/`)
Desktop 1440 px: `desktop-home.jpg`, `desktop-leagues-table.png`, `desktop-compare.png`, `desktop-predictions-gameweek.png`, `desktop-simulations-worldcup.png`, `desktop-simulations-season-controls.png`, `desktop-simulations-season-ranges.png`, `desktop-models.png`. Tablet 820 px: `tablet-home.png`, `tablet-predictions-gameweek-bundesliga.png` (cropped capture). Phone 375 px: `mobile-home.jpg`, `mobile-predictions-fixtures.jpg`, `mobile-predictions-forecast-cards.jpg`.
