# Agent Memories

이 폴더는 코딩 에이전트(GitHub Copilot, Claude Code, Codebuff 등)가 프로젝트를 이해하고 작업하면서 남긴 탐색 기록, 조사 결과, 구현 계획 등을 보관합니다.

## 폴더 구조

```
agent_memories/
├── README.md                                      ← 이 파일 (인덱스)
├── repo/                                          ← 프로젝트 전반 공유 노트 (에이전트 무관)
│   ├── backend-testing-notes.md                   ← 백엔드 테스트 주의사항 및 버그 패턴
│   ├── frontend-notes.md                          ← 프론트엔드 개발/테스트 주의사항
│   └── code-comment-convention-notes.md           ← 코드/주석 컨벤션 적합성 심사 기준 및 판단 기록
├── 01-project-exploration-and-discussion-plan/    ← 탐색 및 토론 시스템 계획
│   ├── lawcast-backend-exploration.md             ← 백엔드 아키텍처 탐색 결과
│   ├── lawcast-frontend-exploration.md            ← 프론트엔드 아키텍처 탐색 결과
│   └── plan.md                                    ← 법률안 토론/댓글 시스템 구현 계획
├── 02-security-bugs-and-pagination/               ← 보안/버그 조사 및 페이지네이션
│   ├── bug-investigation-findings.md              ← 인용 알림 모달 & CF IP 포워딩 버그
│   ├── security-audit-unbounded-requests.md       ← 보안 감사 (요청 경계 검증)
│   ├── pagination-audit-findings.md               ← 페이지네이션 현황 감사
│   └── pagination-implementation-plan.md          ← 커서 기반 페이지네이션 구현 계획
├── 03-quote-notification-plan/                    ← 스레드 인용 알림 구현
│   └── plan.md                                    ← 인용 알림(웹푸시 바인딩) 구현 계획
├── 04-snippet-state-shadowing-bug/                ← 스니펫/상태 변수명 충돌 버그
│   └── bug-investigation-findings.md              ← NewThreadModal 토론 주제 입력 검증 버그 원인 분석
├── 05-webpush-failure-cleanup-audit/              ← 웹푸시 실패 처리/정리 크론 감사
│   └── bug-investigation-findings.md              ← 일시 오류 구독 삭제 + 웹훅 정리 게이트 버그
├── 06-semantic-search-side-project/               ← 시맨틱 검색 사이드 프로젝트
│   └── plan.md                                    ← FAISS 의미 검색 파이프라인 설계 및 모델 선정
├── 07-incremental-indexing/                       ← 시맨틱 인덱스 증분 갱신
│   └── plan.md                                    ← 증분 갱신 설계 결정 및 검증 결과
├── 08-semantic-search-production-deploy/          ← 시맨틱 검색 프로덕션 배포/백엔드 연동
│   ├── plan.md                                    ← 배포 로드맵, API 계약, 남은 작업 목록
│   ├── incremental-update-pipeline-design.md      ← 정기 인덱스 갱신 파이프라인 설계 (설계 소유처)
│   └── production-readiness-status.md             ← 프로덕션 레디니스 3축 현황 + 남은 작업 (측정 기반)
├── 09-embedding-map-web-ui/                       ← 임베딩 맵 웹 UI (시맨틱 검색 시각화 도구)
│   └── plan.md                                    ← 설계 결정, 줌 플리커 패치(2회), 전체 데이터 모드
├── 10-index-last-update-tracking/                 ← 시맨틱 인덱스 마지막 업데이트 시각 표시
│   └── plan.md                                    ← 갱신 경로 분석, 단일 소유자 시각 스탬프 설계·검증
├── 11-api-version-fallback-stamp/                 ← /api/version 0.0.1 프로덕션 버그 원인 분석
│   └── bug-investigation-findings.md              ← compose 하드코딩 기본값(0.0.1)이 버전을 덮어쓰던 버그와 패치
├── 12-cron-env-compose-override/                  ← 크론 환경변수 미주입 프로덕션 버그
│   └── bug-investigation-findings.md              ← compose `environment`가 `env_file`을 덮어쓰던 버그와 패치└── 13-sidecar-concurrency-audit/              ← 시맨틱 검색 사이드카 동시성 감사
    └── sidecar-concurrency-analysis-and-tests.md  ← 사이드카 구조 분석·블로킹 구간 감사·동시성 테스트 실측
├── 14-relevance-tier-search/                  ← 시맨틱 검색 관련도 계층화
│   └── plan.md                                    ← 2임계값 3계층 설계, 키워드 폴백 제거 계약, $state.raw 함정
├── 15-citizen-ux-feedback/                      ← 시민 접근성 UI/UX 피드백
│   └── citizen-ux-feedback.md                     ← "일반 시민의 쉬운 법률안 접근" 목표 대비 UI/UX 전수 분석
├── 16-notion-admin-notices/                     ← Notion 기반 관리자 공지 게시판
│   └── plan.md                                   ← Notion 필드/공개 필터·정렬·캐시·오류 계약, 검증 증거
├── 17-ssr-payload-minimization/                  ← SSR 최소 페이로드 감사·리팩터링
│   └── ssr-minimal-payload-audit.md              ← 로드↔사용 전수 비교 표, 카드 뷰 트림·실측 증거
├── 18-node-build-stale-artifact/                 ← 프로덕션 `node build/index.js` 누락 원인 분석
│   └── bug-investigation-findings.md             ← 어답터 전환 후 build/ 미갱신 + PUBLIC_* 런타임 env 버그와 패치
└── 19-change-notification-exclusion/             ← diffchain 백필 이벤트 알림 제외 계획
    └── plan.md                                   ← 소스 8종 알림 후보 분류(Tier A/B/C), dispatch 게이트 설계, isDoneSync 폭주 가드
```

