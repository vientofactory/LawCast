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
  though the chain holds it.

## 5. Fix status

1. **FIXED in `backend-v1.15.5`** — the cursor now advances over the summary-state rows and
   hydrates one page at a time (`readSummaryBackfillCursorPage` returns
   `{ cursorCount, rows }`; only `cursorCount` is compared against the page size). See §7.
2. **Still open** — `generateSummaryForNotice`'s `contentId` branch ignores the chain and
   re-reads PAL live, and the `!row.contentId` recovery filter keeps those rows out of the
   scan (22 `not_supported` rows, 2 active with a later-revision reason).
3. **Still open** — the 15-minute drain cron leaves no trace when skipped
   (`lastRunAt: null`, `lastError: null`), so the backfill still effectively runs only at
   container start.

Note for future edits: the recovery pass can stay an offset walk only because the apply worker
starts after staging completes. If a pass ever writes summary states while it stages, it must
become a `skip=0` drain loop instead.

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

## 6. Verification method

Read-only: public API (`/api/version`, `/api/stats`, `/api/crawling-transparency`,
`/api/notices/:num/detail`), container logs (`docker logs lawcast-backend`), and  `sqlite3 -readonly` against the production volume
  (`/var/lib/docker/100000.100000/volumes/lawcast_lawcast_db/_data/lawcast.db`). No writes.
  The production host is reachable as `root@10.20.0.1` with `~/.ssh/id_ed25519`; the backend
  container is `lawcast-backend` and its DB is the `lawcast_lawcast_db` volume.
The 209/2214912 reproduction ran offline against the exported `not_supported` list.

**Not established**: the exact date the wedge began (the first inactive candidate's summary
state predates it), and whether `2220952` (marked `ready` on 2026-09-12) was recovered by
this pass or by the crawl-cycle path.
