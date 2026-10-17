# Admin Notice Slow Responses — Backend Holes and SSR Timeout

## Holes Found

Cold Notion refreshes held API callers (and through them SSR) far longer than the
per-request `NOTION_TIMEOUT` (5000ms) suggests. Two holes, both in
`backend/src/modules/admin-notices/`:

### Hole 1 — `GET /api/announcements/top` paid the full body cost

`getTopAdminNotice` called `getPublishedNotices()`, which always ran
`attachNoticeBodies`: sequential notion-to-md block conversions for up to
`NOTION_BODY_FETCH_MAX_NOTICES` (50) notices, every request passing through the
shared 340ms pacing slot. The endpoint returns only `{ id, title }`, yet on a
cold cache it waited for the whole conversion chain. The layout loader hits
`/top` on **every** route (site-wide urgent banner) and home hits it again
(pinned chip), so one cold cache dragged all SSR.

### Hole 2 — cold refresh aggregate was unbounded

`timeoutMs: 5000` bounds each Notion call, but a refresh is up to
`NOTION_QUERY_MAX_PAGES` (10) query pages plus up to 50 body conversions, all
serial. Worst case is minutes, with `inFlight` held and every cold waiter piled
on it. Single-flight, pacing and the 429 pause were already correct (verified in
`agent_memories/16-notion-admin-notices/plan.md`); only the aggregate wait had
no bound.

## Backend Fix (unreleased)

`admin-notices.service.ts`:

- `getPublishedNotices({ includeBodies }: { includeBodies?: boolean } = {})`.
  Default `true` preserves the list/detail contract exactly. `false` is the
  `/top` path: fresh/stale cache reads are unchanged (stale still triggers a
  background **full** refresh), while the cold path runs a body-free query and
  never writes the cache (which only ever holds full items). On light success a
  full refresh is kicked off behind the fast answer so the first list/detail
  view is already warm; on light failure nothing extra is kicked (a 429 pause
  must not be hammered through).
- Split fetch into `refreshFull()` (was `refresh()`, writes the cache) and
  `refreshLight()` (own single-flight slot, no cache write). Query pagination
  factored into `queryPublishedRows()`; `fetchPublishedNotices(includeBodies)`
  adds bodies only when asked.
- `waitWithBudget()` bounds only the **waiting**: the fetch always runs to
  completion in the background, so single-flight is preserved (no duplicate
  sequences) and a budget timeout still warms the cache on success
  (convergence). Exceeding the budget answers 503 fast; a cache that filled
  meanwhile is served instead of the 503.
- Budget default `ADMIN_NOTICES_REFRESH_BUDGET_MS` (15s) in
  `admin-notices.constants.ts`, overridable via `NOTION_REFRESH_BUDGET_MS` →
  `notion.refreshBudgetMs` (`backend/src/config/app.config.ts`); `<= 0`
  disables.

`controllers/admin-notices.controller.ts`: `/top` passes
`{ includeBodies: false }`. Route contract unchanged (still two GET routes, no
writes — the controller spec asserts this).

## Frontend Minimal Patch (unreleased)

`frontend/src/lib/server/announcements.ts` keeps one 2500ms race
(`raceWithTimeout`): the top loader falls back to `{ item: null }` on **any**
error (chip/banner are decorative; the layout awaits this on all routes), the
list loader lets the timeout reject. List/detail route loaders map failures to
`error(503)` (429 preserved), so a slow Notion fetch answers at once instead of
holding SSR. An earlier revision discriminated timeout errors with a marker
interface; removed as over-machinery — catch-all is the whole semantic.

## Verification Evidence

- Backend: `tsc --noEmit` 0, `nest build` green, prettier/eslint clean on all
  touched files, `jest src/modules/admin-notices --runInBand` **31/31**
  (26 service + 5 controller; was 20 + 3).
- New specs (all fail on the old code by construction — they assert the new
  behavior): cold top answers while block fetches stall forever, then warms the
  cache behind it; light served from fresh cache with no re-query; stale top
  served immediately with background full refresh; light 429 → 503 with the
  pause honored; cold refresh exceeding a 100ms test budget → fast 503, then
  convergence on resolve.
- Frontend: `npm run check` 0/0, prettier/eslint clean, comment-language
  checker 0, announcements e2e **7/7** under `DIFFCHAIN_UI_MOCK=1` (one earlier
  full run died with `ERR_CONNECTION_REFUSED` mid-run — dev-server flake,
  green on isolated and full reruns).

## Follow-ups (not done)

- Cold `/top` issues its own query plus the warming full refresh (one extra
  query sequence per cold). Acceptable at cold frequency; revisit if cold
  traffic grows.
- The 15s budget is uncalibrated against a 50-notice board with heavy pages
  (pacing floor alone ≈ 17s): such boards answer cold 503 fast and converge
  behind it, but the tradeoff deserves a live stub measurement.
- No e2e covers the timeout firing (needs a slow backend stub); the race is
  plain `Promise.race`, covered by unit-level reasoning only.
