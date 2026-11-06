# Responsive and Accessibility Fixes

## Baseline and preserved workspace

This follows the [read-only responsive/accessibility audit](responsive-accessibility-audit.md). The existing `codex/open-layout-redesign` branch and all earlier uncommitted redesign work are preserved. No commit, release or deployment is part of this task.

The baseline snapshot contains 251 frontend source files. A deterministic browser probe reproduced all nine findings before edits and again on a separately restored copy. The working frontend retains the fixes. Source hashes, a source archive, a task-only patch and a hash-guarded executable rollback are stored in the artifact directory below.

Artifact directory: `/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/responsive-a11y-fixes/`.

## Fixes in priority order

- **P1 F01:** Replace permanently clipped home shortcuts with focus-within-revealed navigation. Keep real links and visible 44px keyboard targets. The clipping helper excludes only the intentionally unfocused state; a dedicated regression verifies the revealed state.
- **P1 F02:** Bound the mobile menu by `100dvh`, scroll the panel, isolate background siblings with inert, keep body scroll locked through the outro, and restore the actual invoker after disposal. Close a menu when responsive layout switches to desktop controls.
- **P2 F03:** Place integrity explanations and original HTML size inside their related `dd`, not beside it within a definition-list grouping div.
- **P2 F04:** Use `lc-banner-error-soft` for push errors. Deterministic enabled-config plus initialization-failure fixtures exercise this UI state in both themes and all three engines without claiming native push delivery.
- **P2 F05:** Use relative container thresholds for header/status layouts, allow brand shrink/wrap, constrain grid tracks and introduction children, and permit search tracks to shrink. Root-font 200% remains a font-preference stress test, not a native browser-zoom certificate.
- **P2 F06:** Use native `details`/`summary` for WebhookGuide, retaining the shared reduced-motion-aware disclosure action. Its body title is `h3` below the section `h2`.
- **P2 F09:** Restore `main-content` on true 404 pages and `discussion-thread-title` on the thread heading.
- **P3 F07:** Include the user-facing field label in each comparison change-region name.
- **P3 F08:** Normalize Markdown body headings from `h2`, preserving nesting/order without mutating tokens. Remove a generic div's invalid accessible name.

## Cross-engine root causes and regression discipline

- Firefox can report a nominal 12px gap as `11.999984741210938`. Geometry assertions retain the 12px design contract with 0.5px rounding tolerance rather than exact floating-point comparisons.
- WebKit's default native Tab policy omits some controls/links. Shared modal Tab handling explicitly cycles visible enabled controls, with one radio per group. Keyboard-return assertions use a genuine focused keyboard invoker rather than assuming a pointer click focuses a button on Safari.
- Fading status hint text passes through insufficient contrast. Switch its text visibility atomically; retain other card/disclosure/modal motion. The regression checks hidden-state visibility, stable focused contrast and reduced-motion behavior.
- **WebKit pointer hit-test regression:** a scrolled `details.lc-defer-render` can report a summary rectangle but dispatch the pointer event to the enclosing `display: contents` root. Three original repeats failed. Three injected `content-visibility: visible` controls hit the summary and opened it. Keep interactive deferred details live; closed native bodies remain hidden and images remain lazy. The new regression clicks the real summary twice without injected styles.
- Production CSS minification serializes `#ffffff` as `#fff`. Contrast parsing accepts short/long hex including alpha, and the white-token assertion checks equivalent serializations. This is a test representation issue, not a palette regression.
- Wait for the native disclosure enhancement before typing in changes-page controls; otherwise hydration can replace a pre-hydration input.
- Do not edit source or rebuild beneath an active verification server. One exploratory dev run was invalidated by HMR. Final functional/browser matrices use an immutable Node build; interrupted/exploratory failures are not counted as final passes.

## Evidence interpretation

The final report and `VERIFICATION.txt` in the artifact directory record exact completed commands, counts, literal outputs, hashes and rollback results. Every public template is represented across small phones, landscape, tablets and desktops with both themes and three engines. Expanded disclosures, keyboard navigation, 200% root font and text-spacing overrides receive separate checks.

Axe `incomplete` remains a review state, not a pass. Representative captures and computed footer colors are reviewed in addition to automated violations. WebKit layout scans explicitly simulate unavailable PushManager to avoid the known local headless native-push hang; dedicated error fixtures separately verify push error readability. Native Safari/iOS push delivery and screen-reader behavior require separate device/assistive-technology verification and are not certified by these tests.

## Final observed results

- Cross-engine regressions: 240 passed, zero failures (Chromium 151.0.7922.34, Firefox 153.0, WebKit 26.5).
- Functional regressions on the immutable Node build: 368 passed, 28 existing conditional skips, zero failures.
- Production accessibility/theme/navigation suite: 62 passed.
- Public matrix: 1,512 base cases, 648 expanded scans, 2,160 axe scans; zero selected-rule violations, normal/expanded overflow, runtime page errors or scan errors.
- Interaction/stress scenarios: 108 completed without errors. Both root-font 200% and text-spacing overrides have zero overflow in 42 cases each. Keyboard walking has no hidden stops; tested menus/filters have no focus escape and restore their invokers.
- Push error contrast: 5.95:1 light and 9.99:1 dark in all engines; the error contrast rule explicitly passes with zero incomplete results. Footer link minimum exceeds 6.69:1. Other matrix incomplete nodes are retained as review states, not converted to passes.
- Sixteen contact sheets (84 representative captures), direct issue screenshots, enlarged text and landscape-menu screenshots were opened for visual review. This is representative manual inspection, not a claim to inspect every pixel of all 2,160 captures.
- Lint, type check (zero errors/warnings), Cloudflare build, Node build and agent-guideline checks pass. Package files are unchanged.
- Final package: 253 source files, 23 task-only changed paths. Separate-copy rollback restores all 251 original hashes and removes the two added files; browser reproduction restores all nine original findings. Patch replay matches every modified source hash. The actual frontend retains all fixes.
