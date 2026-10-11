# AI 요약 인덱싱 최종 검증 + 프로덕션 레디니스 점검

2026-10-12 기준, 세션 24에서 구현한 `ai_summary` 인덱싱(과 세션 25의 게이트/리포트)에 대해
**성능 향상의 유효성·초기 구축/증분 포함 여부·프로덕션 레디니스**를 현재 호스트 상태에서 다시 측정한 기록.
모든 수치는 같은 날 라이브 아티팩트(21,177공고 / 117,718청크, fingerprint `7d8b7ff5da85`,
`updated_at 2026-10-11T13:45:45Z`)에서 재현한 값이다.

## 1. 결론

| 질문 | 판정 | 핵심 근거 |
| ---- | ---- | -------- |
| 1) 요약 인덱싱이 유효한 성능 향상인가 | **예(재현됨)** | 요약 어휘 질의 miss **33.7% → 0.0%** (hit@1 0.407 → 0.990), 자연 질의 61건 **불변** |
| 2) 초기 인덱스 구축에 요약이 포함되는가 | **예** | `01 --db`가 21,072요약청크를 만들고 라이브 `chunks.jsonl`과 **바이트 동일** |
| 3) 기존 인덱스 증분 갱신에 요약이 포함되는가 | **예** | 라이브 plan 멱등(`to_embed 0`), 요약 없는 세트 plan은 `to_embed 21,072 / dropped 0` |
| 4) 프로덕션 레디 상태인가 | **아니오 (BLOCKER 있음)** | 요약 기능이 **커밋되지 않았고**(HEAD=v2.4.0에 0건) 릴리스 코드는 이 아티팩트를 **되돌린다** |

## 2. 실측

### 2.1 초기 인덱스 구축 — 요약 포함 확인

```bash
cd semantic-search && .venv/bin/python scripts/01_preprocess_chunk.py --db ../backend/lawcast.db \
  --out /tmp/chunks-verify.jsonl
```

```
notices read        : 21177
chunks created      : 117718          (2.1초, 순수 파이썬 청킹)
chunk chars         : mean=120 min=1 max=230
sections detected   : {'body': 3778, 'AI 요약': 21072, '제안이유': 15931,
                       '제안이유 및 주요내용': 56260, '주요내용': 18685, '참고사항': 1895,
                       '제안이유 및 주요 내용': 85, '제안 이유': 3, '주요 내용': 9}
```

- `grep -c '"section": "AI 요약"'` = **21,072**, 총 117,718행.
- `cmp -s /tmp/chunks-verify.jsonl artifacts/chunks.jsonl` → **IDENTICAL**. 즉 라이브 인덱스는
  DB + 현재 코드의 전체 재구축 결과와 정확히 같다(요약이 "어딘가에 섞여 있을 뿐"이 아니라 동일).
- 최장 청크 230자 → KURE-v1 8192토큰 윈도우에서 절단 위험 없음.

### 2.2 증분 갱신 경로 — 두 방향 모두 확인 (읽기 전용 plan)

```bash
# 라이브 세트 기준 (현재 코드 + 현재 DB)
.venv/bin/python scripts/06_incremental_update.py --db ../backend/lawcast.db --plan-only
# 요약 없는 롤백 세트 기준
.venv/bin/python scripts/06_incremental_update.py --db ../backend/lawcast.db --plan-only \
  --chunks artifacts/backup-pre-ai-summary/chunks.jsonl \
  --embeddings artifacts/backup-pre-ai-summary/embeddings.npz \
  --index artifacts/backup-pre-ai-summary/faiss.index \
  --id-map artifacts/backup-pre-ai-summary/id_map.json
```

| 기준 아티팩트 | to_embed | reused | dropped | deleted_notices | has_changes |
| ------------- | -------- | ------ | ------- | --------------- | ----------- |
| 라이브(요약 포함, 117,718) | 0 | 117,718 | 0 | 0 | **false** |
| 롤백(요약 없음, 96,646) | **21,072** | 96,646 | **0** | 0 | true |

- 라이브: **멱등** — 현재 코드가 DB로부터 만드는 집합과 서빙 중인 집합이 같다(요약 행 21,072개가
  `reused`에 포함된다). 첫 스케줄 틱은 no-op이다.
- 롤백 세트: 요약 행을 **순수 추가**로 계획한다(`to_embed 21,072 / dropped 0`) — 증분 갱신이
  요약을 포함하며, 본문 청크는 하나도 건드리지 않는다.

### 2.3 성능 A/B — 실모델·실아티팩트 재측정

`_workspace/ai_summary_ab.py`(세션 24 하니스, KURE-v1 + FAISS, 서빙 창 200청크)를 두 세트에 대해
다시 실행. `before` = 롤백 세트(96,646), `after` = 라이브(117,718).

