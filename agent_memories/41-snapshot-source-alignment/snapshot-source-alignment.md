# Snapshot source alignment: the screenshot must come from the snapshot's page

## 1. Symptoms (production, 2026-10-15 02:25 JST)

Two reports, both visible to the operator:

1. **Wrong archived original / screenshot for LIKMS notices.** The notice pages of the
   bills listed by `likms.assembly.go.kr` showed the `국민참여입법센터` page instead of
   the bill page.
2. **Legacy bills still backfilled.** The Discord bridge logged
   `proposalReason backfill failed for bill 21064: likms has no detail page for bill 21064`
   for 1950s bills (measured and fixed in `agent_memories/40-backfill-assembly-scope/`;
   the warnings in that quote were emitted by the **pre-#208** container, see §5).

## 2. Measurement (production SQLite, read-only)

`notice_archives` on the production host (volume
`/var/lib/docker/100000.100000/volumes/lawcast_lawcast_db/_data/lawcast.db`, read with
`sqlite3 -readonly`; the container ships no `sqlite3` binary, the host does):

| Metric | Value |
| ------ | ----- |
| Rows with a `likms.assembly.go.kr` URL in `http_metadata_json` | **275** |
| ... of those, `source_html` is the NSM portal 404 shell (`errorWrap` / `요청페이지가 없습니다`) | **274** |
| ... of those, `source_html` is a real likms detail page | 1 |
| Rows whose stored screenshot is one identical 21,977 B JPEG | **274** (the 404 page image) |
| Screenshot of the one correctly captured likms row | 118,479 B |
| Legacy rows (`noticeNum < 2200000`) | 33 (`20490`-`50589`, 1953-...) |
| Legacy rows missing a screenshot / `source_html` | 0 / 0 |
| Rows missing `source_html` in the current Assembly | 3 |
| Rows fetched since 2026-10-14 08:49 UTC | 0 |

A damaged row, verbatim:

```json
{"requestUrl":"https://likms.assembly.go.kr/bill/bi/billDetailPage.do?billId=PRC_V2U6C0C9A1B7A1A8Y2Z7V4T1T1S9T4",
 "responseUrl":"https://opinion.lawmaking.go.kr/gcom/nsmLmSts/out/2221887/detailRP",
 "fetchedAt":"2026-10-14T07:28:32.579Z","statusCode":200}
```

`requestUrl` is the likms link the list supplied, `responseUrl` is where the browser
actually ended: the NSM portal, whose body is the `errorWrap` 404 shell. The snapshot and
the screenshot stored for that notice are that shell, not the bill.

## 3. Root cause and timeline

`captureNsmDetailFull` only learned to dispatch on the active list source in
**#201 / backend-v1.15.2 (2026-10-14 17:06 JST)**. Everything archived before that deploy
opened `buildNsmDetailUrl(billNo)` for a likms-listed bill, and `국민참여입법센터` answers a
bill it does not list with HTTP 200 and its 404 shell, which the pipeline stored as a
successful capture:

| Time (UTC) | Rows stored with the NSM 404 shell |
| ---------- | ---------------------------------- |
| 2026-10-14 06:00-08:11 | 275 (all of them) |
| 2026-10-14 08:49 (first row after the #201 deploy) | 0 - the likms page |

The remaining defects were in the **capture-rule edges**, not in the dispatch:

1. `captureNsmDetailScreenshot` (`crawling-core.service.ts`) checked
   `isNsmCrawlerEnabled()` **before** the likms branch, so with
   `CRAWLING_NSM_ENABLED=false` every queued screenshot of a likms-listed bill was
   silently dropped - the same flag that gates the `국민참여입법센터` collection was gating
   a capture that never touches that portal.
2. `ArchiveOrchestratorScreenshotCoordinator` gated both the queue drain and the
   screenshot backfill on the NSM enable flag.
3. Nothing verified **where the browser actually landed**. A capture that redirected to
   another portal (or to the NSM error shell) was stored as this notice's original and
   screenshot.
4. The stored `httpMetadata.requestUrl` was the *intended* NSM URL / the list link, not
   the page that was opened, so a row could claim a portal its snapshot never came from.

## 4. Fix (backend-v1.16.2)

- `isSnapshotSourcePageUrl(url, source)` + `SNAPSHOT_SOURCE_HOST` in
  `crawling-core.service.ts`: the likms full capture **throws** and the likms screenshot
  capture returns `null` when the page landed outside `likms.assembly.go.kr`, so a
  foreign page is never stored. The likms source is unconditional: there is **no**
  fallback to the NSM portal.
- `captureNsmDetailScreenshot`: the likms branch now runs first, so a likms bill's
  screenshot is captured with this application's own browser session regardless of
  `CRAWLING_NSM_ENABLED`; the NSM portal branch keeps its enable flag (that flag really
  does gate that portal).
- `isSnapshotSourceCaptureEnabled()` in `crawler-activation.utils.ts`:
  `isLikmsNsmSourceEnabled() || isNsmCrawlerEnabled()`. The coordinator's queue drain and
  backfill now use it for list-source items.
- `captureNsmDetailFull` returns `requestUrl` (the page it opened) and every
  `httpMetadata` write records it, so the stored row names the portal its snapshot and
  screenshot came from.
- The Assembly floor also covers the three pools that still selected by status alone:
  `getNoticesWithMissingScreenshots`, `getNoticesWithMissingNsmScreenshots` and both
  halves of `getNoticesWithMissingSnapshotArtifacts` now start at
  `ARCHIVE_SYNC.BACKFILL_MIN_NOTICE_NUM`. Note 40 left these out because production had
  0 legacy rows with a NULL screenshot/`source_html`; the floor is applied anyway so the
  gap cannot open again.

### Deliberately NOT repaired: the 274 frozen rows

`trg_notice_archives_prevent_update` (production SQL, read from
`sqlite_master`) permits `source_html`, `source_html_sha256`, `screenshot_blob` and
`screenshot_format` to change **only while the old value IS NULL** - the first-fill
exception from migration `202608130001`. The 274 rows hold non-NULL (wrong) values, so no
update can replace them, and physical delete is blocked by
`trg_notice_archives_prevent_delete`. Repairing them would mean widening the immutability
trigger; the operator reviewed the measurement above and chose the capture rule only,
keeping snapshot immutability absolute. The wrong images therefore stay in the archive as
a pre-fix artifact; the capture rule makes sure nothing new joins them.

## 5. Verification

- `crawling-core.service.spec.ts`: the likms full capture rejects a page that landed on
  the NSM portal; the likms screenshot is captured with the NSM crawler disabled; a
  screenshot whose page landed elsewhere is discarded (`null`, no `page.screenshot()`
  call); `isSnapshotSourcePageUrl` truth table.
- `archive-orchestrator-screenshot-coordinator.spec.ts`: a queued list-source item still
  drains under `CRAWLING_NSM_SOURCE=likms` + `CRAWLING_NSM_ENABLED=false`, and is dropped
  without opening a browser under the NSM source with the crawler off.
- `crawler-activation.utils.spec.ts`: `isSnapshotSourceCaptureEnabled` truth table.
- `notice-archive.service.spec.ts`: all three screenshot/snapshot pools carry
  `moreThanOrEqual(BACKFILL_MIN_NOTICE_NUM)`; `archive-orchestrator-screenshot-failure.spec.ts`
  fixtures moved into the current Assembly so its pool assertions stay meaningful.
- Gates: lint, `tsc --noEmit`, build, **83 suites / 1185 tests**, comment-language
  checker 0 Korean prose lines.

## 6. Post-deploy observation (see §7 for the result)

```bash
ssh root@10.20.0.1 'docker logs lawcast-backend --since 12h 2>&1 | grep -cE "backfill failed for bill 2[01][0-9]{3}"'
ssh root@10.20.0.1 'sqlite3 -readonly /var/lib/docker/100000.100000/volumes/lawcast_lawcast_db/_data/lawcast.db \
  "SELECT COUNT(*) FROM notice_archives WHERE http_metadata_json LIKE \"%opinion.lawmaking.go.kr%\" AND source_html LIKE \"%errorWrap%\";"'
ssh root@10.20.0.1 'sqlite3 -readonly /var/lib/docker/100000.100000/volumes/lawcast_lawcast_db/_data/lawcast.db \
  "SELECT noticeNum, substr(http_metadata_json,1,80) FROM notice_archives ORDER BY http_fetched_at DESC LIMIT 5;"'
```

The first query must return `0` (no attempt on a bill below `2200000`), the second must
not grow beyond the 274 pre-fix rows, and the third must show a `likms.assembly.go.kr`
`requestUrl` for newly archived notices.
