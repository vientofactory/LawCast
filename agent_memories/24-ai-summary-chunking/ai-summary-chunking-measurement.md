# AI 요약(aiSummary) 청킹 포함 — 검색 품질 실측

`agent_memories/06-semantic-search-side-project/plan.md`의 "Future integration ideas"에 있던
**"include `aiSummary` in chunks"** 항목을 실제로 시행하고, 검색 품질에 유효한 변화가 있는지
같은 코퍼스·같은 모델로 before/after A/B 실측한 기록.

## 1. 결론 요약

**유효한 변화가 있다. 단, 효과는 국소적이다.**

| 축 | before (요약 미포함) | after (요약 포함) | 판정 |
| --- | --- | --- | --- |
| 요약 어휘 질의 300건 (자기 요약을 질의로, 서빙 창 200청크) | hit@1 0.407 / hit@5 0.510 / **miss 0.337** | hit@1 **0.990** / hit@5 **1.000** / **miss 0.000** | **압도적 개선 (새 능력)** |
| 자연 시민 질의 24건 | hit@1 0.958 / hit@3 1.000 / MRR 0.979 | 동일 | 불변 |
| 뉴스 의제 질의 37건 | hit@1 0.946 / hit@5 1.000 / MRR 0.959 | 동일 | 불변 |
| 라벨 평가셋 holdout 24건 | 0.000 / 0.250 / 0.292 / MRR 0.149 | 0.000 / 0.250 / 0.292 / MRR 0.147 | 사실상 불변 |
| 라벨 평가셋 기본 16건 | 0.375 / 0.750 / 0.812 / MRR 0.559 | 0.375 / 0.750 / 0.812 / MRR 0.546 | 사실상 불변 |
| 정답 법안명 벤치마크 (n=200, 결정적) | top1 0.065 / miss 0.865 / 어휘 재랭크 top1 0.895 | top1 0.070 / miss 0.865 / 어휘 재랭크 top1 **0.945** | 무회귀·소폭 개선 |
| 요약 질의 dilution (자기 요약 청크 마스킹) | hit@1 0.407 / miss 0.337 | hit@1 **0.307** / miss **0.400** | **비용 확인 (−0.10)** |
| 200청크 창이 덮는 고유 공고 수 (261 질의 평균) | 142.3 | 140.6 (−1.2%) | 창 압박은 무시할 수준 |

해석: 요약 청크는 **"사용자가 요약처럼 말할 때" 검색되던 않던 공고를 검색 가능하게 만든다**
(before miss 33.7% → 0%). 반대로 기존 라벨/자연 질의 지표는 천장에 붙어 있어 변화가 보이지 않고,
비용은 **요약 벡터끼리의 경쟁**으로 나타난다(자기 요약을 가리면 hit@1 −0.10).

## 2. 코퍼스 사실 (실측, 2026-10-11)

- 요약은 `notice_archives`에 없다. **`notice_archive_snapshot_states.ai_summary`** (스냅샷 상태
  테이블, `notice_num` 1:1, 마이그레이션 `202607060003-remove-archive-summary-columns`가 분리).
- `ai_summary_status` 분포: `ready` 21,071 / `not_supported` 106. `ready` 21,071건 전부 실제 텍스트
  보유 → **요약 커버리지 99.5%**. 길이 평균 71자 (13~227자).
- 요약문 자체가 이미 시민체다: `"...하려는 개정안입니다."`, `"...하고자 함."`,
  `"이 법안은 심신장애, 경제적 어려움 ... 취약계층에게 사회보장급여 접근성을 높여 ..."`.
  → 법률 원문(`제안이유`)과 질의 어휘 사이의 거리를 줄여 줄 수 있다는 가설의 근거.

## 3. 구현 (변경 파일)

