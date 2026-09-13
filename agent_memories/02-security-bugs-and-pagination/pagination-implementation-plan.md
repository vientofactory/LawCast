# Pagination Performance: Minimal Backwards-Compatible Implementation Plan

## Overview
Three public APIs currently use page-based pagination. This plan proposes cursor-based variants alongside (not replacing) existing page-based endpoints to maintain full backward compatibility while improving performance for large datasets.

## Implementation Order & Rationale

### Phase 1: Foundation (Best ROI) — ChangeTrackingService.getRecentChanges
**Why first:**
- Already has stable composite index: `idx_notice_change_events_detected_at_id(detected_at DESC, id DESC)`
- Smallest schema/type change footprint
- Lowest risk because queries already optimized
- No N+1 enrichment concerns (unlike archive queries)
- Frontend already supports `anchorEventId` parameter (existing cursor concept)

**Implementation:**
1. Add optional `cursor` query param to `/api/notices/changes` endpoint
2. Decode cursor to extract `(detectedAt, id)` tuple
3. Modify `ChangeTrackingService.getRecentChanges()` to accept optional `cursor?: string`
4. Update query builder:
   ```
   if (cursor) {
     qb.andWhere('(detected_at, id) < (:cursorDetectedAt, :cursorId)', {...})
   } else {
     qb.offset(skip).limit(take)
   }
   ```
