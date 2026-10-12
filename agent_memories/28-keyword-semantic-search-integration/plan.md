# Integrating Semantic Search into the `/notices` Keyword Search (Plan)

How to fold the `semantic-search` engine (KURE-v1 + FAISS sidecar) into the existing
SQLite FTS5/LIKE keyword search on the 전체 입법예고 board (`/notices`), while keeping
the standalone `/notices/semantic-search` page for backward compatibility.

**Status: PLAN ONLY — no code is changed by this document.** Design decisions,
contract changes, and verification steps are the deliverable; implementation follows
the phase order in §6.

---

## 1. Goal & Non-Goals

### Goal

A user typing into the **existing** search box on `/notices` should get relevance-ranked
semantic results with the filters, pagination, and card UI they already use — no separate
page to discover — and should degrade to today's keyword behavior whenever the engine is
unavailable or the user explicitly asks for keyword-only.

### Non-goals (this pass)

- **Do not remove or replace** `routes/notices/semantic-search/*` (kept for backward
  compat: bookmarks, the "의미 검색" entry link, the engine-status widget, existing e2e,
  share links). It stays flag-gated exactly as today.
- **Do not change** the semantic engine (`semantic-search/`), its artifacts, or the
  sidecar wire contract (`/search`, `/health`) beyond what §4/§5 explicitly require.
- **Do not change** `NoticeSearchService.searchNotices` (`/api/notices/search`) or its
  crawler-merge behavior; it stays the keyword engine and the existing semantic fallback.
- **Do not touch** the immutability / diffchain / notification invariants (AGENTS §6).

---

## 2. Current State (evidence)

### 2.1 Keyword search path (what `/notices` actually uses)

| Layer | Location | Behavior |
| ----- | -------- | -------- |
| Route | `frontend/src/routes/notices/+page.server.ts` | SSR load calls `apiClient.getArchivedNotices(...)` → `GET /api/notices/archive` |
| Route UI | `frontend/src/routes/notices/+page.svelte` | Filter form: search box, quick ranges, status, sort, page size, `fullText` toggle; empty state; `PaginationNav`; "의미 검색" entry link (`data-testid="semantic-search-entry"`, L798) |
| Controller | `backend/src/controllers/api.controller.ts` `getArchivedNotices` (~L213-254) | Maps query params → `noticesQueryService.getArchivedNotices` |
| Query service | `backend/src/modules/crawling/notices-query.service.ts` `getArchivedNotices` | Merges cached (in-memory) + archived rows, applies filters, offset-paginates, computes `stats` |
| Archive service | `backend/src/modules/notice/notice-archive.service.ts` `applyArchiveSearchFilters` (~L1683-1799) | **Substring `LIKE`** on `subject`/`committee`/`contentProposer`; **only when `fullText=true`** adds an FTS5 `MATCH` on `proposalReason` via `buildFtsMatchQuery` |
| FTS5 | `backend/src/migrations/202608080001-*.migration.ts` | `notice_archives_fts` (subject/committee/proposalReason, `unicode61`), trigger-synced |

Key facts that shape the integration:

- The board's search is **not** FTS5 by default — it is `LIKE '%q%'`; FTS5 is opt-in via
  `fullText=true` (원문 포함). Any "integrate semantic with the keyword search" design must
  coexist with both.
- Results are **`noticeNum`-ordered and offset-paginated**; `sortOrder` and `PaginationNav`
  assume a total ordering independent of the query.
- The list is a **merge** of archived rows and cache-only (active, not-yet-archived) notices
  (`notices-query.service.ts`). The semantic index is built **only from
  `notice_archives.proposalReason`** (`semantic-search/datasource.py`), so cache-only
  notices are invisible to the engine.

### 2.2 Semantic path (already production-wired)

| Layer | Location | Behavior |
| ----- | -------- | -------- |
| Sidecar | `semantic-search/service/app.py` | `GET /search?query=&k=` returns `results` (clear) + `weakResults` (weak band); `GET /health` reports `maxK`, `status`, index times |
| Backend service | `backend/src/modules/semantic-search/semantic-search.service.ts` | `searchSemantic(query,k)`: chunk windows widened until `k` distinct notices (`CHUNK_FETCH_INITIAL_FACTOR`, `CHUNK_FETCH_GROWTH`, cap from `/health`); **keyword fallback only when the first window fails** (feature disabled / engine down); empty clear tier is a real answer |
| Backend controller | `backend/src/modules/semantic-search/semantic-search.controller.ts` | `GET /api/notices/semantic-search` (`query`, strict `k` 1..50), `GET /api/notices/semantic-search/health` |
| Types/contract | `semantic-search.types.ts`, `semantic-search.constants.ts` | `results`/`weakResults` notice-deduped; `MAX_K=50`, `SIDE_CAR_MAX_CHUNK_K=200`; cross-language pinned by `semantic-search.contract.spec.ts` |
| Frontend page | `routes/notices/semantic-search/*`, `lib/utils/semantic-search.ts` | Flag `PUBLIC_SEMANTIC_SEARCH_ENABLED`; `?search=`; weak-tier reveal; engine-status widget; `SEMANTIC_MAX_QUERY_LENGTH=120` |

