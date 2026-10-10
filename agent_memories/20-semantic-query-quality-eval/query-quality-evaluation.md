# Semantic Search Query-Quality Evaluation

Measurement-based evaluation of the LawCast semantic search engine (`semantic-search/`) against
the real learning corpus in `backend/lawcast.db`, plus concrete directions for raising hit rate.
Everything below is measured on the current host artifacts, not imported from the README.

## 1. Engine structure (what is actually indexed)

Pipeline (`semantic-search/lawcast_semantic/`, one-way DAG `config` <- modules <- `search`):

| Stage | Owner | What happens |
| ----- | ----- | ------------ |
| 0 corpus | `datasource.py` | `SELECT noticeNum, subject, proposerCategory, committee, proposalReason FROM notice_archives` — **only `proposalReason`**. `source_html` is never read. No `lifecycle_status` filter. |
| 1 normalize + chunk | `preprocess.py`, `chunking.py` | NFC, section detect (`제안이유`/`주요내용`), sentence-boundary greedy pack, cap `CHUNK_MAX_CHARS`=200 (subject prefix + body), overlap 50. |
| 2 embed | `embedding.py` | `nlpai-lab/KURE-v1` (bge-m3 base, 1024-dim, 8192-token window), CPU, L2-normalized. Input = `"{subject}\n{body_chunk}"` (`compose_embedding_text`). |
| 3 index | `indexing.py` | `faiss.IndexFlatIP` exact search, chunk-level; `id_map.json` carries `chunks_fingerprint`, `model_name`, `updated_at`. |
| 4 query | `search.py` | `normalize_text(query)` -> `embed_query` -> top-k chunks -> `search_tiered` splits by `MIN_SIMILARITY`(0.25)/`CLEAR_SIMILARITY`(0.45). |
| serve | `service/app.py` | FastAPI sidecar :8300 (`/health`, `/search`, `/reload`) + in-process cron updater. |
| consume | `backend/src/modules/semantic-search/semantic-search.service.ts` | over-fetches chunks (`k*3`, growth x2, cap 200), dedups chunk->notice, returns `results`/`weakResults`. Keyword fallback only when sidecar is disabled/unreachable on the first window. |

Measured host state (2026-10-10, after the incremental refresh in §7):

- artifacts refreshed 2026-10-10: **97,368 chunks / 21,177 distinct notices**, avg chunk 129 chars, 3.4% under 60 chars. Pre-refresh set preserved at `semantic-search/artifacts/backup-pre-20261010/` (97,057 chunks / 21,044 notices, built 2026-10-06).
- `notice_archives` in `backend/lawcast.db`: **21,177 rows**, 878 `source_deleted`, 20,299 `active`;
  avg `proposalReason` 625 chars (short 5,215 / medium 13,689 / long 1,754).
- **4,210 distinct `subject` values for 21,177 notices** — ~5 same-named 개정안 per bill. This is the
  single most important corpus fact for ranking design (see §4.2).
- Index is now in sync with the DB snapshot (21,177 notices, §7) but **still contains all 878 `source_deleted` rows**
  (`datasource.load_notices_from_db` has no lifecycle filter).

## 2. Candidate query set (24 queries, 5 kinds) and results

Ran through the real searcher (`search()`, full ranking, notice-deduplicated) and compared against an
FTS5 baseline (`notice_archives_fts MATCH "tok" OR "tok" ... ORDER BY rank`, same DB).
Relevance was judged against a per-query expected-concept keyword set (a lower bound: a bill can be
relevant without the literal keyword, so keyword hits undercount quality).

| Kind | n | Representative queries |
| ---- | - | ---------------------- |
| colloquial | 6 | `전세 보증금을 못 받으면 어떡하나요`, `배달 라이더도 산재보험 되나요`, `반려동물을 버리고 가면 처벌되나요`, `아파트 층간소음 어떻게 해결하나요`, `공장에서 일하다 다쳤는데 보상받을 수 있나요` |
| synonym | 6 | `월세 세액공제`, `임금을 못 받았어요`, `대부업 이자 제한`, `가습기 살균제 피해 구제`, `소상공인 지원 확대`, `여성 창업 지원` |
| abbr | 5 | `전세사기특별법`, `중대재해처벌법`, `이자제한법`, `고준위방폐물 특별법`, `스토킹처벌법` |
| conceptual | 5 | `공급망 안정화`, `저출산 대응 지원`, `인공지능 규제와 육성`, `기후변화 대응`, `지역 의료 인력 확충` |
| vague | 2 | `돈 관련 법`, `환경 보호` |