## 폴더별 상세 내용

### `repo/` — 프로젝트 전반 공유 노트

모든 에이전트가 참고해야 하는 프로젝트 전반의 주의사항입니다.

- **backend-testing-notes.md**: 백엔드 테스트 작성/실행 시 주의사항. CacheService mock 패턴, Redis 키 관리, diffchain 해시 규칙, immutable snapshot 계약, NSM/PAL 라우팅, 프로덕션 버그 패턴(7건 이상의 발견/수정 기록 포함).
- **frontend-notes.md**: 프론트엔드 개발 주의사항. Svelte runes 사용법, Playwright e2e 테스트 패턴, 모의 데이터 처리, data-testid 사용법.
- **code-comment-convention-notes.md**: 코드/주석 컨벤션 적합성 심사(2026-10-07) 기록. 영문 주석 전환 범위, 한국어 식별자/데이터 인용은 허용이라는 판단 기준, 이모지 규칙의 제품 문자열 예외, `lc-` 접두사 개명 내역, `.util.ts` vs `.utils.ts` 네이밍 충돌(미해결), 컨벤션 리팩터 검증 게이트.

### `01-project-exploration-and-discussion-plan/` — 초기 탐색 및 토론 시스템 계획

- **lawcast-backend-exploration.md**: NestJS 아키텍처, TypeORM 엔티티 구조, 컨트롤러 라우트, 보안 유틸리티, 프록시/IP 처리, 모듈 패턴 등 백엔드 전반의 탐색 결과.
- **lawcast-frontend-exploration.md**: SvelteKit 라우팅, 데이터 로딩 패턴, 컴포넌트 구조, 스타일링 패턴, API 클라이언트 아키텍처, 상세 페이지 구조 등 프론트엔드 전반의 탐색 결과.
- **plan.md**: 나무위키 스타일 토론/댓글 시스템의 5단계 구현 계획.

### `02-security-bugs-and-pagination/` — 보안/버그 조사 및 페이지네이션

- **bug-investigation-findings.md**: 인용 알림 버튼이 모달을 열지 못하는 원인 분석, Cloudflare Pages SSR에서 잘못된 IP가 기록되는 원인 분석.
- **security-audit-unbounded-requests.md**: 요청 경계 검증 감사 결과. noticeNums 무한 배열, 검색 쿼리 무제한, 날짜 범위 미검증 등 보안 취약점 분석.
- **pagination-audit-findings.md**: 현재 API 엔드포인트의 페이지네이션 현황, 인덱스 구조, 커서 기반 전환 준비도 분석.
- **pagination-implementation-plan.md**: 커서 기반 페이지네이션 4단계 구현 계획 (ChangeTracking → Archive → Search 순서).

### `03-quote-notification-plan/` — 스레드 인용 알림

- **plan.md**: 토론 인용 알림 시스템 구현 계약. 웹푸시 바인딩 매핑 테이블, 인용 해석 유틸, 알림 발송 흐름, 프론트 동의 모달 구현 계획.

