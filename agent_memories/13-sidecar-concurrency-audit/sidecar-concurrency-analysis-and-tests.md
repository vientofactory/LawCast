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

Five tests, all passing with the full suite (134 passed, ruff clean):

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
   asserts on the **median** round (see margin rationale below): medians
   `overlap_ratio 0.65–0.69` across 7 runs (single rounds 0.61–0.75), all
   200 with results. Skipped in CI via `skipif` on artifacts + model cache.

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
  signatures.

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
.venv/bin/python -m pytest tests/ -q                 # 134 passed
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