### 2.3 Measured quality (why this is worth doing)

From `agent_memories/20-semantic-query-quality-eval/query-quality-evaluation.md`:

- **61 queries: semantic hit@1 0.918 / hit@5 0.984 vs FTS 0.754 / 0.820.** FTS records
  total misses on citizen phrasing (paraphrase/synonym/약어) while semantic answers at rank 1.
- Absolute cosine thresholds **do not separate** noise from valid queries (§4/§10) — the
  shipped floor (0.25) excludes nothing. The tier design (`14-relevance-tier-search`) still
  supplies the clear/weak split, but must not be re-tuned as a noise filter.
- Name-class weakness: same-title 개정안 competition is the ranking ceiling; **hybrid
  (lexical subject-overlap) rerank** is the §5-1 recommendation, and the alias table
  (`lawcast_semantic/aliases.py`, session 20 §9) already fixes the ~22-acronym class.

These results justify putting semantic **in front of the user by default** on the board,
not only behind a separate page.

---

## 3. Design Decision: What "natural integration" means here

Three candidate shapes were considered:

| Option | Description | Verdict |
| ------ | ----------- | ------- |
| A. Empty-state assist | Keep keyword results exactly; only when keyword returns 0, auto-run semantic and show "이런 결과도 있어요". | Lowest risk, but does not deliver the request ("integrate into the keyword UI") and never improves non-empty queries where FTS ranks badly. Use as **Phase 1 subset** + fallback behavior. |
| B. Mode toggle on the board (**recommended**) | Add a `searchMode` to `/notices` (`auto` default; `keyword`; `semantic`). `auto` = semantic clear tier when the engine is ready, keyword otherwise. Same filters, same cards, relevance metadata. | Delivers the request, reuses the existing UI/endpoint shape, degrades cleanly, preserves the dedicated page. |
| C. Replace keyword with semantic | Board always semantic, keyword removed. | Rejected: loses exhaustive `LIKE`/FTS lookup, breaks `sortOrder`/pagination semantics, no fallback when the engine is down. |

**Recommendation: Option B**, with A as the degraded path. `auto` is the default only when
the feature flag is on; with the flag off the board is byte-identical to today.

### 3.1 The ordering/pagination problem (core design constraint)

Semantic results are a **bounded, rank-ordered list of notice numbers** (the engine ranks
chunks; the current public cap is 50 notices / 200 chunks). The board is **unbounded and
`noticeNum`-ordered with offset pagination**. The reconciliation:

- In `semantic`/`auto` mode the result set is **relevance-ordered and bounded** by an
  internal candidate cap (`SEMANTIC_SEARCH_HYBRID_MAX_NOTICES`, proposed default **100**,
  served from up to `SIDE_CAR_MAX_CHUNK_K=200` chunks — the public `MAX_K=50` stays a
  *public endpoint* limit and is **not** changed).
- The same `page`/`limit` still slice the **ranked** list, so `PaginationNav` keeps working;
  `total` is the count of semantic candidates that survive the filters (≤ cap). When
  `total ≤ limit`, pagination hides naturally.
- **`sortOrder` is ignored in semantic mode** (relevance is the order). The UI must not
  silently lie: hide/disable the sort control with a short note, or surface a new
  "관련도순" option that is only selectable when a query is active. Decide in §8-D2.
- Keyword mode is untouched: unbounded, `noticeNum`-ordered, paginated as today.

### 3.2 Filters

Date range, `isDone`, `proposer`, and `lifecycleStatus` are **not** known to the engine, so
they apply as a **post-filter** over the hydrated semantic candidates:

1. Semantic → ranked notice numbers + `{score, section, excerpt, weak}`.
2. Fetch those archive rows, apply `applyArchiveSearchFilters` (date/proposer) and the
   `isDone` / lifecycle logic.
3. Preserve semantic rank order; drop non-survivors; paginate.

