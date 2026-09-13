# Backend Pagination Audit – Findings Log

## Scope
Backend NestJS/TypeORM application with SQLite database (assumed, SQLite-specific syntax detected).
Migration 202609080001 creates two composite indexes for discussion_threads (not related to notice pagination).

## PUBLIC API ENDPOINTS & SERVICES

### 1. NoticeSearchService.searchNotices
**Endpoint:** `GET /api/notices/search?q=...&page=...&limit=...`
**Service:** `NoticeSearchService.searchNotices(SearchNoticesQuery)`
**Query params:** `page`, `limit`, `includeDone`, `fullText`
**Return type:** `SearchNoticesResult` (items[], total, page, limit, totalPages, keyword, source)
**Frontend caller:** `frontend/src/lib/api/client.ts` → `searchNotices()`
**Frontend route:** `frontend/src/routes/notices/+page.svelte`
**Pagination type:** **Page-based (offset) via page/limit**

Key details:
- Calls `NoticeArchiveService.getArchiveNotices()` with page/limit internally
- Merges results with crawler data
- Frontend supports page size options: [10, 20, 30, ..., 100]
- Default limit: 10, Max limit: 100

### 2. NoticeArchiveService.getArchiveNotices
**Controller path:** Via `NoticesQueryService.getArchivedNotices()`
**Endpoint:** `GET /api/notices/archive?page=...&limit=...&search=...&isDone=...`
**Service method:** `NoticeArchiveService.getArchiveNotices(ArchiveListQuery)`
**Query params:** `page`, `limit`, `search`, `startDate`, `endDate`, `sortOrder`, `isDone`, `fullText`
**Return type:** `{items: ArchiveNoticeItem[], page, limit, total, totalPages, search}`
**Frontend caller:** `apiClient.getArchivedNotices()`
**Frontend route:** `frontend/src/routes/notices/+page.svelte`
**Pagination type:** **Page-based (offset) via page/limit**

### 3. NoticeArchiveService.getArchiveNoticesByOffset (INTERNAL USE)
**Service method:** `NoticeArchiveService.getArchiveNoticesByOffset(ArchiveOffsetQuery)`
**Query params:** `skip`, `take`, `search`, `startDate`, `endDate`, `sortOrder`, `isDone`, `knownTotal`, `fullText`
**Return type:** `{items: ArchiveNoticeItem[], total, search}`
**Internal use:** Called by `NoticesQueryService.getArchivedNotices()` for merged cache/archive pagination
**Pagination type:** **Offset-based (skip/take)**
**Current status:** Already uses offset-based internally; NOT cursor-based

### 4. ChangeTrackingService.getRecentChanges
**Endpoint:** `GET /api/notices/changes?page=...&limit=...&search=...&eventType=...`
**Service method:** `ChangeTrackingService.getRecentChanges(RecentChangesQuery)`
**Query params:** `page`, `limit`, `search`, `noticeNum`, `eventType`, `sortOrder`, `fromEventId`, `toEventId`, `fromDetectedAt`, `toDetectedAt`, `anchorEventId`, `excludeLegacyGenesisSource`, `excludeIsDoneEvents`, `comparableOnly`
**Return type:** `RecentChangesResult` (items[], page, limit, total, totalPages, anchorPage)
**Frontend caller:** `apiClient.getRecentNoticeChanges()`
**Frontend route:** `frontend/src/routes/notices/changes/+page.svelte`
**Pagination type:** **Page-based (offset) via page/limit**

## Current Index Structure (Post-Migration)
- **notice_archives table:**
  - `idx_notice_archives_archive_started_at` (archive_started_at)
  - `idx_notice_archives_is_done` (is_done)
  - `idx_notice_archives_notice_num` (noticeNum) - unique
  - Several lifecycle/metadata indexes
  
- **notice_change_events table:**
  - `idx_notice_change_events_detected_at_id` (detected_at DESC, id DESC) - **covers pagination ordering**
  - `idx_notice_change_events_event_type_detected_at_id` (event_type, detected_at DESC, id DESC)
  - `idx_notice_change_events_notice_num_detected_at_id` (notice_num, detected_at DESC, id DESC)
  - `idx_notice_change_details_is_done_event_id` (partial, where field_path='isDone')

