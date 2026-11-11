# Idle Search Latency Diagnosis

## Finding and confidence

Production observation on 2026-11-11: the intermittent multi-second delay is
inside the sidecar dense pipeline, not merely browser startup or gRPC connection
setup. A 180-second no-probe interval reproduced 1.49-second uncached inference
with 4,435 major faults and 80.8 MiB of process disk reads. Memory paging is
the leading explanation, supported by both the idle control and process swap.
The historical 9–11 second outliers have only aggregate dense timings in logs;
their exact embedding/FAISS split and fault deltas were not recorded. Do not
claim a measured causal allocation of those historical seconds to swap.

No service source, configuration, index, ranking, or deployment was changed.
Sequential production probes only warm the existing in-memory query cache.

## Production evidence

All timestamps below are UTC; add nine hours for the user's Asia/Tokyo timezone.
Evidence is retained in ignored `_workspace/idle-search-diagnosis-20261111/`.

- Container started at 06:27:28, restart count zero. ONNX initialized at
  06:28:23 with two CPU threads and deferred document PyTorch weights.
- At 08:31:02 the sidecar took 11,155.3 ms; the next logged request at
  08:31:09 took 446.1 ms. At 09:30:46 it took 3,145.0 ms, followed by
  108.2 ms. At 12:04:19 it took 8,960.7 ms, followed by 262.3 ms.
- The last slow request had dense=8,954.5 ms, annotation=6.2 ms,
  admission=0.3 ms, rank wait=0.0 ms. Queueing and transport therefore do
  not account for this engine-side outlier.
- Some slow requests occur amid otherwise fast traffic, e.g. 09:40:09
  took 10,207.9 ms after a 213.3 ms request. A simplistic fixed idle timeout
  does not explain all observations; cache hits can mask a cold model.
- Host RAM is 7,935 MiB. Swap usage was 3,538 MiB at 12:06:31 despite
  2,935 MiB of currently available memory. Current availability alone does
  not prove previously swapped anonymous pages are resident again.
- Actual Python worker (container PID 7, not tini PID 1): about 2.67 GiB
  RSS and 0.96 GiB VmSwap. Anonymous regions contain most swapped pages.
  The cgroup reported a 5.15 GiB lifetime memory peak, 2.51 GiB swap, and
  no OOM kills. Cgroup and process counters have different scopes.
- A cache-hit / new-query / repeated-query sequence took 97.15 / 350.02 /
  87.46 ms. The new query had embedding=219.47 ms, ONNX forward/tail=200.27
  ms, FAISS=122.87 ms, 114 major faults, and 1,675,264 read bytes. The
  repeat had embedding=0.049 ms, zero major faults, zero read bytes.
  These warm-process controls establish paging and cache effects, not a
  reproduction of the historical 9-second outlier.
- After 180 seconds without diagnostic search requests, Python RSS fell from
  2,795,244 to 1,979,764 KiB and VmSwap rose from 1,005,628 to 1,782,184
  KiB. No memory pressure, cache flush, or service restart was induced.
  `probe-after-idle.jsonl` records the following three-request sequence:
  - Existing cached query: 187.58 ms wall, embedding=0.152 ms,
    FAISS=144.61 ms, 47 major faults and 2,387,968 disk-read bytes.
  - New query: 1,485.18 ms wall, embedding=1,359.06 ms,
    model forward/tail=1,334.49 ms, FAISS=115.97 ms, admission=0.219 ms,
    4,435 major faults and 84,692,992 disk-read bytes (80.8 MiB).
    VmSwap dropped by 70,156 KiB during that query.
  - Repeating that new query: 103.79 ms wall, embedding=0.048 ms,
    FAISS=94.65 ms, two major faults and 8,192 disk-read bytes.
  This distinguishes keeping the FAISS path warm with cached queries from
  touching cold ONNX inference memory. Major faults alone are not a precise
  I/O-wait duration or an ownership label for each model tensor.

