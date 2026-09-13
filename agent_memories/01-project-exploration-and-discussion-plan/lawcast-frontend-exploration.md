# LawCast Frontend Exploration

## Detail Page Route
- **Route Path**: `frontend/src/routes/notices/[num]/`
  - Uses `[num]` (not `[id]`) as dynamic parameter for notice number
  - Route files: `+page.server.ts`, `+page.svelte`
  - No proposals detail page route (proposals only has listing at `+page.svelte`)

## Data Loading Pattern
**Server-side load function** (`+page.server.ts`):
- `export const load: PageServerLoad` pattern
- Fetches `apiClient.getNoticeDetail(noticeNum, { rev }, fetch)`
- Fetches `apiClient.getNoticeChanges(noticeNum, { limit: 100 }, fetch)`
- Can mock data with `isDiffchainUiMockEnabled()` for UI development
- Error handling with specific HTTP status codes (400, 404, 500)

**Client-side usage** (`+page.svelte`):
- Receives data as `export let data: { detail, changes }`
- Uses `$:` reactive statements extensively (NOT Svelte 5 runes yet)
- Derives reactive state from URL searchParams and data

## Components & UI Libraries
**Styling**:
- Tailwind CSS (v4+)
- Custom CSS variables for theming: `--lc-*` (e.g., `--lc-text-primary`, `--lc-surface-primary`, `--lc-border-soft`)
- Dark mode support via `html[data-theme='dark']`
- Custom border-radius override (all rounded elements use `0.5rem`)

**Icon Library**:
- FontAwesome v7.1.0 (`@fortawesome/svelte-fontawesome`)
- Solid icons: `faArrowLeft`, `faBell`, `faCheck`, `faChevronDown`, etc.

**Components Used in Detail Page**:
- `Header.svelte` - top navigation
- `AIBriefingCard.svelte` - AI summary display
- `NoticeChangeTimeline.svelte` - revision history/changelog
- `NoticeRevisionCompare.svelte` - diff view for comparing revisions
- `Alert.svelte` - info/warning/error/success alerts
- `Footer.svelte`

## Modal/Dialog/Form Patterns
**NO native modal/dialog elements** - uses custom state management:

**Expandable Sections** (managed with `let` state):
- `isArchiveMetaOpen` - archive metadata section toggle
- `isScreenshotExpanded` - screenshot preview toggle  
- `isChangeTimelineOpen` - changelog/timeline toggle
- State synced with URL query params: `?archive=1&screenshot=true&timeline=open`

**Form Components** (examined for patterns):
- `WebhookRegistrationForm.svelte` - form with validation, PoW challenge
- `WebPushConsentForm.svelte` - subscription management
- Pattern: `<form on:submit|preventDefault={handler}>`
- Use callback props: `onSuccess`, `onError`, `onClearMessage`
- No dialog wrapper - forms rendered inline or via conditional display

**State Management for Expandable Sections**:
- Query param parsing: `parseBooleanParam()` converts URL params to boolean
- Auto-scroll on load: `onMount()` with `tick()` and `scrollIntoView()`
- Transitions: `import { fade, slide } from 'svelte/transition'`

## Svelte 5 Rune Usage
**Currently using Svelte 5.41.0 BUT with Svelte 4 patterns**:
- Traditional `export let` for props
- `$:` reactive statements (not `$derived`)
- `let` for local state (not `$state` rune)
- No evidence of Svelte 5 exclusive features yet

## Styling Patterns
**Tailwind + Custom Classes**:
- Custom prefixed classes: `lc-button-primary`, `lc-text-primary`, `lc-panel-card`, `lc-banner-warning`, `lc-chip-blue`
- Transitions: `transition-all duration-200`, `hover:-translate-y-0.5`
- Responsive: `sm:`, `lg:` breakpoints used frequently
- Border-radius: `rounded-2xl`, `rounded-xl`, `rounded-lg` (all become `0.5rem`)

## Key Implementation Details
- Strong TypeScript usage with proper types (PageServerLoad, NoticeDetail, etc.)
- URL search params handled via `SvelteURLSearchParams` utility
- JSON-LD structured data for SEO in `<svelte:head>`
- Accessibility: ARIA labels, semantic HTML (nav, main, section)

---

## API Client Architecture
**File**: `frontend/src/lib/api/client.ts`

**Structure**:
- Centralized `apiClient` pattern - NOT export of individual functions
- Internal `request<T>()` generic function with error handling
- Supports custom fetch functions (for SSR/SSG in SvelteKit)
- NProgress integration for loading indicators

**Error Handling**:
- Cloudflare challenge detection
- JSON content-type validation
- Status code-specific error messages (400, 401, 403, 404, 409, 429, 5xx)
- Normalized `ApiError` class with status property

