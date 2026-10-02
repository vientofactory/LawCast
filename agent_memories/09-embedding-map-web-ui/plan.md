# Embedding Map Web UI (embedding-map/)

## Overview

Standalone web tool at repo root (`embedding-map/`) that visualizes the semantic-search
engine's learning data as a 2D embedding map and traces one real search query through the
engine's four stages: **query embedding → ANN candidate retrieval → scoring/ranking →
results**. Zero-build frontend (vanilla ES modules), FastAPI backend that reuses the sibling
`semantic-search/` package. Not wired into docker-compose/CI; run manually (see
`embedding-map/README.md`).

## Key design decisions

- **Real engine, not a mock**: the backend loads `KoreanEmbedder()` + `SemanticSearcher.load()`
  (validated artifacts: fingerprint + model gates). Trace results are byte-identical to the
  production sidecar `/search` for the same query (verified 2026-10-02).
- **Base map = seeded sample, search = full index** (important): the map draws `SAMPLE_SIZE=1000`
  random rows (seed 42) of the 93,031-chunk index, but ANN retrieval runs over the FULL index.
  Only ~0.5% of candidates fall inside the sample (measured 1/50 for the demo query), so every
  candidate is PCA-projected on the fly and drawn as an overlay marker — otherwise the trace
  would highlight almost nothing on the map. Labeled `DEMO DATA` in header + legend.