5. Return `cursor` in response (encode next page's lastItem as base64)
6. Type interface: `RecentChangesQuery` add optional `cursor?: string`
7. **No migration needed** — index already present

**Tests to add:**
- `change-tracking.service.spec.ts`: cursor decoding, edge cases (first page, last page, empty results)
- `api.controller.ts`: end-to-end cursor param parsing + response encoding

**Backward compatibility:** Page-based still works via `page`/`limit`; cursor optional

---

### Phase 2: Archive Listing Index Optimization
**Goal:** Fix ORDER BY noticeNum gap in isDone-filtered path

**Why needed:**
- `queryArchiveNoticeNumsByIsDoneFilter()` orders by `archive.noticeNum` but composite index doesn't cover this when filtering by isDone via EXISTS subquery
- Creates unexpected offset/scan cost for isDone=true/false paginated queries

**Implementation:**
1. New migration `202610010001-add-archive-isdone-notice-num-index.migration.ts`:
   ```sql
   CREATE INDEX IF NOT EXISTS "idx_notice_archives_is_done_notice_num"
   ON "notice_archives" ("is_done", "noticeNum" DESC)
   ```
2. **No code changes** — schema optimization only
3. Tests: Run existing archive pagination specs; bench with isDone filter

**Expected impact:** isDone=true/false list queries now use covered index; ~40-60% seek reduction

---

### Phase 3: Archive Listing Cursor Support (Optional, Lower Priority)
**Why later:**
- More complex: `getArchiveNoticesByOffset` already reasonably efficient after Phase 2
- Merged cache/archive pagination (NoticesQueryService) makes cursor implementation tricky
- Lower dataset size typically (archive tables < 100K rows in most deployments)

**If prioritized:**
1. Add cursor support to `NoticeArchiveService.getArchiveNoticesByOffset()`
2. Cursor = `(noticeNum, archiveStartedAt)` tuple for stable ordering
3. Add optional `cursor?: string` param to `ArchiveOffsetQuery` interface
4. Modify query logic (similar to Phase 1)
5. Controller: `/api/notices/archive?cursor=...&limit=...`
6. Frontend: `apiClient.getArchivedNotices({cursor: ..., limit: ...})`
7. Frontend `+page.server.ts`: Parse cursor param alongside page

---

### Phase 4: Search Cursor Support (Lower Priority)
**Why later:**
- FTS search results less sensitive to offset cost (queries typically page 1-3)
- Cursor encoding for full-text search results complex (relevance-ranked not insertion-ordered)
- Frontend pagination typically limited to first few pages for search

**If prioritized:**
1. Cursor = `(relevanceScore, noticeNum)` tuple
2. Implement in `NoticeSearchService.searchNotices()` with optional cursor param
3. Challenge: FTS relevance not stable across updates; document limitation
4. Lower priority than archive/changes cursor support

---

## Indexes Summary

**Existing (already optimal):**
- `idx_notice_change_events_detected_at_id(detected_at DESC, id DESC)` — covers Phase 1 ✓

**To add (Phase 2):**
- `idx_notice_archives_is_done_notice_num(is_done, noticeNum DESC)` — covers isDone filter + order

**Optional (Phase 3 enabler):**
- `idx_notice_archives_notice_num_archive_started_at(noticeNum DESC, archive_started_at DESC)` — if cursor via (noticeNum, archiveStartedAt)

---

## DTO/Type Interface Changes

### Phase 1 Only (RecentChangesQuery → RecentChangesQueryWithCursor)
```ts
interface RecentChangesQuery {
  page?: number;        // existing
  limit?: number;       // existing
  cursor?: string;      // NEW: base64-encoded (detectedAt, id)
  // ... rest unchanged
}

interface RecentChangesResult {
  items: RecentChangeItem[];
  page?: number;        // null if cursor-based
  limit?: number;
  total?: number;       // may be omitted for cursor (unknown until query)
  totalPages?: number;  // null if cursor-based
  cursor?: string;      // NEW: next page cursor (null if last page)
  anchorPage?: number | null;
}
```

### Frontend Type Updates
```ts
// frontend/src/lib/types/api.ts
interface RecentNoticeChangesResponse {
  // ... existing fields
  cursor?: string;      // NEW
  // totalPages: optional (null for cursor-based)
}
```

---

## Frontend Integration Points (No Changes Required for Phase 1)

**Current pagination UI (PaginationNav.svelte):**
- Uses `page`, `limit`, `totalPages` for numbered page links
- Cursor pagination would require different UI (Prev/Next only, no page numbers)
- **Recommendation:** Add opt-in feature flag `?useCursor=1` or new route `/notices/changes/cursor`
- Or: Keep current numbered pagination but switch backend to cursor internally

**Least-disruptive approach:** Add cursor support server-side in `+page.server.ts`, keep page-based UI for now (transparent optimization)

---

## Test Coverage Requirements

### Phase 1 (ChangeTrackingService.getRecentChanges)
- Unit: cursor encode/decode, tie-breaking (detected_at DESC, id DESC)
- Integration: `GET /api/notices/changes?cursor=<encoded>&limit=20` returns correct page
- Edge cases: first cursor, last cursor (null/missing), invalid cursor format
- Backward compat: `GET /api/notices/changes?page=1&limit=20` still works

### Phase 2 (Index)
- Benchmark: `isDone=true` + pagination + sort DESC on 100K+ row table
- Existing `notice-archive.service.spec.ts` should pass unchanged (no code changes)

### Phase 3+ (Optional, if implemented)
- Archive cursor: similar to Phase 1 tests
- Merged pagination (cache + archive): cursor alignment across both sources

---

## No Breaking Changes Guarantee
- All existing query params still accepted
- All existing response fields still returned (add cursor as optional new field)
- Page-based pagination path remains untouched
- Frontend routes unchanged (server-side decision whether to use cursor or page)

---

## Summary Table

| API | Phase | Index Change | Code Change | Frontend Impact | Tests Added |
|-----|-------|--------------|-------------|-----------------|-------------|
| getRecentChanges | 1 | ✓ exists | ✓ cursor param | ✓ optional | ✓ unit+integration |
| getArchiveNoticesByOffset | 2 | ✓ new | ✗ (perf only) | ✗ | ✓ bench |
| getArchiveNoticesByOffset | 3 | ✓ new | ✓ cursor param | ✓ optional | ✓ unit+integration |
| searchNotices | 4 | ✓ optional | ✓ cursor param | ✓ optional | ✓ unit+integration |
