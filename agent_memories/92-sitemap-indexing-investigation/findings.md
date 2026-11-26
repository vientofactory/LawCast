# Sitemap Fetch Failures and Google Indexing Decline

## Conclusion and confidence

Investigation date: 2026-11-24 JST. Application code and Cloudflare configuration were not changed.

**HIGH: chunk generation shares one backend rate-limit bucket across every sitemap request.** Each uncached 500-URL chunk consumes five archive-list reads, while that endpoint permits only 30 reads per 60-second window for the shared identity. Per-chunk concurrency limiting does not enforce the global budget. Backend failures become HTTP 503 on the public sitemap routes. The implementation mechanism is reproduced with the actual source, and production shows a matching burst-failure/idle-recovery pattern. Backend production logs were not collected; the underlying 429 for each individual production 503 is inferred, not directly observed.

**HIGH: Google also receives HTTP 403 for ordinary detail pages, independently of sitemap discovery.** A real Search Console live test of `/notices/2219321` returned 403 on 2026-11-24 at 04:36:55 JST, although the same URL returned 200 with an indexable canonical page from this workstation. Cloudflare analytics records originResponseStatus=403 and edgeResponseStatus=403 for that exact inspection request. The application/upstream path needs investigation; attributing this to the frontend-zone WAF or Bot Fight Mode is not supported by the evidence collected here.

**The indexed-page decline cannot honestly be assigned entirely to the chunk-splitting commit.** The largest observed drop coincides with its date, but decline and sitemap-access trouble predate it, and there is a separately confirmed current 403 failure. Historical request-level logs would be needed to apportion the decline.

## Search Console observations

The existing Chrome tab was used. No sitemap was resubmitted, no indexing request was sent, and no validation workflow was started. One live URL test was run. The page-indexing CSV was downloaded through the native export menu; its relevant members are preserved in `evidence/gsc-chart.csv` and `evidence/gsc-exclusions.csv`.

- Current report update: 2026-11-16; indexed pages: 72; excluded pages: 8,294.
- Indexed history: September 22: 566; October 13: 550; October 17: 491; October 20–23: 414; October 24: 155; November 7: 137; November 10: 120; November 14–16: 72.
- The October 23→24 change is 414→155, down 259 (62.56%). September 22→November 16 is 566→72, down 87.28%.
- `/sitemap.xml`: submitted April 30; last successfully read September 27; status “could not fetch”; HTTP error 503; discovered pages 4,002; still described as a Sitemap rather than a Sitemap index. These are stale Google-side observations, not the current XML's type or URL count.
- Exclusion reasons: HTTP 403: 2,900; discovered/not indexed: 3,303; crawled/not indexed: 792; alternate with canonical: 702; noindex: 526; duplicate/Google canonical differs: 46; 404: 18; 5xx: 6; robots blocked: 1.
- 403 first detected June 6. Examples include both parameterized detail URLs and canonical `/notices/2219321`, with last crawls on November 17.
- Noindex first detected May 12. Visible examples were last crawled June–September, including canonical `/notices/2219251` and `/notices/2219335`. This is not evidence of a newly introduced blanket noindex after October 24.
- Inspection of `/notices/2219321`: historical Googlebot smartphone fetch failed with 403 on November 17; crawling allowed; referring page is a parameterized variant; Sitemaps reports a temporary processing error.
- The same URL's real live test failed with 403 on November 24. This is a present failure, not merely delayed reporting.

## Code path and invariants