| 지표 | before | after | 판정 |
| ---- | ------ | ----- | ---- |
| 자연 시민 질의 24건 | 0.958 / 1.000 / 1.000, MRR 0.979 | **동일** | 불변 |
| 뉴스 의제 질의 37건 | 0.946 / 0.946 / 1.000, MRR 0.959 | **동일** | 불변 |
| 요약 어휘 질의 300건 (B1, self-match 포함) | hit@1 0.407 / hit@5 0.510 / **miss 0.337** / MRR 0.452 | hit@1 **0.990** / hit@5 **1.000** / **miss 0.000** / MRR 0.995 | **새 능력** |
| 같은 질의, 자기 요약 청크 마스킹 (B2, dilution) | 0.407 / 0.510 / miss 0.337 (= B1, 요약 청크가 없음) | hit@1 **0.307** / hit@5 0.447 / miss **0.400** | **비용 −0.093** |

- **개선의 실체**: before에서 요약 어휘 질의의 33.7%는 **자기 공고조차 도달하지 못했다**(B1 miss).
  after에서는 0%다. 반대로 기존 자연 질의 지표는 천장(0.95~1.00)이라 움직이지 않는다.
- **비용의 실체**: 자기 요약을 가리면 hit@1이 0.093 떨어진다(다른 공고의 요약 벡터와 경쟁).
- rank-1 청크의 섹션 분포: after의 B1 hit@1 300건 중 **297건이 `AI 요약` 청크**(self-match의 정의상
  당연), 자연 질의에서는 citizen24 4/24 · news37 8/37이 요약 청크로 1위 → 자연 질의도 요약을 쓴다.
- 2026-10-11 세션 24의 최초 측정치와 **소수점까지 동일**하게 재현됐다(아티팩트가 그대로이기 때문).

### 2.4 HTTP 인터페이스 (실사용 경로)

문서화된 CMD로 기동(`uvicorn service.app:app`, 스케줄 off·DB_PATH 빈 값):

```
GET /health → {"status":"ready","model":"nlpai-lab/KURE-v1","device":"mps","indexedChunks":117718,
               "lastUpdateAt":"2026-10-11T13:45:45.301465+00:00","generation":1,"maxK":200}
GET /search?query=저출산 대응 지원&k=5
  1. [AI 요약] score=0.6814 모자보건법 일부개정법률안
  2. [AI 요약] score=0.6715 남녀고용평등과 일·가정 양립 지원에 관한 법률 일부개정법률안
  3. [AI 요약] score=0.6666 모자보건법 일부개정법률안
  4. [AI 요약] score=0.6626 주거기본법 일부개정법률안
  5. [AI 요약] score=0.6596 아동복지법 일부개정법률안
GET /search?query=%20%20&k=5 → 400   (공백 질의 가드)
GET /search?query=세금&k=0   → 422
GET /search?query=세금&k=201 → 422
GET /search?query=전세사기 피해자 지원 확대&k=200 → 200청크 / 55개 서로 다른 공고 / 1위가 [AI 요약]
```

- 사이드카는 `/search`가 **GET**이다(테스트 중 POST로 두드려 405를 만났다 — 아래 §5).
- 검증 후 프로세스를 종료했고, 그 과정에서 아티팩트는 **쓰기 0회**(id_map `updated_at` 불변).

### 2.5 위험 재검증 — 릴리스 코드가 이 아티팩트를 되돌린다

릴리스된 코드(HEAD=`837e077`=v2.4.0, `SUMMARY_SECTION`·`ai_summary` 0건)가 보는 코퍼스로 plan을
계산했다(`strip_derived`로 요약 필드 없는 레코드를 만들어 정확히 같은 입력을 재현):

```
released-code plan vs LIVE artifacts:
  to_embed=0 reused=96646 dropped_rows=21072 deleted_notices=0 added=0 records_changed=True
  has_changes=True shrink_refused=False
```

- 요약 청크 21,072행이 `dropped`로 계획되고 **삭제된 공고는 0건**이라 축소 가드는 열려 있다
  (`shrink_refused=False`) → 다음 틱이 그대로 적용해 요약 벡터를 전부 지운다(재임베딩 0이라 조용하고
  빠르다). 세션 24 §8.1의 기록을 **현재 라이브 아티팩트로 재확인**한 것이다.
- 복구 비용: 재임베딩 21,072행(호스트 MPS 약 11분, 컨테이너 CPU는 더 길다), 그동안 gist 질의 회귀.

## 3. 프로덕션 레디니스 판정

