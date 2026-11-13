# Local Transformer Attention Fusion Evaluation

## Decision

The stock ONNX Runtime Transformer optimizer successfully introduces and executes
all 24 Attention operators without re-exporting or changing FP32 precision.
Nevertheless, the measured local CPU inference does not improve and concurrent
short-query tails worsen. Keep serving the original bundle/configuration.
Production was not contacted, restarted, configured, or deployed.

This follows [offline serialization](../87-onnx-offline-runtime/verification.md),
which did not add Attention fusion. The existing root feature branch is
`codex/onnx-offline-runtime-verification`; service repositories remain unchanged.
Only local ignored experiment artifacts and technical notes are added.

## Construction and exact settings

- Reuse the prior frozen BGE-m3-ko bundle at source revision
  `7074d66aa46562342193ca4feb3d89bf9dad71b4` and the same FlatIP generation.
- Create independent APFS copy-on-write baseline files, not writable hard links.
- Call ORT 1.31.0 `optimize_model` with `model_type='bert'`, `num_heads=16`,
  `hidden_size=1024`, `opt_level=1`, and `use_gpu=False`.
- The pinned config identifies XLMRobertaModel, 24 layers, 16 heads and hidden
  size 1024. BERT-family fusion patterns match this encoder's attention paths.
- Disable EmbedLayerNormalization fusion to avoid replacing the XLM-R position
  embedding path. Preserve raw two-dimensional attention masks, not mask-end
  shortcuts. No GELU approximation, FP16/INT8 conversion or vocabulary change.
- Package external data as `model.onnx_data` and preserve the original tokenizer,
  revision and offline PyTorch probe vectors. Only derivative file hashes change.
  The unmodified production OnnxQueryEncoder constructor accepts the candidate.
- Both baseline and candidate use CPUExecutionProvider, two intra-op threads,
  one inter-op thread, disabled intra-op spinning, and ORT_ENABLE_ALL.
- This is a bundle of Transformer fusions: Attention plus 48 SkipLayerNormalization
  and existing BiasGelu. No Attention-only ablation was run, so do not causally
  attribute every difference exclusively to Attention.

Reproduction scripts: `_workspace/attention-fusion-20261113/optimize.py` and
`package_bundle.py`. The optimizer refuses an existing output folder; use a new
candidate name for a repeated build. Existing isolated ONNX/ml_dtypes tools are
reused; service dependencies are not installed or modified.

## Actual runtime evidence

Independent seven-forward profiles use the real production encoder constructor.
Profiling is disabled in performance trials.

- Current: Attention 0, MatMul 1344, Softmax 168, BiasGelu 168.
- Candidate: Attention 168, MatMul 504, Softmax 0, BiasGelu 168,
  SkipLayerNormalization 336.
- Per forward this is Attention 0 to 24, MatMul 192 to 72 and standalone
  Softmax 24 to 0. All events execute on CPUExecutionProvider.
- Total recorded node events decrease from 7672 to 1323 over seven forwards,
  or 1096 to 189 per forward. This proves execution of fused Attention rather
  than merely inspecting an unused saved node.
- Offline canonical probe max absolute deltas versus pinned PyTorch references:
  baseline 3.27825546e-7, candidate 3.87430191e-7 (existing tolerance 3e-5).

No re-export was needed once this stock optimizer produced and executed fusion.

## Performance method

Local macOS 26.6.2 arm64, ONNX Runtime 1.31.0, CPU only. Three sequential ABBA
blocks give six fresh processes per arm. Every one of the twelve trials is kept.
The original current arm is remeasured, not copied from the prior experiment.
There is no profiler, vector LRU, listener, scheduler or background model warmup.
No cache flush, swap adjustment or artificial memory pressure is applied.

Thirty-two fixed inputs include 24 real holdout queries and eight synthetic
80/160/320/500-character legal-text controls. Token counts span 6–275. Each fresh
process runs three serial rounds and two concurrency-four rounds: each arm has
576 serial and 384 concurrent samples. The real FlatIP index remains loaded and
serial trials additionally time retrieval. Concurrent timing is encoding only.
The 24-query subgroup has 432 serial and 288 concurrent samples per arm.

OS file caches are warm; process startup is fresh. Readiness includes imports,
hashes, tokenizer, session, three probes and FlatIP/id-map loading, not the entire
network service or chunk store. There is one excluded preliminary baseline pilot;
all twelve balanced trials complete without retry or sample exclusion.

