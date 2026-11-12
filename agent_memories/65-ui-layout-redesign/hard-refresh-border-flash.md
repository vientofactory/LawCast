# Hard Refresh Border Flash Investigation

## Observation and confidence

The user supplied an 8.865-second, 3600x2338, 120fps recording of the installed Chrome LawCast app. Around 6.53–6.62 seconds, several interactive elements simultaneously show purple rectangular edges and temporary purple link text: the site-brand anchor, desktop navigation anchors and two linked status items. The theme button also briefly looks like a native bordered button. The rest of the page is already substantially styled. This is not evidence that every element on the page acquires a border.

**The triggering mechanism is not yet conclusively reproduced.** The leading code-level hypothesis is an initial-style transition flash amplified by broad `transition-all` on these exact elements. Do not describe this as a confirmed hydration bug, a proved missing stylesheet, or a known Cloudflare regression.

Evidence is in ignored `verification-artifacts/border-flash/`: contact sheet, high-frequency refresh frames, native extracted flash frame, SSR HTML, downloaded CSS, per-frame style probes and video pixel analysis. The recording's purple outlines are visible directly in `flash-frame.jpg`; the settled screenshot/DOM alone is insufficient to diagnose this transient.

## Source correlation

- `frontend/src/lib/components/Header.svelte:131`: brand anchor uses `transition-all duration-300`.
- `frontend/src/lib/components/Header.svelte:148`: theme button uses `transition-all duration-200`.
- `frontend/src/lib/components/Header.svelte:194`: each desktop menu link uses `transition-all duration-200`.
- `frontend/src/routes/+page.svelte:298,303`: status card and linked archive item use `transition-all duration-200`; the integrity link follows the same pattern.
- `frontend/src/lib/styles/layout.css:789–801`: navigation's final state has transparent border, neutral text and a bottom-only active indicator. This matches the settled video, not the initial purple rectangles.
- `frontend/src/lib/styles/layout.css:535–543`: keyboard focus outlines are explicitly scoped to `:focus-visible`. Many distinct links flashing together is not a normal single-element keyboard-focus event. Globally removing focus outlines would be the wrong mitigation.
- `frontend/src/app.html`: saved/system theme is applied by an inline head script before the stylesheet links. The recording remains visually light; a dark/light palette flash is not demonstrated.

The broad transition declaration can animate more properties than intended. If the browser observes an intermediate computed style before the final cascade settles, changes to colors, border widths/colors, geometry and outline-related properties may be included. The exact initial style-change event that would start this transition in the user's installed-app context remains unobserved; initial load does not universally start transitions merely because `transition-all` exists.

## Checks performed and negative results

1. Read production SSR. All eight initial CSS links, including global app/layout CSS, occur in `<head>` as ordinary render-blocking `rel=stylesheet` links, before body markup. There is no observed async `media=print` stylesheet trick. A bare claim that layout CSS loads only after hydration is contradicted by this HTML.
2. Downloaded current hashed stylesheets. Root/global CSS includes Tailwind reset, utilities and layout overrides; the chunk named SeoHead contains the scoped Header rules. Chunk filenames alone do not indicate missing component CSS.
3. Tested isolated bundled Chromium and installed Chrome with browser cache disabled. Initial-frame computed styles, outlines, focus matches, stylesheet URLs and element animations were sampled. Compared normal JavaScript, blocked application modules and reduced-motion conditions; installed Chrome also performed a normal reload with cache disabled. No matching flash or affected-element CSS transitions were captured. These are not exact installed-PWA Cmd+Shift+R reproductions and do not establish an A/B fix.
4. Read the user's settled LawCast Chrome tab. No inline `<style>` injection was present; the expected CSS links were present; sampled menu links did not match `:focus-visible` and had `outline-style: none`. This does not exclude short-lived extension/PWA/Chromium-specific behavior earlier during reload.
5. Read the service worker. Ordinary navigation is network-first and does not persist SSR/API documents; only the launch-screen path has bounded one-use HTML/style transfers. The recording is a reload of `/`, not demonstrated to be a launch transfer. No evidence currently attributes this to stale stored SSR.
6. The preceding Cloudflare change affects cache eligibility predicates only, not HTML bytes, CSS paths, CSS contents or TTL. Faster/slower resource timing might expose a preexisting visual issue; a causal role of that change was not demonstrated.

No frontend source, production rule or user browser preference was changed. Read-only user-tab inspection ended with the tab unchanged.

## Recommended next experiment, not implemented

First reproduce in the installed-app context with initial computed-style/transition events or a Performance filmstrip around actual Cmd+Shift+R. Include visited-link state and the existing service worker. Capture both `border-*` and `outline-*`; video pixels alone cannot distinguish their CSS origin.

Then compare an isolated build with affected elements restricted to explicitly required transition properties (for example transform/opacity for the brand and status links, and background/color for menu hover only where intentional). Do not remove the brand's existing SVG intro or all motion to mask the problem. Do not indiscriminately hide the entire body or disable keyboard focus indicators. If the flash persists without those transitions, investigate the installed-app renderer/stylesheet lifecycle and profile-specific injection rather than declaring the hypothesis proven.

## Reference