| 파일 | 변경 |
| ---- | ---- |
| `semantic-search/lawcast_semantic/datasource.py` | `NOTICE_SELECT_COLUMNS`·`NOTICE_FROM` 도입 — `notice_archives LEFT JOIN notice_archive_snapshot_states AS summary ON summary.notice_num = notice_archives.noticeNum`, `COALESCE(summary.ai_summary, '')`. `record_from_row`가 `ai_summary` 키를 추가. 읽기 전용·`source_html` 미열람 원칙 불변 |
| `semantic-search/lawcast_semantic/chunking.py` | `SUMMARY_SECTION = 'AI 요약'` 신규. `chunk_notice`가 요약을 **마지막 섹션**으로 추가 (id는 위치 기반이라 앞에 넣으면 본문 청크 id가 전부 밀려 인덱스 전체가 무효) |
| `semantic-search/tests/test_datasource.py` | 픽스처에 스냅샷 테이블 추가(`summaries=` 인자), 레코드 dict 단정에 `ai_summary` 반영, 조인 전용 테스트 1개 |
| `semantic-search/tests/test_chunking.py` | 요약 4종 테스트 — (a) 마지막 `AI 요약` 섹션이고 본문 청크 id·텍스트 불변 (b) 요약 없는 공고/JSONL 스냅샷은 섹션 없음 (c) 빈 `proposalReason` 공고도 제목 청크를 **유지**하고 요약을 추가 (d) 요약도 같은 문자 예산으로 패킹 |
| `semantic-search/tests/test_entrypoints.py` | `--db` 경로가 요약까지 청킹해 `chunks.jsonl`에 `"section": "AI 요약"`을 쓰는지 단정 |
| `semantic-search/README.md` | Stage 0 조인·Stage 1 섹션·청크 스키마·테스트 목록·청크 수 갱신 |

코퍼스 실측: **96,646 → 117,718청크 (+21,072)**, 본문 96,646행은 **바이트 단위로 전량 재사용**
(증분 계획 `to_embed 21,072 / reused 96,646 / dropped 0`) → 순수 추가.

## 4. **CRITICAL**: 첫 구현이 만든 회귀와 그 수정

첫 구현은 빈 `proposal_reason` 공고에서 **요약 청크가 기존 제목 폴백 청크를 대체**했다
(그 공고들은 `chunks`가 비지 않으므로 `if not chunks` 폴백이 실행되지 않음). 그 결과:

- 겉보기 지표는 **올랐다**: `05_evaluate` title recall@1 0.167 → 0.333, news37 hit@1 0.946 → 0.973,
  어휘 재랭크 top1 0.895 → 0.995.
- 그러나 원인은 요약이 아니라 **405건의 title-only 청크(텍스트 == 제목, 이름 질의에 대해 스코어
  1.000)를 인덱스에서 제거한 부작용**이었다. 동시에 그 405건은 자기 제목으로 정확히 검색되던
  능력을 잃었다: `name_bench` added-notice coverage 80/133 → **48/133**, top1 16/133 → **4/133**.
  직접 프로브(`_workspace/added_probe.py`)에서 `1.000 2219970 [body] 수산업법 일부개정법률안`
  같은 1.000 히트가 사라지고 최상위가 0.927로 내려가는 것을 확인.

**수정 (채택안, additive)**: `proposal_reason`이 섹션을 하나도 못 만들면
`('body', subject)` 제목 청크를 **유지한 채** 요약 섹션을 덧붙인다. 117,313 → 117,718청크,
본문 재사용 96,646 유지, `dropped 0`. 재측정 결과 회귀 0건(name_bench added coverage 83/133,
top1 15/133 — before와 동등).

**일반 교훈**: 기존 청크를 *대체*하는 변경은 지표를 올리면서 능력을 지운다. 회귀는 반드시
대칭으로 재측정해야 한다(제목-only 청크 클래스별 커버리지). 그리고 이 프로젝트에서 청크 id는
위치 기반이므로 **섹션은 항상 뒤에 붙인다**.

## 5. 실행 관측 (artifacts/exp-ai-summary)

- live 아티팩트를 복사한 뒤 증분 갱신 1회: `to_embed 21,072 / reused 96,646 / dropped 0`,
  벽시계 **약 11분** (MPS, 모델 로드 포함), `embeddings.npz` 373 → 453MB, `faiss.index` 396 → 481MB.
- `SemanticSearcher.load` 통과(지문·행 수·모델 검증), 117,718청크 / 21,177공고.
- `truncated_count` 위험 없음(최장 임베딩 입력 = 본문 230자 + 제목, KURE-v1 8192토큰).

## 6. 재현