Consequence to document in the UI: with restrictive filters the semantic result count can
shrink below the candidate cap (same trade-off the existing keyword fallback already
accepts). Over-request (candidate cap + margin) to reduce this.

### 3.3 Cache-only (unarchived) notices

The engine never sees cache-only active notices. In `auto`/`semantic` mode, **append
keyword-matched cache-only items after the semantic block** (deduped) so freshly crawled
bills are not lost; label them without a similarity score. This mirrors the existing
cache+archive merge and is the only way the board stays complete. (Alternative: accept the
gap and warn — rejected; it would regress freshness.)

### 3.4 `source_deleted` / `renumbered` rows

Memory 20 §7 finding 4: 878 `source_deleted` rows remain indexed and servable. The board
already renders them with the 소스 미존재(보존) / 보존 상태 chip. **Default: keep them and
render the same lifecycle chips in semantic mode** (consistency with keyword results).
Excluding them is §8-D3.

---

## 4. Backend Plan

### 4.1 Where the hybrid logic lives

Add a **new service** `backend/src/modules/notice/notices-hybrid-search.service.ts`
(name TBD per conventions) that orchestrates semantic → hydrate → filter → paginate, and
**extend the existing `/api/notices/archive` endpoint with an optional `searchMode` param**:

- Default (`searchMode` absent or `keyword`, or flag off): call
  `NoticesQueryService.getArchivedNotices` exactly as today — **zero behavior change**.
- `searchMode=semantic|auto`: the controller delegates to the hybrid service.

Rationale for extending `/api/notices/archive` rather than a new endpoint: the board's SSR
loader stays a single call, the card shape is unchanged (SSR payload minimization, session
17), and the frontend does not branch on two endpoints. Keep the response **additive**.

Why a new service and not a branch inside `NoticesQueryService`: that method is heavily
tested and encodes the cache/archive/isDone merge; leaving it untouched keeps the keyword
path provably unchanged.

### 4.2 Response contract (additive)

Extend `ArchiveNoticeListResponse` with:

```ts
// backend/src/modules/notice/*.types.ts + frontend/src/lib/types/api.ts
searchMode: 'keyword' | 'semantic' | 'auto';      // echoed
semantic?: {
  mode: SemanticSearchMode;                       // 'semantic' | 'keyword_fallback'
  fallbackReason: string | null;
  lastUpdateAt: string | null;
  candidateTotal: number;                         // pre-filter semantic count (≤ cap)
  weakResults: SemanticSearchResultItem[];        // for the empty-state reveal (see §5.3)
} | null;
```

Per-item relevance (only in semantic mode) rides on each `Notice`/card:

```ts
relevance?: {
  score: number | null;      // cosine, null for cache-only appended items
  section: string | null;
  excerpt: string | null;
  weak: boolean;             // true when surfaced from weakResults
};
```

- The new fields are **optional**; older consumers ignore them.
- `toNoticeCard` (`frontend/src/lib/server/ssr-cards.ts`) must carry `relevance` (SSR
  trimming rule from session 17: only fields the card renders may cross the loader).
- If the wire shape changes, **update the cross-language pin** (`semantic-search.contract.spec.ts`)
  in the same change (session 14 rule).

### 4.3 Reuse, do not reimplement

- Call `SemanticSearchService.searchSemantic(query, k)` (already handles widening, cap
  negotiation, weak tier, first-window fallback). Request `k = SEMANTIC_SEARCH_HYBRID_MAX_NOTICES`
  via an internal call — **do not** route through the public controller's `MAX_K=50`, and do
  **not** copy its strict `parseK` into the board.
- Hydrate with a **new `NoticeArchiveService` method**
  `getArchiveNoticesByRankedNums({ noticeNums, filters..., })` that:
  - fetches by `In(noticeNums)`, re-sorts to the semantic rank (pattern already exists in
    `getArchiveNoticesByNoticeNums`, L2119),
  - applies `applyArchiveSearchFilters` (date/proposer) + `isDone`/lifecycle,
  - returns survivors + total. Reuse the existing filter helper so FTS/LIKE semantics stay
    in one owner.
- `isDone` handling: reuse the `notice_archive_snapshot_states` EXISTS predicate
  (`queryArchiveNoticeNumsByIsDoneFilter`) so semantic results obey the same status filter.

### 4.4 Failure/degrade policy (inherits session 14 rules)