1. `frontend/src/lib/server/sitemap.ts:6-8` defines 500 URLs per chunk, 100 rows per backend page, and an hour-long in-memory cache.
2. `sitemapIndex()` at lines 23–31 correctly produces a sitemap index with root-level child locations.
3. `fetchArchivePage()` at lines 54–80 always sets `x-lawcast-client-ip: sitemap-bot` (line 61), calls `/notices/archive`, and throws on any non-2xx (line 66).
4. `noticeSitemap()` at lines 100–119 fetches five archive pages per full chunk. Its two-request concurrency limit applies only within an individual generation, not across chunks, workers, crawlers, or locations.
5. `backend/src/controllers/api.controller.ts:284` applies the expensive read bucket before the archive query, including cached query results.
6. `backend/src/modules/shared/api-read-rate-limit.service.ts:18-19` sets expensive policy to 30 requests / 60 seconds; lines 53–66 key it on forwarded identity and throw HTTP 429 after exhaustion.
7. `cachedSitemap()` at `frontend/src/lib/server/sitemap.ts:151-163` deletes the failed cache entry and maps generation failures to HTTP 503, with Retry-After 60. The index uses this same path and same upstream identity.
8. The cache is a module-local Map, not a global Cloudflare edge artifact or distributed cache. Cache headers are not proof that requests are actually edge-cached: observed sitemap responses were CF-Cache-Status DYNAMIC.
9. At 22,740 bills, 46 chunks require 228 archive-page reads plus one index read: **229 upstream reads**, far beyond a single 30-request budget when the set is crawled cold.
10. Cache GET→SET increments are not atomic. Concurrent requests may undercount, so the exact first failed chunk varies; it should not be predicted as an invariant six-chunk cutoff.

### Additional access-failure path

`frontend/src/routes/notices/[num]/+page.server.ts` rethrows a backend HTTP 4xx, except the special 429 recovery path, at lines 147–148. `frontend/src/hooks.server.ts:45-46` passes through backend fetches, and its forwarding helper preserves most original headers. This is a plausible propagation path for the observed origin 403, not proof of which upstream component originally emitted it.

Successful workstation probes, both normal and Googlebot UA, returned HTTP 200 and `robots=index, follow, max-image-preview:large`. Cookie-bearing probes were DYNAMIC and also returned 200. A matching UA from a workstation does not reproduce a real Google network request; these probes do not establish that Google can crawl.

## Production HTTP proof

Raw first-pass statuses and retry response headers are preserved in `evidence/production-probes.json`. The failed response body and headers are preserved separately.

- Index: HTTP 200, valid `<sitemapindex>`, 47 children: main plus chunks 0–45.
- Sequential first pass: main 200; chunks 0–6: 200 with 500 URLs each; chunks 7–45: 503. Thus 7/46 bill chunks succeeded and 39/46 failed during this pass.
- Failed response body: `사이트맵을 생성하지 못했습니다. 잠시 후 다시 시도해주세요.` This is the application's generation-error text, not a malformed XML body or Cloudflare challenge HTML.
- Failed headers: HTTP 503; Retry-After 60; Cache-Control private, no-store; CF-Cache-Status DYNAMIC.
- After an idle interval exceeding 60 seconds: chunk 7 recovered to 200 with 500 URLs; chunk 45 recovered to 200 with 240 URLs, ending at `/notices/2223143`; index returned 200 again.
- No production setting, purge, deployment, database record or authentication policy was changed by these GET probes.

## Local reproduction and test coverage gap

Run from the repository root:

```bash
node agent_memories/92-sitemap-indexing-investigation/evidence/reproduce.cjs
```

The harness transpiles the current sitemap source and actual ApiReadRateLimitService without modifying either. It substitutes a 22,740-item archive and in-memory clocked cache; framework dependencies and identity hashing are minimal stubs. Both scenarios crawl the index then all 46 chunks with the same request structure. Cache increment races are preserved. Literal output, exit 0:

```text
{"mode":"NO_LIMIT_FIXTURE","index":200,"chunks200":46,"chunks503":0,"firstFailedChunk":-1,"backendCalls":229,"backend429":0}
{"mode":"REAL_30_PER_60_LIMIT","index":200,"chunks200":9,"chunks503":37,"firstFailedChunk":9,"backendCalls":87,"backend429":38}
AFTER_61_SECONDS chunk=9 status=200
```

These are controlled local results, not production 429 logs. The differing production cutoff is compatible with real shared traffic, worker caches, request ordering and non-atomic counters.

The existing `frontend/e2e/fixtures/sitemap-backend.mjs` has synthetic page failures/truncation but **no real read-rate policy**. Therefore its all-chunks completeness case does not test this failure mode.

Existing suite command:

```bash
cd frontend && npx playwright test -c playwright-configs/playwright.sitemap.config.ts
```

