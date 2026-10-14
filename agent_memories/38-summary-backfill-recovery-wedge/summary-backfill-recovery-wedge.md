# AI Summary Backfill Recovery Pass Wedges at the First Inactive Row

Third production defect found on 2026-10-14, while verifying the user's question
"do LIKMS-sourced rows whose `제안이유` arrives in a later revision actually ride the AI
summary backfill?". **Answer: the pipeline path exists and works, but the recovery pass
that serves exactly this case stops after the first page that the ACTIVE-archive join
shortens — so most later-revision rows can never be summarized.**

Measured against production (`law.viento.me`, backend `1.15.4`, container DB read-only over
SSH) and reproduced exactly by simulating the collector itself.

## 1. What is verified working

- `aiSummaryEnabled: true`, Ollama healthy (`exaone3.5:2.4b`), production counts:
  `ready 21,114 / not_supported 377 / not_requested 3`.
- **Reason present when the summary pass reaches the row works.** `2221891` (LIKMS row) is
  `ready` with an 80-char summary from a 732-char head-revision `제안이유`;
  `2221894`–`2221896` turned `ready` on 2026-10-14 10:10–10:12 from the crawl-cycle path;
  `2220952` (`contentId IS NULL`, archive column empty, chain reason 586 chars) is `ready`.
- **Chain fallback is real**: `resolveSummaryBackfillCandidates` resolves `proposalReason`
  from the diffchain for `contentId IS NULL` rows
  (`NoticeArchiveService.getLatestProposalReasonsForNotices`), and
  `SummaryGenerationService.generateSummaryForNotice`'s no-`contentId` branch prefers that
  resolved reason.
- The bootstrap pass drained its whole queue with no failures:
  `Summary backfill apply batch done: ... failed=0` up to `queueRemaining=0`,
  `Summary backfill staged - scanned=209 stagedPending=209 retryScanned=0 stagedRetry=0`,
  `summaryBackfillProcessedTotal: 209`.

## 2. The defect

For a row whose `제안이유` lands in a **later** revision (the LIKMS backlog case: archived
with an empty reason, repaired into the diffchain afterwards), the only path that can
summarize it is the `not_supported` recovery scan
(`getNotSupportedSummaryRecoveryPage` → `collectSummaryBackfillCandidates(NOT_SUPPORTED, …,
row => !row.contentId)`). That scan is wedged in production.

**Mechanism.** `collectSummaryBackfillCandidates` (`notice-archive.service.ts:1747-1782`)
pages over `notice_archive_snapshot_states` ordered by `notice_num ASC` and treats a
**short page as end-of-data**:

```ts
const rows = await this.getSummaryPageByStatus(status, rawSkip, pageSize); // post-join rows
...
if (candidates.length >= pageSize || rows.length < pageSize) break;        // line 1777
```

`getSummaryPageByStatus` joins the archive row **filtered by
`lifecycleStatus: NOTICE_LIFECYCLE_STATUS.ACTIVE`**, so any page containing a
`source_deleted`/`renumbered` (or missing) archive row comes back one row short *by design*.
The staging loop copies the same mistake
(`archive-sync-phase-executors.ts:1581-1610`, `if (batch.length < options.summaryBackfillBatchSize) break;`),
so one short page ends the whole recovery pass — permanently, on every run.

**Live trigger.** Production `2214911` is `not_supported` **and** `source_deleted`, sitting in
this 5-row window (`ARCHIVE_SYNC_SUMMARY_BACKFILL_CPU_BATCH_SIZE=5`; the drain is in
CPU-friendly mode):

```
2214749 active | 2214788 active | 2214857 active | 2214911 source_deleted | 2214912 active
```

**Exact reproduction.** Simulating the collector + staging loop over the production
`not_supported` list (377 rows, fetched read-only) prints:

```
staged candidates: 209 | stop: (210, 'short batch')
max staged num: 2214912
  is 2214911 staged? False      is 2220952 staged? False
  is 2221042 staged? False      is 2221131 staged? False
unreached active-null-cid rows: 143
```