| Situation | Behavior |
| --------- | -------- |
| Flag off | Board = today's keyword path (no semantic fields). |
| `searchMode=auto` + engine ready | Semantic clear tier, keyword-appended cache items. |
| `searchMode=auto` + engine unavailable (first-window failure) | `mode='keyword_fallback'`; serve keyword results + `semantic.fallbackReason`; UI banner. |
| `searchMode=semantic` + engine unavailable | Same fallback (do **not** hard-error the board) — a search page must not go blank because the sidecar is down. Surface the reason. |
| Empty clear tier | Return `results: []` + `weakResults`; **do not** substitute keyword hits (session 14 invariant). Board shows empty/weak states. |
| First-window 4xx | Existing service surfaces `BadRequestException`; the board should treat it like a query error (length cap already enforced by `assertSearchLength`). |

### 4.5 Config / flags

- Reuse `SEMANTIC_SEARCH_ENABLED` (backend) and `PUBLIC_SEMANTIC_SEARCH_ENABLED` (frontend).
- Add `SEMANTIC_SEARCH_HYBRID_MAX_NOTICES` (default 100) and, if the default-on decision
  needs separating from the page flag, `SEMANTIC_SEARCH_BOARD_DEFAULT_MODE` (proposed
  `auto`) — both documented in `backend/.env.example`. Keep compiled defaults in
  `app.config.ts` (`semanticSearch` block) so the numbers stay in one owner.

---

## 5. Frontend Plan

### 5.1 Search mode control

- Add `searchMode` to the board's URL contract (`/notices?search=...&searchMode=semantic`).
  `buildQueryLink`, `handleFilterSubmit`, and `notices/+page.server.ts` all thread it.
- A **segmented control** next to the search box: `자동` / `키워드` / `의미`
  (only rendered when `SEMANTIC_SEARCH_ENABLED`). Default when absent = `auto` (flag on)
  / `keyword` (flag off). `data-testid="notices-search-mode"` per AGENTS.
- Keep the existing "의미 검색" entry link → the standalone page (backward compat). It
  becomes optional; do not remove it this pass.

### 5.2 Result cards

- Reuse the semantic page's presentation vocabulary for `relevance`: a similarity chip
  (`formatSimilarityPercent`), section chip (`body` → 본문), and `excerpt` under the title.
  Factor the semantic result card bits into a small shared component if that avoids
  duplication with `routes/notices/semantic-search/+page.svelte` (§8-D4).
- In `keyword` mode cards render exactly as today (no relevance row).

### 5.3 Empty / weak / fallback states

- **Fallback banner**: reuse the semantic page's `semantic-search-fallback-banner` copy when
  `semantic.mode === 'keyword_fallback'`.
- **Weak reveal**: when the clear tier is empty but `semantic.weakResults` is non-empty, show
  the same explicit reveal button (not automatic). Carry the `weakResults` in the archive
  response (§4.2) so the reveal needs no second request.
- **Empty state**: in `auto`, if semantic is empty and keyword has hits, keyword is already
  the fallback path — the empty state only shows when both are empty.

### 5.4 No new client-side fetch

The board stays SSR (loader-driven), matching the semantic page's SSR-is-source-of-truth
pattern and keeping `handleFetch`-only mocking (frontend notes: SSR calls bypass
`page.route`). New e2e stubs therefore belong in `handleFetch`/mock module, not `page.route`.

---

## 6. Phase Order

| Phase | Work | Risk | Gate |
| ----- | ---- | ---- | ---- |
| **0** | Decide §8 open items; freeze the contract in §4.2; add flags/config + `.env.example`; update `semantic-search.contract.spec.ts` skeleton | low | contract spec green |
| **1** | Backend: `getArchiveNoticesByRankedNums` + `NoticesHybridSearchService` + controller `searchMode`; unit tests (rank, filter, fallback, empty/weak, cache append) | med | backend lint/tsc/build/test green |
| **2** | Frontend: `searchMode` URL threading + segmented control + relevance card rendering + banner/weak/empty; types + `toNoticeCard` | med | `npm run check` green |
| **3** | E2E: mock semantic responses for the archive route in `handleFetch`; assert rank order, mode switch, fallback banner, weak reveal, pagination behavior | med | `test:e2e:semantic-search` + `notices.spec.ts` |
| **4** | Rollout: backend flag first, then frontend flag; verify degrade with the sidecar stopped | low | §7 verification matrix |
| **5** | Release per AGENTS §Deployment (individual submodule PRs, version bumps, semantic-search untouched unless contract changed) | — | release checklist |

---

## 7. Verification Plan

- **Keyword path unchanged**: run the existing `notices-query.service.spec.ts` /
  `notice-archive.service.spec.ts` / `api-*.spec.ts` suites with the flag off; the diff must
  be zero for `searchMode` absent.
