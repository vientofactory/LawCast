# Frontend Design System Guide

Single source of truth for LawCast frontend (`frontend/`) visual and structural
conventions. Read this before adding or restyling any route or component so the
new UI matches the existing pages instead of inventing a parallel dialect.

Companion notes: `repo/frontend-notes.md` (runes/e2e pitfalls),
`01-project-exploration-and-discussion-plan/lawcast-frontend-exploration.md`
(architecture), `15-citizen-ux-feedback/citizen-ux-feedback.md` (UX gaps),
`repo/code-comment-convention-notes.md` (comment/`lc-` rules).

## 1. Page Skeleton

Every route renders the same shell:

```svelte
<SeoHead title description url keywords />
<div class="lc-page-shell">
  <Header />
  <main id="main-content" class="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
    ...
  </main>
</div>
<!-- Footer is rendered by routes/+layout.svelte, not by routes -->
```

Rules:

- `main` MUST carry `id="main-content"` — the layout's skip link
  (`routes/+layout.svelte`) targets it, and responsive contracts assert
  `main h1` is visible on every page
  (`frontend/e2e/helpers/responsive-contracts.ts`).
- Width: `max-w-5xl` for simple list/read pages (`discussions`, `announcements`,
  `license`), `max-w-7xl` for rich dashboard pages (`notices`, `proposals`,
  `status`, `crawling-transparency`, `webhook`, home).
- `Header` is per-route (not in the layout); `Footer` comes from the layout.
  Do not render a second footer.
- NProgress navigation feedback and the Cloudflare challenge reloader live in
  the layout — never re-implement them per route.

## 2. Hero Header

Rich pages open with a hero card; simple lists may use the same card (see
`routes/discussions/+page.svelte`, unified 2026-10-16). Canonical shape
(`routes/proposals/+page.svelte`, `routes/status/+page.svelte`,
`routes/crawling-transparency/+page.svelte`):

```svelte
<div class="lc-panel-hero mb-6 rounded-2xl border p-5">
  <div class="flex flex-wrap items-start justify-between gap-3">
    <div>
      <p class="lc-text-info text-xs font-semibold tracking-wide">DISCUSSIONS</p>
      <h1 class="lc-text-primary mt-1 text-xl font-bold sm:text-2xl">토론 모아보기</h1>
      <p class="lc-text-secondary mt-1 text-sm">One-line page description.</p>
    </div>
    <span class="lc-chip-blue inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold">
      전체 {total.toLocaleString('ko-KR')}건
    </span>
  </div>
</div>
```

Rules:

- Eyebrow is an uppercase English section label (`lc-text-info ... tracking-wide`).
- Exactly one visible `h1` per page; responsive contracts cap it at 2 lines.
- Put the key count/summary chip on the right (`lc-chip-*`, FontAwesome icon +
  `toLocaleString('ko-KR')`), not in the description paragraph.
- `routes/notices/+page.svelte` is the deliberate exception: it keeps an `sr-only`
  `h1` because the filter card is the visual head. Do not copy that exception to
  new pages without a reason.

## 3. Filter Panel and Chip Groups

Filters live in a card, options in a pill group. Canonical shape
(`routes/notices/+page.svelte`, `routes/discussions/+page.svelte`):

```svelte
<section class="lc-panel-card mb-5 rounded-xl border p-4 shadow-sm" aria-label="...">
  <div
    class="lc-chip-group inline-flex items-center rounded-full border p-0.5 text-xs font-semibold"
    role="group" aria-label="..."
  >
    <a
      href={...}
      class={`rounded-full px-3 py-1 transition-colors ${
        isActive ? 'lc-button-primary border-transparent shadow-sm' : 'lc-text-muted hover:text-[var(--lc-text-secondary)]'
      }`}
    >전체</a>
    ...
  </div>
</section>
```

Rules:

- Segmented options MUST use `lc-chip-group` + inner `rounded-full px-3 py-1`
  links/buttons. Never style filter tabs as standalone bordered pills
  (`rounded-full border px-3 py-1.5` outside a group) — that was the pre-unification
  `discussions` look and it is retired.
- Active option: filled (`lc-button-primary` / `lc-chip-*` + `shadow-sm`);
  inactive: `lc-text-muted` with hover to `lc-text-secondary`. Keep the
  `transition-colors` class.
- `discussions` keeps `role="tablist"`/`role="tab"` + `aria-selected` (e2e asserts
  it); `notices` uses `role="group"`. When adding a tablist, follow `discussions`
  and assert `aria-selected` in e2e — asserting only the URL misses stale-state
  regressions (see `repo/frontend-notes.md`).
- Filter chips must stay single-line: responsive contracts enforce `maxLines: 1`
  on every filter control. Test at 360px width.