Aggregate (hit = the query's concept keyword present in a retrieved notice's subject+proposalReason):

```
queries=24   semantic hit@5 = 1.00  hit@1 = 0.92
             FTS      hit@5 = 0.88  hit@1 = 0.88
```

### 2.1 Where semantic wins (paraphrase with zero lexical overlap)

FTS5 returned **nothing or an unrelated bill**; semantic put the right bill at #1:

| query | semantic #1 | FTS #1 |
| ----- | ----------- | ------ |
| `반려동물을 버리고 가면 처벌되나요` | 동물보호법 일부개정법률안 | 민사집행법 일부개정법률안 (miss) |
| `가습기 살균제 피해 구제` | 가습기살균제 피해구제 특별법 전부개정(대안) | 상법 일부개정법률안 (miss) |
| `공장에서 일하다 다쳤는데 보상받을 수 있나요` | 산업재해보상보험법 일부개정법률안 | (no lexical hit) |
| `고준위방폐물 특별법` | 고준위 방사성폐기물 관리 특별법안 | 공공주택 특별법 (matched only "특별법") |
| `학교 급식에 우리 지역 농산물 쓰게 하려면` | 학교급식법 일부개정법률안 | 영유아보육법 (matched only "급식") |

This is the engine's core value and matches the README's stated purpose.

### 2.2 Where semantic loses

- **Exact official name, concatenated abbreviation** — `중대재해처벌법` ranked **중대범죄수사청법안 #1**,
  the actual 중대재해 처벌법 at #2. `전세사기특별법` ranked **주택도시기금법 #1**, the named
  전세사기피해자 지원 특별법 at #3-5.
- **Vague queries** — `돈 관련 법` -> 특정 금융거래정보 보고 법률 / 국가재정법 (generic, low precision);
  `환경 보호` -> 자연공원법 (top-1 score 0.546, barely above the clear threshold).
- **Chunk-level duplication in the served window** — `이자제한법` returned 5 chunks of the *same*
  notice in the top 5; the backend's over-fetch+dedup hides this from users but wastes the over-fetch
  budget (top-20 chunks collapse to only 6-17 distinct notices for name-class queries).

## 3. Objective exact-name benchmark (no hand-labeled relevance)

200 random `subject` values (proposalReason > 300 chars, excluding `(대안)`), each used as its own
query; rank is notice-deduplicated and matched by **bill name** (same-title bills are genuinely
indistinguishable at the notice level — see §4.2).

```
semantic-only                 top1 = 0.560   top<=5 = 0.685   miss = 0.270
+ lexical subject-overlap rerank (same semantic top-100 window)   top1 = 0.915   top<=5 = 0.920
```

Miss classes are systematic, not random: `지방재정법`->지방자치법, `보험업법`->국민연금법,
`한국과학기술원법`->감사원법, `문학진흥법`->관광진흥법, `교통·에너지·환경세법`->도로교통법.
The shared Korean legal boilerplate (`일부개정법률안`, `~에 관한 법률`, `등에`) dominates the
200-char embedding input and pulls semantically unrelated but lexically similar bills together.

## 4. **CRITICAL**: the absolute similarity thresholds are effectively inert

Measured score distributions:

```
query = its own subject, rank-1 score:   mean 0.894  median 0.870  min 0.698
random unrelated notice at rank 20:      mean 0.753  median 0.742  max 1.000
nonsense queries (asdfghjkl / 점심 메뉴 / 2026 월드컵):   0.427 - 0.548
```

- At `CLEAR_SIMILARITY` = 0.45, **100%** of the unrelated sample scores *above* the threshold.
- At `MIN_SIMILARITY` = 0.25, likewise 100%. **Nothing in the servable window ever falls below the
  floor** — corrected in §10.1, which measured 0 of 375 top-15 chunks (noise included) under 0.25 and
  0 rows under 0.25 anywhere in the top 400 of a query. The "only keyboard-mash falls below"
  intuition is wrong: keyboard-mash input also scores above 0.25.
- So the two-tier design in `14-relevance-tier-search/plan.md` is structurally sound but its
  calibration does not separate anything for real Korean legal queries — the clear tier is
  "everything the top-k window contains", and the weak tier is only reachable by nonsense.
  **Re-calibrate on a relative signal (per-query percentile / z-score / rank cut) or accept that the
  tier boundary is a rank cut, not a score cut.**

## 5. Improvement directions (each with its measured basis)

