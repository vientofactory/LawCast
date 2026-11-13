# Local ONNX Offline Optimization Verification

## Decision

Keep the current serving configuration. Serializing the graph optimized by the
current ONNX Runtime session does not add Attention fusion and does not establish
an overall startup, inference, or memory improvement on this local host.
Production was neither contacted nor changed. No service source, live environment,
model, index, precision, threshold, cache, or deployment setting was modified.

The root evidence branch is `codex/onnx-offline-runtime-verification`; the sidecar
remains on its existing clean `main`. No commit, push, release, or deployment was
performed. Existing unrelated root changes were retained.

## Frozen inputs and method

- macOS 26.6.2 arm64, ONNX Runtime 1.31.0, CPUExecutionProvider.
- Two intra-op threads, one inter-op thread, intra-op spinning disabled.
- FP32 BGE-m3-ko revision `7074d66aa46562342193ca4feb3d89bf9dad71b4`.
- APFS copy-on-write copies of the original graph/weights and FAISS generation.
  This is a copy, not an in-place edit or a hard link to a writable original.
- Source graph: 433457 bytes and 1973 nodes. External weights: 2266886160 bytes.
- Optimized ONNX: 271066 bytes and 1096 nodes. External weights are byte-identical.
- Index fingerprint: `5b2a44662491c4627ab150cbee08d252d0379d4c25d75190a994b1753e2821fe`.
- Current arm: original ONNX, `ORT_ENABLE_ALL`. Candidate: serialized optimized
  ONNX, `ORT_DISABLE_ALL`, with the same remaining session options.
- Three sequential ABBA blocks, six fresh processes per arm. No profiler during
  measured runs. OS file caches were not flushed: this is fresh-process startup,
  not a cold-host/disk experiment. No cache eviction, swap manipulation, service
  interruption, or artificial memory-pressure generator was used.
- Twenty-four fixed holdout queries, 6–18 input tokens. Each process ran three
  serial rounds (72 samples) and two concurrency-four rounds (48 samples).
  Each arm therefore has 432 serial and 288 concurrent samples.
- Direct production `OnnxQueryEncoder.encode` calls bypass the vector LRU.
  The benchmark uses its pooling/normalization and the frozen real FlatIP index.
  It does not start HTTP/gRPC, schedulers, background warmup, or document updates.
- Startup is measured from the harness entry through imports, hashes, tokenizer,
  session, canonical three probe vectors, and FlatIP/id-map load. It is NOT full
  service readiness: chunk-store loading, networking and worker setup are absent.

## Runtime Attention fusion

Separate profiles use the actual `OnnxQueryEncoder` constructor. The current
profile enables tracing but does not request graph serialization. The candidate
profile adds only `ORT_DISABLE_ALL` to the existing constructor options.
Each profile records three canonical probes and four heldout queries.

Both profiles execute the same operator counts across seven forwards:

- `MatMul`: 1344 events, or 192 per forward.
- `Softmax`: 168 events, or 24 per forward.
- `BiasGelu`: 168 events, or 24 per forward.
- `LayerNormalization`: 343 events, or 49 per forward.
- `Attention` and `MultiHeadAttention`: zero events.
- Every recorded node executes on CPUExecutionProvider.

**Attention graph/operator fusion is absent in the observed runtime.** GELU/bias
fusion is present. Saving/reloading the current optimized graph preserves this
execution structure; graph serialization is not a Transformer-specific optimizer.
This does not prove a particular exporter pattern caused the missing fusion.
See `semantic-search/lawcast_semantic/query_onnx.py:72-89` for session construction
and `:92-118` for the exact forward/tail used here.

## Balanced measurements

Startup and memory figures below are medians of six fresh processes. Inference
percentiles pool samples within an arm, not independent production requests.

- Session construction: 620.96 to 576.16 ms, 7.22% lower, about 45 ms saved.
  Current process range: 597.13–642.37 ms; candidate: 532.34–663.03 ms.
- Encoder ready, including imports/hash/tokenizer/probes: 5286.41 to 5394.50 ms.
- Encoder plus FlatIP/id-map ready: 5501.45 to 5613.02 ms, 2.03% higher.
  Hashing is approximately 931 ms in both arms; tokenizer/import variation is
  substantially larger than the session-only saving.