## Measured results

Inference percentiles pool the arm's samples; startup and memory are medians of
six processes. Lower latency is better.

- Real short queries, serial encode p50: 24.1085 to 24.7961 ms.
- Real short queries, serial encode p95: 29.9498 to 30.2318 ms.
- Real short queries, concurrency-four encode p50: 59.4804 to 65.6063 ms.
- Real short queries, concurrency-four encode p95: 76.0824 to 104.1616 ms.
- Extended inputs, serial encode p50: 82.9506 to 91.2722 ms.
- Extended inputs, serial encode p95: 182.9375 to 185.3832 ms.
- All 32 inputs, serial encode p50/p95: 24.8354/137.9289 to 25.4746/139.1636 ms.
- All 32 inputs, concurrency-four p50/p95: 60.9787/251.3767 to 70.7282/294.0625 ms.
- Serial encode plus real FlatIP retrieval p50/p95:
  33.1781/146.4162 to 33.8911/147.3990 ms.
- Post-workload RSS: 2306.42 to 2294.40 MiB, 0.52% lower.
- Process RSS high-water: 2437.55 to 2451.52 MiB, 0.57% higher.
- Post-workload macOS physical footprint: 2329.68 to 2311.75 MiB, 0.77% lower.
  Compressed pages occur, so RSS alone is not the full footprint.
- Session construction: 592.28 to 412.67 ms, about 30.3% lower.
- Harness readiness: 5054.92 to 4879.24 ms, about 3.5% lower, with overlapping
  process ranges. This small startup result does not offset slower inference.

**Fusion success is not an inference-speed win on this CPU/thread configuration.**
Memory changes are below one percent and mixed in direction. Results do not
establish performance on deployment Linux CPUs, other thread counts, production
traffic, idle paging or document-update memory peaks.

## Search and numerical parity

A separate real SemanticSearcher loads the frozen chunks, FlatIP and id map and
validates their common fingerprint:
`5b2a44662491c4627ab150cbee08d252d0379d4c25d75190a994b1753e2821fe`.
Its normal alias expansion, preprocessing, ranking and tiering run for 104 unique
queries from existing labeled/holdout/negative/clause fixtures plus aliases and
the eight length controls. Existing local policy is floor 0.25, clear 0.45,
calibrated relevance disabled. No score or cutoff is adjusted for parity.

All 104 queries preserve ordered raw top-100, top-20, clear and weak chunk lists,
and deduplicated clear/weak notice ordering. Maximum normalized query-vector
absolute difference is 2.88709998e-7. Matched cosine score difference is at most
2.98023224e-7. The twelve performance runs also retain the same ordered top-100.
**Values are numerically close, not bitwise identical.** This replay does not
prove parity for every unseen query or future threshold near-tie.

Five additional controls cover empty text, unequal-length right and left padded
batches (different masks verified), a 500-character input, and an interior masked
token. All normalized CLS differences remain below 2e-7. A long input's unpooled
hidden state has max absolute difference 2.05993652e-4 and relative L2 error
6.24123822e-6; it is NOT absolutely equal at 3e-5.

The first comparator incorrectly reused the normalized query-vector 3e-5 gate
for unnormalized hidden states and failed that long control. The original failed
log is preserved. The corrected report retains the failed raw-hidden flag and
all observed deltas, while testing the production normalized-CLS contract with
the unchanged 3e-5 tolerance. Do not describe full hidden tensors as identical.
A metadata key initially held the index timestamp; it was corrected to the
validated fingerprint with the timestamp retained separately. Query rows and
measurements were not changed by that metadata correction.

## Verification and rollback

The executable copy-only ROLLBACK.sh accepts only a marked immediate child of
its rollback-fixtures directory. An independent derivative bundle was restored
to all original graph/weight/tokenizer/manifest bytes, then the production
constructor, 104-query real search path and five shape/mask controls ran again.
Restored vectors, scores and all control tensors match baseline exactly; all
104 order/tier comparisons pass. The fused candidate remains unchanged.

Original service-source/model hashes are checked at completion. The four primary
artifacts and exact baseline/modified/rollback command outputs are in ignored
`_workspace/attention-fusion-20261113/VERIFICATION.txt`, with `DIFF_FILE.json`,
`ROLLBACK.sh`, and derivative `candidates/stock-o1/model.onnx` plus external data,
tokenizer and derivative validation manifest. No commit/push/deployment occurs.
