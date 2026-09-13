## Plan: 스레드 인용 알림

토론 참여자의 스레드별 `author_id`와 웹푸시 endpoint를 별도 매핑으로 연결하고, 프론트의 기존 `>>#N` 인용 형식을 서버에서 해석해 인용 대상 참여자에게 웹푸시를 보낸다. 신규 스레드의 자동 생성 #1 의견과 기존 스레드의 첫 답글 모두 작성 직후 인용 알림 동의를 안내한다.

**Steps**
1. **계약과 데이터 모델**
   - `web_push_subscriptions`는 endpoint 단위의 기존 저장소로 유지하고, endpoint 하나가 여러 스레드 참여자에 연결될 수 있도록 `discussion_web_push_bindings` 매핑 테이블을 추가한다. 매핑에는 `thread_id`, `author_id`, `subscription_id` 또는 endpoint 참조, `is_active`, timestamps와 중복 방지 unique index를 둔다.
   - TypeORM entity와 신규 migration을 추가한다. 기존 구독은 매핑 없이 유지하고, 기존 글로벌 웹푸시 기능의 동작은 바꾸지 않는다.
   - 구독 등록 계약에 선택적인 discussion context(`threadId`)를 추가한다. 서버가 요청 IP와 `thread:${threadId}` scope로 `IpMaskingUtil.authorIdFromIp`를 계산해 매핑하므로 클라이언트가 임의의 `author_id`를 제출하지 않게 한다. 스레드 존재·활성 상태·요청 참여 조건을 검증한다.
   - 관련 파일: `backend/src/modules/notification/web-push-subscription.entity.ts`, `web-push-subscription.service.ts`, `web-push-registration.service.ts`, `dto/create-web-push-subscription.dto.ts`, 신규 migration, 신규 binding entity.

2. **웹푸시 바인딩 API와 조회** (*1과 일부 병렬*)
   - `WebPushSubscriptionService`에 active endpoint를 특정 `(threadId, authorId)`에 bind/unbind하고 해당 참여자의 active subscriptions를 조회하는 메서드를 추가한다. 하나의 endpoint 재등록 시 기존 구독 row를 재활성화하되 다른 스레드 매핑을 덮어쓰지 않는다.
   - 등록 DTO/API 및 프론트 `WebPushSubscriptionRequest`를 확장한다. 기존 `/push/subscriptions`의 글로벌 등록 경로는 유지하고, discussion context가 있을 때만 binding을 생성한다. 해지 시 endpoint 전체 삭제 대신 현재 discussion binding만 비활성화할지 정책을 명확히 하고, 글로벌 해지와 스레드별 해지를 분리한다.
   - `NotificationModule`이 binding entity를 TypeORM에 포함하고, 필요한 subscription service를 `DiscussionsModule`에서 사용할 수 있게 import/export 경계를 구성한다.

3. **인용 해석과 알림 발송** (*1과 병렬 가능, 2에 의존*)
   - 기존 프론트가 생성하는 `>>#N`, `>>N`, standalone `>#N` 형식과 일치하는 서버 유틸을 추가한다. 숫자 sequence만 추출하고, 현재 스레드의 comment만 대상으로 하며, 중복/존재하지 않는 sequence/system comment/자기 자신의 author_id는 알림에서 제외한다.
   - `DiscussionsService.addComment`에서 comment 저장과 thread count 갱신은 기존 transaction으로 완료한 뒤 인용 대상 comment를 해석한다. 알림 실패가 의견 등록 성공을 rollback하지 않도록 commit 후 비동기 호출 또는 안전한 fire-and-forget 경계로 처리하고 실패는 로깅한다.
   - `DiscussionNotificationService`를 추가해 quoted comment의 `author_id`로 binding을 조회하고 기존 bounded/retry web-push dispatch 경로를 사용한다. payload에는 제목/본문, `noticeNum`, `threadId`, quoted sequence, quoting comment id, 상세 URL, `type: opinion_quoted`, dedupe tag를 포함한다. 삭제·시스템 메시지·자기 인용·중복 sequence는 각각 테스트한다.
   - 관련 파일: `backend/src/modules/discussions/discussions.service.ts`, 신규 quote parser/util 및 notification service/spec, `discussions.module.ts`, `notification/web-push-notification.service.ts`의 기존 dispatch 계약.

