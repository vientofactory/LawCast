# HTTP Sidecar Concurrency Analysis and Test Suite (semantic-search)

H1: HTTP sidecar concurrency audit — structure analysis, blocking-point
review, and the `tests/test_concurrency.py` suite that proves concurrent
requests do not block each other.

## Sidecar Structure (code-based)

| Piece | Location | Role |
| --- | --- | --- |
| Entry point | `semantic-search/service/app.py` | FastAPI app, routes `/health`, `/search`, `POST /reload` |
| Server | Dockerfile `CMD python -m uvicorn service.app:app` (port 8300) | production entrypoint |
| Engine state | `EngineState` in `service/app.py` | single-writer lock (`threading.Lock`), snapshot pattern |
| Engine load | `load_engine()` spawned from `lifespan` in a daemon thread | never blocks request handling; `/search` answers 503 while `loading` |
| Update ticks | `service/update_runner.py` scheduler thread + non-blocking `flock` on `artifacts/.update.lock` | skipped (not queued) when another holder owns the lock |
| Search core | `SemanticSearcher.search()` → `embedder.embed_query` (torch) → `VectorIndex.search` (FAISS) | runs OUTSIDE `EngineState._lock` |

### Request flow and blocking review

1. **Sync handlers → anyio threadpool (40 threads)**: FastAPI `def` handlers
   run via `run_in_threadpool`; concurrent requests get separate worker
   threads. No lock is held across I/O.
2. **`EngineState._lock` is snapshot-only**: `snapshot()` copies fields under
   the lock in microseconds; `searcher.search()` executes after release.
   Verified by test: `/health` answers in **0.6–1.8 ms** while a 1.5 s search
   is in flight.
3. **Load path**: model + artifacts load in a background thread; concurrent
   `/search` during load returns 503 in **~10 ms** (no queueing), then serves
   200 after `mark_ready` without restart.
4. **Generation swap**: `mark_ready`/`reload` swap the searcher reference
   under the same short lock; 16 concurrent searches overlapping a live swap
   loop all returned 200 (19–22 swaps observed per run — the count is
   nondeterministic, so the test asserts `>= 2` plus the generation
   invariant, not an exact number).
5. **Scheduler/tick**: `_update_lock` is `LOCK_NB` — a held tick lock yields
   `skipped`, never a blocked request thread.
6. **No module-global mutable state in the request path** beyond `STATE`
   (lock-guarded). uvicorn access log disabled in tests to avoid I/O coupling.

## Test Suite: `semantic-search/tests/test_concurrency.py`

Five tests, all passing with the full suite (269 passed, ruff clean):

1. **`test_concurrent_searches_overlap_and_all_succeed`** — 8 simultaneous
   `/search` against a 0.4 s stub searcher: `wall=0.42s` vs `serial_budget=3.20s`,
   `max_in_flight=8`, all 200 with results.
2. **`test_health_responds_fast_while_slow_search_runs`** — 1.5 s search in
   flight; 5× `/health` at 0.6–1.8 ms, search completes 200.
3. **`test_loading_engine_fails_fast_under_concurrent_load`** — loader held
   on an event; 6× `/search` all 503 in ~10 ms; after release, same server
   serves 200.
4. **`test_searches_keep_succeeding_across_generation_swaps`** — background
   loop swaps generations every 10 ms during 16 requests: all 200,
   `generation == 1 + swaps`.
5. **`test_real_engine_serves_concurrent_queries`** — spawns
   `python -m uvicorn service.app:app` (exact Dockerfile CMD) as a
   subprocess, waits for `ready`, warms up, then measures THREE rounds of
   (sequential baseline, 6 concurrent queries) on the same warm process and
   asserts queue signatures per round (see margin rationale below, and the
   device-shift subsection that replaced the fraction-of-sum gates): cpu
   medians `overlap_ratio 0.62–0.69`, mps 0.86–0.92, all 200 with results.
   Skipped in CI via `skipif` on artifacts + model cache.

### Measurement pitfalls found (control probes, since deleted)

