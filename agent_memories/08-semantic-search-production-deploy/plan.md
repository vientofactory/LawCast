# Semantic Search Production Deployment & Backend Integration Roadmap

Roadmap for taking `semantic-search/` (Python + FAISS sidecar) from a host-run
prototype to a production container wired into the LawCast stack. This file is
the single roadmap for later passes; update item statuses as they land.

## 1. Codebase Survey (2026-09-30)

| Aspect              | Finding                                                                                                                                                                                                                                                                                |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Engine entry points | `scripts/01..06_*.py` offline pipeline CLIs; `service/app.py` is the only online entry point                                                                                                                                                                                           |
| Public library API  | `lawcast_semantic/__init__.py` (PEP 562 lazy exports): `KoreanEmbedder`, `SemanticSearcher`                                                                                                                                                                                            |
| Model loading       | `KoreanEmbedder` loads `nlpai-lab/KURE-v1` via sentence-transformers on first use (~2.2GB, HF auto-download); `SemanticSearcher.load(embedder)` loads `artifacts/{chunks.jsonl, embeddings.npz, faiss.index, id_map.json}` and rejects mixed/stale artifact sets via fingerprint check |
| Online API          | FastAPI sidecar on port 8300: `GET /health` -> `{status: loading\|ready\|failed, model, indexedChunks, error}` (always HTTP 200), `GET /search?query=&k=` -> chunk ranking (503 while loading/failed, 400 blank query, 422 validation). No auth — internal network only                |
| Engine lifecycle    | Loaded once in a background daemon thread at startup; load failures stick until process restart                                                                                                                                                                                        |
| Config/env          | `lawcast_semantic/config.py` single owner: `LAWCAST_SEMANTIC_MODEL/DEVICE/BATCH`; artifact paths were hardcoded to `PROJECT_ROOT/artifacts` (no override)                                                                                                                              |
| OMP quirk           | `omp_env.use_single_threaded_omp()` (macOS libomp crash workaround) called by dual-engine entry points                                                                                                                                                                                 |
| Docker artifacts    | **None existed**: no `Dockerfile`, no `.dockerignore`, no compose service. Root `docker-compose.yml` had backend/frontend/redis/ollama only                                                                                                                                            |
| Backend integration | Already implemented: `backend/src/modules/semantic-search/` (controller `GET /api/notices/semantic-search`, axios client with keyword fallback, config `SEMANTIC_SEARCH_ENABLED/API_URL/TIMEOUT`) + specs                                                                              |
| Data source         | `datasource.py` reads `notice_archives.proposalReason` via SQLite `mode=ro`; backend runs SQLite in **WAL** mode (`sqlite-runtime-tuning.service.ts`)                                                                                                                                  |

## 2. API Contract (sidecar <-> backend, authoritative)

Sidecar `GET /search?query=..&k=..` (query 1..500 chars, k 1..200 default 5).
**k counts CHUNKS, not notices** (cap `MAX_K=200` in `service/app.py`):

```json
{
  "query": "...",
  "k": 5,
  "model": "nlpai-lab/KURE-v1",
  "results": [{ "chunkId": "...", "noticeNum": 2221504, "subject": "...", "committee": "...", "section": "body", "score": 0.76, "text": "..." }]
}
```

Backend `GET /api/notices/semantic-search?query=..&k=..` collapses chunks to
notice-level hits (`SemanticSidecarChunk` -> `SemanticSearchResultItem`) and
falls back to keyword search (`mode: keyword_fallback`) on any sidecar outage
(503/loading/failed/network) — only 4xx surfaces as a request error. Contract
types live in `backend/src/modules/semantic-search/semantic-search.types.ts`.

**k is a result count, not a cap** (API k 1..50 = notice count): the service
over-requests chunks (`k * 3`, doubling per pass up to the sidecar cap 200)
until chunk->notice dedup fills k; below-k survives only when the capped
chunk window itself holds fewer than k notices. Contract limits have one
owner per side — `backend/src/modules/semantic-search/semantic-search.constants.ts`
and `semantic-search/service/app.py` — and are pinned field-by-field (plus
cap equality) by `backend/src/modules/semantic-search/semantic-search.contract.spec.ts`,
which parses both declarations so cross-language drift fails the suite.

## 3. Work Items