`209` matches the production log line and `summaryBackfillProcessedTotal: 209` exactly, and
the stop point matches the window above.

## 3. Consequence

- **143 active `not_supported` rows with `contentId IS NULL` and `notice_num > 2214912` are
  unreachable by the recovery pass** — every affected LIKMS row (`2219xxx`, `2220xxx`,
  `2221xxx`). Live example: `2221042` renders a 3,863-char `제안이유` in its head revision
  (`GET /api/notices/2221042/detail`) yet reports `aiSummaryStatus: not_supported` with no
  summary; its summary state has not been touched since 2026-09-16.
- This is the summary-side twin of the previous-revision overlay bug
  (`agent_memories/36-detail-chain-head-overlay/`): the detail page now shows the recovered
  reason, but the summary never follows because the queue entry is never staged.

## 4. Adjacent gaps found while verifying

- **The periodic trigger never runs.** `proposalReason backfill drain`
  (`PROPOSAL_REASON_BACKFILL_DRAIN`, `9-59/15 * * * *`) — the only recurring caller of
  `runSummaryBackfill` besides bootstrap — reports `lastRunAt: null` for the whole container
  uptime (skipped by `shouldSkipProposalReasonBackfillCron` while write-heavy archive-sync
  phases are active). In practice the summary backfill runs **only at container start**, so
  even a fixed stale-recovery pass would still be restart-gated.
- **`contentId`-set rows are excluded from recovery by design**
  (`row => !row.contentId`). Production has 22 such `not_supported` rows (2 active with a
  later-revision reason in the chain). For those,
  `generateSummaryForNotice` re-reads PAL live (`crawlingCoreService.getContent(contentId)`)
  and ignores the chain, so a row whose reason arrived later stays `not_supported` even
  though the chain holds it. The generator half of this is fixed in §9; the staging filter
  is still open.

## 5. Fix status

1. **FIXED in `backend-v1.15.5`** — the cursor now advances over the summary-state rows and
   hydrates one page at a time (`readSummaryBackfillCursorPage` returns
   `{ cursorCount, rows }`; only `cursorCount` is compared against the page size). See §7.
2. **Generator FIXED (`backend-v1.15.6`, §9)** — `generateSummaryForNotice`'s `contentId` branch
   resolves the reason through the new `resolveSummaryProposalReason` (live payload →
   caller-resolved value → chain head) instead of trusting the PAL payload alone.
   **Still open** — the `!row.contentId` recovery filter keeps those rows out of the
   backfill scan, so the 22 historical `not_supported` rows stay stuck until the scan
   accepts them (rows re-entering the crawl/proposal-retry path are covered by §9).
3. **FIXED (`backend-v1.15.6`, §10)** — the 15-minute tick no longer puts the summary backfill
   behind the crawl/browser guard, and a deferred summary backfill logs at production level
   instead of `debugDev`. Confirmed live in production (§11.2): the tick now fires on the
   cadence, staging `scanned=340 stagedPending=315` per pass. Open question left behind:
   whether a 15-minute cadence with a CPU-friendly batch size keeps up with the LIKMS reason
   backlog.
4. **FIXED (`backend-v1.15.6`, §11)** — the summary-state bulk upsert now stamps `updated_at`,
   so the rows one pass processed are identifiable by timestamp; audited against the
   production DB in §11.2.

Note for future edits: the recovery pass can stay an offset walk only because the apply worker
starts after staging completes. If a pass ever writes summary states while it stages, it must
become a `skip=0` drain loop instead.

## 6. Verification method

Read-only: public API (`/api/version`, `/api/stats`, `/api/crawling-transparency`,
`/api/notices/:num/detail`), container logs (`docker logs lawcast-backend`), and
`sqlite3 -readonly` against the production volume
(`/var/lib/docker/100000.100000/volumes/lawcast_lawcast_db/_data/lawcast.db`). No writes. The
production host is reachable as `root@10.20.0.1` with `~/.ssh/id_ed25519`; the backend container
is `lawcast-backend` and its DB is the `lawcast_lawcast_db` volume. The 209/2214912 reproduction
ran offline against the exported `not_supported` list.

