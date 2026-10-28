# Frontend Lighthouse Audit and Regression Guards

## Scope and method

Production baseline: `https://law.viento.me`, measured on 2026-10-28 JST with Lighthouse 13.6.0 and headless Chrome 156. Mobile uses Lighthouse's default simulated throttling; desktop uses the official desktop preset. All reported results are lab measurements, not CrUX field percentiles. Event Timing samples in Playwright do not establish real-user INP.

Public screens: home, notice board, notice detail (`2221891` in production, `2210001` in isolated tests), changes, discussions, proposals, webhook settings, status, announcements, crawling transparency and license. `/transparency` is not a route: its initial 404 report was discarded and the canonical `/crawling-transparency` was tested separately. A NO_FCP run is invalid, never a zero metric or a passing run.

## Production findings and fixes

- Home mobile baseline: performance 95, accessibility 100, best practices 58, SEO 100; FCP/LCP 2.3 seconds, TBT 20 ms, CLS 0. Desktop: performance 100, accessibility 97, best practices 58, SEO 100; LCP 0.5 seconds, TBT/CLS 0.
- Notice board baseline: performance 98, accessibility 100, best practices 81, SEO 100; LCP 1.7 seconds, TBT 10 ms, CLS 0.
- **HIGH**: external Pretendard CSS blocked rendering for 755–882 ms in the mobile runs. `frontend/src/app.html` linked a separate CDN stylesheet despite the app CSS already being required. The same version, font family, weight mappings, local fallbacks, CDN font binaries and swap behavior now live in bundled `frontend/src/lib/styles/pretendard.css`. The font-origin preconnect remains useful on devices without a locally installed Pretendard font.
- **HIGH**: the automatically loaded Discord iframe fetched its own JS/CSS/avatar tree and set `_cfuvid`, causing third-party-cookie and DevTools Issues deductions. It now loads only after an explicit button press, with a reserved responsive 350-by-500 region. The invite link remains available independently.
- **HIGH**: foreground/background theme transitions were asynchronous for panels using `content-visibility: auto`. A dark foreground could appear over a still-light panel on reveal, reproducing an approximately 1.2:1 contrast ratio in Playwright. Body and shared panel theme colors now update together; panel border/shadow transitions remain. Do not restore independent foreground/background theme transitions without testing a previously offscreen panel.
- Home status links, search submit, scroll cue and Discord invite had accessible names that did not include their visible labels. Natural names or matching labels fix this. Native `ul`/`li` replace `article role=listitem` for status cards.
- Home recent-content components duplicated the names of their outer section landmarks. Inner card wrappers are now neutral `div`s.
- Status crawler headings jumped from h1 to h3 when no warning h2 was present. Crawler cards now use h2.
- Expanded axe checks found statistics and license scroll containers without keyboard focus. Named focusable regions now allow arrow-key scrolling and show a focus outline. Svelte's static noninteractive-tabindex warning is suppressed only on these three scroll containers, with an explanation.
- **HIGH**: the consent banner (`z-index: 9990`) covered modal submit actions (`z-index: 1200`). Shared modals now sit at 10000, above consent and installation prompts, and an analytics-enabled test clicks the validation action while the banner remains visible.
- NProgress's default `role=bar` is invalid ARIA. The shared layout config now uses a named progressbar inside a named region and configures the matching `.bar` selector. A stalled-navigation test audits the indicator while visible.

## External and intentional deductions

- Cloudflare-injected `/cdn-cgi/challenge-platform/scripts/jsd/main.js` reports deprecated Fenced Frame, persistent storage and Protected Audience APIs. The same script accounts for a 280 ms long task on `/webhook` (about 699 ms scripting in that run), explaining its TBT 280 ms / performance 93 baseline. This code is not shipped by the frontend repository. Disabling bot protection merely to raise a Lighthouse score is not an application fix.
- Cloudflare's injected beacon contains legacy polyfills; Cloudflare-owned scripts have cache-lifetime warnings. Do not overwrite their response caching or disable security/analytics to make a local report green.
- GTM has approximately 93 KiB of unused JS in a fresh navigation; Lighthouse estimated zero FCP/LCP savings from this item. Existing consent ordering, Tag Assistant behavior and analytics pageview contracts remain unchanged.
- `frontend/static/robots.txt` intentionally excludes `/status` and `/webhook`, producing SEO 69 for those pages. Keep the crawl policy unless the owner explicitly changes indexing requirements.

## Reproducible checks

