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
└── 03-quote-notification-plan/                    ← 스레드 인용 알림 구현
    └── plan.md                                    ← 인용 알림(웹푸시 바인딩) 구현 계획
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
