# gRPC Query Embedding Profile

## Finding and change

The local BGE-m3-ko CPU run used the same 12 Korean queries, 122,624-chunk
FAISS generation, k=5/50, and concurrency 1/6 as the transport comparison.
In the cache-off replay, the median per-request embedding share of the
sidecar pipeline was 89–92%; at k=50 and concurrency six the embedding,
FAISS retrieval and worker dispatch medians were 255.21, 21.44 and 0.30 ms.
The embedding model subphase alone had a 233.53 ms median in that cell.

Added a model-instance LRU of exact vectors keyed by the normalized,
alias-expanded query. Default capacity is 256; zero disables only caching.
The same query can reuse its vector at another window size or on the same
model after an index reload. FAISS always reads the active generation.
The vector is copied both on insertion and retrieval because FAISS input
normalization mutates its input. Invalid vectors are not cached. The lock
protects only LRU access and does not cover native model execution.

The existing timing log now measures first-worker wait through worker entry
instead of always logging zero for the CPU inline path. Split lanes report
rank-worker wait separately; neither wait is attributed to embedding.
gRPC and the protobuf contract are unchanged.

## Paired local measurements

Replay is explicitly warmed on the 12 measured queries, with separate
processes in cache-off/on/on/off order. There were 96 timed samples per
configuration per cell. HTTP was used only to detect process readiness.

- k=5, concurrency 1: gRPC p95 87.15 to 10.79 ms.
- k=5, concurrency 6: gRPC p95 310.34 to 34.75 ms.
- k=50, concurrency 1: gRPC p95 110.41 to 10.75 ms.
- k=50, concurrency 6: gRPC p95 312.95 to 29.39 ms.

Cold-query controls warmed only unrelated queries and measured the same 12
queries once per fresh process, for 24 samples per configuration at k=50
and concurrency six. p95 was 292.86 to 289.21 ms, with the model executing
for every request. No cold-latency improvement is established.

A separate forced widening test requested k=5 followed by k=50 on the same
initially unseen query, six concurrent query chains, 12 per configuration.
The second window's median embedding was 261.39 to 0.015 ms; the two-RPC
p95 was 642.86 to 303.15 ms. The second window made no model calls after
the change. This is a forced widening replay, not the rate at which
production requests widen.

All 432 response pairs (384 warmed, 24 cold, 24 widening-window responses)
matched exactly excluding timings. The replay is not a production cache
hit-rate estimate. Once embeddings are reused, FAISS is the largest
measured step for those hits.

## Validation

The sidecar passed 387 tests, backend search passed 90, and 41 pre-change
and rollback-copy tests passed on each original-source copy. Rollback
preserved the gRPC listener. No production deployment was performed.
