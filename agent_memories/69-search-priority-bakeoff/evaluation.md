# Search Priority Bake-off

## Decision

Keep the default FP32 FAISS index. Keep the new auto-mode identity path and
explicit one-jamo correction suggestion as local implementation. The SQ8 build
is opt-in and is intended for resource-constrained experiments, not faster
query compute on the measured host. No services or artifacts were deployed.

## Scope and measurement

The local archive contained 22,149 notices and the frozen BGE-m3-ko index
contained 122,268 chunks. Both index formats used the same FP32 embeddings and
chunk IDs. The 46 new curated cases were fixed before running the comparison;
94 existing regression probes were retained. This is a regression replay, not
a blind external relevance study or a sample of production traffic.

Board replay ran the compiled board, semantic HTTP client and archive SQL
against a real local FastAPI sidecar and a read-only archive. The live recent
cache and change tracking were replaced with empty adapters. The lexical
gate was enforced and the cross-encoder was off. The local sidecar advertised
a 50-chunk maximum; the isolated FAISS microbench instead requested 100 rows
on one OpenMP thread with four fresh processes in flat/SQ8/SQ8/flat order.

## Results

- Identifiers: Hit@5 0/8 to 8/8; local median 77.31 to 1.37 ms.
  The new route made zero sidecar calls and preserved archive date scope.
- Formal names: all 12 already had a relevant first hit. The mean filled
  relevant slots in the first five, capped by the known number of relevant
  bills, went from 86.7% to 100%. The first paired pass showed an increase in
  group latency, so this is a quality improvement, not a performance win.
- Corrections: 6/6 expected suggestions, no unexpected suggestions in the
  other 134 cases. The original query was not rewritten. All six were already
  successful at Hit@5 before correction, so this measures guidance only.
- Recent concept searches: Hit@5 remained 10/11 and original-text evidence
  remained 5/11. Existing holdout Hit@5 remained 7/24. No improvement in
  general semantic inference was established.
- Of 77 labeled queries, Hit@5 improved from 48 to 56 and MRR@10 from 0.4863
  to 0.5902. The Hit@5 gain was entirely identifier lookup. The original
  54 unrelated probes had no clear result on 35/54 before and after.
- SQ8: 500,809,773 to 125,210,705 index bytes. Peak RSS delta during isolated
  index load was about 514–515 MB flat and 138 MB SQ8. FAISS p50 increased
  from 7.64–7.71 to 22.13–22.14 ms. The compared board top five changed for
  6/140 queries; aggregate labeled metrics were unchanged. Among common
  raw top-100 hits, 17 crossed one of the relevance thresholds. Same chunk
  capability does not imply same score or ranking.

## Follow-up

Before changing the default index, compare on the deployment architecture
with concurrent load, the real cache, and any enabled reranker. Keep
per-segment metrics: the exact identifier win can otherwise hide a loss in
concept or evidence retrieval. Consider profiling archive hydration for
formal names before widening the exact candidate window. The serving code
uses the existing date, proposer and ended-state constraints; SQ8 leaves the
chunk generator unchanged and incremental writes preserve its selected format.
