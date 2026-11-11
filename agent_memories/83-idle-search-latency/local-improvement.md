# Local Idle Search Improvement

## Scope and implementation

This follows [the production diagnosis](diagnosis.md). The user requested local
implementation and measurement only. No deployment, production request, host
setting, live environment file, or original model/index artifact was changed in this phase.
The root branch is `codex/idle-search-diagnosis`; the sidecar branch is
`codex/idle-search-memory`. Backend and frontend sources are unchanged.

### Reduce update-time allocation overlap

- `semantic-search/lawcast_semantic/incremental.py`: assemble the merged matrix into one
  preallocated float32 buffer instead of a list of row views plus `vstack`.
  Release the old matrix, its owning tuple, and the new-vector input before
  constructing the replacement index. A weak-reference regression verifies
  both inputs are actually released at that boundary.
- `semantic-search/lawcast_semantic/indexing.py`: normalize/add FlatIP vectors in at most
  4096-row blocks. Preserve the full-training SQ8 path, row order, zero-vector
  behavior, caller input immutability, and artifact write order.
- No model, precision, ranking, threshold, vector cache, or wire-format change.

### Bound idle upkeep and improve diagnosis

- `LAWCAST_SEMANTIC_QUERY_WARMUP_SECONDS` defaults to 10; zero disables it.
  Only an already-loaded CPU ONNX session executes inference. The method
  bypasses the vector LRU and never loads document/fallback PyTorch weights.
- A single lifespan-owned task touches ONNX and the selected generation's
  FAISS index after native-inference inactivity. Cached requests do not refresh
  this clock; otherwise a trickle of cache hits could starve upkeep forever. It skips active requests,
  unready/failed engines, updates already in progress, and detected Linux
  memory pressure. New requests are not blocked by a state lock during upkeep;
  this is best-effort background work, not strict priority scheduling.
- Linux pressure guard: skip at memory PSI `some avg10 >= 1.0` or at
  cgroup-v2 `memory.current >= 90% memory.max`. Non-Linux/missing controls
  are tolerated. Upkeep failure does not retire ONNX or change readiness.
- Lifespan shutdown signals the task and joins an executing native pass.
- Search logs include embedding/model/FAISS subphase milliseconds and a
  separate process-wide major/minor fault delta correlated by trace ID.
  Process deltas can include concurrent work; they are not thread-local spans.

## Memory measurements

Fresh local macOS arm64 processes, CPU, the same 122,700-chunk BGE generation.
The served FAISS index remains allocated while a disposable copy is rebuilt.
Peak values are process `ru_maxrss`, not host memory or Docker cgroup peaks.

- Vector merge/FAISS rewrite without a new document-model load:
  2679.86 to 1757.17 MiB peak, **34.43% lower**. Runtime 18.71 to 18.47 s.
- Real update including a ready ONNX query model and a newly embedded document
  with the pinned PyTorch model: 3804.66 to 3261.23 MiB peak,
  **14.28% lower**. Runtime 22.59 to 22.99 s. This measures `apply_update`
  with one new document, not a full HTTP load-swap cycle or a multi-document
  worst case; do not present 34% as the full-service saving.
- Both comparisons produce byte-identical FAISS files, identical embedding
  matrix SHA-256 values, and identical content fingerprints across arms.
  Temporary ZIP/metadata timestamps are not used for vector parity.

## Idle experiment design

The initial exploratory baseline overlapped regression-test processes and
returned 302.37 ms and 9223.53 ms after separate 180-second gaps. Retain it as
loaded-host evidence, not as a quiet-host controlled performance comparison.

The controlled run uses a pinned four-file artifact copy, two-thread FP32 ONNX,
k=20, concurrency one, a real loopback gRPC listener and **vector caching off**.
Five unrelated seed requests establish readiness. The first measured query
text after each gap was not used in those seeds. Repeat requests also execute
the model because caching remains off. Neither health polling nor user search
traffic is sent during the timed gaps; candidate background upkeep is the
intended treatment. Heavy tests and memory benchmarks finish before candidate
timing begins. No memory-pressure generator or cache flush is used.

Quiet baseline after 180 seconds: first unseen request 399.32 ms,
embedding 278.43 ms; immediate repeat 42.49 ms, other query 35.39 ms.
The first trial used a 30-second upkeep interval: its 180-second first request
took 154.52 ms versus 35.27 ms for the repeat. This reduced the absolute delay
but failed the desired first/repeat ratio, so the final default was tightened
to 10 seconds. The 30-second trial was stopped; its completed measurements
remain in `idle-warmup30.json`. The final candidate measures both 180-second
and 600-second gaps with the 10-second interval. Completed
measurements and exact commands are recorded in the evidence verification file.

## Final controlled measurements

The final source uses the native-inference activity clock, not the timestamp
of the last cached request. The model ran on every timed foreground query.

- 180 seconds without user requests: first unseen query **100.03 ms**,
  immediate repeat **35.66 ms**, other query **36.50 ms**. Model stages were
  59.00 and 25.51 ms for first/repeat. The quiet baseline's first query was
  399.32 ms on the same input and generation.
- 600 seconds without user requests: first unseen query **70.76 ms**,
  immediate repeat **33.83 ms**, other query **36.78 ms**. Model stages were
  36.93 and 23.99 ms for first/repeat. There is no 600-second baseline arm;
  do not invent a percentage improvement for that cell.
- Background upkeep completed 75 native ONNX/FAISS passes during the final
  run. Both first requests met the predeclared absolute 200 ms budget.
- A stricter first/repeat ratio below 2x was **not met**: ratios are 2.80x
  and 2.09x. There is still a roughly 37–64 ms first-request penalty. The
  local run shows no seconds-scale stall in these two windows; it does not
  establish warmed-latency equivalence, p95, or a universal latency bound.
- With caching re-enabled at 256, 34 repeated cache-hit requests over
  35 seconds still allowed 3 native background passes; the subsequent
  unseen query took 61.10 ms. The old request-activity clock would
  suppress these passes. This tests cache-hit starvation independently of the
  cache-off idle experiment.
- Final full active-checkout suite: **414 passed**. Baseline and independent
  restored-copy suites: **387 passed, 3 skipped** each; copy-relative corpus
  fixtures explain those skips. Ruff check/format, guideline checker, source
  package and patch application checks pass.

## Evidence and rollback

All source snapshots, benchmark inputs, JSON timings, logs, original SHA-256
manifest, copy-only executable rollback and final verification are under
`_workspace/idle-search-improvement-20261111/` (ignored). `MODIFIED_FILE` is the
reopened source snapshot; the packaged deliverable is `MODIFIED_FILE.tar.gz`.

Large disposable rebuild outputs were removed after their parity hashes were
reopened and checked; their result manifests and the pinned input set remain.

The rollback accepts only a disposable child directory in the evidence folder,
restores all 94 original source hashes, and removes the two newly added modules.
It explicitly rejects the active checkout and original/modified snapshots.
Original startup behavior has no idle-warmup configuration or background task.

Local measurements do not guarantee production Linux swap behavior or remove
the need for RAM headroom. The production 8 GiB host and hourly update pressure
still require a postdeployment idle cache-miss observation before declaring
the production symptom resolved.
