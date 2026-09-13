# LawCast Backend Security Audit: Unbounded Request Defenses

## Summary
Read-only audit of `/backend/src/controllers` focused on client request boundary validation. **Critical gaps identified** in pagination, comma-separated bulk inputs, search query length, and cursor handling. Rate limiting exists only for discussions endpoints.

## Key Findings by Category

### 1. PAGINATION (API.PAGINATION constants)
**Hard Limits:**
- MAX_LIMIT: 100 (not MIN_LIMIT: 1)
- Enforced in: NoticesQueryService.getArchivedNotices(), ChangeTrackingService.getRecentChanges(), DiscussionsService.getThreads()
- Math.min(MAX_LIMIT, Math.max(MIN_LIMIT, limit))

**Defaults:**
- DEFAULT_LIMIT: 10
- MIN_PAGE: 1

**Bypass Risk: LOW (hard caps enforced)**
- All major paginated endpoints respect MAX_LIMIT=100
- Page parameter only has MIN_PAGE=1, no MAX_PAGE → unbounded pagination allowed but memory-safe due to OFFSET clause

### 2. COMMA-SEPARATED BULK IDS (noticeNums parameter)
**CRITICAL VULNERABILITY:**
- Endpoint: GET /api/notices/archive?noticeNums=123,456,789,...
- Parser: NoticesQueryService.parseNoticeNums() [L280-293]
- **NO UPPER LIMIT on array size** - split(',') with no bounds check
- Service: NoticesQueryService.getArchivedNotices() → getArchivedNoticesByNoticeNums()
- Attack: `noticeNums=1,2,3,...,100000` → O(n) SQL IN query, can exhaust memory/CPU
- Verified: normalizeNoticeNum() only validates format, not array length

**Severity: HIGH**
- Bypass: Send 10,000+ comma-separated IDs → SQL IN(...) with thousands of parameters
- Hard cap: None detected

### 3. SEARCH QUERY LENGTH
**Configuration:**
- APP_CONSTANTS.API.SEARCH.MAX_LENGTH: 120 characters
- **NOT ENFORCED in controller** - no decorator validation

**Validation Location:**
- NoticeSearchService.executeSearch(): only .trim() applied
- ChangeTrackingService.getRecentChanges(): normalizedSearch = (query.search || '').trim().toLowerCase(), no length check

**Severity: MEDIUM**
- Bypass: Send 10MB search string → FTS query builds unbounded, potential ReDoS in split(/\s+/)
- Pattern: search.trim().split(/\s+/).map((term) => ...) in buildFtsMatchQuery()
- Hard cap: None, truncation missing

### 4. PAGINATION LIMIT PARAMETER (each endpoint)
**Controller Handling:**
- GET /api/notices/archive: @Query('limit', new DefaultValuePipe(10), ParseIntPipe)
  - No upper bound decorator, relies on service-level Math.min()
- GET /api/notices/search: same
- GET /api/notices/changes: Math.min(100, Math.max(1, limit)) in service [line 1341]
- GET /discussions/threads: Math.min(100, Math.max(1, limit)) in service [line 193]

**Bypass: NONE - service enforces Math.min()**

### 5. CURSOR-BASED PAGINATION
**Endpoints:**
- GET /api/notices/changes: cursor parameter (string)
- GET /discussions/threads/:threadId: cursor parameter (string)

**Implementation:**
- ChangeTrackingService.parseRecentChangesCursor() [~1400]: `value.split('|')` → Date + eventId
  - Date parsing: new Date(detectedAtRaw) → validates NaN
  - Integer check: Number.isInteger(id) && id <= 0 rejects
- DiscussionsService.getThreadDetail(): cursor parsed as Number.parseInt(cursorParam, 10)

**Severity: LOW** - cursor format validated before use

### 6. DATE RANGE FILTERING
**Endpoints:**
- GET /api/notices/archive?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
- GET /api/notices/search (same)
- GET /api/stats/proposals?startDate&endDate

