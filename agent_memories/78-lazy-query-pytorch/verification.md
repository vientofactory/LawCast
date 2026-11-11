# Lazy PyTorch Weights for ONNX Search

## Runtime

A prepared CPU BGE-m3-ko query bundle contains the original FP32 graph and
external weights, a tokenizer from the pinned source revision, and offline
PyTorch probe vectors. The sidecar checks artifact hashes and probe parity
before serving, without creating a PyTorch model. The gRPC contract,
embedding LRU, index, and ranking logic are unchanged. An absent or invalid
bundle uses the existing PyTorch path. Runtime ONNX failure retires the
session and switches the process to a shared PyTorch model.

A document batch borrows a PyTorch model pinned to the bundle revision.
The final borrower drops the model and collects Python object cycles so
weights do not survive until an unrelated collection. Unchanged ticks and
reloads do not acquire a model. A concurrent fallback can keep the same
loaded model, rather than loading two copies.

## Measurement

Mac arm64 CPU, local gRPC, pinned Transformers 5.17.0 stack, one FAISS
generation of 122,624 chunks. Eager and lazy arms both used FP32 ONNX and
the 256-entry cache. Each fresh process warmed three unrelated inputs and
then ran the same twelve queries once. ABBA gave 24 cache misses per
configuration per cell. All 96 ordered result pairs, including scores and
all response fields except timings, were identical.

- k=5 / concurrency 1: p95 37.95 to 33.77 ms; post-query RSS 3.55 to 2.65 GiB.
- k=5 / concurrency 6: p95 141.96 to 116.98 ms; RSS 3.79 to 2.65 GiB.
- k=50 / concurrency 1: p95 38.16 to 38.71 ms; RSS 3.69 to 2.62 GiB.
- k=50 / concurrency 6: p95 139.16 to 121.67 ms; RSS 3.81 to 2.62 GiB.

Across fresh processes, ready RSS median was 3.71 to 2.60 GiB and
post-query median was 3.75 to 2.64 GiB. These are point measurements,
not peak during document updates.

## Update and rollback

Real BGE embedding on a disposable SQLite/FAISS corpus: unchanged and
manual reload did not load weights; inserting notice 1002 caused one
document load, a generation 2 to 3 swap, exact document-vector hashes
versus the eager arm, and gRPC readback of the new notice. A weak reference
confirmed the document model object was collected. An injected ONNX
failure then loaded PyTorch and successfully returned the notice over gRPC.

The full sidecar suite passed 390 tests and focused backend search passed
90. The source baseline and independent rollback each passed 47 focused
tests; source rollback restores eager startup with ONNX still selected.
The staged bundle is retained. No production deployment was performed.
