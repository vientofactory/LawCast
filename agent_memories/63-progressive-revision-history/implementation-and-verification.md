# Progressive Revision History

## Scope and contract

Implementation following [frontend 1.26.0](../62-revision-history-ux/implementation-and-verification.md). The sections below preserve local implementation evidence. The owner subsequently authorized [backend 1.20.0 and frontend 1.27.0 release and production verification](release-verification.md). Feature branches: backend `codex/revision-history-pagination`, frontend `codex/progressive-revision-history`.

`GET /api/notices/:num/changes` retains `noticeNum`, `items`, and the page-local `count`. It adds optional input `beforeHeight` and response fields `hasMore` and `nextBeforeHeight`. The public endpoint now sorts by revision height descending, with an exclusive height cursor. Default page size is 20, maximum 100; pagination has no 100-record total ceiling. Invalid nonpositive, fractional or unsafe cursors return 400. Terminal and empty pages return `hasMore: false` and a null cursor.

The contract is maintained in `backend/README.md`. Existing Jest/SQLite/HTTP regressions and the existing SSR consumer fixture are reused instead of creating a second Postman workspace or publishing API data externally. No existing Postman/OpenAPI artifact was found for this endpoint.

## Backend implementation

- `ChangeTrackingService.getNoticeChangeTimelinePage` uses a limit-plus-one lookahead and the existing unique `(notice_num, event_height)` index. There is no full-count query or all-history read on the public path.
- The legacy internal `getNoticeChangeTimeline` and complete export/archive history paths retain their existing ordering and behavior. No snapshot, event, hash, notification or archive trigger is mutated.
- The controller parses `beforeHeight` with Nest's integer pipe; the service validates positive safe integers. The response change is additive apart from the documented height ordering, which makes pagination independent of clock/backfill timestamp order.
- Controller service mocks include the new method.

## Frontend behavior

- The root detail component owns the notice-scoped history, cursor, request generation and abort controller. It merges keyed records in descending height order and preserves appended pages when selecting a historical view or refreshing SSR data for the same notice.
- Switching notices resets the owner and cursor, aborts the prior request and ignores stale completions. A returned page must match the notice and strictly advance the exclusive cursor; duplicate head pages from an older backend cannot create an automatic request loop.
- An intersection observer near the list bottom requests one older page at a time. Explicit buttons remain available above and below the list, including without IntersectionObserver support. Errors stop automatic loading and retain the existing list and comparison selection until an explicit retry.
- Three theme-aware skeleton cards appear only while the request is pending. They match record-card geometry, are hidden from assistive technology, and pulse only when reduced motion is not requested. A separate status announces loading; the existing list is not replaced.
- New records appear in both comparison selectors. A comparison link to an unloaded record is distinguished from an invalid record and becomes usable once its contiguous page range has loaded. Earlier pages are not stitched into disjoint ranges: all intervening available events are retained for snapshot replay.
- Explicit loading preserves keyboard focus without forcing the viewport to follow a moving button. The final page announces completion. Selection, historical viewing and existing comparison scroll policy remain unchanged.

## Verification coverage

- Backend SQLite cursor tests seed 125 records and an unrelated notice, use timestamps in the opposite order, add a new head between requests and verify exact 125-to-1 traversal without duplicates or notice leakage. Tests also cover page caps, terminal/empty pages, invalid cursors, detail values and indexed query plans without temporary sorting.
- Nest HTTP regression verifies response compatibility, default parameters, exclusive-cursor parsing and malformed-query 400 responses.
- Browser regressions use a dedicated 125-record fixture: delayed response/skeleton visibility, one request in flight, complete loading beyond 100, cross-page comparison, retaining pages through historical viewing, error/retry, stale-response isolation and unloaded deep-link recovery.
- The browser mock proxy implements the same cursor contract. The production Node SSR consumer fixture verifies that the actual browser request forwards the cursor through `/api` to the configured backend and reaches the final page.

## Deployment dependency

**Deploy the backend first**, verify its root-pointer deployment, then release the frontend. The frontend requires the exclusive cursor for older pages. Optional metadata handling lets existing three-record mocks and terminal legacy windows render, but does not make an old backend capable of paging; nonadvancing responses intentionally surface a retryable error.

## Final local results

- Backend lint, TypeScript check and build passed; **88 Jest suites / 1,282 tests passed**, including real SQLite pagination and Nest HTTP parsing.
- Frontend lint and Svelte check passed with zero errors/warnings; Cloudflare build passed. **48 mock UI/detail/navigation tests and 16 production Node SSR tests passed**. The six progressive-history cases were repeated after synchronizing screenshot capture with the disclosure animation, all passing.
- Desktop light and mobile dark skeleton screenshots were inspected. Reduced-motion mode disables skeleton pulsing. The loading live region sits outside the busy placeholder region so the announcement is not suppressed.
- These are local implementation and verification results. No commits, PRs, releases, deployments or shared Postman publications were performed for this change.

## History deep-link scrolling follow-up

The detail route now handles requested history scrolling in `afterNavigate`, including component reuse, rather than only `onMount`. `timeline=true` (and its existing true aliases) targets the history section; `cmpFrom`, `cmpTo` or `cmpShowAll` target a rendered comparison result, falling back to the section for incomplete/invalid selection. Matching parameters open the disclosure before positioning. Explicit unrelated fragments retain native anchor behavior. In-place comparison `goto` operations skip the jump while their `comparisonPending` flag is active.

A local regression reproduced a paused disclosure animation after navigating to another revision in the same component: the router reset the document to the top, while `getAnimations().finished` remained pending in the offscreen `content-visibility: auto` subtree. The route temporarily exposes that section, waits for finite animations, restores deferred rendering, waits for layout frames and then scrolls the document to the target's measured position minus its CSS scroll margin. A token cancels stale positioning; a reference count ensures overlapping navigation tasks restore the temporary override. Scrolling the document directly also avoids scrolling clipped slide ancestors.

New browser checks cover direct timeline/comparison links, a display-only comparison flag, changes-list entry, historical revision navigation that reuses the component, and preserving the reading position during in-place comparison changes.

The scrolling follow-up passed frontend lint, Svelte check (0 errors/warnings), Cloudflare build and all **28 focused history/navigation/pagination browser tests**; the root guideline checker reported zero violations. This follow-up remains local and unreleased.

## Manual mock fixture

The existing 125-event fixture (`2210010`) is now discoverable by searching for `국가재정` in mock mode. Its list and detail title explicitly identify the progressive-loading test, and the list's event count matches the detail history. Its lifecycle remains active to avoid an unrelated renumbering warning.

Start the frontend with `DIFFCHAIN_UI_MOCK=1 npm run dev`, then open `http://localhost:5173/notices/2210010?timeline=true`. Older-page requests for this fixture alone wait 650 ms so the real loading skeleton can be inspected without response interception. Initial SSR, other mock notices and production requests do not receive this delay. The README also provides a cross-page comparison link (`cmpFrom=90&cmpTo=125`).

The list-discovery and skeleton regression uses the unmodified mock proxy response. Together with the existing pagination and notice-list coverage, **93 browser tests passed and 1 was skipped**.
