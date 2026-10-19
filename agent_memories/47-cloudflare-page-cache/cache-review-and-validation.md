# Cloudflare Page Cache Review and Validation

## Scope and evidence

- Requested: inspect frontend/backend endpoint relationships, tune the connected Cloudflare dashboard, and verify production behavior with real measurements.
- Date: 2026-10-18 JST. Requests ran on 2026-10-17 UTC and reached Cloudflare KIX.
- Production UI reported frontend v1.19.4 and API v1.18.2; the inspected local versions match (frontend commit `583df08`, backend commit `7e2117f`).
- No application source, dependencies, versions, or deployment pointers were changed. Dashboard changes are already live. This directory records the investigation, not a pending application release.
- Raw measurements: [measurements.jsonl](measurements.jsonl). Each line preserves status, cache status, Age, response control, duration, URL, and Cloudflare Ray where collected.
- Related policies: [frontend notes](../repo/frontend-notes.md), [SSR payload audit](../17-ssr-payload-minimization/ssr-minimal-payload-audit.md), and [search UI review](../29-search-ui-persona-audit/usability-audit-and-improvements.md).

## Request paths and endpoint relationships

### Three distinct request paths

1. Initial document: browser -> Cloudflare -> SvelteKit page/layout loaders -> backend -> SQLite/Redis and service providers. A document cache HIT avoids rendering and all loader API calls for that document.
2. Client API: browser -> `/api/[...path]` -> backend. This proxy is implemented at `frontend/src/routes/api/[...path]/+server.ts:64`.
3. SPA navigation/refresh: browser -> route `/__data.json` -> page/layout loaders -> backend. HTML caching alone does not eliminate these reads.

**HIGH**: SSR `fetch('/api/...')` bypasses the browser-facing API proxy. `frontend/src/hooks.server.ts:19` rewrites it to `API_BASE_URL` at lines 49-64 and forwards visitor IP. Caching only the public frontend `/api/*` URLs cannot be assumed to cache these SSR calls; the actual target URL and its zone rules would need separate inspection.

### Shared layout

`frontend/src/routes/+layout.server.ts:61` loads `/api/announcements/top?urgent=true` on initial page loads. It also resolves backend version, normally from a build-time value, with a runtime `/api/version` fallback. The global notice loader has a 2.5-second timeout (`frontend/src/lib/server/announcements.ts:16`). Client navigation may reuse the layout rather than loading it again.

### Page-specific dependencies and decisions