**Not established**: the exact date the wedge began (the first inactive candidate's summary
state predates it), and whether `2220952` (marked `ready` on 2026-09-12) was recovered by this
pass or by the crawl-cycle path.

## 7. Fix verification (`backend-v1.15.5`)

`collectSummaryBackfillCandidates` (`notice-archive.service.ts`) + new
`readSummaryBackfillCursorPage`. The three staging loops in
`archive-sync-phase-executors.ts` are unchanged except for a contract comment.

- **Unit** (`notice-archive.service.spec.ts`, `summary backfill cursor paging`): a stateful
  paging mock drops one row from a full cursor page; the page still returns 5 candidates
  `[1001, 1002, 1003, 1005, 1006]` and the next `skip` step returns `[1006, 1007]`.
  **Confirmed failing on the pre-fix service** (returned 4).
- **E2E** (`diffchain.e2e-spec.ts`, real SQLite): 7 `not_supported` rows seeded through
  `upsertNoticeArchive`, `9104` flipped to `source_deleted`, then
  `getNotSupportedSummaryRecoveryPage(0, 5)` returns `[9101, 9102, 9103, 9105, 9106]`.
  **Confirmed failing on the pre-fix service** (returned 4).
- **Production replay**: the new walk over the live 377-row `not_supported` set stages all
  **352** active candidates in **76 terminating steps** (was 209 staged / 143 unreachable),
  reaching `2221042` and `2221131`.
- Gates: lint 0, `tsc --noEmit` 0, build 0, `npm test` 80 suites / 1115 tests,
  `npm run test:e2e` 44, comment-language 0.

## 8. Live deployment verification (`backend-v1.15.5`, 2026-10-14)

Deployed through the root-pointer push; the container restarted and its bootstrap pipeline ran the
fixed recovery pass.

- **Staging scope**: the pass staged `355` rows (`3` pending + `352` recovery) against the old
  code's `209`. The apply queue drained past the old `209` watermark
  (`summaryBackfillProcessedTotal` climbed past it while the queue still had rows left) - the
  pre-fix collector could not stage more than `209` under any circumstance.
- **Rows recovered in the wedge zone** (`notice_num > 2214912`, previously unreachable): 19 had
  left `not_supported` by the time of the check (queue still draining), e.g. `2221036`, `2221042`,
  `2221051`, `2221060`.
- **End-to-end**: `2221042` - the row that renders a 3,863-char head-revision `제안이유` while
  reporting `not_supported` - now returns `aiSummaryStatus: ready` with a real Ollama summary
  (`출산 및 보육 지원 강화와 주택 세제 혜택 확대를 통해 국민의 경제적 부담을 경감하고 주거
  안정성을 높이는 데 초점을 맞춤.`).
- **Caveat found while verifying**: `updateSummaryStatesByNoticeNums` did not bump
  `notice_archive_snapshot_states.updated_at`, so `updated_at` was not a reliable marker for
  "this pass touched the row" (rows processed by the 09:37 pass showed no timestamp change).
  Compare status sets instead. **Fixed in §11**, released as `backend-v1.15.6` and audited
  live in §11.2.
- Rows that still carry no reason anywhere stay `not_supported` after the pass (358 at check
  time) - expected, and they re-enter the scan on every pass now that the wedge is gone.

## 9. Follow-up fix - `contentId` rows now summarize from the chain (`backend-v1.15.6`)

Asked by the user after §8: "make rows that have a `contentId` generate their summary from the
chain's latest `제안이유` too". The generator was the single point that threw the recovered reason
away: for `notice.contentId` set it fetched PAL live and returned `not_supported` whenever
`content.proposalReason` was empty, even though the caller had just resolved the text.

**Change** (`summary-generation.service.ts`): the `contentId` branch now resolves the reason via
the new private `resolveSummaryProposalReason(notice, liveReason)`, whose precedence is

1. the live source payload (`content.proposalReason`) - unchanged healthy path;
2. `notice.proposalReason` - a reason the caller already resolved (archive snapshot, or the
   fresh LIKMS recovery that `crawling-scheduler-proposal-retry.ts` puts on the notice);
