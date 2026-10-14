# LIKMS Source Switch and Collection Enablement — Risk Assessment

Assessment of what breaks if production flips `CRAWLING_NSM_SOURCE=likms` **and**
`CRAWLING_NSM_ENABLED=1` on top of `backend-v1.15.0`. Every number below was
measured on 2026-10-14 against the production host `10.20.0.1` and a read-only
copy of the production database; no production setting was changed by this
assessment (`CRAWLING_NSM_ENABLED` is still `0`).

Related notes: `agent_memories/31-likms-nsm-adapter-integration/` (adapter
wiring), `agent_memories/32-nsm-ua-block-and-probe-storm/` (portal block, probe
storms, UA rotation).

## 1. Production state when measured

| Item | Value |
| --- | --- |
| `lawcast-backend` | `APP_VERSION=1.15.0`, started `2026-10-14T06:09:44Z`, healthy |
| Migration `202610140001` | applied — `nsm_last_seen_in_list_at`, `nsm_list_absence_probed_at` exist |
| `CRAWLING_NSM_ENABLED` | `0` (NSM-shaped collection fully stopped) |
| `CRAWLING_NSM_SOURCE` | unset → default `nsm` |
| `CRAWLING_NSM_DELETION_DETECTION_ENABLED` | unset → default **enabled** |
| Archive rows | 21,203 (active 20,325 / `source_deleted` 878) |
| NSM-shaped active rows (`contentId IS NULL`) | 19,845 |
| … of those, `content_bill_number IS NULL` (top detail-probe priority) | **40** |
| Pending cron | `6-59/20 * * * *` (every 20 min) |
| Detail-probe batch | cron path 20/cycle, pending-sync path 50/cycle |
| Crawler request shape | `pageSize` 100, `delayMs` 1000, `concurrency` 3, the two list streams serialized on purpose |

`/var/lib/docker/.../lawcast_lawcast_db/_data/lawcast.db` is the live DB; the
container reads it at `/app/data/lawcast.db`.

## 2. Measured LIKMS list

`LikmsNsmAdapter.search({ pageIndex, pageSize: 100 })`, one HTTP request per page
(4 + 5 + 4 requests total across the three measurement passes):

- **total 15,956 bills / 160 pages** at `pageSize=100`.
- Status distribution over 456 sampled rows (pages 1, 40, 80, 120, 160):
  `접수` 23 (5.0%), `소관위접수` 107 (23.5%), `소관위심사` 260 (57.0%),
  `소관위의결` 7, `본회의불부의` 3, empty 56 (page 160 only).
- Page 1 (the newest bills) carries the `접수` population: 18 of 100 rows are
  exactly `접수`, which is what the adapter's client-side `filterPending` keeps.
- **Pages ~153-160 are legacy document pages**, not bills: `ZZ1652` 인사청문요청안
  (2003-02-07), `ZZ1648` 보상금 지급 보고, `2001년도기금운용평가보고서`, plus
  **6-digit numeric ids** (`050470`, `050375`, `030933`, `021088`, …) that are not
  `의안번호`. Page 160 returned 56 rows of which 33 are numeric.

### Archive coverage per sampled page

| page | items | numeric ids | in archive | missing | NSM-shaped match | `접수` |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 100 | 100 | 58 | 42 | **0** | 18 |
| 40 | 100 | 96 | 95 | 1 | 95 | 1 |
| 80 | 100 | 98 | 96 | 2 | 96 | 3 |
| 120 | 100 | 100 | 99 | 1 | 99 | 1 |
| 135 | 100 | 99 | 99 | 0 | 99 | — |
| 145 | 100 | 100 | 100 | 0 | 100 | — |
| 150 | 100 | 98 | 97 | 1 | 97 | — |
| 160 | 56 | 33 | 0 | 33 | 0 | 0 |

Reading: mid-list pages are ~99% archived already, page 1 is 58% (the rows it
does match are **PAL-shaped**, `contentId IS NOT NULL` — the newest LIKMS bills
are only in the archive where a `입법예고` notice exists), and the tail pages are
0% archived because they are legacy documents. Pooled over 724 sampled rows:
80 missing (11.0%) → naive extrapolation ≈ **1,750 new rows**; the mid-list rate
(≈1% over ~14,000 rows ≈ 150-250) plus page 1 (≈42) plus an unmeasured tail is
the honest band: **a few hundred, up to ~1,800**.

## 3. Risk register

### R1 — HIGH. Creation and deletion are judged by two different portals

The list comes from LIKMS after the switch, but three paths still ask the **NSM
portal** whether a bill exists:

| Path | Code | Portal |
| --- | --- | --- |
| List scan | `getAllNsmPages` / `getAllNsmPendingPages` → `LikmsNsmAdapter` | LIKMS |
| Detail capture (per new row) | `archiveNsmBillItems` → `crawlingCoreService.captureNsmDetailFull(billNo)` | **NSM** (`opinion.lawmaking.go.kr`) |
| Detail probe 20/50 per cycle | `probeExistingNsmBillsForSourceDeletion` → `captureNsmDetailFull` + `probeNsmDeletedBillAlert` | **NSM** |
| List-absence reconciliation | `markSourceDeletedByMissingNsmNums` → `probeNsmDeletedBillOutcome` | **NSM** |

Measured on the live portal with a real browser UA (3 requests):

| bill | origin | response | `안건정보가 없습니다` |
| --- | --- | --- | --- |
| 2221866 | archived | 200, 45,341 B | no |
| 2221888 | LIKMS-only (page 1, not archived) | 200, 42,802 B | no |
| **2221889** | LIKMS-only (page 1, newest, not archived) | 200, 38,558 B | **yes** |

So the NSM portal really does answer "bill information not found" for bills that
LIKMS still lists. Consequence chain:

1. A new LIKMS-only bill is archived (`upsertNoticeArchive`) — the per-item
   `captureNsmDetailFull` fails, so `content_bill_number` stays `NULL`. The
   in-capture deletion branch is a **no-op at this point** because
   `appendSourceDeletedAndFlushNotifications(notice.num)` reads a row that does
   not exist yet (`getTrackedRowByNoticeNum` returns early). So no false
   `source_deleted` **at creation**.
2. The row then enters the detail-probe pool, which prioritizes
   `content_bill_number IS NULL` (`getActiveNsmBillsForProbe`). On the next
   probe the row exists, so a confirmed NSM "not found" marks it
   **`source_deleted`** and appends a diffchain event plus notifications.

That second step is the false-positive window, and the population it draws from
(the newly imported LIKMS-only bills) is exactly the population NSM is most
likely to answer "not found" for. Note the cooldown from note 32 §3-2
(`ARCHIVE_SYNC_NSM_LIST_ABSENCE_REPROBE_COOLDOWN_HOURS`) **does not cover the
detail-probe path** — that path still samples the whole pool every cycle.

### R2 — HIGH. List-scan cost is ~160× the NSM list

`getAllPendingPages` on LIKMS has no server-side filter (the adapter comments say
the `srngPrgrsSttsCd` value is unknown), so it scans the whole list and filters
`접수` client-side. The backend passes only `{ pageSize, delayMs, concurrency }`
— **never `maxPages`** — in both call sites
(`crawling/utils/crawling-scheduler-pending-support.ts`,
`crawling/utils/archive-sync-phase-executors.ts`).

Per pending cycle both streams run: `getAllNsmPages` (~160 requests) then
`getAllNsmPendingPages` (~160 requests) = **≈320 requests / 20 min ≈ 960/hour ≈
23,000/day** to `likms.assembly.go.kr`, each page 100 rows. Today the NSM-shaped
crawler issues **zero** requests (disabled). The two streams are serialized
deliberately (anti-Waitingroom design), so a cycle spends minutes just scanning,
against a 20-minute cron.

### R3 — MEDIUM. Detail-probe pool grows from 40 to the size of the import

Today `content_bill_number IS NULL AND lifecycle_status='active'` = **40** rows.
Every newly archived LIKMS row whose NSM capture fails lands in this pool, so a
few hundred to ~1,800 imported rows become the top-priority probe candidates,
probed 20/cycle (cron) + 50/cycle (pending sync) ≈ 70/cycle ≈ 5,000/day. Much of
that spend is on rows that will never succeed, because their detail page does not
exist on the probe portal.

### R4 — MEDIUM. Recent-notices cache is displaced

`processNewNsmSyncOnlyBillsInBackgroundInternal` pushes every newly archived
sync-only notice into the recent-notices cache (`CACHE.MAX_SIZE` = 5,000). A
first-scan import of a few hundred to ~1,800 rows rewrites a large slice of the
home/recent list with `계류`-stage bills, reducing PAL  `입법예고` visibility until
the cache turns over.

### R5 — MEDIUM. An empty page silently truncates the whole scan

`LikmsStateCrawler._getAllPagesImpl` stops the generator without error when a
page parses to zero items (`if (result.items.length === 0) return;`). During
measurement one direct page request returned items that all failed the bill
filter where neighbouring pages were normal, and the tail pages are structurally
different from the middle. A truncated scan is **not** an error, so
`reportNsmListScanOutcome` does not warn (it only escalates zero rows overall),
yet `rawItemMap` is incomplete — which is the input to
`markSourceDeletedByMissingNsmNums`. The §3-2 stamping limits the blast radius to
≤50 probes per cycle plus a 168 h cooldown, but the scan silently under-reports.

### R6 — LOW/MEDIUM. Legacy documents enter the archive as notices