Sandboxed startup first failed with EPERM binding 127.0.0.1:4319. Re-run with local-server access completed: **9 passed, 1 failed**, exit 1. The failure is an outdated exact header expectation: `no-store` expected, `private, no-store` returned by the shared hook. All-chunks completeness passed against the unthrottled fixture. No test was edited to hide this failure.

## Git chronology

- Backend expensive-read limiting exists since September 8 (`4600c65`); forwarded visitor identity behavior changed September 8–10. Current expensive policy is 30/60.
- Before October 24, `frontend/src/routes/sitemap.xml/+server.ts` returned one URL set, latest first, capped at 5,000 notices. It fetched up to 50 pages and silently ignored failed later pages, then cached HTTP 200 even with a partial set.
- October 24 at 00:54:49 JST: `a77148d`, PR 164, splits the sitemap into index/main/500-URL chunks; uses ascending ordering and removes the 5,000-notice cap; rejects incomplete/upstream-failed results as 503. This improves correctness but exposes the unresolved shared-read budget problem instead of publishing partial success.
- Current sitemap source differs from that commit only in environment/import migration syntax (`b17828a`, November 7); the generation/rate-limit mechanism remains.
- Ascending order means successful early chunks favor older notices, whereas the former capped sitemap favored recent ones. This amplifies lost fresh-URL discovery when later chunks fail; exact Google-fetched child coverage was not available because the parent index itself is failing in Search Console.
- Last Google-side successful sitemap read is September 27, before splitting. Decline to 414 also precedes splitting. October 24's 259-page drop is temporally aligned, not proof that every removed URL was caused by this commit.

## Cloudflare read-only corroboration

`evidence/cloudflare-google-errors.json` stores the adaptive analytics query result for 2026-11-22 19:40 through November 23 19:40 UTC (November 23 04:40 through November 24 04:40 JST), filtered to law.viento.me, eyeball requests, Google-like UA, and errors.

- Googlebot-like `/sitemap.xml`: 4 estimated requests, origin and edge both 503.
- Googlebot smartphone-like `/notices`: 8 estimated 403s; `/notices/2218712`: 2; `/notices/2218806`: 1. Both origin and edge statuses are 403.
- The live Google Inspection Tool request for `/notices/2219321` also appears with origin and edge 403. Search Console is the authority that this test really came from Google; a UA match alone is not identity verification.
- Adaptive counts are sampled/estimated, not exact access-log counts.
- Frontend-zone custom LawCast challenge rule is disabled, last changed August 15; no rate-limit ruleset exists in the zone. Bot Fight Mode and JS detections are enabled. No matching frontend-host Google firewall event was returned for the queried window.
- These observations favor an application/upstream response over an obvious frontend-zone custom WAF rule. They do not rule out controls on the backend's own host or a platform-origin policy.

## Remediation priorities and remaining proof

1. Fix sitemap delivery's ownership boundary: serve a prebuilt/persisted complete sitemap artifact or introduce an appropriately protected internal sitemap read model that does not consume the public interactive archive quota per 100 URLs. Coordinate generation across workers and retain a last-known-good artifact on transient generation failure. Do not merely lower per-chunk concurrency or return partial XML as successful.
2. Add an integration regression with the actual 30/60 policy, cold index plus every chunk, multiple simultaneous readers/worker instances, and expiry/failure recovery.
3. Independently trace the real Google 403 through frontend request logs, SSR backend calls and the backend host's access controls. Correlate the known live-test timestamp and path. Preserve legitimate protection; do not blanket-disable the zone's security or exempt a caller solely on User-Agent.
4. After both paths are healthy, verify Google live fetches for representative old/new canonical URLs and the parent/child XMLs, then resubmit the parent and monitor read dates/discovered URLs separately from indexing counts. XML discovery success is not a guarantee of indexing.
5. Historical worker/backend request logs around September 27 and October 20–24 would be required to distinguish the older sitemap failure from the exact trigger of October 24's indexing drop.

At the end of the initial read-only investigation, no application fix, commit, push, deployment, sitemap resubmission or indexing request had been performed. Subsequent authorized remediation is recorded below.

## Follow-up implementation and confirmed 403 source (2026-11-24)

