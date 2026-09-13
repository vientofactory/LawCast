# 법률안 익명 토론/댓글 시스템 구축 계획

## 1. 개요 및 설계 목표
- **목적**: 개별 법률안 조회 페이지(`/notices/[num]`)에 나무위키(namu.wiki) 및 미디어위키(MediaWiki) 스타일의 **주제별 익명 토론/댓글 시스템**을 구현합니다.
- **핵심 정책**:
  1. **작성자 식별**: 사용자가 입력한 닉네임과 접속 클라이언트 IP의 첫 2옥탯을 조합하여 `입력받은 닉네임 (IP 2옥탯)` 형태로 표기 (예: `홍길동 (211.234.***.***)`).
  2. **비밀번호 보호**: 댓글/스레드 작성 시 비밀번호를 입력받아 안전하게 단방향 해싱(Salt + Scrypt/PBKDF2)하여 저장하며, 수정 및 삭제 시 비밀번호 일치 여부를 검증.
  3. **토론 스레드 구조 (나무위키 레퍼런스)**:
     - 법률안별로 여러 개의 주제별 토론 스레드(제목, 열림/닫힘 상태)를 개설 가능.
     - 각 스레드 내에서 `#1, #2, #3...`의 고유 레스(res) 번호로 발언이 순차 누적.
     - 삭제 시 스레드 흐름 보존을 위한 소프트 삭제(Soft Delete: "작성자에 의해 삭제된 의견입니다" 표시).

---

## 2. 세부 구현 단계

