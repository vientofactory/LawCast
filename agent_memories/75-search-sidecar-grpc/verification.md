# Search Sidecar gRPC Migration

## Contract and rollout

The backend selects one transport at startup. Compose selects gRPC on internal
port 8301; setting the root Compose variable `SEMANTIC_SEARCH_GRPC_TARGET` to
an empty string selects the original HTTP connection. Deploy the listener
before turning on the gRPC client. HTTP health, reload and search remain
available on port 8300; the frontend and public backend API do not change.

Both adapters call `search_with_admission` on the same engine generation.
The backend keeps its chunk cap negotiation, widening budget, partial-result
handling, timing fields and keyword degradation. Protobuf preserves the
distinction between an absent candidate count and zero. Out-of-range chunk
windows retain the one-time health refresh; invalid queries are not retried.
Deadline handling cancels queued work but lets active native workers finish
without releasing their limiter tokens early.

## Local measurement

Same warm CPU process, Node 24.22.1 and Python 3.13.5 on macOS arm64,
dragonkue/BGE-m3-ko and 122,624 FAISS chunks. Twelve Korean queries at k=5
and k=50, sequential and concurrency six. Four paired ABBA rounds per
condition (48 timed requests per transport per condition), plus 24
HTTP/gRPC result comparisons excluding timing metadata. Both rounds of the
experiment passed every parity check; no model or index rebuild was needed.

Final p95 round trip, HTTP to gRPC:

- k=5, concurrency 1: 91.45 to 96.66 ms.
- k=5, concurrency 6: 334.80 to 322.59 ms.
- k=50, concurrency 1: 120.01 to 118.97 ms.
- k=50, concurrency 6: 321.48 to 313.28 ms.

Median response body was 3,393 to 2,337 bytes (−31.1%) at k=5 and
27,390 to 21,543 bytes (−21.3%) at k=50, excluding transport framing and
headers. The transport did not deliver a stable latency improvement.
For example, k=5 concurrency six p95 increased from 334.25 to 374.63 ms
in the earlier run. In the final run, per-request p50 outside the measured
pipeline was 1.10–3.19 ms with HTTP and 1.13–5.01 ms with gRPC. This
residual also includes scheduling and serialization; it is not wire time.
The measured bottleneck is the search pipeline, not HTTP framing. Profile
embedding, FAISS and queueing independently before pursuing latency changes.

## Checks

Baseline and independent rollback both passed 85 focused backend and 24 HTTP
sidecar tests. Final workspace passed 1,328 Jest tests and 381 sidecar tests,
including real loopback gRPC, stale cap recovery, invalid-input handling,
deadline cancellation and a native-worker ownership regression. Backend
build, frontend check, Compose config, and agent guidelines passed. No
production traffic or data was changed.