**CRITICAL — client-side SSL setup contaminates latency measurements.**
Building `httpx.Client` inside the timed window costs ~30 ms alone but
**~0.42 s under N-way GIL contention** (CA-bundle parsing is Python work on
the same GIL as the server when uvicorn runs in-process). Session control
probes (git-ignored `_workspace/uv_control_probe*.py`, removed after the
audit) isolated it:

- probe v2: server-side handler entry spread ≤1 ms, exit at +0.405 s → server was never blocked;
- probe v3/v4: `barrier→sent` gap ≈0.44 s regardless of handler sleep → client-side;
- probe v5: pre-creating clients drops `barrier→done` to 0.06 s (= the 0.05 s sleep).

Fix used in `fire_concurrently`: build all `httpx.Client`s in the calling
thread BEFORE the barrier/window.

**HIGH — undrained subprocess `stdout=PIPE` deadlocks the server** once
~64 KB of loader output accumulates. `real_sidecar_process` drains through a
daemon reader thread into a bounded chunk list.

**MEDIUM — cold-start inflates baselines (and silently deflates
`overlap_ratio`).** First real query costs 2.56–2.83 s (model warm-up) vs
0.11 s steady state, and the baseline stays **uniformly** elevated for
several queries after it (measured 0.17 s/query vs 0.12 s steady with
`first_vs_median=1.01` — not a first-query outlier; whole-batch elevation),
which inflates `sequential_sum` while the later concurrent batch runs warm →
ratio drops toward 0.56 and the overlap claim is overstated. One warm-up
query was not enough; the harness now warms with 3 queries before the first
measured round, and 3 rounds judged on their median absorb any residual
cold round.

**HIGH — HuggingFace Hub revalidation makes engine load network-dependent
(root cause of the 124 s outlier).** Phase timing in the real-engine test
showed `engine_load` (not readiness polling, batch, or teardown) absorbing
the delay: 10–12 s online, **143.63 s when huggingface.co is unreachable**
(hub HEAD revalidation retries with backoff during `SentenceTransformer`
construction) vs 3–4 s with `HF_HUB_OFFLINE=1`. The fixture now sets
`HF_HUB_OFFLINE=1` in the subprocess env — the `skipif` gate already
requires the model in `HF_HUB_CACHE`, so no network access is needed, and
all measured phases are then network-free. The `[real phases]` /
`[real sidecar teardown]` prints keep any future slow run attributable.

### Overlap-ratio variance: attribution and margin rationale

Single-shot `overlap_ratio` (concurrent wall / sequential sum) drifted
**0.56–0.79** against the 0.85 threshold. Per-phase instrumentation
(`[real phases]`, per-query singles, `client_delta`, per-batch wall)
split the variance into its roots:

| Root | Evidence | Direction |
| --- | --- | --- |
| **(a) baseline pollution** (cold run) | singles uniformly 0.17 s vs 0.12 s steady (`first_vs_median=1.01`, `ratio_raw ≈ ratio_steady` — first-query outlier ≤1.30× median was NOT the driver) while the batch wall stayed normal 0.54 s | denominator inflated → ratio too **low** (0.56): dishonest overlap claim |
| **(b) concurrent batch wall variance** (warm runs) | batch wall 0.60–0.70 s vs 0.50 s steady with a normal baseline | wall inflated → ratio too **high** (0.74–0.79): flaky against 0.85 |
| client-side overhead | `client_delta = baseline_wall − sequential_sum = 0.000 s` every round | ruled out |

Both tails were single-shot artifacts, so the test was recalibrated
(measured 2026-10-04, 7 process runs / 21 rounds):

- **3 measurement rounds judged on the median** (per-round baseline AND
  batch, same warm process) — median spreads 0.04 (0.65–0.69) vs 0.23
  (0.56–0.79) single-shot; either tail drops out while a serialized
  sidecar would pin **every** round near 1.0, which a median cannot hide.
- **3-query warm-up** before round 1 (one query left the baseline elevated).
- **Threshold kept at 0.85, rationale documented in the test**: ≥0.10
  headroom over the worst single round (0.75), ≥0.16 over every median
  (max 0.69), and serialization lands at ~1.0 — strictly between the two
  signatures. **Superseded 2026-10-10**: that margin only held on the
  CPU-only stack; see the device-shift subsection below for the
  ladder-based replacement.

