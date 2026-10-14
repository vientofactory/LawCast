# LIKMS 제안이유 백로그 대비 15분 요약 백필 처리량 실측

## 1. 질문과 결론

"15분 주기 요약 백필이 LIKMS 제안이유 백로그를 실제로 따라잡는가"를 `backend-v1.15.6`
프로덕션(`10.20.0.1`, 컨테이너 기동 `2026-10-14 11:59:38 UTC`, 실측 `14:50~15:10 UTC`)에서
배치 크기·처리량 근거로 측정했다.

**결론: 요약 백필 자체는 병목이 아니다. 같은 틱의 `proposalReason` 드레인이 13틱 중 0회
실행되어 백로그는 0행 진행 중이고, 실행되더라도 후보 선택이 선입선출 head-of-line으로
막혀 있어 실제 대상 180행에 도달하지 못한다.**

| 항목 | 값 | 근거 |
| --- | --- | --- |
| 요약 백필 패스 실행 | 13틱 중 12회 (1회 스킵) | `Summary backfill staged -` 12줄 + 스킵 1줄 |
| 패스당 처리량 | 315행 / 25~27초 (평균 ≈26초, ≈12행/s) | 13패스 전부 적용 배치 63개 × 5행 |
| 패스당 판정 변경 | 0행 | `ready` 21,154·`not_supported` 340 불변 |
| 제안이유 드레인 실행 | 13틱 중 **0회** | 로그 0줄 + Redis 큐 키 부재 |
| 요약 생성 실측 비용 | 16.2~50.2초/건 (중앙값 ≈25초) | Ollama GIN 로그 69건 |
| 제안이유 도착률 (7일) | 294건 ≈ 1.75건/h | `proposalReason` 변경 이벤트 |
| 백로그 | 925행 (그중 실대상 180행) | 후보 술어 일치 카운트 |

## 2. 배치·주기 설정 (코드·환경 근거)

- **틱**: `PROPOSAL_REASON_BACKFILL_DRAIN: '9-59/15 * * * *'`
  (매시 9/24/39/54분, `config/app.config.ts:491`, 배선 `cronjobs.service.ts:417`).
- **틱의 두 반쪽** (`cronjobs.service.ts:420` `handleProposalReasonBackfillDrain`):
  1. NSM/LIKMS **제안이유 드레인** `handleProposalReasonBackfillCron`
     (`crawling.service.ts:59` → `crawling-scheduler.service.ts:207`) —
     가드 `shouldSkipProposalReasonBackfillCron`(`cronjobs.service.ts:235`) =
     archive-sync write-heavy **OR** `isSchedulerBusy({ includeBackground: true })`.
     스킵은 프로덕션 레벨로 로그되지 않는다(`visibleInProduction` 미지정).
  2. **요약 백필** `runSummaryBackfill('proposal-reason-cron')` —
     가드 `shouldSkipSummaryBackfillCron`(`cronjobs.service.ts:273`) = archive-sync
     write-heavy만. 스킵 시 프로덕션 로그 1줄(§38 §10에서 분리한 결과).
- **드레인 배치**: `limit = SUMMARY_BACKFILL_BATCH_SIZE = 20`
  (`crawling-scheduler.service.ts:215`), 큐 `MAX_SIZE 5000`, 시도 상한 5회, 나이 상한 24h
  (`app.config.ts:376-378,415`). 성공 시 요약을 **인라인 생성**(`crawling-scheduler-proposal-retry.ts`
  drain 루프의 `generateSummaryForNotice`).
- **요약 백필 배치**: 스테이징 20행, 적용 5행 + 배치 간 250ms, 동시성 1
  (`OLLAMA_CPU_MODE=true` → `SUMMARY_BACKFILL_CPU_FRIENDLY_MODE`, `app.config.ts:429-450`).
  `OLLAMA_TIMEOUT=1800000`.
- **프로덕션 env 확인**: `CRAWLING_NSM_SOURCE=likms`, `CRAWLING_NSM_ENABLED=1`,
  `CRAWLING_NSM_DELETION_DETECTION_ENABLED=0`, `OLLAMA_CPU_MODE=true`,
  `OLLAMA_MODEL=exaone3.5:2.4b`, 요약 백필 배치 override 없음(기본 20/5).

## 3. 실측: 요약 백필 패스는 정상 주기로 돈다

13틱(12:09~15:09 UTC) 중 12회 실행, 각 패스가 동일하게:

```
Summary backfill staged - scanned=340 stagedPending=315 retryScanned=0 stagedRetry=0 queue=0
```