### Phase 1: 백엔드 DB 스키마 및 마이그레이션 (NestJS + TypeORM + SQLite)
1. **마이그레이션 파일 작성**:
   - `backend/src/migrations/202609050001-add-discussions-and-comments.migration.ts`
   - `discussion_threads` 테이블:
     - `id` (INTEGER PK AUTOINCREMENT)
     - `noticeNum` (INTEGER NOT NULL, INDEX)
     - `title` (VARCHAR(255) NOT NULL)
     - `status` (VARCHAR(20) NOT NULL DEFAULT 'open' - 'open' | 'closed')
     - `authorNickname` (VARCHAR(100) NOT NULL)
     - `authorIpMasked` (VARCHAR(50) NOT NULL)
     - `authorIpHash` (VARCHAR(64) NOT NULL)
     - `passwordHash` (VARCHAR(128) NOT NULL)
     - `passwordSalt` (VARCHAR(64) NOT NULL)
     - `commentCount` (INTEGER NOT NULL DEFAULT 1)
     - `createdAt`, `updatedAt` (DATETIME NOT NULL)
   - `discussion_comments` 테이블:
     - `id` (INTEGER PK AUTOINCREMENT)
     - `threadId` (INTEGER NOT NULL, FK to discussion_threads ON DELETE CASCADE)
     - `noticeNum` (INTEGER NOT NULL, INDEX)
     - `sequence` (INTEGER NOT NULL - 스레드 내 #1, #2...)
     - `authorNickname` (VARCHAR(100) NOT NULL)
     - `authorIpMasked` (VARCHAR(50) NOT NULL)
     - `authorIpHash` (VARCHAR(64) NOT NULL)
     - `passwordHash` (VARCHAR(128) NOT NULL)
     - `passwordSalt` (VARCHAR(64) NOT NULL)
     - `content` (TEXT NOT NULL)
     - `isDeleted` (INTEGER NOT NULL DEFAULT 0)
     - `isEdited` (INTEGER NOT NULL DEFAULT 0)
     - `editedAt` (DATETIME NULL)
     - `createdAt`, `updatedAt` (DATETIME NOT NULL)
2. **TypeORM Entity 생성**:
   - `backend/src/modules/discussions/entities/discussion-thread.entity.ts`
   - `backend/src/modules/discussions/entities/discussion-comment.entity.ts`
3. **마이그레이션 등록 및 AppModule 엔티티 연결**:
   - `backend/src/migrations/index.ts`에 신규 마이그레이션 등록
   - `backend/src/app.module.ts`의 `TypeOrmModule`에 신규 Entity 추가

### Phase 2: 백엔드 비즈니스 로직 및 보안/유틸리티 구현
1. **IP 마스킹 및 보안 유틸리티**:
   - `backend/src/modules/discussions/utils/ip-masking.util.ts`:
     - Proxy 헤더(`x-forwarded-for`, `cf-connecting-ip`, `x-real-ip`) 및 `req.ip` 안전 추출.
     - IPv4 마스킹 (`123.45.67.89` -> `123.45.***.***`).
     - IPv6 마스킹 (`2001:0db8:...` -> `2001:db8:****:****`).
     - IP 해시 생성 (스팸 방지 및 속도 제한용 SHA-256).
   - `backend/src/modules/discussions/utils/password-security.util.ts`:
     - `hashPassword(password: string)`: Node.js 내장 `crypto.scryptSync` / `crypto.pbkdf2Sync` + Random Salt.
     - `verifyPassword(password: string, salt: string, hash: string)`: `crypto.timingSafeEqual`을 사용한 타이밍 공격 방지 일치 검증.
2. **DTO 정의 (`class-validator`)**:
   - `create-thread.dto.ts` (title, authorNickname, content, password)
   - `create-comment.dto.ts` (authorNickname, content, password)
   - `update-comment.dto.ts` (content, password)
   - `delete-comment.dto.ts` (password)
   - `update-thread-status.dto.ts` (status, password)
3. **Discussions Service & Controller 구현**:
   - `backend/src/modules/discussions/discussions.service.ts`:
     - `getThreads(noticeNum, page, limit)`: 스레드 목록 및 최신 발언 시각 조회
     - `getThreadDetail(threadId)`: 스레드 상세 및 레스 순차 목록(삭제된 레스는 내용 마스킹 처리)
     - `createThread(noticeNum, dto, clientIp)`: 트랜잭션으로 스레드 생성 + #1 레스 등록
     - `addComment(threadId, dto, clientIp)`: 스레드 열림 상태 확인 후 `MAX(sequence)+1`로 레스 추가, `commentCount` 갱신
     - `updateComment(commentId, dto)`: 비밀번호 검증 후 내용 수정 및 `isEdited` 플래그 설정
     - `deleteComment(commentId, dto)`: 비밀번호 검증 후 `isDeleted = 1` 소프트 삭제
     - `updateThreadStatus(threadId, dto)`: 비밀번호 검증 후 스레드 열림/닫힘 상태 전환
   - `backend/src/modules/discussions/discussions.controller.ts`:
     - REST API 라우트 엔드포인트 제공
4. **모듈 등록**:
   - `backend/src/modules/discussions/discussions.module.ts` 생성 및 `app.module.ts`에 Import.

### Phase 3: 프론트엔드 API 연동 및 상태 관리
1. **프록시 및 API 클라이언트 확장**:
   - `frontend/src/routes/api/[...path]/+server.ts`: PATCH 메서드 프록시 핸들러 추가
   - `frontend/src/lib/types/api.ts`: Discussion 관련 인터페이스(`DiscussionThread`, `DiscussionComment`, 요청/응답 DTO) 추가
   - `frontend/src/lib/api/client.ts`: 토론 API 함수들 구현 (`getDiscussionThreads`, `getDiscussionThread`, `createThread`, `addComment`, `updateComment`, `deleteComment`, `updateThreadStatus`)

### Phase 4: 프론트엔드 나무위키 스타일 토론 UI 컴포넌트 구현
1. **토론 컴포넌트 패키지 구성 (`frontend/src/lib/components/discussions/`)**:
   - `NoticeDiscussions.svelte`: 전체 토론 컨테이너 (스레드 목록 뷰 / 스레드 상세 대화 뷰 전환, 탭 UI, 다크모드 대응)
   - `ThreadListView.svelte`: 스레드 목록 카드, 상태 배지(🟢 열림 / 🔒 닫힘), 작성자 `닉네임 (IP)`, 레스 수 배지, '새 토론 시작' 버튼
   - `ThreadDetailView.svelte`: 스레드 상단 헤더(제목, 상태, 스레드 닫기/열기), `#1, #2, #3...` 레스 타임라인 박스, 하단 빠른 답변 폼
   - `CommentItem.svelte`: 개별 레스 박스 (나무위키 스타일 res 번호 배지, 작성자명 `닉네임 (IP)`, 시간, 본문, 수정/삭제 버튼, 삭제된 의견 묘비 표시)
   - `NewThreadModal.svelte`: 닉네임, 비밀번호, 토론 주제, 첫 발언 내용 입력 모달
   - `CommentActionModal.svelte`: 수정(본문+비밀번호) 및 삭제(비밀번호) 확인 팝업 모달
2. **법률안 상세 페이지 통합**:
   - `frontend/src/routes/notices/[num]/+page.svelte` 본문 하단에 `NoticeDiscussions` 배치
   - 상단 헤더 및 메타 영역에 '💬 토론 (N)' 바로가기 앵커 링크 추가

### Phase 5: 검증 및 테스트
1. **백엔드 단위/통합 테스트**:
   - IP 마스킹 유틸리티 테스트 (IPv4, IPv6, Proxy 헤더 케이스)
   - 비밀번호 해싱 및 검증 유틸리티 테스트
   - 토론 스레드 생성, 레스 추가, 비밀번호 불일치 시 401/403 예외 처리, 수정/삭제(소프트 삭제) 테스트
2. **프론트엔드 타입/린트 및 브라우저 검증**:
   - `cd frontend && npm run check` 검증
   - 다크 모드 / 라이트 모드 스타일 정합성 및 모바일 반응형 검증
   - 비밀번호 오류 시 토스트/알림 피드백, 실시간 댓글 등록 UX 검증