- `/`: five reads at `frontend/src/routes/+page.server.ts:70`: `/api/notices/recent`, `/api/notices/keywords?limit=8`, `/api/stats`, `/api/discussions/threads?limit=5&status=open`, and `/api/announcements/top`; plus shared layout. **Enabled 120-second HTML caching.** This is the largest fan-out saved per document HIT. Recent discussions and urgent notices in this document can also lag by the edge lifetime.
- `/notices`: `/api/notices/archive` with pagination, searchMode, search/proposer/date/lifecycle filters, and optional digest notice numbers (`frontend/src/routes/notices/+page.server.ts:109`). The backend joins cached active notices with archive queries (`backend/src/modules/crawling/notices-query.service.ts`). Auto/semantic searches also involve the semantic sidecar and query embedding. **Left uncached**: the current explicit `private, no-cache` policy preserves per-request random example-query chips, documented in `frontend/src/lib/server/ssr-cache-policy.ts:1`. This page remains a high-value candidate after separating the random examples from cacheable content.
- `/notices/semantic-search`: `/api/notices/semantic-search` only when a query is present; browser also reads `/api/notices/semantic-search/health`. **Left uncached** for the same random-example policy and high query cardinality.
- `/notices/[num]`: parallel `/api/notices/:num/detail?rev=...`, `/api/notices/:num/changes`, and `/api/notices/:num/discussions` at `frontend/src/routes/notices/[num]/+page.server.ts:71`; plus shared layout. **Enabled 120-second HTML caching.** Detail reconstructs revision/archive data; changes read the diffchain; discussions read the DB and enforce a read rate limit. `rev` remains part of the full query cache key. The initial discussion list may lag, while its refresh remains uncached.
- `/notices/changes`: `/api/notices/changes` and `/api/notices/changes/summary`; digest jumping can add discovery and anchor reads (`frontend/src/routes/notices/changes/+page.server.ts:133`, `:154`, `:179`, `:197`). **Left uncached** in this conservative first pass. It could use a separate 30-120 second policy once the digest redirect/query variants are explicitly verified.
- `/proposals`: `/api/stats/proposals?granularity=...&startDate=...&endDate=...`. **Enabled 120-second HTML caching.** Its backend aggregation already has a 5-minute cache (`backend/src/modules/notice/proposal-statistics.service.ts:31`), but a document HIT additionally avoids SSR and the network/API read.
- `/crawling-transparency`: `/api/crawling-transparency`. **Enabled 120-second HTML caching.** The backend already caches its multi-aggregation result for 5 minutes (`backend/src/modules/health/runtime-stats.service.ts:126`).
- `/announcements` and `/announcements/[id]`: `/api/announcements`, with detail selecting one item and lexing its Markdown on the server (`frontend/src/routes/announcements/[id]/+page.server.ts:23`). **Enabled 120-second HTML caching.** The backend Notion list has a default 60-second cache with stale refresh (`backend/src/modules/admin-notices/admin-notices.constants.ts:49`); its environment can override this.
- `/license`: `/api/packages`, plus build-time frontend package metadata and shared layout. **Changed from long-lived caching to 120 seconds.** This prevents package/version/banner HTML from remaining pinned after releases.
- `/webhook`: shared layout; interactive push/webhook operations occur through client APIs. **Changed the page shell to 120 seconds.** Subscription state and mutation endpoints remain uncached.
- `/status`: `/api/stats`, including runtime, crawler and health data. **Left uncached** so an operator's refresh remains useful.
- `/discussions`: `/api/discussions/threads` with status/page filters. `/notices/[num]/discussions/[threadId]`: detail and `/api/discussions/threads/:threadId`. **Left uncached**, including comments and post-write refreshes.
- `/sitemap.xml`: existing origin `public, max-age=3600, s-maxage=3600` remains unchanged.
- `/notices/[num]/og.png`: SSR image generation reads detail and runs the image renderer. `/api/notices/:num/screenshot`: serves an archived image. **Enabled 120-second caching for successful image responses**, replacing their membership in the old month/year rule.

### API groups that must remain separate

- Public reads: notices recent/keywords/archive/search/detail/changes/summary, proposal statistics, announcements/top/list, version/packages, and transparency. Their backend work ranges from cache reads to archive/diffchain reconstruction, SQL aggregation, and semantic inference.
- Operational reads: stats, health, batch/status, redis/status/connection, webhook diagnostics, and semantic health. No new shared caching was applied.
- User-specific reads: `/api/push/subscriptions/notice-status` and `/api/push/subscriptions/discussions/:threadId/status`; the latter depends on both endpoint and visitor-derived author identity (`backend/src/controllers/api.controller.ts:111`). Never place these behind a broad `/api/*` cache rule.
- Mutations: webhook registration, push subscription registration/deletion/preferences/binding, discussion/thread/comment creation/update/deletion. No POST/PATCH/DELETE matching was added.
- `/api/notices/:num/export` emits `no-store` (`backend/src/controllers/api.controller.ts:502`) and remains outside the allowlist.

## Dashboard changes applied

### Previous state

The existing rule named `LawCast` combined hashed assets, `/webhook`, `/license`, notice screenshots, and dynamic OG images. It forced a one-month edge TTL and a one-year browser TTL. Baseline `/webhook` had `Age: 105307` and `Cache-Control: max-age=31536000`; it was already serving day-old HTML. OG images also advertised a one-year browser TTL.

The zone-wide Browser Cache TTL is one month. It was not changed because the zone serves unrelated applications. Cache Response Rules now provide explicit `max-age=0` on the scoped fresh public responses.