- **Hybrid unit matrix** (new spec): rank preserved through hydration; date/isDone/proposer
  post-filter drops correctly and `total` matches survivors; candidate cap enforced;
  cache-only append deduped; `keyword_fallback` on injected first-window outage; empty
  clear tier returns no keyword hits + weak carried.
- **Contract**: `semantic-search.contract.spec.ts` still green (and extended if the sidecar
  wire changed — it should **not** this pass).
- **Frontend**: `npm run check`; `notices.spec.ts` for the keyword mode; semantic e2e config
  for mode switch + fallback + weak + rank chips.
- **Live degrade**: with the sidecar container stopped, `searchMode=auto` on a real query
  returns keyword results + the fallback banner; with it up, semantic scores appear and
  match the dedicated page's ranks for the same query (same engine, same index).
- **Bound behavior**: confirm the board hides pagination when `total ≤ limit` and that no
  ranked item beyond the candidate cap is silently presented as "all results" (show a
  "관련도순 상위 N건" note).
- **Flags**: `PUBLIC_SEMANTIC_SEARCH_ENABLED` off → segmented control and the entry link
  both disappear and the board is byte-identical to today's SSR output.

---

## 8. Open Decisions (need owner sign-off)

- **D1 — Default mode. DECIDED (2026-10-13, owner sign-off): `auto`.** `auto`
  (semantic-first) when the page flag is on, `keyword` otherwise — i.e. the implemented
  behavior; no soft-launch release with a `keyword` default. Accepted with the measured
  narrowing (`임대차`: semantic 95 vs keyword 170 notices), mitigated in-UI by the scope
  note, the on-demand keyword count and the keyword-mode link. The alternatives
  (`keyword` soft launch for one release, or holding the flag off) were rejected. Do NOT
  "fix" the default back to `keyword` without a new owner decision.
- **D2 — Sort in semantic mode.** Hide the sort control with a note, vs add a
  "관련도순" option. Recommended: add the option (explicit, testable) and default the select
  to it when a query is present in semantic mode.
- **D3 — Lifecycle in semantic mode.** Keep `source_deleted`/`renumbered` with their
  existing preservation chips (recommended, consistency) vs exclude them from the semantic
  candidate set. Requires an archive-side filter in either case if chosen.
- **D4 — Shared card component.** Extract a shared relevance-row/weak-reveal component from
  the semantic page, vs duplicate the small markup on the board. Recommended: extract only
  if the duplication exceeds ~30 lines.
- **D5 — Candidate cap value.** `SEMANTIC_SEARCH_HYBRID_MAX_NOTICES` default 100 (≈ up to
  200 chunks, within `SIDE_CAR_MAX_CHUNK_K`) vs a smaller value. Higher cap = better recall
  under restrictive filters, more hydration cost per search.
- **D6 — Exhaustive search affordance.** Make it explicit in the UI that semantic mode is a
  bounded relevance view and keyword mode is exhaustive (e.g. "전체 결과는 키워드 검색" hint).

---

## 9. Implementation Status

### Phase 1 (backend) — IMPLEMENTED (2026-10-12)

Backend-only change, additive and backward compatible. `searchMode` absent or any
non-`semantic`/`auto` value keeps the existing keyword path byte-for-byte.

| File | Change |
| ---- | ------ |
| `backend/src/config/app.config.ts` | `semanticSearch.hybridMaxNotices` (env `SEMANTIC_SEARCH_HYBRID_MAX_NOTICES`, default 100) |
| `backend/.env.example` | documents the new env var |
| `backend/src/modules/notice/notice-archive.service.ts` | new `getArchiveNoticesByRankedNums({noticeNums, proposer, startDate, endDate, isDone, fullText})` — fetch by `IN (...)`, reuse `applyArchiveSearchFilters` + the snapshot-state `isDone` EXISTS predicate, preserve semantic rank, return all matching items + total |
| `backend/src/modules/crawling/notices-query.service.ts` | new public `getCacheOnlySearchMatches({search, proposer})` (reuses the private cache helpers); `parseDateRange` made public |
| `backend/src/modules/semantic-search/notices-hybrid-search.service.ts` | **new** `NoticesHybridSearchService` — keyword passthrough / semantic hydration / fallback / weak-tier passthrough / cache-only append / relevance-ordered pagination |
| `backend/src/modules/semantic-search/semantic-search.module.ts` | imports `NoticeModule` + `ChangeTrackingModule`; provides/exports the hybrid service |
| `backend/src/controllers/api.controller.ts` | `getArchivedNotices` accepts `searchMode`; `parseSearchMode` (lenient; only `semantic`/`auto` switch paths); scoped `noticeNums` (digest) always keyword |

