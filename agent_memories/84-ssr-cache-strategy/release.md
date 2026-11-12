# Realtime SSR Isolation Release

## Implementation and review

Frontend PR [#205](https://github.com/vientofactory/LawCast-Frontend/pull/205) releases 3.1.2. Public notice detail/history and home statistics remain SSR; notice/home discussion lists and counts are component-owned no-store browser reads. One layout-owned urgent-announcement context revalidates visible pages every 60 seconds. Discussion reads refresh every 30 seconds while visible, coalesce focus/visibility events, preserve genuine 429 cooldowns and cancel superseded requests.

Bugbot found one P2 regression: background refresh replaced populated thread links with a spinner and lost focus. The fix limits the full loading placeholder to the initial read; a desktop/mobile regression holds a refresh pending and verifies the existing link remains focused before and after the response. Security Review found no high-confidence exploitable issues in the diff.

The metadata-only response hook sends no-store directives on error/private API responses. Public HTML fallbacks use their failure status rather than HTTP 200 because the unchanged production cache rule overrides origin cache-control for successful HTML. SvelteKit data recovery preserves its HTTP-200 protocol with no-store; existing rules already bypass data URLs. No HTML reparsing, Cookie exception, longer public TTL, new public payload cache, backend API change or production fault injection is included.

## Local gates

- Production Node consumer tests: 68 passed; existing home/announcement/discussion/detail/navigation tests: 77 passed.
- Error/429/transport recovery: 79 passed; production Web Vitals/accessibility: 62 passed; local workerd OG/offline: 2 passed.
- Notification regressions across Chromium, Firefox, WebKit and touch: 46 passed. The initial PR run exposed a global-animation wait that included independently canceled CSR progress; the test now waits on its notification host without changing accessibility assertions.
- Request classification/Lighthouse/CI-install unit tests: 23 passed; vendor tests: 3 passed.
- Frontend lint, Svelte/native TypeScript checks, adapter builds and root agent-guideline checker pass.
- The Discord widget test preserves exact reserved dimensions and permits less than one CSS pixel of native viewport anchoring roundoff; deferred offscreen layout can change document offsets without moving the on-screen widget.
- Version metadata is synchronized with a real npm 11.13.0 install; no dependency-resolution changes remain.

Raw review, archive, diff, rollback, CI and production evidence stays in ignored `verification-artifacts/ssr-release/`. Cloudflare cache rules were read before release: ruleset version 44, last updated 2026-10-18, seven unchanged rules. Postdeployment evidence follows below.


## Release and production verification

- Frontend PR #205 merged as `bc4f45dac465bdd22a27acca349f3f7011ee8db1`; [frontend-v3.1.2](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v3.1.2) points to that exact commit. Feature commits were explicitly maintainer-PGP signed, and GitHub verifies the merge commit signature.
- All final PR checks passed in [run 43244077215](https://github.com/vientofactory/LawCast-Frontend/actions/runs/43244077215). The initial notification wait failure was fixed without disabling workflows, skipping assertions or changing CI budgets.
- [Production Pages run 43247523271](https://github.com/vientofactory/LawCast-Frontend/actions/runs/43247523271) succeeded. Canonical production deployment `7cd70acb-bbf2-4c03-97aa-8f9ddc951465` reports the exact merge SHA, main branch and clean commit. All seven encrypted binding names/types match their predeployment state; values were not logged.
- Real anonymous browser verification on `https://law.viento.me` found no urgent/discussion payload in SSR HTML, loaded home and notice discussions through live APIs, and observed the actual urgent revalidation interval. Live API responses were private/no-store and not cache HITs. No browser page errors occurred.
- Invalid revision HTTP 400 and missing-notice HTTP 404 were each requested twice; all responses carried no-store and were not cache HITs. HTTP 503/429 recovery fallbacks are covered by local/CI fixtures; no production upstream outage or content mutation was induced.
- Before/after Cloudflare cache ruleset objects are equal: version 44, seven rules, original 2026-10-18 modification time. No cache rule, Cookie bypass, TTL or runtime binding setting was written.
- Frontend dev was fast-forwarded to the release SHA and pushed to origin/dev; npm 11.13.0 install leaves package/lock metadata clean. Backend remains on dev and semantic-search on main; their root pointers are unchanged.
