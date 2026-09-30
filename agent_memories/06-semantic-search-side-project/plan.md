# Semantic Search Side Project (semantic-search/)

## Overview

Independent side project at repo root (`semantic-search/`, Python 3.13 + FAISS) that prototypes
a semantic search layer over LawCast legislation data. LawCast's existing search is FTS5
keyword matching only (`notice_archives_fts`), so queries like "세입자 보호" miss documents
that say "임차인". This project does not modify `backend/` or `frontend/`.

## Pipeline (4 independently runnable stages)

1. **Preprocess + chunk** (`lawcast_semantic/preprocess.py`, `chunking.py`): NFC normalize,
   strip HTML/zero-width chars, preserve `\n` (proposalReason line breaks are structure),
   section detection (`제안이유`, `제안이유 및 주요내용`, `주요내용`, ...), sentence-boundary
   packing to <=200 chars with ~50-char tail overlap.
2. **Tokenize + embed** (`embedding.py`): `KoreanEmbedder` wraps
   `SentenceTransformer('jhgan/ko-sbert-sts')`, reports token counts vs max_seq_length.
3. **FAISS indexing** (`indexing.py`): `IndexFlatIP` over L2-normalized vectors (= cosine),
   persisted with `id_map.json` row -> chunk_id mapping.
4. **Query + similarity** (`search.py`): same normalization/embedding for queries, top-k
   ranked `SearchResult` with notice metadata.

Scripts in `semantic-search/scripts/` (01-04) chain artifacts: `chunks.jsonl` ->
`embeddings.npz` -> `faiss.index` + `id_map.json`. Tests: `semantic-search/tests/` (19, no
model download required; stub embedder for index/search).

## Model choice: jhgan/ko-sbert-sts (verified working)

- Korean Sentence-BERT fine-tuned on **KorSTS** (Korean semantic textual similarity) —
  matches the query-document similarity task exactly.
- Downloaded from HuggingFace and exercised in all stages; native sentence-transformers
  format (no custom code). 768-dim, ~420MB, CPU-friendly.
- Rejected: KoSimCSE (non-standard ST loading), upskyy/bge-m3-korean + dragonkue/bge-m3-ko
  (~2.2GB, overkill for prototype), KURE-v1 (strong but heavy; upgrade candidate).
- **CRITICAL constraint**: max_seq_length = 128 tokens. Korean legal prose tokenizes at
  ~1.8-1.9 chars/token, so `CHUNK_MAX_CHARS=200` is calibrated to avoid silent truncation.
  Stage 2 prints `truncated_count` as a guardrail (currently 0 / 68 chunks). If the model
  is swapped (env `LAWCAST_SEMANTIC_MODEL`), re-check this ratio.

## LawCast data notes (for future search work)

- Source of truth: `notice_archives` (SQLite). Embeddable text = `proposalReason`
  (제안이유/주요내용 with `가. 나. 다.` enumerated items separated by newlines).
- Sample data: `semantic-search/data/sample_notices.jsonl` (12 notices, stratified by
  proposalReason length, extracted read-only from `lawcast_prod.db` via
  `scripts/extract_sample_data.py`).
- Semantic demo result: query "임대차 계약에서 세입자 보호" ranks 상가건물 임대차보호법
  ("임차인") chunks first despite zero keyword overlap — the case FTS5 cannot solve.

## Learning data source (2026-09-30, mission step 1)