- 스킵 1회는 `12:09:00 UTC`, 사유 `runningWriteHeavyActivities=integrity check`.
- 13패스 전부 적용 배치가 **정확히 63개**(63×5 = 315행), `requested=5, removed=5, failed=0`.
  배치 로그의 첫/마지막 타임스탬프 스팬은 **25~27초**(패스별 25.0/25.0/26.0/26.0/27.0/25.0/27.0/27.0/
  27.0/25.0/26.0/27.0/26.0, 평균 ≈26초) → **≈12행/s**. 250ms×63 = 15.8초가 순수 대기이므로
  실제 행 처리는 약 32ms/행이며, `queue=0`을 찍는 `staged` 로그가 마지막 배치와 같은 초에 나온다
  (CPU-friendly 모드가 워커를 await하므로 드레인 종료 후 스테이징 라인이 출력된다).
- **행이 싸게 처리되는 이유**: 315행이 전부 `contentId IS NULL`이라 라이브 조회 없이
  즉시 `not_supported`가 된다. 이 경로는 Ollama를 호출하지 않는다(`summary.total = 0`).
- 12패스 동안 `ready` 21,154 / `not_supported` 340 / `not_requested` 0 / `unavailable` 0 불변
  → 판정 변경 0행. 즉 백필은 "돌고 있지만 옮기는 것이 없다".

## 4. 실측: 제안이유 드레인은 한 번도 돌지 않았다

세 가지 독립 근거:

1. **로그 0줄**: 컨테이너 기동 이후 `proposalReason retry cron:` 0건, `Cache not initialized
   yet, skipping proposalReason` 0건. 대조군으로 요약 백필 스테이징 12줄·스킵 1줄이 있다.
   (드레인이 돌면 `proposalReason retry cron: queue before=..., seeded=...` 를 반드시 남긴다.)
2. **Redis 큐 키 부재**: DB 7키 중 `crawling:proposalReasonRetryQueue` 없음(`EXISTS` = 0).
   `enqueue`는 항상 `setQueue`를 쓰고 TTL이 48h이므로, 한 번이라도 시드했다면 키가 남는다.
3. **크론 상태**: `proposalReason backfill drain | idle | last= 2026-10-14T14:54:37Z` —
   틱 자체는 fire하지만 반쪽만 실행된다.

**차단 원인 규명**: 12개 실행 틱 중 11개에서 요약 백필 반쪽이 돌았으므로 그 시점
`archiveState.isWriteHeavyPhaseRunning`은 false다. 그런데 같은 틱의 드레인은 실행되지 않았다.
`skipNsmReasonDrain`은 이 조건에 `isSchedulerBusy({ includeBackground: true })`를 **추가로**
요구하므로, **11개 틱 전부에서 크롤 스케줄러가 busy였다**고 귀결된다(PAL 크롤 10분 주기
`2-59/10 * * * *` + NSM pending 20분 주기 + 백그라운드 후속 작업). 틱이 15분 주기라
:09/:24/:39/:54가 크롤/후속 창에 계속 겹친다 — §38 §10이 요약 백필에서 제거한 바로 그
구조가 드레인에는 남아 있고, 그 스킵은 debug 레벨이라 **조용히 굶는다**.

## 5. 실측: 실제 요약 1건의 비용 (Ollama)

`lawcast-ollama` GIN 로그 `POST /api/generate` 69건(최근 24h, 전부 11:17 이전 = LIKMS 전환 전):

- 전체 소요 **16.2 ~ 50.2초** (표본 중앙값 약 25초), 슬롯 1개 직렬.
- 프롬프트 평가 8.0~41.5초 / 200~968 토큰 (21~25 tok/s) — 비용 대부분이 프롬프트 평가.
- 즉 요약 처리 상한은 **약 2.4건/분 ≈ 144건/h**.
- 백엔드 `ollama.summary.total = 0` (재기동 이후 생성 시도 0건) — 드레인이 안 도니 요약도 0.

## 6. 실측: 백로그 구성

후보 술어(`notice-archive-maintenance-support.ts:60-115`) 그대로 카운트(0.15초):

```sql
lifecycle_status = 'active'
AND (proposal_reason IS NULL OR TRIM(proposal_reason) = '')
AND NOT EXISTS (# proposalReason 변경 이벤트 중 비어 있지 않은 after_value)
```

- **925행**. 나이: `>90d` 92, `30-90d` 379, `7-30d` 158, `<7d` 296 → 649행이 이미 24h 초과
  (드레인 큐의 나이 상한을 넘긴 채 대기).