4. **스레드 정보와 프론트 동의 흐름** (*2, 3의 API 계약에 의존*)
   - `frontend/src/lib/components/WebPushConsentForm.svelte`의 지원 감지, VAPID 조회, PoW, permission 요청, service-worker subscription, 등록/롤백 로직을 재사용 가능한 helper/component로 분리하거나 discussion용 얇은 modal에서 공유한다. 기존 webhook 페이지의 관리 UI와 성공/실패 동작은 유지한다.
   - 토론 상세의 첫 답글 성공 경로인 `frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte`에서 기존 comment count가 1이고 등록이 성공한 경우에만 동의 modal을 연다. 이미 해당 스레드/참여자에 binding된 endpoint가 있으면 중복 prompt를 피하고, 지원 불가·권한 거부·서버 비활성 상태도 조용히 처리한다.
   - modal 문구는 “의견이 인용될 때 브라우저 알림을 받을 수 있다”는 목적을 명시하고 `동의 및 활성화`와 `나중에`를 제공한다. 동의 시 discussion `threadId` context를 포함해 등록해 현재 endpoint와 현재 참여자의 `author_id`를 bind한다. 거절/실패 후에는 같은 페이지에서 반복 표시하지 않도록 명시적인 dismissal 상태를 저장한다.
   - 신규 스레드의 경우 `frontend/src/lib/components/discussions/NoticeDiscussions.svelte`에서 생성 성공 후 이동할 때 “방금 #1 의견을 작성한 작성자”라는 일회성 session marker를 thread id와 함께 전달한다. 상세 페이지는 marker가 있을 때만 modal을 열고 일반 열람자가 댓글 1개인 스레드를 방문했다고 prompt하지 않는다. marker는 소비 즉시 제거한다.
   - `frontend/src/lib/api/client.ts`, `frontend/src/lib/types/api.ts`, 신규 consent modal/helper 및 필요한 route/component를 수정한다. Svelte runes/기존 컴포넌트 스타일을 따른다.

5. **백엔드 테스트**
   - quote parser unit test: 지원 형식, 여러 참조, 잘못된 sequence, system/deleted/self 대상 필터.
   - binding service/registration test: endpoint 재활성화, 하나의 endpoint에 여러 스레드 매핑, 현재 thread/author 계산, 글로벌 등록 회귀.
   - discussion service test: comment transaction 성공 후 quote dispatch 호출, 대상 author_id 전달, dispatch 실패가 comment 응답을 깨지 않음, self-quote 미발송.
   - notification service test: quoted author의 active bindings만 조회하고 기존 web-push batch/retry 경로에 정확한 payload를 전달.
   - controller/API isolation 또는 관련 DTO 테스트: discussion context validation과 기존 `/push/subscriptions` 요청 호환.

6. **프론트 테스트와 수동 검증**
   - `frontend/e2e/discussions.spec.ts`에 기존 첫 답글 테스트를 확장해 첫 답글 성공 시 modal 표시, 동의 시 public-key/구독 등록 요청에 thread context 포함, 거절 시 상태 저장과 재표시 방지를 검증한다.
   - 신규 스레드 개설 e2e에서 생성 성공 후 상세 페이지에서만 #1 작성자용 modal이 표시되고, 일반 새로고침/다른 사용자의 접근에서는 표시되지 않는지 검증한다.
   - 이미 현재 스레드에 binding된 endpoint, browser push 미지원/permission denied, 두 번째 답글, 자기 인용, 타 참여자 인용 각각을 mock API로 검증한다.
   - 실행 명령: `cd backend && npm test -- --runInBand`의 관련 discussion/notification/web-push spec 우선 실행 후 전체 backend test; `cd frontend && npm run check`; 필요 시 `cd frontend && DIFFCHAIN_UI_MOCK=1 npx playwright test e2e/discussions.spec.ts`.
   - 수동으로 두 브라우저/두 IP 참여자가 같은 스레드에서 각각 동의한 뒤 한 참여자가 다른 참여자를 `>>#N`으로 인용했을 때 인용 대상만 수신하는지, endpoint 재사용과 구독 해지 후 재등록이 정상인지 확인한다.