```bash
cd semantic-search
# 1) 실험 아티팩트 세트 (live는 건드리지 않는다)
mkdir -p artifacts/exp-ai-summary
cp -p artifacts/{chunks.jsonl,embeddings.npz,faiss.index,id_map.json} artifacts/exp-ai-summary/
HF_HUB_OFFLINE=1 LAWCAST_SEMANTIC_ARTIFACTS_DIR=$PWD/artifacts/exp-ai-summary \
  .venv/bin/python scripts/06_incremental_update.py --db ../backend/lawcast.db --plan-only
HF_HUB_OFFLINE=1 LAWCAST_SEMANTIC_ARTIFACTS_DIR=$PWD/artifacts/exp-ai-summary \
  .venv/bin/python scripts/06_incremental_update.py --db ../backend/lawcast.db

# 2) A/B (before는 라이브 아티팩트 = 요약 없음)
.venv/bin/python ../_workspace/ai_summary_ab.py --label before --artifacts $PWD/artifacts
.venv/bin/python ../_workspace/ai_summary_ab.py --label after  --artifacts $PWD/artifacts/exp-ai-summary
.venv/bin/python ../_workspace/window_coverage.py --label before --artifacts $PWD/artifacts
.venv/bin/python ../_workspace/name_bench.py --label after \
  --chunks artifacts/exp-ai-summary/chunks.jsonl \
  --index artifacts/exp-ai-summary/faiss.index \
  --id-map artifacts/exp-ai-summary/id_map.json
LAWCAST_SEMANTIC_ARTIFACTS_DIR=$PWD/artifacts/exp-ai-summary \
  .venv/bin/python scripts/05_evaluate.py --eval data/eval_queries.jsonl
```

하니스(모두 gitignored, host-local): `_workspace/ai_summary_ab.py`(A/B 본체 — 자연 질의 +
요약 질의 self-match/dilution 두 모드), `_workspace/window_coverage.py`(고정 청크 창의 공고
커버리지), `_workspace/one_query.py`(단일 질의 창 출력), `_workspace/added_probe.py`(added-notice
클래스 프로브), 기존 `_workspace/name_bench.py`·`scripts/05_evaluate.py`.

## 7. 한계 (주장하지 않는 것)

- **B(요약 질의)의 self-match 수치는 자연 질의 추정치가 아니다.** 질의 텍스트가 인덱스에 그대로
  들어가므로 hit@1 0.990은 천장값이다. 신뢰할 수 있는 부분은 **before의 miss 0.337**(=요약 어휘가
  본문만으로는 1/3 확률로 도달 불가)과, dilution 모드(B2)의 델타다.
- 자연 질의 61건·라벨 40건은 이미 포화(hit@1 0.92~0.96 / 0.375)라 개선 여력이 작다. 요약의 효과를
  이 셋으로 측정하는 것은 바닥효과/천장효과에 갇힌다.
- 사람이 판단한 정밀도(precision)는 측정하지 않았다. 공고 단위 정답이 같은 법안명 5건 경합 때문에
  본질적으로 모호한 것은 메모리 20 §3과 동일.
- 코퍼스 1개, 모델 1개(KURE-v1), 시점 1개(2026-10-11) 실측이다. `LAWCAST_SEMANTIC_MODEL` 교체 시
  재측정 필요.

## 8. 라이브 승격 기록 (2026-10-11)

실측 아티팩트 세트를 호스트 라이브 `artifacts/`로 승격하고 실제 HTTP 인터페이스로 확인했다.

- **롤백 세트**: `artifacts/backup-pre-ai-summary/` (96,646청크, fingerprint `2c3e03179db0`,
  id_map `updated_at` 2026-10-10T09:39:22Z). 되돌리려면 이 네 파일을 `artifacts/`로 다시 복사한다.
- **승격**: `embeddings.npz` → `id_map.json` → `faiss.index` → `chunks.jsonl` 순서로 각 파일을
  tmp 이름으로 복사한 뒤 `mv`(rename). `chunks.jsonl`을 마지막에 두는 것은 파이프라인
  `_write_artifacts`의 커밋 지점과 동일한 순서다. 승격 후 라이브 = 117,718청크,
  fingerprint `7d8b7ff5da85`, id_map `updated_at` 2026-10-11T13:45:45Z.
- **검증(HTTP, 실제 사용 인터페이스)**: 사이드카를 문서화된 CMD로 기동 → `/health`
  `{status: ready, device: mps, indexedChunks: 117718, generation: 1, maxK: 200}`,
  `POST /reload` → `generation: 2`, `reloadError: null` (핫 리로드 경로가 승격 세트에서 통과).
  gist 질의 3종(`저출산 대응 지원`, `여성 창업 지원`, `전세사기 피해자 지원 확대`)이 모두
  `[AI 요약]` 청크를 1위로 반환. 요약 텍스트 질의 5건 before(롤백 세트)→after(라이브 HTTP)
  순위: `없음→1`, `5→1`, `1→1`×3, **악화 0/5**.
  계약 검증: 공백 질의 400, `k=0`/`k=201`/질의 501자 422 (불변). 스케줄러 틱은 미발생(`index update` 0줄).

