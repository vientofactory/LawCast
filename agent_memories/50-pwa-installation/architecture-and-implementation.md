# PWA Architecture and Installation

## Current structure

- The root repository orchestrates deployments and pins the backend, frontend and semantic-search submodules. `embedding-map/` is an independent ignored checkout.
- `backend/` runs NestJS, TypeORM/SQLite, Redis caching, legislative-notice crawling and immutable archives, diffchain tracking, discussions and notifications.
- `semantic-search/` provides the Python embedding/index/search sidecar used by the backend.
- `frontend/` runs SvelteKit 2 and Svelte 5 with route-level SSR loaders, a shared API client, server hooks and a same-origin API proxy. Cloudflare Pages is the production target; adapter-node supports local production tests.
- `src/routes/+layout.svelte` owns global navigation effects, the footer and consent UI. It now also owns PWA installation and worker registration.
- Before this change, `static/sw.js` handled push and notification clicks only, and `WebPushConsentForm.svelte` registered it on demand. Existing brand icons already included 192px and 512px PNGs.

## Implementation decisions

- Keep `/sw.js` and its root scope. A competing service worker would replace the push registration and risk subscriptions. The existing push and notification-click handlers remain intact.
- `static/manifest.webmanifest` provides a stable root identity, start URL, root scope, Korean metadata and standalone display using the existing `static/brand/` PNGs. `src/app.html` links the manifest; the existing Apple touch icon remains.
- `PwaInstallPrompt.svelte` registers the worker on every page in secure contexts. It retains the browser-provided `beforeinstallprompt` event and invokes its one-shot `prompt()` from the install button click. There is no automatic native dialog on page load: browsers require user activation.
- Show installation only when the browser offers it. Standalone display and iOS standalone suppress the offer; `appinstalled` clears it. Unsupported browsers, including iOS browsers without this event, keep their normal platform installation menu.
- Deferral or native rejection sets a seven-day timestamp cooldown. Storage errors do not block installation. No permanent installed flag is stored, so uninstalling does not permanently suppress future eligibility.
- The worker precaches only the offline document and two brand icons in `lawcast-pwa-v2`. Navigations use the network and fall back on network rejection. API responses, SSR payloads, authenticated content, challenges and errors are never added to cache. HTTP errors retain their real status instead of becoming offline pages.
- The offline page is a connection notice, not a snapshot of legislative information. It works without JavaScript or external styles/fonts, including on deep URLs, and offers a root retry link.
- Increment the worker's cache version when changing precached assets. Activation removes only older `lawcast-pwa-` caches, preserving unrelated caches.

## Validation

Verified locally: frontend lint passed, Svelte check reported zero errors and warnings, the agent-guideline checker reported zero violations, and all 12 PWA Playwright tests passed against each of the Node and Cloudflare Pages production runtimes. Chromium reported no installability errors. The 375px mobile installation screenshot was inspected. Both the Node test build and the final Cloudflare production build passed.

`npm run test:e2e:pwa` and `npm run test:e2e:pwa:cloudflare` use `playwright-configs/playwright.pwa.config.ts`, build adapter-node or Cloudflare Pages production output and start a dedicated mock-mode server on 127.0.0.1:4185. It refuses to reuse another server. The generic and integration suites exclude this production-only spec.

The suite checks manifest discovery and Chromium parsing, real icon dimensions, shared push registration and scope, deep-link offline navigation and online recovery, bounded asset caching and API network behavior, installation eligibility, click/user-activation and one-shot prompt semantics, cooldown and expiry, native rejection, installed/standalone suppression, prompt failures and blocked storage.

Headless tests use synthetic installation events for the prompt contract; they do not claim to install an OS application or automate browser-owned installation UI. Real manifest parsing and service-worker/offline behavior use Chromium without mocks of those browser APIs.

Related context: [frontend testing notes](../repo/frontend-notes.md), [frontend exploration](../01-project-exploration-and-discussion-plan/lawcast-frontend-exploration.md), [page cache policy](../47-cloudflare-page-cache/cache-review-and-validation.md).


## Production Pages HTML normalization regression

**HIGH**: Initial production verification of frontend 1.24.0 found that the worker never activated. A direct `navigator.serviceWorker.register('/sw.js')` produced an installing worker that disappeared; `Cache.addAll` failed with a request error. Network evidence: `/offline.html` returned 308 to `/offline`, which returned 404 from SvelteKit. Both brand icons returned 200.

Cloudflare Pages normalizes HTML asset URLs to extensionless paths. The adapter generated a static exclusion for `/offline.html` only, so `/offline` was routed into the SvelteKit worker instead of the static HTML asset. Node production serving does not perform this normalization, so the initial Node suite passed.

The fix in `frontend/svelte.config.js` retains the default `<all>` exclusions and adds `/offline` to `adapterCloudflare({ routes: { exclude: ... } })`. The shared PWA suite now has an HTTP regression assertion for the offline document and an optional Cloudflare runtime via `npm run test:e2e:pwa:cloudflare` (Wrangler Pages local mode with a mock-data binding). Keep this platform-specific check alongside the Node suite.