### A. Done in this pass (docker + integration blockers)

1. **`semantic-search/Dockerfile`** (new) — python:3.13-slim, CPU-only torch
   wheel from the PyTorch CPU index (PyPI torch pulls multi-GB CUDA deps),
   pinned `requirements.lock`, non-root `semantic` user, tzdata + Asia/Seoul,
   `service.app:app` uvicorn on 8300. No HEALTHCHECK in the image — compose
   owns healthchecks (repo convention).
2. **`semantic-search/.dockerignore`** (new) — excludes `.venv/`, `artifacts/`
   (~785 MiB), `data/`, `tests/`, caches. Without it the build context balloons
   past 1.6GB and local artifacts can leak into layers.
3. **`requirements.lock`** (new) — pip-freeze of the test-verified venv (69
   green tests at capture time). Docker installs from the lock so image builds
   are reproducible; `requirements.txt` stays the human-edited source. Policy:
   after changing deps and re-running tests, regenerate the lock.
4. **`docker-compose.yml`** — new `semantic-search` service: build from
   `./semantic-search`, `127.0.0.1:8300` published for host debugging,
   artifacts bind mount `./semantic-search/artifacts:/app/artifacts` (rw so
   incremental updates can rewrite in place; host pipeline remains the single
   artifacts dir per README "아티팩트 교체 규칙"), named volume
   `lawcast_semantic_hf_cache:/cache` for `HF_HOME` (KURE-v1 weights download
   once), healthcheck failing only on `status: failed` (loading stays healthy),
   `restart: unless-stopped`, same network/TZ as siblings.
5. **Backend env fix (integration blocker)** — compose sets
   `SEMANTIC_SEARCH_API_URL=http://semantic-search:8300` on the backend
   service. `backend/.env` default `http://127.0.0.1:8300` is unreachable from
   inside the backend container (it points at the container itself), so
   in-container semantic search silently always fell back to keyword mode.
   Host-local dev keeps using `backend/.env`. No `depends_on` on purpose:
   graceful fallback is the contract (same pattern as ollama).
6. **`config.py` refactor** — `LAWCAST_SEMANTIC_ARTIFACTS_DIR` env override for
   the artifacts dir (was hardcoded to `PROJECT_ROOT/artifacts`), so container
   mounts / ops layout are decoupled from the code layout. Contract tested in
   `tests/test_config.py` (subprocess isolation, matching entrypoint test style).
7. Docs: root README service/port list, semantic-search README deploy section,
   memory index.

### B. Remaining (later passes, priority order)

> **Status refresh 2026-10-01**: items 2 and 3 are **implemented** (see the
> struck-through text below); item 4 exists as an unmerged feature branch.
> The authoritative remaining-work list with reasons and completion criteria
> now lives in `production-readiness-status.md` §5.

1. **Index bootstrap to production (decision needed)** — `artifacts/` is
   gitignored (~785 MiB) so the image ships code only. Options: (a) host-built
   artifacts (MPS pipeline) + rsync to `./semantic-search/artifacts` on the
   server [fits current bind-mount design], (b) bake artifacts into an image
   variant, (c) build inside the container (CPU: stage 2 took ~40 min on MPS,
   hours on CPU). Default to (a); document the runbook.
2. ~~**Stale index after incremental updates (HIGH)** — the sidecar loads
   artifacts once at startup; `scripts/06_incremental_update.py` rewrites the
   files but the running process keeps serving the old index until restart.
   Add hot reload (e.g. `POST /reload` reusing `EngineState`, or SIGHUP, or
   fingerprint polling) before relying on incremental updates in production.~~
   **DONE (2026-10-01)**: load-validate-swap (`EngineState.reload`,
   generation/`reloadError`/`lastUpdate*` `/health` fields), `POST /reload`
   (409 boundaries pinned by endpoint tests + observed live), fingerprint
   self-heal (§5.3) — implemented per `incremental-update-pipeline-design.md`
   §5/§7, contract-tested in `tests/test_update_runner.py`.
