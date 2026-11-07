# Zipge Gap Follow-up

## Status

SSH on 2026-11-08 confirmed the earlier releases, 120,958 indexed chunks,
the full Korean BGE teacher, and no running BGE20 shadow container. Automatic
identifier lookup and the canonical Pages correction link were rechecked.
Zipge HEAD was still 9f519014d550e80f832b8910bb0291b980b15fb3.

## Local Improvement

On an isolated branch from deployed backend v2.1.0, the ranked archive query
still filters and sorts the full bounded candidate window. It returns all
matching IDs for counts, cache and weak-tier deduplication but enriches only
the visible page. The ranked list omits proposal body overlays, which its
card mapping does not expose. Other archive paths keep existing overlays.

A read-only 22,149-notice SQLite replay compared 444 complete board
responses and found them identical. The 96 repeated exact-law requests
used real summary and diffchain queries with cached dense candidates.
Summary, overlay, and change-count input rows each fell from 5,608 to 480;
proposal overlays fell from 5,608 to zero. Local backend-path p50/p95 were
7.050/13.956 ms before and 5.192/10.171 ms after. The backend suite passed
1,297 tests; an independent rollback restored the 115 focused tests.
No deployment or production latency claim is made for this change.

## Remaining Decisions

An exploratory FTS5/BM25 and equal-weight RRF test did not justify adding
a general lexical ranker: dev Hit@5 13/16 to 12/16, holdout 7/24 to 6/24,
recent 10/11 unchanged. This does not settle morphology-specific retrieval.
Next, add independently adjudicated citizen paraphrases, law-family hard
negatives and recent bills, then compare a bounded morphological signal
without replacing the existing keyword or unrelated-query behavior.

SQ8 stays optional because of the measured scan cost. BGE20 stays in a
disposable shadow replay until recent-notice and tail performance gates
can be met. Browser-side indexing, range-sharded vocabulary and graph-based
recommendations solve different deployment or product needs and were not
adopted for the LawCast search board.
