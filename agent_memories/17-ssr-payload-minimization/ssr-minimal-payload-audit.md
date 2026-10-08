# SSR Minimal Payload Audit & Refactor (2026-10-08)

Goal: for **every** SvelteKit route, compare what `load()` serializes against what the page
(and its components/helpers) actually renders, then trim the loaders to the minimum in one
consistent direction — full API types stay in the client layer, routes embed **card views**.

## Method

1. Inventory: 15 server loaders (`+layout.server.ts` + 14 `+page.server.ts`).
2. Per route, enumerate consumers: `data.<key>` refs, local `data:` annotations, prop threading
   into components, and **helper functions inside components** (template greps alone miss these).
3. Measure every route's SSR HTML + per-key serialized bytes (devalue spans, brace-matched).
4. Trim only where loaded ⊋ used with meaningful bytes; document routes that are already minimal.

## Loaded-vs-used verdict (per route)

| Route | Loaded keys | Actually used | Action |
| --- | --- | --- | --- |
| layout (global) | versions, `urgentNotice` | Footer (versions), Header banner (id/title) | notice → `AdminNoticeCard` (id/title) |
| `/` home | stats, quickKeywords, recentNotices, recentDiscussions, pinnedNotice | 4 stats sections, keyword+updatedAt+sourceNoticeCount, 8 row fields, 8 row fields, id/title | all sliced (`toHomeStats`, `toHomeQuickKeywords`, cards) |
| `/status` | `stats`, fetchedAt, loadError | webhooks, webPush, cache, archive, crawlers, ollama (+fetchedAt/loadError); NOT changeTracking/nodeRuntime/aiSummaryEnabled | `pickStatusStats()` drops the 3 unused sections |
| `/discussions` | threads(items+meta), status, loadError | 9 item fields, meta, status, loadError | items → `DiscussionThreadCard` |
| `/notices` | archive(items+meta+stats), digestContext, loadError | 12 item fields; meta; stats.totalArchiveCount/archiveCount only | items → `NoticeCard` |
| `/notices/changes` | changes(items+meta), summary, filters, digestContext | 8 item fields (NO hashes/diffSummary/details), meta, filters(5), digest(5) | items → `NoticeChangeCard`, meta explicitly picked |
| `/notices/[num]`, thread detail, `/announcements/*` | detail/changes/discussions/integrity/http/tokens | every top-level key referenced | no change (already minimal at key level) |
| `/proposals`, `/crawling-transparency`, `/notices/semantic-search`, `/license` | statistics / transparency / search / package lists | all rendered (license loader already maps to name/version/license/note) | no change |
| `cf-challenge-test` | `{}` | — | no change |

## New contract: card views

- `frontend/src/lib/types/api.ts`: `AdminNoticeCard`, `NoticeCard`, `DiscussionThreadCard`,
  `NoticeChangeCard(+ListResponse)`, `DiscussionThreadCardListResponse`,
  `ArchiveNoticeCardListResponse`. Full API response types untouched (client layer, sitemap,
  detail timeline keep them).
- `frontend/src/lib/server/ssr-cards.ts`: shared mappers `toAdminNoticeCard`, `toNoticeCard`,
  `toDiscussionThreadCard`, `toNoticeChangeCard` — the single place the field lists live.
- Backend `GET /api/announcements/top` now returns the cap-1 view `{item: {id, title} | null}`
  (content/body never leave the endpoint); controller spec asserts the slim shape with a
  content/body-bearing fixture.
- Route `data:` annotations that named full responses (notices/discussions/changes pages) were
  switched to the card responses in the same commit — loaders and annotations must move together.

## Measurements (mock fixtures, dev server)

| Page | before → after (this pass) | Key deltas |
| --- | --- | --- |
| `/` | 185,032 → 179,680 B (−5,352) | stats 4,318→**128**, quickKeywords 320→179, recentNotices 2,348→1,909, recentDiscussions 277→225, pinned+urgent 336→**73** each |
| `/notices/changes` | 175,930 → 171,543 B (−4,387) | changes 6,142→**2,018** (hashes/details gone) |
| `/notices` | 264,620 → 262,601 B (−2,019) | archive 8,941→7,185 |
| all other routes | −261…−319 B each | urgentNotice card trim benefits **every** page |
| `/status` | 165,575 → 165,305 B | stats unchanged in mock (mock lacks the 3 dropped sections); pick matters for real payloads |

Prior pass (notice list out of global SSR) is documented in
`agent_memories/16-notion-admin-notices/plan.md`.

## Pitfalls

- **CRITICAL**: grepping templates for `notice.field` misses field access inside component
  helper functions (`isSourceDeleted(notice)` reads `lifecycleStatus`); grep `function` bodies too.
- Pages with local `data: { ... }` prop annotations (notices, discussions, changes) do NOT use
  generated `PageData` — update them or svelte-check fails on the trimmed shapes.
- Two different stats slices by design: home needs 4 sections, /status needs 6 — keep the slices
  next to their loaders (`toHomeStats` in `routes/+page.server.ts`, `pickStatusStats` in
  `routes/status/+page.server.ts`), not in a shared helper.
- `pickStatusStats` returns an object missing only *optional* `SystemStats` fields, so the
  status page's `as SystemStats` cast stays legal.
- Known residue (documented, not trimmed): `/notices` `archive.stats` unused subkeys
  (~70 B; required by the response type) and detail-page subfield-level trim (top-level keys all
  used; item-level cut deferred).

## Verification (2026-10-08)

- Backend: lint / `tsc --noEmit` / `nest build` green, **885/885 specs** (26 admin-notices,
  top-route specs assert id/title-only with a content-bearing fixture).
- Frontend: `npm run lint` green, `svelte-check` **0/0 twice** (before and after prettier pass).
- E2E: full mock suite **255 passed / 45 skipped / 0 failed** with
  `--config playwright-configs/playwright.config.ts` (chip, banner, list, detail, payload guard).
- Live backend (real Notion): `GET /api/announcements/top` → 200 `{item:{id,title}}`,
  `?urgent=true` → 200 `{item:null}`; server stopped after the check.
- **Real-mode integration (12/12 PASS)**: built backend on 3001 + `DIFFCHAIN_UI_MOCK=0` dev
  server on 5195 — all six routes (/, /status, /discussions, /notices, /notices/changes,
  /announcements) returned 200 with the real Notion rows, proving the `.then(mapper)` real-API
  branch of every trimmed loader; absence checks held (`webhooks:{` gone from home,
  `changeTracking:`/`nodeRuntime` gone from status, `isLocked`/`contentId`/`eventHash` gone from
  their lists) while `/announcements` still shipped the full list. Servers stopped afterwards.
- Changes left uncommitted (no commit/release requested).