1. **Hybrid lexical + semantic rerank over the candidate window** — the single highest-value change.
   Measured `+0.355` top-1 on the exact-name class (0.560 -> 0.915) with a trivial
   subject-token-overlap rerank over the semantic top-100. FTS5 already exists in the same DB
   (`notice_archives_fts`), so this is BM25/overlap fusion, not new infrastructure.
2. **Recalibrate/remove the absolute thresholds** (§4). Prefer a relative cut.
3. **Filter `lifecycle_status` at index and query time** — 878 `source_deleted` notices are currently
   ranked and servable; the corpus query has no filter.
4. **Abbreviation/alias expansion** — a small dictionary mapping citizen abbreviations
   (전세사기특별법, 중대재해처벌법, 방폐물, 보이스피싱) to official bill-name fragments fixes the
   `중대재해처벌법` class; the engine otherwise lands the right bill at #2-5.
5. **De-boilerplate the embedding input** — strip `(…의원 등 N인)` and down-weight the
   `일부개정법률안` suffix in the subject prefix, then re-embed and A/B on the §3 benchmark
   (`truncated_count` guardrail stays). Hypothesis target: the §3 miss class.
6. **Group/dedupe by bill name for display** — 4,210 names for 21,177 notices means a name query
   legitimately returns several near-identical 개정안; a "대안/최신 우선" representative policy is a
   product decision, and currently the ranking does not encode it.
7. **Cross-encoder reranker over the top ~50** — standard next step, adds a dependency and latency;
   justify with the §2/§3 benchmarks.
8. **Chunk size** — cap 200 chars is a leftover from the retired `ko-sbert-sts` 128-token
   calibration; KURE-v1 has an 8192-token window, so larger chunks (more context per vector) is now
   available, at a precision/recall trade-off to be measured.

## 6. Reproduction

Harness (gitignored, host-local): `_workspace/semantic_query_eval.py`
(raw transcript: `_workspace/eval_out.txt`). Run from the submodule venv:

```bash
cd semantic-search && .venv/bin/python ../_workspace/semantic_query_eval.py
```

Engine loading requires `semantic-search/.venv` plus the model cache; DB access is `mode=ro` against
`backend/lawcast.db`. Evaluation metrics use `lawcast_semantic/evaluation.py` (notice-level rank),
which is the same measure as `scripts/05_evaluate.py`.

## 7. Incremental refresh re-measurement (2026-10-10)

Bringing the index to the current DB and re-running every metric, to test whether freshness was
limiting the numbers above.

```bash
cd semantic-search
cp -p artifacts/{chunks.jsonl,embeddings.npz,faiss.index,id_map.json} artifacts/backup-pre-20261010/
.venv/bin/python scripts/06_incremental_update.py --db ../backend/lawcast.db --plan-only
.venv/bin/python scripts/06_incremental_update.py --db ../backend/lawcast.db
```

Preconditions checked: **no sidecar was listening on :8300** (so no scheduled tick could race the
manual run), `semantic-search/.env` points `LAWCAST_SEMANTIC_DB_PATH` at `../backend/lawcast.db`,
83 GiB disk free for the 793 MiB backup.

| | value |
| --- | --- |
| notices read | 21,177 (was 21,044 indexed) |
| added / updated / deleted notices | **133 / 0 / 0** |
| chunks to embed / reused / dropped | **311 / 97,057 / 0** |
| chunks total | 97,057 -> 97,368 |
| wall time | **55 s** (CPU, model load included) |
| `id_map.updated_at` | 2026-10-06T12:00:20Z -> **2026-10-09T19:19:12Z** |

**Verified pure append:** for all 97,057 reused chunk ids the stored vector is byte-identical to the
pre-update row (0 mismatches) and the reused relative order is preserved; only the 311 new vectors
were computed. The new vectors sit at the *front* because chunk order follows `noticeNum DESC` and the
new notices carry the highest numbers — so `after[311:] == before` is False by construction; align by
`chunk_id`, not by prefix.

| metric | before (21,044) | after (21,177) | delta |
| ------ | --------------- | -------------- | ----- |
| 24-query set: semantic hit@5 / hit@1 | 1.00 / 0.92 | 1.00 / 0.92 | **none** |
| deterministic exact-notice top1 / miss (n=200) | 0.065 / 0.880 | 0.065 / 0.865 | none (noise-level) |
| + lexical subject-overlap rerank top1 / top5 | 0.910 / 0.915 | 0.910 / 0.915 | none |
| calibration: related rank1 mean | 0.910 | 0.910 | none |
| calibration: cross-query @rank20 above 0.45 | 1.00 | 1.00 | **none — §4 holds** |
| the 133 new notices retrievable by own name | **0 / 133** | **80 / 133** in top-50; name-level top1 **0.65** / top5 0.78 / top10 0.86; exact-notice top1 13/133 | new content only |