- `contentId IS NULL` **745행**(noticeNum 20490~2221897), `contentId` 있음 **180행**(2219108~2221827).
- 요약 상태 교차표: `not_supported` 340행 + `ready` 588행이 제안이유 공백(합 928, 그중 3행은
  비활성/필터 차이로 후보 술어 밖).
- **제안이유 도착률**: `field_path='proposalReason'` 이벤트가 7일간 294건(≈42건/일 ≈ 1.75건/h),
  마지막은 `2026-10-14 09:49:41 UTC` — LIKMS 전환(11:59 UTC) 이후 **0건**.

## 7. 두 번째 결함: 선입선출 head-of-line

후보 쿼리는 `ORDER BY na.noticeNum ASC LIMIT :limit`이고, **시도 이력 필터가 없다**
(큐에서 제거되면 시도 횟수도 사라진다). 그런데 정렬 선두가 전부 죽은 행이다:

- 선두 20행(noticeNum 20490~21076): **20/20이 `contentId IS NULL`, 20/20이 의안번호 없음**.
  내용은 `국회의원사임서`, `사직의건`, `감사문발송의건`, `결의안` 등 **제안이유가 존재하지 않는
  절차 안건**이다.
- 첫 실대상(`contentId` 보유, noticeNum 2219108) 앞에 **267행**이 줄 서 있다.
- `contentId IS NULL` 행의 복구는 활성 소스가 likms이므로 `captureLikmsDetailFull` →
  `resolveLikmsDetailUrl`을 타는데, likms에 상세 페이지가 없으면 throw → `fetchAndUpdateProposalReason`이
  null 반환 → 드레인 루프가 그 항목을 **즉시 큐에서 제거**한다(`proposalReason retry: empty
  proposalReason ... - dropping`). 다음 틱에 후보 쿼리가 **같은 20행을 다시 시드**한다.
- 결과: 실행되더라도 틱당 **신규 진행 0행**이고 180개 실대상은 영원히 도달 불가.
  (§38의 "짧은 페이지를 끝으로 오해" 계열과 같은 부류의 커서 웨지이지만, 원인은
  **정렬 선두에 영구 미해결 행이 고정**되는 것.)

## 8. 용량 vs 수요

| 경로 | 상한 | 근거 |
| --- | --- | --- |
| 제안이유 공급(드레인) | 20행/틱 × 4 = **80행/h** | 시드 `limit` |
| 요약 생성(Ollama) | **≈144건/h** | 25초/건, 슬롯 1 |
| 실측 수요 | **≈1.75건/h** | 7일 294건 |

- 드레인 1틱 비용 = 20 × (상세 캡처 + 요약 ≈25초) ≈ 600초 = 10분 < 15분 주기 → **주기는
  충분하다.** 925행 전량은 약 46틱(≈11.5시간), 실대상 180행은 약 9틱(≈2.25시간)이면 소진된다.
- 따라서 "따라잡지 못하는" 원인은 **용량이 아니라 (a) 크롤 가드로 인한 무실행,
  (b) 선두 고정 행으로 인한 0 진행**이다.

## 9. 재현 명령

```bash
# 1) 드레인 실행 여부 (0이면 한 번도 안 돎)
ssh root@10.20.0.1 'docker logs lawcast-backend --since 12h 2>&1 | grep -c "proposalReason retry cron:"'
ssh root@10.20.0.1 'docker exec lawcast-redis-1 redis-cli EXISTS crawling:proposalReasonRetryQueue'

# 2) 요약 백필 패스 (틱마다 scanned=340/stagedPending=315, queue=0 인지)
ssh root@10.20.0.1 'docker logs lawcast-backend --since 12h 2>&1 | grep "Summary backfill staged -"'

# 3) Ollama 실비용 (POST마다 총 소요·프롬프트 평가 시간이 찍힌다)
ssh root@10.20.0.1 'docker logs lawcast-ollama --since 24h 2>&1 | grep "POST.*generate" | tail'

# 4) 백로그 (0.15초)
DB=/var/lib/docker/100000.100000/volumes/lawcast_lawcast_db/_data/lawcast.db
sqlite3 "$DB" "SELECT COUNT(*) FROM notice_archives na WHERE na.lifecycle_status='active'
  AND (na.proposalReason IS NULL OR TRIM(na.proposalReason)='') AND NOT EXISTS (
    SELECT 1 FROM notice_change_events e JOIN notice_change_details d ON d.event_id=e.id
    WHERE e.notice_num=na.noticeNum AND d.field_path='proposalReason'
      AND d.after_value IS NOT NULL AND TRIM(d.after_value)!='');"
```

## 10. 남은 것 (이 기록은 측정만 하고 코드는 바꾸지 않았다)

