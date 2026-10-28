# Frontend API consumption and SQLite contention

## Scope and baseline

Local-only follow-up to [the API tail investigation](../58-api-tail-db-queue/verification.md) and [the post-release findings](../58-api-tail-db-queue/release-verification.md). No SSH, production configuration changes, migrations, release, push or deployment were performed in this session. All browser checks used local targets; the first legacy-suite invocation reused an existing development server and was replaced by an isolated mock-only run. The dedicated consumer suite always uses a separate fixture API and production Node SSR build.

Backend baseline: `backend-v1.19.5` / `b3f9aa9af898dd80093fff5d1bafe2eff6964980`. Frontend baseline: `5888b7d501fc99f5aed4b167585fcb3c4b49b56d` (1.25.3). Both local changes are on `codex/frontend-api-sqlite-performance`. Versions are unchanged because this is not a release.

## Consumption paths and findings

### Home and shared layout

`frontend/src/routes/+page.server.ts` concurrently loads recent notices, eight keyword suggestions, statistics, five discussion threads and one pinned announcement. The shared layout independently loads the urgent announcement and backend version. The home previously requested the full `/api/stats` before slicing its four displayed sections, so removing unused serialized properties did not remove the server work.

`backend/src/modules/health/runtime-stats.service.ts:169` now provides `/api/stats?view=home`: archive count, cache last-update time, comparable change-event total and AI enablement. It omits webhook, web-push and crawler operational collection and does not wait for an Ollama health check. The frontend client and home loader consume this additive view. Default `/api/stats` remains compatible. API documentation and a real SSR HTTP fixture establish the new contract.

### Notice list and detail

Archive lists already use `NOTICE_ITEM_SELECT`; discussion list joins already select notice number and subject. Detail artifact support already avoids loading HTML/screenshots for complete metadata, and the default detail route does not request the full revision timeline. These paths were reviewed and preserved rather than rewritten.

`backend/src/controllers/api.controller.ts:334` formerly awaited Ollama metrics simply to expose `aiSummaryEnabled`. It now uses the same configured enablement boolean as the Ollama client. This removes a possible cold health-probe deadline from notice detail without changing generation timeouts or health monitoring. Regression checks assert that the actual `HealthCheckService.getOllamaMetrics` dependency is not called.

### Change summaries, proposal statistics and transparency

Home, status and the changes page can overlap their comparable-summary reads. `backend/src/modules/change-tracking/change-tracking.service.ts:1626` replaces two sequential counts with one `COUNT(*)` / `COUNT(DISTINCT notice_num)` query and shares only the current in-flight query. Later requests execute afresh; there is no new TTL. Real-schema tests cover baseline-height exclusion, distinct notice counts, twenty concurrent callers, independent returned objects, newly appended events and recovery after failure.

`backend/src/modules/notice/proposal-statistics.service.ts:43` and `backend/src/modules/health/runtime-stats.service.ts:299` had five-minute caches but no protection against simultaneous cold misses. Proposal statistics now coalesce per complete filter key; transparency shares its current read. Existing TTLs and query semantics are unchanged, and `finally` clears failed reads. Twenty simultaneous transparency requests now launch one set of five aggregations rather than twenty sets. Tests cover key independence, failures and subsequent cache snapshots.

The existing proposal period/time-zone formatting was preserved. This audit does not claim to resolve a separate calendar-formatting issue or to eliminate every cold aggregate scan.

### Status refresh

`frontend/src/routes/status/+page.server.ts` declares `app:system-stats`. Manual, timer and retry refreshes invalidate this dependency instead of `invalidateAll()`. This keeps refreshing the displayed operational statistics while avoiding an unrelated shared-layout announcement/version reload. Desktop and mobile browser tests observe the actual SSR API paths before and after refresh.

## SQLite writer contention

`stampNsmListSeen` updates operational metadata on the same `notice_archives` rows that hold large immutable HTML/screenshots. The original `BEFORE UPDATE` trigger compared protected values even when the statement touched only last-seen metadata. A consistent local SQLite backup (~5.5 GiB) reproduced the cost without modifying the source database.

The new migration `backend/src/migrations/202610280001-optimize-archive-metadata-updates.migration.ts` scopes the existing trigger to its existing protected columns with `BEFORE UPDATE OF`. It preserves the exact predicate and abort body, including first-fill and lifecycle rules. It also includes `rowid`, `_rowid_` and `oid`: SQLite can change an INTEGER PRIMARY KEY through those aliases. Unsupported or missing definitions fail closed. Rollback restores the original trigger header. The migration is registered but was applied only to in-memory fixtures and a disposable backup.

