# Correlated External API Tail and SQLite Connection Queue

## Verdict

**The reproduced multi-second tail is inside the origin application, primarily a slow retry-candidate SQL statement monopolizing its shared SQLite connection. It is not principally a Cloudflare delay, a global database read lock, or a stopped JavaScript event loop.** A local SQL rewrite removes the reproduced queue bottleneck. The initial local phase had not deployed it; the later owner-authorized release phase is recorded below.

This conclusion combines same-request passive wire timings, concurrent origin controls, independent read-only DB queries, the existing cron logs, the production query plan, and a controlled local reproduction using the real TypeORM/sqlite3 implementation. It does not assign a cause to every historical outlier for which no trace exists.

## Authorization and production safety

The owner authorized read-only SSH diagnostics and local fixes/tests. Production remained backend 1.19.4, container started `2026-10-28T07:11:33.460735958Z`, restart count 0, healthy before and after. Root/backend source status remained clean. No restart, deployment, migration, write query, ANALYZE/optimize, cache clear, application instrumentation or Cloudflare setting change was performed. No PR, push, release, version bump or commit was made for this local patch.

A 210-second `tcpdump` observer on loopback TCP port 3001 ran without writing a remote pcap file. Its Python reader retained only requests tagged with `__lc_probe=lc58-...`, minimal timing/ID/status/byte metadata, and selected returned health/event-loop metrics. Other packet content and request/authentication headers were not persisted. The capture ended with **1258 packets captured, zero kernel drops**, and no observer was left running. Probe counts were bounded; no fault injection or load test was performed.

The initial auxiliary DB-probe path referred to the checkout rather than the Docker volume and produced `unable to open database file`; these are diagnostic setup failures, not evidence of database failure. Docker mount inspection identified the actual volume, and the separate corrected `mode=ro`/`query_only` series below overlapped the tail window. The original capture events preserve the failed setup probes transparently.

## Same-request production evidence

[Matched requests](matched-requests.json) join [48 external requests](external-requests.json) to [sanitized origin events](origin-events.jsonl) using unique request IDs, independently of client/server wall-clock offsets. All 48 requests were seen arriving at the origin. Forty-four completed with HTTP 200; four timed out at the client after 15 seconds. The four timeouts are failures, not omitted or counted as successful samples.

The decisive completed sample is `lc58-external-4029c52fed654f`, direct backend `/api/stats`, Cloudflare Ray `a5184afec91596a4-KIX`:

- External DNS: 3.312 ms; TCP established by 68.123 ms; TLS established by 155.372 ms.
- External TTFB: **4962.615 ms**; complete response: **4963.355 ms**.
- The matching request arrived on origin port 3001 at server epoch `1793173232.472970`.
- Matching first response bytes and complete 6344-byte response left at `1793173237.159398`: **4686.428 ms inside the origin**, about **94.4% of external TTFB**.
- Its returned Ollama health result was already cached from `07:40:28.317Z`, before this request arrived at `07:40:32.473Z`. The cached health measurement was 2012 ms; it was not a 4.69-second health probe performed by this request.

All four 15-second client timeouts also had matching origin ingress: a frontend-proxied discussions request, direct-backend stats, frontend-proxied stats, and another discussions request. No complete response for those IDs was captured before their client connections expired. This proves that those requests reached the origin and rules out an exclusively pre-origin Cloudflare stall.

Across the blocked interval, origin-only `/api/version` reads continued to complete: for example 6.364, 9.840, 4.659, 3.576, 3.703, 4.017, 7.444, 3.701, 3.577 and 4.298 ms. Origin stats probes in the same interval instead hit four 12-second timeouts. The lightweight version control does not touch the DB. This separates DB-backed application waiting from a globally frozen Node event loop. Subsecond shared scheduling jitter still exists outside this major stall (maximum successful version probe in the complete observation was 200.815 ms).

The diagnostic curl harness reused its body output file on HTTP-less timeouts; stale `success`/health data were explicitly discarded from the persisted external evidence for `exit=28/status=0`. The HTTP status, curl failure and matching ingress remain authoritative. TTFB 0 on these failures means no response headers, not a zero-latency success.

## Separating DB execution from a global DB lock