- **미수정**: 드레인 가드(크롤 busy) 분리 여부 — §38 §10처럼 요약 백필만 뗀 것과 대칭으로
  결정해야 한다. 단 드레인은 브라우저 세션을 쓰므로 무조건 떼면 안 되고, 최소한 스킵을
  프로덕션 레벨로 남겨야 조용한 굶주림이 사라진다.
- **미수정**: 후보 커서를 시도 이력 기준으로 전진시키기(예: 시도 횟수/최근 시도 시각 컬럼,
  또는 큐 eviction을 후보 쿼리에 반영). 지금은 영구 미해결 267행이 실대상 180행을 막는다.
- **미검증**: 위 두 수정 없이는 LIKMS 전환 후 제안이유 도착률 자체가 측정 불가(0건)라
  "전환 후 크론 사이클의 정상 동작"은 §34 이후에도 여전히 미검증이다.

## 11. 수정 - 후보 커서를 시도 이력 기준으로 전진 (미릴리스)

§7의 head-of-line 결함을 고쳤다. 후보 페이지는 이제 **시도 이력**으로 정렬되고, 드레인이
자기가 시도한 행을 되짚어 기록한다.

**변경 파일**

- `backend/src/migrations/202610150001-add-proposal-reason-retry-tracking.migration.ts` (신규,
  `src/migrations/index.ts`에 등록): `notice_archives`에 `proposal_reason_retry_count`
  (integer NOT NULL DEFAULT 0)와 `proposal_reason_retried_at` (datetime) 추가. 기존 행은
  count 0 / NULL = "아직 시도 안 됨"으로 읽히므로 별도 백필이 필요 없다. 두 칼럼 모두
  불변성 트리거의 unchanged 목록 밖이라(list-sighting 스탬프와 같음) 트리거 마이그레이션이 필요 없다.
- `backend/src/modules/notice/notice-archive.entity.ts`: 두 칼럼 매핑 + 왜 필요한지 문서화.
- `backend/src/modules/notice/utils/notice-archive-maintenance-support.ts`:
  `ORDER BY proposal_reason_retry_count ASC, proposal_reason_retried_at ASC, noticeNum ASC`
  (`noticeNum ASC`는 안정적인 페이지를 위한 3차 키) + `recordProposalReasonAttempts()`
  (400행 청크, DB측 `+ 1` 식으로 증가시켜 동시 패스의 갱신 유실을 피한다).
- `backend/src/modules/notice/notice-archive.service.ts`: `recordProposalReasonAttempts`
  래퍼. `backend/src/modules/crawling/utils/crawling-scheduler-proposal-retry.ts`: 드레인
  루프가 시도한 noticeNum을 모아 `finally`에서 스탬프(중단된 드레인도 진행 상황을 남긴다),
  `proposalReason retry: recorded N attempt(s) for candidate rotation` 로그, 스탬프 실패는
  warn 후 삼킨다(스탬프 유실은 재시도 1회 비용이지만, 예외를 던지면 이미 이유·요약을 만든
  드레인 결과를 버리게 된다).

**의도한 의미**

- 시도 0회 행(신규 도착 후보 포함)이 항상 먼저 → 새로 온 후보가 이미 실패한 행 뒤에 서지 않는다.
- 같은 시도 횟수 안에서는 오래 전에 시도한 행이 먼저 → 선두가 고정되지 않고 로테이션된다.
- **제외(exclusion)는 하지 않는다.** 이유는 나중에 도착할 수 있으므로(이 백필의 존재 이유)
  영구 제외하면 그 케이스를 놓친다. 대가는 미해결 행 1개당 사이클당 1회 재시도인데,
  실측 상한 20행/틱 = 80행/h 대 수요 1.75건/h이므로 여유가 크다.

**검증**

- 신규 `backend/src/modules/notice/notice-archive-proposal-reason-retry.spec.ts` (실 SQLite +
  전체 마이그레이션 체인, 7건): 프로덕션 형상(선두 20행 미해결 + 뒤 2행 실대상)에서 ① 스탬프가
  없으면 페이지가 매번 같은 선두를 반환(웨지 재현, 구버전과 동일 동작) ② 스탬프 후 실대상이
  페이지 앞으로 온다 ③ 같은 페이지 안에서 시도한 행이 뒤로 밀린다(로테이션) ④ 신규 도착 후보가
  실패 행보다 먼저 온다 ⑤ 시도 횟수 누적·최신 시각 유지 ⑥ 비정상 입력(0/음수/소수) 무시
  ⑦ 체인으로 이유가 도착한 행은 여전히 제외.
  **판별력 확인**: 정렬을 구버전 `noticeNum ASC`로 되돌리면 ②③④ 3건이 실패하고 나머지 4건은
  통과한다(측정).
