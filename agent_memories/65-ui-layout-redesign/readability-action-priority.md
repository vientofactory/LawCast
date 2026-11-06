# Readability and list action priority

## Current brand animation contract

The owner explicitly requested restoring the original git animation after the readability review. The earlier always-opaque tagline override below is superseded: `c82ae63` delays the caption1700ms, then fades/translates it over450ms. `Header.svelte` now restores that exact block; `BrandLogo.svelte` remains byte-identical to the commit. Accessibility regressions wait for the completed heading animation rather than changing intentional animation frames to satisfy a settled-state contrast audit. Reduced-motion visibility remains immediate. Evidence: /Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/restore-brand-animation/VERIFICATION.txt

## Changes

- `frontend/src/lib/components/Header.svelte`: keep the tagline opaque during its existing translation animation. The prior fade reproduced a normal-motion 320px contrast failure. The symbol/wordmark assembly animation is unchanged. Measured stable foreground/background ratios are 7.71:1 light and 9.66:1 dark; five intro samples per theme/motion combination retain opacity 1.
- `frontend/src/lib/styles/layout.css`: supporting text utilities inside the main region have a 14px/rem-based floor. Specific results-note, reset-control, home metadata, signal label and diff-hunk rules also use that floor. Headings retain their existing distinct roles.
- `frontend/src/lib/components/Footer.svelte`: version metadata now uses 14px supporting type.
- `frontend/src/routes/proposals/+page.svelte`: chart axis and tooltip fonts increase from 11px/default sizes to 14px; automatic tick skipping remains enabled. The accessible data table remains available.
- `frontend/src/routes/notices/+page.svelte`: the title link is the primary reading destination; the redundant same-destination action was removed in a follow-up; PDF, HWP and the external parliamentary source are neutral secondary actions with visible labels. Accessible names include visible text. Touch heights remain 44px and actions wrap.
- `frontend/src/lib/components/RecentNotices.svelte`: preserve 18px full-width mobile titles; place secondary actions on a separate mobile row, without colored icon boxes.

## Completed verification

