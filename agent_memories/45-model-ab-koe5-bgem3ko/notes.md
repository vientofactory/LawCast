# Model A/B: KURE-v1 vs BGE-m3-ko vs KoE5 (2026-10-17, measured)

## 1. Question

README "확장 아이디어 -> 미검증 후보 (nlpai-lab/KoE5, dragonkue/BGE-m3-ko 등)와의 추가 A/B"를 실측으로 검증한다.
기준선은 현행 라이브 모델 `nlpai-lab/KURE-v1`이다.

## 2. Method (shared-subset relative A/B)

- Full-corpus embed이 KoE5 기준 ~2h(MPS)이므로, 동일 코퍼스·동일 쿼리의 공유 서브셋으로 상대 비교했다.
- 서브셋: 전체 청크에서 평가 정답 공고 전체 포함 + seeded random fill, 12,000 chunks (`SEED=20261017`, `TARGET_CHUNKS=12000`).
  - 빌드 스크립트: `semantic-search/_workspace/ab_make_subset.py` (출력 `artifacts/ab-subset/chunks.jsonl` — 실제 빌드는 이를 4개 후보 디렉토리에 복사: `ab-sub-kure`, `ab-sub-bgem3ko`, `ab-sub-koe5drop`, `ab-sub-koe5prefix`)
- 후보 4종 (동일 12k 청크, 각자 임베딩+FAISS):
  - `kure-v1-sub`: `nlpai-lab/KURE-v1` (baseline, 현행)
  - `bgem3ko-sub`: `dragonkue/BGE-m3-ko`
  - `koe5drop-sub`: `nlpai-lab/KoE5` drop-in (prefix 없음)
  - `koe5prefix-sub`: `nlpai-lab/KoE5` + 학습 규정 prefix (`passage: ` 문서 / `query: ` 쿼리)
- 비교 하네스: `semantic-search/_workspace/ab_compare.py --subset` (쿼리 40개 = `data/eval_queries.jsonl` 16 + `data/eval_holdout_queries.jsonl` 24, notice-level recall@k/MRR, depth=12000)
- 결과 원본: `semantic-search/_workspace/ab_results_subset.json`, 로그 `semantic-search/_workspace/ab_compare_subset.log`
- 빌드 로그: `semantic-search/_workspace/ab_build_subset.log`

### Model specs (measured at build)

| 후보 | dim | max_seq_length | 비고 |
| --- | --- | --- | --- |
| KURE-v1 | 1024 | 8192 | subset 토큰 최대 151, truncated 0 |
| BGE-m3-ko | 1024 | 8192 | 동일, truncated 0 |
| KoE5 (drop/prefix) | 1024 | 512 | 토큰 최대 151(prefix 153), truncated 0 — 서브셋에서는 잘림 없음 |

## 3. Results (shared 12k subset; absolute values are subset-inflated, deltas are the signal)

### 3.1 Main eval (16 queries)

| 후보 | r@1 | r@3 | r@5 | MRR |
| --- | --- | --- | --- | --- |
| kure-v1-sub (base) | 0.812 | 0.812 | 0.812 | 0.830 |
| bgem3ko-sub | 0.812 | 0.812 | 0.875 | 0.838 (+0.008) |
| koe5drop-sub | 0.688 | 0.812 | 0.875 | 0.748 (-0.082) |
| koe5prefix-sub | 0.688 | 0.812 | 0.875 | 0.754 (-0.076) |

- body 10문항: KURE/BGE MRR 1.000, KoE5 0.858/0.867로 하락.
- title 6문항: KURE MRR 0.547, BGE 0.569(+), KoE5 0.565/0.565 — 타이틀에서는 KoE5가 baseline과 동률 수준.

### 3.2 Holdout eval (24 queries)

| 후보 | r@1 | r@3 | r@5 | MRR |
| --- | --- | --- | --- | --- |
| kure-v1-sub (base) | 0.417 | 0.500 | 0.667 | 0.494 |
| bgem3ko-sub | 0.417 | 0.500 | 0.667 | 0.506 (+0.012) |
| koe5drop-sub | 0.292 | 0.542 | 0.583 | 0.430 (-0.064) |
| koe5prefix-sub | 0.333 | 0.542 | 0.625 | 0.452 (-0.042) |

- BGE: abbr MRR 0.482→0.584 개선, 반면 colloquial 0.465→0.397 하락. synonym 0.530→0.543 소폭 상승.
- KoE5 prefix는 drop-in 대비 holdout MRR +0.022 개선하지만 baseline에는 못 미친다.

### 3.3 Per-query wins/losses vs baseline

- Main(16): BGE win 2 / loss 0 (예: `공급망 안정화 지원` 6→4, `조세특례제한법 개정` 37→14). KoE5-drop win 1 / loss 4. KoE5-prefix win 2 / loss 3.
- Holdout(24): BGE win 6 / loss 5 / tie 13. KoE5-drop win 8 / loss 9. KoE5-prefix win 9 / loss 8.
- KoE5는 개별 쿼리 대승이 있다 (`예보법 개정` 313→50, `KIC 관련법 개정` 377→64, `통화 녹음해서 증거로 써도 되나요?` 597→107) — 그러나 여전히 top-5 밖이라 MRR 기여가 작고, 패한 쿼리가 더 많아 net은 마이너스다. 분산이 큰 모델이다.
- BGE는 대승보다 패가 적은 균형형이다.