### Device shift retired the 0.85 gate: latency-ladder signature (2026-10-10)

**CRITICAL — the wall/sum margin is device calibration, not a queue
detector.** After `LAWCAST_SEMANTIC_DEVICE=auto` (the default) started
resolving to `mps` on this Apple Silicon host, the real-engine test failed
**consistently** (`median_ratio 0.88–0.91 > 0.85`). A/B with identical code
and artifacts (96646 chunks):

| Device | single | sequential_sum | batch wall | wall/sum | inflation | latency shape |
| --- | --- | --- | --- | --- | --- | --- |
| `auto` → mps | 0.08 s | 0.47–0.49 s | 0.41–0.44 s | **0.86–0.92** | 4.8–5.5x | uniform, min/max 0.61–0.98 |
| `cpu` pin | 0.13–0.14 s | 0.82–0.84 s | 0.55–0.56 s | 0.62–0.68 | 3.7–3.8x | uniform, min/max 0.89–1.0 |
| lock prediction | — | = wall | ≈ sum | ≈ 1.00 | — | ladder min/max ≈ 1/N = 0.17 |

**Environment scope**: macOS 26.6.2 (Darwin arm64) / Apple M4 / torch 2.14.0, `mps` backend
vs the identical build pinned to `cpu`; faiss-cpu 1.15.1 for the index. CUDA/XPU, other
OSes (Linux/Windows) and the Docker runtime were NOT part of this A/B. On any other chip,
torch build or machine load the absolute latencies and the 0.61–1.0 ladder range **will
shift** — what generalizes is the mechanism (simultaneous starts → uniform latencies vs a
lock → 1/N ladder), not the figures.

**Root cause: no queueing at all.** Every latency equals the batch wall
(all requests start together behind the barrier), so requests genuinely
overlap; MPS only narrows the margin because GIL + the single MPS command
queue inflate each in-flight encode ~5x while the single-query baseline
got 1.7x faster, shrinking the denominator. The 0.85 threshold
(calibrated 2026-09/10-04 on a CPU-only stack) cannot separate that
contention signature from a lock. No request-path lock was added — the
only `service/app.py` change that period was the `/health` `device` field
(snapshot-only lock usage).

**Fix (device-independent), refined 2026-10-11 after flake evidence:** the
test gates on the **first finisher's speed** — `min(latencies) >= 2.0 ×
median(single)` on every round. A lock releases requests one by one, so
the first finishes at its uncontended single-query speed (~1x baseline);
with genuine overlap nobody finishes fast (measured 3.0–5.5x across cpu
and mps, idle and busy — threshold 2.0 keeps ≥1.5x headroom). The earlier
pair (`min >= 0.5 × max` ladder spread + `median_ratio < 1.0`) was
replaced because BOTH proved load-sensitive on a busy host: honest
wall/sum reached **1.02** (a serialized sidecar also lands ~1.0 → no
separating margin for a sub-second wall clock) and ladder spread
compressed to 0.57–0.61 under a head-start finisher while the batch was
genuinely overlapping. Ratio and ladder now remain print-only diagnostics
(`[real margin]`), and both fraction-of-sum gates (0.85) are likewise gone
— a wall-clock fraction would need re-calibrating per device (cuda next).
Verified: 8/8 isolated real-engine runs, then full suite green.

### GIL vs lock separation (real engine)

The batch inflates per-request latency **3.4–4.1×** (mean concurrent /
mean single) while `max(latency)/sequential_sum` stays **0.65–0.69** — a
lock held across `search()` would queue every request and pin that ratio
(and `wall/sum`) at **~1.0** regardless of machine speed (last request
waits for all others). Overlapped-but-slowed = CPU/GIL contention, printed
by `[real gil-vs-lock]` with the lock prediction alongside; lock absence
itself is proven directly by the stub tests (`max_in_flight=8`, /health
at 0.6–1.8 ms during a 1.5 s search). Mean inflation alone does NOT
separate the two (a serialized queue's mean latency is also ≈(N+1)/2 ×
single) — the separating observables are `max/sum` and `wall/sum`.

## Verification Commands

```bash
cd semantic-search
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python -m pytest tests/ -q                 # 269 passed
.venv/bin/python -m pytest tests/test_concurrency.py -v -s   # timing prints

