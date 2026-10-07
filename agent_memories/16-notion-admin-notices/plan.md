# Notion Admin Notice Board (Read-Only) — Implementation Contract

## Goal and Scope

Backend reads a Notion database and serves published admin notices; the main page shows the first one as a hero title chip linking to its body page. **CRUD happens only in Notion** — no create/update/delete endpoints exist anywhere in this feature (guarded by a controller spec that asserts a single GET route).

- Requested scope: backend Notion integration + main hero chip (→ body page), board list page
  `/announcements`, and detail/list design aligned with the site's shared patterns.
- Not requested and therefore NOT built: notice write APIs, a Notion editor UI.

## Notion Database Contract

Property names are fixed constants in `backend/src/modules/admin-notices/admin-notices.constants.ts` and must match the configured Notion database exactly:

| Notion property | Type | Role |
| --- | --- | --- |
| `제목` | title | Notice title (empty-title rows are dropped) |
| `공개 여부` | checkbox | **Publication gate** — only `true` rows are exposed |
| `상태` | status or select | Surfaced as `status` metadata, never a gate |
| `노출 순서` | number | Ascending display order; `null` sorts last |
| `내용` | rich text | Body; newlines are preserved (never whitespace-collapsed) |
| `긴급` | checkbox | Urgent flag — the top urgent row renders a site-wide banner under the header |

**HIGH**: `공개 여부` is the only publication filter. `상태` is display metadata — filtering on it was rejected because the status option names are unknown and a wrong guess would hide every notice.

## Backend Contract

- Endpoint: `GET /api/announcements` → `{ success: true, data: { items: AdminNotice[] } }`
  (`backend/src/modules/admin-notices/`, registered in `app.module.ts`; standard read rate-limit bucket via `ApiReadRateLimitService`)
- Query: `POST {NOTION_API_URL}/v1/databases/{id}/query` with `filter: 공개 여부 = true`,
  `sorts: 노출 순서 ascending`, `page_size 100`, pagination capped at `NOTION_QUERY_MAX_PAGES = 10`
  (axios, `Authorization: Bearer`, `Notion-Version: 2022-06-28`)
