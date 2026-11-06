# Request failure classification and recovery

**Current rule:** only a connection failure without an upstream HTTP response uses the standalone offline screen. HTTP 429 uses the rate-limit UI; all other HTTP errors and timeouts retain the ordinary failure UI and site chrome. This supersedes the earlier broad unavailable-gateway rule below.

## Root cause

Pages rendered `RateLimitOverlay` for any non-null `loadError`. The serialized error omitted status/kind, and discussion mount effects also started a cooldown for every initial failure. A 503 or broken connection therefore looked like HTTP 429.

## Implementation

- `frontend/src/lib/utils/request-failure.ts` centralizes status-authoritative classification. Only numeric HTTP 429 starts a cooldown; `Retry-After`, error text and a claimed rate-limit kind alone never do.
- `frontend/src/lib/api/client.ts` retains transport failure kinds and bounds requests/body reads to 30 seconds. The SSR hook and API proxy forward abort signals. A deadline abort becomes timeout, not rate limiting.
- `frontend/src/lib/server/load-error.ts` serializes status/kind. `LoadFailureState.svelte` reuses the existing rate overlay only for 429; other failures use persistent, in-flow themed feedback with immediate retry for recoverable failures.
- List, statistics, transparency, semantic-search and discussion views share the same classification. Partial discussion failures no longer masquerade as an empty list. Successful retries clear stale cooldowns; generic page errors retain meaningful status and recovery guidance.
- The Cloudflare challenge sentinel and existing challenge recovery flow remain intact.

## Verification

Real HTTP fixtures test 503 with misleading Retry-After, socket failure, HTTP 504, authentication/authorization errors, malformed/non-JSON responses, HTTP 200 unsuccessful envelopes, genuine 429, recovery transitions, partial discussion outages and a real 30-second unanswered request. Desktop/mobile screenshots and axe checks cover light/dark feedback. The fixture is local test evidence, not a production availability check.

Evidence and baseline/modified/rollback commands: `/private/tmp/lawcast-load-errors/VERIFICATION.txt`. Baseline reproduces the 503-as-rate-limit defect. Active source stays modified; rollback is tested on a separate copy only.

## Dedicated server connection screen

`ServerOfflineState.svelte` presents a centered branded recovery screen with a manual retry, official Discord invite (`PUBLIC_DISCORD_SERVER_URL`, with the existing official invite as fallback) and the supplied UptimeRobot status URL. It requires no backend request to render either external link. The copy does not claim a confirmed global outage: it covers an unavailable or delayed data server.

The shared layout now replaces primary page content only when `loadError` represents a connection failure without an upstream HTTP response (the initial broader timeout/gateway rule was superseded). Partial discussion failures stay local through `LoadFailureState`; generic HTTP 500, auth failures and HTTP 429 retain their own UI. Error routes reuse the same screen without interfering with Cloudflare challenge recovery. Home requires both its recent-notice and stats reads to be unavailable before using this full-screen state, rather than treating a single optional widget failure as a site outage. Retry preserves the current URL/search and restores normal content through `invalidateAll` (full reload on error routes). No polling or extra health probe was introduced.

The static `offline.html` and service worker remain unchanged: device/network-offline navigation still uses the PWA fallback, while an available frontend can render this server-connection screen. Light/dark styles reuse app tokens, and all actions have minimum 44px touch targets and keyboard focus. Current-task evidence: `/private/tmp/lawcast-server-offline/VERIFICATION.txt`.

### Design-system alignment

The server-connection state now uses the same `lc-main--form` reading width, shared page-title underline and neutral icon surface as other pages. It no longer places a white-background bitmap logo inside a second centered card. Its content aligns to the page gutter without nested horizontal padding. Retry remains the sole primary action; the independent status link is a neutral secondary action alongside it, and Discord is a lower-priority text link under a soft divider. Narrow layouts give retry/status their own full-width rows, while all three actions keep 44px targets and existing focus styles. The same component handles full-page and partial failures; inline headings remain below the surrounding page-title size.

No failure classification, URL, PWA document or service worker changed in this refinement. The existing unanswered-request regression exposed a fetch implementation that did not finish after abort: the API now races the full response/body operation against the 30-second deadline as well as sending the abort signal. The local slow fixture waits 60 seconds rather than 31 seconds so its response cannot narrowly race the deadline. Evidence: `/private/tmp/lawcast-server-offline-design/VERIFICATION.txt`; the added regression checks the shared heading/layout classes, removal of the bitmap, action hierarchy and actual theme-switch interactions.

### Standalone recovery shell

Full-page backend-offline guidance now omits the site header/navigation and footer, for both structured primary load failures and unavailable error routes. Its reading column fills at least `100svh`. The shared layout restores the footer when the primary request recovers; the normal page restores its header. Non-offline errors (including 404) retain site chrome, and partial discussion failures do not replace otherwise available page content. Recovery actions and external links are unchanged. Evidence: `/private/tmp/lawcast-server-offline-chrome/VERIFICATION.txt`.

### Connection failures versus error responses

`isServerUnavailable` now requires missing upstream HTTP status and `kind: network`. Actual HTTP 408/500/502/503/504 and local request deadlines use the ordinary `LoadFailureState`/error-page UI; only HTTP 429 starts a cooldown. A generic programming `TypeError` is no longer sufficient evidence of a connection failure; browser fetch messages (including Safari `Load failed`) and transport error codes remain supported.

SvelteKit error routes necessarily expose an HTTP error status to the browser, so the detail/thread loaders also serialize their normalized `kind` in `App.Error`. The error page/layout use that field to distinguish a synthetic transport-error wrapper from a real backend HTTP 503. Browser proxy connection failures use a reserved response header (only for the proxy's generated 502), which the API client normalizes back to a status-less network failure. Real upstream responses have this header stripped on both SSR and browser proxy forwarding, preserving HTTP status authority. Client timeouts remain timeout errors, not offline or rate limiting.

The general `LoadFailureState.svelte` and `RateLimitOverlay.svelte` components were not redesigned in this correction. Three existing rendering branches remain distinct; the dedicated offline component only changed its copy to describe connection establishment failure. Local fixtures exercise real HTTP failures, SSR synthetic statuses and subsequent browser proxy retries. Evidence: `/private/tmp/lawcast-offline-separation/VERIFICATION.txt`.
