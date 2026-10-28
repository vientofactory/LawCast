# Postdeployment SSR and Browser Delivery Verification

## Verdict and scope

**Partial remediation, not proof that every bottleneck is resolved.** After backend 1.19.4 deployment, all 36 new production Lighthouse navigations passed the individual LCP <=2500 ms, TBT <=200 ms and CLS <=0.1 lab budgets. Fourteen Playwright cases passed. However, independent external API samples still reproduced transient multi-second response waits, and the origin still exhibited intermittent subsecond delays on its trivial version endpoint. These observations must not be discarded because the browser runs passed.

Measurements were taken on 2026-10-28 JST against `https://law.viento.me` and `https://lawcast-backend.viento.me`. The Cloudflare connector confirmed frontend production deployment `68d912a6-2c19-43d1-a301-089c02f4c52e`, main SHA `5888b7d501fc99f5aed4b167585fcb3c4b49b56d`, successful frontend 1.25.3. Backend 1.19.4 was already deployed before this investigation. No production code, data, container, cache, security rule, analytics setting or configuration was changed during this verification. Tests used public GET requests and read-only SSH observations; UI interactions changed only isolated browser-context theme state.

The Web Perf skill was inspected, but Chrome DevTools MCP was unavailable. Its MCP workflow could not run; existing Lighthouse CLI/trace tooling and Playwright were used instead. Cloudflare and Postman API Engineer/testing guidance informed the read-only checks. Browser measurements ran sequentially, with no concurrent Lighthouse or Playwright browser processes. Low-volume HTTP probes and read-only server observations were additional diagnostic activity.

## Browser evidence

[All Lighthouse summaries](lighthouse-summary.json) preserve each observation, score, document timing, Cloudflare cache state and failed audit. Lighthouse 13.6.0 and Chrome 156 were used. Raw HTML/JSON reports and matching DevTools logs/compositor traces remain in ignored `frontend/lighthouse-reports/backend-1.19.4-{stock,devtools,fresh-ssr,desktop}/`.

- **Stock simulated mobile, 15 navigations:** home, status, notices, changes and license, three each. Modeled LCP 792–1451 ms; directly observed LCP 336–1642 ms; maximum TBT 29 ms; maximum CLS 0.003071. Performance 99–100. No individual budget failure.
- **Actual DevTools-throttled mobile, nine navigations:** home, status and license, three each. LCP 2189–2383 ms, TBT <=62.682 ms, CLS <=0.000027085. Performance 95–96. These use the explicitly labeled `render-document` diagnostic browser profile from session 55; they are not stock PSI scores and must not be compared directly with simulated values as a website speedup.
- **Fresh SSR under actual mobile throttling, six navigations:** each URL received a unique `__vitals_probe` query parameter. All three home documents were verified `MISS`; all three status documents were `DYNAMIC`. Home LCP 2301–2371 ms; status LCP 2339–2401 ms. TBT <=76.389 ms; CLS <=0.000027085. Performance 94–96. This specifically prevents a cached home HTML response from standing in for an executed SSR load.
- **Stock simulated desktop, six navigations:** home and status, three each. Modeled LCP 271–323 ms, observed LCP 358–667 ms, TBT 0, CLS <=0.018335. Performance 100.

The fresh-SSR runs had document server-response audit values 163–175 ms, while end-to-end navigation TTFB was 349–441 ms. The latter includes preceding connection/network work and must not be equated with backend execution time. Cloudflare reported `cfEdge` 5–26 ms and `cfOrigin` 64–107 ms; these are provider-defined timings, not independently instrumented SvelteKit loader or per-API spans. No `cfWorker` or application per-dependency span was available. They cannot be subtracted to derive exact SSR CPU time.

In those actual mobile runs, LCP was the server-rendered hero heading. The reported element-render-delay component was 1929–2007 ms; that category includes resource delivery and rendering and is **not two seconds of JavaScript CPU**. In the slowest status example, the main stylesheet transferred 17120 bytes (93079 decoded), finished at 2312.925 ms, and LCP followed at 2400.677 ms. Lighthouse estimated zero LCP savings for its render-blocking and unused-code diagnostics. This evidence does not justify an unmeasured CSS or hydration rewrite.

[Playwright evidence](browser-check.json) and the [read-only reproduction harness](browser-check.mjs) cover 12 fresh contexts: desktop/mobile × home/status/notices × two runs. Every home was `MISS`; status/notices were `DYNAMIC`. Assertions verified HTTP 200, visible heading, frontend 1.25.3 footer, initialized real status data and nonzero home archive count. Real theme changes completed, with no uncaught page errors. Native observed LCP was 384–784 ms. Recorded interaction-event durations were <=80 ms; these samples do **not** establish field INP.

Home/status issued no browser `/api/` fetches during initial loading; their data arrived via SSR. The notices page additionally requested semantic engine status. Two separate tests held hydration/GTM script requests pending: home and status still painted their SSR headings at 580/368 ms while `loadEventEnd` remained zero, with 23/26 requests pending. Those intentionally blocked-script tests are isolated causality checks, not the unmodified-page Lighthouse results.

## API path and origin evidence