**Validation:**
- NoticesQueryService.parseDateInput() [L264-272]: `/^\d{4}-\d{2}-\d{2}$/` regex enforced
  - Malformed dates → undefined (safe)
- ChangeTrackingService: parseIsoDate() in controller, then passed to service
- ProposalStatisticsService: **NO validation** of startDate/endDate

**Severity: MEDIUM (ProposalStatisticsService)**
- Bypass: POST dates of arbitrary length → service doesn't validate format
- Hard cap: None

### 7. EXPORT/DOWNLOAD (File Generation)
**Endpoint:**
- GET /api/notices/:num/export → buildArchiveExportZip()

**Risk Assessment:**
- Parameter: only noticeNum (int, validated)
- Output: StreamableFile with Content-Disposition
- No bulk export endpoint detected
- **Severity: LOW** - single-notice export

### 8. SCREENSHOTS
**Endpoint:**
- GET /api/notices/:num/screenshot

**Risk Assessment:**
- Parameter: only noticeNum (int)
- Output: Binary blob
- No bulk download

### 9. RATE LIMITING
**Discussions Only:**
- DiscussionsController: @UseFilters(DiscussionsRateLimitFilter)
- Policy: read=60/min, write=10/min per IP
- **Other endpoints have NO rate limiting**

**Verification:**
- GET /api/notices/search (unlimited)
- GET /api/notices/changes (unlimited)
- GET /api/stats/proposals (unlimited)

**Severity: MEDIUM** - DoS-able search/change enumeration

### 10. BODY ARRAYS/UPLOADS
**POST Endpoints:**
- POST /api/webhooks (CreateWebhookDto)
- POST /api/push/subscriptions (CreateWebPushSubscriptionDto)
- POST /api/push/subscriptions/preferences (UpdateWebPushPreferencesDto)
- POST /discussions/threads (CreateThreadDto)
- POST /discussions/threads/:threadId/comments (CreateCommentDto)

**Validation:**
- Global ValidationPipe with whitelist=true, forbidNonWhitelisted=true
- No request size limit in main.ts (default express ~100KB JSON)
- DTOs not visible in audit scope → likely have @IsString, @MaxLength decorators but not verified

**Assumed: MEDIUM** - default express limit ~100KB, no explicit override found

### 11. QUICK KEYWORDS ENDPOINT
**Endpoint:**
- GET /api/notices/keywords?limit=8

**Handling:**
- @Query('limit', new DefaultValuePipe(8), ParseIntPipe)
- Service: crawlingService.getQuickKeywordSuggestions(limit)
- **NO upper bound enforcement** in controller/service visible
- Assumed unbounded fetch from cache

**Severity: LOW** (likely cache-backed, small dataset)

## Concrete Bypasses Summary

| Endpoint | Parameter | Bypass | Severity | Hard Cap | Default |
|----------|-----------|--------|----------|----------|---------|
| /archive | noticeNums=1,2,... | 10k+ CSV→SQL IN() | HIGH | None | N/A |
| /archive | search | 10MB string | MEDIUM | None | "" |
| /search | search | 10MB string | MEDIUM | None | "" |
| /changes | search | 10MB string | MEDIUM | None | "" |
| /changes | limit | Default enforced | LOW | 100 | 10 |
| /stats/proposals | startDate/endDate | Any string | MEDIUM | None | undefined |
| all | page | Unlimited offset | LOW | N/A (offset-safe) | 1 |
| /discussions/* | * | Rate limited 60/min | LOW | Yes | 60 |

## Recommended Actions
1. **URGENT**: Add @MaxLength(120) or service-level truncation to search parameters
2. **URGENT**: Add @MaxLength or split-array-length limit to noticeNums parameter (suggest MAX=1000)
3. Add request size limit middleware (e.g., express.json({limit: '1MB'}))
4. Add @MaxLength(10) to date range parameters in ProposalStatisticsController
5. Extend rate limiting to /api/notices/*, /api/stats/* endpoints
