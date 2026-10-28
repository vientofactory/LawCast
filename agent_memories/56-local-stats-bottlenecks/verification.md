# Local Stats Cache and Ollama Health Deadline Verification

## Scope

The initial implementation phase was local only, following the owner's instruction not to touch production. No SSH, production API requests, remote pushes, PRs, merges, releases or deployments were performed during that phase. Backend and root work started on `codex/local-stats-bottlenecks`. The owner subsequently explicitly authorized backend deployment, including existing external modifications; the release phase is recorded below.

## Patch

- `backend/src/modules/cache/cache.service.ts:65`: recent-list and statistics calls share the existing process-local recent-notice snapshot. A cold process restores it once from Redis; concurrent callers share that load. Warm `getCacheInfo()` reads only the small last-updated key, not the recent-notice body. No Redis key or public service method was added.
- Successful cache updates publish a new snapshot; clears invalidate it. A generation counter prevents an older pending read from restoring stale contents after an update or clear. Failed cold reads can be retried; empty snapshots are retained rather than reloaded on every request.
- `backend/src/modules/ollama/ollama-client.service.ts`: `/api/tags` uses `ollama.healthTimeoutMs` (`OLLAMA_HEALTH_TIMEOUT_MS`, default 2000 ms) with both an Axios request timeout and `AbortSignal.timeout`. This bounds a trickling response as well as an unresponsive dependency. Concurrent probes share one in-flight request. Failure retains the existing unhealthy status and 30-second health cache policy.
- The Axios instance's generation timeout and `/api/generate` request are unchanged. A configured `OLLAMA_TIMEOUT=1800000` still applies to generation; health checks only override their own request configuration.

## Regression checks

Fifteen added tests cover cold-load coalescing, repeated warm stats calls, empty cache, update/clear invalidation, failed-read recovery, stale-read races, independent health/generation deadlines, invalid health settings, concurrent health failure/recovery, and real local HTTP cancellation.

The real HTTP dependency tests include a server that never answers promptly, a server that trickles whitespace to keep a socket active, and a generation response that succeeds after the health request has already timed out. They use an 80 ms health deadline for test speed and retain the 1,800,000 ms generation configuration; a separate test checks the default 2000 ms health deadline.

Local verification passed: ESLint, TypeScript `--noEmit`, Nest build, and the entire backend suite (**85 suites / 1253 tests**). The real HTTP tests are included in that count. Agent guideline checks reported zero violations.

## Controlled before/after measurement

The local measurement harness loaded released implementations directly from `backend-v1.19.3` and compared them with working-tree classes, without overwriting either source tree. Both arms used the actual stats controller and assembly, CacheService, HealthCheckService and OllamaClientService. It started a dedicated Redis on a temporary Unix socket with persistence disabled, plus loopback-only HTTP fixtures; it never loaded application secrets or booted the crawler/application module. Services and temporary files were cleaned up at completion. The scratch benchmark script was absent from the working tree when release was authorized and is not shipped; the original measurements below remain preserved.

The fixture contains **1405 synthetic notices / 2,891,786 serialized bytes**, approximating the previously diagnosed three-megabyte cache. DB aggregation and crawler status are identical fixed fixtures in both arms. These results isolate the changed paths; they are not measurements of the full production application or production LCP.

Four warm-cache rounds used 20 measured requests per arm after warmup, with alternating arm order:

- Released: per-round request medians **7.23–8.46 ms**, p95 **11.82–15.49 ms**.
- Patched: per-round request medians **0.198–0.242 ms**, p95 **0.263–0.321 ms**.
- Recent-body reads per 20 requests: **20 → 0**, avoiding about **57.8 MB** of repeated logical payload reads per round. Small metadata reads still occur.
- Node-process CPU per 20 requests: **244–340 ms → 4.6–6.8 ms**. This counter includes the local HTTP harness but excludes the separate Redis process.

Two cold-health rounds issued eight concurrent stats requests against a `/api/tags` fixture delayed by 3000 ms, while retaining the 1,800,000 ms generation timeout:

- Released: request median **3008–3010 ms**, eight upstream health requests per round.
- Patched: request median **2005–2018 ms**, one upstream health request per round. Requests return HTTP 200 with health marked unhealthy rather than waiting for the fixture's late healthy response; `aiSummaryEnabled` remains true.
- All 192 measured HTTP responses preserved the asserted cache-size and AI-enabled contract. [Raw measurements](measurements.json) include CPU/event-loop data, each round's distribution, body reads and probe counts.

