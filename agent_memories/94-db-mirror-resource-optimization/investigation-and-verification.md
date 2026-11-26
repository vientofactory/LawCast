# Database Mirror Resource Optimization

## Investigation

Date: 2026-11-25 (Asia/Tokyo). The owner approved deployment followed by one observed upload before deciding whether to restore recurring mirroring.

The current production backend and local baseline both used backend commit `2db310a` (3.2.6). Production configuration had `FILE_MIRROR_ENABLED=false`, startup testing off, dump retention off and no mirror announcement channel. The host had four CPUs, 7,935 MiB RAM and approximately 3.3 GiB used swap. Available RAM was approximately 3 GiB. The backend had no cgroup memory/CPU quota, was healthy, and had zero current restart/OOM counters. Its cgroup lifetime memory peak was 4,645,584,896 bytes, encompassing API and browser workers, not just mirroring.

**Historical attribution remains incomplete.** The retained current-container logs only show disabled mirror scheduling. The available kernel query found no matching OOM records. Current counters do not establish what happened to older containers. Earlier process isolation already prevents synchronous SQLite work from directly blocking the API event loop; it does not eliminate shared host CPU, I/O or memory competition.

The baseline dump worker performed `VACUUM INTO` over the whole database, dropped non-allowlisted tables, then ran a second full `VACUUM`. The live production database was about 6 GiB (1,575,762 pages of 4,096 bytes). A local 6 GiB snapshot had 4,852.9 MiB in `notice_archives`, 818.9 MiB in 3,765,006 integrity-check rows, and approximately 301.9 MiB in that table's two indexes. Removing HTML/screenshots or historical integrity records would change the dataset contract, so this work does neither.

## Implementation and invariants

