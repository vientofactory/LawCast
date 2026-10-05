# Relevance-Tiered Semantic Search (Engine + Backend + Frontend)

Cross-stack change making search results relevance-aware: unrelated hits are dropped
entirely, clear hits render normally, and weak hits are hidden behind an explicit reveal
button in the empty-results UI.

## Design: two thresholds, three tiers

| Tier | Score band (cosine) | Contract surface |
| ---- | ------------------- | ---------------- |
| clear | `score >= CLEAR_SIMILARITY` (0.45) | sidecar `results` -> backend `results` -> rendered list |
| weak | `MIN_SIMILARITY` (0.25) <= `score <` clear | sidecar `weakResults` -> backend `weakResults` -> empty-state reveal button |
| unrelated | `score < MIN_SIMILARITY` | dropped inside the engine; appears nowhere |

- **Thresholds are owned by `semantic-search/lawcast_semantic/config.py`**
  (`LAWCAST_SEMANTIC_MIN_SIMILARITY` / `LAWCAST_SEMANTIC_CLEAR_SIMILARITY`, defaults
  0.25/0.45, import fails fast when MIN > CLEAR — the relation would silently invert
  the tiers). Documented in `.env.example`.
- **Engine**: `SemanticSearcher.search_tiered(query, k)` (`lawcast_semantic/search.py`)
  ranks via the existing raw `search()` and splits the SAME top-k window
  (`len(results) + len(weak_results) <= k`). Raw `search()` stays unfiltered for the
  CLI/evaluation/embedding-map, which need the unfiltered ranking (rank-order tests
  with synthetic scores would otherwise break on the floor).
- **Sidecar** (`service/app.py`): `/search` response gains `weakResults: list[SearchHit]`
  (`_hit()` maps one engine hit). **Dual-owned with backend
  `SemanticSidecarSearchResponse` — pinned field-by-field by
  `semantic-search.contract.spec.ts`; add the field to BOTH sides in one change.**
- **Backend** (`backend/src/modules/semantic-search/`): `collectChunks` accumulates both
  tiers (exhaustion counts them together — they cut the same window), widens on the
  CLEAR tier only, and `searchSemantic` returns
  `{results: clear.slice(0,k), weakResults: weak.slice(0,k)}`.
  `window.weakResults ?? []` tolerates an older sidecar (separate containers deploy
  independently; a TypeError there degrades to keyword fallback anyway).

## **CRITICAL: keyword fallback on zero hits is GONE**

`FALLBACK_REASON_NO_HITS` was removed. When the sidecar answers with an empty clear
tier, the backend returns `mode: 'semantic'` with `results: []` (plus any weak hits) —
it must NOT substitute keyword hits, or "unrelated query returns none" would be
violated by substring matches. Keyword fallback now means only:
feature disabled / sidecar unreachable or failing on the first window (4xx still
surfaces as a request error). Frontend mock (`semantic-search-mock.ts`) marker
`약한` produces the weak-only scenario; e2e in
`frontend/e2e/semantic-search.spec.ts::hides weak results behind a reveal button...`.

## Frontend

- `SemanticSearchResponse.weakResults` added in `frontend/src/lib/types/api.ts`.
- Page (`routes/notices/semantic-search/+page.svelte`): the reveal is pinned to the
  response payload identity (`revealedResponse === response`), so a new search resets
  it without an `$effect`. **`$state.raw` is mandatory there** — plain `$state` proxies
  the object and identity comparison never matches (see `repo/frontend-notes.md`).
  Empty state with `weakResults.length > 0` shows the `semantic-search-show-weak`
  button; revealed list renders behind a `semantic-search-weak-banner` + hide button.
  `displayedResults` drives the one shared result-list branch (no markup duplication).

## Findings

- **Pre-existing e2e breakage (not this change)**: the 3 tests in
  `frontend/e2e/semantic-search-loading.spec.ts` fail on
  `data-testid="wand-sparkle-sweep"`, which no longer exists in
  `lib/components/WandSparkleLoader.svelte` — the loader was simplified in frontend
  commit f4b2ee2 while the spec kept the old assertions. Verified absent at HEAD;
  unrelated files.
- Verification baseline after this change: semantic-search ruff + 142 pytest green;
  backend lint/tsc/build + 857 jest tests green (contract spec 3/3); frontend
  lint/check/build green; `npm run test:e2e:semantic-search` 19 passed with only the
  3 pre-existing loading failures above.