**Response contract** (additive, keyword path unchanged): archive response gains
`searchMode` (echoed), `appliedMode` (`keyword`/`semantic`), optional `semantic
{mode, fallbackReason, lastUpdateAt, candidateTotal, weakResults}`, and per-item
`relevance {score, section, excerpt, weak}` (semantic mode only). `stats` is kept so
the board's archive count still renders.

**Decisions taken (D1-safe soft launch):** the backend default is **keyword** when
`searchMode` is absent regardless of the flag, so existing clients/URLs are unchanged;
the frontend (Phase 2) must send `searchMode=auto` explicitly to opt in.

**Failure policy (matches session 14):** engine unavailable → keyword results +
`semantic.mode='keyword_fallback'` (never a blank board, never a 500); empty clear
tier stays empty with `weakResults` carried for the reveal; a `BadRequestException`
(4xx contract violation) propagates.

**Verification (measured):** `npm run lint` clean; `npx tsc --noEmit` 0 errors;
`npm run build` ok; **`npm test` 927 passed / 70 suites** — includes the new
`notices-hybrid-search.service.spec.ts` (keyword passthrough, no-query, rank order +
relevance, post-filter drop, keyword_fallback, empty clear + weak, cache-only append +
dedup, cache skip on date/isDone, pagination, 4xx rethrow, unexpected-error fallback)
and the `api-isolation.spec.ts` routing tests (semantic → hybrid, absent/keyword →
keyword). `NoticeSearchService.searchNotices` and the sidecar wire contract are
untouched, so `semantic-search.contract.spec.ts` is unaffected.

**Not yet done (later phases):** e2e (Phase 3); rollout (Phase 4); no `AppModule`
bootstrap test exists, so the module graph is verified by compile + static DAG
analysis (acyclic: only `app.module.ts` imports `SemanticSearchModule`; all four hybrid
dependencies are exported by imported modules), not by booting the app.

### Phase 2 (frontend) — IMPLEMENTED (2026-10-13)

Flag-gated (`PUBLIC_SEMANTIC_SEARCH_ENABLED`): with the flag off the board renders
byte-for-byte as before and never writes `searchMode` to the URL.

| File | Change |
| ---- | ------ |
| `frontend/src/lib/types/api.ts` | `BoardSearchMode`, `BoardRelevance {score, section, excerpt, weak}`, `BoardSearchSemanticMeta {mode, fallbackReason, lastUpdateAt, candidateTotal, weakResults}`; `Notice.relevance?`, `NoticeCard.relevance?`; archive response gains `searchMode` / `appliedMode` / `semantic` |
| `frontend/src/lib/api/client.ts` | `getArchivedNotices` accepts `searchMode` and appends `?searchMode=` **only** for `auto`/`semantic` (an absent param keeps the backend keyword path) |
| `frontend/src/lib/utils/semantic-search.ts` | `BOARD_SEARCH_MODES`, `BOARD_SEARCH_MODE_LABELS` (자동/키워드/의미), `normalizeBoardSearchMode(raw, enabled)` (flag default: `auto` on, `keyword` off), `formatSectionLabel` (`body` → `본문`) |
| `frontend/src/lib/server/ssr-cards.ts` | `toNoticeCard` carries `relevance` (session 17 pitfall: the SSR payload strips unlisted fields) |
| `frontend/src/routes/notices/+page.server.ts` | normalizes `?searchMode=` server-side, sends the effective mode to the API (and to the mock), adds `searchMode`/`semantic: null` to the error fallback |
| `frontend/src/routes/notices/+page.svelte` | 검색 방식 segmented control (`notices-search-mode` / `-auto` / `-keyword` / `-semantic`), relevance chips (`notice-relevance-score\|section\|excerpt-<num>`) + excerpt line, sort slot switches to a non-interactive 관련도순 chip when `appliedMode === 'semantic'`, keyword-fallback banner (`notices-semantic-fallback-banner`), weak-tier reveal/hide (`notices-semantic-show-weak` / `-hide-weak` / `notices-semantic-weak-list`) |
| `frontend/src/lib/server/diffchain-ui-mock.ts` | mock archive honours `searchMode`; marker words `키워드`/`폴백` → keyword fallback, `약한` → empty clear tier + one weak hit, else relevance-ranked items |

**Decisions taken:**

