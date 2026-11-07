# Page-scoped Search Deployment and GPU Evaluation

## Deployment and timing

The page-scoped enrichment backend shipped as v2.1.1 (5755635) via backend PR 234 and root pointer PR 36 (ec33ca3). Root Actions run 42386133215 succeeded, and SSH readback showed both containers healthy with the same 120,958-chunk CPU semantic index. The 56-request, 14-query production baseline on v2.1.0 measured p50/p95 443.5/533.6 ms for localhost HTTP through JSON parsing. The follow-up production load probe was cancelled before its first request when the user requested GPU execution. The expensive search rate limiter refreshes the per-client 60-second TTL on successful requests, so continuous pacing alone may still exhaust the quota; use bounded batches with idle periods or passive observations.

## GPU replay and judgment

The production machine exposed no GPU device. Local Apple MPS ran both BGE-m3-ko inference and exact FP32 top-k over 122,268 local chunks. The 36 timed semantic-leg calls measured p50/p95 31.2/34.3 ms, without HTTP, backend enrichment, or production latency implications. The bulk local WASM jobs were stopped; only bounded lexical gate analysis was run on the GPU-ranked top-50 windows.

Freeze human-readable source anchors before ranking. The 38-item holdout uses 30 new target notices (10 recent, 10 citizen paraphrases, 10 similar bills with judged confounders), eight off-domain controls, and no labeled-ID overlap with the four earlier fixtures. Garu 0.5.4 as a replacement lexical predicate increased Hit@5 from 25/30 to 26/30; new and similar cohorts stayed at 10/10. The paired bootstrap MRR@10 difference interval was [-0.01038, +0.02606]. Keep the production gate unchanged; this is evidence for a limited shadow follow-up, not deployment. For next evaluation, use multiple blind adjudicators and a broader citizen sample.

## Paired local full-API follow-up

Both released backends served the actual archive API with the same SQLite snapshot and one released FastAPI sidecar, using a shared 122,268-row FP32 MPS scan and BGE-m3-ko. The isolated fixture disabled unrelated crawler startup and scheduled work; Redis databases were separate. The exact 14 production probe cases were alternated over 24 timed passes per version (336 pairs, all HTTP 200), after two warm-up passes. All 336 raw response bodies were byte-identical. Full localhost HTTP p50/p95 went from 41.3068/46.4892 to 39.0927/43.8491 ms; the paired median delta was -1.7722 ms (query-cluster bootstrap interval -2.7902 to -0.7208 ms). No production traffic was sent, and all four local listener ports were closed after measurement.