3. the chain head (`NoticeArchiveService.getLatestProposalReasonForNotice`) - where a LIKMS
   repair lands when the snapshot column was archived empty.

The no-`contentId` branch keeps its old precedence (stored → chain) and now shares the helper.
When no source carries a reason the row still returns `not_supported`, and the log line now
names all three sources. `content?.title || notice.subject` supplies the title when PAL returns
no payload at all.

**Why this matters in production**: every generator caller (`crawling-scheduler-pending-support`,
`crawling-scheduler-proposal-retry`, `archive-sync-phase-executors`, `crawling-scheduler-summary-support`)
now keeps a reason it already holds, and the LIKMS recovery flow (`fetchAndUpdateProposalReason`
→ chain append → `generateSummaryForNotice`) stops ending in `not_supported` for contentId rows.

**Verification**:

- Unit (`summary-generation.service.spec.ts`): 4 new/changed cases - contentId row with an empty
  payload reason takes the chain head (4-row pre-fix failure: `not_supported`), a caller-resolved
  reason is used without a chain read, a missing payload falls back to `notice.subject`, and the
  healthy path asserts no extra chain read.
- E2E (`diffchain.e2e-spec.ts`, real SQLite): notice `9301` archived with `contentId` and an
  empty snapshot reason, `appendLikmsProposalReasonRepair` appends the text to the chain, a stub
  PAL payload carries no reason - `generateSummaryForNotice` returns `ready` and passes the chain
  text to `summarizeProposal`. **Confirmed failing on the pre-fix service** (`not_supported`).
- Gates: lint 0, `tsc --noEmit` 0, build 0, `npm test` 80 suites / 1118 tests,
  `npm run test:e2e` 45, comment-language 0.

**Not done (deliberate, separate decision)**: the `!row.contentId` filter in
`getNotSupportedSummaryRecoveryPage` still excludes contentId rows from the `not_supported`
recovery scan, so the 22 historical rows need that widening (or a re-crawl) before they are
re-attempted.

## 10. Follow-up fix - the 15-minute trigger now runs the summary backfill (`backend-v1.15.6`)

Asked by the user after §9: make the 15-minute cron actually run the summary backfill
instead of only the start-up pass.

**Mechanism.** `handleProposalReasonBackfillDrain` (`cronjobs.service.ts`) put both parts of
the tick behind one guard, `shouldSkipProposalReasonBackfillCron` = archive-sync write-heavy
activity **or** `crawlingService.isSchedulerBusy({ includeBackground: true })`. The NSM
reason drain needs that (it drives a browser session); the summary backfill does not -
`runSummaryBackfill` writes single summary rows, fetches PAL content over HTTP
(`CrawlingCoreService.getContent`, no browser session) and talks to Ollama. Inheriting the
crawl half starved it.

**Live evidence** (backend `1.15.5`, container started 10:41 UTC 2026-10-14; `/api/stats`
polled every 20 s plus `docker logs`):

- The task never ran in that uptime. `cronJobs['proposalReason backfill drain'].lastRunAt`
  stayed `null`, and `docker logs lawcast-backend 2>&1 | grep -c 'proposalReason backfill
  drain'` returned `0` - `shouldSkipCron` logs at `debugDev`, a no-op under
  `NODE_ENV=production`, so every skip was invisible.
- Ticks at 10:54/11:09/11:24 are explicable by archive-sync alone (bootstrap pass plus its
  async apply drain until 11:17:22, then `isDone sync` 11:21:43-11:25).
- The **11:39 tick is the decisive one**: every sample from 11:38:58 to 11:40:00 showed no
  running phase, no running async apply worker and no queued apply task, the crawl cron had
  run at 11:32:04, and the task still did nothing (`lastRunAt: null`, no log line). With the
  archive-sync side verifiably idle, the crawl/browser clause is the only guard left that
  could have deferred it.

**Change** (`cronjobs.service.ts`):

- New `shouldSkipSummaryBackfillCron(taskName)` - the archive-sync write-heavy guard only,
  logged at production level (`shouldSkipCron` gained a `visibleInProduction` option) so a
  deliberate deferral is never silent.