`backend/src/modules/notice/notice-archive.service.ts:233` reduces last-seen write batches from 400 to 100 rows and yields between batches. This bounds the SQL statement holding the shared connection and lets queued frontend reads progress. Counts, monotonic timestamps, duplicate/invalid-ID handling and immutable snapshots are retained. A real-schema 205-row regression verifies multiple batches, newer sightings and snapshot preservation.

The FTS trigger was inspected and ruled out: it already restricts updates to its indexed text columns. No FTS trigger change was needed.

## Local measurements

[Raw shared-connection measurements](shared-db-results.json) use actual baseline/patched `NoticeArchiveService.stampNsmListSeen` and TypeORM against the same disposable backup, sequentially updating the latest 2,000 rows. Each arm changes all 2,000 timestamps and verifies all 2,000 persisted. Forty archive-count probes share the same SQLite connection, separated by a 1 ms timer. Both arms use identical connection/journal configuration (`synchronous=NORMAL`); the patched arm applies the new trigger and 100-row batches. This is a DB contention experiment, not a complete Nest HTTP or production latency measurement.

Arm order is baseline, patched, patched, baseline, baseline, patched. No full test suite or frontend build ran concurrently during this final measurement. The first baseline pass was colder: total write 1,584 ms, read p95 242 ms, maximum 604 ms. Do not attribute its entire improvement to the patch.

The two later baseline passes took 229–231 ms, with read p95 32.3–33.1 ms and maxima 99.7–100.1 ms. The three patched passes took 160–165 ms, with p95 16.4–17.8 ms and maxima 27.2–28.7 ms. This supports reduced local queue occupancy under these conditions, not an equivalent percentage reduction in production LCP.

[Alternating trigger-only measurements](trigger-vm-results.json) on genuine 400-row updates show approximately 101,000–102,000 SQLite VM instructions with the original trigger versus 21,000–22,000 with scoped protection. Warm elapsed times overlap (baseline 40–43 ms versus scoped 32–40 ms); disk/page rewrite costs remain. An earlier non-alternating cold comparison and an experiment concurrent with checks were exploratory and are not the improvement claim.

### Reproduction

Run from the repository root to create a disposable, consistent backup. It needs several GiB of free space. Never use the original database as the benchmark write target.

```bash
python3 - <<'PY'
import sqlite3
with sqlite3.connect('file:backend/lawcast.db?mode=ro', uri=True) as source:
    with sqlite3.connect('/tmp/lawcast-consumer-copy.db') as copy:
        source.backup(copy)
PY
cd backend
LAWCAST_BENCH_DB=/tmp/lawcast-consumer-copy.db node ../agent_memories/59-frontend-api-sqlite-audit/shared-db-benchmark.cjs
```

The harness requires a backup from the baseline trigger schema, reads the source only with `OPEN_READONLY`, refuses the source path as a write target, and loads the baseline service from the release tag. Results default to `/tmp/lawcast-shared-db-benchmark.json`; `LAWCAST_BENCH_OUTPUT` overrides the result file. It writes artificial future timestamps only to the disposable backup, so never promote that backup to an application database.

## Regression verification

- Backend lint, TypeScript, build and full Jest: 87/87 suites and 1,273/1,273 tests passed in 39.77 seconds. The Jest process exited normally without force-exit or an open-handle warning.
- Immutable archive regression: protected changes and all rowid aliases reject mutations; permitted first-fill/lifecycle transitions remain valid; rollback/reapplication works. `EXPLAIN` verifies metadata-only updates have no protection-trigger program, while 512 KB HTML and BLOB artifacts remain unchanged.
- Frontend lint and Svelte check: zero errors and warnings; production Node build passed in the consumer suite.
- Dedicated real SSR consumer suite: 6/6 desktop/mobile checks passed. Command: `cd frontend && npx playwright test --config playwright-configs/playwright.consumers.config.ts`.
- Existing mock-only home/status suite: 35/35 passed on isolated port 4198. The default configuration's `reuseExistingServer` initially reused a non-mock server on 5173, causing one status assertion to see an API rate-limit fallback. No application workaround was introduced; the isolated run supplied the intended fixtures.
- The first sandboxed full backend test attempt failed because existing HTTP tests could not bind localhost (`listen EPERM`). The subsequent run with local socket access passed and exited normally; tests were not disabled or weakened.

## Limits and next release considerations

The patches reduce confirmed consumer work and contention; they do not establish that all production tails are gone. Large archive-row rewrites, other background writers, filesystem/cache behavior and external connection/Cloudflare delays remain outside this local verification. Separating mutable operational state from immutable artifact storage is a larger architectural option if production measurements still show row-rewrite contention.

For a future authorized release, the backend migration and additive stats view must be deployed before the frontend starts requesting it. Follow the repository's version, PR, signed-commit, submodule-pointer and deployment verification procedure. No such release was requested here.
