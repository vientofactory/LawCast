# diffchain Change Notification Exclusion Plan (backfill events)

## 1. Goal and scope

Add notification-exclusion logic so change events that do **not** represent a
real, user-visible change of a bill (internal backfill/repair runs) never reach
Discord webhooks or web push — while the diffchain itself stays untouched.

- **In scope**: change notifications only (Discord `change` /
  `noticePeriodEnded` / `sourceDeleted` / `nsmToPal` embeds + web push
  `sendChangeBatch` / `sendChangeDigestBatch`).
- **Out of scope**: `/api/notices/changes` timeline UI, chain audit, revision
  detail, AI-summary reset, regular notice notifications.
- **Hard invariant**: events are **always appended**. The hash chain, the
  revision timeline (`buildDiffBaselineSnapshot` merges chain-head values) and
  `resetSummaryStateForProposalReasonChange` all depend on events existing.
  Exclusion must only gate *dispatch*, never append.

## 2. Current pipeline (code map)

### 2.1 Event types and sources

`CHANGE_EVENT_TYPE` (`backend/src/modules/change-tracking/notice-change-event.entity.ts`):

| eventType | 의미 | 현재 알림 처리 |
| --- | --- | --- |
| `created` | 최초 아카이브 | dispatch에서 이미 skip (`regular notice notification`이 이미 커버) |
| `updated` | 내용 변경 | 알림 발송 대상 |
| `invalidated` | 삭제/번호개편 | `sourceDeleted` 전용 임베드 |

`NoticeChangeSource` (8종, `notice-change-source.enum.ts`):

| source | 발생처 | 이벤트 볼륨 (DB 실측) |
| --- | --- | --- |
| `archive:upsert` | 정상 크롤 upsert | created 19,856 / updated 6,475 |
| `archive:isDoneSync` | cron 처리완료 동기화 (`markNoticesDoneByNums`) | updated 19,424 |
| `bootstrap:legacy-seed` | 초기 시드 | created 1,321 (dispatch skip됨) |
| `archive:source-missing` | NSM 삭제 2중 확인 | invalidated 881 |
| `archive:updateNsmHtmlAndDetail` | **NSM HTML/디테일 백필** (`backfillMissingSnapshotArtifacts`, `fetchAndUpdateProposalReason`) | updated 203 |
| `archive:likmsProposalReason` | **PAL 제안이유 복구** (`appendLikmsProposalReasonRepair`) | updated 0 (기능 활성, 재발 가능) |
| `archive:renumbered` | 번호 개편 무효화 | 0 |
| `archive:updateSourceHtml` | **dead — enum 정의 완료 후 사용처 0** | 0 |

### 2.2 Dispatch path (single choke point)

```
appendTrackedDiffEvent        notice-archive.service.ts:3397  (source 고정 전달)
appendExplicitEventWithDiff   notice-archive.service.ts:3710
  └→ ChangeTrackingService.dispatchChangeNotification  change-tracking.service.ts:879
       gates (현재 3종):
         1. notificationSuppressionDepth > 0            (L886, bootstrap pipeline 전용)
         2. eventType === 'created'                     (L893)
         3. source prefix ∈ NOTIFICATION_SUPPRESSED_SOURCE_PREFIXES = ['bootstrap:']   (L197/L917)
  └→ queuedChangeNotifications  (+100ms timer flush / collection end flush)
  └→ NotificationBatchService.processChangeNotificationBatch
  └→ executeChangeNotificationBatch   notification-batch.service.ts:445
       4-way split:
         sourceDeleted     : source === 'archive:source-missing' OR (lifecycleStatus + sourceDeletedAt)
         noticePeriodEnded : changedFields includes 'isDone'
         nsmToPal          : isNsmToPalTransition (contentId 'added')
         regular           : 그 외 → "변경 추적" 임베드 + web push
```

- 디스패치 호출부는 `notice-archive.service.ts` 2곳(3470 tracked, 3764 explicit)
  이 유일 — **게이트 1곳 추가로 전체 커버 가능**.
- bootstrap pipeline만 suppression(`archive-sync.service.ts:268~358`),
  **cron 경로(`cronjobs.service.ts:422 runIsDoneSync('cron')`)는 suppression 없음**.

### 2.3 기존 제외 메커니즘 (참고 패턴)