The owner authorized sequential remediation and deployment. The sitemap fix is prepared as backend PR 249 (backend-v3.2.5), root deploy-pointer PR 68, and a dependent frontend PR. It replaces the paginated quota-consuming reads with a fixed, metadata-only persisted snapshot. The public endpoint accepts no search or paging arguments; interactive API quotas remain unchanged. Redis holds complete generations, in-flight readers coalesce, and a failed refresh can serve a last-good snapshot up to 24 hours old with a 60-second retry cooldown. Frontend chunks slice that snapshot without further archive-list reads. Full backend gates passed: 106 suites / 1,425 tests. The extended frontend HTTP test covers 22,740 URLs, 46 chunks, concurrent cold reads, upstream 503, truncated metadata, retry, credentials, origins and chunk bounds.

The 403 attribution is now **confirmed**, superseding the earlier unresolved attribution: Pages tail logs for the actual Google live test show `LC_CF_CHALLENGE_DETECTED` while loading detail and changes. Querying Worker subrequests, rather than only the frontend eyeball requests, identifies `lawcast-backend.viento.me/api/notices/2219321/{detail,changes}` with edge 403 and origin 0. Security events at 19:49:00 and 19:51:24 UTC identify `source=botFight`, `ruleId=bot_fight_mode`, `action=managed_challenge`, with an empty User-Agent. The frontend's original 403 is propagation of this upstream Cloudflare challenge; it is not a NestJS authorization denial or a missing notice. Evidence: `evidence/backend-bot-fight.json` and ignored `_workspace/sitemap-recovery/production-tail.jsonl`.

Cloudflare documents that Free Bot Fight Mode applies zone-wide and cannot be skipped with WAF custom rules or Page Rules. A blanket disable would affect other viento.me services. The owner has been asked to choose between preserving protection and using an authenticated server-to-server path, or explicitly approving the zone-wide disable. No bot protection was changed. Do not claim that setting a browser/Google User-Agent is authentication or a verified durable fix. Direct SSH diagnosis was attempted on the documented private host and its public address; both timed out.

Release and production success must be established from subsequent push/deploy runs, not inferred from the prepared PRs or local tests. See `_workspace/sitemap-recovery/VERIFICATION.txt` for incremental evidence and copy-only rollback proof.


### Authenticated-origin rollout

The owner chose to keep Bot Fight Mode and reconnected the operating VPN. Key-based SSH then succeeded. The original server had nginx listening only on HTTP port 80 and a firewall restricted to Cloudflare source ranges; direct HTTPS was not available. The completed server path uses a separate Caddy 2.11.9 process, pinned from the official release and checked with its SHA512 manifest. It owns publicly trusted TLS and automatic TLS-ALPN renewal on a dedicated origin hostname; no DNS API credential or certificate-renewal reminder is required. The proxy authenticates a 256-bit random service credential before forwarding to loopback NestJS, removes it upstream and redacts it from logs. The frontend uses server-only service URL/token bindings, strips visitor-supplied service headers, retains visitor IP attribution, requires production HTTPS and rejects API redirects. API_BASE_URL remains available as an explicit rollback route.

The only ingress change is a dedicated IPv4 TCP 443 ACCEPT rule for the new authenticated HTTPS listener. The existing public HTTP hosts, Cloudflare-only HTTP firewall policy and public nginx configuration are unchanged; no SSH/database/container port was opened. No/wrong keys return 403 over verified HTTPS, while a valid key returns backend version 3.2.5. The service has a dynamic unprivileged user, private state/admin Unix socket and no nginx/Docker restart dependency. Host backup: /root/lawcast-ops/sitemap-origin-20261124; source and operational rollback: ops/lawcast-origin/README.md, root PR 69.

Backend PR 249 merged at 5830fcba4bf9bdda4415ed59d9df90901d20c5eb and backend-v3.2.5 matches it. Root pointer PR 68 merged at 4872e54314793a87cd9e652a2118417405ec93f8. Its real main push run 45255754014 completed successfully, including both deployment jobs; the live backend is healthy and returns a complete 22,740-item sitemap snapshot. The pointer PR's first run had an unrelated shutdown wall-clock boundary assertion; failed jobs passed unchanged on retry, retaining both runtime checks and the original failure log.