- `crawling-scheduler-proposal-retry.spec.ts` +2: 이유를 못 찾아 큐에서 버려진 행도 시도로
  기록된다(이게 다음 페이지를 밀어낸다), 기록 실패가 드레인 결과를 버리지 않는다.
- `archive-immutability-trigger.spec.ts` +3: 두 칼럼의 기본값(0/NULL), 스탬프 UPDATE 허용 +
  누적 증가, 불변 칼럼과 함께 묶은 스탬프는 여전히 거부.
- 마이그레이션의 프로덕션 경로(행이 있는 테이블)를 raw SQLite로 확인: 기존 행이 0/NULL로 읽히고
  `+ 1` 증가가 동작한다.
- **비용 측정(임시 벤치, 측정 후 삭제)**: 프로덕션 형상(21,494 아카이브 / 후보 925 / 그중 745가
  이미 스탬프됨)에서 구 정렬 29.700ms vs 신 정렬 29.785ms 중앙값 — 정렬 키 추가 비용이 노이즈
  이하이고 비용은 NOT EXISTS 서브쿼리가 지배한다. 그래서 **새 인덱스는 추가하지 않았다**(쓰기 비용만 늘어난다).
- 게이트: prettier 0, lint 0, `tsc --noEmit` 0, build 0, `npm test` **82 suites / 1145 tests**,
  `npm run test:e2e` 46 passed / 9 skipped, comment-language 0.

**중요한 한계 - 이 수정만으로는 프로덕션 백로그가 움직이지 않는다**

드레인 자체가 여전히 13틱 중 0회 실행된다(§4의 크롤 busy 가드). 이 수정은 **드레인이 실행될 때**
선두 고정 없이 전진하게 만들 뿐이므로, 가드 수정과 함께 배포되어야 925행이 실제로 소진된다.
순서상 두 수정은 상보적이며, 지금 배포하면 동작 변화는 "다음에 드레인이 돌 때 실대상 180행이
실제로 시도된다"까지다.

**미릴리스**: backend-v1.15.6은 이미 배포된 버전이라 이 변경은 릴리스 대기 중인 워킹트리
(§38 §12~14와 같은 상태)에 포함된다. 버전 범프·PR·배포는 하지 않았다.

## 12. 수정 - 드레인 가드를 브라우저 임대 기준으로 좁히고, 스킵 대신 유한 대기 (미릴리스)

§4/§10의 "드레인은 한 번도 돌지 않는다"를 다시 실측하고 고쳤다.

**재실측 (2026-10-14, 컨테이너 기동 `11:59:38Z` ~ 관측 `15:51Z` = 15틱)**

| 항목 | 값 | 근거 |
| --- | --- | --- |
| 드레인 실행 | **0 / 15틱** | `proposalReason retry cron:` 0줄, `proposalReason retry` 접두 로그 자체가 0줄 |
| 같은 틱 요약 백필 | **15 / 15틱** | `Summary backfill staged -` 15줄 |
| 후보 술어 일치 풀 | **334행** (재사용 가능 20 + 소스 없음 314) | 3개 조건 전체 적용(§14의 925행과 다름) |

요약 반쪽이 15틱 **전부** 실행됐다는 것은 그 15틱에서 `isWriteHeavyPhaseRunning`이 false였다는
뜻이고, 같은 틱의 드레인만 0회라는 것은 차별 조건이 `isSchedulerBusy({includeBackground: true})`
하나뿐임을 뜻한다. §4의 11/11 추론이 15/15로 재확인된 셈이다.

**왜 그 조건이 틀렸나**

`includeBackground: true`는 **등록된 작업이 있으면** true다. 그 안에는 브라우저를 전혀 쓰지 않는
후속 작업(요약 적용 드레인, 무결성 스캔, 캐시 반영)이 섞여 있고, 브라우저를 쓰는 작업도 임대로
직렬화된다. 즉 "백그라운드 작업이 있음"은 자원 신호가 아니다. 실제로 드레인이 경합하는 자원은
**브라우저 임대**와, 알림 지연에 민감한 **크롤 fast path**뿐이다.

**변경 파일**

- `backend/src/modules/crawling/browser-lease-manager.service.ts`: `hasActiveLease()` 추가 —
  `activeLeases > 0`만 보는 저렴한 신호(`getDebugState()`의 `ps` 스캔과 구분).