The project's own tool (`scripts/05_evaluate.py`, notice-level recall/MRR) agrees on both artifact sets:

| eval set | before | after |
| -------- | ------ | ----- |
| `eval_holdout_queries.jsonl` (24: abbr 7 / colloquial 8 / synonym 9) | recall@1 0.042, @3 0.250, @5 0.292, MRR 0.170 | **identical** |
| `eval_queries.jsonl` (16: title 6 / body 10) | recall@1 0.375, @3 0.750, @5 0.812, MRR 0.549 | **identical** |

Individual ranks moved only by the 311 inserted rows (e.g. `예보법 개정` target 2221498: rank 1461 -> 1464).
Run the "before" side with `LAWCAST_SEMANTIC_ARTIFACTS_DIR=$PWD/artifacts/backup-pre-20261010`.
Caveat carried over from the README: these labels were written against a specific corpus, so the
absolute values are not comparable across corpora — only the before/after delta inside one corpus is.
Note the low title recall@1 (0.167) is the same name-class weakness as §3.

Conclusions:

1. **Freshness improved availability, not ranking quality.** The 133 new bills went from absent to
   retrievable (0 -> 80/133 within top-50; the bill name is rank-1 for 65% of them), while every
   pre-existing-content metric is byte-for-byte unchanged — exactly what a pure 311-vector append predicts.
2. **The §4 threshold finding reproduces on a fresh index**: related rank-1 mean is again 0.910 and
   **100%** of cross-query rank-20 pairs score above `CLEAR_SIMILARITY` 0.45, so the absolute tiers
   still separate nothing.
3. **The §3 name class is a ranking ceiling, not a freshness problem.** After refresh the exact target
   *notice* is rank-1 for only 13/133 new bills while the bill *name* is rank-1 for 65% — the gap is
   same-title 개정안 competition (§4.2). Availability is no longer the bottleneck; hybrid rerank
   (§5 finding 1) and name-level grouping (§5 finding 6) are.
4. `source_deleted` 878 rows are still indexed and servable — an incremental update does not remove
   them, because the DB rows still exist and only `lifecycle_status` changes.

Re-measurement harness: `_workspace/name_bench.py --label <before|after> [--chunks ... --index ... --id-map ...]`
runs the deterministic name benchmark + calibration on either artifact set (backup vs live) plus
added-notice coverage; `_workspace/semantic_query_eval.py` re-runs the 24-query set
(`_workspace/eval_out_after.txt`).

## 8. News-agenda query expansion (2026-10-10)

Query set widened to the current legislative agenda as reported by major Korean outlets in
2026-09/10 — 국정감사 이슈(국회입법조사처 281문항), 10/1 본회의 통과 법안(산업안전보건법 등),
플랫폼 공정화법·배달플랫폼 수수료율 규제, 수사·기소 후속입법, AI·개인정보, 연금·응급의료.
**Each concept was first verified to have real bills in `notice_archives`** (`subject LIKE` probe),
so every query below has ground truth in the corpus.

37 queries across 5 styles (`_workspace/news_query_eval.py`, transcript `_workspace/news_out.txt`):

| style | n | semantic hit@1 / hit@5 | FTS hit@1 / hit@5 |
| ----- | - | ---------------------- | ----------------- |
| colloquial | 14 | **0.93 / 1.00** | 0.57 / 0.64 |
| headline (기사체) | 8 | 0.88 / 1.00 | 0.75 / 0.75 |
| jargon (정책용어) | 7 | **1.00 / 1.00** | 0.86 / 1.00 |
| abbr | 5 | 0.80 / 0.80 | 0.60 / 0.80 |
| synonym | 3 | 1.00 / 1.00 | 0.67 / 1.00 |
| **ALL** | **37** | **0.92 / 0.97** | **0.68 / 0.78** |

Combined with the §2 set: **61 queries, semantic hit@1 0.918 / hit@5 0.984 vs FTS 0.754 / 0.820.**
FTS records total misses (0 lexical hits) on citizen phrasing — `가게가 배달앱한테 갑질당해요`,
`일하다 죽으면 회사가 처벌받나요`, `산업안전보건법 개정안 국회 본회의 통과`, `응급실에 갈 곳이 없어요`.
Semantic answers all four at rank 1.

### 8.1 The alias gap is now measured per variant

Canonical bill's notice-deduped rank for different phrasings of the same bill:

| bill | citizen acronym | truncated name | official / spaced name |
| ---- | --------------- | -------------- | ---------------------- |
| 중대재해 처벌 등에 관한 법률 | `중처법` **MISS** | `중대재해처벌법` 2 | `중대재해 처벌법` **1** |
| 산업안전보건법 | `산안법` **MISS** | `산업안전보건법` 1 | 1 |
| 전자상거래 등에서의 소비자보호에 관한 법률 | `전상법` **154** | `전자상거래법` 2 | — |
| 인공지능 발전과 신뢰 기반 조성 등에 관한 기본법 | `AI 기본법` 8 | `인공지능 기본법` 2 | full official **1** |
| 지방의회법 | — | `지방의회법` 7 | `지방의회 설치` **1** |
| 온라인 플랫폼 공정화법 | `플랫폼법` 5 | `플랫폼 공정화법` **1** | 1 |
| 노동조합 및 노동관계조정법 | `노조법` **1** | `노동조합법` **1** | 1 |
| 상속세 및 증여세법 | `상증법` 3 | `상속세법` **1** | 1 |

Pattern: **syllable-initial acronyms that never occur in the corpus fail or degrade** (`중처법`,
`산안법` MISS; `전상법` 154; `AI 기본법` 8; `지방의회법` 7; `플랫폼법` 5), while any variant whose
surface form appears in the text is rank 1. `노조법` works only because 노동조합 shares the syllable.
This is the quantified basis for §5 finding 4 — an alias dictionary for ~10 citizen acronyms is a
cheap, high-certainty fix for a class that currently returns *nothing*.

### 8.2 Other failures found by the news set

- `가게가 배달앱한테 갑질당해요` -> rank 1 was 농수산물의 원산지 표시 등에 관한 법률; the actual
  배달플랫폼 거래 공정화 법안 did not reach the top 3. Highly indirect colloquial phrasing with no
  shared vocabulary still dilutes.
- `기업들이 짜고 가격 올리면 어떻게 되나요` -> rank 4 (FTS 8): 담합 is expressed as 짜고/가격 담합;
  the jargon form `반복 담합 과징금 강화` is rank 1 (0.73), so the gap is wording, not the index.
- `일하다 죽으면 처벌` -> 중대재해 처벌법 at rank 15; the domain lands (산업안전보건 계열이 상위) but
  the specific statute does not.
- `지방의회법 제정` -> 지방자치법 3건이 rank 1-3을 차지하고 지방의회법은 4위: §3의 근접 명칭 혼동과
  같은 클래스(지방의회법 vs 지방자치법).
- `안전보건 공시제`, `작업중지 범위 확대`, `상속세 및 증여세법 개정`, `은퇴자마을 조성 특별법`은
  모두 rank 1 — 최신 의제도 인덱스에 반영되어 있다(§7 갱신 효과).

## 9. Alias dictionary implemented (2026-10-10)

§8.1의 약어 실패 클래스를 실제로 고쳤다.

**변경 파일**

| 파일 | 변경 |
| ---- | ---- |
| `semantic-search/lawcast_semantic/aliases.py` | **신규** — `ALIASES`(약어→정식 법안명) 단일 소유 + `expand_query()` (질의 토큰 인플레이스 치환, `QueryExpansion` 반환) |
| `semantic-search/lawcast_semantic/search.py` | `search()`가 `normalize_text(expand_query(query).text)`를 임베딩 (1줄 + 독스트링) |
| `semantic-search/lawcast_semantic/__init__.py` | `ALIASES`·`QueryExpansion`·`expand_query` 지연 공개 API 추가 |
| `semantic-search/tests/test_aliases.py` | **신규** 15개 테스트 — 표 무결성, 단독/조사 경계, 다중·중복 약어, 대소문자·공백 변형, 빈 질의, `search()`가 확장문을 임베딩하는지 배선 검증 |
| `embedding-map/server/engine.py` | 추적 UI도 같은 질의 경로를 쓰도록 `normalize_text(expand_query(query).text)` |
| `semantic-search/README.md`, `embedding-map/README.md` | 질의 흐름·Stage 4·테스트 목록 갱신 |

**설계: 인덱스를 건드리지 않는다.** 확장은 질의 벡터를 코퍼스가 실제로 가진 정식명 쪽으로
옮기는 방식이라 재임베딩·아티팩트 교체가 전혀 필요 없다. 표의 모든 정식명은
`notice_archives.subject`에 prefix로 실재함을 사전 검증했다(23개 후보 전부 OK).
경계 규칙: 약어는 단독일 때만 확장되고(`중처법상` O, `중처법률` X), 뒤따르는 조사
(은/는/이/가/을/를/의/에/도/만/상/로/과/와/에서/으로)는 보존된다. `AI 기본법`은 공백 유무
(`AI기본법`)와 대소문자를 모두 허용해 하나의 항목으로 처리한다.