- Form controls: `lc-input lc-input-focus ... shadow-sm`, icon inside input with
  `pointer-events-none absolute`, `disabled:opacity-50 disabled:cursor-not-allowed`.
  Submit buttons show a spinner state (`faSpinner animate-spin` + `불러오는 중`).

## 4. Results Region and List Rows

Wrap results in a labelled region (`routes/notices/+page.svelte`,
`routes/discussions/+page.svelte`):

```svelte
<section class="relative" aria-labelledby="discussions-results-heading" data-testid="discussions-page-region">
  <h2 id="discussions-results-heading" class="sr-only">토론 스레드 목록</h2>
  ...
</section>
```

Row lists (`discussions`, `announcements`) share one pattern — keep them identical:

- Container: `lc-panel-card divide-y divide-[var(--lc-border-soft)] overflow-hidden
  rounded-xl border border-[var(--lc-border-soft)] bg-[var(--lc-surface-primary)] shadow-sm`.
- Row: `group flex ... p-4 ... transition-colors hover:bg-[var(--lc-surface-hover)]`,
  whole row is one link (`text-inherit no-underline`).
- Title: `lc-text-primary truncate text-sm font-semibold group-hover:text-blue-600`.
- Trailing chevron: `lc-text-dim hidden h-3 w-3 transition-transform
  group-hover:translate-x-0.5 sm:inline-block`.
- Status chips inline before the title: `lc-chip-success` + `lc-dot-success` for
  open/in-progress, `lc-chip-muted` + lock icon for closed.
- Meta line: `lc-text-muted ... text-xs` with `h-2.5 w-2.5` icons; counts in a
  `lc-chip-blue rounded-full px-2.5 py-1 text-xs` pill with `title` tooltip.
- Timestamps via `formatDateTimeKST` / `formatDateOnlyKST`
  (`frontend/src/lib/utils/helpers.ts`).

## 5. Empty and Loading States

- Simple empty state: `lc-panel-card rounded-xl border border-dashed
  border-[var(--lc-border-soft)] p-8 text-center shadow-sm` with a semibold
  `lc-text-primary text-sm` line + a `lc-text-muted text-xs` hint line. Keep the
  existing `data-testid` (`discussions-empty-state`, `admin-notices-empty-state`).
- Illustrative state (loading/empty with iconography): `lc-empty-state
  rounded-2xl border p-16 text-center shadow-xl` with `lc-empty-state-icon
  rounded-full p-6` (`routes/notices/semantic-search/+page.svelte`).
- Inline form progress: `lc-loading-track` + `lc-loading-fill lc-loading-slide`
  (see `notices/+page.svelte`). Do not invent new loader visuals — reuse
  `LoadingOverlay`, `LoadingSpinner`, or `WandSparkleLoader`.

## 6. Pagination

Render `PaginationNav` directly — never wrap it in a spacing `div`. The component
owns `mt-12` on its `nav` plus the page-count badge
(`frontend/src/lib/components/PaginationNav.svelte`). Always pass `ariaLabel`
and `testId`. Contract: it renders only when `totalPages > 1 && totalItems > limit`.

## 7. Overlays (Blocking Contracts)

Overlays MUST block interaction with what they cover. Established 2026-10-16
after `LoadingOverlay` shipped `pointer-events-none` on both layers and clicks
leaked through during loads:

- `LoadingOverlay` (`lib/components/LoadingOverlay.svelte`): absolute dim layer
  covers the section, `fixed inset-0 z-50` spinner layer (`role="status"`,
  `aria-live="polite"`) covers the viewport. Neither layer may carry
  `pointer-events-none`. Reuse it instead of hand-rolling inline spinners.
- `RateLimitOverlay` / `SemanticSearchUnavailableOverlay`: `absolute inset-0`
  over the nearest `relative` section; parent blocks by default — do not add
  `pointer-events-none`. `RateLimitOverlay` needs a live `retryAfter` ticking
  through `RetryCountdown`, otherwise the retry button stays disabled forever
  (see `repo/frontend-notes.md`). Disable or `inert` the covered controls while
  an overlay is visible, and add `disabled={isLoading}` to every control the
  overlay does not cover (the `proposals` chart-type buttons gap, fixed 2026-10-16).
- `ModalShell` (`lib/components/ModalShell.svelte`): `fixed inset-0 z-[1200]`,
  backdrop click + Escape close, `closeDisabled` during submission,
  `fade`/`scale` transitions. All modals go through it. Never name a `$state`
  variable `title` in a consumer — it shadows the `{#snippet title()}` slot and
  breaks `bind:value` (see `04-snippet-state-shadowing-bug/`).
- Mobile menu (`Header.svelte`): `fixed inset-0 z-1100` with backdrop button +
  `use:trapFocus` panel. Keep this z-order: loading `z-50` < header menu `1100` <
  modal `1200` < skip link `9999`.

## 8. Banners, Alerts, Chips, Buttons