- **discussion_threads table:**
  - `idx_discussion_threads_updated_at_id` (updated_at DESC, id DESC) - NEW (202609080001)
  - `idx_discussion_threads_status_updated_at_id` (status, updated_at DESC, id DESC) - NEW (202609080001)

## Cursor Readiness Assessment

### NoticeSearchService.searchNotices
- **Current:** Page-based (page/limit)
- **Cursor readiness:** LOW - would require schema change (add cursor-encoded column)
- **Safe to extend:** YES, can add optional `cursor` param alongside `page` for backward compatibility
- **Recommended:** Add cursor support for large result sets (>100K records)

### NoticeArchiveService.getArchiveNotices / getArchiveNoticesByOffset
- **Current:** getArchiveNotices uses page/limit; getArchiveNoticesByOffset uses skip/take internally
- **Cursor readiness:** MEDIUM - noticeNum ordering is indexed but requires direction consistency
- **Safe to extend:** YES, can add optional cursor params; skip/take already offset-optimized
- **Ordering:** `archive.noticeNum` ASC/DESC (currently used)
- **Issue:** ORDER BY noticeNum not covered by composite index in isDone-filtered path
- **Recommended:** Add cursor variant for better large-offset perf

### ChangeTrackingService.getRecentChanges
- **Current:** Page-based (page/limit)
- **Cursor readiness:** HIGH - already has `detected_at, id` ordering with composite index
- **Safe to extend:** YES, can add optional `cursor` param; existing indexes support this
- **Existing index:** `idx_notice_change_events_detected_at_id(detected_at DESC, id DESC)` ✓
- **Recommended:** Priority for cursor implementation (best index coverage)

## Frontend Response Field Expectations

### SearchNoticesResult (frontend/src/lib/types/api.ts)
```ts
items: SearchNoticesItem[] (num, subject, proposerCategory, committee, link, contentId, isDone, 
                             isArchived, aiSummary, aiSummaryStatus, lifecycleStatus, 
                             sourceDeletedAt, attachments, archiveStartedAt, lastUpdatedAt)
total: number
page: number
limit: number
totalPages: number
keyword: string
source: 'archive' | 'crawler' | 'mixed'
```

### ArchiveNoticeListResponse (frontend/src/lib/types/api.ts)
```ts
items: Notice[]  (num, subject, proposerCategory, committee, link, isDone, archiveStartedAt, 
                  lastUpdatedAt, aiSummary, aiSummaryStatus, lifecycleStatus, sourceDeletedAt, 
                  contentId, changeEventCount, attachments)
page: number
limit: number
total: number
totalPages: number
search: string
startDate?: string
endDate?: string
sortOrder?: 'asc' | 'desc'
aiSummaryEnabled?: boolean
stats: { cacheCount, matchedCacheCount, archiveCount, totalArchiveCount, mergedCount }
```

### RecentNoticeChangesResponse (frontend/src/lib/types/api.ts)
```ts
items: RecentNoticeChangeItem[] (id, noticeNum, subject, detectedAt, eventType, source, 
                                 eventHeight, eventHash, changedFieldCount, diffSummary)
page: number
limit: number
total: number
totalPages: number
anchorPage?: number | null
```

## Performance Bottlenecks Identified
1. **isDone filtering:** Uses EXISTS subquery on summary_state; noticeNum ORDER BY not in composite index
2. **Archive listing with search:** Full table scan on subjects/committees when search+isDone
3. **FTS search:** Custom query parsing (buildFtsMatchQuery) adds CPU overhead
4. **Change tracking page offset:** Stable with existing indexes; good candidate for cursor optimization
5. **N+1 enrichment:** Archive items fetch summary_state + diffchain overlays per result
6. **Merged pagination:** NoticesQueryService merges cache + archive; complex offset calculation

## Discussion Migration (202609080001)
- Adds indexes for discussion_threads listing (unrelated to notice pagination)
- Uses `updated_at DESC, id DESC` pattern consistent with change_tracking indexes
- Pattern suggests stable composite ordering best practice for pagination