### 8.1 **CRITICAL**: 아티팩트는 호스트 공유, 컨테이너 코드는 이미지 고정 — 축소 가드는 막지 못한다

`docker-compose.yml`은 `./semantic-search/artifacts:/app/artifacts`를 **rw로 바인드**한다 — 즉
승격한 디렉터리가 프로덕션 컨테이너가 서빙하는 그 디렉터리다(지금은 Docker 데몬이 내려가 있어
서빙 중인 인스턴스가 없고, 배포·재시작은 하지 않았다).

두 상태가 어긋날 때의 동작은 **실측**했다(라이브 아티팩트를 상대로 `plan_update` plan-only — 쓰기 0회):

```
old-code (no summary join)   to_embed=     0 reused= 96646 dropped_rows= 21072 deleted_notices=  0 has_changes=True  shrink_refused=False
new-code (summary join)      to_embed=     0 reused=117718 dropped_rows=     0 deleted_notices=  0 has_changes=False shrink_refused=False
```

- **구 이미지 + 새 아티팩트**: 요약 청크 21,072행이 `dropped_chunk_rows`로 계획되는데
  `deleted_notices=0`이라 `_shrink_refused`는 **False**다. `_shrink_refused`는 삭제율을 **공고 수**
  기준으로 계산한다(`deleted * 5 > old_notices`) — 405건 폴백 → 요약 교체 케이스처럼 **공고는 남고
  청크만 사라지는 변경은 가드 대상이 아니다**. `has_changes=True`이므로 `_tick`은 그대로 `_apply`하고
  **아티팩트 세트를 96,646청크로 되돌려 요약 벡터를 전부 지운다**(재임베딩 0이므로 빠르고 조용하다).
- **탐지 범위**: DB는 건드리지 않는다(엔진은 `notice_archives`를 쓰지 않음) — 공고·데이터 손실은 없다.
  그러나 다음 새 코드 틱이 요약 21,072행을 다셔 재임베딩해야 한다(약 11분, 컨테이너 CPU면 더 길다).
  그동안 gist 질의는 baseline으로 회귀한다.
- **정정**: 이 문서 초판은 "축소 가드가 거부해서 인덱스가 안전하다"고 적었는데, 그 추정은 **틀렸고**
  위 표가 그것을 반증한다. 가드는 공고 삭제만 보고 청크 행 삭제는 보지 않는다.

**따라서 순서가 강제된다**: 코드 릴리스(버전 범프 + PR + 태그) → 컨테이너 재빌드/재배포
(`./deploy.sh semantic-search`) **후에** 스택을 기동한다. 코드 배포가 지연된다면, 구 이미지가 도는
동안에는 승격본이 아니라 `artifacts/backup-pre-ai-summary/`(구 코드와 정합)를 두는 편이 안전하다.

부수 확인(이 변경이 만든 것이 아님): 백엔드에 `section` 허용 목록은 없다(타입만 `string | null`),
프런트 `sectionLabel`은 `body` 외 값을 그대로 표시하므로 `AI 요약` 칩이 추가 UI 변경 없이 뜬다.
`source_deleted` 878행은 여전히 인덱스에 포함된다(메모리 20 §5-3의 기존 과제, 이제 요약까지 포함).

## 9. 남은 작업

- 권고: **채택 유지**(저비용·무회귀·새 능력). 요약 청크는 "같은 공고의 다른 표현"이므로 공고 단위
  dedup이 이미 완충하고, 남는 비용은 gist 질의에서 요약끼리 경쟁하는 정도다.
- 후속 후보: (a) 백엔드 over-fetch 성장 루프가 창 압박을 흡수하는지 확인, (b) §5-1 어휘 재랭크와
  결합 시 gist 질의 이득이 유지되는지 측정, (c) `source_deleted` 878건 필터(메모리 20 §5-3)와 함께
  재측정.
- **커밋/버전 범프/PR·릴리스·컨테이너 재배포는 미실시.** AGENTS.md 릴리스 워크플로를 따른다면 새
  기능이므로 `semantic-search/pyproject.toml` minor 범프 + 태그가 필요하고, §8.1 때문에 **이미지가
  새 코드를 갖도록 재배포해야 자동 갱신이 재개된다**.
- `artifacts/exp-ai-summary/`(약 1.6GB, gitignored)는 이제 라이브와 동일한 사본이라 삭제 가능.
  롤백 세트는 `artifacts/backup-pre-ai-summary/`로 보존.