- `handleProposalReasonBackfillDrain` evaluates the guards separately (NSM drain keeps
  `shouldSkipProposalReasonBackfillCron`) and wraps the tick in `execute(...)` regardless, so
  the status snapshot shows the schedule firing. The phase-level `crossPhaseGuard` inside
  `runSummaryBackfill` still refuses to overlap another write-heavy phase and logs a visible
  warning, which is what protects the DB.

**Verification** (`cronjobs.service.spec.ts`, 3 new cases): crawl-busy + archive-idle runs the
summary backfill while skipping the NSM drain; archive write-heavy defers it and emits the
production-level skip line; idle runs both. **The first two fail on the pre-fix service**
(the third is the control covering the already-working idle path). Gates after the change:
lint 0, `tsc --noEmit` 0, build 0, `npm test` 80 suites / 1121 tests, `npm run test:e2e` 45,
comment-language 0.

**Deployed and confirmed live** (`backend-v1.15.6`, container started 2026-10-14 11:59:38 UTC).
The periodic tick now runs in production: `cronJobs['proposalReason backfill drain'].lastRunAt`
moved from `null` (the §10 pre-fix evidence) to `2026-10-14T12:54:37Z`, then `13:54:37Z`, on the
15-minute cadence, and each pass logs `Summary backfill staged - scanned=340 stagedPending=315`
followed by a drain to `queueRemaining=0` (80 batches of `requested=5, removed=5, failed=0`).
The row-level audit of that pass is §11.2.

## 11. Follow-up fix - summary state writes stamp `updated_at` (`backend-v1.15.6`)

Asked by the user after §10: make the summary-state writes advance `updated_at` so the rows a
backfill pass processed can be identified by timestamp (the caveat recorded in §8).

**Root cause.** Two write paths disagreed:

- `updateSummaryStateByNoticeNum`, `persistSummaryState` and the isDone flips call
  `repository.update(...)`, and TypeORM's `UpdateQueryBuilder` appends
  `"updated_at" = CURRENT_TIMESTAMP` for the `@UpdateDateColumn`.
- `updateSummaryStatesByNoticeNums` - the path the summary backfill's apply worker prefers
  (`archive-sync-phase-executors.ts`: bulk first, per-row only as a fallback) - is a raw
  `INSERT ... ON CONFLICT (notice_num) DO UPDATE SET ai_summary = EXCLUDED.ai_summary,
  ai_summary_status = EXCLUDED.ai_summary_status`. `orUpdate` rewrote only the two listed
  columns, and TypeORM's own `updated_at = DEFAULT` injection for the conflicting row is
  explicitly skipped for the SQLite driver family (`InsertQueryBuilder.js`), so the column
  kept its insert-time value.

**Production evidence** (read-only, production volume DB): `2221036` and `2221042` turned
`ready` during the 11:17 UTC pass of `backend-v1.15.5`, yet both still showed
`updated_at = 2026-09-16 15:13:02`, and `2221131` (also `ready`) showed `2026-09-18 15:00:55`.
The rows with a fresh `updated_at` were the ones written through `repository.update` (isDone
flips) or freshly inserted.

**Change** (`notice-archive-maintenance-support.ts`): `orUpdate(['ai_summary',
'ai_summary_status', 'updated_at'], ['notice_num'])` - the conflict branch now takes the
proposed row's `updated_at` (the column default, i.e. the write time), like the other two
columns.

**Verification** (`notice-archive-summary-state-timestamp.spec.ts`, real in-memory SQLite,
4 cases): the bulk upsert advances `updated_at`; a repeated bulk upsert of the *same* text
advances it again; the single-row write advances it; the bulk insert stamps it. The two bulk
cases **fail on the pre-fix code** - they assert the value moved away from a backdated
sentinel, so SQLite's one-second timestamp resolution cannot make them flaky - and the other
two pin the already-correct paths. Gates: lint 0, `tsc --noEmit` 0, build 0, `npm test` 81
suites / 1125 tests, `npm run test:e2e` 45, comment-language 0.