[HTTP-path evidence](http-paths.json) contains 45 sequential curl reads (five rounds, reversed order on alternating rounds), retaining HTTP status, DNS/connect/TLS/TTFB/total, payload size, cache information and Cloudflare Ray IDs. All returned HTTP 200 and all API envelopes reported success.

- Home/status/license HTML TTFB medians were 279.5/352.9/446.5 ms. Home and license can be edge-cached; these are not all fresh SSR observations.
- Frontend `/api/stats` TTFB: **4314, 5076, 4888, 352, 435 ms**.
- Backend external `/api/stats` TTFB: **5799, 5813, 3389, 702, 585 ms**.
- Six of the ten stats reads exceeded one second. Two discussions-list reads also took 3459/4308 ms. Across the entire series, 8/45 reads exceeded one second. Later fast responses do not erase these observations.
- TLS setup for the slow stats reads was 164–476 ms; most of the delay occurred after TLS establishment. This excludes DNS/TLS setup as the sole explanation. Because the direct backend hostname also delayed, a frontend-SSR-only explanation is insufficient.

The slow external reads lacked per-dependency server timings and were not accompanied by simultaneous origin samples. Their exact split among backend work/queueing, upstream network and Cloudflare is **unresolved**. They do not prove a 3–6 second original-backend handler, a Cloudflare-only defect, a failing Ollama probe, or a slow rendered page. Browser page tests did not coincide with every slow API sample.

[Origin series](origin-series.json) subsequently measured 24 alternating version/stats pairs through `127.0.0.1:3001`: stats median **25.595 ms**, range **20.296–155.626 ms**; version median **3.582 ms**, maximum **468.296 ms**, with three version observations above 250 ms. Ollama health stayed healthy and its two recorded refreshes took 4/5 ms. Warm stats improvement is consistent with the previous release's 79.5→26.0 ms observation, but the samples are not a controlled before/after workload.

[Additional correlated server-side probes](correlated-origin-edge.json) measured eight rounds. Origin stats median 31.88 ms/max 698.404 ms and version median 6.354 ms/max 543.764 ms. Existing Node event-loop telemetry reported window maxima of 266–351 ms; Ollama health latency was 6 ms. A single `docker stats` sample reported backend CPU 23.24%, memory 1.765 GiB. This is evidence of remaining shared process scheduling delay, not proof that a specific crawler or SQL query caused the earlier multi-second external waits.

The two external controls requested **from the server** in that last series returned 403 and were excluded from performance comparisons: Cloudflare bot policy treated that source/client differently. They are explicitly failed controls, not fast successful API samples. No bot protection was disabled. Existing nginx access logs lack request/upstream duration fields, so they cannot retroactively resolve the earlier Ray-ID samples.

## SSR contract and remaining limits

- `frontend/src/routes/+page.server.ts` awaits recent notices, keywords, stats, discussions and pinned notice through `Promise.all`; its critical path is the slowest awaited dependency. The layout separately awaits the urgent notice. A warm stats improvement does not cap all these dependencies.
- `frontend/src/routes/status/+page.server.ts` awaits stats before returning its server data.
- `frontend/src/hooks.server.ts` forwards server-side API requests to the backend; `src/routes/api/[...path]/+server.ts` serves browser/API proxy requests. The proxy probes approximate this external path but are not instrumented timings of the internal SSR `handleFetch` invocation.
- `backend/src/modules/health/runtime-stats.service.ts` still aggregates several DB/service reads. `getComparableChangeSummary()` performs two awaited count queries. The cache snapshot and Ollama deadline change do not impose a deadline on this entire aggregation.
- The independent 2000 ms Ollama health timeout bounds that upstream request, not all SSR work; JavaScript event-loop blocking can also delay timer delivery. Generation timeout remains 1800000 ms, as verified after deployment in session 56.
- Real-user p75 LCP/INP/CLS, other regions/devices, high concurrency, a cold Notion refresh and unhealthy Ollama during live SSR were not established by this small lab sample. No production fault injection was performed.
- Existing vendor-script best-practice deductions remain (stock Best Practices 81). They were not treated as proof of the measured API waits. Status SEO 69 includes its existing indexing policy; this task did not change it.

## Next diagnostic step

To attribute a future tail precisely, correlate one request across `handleFetch`, the backend stats aggregator's individual dependencies, DB queue time and event-loop telemetry, with request IDs and bounded per-stage timing. Existing Cloudflare timing and current nginx logs do not provide those spans. Investigate shared origin stalls alongside the slow external stats/discussions responses before choosing another optimization. The evidence supports an ordinary-page lab pass and a warm stats improvement, while **an all-path, all-tail, real-user Web Vitals pass remains unproven**.

References: [Web Vitals definitions and field p75](https://web.dev/articles/vitals), [Cloudflare Server-Timing semantics](https://developers.cloudflare.com/changelog/post/2026-02-18-cfworker-server-timing/), [previous browser-profile investigation](../55-lcp-outlier-diagnostics/investigation.md), [backend cache/deadline release](../56-local-stats-bottlenecks/verification.md).


## Follow-up attribution

[Session 58](../58-api-tail-db-queue/verification.md) subsequently matched external requests to passive origin ingress/egress timestamps and reproduced a retry-candidate SQL queue bottleneck locally. That new evidence resolves the main ambiguity above for the newly reproduced requests; it does not retroactively provide per-request spans for every earlier sample.