References: [Pages HTML normalization](https://developers.cloudflare.com/pages/configuration/serving-pages/), [Pages Function routing exclusions](https://developers.cloudflare.com/pages/functions/routing/).

The Cloudflare suite also exposed a second edge: replaying a cached redirected response for a navigation fails with Chromium `net::ERR_FAILED` because navigation uses manual redirect mode. The worker returns a fresh HTML `Response` around the cached body to remove redirected-response metadata; cache version v2 replaces any old entries.

## Release references

- Initial PWA release: [frontend PR 168](https://github.com/vientofactory/LawCast-Frontend/pull/168), tag `frontend-v1.24.0`, squash commit `a46908489dce27ab7282aaff52e02591288439b2`.
- Pages compatibility patch: [frontend PR 169](https://github.com/vientofactory/LawCast-Frontend/pull/169), tag `frontend-v1.24.1`, squash commit `fc21a6e0f3b07bffd3abfd5066d0647ba492ea9e`.
- Final production deployment: `e730f095-0f83-412f-aa43-eb4b55bca549` in Pages project `lawcast-frontend`, serving `law.viento.me`.
- Both release commits were created on feature branches with explicit GPG signing; frontend `dev` was fast-forwarded after each squash merge, dependencies reinstalled and `origin/dev` synchronized.

## Cached launch screen (2026-10-29)

- `frontend/static/pwa-start.html` is a self-contained loading document with inline CSS and JavaScript, system fonts, saved/system theme support and a visible retry link. Its only visible content is the header's SVG symbol geometry and retry control. The C arc, L and notification dot assemble on a three-second loop, hold, fade out and reset invisibly; reduced motion shows the complete static symbol. The worker precaches it in `lawcast-pwa-v5` and serves `/pwa-start` navigations from that cache before any network request. Keep the retry link visible from the beginning: Chromium can suspend old-document timers during pending replacement navigation, so a delayed hint may never appear.
- The manifest retains the existing `/` app identity and scope but changes `start_url` to `/pwa-start`. The launch document observes first contentful paint before using `location.replace` to navigate to `/`, preserving search and hash. A bounded one-second fallback handles hidden windows and browsers without paint timing. Animation frame callbacks alone do not guarantee a displayed frame; Chromium also exposes no paint timing entry when queried from the old document during pending replacement navigation, so the browser test verifies the actual captured screen rather than treating that metric as proof. The browser keeps the launch document visible while waiting for the home response. History replacement avoids a back-button launch loop. Ordinary page responses keep their original status, headers, redirects and SvelteKit hydration; no SSR or API data enters the cache.
- This covers launches using the updated manifest, not arbitrary deep-link navigations. Existing installations must receive the browser's manifest update before they use the new start URL. A first visit without an installed worker still needs the network to obtain the static entry document.
- Keep `/pwa-start` alongside `/offline` in Cloudflare adapter routing exclusions: Pages normalizes `.html` asset URLs before routing. Cached documents are rewrapped to remove redirect metadata, as required by the earlier offline regression.
- The PWA test configuration places a local HTTP proxy on port 4187 in front of the production runtime on port 4185. The fixture delays only `/?pwa-test=slow` for 17 seconds. Browser route interception cannot reliably delay worker-owned fetches. During a pending replacement navigation, Playwright locator assertions wait for navigation; the launch regression uses CDP to inspect the launch document, capture its screenshot and verify retry visibility before checking final hydration and client navigation.
- Local verification: frontend lint passed; Svelte check reported zero errors and warnings; the root agent-guideline checker reported zero violations. All 23 PWA tests passed against both Node and Cloudflare Pages production builds, including a repeat against release version 1.25.6. Symbol geometry matches `src/lib/brand-symbol.js`; deterministic timeline assertions cover assembly, fade, loop boundaries, stable bounds and reduced motion. Two screenshots taken during the real delayed replacement navigation differ, confirming the animation continues while waiting for HTTP. Light/dark 375 × 812 screenshots were visually inspected.

### Frontend 1.25.6 release

- The same release includes the 2px NProgress indicator in theme-aware orange (`#c2410c` in light mode, `#fb923c` in dark mode), including glow and spinner colors, to distinguish it from the PWA's blue theme.
- `npm install` synchronized package and lockfile versions to 1.25.6; the resolved dependency tree did not change.
- [Frontend PR 176](https://github.com/vientofactory/LawCast-Frontend/pull/176) contains feature commit `9684f31201d639ac08b5fec150e2175db123e7ed`, created with explicit GPG signing and verified locally and by GitHub.
- PR checks passed: [Web Vitals CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40739908033) and GitGuardian. Squash merge commit: `45e255ade780814828fc336c59895d443704a397`.
- [Release frontend-v1.25.6](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.25.6) targets that exact merged commit. The corresponding production deployment is tracked by [Pages Actions run 40740492979](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40740492979).
- Frontend `dev` was fast-forwarded to the release commit, dependencies reinstalled without lockfile changes, and `origin/dev` synchronized. Backend and semantic-search remain at their existing release commits; no service code changed in either repository. The root pointer records the frontend release commit, reachable from both `origin/dev` and `origin/main`.