### `04-snippet-state-shadowing-bug/` — 스니펫/상태 변수명 충돌 버그

- **bug-investigation-findings.md**: `NewThreadModal`에서 `{#snippet title()}`와 `let title = $state('')` 이름 충돌로 `bind:value`가 스니펫 함수를 참조하여 토론 주제 입력 검증이 항상 실패하던 버그의 원인 분석 및 수정 기록. **Svelte 스니펫 이름과 상태 변수 이름은 절대 겹치지 않아야 함.**

### `05-webpush-failure-cleanup-audit/` — 웹푸시 실패 처리/정리 크론 감사

- **bug-investigation-findings.md**: 웹푸시 전송 실패 예외 처리와 삭제 마킹→정리 크론 데이터 흐름 감사. (1) 일시 오류(429/5xx/네트워크) 누적만으로 구독을 무효화·즉시 삭제하던 명세 위반 수정 — 404/410에서만 무효화(RFC 8030/FCM/autopush 기준). (2) 웹훅 정리 크론의 게이트 조건(30일 카운터)과 삭제 조건(14일) 불일치로 삭제 마킹된 웹훅이 2배 늦게 정리되던 버그 수정. 실제 sqlite 데이터 플로우 회귀 테스트 추가 및 사전 패치 코드에서 실패함을 확인.

### `06-semantic-search-side-project/` — 시맨틱 검색 사이드 프로젝트

- **plan.md**: `semantic-search/` (Python + FAISS) 의미 검색 파이프라인 설계. 법률안 `proposalReason` 전처리·청킹 → `jhgan/ko-sbert-sts` 임베딩 → FAISS 코사인 인덱스 → 질의 유사도 검색 4단계 구조와 모델 선정 근거. **중요**: ko-sbert-sts는 max_seq_length=128 토큰이라 청크 200자 캘리브레이션 필수(한국어 ~1.9자/토큰), stage 2의 truncated_count가 가드레일.

### `07-incremental-indexing/` — 시맨틱 인덱스 증분 갱신

- **plan.md**: 전체 재구축 없이 신규/수정/삭제 공고만 반영하는 증분 갱신 설계(`lawcast_semantic/incremental.py` + `scripts/06_incremental_update.py`). 행별 출처 다이제스트(`chunk_text_digests`)로 재사용·크래시 복구를 보증하고 지문 검증 계약은 불변. **설계 결정·검증 결과의 단일 소유처** — 전체 재구축과의 동등성 대조 기록 포함.

### `09-embedding-map-web-ui/` — 임베딩 맵 웹 UI

- **plan.md**: `embedding-map/` 도구의 설계 결정·검증 기록 단일 소유처. 시맨틱 검색 엔진(KURE-v1 + FAISS 93,031 청크)의 학습 데이터 2D 맵 + 검색 쿼리 4단계(임베딩→ANN 후보→스코어링→결과) 추적 UI. 줌 플리커 패치 2라운드(컴포지터 레이어 제거·전역 pinch 가드·반경 버킷링), **`run.py --full` 전체 데이터 모드**(93k 포인트 canvas 렌더링, `/api/chunk/{id}` 레지 툴팁, 18.9MB→1.57MB gzip 페이로드)와 라이브 검증 수치 포함.

### `11-api-version-fallback-stamp/` — `/api/version` 0.0.1 원인 분석

- **bug-investigation-findings.md**: 프로덕션 `/api/version`이 항상 `0.0.1`(`buildEnv: env`)을 반환하던 버그의 원인 분석. `docker-compose.yml`의 `${APP_VERSION:-0.0.1}` 하드코딩 기본값이 CI 밖에서 실행된 `docker compose up`/`./deploy.sh` 컨테이너 재생성 시 실제 버전을 가짜 값으로 도장 찍고, 백엔드 폴백 체인 1순위(env)가 `package.json`보다 우선하던 문제. CI export 검증 로그·부트 파이프라인 타임스탬프 기반 시각선, `${APP_VERSION:-}` 패치와 검증 방법 포함.

### `10-index-last-update-tracking/` — 시맨틱 인덱스 마지막 업데이트 시각