- In-memory defense: unpublished/empty-title rows are dropped again after mapping, and `노출 순서`
  is re-sorted ascending in memory with `null` last (stable sort keeps Notion's relative order)
- Config (`backend/src/config/app.config.ts` `notion.*`, documented in `backend/.env.example`):
  `NOTION_API_KEY`, `NOTION_DATABASE_ID` (both required to enable), `NOTION_API_URL`
  (default `https://api.notion.com` — also enables stub-based testing), `NOTION_TIMEOUT` (default 5000ms),
  `NOTION_CACHE_TTL_MS` (default 60000ms — env-injectable in-memory cache TTL, values <= 0 disable the cache),
  `NOTION_MIN_REQUEST_INTERVAL_MS` (default 340ms — outbound pacing under Notion's ~3 req/s budget, <= 0 disables)

### Caching and Failure Contract (**CRITICAL**)

- 60s in-memory cache (default `ADMIN_NOTICES_CACHE_TTL_MS`, overridable at runtime via `NOTION_CACHE_TTL_MS` → `notion.cacheTtlMs`) keyed in the singleton service — all visitors share one Notion fetch, keeping well inside Notion rate limits
- **TTL expiry = stale-while-revalidate (non-blocking)**: an expired cache is served immediately from the stale snapshot while a single background refresh runs; the updated data appears from the next request on, so a slow Notion call never blocks a page view. A cold cache (no snapshot) still waits for the first fetch — there is nothing else to show. Background failures are logged inside the flight and the stale snapshot keeps being served
- **Unconfigured** (missing key or database id): returns `{ items: [] }` once-logged, treated as "feature off" so production does not scream before the env is set
- **Notion error with a cached snapshot**: serves the stale snapshot (a pinned board must not blink out on a transient failure)
- **Notion error with no snapshot**: `503` with a Korean message; the frontend `.catch(() => ({ items: [] }))` renders the home page without the section

### Rate-Limit Compliance (**CRITICAL**)

Notion rate-limits integrations to ~3 requests/second on average (429 + `Retry-After`). The only
Notion call site in the whole repo is `AdminNoticesService` (its paginated query loop); it defends
on three levels:- **Single-flight**: concurrent cache misses and background revalidations share one `inFlight` fetch promise — a visitor burst collapses into exactly one Notion query sequence (failure logs emitted once per flight)
- **Pacing**: every outgoing request passes `waitForRequestSlot()` — a 340ms minimum gap
  (`NOTION_MIN_REQUEST_INTERVAL_MS` → `notion.minRequestIntervalMs`; <= 0 disables) shared across
  pagination and refetches, sustaining ~2.9 req/s
- **429 backoff**: on 429 the service records `rateLimitedUntil` from `Retry-After`
  (default 1s, capped 60s) and, during the pause, serves the snapshot (or 503 with no snapshot)
  without touching Notion
- Inbound side (already existing): `ApiReadRateLimitService` standard bucket 60 req/60s per client

## Frontend Wiring

- Types: `AdminNotice` / `AdminNoticeListResponse` in `frontend/src/lib/types/api.ts`
- Client: `getAdminNotices()` in `frontend/src/lib/api/client.ts` (registered on `apiClient`)
- Load: all three routes (home, list, detail) go through
  `lib/server/announcements.ts::loadAdminNoticeList` — the single mock/real branch (per-route
  duplication already caused one missing-mock bug). Home adds `.catch(() => ({ items: [] }))` so a
  failed fetch just hides the chip; list/detail surface failures as the error page.
- UI: home hero renders a single notice-title **chip** (`data-testid="pinned-notice-chip"`, inline
  in `frontend/src/routes/+page.svelte` next to the kicker). **The cap to exactly 1 (first by
  노출순서) is owned solely by `+page.svelte`** (`pinnedNotice = items[0]`); the loader passes the
  full published list untouched.
- Board list `/announcements` (discussions-list design: h1 header, divided row links with status
  chip + excerpt, dashed empty state) and detail `/announcements/[id]` (notices-detail design:
  `nav[aria-label="이동 경로"]` breadcrumb back to the list + `lc-panel-card`). Footer adds a 공지사항
  link. No new backend route; detail resolves ids against `GET /api/announcements` and 404s when
  missing. testids: `pinned-notice-chip`, `admin-notices-list`, `admin-notices-list-link-{id}`,
  `admin-notices-empty-state`, `admin-notice-back-link`, `admin-notice-title`,
  `admin-notice-status`, `admin-notice-content`
- Operator-facing setup guide (Notion DB structure, integration behavior, env vars, paste-ready
  property/row/`.env` templates): root `README.md`, section "Notion 관리자 공지 게시판" — the
  single source of truth for standing up the Notion database
- **Urgent banner (site-wide)**: `+layout.server.ts` loads `adminNotices` (`.catch(() => ({ items:
  [] }))` — a failure only hides the banner; page loaders keep their own error semantics),
  `Header.svelte` derives `page.data.adminNotices.items.find(n => n.urgent)` (items already sorted
  ascending, so the first urgent row = top display order) and renders
  `UrgentNoticeBanner.svelte` directly after `</header>` on every page — red `lc-urgent-banner` bar,
  `긴급` badge, `role="alert"`, whole bar links to `/announcements/{id}`.
  testids: `urgent-notice-banner`, `urgent-notice-link`. Mock fixture `mock-announcement-1` is
  `urgent: true` so the mock e2e always exercises it.

## Verification Evidence (2026-10-07)

- Backend: `npm test` 68 suites / 871 tests green, including 12 new specs
  (`admin-notices.service.spec.ts`, `admin-notices.controller.spec.ts`); `lint`, `tsc --noEmit`, `build` green
- Live contract check: local stub Notion server + `node dist/main.js` with `NOTION_*` env →
  `GET /api/announcements` returned `[order 1, order 2, null]`, unpublished row excluded, `\n` preserved;
  stub log confirmed `filter/sorts/page_size` body, `Bearer` auth and `Notion-Version` headers;
  second request within TTL did not re-query (stub POST count stayed 1)
- Frontend: `npm run lint` + `npm run check` green; e2e `announcements.spec.ts` (3 tests: hero chip
  1개·제목 전용 / 칩→상세 본문(줄바꿈) / 목록 2행 노출 순서 + 행→상세 + 브레드크럼 디자인) +
  `home.spec.ts` 21/21 → **24 passed** under `DIFFCHAIN_UI_MOCK=1`, 1 passed + 2 skipped without mock
- **Real Notion API verified (2026-10-07)**: the operator's running backend (real
  `NOTION_API_KEY`/`NOTION_DATABASE_ID`) returned the two README sample rows — publish filter,
  노출 순서 1→2, status select mapping, newline content all correct; SSR list/detail/chip checked
  against those real rows (list 2행 순서, breadcrumb, 404 on unknown id).
- **Route rename + UX pass (2026-10-07)**: default path renamed `admin-notices` → `announcements`
  end-to-end (`@Get('announcements')` + route-path spec assertion, client path, `/announcements`
  board routes, loader moved to `lib/server/announcements.ts`, footer/hero links, e2e renamed to
  `announcements.spec.ts`, mock ids `mock-announcement-*`); user-facing copy no longer mentions
  display order or Notion internals; hero chip gained a left bullhorn icon and lower-contrast
  styling (`.lc-home-notice-chip`). Domain identifiers (backend module, `AdminNotice*` types,
  testids) intentionally keep the admin-notice name. Re-verified: backend 871/871 green,
  frontend lint/check green, full mock e2e **252 passed / 45 skipped / 0 failed**, default-mode
  e2e 1 passed + 2 skipped, live `GET /api/announcements` → 200 with the 2 real rows while the old
  path 404s.
- **`긴급` urgent banner pass (2026-10-07)**: Notion contract gained the `긴급` checkbox
  (`NOTION_PROPERTY.URGENT` → `AdminNotice.urgent`, absent property maps to `false`); site-wide
  red banner below the top nav on every page (layout load + Header derive + UrgentNoticeBanner),
  README property/copy/template tables updated to 6 properties. Re-verified: backend 873/873
  green (mapping spec asserts urgent true/false), frontend lint/check green, full mock e2e
  **253 passed / 45 skipped / 0 failed** (new banner test: header-relative position, site-wide
  persistence, click→detail), default-mode announcements spec 2 passed + 2 skipped, live
  `GET /api/announcements` → 200 with `urgent: false` on both real rows (DB has no `긴급`
  property yet — missing property must not crash).
- **Stale-while-revalidate pass (2026-10-07)**: TTL expiry no longer blocks the request — the
  snapshot is served immediately and a single background refresh updates the cache (cold start
  still blocks; 429 pause and error fallbacks unchanged). Unit: 2 new specs (stale served +
  next-request refresh; concurrent stale reads collapse to one background fetch) + `mockPost`
  once-queue reset in `beforeEach` (an unconsumed `mockResolvedValueOnce` leaked across tests and
  cascaded 4 failures — flush background flights with `setImmediate` before advancing mocked time)
  → backend **879/879 green**, lint/tsc/build green. Live timing proof (slow stub, 800ms Notion
  delay, `NOTION_CACHE_TTL_MS=2000`): TTL-expired request answered in **3.5ms** with the stale
  title while the refresh ran in the background (stub log), the request after completion served
  the updated title in **2.5ms** from cache with no extra Notion call.
- **Rate-limit compliance pass (2026-10-07)**: added single-flight, 340ms request pacing and
  429 `Retry-After` backoff to `AdminNoticesService`. Unit: 4 new specs (concurrent misses → 1
  POST; interval spacing; 429 pause honors Retry-After then resumes; default 1s cooldown without
  the header) — backend **877/877 green**, lint/tsc/build green. Live stub measurement
  (`NOTION_API_URL` → local stub returning 2-page fetches, `NOTION_CACHE_TTL_MS=2000`, default
  pacing): 10 concurrent cold requests → **2** stub requests (single-flight; would be 20 before);
  10 concurrent after TTL → 2 more; within-fetch gaps **341/341/342ms ≥ 340ms** (min gap overall
  341ms ≈ 2.93 req/s < 3 req/s); stub 429 `Retry-After: 2` → stale snapshot served with HTTP 200,
  3 follow-up requests during the pause → **0** stub calls, log line `pausing Notion requests for
  2000ms`, refetch resumed after the window (sequence `1,2,1,2,429,1,2`).

## Block body → Markdown pass (2026-10-07)

- **Problem**: notice bodies that live in the Notion **page block tree** (not the `내용` rich_text
  property) displayed as "등록된 본문이 없습니다" — `mapPage` only read `properties['내용'].rich_text`,
  so a page whose property is empty but whose body has 8 blocks (heading/list/bold/table — the
  `공지 본문 표시 테스트` row) rendered empty. Confirmed against the live Notion API before coding.
- **Backend**: `AdminNoticesService` now converts each published page's block children to Markdown
  with **notion-to-md** (v3.1.9) and serves it as a new `AdminNotice.body` field (`content` stays
  the property-based preview/fallback). notion-to-md only calls `blocks.children.list`, so it is
  wired to a 15-line adapter over the shared axios instance — block requests reuse auth, timeout,
  the 340ms pacing slot and the 429 backoff. Failure degrades per notice: **429 rethrows** (shared
  backoff pauses all Notion traffic), any other error logs a warning and leaves `body` empty.
  Bounds: `NOTION_BODY_MAX_BLOCK_PAGES = 2` (200 blocks/page) and
  `NOTION_BODY_FETCH_MAX_NOTICES = 50` per refresh (both documented in the constants file).
  `parseChildPages: false` + `convertImagesToBase64: false` (no extra fetches, no node-fetch).
  `@notionhq/client` is NOT installed — its type import inside notion-to-md's d.ts is skipped by
  `skipLibCheck: true`; the adapter object is passed directly.
- **Frontend**: detail page (`/announcements/[id]`) lexes `notice.body` server-side with **marked**
  v18 (`[...marked.lexer(md)]` — the spread strips TokensList's extra `links` property for devalue)
  and renders tokens through `src/lib/components/MarkdownBody.svelte` — a recursive token renderer
  with **zero `{@html}`**: Svelte escapes every text node, `javascript:`/`data:` hrefs render as
  plain text, raw HTML tokens show as literal text. It has **no root wrapper** (a `<div>` inside
  `<p>` recursion is invalid SSR nesting — host provides `.lc-md`); Tailwind preflight strips list
  markers, so `list-style: disc/decimal` must be restored (found only by screenshotting the page).
  Headings shift +1 (`#`→`h2`) because the notice title owns `h1`.
- **Fallback chain** on the detail page: markdown body → property `content` (whitespace-pre-line,
  testid `admin-notice-content` unchanged) → "등록된 본문이 없습니다." List preview keeps using
  `content` only (never raw markdown).
- **Verification**: backend **882/882** (+3 specs: block→md conversion, non-429 failure fallback,
  429 backoff from block fetch; existing specs gained `mockGet` + `body: ''`), lint/tsc/build green;
  live integration against real Notion returned `body: "# 마크다운 테스트\n\n- asdf…"` for the test
  row and `body: ""` + property content for the other published row. Frontend lint/check (0/0),
  build green; **254 passed / 0 failed** full mock e2e (+1 new: h3/strong/ul/table/blockquote, no
  `##`/`| --- |` leaks); screenshots of `/announcements/mock-announcement-2` verified light + dark.
  New deps: backend `notion-to-md`, frontend `marked` (lockfiles updated — include in the release
  commit).

## Release Notes (when this ships)

- Submodule versions (`backend/package.json`, `frontend/package.json`) must be bumped per AGENTS.md
  before the release PR; production needs `NOTION_API_KEY`/`NOTION_DATABASE_ID` in `backend/.env`
  or the endpoint simply returns an empty list