1. 전역 suppression depth (`begin/endChangeNotificationSuppression`)
2. `created` 이벤트 skip (logAndBridge DEBUG로 관측 가능하게 남김)
3. `bootstrap:` 소스 prefix skip

## 3. Measurement (read-only query on `backend/lawcast.db`, 2026-10-09)

### 3.1 이벤트/필드 분포

- `archive:isDoneSync` 19,424건 중 **19,378건(99.7%)이 isDone 단일 필드** — 나머지 46건은 레거시 코드가 만든 다필드 이벤트(현 코드는 `{...baseline, isDone}`라 단일 필드 고정).
- `archive:upsert`가 `isDone`을 뒤집은 사례: **0건** → **마감(noticePeriodEnded) 알림은 isDoneSync 하나가 전담**.
- `archive:updateNsmHtmlAndDetail` 203건 필드: `proposalReason` modified 139, `proposalDate`/`proposalSession` modified 74, `billNumber`/`proposer`/날짜 added 39.
- `archive:upsert` updated 중 제안이유 단일 변경 3,551건(실제 소스 수정 → 알림 정당), contentId 단일 추가 331건(NSM→PAL 전용 임베드).

### 3.2 시간 분포 (이상치)

| 날짜 | isDoneSync 이벤트 |
| --- | --- |
| **2026-08-10** | **17,224 (하루 폭주 — 백필/일괄 플립 증거)** |
| 2026-08-02 | 283 |
| 2026-08-23 | 268 |
| 상시 | 하루 68~126 |

- `updateNsmHtmlAndDetail`은 하루 1~22건 수준의 저빈도 백필.

## 4. 후보 추림

### Tier A — 제외 대상 (확실한 내부 백필/복구) **권고: 제외**

| # | source / 규칙 | 근거 | 알림现状 |
| --- | --- | --- | --- |
| A1 | `archive:updateNsmHtmlAndDetail` | ① 발생처가 `backfillMissingSnapshotArtifacts`(`archive-orchestrator.service.ts:334`)와 제안이유 재시도 `fetchAndUpdateProposalReason`(L993)로 **전부 백필 파이프라인**. ② NSM contentId 가드(`updateNsmHtmlAndDetail` early-return) 때문에 항상 우리 측 데이터 보강 맥락. ③ **이중 알림 증거**: 재시도 성공 시 같은 bills에 대해 `crawling-scheduler-proposal-retry.ts:425`가 `notificationOrchestratorService.sendNotifications()`(정규 알림)까지 보냄 → "변경 추적: 제안이유/입법예고 기간 변경"이 중복 도착. | regular 임베드로 발송 중 |
| A2 | `archive:likmsProposalReason` | `appendLikmsProposalReasonRepair` 주석에 명시된 "repair" 전용 경로(PAL 제안이유 복구). 값 동일하면 아예 이벤트를 안 남기게 되어 있어(중복 방지) 생길 이벤트는 100% 최초 복구 → 알림 가치 없음. | regular 임베드로 발송 예정 (DB 0건) |
| A3 | `archive:updateSourceHtml` | enum에만 정의, 사용처 0(dead). 알림 영향 없음 — **정리 후보**(삭제 또는 구현 연결 시 재검토). | 없음 |

### Tier B — 조건부 제외/가드 (의사결정 필요) **권고: 유지 + 폭주 가드**

| # | 대상 | 분석 | 권고 |
| --- | --- | --- | --- |
| B1 | `archive:isDoneSync` (19,424) | isDone 뒤집기 = **입법예고 마감/처리완료라는 실질 정보**이고 upsert는 isDone을 한 번도 뒤집지 않음 → **전면 제외하면 마감 알림 채널이 통째로 사라짐**. 다만 2026-08-10 하루 17,224건 폭주는 "실제 마감"이 아니라 DB 복원/일괄 플립성 백필로, 그날 알림 채널이 폭주했을 가능성 높음. | **유지하되 런 단위 폭주 가드**(§5.2) 추가 |
| B2 | `archive:upsert` 전량 `removed`-only 이벤트 (소스삭제 아님: noticePeriod 21, referralDate 21, contentCommittee 4) | 일시적 파싱 실패로 필드가 지워졌다가 다음 크롤에서 복원 → "변경" 알림이 2회 왕복. 볼륨 작음. | Phase 3에서 관찰 후 결정 (코드 복잡도 대비 효과 작음) |
| B3 | contentId 단일 추가(NSM→PAL) 331건 | 이미 전용 임베드(`sendDiscordNsmToPalTransitionBatch`)가 있음. "우리가 PAL 페이지를 처음 발견"한 것이라 실질 변경은 아니나, 링크·본문 출처가 바뀌는 사용자 체감 정보. | 유지 권고 (전용 메시지가 이미 존재) |