- `backend/src/modules/crawling/crawling-core.service.ts`: `isBrowserLeaseActive()` 위임 —
  스케줄러가 임대 관리자를 직접 알 필요 없이 경합 여부를 묻는다.
- `backend/src/modules/crawling/crawling-scheduler.service.ts`:
  `collectProposalReasonDrainBlockers()`(pal crawl fast path / pending crawl fast path /
  열린 브라우저 임대) + `waitForProposalReasonDrainWindow()`(유한 대기) 추가, 드레인 진입 시
  대기. 대기 후 실행하면 `proposalReason retry cron: browser freed after Nms, draining now`,
  예산을 다 쓰고도 못 비면
  `proposalReason retry cron: deferred this tick - <blockers> held the browser for Nms` (warn,
  브리지는 DEBUG로 두어 Discord 스팸 없이 프로덕션 로그에만 남긴다).
- `backend/src/config/app.config.ts`: `PROPOSAL_REASON_DRAIN_WAIT_MS`(기본 300000, env
  `ARCHIVE_SYNC_PROPOSAL_REASON_DRAIN_WAIT_MS`)와 `PROPOSAL_REASON_DRAIN_WAIT_POLL_MS`
  (기본 10000) 추가. 폴 하한 250ms는 잘못된 설정이 스핀으로 바뀌지 않게 하는 장치다(프로브는
  boolean 읽기 2회).
- `backend/src/modules/scheduling/cronjobs.service.ts`: `shouldSkipProposalReasonBackfillCron`
  → `shouldSkipNsmReasonDrainCron`으로 이름과 의미를 좁힘. 이제 archive-sync write-heavy activity
  만 스킵 사유이고 스킵은 **프로덕션 레벨 로그**다(요약 백필과 같은 정책).

**의도한 의미**

- 브라우저 임대가 비어 있으면 **즉시** 실행한다(대기 0ms).
- 크롤 fast path나 열린 임대가 있으면 **버리지 않고 기다린다.** 드레인은 마감이 없는 백필이고,
  한 번 건너뛴 틱은 그 틱이 처리했을 모든 진행을 영구히 잃는다. 대기 상한은 틱 간격의 1/3로,
  다음 틱이 시작하기 전에 끝난다(그 사이에 이전 드레인이 아직 돌면 다음 틱은 `drain()`의
  재실행 조인으로 합류한다).
- archive-sync write-heavy 구간은 DB 쓰기 작업이라 여전히 양보하고, 그 사실을 로그로 남긴다.

**검증**

- `crawling-scheduler.service.spec.ts` 신규 5건: ① 임대가 잠깐 열려 있으면 대기 후 **실행**(시드까지
  도달) ② 예산 안에서 여러 번 재확인(단일 프로브 스킵과의 차이) ③ 크롤 fast path가 blocker로
  이름에 남음 ④ 아무것도 없으면 즉시 시작 ⑤ 캐시 초기화 전에는 대기 자체를 하지 않음.
  **대조군 측정**: 대기 루프를 "첫 프로브 1회"로 되돌리면 ①②가 실패하고 ③④⑤는 통과한다.
- `cronjobs.service.spec.ts` 재작성 3건: 크롤 스케줄러가 busy여도 드레인에 틱을 넘김(가드가
  다시 끼어들면 실패하도록 `isSchedulerBusy` 목이 **호출 시 throw**), write-heavy에선 두 반쪽 모두
  디퍼되고 각자 이름을 남김, 유휴면 둘 다 실행.
- 게이트: prettier 0, lint 0, `tsc --noEmit` 0, build 0, `npm test` **83 suites / 1169 tests**,
  `npm run test:e2e` 46 passed / 9 skipped, comment-language 0.

**미릴리스·미배포**: 이 변경은 §38 §12~14·§11과 같은 워킹트리에 있고 버전 범프·PR·배포는 하지
않았다. 따라서 프로덕션은 여전히 §4 상태(드레인 0회)다.

## 13. 관측 절차와 지표 - 925행이 실제로 소진되는지 틱 단위로 본다

도구: `backend/src/scripts/proposal-reason-drain-observation.ts`
(`npm run build` 후 `dist/scripts/proposal-reason-drain-observation.js`, 프로덕션 이미지에 포함).

```bash
# 배포 후, 컨테이너 안에서 DB를 읽고 컨테이너 로그를 stdin으로 받는다
docker logs lawcast-backend --since 6h 2>&1 | \
  docker exec -i lawcast-backend node dist/scripts/proposal-reason-drain-observation.js \
    --db "$DATABASE_PATH" --logs - --ticks 16
```