[Tailwind transition-property documentation](https://tailwindcss.com/docs/transition-property) defines `transition-all` as `transition-property: all`. [CSS Transitions](https://www.w3.org/TR/css-transitions-1/#starting) specifies before/after style-change requirements; it does not guarantee an initial page-load transition for every element.

## Local mitigation and regression verification

On 2026-11-13, implemented the requested property restrictions on frontend feature branch `codex/fix-hard-refresh-border-flash`, without deployment, version bump or package changes. Header brand uses transform-only transitions; desktop/mobile theme and menu controls use background/color only. Linked status items have no own transition; their parent cards retain the translate hover/focus motion. The unlayered `.lc-home-signal-card` declaration also needed narrowing to `translate 200ms ease`: changing Tailwind classes alone left border-color transitions active through CSS cascade precedence. Brand SVG animation source/keyframes and global keyboard-focus styles are unchanged.

Added `frontend/e2e/hard-reload-styles.spec.ts` and `frontend/playwright-configs/playwright.hard-reload.config.ts`. Local production Node build tests passed **24 cases**: eight forced-reload cases across desktop/touch, light/dark and normal/reduced motion, plus 16 existing historical brand-animation cases. The new cases execute two CDP `Page.reload({ignoreCache:true})` cycles each and disable the network cache, sample initial-frame computed transition/outline styles, and check real keyboard navigation/theme toggling and mobile menu focus return. These are local Chromium hard-reload-equivalent tests, not a reproduction in the user's installed Chrome PWA profile.

The newly added guard fails against original code with `site-brand: all` and other overly broad transition declarations. After narrowing, 24 tests pass (24.2s); existing production Web Vitals/accessibility regressions also pass, 62 cases (37.2s). Frontend lint/check/native TypeScript/vendor checks and Cloudflare adapter build pass locally. Early mobile test failures were fixture errors (hidden desktop theme control, followed by focus movement before the real menu outro completed); tests now use the actual mobile menu and await removal/return focus rather than weakening assertions.

Raw results, original source archive, modified source archive, patch, executable rollback and exact commands/results are preserved in `verification-artifacts/border-flash-fix/`. Reverse patching an independent source copy restores all 324 original files byte-for-byte. Temporarily restoring the test harness there makes the original guard fail again as expected; the temporary files were removed afterward. Active frontend retains the narrowed transitions. This establishes the requested property restrictions and preserved interactions; complete elimination of the original non-deterministic recorded pixel flash remains unproven until checked in that installed-app environment.

## Release review and CI follow-up

Frontend [PR #206](https://github.com/vientofactory/LawCast-Frontend/pull/206) targets patch release 3.1.3. Read-only Bugbot found no application-code regression but reported a P2 missing CI invocation. After explicit user approval, the existing PR/main Web Vitals workflow gained an explicit hard-reload/brand suite step. Security Review found no high-confidence exploitable findings. Initial feature commit `92f7eb8321af04516bed5ae0db163c659256d336` was explicitly maintainer-PGP signed.

Initial remote run `43264059893` passed all shared-UI jobs but failed two existing widget viewport-y assertions in the production Web Vitals suite. The fixture now establishes focus before measuring and uses real Enter activation, avoiding Playwright's intervening pointer auto-scroll while keeping all width/height/x/y assertions and the subpixel tolerance. This follow-up passed 20 repeated desktop/mobile cases, the complete 62-case local suite, lint and type checks; signed follow-up commit is `18532c1f9da1322728dd9afac816b1d9292023df`. Production verification must still distinguish property/interaction checks from a guaranteed reproduction of the original installed-app renderer-specific flash.

## Frontend 3.1.3 deployment verification

Frontend PR #206 merged as `25184e0fbee069376be153d7b98fe6f7a5db7951`; [frontend-v3.1.3](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v3.1.3) and origin/dev point to that exact commit. GitHub verifies the squash-merge signature. All final PR checks passed in [run 43265973704](https://github.com/vientofactory/LawCast-Frontend/actions/runs/43265973704), including the newly wired hard-reload/brand suite and all shared-browser jobs.

[Pages deployment run 43269634288](https://github.com/vientofactory/LawCast-Frontend/actions/runs/43269634288) succeeded. Canonical production deployment `0e70c821-a68e-4933-a03b-2631def3c151` reports the release SHA, main branch and clean commit; deployment completed 2026-11-13 02:28:48 JST.

On actual `https://law.viento.me`, the canonical HTML reports 3.1.3. The production hard-reload/brand/focus suite passed **24 cases (51.8s)** across desktop and touch, both themes and normal/reduced motion, with video evidence. Initial-frame assertions found no unintended non-focus outline or broad border/outline/layout transition; historical brand frames and real keyboard focus/theme/menu interactions pass. These are isolated Chromium production tests, not proof of every original installed-app rendering condition. Separate live checks found HTTP 400/404 and real-time APIs still no-store/non-HIT and no page errors.

Cloudflare request cache ruleset objects before/after deployment are identical: version 45, seven rules, unchanged 120-second successful-public-HTML TTL. Seven encrypted runtime binding names/types are preserved; values were not logged. No cache-rule, WAF or TTL write was performed. Frontend and backend are on dev; semantic-search remains on main. Backend/semantic source versions and root pointers are unchanged.