Evidence directory:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/readability-actions/`

- `report.html` contains before/after browser screenshots, focus captures and exact verification commands/results.
- Final Chromium open-layout suite: 78 passed, no retries/skips/flaky cases.
- Three-engine readability and hierarchy suites: 36 passed.
- Firefox/WebKit full-page accessibility matrix: 16 passed. Combined with Chromium, this checks 15 route/states at 320/390/820/1440px in light/dark: 360 route/viewport/theme/engine scans, with no violations or horizontal overflow.
- Separate screenshot audit: 68 cases, zero overflow, 64 automated WCAG scans with zero violations.
- Lint, Svelte check (zero errors/warnings), agent guidelines, Cloudflare build and Node build passed.
- Original 264 source hashes preserved. Archive/patch replay agree with all 265 modified source hashes. Independent rollback restores the original hashes and behavior; active source remains modified.

## Regression corrections and limits

- The old first-result y <= 450 assertion was invalid even before this task (557.34px in the baseline). Its replacement asserts the complete first title remains in the initial 844px viewport rather than shrinking readable text to satisfy an obsolete coordinate.
- Mobile comparison mode intentionally hides the record list. The nested-disclosure regression now selects the record-list tab before interacting with a nested record; it does not skip nested interaction.
- Firefox serializes a 44px target rectangle as 43.9998779px in some viewport cases. The test asserts CSS min-height exactly 44px and uses a 0.01px rectangle tolerance.
- WebKit keyboard tests use native Option-Tab for all-control traversal, not a custom application key trap.
- Native headless WebKit push initialization stalls, as previously recorded in [the initial audit](responsive-accessibility-audit.md). A service-worker-blocked 320px/light control passes. Full WebKit UI coverage reuses the existing `a11y-fixes.spec.ts` unsupported-PushManager fixture; the native failures remain in `logs/native-webkit-push-stall.log`. **Native Safari/iOS push delivery and permission behavior are not certified by these UI tests.**
- Automated accessibility scans and scripted keyboard checks are not a replacement for an actual screen-reader/user study.


## Duplicate entry follow-up

The owner requested removing the redundant reading CTA. `notice-open-summary` and its unused primary-action CSS were removed; title-link navigation and file/source actions remain. Updated three-engine readability tests pass all 24 cases. Evidence: /Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/remove-duplicate-summary/VERIFICATION.txt

## Notice row theme and gutter follow-up (2026-11-04)

- The notice-list row reset in `frontend/src/lib/styles/layout.css` had lower specificity than `html[data-theme='dark'] .lc-notice-card` and its ended variant in `frontend/src/app.css`. Dark mode therefore restored card fills and soft separator colors while light mode kept transparent rows and strong separators.
- The scoped `.lc-main .lc-result-list > .lc-notice-card.lc-result-row` selector now keeps both lifecycle states transparent with the same separator token in both themes. AI summaries alone retain the muted inset surface. Other notice cards outside the archive list are unchanged.
- Rows keep 24px block padding and receive 16px inline padding below 640px, 24px at wider widths. The page gutter remains unchanged; title, metadata, summary and secondary actions all share the row's inner inset.
- The existing neutral-surface regression in `frontend/e2e/open-layout.spec.ts` now checks transparent ongoing/ended rows, separator colors, summary surfaces, actual child insets and horizontal overflow instead of requiring zero horizontal padding. Evidence: `/private/tmp/lawcast-notice-spacing/VERIFICATION.txt`.
- Native 320px verification caught an additional 8px document overflow after adding gutters: deferred grid items retained an intrinsic minimum width. An explicit `minmax(0, 1fr)` results track and `min-width: 0` rows keep skipped content within the viewport; the geometry assertion runs before an axe scan expands deferred content.

### Superseding horizontal-padding correction (2026-11-04)

The owner subsequently requested removing the added row gutters. Archive rows now retain the page reading axis with `padding: 1.5rem 0` at every breakpoint; the page gutter and AI-summary internal padding remain unchanged. Transparent ongoing/ended row backgrounds stay consistent across themes. Repeated item separators and the summary's left rule now use `--lc-border-soft`, leaving the section's 2px `--lc-border-strong` boundary dominant and the muted summary fill subordinate to the title. Zero-minimum grid sizing remains in place. Updated regressions assert zero child insets, soft separator tokens, no horizontal overflow, and axe accessibility. Follow-up evidence: `/private/tmp/lawcast-notice-hierarchy/VERIFICATION.txt`.

### Loading backdrop palette follow-up (2026-11-04)

The attached screen recording showed a blue-black rectangle during archive search navigation even though settled results already used neutral surfaces. The shared `.lc-loading-overlay` still had a hardcoded dark `rgba(2, 6, 23, 0.48)` background and a forced 16px radius. It now derives a 55%-opacity veil from `--lc-body-bg` in both themes and inherits its host region's radius. The existing blur and loading animation remain unchanged; the results region stays square and retains the corrected row hierarchy during requests. Delayed SvelteKit data-response regressions cover keyword/spinner and semantic/signal loading at 390px and 1440px in both themes, including overlay removal and zero row gutters after completion. Evidence: `/private/tmp/lawcast-loading/VERIFICATION.txt`.

### Cross-page loading consistency (2026-11-04)

- Inventory covered archive/changes/proposals shared overlays, dedicated semantic search, home progress, discussion thread/comment skeletons, revision-history placeholders, notice screenshot spinner, engine status and webhook/push/PoW busy states. Existing skeletons, progress tracks and inline busy indicators already use neutral surface/text tokens and remain unchanged.
- Dedicated semantic search still used the old rounded, filled empty-state card while loading. It now renders an open inline loading region with soft horizontal boundaries, transparent fill and the existing signal animation.
- `--lc-loading-backdrop` centralizes the existing page-color 55% veil. Shared loading and rate-limit/retry overlays both use it. Rate-limit cards no longer override dark surfaces with blue-black literals or heavy shadows; cards, icons, countdown, button borders and typography follow current semantic tokens and 44px retry targets.
- Light-mode shared spinner colors were still hardcoded blue; spinner rings now use `--lc-border-soft` and `--lc-text-accent` in both themes. Changes and proposals use the corrected shared component without route-specific patches.
- The open-layout suite adds delayed-navigation checks on semantic search, changes and proposals, plus no-JavaScript discussion-skeleton palette/reduced-motion checks. The isolated rate-limit suite checks retry surfaces in both themes at 390/1440px; it keeps mock mode disabled to avoid bypassing the forced-429 hook. Evidence: `/private/tmp/lawcast-loading-pages/VERIFICATION.txt`.

### Semantic result light-theme hierarchy (2026-11-04)

The dedicated semantic-search result cards used `--lc-surface-primary`, which is white like the light page background but visibly raised in dark mode. This left a floating left rule and links in light mode instead of a coherent result surface. A route-specific `lc-semantic-result` class now uses `--lc-semantic-result-bg` (muted in light, the existing primary surface in dark); neutral metadata chips use a white surface in light and retain their existing muted dark surface. Similarity status colors, title/CTA links, left rule, spacing and dark-theme appearance remain unchanged. The archive list's transparent rows and zero inline gutters are separate and unchanged. Tests pin colors, overflow, links, existing card spacing, axe contrast and fallback/weak results. Evidence: `/private/tmp/lawcast-semantic-light/VERIFICATION.txt`.

### Cross-page light content surfaces (2026-11-04)

The white-on-white surface issue also affected proposal summary cards, change-event cards, discussion/announcement list groups, weak semantic-board results and active discussion comments. These now explicitly opt into `lc-content-card`: a muted light surface and white neutral metadata chips, with the exact previous primary-card/muted-chip colors in dark mode. Discussion initial and load-more comment skeletons opt into the same surface as their loaded comments.

Do not change `--lc-surface-primary` or `.lc-panel-card` globally to achieve this: popovers, form controls and modal shells need their own surface role. Plain reading content, charts, status/service sections and the archive list remain intentionally open; archive rows retain zero inline gutters. Warning-highlighted changes (`lc-banner-warning`) are excluded from the content override, deleted comments do not opt in, and system/admin comment border semantics remain untouched. Cross-page regressions cover affected surfaces, metadata, no overflow and axe checks in light/dark at 390/1440px, plus unchanged open archive/detail regions. Existing semantic-card and discussion-skeleton tests are retained. Evidence: `/private/tmp/lawcast-light-cards/VERIFICATION.txt`.

### Live palette transitions and list feedback (2026-11-04)

- Settled-theme assertions do not cover color interpolation. `syncTheme` now marks an actual palette change with `data-theme-changing` for two animation frames. While marked, CSS permits transform/opacity transitions but snaps foreground/background/border colors together; keyframe animations are not disabled. Rapid changes cancel the previous cleanup frame and schedule cleanup for the newest palette.
- Announcements and discussion list rows share `lc-card-list-link` hover/focus treatment: theme accent titles and theme hover surfaces. The former announcement-only fixed-blue hover utility was replaced; keyboard focus uses the same treatment, with a -3px inset outline so `overflow-hidden` list wrappers cannot clip the ring.
- `e2e/helpers/theme-palette.ts` samples computed foreground and alpha-composited ancestor backgrounds on animation frames plus the theme mutation, using canvas color conversion to handle modern CSS color syntax. Tests retain hover/focus while invoking the actual switch handler, rather than moving the pointer away to click it. Busy overlays similarly retain their blocking behavior while their switch handler is invoked programmatically for theme-update coverage.
- Evidence and baseline/modified/rollback commands: `/private/tmp/lawcast-theme-states/VERIFICATION.txt`.
- Completed Chromium checks: 12 primary regression cases passed; an additional screenshot rerun and isolated negative control passed. The negative control restores only the neutral button's previous color interpolation and reproduces 1.12:1 mid-swap contrast; guarded samples stay at or above 4.67:1. This is computed-style frame sampling, not native-device pixel/screen-reader certification. The final inset focus ring was visually checked on announcements in light/dark states. Theme-control transform motion and keyframe animations remain enabled.

### Cross-engine and touch theme checks (2026-11-04)

A dedicated `playwright.theme-states.config.ts` reuses the immutable production Node server with Firefox/WebKit desktop projects and separate coarse-pointer touch projects. Cross-page cards and retained hover/keyboard-focus tests run at 390/1440px; real `tap()` flows open the mobile menu, change themes in both directions and focus the search input with normal/reduced motion. Engine versions and touch capabilities are recorded in annotations; captures are separated by project.

The first matrix found test-fixture problems rather than palette defects: WebKit PWA service-worker requests bypassed a browser route hold, and both touch engines reported zero `maxTouchPoints` despite coarse-pointer media. The controlled suite now blocks service workers and verifies trusted `touchstart` events. The focused 16-case rerun passed. Product CSS and `theme.ts` remain byte-identical to the preceding task: no unsupported browser-specific palette workaround was introduced. This covers Playwright WebKit (Safari engine) and Firefox plus touch/device emulation, not physical Safari/iOS or Android devices. Full commands and final results: `/private/tmp/lawcast-cross-engine/VERIFICATION.txt`.
- Final isolated matrix: **48 passed**, zero failures/retries/skips, Firefox 153.0 and WebKit 26.5. Each desktop engine and each touch-emulated project passed 12 cases. Frame samples remain >=4.5:1; see per-project sample counts/minima in `sample-summary.json`. The existing product palette and theme-switch implementation were preserved byte-for-byte; changes in this follow-up are limited to regression tooling and documentation.

### Archive screenshot preview modal (2026-11-04)

The archive screenshot now opens in `NoticeScreenshotModal`, composed from the existing `ModalShell` and `NoticeScreenshot` components. The route mounts it outside the deferred archive disclosure/reading column so viewport positioning is not clipped or contained by deferred content. Screenshots remain lazy until the modal opens, with existing loading, error/retry and download behavior.

`ModalShell` adds optional `returnFocus` and `stickyHeader` props without changing defaults for existing callers. Screenshot invokers provide an explicit return target (Safari pointer clicks need not focus their button), and the close header stays visible while the long image scrolls. Screenshot deep links open archive metadata before opening the modal; closing removes only the screenshot flag through shallow replacement and retains the reading position. The modal preserves Escape/backdrop dismissal, focus containment, background inertness, body scroll lock and outro focus restoration.

The screenshot regression fixture PNG had invalid decoding behavior in Firefox; it was replaced with a valid RGBA PNG. Background isolation assertions check inert ancestors, not only a direct `main[inert]` attribute. Dedicated Chromium/Firefox/WebKit coverage at 320/390/1440px in both themes passes 39 cases including image failures/retry, lazy loading, reopen, deep links, focus loop/return, sticky close header, bounded dialog scrolling, downloads and axe. Evidence: `/private/tmp/lawcast-screenshot-modal/VERIFICATION.txt`.

### Screenshot zoom and bounded mobile viewport (2026-11-04)

`NoticeScreenshotModal` now keeps header/toolbar fixed in a bounded flex shell and scrolls only a named, keyboard-focusable image viewport. Controls support fit width (without upscaling), intrinsic 100% size and manual 10–400% zoom; the reading center is preserved across zoom changes. Fit mode tracks viewport width on rotation/resizing. Mouse pointer capture supports drag-to-pan; touch keeps native pan/pinch behavior via `touch-action: pan-x pan-y pinch-zoom` rather than overriding browser gestures. Keyboard shortcuts are scoped to the viewport and do not intercept Ctrl/Meta browser zoom.

`NoticeScreenshot` adds optional dimension callbacks, explicit image width and a frameless mode; default callers retain the old layout. Zoom controls stay disabled until image dimensions load. Reopening starts at fit width. ModalShell/focus/isolation/download/retry behavior remains reused. Explicit pixel width uses content-box sizing so 100% equals the intrinsic image width; fit calculations include padding and border pixels to prevent horizontal overflow.

The screenshot suite now includes zoom/original/fit state, keyboard bounds, drag pan, fixed controls while scrolling, fit on reopen, and a WebKit touch/landscape project. Touch taps and scroll geometry are automated; physical inertia/pinch gestures are not certified. Evidence: `/private/tmp/lawcast-screenshot-zoom/VERIFICATION.txt`.
- Final zoom suite: 44 passed across Chromium, Firefox, WebKit and a WebKit touch/landscape project. Manual zoom limits, 100% intrinsic width, fit-on-rotation, native scroll geometry, mouse drag and keyboard shortcuts are pinned. On coarse-pointer devices, nonselected controls suppress touch-generated sticky hover so it cannot look like a second selected mode. Type/lint/guidelines and production build pass; final screenshots were visually checked in narrow dark and landscape light layouts.

### Bottom-docked screenshot tools (2026-11-04)

`NoticeScreenshotModal` now orders its bounded image scroll region before a nonshrinking footer dock. The footer never overlays the image: zoom, fit, original-size and download remain available while panning a long capture. Below 640px, zoom occupies a centered first row and view modes/download share a second row; desktop uses one centered row. All tool targets are at least 48px, safe-area bottom padding is retained, and DOM/tab order follows visual order. `ModalShell`, focus trapping, theme tokens and native touch panning are reused unchanged.

The cross-engine screenshot matrix adds 820px tablet coverage and checks dock geometry, no horizontal overflow, 48px targets, keyboard focus wrapping and touch zoom buttons. Measure button rectangles only after the modal entrance animation settles; transform scaling otherwise reports slightly less than the CSS target size.

Firefox consistently reused a failed same-URL image after an HTTP error during this verification. `NoticeScreenshot` now adds an attempt query parameter only on explicit retry (original load and download URL remain unchanged). Tests assert the fresh retry request and retain HTTP/invalid-image recovery coverage. Evidence, preserved originals and independent rollback: `/private/tmp/lawcast-viewer-dock/VERIFICATION.txt`.
- Final dock matrix: 53 passed across three desktop engines and WebKit touch emulation; light/dark, mobile/tablet/desktop and landscape remain covered. ESLint, formatting, typecheck, guidelines and Cloudflare build pass. Active sources retain the dock; rollback on an independent fixture restores three task-start hashes.

## Remaining boxed surfaces follow-up (2026-11-07)

- The screenshot-identified notice empty state, recent-change cards and discussion index now share the open page surface instead of the earlier cross-page content-card treatment. Semantic empty states and embedded discussion lists use the same treatment for consistency. Other semantic result cards, statistical panels and announcement surfaces remain unchanged.
- `frontend/src/lib/styles/layout.css` owns `lc-open-empty-state`, `lc-flat-list` / `lc-flat-list-row`, plain inline statuses and underlined discussion status filters. Repeated rows retain soft bottom separators, zero inline inset and 24px block spacing. Digest-matched changes keep an explicit 3px warning-colored leading rule instead of a filled card. Titles wrap rather than truncate in the changes index.
- Secondary change actions reuse `lc-result-action-secondary`, including its 44px target and existing focus/hover treatment. Search recovery buttons, query parameters, explicit weak-result reveal and comparison links preserve their existing behavior.
- `frontend/e2e/open-layout.spec.ts` adds four-route checks at 320/390/820/1440px in both themes, including transparent backgrounds, zero outer borders/radius, overflow, scoped axe checks, weak-result reveal, comparison destinations, status navigation and keyboard thread entry. Existing content-hierarchy and theme-palette selectors now distinguish open lists from retained cards.
- Task-only originals/hashes, patch, modified archive and separate-copy rollback evidence: `/private/tmp/lawcast-flat-surfaces/VERIFICATION.txt`. The working frontend remains on `codex/flatten-remaining-surfaces-20261107`; unrelated pre-existing dependency-migration edits are preserved.
- Hover contrast follow-up: removing the green status fill exposed the original `#15803d` text directly over the light row-hover surface, measuring 4.28:1. Plain list success text now mixes the theme success token with 20% primary text. Keep the existing theme-palette hover/focus frame tests; idle axe checks alone did not catch this state.
- Final verification: 16 browser regressions passed (four-route responsive/theme matrix, retained card hierarchy and hover/focus palette frames). Lint, Svelte/native type checks, vendor tests, guideline checker and Cloudflare production build passed. The independent rollback copy restored all eight original hashes and passed the original content-card browser regression.