**Relevant files**
- `backend/src/modules/discussions/discussions.service.ts` — 의견 저장 후 인용 참조를 해석하고 알림을 commit 이후 호출.
- `backend/src/modules/discussions/discussions.module.ts` — 신규 discussion notification/binding 의존성 구성.
- `backend/src/modules/discussions/entities/discussion-comment.entity.ts` — sequence/author_id/message type가 quote 대상 기준.
- `backend/src/modules/notification/web-push-subscription.entity.ts` 및 `web-push-subscription.service.ts` — endpoint lifecycle과 binding 조회/갱신.
- `backend/src/modules/notification/web-push-registration.service.ts`, `dto/create-web-push-subscription.dto.ts` — thread context를 검증하고 author_id를 서버에서 계산.
- `frontend/src/lib/components/discussions/CommentItem.svelte` 및 `ThreadDetailView.svelte` — 기존 `>>#N` 인용 형식의 source of truth.
- `frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte` — 첫 답글 성공 후 동의 modal 삽입.
- `frontend/src/lib/components/discussions/NoticeDiscussions.svelte` — 신규 스레드 #1 의견 이후 일회성 prompt marker 전달.
- `frontend/src/lib/components/WebPushConsentForm.svelte`, `frontend/src/lib/api/client.ts`, `frontend/src/lib/types/api.ts` — 기존 웹푸시 흐름과 API 타입 재사용/확장.
- `frontend/e2e/discussions.spec.ts` — 토론 및 동의 흐름 회귀 테스트.

**Verification**
1. migration을 빈 SQLite와 기존 웹푸시 데이터베이스 양쪽에 적용해 기존 endpoint unique/index와 신규 binding unique/index가 생성되는지 확인한다.
2. backend targeted Jest로 parser, binding, discussion notification, web-push dispatch 테스트를 실행하고, 특히 알림 dispatch 실패가 comment 등록을 실패시키지 않는지 확인한다.
3. `cd frontend && npm run check`로 타입/Svelte 진단을 확인한다.
4. `DIFFCHAIN_UI_MOCK=1` Playwright에서 기존 토론 등록 회귀, 기존 스레드 첫 답글 동의, 신규 스레드 #1 동의, 두 번째 답글 no-prompt를 실행한다.
5. 브라우저 두 세션에서 endpoint/author binding을 확인하고, 인용 대상만 push payload를 수신하는지 실제 service worker 알림으로 검증한다.

**Decisions**
- `author_id`는 기존처럼 `thread:<threadId>` scope의 HMAC 값을 사용한다. 이를 전역 사용자 ID로 확장하지 않는다.
- endpoint row에 단일 `author_id`를 추가하지 않고 별도 매핑을 사용한다. 같은 브라우저 endpoint가 여러 스레드 참여자로 등록될 수 있기 때문이다.
- 인용 syntax는 이미 UI가 생성하는 `>>#N` 계열을 서버가 authoritative하게 해석한다. 닉네임 `@mention`은 이번 범위에 포함하지 않는다.
- 신규 스레드 자동 #1 의견과 기존 스레드의 첫 답글 모두 동의 대상이다. 일반 열람자에게 오탐 prompt가 뜨지 않도록 신규 스레드 생성 성공 marker를 사용한다.
- 알림은 의견 저장 트랜잭션과 분리한다. 웹푸시 장애가 사용자 의견 등록을 막지 않아야 한다.
- 기존 글로벌 웹푸시 등록/해지 및 다른 알림 유형은 회귀 없이 유지한다.

**Further Considerations**
1. 요청 IP가 의견 작성 시점과 동의 시점에 달라지면 기존 author_id 전략상 같은 참여자로 복원할 수 없다. 현재 시스템의 익명 식별 정책을 유지하는 권장안이며, 장기적으로는 별도 익명 브라우저 토큰/세션 식별자가 필요하다.
2. 동의 거절 상태를 전역 localStorage로 저장하면 다른 스레드에서 동의를 막을 수 있으므로 thread-scoped key 또는 server binding 상태와 함께 관리한다.
3. 구독 해지 UX는 글로벌 endpoint 전체 해지와 현재 스레드 binding 해지를 구분해야 한다. 이번 기능에서는 동의 흐름의 등록과 기존 글로벌 관리 화면을 우선 보존한다.