The initial `probe.jsonl` selected tini because its command line contains
the uvicorn arguments. Its search timings remain valid, but its process
fault/swap counters are invalid for inference. Use `probe-correct-pid.jsonl`
and later probes, whose executable filter selects Python PID 7.

## Source explanation

- `semantic-search/lawcast_semantic/embedding.py:246-267`: exact-vector
  LRU has a capacity of 256 in production, not a time TTL. Cache hits bypass
  inference; eviction is capacity-based. Increasing its size does not fix
  first-seen query latency.
- `semantic-search/lawcast_semantic/query_onnx.py:72-90`: one session is
  constructed and probed at startup. No idle unload exists in this path.
  Disabling thread spinning is not unloading weights.
- `semantic-search/service/app.py:466-490`: health only reads state. The
  Docker 30-second healthcheck does not exercise ONNX or FAISS and therefore
  does not keep the inference working set resident.
- `semantic-search/lawcast_semantic/embedding.py:113-139`: document updates
  temporarily load PyTorch and release the model after the last borrower.
  Query ONNX remains alive; object release does not itself guarantee all
  native allocator memory returns to the OS.
- Production cron is hourly (`0 * * * *`). Logs show document weight
  leases around 07:00, 08:00, 09:00, 10:00, and 12:00, followed by releases.
  This is a plausible memory-pressure contributor, not proof that every
  later outlier was caused by that update.
- `semantic-search/lawcast_semantic/incremental.py:226-281,374-398` loads
  the old full embedding matrix, stacks a merged full matrix, and constructs
  a fresh index while the serving generation stays available. One FP32
  121,422 x 1,024 matrix is approximately 474.3 MiB; multiple full buffers
  and temporary PyTorch weights explain a substantial transient footprint.
- `backend/src/modules/semantic-search/semantic-search.service.ts:360-379`
  refreshes the chunk cap after 60 seconds. That adds a health RPC, but the
  observed multi-second delay already exists inside sidecar dense work.
  Production per-request and total search timeouts both equal 30,000 ms.

## Follow-up priorities

1. Capture a naturally slow request's dense subphases, major faults,
   disk-read bytes, swap-in, and memory pressure together. Existing gRPC
   response timings provide the subphases, but historical INFO logs omit
   them. A cache-hit then uncached control separates FAISS warming from
   actual model warming. Do not create artificial host memory pressure.
2. Reduce update-time overlap first: bounded/batched vector processing,
   fewer complete matrix copies, or isolate the update worker lifecycle.
   A separate process can reliably return its allocations on exit, but
   does not by itself eliminate simultaneous host-wide peak memory use.
3. Evaluate sufficient RAM headroom or host workload separation against the
   measured update peak, then repeat idle cache-miss measurements.
4. A bounded, low-priority inference warmup may mitigate cold pages, but
   repeating a cached search only warms FAISS, not ONNX. Use a direct encode
   or a deliberate cache bypass, skip during updates/pressure, and compare
   fault counts and idle p95 before enabling it.
5. Treat INT8 or smaller models as separate quality-gated experiments.
   Keep the existing capability and relevance parity guards.

Do not immediately disable swap, lock all model memory, increase cache size,
or enable busy spinning as a claimed fix. None has been validated here.

## Counter definitions

- Linux documents VmSwap and major-fault counters in
  <https://www.kernel.org/doc/html/v6.15/filesystems/proc.html>.
- Major faults require disk-backed page resolution; they do not distinguish
  every file-backed fault from anonymous swap-in. See
  <https://www.kernel.org/doc/gorman/pdf/understand.pdf>.
- ONNX thread spinning trades CPU consumption for wakeup latency, not model
  residency: <https://onnxruntime.ai/docs/performance/tune-performance/threading.html>.

## Local follow-up

The user subsequently requested implementation and local verification. See
[local improvement](local-improvement.md) for memory-overlap reduction, bounded
cache-bypassing upkeep, controlled idle measurements, and copy-only rollback.
