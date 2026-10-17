# GA4 Consent Integration

## Root cause

**HIGH**: Google consent commands were queued as plain Arrays in
`frontend/src/lib/utils/consent.ts` and the SSR snippet in
`frontend/src/routes/+layout.svelte` (pre-fix lines 69/91 in the consent helper
and line 64 in the uncommitted official-loader snippet). The Google command API expects the
`Arguments` object produced by `function gtag() { dataLayer.push(arguments); }`.
Tag Assistant showed `virtual_pageview` firing a GA4 `page_view`, but the hit
still carried `gcs=G100` and GA4 DebugView had no devices. The container also
had a denied-default override that requires an explicit consent update.

A returning visitor received only another `default`, never `update`. The
old helper also granted advertising consent together with analytics consent,
and accepting again on the same page sent a duplicate page view.

## Patch

- `frontend/src/lib/utils/gtm-bootstrap.ts`: validated official `gtm.js`
  bootstrap, denied default followed by a stored analytics-only update before
  the container loads. No noscript tracking iframe because it cannot read
  the localStorage consent choice.
- `frontend/src/lib/utils/consent.ts`: Arguments command queue; hydration
  reconciles using `update`, never resets defaults; storage access is inside
  try/catch. Advertising consent always remains denied.
- `frontend/src/lib/components/CookieConsentBanner.svelte`: storage failures
  do not dismiss the banner or grant tracking; repeated acceptance does not
  duplicate the current page view.
- Existing uncommitted official-loader improvements were preserved and
  included in the release branch; backup patch was saved before editing.

## Container settings

Container `GTM-N82SX8WB`, destination `G-ZWHM927MQ6`:

- Version 4: GA4 `page_view` fires only on `virtual_pageview`; maps
  `page_location` and `page_title` from v2 Data Layer Variables and
  `page_path` from the built-in Page Path. Base tag uses `send_page_view=false`.
- GTM automatic browser-history page views must be disabled independently
  of GA4 enhanced measurement. Both were originally separate settings;
  leaving GTM history enabled produced three hits for two page views.
- Version 5: Manage data transmission prevents advertising, analytics and
  diagnostic transmission while the relevant consent is denied. The
  denied-default override remains enabled; the site must send `update`.

## Verification

- Dedicated Playwright config at port 5193 with a valid test container ID,
  mock backend, and Google script requests intercepted.
- Five regression cases: undecided/declined, acceptance plus SPA/repeated
  acceptance, returning visitor ordering, withdrawal, consent storage failure.
- Run the analytics spec through its dedicated config; the standard suite
  skips it because it intentionally has no configured GTM container.
- Lint, Svelte check, Cloudflare build and root comment-language checker.
- Frontend PR [160](https://github.com/vientofactory/LawCast-Frontend/pull/160)
  merged to `583df0896d8949e17cb93fa2499aaacc71b06c05`; release
  `frontend-v1.19.4` created. Cloudflare Pages check completed successfully
  and the live footer showed `v1.19.4 / API v1.18.2`.
- Production Tag Assistant: declined initial visit transmitted zero hits;
  acceptance changed only `analytics_storage` to granted, while all three
  advertising consent types stayed denied. The accepted home page and SPA
  `/notices` navigation produced exactly two `page_view` hits.
- GA4 DebugView received those two `page_view` events at 03:45:45 and
  03:46:04 JST on 2026-10-18. After withdrawal and navigation back home,
  hit count remained two. A subsequent declined reload emitted no page view.
- Root CI's first backend Node 22 run failed an unrelated wall-clock delay
  assertion (`>=100ms`, actual `99ms` in
  `src/modules/shared/batch-processing.service.spec.ts`). Frontend Node
  22/24 and semantic-search checks passed. Reverification is required
  before merging the root pointer synchronization PR.


## References

- [Google consent setup](https://developers.google.com/tag-platform/security/guides/consent)
- [Google data layer](https://developers.google.com/tag-platform/devguides/datalayer)
- [Frontend testing notes](../repo/frontend-notes.md)