`isCrawlableNsmBill` only requires a positive integer `billNo`, so the 6-digit
legacy ids (`050470` → `50470`) pass. They are not in the archive and do not
collide with any existing `noticeNum` (measured: 0 collisions among page 160's
33 numeric ids), so on switch-on they would be archived as
`NEW_SYNC_ONLY_BILLS` notices and pushed into the cache — a 2002 report rendered
as a bill notice.

### R7 — LOW. Notifications

`beginChangeNotificationCollection` only **batches** notifications; it does not
suppress them (bootstrap uses `beginChangeNotificationSuppression` instead, and
the scheduled sync phase does not). However, `dispatchChangeNotification` is
called only after a **diff** event is appended, so a first-seen row with no
baseline snapshot does not emit one. Notifications therefore scale with the
`접수` (pending) import — page 1 measured 18 `접수` with ~42% of page 1 unarchived,
i.e. tens of rows per early cycle — not with the whole import. Re-compare of
existing pending rows (`EXISTING_PENDING_RECOMPARE`) also grows slightly.

### R8 — LOW. Stamping cost and diffchain growth

Every completed scan stamps `nsm_last_seen_in_list_at` for every seen row
(400-row chunks; 2.4-5.9 s for 12k-19.8k rows on a DB copy), twice per cycle
(cron + sync). Each imported row also adds a diffchain baseline, and
`comparableEventTotal` (31,251 today) grows accordingly.

### R9 — Config path. Enablement is compose-level, not `.env`

There is **no** `backend/.env` on the production host; the container receives
`CRAWLING_NSM_ENABLED=0` and friends through compose. Note 12 recorded that
compose `environment` overrides `env_file`, so the switch has to be made where
the container actually gets its env, and a `CRAWLING_NSM_SOURCE=likms` line added
next to it.

## 4. Recommended order if the switch is wanted

1. **Keep deletion detection off for the first window**:
   `CRAWLING_NSM_DELETION_DETECTION_ENABLED=0` while turning on
   `CRAWLING_NSM_SOURCE=likms` + `CRAWLING_NSM_ENABLED=1`. New rows still get
   imported and stamped, the detail probe stays inert, and no LIKMS-only bill can
   be falsely marked deleted (R1, R3 disappear; they return when detection is
   re-enabled).
2. **Cap the scan** before enabling: pass `maxPages` for the pending stream, or
   find a working LIKMS progress-stage filter, otherwise R2 stands at ~23k
   requests/day and the cycle may not finish inside 20 minutes.
3. **Move the deletion authority to the source** before re-enabling detection:
   route detail capture/probe through the adapter (`getDetail` already follows
   the source; `captureNsmDetailFull` and `probeNsmDeletedBillOutcome` do not),
   and extend the §3-2 cooldown/stamp columns to the detail-probe path.
4. Expect R4/R6 to be visible for one or two cycles after the first scan; the
   legacy-document rows can be filtered by rejecting ids that are not 7-digit
   `의안번호` (a `isCrawlableNsmBill` tightening).

## 5. Not verified / limits

- Only 8 of 160 pages were sampled for coverage; the unmeasured region is the
  page range between 120 and 160, where the tail's legacy documents begin (page
  153-158 returned full pages of rows, several of which were all non-numeric).
- Page 160 returned 56 rows on two measurements but page 155 returned 0 rows once
  (structural, legacy documents) — the exact boundary of the legacy block was not
  mapped.
- The first-scan new-row count is an extrapolation, not a full crawl: the whole
  list was never walked end-to-end (that alone would be ~160 requests).
- LIKMS rate-limit thresholds were not probed; only ordinary page requests were
  measured, with 0.9-1.2 s spacing.
- Nothing in production was switched on for this assessment.

## 6. Commands used

```bash
# LIKMS list inventory (pal-crawl 2.3.0, one request per page)
node /tmp/likms-sample.js          # total/totalPages + 5 sampled pages
node /tmp/likms-coverage.js        # per-page archive coverage against the DB copy
node /tmp/likms-nsm-probe.js       # LIKMS-only bill vs NSM detail deletion marker

# Read-only DB checks (production copy, 5.5 GB)
sqlite3 -readonly backend/lawcast.db \
  "SELECT lifecycle_status, COUNT(*) FROM notice_archives GROUP BY 1;"
sqlite3 -readonly backend/lawcast.db \
  "SELECT COUNT(*) FROM notice_archives WHERE contentId IS NULL AND lifecycle_status='active' AND content_bill_number IS NULL;"

# Production verification after the v1.15.0 deploy
docker inspect lawcast-backend --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E 'CRAWLING_NSM|APP_VERSION'
sqlite3 -readonly /var/lib/docker/100000.100000/volumes/lawcast_lawcast_db/_data/lawcast.db \
  "SELECT name FROM pragma_table_info('notice_archives') WHERE name LIKE 'nsm%';"
```