- **plan.md**: 인덱스 갱신 경로 분석(호스트 03/06, 사이드카 틱·부트 리페어가 `VectorIndex.save`로 수렴)과 시각 기록의 단일 소유처. `id_map.json`의 `updated_at` 스탬프(재시작 후 유지) -> `SemanticSearcher.index_updated_at` -> `EngineState.mark_ready/reload` 채택 -> 사이드카 `/search` -> 백엔드 API -> 프론트 "마지막 업데이트" 표시까지 **미션 3단계 전부 구현·검증한 기록**. 틱 결과와 시각의 소유권 분리, 크로스 언어 계약 이중 소유 주의, 레거시 `null`->"기록 없음" 계약 포함.

### `08-semantic-search-production-deploy/` — 시맨틱 검색 프로덕션 배포

- **plan.md**: `semantic-search/` 사이드카의 프로덕션 배포·백엔드 연동 로드맵. 코드베이스 조사 표, 사이드카↔백엔드 API 계약, 완료된 Docker/설정 작업과 남은 작업 우선순위(§3.B 항목은 2026-10-01 기준으로 갱신됨 — 핫 리로드·스케줄링은 구현 완료). **배포 관련 남은 작업의 단일 로드맵.**
- **incremental-update-pipeline-design.md**: 정기 인덱스 갱신 파이프라인 설계 **및 구현의 단일 소유처** — 공유 `lawcast_db` 볼륨(WAL/-shm/uid 처리), 사이드카 내부 스레드 스케줄(기본 60분), load-validate-swap 핫 리로드(`POST /reload`), 부트 리페어·삭제 가드·지문 자가치유 매트릭스. §7 항목 전부 구현됨(2026-10-01).
- **production-readiness-status.md**: 프로덕션 레디니스 **측정 기반 현황 분석**(2026-10-01). ① 엔진 구현 상태 ② 도커 환경(uid 1001 볼륨 마운트·lawcast_db 배선·세 게이트·`POST /reload` 라이브 실측) ③ 백엔드/프론트엔드 대응 상태 3축 정리 + production-ready까지 남은 작업의 '남은 이유·완료 기준' 목록. 최신 실측 기준선.

### `13-sidecar-concurrency-audit/` — 시맨틱 검색 사이드카 동시성 감사

- **sidecar-concurrency-analysis-and-tests.md**: `semantic-search/service/app.py` HTTP 사이드카 구조 분석 + 블로킹 구간 코드 감사(스냅샷 락·백그라운드 로드·비차단 flock 확인)와 `tests/test_concurrency.py` 5개 동시성 테스트 실측치. **측정 함정 4건 기록**: 클라이언트 SSL 컨텍스트의 GIL 경합(~0.42s 측정 오염 → 사전 클라이언트 생성으로 해결), 서브프로세스 `stdout=PIPE` 미소비 데드락, 콜드스타트 기준선 왜곡(2.56s vs 0.11s → 3회 워밍업 + 3라운드 중앙값 필요), HuggingFace Hub 재검증으로 인한 엔진 로드 네트워크 의존성(정상 10s vs 허브 불가 143s → `HF_HUB_OFFLINE=1`로 아웃라이어 제거). **overlap_ratio 분산 계측 귀인(단발 0.56–0.79)**: (a) 콜드 기준선 전체 상승 → ratio 과소(중복 주장 부정확), (b) 동시 배치 wall 편차 → ratio 과대(0.85 임계 플리커), 클라이언트 오버헤드는 `client_delta=0.000s`로 배제 → 3라운드 중앙값(0.65–0.69, 스프레드 0.04) 재보정 + 0.85 마진 근거를 테스트에 문서화. GIL-vs-락 분리: 지연 3.4–4.1x 상승이면서 `max/sum`=0.65–0.69(락이면 ~1.0) → GIL/CPU 포화 증거.

### `14-relevance-tier-search/` — 시맨틱 검색 관련도 계층화

- **plan.md**: 검색 결과를 코사인 유사도 2임계값(`LAWCAST_SEMANTIC_MIN_SIMILARITY` 0.25 / `LAWCAST_SEMANTIC_CLEAR_SIMILARITY` 0.45)으로 명확/약한/무관 3계층으로 분리한 크로스 스택 설계 — 엔진 `search_tiered` → 사이드카 `weakResults` → 백엔드 통과 → 프런트 빈 결과 화면의 reveal 버튼. **CRITICAL**: 무결과 키워드 폴백 제거(무관 쿼리는 반드시 빈 결과), 크로스 언어 계약(`semantic-search.contract.spec.ts`) 양쪽 동시 수정 규칙, Svelte 5 `$state` 프록시 identity 함정(`$state.raw` 필요), 로더 단순화(f4b2ee2) 이후 깨진 로딩 e2e 3건(사전 존재) 기록.