## Limits and reproduction

The first snapshot restore still reads the body once. This uses the same single-writer, process-local snapshot assumption already used by recent-list reads; it is not cross-process cache invalidation. A cold/expired health read may still wait about two seconds. Background Chromium work and the previously observed production event-loop stalls were not changed or remeasured in this phase. Production DB latency, host contention, Cloudflare latency and frontend LCP improvement cannot be inferred from the fixture timings.

## Jest process exit follow-up

The owner reported that passing tests still left the Jest process alive. A normal full run reproduced the warning: all 1253 tests passed, but the process exited **7692 ms after the summary**. `--detectOpenHandles` traced one `Timeout` to `NotificationDigestBuffer.enqueue()` at `notification-digest-buffer.ts:38`, called by the no-active-webhooks test in `fault-isolation.spec.ts:636` before the fix.

That suite stored its Nest TestingModule in a `beforeEach` local variable, and its teardown only cleared mocks. Consequently Nest never invoked `NotificationBatchService.onModuleDestroy()`, leaving the queued 30-second digest timer alive. The earlier cache/Ollama changes were not the source of this handle.

The notifier fault-isolation suite now retains and closes its module before resetting mocks, letting the real destruction hook flush pending notifications. A scoped fake clock verifies that the pending timer exists and that disposal leaves zero timers. A new regression also checks that queued work is dispatched exactly once during disposal. It does not sweep timers away or modify production digest behavior.

Validation: the affected fault-isolation suite and real Ollama HTTP suite passed **53 tests** with `--detectOpenHandles` and no handle report. The full ordinary suite then passed **85 suites / 1254 tests**, without an exit warning, and the actual npm child process exited with code 0 **158 ms after its summary**. ESLint, TypeScript and agent-guideline checks passed. No `--forceExit`, timeout-warning override or production change was used.

The first full diagnostic run's async-hook instrumentation also pushed the existing API-isolation heap-allocation check above its 10 MB threshold (16.1 MB). That diagnostic-only failure was kept separate from the timer cause; its threshold was not relaxed, and the full ordinary run passed it. [Exit evidence](jest-exit-verification.json).

Regression checks from `backend/`:

```bash
npm test -- --runTestsByPath src/modules/cache/cache.service.spec.ts src/modules/ollama/ollama-client.service.spec.ts src/modules/ollama/ollama-health-deadline.spec.ts
npm run lint
npx tsc --noEmit
npm run build
npm test
```


## Backend 1.19.4 release

The owner explicitly authorized deployment including existing external modifications. Backend PR [#222](https://github.com/vientofactory/LawCast-Backend/pull/222) includes the cache/deadline fixes, Jest teardown regression, and the owner's one-line deletion of `immutableSnapshot: true` from warning log metadata in `crawling-scheduler-pending-support.ts:637`. That deletion does not change archive snapshot immutability. The scratch benchmark script had been removed externally before release; the obsolete README command was removed rather than shipping a reference to a nonexistent file.

The signed implementation commit was `42b2aee6126e55272738ede78f681da038c6157f`. Squash merge and release `backend-v1.19.4` point to `ccdf0ad238a6171b22f33407b255cb7550bb5616`. Backend `dev` was fast-forwarded to the same release commit. Full `npm install` changed only the version fields in the committed lockfile; post-merge installation left the lockfile clean.

Release checks: backend lint, TypeScript, build and **85 suites / 1254 tests** passed with normal process exit and no open-handle warning. Frontend lint/check passed with zero diagnostics. Agent guideline checks passed. Sidecar lint/format and read-only capability report passed: 120420 chunks, 21786 indexed notices; index integrity OK. The first sidecar test run stalled in model revalidation and was stopped; offline mode used the cached model. The first offline run passed 344 tests and failed the unchanged real-model concurrency timing assertion (fastest 0.544 s versus 2 × 0.293 s baseline). No threshold was relaxed. A complete offline rerun then passed **345/345 tests in 61.92 seconds**.

Immediately before deployment, eight sequential origin `/api/stats` reads all returned HTTP 200: 71.783–169.552 ms (median 79.466 ms), with `/api/version` reporting 1.19.3. Raw before/after production evidence is retained in this session's release directory until verification is complete. These low-volume samples include real background activity and cannot isolate the patch's effect from host load.
