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
│   └── bug-investigation-findings.md              ← compose `environment`가 `env_file`을 덮어쓰던 버그와 패치
├── 13-sidecar-concurrency-audit/              ← 시맨틱 검색 사이드카 동시성 감사
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
├── 19-change-notification-exclusion/            ← diffchain 백필 이벤트 알림 제외 계획
│   └── plan.md                                   ← 소스 8종 알림 후보 분류(Tier A/B/C), dispatch 게이트 설계, isDoneSync 폭주 가드
├── 20-semantic-query-quality-eval/              ← 의미 검색 쿼리 후보 평가·적중률 분석
│   └── query-quality-evaluation.md                ← 24개 후보 질의 실측(semantic vs FTS), 정답명 벤치마크, 임계값 캘리브레이션, 개선 방향
├── 21-indexing-boilerplate-stripping/           ← 인덱스 구축 시 섹션 라벨·열거자 제거
│   └── chunk-text-normalization.md                ← 라벨 접두 인식·열거자 제거 설계, 실측 절감(−0.93% 청크·−1.04% 토큰), 오탐 함정 2종, 선행 버그 발견
├── 22-chunk-floor-content-loss/                  ← 청크 하한 필터의 내용 손실 수정
│   └── chunk-floor-content-loss.md                ← 하한 미만 청크 병합·필터 제거, 내용 손실 실측, 회귀 가드 3종
├── 23-embedding-device-autodetect/               ← 임베딩 하드웨어 자동 탐지
│   └── plan.md                                      ← auto 디바이스 탐지(cuda>mps>xpu>cpu) 설계, cpu 폴백 게이트, cpu/mps 실측 2.98x/2.06x, 검증 근거
├── 24-ai-summary-chunking/                        ← AI 요약 청킹 포함 + 검색 품질 A/B
│   └── ai-summary-chunking-measurement.md           ← ai_summary 조인·`AI 요약` 섹션 구현, 405건 title-chunk 회귀와 additive 수정, before/after 실측(요약 질의 miss 33.7%→0%, 기존 지표 불변, dilution −0.10)
├── 25-chunking-capability-gate/                    ← 청킹/파생 필드 능력 회귀 게이트 + 릴리스 리포트
│   └── capability-regression-gate.md                ← 능력 오라클(`capabilities.py`)·게이트 설계, 스왑 회귀 자동 재현(405건), 실패/통과 양방향 검증, `scripts/07_capability_report.py`(릴리스 전후 한 줄 대조·무결성 2종)
├── 26-ai-summary-final-verification/               ← AI 요약 인덱싱 최종 검증 + 프로덕션 레디니스
│   └── readiness-verification.md                    ← 초기 구축/증분 포함 확인(byte-identical·plan 양방향), 성능 A/B 재현(miss 33.7%→0%), HTTP 경로 실측, 릴리스 코드 위험 재검증, **BLOCKER 2건**(미커밋·미배포 역전)
├── 27-capability-guard-backfill-break-glass/        ← 능력 게이트 LOST의 데이터 백필 규명 + 브레이크글라스 배포
│   └── capability-guard-break-glass.md                ← v2.5.0 게이트 실패(title_text 8건 LOST) 원인은 제안이유 백필, v2.4.0/v2.5.0 A/B 동일 손실 증명, allow_capability_loss 재실행으로 배포 완료
├── 28-keyword-semantic-search-integration/          ← /notices 키워드 검색 UI에 의미 검색 통합
│   └── plan.md                                          ← searchMode(auto/keyword/semantic) 설계, 하이브리드 백엔드·프론트 배선, 계약·필터·폴백·검증 계획 + **Phase 1(백엔드)·Phase 2(프론트) 구현 완료** 기록
├── 29-search-ui-persona-audit/                     ← /notices 검색 UI 페르소나 사용성 실측·개선
│    └── usability-audit-and-improvements.md          ← 시민/법조인 관점 실측, 1차 6건 개선(모드 설명·부분집합 고지·0건 회복·칩 설명·예시 검색어) + 2차 한계 재검토 5건(실 백엔드 재측정·온디맨드 키워드 건수·건수 의미 불일치 수정·약한 계층 페이징, 그리고 **예시 검색어 결정화 → 오너 결정으로 되돌림**), SSR 상태 매트릭스·e2e 검증
├── 30-keyword-fts-default/                         ← 키워드 검색 FTS 기본화(제안이유 토글 제거)
│    └── keyword-fts-default.md                       ← `fullText` 파라미터 도메인 제거, FTS5 무조건 적용 + LIKE 부분일치 유지 근거, 캐시 매처 동기화, 실 인덱스 집합 실측(LIKE3 ∪ FTS = API total), e2e 재작성·검증
├── 31-likms-nsm-adapter-integration/               ← pal-crawl 2.3.0 + LikmsNsmAdapter 소스 전환
│   └── likms-nsm-adapter-integration.md             ← `CRAWLING_NSM_SOURCE` 플래그·NSM 포트 어댑터 배선(호출부 무변경), 계류의안 라이브 실측(199/13건), 비의안 행(`ZZ22142`) 차단, 게이트(1010 tests)
└── 32-nsm-ua-block-and-probe-storm/                ← NSM 포털 UA 차단 → 조용한 수집 실패 + 삭제 프로브 폭주
    └── nsm-portal-block-and-probe-storm.md          ← `LawCast/1.0` UA만 5,451B 오류 페이지(브라우저·curl UA는 정상), NSM 수집 2026-09-09 중단, 삭제 프로브가 확정 불가 → 로그 폭주·감지 5주 공백, 후보 약 10,300건/사이클, 킬 스위치 완화