**측정 (before = 확장 전 경로, after = 배포된 `search()`)** — `_workspace/alias_ranking.py`:

| 별칭 | 정식 법안 | 단독: before → after | 문장: before → after |
| ---- | --------- | -------------------- | -------------------- |
| 중처법 | 중대재해 처벌 등에 관한 법률 | **MISS → 1** | 133 → **1** |
| 산안법 | 산업안전보건법 | **MISS → 1** | 148 → **1** |
| 전상법 | 전자상거래 등에서의 소비자보호에 관한 법률 | **125 → 1** | 3 → **1** |
| 개보법 | 개인정보 보호법 | **98 → 1** | 1 → 1 |
| 정통망법 | 정보통신망 이용촉진 및 정보보호 등에 관한 법률 | **16 → 1** | 1 → 1 |
| 주임법 | 주택임대차보호법 | **MISS → 1** | 4 → **1** |
| 산재법 | 산업재해보상보험법 | 7 → 2 | 10 → **1** |
| 상증법 | 상속세 및 증여세법 | 3 → **1** | 1 → 1 |
| AI 기본법 | 인공지능 발전과 신뢰 기반 조성 등에 관한 기본법 | 4 → **1** | 3 → **1** |
| 인공지능 기본법 | (동일) | 2 → **1** | 2 → **1** |
| 중대재해처벌법 | 중대재해 처벌 등에 관한 법률 | 2 → **1** | 1 → 1 |
| 근기법 | 근로기준법 | 2 → **1** | 1 → 1 |
| 플랫폼법 | 온라인 플랫폼 중개거래의 공정화에 관한 법률 | 4 → **1** | 4 → 3 |
| (중립 유지) 노조법·하도급법·가맹사업법·대부업법·공정거래법·자본시장법·전세사기특별법·청탁금지법·양육비이행법 | — | 1 → 1 | 1 → 1 (공정거래법은 2 → 1) |

별칭 22개 기준: 단독형 12개가 rank1로 **새로** 도달, 문장형 8개가 rank1로 새로 도달,
**회귀 0건**.

**규칙을 실제로 적용해 항목 하나를 제거했다.** `스토킹처벌법`을 넣었더니 원래 rank1이던 것이
확장 후 rank2로 **악화**되어(1 → 2) 표에서 삭제하고 그 사실을 코드 주석으로 남겼다. 표에 들어가는
조건은 “실패를 고치거나 최소한 중립일 것”이다.

**남은 비-rank1 3건**: 산재법 단독 2(`고용보험 및 산업재해보상보험의 보험료징수 …법`이 제목이
더 길어 근소 우위 — 근접 명칭 문제), 플랫폼법 문장 3(뒤에 붙은 “수수료 규제”가 배달플랫폼 법안을
끌어옴), 양육비이행법 문장 2(중립).

**별칭으로 못 고치는 것**: `지방의회법`은 별칭이 아니라 질의 자체가 정식명이라 확장이 무의미하고
(단독 rank 7, “지방의회법 제정” 4), `지방자치법`과의 근접 명칭 경합이 원인이다. 별칭 사전이 아니라
순위 문제이므로 별도 작업이다.

**검증(모두 통과)**

- `ruff check .` + `ruff format --check .` clean (semantic-search, embedding-map 양쪽)
- `pytest`: semantic-search **157 passed**, embedding-map **18 passed**
- 회귀 게이트: `scripts/05_evaluate.py` holdout `0.042 / 0.250 / 0.292 / 0.170`,
  기본셋 `0.375 / 0.750 / 0.812 / 0.549` — 변경 전과 동일(무회귀)
- 사용자 인터페이스 실측: `scripts/04_search.py --query 중처법` → 중대재해 처벌 등에 관한 법률
  rank1(0.690), `--query 산안법` → 산업안전보건법 rank1(0.815), `--query "전상법 개정"` →
  전자상거래법 rank1(0.861); 사이드카 진입점 `search_tiered('중처법')` → clear tier rank1
**관측된 두 가지 기존 이슈(내 변경이 원인 아님)**

