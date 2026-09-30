# Agent Memories

이 폴더는 코딩 에이전트(GitHub Copilot, Claude Code, Codebuff 등)가 프로젝트를 이해하고 작업하면서 남긴 탐색 기록, 조사 결과, 구현 계획 등을 보관합니다.

## 폴더 구조

```
agent_memories/
├── README.md                                      ← 이 파일 (인덱스)
├── repo/                                          ← 프로젝트 전반 공유 노트 (에이전트 무관)
│   ├── backend-testing-notes.md                   ← 백엔드 테스트 주의사항 및 버그 패턴
│   └── frontend-notes.md                          ← 프론트엔드 개발/테스트 주의사항
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
└── 08-semantic-search-production-deploy/          ← 시맨틱 검색 프로덕션 배포/백엔드 연동
    ├── plan.md                                    ← 배포 로드맵, API 계약, 남은 작업 목록
    ├── incremental-update-pipeline-design.md      ← 정기 인덱스 갱신 파이프라인 설계 (설계 소유처)
    └── production-readiness-status.md             ← 프로덕션 레디니스 3축 현황 + 남은 작업 (측정 기반)
```

## 폴더별 상세 내용

### `repo/` — 프로젝트 전반 공유 노트

모든 에이전트가 참고해야 하는 프로젝트 전반의 주의사항입니다.

- **backend-testing-notes.md**: 백엔드 테스트 작성/실행 시 주의사항. CacheService mock 패턴, Redis 키 관리, diffchain 해시 규칙, immutable snapshot 계약, NSM/PAL 라우팅, 프로덕션 버그 패턴(7건 이상의 발견/수정 기록 포함).
- **frontend-notes.md**: 프론트엔드 개발 주의사항. Svelte runes 사용법, Playwright e2e 테스트 패턴, 모의 데이터 처리, data-testid 사용법.

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

### `08-semantic-search-production-deploy/` — 시맨틱 검색 프로덕션 배포

- **plan.md**: `semantic-search/` 사이드카의 프로덕션 배포·백엔드 연동 로드맵. 코드베이스 조사 표, 사이드카↔백엔드 API 계약, 완료된 Docker/설정 작업과 남은 작업 우선순위(§3.B 항목은 2026-10-01 기준으로 갱신됨 — 핫 리로드·스케줄링은 구현 완료). **배포 관련 남은 작업의 단일 로드맵.**
- **incremental-update-pipeline-design.md**: 정기 인덱스 갱신 파이프라인 설계 **및 구현의 단일 소유처** — 공유 `lawcast_db` 볼륨(WAL/-shm/uid 처리), 사이드카 내부 스레드 스케줄(기본 60분), load–validate–swap 핫 리로드(`POST /reload`), 부트 리페어·삭제 가드·지문 자가치유 매트릭스. §7 항목 전부 구현됨(2026-10-01).
- **production-readiness-status.md**: 프로덕션 레디니스 **측정 기반 현황 분석**(2026-10-01). ① 엔진 구현 상태 ② 도커 환경(uid 1001 볼륨 마운트·lawcast_db 배선·세 게이트·`POST /reload` 라이브 실측) ③ 백엔드/프론트엔드 대응 상태 3축 정리 + production-ready까지 남은 작업의 '남은 이유·완료 기준' 목록. 최신 실측 기준선.

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