[Thirty independent read-only DB samples](db-series.json) opened the actual mounted SQLite database with `mode=ro`, `query_only=ON` and a 100 ms connection busy timeout. Each ran the archive count, comparable-event count and distinct comparable-notice count. All completed; total three-query time was **18.068–60.034 ms**.

Two samples directly overlapped the end of the blocked API window:

- At server epoch `1793173231.576795`, all three queries completed in **22.012 ms**.
- At `1793173234.598970`, all three completed in **23.489 ms**, while the matched stats request remained pending until `1793173237.159398`.

The DB was in WAL mode. Independent readers were not waiting seconds on a global read lock. The origin process could serve non-DB requests while DB-backed API requests waited. The real TypeORM sqlite driver has a shared database connection; its costly statement delays subsequent reads on that connection. This is a connection queue/execution bottleneck rather than the representative count queries themselves becoming multi-second operations.

## Identified SQL and cron correlation

`backend/src/modules/crawling/crawling-scheduler.service.ts:305` seeds the 15-minute proposal-reason retry cron through `getProposalReasonRetryCandidates()`. The cron schedule includes minute 39. Existing [operation logs](operation-log.txt) show summary apply work ending at `07:39:25.017Z`, followed by the retry cron reporting its seeded page at `07:40:37.189Z`, immediately after the blocked API response at `07:40:37.159Z`.

That log interval is consistent with the candidate selection bottleneck; it is **not** presented as an instrumented 72-second duration of one specific production SQL invocation. No live query logger or profiler was installed.

The old query in `notice-archive-maintenance-support.ts` contained two correlated `NOT EXISTS` predicates, each joining change events to details. SQLite was free to reorder each inner join. The [production EXPLAIN plan](production-retry-query-plan.json), obtained without executing the expensive statement, selects:

1. Search **all details for a field path** through `idx_notice_change_details_field_path_event_id_id`.
2. Lookup each event by its primary key.
3. Test whether that event belongs to the outer notice.
4. Repeat for every candidate archive row, for both history guards.

The EXPLAIN query used the same predicates/order/limit and projected notice numbers. The local real-service benchmark below uses the complete generated service query. Both exhibited the same bad join order. This multiplies global history work by the number of reasonless notices and holds the application's DB connection even though useful per-notice indexes already exist.

## Local patch

Branch: `codex/retry-candidate-query-latency`. Only two backend files changed:

- `src/modules/notice/utils/notice-archive-maintenance-support.ts:112`: scope the event lookup to the current notice, then nest a detail `EXISTS` keyed by event ID for each guard. The plan now searches `e` by `notice_num` and `d` by `event_id` plus `field_path`, using existing indexes.
- `src/modules/notice/notice-archive-proposal-reason-retry.spec.ts:314`: add real-schema selection and query-plan regression checks.

The original contract is preserved: current-Assembly/lifecycle/empty-reason eligibility, historical nonempty-reason and deletion exclusions, inclusion of ended notice periods, retry-history ordering, page limit, and selected payload/state mapping. In particular, this does not silently change an existing historical exclusion into a latest-value rule. No migration, index, TTL, API contract, caller timeout or summary-generation timeout changed.

## Local causal reproduction and improvement

[SQL-only comparison](local-sql-benchmark.json) against the existing local DB snapshot: baseline **14397.641 ms**; nested EXISTS alternative **372.622 / 28.593 / 28.325 ms**, with exactly the same ordered 20 notice IDs. The very first alternative trial before warming those reads took 3052.490 ms; this cold result is retained here rather than claiming that all possible cold executions take 28 ms. Production and local snapshots/workloads are not identical.

[HTTP/driver comparison](local-http-benchmark.json) loads the released helper from `backend-v1.19.4` and the working helper, running each through actual TypeORM and sqlite3 3.52.0 against the same **read-only local DB**. It starts an isolated loopback server and requests a DB-free version response plus two DB-backed handlers while candidate selection runs on their shared connection. The handlers are representative counts, **not the full production Nest controller**, and external dependencies are not contacted.