**BLOCKER 1 — 요약 기능이 커밋되지 않았다.** 워킹트리에만 존재한다(`lawcast_semantic/chunking.py`,
`datasource.py` 등 M 상태, `tests/test_chunking.py` 등). semantic-search HEAD는 v2.4.0이며
`SUMMARY_SECTION`·`ai_summary` 참조가 0건이다. 즉 **지금 이미지를 빌드/재배포하면 요약을 모르는 코드**가
되고, 라이브 아티팩트와 어긋나 §2.5의 사고가 자동 발생한다. 필요한 순서:

1. semantic-search 버전 **minor 범프**(2.4.0 → 2.5.0, 새 기능) + 커밋 + PR + 태그
   (`git tag -l 'semantic-search-v*'`에 충돌 없음 확인).
2. 컨테이너 재빌드·재배포(`./deploy.sh semantic-search`) **후에** 아티팩트가 정합. 배포가 지연되면
   그동안은 라이브 대신 `artifacts/backup-pre-ai-summary/`(구 코드와 정합, 96,646청크)를 두는 편이 안전.
3. 배포 후 확인: `scripts/07_capability_report.py --compare <배포 전 기준선>`이 `OK`/exit 0,
   `06 --plan-only`가 `has_changes false`, 스케줄 틱 로그에 `index update:` 변화 없음.

**BLOCKER 2 (조율) — 같은 워킹트리에 다른 스레드의 미커밋 작업이 섞여 있다.** `lawcast_semantic/config.py`,
`service/app.py`, `tests/conftest.py`, `tests/test_config.py`, `tests/test_service.py`, `.env.example`
(+181/−16): 사이드카 요청 경계(`MAX_QUERY_LENGTH`/`MAX_K`/`DEFAULT_K`) 기능이고 요약과는 무관하다.
한 PR로 묶을지 분리할지, 그리고 계약 테스트(`backend/src/modules/semantic-search/semantic-search.contract.spec.ts`)가
백엔드 상수와 핀되어 있으니 두 저장소의 동시 수정 여부를 정해야 한다.

**확인된 정상 항목**

- 스케줄 갱신 소스는 **DB**: `service/update_runner.py`의 `_plan_for(config.DB_PATH)` →
  `load_notices_from_db`(요약 조인 포함). compose가 `LAWCAST_SEMANTIC_DB_PATH=/data/lawcast.db`를 주입하고
  `./semantic-search/artifacts:/app/artifacts`를 rw로 바인드한다.
- 백엔드 통과: `semantic-search.service.ts:405`가 `section: chunk.section`을 그대로 반환하고 타입은
  `string | null`(허용 목록 없음) → `AI 요약` 값이 추가 배포 없이 흐른다.
- 프런트: `frontend/src/routes/notices/semantic-search/+page.svelte`의 `sectionLabel(section)`이 값을 그대로
  렌더 → 새 칩 표시에 변경 불필요.
- 첫 스케줄 틱은 no-op(§2.2), 최장 청크 230자 → 절단 0.
- 용량/비용: `embeddings.npz` 373→**454MB**, `faiss.index` 396→**482MB**(+약 167MB, 부팅 메모리 영향),
  재임베딩 21,072행(순수 추가). 이 정도는 부하 테스트로 문제되지 않았으나 컨테이너 메모리 한도 확인 권장.

**미확인 / 불가**

- **Docker 데몬이 실행되지 않아**(OrbStack 소켓 없음) 컨테이너 이미지 빌드·배포·실서비스 환경 검증은
  하지 못했다. §2.4의 HTTP 검증은 호스트에서 스케줄 off로 기동한 로컬 프로세스다(프로덕션 컨테이너 아님).
- 프런트엔드는 이번 변경에 배포가 필요 없다(응답 필드와 칩 렌더 경로가 이미 허용).
- `source_deleted` 878건이 여전히 인덱스에 포함된다(세션 20 §5-3의 기존 과제, 이제 요약까지 포함).

## 4. 재현