### `15-citizen-ux-feedback/` — 시민 접근성 UI/UX 피드백

- **citizen-ux-feedback.md**: 핵심 목표 "일반 시민의 쉬운 법률안 접근" 대비 프론트엔드 UI/UX 전수 분석(홈/목록/상세/의미 검색/알림 여정 + 코드 근거 + 모의 실행 화면 확인). **CRITICAL 3대 결론**: ① 참여 동선 부재(의견 제출 CTA 없음) ② D-day/마감 기한 부재 ③ 전문용어 무설명 + "증거 수집 플랫폼" 프레이밍. 문제점 P1~P16을 근거 라인과 함께 기록하고 우선순위별 개선 제안(P0~P3) 정리. 2차 패스에서 의미 검색/웹훅/토론 화면 실탐색 + WCAG 대비율 실측(라이트 3건·다크 1건 AA 미충족) 반영.

### `16-notion-admin-notices/` — Notion 관리자 공지 게시판

- **plan.md**: Notion 데이터베이스 필드 계약(`제목`/`공개 여부`/`상태`/`노출 순서`/`내용`), `GET /api/announcements` 응답/설정(`NOTION_API_KEY`, `NOTION_DATABASE_ID`, `NOTION_API_URL`, `NOTION_TIMEOUT`, `NOTION_CACHE_TTL_MS`, `NOTION_MIN_REQUEST_INTERVAL_MS`) 계약, 60초(기본) 캐시·스냅샷 서빙·503 실패 계약, Notion 레이트리밋 방어(single-flight·340ms 페이싱·429 Retry-After 백오프, 스텁 실측 증거), `긴급` 체크박스 → 사이트 전체 긴급 배너(헤더 하단) 계약, 프론트 메인 최상단 고정 공지 배선, CRUD는 Notion 전용(  단일 GET 라우트 스펙으로 방어) 기록 + 검증 증거.

### `17-ssr-payload-minimization/` — SSR 최소 페이로드 감사·리팩터링

- **ssr-minimal-payload-audit.md**: 15개 서버 로더 전수에 대한 "로드된 키 ↔ 실제 사용 필드" 비교대조 표와 카드 뷰(`NoticeCard`/`DiscussionThreadCard`/`NoticeChangeCard`/`AdminNoticeCard`) 트림 기록. `lib/server/ssr-cards.ts` 매퍼가 필드 목록의 단일 소유처, `/api/announcements/top` 응답을 `id`·`title` 캡-1 뷰로 축소, 홈 stats 4,318→128B·변경목록 6,142→2,018B 실측치. **CRITICAL**: 템플릿 grep이 컴포넌트 헬퍼 함수의 필드 접근을 놓침(`isSourceDeleted`→`lifecycleStatus`), 로컬 `data:` 어노테이션 동기화 규칙, 홈/상태 각각 별도 stats 슬라이스 원칙 + 검증 증거(백엔드 885, e2e 255/0).

### `18-node-build-stale-artifact/` — 프로덕션 `node build/index.js` 누락 원인 분석

- **bug-investigation-findings.md**: dev에선 정상·프로덕션에선 대량 누락(``/discussions`` 404 등)의 두 가지 원인 — ① **CRITICAL** 2026-08-15 어답터 전환(43471c6, adapter-node → adapter-cloudflare) 후 `npm run build`가 `.svelte-kit/cloudflare`만 갱신해 `build/`가 8월 14일 아티팩트로 얼어버림(Dockerfile `COPY /app/build`도 함께 깨짐), ② `$env/dynamic/public`(`PUBLIC_*`)이 adapter-node에선 `process.env` 런타임 전용이라 `.env`를 안 읽으면 디스코드 섹션·시맨틱 검색 게이트가 사라짐. 패치: `SVELTE_ADAPTER=node` 듀얼 어답터 + `build:node`/`start:node`(`--env-file-if-exists`) 스크립트 + Dockerfile `ENV`·CMD 수정. **검증**: 10개 라우트 전부 200, 홈 텍스트 prod==dev 1,427자 0 word diff, lint/check 통과. 함정: 순수 `npm run build`는 여전히 cloudflare 출력(=build/ 미갱신), dev/prod HTML 바이트 비교 금지(dev는 CSS 116KB 인라인), `/api/announcements/top` 배포 순서(백엔드 먼저).