3. ~~**Incremental update scheduling in production** — needs the DB: mount
   `lawcast_db` volume into the sidecar (WAL: must be rw for `-shm` access
   even though `datasource.py` connects `mode=ro`) and schedule (host cron via
   `docker compose exec` or a backend cron hook). Blocked on item 2.~~
   **DONE (2026-10-01)**: `service/update_runner.py` (lifespan scheduler
   thread, 60-min ±10 % jitter, flock single-flight, §6 shrink guard, §6.1
   boot repair), compose wiring `lawcast_db:/data` + three §4.2 gates +
   `user: "1001:1001"` §3.2 uid alignment — in-container tick and volume-DB
   read live-verified; residual data issue (stale volume snapshot) and tick
   completion tracking in `production-readiness-status.md` §5.
4. **Frontend consumption** of `GET /api/notices/semantic-search` (result list
   UI, `mode: keyword_fallback` indicator). **Exists on branch
   `feat/semantic-search-ui`** (route `notices/semantic-search`, feature-flag
   `PUBLIC_SEMANTIC_SEARCH_ENABLED`, e2e spec) with uncommitted changes —
   commit/PR/flag decision pending (`production-readiness-status.md` §4/5.5).
5. **Full-corpus eval relabeling** — current holdout answers are labeled on the
   300-notice sample; full-corpus quality numbers need new labels (README
   documents the trap).
6. **Optional hardening** — `/health` readiness detail (model download progress),
   image provenance (pin base image digest), metrics/latency logging, torch
   wheel provenance if the PyTorch CPU index lags PyPI versions.

## 4. Verification Status (measured 2026-09-30; deployment-lifecycle matrix)