- The mode link **always writes `searchMode` explicitly** while the flag is on. Deleting
the param would re-resolve to the flag default (`auto`), so "키워드" would silently snap
back — caught by clicking the control in a hydrated browser, not by SSR.
- The control echoes the **requested** mode and the sort slot keys off the **applied**
one, so `auto` serving semantic shows 실제 관련도순 while a fallback shows the sort select.
- The weak-tier reveal is pinned with `$state.raw` against the exact response payload
(session 14 pitfall), so a new search starts hidden without an `$effect`.
- The legacy `/notices/semantic-search` entry (`semantic-search-entry`) moved out of the
search action row (검색 / 필터 초기화 only) into a right-aligned footer row rendered
**after** the branch chain and **outside** `PaginationNav`. Nesting it in the nav would
hide it whenever `totalPages <= 1 || totalItems <= limit`, and the entry tests cover a
query with zero keyword hits (`?search=...` renders the empty state, pagination absent),
so the footer must not depend on pagination visibility.
- Failure policy mirrors Phase 1: fallback banner + keyword results, weak tier hidden
behind the reveal, never a blank board.

**Verification (measured):** `npm run check` 0 errors / 0 warnings; `npm run lint` clean;
`DIFFCHAIN_UI_MOCK=1 npm test:e2e` (notices, all 90) **89 passed / 1 skipped / 0 failed**;
`E2E_SEMANTIC_SEARCH=1 npm run test:e2e:semantic-search` (standalone page) **23 passed /
0 failed**, including the two `semantic-search-entry` tests that pin the entry's
visibility and href on `/notices`. Note `DIFFCHAIN_UI_MOCK` must be set on the **test
runner** too (the shared config only sets it on the web server), otherwise the 70
cross-dimension tests silently skip — and a bare `npx playwright test` reusing a stale
third-party dev server on 5173 can flip the conditional pagination test between skip and
pass. SSR HTML
probed for five scenarios (absent param → `auto`, `keyword`, `semantic`, fallback marker,
weak marker) — control current-mode, sort slot, chip counts, banner, reveal all match.
Hydrated browser run: 자동 → 키워드 → 의미 → 자동 each lands on the explicit `searchMode`
URL with the right chips and sort slot, weak reveal/hide round-trips, no console errors.

**Not yet done:** Phase 3 (e2e specs for the board control/chips/fallback) and Phase 4
(rollout). The mock's semantic branch is exercised only through SSR/e2e mock mode, not
against the real sidecar.

## 10. Risks & Pitfalls (carry into implementation)

- **`$state` proxy identity** (session 14 / frontend notes): if the board pins "which
  response was revealed" for the weak toggle, use `$state.raw` or the comparison never
  matches — only an e2e click test catches it.
- **URL reactivity** (frontend notes): `searchMode` must be read off a `$state(page.url)`
  snapshot, or the segmented control silently stops reflecting the URL after `goto`.
- **SSR payload** (session 17): `relevance` must be added to `toNoticeCard`, or it is
  stripped from the SSR payload while the template still references it (grep-based field
  audit misses helper-function access).
- **Do not weaken session 14 invariants**: no keyword substitution on an empty clear tier;
  keyword fallback only for disabled/unreachable engine.
- **Do not re-tune thresholds as a noise filter** (session 20 §10): the floor excludes
  nothing and any absolute cutoff fails to separate noise from valid vague queries.