## 4. Conclusion (SUBSET STAGE ONLY — final verdict in §8, which reverses point 1)

> Subset read: keep KURE-v1. Full-corpus promotion (§8) showed BGE-m3-ko beating
> KURE-v1 on the realistic holdout set (+0.085 MRR) at main-parity — final
> recommendation is BGE-m3-ko promotion. Points 2–4 below still stand.

1. **현행 KURE-v1 유지.** 두 후보 모두 baseline을 명확히 넘지 못했다.
2. **BGE-m3-ko는 가장 가까운 대안** (main +0.008, holdout +0.012, main 무패) — 그러나 n=40에서 노이즈 범위이므로 교체 근거는 안 된다.
3. **KoE5는 prefix를 지켜도 baseline 미달** (main -0.076, holdout -0.042). Prefix는 drop-in보다 낫다(holdout +0.022)는 것만 확인됐다. 현 파이프라인(raw 텍스트 임베딩) 그대로 KoE5로 교체하면 회귀다.
4. KoE5 특기: 약어 쿼리의 대폭 순위 상승이 있으나 top-5 진입에는 못 미쳤다. 약어 처리가 목표라면 모델 교체보다 쿼리 확장/별칭 사전이 직접적이다.

## 5. Limits (what this does NOT claim)

- 서브셋 상대 비교이므로 절대 recall은 full-corpus와 비교 불가 (경쟁자 119k→12k라 부풀려진다).
- n=40이라 ±0.01대 델타는 노이즈일 수 있다. BGE의 +0.008/+0.012를 "승리"로 주장하지 않는다.
- 품질 축은 recall@k/MRR만 측정. 지연·메모리·인덱스 크기·긴 문서(512 초과) 잘림은 이번 A/B의 서브셋(최대 153 토큰)에서는 발현되지 않았다. KoE5의 512 윈도우는 full-corpus 긴 청크에서 별도 검증이 필요하다.
- Full-corpus 승격 검증을 하지 않았으므로, 어떤 후보도 라이브 교체 근거로 쓸 수 없다.

## 6. Repro

```bash
cd semantic-search
.venv/bin/python _workspace/ab_make_subset.py
for d in ab-sub-kure ab-sub-bgem3ko ab-sub-koe5drop ab-sub-koe5prefix; do
  cp artifacts/ab-subset/chunks.jsonl artifacts/$d/chunks.jsonl
done
# KURE / BGE-m3-ko / KoE5-dropin (stage 2+3 per dir, sequential on MPS)
.venv/bin/python -u scripts/02_extract_embeddings.py --chunks artifacts/ab-sub-kure/chunks.jsonl --out artifacts/ab-sub-kure/embeddings.npz --model nlpai-lab/KURE-v1
.venv/bin/python -u scripts/03_build_index.py --embeddings artifacts/ab-sub-kure/embeddings.npz --out artifacts/ab-sub-kure/faiss.index --id-map artifacts/ab-sub-kure/id_map.json
# ... (same for bgem3ko, koe5drop)
.venv/bin/python -u _workspace/ab_embed_koe5_prefix.py ab-sub-koe5prefix artifacts/ab-sub-koe5prefix/chunks.jsonl
.venv/bin/python -u _workspace/ab_compare.py --subset --out _workspace/ab_results_subset.json
```

Build times (MPS, 12k chunks): KURE ~100min (초기 HF 타임아웃/재시도 포함), BGE-m3-ko ~6min (캐시 적중), KoE5-dropin ~6min, KoE5-prefix ~6min.

## 8. Full-corpus promotion validation (2026-10-17, measured — FINAL VERDICT)

Subset screening (§3) narrowed the field to BGE-m3-ko + KoE5-prefix (KoE5-dropin
was a strict strawman: prefix was better-or-equal everywhere). Both were built on
the FULL 118,973-chunk corpus and compared against the live KURE-v1 artifacts
(same 40 queries, depth=118973).

### Builds (MPS, sequential)

| 후보 | 아티팩트 | embed wall | tokenizer (full corpus) |
| --- | --- | --- | --- |
| bgem3ko-full | `artifacts/ab-bgem3ko/` | ~58min | 9,625,248 tok, max 172, truncated 0 |
| koe5prefix-full | `artifacts/ab-koe5-prefix/` | ~58min | 9,861,502 tok, max 174, truncated 0 |

Both verified: `embeddings.npz` (118973, 1024), `faiss.index` ntotal 118973.
KoE5's 512-token window does NOT truncate anything even on the full corpus
(max 174 tokens incl. `passage: ` prefix) — the truncation headwind did not materialize.
Raw result: `semantic-search/_workspace/ab_results_full.json`
(harness `semantic-search/_workspace/ab_compare_full.py` = live KURE + BGE + KoE5-prefix).