The corpus is learned strictly from DB `notice_archives.proposalReason` — no HTML text
extraction. Audit found no HTML-based source in the pipeline (the only HTML handling was
`normalize_text`'s tag-strip guard); the DB seams were formalized:

- **Data source loading**: new `semantic-search/lawcast_semantic/datasource.py` — read-only
  `load_notices_from_db` / `extract_sample` / JSONL snapshot IO. `source_html` is never read
  (proven by `tests/test_datasource.py`). `scripts/extract_sample_data.py` is now a thin CLI.
- **Preprocessing**: unchanged behavior; `preprocess.py` docstrings clarify the input is the
  stored `proposalReason` value and the HTML-tag regex is a residual-markup guard only.
- **Learning pipeline**: `scripts/01_preprocess_chunk.py` gained `--db` to chunk straight from
  `notice_archives.proposalReason` (full-corpus path: 20,895 notices -> 96,590 chunks);
  `--input` JSONL snapshot remains the default for reproducible eval runs.

## Structure refactor (2026-09-30, mission step 2)

Prototype -> library structure for the upcoming backend integration (steps 3-4). Behavior
preserved: 46 tests kept passing (47 total with one new boundary test), eval numbers identical
(holdout recall@1 0.667 / MRR 0.714), fingerprint validation untouched.

- **Config single owner**: root `config.py` deleted; `lawcast_semantic/config.py` owns settings
  + artifact path defaults (same `LAWCAST_SEMANTIC_*` env surface). The package no longer
  imports root-level modules — `from lawcast_semantic import SemanticSearcher` now works for
  any consumer without sys.path tricks beyond locating the package itself.
- **Lazy public API** (`lawcast_semantic/__init__.py`, PEP 562): same exports, but light
  modules (datasource/chunking/preprocess) import without loading torch/faiss/sentence-
  transformers. Locked by `test_package_imports_stay_light`.
- **Chunk JSONL format owner**: `chunking.py` (`load_chunks_jsonl`/`write_chunks_jsonl`)
  replaces 4 inline JSONL read/write sites (scripts 01/02, `SemanticSearcher.load`, tests).
- **Tests**: `tests/conftest.py` is the only sys.path bootstrap; per-file inserts removed.
- **CLI**: scripts are argparse + presentation only; redundant wiring
  (`device=config.DEVICE`, `batch_size=...`) dropped since library defaults come from config.
- Dependency direction is a DAG: `config` <- {datasource, preprocess, chunking, embedding,
  indexing} <- `search`; `evaluation` standalone. No cycles.

Step 3 integration notes: the backend (NestJS) cannot import Python directly — the clean path
is a small Python sidecar/service that imports `lawcast_semantic` (search stack is
`KoreanEmbedder` + `SemanticSearcher.load` + `.search()`), or pip packaging (`pyproject.toml`)
if installable distribution is wanted. Artifact paths are overridable per call but not yet
env-configurable — likely needed when the service deploys.

## Backend integration (2026-09-30, mission step 3)

**Integration decision: FastAPI sidecar over HTTP + NestJS thin proxy.** Rationale: mirrors the
backend's existing Ollama integration pattern (axios + config URL/timeout + graceful
degradation), keeps process supervision out of Node, and stays independently restartable /
curl-debuggable. Rejected: per-request Python spawn (model load ~1 min per call) and a
long-lived stdio worker (custom line protocol + crash supervision inside Node).

New endpoint: `GET /api/notices/semantic-search?query=&k=` (separate controller; existing
search/API untouched). Contract: `{query, mode: semantic|keyword_fallback, fallbackReason,
results: [{noticeNum, subject, committee, section, score, excerpt}]}` — notice-deduplicated
(best chunk per notice). Validation: query required/<=120 (`assertSearchLength` shared policy),
k 1..50 default 5; rate-limited with the existing 'expensive' bucket. Degradation: sidecar
5xx/unreachable/model-load-failure -> keyword fallback via `NoticeSearchService.searchNotices`
(read-only reuse); sidecar 4xx -> BadRequest; fallback failure -> 503.

Files: `semantic-search/service/app.py` (sidecar: /health + /search, background one-shot model
load, loading/ready/failed state, no request blocking), `semantic-search/tests/test_service.py`
(6 tests, stub loader), `backend/src/modules/semantic-search/` (module/controller/service/
types + 2 specs), `app.config.ts` semanticSearch section, `app.module.ts` registration,
`.env.example` SEMANTIC_SEARCH_* block.

Verified with real requests (2026-09-30): semantic mode returns ranked notices
("세입자 보호" -> 상가건물 임대차보호법 1위, score 0.586); validation 400s (missing/blank/overlong
query, k 0/51/abc/-3); model-load failure (bogus model) -> keyword_fallback with reason;
sidecar down -> same; existing `/api/notices/search` unchanged. Checks: backend lint/tsc/build
+ 836 jest tests (65 suites), semantic-search ruff + 53 pytest. Service runs on port 8300.

Remaining gaps for later: Docker Compose service for the sidecar, env-configurable artifact
paths, readiness gating before routing traffic (warmup falls back to keyword in the meantime).

## Frontend UI (2026-09-30, mission step 4)

Flag-gated semantic search UI in `frontend/` consuming the step-3 contract unchanged.

- **Flag**: `PUBLIC_SEMANTIC_SEARCH_ENABLED` (`$env/dynamic/public`; truthy values
  `1/true/yes/on` via `src/lib/utils/semantic-search.ts`). Off (default) = zero UI change:
  entry point not rendered, `/notices/semantic-search` server-redirects (303) to `/notices`.