- **Backend `parsePositiveInteger` is lenient**; if `searchMode` validation is added, keep
  the strict-parsing pattern scoped (like the semantic controller's `parseK`) and do not
  change the shared util.
- **Stale sidecar/image verification traps** (session 08 §5): rebuild the sidecar before
  contract probes; a host listener on `:8300` shadows container traffic.
- **Jest CLI**: use `--testPathPatterns` (plural) per backend notes.

---

## 11. Cross-References

- `agent_memories/06-semantic-search-side-project/plan.md` — engine design, chunking.
- `agent_memories/08-semantic-search-production-deploy/plan.md` — sidecar deploy + API contract.
- `agent_memories/14-relevance-tier-search/plan.md` — clear/weak tiers, the no-keyword-substitution invariant.
- `agent_memories/17-ssr-payload-minimization/ssr-minimal-payload-audit.md` — card-field trimming rules.
- `agent_memories/20-semantic-query-quality-eval/query-quality-evaluation.md` — measured semantic vs FTS quality, threshold findings, alias table, hybrid-rerank direction.
- `agent_memories/repo/frontend-notes.md` — `$state.raw`, URL reactivity, SSR/`handleFetch` mocking.
- `agent_memories/repo/backend-testing-notes.md` — mock-sync rules, Jest CLI.

---

## 12. Release-readiness verdict (2026-10-13)

Review of the whole WIP (this session + the out-of-session semantic-search Dockerfile
change) as a single three-target release. **Code quality: shippable. Release process: not
started** — every change in all three submodules is an uncommitted working-tree edit with
`ahead/behind = 0/0` vs `origin`, so the pipeline can ship nothing yet.

### Gates re-run on the final working tree (all green)

| Target | Result |
| ------ | ------ |
| backend | `lint` clean (no file rewritten) · `tsc --noEmit` 0 · `build` ok · **70 suites / 928 tests passed** |
| frontend | `lint` clean · `check` **0 errors / 0 warnings** · mock e2e **253 passed / 52 skipped / 0 failed** · semantic e2e (incl. `semantic-search-board.spec.ts`) **33 passed / 0 failed**, exit 0 |
| semantic-search | `ruff check` + `format --check` clean · **313 tests passed** · **capability release guard reproduced locally**: save served baseline → `01_preprocess_chunk.py` candidate from the current code → `capability deltas: none`, `release check: OK` (21,188 notices / 117,813 chunks) |

### Live integration evidence (real backend + live sidecar, not mocks)

Production-data copy (21,188 notices) with the running KURE-v1 engine (`maxK=200`):

- no `searchMode` → `auto` served semantically (`/notices?search=임대차` SSR: relevance
  chips + scope note + 95건, no fallback banner)
- `searchMode=keyword` → 170건, zero relevance chips (keyword path byte-level behavior kept)
- `searchMode=semantic` → 95건, `candidateTotal=95`, consistent pagination (32 pages)
- nonsense query `달빛조각사` → empty clear tier + weak reveal (no 100-row dump), no fallback
  banner — engine answered, so no keyword substitution (session 14 invariant held)
- Latency: warm **0.14-0.45s** (keyword 0.06s), but the **first call in a cold process took
  9.27s** — the first visitor after a restart pays it.

### Remaining release blockers / notes

1. Commit → branch → PR → tag for each submodule; root pointer is `-dirty` and nothing is staged.
2. Version bumps: backend HEAD **is** the `backend-v1.11.0` commit → `1.12.0` needed;
   semantic-search HEAD **is** `v2.5.0` → `2.5.1` needed; frontend is already `1.15.0`
   (last tag `v1.14.0`), no further bump.
3. Untracked files must be added explicitly: `notices-hybrid-search.service.ts` (+ spec),
   `frontend/e2e/semantic-search-board.spec.ts`.
4. Release order: backend → root pointer push → `deploy-backend` green → frontend merge
   (the frontend reads `searchMode`/`relevance`); semantic-search is order-free but its
   deploy runs the capability guard.
5. Doc gaps — RESOLVED (2026-10-13). Documented before release: `backend/README.md`
   (semantic env block + `### 시맨틱 검색 설정` + the two semantic endpoints in the API table
   + the semantic endpoint in the rate-limit table + `searchMode`/`noticeNums` and the
   response contract under 주요 쿼리 파라미터 + the stale "원문 포함 여부" filter bullet
   removed), `frontend/README.md` (search-mode section with the URL contract, the
   `PUBLIC_SEMANTIC_SEARCH_ENABLED` flag, the semantic endpoints, and the two
   `semantic-search*` spec rows + the 5202 config row; the spec count was corrected to 23),
   and `frontend/.env.example`. Note `backend/README.md` is **not** prettier-formatted
   (`npm run lint` is ESLint only), so its markdown tables must be hand-aligned — the two
   tables touched here were re-padded with a script. Four unrelated specs
   (`announcements`, `color-contrast`, `responsive`, `responsive-long-content`) remain
   absent from the frontend E2E table (pre-existing, unrelated to this release).
6. Out-of-session `semantic-search/Dockerfile` (tini ENTRYPOINT + `--no-access-log`, 5
   why-comments removed) is **included as-is** per owner decision. `--no-access-log` is valid
   on the pinned uvicorn 0.54.0 and compose has no entrypoint override (so the guard's
   `--entrypoint python` calls are unaffected), but the **image build itself was not
   verified locally** — no Docker daemon — so `apt-get install tini` is first exercised in CI.
7. Late change carried by this release (2026-10-13, owner decision): the example-query
   chips on `/notices` and `/notices/semantic-search` are **random per request again**.
   `pickExampleQueries()` had been made deterministic per KST day during the session-29
   audit; the owner reverted it because one fixed set for the whole day defeats the chips'
   purpose. Details, measured rationale and the "do not reintroduce day-determinism" note:
   session 29 §5.3. The board e2e now asserts three distinct chips drawn from the pool and
   never equality across loads (two independent 3-of-18 draws collide in 0.12% of runs).