### Final rules

1. Renamed the original rule to `LawCast immutable assets` and restricted it to host `law.viento.me` with path prefix `/_app/immutable/`. Its month edge/year browser policy remains appropriate for content-hashed build assets.
2. Created `LawCast public pages - short cache`: the public page/image allowlist above, host `law.viento.me`, GET/HEAD only, no nonempty Authorization header, and a global exclusion for paths ending `/__data.json`. Cache eligibility is enabled; Edge TTL respects response cache-control and bypasses when absent. Default query-string keys are retained.
3. Created `LawCast public responses - 120 seconds`: the same request expression, response status 200 only, no nonempty Set-Cookie response header. It adds `public`, `max-age=0`, and `s-maxage=120`. The Cloudflare-only switches are off, so clients can see the policy. No cookie headers were stripped and no private response policy was removed.

The dashboard showed six active Cache Rules and one active Cache Response Rule. Four unrelated application rules were left unchanged.

Official basis: [Cache Response Rules](https://developers.cloudflare.com/cache/how-to/cache-response-rules/) operate before the cache decision and can set cache directives. This permits the short shared lifetime without using the Free plan's ordinary Edge TTL override minimum of two hours ([TTL documentation](https://developers.cloudflare.com/cache/how-to/edge-browser-cache-ttl/)).

### Existing objects required purging

**HIGH**: rule changes did not retroactively rewrite cached response metadata. The first after-pass still returned old `/webhook`, `/license`, and OG cache objects with month browser headers. A scoped prefix purge was then applied to:

- `law.viento.me/webhook`
- `law.viento.me/license`
- `law.viento.me/notices`
- `law.viento.me/api/notices`

This excluded hashed asset paths and other hosts. Subsequent `/webhook` and `/license` requests returned MISS then HIT with `max-age=0, s-maxage=120, public`. This purge cannot remove an old response already held in an end user's browser under the previous one-year policy.

## Measured results

### Method

Small sequential public GET samples with curl, compression enabled, no authenticated session, one client location, KIX edge. Initial baseline: 3 requests per URL. Stable comparison: up to 5 follow-up requests per selected URL; report HIT durations separately from MISS. This is a functional experiment, not a load test or production traffic estimate.

Use **full response completion time**, not just curl TTFB: SvelteKit sends HTTP 103 Early Hints, so `time_starttransfer` can precede the final body and understate SSR work. The raw records keep both fields.

### Full response completion medians

- Home: baseline 407.22 ms (n=3) -> HIT 168.45 ms (n=5), 58.6% lower.
- Notice 2221944: 241.22 ms (n=3) -> HIT 163.375 ms (n=4), 32.3% lower.
- Proposals: 362.11 ms (n=3) -> HIT 166.76 ms (n=5), 53.9% lower.
- Transparency: 215.15 ms (n=3) -> HIT 171.95 ms (n=5), 20.1% lower.
- Announcements: 242.63 ms (n=3) -> HIT 169.12 ms (n=5), 30.3% lower.

In the 25-request stable set, 24 were HIT and one notice request was MISS following the scoped purge. Thus 24/25 document renders were avoided in this deliberately repetitive sample. Do not interpret 96% as a real-user cache hit rate or a measured CPU reduction.

One initial post-change home MISS took 10.23 seconds, and uncached notices briefly took 7-12 seconds before recovering. These outliers are retained in the initial after records, not hidden in HIT medians. The cause of that transient origin slowness was not established. Page caching protects repeated requests after fill; it does not fix a slow cold origin. The slow home fill also had a smaller body, consistent with a tolerated loader fallback; the exact fallback was not proven.

### Boundary checks

- Daily and monthly proposal query URLs independently transitioned MISS -> HIT. Their response sizes differed (71,284 vs 39,637 bytes); a separate SSR payload read confirmed `statistics:{granularity:"monthly"...}` on the monthly URL.
- `?rev=1` independently transitioned MISS -> HIT; the unversioned URL is a separate key.
- `?rev=0` returned 400 BYPASS twice; an unknown notice returned 404 BYPASS twice.
- `/notices/__data.json` remained DYNAMIC with `private, no-cache`; notice-detail `/__data.json` remained DYNAMIC with `private, no-store`.
- `/discussions`, `/status`, and `/api/push/subscriptions/notice-status` stayed DYNAMIC.
- Requests to an otherwise cacheable `/proposals` carrying a synthetic non-secret Authorization header stayed DYNAMIC twice.
- Browser rendering of notice 2221944 succeeded; its discussion refresh button worked and captured browser error/warning logs were empty.
- TTL expiry was checked separately on an isolated proposal URL; see the final TTL evidence appended below.

## Remaining opportunities and limits

- **Highest next opportunity**: make `/notices` HTML cacheable for 30-120 seconds after moving its random example chips to a separate client-only draw or explicitly accepting a shared short-lived draw. Preserve query keys; never ignore all query parameters because search, pagination, digest, dates, and revision change content.
- Search-result reuse should be bounded by TTL, key count, and query cardinality. A backend result cache can also benefit SSR fetches and SPA loads; frontend proxy caching alone cannot be assumed to do so.
- All `/__data.json` traffic intentionally remains live. Document caching mainly benefits direct visits, reloads, and crawlers; it does not claim to eliminate SPA navigation work.
- Edge lifetime adds to existing data staleness: proposal/transparency data may already be up to 5 minutes old before another 2 minutes at the edge. Notion uses stale refresh and an environment-specific TTL, so an absolute freshness bound is not implied.
- An HTTP 200 page containing a tolerated loader error can still be cached for 120 seconds. A future source change should mark degraded loader responses `no-store` or use non-200 status where semantically appropriate. Response-status filtering alone cannot inspect SvelteKit's embedded `loadError` state.
- Future introduction of sessions, server-side cookie preferences, or visitor-specific HTML requires revisiting the allowlist before deployment. Current inspected loaders do not read cookies/locals for personalization; all Authorization-bearing requests are excluded.
- Cache purge on content release should target these public HTML paths if immediate visibility is required; otherwise the new edge lifetime is 120 seconds. Previously browser-cached one-year responses are outside CDN purge control.
- No source change was made, so application builds, unit tests, and version/release workflows were not run. Validation here is the real HTTP experiment and browser interaction. Root notes remain uncommitted on a dedicated feature branch.

## Final TTL expiry evidence

- Isolated URL: `/proposals?cache_validation=20261018-ttl`.
- Cold: MISS, no Age, 227.00 ms. Immediate repeat: HIT, Age 0, 183.99 ms.
- After 65 seconds: HIT, Age 65, 170.94 ms.
- After 125 seconds: EXPIRED, no Age, 308.15 ms; the origin was fetched again.
- All four responses were HTTP 200 and advertised `max-age=0, s-maxage=120, public`.

## Reproduce a cache check

```bash
curl -sS --compressed -D - -o /dev/null -w "total=%{time_total}\n" https://law.viento.me/proposals
```

Repeat with the exact same URL to observe HIT and Age; use separate daily/monthly query URLs when checking query isolation. These samples were GET requests, not HEAD-only probes.

## Migration to a regular Cache Rule (2026-10-18 JST)

The user subsequently requested moving the active response rule into ordinary Cache Rules and removing the original response rule. This section supersedes the response-rule-based configuration above.

### Replacement configuration

- Updated the existing regular rule in place (ID `be60b4d038f34dbda98de7034e9f672d`), renamed to `LawCast public pages - 120 seconds`. Its host, page/image allowlist, GET/HEAD restriction, Authorization exclusion, SPA data exclusion, and full query-string cache keys were preserved.
- Edge TTL base mode: respect response cache-control and bypass if absent (`bypass_by_default`).
- Status-code TTL: **200 -> 120 seconds**, **>=201 -> No store**. The response-status condition is now expressed through TTL policy instead of a response-phase filter.
- Browser TTL: **Bypass cache**, yielding `Cache-Control: no-store` to clients for the tested HTML documents, while the explicit edge status-code TTL still produces CDN HITs. This is stronger browser storage avoidance than the previous `max-age=0` policy. OG responses retain origin `public, max-age=300` alongside `no-store`; browsers must honor the restrictive no-store directive.
- The dashboard accepted and persisted **2 minutes** as a custom status-code TTL even on this Free zone. The documented minimum for the ordinary default Edge TTL must not be assumed to prohibit this verified status-code setting. This corrects the earlier assumption that a response rule was necessary to achieve 120 seconds here.
- The zone-wide Browser Cache TTL and unrelated rules were left unchanged. At the start of this migration the dashboard had 5 regular rules (the user had removed an unrelated rule since the earlier session), not the earlier 6.

### Differences that cannot be copied literally

Regular Cache Rules cannot match response headers or directly add `public`/`s-maxage` response directives. The original response-only `Set-Cookie` filter is therefore not part of the replacement expression. Current inspected public loaders do not produce visitor-specific HTML, and all migration probes returned no Set-Cookie. The replacement remains tightly restricted to those public paths and excludes Authorization requests.

**HIGH**: if a future implementation adds sessions or Set-Cookie responses to an allowlisted page, reassess the rule before shipping that implementation. Cloudflare documents that an explicit status-code TTL can strip Set-Cookie and cache the response; do not assume the old response-header guard survived migration. See [Cloudflare cookie behavior](https://developers.cloudflare.com/cache/concepts/cache-behavior/) and [dynamic-content troubleshooting](https://developers.cloudflare.com/cache/troubleshooting/dynamic-content-and-login-issues/).

### Independent replacement verification

The original response rule was disabled before these requests, so its directives could not account for the observed new cold-cache fills. Unique query URLs were used to avoid treating old cached metadata as proof of the replacement.

- 27 sequential GET probes covered home, proposals, monthly proposals, notice detail, webhook, license, OG image, search listing, both SvelteKit data routes, subscription status, invalid revision, missing notice, and Authorization bypass.
- Seven public page/image variants transitioned MISS/EXPIRED -> HIT with the original response rule disabled.
- Daily/default and monthly query variants filled independent cache keys.
- Search listing and SPA data stayed DYNAMIC; subscription and Authorization requests stayed DYNAMIC.
- Invalid revision 400 and missing notice 404 stayed BYPASS on both repeats.
- Raw evidence: [cache-rule-migration-measurements.jsonl](cache-rule-migration-measurements.jsonl).
- Independent TTL test with the response rule disabled: cold MISS -> immediate HIT (Age 0) -> HIT after 65 seconds (Age 65) -> EXPIRED after 125 seconds. All responses were HTTP 200 and advertised browser `no-store`.
- After this successful independent test, removed `LawCast public responses - 120 seconds` (ID `ed61b034e9d44a39998711d668e7dc16`) from the dashboard.
- Final UI: **5 active regular Cache Rules**, replacement `LawCast public pages - 120 seconds` Active; **0 active Cache Response Rules** and `No Cache Response Rules created`.
- Restoration reference: [response-rule-before-migration.json](response-rule-before-migration.json). No application code or deployment pointer was changed during migration.


## Privacy review and bypass hardening (2026-10-18 JST)

This section supersedes the migration's final rule count and request exclusions. Review scope: frontend `583df08` (v1.19.4), backend `7e2117f` (v1.18.2), and the deployed public HTTP behavior.

### Source findings

- No allowlisted SSR loader was found using cookies, locals, authorization, or a requester identity to personalize HTML. No application Set-Cookie/session producer was found in the reviewed source. This is a scoped finding, not a guarantee for future releases.
- Public loaders expose notice data, aggregate statistics, public discussion summaries, and published announcements. Backend `discussions.service.ts:142` and `:164` sanitize comments/threads; requester-independent list methods are at `:204` and `:237`. Public nicknames and masked IP values are intentional public fields; raw author IDs/passwords are excluded.
- Backend `api.controller.ts:111` push binding status and `:134` notice subscription status depend on requester/endpoint information and must remain uncached. Notion publication filtering is in `admin-notices.service.ts:319` and `:442`.
- Frontend SSR forwarding in `src/lib/server/client-ip.ts` and `src/hooks.server.ts` can forward request context. Although currently used for rate limiting rather than personalized public HTML, it makes future personalization a reason to reassess caching.
- Browser consent storage (`src/lib/utils/gtm-bootstrap.ts:9`) is client-side and does not personalize SSR documents.
- No current cross-user private-data disclosure was confirmed. Before hardening, a synthetic session-cookie request did reuse the public proposal cache (HIT), establishing the missing request guard, not a private-payload leak.

### Applied production configuration

- Added an empty-Cookie requirement to `LawCast public pages - 120 seconds`, alongside its existing Authorization exclusion.
- Added **LawCast private requests - bypass cache**, ID `335a264844564074bdd59a678400bcd3`, as the final rule, after the public-page rule. Actions: cache eligibility Bypass; Browser TTL Bypass.
- The final rule bypasses every nonempty Cookie or Authorization header; methods other than GET/HEAD; SvelteKit `__data.json`; API paths except the public screenshot endpoint; notice search/change/semantic-search pages; status and discussion routes.
- Hashed `/_app/immutable/` assets are excluded from this additional bypass so analytics cookies do not disable static-asset caching. The host is limited to `law.viento.me`.
- **Tradeoff:** even `_ga` cookies cause document bypass. Returning visitors therefore receive less HTML cache reuse, avoiding assumptions about future cookie names.
- Final saved dashboard state: **6 active regular Cache Rules, 0 Cache Response Rules**. Anonymous public HTML retains the 120-second status-code TTL. Exact expressions: [private-request-bypass.json](private-request-bypass.json).

### Independent privacy probes

Evidence: [cache-privacy-measurements.jsonl](cache-privacy-measurements.jsonl), 3 before and 31 after requests. All credential values were synthetic and non-secret.

- Warm anonymous proposal cache: anonymous EXPIRED -> HIT; synthetic session A/session B, analytics-only, Authorization-only, and combined cookie requests all returned DYNAMIC twice each, without Age.
- Cold URL: cookie A and cookie B returned DYNAMIC; the subsequent first anonymous request was MISS, followed by HIT. Cookie requests neither consumed the anonymous entry nor populated it.
- Anonymous notice detail remained MISS -> HIT; the same detail with a session cookie returned DYNAMIC.
- Subscription status, SPA data, notice listing, discussions, and status remained DYNAMIC. Missing notice 404 remained BYPASS twice.
- All probes returned no Set-Cookie. No real credentials or private user data were collected.
- Browser TTL Bypass is configured, but DYNAMIC cookie/authorization responses in this experiment did not consistently receive a Cache-Control header. Do not infer client-side `no-store` from the CDN bypass result. Anonymous cached HTML did advertise `no-store`.

### Residual limit

**HIGH, conditional future risk:** request-cookie bypass cannot detect the first anonymous response that newly creates a session. Cloudflare documents that explicit edge/status-code TTL can strip Set-Cookie and cache the response. Therefore the new request guard is not equivalent to the removed response-header guard. Before introducing sessions, Set-Cookie, or per-visitor SSR on an allowlisted route, remove that route from eligibility or implement response-aware cache protection and revalidate. Current source and probes do not demonstrate an exploitable private-response leak.

References: [Cloudflare Set-Cookie behavior](https://developers.cloudflare.com/cache/concepts/cache-behavior/), [cookie bypass example](https://developers.cloudflare.com/cache/how-to/cache-rules/examples/bypass-cache-on-cookie/).

No application source, dependency, release, or deployment pointer was changed. Verification consisted of saved dashboard settings and real HTTP GET probes; application build/tests were not applicable.