**Key API Methods**:
```
getNoticeDetail(noticeNum, { rev? }, fetch?)
getNoticeChanges(noticeNum, { limit? }, fetch?)
getArchivedNotices({ page, limit, search, startDate, endDate, sortOrder, isDone, ... }, fetch?)
searchNotices({ q, page?, limit?, includeDone? }, fetch?)
getRecentNoticeChanges({ page?, limit?, search?, eventType?, sortOrder?, ... }, fetch?)
getComparableNoticeChangesSummary(fetch?)
registerWebhook(requestData, fetch?)
getWebPushPublicConfig(fetch?)
registerWebPushSubscription(requestData, fetch?)
getCrawlingTransparency(fetch?)
getProposalStatistics({ granularity?, startDate? }, fetch?)
getSystemStats(fetch?)
getSystemHealth(fetch?)
```

**Frontend API Gateway** (`frontend/src/routes/api/[...path]/+server.ts`):
- SvelteKit server route proxies all `/api/*` calls to backend
- BASE_URL: `env.API_BASE_URL || 'http://localhost:3001/api'`
- Forwards GET, POST, PUT, DELETE with body streaming
- Supports query params and custom headers

---

## Notice Detail Page (`[num]/+page.svelte`) - Page Sections

**1. Navigation & Status Banners**
- Back link with breadcrumb (preserves list filters)
- Historical revision warning (if `?rev=N` mode)
- "입법예고 종료" (completed notice) banner
- "보존 상태로 전환됨" (source deleted) banner
- "의안번호 변경 이력" (renumbered) banner

**2. Notice Summary Card** (top hero section)
- Chips: 의안번호, status (진행중/종료됨), source status
- Title + proposer category + committee + archive time
- Share button (native Share API or clipboard fallback)
- "국회 페이지 열기" external link
- Optional: AI Briefing Card (if enabled)

**3. 입법예고 정보** (Metadata Facts)
- Grid of metadata: 의안번호, 제안자, 제안일, 소관위원회, 회부일, 입법예고기간, 제안회기
- Conditionally rendered if facts exist
- Data-testid attributes for E2E testing

**4. 제안이유 및 주요내용 원문** (Proposal Reason)
- Plain text content with whitespace-pre-line (preserves formatting)
- Warning banner if content missing

**5. 변경 추적 타임라인** (Collapsible Change Timeline)
- Wrapper: `<section id="change-tracking-timeline">`
- Bound to `isChangeTimelineOpen` state
- Auto-scroll to section if `?timeline=1` in URL
- Renders `NoticeChangeTimeline` component

**6. 아카이브 상세정보** (Collapsible Archive Metadata)
- `<details>` element (native HTML details)
- Screenshot preview toggle + download button
- Archive export (ZIP file download)
- Integrity status, SHA256 hash, HTTP metadata
- Bound to `isArchiveMetaOpen` state
- Query param sync: `?archive=1`

---

## Revision/Change Tracking Pattern

**Revision System**:
- `detail.revision` contains: `requestedRev`, `resolvedRev`, `headRev`, `hasDiffchain`, `isHistorical`, `hasLegacyGenesisBoundary`
- Historical view mode: `?rev=N` parameter
- Warning banner shown when viewing non-latest revision

**Change Timeline Component** (`NoticeChangeTimeline.svelte`):
- Props: `isOpen`, `changes`, `activeRevisionForUi`, `buildRevisionLink`, `isCompareMode`, `selectedFromRev/ToRev`, `revisionDiffItems`, `onSelectCompare`
- Each event shows: event type (created/updated/invalidated), detected time, source, event hash, field count
- "Invalidated" events highlighted (red warning chip)
- Source labels: "아카이브 저장", "의안번호 변경", "원문 HTML 갱신", etc.

**Compare Mode** (`NoticeRevisionCompare.svelte`):
- URL params: `?cmpFrom=N&cmpTo=M&cmpShowAll=1`
- Side-by-side field comparison with inline diff highlighting
- Supports showing all fields vs. only changed fields
- Before/After segments with visual diff (removed=red, added=green)
- Change type badges: "추가됨", "삭제됨", "수정됨"

---

## Real-Time / Polling Patterns
**NO real-time features currently**:
- No WebSocket
- No polling with setInterval in detail page
- Data loaded once via SSR (`load` function in `+page.server.ts`)
- Status page has ticking interval (not detail page)
- Archive metadata, screenshots, and ZIP exports are on-demand (buttons trigger loads)

---

## Markdown/Discussion/Comment Components
**Currently NONE**:
- `frontend/src/lib/components/discussions/` is empty
- No markdown renderer imported
- No comment/discussion thread components
- Proposal detail page does NOT have discussion area yet

---

## Other Notable Components
- `PaginationNav.svelte` - paginated notice lists
- `RecentNotices.svelte` - sidebar with recent notices
- `Alert.svelte` - reusable alert component
- `WebhookRegistrationForm.svelte` - form with validation
- `WebPushConsentForm.svelte` - Web Push subscription UI
- `PoWChallengeStatus.svelte` - Proof-of-Work challenge display
- `LoadingSpinner.svelte`, `LoadingOverlay.svelte`
