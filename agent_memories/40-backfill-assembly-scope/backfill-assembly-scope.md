# Backfill scope: bills from earlier Assemblies are out of the pool

## 1. Symptom (production)

The Discord debug bridge emitted one warning per legacy bill per drain tick:

```
[WARN] ArchiveOrchestratorService proposalReason backfill failed for bill 21064:
likms has no detail page for bill 21064
```

The bill behind it (`21076`, proposal date **1953-11-14**) renders as a normal notice
page with 입법예고 정보 and no 제안이유 at all - it is a historical record, not a bill
any source can still describe.

## 2. Where the old bills come from

`notice_archives` holds two numbering schemes side by side:

| Scope | Rows | noticeNum range | contentId |
| ----- | ---- | --------------- | --------- |
| 22nd Assembly (current) | 21,461 | 2200001 - 2221897 | present on PAL-origin rows |
| Earlier Assemblies | 33 | 20490 - 50589 | always NULL |

Notice numbers encode the Assembly as `<assembly><5-digit serial>`: 22nd Assembly bills
start at 2200001, 21st Assembly bills at 2100001. The historical rows use the legacy
5-digit numbering of the assemblies they belong to.

Both backfill surfaces selected rows by **status**, never by Assembly:

- `getProposalReasonRetryCandidates` (`modules/notice/utils/notice-archive-maintenance-support.ts`)
- the summary-backfill cursor scan (`readSummaryBackfillCursorPage` in
  `modules/notice/notice-archive.service.ts`), which serves the `not_requested`,
  `not_supported` recovery and `unavailable` passes

Measured pool at the time of the finding: **334 rows = 33 legacy + 301 current Assembly**,
of which only 20 carry a recoverable source (`contentId`).

## 3. Cost of the missing floor

- The 33 legacy rows have the smallest notice numbers in the table, so they were the
  head of every candidate page: the drain spent its whole 20-row page on them and
  logged one warning per row, per tick (production: `21063`, `21064`, `21066`, `21076`
  among them).
- The summary backfill staged all 33 on every pass: `scanned=319 stagedPending=316`
  was 286 current-Assembly `not_supported` rows plus the 33 legacy ones, and a
  `not_supported` verdict can never change for a bill whose source publishes nothing.
- Attempt-history stamps (v1.16.0) rotated the drain past them, but rotation only
  reordered the waste: the legacy rows came back once their attempt count was again
  the lowest in the pool.

## 4. Fix (backend-v1.16.1)

`APP_CONSTANTS.ARCHIVE_SYNC`:

- `CURRENT_ASSEMBLY` (env `ARCHIVE_SYNC_CURRENT_ASSEMBLY`, default `22`)
- `BACKFILL_MIN_NOTICE_NUM = CURRENT_ASSEMBLY * 100000` (default `2200000`)

The floor is applied to:

1. `getProposalReasonRetryCandidates` - `na.noticeNum >= :minNoticeNum`
2. `readSummaryBackfillCursorPage` - `noticeNum: MoreThanOrEqual(...)` on both the
   summary-state cursor and the archive-table fallback
3. the operator tooling (`src/scripts/proposal-reason-drain-observation.ts`) - the pool
   predicate and its report now carry the same floor, so the report measures the pool
   the drain actually works through

The floor is a **scope boundary, not a deletion**: legacy rows keep their archive,
lifecycle and summary state and stay readable. The next Assembly only needs
`ARCHIVE_SYNC_CURRENT_ASSEMBLY` bumped.

## 5. Verification before release

- `notice-archive-proposal-reason-retry.spec.ts` (real SQLite schema built by the
  migration chain): legacy rows `20490`, `21076`, `50589` are never seeded even though
  they are active, reasonless and never attempted; every other case in that spec was
  moved onto current-Assembly numbers.
- `notice-archive.service.spec.ts`: the recovery and pending scans both pass
  `moreThanOrEqual(BACKFILL_MIN_NOTICE_NUM)` into the cursor query.
- `proposal-reason-drain-observation.spec.ts`: fixtures moved into the current Assembly
  range plus one legacy row that must stay out of the pool count.
- Gates: lint, `tsc --noEmit`, build, **83 suites / 1172 tests**, comment-language
  checker 0 Korean prose lines.

