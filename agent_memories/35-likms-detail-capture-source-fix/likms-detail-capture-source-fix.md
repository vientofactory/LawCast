# LIKMS Detail Capture Follows the Active Source

Root cause and fix for the two live defects found in
`agent_memories/34-likms-live-pipeline-verification/`: with
`CRAWLING_NSM_SOURCE=likms`, bill detail capture still opened the NSM portal
(`opinion.lawmaking.go.kr`), so every newly archived likms bill stored the NSM
error page (`errorWrap`, 6,207 B) with an empty `제안이유` and a screenshot of
`국민참여입법센터` instead of `국회 의안정보시스템`.

## 1. Root cause

`CrawlingCoreService.captureNsmDetailFull` and `captureNsmDetailScreenshot`
hardcoded `new NsmLmSts(...)` plus `buildNsmDetailUrl(billNo)`
(`https://opinion.lawmaking.go.kr/gcom/nsmLmSts/out/{billNo}/detailRP`) and
parsed with `NsmLmStsParser`. Only `getNsmDetail` followed
`createNsmClient()`; the capture path did not. A likms-only `의안번호` has no NSM
detail page, so the portal answered with its own error template and the capture
was persisted verbatim (`http 200`, real-looking HTML and screenshot, no detail
fields).

Evidence (production, 270 rows archived in 90 minutes): `responseUrl` =
`opinion.lawmaking.go.kr/...` while `requestUrl` was the likms link;
`source_html` contained `errorWrap` at a constant 6,207 B for all rows;
`proposalReason` non-empty in 0 rows; `/api/notices/archive` reported
`aiSummaryStatus: not_supported`.

## 2. Fix (`backend/src/modules/crawling/crawling-core.service.ts`)

- `captureNsmDetailFull` / `captureNsmDetailScreenshot` now dispatch on
  `isLikmsNsmSourceEnabled()`.
- New `captureLikmsDetailFull`:
  - resolves the detail URL with `resolveLikmsDetailUrl` (accepts a `PRC_...`
    `billId` as-is, otherwise `LikmsCrawler.resolveBillId(의안번호)`), and throws
    `likms has no detail page for bill <n>` when likms has no such bill;
  - reads parsed fields from `createNsmClient().getDetail(billNo)` — the list
    source's own adapter, whose `getDetail` performs the detail-page +
    `심사정보`-fragment round trip that no single page HTML can serve (this is
    where `제안이유 및 주요내용` lives);
  - navigates the browser to the likms detail page for the HTML snapshot and
    screenshot, with no NSM Waitingroom or NSM deletion heuristic.
- New `buildLikmsBillDetailUrl(billId)` mirrors pal-crawl's private
  `LikmsCrawler.buildDetailPageUrl` (path + `currMenuNo=2600044`), the same way
  `buildNsmDetailUrl` mirrors the NSM URL.
- New `captureLikmsDetailScreenshot` serves the backfill queue for likms rows.
- Extracted `fitScreenshotWithinSizeLimit(raw, label)` so both sources share the
  JPEG recompression pipeline (the NSM path's messages are unchanged).
- `LikmsCrawler.resolveBillId` and `LikmsNsmAdapter.getDetail` verified live
  before implementation: `2221891` → `PRC_E37FE80B84E64084BABD8E9EB5F802`,
  `proposalReason` 732 chars, detail page 204,427 B with `errorWrap: false`.

## 3. Backlog behaviour (measured against the code)

- **`proposalReason` / detail fields recover automatically.** The
  `PROPOSAL_REASON_BACKFILL_DRAIN` cron
  (`getProposalReasonRetryCandidates`) selects active rows with an empty
  `proposalReason` and no non-empty `proposalReason` chain event;
  `CrawlingSchedulerProposalRetry.enqueue` falls back to `notice.num` when
  `billNo` is null, and the drain calls
  `fetchAndUpdateProposalReason(num, num, null)`, which now takes the likms
  path. The value lands through `updateNsmHtmlAndDetail`'s **diffchain** event,
  not the immutable archive column.
- **The wrong screenshot/HTML cannot be rewritten.** `notice_archives`'
  immutability trigger (`202609020001-allow-lifecycle-status-transition.migration.ts`)
  keeps `source_html`/`screenshot_blob` in `FIRST_FILL_COLUMNS` — writable only
  while NULL. The 270 rows already hold the NSM error page, so
  `fillMissingSnapshotArtifacts` skips them. Correcting those artifacts needs a
  deliberate migration (a one-time replacement predicate), not a code change.

## 4. Verification

- New tests in `crawling-core.service.spec.ts`: likms capture opens the likms
  page and takes fields from the adapter (NSM parser and NSM URL are asserted
  unused), a missing likms detail page throws, and the screenshot backfill uses
  the likms page.
- Gates: lint 0, `tsc --noEmit` 0, build 0, comment-language 0,
  `npm test` 80 suites / 1110 tests (was 1107).
- Shipping version: backend `1.15.2`.