### `19-change-notification-exclusion/` — 백필 이벤트 알림 제외 계획

- **plan.md**: diffchain 변경 이벤트 8개 소스에 대한 **알림 제외 후보 분류와 제외 로직 설계의 단일 소유처**. 측정 기반 근거(`lawcast.db` 이벤트 분포: isDoneSync 19,424 / updateNsmHtmlAndDetail 203 / upsert isDone 플립 0건), Tier A 제외 대상(`archive:updateNsmHtmlAndDetail`, `archive:likmsProposalReason` — 백필 파이프라인 + 재시도 경로의 이중 알림 증거), Tier B 보류(isDoneSync 마감 알림 전채널 ⇒ 전면 제외 금지, 2026-08-10 하루 17,224건 폭주 ⇒ 런 단위 가드), **CRITICAL**: 제외는 `dispatchChangeNotification` 게이트에서만 — 이벤트 append/요약 재생성/체인 감사엔 절대 손대지 않는다.

## 에이전트 메모리 기록 규칙

1. **파일명**: `영문-하이픈-이름.md` (예: `pagination-implementation-plan.md`)
2. **제목**: `# 주제` (Markdown H1)
3. **구조**: 섹션별 H2/H3 사용, 코드 블록으로 관련 파일 경로/함수명 명시
4. **언어**: 기술 문서는 영문 우선, 사용자 대상 설명은 한국어 허용
5. **파일 경로 표기**: 상대 경로 사용 (예: `backend/src/modules/...`)
6. **중요도 표기**: `**CRITICAL**`, `**URGENT**`, `**HIGH**` 등 볼드로 강조

## 새로 메모리를 추가할 때

### 언제 메모리를 만드는가

| 상황                                           | 저장 위치                        | 예시                                   |
| ---------------------------------------------- | -------------------------------- | -------------------------------------- |
| 프로덕션 버그 또는 원인 분석 완료              | 보안/버그 폴더 또는 새 세션 폴더 | `bug-investigation-findings.md`        |
| 보안/성능 감사 완료                            | 보안/버그 폴더 또는 새 세션 폴더 | `security-audit-unbounded-requests.md` |
| 새 기능 구현 계획 수립 완료                    | 새 세션 폴더                     | `plan.md`                              |
| 프로젝트 아키텍처 탐색 완료                    | 새 세션 폴더                     | `lawcast-backend-exploration.md`       |
| 모든 에이전트가 알아야 할 전범위 주의사항 발견 | `repo/`                          | `backend-testing-notes.md`             |

**메모리를 만들지 않는 경우:**

- 소스 파일 내 주석이나 TODO로 충분할 때
- 단순 오타나 포맷 수정일 때
- 기존 메모리에 이미 동일 내용이 있을 때 (기존 파일 업데이트)

### 폴더 네이밍 규칙

세션 폴더 형식: `{NN}-{descriptive-english-name}/`

- **`NN`**: 두 자리 영문 숫자 (예: `01`, `02`, `03`)
- **`descriptive-english-name`**: 소문자 하이픈 구분 주제명
- 최대 ~5단어; 구체적이고 간결하게

**예시:**
| Good | Bad |
|-----------|------------|
| `01-project-exploration-and-discussion-plan/` | `notes/` |
| `02-security-bugs-and-pagination/` | `temp/` |
| `03-quote-notification-plan/` | `copilot-session-2026-09-14/` |
| `04-api-rate-limiting/` | `backend/` (실제 백엔드 디렉토리와 혼동) |

**`repo/` 폴더**: 모든 에이전트가 참고할 전범위 노트 전용. 번호 매긴 하위 폴더를 만들지 않음.

### 파일 네이밍

- 형식: `영문-하이픈-이름.md` (예: `pagination-implementation-plan.md`)
- 파일당 하나의 주제; 500줄 이상이면 분리
- 세션 폴더에 저장 (번호-영문-설명/)
- 전범위 노트는 `repo/` 에 저장

### 필수 업데이트

**반드시 이 README.md의 목차를 업데이트하세요.** 새 폴더를 만들었으면 해당 폴더 설명도 추가합니다.