### Tier C — 유지 (실질 변경)

- `archive:upsert` updated 6,475건 (제안이유 3,551, 위원회 2,069, 제목 862 …)
- `archive:source-missing` 881건 (삭제 감지 — 2중 확인 보장, 전용 임베드)
- `archive:renumbered` (번호 개편 INVALIDATED)
- `created` / `bootstrap:` — 이미 dispatch 게이트가 처리

## 5. Proposed design

### 5.1 Phase 1 — dispatch 게이트에 소스 제외 Set 추가 (Tier A)

위치: `change-tracking.service.ts` `dispatchChangeNotification`(L917 소스 prefix 게이트 바로 옆).

```ts
// Sources that record internal backfill/repair runs. The diffchain event is
// still appended (timeline, chain audit and summary reset depend on it);
// only the notification is skipped because no user-visible bill change
// happened (see agent_memories/19-change-notification-exclusion/plan.md).
private readonly NOTIFICATION_EXCLUDED_SOURCES: ReadonlySet<NoticeChangeSource> =
  new Set([
    NoticeChangeSource.ARCHIVE_UPDATE_NSM_HTML_AND_DETAIL,
    NoticeChangeSource.ARCHIVE_UPDATE_LIKMS_PROPOSAL_REASON,
  ]);
```

게이트 추가 순서 (suppression → created → prefix → **excluded source**):

- skip 시 `logAndBridge` DEBUG 1줄(created skip 패턴 L893과 동일)로 **관측 가능하게** — 주석 처리된 기존 소스 skip 로그(L909~930)와는 분리 유지.
- prefix 게이트와 분리한 이유: prefix는 "계열 전체"(`bootstrap:`), Set은 "명시된 소스 단위" — 의미가 다르고 추가/제거가 데이터 마이그레이션 없이 가능.
- **이벤트 append, summary reset, queue 외부 로직에는 손대지 않음** → `notice-archive.service.spec.ts`의 mock 기반 테스트는 영향 없음.

효과: Discord + web push + digest 딜리먼트까지 한 게이트에서 모두 차단
(디제스트에 백필 payload가 섞여 "변경 N건 요약"이 과대 집계되는 문제도 동시 해소).

### 5.2 Phase 2 — isDoneSync 런 단위 폭주 가드 (Tier B1)

**안전한 허용치 근거**: 일별 최대 283건(정상 상한), 이상치 17,224건(17,224 ≫ 임계).

설계 (suppression 프리미티브 재사용, 새 메커니즘 최소화):

1. `reconcileIsDonePhase`(`archive-sync-phase-executors.ts:1351`)를 **수집→판정→적용** 2-pass로 재구성:
   - pass 1: done 목록 전체 페이지를 수집(현재 페이지 단위 크롤은 유지, nums만 누적 — 17k ints이라 메모리 무해).
   - `markNoticesDoneByNums`가 이미 하는 `summary_state WHERE isDone=false` 조회 결과 수를 **미리 센다** (dry-count: `find` only, update 없음).
   - count > `IS_DONE_SYNC_NOTIFY_LIMIT`(기본 500, 상수 주석에 근거 명기)이면
     `beginChangeNotificationSuppression()` → mark → `endChangeNotificationSuppression()`
     + `logAndBridge` WARN("대량 마감 전환 감지 — 알림 생략, 이벤트는 기록됨")로 운영자에게 통지.
   - 임계 이하면 현행 그대로(알림 정상 발송).
2. **권장하지 않는 대안**: flush 배치 크기 기준 임계(플러시가 페이지 크기로 쪼개져 trip 안 됨, 100ms 타이머 의존) — 측정 불안정으로 제외.
3. `revertNoticesDoneByNums`(isDone false 전환)는 **생산 경로 없음**(spec 전용) — 되살릴 경우 `noticePeriodEnded` 임베드로 잘못 라우팅되므로, 되살릴 때 재검토 표기를 남긴다.

### 5.3 Phase 3 — 보류 (의사결정 후)

- B2 removed-only 왕복 알림, B3 contentId 전용 알림 유지 여부.
- `archive:updateSourceHtml` dead enum 정리.

