# Semantic Search Relevance Rollback

## Scope and evidence

Semantic-search commit `072131f` (#23) combined independent changes. Its
`SemanticSearcher.load` could build an IDF/background profile for Korean BGE
FlatIP, and its tiering method could filter a dense window using that profile.
Even with the flag off, same-law recovery could return amendments below the
configured minimum. The local dotenv had the flag off but overrode the
previous `0.25` / `0.45` thresholds with `0.49` / `0.51`. These observations
describe this checkout, not a measurement of the production environment.

## Restored behavior

Request serving again splits the unchanged FAISS window by its configured
cosine thresholds, like `284125e`. The local thresholds are restored to
`0.25` / `0.45`. The calibration experiment remains runnable offline.
The internal response still serializes `candidateCount: null`, which selects
cosine-window counting in the existing backend. The encoder, FAISS index,
aliases, timing fields and optional worker lanes are unchanged. The
cross-encoder is not reintroduced.

## Verification

- The two targeted regressions fail against `072131f`, pass with the change,
  and fail again after reversing the patch in an independent copy.
- All 374 sidecar tests pass, including concurrency and HTTP response tests.
- On the same local FlatIP generation (122,381 chunks), with the same five
  fixed query vectors, both ordered tiers match `284125e` for all five
  queries. This is a parity check, not a search-quality or latency benchmark.