- Baseline candidate-and-request round: **17195 ms**. Version HTTP **16 ms**; DB-backed stats/discussions handlers **17174 / 17174 ms**.
- First patched round: **213 ms**. Version **2 ms**; DB handlers **200 / 200 ms**.
- Next patched rounds: **33 / 33 ms**. Version **1–2 ms**; DB handlers **19–22 ms**.
- Every measured local HTTP response was 200 and the ordered candidate IDs matched in all four rounds. Both generated query plans are retained in the JSON. This reproduces the selective queueing pattern seen on production and removes it by changing only the candidate SQL.

The [portable local reproduction harness](local-http-benchmark.cjs) runs from this folder with Node and the backend's installed dependencies. It opens only the local DB read-only, pins the baseline tag, starts a loopback server, and defaults its report to `/tmp/lawcast-retry-query-benchmark.json`. `LAWCAST_DIAGNOSTIC_OUTPUT` may select another report location. Do not run this expensive baseline inside production.

## Regression and quality results

- Two new tests use the real full-migration SQLite schema. One preserves blank/null/unrelated/multiple-event recovery/deletion semantics; one checks both history lookups stay constrained by notice/event IDs, without fragile wall-time thresholds or exact index names. The old baseline plan fails that scaling property.
- Candidate/archive/scheduler suites: **140 tests passed**. The actual retry-support suite additionally passed **13 tests**. An initial targeted command referenced a stale spec path and failed before that suite loaded; the path was corrected, and the relevant actual suites plus the full suite passed.
- Backend ESLint, TypeScript `--noEmit`, Nest build, and Prettier checks passed.
- Full Jest: **85 suites / 1256 tests passed**, normal process exit with no open-handle warning.
- Frontend `npm run check`: zero errors/warnings. Agent guideline checker: zero violations.

## Interpretation limits and follow-up

The correlated 4.96-second sample is dominated by its measured 4.69-second origin span. There is no evidence that Cloudflare dominates that sample. Its remaining time includes connection/network/proxy overhead and was not attributed to Cloudflare CPU. Request IDs, not unsynchronized wall-clock subtraction, establish correspondence; comparisons use monotonic/client durations and within-server packet durations. Clock-offset observations are retained separately.

`health.lastLatencyMs` can also be overwritten by successful summary generation (`ollama-client.service.ts:175`), so a returned 38910 ms value later in this series is not proof that a `/api/tags` probe ignored its two-second timeout. The cached check time and actual request spans must be considered.

The evidence identifies the dominant reproduced root cause and validates a local fix. It does not prove that every historical external delay had this cause or that cold disk/cache behavior, background CPU jitter or other queries are now bounded. **Production remains unfixed until a separately authorized release and correlated postdeployment recheck.**

References: [SQLite join-order documentation](https://www.sqlite.org/optoverview.html#joins), [earlier unresolved external-path measurements](../57-postdeploy-ssr-vitals/verification.md), [warm stats/Ollama deadline release](../56-local-stats-bottlenecks/verification.md).


## Owner-authorized backend 1.19.5 release

The owner subsequently requested final validation, deployment following project instructions, and correlated production verification. Final pre-release backend lint, TypeScript, build and **85 suites / 1256 tests** passed with normal Jest exit. Frontend lint/check passed. Sidecar lint/format and capability report passed; one existing real-model timing test failed in the first full run (344 passed), and a separate complete rerun passed **345/345 in 57.26 seconds** without changing that service or threshold. Index integrity remained 120420 chunks / 21786 indexed notices.

[Final local HTTP comparison](release-local-http-benchmark.json) again preserved the ordered candidates: baseline DB-backed requests **14465 ms**; patched **42 ms initially, then 20–21 ms**. Version stayed **2 ms** in patched runs. All local responses were HTTP 200. This remains a read-only representative local harness, not a production speed claim.

The signed backend implementation commit is `adde45abf3ec93d88a8b3838e175b72296dd3464`. [PR #223](https://github.com/vientofactory/LawCast-Backend/pull/223) passed its security check and merged as `b3f9aa9af898dd80093fff5d1bafe2eff6964980`; release `backend-v1.19.5` targets that exact SHA. Full npm install changed only committed version fields; no dependency resolution changes were introduced. The root release pointer will trigger the mandatory CI/deploy workflow. Subsequent production observations are recorded separately after deployment.