# Degraded-network repro (proves HF_HUB_OFFLINE=1 keeps load network-free).
# NO_PROXY MUST exempt localhost when HTTP_PROXY is set: pytest's own httpx
# clients honor proxy env (trust_env default), and without NO_PROXY the
# /health polling routes 127.0.0.1 through the dead proxy → "engine did not
# become ready within 180s" FALSE failure (wasted 2 × 180 s runs):
HTTPS_PROXY=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 \
NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
.venv/bin/python -m pytest tests/test_concurrency.py -q -k real   # engine_load ~4-5s, passed

# CI-skip path (no artifacts → real test skips):
LAWCAST_SEMANTIC_ARTIFACTS_DIR=$(mktemp -d) .venv/bin/python -m pytest tests/test_concurrency.py -q   # 4 passed, 1 skipped
```

## Verdict

No blocking section found in the sidecar request path: lock scope is
microsecond snapshots, heavy work (model load, FAISS search, artifact swap)
all happens outside the state lock or on dedicated threads; concurrency tests
prove overlap (wall ≈ single-request time under an 8-client batch) both with
the stub engine and the real KURE-v1 + FAISS engine behind the production
uvicorn CMD.

## FP32 MPS blocking and admission follow-up (2026-11-09)

- Real Chrome trace IDs showed distinct waits on the request worker. For the
  1,044 ms request, `psynch_cvwait` spanned 346.7 ms inside
  `MTLCommandBuffer.waitUntilCompleted` on the MPS copy path and 265.8 ms in
  `MPSEvent::synchronize`. In the 679 ms request, encode overlapped 156.9 ms of
  file-backed page-ins and 98.9 ms of swap decompression. FAISS in both requests
  included decompression and swap faults. These trace intervals can overlap and
  must not be added as independent costs. Runnable time was under 4 ms per
  request; the evidence is blocking, not sustained lack of CPU scheduling.
- The HTTP MPS admission gate now waits on the event loop before borrowing an
  AnyIO worker and releases the slot after embedding, before FAISS. The native
  embedder's semaphore still protects direct synchronous callers. The setting
  remains opt-in; the response contract and FP32 precision are unchanged.
- Replaced latency-ratio concurrency assertions with explicit rendezvous and
  worker-count checks. The real HTTP engine test compares both result tiers
  against serial results rather than inferring a lock from the first finisher.
- Local HTTP A/B (same 122,381 chunks, slot limit 1, two reversed-order sessions):
  search p95 at concurrency 1/4/48 was 42.36/140.77/1443.88 ms before versus
  39.66/129.97/1699.36 ms after. Health worst-case at concurrency 48 fell from
  264.58 to 54.56 ms, but its p95 rose from 4.75 to 8.46 ms. Both result tiers
  matched in all 288 pairs. This is worker isolation, not a fix for memory
  pressure or Metal's blocking, and not a throughput win under saturation.

## Separate embedding and ranking budgets under load (2026-11-09)

- The optional HTTP path uses separate AnyIO capacity limiters for embedding
  and FAISS/ranking/annotation, not permanently assigned OS threads. Each
  limiter admits work before it borrows a worker. Ranking does not hold an
  embedding token, and the default pool remains available for health requests.
  Each request holds one index generation across both stages, including refresh.
- Same BGE-m3-ko FP32 model and 122,381 indexed chunks, HTTP concurrency 48:
  CPU with 4 embedding and 2 ranking slots cut health p95 from 206.72 to
  6.64 ms and FAISS p95 from 87.46 to 19.31 ms. Search p50/p95 fell from
  1940.58/2507.48 to 1315.61/2434.46 ms, but median time to drain a wave rose
  from 2415.41 to 2484.02 ms. At concurrency 4, search p95 also rose from
  198.89 to 227.27 ms. This is a contention and responsiveness improvement
  under CPU saturation, not a throughput improvement. CPU was measured once.
- On MPS, with embedding capped at 1 in both arms, the extra handoff did not
  help in either run order. At concurrency 48, pooled search p95 rose from
  1390.07 to 1456.13 ms and health p95 from 3.34 to 3.97 ms. More CPU workers
  did not remove Metal completion waits. Keep the additional scheduling opt-in
  (`LAWCAST_SEMANTIC_QUERY_RANK_WORKERS=0` by default).
- The ordered chunk IDs in both result tiers matched in all 144 CPU and 288
  MPS request pairs. The HTTP test holds ranking workers with an event and
  verifies that embedding and health still make progress, the concurrency caps
  are honored, and a refresh cannot mix index generations.

## Production CPU OpenMP trial (2026-11-09)

- The v3.0.0 production container was pinned to CPU, with four schedulable
  CPUs from `os.sched_getaffinity(0)`, no CPU quota, and 121,067 indexed
  chunks. The initial `nproc` output was 2 with `OMP_NUM_THREADS=2`; do
  not infer process affinity from that output when the variable is set.
- On the same image, index generation, FP32 model, and four queries
  (`k=10`, 20 samples per concurrency and setting), lowering
  `OMP_NUM_THREADS` from 2 to 1 moved HTTP p95 from 531/1050/1223 ms to
  649/895/1119 ms at concurrency 1/2/4. At concurrency 4, model p95 was
  957 ms and FAISS p95 was 275 ms before tuning, versus 899 and 125 ms.
  This is a small live-host sample, not a capacity test.
- The trial required at least 10% improvement at concurrency 4 and no
  more than 15% p95 regression at concurrency 1 or 2. It failed both the
  concurrency-4 and serial criteria. The original environment bytes
  and CPU readiness were verified after reverting to 2. Keep the split
  worker budgets at their prior defaults unless a higher-concurrency
  experiment supports changing them.

## Production two-embedding/one-ranking trial (2026-11-09)

- On the same CPU FP32 v3.0.0 image with `OMP_NUM_THREADS=2` and index
  generation, measured the same four queries at concurrency 1/2/4
  (`k=10`, 20 measured requests per cell). Splitting into 2 embedding and
  1 ranking slots changed HTTP p95 from 1425/1906/2390 ms to
  1187/2551/4040 ms. Ordered result hashes for both relevance tiers matched.
- At concurrency 4, FAISS p95 fell from 589 to 297 ms and model p95 changed
  from 1918 to 1869 ms, but embedding elapsed time, which includes admission
  in the split path, rose from 1978 to 3796 ms. This is consistent with
  queueing at the embedding limit outweighing the FAISS improvement.
- The live baseline varied across attempts. The first split trial was aborted
  during warm-up by the five-second guard, and a restored cold search also
  took over five seconds. The completed comparison excludes warm-up.
  Restored the original environment bytes and effective settings, verified
  CPU readiness and a successful search, and left the worker split disabled.

## Production four-embedding/one-ranking trial (2026-11-09)

- With CPU FP32 and `OMP_NUM_THREADS=2`, a fresh live baseline and
  4-embedding/1-ranking trial used the same image and index generation,
  four queries, `k=10`, and 20 measured requests per concurrency cell.
  HTTP p95 changed from 479/624/1017 ms to 412/730/1373 ms at concurrency
  1/2/4. Ordered result hashes for both relevance tiers matched.
- All 120 response timings matched unique sidecar log duration triples.
  Split embedding admission p95 was 0.6/2.3/4.1 ms, while rank-worker wait
  was 0.3/73.7/199.4 ms. At concurrency 4, model p95 also rose from 747 to
  1057 ms. The default path logs admission as zero; this does not quantify
  waiting for the default AnyIO pool. Do not add marginal p95 values.
- Restored the original environment bytes before recreating only the sidecar;
  Compose reported it started. SSH disconnected before readiness could be
  verified and the follow-up SSH connection timed out. Final HTTP readiness
  was not observed during this run.