| 옵션 | 기본 | 의미 |
| --- | --- | --- |
| `--db` | `$DATABASE_PATH` | SQLite 경로(읽기 전용으로 연다) |
| `--logs` | 없음 | 로그 파일, 또는 `-`(stdin). 없으면 DB 지표만 본다 |
| `--ticks` | 16 (4시간) | 재생할 틱 수 |
| `--log-utc-offset` | 540 | 로그 타임스탬프가 현지 시각일 때 UTC로 옮기는 분. 컨테이너는 `TZ=Asia/Seoul` |
| `--no-pool-scan` | 꺼짐 | 풀 스냅샷(약 3초)을 생략한다 |
| `--json` | 꺼짐 | 기계 판독용 전체 리포트 |

**틱 기준**: 버킷은 크론 표현식에서 직접 읽는다(`9-59/15` → 분 9부터 15분). :54 틱은 다음 :09까지를
소유하므로 :05의 이벤트는 이전 시각 :54 창에 들어간다.

**지표** (한 틱 = 15분)

| 지표 | 출처 | 정상값 | 주의 |
| --- | --- | --- | --- |
| `status` | 로그 | `ran` (또는 정직한 `deferred`) | `no tick log`는 로그를 안 받았거나 TZ 가정이 틀린 신호 |
| `seed` | 로그 `queue before=.., seeded=..` | ≤ 20 | 시드 라인은 브라우저 창을 얻은 뒤에만 찍히므로 "이 틱은 돌았다"의 확정 신호 |
| `att(log)` | 로그 `recorded N attempt(s)` | ≈ seed | **틱별 시도 수의 1차 출처**(정확) |
| `att(db)` | `proposal_reason_retried_at` | ≥ 1 | 행별 **마지막** 시도만 남으므로 과거 틱은 과소 집계된다 |
| `realAtt` | 위 + `contentId IS NOT NULL` | 재사용 대상에 도달한 틱부터 ≥ 1 | 재사용 대상 소진 판정의 핵심 |
| `arriv` | `proposalReason` 도착 이벤트 | ≥ 0 | 이유가 실제로 도착한 수(진짜 진행) |
| `resolved` | 로그 `resolved bill` | ≥ 0 | 드레인이 요약까지 만든 건수 |
| `queue` | 로그 `queue after drain=` | 감소 또는 0 | 큐가 계속 차 있으면 상류가 안 풀리는 중 |
| `wait` | 로그 `browser freed after Nms` / `deferred ... for Nms` | 0에 가까움 | 틱마다 상한(300s)에 붙으면 크롤과 계속 겹치는 중 |
| `pool~` / `real~` | 스냅샷 + 이후 도착 역산 | 단조 감소 | 현재 스냅샷에서 과거 시점을 되돌려 추정한다 |

**판정 7종** (하나라도 fail이면 종료 코드 1 → 그대로 게이트로 쓸 수 있다)

| id | 질문 | 임계 | fail이면 |
| --- | --- | --- | --- |
| `retry-tracking-deployed` | 시도 이력 칼럼이 있는가 | 존재 | 마이그레이션 미배포 — 925/334행이 회전할 수 없다 |
| `drain-tick-executed` | 틱이 실제로 돌았는가 | ran/관측 ≥ 0.75 (0이면 fail, 그 사이 warn) | 로그의 `deferred` 사유(`blockers`)를 본다 = 아직 가드/크롤 경합 |
| `pool-moved` | 풀이 움직였는가 | 시도+도착 > 0 | 시드 0이면 상류, 시도 0이면 스탬프 경로 |
| `cursor-rotated` | 같은 행만 반복하는가 | distinct/기대 ≥ 0.8 (0.5~0.8 warn) | `att(log)` 대비 distinct가 낮다 = 커서가 다시 선두로 고정 |
| `real-targets-burned-down` | 재사용 대상을 실제로 도달·해소했나 | 이탈 > 0이면 pass, 도달했는데 해소 0이면 warn, **도달 자체가 0이면 fail** | fail은 head-of-line 재발, warn은 상류에 아직 이유가 없음 |
| `tick-cost-in-budget` | 틱 1회가 예산 안인가 | seed ≤ 20, 대기 ≤ 900s | 크롤과 과도하게 겹치거나 시드 상한이 늘어남 |
| `attempt-stamp-alive` | 시드한 틱이 스탬프도 남겼나 | 모든 시드 틱에서 ≥ 1 | §11의 스탬프 경로 회귀 |

**예상 타임라인 (현재 풀 = 334행: 소스 없음 314 + 재사용 가능 20)**

