# Backend 1.19.5 Release and Production Bottleneck Verification

## Final verdict

**Deployment and CI succeeded; the retry-candidate SQL improvement is verified, but end-to-end production API latency is only partially remediated.** Do not mark the entire backend bottleneck resolved. During the postdeployment pending-sync workload, new matched external/origin measurements still reproduced multi-second stats/discussion responses and event-loop stalls.

## Release integrity and final local checks

- Backend [PR #223](https://github.com/vientofactory/LawCast-Backend/pull/223), signed implementation `adde45abf3ec93d88a8b3838e175b72296dd3464`, squash release SHA `b3f9aa9af898dd80093fff5d1bafe2eff6964980`.
- [backend-v1.19.5](https://github.com/vientofactory/LawCast-Backend/releases/tag/backend-v1.19.5) targets that exact merge. Backend `dev` was fast-forwarded and pushed to the same SHA. Full npm install synchronized version-only lockfile changes and left the post-merge lockfile clean.
- Signed root release commit `ce5838b7aa83f2a18ab5b1f97977389093614d03` records that backend gitlink. Frontend remains `5888b7d501fc99f5aed4b167585fcb3c4b49b56d` on dev; semantic-search remains `8438508b61d42b7b5586633ac1af43ac4d71cff8` on main.
- Backend lint/type/build and **85 Jest suites / 1256 tests** passed before commit, normal process exit. Frontend lint/check passed. Sidecar lint/format and capability integrity passed. Its unchanged real-model concurrency timing test failed once in the initial full run (344 passed), then the complete isolated rerun passed **345/345** in 57.26 seconds without relaxing thresholds.
- The final [local causal comparison](release-local-http-benchmark.json) again produced identical ordered candidates: old-query DB-backed HTTP requests 14465 ms; patched 42 ms initially, then 20–21 ms. These are representative local handlers, not a complete production application benchmark.

## CI and actual deployment

[Root CI / deployment run 40655224025](https://github.com/vientofactory/LawCast/actions/runs/40655224025) completed successfully. Both Node 22.23.4 and 24.22.1 backend lint/type/build/test jobs passed; both frontend builds, sidecar checks, and CI gate passed. The backend deploy job rebuilt the container with `APP_VERSION=1.19.5` and reported healthy at `2026-10-28T08:18:14Z`. The semantic-search job returned early because it had no actual service changes.

Seven Postman assertions passed through the backend external version/health endpoints and frontend stats proxy: HTTP 200, actual backend 1.19.5, initialized bounded cache and AI enabled/configured. The existing frontend release was not redeployed.

## Native production query verification

[Native result](release-1.19.5/production-query.json) comes from a separate process in the deployed backend container, using its real helper, TypeORM, sqlite3 **3.52.0** and Node **24.22.1**. The operational DB was opened **OPEN_READONLY**, with migrations/synchronization disabled; no application module, scheduler or crawler was started by this diagnostic.

- Full candidate/helper calls: **312.555, 147.666, 163.196 ms**.
- The real production query plan passed both notice/event-scoped lookup guards, using existing indexes. No global field-path-first detail scan remained in this query.
- Package version was 1.19.5. Summary generation timeout remained **1800000 ms**; independent Ollama health timeout remained **2000 ms**.

The first attempt at this independent diagnostic encountered a Node stdin lexical-name collision before DataSource initialization. The script variable was renamed, and the successful results above are the actual validation. The running application was unaffected.

This proves the deployed query and driver use the intended plan. It does not by itself measure the live application's shared connection under every workload.

## Correlated live workload: remaining failure

A bounded four-minute passive capture started at server epoch `1793175822.200296` (2026-10-28 08:23:42 UTC) and covered the natural 08:24 proposal-reason cron window. As in the earlier diagnostic, only unique `__lc_probe=lc195-...` request IDs were retained, with selected timing/status/health metadata. No raw pcap or unrelated/authentication header content was saved. [Origin events](release-1.19.5/origin-events.jsonl) report **1674 packets captured, zero kernel drops, no capture errors**; the observer terminated cleanly.

[All 68 matched requests](release-1.19.5/matched-requests.json) completed with HTTP 200 and matching origin ingress/egress. There were no client timeouts in this series, but **11/68 external TTFBs exceeded one second**. This is not an all-latency pass:

- Direct backend stats, 17 reads: external median/max **583.801 / 5579.966 ms**; matching origin median/max **64.099 / 5305.394 ms**.
- Frontend stats proxy, 17 reads: external median/max **587.019 / 6093.534 ms**; matching origin median/max **29.025 / 5573.686 ms**.
- Direct backend version, 17 reads: external median/max **445.010 / 714.358 ms**; origin median/max **1.751 / 6.588 ms**.
- Frontend discussions proxy, 17 reads: external median/max **533.057 / 4640.227 ms**; origin median/max **5.816 / 4111.782 ms**.
- Independent origin stats controls, 34 reads: median **32.493 ms**, maximum **7272.018 ms**. Origin version controls, 101 reads: median **3.693 ms**, maximum **2127.550 ms**.
- The 34 independent read-only three-count DB probes remained quick: median **21.783 ms**, maximum **31.452 ms**. They do not indicate a global SQLite reader lock.

For example, direct backend request `lc195-external-0bda4a3bbf1541` spent **5579.966 ms externally and 5305.394 ms inside the origin**. The cached Ollama metric for that response came from a 5 ms check before the request. Later matched responses still had origin waits of 3–5 seconds. These samples do not support a Cloudflare-dominant explanation.

[Existing cron logs](release-1.19.5/cron-observation.txt) explicitly show that the minute-24 proposal-reason drain and summary-backfill cron **skipped** because `pending sync` was write-heavy. Therefore this series must not be claimed as a successful natural retry-candidate cron run. The direct read-only native helper validation above is the query-specific production evidence.

[Write-phase logs](release-1.19.5/write-phase-log.txt) place pending sync at NSM page 163/163 at **08:24:11.552Z**, overlapping the onset of the new stalls. Returned Node telemetry reported event-loop maxima around **1.8–2.3 seconds**, and DB-free origin version probes also stalled intermittently. Later in the same observation, requests returned to subsecond external latency as the workload moved on to summary apply batches.

This separates the observed remaining pending-sync/application scheduling contention from the corrected retry-candidate plan. **The exact remaining synchronous function, query and queue composition were not profiled in this release.** The temporal association and event-loop signal are diagnostic evidence, not a claim that every pending-sync statement is slow or that one specific uninstrumented method is proven responsible.

## SSR and browser verification

[Six actual-throttled mobile Lighthouse observations](release-1.19.5/lighthouse-summary.json) used the explicitly labeled `render-document` diagnostic profile, fresh Chrome processes, unique cache-busting HTML URLs and retained traces/network logs. Home was `MISS` on all three runs; status was `DYNAMIC` on all three.

- Home LCP **2541.585 / 2306.846 / 2212 ms**, median **2306.846 ms**. The first sample failed the 2500 ms individual budget; the strict command correctly exited 1 and was not repeated until green.
- Status LCP **2333 / 2386.562 / 2440.951 ms**, all within 2500 ms. Maximum TBT across the series was **128.531 ms**, CLS zero. These are lab observations, not field p75 or INP guarantees.
- The 2541.585 ms home sample had document server-response audit **90 ms**, full navigation TTFB **341.058 ms** and element-render-delay **2200.527 ms**. The main CSS finished at **2406.034 ms**. Lighthouse estimated zero LCP savings for its render-blocking insight. It is not evidence of a multi-second SSR/API response on that navigation.

[Fourteen Playwright cases](release-1.19.5/browser-check.json) passed independently after the Lighthouse budget failure: twelve real fresh-context SSR loads/interactions and two pending-hydration checks. Visible real SSR data, footer, theme changes and zero uncaught page errors were verified. Native LCP was **424–868 ms**, sampled interaction durations <=80 ms. With hydration/GTM scripts deliberately held, home/status still painted at **508/516 ms** while load remained incomplete. These intentionally blocked-script controls are separate from the unmodified Lighthouse runs.

## What is and is not resolved

The released retry-candidate query no longer uses the demonstrated pathological plan; its local shared-connection reproduction and native production plan/timings confirm that improvement. CI, release integrity and deployed health passed.

However, **the production 3–6-second API tail is still reproducible under another background phase**. The task's production verification therefore yields **partial remediation**, not a complete bottleneck-clear verdict. Keep the candidate-query fix; investigate pending-sync post-scan work, shared DB connection queueing and synchronous event-loop work next, with matched request/phase timing before another optimization or release. Do not disable protection, skip crawler work, or relax performance budgets to manufacture a pass.