## 6. 영향 파일과 테스트 계획

| 파일 | 변경 |
| --- | --- |
| `backend/src/modules/change-tracking/change-tracking.service.ts` | Phase 1: `NOTIFICATION_EXCLUDED_SOURCES` + 게이트 + DEBUG 브리지 |
| `backend/src/modules/crawling/utils/archive-sync-phase-executors.ts` | Phase 2: `reconcileIsDonePhase` 2-pass 재구성 |
| `backend/src/modules/change-tracking/change-tracking.service.spec.ts` | 신규 2건: 소스 제외(백필 2종 skip) + 제외 건 다음에 이어지는 upsert payload는 정상 발송(대조). 기존 NSM→PAL/ auto-flush 테스트가 백필 소스를 편의 payload로 쓰던 것을 `ARCHIVE_UPSERT`로 교체 |
| `backend/src/modules/crawling/fault-isolation.spec.ts` (Phase 2 실제 위치) | 공고: 폭주 가드(임계 초과 → begin/end suppression 호출 + flip은 그대로 수행, status `idle`), 임계 이하면 미호출. 계획 초안의 `notification-batch.service.spec.ts`는 §5.2 설계(억제가 소스 쪽)에 맞지 않아 이쪽으로 이동 |
| `backend/src/e2e/diffchain.e2e-spec.ts` | `appendLikmsProposalReasonRepair` 케이스(L549)에 "이벤트는 append됨 + `processChangeNotificationBatch` mock에 해당 payload 없음" 단언 추가 |
| `agent_memories/repo/backend-testing-notes.md` | 회귀 함정: "제외는 dispatch 게이트에서만 — append/summary reset 금지" 기록 |

검증 게이트 (변경 후 전수):

```bash
cd backend && npm run lint && npx tsc --noEmit && npm run build && npm test
RUN_SNAPSHOT_BROWSER_E2E=true npm run test:e2e   # exit 0 필수 (9 suites)
```

파일 변경 없는 CI 경로(`npm test`) 영향 없음 — 게이트는 기존 `created`/`bootstrap` skip과 동일 구조의 상수 추가.

## 7. 실행 순서 (2026-10-09 구현 완료 — Phase 1·2)

1. **Phase 1** (Tier A) ✅: `NOTIFICATION_EXCLUDED_SOURCES` 상수 + dispatch 게이트 + DEBUG 브리지 + 단위 테스트 2건 추가·2건 소스 교체 → 해당 슈트 31/31 통과.
2. **Phase 2** (B1 가드) ✅: `NoticeArchiveService.countNotDoneByNoticeNums` dry-count + `reconcileIsDonePhase` fetch-all→count→mark 2-pass + `IS_DONE_SYNC_NOTIFY_LIMIT = 500` + 초과 시 suppression(try/finally) + WARN 브리지 → fault-isolation 슈트 39/39 통과.
3. 기록 ✅: `backend-testing-notes.md`에 제외 게이트 불변식·mock 동기화·Jest 30 `--testPathPatterns` 리네임 기록 + 본 문서에 구현 위치 반영.
4. **Phase 3**는 별도 결정 후 착수 (Q2 폭주 시 '완전 생략+WARN' 채택으로 잠정 결정).

## 8. Risks and open questions

- **Q1 (필요한 결정)**: isDoneSync 알림 유지(권고) vs 제외. 제외 시 마감 알림 채널 소멸(upsert가 isDone 0건) — 대안은 "일반 변경 임베드로 격하"도 아님(어차피 isDone이면 noticePeriodEnded로 라우팅됨).
- **Q2**: 폭주 시 "알림 완전 생략 + 운영자 WARN" vs "정상 건수만 발송 + 초과분 생략". 전자가 구현 단순·안전.
- **Q3**: UI 변경목록(`/notices/changes`)에서도 백필 이벤트를 숨길지 — 현재 `excludeIsDoneEvents` 플래그처럼 쿼리 파라미터가 이미 있는 패턴을 따를 수 있으나 **본 계획 범위 밖**.
- 위험: dispatch 게이트 순서 실수로 created/prefix skip을 깨는 회귀 → 대조 테스트(upsert payload는 반드시 발송) 필수.
- 위험: Phase 2 2-pass 재구성이 done 크롤 페이지 단위 리트라이/지연 백오프를 흡수하도록 `fetchDonePageWithRetry`는 pass 1에 그대로 보존해야 함.
