# Index-Construction Boilerplate Stripping (Section Labels + Item Markers)

Request: during index construction, strip `제안이유` / `주요내용` / `제안이유 및 주요내용` and the
`가. 나. 다.` item markers out of the text before it is embedded, so no embedding work is spent on
corpus-wide boilerplate.

Everything below is measured on the host corpus (`backend/lawcast.db`, `notice_archives`, 21,177 rows)
with the current artifacts (`nlpai-lab/KURE-v1`, 97,368 chunks). Harnesses are gitignored host-local
files under `_workspace/`.

## 1. What the corpus actually contains

Line-start token counts over the newest 3,000 notices (proposalReason > 300 chars):

| line-start token | count | verdict |
| ---------------- | ----- | ------- |
| `제안이유` | 2,148 | label — the single most common line-start token in the corpus |
| `주요내용` | 432 | label |
| `참고사항` | 184 | label |
| `가.` `나.` `다.` `라.` `마.` `바.` `사.` `아.` `자.` `차.` `카.` `타.` | 2,473 total | enumeration |
| `1)` / `2)` | 84 | enumeration |
| `이에` 2,230, `현행법은` 1,224, `그런데` 749 | — | real content, must NOT be touched |

**The dominant label shape is glued, not standalone**: `제안이유 및 주요내용 <본문이 바로 이어짐>`.
The shipped `SECTION_HEADER_RE` required the label to occupy the whole line (`\s*$`), so in that shape
the label was not recognized as a header at all and stayed inside the embedded text. Measured: **813 of
14,672 chunks** (5.5%) carried a leaked label in their first 20 characters, and 1,059 chunks contained a
label token anywhere.

Qualifier variants found by scanning every label occurrence: `대안의 제안이유` (150), `대안의 주요내용`
(88), `2. 대안의 제안이유`-style (7), `가. 제안이유`-style (6). One false-positive shape exists in the
corpus too: `계약의 주요 내용` (prose).

## 2. Design

| file | change |
| ---- | ------ |
| `lawcast_semantic/preprocess.py` | `SECTION_HEADER_CORE` + `SECTION_HEADER_RE` became **prefix-anchored** (optional `[`/`【` bracket, optional `대안의` qualifier, then the core, then whitespace or line end). Added `split_section_header`, `ITEM_MARKER_RE` + `strip_item_marker` (line-leading marker), and `_GLUED_PREFIX_RE` + `strip_glued_prefixes` (marker/label glued after a sentence end). |
| `lawcast_semantic/chunking.py` | `chunk_notice` now strips, per paragraph, the line-leading marker and then the glued prefixes, before building units; the fallback path strips markers too. |
| `tests/test_preprocess.py`, `tests/test_chunking.py` | +15 tests pinning the accepted shapes, the rejected shapes, and end-to-end chunk text. |

Two rules keep the transform from deleting real text, and both came out of a measured trap rather than
from theory:

1. **A label is only a label when whitespace or the line end follows it.** Otherwise
   `주요 내용은 다음과 같음.` and `계약의 주요 내용` would lose their first words.
2. **A paragraph-initial label is left alone; only a sentence-glued one is removed.** `가. 주요 내용
   첫 번째 항목임.` is a body item whose second word looks exactly like a label. An earlier version
   accepted an enumeration prefix before the header core and stripped this line to `첫 번째 항목임.` —
   the pre-existing `test_section_names_propagate_to_chunks` caught it. Consequently an enumeration
   marker is **not** accepted as a header prefix at all (`가. 제안이유` stays content), which costs the
   14 enumerated headers in 3,000 notices so that body items stay intact.

`normalize_text` is deliberately left transform-free: it is shared with the **query** path
(`search.py`, `embedding-map/server/engine.py`), where deleting what a user typed would change the
search. All stripping lives in the indexing path only. `tests/test_preprocess.py` pins this with
`test_normalize_text_keeps_structure_tokens`.

Sentence-glued removal happens on the paragraph text, not per packed unit: which sentence a chunk
boundary lands on is decided later by the packer, so a prefix removed only from a unit start survives
whenever the packer grouped it with the sentence in front of it (first attempt did exactly that).

## 3. Measured effect (newest 3,000 notices, proposalReason > 300 chars)

| metric | before | after | delta |
| ------ | ------ | ----- | ----- |
| chunks | 14,672 | 14,536 | **−0.93%** (136 fewer vectors) |
| embedded characters | 2,284,803 | 2,262,240 | −0.99% |
| embedded tokens | 1,311,366 | 1,297,707 | **−1.04%** |
| chunks containing a label token | 1,059 | 66 | −94% |
| chunks starting with an item marker | 1,921 | 10 | −99.5% |
| notices with 100% paragraph coverage | 803 | 802 | −1 notice (see §4) |

Extrapolated to the full corpus: ~905 fewer vectors and ~1% fewer tokens — i.e. **the compute saving is
about one percent**, not the large win the request assumed. The real value is quality: the label was the
corpus's most common line-start token, identical across thousands of notices, so embedding it pulled
unrelated bills closer together (same class of problem as §3 of
`20-semantic-query-quality-eval/query-quality-evaluation.md`).

