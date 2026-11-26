# Backend SQL audit and optimization

## Scope and evidence

Branch: `codex/sql-query-optimization`. Local source changes only.

The audit enumerates TypeORM and native SQLite calls across `backend/src`, including
workers, observation scripts and every registered migration. The final typed
inventory contains **259 runtime call sites in 18 files**, plus **275 migration
call sites**. These are source calls, not 534 distinct SQL statements: builder
operations and prepared-statement executions can belong to the same statement.
The initial name-only scan included array/cache calls; the typed inventory excludes
those false positives. `backend/scripts` contains no additional application SQL.

Raw inventory, generated SQL, bound parameters, EXPLAIN plans, benchmarks, source
hashes, counterexamples and test transcripts live in ignored `_workspace/sql-audit/`.
Reproduce enumeration with `node _workspace/sql-audit/inventory.cjs`.

Runtime owners reviewed:

- `modules/notice/notice-archive.service.ts`: archive lists, offsets, ranked hydration,
  identities, lifecycle/reconciliation, backfills, artifact candidates and guarded writes.
- `modules/notice/utils/notice-archive-maintenance-support.ts`: retry candidates,
  attempt stamps, recent cache seed, metadata/counts and summary-state updates.
- `modules/notice/utils/notice-archive-artifact-support.ts`: lazy artifact reads,
  integrity verification, exports, paged rescan and integrity-state writes.
- `modules/notice/notice-sitemap.service.ts`: consistent metadata snapshot and cache.
- `modules/notice/proposal-statistics.service.ts`: indexed date aggregation and cache coalescing.
- `modules/change-tracking/change-tracking.service.ts`: append/deduplication,
  timelines, latest values, event counts, recent changes and comparable summary.
- `modules/change-tracking/change-tracking-chain-audit.utils.ts`: paged full verification.
- `modules/change-tracking/chain-audit-child.ts`: readonly supervised audit connection.
- `modules/discussions/discussions.service.ts`: lists, comment cursors, transactional
  writes, closure and moderation.
- `modules/discussions/discussion-notification.service.ts`: quoted-comment lookup.
- `modules/notification/web-push-subscription.service.ts`: subscription/binding lookup,
  delivery bookkeeping, cleanup and statistics.
- `modules/notification/web-push-registration.service.ts`: thread existence lookup.
- `modules/webhook/webhook.service.ts`: indexed identity lookup, bulk registration,
  cleanup and conditional aggregate statistics.
- `modules/health/runtime-stats.service.ts`: coalesced archive/event transparency counts.
  Existing uncommitted health changes were preserved, not included in the patch.
- `modules/scheduling/cronjobs.service.ts`: scheduled SQLite maintenance.
- `modules/shared/sqlite-runtime-tuning.service.ts`: connection pragmas.
- `modules/db-mirror/database-dump-child.ts`: consistent allowlisted streaming dump,
  retained indexes/triggers and temporary output isolation.
- `scripts/proposal-reason-drain-observation.ts`: readonly diagnostic SQL.

All paths above are under `backend/src/`. Static coverage is exhaustive for these
source-call patterns; runtime timing is representative, not an execution of every
possible filter, historical migration or production write. Tests execute the real
complete schema and write invariants on disposable databases.

## Causes and changes

### Global history joins for bounded latest-value requests

`change-tracking.service.ts:1180-1290` now forces notice/event-first lookups with
SQLite CROSS JOIN. An ordinary INNER JOIN, even after `AS MATERIALIZED`, let the
planner start with all details for each requested field, then look up events.
The single-field batch API now reuses the existing bounded 200-notice multi-field
reader rather than maintaining a second unbounded global-window query.

Preserved invariants: event height before detail ID, latest explicit NULL/blank
clears versus latest nonempty history, trimmed single-field versus raw multi-field
values, absent map keys, duplicate IDs/fields, empty inputs, bound parameters and
single-field fallback on batch failure. No event append/hash/notification rules changed.

### Partial-index predicates and lifecycle-ordered candidate scans

`notice-archive.service.ts:3306,3335,3587` emits native `IS NOT NULL` for PAL
content IDs. TypeORM's `Not(IsNull())` emitted `NOT(contentId IS NULL)`, which did
not imply the existing partial-index predicate to SQLite's limited theorem prover.
`notice-archive-maintenance-support.ts:111` uses the equivalent
`COALESCE(TRIM(proposalReason), '') = ''` term shared with the retry index.

`202611260001-optimize-archive-maintenance-indexes.migration.ts` replaces the four
existing missing-HTML/screenshot indexes with `(lifecycle_status, noticeNum)`
partial indexes and adds one partial retry index on lifecycle and the existing
attempt-count/time/number order. The old plan scanned every active archive and
sorted candidates; the new plan seeks the partial index without an ORDER BY temp
B-tree. Historical reason/deletion EXISTS exclusions remain intact.

The four replacements remain one 4 KiB page each on the local snapshot; the new
retry index uses nine pages, **36 KiB**. This is one additional index, not five
additional indexes. Writes to retry stamps now maintain that small index.
Migration down restores the original four definitions and removes the retry index.
No archive data, immutable/FTS triggers or schema columns change. Old application
queries remain valid with the new indexes and new queries work with old indexes.

