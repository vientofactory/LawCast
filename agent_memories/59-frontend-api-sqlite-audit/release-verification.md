# Backend 1.19.6 and frontend 1.25.4 production verification

## Verdict

**Production deployment and CI passed. Unnecessary home API work and response size decreased, but a meaningful end-user Web Vitals improvement is not established, and origin tail latency remains.** Do not declare the backend or end-to-end bottleneck fully resolved.

The home API response shrank about 97.3% (median 6,430 to 174 bytes). Matched-profile home Lighthouse LCP was essentially unchanged (2,184 to 2,189 ms). Status Lighthouse LCP worsened in this sample (2,226 to 2,615 ms median; two of three postdeployment runs exceeded 2,500 ms). During natural post-scan writes, origin full/home statistics still reached 1,421/1,110 ms. These results preserve failures instead of replacing them with additional passing runs.

## Release and CI integrity

- Backend [PR #224](https://github.com/vientofactory/LawCast-Backend/pull/224), [backend-v1.19.6](https://github.com/vientofactory/LawCast-Backend/releases/tag/backend-v1.19.6), SHA `0219e2c6fa059305ca9069c6b48c76d9f01f74ea`. Implementation `7dcf172e90f823bf091d04033fe8a76fefbbc1b5` has a verified maintainer PGP signature.
- Signed root `606a13dde0246b9d46e3acea6e04400072597df9` deployed backend first. [Root run 40666732295](https://github.com/vientofactory/LawCast/actions/runs/40666732295) passed both Node backend/frontend matrix jobs, sidecar and CI gate, then deployed successfully. The deploy log reports healthy at `2026-10-28T09:50:17.962Z` and records the release SHA.
- Frontend [PR #174](https://github.com/vientofactory/LawCast-Frontend/pull/174), [frontend-v1.25.4](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.25.4), SHA `866709739dd096ff4e6d675a31377ef2d6c16ec6`. Signed implementation `4de8005` and signed CI addition `039daa3` were reviewed locally; the PR was merged only after backend version, health, view contract and native migration verification succeeded.
- [Pages deployment run 40667701198](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40667701198) passed. Cloudflare independently reports production deployment `224d6be9-c331-4758-b088-40796bf4ffe2`, exact frontend release SHA, stage success at `09:54:22.022Z`, and alias `https://law.viento.me`.
- [Frontend main CI 40667701182](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40667701182) passed **62 production Web Vitals regressions plus 6 SSR API consumer regressions**. The latter now run on every PR/main CI.
- Signed root `3e5b2e1c24ff12e93146538464f86b659ee8e939` records the frontend pointer. [Final root run 40667784996](https://github.com/vientofactory/LawCast/actions/runs/40667784996) passed all checks. Its deploy guards correctly skipped unchanged backend and semantic-search services rather than restarting them during measurements.
- Backend/frontend dev branches were fast-forwarded and pushed to their exact release SHAs/tags; full npm install left both lockfiles clean. Semantic-search remains on unchanged main `8438508b61d42b7b5586633ac1af43ac4d71cff8`. All three gitlinks match the root, with no plus/minus markers.

Pre-release local checks passed backend lint/type/build and **1,273 Jest tests**, normal process exit; frontend lint/check and six local SSR consumer tests; unchanged sidecar lint/format, **345 tests** and index-capability integrity; agent guidelines. Both implementation commits were explicitly GPG-signed and verified with the maintainer key.

## Deployed migration and contract

[Native schema probe](release-1.19.6/deployed-schema.json) runs inside the actual container, with sqlite3 `OPEN_READONLY`, no application bootstrap, synchronization or migration execution. It confirms:

- Runtime package 1.19.6 and Node v24.22.1.
- `OptimizeArchiveMetadataUpdates1793145601000` is recorded in production migrations.
- Trigger `BEFORE UPDATE OF` retains all protected columns and `rowid`, `_rowid_`, `oid` aliases.
- Metadata-only `EXPLAIN UPDATE` has no trigger Program opcode. EXPLAIN compiles the statement; no UPDATE was executed by the probe.

The diagnostic began after the rollout and is explicitly not a pre-migration production comparison. Actual protected-update and first-fill/lifecycle guards are established by local real-schema regressions, not by attempting mutations in production.

Public origin/proxy version reads report 1.19.6. Health reports healthy Redis/Ollama. `/api/stats?view=home` returns exactly archive count, cache lastUpdated, comparable event total and AI enablement. The existing full stats contract remains available. Browser footer/SSR checks confirm frontend 1.25.4.

## Measurement design and evidence

[External comparison](release-1.19.6/http-comparison.json) retains 12 predeployment rounds (60 requests) and 40 postdeployment rounds (200 requests). Each round performs five public GETs concurrently: backend version/full stats/home view, frontend unique-query home HTML and frontend home-view API proxy. Rounds are separated by four seconds, with a 20-second client deadline. All 260 requests returned HTTP 200; no requests timed out. Curl timing includes connection/TLS establishment, which is retained separately.

[Before origin](release-1.19.6/before-origin.json), [initial after origin](release-1.19.6/after-origin.json) and [live write-window origin](release-1.19.6/after-origin-live.jsonl) use independent localhost GET controls: version, full stats and home view, in that order. Counts are 12/24/40 rounds respectively. These controls are simultaneous observations, not exact packet-matched durations for an individual external request. All control requests succeeded.

The before interval was quieter; after includes a real startup pending sync. Sample counts, workload, cache state and connection timing differ. No production writes, crawler invocations, cache purges, restarts outside the official deployment, or artificial database updates were introduced for benchmarking. Do not infer a controlled causal percentage improvement or field p75 from these samples.

### API results

External median TTFB, before to after:

- Backend home view: **262 to 225 ms**; its maximum after is **1,112 ms**, p95 **973 ms**.
- Full backend stats: **238 to 242 ms**; maximum after **1,400 ms**, p95 **994 ms**.
- Frontend home-view proxy: **292 to 275 ms**; maximum after **1,108 ms**, p95 **973 ms**.
- Unique-query frontend home HTML: **168 to 158 ms**; maximum after **372 ms**. The latter sample spent 253 ms establishing TCP and 309 ms through TLS, so it is not evidence of a slow SSR computation.
- DB-free external version: **189 to 175 ms**. Some of the small median API change can therefore be ordinary connection variation.

Median home-view response size decreases **6,430 to 174 bytes (97.3%)**. This reduces backend-to-SSR/proxy transport and removes irrelevant operational dependencies; it is not a 97% reduction in the user's HTML. Home HTML was already sliced before this release and changed only **62,865 to 62,637 bytes** median.

Independent origin medians before/initial after: home view **27.90/21.85 ms**, full stats **24.78/28.01 ms**, version **3.67/3.64 ms**. This is a modest home-specific reduction with no overall full-stats speedup.

### Natural write phase and remaining tails

[Phase log](release-1.19.6/after-write-phase.log) records NSM page 163/163 and scan completion at **09:56:22Z** (163 pages, 16,289 raw items, 15,495 unique). [Subsequent work](release-1.19.6/after-final-workload.log) includes summary backfill apply batches through **09:57:59Z**. The external and localhost observations cover this real workload.

Across the 40-round write-window localhost series:

- Full stats: median **30.00 ms**, p95 **756.75 ms**, maximum **1,420.77 ms**.
- Home stats: median **24.23 ms**, p95 **972.75 ms**, maximum **1,109.80 ms**.
- DB-free version: median **3.25 ms**, p95 **43.28 ms**, maximum **120.16 ms**.

The largest external home/proxy waits occur together around **09:57:11.852Z** at 1,112/1,108 ms; TCP took ~48–50 ms and TLS ~100–102 ms. The largest external full-stats wait is at **09:57:22.088Z**, 1,400 ms with 49 ms TCP / 102 ms TLS. The corresponding independent origin series also has ~1-second stats waits. This demonstrates remaining origin work/dependency contention, not a connection-only explanation. It does not identify an exact remaining SQL statement or distinguish all shared-connection waits from every other awaited dependency.

The previously observed 3–7-second tails did not recur in this finite window. However, the old and new background workloads are not identical, so this absence cannot prove those tails permanently eliminated or attribute a precise speedup to the new trigger/batches.

## Lighthouse and browser results

[Before Lighthouse](release-1.19.6/lighthouse-before.json) and [after Lighthouse](release-1.19.6/lighthouse-after.json) each contain three fresh-Chrome mobile runs for home/status, sequentially. Both use the existing explicitly diagnostic **render-document browser profile with actual devtools throttling**. These are not stock-default Lighthouse scores, field Core Web Vitals or INP p75. The original first before run overlapped the tail of local sidecar verification, so its elevated TBT should not be used as proof of a code improvement; browser runs were otherwise sequential.

Home LCP: before **2372 / 2184 / 2160 ms**, after **2207 / 2189 / 2181 ms**. Median **2184 to 2189 ms**, essentially unchanged. Both series have one CF MISS followed by two HITs. Home is within the 2500 ms lab budget in all six runs.

Status LCP: before **2246 / 2223 / 2226 ms**, after **2615 / 2676 / 2485 ms**. All are CF DYNAMIC; **two postdeployment runs fail the individual 2500 ms budget**. Their server-response audit is **57/53/81 ms**, and Lighthouse attributes most LCP time to element render delay. The raw network log shows the same CSS URLs/hashes in both versions, with the main CSS completed at **2118–2129 ms before versus 2391–2568 ms after**. CSS discovery is also later (**643–654 versus 901–1095 ms**); h3 document receiveHeadersEnd is **622–636 versus 888–1059 ms** under emulation. This explains the observed later paint in these traces, but does not prove a new application-code regression or eliminate the independently observed origin tail. No failing sample was discarded or rerun until green.

[Before browser](release-1.19.6/before-browser.json) and [after browser](release-1.19.6/after-browser.json) each pass 14 production Playwright checks: 12 fresh-context desktop/mobile home/status/notices loads with visible SSR, footer, theme/menu interactions and no uncaught page errors, plus two controls with hydration/GTM scripts held. After native, unthrottled LCP is at most **468 ms**, sampled interaction duration at most **80 ms**. Those finite native observations do not override the throttled Lighthouse failures or establish field INP.

## Follow-up boundary

The confirmed improvements are less home API work/transport, non-duplicated aggregates, scoped trigger execution and bounded write batches. Production deployment and functional regression checks are successful. User-visible speed improvement remains small or unproven, and status lab LCP plus ~1-second origin stats tails remain open. A next investigation should profile the real post-scan shared-connection queue and the late dynamic-document/CSS discovery path with exact correlated spans; this release does not manufacture a full-resolution verdict.
