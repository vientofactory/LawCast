# Production Cache Observation After Frontend 3.1.2

## Measurement and unchanged production state

Read-only investigation on 2026-11-13 JST after [release verification](release.md). Raw evidence and reusable probes live in `verification-artifacts/cache-observation/` (ignored); `summary.json` derives every reported percentage and median from saved inputs. No application source, production cache rule, setting, purge, deployment or WAF policy changed. Re-reading the complete request cache ruleset confirmed byte-equivalent objects, version 44, seven rules, original 2026-10-18 modification time. Response cache ruleset version 4 has no rules. Development mode is off, legacy active Page Rules are empty, Rocket Loader remains disabled for LawCast.

Cloudflare GraphQL queries are read-only POST queries, not mutations. They filter `law.viento.me`, `requestSource: eyeball`; strict HTML HIT ratios use HTTP 200 only, home `/` and numeric `/notices/<num>` paths. They exclude data/subroutes and 400/403/404/499 responses. Cookie-bearing successful requests remain in the denominator: this is not an eligible-only HIT ratio. Bots and this session's earlier release-verification traffic are included; this is not a human-only cohort.

## Operating traffic

The 24-hour window is 2026-11-12 00:46 through 2026-11-13 00:46 JST and predominantly precedes the new release. GraphQL adaptive counts are estimates (observed average sample intervals range from 1 to 10); do not label them exact access-log counts. Rounding/sampling across independently grouped queries can differ slightly.

- Home HTTP 200 count estimate: 605; HIT 10 (1.65%), EXPIRED 517, MISS 4, STALE 56, DYNAMIC 18. If STALE is counted as cache-served, 66/605 = 10.91%, distinct from strict fresh HIT.
- Numeric notice-detail HTTP 200 estimate: 280; HIT 3 (1.07%), EXPIRED 55, MISS 219, DYNAMIC 3.
- A separate path/colo aggregation observes 200 distinct numeric detail paths and 52 colos; home is spread over 23 colos. This supports sparse per-key/per-location reuse as a contributor to low effectiveness at 120 seconds; it does not by itself prove a particular TTL's future HIT rate.
- SvelteKit home/notice data reads: 76 HTTP 200 DYNAMIC. Brand requests: 179 DYNAMIC 304, 37 DYNAMIC 200, 3 MISS 200, 9 REVALIDATED 200.
- Matched short windows, 00:06–00:26 and 00:26–00:46 JST: home before 0/5 HIT versus after 2/20 (10%); detail before 0/13 versus after 1/7 (14.29%). The after window starts approximately at deployment, includes old edge objects during expiry and our release tests, and has very small counts. This does not establish a causal release improvement.
- Edge-wide TTFB and request-query dimensions are unavailable to this zone's current GraphQL entitlement. No global production latency percentile, tracking-query share or cookie cohort share is inferred from local timings.

## Direct requests and browser evidence

`python3 verification-artifacts/cache-observation/probe.py` exits 0 with `READONLY HTTP PROBES COMPLETE`. It sends 34 sequential GETs, with a short pause, no load concurrency, no cache-bypass header and no random cache-busting query. Each curl process opens a new connection, so TTFB includes DNS/connect/TLS. Results describe one workstation and KIX, not global users.

- Home: 8/8 HIT, median TTFB 447.99ms, nearest-rank p95 624.88ms; the canonical URL was already warmed by the preliminary read.
- Notice 2222755: 1 MISS then 7 HIT, median TTFB 489.46ms, nearest-rank p95 712.54ms. Warm subset is not an operational HIT ratio.
- Synthetic preference Cookie: home 3/3 DYNAMIC, median 665.20ms; detail 3/3 DYNAMIC, median 623.46ms. Tiny unmatched groups do not establish causal latency savings.
- Two distinct `utm_source` values each produce MISS then HIT: default full-query key fragmentation is confirmed. The actual traffic share is not measured. Keep `rev`, filter and other semantic query values in distinct keys.
- Root/detail `__data.json`: four reads are DYNAMIC. Two invalid-revision reads are HTTP 400 BYPASS with `private, no-store`; error non-storage remains intact.
- Two brand SVG reads are REVALIDATED, not fresh HIT, despite long browser max-age. This is a smaller secondary candidate, not a demonstrated LCP bottleneck.