### Unbounded quote lookup

`discussion-notification.service.ts:29-36` previously loaded every comment and
password/content columns in a thread before filtering references in JavaScript.
The query now seeks `(thread_id, sequence)` for the referenced numbers and projects
only fields needed for eligibility. A 3,000-comment SQLite fixture hydrates six
candidates instead of 3,000, preserving self/deleted/system/admin/other-thread
exclusions, duplicate-reference handling and per-quoted-comment delivery.

### Offset filter overwrite and duplicate empty-page reads

`notice-archive.service.ts:2722` previously selected an isDone-filtered page, then
fell through to an unfiltered query whenever that page was nonempty. Empty pages
could repeat the same filtered selection. Supplying `knownTotal` changed behavior.
The branch now chooses filtered or unfiltered selection exactly once. This fixes
an existing intent violation, not merely a timing change: unknown-count requests
now honor the same isDone contract as known-count requests.

Tests cover both booleans and sort orders, known/unknown totals, skip/take,
missing summary rows, empty pages, and count-only requests. The old source fails
three of the four new tests; the changed source passes all four.

## Measurements and result equivalence

SQLite backup created a consistent disposable copy of the local 6.1 GiB database:
**22,856 archives, 53,241 events and 322,502 details**. The source database was opened
readonly/query_only; no source migration, ANALYZE, VACUUM or data rewrite ran.

Five sequential executions per case, with the same service inputs and database
contents, yielded these local medians (baseline → modified, milliseconds):

- Latest value: **2.603 → 0.029**; latest nonempty history: **27.812 → 0.029**.
- 50-notice single-field batch: **4.610 → 1.379**.
- 50-notice six-field batch: **5.635 → 2.145**.
- Retry candidates: **42.047 → 1.741**.
- PAL screenshot candidates: **18.856 → 0.118**.
- NSM screenshot candidates: **20.396 → 0.076**.
- PAL + NSM missing HTML: **32.370 → 0.245**.

All **14 representative service result digests** match the original and the
schema-rollback run. Across **all 22,856 archives**, all six requested latest fields
and the normalized latest proposal reason match byte-for-byte as serialized maps.
That whole-corpus multi-field read took 2,452 ms versus 424 ms in the recorded
single parity execution; this is parity evidence, not a statistical latency claim.
The offset contract repair is separately tested against expected results rather
than claimed byte-identical to the erroneous original.

Timings are local warm/mixed-cache service measurements, not production SLOs or
cold-storage guarantees. Early first executions and all five samples remain in
JSON. Search/count timings varied (about 30–50 ms), and no search improvement is
claimed; the substring OR FTS search contract is intentionally unchanged.

## Existing heavy work retained deliberately

- Date statistics already use the date covering index, five-minute cache and
  in-flight coalescing. Local cold-cache aggregation still costs roughly 0.9 s;
  the local SQLite `localtime` conversion is expensive (about 11.8 ms without the
  modifier versus 1.10 s with it in a diagnostic comparison). Removing it or
  grouping UTC dates would change timezone/week boundaries. No such rewrite was made.
- Broad LIKE substring searches cannot be replaced with token-prefix FTS alone
  without losing existing matches. No speculative wide covering index was added.
- Full archive export, integrity hashing, whole-chain audits and mirror copies
  inherently read history/artifacts. Existing pages, yields, readonly snapshots,
  worker isolation, cancellation and consistency were preserved.
- Discussion transactional sequence allocation and webhook per-row registration
  retain their atomicity/reactivation contracts. Small subscription statistics
  were not changed merely to reduce query counts.

## Regression proof and rollback

- Original source copy: 108 suites / 1,451 tests passed.
- Modified source: 112 suites / 1,461 tests passed.
- Restored source copy: 15 affected suites / 233 tests passed; original source hashes restored.
- New real-schema latest-value tests fail on the original plan; the quote fixture
  fails on original hydration (3,000 versus six); the offset fixture fails on
  original filter/empty-page behavior. They pass on the modified implementation.
- Migration up/down/up preserves ordered candidates, all archive rows, trigger
  SQL, original index definitions on down, and `PRAGMA integrity_check = ok`.
- Backend lint, both TypeScript compilers, build, frontend check (zero errors and
  warnings), agent guidelines and diff whitespace checks passed.

The first unrestricted full run exposed an existing test's assumption that the
metadata-trigger migration was always newest. That test now rolls back through
the named migration; all old immutability assertions remain. Initial sandbox
loopback EPERM failures were resolved by rerunning the same full tests with local
HTTP/gRPC ports available; no tests or runtime matrices were removed.

Exact commands, outputs, exit statuses, hashes, package/diff paths and copy-only
rollback instructions are in `_workspace/sql-audit/VERIFICATION.txt`. Source and
candidate DB remain modified; only disposable rollback copies were restored.
The initial audit phase performed no commit, version bump, PR, release or deployment.
The subsequent owner-authorized [3.2.9 release](release.md) records the completed deployment.