Backend PR [251](https://github.com/vientofactory/LawCast-Backend/pull/251), release `backend-v3.2.7`, commit `a8815cd3b9483680106e420f50dbc475182420bb`.

- `backend/src/modules/db-mirror/database-dump-child.ts` creates only the existing six allowlisted tables, streams one row at a time from a read-only/file-must-exist connection, and builds indexes/triggers after copying. Private data and FTS shadow tables never enter the output file.
- One source read transaction covers schema, all tables, sequence high-water marks and database metadata. It is released before destination index building, avoiding additional WAL pinning during index sorting.
- Raw statements use safe integers so values above JavaScript's exact-number range remain unchanged. BLOBs, generated-column handling, index SQL, append-only triggers, `sqlite_sequence`, `user_version` and `application_id` are preserved.
- Each SQLite connection gets an 8 MiB page-cache target, mmap is disabled, sort temporary storage uses files and index worker concurrency is limited. Linux dump priority is lowered. These are **not a total-process memory hard limit**.
- `DbMirrorService.runMirrorJob()` holds admission through dump, upload and cleanup, rather than allowing a second dump while a previous upload remains active. Failure releases admission.
- Existing child timeout, shutdown cancellation, atomic destination reservation, reaping-before-cleanup and partial-file cleanup remain intact. No application schema, migrations, provider API, recurring schedule or production environment setting is changed.

## First-stage local verification

Originals, hashes, raw logs, full-row digests and executable copy-only rollback are retained under ignored `_workspace/db-mirror-20261125/`.

| Check | Result |
| --- | --- |
| Baseline mirror tests | 4 suites / 21 tests passed |
| Changed mirror tests | 4 suites / 24 tests passed |
| First-stage full backend tests | 106 suites / 1,428 tests passed |
| Lint, TypeScript 6, native TypeScript, build | Passed |
| Frontend check and agent guidelines | Passed; guideline violations 0 |
| Independent rollback copy | All 10 original file hashes restored; 4 suites / 21 original tests passed |
| Real-snapshot parity | Every row/BLOB digest, all table/index/trigger SQL and sequence values match baseline; quick_check and foreign keys pass |
| Source SHA-256 before/after final run | `2fc7575be98c27d6698eb281f5303079f770c4265df38b7c773e9ecb370ba189` unchanged |

Regression tests cover committed WAL visibility versus in-flight writes, cross-table snapshot consistency while a writer commits, exact 64-bit values, BLOBs, private-data exclusion, trigger enforcement, metadata logging, overlapping jobs, timeout, shutdown and cleanup/retry.

Local native-child phase totals on the same real snapshot:

| Arm | Phase sum | Child peak RSS |
| --- | --- | --- |
| Baseline | 94.854 s | 88.7 MiB |
| Initial candidate | 66.520 s | 139.1 MiB |
| Final code | 63.919 s | 142.2 MiB |

These are sequential local measurements, not a controlled production benchmark. Cache state and concurrent work differ. Phase sums exclude worker startup and the final destination commit. The improvement is fewer full-database rewrites and lower phase elapsed time, **not lower measured peak RSS**. A separate 32 MiB V8-heap experiment still peaked at 140.0 MiB overall, so that heap change was not shipped. Native SQLite and BLOB allocation remain outside the V8 limit; the worker exits to release its complete working set.

Initial broad tests inside the restricted environment failed socket-binding cases; the unrestricted full run and final release-state run both passed all 1,428 tests. An initial rollback test filter matched the scratch parent directory; that run was stopped and rerun using the anchored module-path regex, with all 21 original tests passing. No test assertions were relaxed.

## Deployment and production observation

Both deployment/observation stages are recorded below. Scheduled mirroring remains disabled.

## First production result and upload follow-up

Backend 3.2.7 shipped via root PR [72](https://github.com/vientofactory/LawCast/pull/72), root main `aed4d26004f102fdd7b986010bf8785715433a32`, push run [45485473949](https://github.com/vientofactory/LawCast/actions/runs/45485473949). Both deployment jobs succeeded, and the actual origin reported 3.2.7 with a healthy container. The owner explicitly confirmed the destination and six-table payload before any external upload began.

The controlled extra Node parent instantiated the deployed dump/upload/mirror services without booting a second Nest application or crawler. Its upload path was the same native client then wired into the API, but its heap limit was 128 MiB; this is not a guarantee for the API's different heap/lifetime. The run completed successfully at 06:18:09 JST after 561.008 seconds: dump wait 205.934 s, upload 354.693 s. Upload parent RSS high-water was **802.7 MiB** and its event-loop maximum delay was **749 ms**. Because scheduled uploads still executed that client inside the API process, snapshot optimization alone was insufficient to recommend reactivation.

All 513 monitored origin requests returned HTTP 200 (49 before / 110 during / 12 after samples of each endpoint). During-run stats p95 was 122.10 ms, maximum 205.98 ms. The non-DB version endpoint had a 2,563.97 ms outlier. A scheduled chain-audit child also ran, so these observations are not a controlled isolation experiment. Minimum host available memory was 1,775.6 MiB; backend cgroup maximum was 3,167.7 MiB. There were no OOM events/restarts, and the dump directory was empty after completion. The remaining source WAL was 634.9 MiB; its peak was not sampled in the first run.

The owner then approved upload isolation, another release, and exactly one additional encrypted upload of the same six tables to file.kiwi. Recurring mirroring remains explicitly disabled.

### Upload isolation implementation

Backend PR [252](https://github.com/vientofactory/LawCast-Backend/pull/252), release `backend-v3.2.8`, commit `82c95265ba87c42c09db7c187f95b5729f9378a4`.

- `FileKiwiUploadWorkerService` owns a disposable encryption/upload process, a 128 MiB V8 heap target, bounded stdout/stderr protocol, overlap/shutdown admission and a configurable 30-minute whole-job deadline (`FILE_MIRROR_UPLOAD_TIMEOUT_MS`). Native allocations remain outside the heap limit.
- The API module injects the worker, not the raw `FileKiwiClientService`. The worker does not inherit application/bot credentials, `NODE_OPTIONS` or the API allocator preload; it preserves selected explicit HTTP(S) proxy/CA configuration. It lowers Linux priority, then reuses the existing client and cryptographic library without changing the provider protocol.
- Each HTTP request has an abort deadline (60 seconds for control requests, 120 seconds for a chunk). One plaintext buffer is reused, short reads loop until complete, premature EOF fails rather than encrypting padding, and ciphertext views are sent without another full buffer copy.
- An abort callback alone is not proof of process exit: the parent always waits for `close` before resolving/rejecting and allowing the mirror's cleanup to remove its input file.
- Existing immutable archive, source snapshot, encryption, share-link and notification semantics are retained. The worker terminates to return its complete native working set; no low total-RSS hard cap or host-wide latency guarantee is asserted.

Final local gates passed: **108 suites / 1,440 tests**, lint, both TypeScript compilers and build. Focused mirror tests passed **6 suites / 36 tests**, including a real native-encryption/v2-protocol loopback provider, buffer/view/EOF checks and process lifecycle/protocol/error tests. Combined original-3.2.6 rollback restored **16 original file states** (12 original hashes plus deletion of four added files), then passed all 21 original tests. No assertions or supported Node runtimes were removed.

Intermediate benchmark SQLite outputs totaling 25,685,467,136 bytes were deleted after full digest/integrity comparison; code artifacts, manifests, original sources, raw logs and reproduction scripts remain. The original local DB was not deleted or changed.

## Final production result — 3.2.8

Root PR [73](https://github.com/vientofactory/LawCast/pull/73), root main `09753fb1e6ad595ccec896139a8457af16c86537`, push run [45495115688](https://github.com/vientofactory/LawCast/actions/runs/45495115688). Both deployment jobs succeeded, the deployed backend pointer equals the release tag, and the actual origin reports 3.2.8. A PR validation check initially exposed inconsistent GitHub status metadata (success/concluded timestamp but still in_progress); CI was re-executed rather than bypassed. A final gh-watch network-read error was resolved by fetching the completed successful run JSON; deployment was not repeated.

The second explicitly approved upload completed at **07:13:08 JST**, exit 0, producing/uploading a **6,415,294,464-byte** sanitized SQLite file. Total duration was 595.996 s: dump wait 270.387 s, upload including worker startup/exit 325.186 s. These timings are not a controlled speed comparison with the first run.

| Upload measurement | 3.2.7 native-client caller | 3.2.8 worker caller |
| --- | --- | --- |
| Caller process RSS high-water | 802.7 MiB | 159.6 MiB |
| Caller upload sampled RSS peak | 736.1 MiB | 132.7 MiB |
| Caller RSS after upload | 619.5 MiB | 86.0 MiB |
| Caller upload event-loop maximum delay | 749 ms | 31 ms |

**The upload child's own peak remained 800.6 MiB.** This work isolates the API/caller and returns the worker's complete native memory on exit; it does **not** demonstrate a lower whole-job instantaneous memory peak. Reducing that peak further would require investigating the provider chunk/crypto buffering path, such as a protocol-compatible streaming implementation. The library and buffers, allocator environment and process lifetimes are not independently controlled in these two observations.

### Remaining API/storage contention — do not reactivate automatically

The second observation recorded 556 origin probes: 555 HTTP 200 responses and **one five-second version timeout**. During the dump copy, the actual API's two-second event-loop monitor reported a **6,900 ms** window maximum. This is separate from the mirror caller's 31 ms upload-phase delay: the pause happened at 07:04:47–07:04:53 JST, **before upload began at 07:07:43**.

Matching main-container logs show pending sync finishing at 07:04:41.409, full archive sync starting at 07:04:41.503, then its first page log at 07:04:53.113. The main API process accumulated about 187 MB of physical reads in the adjacent sampled interval while the dump was concurrently scanning. This supports synchronous archive/database work plus shared-storage contention as a leading hypothesis, not a uniquely identified SQL statement or proof that mirroring alone caused the stall. No main-process swap was recorded at that sample. The dump caller's own maximum loop delay was only 32 ms.

Other observations:

- Stats during-run p95 191.34 ms / maximum 221.16 ms; health p95 182.83 ms / maximum 967.71 ms. Post-run version/health/runtime p95 returned below 5 ms and stats p95 was 33.62 ms. These sampled endpoints do not establish an all-traffic latency SLO.
- Minimum host available RAM 2,366.5 MiB; maximum backend cgroup memory 3,268.6 MiB. The same backend container remained healthy, restart count 0, with no OOM events.
- Sampled WAL physical size grew from at most 3.7 MiB before the run to 241.3 MiB. The source read transaction still ends before destination indexing; physical WAL size is not the same as the count of uncheckpointed live frames.
- Semantic-search cgroup swap rose from 1,995.8 to 2,047.3 MiB. No uncached inference latency experiment was performed, so no semantic-search latency guarantee is claimed.
- Both mirror workers and the controlled parent exited; the local dump directory was empty. Production `FILE_MIRROR_ENABLED=false` and startup testing remain unchanged, as explicitly requested.

**Final recommendation: keep recurring mirroring disabled.** The deployed snapshot and upload isolation improvements are verified, but safe recurring overlap with ongoing crawling/storage work and the approximately 800 MiB upload peak are not resolved by these changes. Any next phase should explicitly decide the acceptable data-freshness/resource tradeoff for non-overlapping background jobs and investigate streaming crypto before claiming a low total memory budget. Historical container-interruption attribution remains incomplete.

## Source evidence references

- Snapshot transaction and source release: `backend/src/modules/db-mirror/database-dump-child.ts:70-179`, including read-only opening, `BEGIN`, safe-integer row iteration and `COMMIT` before indexes.
- Whole-job admission and worker injection: `backend/src/modules/db-mirror/db-mirror.service.ts:15-61`, and `db-mirror.module.ts:4-10`.
- Bounded child execution and reap-before-cleanup: `backend/src/modules/db-mirror/file-kiwi-upload-worker.service.ts:80-104` and its `close` handler.
- Buffer reuse and request abort deadlines: `backend/src/modules/db-mirror/file-kiwi-client.service.ts:152-164,252,288,310`.
- Concurrent full-sync entry: `backend/src/modules/crawling/utils/archive-sync-phase-executors.ts:919`. Timestamp proximity and sampled I/O identify a hypothesis, not a traced individual SQL statement.

```typescript
source.exec('BEGIN');
// All allowlisted row/sequence reads share the pinned source snapshot.
source.exec('COMMIT');
// Destination indexes are then built without pinning the live WAL.
```

```typescript
child.once('close', () => {
  // Only a reaped worker can release admission and allow input-file cleanup.
});
```