정렬이 `proposal_reason_retry_count ASC` → `retried_at ASC` → `noticeNum ASC`이므로, 시도 0회
그룹 안에서는 **noticeNum이 작은 소스 없는 절차 안건 314행이 먼저** 소진되고 재사용 가능한
20행(noticeNum 2219xxx~2222xxx)은 그 뒤에 온다. 즉

- 1~4틱(1시간): "드레인이 도는가 / 시도가 스탬프되는가 / 로테이션되는가"만 판정 가능.
- 약 16틱(≈4시간)부터 재사용 대상에 도달하기 시작하고, 소진 판정은 **`--ticks 20` 이상(≈5시간)**
  창에서 해야 한다(§8의 "실대상 9틱" 추정은 재사용 대상이 페이지 선두였다고 가정한 값이라 이
  순서에서는 성립하지 않는다).
- 배포 직후 첫 실행은 배포 **이전** 틱까지 재생되므로(로그가 없으면 `no tick log`) 배포 전후를
  한 표에서 비교할 수 있다.

**한계·주의**

- `att(db)`는 행별 마지막 시도만 반영하므로 틱별 시도 수는 로그에서 읽는다. 로그 없이 돌리면
  과거 틱은 과소 집계된다.
- 진행 중인 틱도 창에 포함되므로 ran 비율 분모가 1 커진다(15/16 = 0.94로 여전히 pass).
- 미배포 DB에서 돌리면 `attempt history MISSING`과 함께 3건 실패로 끝난다(exit 1) — 로컬 5.4GB
  스냅샷에서 확인한 기대 출력이다.

## 14. 별건 - 후보 쿼리 비용 137초, 동등한 집합 표현은 2.8초

관측 도구를 프로덕션에 붙이면서 발견했다. 후보 술어를 **그대로** 실행한 `COUNT(*)`가
프로덕션에서 **139.2초 / 137.1초**(2회 측정, 같은 결과 334/314/20)였다. `EXPLAIN QUERY PLAN`은
상관 스칼라 서브쿼리 형태를 보여준다:

```
|--SEARCH na USING INDEX idx_notice_archives_lifecycle_status (lifecycle_status=?)
`--CORRELATED SCALAR SUBQUERY 1
   |--SEARCH d USING INDEX idx_notice_change_details_field_path_event_id_id (field_path=?)
   `--SEARCH e USING INTEGER PRIMARY KEY (rowid=?)
```

`field_path='proposalReason'`로 상세를 먼저 훑고 그 다음 `e.notice_num`을 대조하므로, 아카이브
행마다 이유 상세(프로덕션 31,381행)를 다시 스캔한다 — O(아카이브 × 이유 상세). 테이블 크기는
작다: 상세 302,754행, 이벤트 52,842행, 아카이브 21,494행(5.6GB는 스냅샷 blob이 차지한다).

같은 술어를 **집합으로 물질화**해(`DISTINCT e.notice_num` 서브쿼리 2개를 LEFT JOIN) 평가하면
동일한 334/314/20을 **2.836초**에 반환한다 — 약 48배. 관측 도구는 이 형태를 쓴다
(`POOL_PREDICATE_SQL`, 5.4GB 로컬 스냅샷에서 2,816ms).

**영향과 미수정 사항**

- 드레인은 틱마다 이 쿼리(`ORDER BY ... LIMIT 20`)를 실행하므로 **브라우저 작업을 시작하기 전에
  약 2.3분을 쓴다.** §8의 "드레인 1틱 비용 ≈600초"에는 이 비용이 빠져 있었고, §11의 로컬 벤치
  (29.700 vs 29.785ms)는 정렬 키 추가 비용만 본 것이라 이 비용과 무관하다.
- 애플리케이션 쿼리는 **이번 작업에서 건드리지 않았다**(같은 의미·같은 결과를 2.8초에 반환함은
  확인했다). 후속으로 집합 표현 전환 또는 `(field_path, event_id)` 외에 `noticeChangeEvents.notice_num`
  중심 인덱스 추가를 검토할 만하다.

**§6의 925행 정정**

`lifecycle_status='active' AND 제안이유 공백`만 세면 **925행**이지만, 코드의 후보 술어(=이유 도착
이벤트·`source_deleted` 이벤트 제외)를 모두 적용하면 **334행**이다. 차이 591행은 이미 이유가
**체인에 도착해 기록된** 행(§38의 체인 경로로 서빙되며 컬럼은 불변이라 비어 있다)이라 후보가
아니다. 따라서 "드레인이 소진해야 할 백로그"는 925행이 아니라 **334행(재사용 가능 20행)**이고,
이 수치가 §13의 타임라인·임계를 좌우한다.