> **Retraction note**: an earlier draft of this section reported "ready in
> 1-8s" on first boot and "ready in ~1s" after restart. Those numbers were
> measured against the **wrong process** — a leftover host dev-sidecar on
> `127.0.0.1:8300` (see pitfalls) answered every host-side curl while the
> container engine was still downloading weights. All numbers below were
> re-measured with authoritative in-container probes and service-DNS probes
> (the backend's real path).

| Scenario (all executed)                                                    | Observed result                                                                                                                                                                                             |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Compose env precedence                                                     | `docker compose run --rm --no-deps --entrypoint printenv backend SEMANTIC_SEARCH_API_URL` -> `http://semantic-search:8300` (override wins); `SEMANTIC_SEARCH_ENABLED=true` still merged from `backend/.env` |
| Warm recreation (`down` + `up`, volume kept)                               | volume survives `down`; engine `loading` -> `ready` in **17s**; zero re-download (cache fingerprint identical); service-DNS queries baseline-identical (`0.5627/2213685`, `0.7666/2221504`)                 |
| Cold cache (`volume rm` + `up`)                                            | `/health` reports **`loading` for the full 400s download**, flips to `ready` only at cache completion (2,234,944KB) — **no premature ready**; first queries correct (1.08s/0.44s)                           |
| Cold download shape                                                        | xet chunked, stepwise (0 -> 65MB -> 196MB -> 262MB plateau -> 1.2GB -> 2.2GB); full model lands in `lawcast_semantic_hf_cache`                                                                              |
| Failure: bogus model (`LAWCAST_SEMANTIC_MODEL=does-not-exist-xyz`)         | `failed` in ~8s (`RepositoryNotFoundError`), `/search` -> 503                                                                                                                                               |
| Failure: missing artifacts (`LAWCAST_SEMANTIC_ARTIFACTS_DIR=/nonexistent`) | `failed` in ~16s (`FileNotFoundError: /nonexistent/chunks.jsonl`), `/search` -> 503                                                                                                                         |
| No self-retry on failure                                                   | status stays `failed` across a 35s watch (7/7 polls); documented "sticks until restart" behavior confirmed                                                                                                  |
| Recovery: `docker restart` with same bad env                               | still `failed` (restart alone cannot heal bad config) — correct                                                                                                                                             |
| Recovery: recreate with fixed env                                          | `ready` in ~16s                                                                                                                                                                                             |
| Healthcheck on failed engine                                               | exact compose healthcheck command exits 1; Docker verdict flips to `unhealthy` (engine failed t+9s -> unhealthy t+15s with 5s/2-retry probe timings; compose's 30s/3 takes ~60-90s)                         |
| Build/quality baseline                                                     | `docker compose build` ok (torch `2.14.0+cpu`, 0 nvidia pkgs, 1.94GB image); ruff clean; **72 py tests** green; backend `tsc --noEmit` 0 errors; 14 semantic-search specs pass                              |

### Backend -> sidecar end-to-end (exercised 2026-09-30, two levels)

**Level 1 — real module code over real HTTP**: the compiled
`SemanticSearchService` + `SemanticSearchController` (backend/dist, unmodified)
drove live requests to `http://semantic-search:8300` on the compose network
(only DI stubs: rate limiter, keyword-DB path). 26/26 checks: exact result
shape (`noticeNum/subject/committee/section/score/excerpt`), chunk->notice
dedup, k passthrough (k=1 -> 1 hit, k=50 -> 30 after dedup), controller 400s
(missing/blank query, 121 chars, k=0/-1/51/100/abc — exact messages), sidecar
4xx -> `BadRequestException` WITHOUT fallback, dead URL -> `keyword_fallback`
with exact `searchNotices` args and null-shaped items, **real 503 during
engine loading -> `keyword_fallback`** (caught live during a restart window),
recovery -> semantic again, 10 concurrent all-semantic.

**Level 2 — real HTTP through the full NestJS pipeline** (routing, validation
pipe, real Redis rate limit, controller, service, axios): `GET
/api/notices/semantic-search` returned `{success, data:{query, mode:'semantic',
…}}` with baseline-identical scores (0.5627/2213685); careless inputs returned
Nest error envelopes with exact messages (400s above); 12 concurrent requests
all `semantic`; sidecar stopped -> `keyword_fallback` served from the REAL
20k-notice DB (same 3 hits as `/api/notices/search?q=임대차` — faithful reuse);
sidecar restarted -> `semantic` again.

**Isolation recipe** (full app has no cron kill switch; bootstrap crawls):
run on a `--internal` docker network (no internet — crawl/webhook attempts
fail closed), disable `OLLAMA/FILE_MIRROR/WEB_PUSH/DISCORD_BRIDGE` via env,
point `DATABASE_PATH` at a scratch DB copy, and mark
`screenshot_capture_status='captured'` on all rows first — otherwise the
`fillMissingSnapshotArtifacts` backfill launches Chromium per NULL row (20k
rows) and boot never settles. Sidecar joined the isolated network with alias
`semantic-search` temporarily. All scaffolding removed after.

**Findings (no contract mismatches, no product defects)**:

- QUIRK [FIXED, see §4 bounded-fixes pass]: `k=3.9` was accepted as k=3
  (`parsePositiveInteger` uses lenient parseInt; shared util also used by
  `page` — tightened in the semantic endpoint scope only).
- QUIRK: success envelope is `{success, data}` but errors use the Nest default
  `{message, error, statusCode}` — consumers must handle both (app-wide style).
- DEAD END (inherent): keyword fallback returns empty for paraphrase queries
  ("세입자 보호" -> 0) — exactly the gap semantic search fills; `fallbackReason`
  labels it so the UI can explain (frontend still pending, item B4).
- UX [FIXED, see §4 bounded-fixes pass]: `results.length` could be < k after
  chunk->notice dedup (k=50 -> 30) — now the service fills k by
  over-requesting chunks.

### Bounded fixes pass (2026-09-30, playtest findings)

Three scope-limited fixes, no new features / no frontend / no app-wide error
envelope change / no index hot reload (still item B2):

1. **k-fill contract** — `SemanticSearchService.fetchNoticeHits` now
   over-requests sidecar chunks (`k * CHUNK_FETCH_INITIAL_FACTOR=3`, doubling
   per pass, clamp `SIDE_CAR_MAX_CHUNK_K=200`) and stops widening once the
   sidecar returns fewer chunks than requested (corpus exhausted) or the cap
   is hit. k is a result count: dedup fills k, then trims to k. Sidecar
   `MAX_K` raised 50 -> 200 (`service/app.py`) — one request must be able to
   carry the over-requested window.
   **Per-phase failure policy** (refined after the first fill version
   regressed): a failed widening request keeps the chunks collected so far
   and returns partial semantic results (mode `semantic`, count < k allowed)
   — the keyword fallback returns nothing for paraphrase queries, so
   discarding collected hits was strictly worse. Keyword fallback happens
   only when the first window fails or zero semantic hits were collected
   (`FALLBACK_REASON_NO_HITS`); first-window 4xx still surfaces
   `BadRequestException` (never masked by a fallback). Pinned in
   `semantic-search.service.spec.ts` (widening reject x3 shapes -> partial,
   first-window reject -> fallback, zero hits -> fallback).
2. **Contract-pinning test** — `semantic-search.contract.spec.ts` (backend
   Jest, runs in root CI which checks out submodules recursively): parses the
   Python Pydantic declarations and the TS interfaces and compares
   `SearchHit` <-> `SemanticSidecarChunk`, `SearchResponse` <->
   `SemanticSidecarSearchResponse` field-by-field (canonical type mapping;
   Python `int`/`float` -> `number` is the only lossy point), plus
   `MAX_K` == `SIDE_CAR_MAX_CHUNK_K`. Mutation-verified: renaming one Python
   field fails the suite with an exact field diff.
3. **Strict k parsing (semantic scope only)** — controller `parseK` accepts
   only `[0-9]+` within 1..50 (`3.9`, `5.0`, `1e2`, `+5` now 400);
   `query-parsing.utils.parsePositiveInteger` is untouched — `page` etc. keep
   the lenient behavior.

**Verification (measured)**: python 72 tests green + ruff clean; backend
tsc/eslint clean, 846 tests green (24 semantic specs); live sidecar via
service DNS from a container: `k=150 -> 150 chunks/150 notices`,
`k=200 -> 200/199`, `k=201 -> 422`, response/result keys exactly the pinned
contract; compiled `SemanticSearchService` (fresh dist) over service DNS:
k=1/5/30/50 x 3 queries all `count == k` (`세입자 보호` k=50 -> 50, was 30
before the fix), 210-350ms per query. Failure-policy live proof (compiled
service, service DNS, real sidecar first window + injected widening outage):
partial `semantic` results kept (14 of k=50, 0 keyword-fallback calls, 2
sidecar calls); injected first-window outage -> `keyword_fallback` with the
`UNAVAILABLE` reason (1 keyword call); un-injected fill unchanged (k=5 -> 5,
k=50 -> 50). 851 backend tests / 72 python tests green.

## 5. Pitfalls

- **Never** copy `artifacts/` into the image: stale index would be baked in and
  the bind mount would shadow it anyway.
- torch on PyPI for linux is CUDA-heavy; the Dockerfile must keep installing
  torch from `https://download.pytorch.org/whl/cpu` (or equivalent) first.
- `SEMANTIC_SEARCH_API_URL` in `backend/.env` is for host-local dev only;
  container traffic goes through the compose `environment` override.
- Docker healthcheck treats `loading` as healthy (first boot downloads ~2.2GB
  weights in the background); only `failed` is unhealthy.
- On Linux hosts the artifacts bind mount is written as container uid (the
  `semantic` system user); host files owned by another uid block in-place
  incremental updates. macOS/OrbStack mounts are permission-transparent.
  **FIXED (2026-10-02)**: production runs everything as root, so the tick
  (uid 1001) died on its first write — creating `artifacts/.update.lock` —
  with `update tick failed: PermissionError: [Errno 13] Permission denied:
  '/app/artifacts/.update.lock'`. **`deploy.sh` owns the invariant**: before
  `docker compose up` it chowns `/cache` **and** `/app/artifacts` to
  `1001:1001` (root, idempotent, `</dev/null`-guarded), so the workflow and
  manual deploys both align the mounts before the container boots.
- **Stale-image verification trap**: `docker compose up -d --no-build` after
  a source change re-serves the old image — the raised `MAX_K` was first
  probed as still-50 against the previous build. Rebuild
  (`docker compose build semantic-search`) before contract probes.
- **Host-listener port shadowing (verification trap)**: if a dev sidecar already
  listens on `127.0.0.1:8300` on the host (e.g. `.venv/bin/python -m uvicorn
service.app:app`), OrbStack silently routes host-port traffic to THAT process
  instead of the container — host-side curl then measures the wrong engine and
  invalidates verification (it invalidated the first draft of section 4).
  Always probe the container engine via `docker compose exec ... 127.0.0.1:8300`
  or via service DNS (`http://semantic-search:8300` from a container on
  `lawcast_lawcast-network`); backend traffic uses service DNS and is not
  affected. Kill stale dev sidecars before host-port testing.