1. `pytest tests/test_indexing_search.py tests/test_entrypoints.py`처럼 **faiss(`indexing`)를 먼저
   import한 뒤 같은 인터프리터에서 torch(`transformers`)를 import하면 `Fatal Python error: Aborted`
   (SIGABRT, exit 134)**로 죽는다. 재현/특성화:
   - 위 2개 파일(둘 다 기존 파일, 내 변경과 무관) 조합 → 134, **순서를 뒤집으면** 22 passed,
   - 문서화된 전체 suite 명령(`pytest tests/ -q`) → **157 passed**,
   - 새 인터프리터에서 `import faiss, torch` 단독 → OK.
   즉 특정 파일 순서의 부작용이고, CI가 쓰는 전체 suite 경로는 통과한다. 별도 과제로 남긴다.
2. 전체 suite 1회차에서 `test_concurrency.py::test_real_engine_serves_concurrent_queries`가 타이밍
   마진으로 실패했으나, 단독 실행(median_ratio 0.66 < 0.85)과 이후 전체 재실행 모두 통과.
   README에 타이밍 민감으로 문서화된 기존 항목이다.

측정 도구 실행 시에는 파이프로 출력을 거를 때 `PIPESTATUS`로 실제 상태를 확인했다(위 134를
`$?`=0으로 잘못 읽을 뻔한 지점).

**아직 안 한 것**: 커밋/PR/버전 범프. 코드 변경이므로 AGENTS.md 릴리스 워크플로를 따른다면
`semantic-search/pyproject.toml` 버전 범프(신규 기능 → minor) + 태그가 필요하다.

## 10. Below-threshold exclusion in the sidecar: cost analysis (2026-10-10)

**Question under review**: the sidecar drops hits whose cosine similarity is below a fixed threshold
and treats them as invalid, before answering. Does that exclusion degrade result quality?

The option already exists and is configurable: `LAWCAST_SEMANTIC_MIN_SIMILARITY` (default **0.25**,
`lawcast_semantic/config.py`) is applied by `SemanticSearcher.search_tiered`
(`lawcast_semantic/search.py`), and `service/app.py` maps the two tiers onto the wire as `results`
(clear, >= `CLEAR_SIMILARITY` 0.45) and `weakResults` (the band between the two). Below the floor the
hit appears in neither list.

Harnesses (gitignored, host-local): `_workspace/threshold_analysis.py` (transcript
`_workspace/threshold_out.txt`) and `_workspace/floor_separability.py` (transcript
`_workspace/sep_out.txt`). Measured on the live artifacts after §7: **97,368 chunks / 21,177 notices**,
`nlpai-lab/KURE-v1`, floor 0.25 / clear 0.45, full 200-chunk window (`SIDE_CAR_MAX_CHUNK_K`).

### 10.1 The shipped floor excludes nothing, so its cost is exactly zero

| measurement | value |
| ----------- | ----- |
| chunks in the top-15 of 25 queries (5 noise + 5 vague-valid + 15 concrete) | 375 |
| of those, score < `MIN_SIMILARITY` 0.25 | **0** |
| lowest score anywhere in that 375-chunk window | 0.403 |
| rows below 0.25 at ranks 16-400 (noise `asdfghjkl`, `오늘 점심 메뉴`) | **0** (min 0.365 / 0.402) |

Consequence: `MIN_SIMILARITY=0.0` and `=0.25` are **measurably identical** — the floor sweep gives the
same hit@1/@5/@10/MRR, the same 0/40 labeled empties and 0/20 natural empties. The exclusion is free in
both directions; it is an unused safety net rather than a filter.

### 10.2 What a floor would have to beat

Best-chunk score of the query's own labeled target:

| set | n | reachable | best-chunk min / median / max | below 0.25 | below 0.45 | below 0.55 |
| --- | - | --------- | ----------------------------- | ---------- | ---------- | ---------- |
| `eval_holdout_queries.jsonl` + `eval_queries.jsonl` | 40 | 32 | 0.505 / 0.615 / 0.754 | 0/32 | 0/32 | 8/32 |
| self-query (each notice asked by its own subject) | 300 | 127 | 0.644 / 0.717 / 0.919 | 0/127 | 0/127 | 0/127 |

The 8/40 unreachable targets are unreachable at **any** floor (absent from the 200-chunk window — same
title-competition class as §3/§4.2), so they are not a floor effect. Conclusion: a floor anywhere up to
**0.50 removes no known-relevant answer** from the candidate window.

### 10.3 Where the cost actually starts

Labeled set = the project's own 40 held-out labels; read the **deltas** across a row set, not the levels
(§3 explains why the levels are low). `natural` = 20 real citizen queries; `noise` = 5 non-legislative
strings. Backend column simulates `collectChunks` (k=5, first window 15, growth x2, cap 200).