- Serial encode p50: 25.53 to 25.41 ms, 0.48% lower.
- Serial encode pooled p95: 34.91 to 32.31 ms, 7.44% lower.
- Serial encode plus FlatIP top-100 p50: 34.17 to 34.22 ms.
- Serial encode plus FlatIP top-100 pooled p95: 48.45 to 43.33 ms.
- Concurrency-four encode p50: 63.89 to 64.14 ms, 0.40% higher.
- Concurrency-four encode pooled p95: 88.77 to 94.18 ms, 6.10% higher.
  Per-process p95 ranges are 65.19–118.22 and 63.40–173.17 ms. The median of
  per-process p95s instead falls from 78.17 to 71.13 ms. Preserve both summaries:
  the tail is sensitive to run variation; no consistent inference gain is proven.
- Post-workload RSS: 2145.60 to 2169.74 MiB, 1.13% higher.
- Process RSS high-water: 2203.38 to 2177.73 MiB, 1.16% lower.
- Post-workload macOS physical footprint: 2288.84 to 2280.96 MiB, 0.34% lower.
  Compressed pages were present, so RSS alone is not the full memory footprint.
  `task_info(MACH_TASK_BASIC_INFO/TASK_VM_INFO)` reads only the current process.

There is a small session-initialization reduction but no end-to-end startup or
material memory reduction. Near-identical inference medians and opposing pooled
p95 changes do not justify switching formats for request speed. These short-query
local results do not establish performance for long inputs, Linux deployment CPU,
production concurrency, idle paging, or document-update peak memory.

## ORT format outcome

The same FP32 model fails native `.ort` serialization in ORT 1.31.0:
`SaveToOrtFormat Failed to save ORT format model to file`; exit 1, zero-byte output.
The official `onnxruntime.tools.convert_onnx_models_to_ort` Fixed/all conversion
also reaches the same native failure after its dependencies are available.
There is no valid ORT candidate and therefore no ORT performance comparison value.
Do not report the empty file as a model or label conversion failure as slow inference.

The external FP32 weights alone exceed 2 GiB. Upstream v1.31.0
[SaveToOrtFormat](https://github.com/microsoft/onnxruntime/blob/v1.31.0/onnxruntime/core/session/inference_session.cc)
assigns the serialized buffer size to a signed `int` before writing it. This is
consistent with the observed large-model serialization boundary, not a debugger-
verified diagnosis of every instruction in the installed wheel. No runtime binary,
weight precision, vocabulary, or graph partition was changed to force a result.

The first official-tool attempt stopped at a missing `ml_dtypes` import. It is
retained separately and is NOT counted as native serialization evidence. Only
`ml_dtypes` was installed into the ignored experiment-local `tools` directory;
the existing isolated ONNX tool copy was reused. No service dependency was added.
The first pilot's `ps` RSS probe was denied by the sandbox; its failed result is
retained. The final harness uses current-process Mach counters. Both pilots are
excluded from the twelve predefined balanced runs, none of which was discarded.

## Verification and rollback

- All twelve measured processes pass pinned digest, signature and vector probes.
- Compared vectors are exactly identical across all twelve runs. Candidate/current
  comparisons preserve all 24 ordered top-100 row lists and scores in each of six
  candidate runs (144 paired query readbacks). This is replay parity, not an
  exhaustive relevance guarantee.
- Actual production constructor checks pass on original and optimized bundles.
- A separate disposable candidate bundle is restored to original graph/manifest/
  weights/tokenizer bytes, then the original constructor/probes, all 24 vectors
  and ordered top-100 checks pass again. The optimized candidate stays unchanged.
- Focused sidecar regression: 35 passed in 3.78s.
- Original service-source and original model/tokenizer hashes are checked again
  at completion. Original/local serving and production configuration remain intact.

Evidence is kept in ignored `_workspace/onnx-offline-20261113/`: `experiment.py`,
`run_all.py`, raw process results, NumPy vectors/ranks, separate runtime profiles,
`summary.json`, `DIFF_FILE.json`, `VERIFICATION.txt`, and executable `ROLLBACK.sh`.
The derivative deliverable is `optimized-onnx/model.onnx`, accompanied by external
weights, tokenizer and a derivative validation manifest. `verify.sh` exposes
BASELINE, MODIFIED and ROLLBACK checks without touching an active service.

Follow-up experiments should distinguish a hardware-matched serialization cache
from Transformer-specific Attention fusion/re-export. Neither a graph-format
switch nor the present result addresses the production memory/idle findings in
[the earlier diagnosis](../83-idle-search-latency/diagnosis.md).