- **Files**: `src/routes/notices/semantic-search/+page.svelte` (experience: loading/initial/
  empty/error/keyword_fallback states, `RateLimitOverlay` for 429) + `+page.server.ts` (flag
  gate), entry link on `src/routes/notices/+page.svelte` (flag-guarded block in the search
  form actions row), `semanticSearch()` in `src/lib/api/client.ts`, contract types in
  `src/lib/types/api.ts`.
- **States**: `mode=keyword_fallback` renders a warning banner with `fallbackReason` and
  score/section chips omitted; `body` section label displays as `본문`.
- **E2E**: `e2e/semantic-search.spec.ts` (6 tests) + `playwright-configs/playwright.semantic-search.config.ts`
  (port 5202, `reuseExistingServer: false`, boots with the flag on) + `npm run test:e2e:semantic-search`.
  Skip-gated on `E2E_SEMANTIC_SEARCH` like the CF-challenge suite. API mocked via
  `page.route` for deterministic results/empty/fallback/error states.
- **Gotcha**: the search form is client-side (SvelteKit lazy route chunks hydrate after
  `load`), so e2e clicks can beat hydration and fall back to a native GET submit; the spec's
  `search()` helper retries until the API request is observed.
- Verified live (real stack: vite + NestJS + sidecar + KURE-v1): flag ON entry visible,
  semantic results ("세입자 보호" -> 상가건물 임대차보호법, 유사도 0.586), sidecar-down fallback
  banner + keyword results, blank-query error, flag OFF entry hidden + route redirect.
  Checks: `npm run lint` / `npm run check` / `npm run build` clean, e2e semantic 6/6,
  default suite 132 passed (0 failed, semantic skipped).

## Full-corpus index (2026-09-30, mission step 5)

`artifacts/` replaced with a full-DB index; sample-era artifacts backed up at
`artifacts/backup-sample-300/` (local only, `artifacts/` is gitignored). Replacement rule
documented in `semantic-search/README.md` ("아티팩트 교체 규칙"): pipeline rebuilds stages 1->3
as one set; `chunks_fingerprint` + `model_name` in `embeddings.npz` make `SemanticSearcher.load`
reject mixed sets, so partial replacement is impossible by design.

- Corpus: 20,919 notices (DB grew ~24 vs the earlier 20,895 count) -> 96,754 chunks (mean 129
  chars), tokens mean 86.6 / max 172, 0 truncated vs the 8,192-token window.
- Timing: stage 1 3.9s (peak RSS ~158MB), stage 2 39.6 min on MPS (peak RSS ~1.9GB), stage 3
  seconds. Device pick benchmarked via `scripts/benchmark_device.py`: cpu 21.0 vs mps 38.6
  chunks/s (96-chunk batch), so MPS was used (`LAWCAST_SEMANTIC_DEVICE=mps`). Artifacts total
  ~785 MiB (chunks 54 / embeddings 352 / faiss 378 / id_map 2).
- **CRITICAL - duplicate libomp crash (macOS)**: torch and faiss each bundle their own
  `libomp.dylib`; loading both in one process segfaults at search time (non-deterministic
  failure point). The workaround and its measured evidence (which alternatives failed and why)
  are owned by `lawcast_semantic/omp_env.py`; `scripts/04_search.py`, `scripts/05_evaluate.py`
  and `service/app.py` call `use_single_threaded_omp()` before loading the engines. This did
  NOT happen in earlier sessions on the same stack - treat the environment as changed.
- Verification: `04_search.py` real queries over 96,754 chunks; sidecar restarted -> `/health`
  `{status: ready, indexedChunks: 96754}`, `/search` returns distinct full-corpus notices,
  typo query still hits the right bill cluster, 400/422 validation intact; holdout eval runs
  cleanly; 53 pytest + ruff pass. Backend/frontend untouched.
- **Eval caveat**: eval answer keys are labeled against the 300-notice sample, so full-corpus
  metrics (holdout r@1 0.042 / r@5 0.292 / MRR 0.170; title-body r@5 0.812 / MRR 0.559) are
  pipeline-sanity numbers only - not comparable to sample-era numbers (0.667/0.833/0.714).
  Quality claims on the full corpus need newly labeled holdout answers first.

## Future integration ideas

- Hybrid search: FTS5 (BM25) + FAISS cosine reranking behind `/api/notices/search`.
- Incremental indexing driven by archive change events; include `aiSummary` in chunks.
- Model upgrade path: KURE-v1 / bge-m3-ko via `LAWCAST_SEMANTIC_MODEL` (larger chunks OK).