- Banners: `lc-banner-{muted,warning,info,success,error-soft} ... rounded-xl border
  p-3/p-4` with a leading FontAwesome icon (`faCircleInfo`, `faTriangleExclamation`).
  One-off dismissible alerts go through `Alert.svelte`
  (`type: error|success|warning|info`, `role="alert"`, auto-hide only for success).
- Chips: `lc-chip-{blue,cyan,muted,success,warning,danger,purple,teal,info}` as
  `inline-flex items-center rounded-full` pills (`text-[11px]`/`text-xs`,
  `font-semibold`); status dots via `lc-dot-success` / `lc-dot-warning`.
- Buttons: `lc-button-primary` (filled action), `lc-button-neutral` (bordered),
  `lc-button-secondary`. Always `cursor-pointer` and
  `disabled:cursor-not-allowed disabled:opacity-50` (or `opacity-60` for primary).
  Icon sizes step with context: `h-2.5 w-2.5` meta, `h-3 w-3` / `h-3.5 w-3.5`
  controls, `h-4 w-4` hero/empty icons.
- Text colors: `lc-text-primary` (headings/values) > `lc-text-secondary` (body) >
  `lc-text-muted` (meta) > `lc-text-dim` (decorative). Accent links: `lc-link`,
  info labels: `lc-text-info`, danger: `lc-text-danger`.

## 9. Global CSS Gotchas (`frontend/src/app.css`)

**CRITICAL** — the top of `app.css` flattens entire Tailwind categories:

- `rounded-*` ALWAYS renders `0.5rem` (`[class*='rounded'] { border-radius:
  0.5rem !important; }`, `app.css:140-143`). Size variants (`rounded-xl` vs
  `rounded-2xl`) are documentation only, except components with their own
  `!important` radius declared LATER in the file (`lc-panel-hero` 1.25rem,
  `lc-loading-shell` 1rem). Pick radius classes for intent, never for pixels.
- Tailwind `shadow-*`, `backdrop-blur-*`, and `focus:ring-*` are STRIPPED
  (`box-shadow: none !important; backdrop-filter: none !important;`,
  `app.css:145-153`). Depth comes only from `lc-panel-*` borders and
  `var(--lc-shadow-soft)`. Do not add `shadow-md`/`backdrop-blur-sm` expecting an
  effect — keep them only where they already exist for documentation parity.
- Every custom surface needs a dark variant: `html[data-theme='dark']` overrides
  exist for all `lc-panel-*`, `lc-chip-*`, `lc-banner-*`, overlays, and inputs.
  New `lc-*` classes without a dark override render broken in dark mode.
- Motion: panel transitions are `180ms ease`; interactive lifts use
  `transition-all duration-200` + `hover:-translate-y-0.5`. Decorative animation
  must respect `prefers-reduced-motion` (global kill-switch at `app.css:1648`,
  loader-specific at `app.css:1621`, guarded by
  `e2e/semantic-search-loading.spec.ts`).
- Font stack starts with Pretendard (`app.css:155`); tabular numbers for counts
  (`tabular-nums` / `font-variant-numeric`).
- 44px touch targets (`style="min-height:44px"` on mobile nav links).

## 10. New-Page Checklist

1. `SeoHead` with `title` (page text WITHOUT ` - LawCast` — the component appends
   it), `description`, canonical `url`, `keywords`. Exactly one `<title>` per
   page; page-specific extras (JSON-LD, `robots noindex`) stay in the route's own
   `<svelte:head>` (see `repo/frontend-notes.md`). Canonical for filtered views
   stays on the clean route.
2. Visible `h1` in a hero card (§2); `aria-labelledby` + `data-testid` on primary
   regions and interactive elements.
3. Filters in a `lc-panel-card` + `lc-chip-group` (§3); filter/pagination state in
   the URL so views are shareable (`buildFilterLink`/`buildPageLink` with
   `SvelteURLSearchParams`, `goto` + `afterNavigate` reset of `pendingPage`).
4. `RateLimitOverlay` wired to `RetryCountdown` + `loadError` with the
   `opacity-60` dim wrapper (§7).
5. Register the route in `frontend/e2e/helpers/responsive-contracts.ts` (visible
   selectors + `maxLines` clamps) — CI checks 5 viewports for overflow.
6. Runes discipline: URL-derived state as `let currentUrl = $state(page.url)`,
   `$derived` (never `$:`), `$state.raw` for identity-compared payloads, inline
   `data` prop type extended with every new loader field, `DIFFCHAIN_UI_MOCK=1`
   branch for every new browser-issued API read (see `repo/frontend-notes.md`).
7. Verify: `cd frontend && npm run lint && npm run check`,
   `python3 tools/check-comment-language.py` from the root, and the route's e2e
   on a dedicated mock port (never reuse the 5173 dev server).
