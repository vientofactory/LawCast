# Open Signal Brand and Intro Animation

## Asset identity and browser updates

The selected Open Signal mark consists of a rounded C arc, an inner rounded L and a detached notification dot. The existing Pretendard wordmark path is preserved exactly. Light and dark wordmarks are separate SVG assets, while `frontend/src/lib/brand-symbol.js` shares symbol geometry between the UI and the asset generator.

**HIGH**: changing the bytes behind an installed PWA icon's existing URL does not reliably trigger an icon update. Chrome's updated manifest process detects icon changes by URL. Every new logo, wordmark, favicon, Apple touch icon, PWA icon and notification badge is therefore published under `/brand/v2/`. The previous unversioned assets remain unchanged for older clients. Keep the manifest URL, `id`, `start_url`, service-worker URL and registration scope stable to preserve installed-app identity and push subscriptions.

Reference: [Chrome web app update process](https://developer.chrome.com/blog/improvements-to-web-app-updates?hl=en). Installed icon refresh timing and confirmation remain controlled by the browser and platform; URL rotation does not promise immediate replacement of every existing OS shortcut.

`frontend/scripts/generate-brand-assets.mjs` regenerates the versioned asset set with the existing resvg dependency. The colored launcher icons have opaque white padding. Android notification badges contain only a white symbol on transparent pixels. Future identity revisions must use a new asset URL revision and update all consumers together.

## UI animation contract

- Header only: the C draws and rotates into place, the L slides in, the dot lands and emits a single ring, and the wordmark reveals from left to right.
- The wordmark completes at 1,700 ms. The subtitle then fades upward over 450 ms, with its layout space reserved from the initial render.
- Client-only module state claims the intro once per document. Client navigation does not replay it; SSR never mutates visitor-shared state.
- Animation styles exist only inside `prefers-reduced-motion: no-preference`. With reduced motion enabled, including during playback, the complete logo and subtitle appear immediately and the ring stays hidden.
- Footer, app icons, push icons and OG images use static branding. The OG renderer imports the versioned full SVG logo.

## PWA and cache integration

The stable `/manifest.webmanifest` references the new 192px and 512px icon URLs. HTML favicon and Apple links, installation prompt, offline page and notification options also reference `/brand/v2/`. The existing worker upgrades `lawcast-pwa-v2` to `lawcast-pwa-v3`, precaching only the offline document, versioned app icons and notification badge. Activation deletes only older `lawcast-pwa-` caches.

## Validation

The production Playwright PWA suite covers the assembly timeline and subtitle delay, stable geometry, no replay on SPA navigation, initial and dynamically enabled reduced motion, light/dark/mobile branding, image dimensions and badge alpha, manifest icon URLs and installability, legacy cache removal, push notification options, offline recovery and installation prompt behavior. Run both `npm run test:e2e:pwa` and `npm run test:e2e:pwa:cloudflare` because Pages HTML normalization differs from Node.

These tests do not install an OS app or send a real push through a user's subscription. They exercise Chromium's manifest and service-worker APIs and invoke the worker push handler in an isolated harness.

## Release and production evidence

- Frontend release: [PR 170](https://github.com/vientofactory/LawCast-Frontend/pull/170), [frontend-v1.25.0](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.25.0).
- Feature commit `871a5a6d4916c84ff91ad15ee8963a5785e4171c` was explicitly GPG-signed and verified before push. Squash release commit: `c82ae63398eb38d56f2b4ca9043ce27ba814d02c`.
- Final local verification: lint, Svelte check (zero errors/warnings), agent guideline checker (zero violations), Node production PWA suite (19 passed), Cloudflare Pages local suite (19 passed). `npm install` after version bump changed only the manifest and lockfile version metadata; dependencies did not change.
- Cloudflare Pages production deployment `4fccd99c-1f84-4218-a631-025de0a2de30` succeeded for the squash commit. Production hostname: `law.viento.me`.
- Production HTTP checks confirmed the homepage's versioned favicon, stable manifest ID with versioned icon URLs, and exact byte matches for both PWA icons, notification badge, both wordmarks, favicon SVG and Apple touch icon. The served worker contains the v3 cache and versioned push asset URLs.
- Local frontend `dev`, `origin/dev` and the release tag point to the same squash commit. Existing unrelated backend working-tree changes were preserved and excluded from the release.