| floor | hit@1 | labeled empty | natural empty | noise empty | backend mean notices | queries short of k=5 |
| ----- | ----- | ------------- | ------------- | ----------- | -------------------- | -------------------- |
| 0.00 | 0.175 | 0/40 | 0/20 | 0/5 | 5.00 | 0/40 |
| **0.25 (shipped)** | 0.175 | 0/40 | 0/20 | 0/5 | 5.00 | 0/40 |
| 0.35 | 0.175 | 0/40 | 0/20 | 0/5 | — | — |
| 0.45 | 0.175 | 0/40 | 0/20 | 2/5 | 5.00 | 0/40 |
| 0.50 | 0.175 | 0/40 | 1/20 | 3/5 | — | — |
| 0.55 | 0.150 | 2/40 | 2/20 | 5/5 | 4.53 | 5/40 |
| 0.60 | 0.150 | 5/40 | 6/20 | 5/5 | — | — |

Up to 0.45 the only visible effect is that some nonsense input starts returning nothing, and no genuine
query loses a result. Past 0.50 genuine queries begin to disappear.

### 10.4 **CRITICAL**: no absolute floor can separate noise from valid queries

Top-1 score, i.e. the exact number a floor is compared against:

```
noise       : 0.427 asdfghjkl  0.449 우리 동네 축제 일정  0.469 2026 월드컵 우승 전략
              0.523 화성 이주 계획  0.536 오늘 점심 메뉴
vague-valid : 0.480 그거 어떻게 되나요  0.546 환경 보호  0.570 뭔가 이상한 법 있어요
              0.584 요즘 화제인 법  0.605 돈 관련 법
concrete    : 0.583 - 0.746 (내 개인정보 함부로 못 쓰게 해주세요 ... 월세 세액공제)
```

The highest noise query (`오늘 점심 메뉴`, 0.536) scores **above** valid vague queries
(`그거 어떻게 되나요` 0.480, `환경 보호` 0.546). The distributions overlap, so **every floor high enough
to reject noise also empties at least one valid citizen query** — there is no separating threshold.
An absolute cosine floor is therefore a rank cut in disguise, not a relevance filter.

Corroborating: the 15th-ranked chunk of a *noise* query still scores 0.403-0.486, i.e. inside the
two bands. Noise is not confined to the weak tier either — of a noise query's top-15, **6.2 on
average already land in the clear tier** (8.8 in weak, 0 dropped), versus 15.0 clear for valid queries.
All 44 of the 375 measured chunks below `CLEAR_SIMILARITY` 0.45 come from the 5 noise queries; the valid
top-15 windows are 100% clear. So the tier split does not contain noise — what does is the frontend's
explicit reveal button, and §4's "the weak tier is only reachable by nonsense" is confirmed here.

### 10.5 The cost is not only ranking — it shortens the served list

`search_tiered` cuts the top-k window, and the backend's `collectChunks` stops widening when
`results + weakResults < chunkK` (`corpusExhausted`, `semantic-search.service.ts:223`). A raised floor
shrinks that sum, so the over-fetch loop terminates earlier and can return **fewer notices than k**
(measured: 4.53 mean / 5 of 40 queries short at floor 0.55). Separately, setting
`MIN_SIMILARITY = CLEAR_SIMILARITY` (0.45) makes the weak band empty **by construction**, so
`weakResults` is always `[]` and the frontend's reveal affordance can never render.

### 10.6 Verdict

1. **Keep the default 0.25.** Its measured cost is zero (10.1) and it remains a guard for input no eval
   set covers; §4 carried the incorrect assumption that it rejects garbage, which 10.1 disproves.
2. **Do not raise it as a noise filter.** 10.4 shows no separating floor exists. If noise rejection is
   the goal, the discriminating signal is lexical — the subject/token-overlap rerank of §5 finding 1
   (measured +0.355 top-1) — or a relative per-query cut, never an absolute cosine.
3. **Re-measure if the embedding model changes.** KURE-v1 compresses the whole corpus into a high band
   (lowest score over a query's top-400 was 0.365); a model with a wider dynamic range could make the
   same default start firing, which would then matter.

Limitations: one corpus, one model, ~65 queries; the labeled set's absolute levels are low for the
same-title reason in §3, so only row-wise deltas are meaningful. Not measured: human-judged precision of
the retained hits at each floor, and the same sweep on a larger natural-query sample.

**No source code changed for §10** — this is analysis only; the harnesses are gitignored host-local
files.