Frontend PR 217 includes both sitemap and authenticated-origin fixes as version 3.2.1. The six auth/IP HTTP tests and four sitemap HTTP tests pass; root operational tests total 39. Remaining release and Google live results must be appended after they are actually observed.


### Deterministic fixture correction

Root PR 69's first Node 22 run exposed a genuine flaw in the newly added test fixture: Date.now was frozen while new Date still used the real wall clock, so the first generated snapshot could appear a few milliseconds in the future. Backend PR 250 uses Jest's system clock for both APIs and restores real timers after each case. The runtime service and its future/stale validation remain unchanged. Full Node 24 gates pass (106 suites / 1,425 tests), and the six targeted sitemap cases pass on Node 22.23.4. The correction is released as backend-v3.2.6 at 2db310aa6b15b707baa7e356c8b92823dd90760b; root PR 69 now points at it. This is distinct from the earlier unrelated graceful-shutdown timing flake; neither failure is hidden or reclassified as a production symptom.


### Workers redirect-mode incompatibility and production rollback

Frontend-v3.2.1 passed the browser CI workflow and Pages deployment but its immediate production probes returned 503. A new Pages tail identifies the exact cause: Workers rejects Request.redirect=`error` at construction and supports only `follow`/`manual`. Node's Fetch accepts `error`, so the Node/HTTP tests had not exposed this runtime difference. The production site was immediately rolled back to its known-good Pages deployment ba1e7c4d-5db6-4a30-83ab-b465116b0a46 (ad945b8); a cache-bypassed detail probe returned HTTP 200 again. The zone's SSL mode was inspected during diagnosis but not changed; the captured exception, not that setting, explains these 503s.

The correction uses `manual` and a shared explicit redirect-status rejection (301/302/303/307/308), keeping 304 semantics intact. A dedicated sitemap workerd config is added to the shared CI matrix. Its real Workers test covers 503, refused redirect, truncated snapshot, cold coalescing and every chunk: four cases pass. The six auth/IP HTTP tests still pass with the redirect sink never reached. A real workerd smoke test against the authenticated production HTTPS origin passed for the detail page (200), sitemap index (200, 47 children), and last chunk (200, 240 URLs). The public fallback was deliberately unreachable. Release/Google success will be recorded only after observed verification. No failed release or temporary rollback is omitted from this evidence trail.


### Corrected release validation and backend deployment

Frontend PR 218 uses Workers-supported `manual` mode and rejects redirect responses explicitly. Its first CI run caught a stale exact matrix-list assertion in `scripts/ci-install.test.mjs` after adding `sitemap-cloudflare`. The guard now requires the new suite as well as all existing suites; the assertion was extended, not removed. Local lint, Svelte check, all CI-install guard tests, and repository agent guidelines pass. The corrected CI's actual workerd sitemap job also passes.