```bash
cd semantic-search
# 1) 초기 구축에 요약 포함 (2초)
.venv/bin/python scripts/01_preprocess_chunk.py --db ../backend/lawcast.db --out /tmp/chunks-verify.jsonl
grep -c '"section": "AI 요약"' /tmp/chunks-verify.jsonl && cmp -s /tmp/chunks-verify.jsonl artifacts/chunks.jsonl

# 2) 증분 plan 두 방향 (읽기 전용)
.venv/bin/python scripts/06_incremental_update.py --db ../backend/lawcast.db --plan-only
.venv/bin/python scripts/06_incremental_update.py --db ../backend/lawcast.db --plan-only \
  --chunks artifacts/backup-pre-ai-summary/chunks.jsonl \
  --embeddings artifacts/backup-pre-ai-summary/embeddings.npz \
  --index artifacts/backup-pre-ai-summary/faiss.index \
  --id-map artifacts/backup-pre-ai-summary/id_map.json

# 3) 성능 A/B (~1.5분/세트)
.venv/bin/python ../_workspace/ai_summary_ab.py --label after  --artifacts $PWD/artifacts
.venv/bin/python ../_workspace/ai_summary_ab.py --label before --artifacts $PWD/artifacts/backup-pre-ai-summary

# 4) HTTP 경로
HF_HUB_OFFLINE=1 LAWCAST_SEMANTIC_UPDATE_CRON= LAWCAST_SEMANTIC_DB_PATH= \
  .venv/bin/python -m uvicorn service.app:app --host 127.0.0.1 --port 8399 --log-level warning
curl -s 'http://127.0.0.1:8399/health'
curl -s -G 'http://127.0.0.1:8399/search' --data-urlencode 'query=저출산 대응 지원' --data-urlencode 'k=5'

# 5) 위험 재검증 (릴리스 코드 시야 + 라이브 아티팩트)
.venv/bin/python /tmp/hazard_check.py   # strip_derived(notice) 레코드로 plan_update

# 6) 능력 리포트 (세션 25)
.venv/bin/python scripts/07_capability_report.py --db ../backend/lawcast.db --save /tmp/cap-before.json
.venv/bin/python scripts/07_capability_report.py --db ../backend/lawcast.db --compare /tmp/cap-before.json
```

## 5. 한계 / 주의

- 성능 수치의 B1은 **self-match 천장값**이다(질의 텍스트가 인덱스에 그대로 있다). 신뢰할 수 있는 부분은
  **before의 miss 0.337**과 B2의 델타다.
- 코퍼스 1개·모델 1개(KURE-v1)·시점 1개(2026-10-12 라이브, 2026-10-11 승격) 기준이다. 모델 교체나
  코퍼스 재추출 시 재측정이 필요하다.
- 이번 검증은 아티팩트 세트 **2개**를 **같은 코드**로 서빙한 비교다(코드 교체 실험이 아니다). 코드
  버전 차이의 영향은 §2.5의 plan 증거로만 판단했다.
- 사이드카 `/search`는 **GET**이며 쿼리 파라미터는 `query`·`k`다. POST로 두드리면 405(계약 위반이 아니라
  사용 오류). 테스트를 쓸 때 이 점을 기억할 것.
- Docker 검증 불가(§3)와 커밋·릴리스 미실시가 이 문서의 가장 중요한 미완이다.

## 6. 후속 — 배포 완료 (2026-10-12)

§3의 BLOCKER는 모두 해소됐다. 이 절이 §3의 판정을 대체한다.

- **사전 조치(사용자)**: 요약이 학습된 아티팩트를 프로덕션 서버에 수동 반영. 즉 §2.5의
  "릴리스 코드가 라이브 아티팩트를 되돌린다" 위험은 배포 전에 서버 아티팩트를 새 코드와 맞추는 방식으로 제거됐다.
- **semantic-search v2.5.0** (PR #11, squash `da6c0be`, 태그·릴리스 `semantic-search-v2.5.0`): 요약 인덱싱 +
  요청 경계(`LAWCAST_SEMANTIC_MAX_QUERY_LENGTH`/`_MAX_K`/`_DEFAULT_K`) + 능력 오라클·`scripts/07`을 한 PR로
  커밋. BLOCKER 2의 "다른 스레드 작업 혼재"는 같은 릴리스로 묶어 처리(요약과 무관하지만 계약 핀 때문에 동시 수정 필요).
- **backend v1.11.0** (PR #194, squash `740410a`, 태그·릴리스 `backend-v1.11.0`): `maxK` 캡 협상 +
  `SEMANTIC_SEARCH_CHUNK_CAP_REFRESH_MS` + 계약 스펙 갱신, 그리고 이전 워킹트리에 남아 있던 diffchain/change-tracking
  가드 스펙을 동봉.
- **가드**: 루트 `deploy-semantic-search.yml`에 능력 릴리스 게이트(baseline → 배포 코드 후보 대조, 손실 시 실패 +
  `allow_capability_loss` 브레이크글래스)가 추가돼, §2.5류 사고는 이제 배포 잡이 차단한다.
- **검증(호스트)**: `ruff` clean, pytest 313 passed, `07 --db ../backend/lawcast.db` exit 0(117,718청크, 지문
  `7d8b7ff5da85`, `derived:ai_summary=21071`); backend `tsc`/build/eslint/prettier clean, `npm test` 913 passed.
- **남은 한계**: 최종 확인은 루트 `main` push가 트리거한 `deploy-semantic-search` 잡(컨테이너 빌드 + 게이트)에서
  이뤄진다 — 로컬 Docker 데몬 없이 호스트에서 검증한 범위는 그대로다.