- **PCA basis fitted on the full corpus** (`Layout.fit` over `reconstruct_n` of the whole index`,
  ~1.4s, recomputed at every startup — deliberately NOT cached to keep the tool stateless).
  Out-of-sample projection gives query/candidate points the same basis as base points.
  Explained variance (~5.7%) is surfaced in the UI as an honesty metric.
- **Stages map to the mission spec, not to the engine's internal call structure**:
  stage 2 = `VectorIndex.search(q, k=50)` (ANN scores), stage 3 = explicit per-candidate
  `np.dot` re-scoring + `(-score, chunk_id)` ranking (same contract as
  `SemanticSearcher.search`), stage 4 = top-5 cut. `server/trace.py` owns the pure ranking rule.
- **App factory + injectable loader** (`create_app(state, loader=None)`) so tests never start the
  model-load thread; `server/engine.py` takes a `SemanticSearcher` — tests build one with a real
  FAISS index + `StubEmbedder` (no torch, suite runs in <1s).

## Data model / API contract

- `GET /api/status` → `{status: loading|ready|failed, error}` (UI polls; background loader thread).
- `GET /api/map` → `{model, dimension, corpusSize, sampleSize, seed, candidateK, resultK,
  explainedVariance, committees[8], points[{id,x,y,subject,committee,section,noticeNum,text}]}`.
- `POST /api/trace {query}` → `{query, normalized, model, embedding{tokenCount,maxSeqLength,
  truncated,dimension,norm,point}, corpusSize, candidateK,
  candidates[{id,row,retrievalRank,retrievalScore,rank,score,metadata,inSample,point}],
  results[ranked top-k]}`. Validation: blank → 400, missing/overlong (>200) → 422, engine
  loading/failed → 503.

## Verification (2026-10-02)

- `pytest tests/` 16 passed (layout, sample determinism, stage widths, cosine-score equality,
  chunk_id tie-break, parity with `SemanticSearcher.search`, API contracts); ruff check+format clean.
- Live: server on port **8310**, engine ready ~15s; trace of "임대차 계약에서 세입자 보호" ==
  fresh `SemanticSearcher.search` AND == production sidecar (8300) top-5 (0.6375 신탁법 …).
- Browser exercised end-to-end: load → badges/legend/stepper, search → stage 1-4 panels, map
  overlays (query marker, 50 amber rings + dimming, rank labels 1-10, result markers + trace
  lines), hover tooltip, zoom. Two UI bugs found & fixed in-session: (1) sidebar min-content
  overflow at narrow widths → `minmax(0,1fr)` + `.side > * { min-width: 0 }`;
  (2) stage-1 markers invisible (`renderOverlay` returned before `_apply`, leaving `r` unset)
  → `_apply(force)` on every overlay rebuild.

## Zoom flicker patch (2026-10-02, follow-up session)

User reported: **"임베딩 맵을 확대, 축소할 때 UI가 깜빡이는"** (UI flickers while zooming).
Investigation: frame-diff analysis of browser recordings + rAF timing + DOM-state sampling
found no dropped frames at idle, but three structural causes in the zoom path:

1. **CRITICAL — wheel handler was bound to the `svg` only.** The legend/zoom-tools overlay the
   panel *above* the svg, so a pinch (`ctrl+wheel`) or wheel over the legend fell through to the
   browser → **whole-page browser zoom jumped** (entire UI rescales = the visible "flicker").
   Fix: listener moved to the whole `#map-panel` (`this.container`) with `preventDefault`, so
   every wheel over the map panel zooms the map, never the page. Verified: `window.innerWidth`
   stays 1440 after `ctrl+wheel` over the legend.
2. **Per-frame full SVG re-raster.** `_apply` rewrote `r` on all 1000 circles + all markers every
   zoom frame (`k !== _lastK` always true while moving) and the transform was a presentation
   attribute → display-list rebuild + re-raster every frame (the classic SVG-zoom shimmer).
   Fix: viewport `<g>` now uses a **CSS transform** with `will-change: transform` (+
   `transform-box: view-box; transform-origin: 0 0` to keep attribute semantics) so zoom can be
   a compositor-only update; radii/strokes are rewritten only when the zoom level crosses a
   **~5% bucket** (`RADIUS_BUCKET = 1.05`, `Math.log` bucketing) instead of every frame.
3. **`vector-effect: non-scaling-stroke` removed** from markers/lines/halo — it forces stroke
   re-projection at paint time (defeats layerization). Stroke widths are now `stroke-width`
   attributes counter-scaled with the radii (`dataset.sw`), screen-constant within the same 5%
   bucket. Also: tooltip hides on zoom/stage change (it pointed at stale screen positions).

Verification: fit rendering pixel-identical to pre-patch screenshot; screen-constant sizes
(`r*k` = 4.2/7/9, `sw*k` = 1.6/1.2/1.5 at k=1095 and k=19524, drift <5%); deep zoom k=12081
renders markers/lines/labels correctly; hover tooltip, drag-pan, ±buttons, 전체 still work;
post-patch recording of a 40+40 wheel burst shows **continuous frame updates, zero freeze
windows**; idle-state rAF timing identical to pre-patch (avg 8.3ms / p95 8.8ms / 0 long
frames); `node --check` on map.js, ruff clean, 16/16 pytest pass.

## Zoom flicker, round 2 — layer revert + global pinch guard (2026-10-02)

User reported the flicker/breakage **still remained** after round 1. Deeper forensics
(970-frame native recording of a 20s pinch-like burst + per-region diffing):

- **Video-based flicker detection is contaminated**: VP8 keyframes (every ~101 frames, plus
  extra ones during high motion) shift static-region pixels by 1–16 mean-abs-gray — a "sidebar
  flash" in the numbers turned out to be pure compression noise. Always visually confirm
  suspected frames at native resolution before trusting region diffs.
- **Apparent blank map frames were legitimate**: at ~5.6× fit zoom anchored at panel center the
  candidate cluster flies off-screen and the ~9 remaining on-screen points are all dimmed to
  opacity 0.16 → panel looks empty (also invisible after video compression). DOM inspection
  (getBoundingClientRect per point) is the ground truth.

**Real fixes applied in round 2:**

1. **REVERTED the round-1 composited layer**: `.viewport` goes back to the `transform`
   presentation attribute, `will-change`/`transform-box` CSS removed. The infinite
   `query-halo` pulse animation lives inside that layer, so every animation step forced a
   full-layer re-raster racing the zoom — the compositor can present stale/blank layer
   content (blur/flash). Main-thread SVG paint is synchronous: a frame is never shown with
   missing content. Bucketed radius/stroke updates retained (strictly less work than the
   original code).
2. **Global pinch guard**: capture-phase `document` wheel listener cancels `ctrlKey` wheels
   everywhere (sidebar/topbar pinch used to trigger *browser* page-zoom → whole UI
   re-scales/reflows = "UI elements breaking"), plus `gesturestart/gesturechange`
   preventDefault for WebKit. Panel-level handler still map-zooms on pinch over the map;
   plain sidebar scrolling untouched.
3. **Labels snapped to integer px** (`Math.round` in `_apply`): fractional text coordinates
   re-raster with different antialiasing every zoom frame (text shimmer).

Verified: attribute transform set (style empty), sidebar plain-wheel NOT prevented / pinch
prevented, panel pinch prevented AND map zooms, screen-constant radii/strokes, all label
coords integers, mid-gesture screenshots sharp with full content, hover tooltip works, fit
k identical to original (1095.966…), stage-4 frame timing avg 9.4 / p95 16.7 ms, ruff clean,
16/16 pytest, `node --check` clean.

## Full-corpus mode — `run.py --full` (2026-10-02, follow-up session)

**Goal**: launch the map with a flag so it loads the search engine's FULL
artifacts and plots every index row (~93k) instead of the 1,000-point demo sample.

### How it works

- `LAWCAST_MAP_FULL=1` env var, read **once at import time** in
  `server/config.py` (`FULL_DATA`). `run.py --full` sets it BEFORE importing
  `server.config`; plain uvicorn works too if exported manually.
- `server/loader.py` passes `full=config.FULL_DATA` to `Engine`.
- `server/engine.py` `Engine(full=True)`: `rows = np.arange(corpus_size)`
  (every FAISS row) instead of the seeded sample; payload gains
  `mode: 'full'|'sample'` and `pointRadiusPx` (4.2px demo → shrinks by
  `sqrt(SAMPLE_SIZE/corpus)`, floored at 1.5px, so 93k points stay readable).
- **Body excerpts (`text`) are omitted from full-mode points** (would be tens
  of MB); the UI lazy-loads them per hover from **`GET /api/chunk/{id}`**
  (200 with metadata+excerpt, 404 otherwise), caching the promise per chunk in
  `map.js` (`_chunkTexts`) and re-rendering the tooltip when it resolves
  (placeholder `본문 불러오는 중…` meanwhile).
- `/api/map` returns a cached `json.dumps` string (`map_payload_json()`) through
  a `Response` + `GZipMiddleware(minimum_size=1024)` — 18.97MB raw → **1.57MB
  gzip**, re-served in ~15ms on cache hit.
- Base points moved from SVG circles to a **`<canvas>` layer** (`#points-canvas`,
  z-index under the SVG overlays): DPR-aware `_sizeCanvas()`, synchronous
  `_drawPoints()` with viewport culling, color-batched paths (≤8 fillStyle
  switches), `fillRect` instead of arcs when radius < 1.75px, dim pass at
  alpha 0.16 then bright pass. `ResizeObserver` re-sizes + redraws on resize.
- UI branches on `payload.mode`: green `FULL DATA` badge / `맵 전체 N점`,
  legend note without seed, and the "지도에 없는 후보" hint is sample-only
  (in full mode every candidate has a base point — verified `inSample=true`
  for all 50 candidates in a live trace).

### Verified live (2026-10-02)

- `run.py --full --port 8311` (daemon) ready in <20s incl. PCA over 93031×1024.
- `/api/map`: 93,031 points, `mode=full`, `pointRadiusPx=1.5`, raw 18.97MB /
  gzip 1.57MB / cached 0.015s. Trace 2.49s cold (first query warms the model),
  50 candidates, all `inSample=true`. `/api/chunk/{id}` 1.2ms, 404 path OK.
- Browser: all 4 stage overlays + canvas dimming + zoom (60-notch synthetic
  wheel burst: p50 12.5ms / p95 43.6ms frames, clamp at kFit×80 holds, fit()
  restores), lazy tooltip placeholder→body re-render, no console errors.
- Demo mode regression-checked on 8310: `mode=sample`, inline tooltip text,
  **zero** `/api/chunk` fetches on hover.
- Tests: 18 passed (`full_mode_plots_every_row_without_text`,
  `test_chunk_endpoint_returns_text_or_404`, 503-while-loading for `/api/chunk`).

### Gotchas discovered while verifying

- **`#map-svg { z-index: 1 }` (canvas stacking) silently broke the zoom
  buttons**: `.zoom-tools`/`.legend` are `position: absolute` with `z-index: auto`,
  so a positive-z-index SVG painted above them and swallowed their pointer
  events (buttons LOOKED fine, just never clicked; `document.elementFromPoint`
  at a button center returned the SVG). Fixed with `z-index: 2` on both.
  Rule: any panel control above the map needs an explicit z-index > 1 —
  verify with `elementFromPoint`, not by looking at the screenshot.
- CDP screenshots can capture a frame **before the queued rAF** (fit/zoom
  transitions) — the page can look blank/stale while the DOM transform state is
  already correct. Read the `.viewport` transform attribute to tell harness
  timing from a real bug.
- Synthetic `WheelEvent` bursts are far more aggressive than real input (one
  event per rAF at factor 1.21/frame) — use them as a stress test only.

## Environment gotchas

- **The terminal tool reaps background processes when a command returns** (nohup/`&` both die).
  Persistent servers must be double-forked + `os.setsid()` (see the daemon snippet pattern):
  that survives across tool calls. `uvicorn --app-dir embedding-map server.app:app` from repo root.
- Pre-existing processes on this machine: sidecar 8300, backend 3001, frontend dev 5173 —
  do not disturb. OMP: `server/__init__.py` applies `use_single_threaded_omp()` before any
  torch/faiss import (duplicate-libomp crash, see `lawcast_semantic/omp_env.py`).

## Remaining gaps / possible next steps

- No Playwright e2e for the tool (frontend tests only exercised manually in-browser).
- Tool is untracked by root CI/docker; no version/release story (root repo, not a submodule).
- PCA-2D of 1024-dim legal embeddings is a blobby cloud (5.7% variance) — a cluster overlay
  (k-means colors) or UMAP would show structure better, at the cost of out-of-sample projection.
