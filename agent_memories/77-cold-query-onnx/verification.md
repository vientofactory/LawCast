# Cold Query Inference with FP32 ONNX

## Implementation

The opt-in CPU BGE-m3-ko path substitutes a shared ONNX Runtime session
only for the transformer forward of cache-miss queries. The existing
SentenceTransformer tokenizer, pooling, and normalization still run.
A context-local selector prevents corpus ingestion or other model instances
from being routed to ONNX. No changes were made to gRPC, the LRU, FAISS,
or the on-disk index. Startup validates the graph interface and compares
three PyTorch/ONNX probe vectors; failure leaves the original backend active.
The same-revision FP32 graph and external weights are staged outside Git
under `semantic-search/artifacts/query-onnx/`.

Set `LAWCAST_SEMANTIC_QUERY_ONNX_PATH` to the local graph path to enable it.
The default is empty. The two-thread shared ONNX session does not spin while
idle. Disabling the path leaves the gRPC transport and cache intact.

## Measurement

ABBA (PyTorch / ONNX / ONNX / PyTorch) on local macOS arm64. Both arms used
the same BGE-m3-ko revision, same 122,624-chunk CPU FAISS generation and
the twelve queries from the transport test. The cache remained enabled at
256; each process warmed three unrelated inputs and timed each test query
once. Every timed response had a nonzero model stage. There were 24
requests per arm per cell.

- k=5, concurrency 1: gRPC p95 82.12 to 36.93 ms.
- k=5, concurrency 6: gRPC p95 308.66 to 146.50 ms.
- k=50, concurrency 1: gRPC p95 99.74 to 56.39 ms.
- k=50, concurrency 6: gRPC p95 280.55 to 156.86 ms.
- At k=50 and concurrency 6, median embedding fell from 236.63 to
  110.09 ms. Model loading time is outside these request timings.

Both returned tiers retained exact ordered chunk and notice IDs in all 96
paired responses; the maximum matched cosine score difference was
4.77e-7. The pinned Transformers 5.17.0 stack repeated the comparison
with 48 additional rank matches. These are replay parity results, not
a guarantee for all queries or near-ties.

After readiness, process RSS medians were about 1.40 and 3.63 GiB for
PyTorch and ONNX. The ONNX session is additional because update-time corpus
embedding retains PyTorch. No production deployment or capacity claim.
