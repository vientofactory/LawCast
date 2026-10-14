# LIKMS Live Pipeline Verification (2026-10-14)

Live end-to-end verification of the 계류의안 crawler with `CRAWLING_NSM_SOURCE=likms`
actually enabled in production, measured against the production host `10.20.0.1`
(read-only DB probe, container logs) and the public site `law.viento.me`.

## 1. Observed configuration

The switch is live, not a dry run:

```
CRAWLING_NSM_ENABLED=1
CRAWLING_NSM_SOURCE=likms
CRAWLING_NSM_DELETION_DETECTION_ENABLED=0   # redundant: likms force-off also applies
APP_VERSION=1.15.1  (package.json + /api/version -> buildEnv: package.json)
```

`/api/stats` reports `nsmPendingCrawler.source = likms.assembly.go.kr`,
`/api/crawling-transparency` reports `noticeSources[nsm].url = https://likms.assembly.go.kr`.
Container up, healthy.

## 2. What works (verified)

- **List ingestion**: one full scan walked `allPages=160`, `allItems=15958`,
  `unique=15164`, `scanMs=340489`, `pendingCandidates=77`. `listScan.degraded=false`,
  `consecutiveZeroRowScans=0` (`/api/stats`).
- **Redundant pending stream skipped** (patch from §4-1 of
  `agent_memories/33-likms-source-switch-risk/`): log
  `Pending sync NSM(pending) stream skipped: the active source classifies pending bills from the all-bills scan`.
- **Deletion detection force-off** (same patch): log
  `recorded 14950 list sighting(s) and skipped the probe pass — deletion detection is off because the active source is likms`.
  `source_deleted` count stayed at **8** through the whole cycle (no false positives).
- **Pipeline plumbing**: `Pending sync done - scanned=15164 new=214 newPending=77 syncOnly=137 sourceDeleted=0`.
  - `NSM archive run started (new-sync-only-bills) count=137` then `(new-pending-bills) count=77`.
  - 270 rows written in 90 minutes: `archive count 21274 -> 21488`.
  - 270/270 have `contentId IS NULL` (NSM/LIKMS origin, not PAL), `http_status_code=200`,
    a stored `source_html` and `screenshot_blob`.
  - 270 diffchain `created` events (`source=archive:upsert`).
  - Redis cache `1207 -> 1458`.
  - Summary backfill phase ran afterwards: `Summary backfill staged - scanned=314 stagedPending=314 ... queue=0`.
- **Public surface**: `https://law.viento.me/api/notices/archive` returns the new rows with
  `link = https://likms.assembly.go.kr/bill/bi/billDetailPage.do?billId=...`, `contentId: null`.

## 3. Confirmed defect — detail capture still targets the NSM portal

**Every** newly archived row in the window carries the NSM portal's **error page**, not the
bill's page:

- `http_metadata_json`: `requestUrl = https://likms.assembly.go.kr/...` (the notice link) but
  `responseUrl = https://opinion.lawmaking.go.kr/gcom/nsmLmSts/out/<billNo>/detailRP`.
- `source_html` contains `errorWrap` (the portal error template), `<title>국민참여입법센터</title>`,
  and its length is **6207 bytes for all 270 rows** (screenshot 21977 bytes for all).
- Resulting field completeness on the 270 new rows: `proposalReason` non-empty **0**,
  `content_bill_number` non-empty **0**, `content_proposal_date`/`content_committee` **null**.
- Baseline for comparison: pre-switch `contentId IS NULL` NSM rows — 19,867 total,
  **19,395 with a non-empty `proposalReason`** (97.6%).
- Consequence downstream: the public API reports `aiSummaryStatus: not_supported` for the new
  rows (empty `proposalReason` -> summary not supported).

Root cause: `captureNsmDetailFull` (`backend/src/modules/crawling/crawling-core.service.ts`) and
`buildNsmDetailUrl` hardcode `NsmLmSts` / `opinion.lawmaking.go.kr`; unlike `getNsmDetail`, they
do **not** follow `createNsmClient()`. This is the residue already named in
`agent_memories/31-likms-nsm-adapter-integration/` line 126 and
`agent_memories/33-likms-source-switch-risk/` line 79. With NSM as source the portal has data;
with LIKMS as source the 의안번호 exists only in LIKMS, so the NSM detail URL answers with its
error page and the capture is stored verbatim.

**The error page is archived as the snapshot artifact without complaint** — nothing rejects a
6,207-byte `errorWrap` page, so the archive looks healthy (`http 200`, HTML, screenshot) while
carrying no detail.

## 4. Secondary finding — non-법률안 계류의안 enter the bill pipeline

Of the 270 new rows, subject classification: `법률안` 54, `결의안` 88, `동의안` 13,
`탄핵소추안` 6, `규칙안` 2, `선언`/`협약`/`의견` 4, and 126 with none of those keywords
(mostly `징계안`). So roughly **80% of the ingested LIKMS rows are not 법률안**. `isCrawlableNsmBill`
only drops non-numeric `billNo` rows (e.g. `ZZ22142`); numeric-id non-bill 의안 (징계안, 결의안,
동의안) still pass `nsmBillToCachedNotice` and are archived, cached and shown as notices.

## 5. Not exercised

- **Notification dispatch**: the last cycle ran through the bootstrap pipeline
  (`ArchiveSyncService.runBootstrapPipeline` calls `beginChangeNotificationSuppression()`), so
  the 214 new rows produced no webhook/Discord/web-push send. No notification path was observed
  on this run.
- **No cron cycle was observed after the switch settled**, so the genuinely-new-bill path (with
  notifications) is still unverified.
- Actual LIKMS detail parse quality could not be judged, because the capture never reached LIKMS.

## 6. Recommended next steps (in order)

1. Make detail capture follow the active source, or use `getNsmDetail` (which already routes
   through `LikmsNsmAdapter.getDetail`) for LIKMS rows instead of the NSM browser capture.
2. Reject/quarantine a captured page that is the portal error template (`errorWrap`) before it is
   written as a snapshot — a 200 with an error body must not become the archive artifact.
3. Decide whether numeric-id non-법률안 계류의안 (징계안/결의안/동의안) should be filtered at
   ingestion or kept as first-class notices.
4. Until (1) lands, LIKMS-sourced rows carry subject-only data and no AI summary; consider keeping
   the source on `nsm` or accepting a degraded archive.