### Results — main eval (16 queries, easier title/body set)

| 후보 | r@1 | r@3 | r@5 | MRR |
| --- | --- | --- | --- | --- |
| kure-v1 (live) | 0.375 | 0.750 | 0.812 | 0.535 |
| bge-m3-ko | 0.375 | 0.625 | 0.812 | 0.522 (-0.013) |
| koe5-prefix | 0.438 | 0.500 | 0.625 | 0.522 (-0.013) |

Per-query vs KURE: BGE win 3 / loss 2 / tie 11; KoE5-prefix win 5 / loss 5 / tie 6.
KURE holds the easy set; gaps are one-query rank shifts (n=16).

### Results — holdout eval (24 queries: abbr/colloquial/synonym, the hard + realistic set)

| 후보 | r@1 | r@3 | r@5 | MRR |
| --- | --- | --- | --- | --- |
| kure-v1 (live) | 0.000 | 0.250 | 0.292 | 0.147 |
| bge-m3-ko | 0.125 | 0.292 | 0.292 | 0.232 (+0.085) |
| koe5-prefix | 0.125 | 0.208 | 0.250 | 0.206 (+0.059) |

Per-query vs KURE: BGE win 13 / loss 8 / tie 3; KoE5-prefix win 15 / loss 8 / tie 1.
BGE top-1 hits where KURE has zero (3/24: `한은 전북 이전`, `5·18 유공자 위탁병원 진료`,
`중소기업에서 사람 뽑기가 너무 힘들어요` — all rank 4→1, 2→1 class moves).
KoE5 posts bigger rank jumps on abbreviations (`예보법 개정` 3287→418,
`KIC 관련법 개정` 3819→428, `통화 녹음…` 5555→1115) but stays outside top-5,
so its MRR contribution is smaller; it also collapses on colloquial
(MRR 0.051 vs KURE 0.146 vs BGE 0.219).

Combined 40-query MRR: BGE 0.348 > KoE5-prefix 0.333 > KURE 0.303.

### Latency (MPS, 5 queries, models cached)

KURE-v1 35.8ms / BGE-m3-ko 35.7ms / KoE5 37.6ms per query — no differentiator.
(Same 1024-dim, same model class; prod is CPU but relative parity holds.)

### FINAL VERDICT — BGE-m3-ko has merit, KoE5 does not

1. **BGE-m3-ko is the only candidate that beats KURE-v1 where it matters.**
   Holdout MRR +0.085 with 3 extra top-1 hits, main within noise (-0.013 MRR,
   identical r@5). The holdout set (abbreviations, colloquial speech, synonyms)
   is the realistic user-query distribution; the main set is dominated by
   near-verbatim title/body matches where every model saturates.
2. **KoE5-prefix is dominated by BGE** (worse-or-equal on every reported cut:
   main MRR tie, holdout MRR -0.026 vs BGE, colloquial collapse) — eliminated,
   no full-corpus future work justified.
3. **Switch cost is low**: same 1024-dim / same FAISS layout / same serving code —
   only `LAWCAST_SEMANTIC_MODEL` + a live artifact rebuild (~1h) + the standard
   submodule release train. No code change, no latency change.
4. **Caveat**: n=40. The holdout gap (+0.085, 13W/8L) is the most substantial
   signal in the whole exercise, but a production switch is still a judgment call.
   Recommended path: switch BGE-m3-ko to live, then confirm on the next eval
   expansion (more abbreviation/colloquial queries) rather than growing the eval
   first — the switch is cheap and reversible.

## 7. Follow-ups

- ~~Full-corpus A/B는 BGE-m3-ko 1종으로만 좁혀서 해도 충분하다~~ — DONE (§8:
  BGE + KoE5-prefix full-corpus 완료. KoE5 탈락 확정, BGE 승격 후보).
- 약어 쿼리(`예보법`, `KIC`, `한은`) 개선은 모델 교체가 아니라 쿼리 확장/별칭 문제로 분리할 것 — 세 모델 모두 해당 쿼리에서 2~3자리수 순위를 기록했다.
  (UPDATE §8: BGE 승격이 이 중 `한은 전북 이전`을 top-1로 해결. `예보법`/`KIC`는
  여전히 전부 3~4자리수 → 별칭 사전이 별도 과제로 남는다.)
- ~~KoE5를 재검토하려면 512 윈도우 초과 청크의 잘림률부터 full-corpus에서 측정할 것.~~ — DONE (§8:
  full-corpus 최대 174 토큰, truncated 0 — 잘림은 논외, 품질로 탈락).


- Full-corpus A/B는 BGE-m3-ko 1종으로만 좁혀서 해도 충분하다 (KoE5는 서브셋에서 탈락).
- 약어 쿼리(`예보법`, `KIC`, `한은`) 개선은 모델 교체가 아니라 쿼리 확장/별칭 문제로 분리할 것 — 세 모델 모두 해당 쿼리에서 2~3자리수 순위를 기록했다.
- KoE5를 재검토하려면 512 윈도우 초과 청크의 잘림률부터 full-corpus에서 측정할 것.
