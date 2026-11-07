# Production Search Shadow

## Scope

On 2026-11-07, the production release verified automatic-search identifier
priority and explicit typo suggestions. The published code isolates the
BGE20 projection in a one-shot, networkless replay. It is not loaded by the
HTTP application and does not see or answer live user queries. Production
retains the 24-layer Korean BGE teacher, the existing FP32 index and its
reranker-off configuration. SQ8 remains an explicit builder option.

The refinement overlaps exact-name discovery with the dense request, caps
the combined candidate set and skips the recent cache when an exact number
has already been found in the archive. The frontend consumes the additive
suggestion field; its correction link is explicit, not an automatic rewrite.
A 140-query local replay retained the 48/77 to 56/77 labeled Hit@5 change.
Both the local rollback copy and the production scope checks passed.

## Operational verification

- [Backend PR 233](https://github.com/vientofactory/LawCast-Backend/pull/233)
  released as `backend-v2.1.0`.
- [Semantic search PR 20](https://github.com/vientofactory/semantic-search/pull/20)
  released as `semantic-search-v2.9.0`.
- [Root PR 34](https://github.com/vientofactory/LawCast/pull/34) and
  [main deploy run](https://github.com/vientofactory/LawCast/actions/runs/42380253092)
  shipped both services. The production index capability comparison reported
  no deltas and no capability loss. SSH readback confirmed 120,958 chunks.
- The backend origin returned HTTP 200 on all 12 fixed queries before and
  after. Exact bill `2205171` went from no hits at 389.26 ms to one correct
  hit at 9.72 ms; `2222500` went from unrelated results at 588.41 ms to one
  correct hit at 28.03 ms. The exact-name top five, explicit typo suggestion,
  no suggestion in semantic mode and date scope were separately verified.

## Timing

The 12-query backend HTTP sample (including archive hydration) had p50
576.37 to 591.42 ms and p95 756.81 to 865.85 ms. Excluding the two identifiers,
p50 was 589.85 to 602.75 ms. The identity fast path does not establish a
general end-to-end speedup; larger exact name candidate sets can add
archive hydration work.

On the actual released image, 20 paired probes (10 fixed queries twice,
CPU capped, read-only index/cache, alternating order) gave:

- Encode p50: 290.96 to 243.78 ms.
- FAISS p50: 70.38 to 71.21 ms.
- Sidecar total p50/p95: 373.85/474.67 to 322.20/386.11 ms.
- BGE20 was faster in 20/20 pairs. The ordered top five matched in only 4/20.

These Docker totals include embedding, FAISS, annotation and serialization
but not backend HTTP/hydration. A staging replay on the same host had a worse
BGE20 p95 (500.40 to 589.13 ms), so the tail gain is not stable. In a separate
8-pair reranker-on diagnostic, sidecar p50 increased from 2749.37 to
2933.47 ms despite cheaper encoding. Keep BGE20 in shadow only.

## Frontend

[Frontend PR 198](https://github.com/vientofactory/LawCast-Frontend/pull/198)
released as `frontend-v2.2.0` after the backend was live.
[Pages run](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42381064206)
deployed the exact release commit. The canonical site returned HTTP 200 and
rendered a correction link to the corrected query in automatic mode.

[Root PR 35](https://github.com/vientofactory/LawCast/pull/35) and its
[final CI run](https://github.com/vientofactory/LawCast/actions/runs/42381436066)
succeeded. SSH confirmed a clean main, all release gitlinks matched, backend
and semantic search healthy, and no disposable shadow containers left behind.