### Flat pagination follow-up (2026-11-07)

- Shared `PaginationNav.svelte` now uses bare arrows/numbers with a theme-accent underline for the current page. Box borders, active scaling/shadows and the filled result-count badge are removed. All real controls retain 44px minimum width/height, the shared keyboard focus outline and existing navigation callbacks.
- Below 640px, compact first/current/last number links replace the wider neighbor sequence; duplicate boundary arrows are hidden while previous/next arrows remain. First/last direct navigation remains available through the numeric links. Both sequences are SSR-rendered and CSS chooses one, so no viewport-dependent hydration shift is needed.
- Numeric links expose `aria-current="page"` and stable accessible labels. The nav exposes `aria-busy`; an invisible numeric placeholder preserves the width while its pending spinner is visible. Fine-pointer hover fill remains neutral; dark touch hover cannot reintroduce legacy boxed styles.
- Regression evidence: `/private/tmp/lawcast-flat-pagination/VERIFICATION.txt`. The browser matrix covers mobile/tablet/desktop themes, minimum targets, selected styles, axe, first/last navigation and pending feedback. A separate actual-component SSR fixture renders 1,448-page start/middle/end states at 320/390/1440px in both themes; it checks geometry rather than claiming live archive data. Independent rollback restores the task-start hashes and original boxed browser rendering.