`node verification-artifacts/cache-observation/browser.mjs` exits 0 with `BROWSER LAB PASS: 6 fresh-context page loads recorded`. Three clean contexts per route, desktop 1365x950, no CPU/network throttle, service workers blocked, five-second observation after load:

- Home median TTFB 553.7ms, observed LCP 956ms, initial CLS 0.
- Detail median TTFB 494.2ms, observed LCP 812ms, initial CLS 0.
- No page errors. These are lab observations, not field p75 Core Web Vitals or interaction INP measurements. Later shifts and mobile performance were not evaluated.

**HIGH: Real Cookie behavior matters more than clean curl repeats.** `node verification-artifacts/cache-observation/cookie-navigation.mjs` exits 0. A fresh home document is HIT without cookies; after five seconds the browser has only `cf_clearance`. A normal reload sends that Cookie and becomes DYNAMIC. A full detail document request is also DYNAMIC. Trusted internal navigation requests `/notices/2222755/__data.json` and is DYNAMIC. Cookie names only were recorded, never values. Cloudflare documents that JavaScript Detections issues `cf_clearance`; do not remove the Cookie or disable bot verification to obtain cache hits.

## Proposed sequence, not applied

1. **Cookie classification first.** For anonymous, public HTML GET/HEAD only, evaluate allowing an empty Cookie set or a set containing solely verified non-personalizing Cloudflare Cookie names (first candidate `cf_clearance`). Unknown/application/session Cookie names, Authorization, private routes and APIs still bypass. Modify BOTH the public HTML eligibility rule's Cookie exclusion and the later private bypass rule; changing only the first is defeated by the later rule. Do not key public HTML by the unique clearance value. Before deployment, test account/session isolation, duplicate/malformed Cookie parsing, cache key equivalence, WAF behavior, error non-storage and final rule precedence. The test proves the candidate, not that every Cookie is harmless or that an arbitrary presence of `cf_clearance` grants authentication.
2. **Split HTML freshness budgets.** Pilot only notice detail HTTP 200 at 600 seconds (120 to 600), then evaluate 1800 if accepted; keep home 120 initially and consider 300 separately. Keep errors/redirects uncacheable and browser no-store. Detail contains mutable history even with a fixed `rev`; whole HTML must not be marked immutable. On releases, pinned-announcement/content corrections, use an explicit tested invalidation policy; CSR urgent revalidation does not make all SSR fields current. Measure per-route/colo HIT, EXPIRED, MISS and origin traffic against agreed freshness budgets for at least 24–48 hours.
3. **Tracking-only key normalization.** Preserve semantic `rev` and invalid-revision separation. Exclude only a reviewed set such as `utm_*`, `gclid`, `fbclid` from the key, after verifying they never change HTML. Cloudflare custom-query selection depends on plan; confirm entitlement before choosing implementation. Do not broadly ignore all queries. Current zone cache level is aggressive (standard query-sensitive behavior).
4. **Preserve data/API bypass.** Do not cache all `__data.json`, discussions, push configuration or urgent-announcement API responses to raise the metric. SPA navigation does not request cached HTML. If data navigation is a material tail, profile/cache only the public backend read model or adopt an explicitly separate public-data contract while preserving live CSR and failures.
5. **Secondary static cleanup.** Review `/brand/v2/*` as versioned but not content-hashed resources. A narrow successful-static rule may avoid repeat revalidation, with a release invalidation strategy; do not apply one-year immutable treatment to mutable filenames, API responses, service workers or version manifests. Global browser TTL is 31 days but the HTML rule overrides it with browser bypass. Existing hashed assets already get one year browser and 31 days edge; this is not the first bottleneck.

## Sources

- [Cloudflare JavaScript Detections](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/javascript-detections/): automatic issuance of `cf_clearance`.
- [Cache Rules settings](https://developers.cloudflare.com/cache/how-to/cache-rules/settings/): status-code TTL override semantics and plan-dependent custom query key controls.
- [Cache response meanings](https://developers.cloudflare.com/cache/concepts/cache-responses/): distinguish HIT, STALE, EXPIRED, DYNAMIC and REVALIDATED.
- [Adaptive confidence intervals](https://developers.cloudflare.com/analytics/graphql-api/features/confidence-intervals/): sampled Analytics estimates versus exact logs.