Nothing reads the column yet (it is an operational marker), so a pass can now be audited with
`WHERE updated_at >= '<pass start>'` instead of diffing status sets.

### 11.1 Live verification (`backend-v1.15.6`, deployed 2026-10-14 11:59:38 UTC)

Release trail: PR `#206` (`fix: resume the AI summary backfill and make its writes auditable`, squash,
signed) → tag `backend-v1.15.6` → `dev` fast-forwarded → root-pointer commit
`chore: update backend submodule to v1.15.6` on `main` → `deploy-backend` job green,
`/api/version` = `1.15.6`.

The container restarted into the fixed build and its bootstrap pass staged
`scanned=340 stagedPending=315`, then drained the apply queue (`queueRemaining=0` at
12:07:32). Read-only against the production volume DB:

- **315 rows carry `updated_at >= 11:59:38`** - exactly the staged count, so the processed
  set is now identifiable by timestamp.
- Diffing the `not_supported`/`not_requested`/`unavailable` set before the deploy against the
  same set afterwards: **315 rows moved, 25 did not**, and every unmoved row is one the scan
  deliberately skips - `22` are `contentId` + `active` (the `!row.contentId` recovery filter,
  still open) and `3` are `no contentId` + `source_deleted` (dropped by the active-archive
  join). The counts reconcile: `315 + 22 + 3 = 340`.
- No row flipped status in this pass (`not_supported 340 -> 340`, `ready 21,154 -> 21,154`):
  those rows genuinely carry no `proposalReason` anywhere, so the pass rewrote the same
  verdict - which is exactly the case the timestamp now makes visible.
- Pre-fix comparison from the same DB: `2221036`/`2221042` had turned `ready` in the 11:17
  pass while keeping `updated_at = 2026-09-16 15:13:02`.

### 11.2 Post-deploy audit of a periodic pass (the acceptance criterion)

Re-verified read-only against the production volume DB once the periodic tick had run twice
(12:54 and 13:54 UTC), i.e. against a pass the 15-minute cron started rather than the bootstrap
one. Criterion: **the rows a post-deploy backfill pass processed are identifiable from
`updated_at` alone.**

- **The 13:54 window isolates exactly the staged set.** `updated_at >= '2026-10-14 13:54:00'`
  returns **315 rows, all `not_supported`**, spanning `13:54:10`-`14:01:14` (the async apply
  drain). **No `ready` row falls inside the window**, so there is no false positive: the
  timestamp does not sweep in rows some other path touched.
- **All 340 `not_supported` rows are accounted for.** Joining the summary states to their archive
  rows: **315 stamped in the pass**, **25 not** - `22` `contentId` set and `3` inactive archive
  row. That is exactly `scanned=340 stagedPending=315` in the pass log, and exactly the two
  deliberate skips (§9's `!row.contentId` filter and the active-archive join).
  `315 + 22 + 3 = 340`, and `0` summary-state rows lack an archive row.
- **The crawl path is separable.** It stamped only `ready` rows today, and those land *between*
  passes (`13:49`-`13:51`, plus `08:52`-`09:02` and `00:23`), never inside `13:54`-`14:01`.
- **Caveat - anchor the window at the pass, not the deploy.** A window anchored at the container
  start (`>= 11:59:38`) no longer isolates one pass: the 12:54 and 13:54 passes re-stamped the
  same candidate set (a repeated bulk upsert of the *same* verdict still advances `updated_at`,
  as §11's spec pins), and the crawl cycle added ~17 `ready` rows in the gaps. Audit **per pass**
  by anchoring on `cronJobs['proposalReason backfill drain'].lastRunAt` or the
  `Summary backfill staged` log line.
- **Why the marker only works now.** `2221036`, `2221042` and `2221131` still show
  `2026-09-16 15:13:02` / `2026-09-18 15:00:55`: they are `ready`, left the recovery scan when
  the 11:17 pass of `backend-v1.15.5` summarized them, and no later pass re-touches them. Under
  the pre-§11 code that state was indistinguishable from "the pass never ran".