```

## 폴더별 상세 내용

### `repo/` — 프로젝트 전반 공유 노트

모든 에이전트가 참고해야 하는 프로젝트 전반의 주의사항입니다.

- **backend-testing-notes.md**: 백엔드 테스트 작성/실행 시 주의사항. CacheService mock 패턴, Redis 키 관리, diffchain 해시 규칙, immutable snapshot 계약, NSM/PAL 라우팅, 프로덕션 버그 패턴(7건 이상의 발견/수정 기록 포함).
- **frontend-notes.md**: 프론트엔드 개발 주의사항. Svelte runes 사용법, Playwright e2e 테스트 패턴, 모의 데이터 처리, data-testid 사용법, 라우트의 명시적 `data` prop 타입 함정.
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

### `28-keyword-semantic-search-integration/` — 전체 입법예고 검색에 의미 검색 통합

- **plan.md**: `/notices`(전체 입법예고)의 기존 키워드 검색 UI에 의미 검색을 자연스럽게 통합하는 **구현 계획**. **Phase 1(백엔드) 구현 완료(2026-10-12)**: `searchMode`를 `/api/notices/archive`에 추가, `NoticesHybridSearchService`(키워드 패스스루·의미 하이드레이트·폴백·약한 계층·캐시 전용 append·관련도순 페이지네이션) + `NoticeArchiveService.getArchiveNoticesByRankedNums` + `NoticesQueryService.getCacheOnlySearchMatches`. 응답 가산적(`searchMode`/`appliedMode`/`semantic`/항목별 `relevance`), 기본값 keyword(하위호환). 검증: lint·tsc·build·**927 tests/70 suites** 그린. **Phase 2(프론트) 구현 완료(2026-10-13)**: `/notices` 검색 폼에 검색 방식 세그먼트 컨트롤(`자동`/`키워드`/`의미`, 플래그 게이트)과 관련도 칩(`유사도`/섹션/발췌) 추가, `?searchMode=`가 URL·로더·SSR 카드까지 배선(`toNoticeCard`가 `relevance` 이월), `appliedMode==='semantic'`일 때 정렬 슬롯이 관련도순 칩으로 전환, 폴백 배너·약한 계층 공개/숨기기 포함. 모드는 항상 명시적으로 기록(파라미터 삭제 시 플래그 기본값 `auto`로 되돌아가는 버그를 하이드레이션 클릭으로 발견·수정). 기존 `/notices/semantic-search` 진입 버튼(`semantic-search-entry`)은 검색 액션 줄에서 결과 하단 우측 구석(페이지네이션 옆, `PaginationNav` 바깥)으로 이동 — nav 안에 넣으면 `totalPages <= 1`일 때 사라져 빈 결과 케이스 e2e가 깨진다. 검증: `npm run check` 0/0, lint 클린, notices e2e(90개 전수) 89 pass/1 skip, semantic-search e2e 23 pass, SSR 5시나리오 + 하이드레이션 브라우저 클릭 플로우. e2e 스펙(Phase 3)·롤아웃(Phase 4) 미착수. 현재 상태 근거(`/api/notices/archive` → `NoticesQueryService` → `LIKE`/옵션 FTS5, `noticeNum` 정렬·오프셋 페이지네이션, 캐시+아카이브 병합; 의미 검색은 별도 엔드포인트/사이드카). **핵심 설계 결정**: `searchMode`(`auto` 기본/`keyword`/`semantic`)를 기존 `/api/notices/archive`에 추가하고, 새 `NoticesHybridSearchService`가 의미 후보(공개 `MAX_K=50`이 아닌 내부 상한 ~100)를 하이드레이트→필터(날짜/isDone/proposer)→관련도순 페이지네이션. 답변 계약은 가산적(`semantic{...}`, 항목별 `relevance{score,section,excerpt,weak}`), session 14 무결과 키워드 대체 금지·session 20 임계값 노이즈 필터 금지·session 17 SSR 카드 트림 규칙 준수. 캐시 전용(미아카이브) 공고는 키워드 매칭분을 뒤에 append, `source_deleted`는 기존 보존 칩 유지. `/notices/semantic-search` 페이지는 이전 호환용 존치. 6단계 페이즈·검증 매트릭스·미결 결정 6건(D1~D6).

### `30-keyword-fts-default/` — 키워드 검색 FTS 기본화

- **keyword-fts-default.md**: 제안이유 포함 검색 토글을 없애고 키워드 검색이 기본으로 제안이유를 FTS5로 매칭하도록 백엔드(7파일)·프론트엔드(7파일)·e2e를 고친 기록. 설계 판단(FTS만 쓰면 한국어 법률안명 부분일치가 깨져 LIKE 유지, 캐시 매처에 proposalReason 추가), 실 인덱스 집합 실측(`보호`/`임대차`/`국민연금`에서 `LIKE3 ∪ FTS = API total` 일치, `희토류` 0→4, `matchedCacheCount` 근거), 게이트(백엔드 928 테스트·프론트 e2e 253+33), 남은 관찰(중간 부분일치 구멍, `auto` 기본값 재검토, 파라미터 제거에 따른 버전 범프 필요).

### `31-likms-nsm-adapter-integration/` — pal-crawl 2.3.0 + LikmsNsmAdapter 소스 전환

- **likms-nsm-adapter-integration.md**: `pal-crawl` 2.2.0 → 2.3.0 후 새로 추가된 `LikmsNsmAdapter`(국회 의안정보시스템 계류의안)를 기존 NSM 크롤러 자리에 끼워, **호출부 수정 없이** 동일한 NSM 포트(`INsmListCrawler`/`INsmDetailCrawler`)로 목록을 받아 기존 파이프라인(`nsmBillToCachedNotice` → 아카이브 → 캐시 → 알림)을 타게 한 기록. `CRAWLING_NSM_SOURCE=likms` opt-in 플래그(기본 `nsm`, 동작 불변) + `createNsmClient()` 팩토리 교체 + 계류 판정 공유 헬퍼(`isPendingProgressStatus` = `발의`/`접수`, `isCrawlableNsmBill`)로 비의안 행(`billNo` `ZZ22142` 인사청문요청안)을 매핑 전에 차단. **라이브 실측**: 실제 서비스로 계류의안 199건·접수 13건 수집·매핑(드롭 1건), 게이트 lint/tsc/build + **1010 테스트**. 이어서 `/api/stats`·`/api/crawling-transparency`가 `resolveNsmSourceInfo()`로 **활성 소스**(`opinion.lawmaking.go.kr` ↔ `likms.assembly.go.kr`)를 보고하도록 수정(기본값 `nsm`이면 문자열 동일, 1013 테스트)했고, `/status` 페이지도 payload의 `name`을 카드 제목·크론 라벨·비활성 배너에 반영하도록 배선(카드에 `data-testid` 추가, `responsive-contracts`의 `/status` 계약을 testid 기반으로 전환, 크롤러 소유 크론 작업 카드에 활성 수집 소스 배지(`cron-source-pal`/`cron-source-nsm`) 추가, `status.spec.ts` 13 pass + 실 백엔드(LIKMS) 브라우저 실측 + 5개 뷰포트 계약 확인). 남은 작업(버전 범프 미실행, 캡처·삭제 프로브는 여전히 NSM URL, `/crawling-transparency` 이관 흐름 박스 1곳, `responsive.spec.ts`의 `/discussions` 선행 실패) 명시.

### `32-nsm-ua-block-and-probe-storm/` — NSM 포털 UA 차단과 삭제 프로브 폭주

- **nsm-portal-block-and-probe-storm.md**: 운영 로그의 `markSourceDeletedByMissingNsmNums … not confirmed deleted on detail page; left active` 폭주를 추적한 기록. `opinion.lawmaking.go.kr`가 **`LawCast/1.0` 토큰이 든 UA에만** 사이트 오류 페이지(200 + `<body class="errorWrap">`, 5,451 B)를 돌려준다는 것을 UA 매트릭스 2회 반복으로 확정(브라우저·`curl/8.7.1`·`Crawler/1.0`은 정상). 결과: (1) NSM 목록이 예외 없이 `total=0`이 되어 **수집이 조용히 0건**(DB상 마지막 NSM 행 2026-09-09 16:33, 이후 PAL만), (2) `probeNsmDeletedBillAlert`가 영원히 `null`이라 삭제 감지가 죽고(878 `source_deleted` 전부 2026-08-28) 같은 행을 매 사이클 재프로브, (3) 후보 풀 19,845행 대비 LIKMS 목록 15,950건 표본 커버리지 59.8% → **사이클당 약 10,300건 프로브**. 완화(`CRAWLING_NSM_DELETION_DETECTION_ENABLED=false`), 근본 원인 결정(UA 교체 vs NSM 소스 폐기), 후보 집합 재설계(마지막 목록 목격 시각 기록), 조용한 실패 제거, 관측성 구멍까지 정리. Notion `fetch failed` WARN은 별개(현재 도달 정상, 스냅샷 폴백 동작). **코드 패치 적용(§3-1)**: 0행 스캔 WARN, 포털 오류 페이지 감지(`nsm-portal-error-page.util.ts`), 프로브 outcome 분류(`deleted/alive/blocked/error/disabled`), 후보 상한 50 + 무작위 표본, 연속 unreadable 시 패스 중단, 활성 소스 라벨 — 게이트 lint/tsc/build + 1031 테스트 + 프론트 `check`/`status.spec` 13 pass. **후보 집합 재설계(§3-2)**: `nsm_last_seen_in_list_at`·`nsm_list_absence_probed_at` 컬럼 + 마이그레이션 `202610140001`, "목록에서 새로 사라진 행만" 후보(+쿨다운 168h·상한 50), 실 DB 사본 실측 — 완전 목록 0 프로브/200행 결손 시 프로브 전건이 그 200행 안/복귀 시 0, 게이트 75 suites·1042 테스트. **0행 스캔 승격(§3-3)**: 캐시 `crawling:nsmListScanHealth` 런렝스(연속 0건 스트리크·마지막 정상 수집), 임계값 3에서 ERROR 알림+`/api/stats` `status: degraded`, `/status`에 `수집 중단` 배지·전체 상태 주의 필요(전용 e2e 5건), 게이트 77 suites·1065 테스트. **UA 순환(§3-4)**: §3의 "UA 교체" 결정을 기본값으로 구현 — 실제 브라우저 UA 12개 풀(`browser-identities.util.ts`)에서 요청마다 하나를 뽑고, 그 신원이 보내는 클라이언트 힌트·`Sec-Fetch-*`·`Upgrade-Insecure-Requests`까지 함께 보낸다(`browser-request-headers.util.ts`). pal-crawl은 요청마다 `{User-Agent, ...customHeaders}` 스프레드를 만들므로 `customHeaders` 접근자로 클라이언트 하나에서 요청별 회전(이름 집합이 family별로 다르므로 family는 클라이언트당 고정), axios 경로는 요청별 전체 신원 회전. `CRAWLING_USER_AGENT`는 이제 고정용 이스케이프 해치. 검증: 신규 28 테스트 + `https.request` 스텁으로 **실제 pal-crawl 요청 헤더 캡처**.

### `29-search-ui-persona-audit/` — /notices 검색 UI 페르소나 사용성 실측·개선

- **usability-audit-and-improvements.md**: `/notices` 검색 UI가 일반 시민부터 법조인까지 포괄적으로 쓸 만한지 **mock 렌더 실측**으로 판정한 기록. SSR 프로브 8개 상태 + 1440/390 브라우저 측정(innerText·레이아웃·오버플로·탭 영역). 발견: 모드 설명 0건, 의미 모드가 **부분집합**이라는 고지 없음(계획 D6 미결), 0건 막다른 길, 유사도 칩 설명 없음, 콜드 스타트 어포던스 0건. 개선 6건(모드별 1줄 설명·범위 고지+키워드 링크·0건 회복 2방향·칩 `title`·예시 검색어 3개 로더 생성)과 검증(SSR 상태 매트릭스, notices e2e 89 pass, semantic e2e 26 pass) 포함.
  **2차(§5~§7)**: 실 백엔드/엔진을 붙여 SSR·브라우저로 재측정하며 한계를 다시 판정. 의미 모드의 `stats.totalArchiveCount`(전체 아카이브 21,188)를 결과 건수로 오용해 문서 제목이 21,188건을 광고하던 문제, 무관한 쿼리에 약한 계층이 **100장 카드로 쏟아지던** 문제를 실측으로 찾아 수정(온디맨드 키워드 건수 대조 39 vs 509, 약한 계층 10건 배치 페이징). 예시 검색어는 이 라운드에서 KST 날짜 결정화를 시도했다가 **같은 날 전원이 같은 칩을 보게 되어 오너 결정으로 랜덤 추출로 되돌렸다**(§5.3) — 다시 결정화하지 말 것. 보드 의미 UI에 `e2e/semantic-search-board.spec.ts` 6개 테스트를 새로 붙였다(1차 기능은 수동 검증뿐이었다). 검증: mock e2e 256 pass, semantic e2e 33 pass.

### `10-index-last-update-tracking/` — 시맨틱 인덱스 마지막 업데이트 시각

- **plan.md**: 인덱스 갱신 경로 분석(호스트 03/06, 사이드카 틱·부트 리페어가 `VectorIndex.save`로 수렴)과 시각 기록의 단일 소유처. `id_map.json`의 `updated_at` 스탬프(재시작 후 유지) -> `SemanticSearcher.index_updated_at` -> `EngineState.mark_ready/reload` 채택 -> 사이드카 `/search` -> 백엔드 API -> 프론트 "마지막 업데이트" 표시까지 **미션 3단계 전부 구현·검증한 기록**. 틱 결과와 시각의 소유권 분리, 크로스 언어 계약 이중 소유 주의, 레거시 `null`->"기록 없음" 계약 포함.

### `08-semantic-search-production-deploy/` — 시맨틱 검색 프로덕션 배포

- **plan.md**: `semantic-search/` 사이드카의 프로덕션 배포·백엔드 연동 로드맵. 코드베이스 조사 표, 사이드카↔백엔드 API 계약, 완료된 Docker/설정 작업과 남은 작업 우선순위(§3.B 항목은 2026-10-01 기준으로 갱신됨 — 핫 리로드·스케줄링은 구현 완료). **배포 관련 남은 작업의 단일 로드맵.**
- **incremental-update-pipeline-design.md**: 정기 인덱스 갱신 파이프라인 설계 **및 구현의 단일 소유처** — 공유 `lawcast_db` 볼륨(WAL/-shm/uid 처리), 사이드카 내부 스레드 스케줄(기본 60분), load-validate-swap 핫 리로드(`POST /reload`), 부트 리페어·삭제 가드·지문 자가치유 매트릭스. §7 항목 전부 구현됨(2026-10-01).
- **production-readiness-status.md**: 프로덕션 레디니스 **측정 기반 현황 분석**(2026-10-01). ① 엔진 구현 상태 ② 도커 환경(uid 1001 볼륨 마운트·lawcast_db 배선·세 게이트·`POST /reload` 라이브 실측) ③ 백엔드/프론트엔드 대응 상태 3축 정리 + production-ready까지 남은 작업의 '남은 이유·완료 기준' 목록. 최신 실측 기준선.

### `13-sidecar-concurrency-audit/` — 시맨틱 검색 사이드카 동시성 감사

- **sidecar-concurrency-analysis-and-tests.md**: `semantic-search/service/app.py` HTTP 사이드카 구조 분석 + 블로킹 구간 코드 감사(스냅샷 락·백그라운드 로드·비차단 flock 확인)와 `tests/test_concurrency.py` 5개 동시성 테스트 실측치. **측정 함정 4건 기록**: 클라이언트 SSL 컨텍스트의 GIL 경합(~0.42s 측정 오염 → 사전 클라이언트 생성으로 해결), 서브프로세스 `stdout=PIPE` 미소비 데드락, 콜드스타트 기준선 왜곡(2.56s vs 0.11s → 3회 워밍업 + 3라운드 중앙값 필요), HuggingFace Hub 재검증으로 인한 엔진 로드 네트워크 의존성(정상 10s vs 허브 불가 143s → `HF_HUB_OFFLINE=1`로 아웃라이어 제거). **overlap_ratio 분산 계측 귀인(단발 0.56–0.79)**: (a) 콜드 기준선 전체 상승 → ratio 과소(중복 주장 부정확), (b) 동시 배치 wall 편차 → ratio 과대(0.85 임계 플리커), 클라이언트 오버헤드는 `client_delta=0.000s`로 배제 → 3라운드 중앙값(0.65–0.69, 스프레드 0.04) 재보정 + 0.85 마진 근거를 테스트에 문서화. GIL-vs-락 분리: 지연 3.4–4.1x 상승이면서 `max/sum`=0.65–0.69(락이면 ~1.0) → GIL/CPU 포화 증거. **2026-10-10 갱신**: device=auto가 mps를 잡으면 wall/sum이 0.86–0.92로 떠 0.85 게이트가 지속 실패(큐잉 아님 — 전 지연시간이 batch wall에 수렴, 즉 동시 시작) → 하드웨어 독립 **1차 완료자 게이트**(`min ≥ 2×median(single)`: 락이면 ~1x, 정직 실행은 3.0–5.5x)로 재설계 — wall/sum·사다리 스프레드 게이트는 부하에 흔들려(정직 실행 wall/sum 최대 1.02, 스프레드 0.57) 인쇄 전용으로 강등(2026-10-11).

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

### `20-semantic-query-quality-eval/` — 의미 검색 쿼리 품질 평가

- **query-quality-evaluation.md**: `semantic-search/` 엔진 구조와 `backend/lawcast.db` `notice_archives` 학습 코퍼스 실측(97,057 청크 / 21,044 공고 / 21,177 행 / 878 source_deleted / 4,210 고유 법안명) 및 24개 후보 질의(구어체·동의어·약칭·개념·모호) 실측 평가. **CRITICAL**: ① 절대 코사인 임계값(0.25/0.45)이 실제 한국어 법률 질의를 전혀 분리하지 못함(무관 쌍 100%가 0.45 초과, 관련 rank1 최소 0.698) — `14-relevance-tier-search`의 계층 설계 캘리브레이션 재검토 필요 ② 정답 법안명 질의 top1 0.560 → 어휘(주제어 중첩) 재랭크만으로 0.915(+0.355) ③ 색인에 `source_deleted` 878건 포함 ④ 동일 법안명 개정안이 평균 5건이라 공고 단위 정답은 본질적 모호. 개선 방향 8종을 실측 근거와 함께 기록. §7은 2026-10-10 증분 갱신(133건 추가·311청크·55초·기존 97,057벡터 바이트 동일 = 순수 append) 전후 재측정으로, **기존 콘텐츠 지표는 전부 불변**(24쿼리 1.00/0.92, 캘리브레이션 0.910, 임계값 0.45 미분리 재확인)이고 **신규 133건만 0→80/133 도달**(법안명 top1 0.65)했음을 기록 — 즉 병목은 신선도가 아니라 순위(동일 법안명 경합)임을 입증. §8은 한국 언론 2026-09/10 의제(국정감사 이슈·10/1 본회의 통과 법안·플랫폼 공정화법 등)에서 37개 질의를 추가 검증 — **61개 질의 종합 semantic hit@1 0.918 / hit@5 0.984 vs FTS 0.754 / 0.820**, 그리고 동일 법안의 표현별 순위 표로 **음절 약어(중처법 MISS, 산안법 MISS, 전상법 154)가 체계적으로 실패**하고 정식명·띄어쓰기 변형만 rank 1이 됨을 정량 입증(별칭 사전 근거). §9는 그 수정을 실제 구현 — `lawcast_semantic/aliases.py`(질의 약어→정식 법안명, 인덱스 무변경) + `search.py` 1줄 배선 + `test_aliases.py` 15개. 실측: 별칭 22개 중 단독 12·문장 8개가 rank1로 새로 도달, **회귀 0**, 05_evaluate 무회귀(동일 수치), ruff clean + pytest 157/18 passed. 규칙 적용으로 `스토킹처벌법` 항목은 1→2 악화가 측정되어 제거함. §10은 사이드카 응답 전 임계값 미달 결과 제외 옵션(`LAWCAST_SEMANTIC_MIN_SIMILARITY`)의 품질 비용 분석 — **측정상 제외되는 결과가 0건**(top-15 375청크 중 0.25 미만 0건, 상위 400위까지도 0건, 최저 0.365)이라 비용이 정확히 0이고, 반대로 **어떤 절대 임계값으로도 노이즈와 유효한 모호 질의를 분리할 수 없음**(노이즈 최고점 `오늘 점심 메뉴` 0.536 > 유효 `그거 어떻게 되나요` 0.480·`환경 보호` 0.546)을 입증. 0.50 초과부터 실비용 발생(0.55에서 라벨 2/40·자연 2/20 공백, 백엔드 평균 4.53건·5/40이 k 미만), `MIN_SIMILARITY = CLEAR_SIMILARITY`면 약한 계층이 구조적으로 공백이 되어 프런트 reveal 버튼이 영영 뜨지 않음. 권고: 기본값 유지, 노이즈 필터로 올리지 말 것(대안은 §5-1 어휘 재랭크).

### `21-indexing-boilerplate-stripping/` — 인덱스 구축 보일러플레이트 제거

- **chunk-text-normalization.md**: 인덱스 구축 시 섹션 라벨(`제안이유`/`주요내용`/`제안이유 및 주요내용`)과 열거자(`가.`~`타.`, `1)`, `①`, `ㅇ`)를 임베딩 입력에서 제거한 작업 기록. **핵심 사실**: 코퍼스는 라벨을 독립 줄이 아니라 본문 첫 문단에 **붙여** 쓴다(`제안이유 및 주요내용 현행법은 ...`)는 쪽이 훨씬 흔하고, 예전 규칙은 줄 전체만 라벨로 인정해 이 라벨이 그대로 임베딩에 남았다(라벨 포함 청크 813/14,672). 실측(3,000 공고): 청크 −0.93%, 문자 −0.99%, 토큰 −1.04%, 라벨 포함 청크 1,059→66, 열거자로 시작하는 청크 1,921→10 — **절감은 약 1%이고 진짜 가치는 질의 품질**(코퍼스 최다 줄머리 토큰이 모든 청크를 서로 닮게 만들던 문제). **오탐 함정 2종**(테스트로 고정): ① 라벨 뒤에 공백/줄끝이 와야 함(`주요 내용은 ...`·`계약의 주요 내용` 보호) ② 문단 첫 라벨은 본문일 수 있으므로 손대지 않음(`가. 주요 내용 첫 번째 항목임.`) — 그래서 열거자 접두 헤더는 아예 인정하지 않음. `normalize_text`는 질의 경로 공유라 **변환을 넣지 않는다**(질의에 적용하면 사용자가 입력한 텍스트 삭제). **선행 버그 발견(세션 22에서 수정)**: `CHUNK_MIN_CHARS`(40) 꼬리 조각 필터가 실제 내용을 버림 — 이 세션이 보고한 **2,197건(73%)은 하니스 매칭이 느슨해 3배 부풀려진 값**(정정: 737건/24.6%, 전량 코퍼스 3,795건/19.6%). 배포 비용: 증분 재임베딩 20,178/96,565청크(20.9%, 약 31분), 전체 재구축은 약 2.5시간.

### `22-chunk-floor-content-loss/` — 청크 하한 필터의 내용 손실 수정

- **chunk-floor-content-loss.md**: `chunk_notice`의 `if len(text) < min_chars and chunks: continue` 필터가 **팩커가 이미 만든 텍스트를 삭제**해 인덱스에서 사라지게 하던 버그의 수정 기록. **메커니즘**: 하한 미만 청크는 항상 "끼어들 자리가 없던 잔여물"이고, 주 원인은 `_paragraph_units`가 문장부호 없는 장문(200~240자)을 예산 크기로 강제 분할한 **뒤의 꼬리 조각**(예: 공고 2221824 유닛 `[138,167,173,18]`의 18자). 캐리는 이전 청크의 마지막 유닛 단독이 `CHUNK_OVERLAP_CHARS`(50)를 넘으면 비므로, 그 조각은 뒤 청크에도 남지 않아 **완전히 검색 불가**가 됐다. **수정**: `_pack_units`가 하한 미만 청크를 앞 청크에 **병합**(캐리 중복분은 제외한 신규 유닛만)하고 `chunk_notice`는 필터를 제거. **실측(전량 코퍼스 19,396공고)**: 내용 손실 3,795건/4,434유닛 → **0**, 청크 93,701 → 93,782(+0.09%), 문자 +0.66%, 재임베딩 필요 5.54%(5,109 텍스트 변경 + 81 신규). **핵심 설계 이득**: 드롭과 병합 모두 청크 하나를 제거하므로 **청크 id·index가 불변** → 증분 갱신 비용이 바뀐 텍스트뿐. **예산 초과**는 병합에서만 최대 `CHUNK_MIN_CHARS`(40)자로, 최장 임베딩 입력 240자 = 최대 158토큰, `KURE-v1` 윈도우 8192에서 `truncated_count=0` 검증(단, 128토큰 모델로 교체 시 상위 5% 절단 위험). **대안 검토·기각**: 꼬리 조각을 앞 청크 문맥(~170자)으로 패딩해 별도 청크로 유지(+872 벡터/3,000공고, 중복 내용 경쟁), 마지막 두 청크 재분배(중간 단어 절단 패스 추가, 얻는 것 없음). **회귀 가드**: `tests/test_chunk_coverage.py` + 커밋된 실제 공고 픽스처 `tests/fixtures/notices-chunk-coverage.jsonl`(11건: 손실 공고 5건 직접 검증분·최단 `).`/최장 39자 조각·중간 손실·섹션 통째 손실·무영향 대조군 3건)가 문단 텍스트가 인덱스에서 사라지지 않음을 검증합니다. 오라클은 원문에서 재유도(공백 무시)하므로 패킹 변경이 스스로 만족시킬 수 없고, 2,000공고 전수 스윕은 `lawcast.db`가 있는 호스트에서만 실행됩니다(CI엔 DB가 없음). **fault-injection 3세계 매트릭스**(`_workspace/verify_coverage_guard_catches_drop.py`)로 각 단정이 자기 실패 모드에 반응함을 증명: drop 세계 coverage **19/38 실패**·corpus **실패**, 미병합 세계는 coverage 통과·**merge 속성 실패**, 병합 세계는 전부 통과. **검색 계층 가드** (`test_chunk_coverage_retrieval.py`): 청크 집합이 아니라 **질의로 도달되는지**를 단정 — 조항이 속한 문장으로 `/search` 기본 창(k=5)을 조회해 그 조항을 담은 청크가 **조항의 공고** 안에서 창에 들어오고 첫 공고가 그 공고임을 요구. 실측(해싱 n-gram 스텁): 출시 **11/11·11/11**, 병합 이전 **8/11·0/11**. faiss 검색을 먼저 하고 torch를 나중에 로드하면 libomp 이중 초기화로 abort하므로 랭킹은 서브프로세스 프로브(`tests/retrieval_probe.py`)에서만 돌리고, 병합 이전 규칙 복원은 `sitecustomize` shim으로 주입해 **11/11 케이스가 실패**함을 증명했습니다(훅 없는 주입). **검증**: ruff clean, pytest **242 passed, 0 skipped**(+4 청킹, +51 내용 보존 가드, +14 검색 가드 — 실모델 레이어와 사이드카 동시성 테스트가 라이브 아티팩트 재구축 후 최초로 skip 없이 실행), 하니스 `_workspace/chunk_floor_coverage.py`. 배포: 증분 계획 `to_embed 24,816 / reused 71,830 / dropped 825`→ **2026-10-10 apply 완료**(fingerprint `2c3e03179db0`, 백업 `artifacts/backup-pre-session22-apply/`, 사후 plan `to_embed 0`). 실모델 조항 recall@1 **10/11**(1건은 병행 법안군과 동일한 회계 보일러플레이트 문장이라 8위 → 실모델 레이어는 첫 페이지 내 노출(`SURFACE_BOUND=10`)을 단정, 근거·수치는 메모리 22 §7), 평가셋 회귀 없음(holdout 상위 1쿼리만 1→2위 스왑, `05_evaluate.py` 대조 실측). 커밋·버전 범프·프로덕션 배포는 미실시.

### `24-ai-summary-chunking/` — AI 요약(aiSummary) 청킹 포함 + 검색 품질 A/B

- **ai-summary-chunking-measurement.md**: `plan.md`의 "include `aiSummary` in chunks" 항목을 실제 시행한 구현·실측 기록. `notice_archive_snapshot_states.ai_summary`(21,177공고 중 21,071건, 평균 71자)를 `LEFT JOIN`으로 읽어 **`AI 요약` 섹션**으로 인덱싱(96,646 → 117,718청크, 본문 96,646행 바이트 단위 전량 재사용 = 순수 추가). **CRITICAL 회귀·수정**: 첫 구현이 빈 `proposal_reason` 405건의 제목-only 폴백 청크를 요약으로 *대체*해 title 부류 지표가 오르는 것처럼 보였으나(실은 청크 제거 부작용) 그 405건이 정확 제목 매칭 능력을 잃음(name_bench added coverage 80/133 → 48/133) → 제목 청크를 **유지한 채** 요약을 덧붙이는 additive 방식으로 수정(회귀 0). **실측**: 요약 어휘 질의 300건 miss **33.7% → 0%**(hit@1 0.407 → 0.990, self-match 천장값), 자연 시민 질의 61건·라벨 평가셋 40건·정답 법안명 벤치마크(n=200)는 **불변~소폭 개선**(무회귀), 비용은 요약 벡터끼리의 경쟁(dilution, 자기 요약 마스킹 시 hit@1 −0.10)이며 200청크 창의 공고 커버리지는 −1.2%로 무시 가능.

### `25-chunking-capability-gate/` — 청킹/파생 필드 능력 회귀 게이트

- **capability-regression-gate.md**: 세션 24의 405건 title-chunk 회귀를 **사람이 발견하는 대신 테스트가 자동으로 잡게** 만든 게이트 기록. `lawcast_semantic/capabilities.py`가 공고별 능력(`indexed`, `title_text`, `section:<라벨>`, `derived:<필드>`)을 원문에서 재유도하고, `derived_field_diff`가 파생 필드를 뺀 baseline과 넣은 후보를 비교해 잃은 능력이 있으면 실패합니다. `DERIVED_NOTICE_FIELDS` 미등록 새 레코드 필드는 스키마 검사에서 실패하므로 새 파생 필드가 게이트를 우회할 수 없습니다. 실측: 구현을 스왑으로 되돌리면 **구조 계층 5건 + 검색 계층 8건 실패**(빈 `proposalReason` 405건 보고), 되돌리지 않으면 25 passed. **함정 1건 수정**: `section:<라벨>`을 원문에서만 유도하면 어떤 규칙에도 반응하지 않는 공허한 능력이 되므로, 라벨은 원문에서·carrier는 청크 집합에서 판정하도록 고쳤습니다(라이브 0/24 위반 vs 라벨 `body` 전환 8/24·라벨 제거 12/24).
- 아티팩트 리포트 `scripts/07_capability_report.py`: 서빙 중인 인덱스의 능력별 공고 수를 한 줄로 찍고, 저장한 기준선과 **공고 단위로** 대조해 손실 시 exit 1 합니다(카운트 델타로는 0으로 보이는 스왑도 잡힘). 모델·FAISS 없이 전량 4.4초. 롤백 세트 대조 실측에서 `derived:ai_summary 21071 → 0`(메모리 24 §8.1 사고)과 요약이 법안명을 담은 3건에 의한 `title_text 545 → 542`를 보고했고, 같은 읽기에서 `chunks.jsonl` ↔ `id_map.json` 행/지문 불일치도 `MISMATCH`로 잡습니다.

### `26-ai-summary-final-verification/` — AI 요약 인덱싱 최종 검증 + 프로덕션 레디니스

- **readiness-verification.md**: 세션 24/25의 요약 인덱싱을 현재 호스트에서 다시 측정한 최종 검증. ① 초기 구축: `01 --db`가 **21,072요약청크를 포함한 117,718청크**를 만들고 라이브 `artifacts/chunks.jsonl`과 `cmp` **바이트 동일**. ② 증분: 라이브 plan **멱등**(`to_embed 0 / reused 117,718 / has_changes false`), 요약 없는 세트 plan은 요약 행 **순수 추가**(`to_embed 21,072 / dropped 0`). ③ 성능 A/B 재현: 요약 어휘 질의 miss **33.7% → 0.0%**, 자연 질의 61건 불변, dilution −0.093. ④ HTTP 경로 실측(`/health` 117,718·gist 질의 top5 전부 `[AI 요약]`·경계 400/422). ⑤ **릴리스 코드 위험 재검증**: v2.4.0 시야 + 라이브 아티팩트 → `dropped 21,072 / shrink_refused false` = 요약 벡터 자동 삭제. **BLOCKER 2건**: 요약 기능이 **미커밋**(HEAD=v2.4.0에 `SUMMARY_SECTION`/`ai_summary` 0건)이라 지금 이미지를 빌드하면 §⑤ 사고가 자동 발생하며, 같은 워킹트리에 다른 스레드의 미커밋 요청 경계 작업이 섞여 있어 PR 분리 조율이 필요. Docker 데몬 미실행으로 컨테이너 배포 검증은 불가(로컬 프로세스 HTTP 검증만).

### `27-capability-guard-backfill-break-glass/` — 능력 게이트 LOST의 데이터 백필 규명 + 브레이크글라스 배포

- **capability-guard-break-glass.md**: semantic-search v2.5.0(`da6c0be`) 릴리스를 필수 능력 게이트가 `title_text` 8건 LOST로 블록한 사건의 규명·해결 기록. 원인은 **코드 회귀가 아니라 데이터 백필**: 제안이유가 비어 있던 8건 공지가 likms/PAL 백필로 채워지면서 제목 전용 폴백 청크가 실제 본문 섹션 청크로 대체되어, 제목 원문이 청크 텍스트에서 사라짐(제목은 여전히 임베딩 컨텍스트로만 존재). v2.4.0(서빙 중)·v2.5.0 청커를 동일 레코드로 A/B하여 **두 버전 모두 동일 8건을 손실**함을 증명했으므로 롤백으로 예방 불가. 반대편으로 146건이 title_text을 순증. `allow_capability_loss=true`로 재실행(run 38184195199)했고, 이전 업데이트 틱이 인덱스를 이미 갱신해 재비교는 `OK — no capability class lost`로 통과, `/health`에 `maxK:200` 노출 확인(백엔드 v1.11.0 cap 협상과 연결). 교훈: **게이트 LOST를 보면 코드 타임라인보다 데이터 타임라인을 먼저 대조**하라.

### `23-embedding-device-autodetect/` — 임베딩 하드웨어 자동 탐지

- **plan.md**: 임베딩 모델의 실행 디바이스를 `LAWCAST_SEMANTIC_DEVICE` 기본값 `auto`로 바꿔 CPU보다 우수한 하드웨어를 자동 탐지·사용하게 한 구현 기록. **핵심 설계**: `config.DEVICE`는 요청값(경량 유지·torch 지연 임포트), 탐지·핀 해석은 `lawcast_semantic/device.py` 단일 소유(cuda > mps > xpu > cpu, 각 가용성 검사 격리 → 불량 드라이버는 다음 후보로 강등), `KoreanEmbedder`는 **프로브 인코딩(형상+유한값) 통과 못 하면 경고 후 cpu 재로드**. 핀(`cpu` 등)은 탐지 없이 그대로 존중. **디바이스는 아티팩트를 무효화하지 않음**(cpu/mps 벡터 cosine 1.000000·max delta 0 실측). 관측: stage 2 `device` 줄 + `/health.device`(모델 단계에서 기록 → 아티팩트 로드 실패 시에도 남음, `mark_ready`에 두면 지워지는 함정). 실측(Apple Silicon, torch 2.14): 단일 질의 96.8→32.5ms(2.98x), 배치 14.4→29.6 chunks/s(2.06x), 모델 로드 +3s. 검증: ruff clean, pytest **267 passed** + 사전 존재 실패 1(`artifacts/faiss.index` 소실 → `embeddings.npz`/`id_map.json`도 없음, 이 세션 테스트 이전 상태)·skip 1(동일 원인), stage 2 CLI·uvicorn `/health` 라이브 실측. 운영 컨테이너는 CPU 전용 휠이라 `auto`→`cpu`로 행동 불변.

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