**Residual boilerplate** (documented, not fixed): ~60 chunks keep a label that is run together with the
neighbouring text without whitespace (`...것임.주요내용가.`, `...신설).참고사항 이...`), and ~10 chunks
start with a marker that follows a non-sentence boundary (`... (제4조ㆍ제5조) 나. ...`). Both are
≈0.4% of chunks and need a rule with more false-positive risk than they are worth.

## 4. (pre-existing at the time) the trailing-fragment filter dropped real content — **FIXED in session 22**

**Corrected 2026-10-10**: the numbers below were produced by a harness whose matching was too loose, and
they over-count by ~3x. The real figures (whitespace-insensitive matching that mirrors the chunker's
cleaning exactly) are **737 / 3,000 notices (24.6%) and 872 content units**, and on the full corpus
**3,795 notices (19.6%) / 4,434 units** — not 73%. See
`22-chunk-floor-content-loss/chunk-floor-content-loss.md §2` for the two false-positive causes and §3 for
the corrected measurement. The mechanism and the trigger below were correct.

The filter that did it, in `chunk_notice`:

```python
if len(text) < min_chars and chunks:   # CHUNK_MIN_CHARS = 40
    continue
```

A leftover that did not fit beside its neighbour (a sentence tail from `_paragraph_units`, or a section's
last paragraph after a full chunk) landed alone, fell under 40 characters and disappeared from the index —
it was then unsearchable. Shortening the text (a marker or label removed) cannot shift boundaries enough
to create such a leftover on its own, which is why this change costs only one notice (`2218568`, the
39-character clause `약식명령절차에서도 형의 집행유예가 가능하도록 함(안 제448조제2항).`).

**Resolved in session 22** (`agent_memories/22-chunk-floor-content-loss/`): the floor is now a merge, not
a filter, and the loss is 0 on the full corpus.

## 5. Re-embedding cost of shipping this change

`scripts/06_incremental_update.py --db ../backend/lawcast.db --plan-only`, against a copy of the live
artifacts:

```
notices 21177  chunks_total 96565  to_embed 20178  reused 76387  dropped 845
```

So the incremental path re-embeds **20.9%** of the chunk set (~31 min at the measured 11 chunks/s on
CPU) and produces exactly what a full rebuild would: chunk ids are `noticeNum-####`, so most rows keep
their id and only their text changes. A full rebuild of the corpus costs ~2.5 h, so the incremental path
is the right way to ship this.

## 6. Verification

- `ruff check .` + `ruff format --check .` clean (37 files).
- `pytest tests/ -q` → **172 passed** (was 157; +15 new tests).
- Corpus measurement above (`_workspace/marker_coverage.py`, `_workspace/marker_cost.py`).
- Ranking A/B on the real index: candidate artifacts built under
  `LAWCAST_SEMANTIC_ARTIFACTS_DIR=/tmp/lc-cand-artifacts` and compared against the untouched live
  artifacts with `scripts/05_evaluate.py` plus the alias/per-variant ranking probe. Results: see §7.

## 7. Ranking A/B on the rebuilt index

Candidate artifacts were built by `scripts/06_incremental_update.py` into
`LAWCAST_SEMANTIC_ARTIFACTS_DIR=/tmp/lc-cand-artifacts` (exit 0; `chunks_total 96565`,
`to_embed 20178`, `reused 76387`, `dropped 845`, fingerprint `79da2b4d52c7`, ~26 min wall). The live
`semantic-search/artifacts/` was left untouched and serves as the baseline, so this compares the two
chunk sets with every other variable fixed: same model, same searcher code, same queries.

`scripts/05_evaluate.py`, full ranking:

| eval set | baseline | candidate |
| -------- | -------- | --------- |
| `eval_queries.jsonl` (16: body 10 / title 6) recall@1 / @3 / @5 / MRR | 0.375 / 0.750 / 0.812 / 0.549 | 0.375 / 0.750 / 0.812 / **0.559** |
| — the `title` bucket alone, MRR | 0.269 | **0.296** |
| `eval_holdout_queries.jsonl` (24: abbr 7 / colloquial 8 / synonym 9) | 0.042 / 0.250 / 0.292 / 0.170 | 0.042 / 0.250 / 0.292 / 0.170 |

Alias / citizen-variant ranking on both indexes (notice-deduplicated rank of the expected bill):
**better=0, same=14, worse=0** — 중처법 1/1, 중대재해처벌법 1/1, 산안법 1/1, 산재법 2/2, 전상법 1/1,
개보법 1/1, 정통망법 1/1, 주임법 1/1, 상증법 1/1, `AI 기본법` 1/1, 근기법 1/1, 플랫폼법 1/1,
노조법 1/1, 청탁금지법 1/1.

Individual rank moves are small and both-directional: `공급망 안정화 지원` 88 → 85,
`정보통신망 이용촉진` 151 → 152, `예보법 개정` 1464 → 1499. No recall bucket moves in either
direction.

**Verdict**: stripping the boilerplate is quality-neutral on the project's own metrics (one MRR bucket
improves, nothing regresses) for a ~1% compute saving, and it removes the corpus's most common
boilerplate token from every chunk that carried it. The live artifacts must be rebuilt (incremental) for
the change to reach production; the temporary candidate set under `/tmp` is verification scaffolding and
can be deleted.
