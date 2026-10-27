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