Root PR 69 merged at d57c021. Actual main push run [45263504068](https://github.com/vientofactory/LawCast/actions/runs/45263504068) passed both deployment jobs. An SSH loopback probe at the configured port 3001 returns `{ "success": true, "data": { "version": "3.2.6", "buildEnv": "env" } }`; `lawcast-origin` remains active. A preliminary probe of unused port 3000 failed (curl exit 7); the checked-in Caddyfile establishes port 3001 as the real listener, and the corrected probe exits 0.


### Production and Google verification

- Frontend PR 218 merged at `b82dedf715ad07538fd6e21a1ff010ace272770e`; `frontend-v3.2.2` matches exactly. All PR checks passed, including workerd sitemap, cross-browser suites, accessibility, and SSR API consumers (run [45263700390](https://github.com/vientofactory/LawCast-Frontend/actions/runs/45263700390)).
- Actual Pages deploy [45265874328](https://github.com/vientofactory/LawCast-Frontend/actions/runs/45265874328) passed. Cloudflare canonical deployment `ab4dd531-76df-414a-b019-3e3477582f67` reports success and exactly the release SHA. Existing nine encrypted bindings remain configured.
- `python3 _workspace/sitemap-recovery/verify-production.py` exits 0: `{"index": 200, "children": 47, "chunks200": 46, "uniqueNotices": 22740, "lastChunkUrls": 240, "main": 200, "detail": 200}`. It checks all 46 actual public chunks, not a sample. The initial Python urllib probe got 403; curl with its ordinary client identity returned 200 and completed the same verification. This does not impersonate Google.
- A separate literal-token scan finds no service token in the production SSR HTML/XML or the local client bundle. Missing/wrong origin keys return 403; authenticated HTTPS returns backend 3.2.6; nginx's original SHA256 is unchanged, private state permissions are 0700 and token environment is 0600. Bot Fight Mode remains `fight_mode=true`.
- Genuine Search Console live test for `https://law.viento.me/notices/2219321` at **2026-11-24 06:07:20 JST** now shows `URL을 Google에 등록할 수 있음`, Google Inspection Tool smartphone, crawl allowed yes, **page fetch success**, indexing allowed yes, and the correct declared canonical. The same UI previously returned 403 at 04:51:24. Screenshots were displayed in the task.
- The parent `https://law.viento.me/sitemap.xml` was resubmitted through the existing Search Console tab. The UI confirmed `사이트맵이 제출됨`; submission date changed to November 24. The table still shows its previous September 27 read date, old fetch error and 4,002 discovered pages pending Google's asynchronous reprocessing. Submission is not proof of a completed reread or an increased indexed-page count. No individual indexing request was submitted.
- Root pointer PR 70 records only the verified frontend release gitlink. Its post-merge run and final pointer checks are recorded below once observed.


### Final repository alignment

Root PR 70 passed CI [45266449862](https://github.com/vientofactory/LawCast/actions/runs/45266449862) and merged at `32dd002`. Its backend/frontend pointers exactly match `backend-v3.2.6` / `frontend-v3.2.2`; both local submodules are clean on `dev`, actual npm 11.13.0 install completed and lockfiles remain clean. Root stays detached at merged `origin/main` because `main` is already checked out in another existing worktree; no other worktree was modified. The final push run is [45267410156](https://github.com/vientofactory/LawCast/actions/runs/45267410156).

Final main push run 45267410156 completed **success**, including both deployment jobs (unchanged-service guards exit successfully). Frontend main regression run 45265874298 also completed **success**. The full public sitemap/detail verification was repeated after the final push and still passes all 46 chunks / 22,740 unique notices. Agent guidelines report zero violations. Copy-only rollback reverified all original hashes and reproduces the original quota failure; the actual released implementation remains in the working tree.

## Follow-up: intermittent 503 versus Workers CPU limits (2026-11-24 06:35–06:45 JST)

The attached screenshot is a report of another live check, not evidence that its successful retry permanently resolved delivery. The new incident is after frontend 3.2.2. No application source, production configuration, protection setting, or deployment was changed during this analysis.

### Historical corroboration

Cloudflare canonical Pages deployment remains `ab4dd531-76df-414a-b019-3e3477582f67`, release SHA `b82dedf715ad07538fd6e21a1ff010ace272770e`, usage model `standard`. Zone adaptive analytics for `/sitemap.xml` show the following sequence in MSP with ordinary `curl/8.14.1` identity:

- 06:31 JST: one edge 499 / origin 0 (client disconnected).
- 06:32 JST: two edge 503 / origin 503; reported average origin-response duration 44.5 ms.
- 06:33 JST: one edge 200 / origin 200, reported duration 2,603 ms.

These are sampled analytics, not exact per-request trace records. The origin duration is a platform metric and is not interpreted as a direct measurement of the authenticated backend subrequest. A genuine Googlebot-like sitemap request also returned 200 at 06:08; User-Agent analytics alone do not establish caller identity.

The Pages invocation dataset for 06:25–06:39 shows only `success` and one `clientDisconnected`, with zero invocation errors and no CPU-exhausted outcome. At 06:32, whole-worker CPU p50 = **6.197 ms**, p99 = **71.532 ms**. The GraphQL schema explicitly defines CPU quantiles in **microseconds**, so raw 6,197 and 71,532 are divided by 1,000. These are aggregate metrics across routes, not historical CPU measurements of the two failed sitemap requests. Duration quantiles are GB-seconds and must not be mislabeled as wall seconds.

### Current execution and source evidence

A temporary live Pages tail captured 712 invocations, all `outcome=ok`. The four specifically correlated sitemap probes returned 200 with CPU/wall milliseconds: index 0/0, chunk 0 0/0, chunk 23 0/0, chunk 45 **12/129**. Rounded zero values reflect cached/light executions, not a cold-generation benchmark. No exceptions or error logs appeared in these four events. A fresh complete public check again passes 47 children, all 46 chunks, 22,740 unique notices, last chunk 240 URLs, and detail HTTP 200. The temporary tail was deleted after capture.

`frontend/src/lib/server/sitemap.ts:163–167` catches generation errors, logs `sitemap: generation failed`, and deliberately returns the Korean application 503 body plus `Retry-After: 60` / `Cache-Control: no-store`. `/sitemap.xml` depends on `fetchSitemapSnapshot`, whose fetch, HTTP status check, JSON parsing and completeness/order validation are at lines 65–91. Thus the screenshot's stated application body and the zero resource-error aggregate favor a **caught application/snapshot-path failure, not Workers CPU-limit termination**. Cloudflare CPU-limit failures use resource-limit error 1102 / invocation outcome `exceededCpu` ([official limits documentation](https://developers.cloudflare.com/workers/platform/limits/)). Network waiting is not CPU time.

The 06:31 disconnect is temporally adjacent, not a demonstrated cause. A diagnostic against the actual built app in fresh local workerd instances tested a two-second delayed 22,740-item backend response: ordinary concurrent clients returned 200/200 and one backend read; aborting the first client after 200 ms still let the second client and last chunk return 200 with one backend read. **The simple shared-promise/client-abort hypothesis did not reproduce.** Command: `node _workspace/sitemap-recovery/probe-client-abort.mjs`, exit 0. This diagnostic made no product-code changes and contacted only a local backend fixture.

### Remaining attribution and next step

The original 06:32 exception payload is not present in the historical telemetry query; a live tail started later cannot recover it. Both private and existing public SSH endpoints time out again, so contemporaneous backend/Caddy logs remain unchecked. The precise cause among upstream transport/HTTP response failure, JSON decoding or snapshot validation is **not yet established**. Do not label it a proven timeout, CPU issue, Bot Fight recurrence, or bad XML structure.

A cold isolate or expired cache must fetch the snapshot; frontend cache is in-isolate memory, and a failed fetch has no frontend last-good artifact/retry. Backend Redis last-good protects backend generation, not an edge-to-origin transport failure. This is a concrete resilience gap, not proof of which exception occurred. The next useful evidence is the failed request's exception/ray and corresponding origin logs; an increased CPU limit is not supported by current evidence. If transport failure is confirmed, consider bounded retry and a shared complete last-good XML/snapshot artifact without weakening validation or publishing truncated 200 responses. The earlier all-200 deployment checks did not establish absence of intermittent failures.

Evidence: `evidence/cpu-follow-up-edge.json`, `evidence/cpu-follow-up-analytics.json`, `evidence/cpu-follow-up-live-sitemap.json`; local diagnostic result `_workspace/sitemap-recovery/client-abort-results.json`. The evidence files and this report were reopened after writing.

## Transport-recovery remediation (2026-11-24)

### Confirmed versus historical attribution

After the owner reconnected the tunnel, SSH confirmed no backend restart (restart count zero) and no sitemap/backend errors in the 06:25–06:40 window. Caddy emitted 51 incomplete-response warnings for unrelated notice routes, all `writing: http2: stream closed`; none is a sitemap request. They are not treated as the sitemap cause. The backend had a complete 22,740-item snapshot generated at 06:18:03.281 JST. Backend-host firewall/subrequest analytics show no matching Bot Fight recurrence. A later live tail captured 2,375 invocations, all `ok`, with no generation exception. The old 06:32 exception payload is still not available; this remediation does **not** uniquely attribute that historical event.

A temporary signed diagnostic branch ran public probes from GitHub's US runner (run45274517513). The public domain was challenged403 by existing protection on that runner, while the public Pages alias succeeded. This is not the old application503. The temporary diagnostic workflow was removed before the PR; no security setting or secret access was expanded.

### Reproduced failure and bounded fix

A real workerd fixture closes the upstream socket before response headers and, separately, sends a partial HTTP200 body then closes it. Both produce the native exception **`Error: Network connection lost.`**, with platform fields **`retryable: true`** and `remote: true`. It is not a `TypeError`. A retry implementation testing only `TypeError` failed the native regression (expected200/received503, one failed case); recognizing the explicit platform retryable marker fixes it. This is demonstrated failure behavior, not a guessed historical exception.

`frontend/src/lib/server/sitemap.ts` now uses a small internal `readSnapshot` boundary: at most two total attempts, one shared existing10,000ms deadline, 150ms backoff, and only network transport errors or HTTP5xx are retried. Redirects,403, malformed JSON and invalid/incomplete snapshots remain terminal. The complete-snapshot cache and coalescing stay intact. Logging records request/status/body/validation stage, upstream status, attempt and public correlation data without credentials or request headers.

PR219, version3.2.3, contains this bounded recovery and fixture regressions. Verification before release:

- Native workerd:4 cases pass, including socket loss before headers, body truncation, retry budget exhaustion, terminal redirects403/JSON/schema rejection, all46 chunks and22,740 unique URLs.
- Node HTTP:4 cases pass.
- Auth/IP: initial invocation omitted enable flag and skipped6; corrected `E2E_IP_ECHO=1` run passes all6. Skips are not reported as proof.
- Native deadline check: two upstream attempts that each require6 seconds terminate after10,012ms in total, HTTP503; the following request returns200. The timeout budget was not doubled.
- Frontend lint/check and agent guidelines pass; actual npm11.13.0 install syncs package3.2.3 with its lockfile.
- Separate-copy rollback restores all five original file hashes and reproduces the original one-call503 behavior; actual source stays modified.

Evidence and exact commands/results: `_workspace/sitemap-exception-repair/VERIFICATION.txt`, `MODIFIED_FILE`, `DIFF_FILE`, executable `ROLLBACK.sh`. The original broad sitemap-recovery artifacts remain unchanged. Deployment outcomes are appended only after verified.

Frontend PR219 passed all checks (run45276707677) and merged as `947c0ae19f704ee8b210e3d136e2762eced0a848`; tag `frontend-v3.2.3` matches exactly. Pages main-push deploy45278787333 succeeded and canonical deployment `124c3c61-dc54-414a-923e-6de8b742016c` reports this SHA. Production verification now reads the actual metadata snapshot, compares **every** notice URL, and requires SSR HTMLversion3.2.3: index200,47 children, all46 chunks200,22,740 unique notices, final240, main200/detail200. The new build also passed real local workerd against authenticated production HTTPS with the public fallback deliberately unreachable; temporary0600 bindings were removed afterward. Root pointer PR71 records only the released frontend gitlink; final main-push proof follows once observed.

Root PR71 passed CI45278914531 and merged at `9d2d4cf`; final pointers are backend`2db310a` / frontend`947c0ae`, exactly the released main commits. Frontend main regression45278787688 succeeded. Root main push45279730550 first attempt failed solely on the unchanged backend graceful-shutdown wall-clock assertion (expectedat least100ms, actual99ms);105 suites and1,424 cases passed, and matrix Node22 was canceled. The original failure is retained; failed/dependent jobs are rerun unchanged, without relaxing tests. This is the same pre-existing timing flake noted during the earlier release, not a sitemap production exception.

The new production tail captured142 invocations:141`ok`, one ordinary cancellation, no log/exception/HTTP5xx events.39 sitemap-related captured events used at most15ms CPU; this is a subset of requests, not an exact census. All46 HTTP chunk probes separately passed. The temporary tail/collector and private smoke bindings were removed. Service-token literal scan passed on deployed HTML/XML, client build and evidence package.

Final root main push45279730550 passed on the unchanged retry, including both backend runtime matrices, CI gate, and both deployment jobs (unchanged-service guards). Frontend main regression45278787688 is also green. Full production verification was repeated after this run and remains47 children /46 chunks200 /22,740 unique URLs /last240 /detail200. Both service submodules are clean on dev and match root release pointers without+/-; no unrelated notes were committed. Final guidelines:0 violations. The reproduced transport-failure path is shipped and verified; the exact old06:32 exception remains unconfirmed, not retrospectively claimed as solved attribution.