- `npm run audit:lighthouse` runs all configured public routes three times sequentially, retaining original JSON/HTML and a summary with median metrics and every failed audit. `--url`, `--routes`, `--runs`, `--form-factor`, `--output-dir` and `--assert` select controlled comparisons. The assert budget is median LCP <=2500 ms, TBT <=200 ms, CLS <=0.1. Runtime/HTTP errors fail rather than silently disappearing.
- `npm run test:e2e:web-vitals` starts an isolated Node production build with mock data, configured GTM and Discord, then tests desktop/mobile and light/dark mode. Google and the explicitly activated Discord widget are fulfilled locally in tests. The normal/integration configs exclude this dedicated suite.
- `.github/workflows/web-vitals.yml` runs lint, type checks and the isolated production browser suite on frontend PRs to main and main pushes. It has no deployment steps or secrets. The default browser suite explicitly disables analytics; the analytics and web-vitals suites enable it to avoid local `.env` values changing unrelated test assumptions.
- Tests cover all 11 screens with axe, blocked external font loading, explicit widget activation and reserved geometry, previously offscreen theme contrast, conservative layout-shift and interaction-duration budgets, actual keyboard scrolling, and the pending-navigation progressbar.
- **Do not run `svelte-kit sync` / type checks concurrently with a Vite production build**: regenerating SvelteKit's app identifier during compilation can produce mismatched server/client identifiers and a hydration error. Also restart a Node preview after rebuilding; an old process retains old server modules while serving new static client files.
- Run Lighthouse after other browser tests finish. CPU contention invalidates controlled comparisons. Use identical build-time public variables and mock data for baseline/candidate A/B; compare production before/after separately because CDN, live data, injected security scripts and compression differ.

## Validation and release

- GitHub PR CI passed: [web-vitals run 40613008673](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40613008673), including lint, type check and all 58 production-build browser tests; GitGuardian also passed.
- Candidate version: `frontend-v1.25.2`; signed feature commit `93242c9`. GPG verification reported a good signature. [PR 172](https://github.com/vientofactory/LawCast-Frontend/pull/172) is ready for review. Production deployment is pending owner approval; no post-deployment production result is claimed.
- Controlled home mobile comparison, three cold runs per version: median performance **98 → 100**, FCP/LCP **1969.6 → 945.6 ms** (52.0% faster), TBT **8.5 → 4.5 ms**, CLS **0 → 0**. Candidate scores were 100 in performance/accessibility/best practices/SEO in every run. Baseline best practices was 77 (the local baseline still loads Discord, while it has no zone-level Cloudflare injections).
- All eleven candidate mobile screens passed median lab budgets; the ten non-home routes each scored 100 performance/accessibility/best practices. Five representative desktop screens also scored 100 in these three categories. Status/webhook SEO remains 69 because of intentional robots exclusions. Desktop status CLS was 0.0112, within the 0.1 budget; other candidate measurements were 0.
- The production crawling-transparency retry succeeded: performance 88, accessibility 100, best practices 81, SEO 100; LCP 1942 ms, TBT 7.5 ms, CLS 0. Its render-blocking CDN font CSS took 1035 ms. The initial NO_FCP run is excluded from comparisons.
- Frontend lint and Svelte checks passed with zero errors/warnings. The guideline checker reported zero violations. Node and Cloudflare production builds both succeeded.
- Existing generic suite: 263 passed / 65 skipped / one test-only stale `h3` selector failed. After updating that selector to `getByRole('heading', {level:2})`, all 14 status tests passed. The other earlier heading-selector and pre-hydration-toggle issues were corrected before that full run. This covers all 264 active tests without claiming that the initial selector failure never occurred.
- Analytics consent: 5 passed. Node PWA/brand suite: 19 passed. Cloudflare PWA/brand suite: 19 passed. Final isolated web-vitals suite: **58 passed** (44 page/theme/device axe combinations and 14 behavioral checks).
- Small machine-readable evidence: [measurements.json](measurements.json). Original Lighthouse JSON/HTML reports remain under ignored `frontend/lighthouse-reports/`; run the documented command to regenerate them. Local measurements are not interchangeable with production/CDN/CrUX values.

## Source evidence

- `frontend/src/app.html`: the external render-blocking stylesheet is removed; bundled font declarations are at `frontend/src/lib/styles/pretendard.css:1` and imported from `frontend/src/app.css:2`.
- Native status list: `frontend/src/routes/+page.svelte:189`; reserved Discord slot and activation: lines 468–491.
- Named progressbar template: `frontend/src/routes/+layout.svelte:17`; modal layering: `frontend/src/lib/components/ModalShell.svelte:48`.
- The regression suite is `frontend/e2e/web-vitals.spec.ts`; its dedicated production configuration is `frontend/playwright-configs/playwright.web-vitals.config.ts`.
