# NSM 포털 UA 차단 → 조용한 수집 실패 + 삭제 프로브 폭주

## 1. 증상 (2026-10-14 운영 로그)

```
DEBUG [NoticeArchiveService] markSourceDeletedByMissingNsmNums: notice 2206783 missing from list scan but not confirmed deleted on detail page; left active
DEBUG [NoticeArchiveService] markSourceDeletedByMissingNsmNums: notice 2206781 missing from list scan but not confirmed deleted on detail page; left active
...
WARN  [AdminNoticesService] notion notice fetch failed; serving last good snapshot: fetch failed
```

두 줄은 **서로 무관한 문제**다. 앞의 DEBUG 줄들이 진짜 버그이고, WARN은 일시적 네트워크 실패다.

## 2. 근본 원인: NSM 포털이 `LawCast/1.0` UA를 차단한다

`opinion.lawmaking.go.kr`는 이제 LawCast의 제품 토큰이 들어간 UA에 대해 **사이트 오류 페이지**(200 + `<body class="errorWrap">`, 5,451 bytes, "404 (페이지 없음) Not Found")를 돌려준다. 재현·확정한 매트릭스(각 조건 2회 반복, 완전 재현):

| User-Agent | 결과 |
| --- | --- |
| `LawCast/1.0 (Legislative Notice Crawler)` | **오류 페이지 (5,451 bytes)** |
| `LawCast/1.0` | **오류 페이지** |
| `Mozilla/5.0 (compatible; LawCast/1.0; +https://example.com)` | **오류 페이지** |
| `Legislative Notice Crawler` | 정상 (목록 100건, 234 KB) |
| `Crawler/1.0` | 정상 |
| `Mozilla/5.0 (Windows NT 10.0 …) LawCast` | 정상 |
| `curl/8.7.1` | 정상 |
| 실제 브라우저(Chrome) | 정상 |

즉 차단 기준은 **`LawCast/1.0` 토큰**이다. IP 차단도, 세션/쿠키 문제도, `yType` 파라미터 누락도 아니다(브라우저로 사이트 자체 링크를 클릭해도 같은 404가 나오던 현상은 UA 차단과 별개로 사이트 자체 링크가 `/gcom/nsmLmSts/out`를 그대로 가리키기 때문이며, 크롬 UA로 직접 호출하면 목록이 정상 반환된다 — 즉 `yType`은 무관했다).

`pal-crawl`의 URL 자체는 유효하다(`crawling-core.service.ts`의 `buildNsmDetailUrl` = `/gcom/nsmLmSts/out/{billNo}/detailRP`). 크롬 UA로 호출하면 2206783 상세도 정상(59 KB)으로 내려온다. **UA만 바꾸면 데이터는 정상**이라는 뜻이다.

### 영향 1 — NSM 수집이 조용히 0건이 된다 (HIGH)

- `getAllNsmPages`/`getAllNsmPendingPages`는 plain HTTP(`HttpClient`)로 목록을 받아 파서에 넘긴다. 오류 페이지에는 목록 테이블이 없으므로 **예외 없이 `items=[]`, `total=0`**이 된다.
- 실측: `new NsmLmSts(config).search({pageIndex:1,pageSize:100})` → `total=0 totalPages=0 page1Items=0`.
- 그래서 `executePendingSyncPhase`/`crawling-scheduler-pending-support`는 "수집 0건, 신규 0건"으로 조용히 성공 처리한다(`rawItemMap.size > 0` 가드에 걸려 소스-누락 판정은 아예 건너뜀). **경고도 에러도 남지 않는다.**
- DB 증거: `notice_archives`에서 NSM(`contentId IS NULL`) 신규 행의 **마지막 archived_at = 2026-09-09 16:33:37**. 그 뒤로는 PAL 행만 쌓인다.

| 월 | NSM 신규 행 |
| --- | --- |
| 2026-06 | 289 |
| 2026-07 | 630 |
| 2026-08 | 18,627 (8/8~8/10 대량 백필 18,064 포함) |
| 2026-09 | 302 (9/9 중단) |
| 2026-10 | 0 |

### 영향 2 — 삭제 감지 프로브가 절대 확정할 수 없다 → 로그 폭주 (HIGH)

`markSourceDeletedByMissingNsmNums`는 목록에서 사라진 active NSM 행마다 `confirmDeletion(billNo)`를 호출하고, 그 구현이 `probeNsmDeletedBillAlert`(= NSM 상세 URL plain HTTP)다.

1. 프로브가 차단 UA로 요청 → 오류 페이지 수신
2. `detectNsmDeletedBillFromHtml`이 삭제 마커(`안건정보가 없습니다`)를 못 찾음 → `null`
3. `confirmDeletion` false → `left active` DEBUG 로그 → **다음 사이클에 같은 행을 다시 프로브**

이 로그는 "상세 페이지를 확인했는데 살아 있더라"가 아니라 **"확인 자체가 불가능했다"**는 뜻인데, 실패와 생존을 구분하지 못한다(관측성 구멍). 결과적으로 **실제 삭제된 의안도 영원히 감지되지 않는다** — `source_deleted` 878건은 전부 **2026-08-28 하루**에 몰려 있고, 그 이후 5주간 0건이다.

### 영향 3 — 후보 집합이 1만 건 규모다 (설계 문제, 소스 전환으로 증폭)

차단과 별개로, 후보 선정 자체가 과도하다.

- 후보 풀 = `lifecycle_status='active' AND contentId IS NULL` **19,845행** (필터 없음, 상한 없음)
- 현재 활성 소스는 `CRAWLING_NSM_SOURCE=likms`(`backend/.env` 확인). LIKMS 계류의안 목록 = **15,950건/160페이지**, 표본 331건 중 **59.8%만** active NSM 풀에 존재
- ⇒ 사이클당 삭제 후보 **약 10,300건**, 각 1회 HTTP 요청(상한·딜레이 없음, 순차)

즉 20분 크론마다 약 1만 건의 요청을 NSM 포털에 던진다(전부 차단 UA) — 포털 입장에서는 크롤러의 공격적 호출로 보일 수 있고, 8/28 이전 코드(목록 부재만으로 삭제 마킹)가 만들었을 오탐 위험과 함께 봐야 한다.

## 3. 조치 방향

1. **즉시 완화(코드 변경 없음)**: `CRAWLING_NSM_DELETION_DETECTION_ENABLED=false` — `isNsmDeletionDetectionEnabled()` 킬 스위치가 런타임에 읽히므로 재시작 없이 프로브 폭주와 로그가 멈춘다(감지는 당분간 포기하는 트레이드오프).
2. **근본 원인**: NSM 요청 UA에서 `LawCast/1.0` 토큰을 제거/교체할지, 아니면 차단을 존중하고 NSM 소스를 폐기할지는 **운영자 결정**. 차단을 우회하는 방향이면 (a) `pal-crawl` 설정의 UA 교체, (b) 호출량 자체를 줄이는 3번 작업을 함께 해야 한다(UA만 바꾸고 1만 건을 계속 던지면 다시 차단된다).
3. **후보 집합 재설계**: "마지막으로 목록에서 본 시각"을 행에 기록해 **새로 사라진 행만** 프로브하거나, 후보를 직전 성공 스캔 참여 행으로 한정한다. 지금은 매 사이클 전 풀을 재프로브한다.
4. **조용한 실패 제거**: 목록 스캔 결과가 0건이면 "신규 없음"과 구분해 경고/실패로 올린다. 차단 상태가 5주간 아무 신호도 내지 않은 것이 이 사건의 최악 부분이다.
5. **관측성**: 프로브 실패(네트워크/차단)와 "살아 있음"을 다른 로그로 분리한다.

## 3-1. 적용한 코드 패치 (2026-10-14, 코드로 고칠 수 있는 부분)

운영자 결정이 필요한 §3의 2·3번(UA 교체 vs 소스 폐기, 후보 집합 재설계)은 남겨 두고, **차단이 다시 조용히 지나갈 수 없게** 만드는 부분을 코드로 막았다.

| # | 문제 | 패치 | 파일 |
| --- | --- | --- | --- |
| P1 | 차단된 목록 스캔이 `items=[]`로 조용히 성공 처리 | 스캔이 **에러 없이 0행**이면 활성 소스명과 함께 WARN + Discord 브리지. 스캔 에러(부분 스캔) 메시지와 분리해 "신규 없음"으로 오독되지 않게 한다 | `crawling/utils/crawling-scheduler-pending-support.ts`(cron 경로), `crawling/utils/archive-sync-phase-executors.ts`(`executePendingSyncPhase`) |
| P2 | 포털 오류 페이지를 "의안 생존"으로 판정 | `isNsmPortalErrorPageHtml()` 신규(`errorWrap` 클래스 또는 `요청페이지가 없습니다`) — UA 차단 응답은 200 + 5,451 B 셸 페이지이므로 생존 판정에서 제외 | `crawling/utils/nsm-portal-error-page.util.ts`(+ `.spec.ts`) |
| P3 | 프로브 실패와 생존을 구분 못 함 | `probeNsmDeletedBillOutcome()`이 `deleted`/`alive`/`blocked`/`error`/`disabled` 반환(blocked = 포털 오류 페이지 또는 Waitingroom). 기존 `probeNsmDeletedBillAlert()`는 하위 호환 래퍼로 유지(`deleted`일 때만 메시지) | `crawling/crawling-core.service.ts` |
| P4 | 후보 1만 건을 매 사이클 순차 프로브 | `markSourceDeletedByMissingNsmNums(set, confirmDeletion, { maxCandidates, unusableAbortThreshold })` — 기본 상한 **50**(`ARCHIVE_SYNC_NSM_MISSING_PROBE_MAX_CANDIDATES`), 초과 시 무작위 표본이라 여러 사이클에 걸쳐 풀 전체를 커버. 상한이 후보 수에 압도되면 "스캔 목록이 아카이브와 다른 인구를 본다"는 WARN을 남긴다 | `notice/notice-archive.service.ts` |
| P5 | 차단 상태에서도 배치 전체를 계속 두드림 | 연속 **unusable** 프로브(포털 오류 페이지/Waitingroom/네트워크 실패)가 `unusableAbortThreshold`(기본 5)에 도달하고 그 사이 읽을 수 있었던 페이지가 하나도 없으면 패스를 중단하고 WARN. 한 번이라도 정상 페이지가 오면 계속 진행(일시적 블립과 진짜 차단 구분) | `notice/notice-archive.service.ts` |
| P6 | 로그가 어느 포털을 말하는지 불명 | `getActiveNsmSource()`로 `source=nsm|likms` 라벨을 0행 경고·후보 초과 경고에 포함 | `utils/crawler-activation.utils.ts` |

새 설정 키(`app.config.ts` + `.env.example`):

- `ARCHIVE_SYNC_NSM_MISSING_PROBE_MAX_CANDIDATES` (기본 50)
- `ARCHIVE_SYNC_NSM_MISSING_PROBE_UNUSABLE_ABORT_THRESHOLD` (기본 5)

**부수 계약 변경**: `markSourceDeletedByMissingNsmNums`의 `confirmDeletion` 콜백이 이제 `boolean`이 아니라 outcome 문자열(`'deleted'|'alive'|'blocked'|'error'|'disabled'`)을 반환한다(두 호출부 모두 `probeNsmDeletedBillOutcome` 사용으로 교체). 새 콜백 형태를 모르는 호출부가 생기면 차단이 다시 "살아 있음"으로 흘러들어간다.

**아직 남은 것(운영자 결정/별도 마이그레이션)**:

- UA에서 `LawCast/1.0` 토큰을 빼는지, NSM 소스를 폐기하고 LIKMS로 고정하는지는 여전히 미결이다. 상한·랜덤 표본·차단 중단은 **완화책**일 뿐, UA가 살아나도 1만 건 풀을 다시 던지면 재차단될 수 있다.
- "마지막으로 목록에서 목격한 시각" 컬럼(새 사라진 행만 프로브)은 마이그레이션이 필요해 미실행.

## 3-2. 목록 관측 기반 후보 집합 재설계 (구현 완료, 2026-10-14)

§3의 3번(후보 재설계)을 코드로 구현했다. 3-1의 상한·재프로브 쿨다운은 "무한 반복을 막는" 완화책이었고, 이번 작업은 **후보 자격 자체를 "목록에서 새로 사라진 행"으로 바꾼다**.

### 무엇을 기록하는가

| 컬럼 | 의미 |
| --- | --- |
| `notice_archives.nsm_last_seen_in_list_at` | 완료된 목록 스캔이 이 행을 마지막으로 반환한 시각. `NULL` = 이 추적 도입 이후 한 번도 목록에 없었음 |
| `notice_archives.nsm_list_absence_probed_at` | 결손을 조사했지만 삭제가 확정되지 않은 시각 |

마이그레이션 `202610140001-add-nsm-list-absence-tracking`(nullable 2컬럼, 인덱스 추가 없음 — 후보 쿼리는 `lifecycle_status` 인덱스로 좁혀지는 2만 행 이하 집합이라 불필요). **아카이브 불변성 트리거는 변경하지 않았다**: 추적 컬럼만 바뀌는 UPDATE는 기존 predicate(불변 컬럼 동일 + 스냅샷 1회 채움 + lifecycle 동일)를 그대로 통과한다 — 실 스키마 스펙으로 확인.

### 후보 선정 규칙

1. `markSourceDeletedByMissingNsmNums(seenNums, probe, opts)`가 먼저 `seenNums` 전체를 `nsm_last_seen_in_list_at = scannedAt`으로 스탬프한다(400행 청크, 이미 이번 스캔 시각 이후로 찍힌 행은 건너뜀). 스캔에 나온 행은 그래서 절대 후보가 되지 않는다.
2. **사라진 행**(`nsm_last_seen_in_list_at < scannedAt`)을 오래 사라진 순으로 상한(50)까지.
3. 남은 자리만 **한 번도 본 적 없는 행**(`IS NULL`)으로 채운다(마이그레이션 직후 아카이브가 한 번에 쓸리지 않도록).
4. 두 그룹 모두 `nsm_list_absence_probed_at`이 쿨다운(기본 168h) 안이면 제외.
5. 프로브가 `deleted`가 아니면(살아 있음/차단/오류) 조사 시각을 기록 → 같은 행이 매 사이클 후보로 돌아오지 않는다.

`seenNums`가 비면 아무것도 하지 않는다(0행 스캔은 §3-1 P1의 경고로 보고된다). 감지 킬 스위치가 꺼져 있어도 **스탬프는 계속**한다 — 다시 켰을 때 "감지가 꺼져 있던 동안 사라진 행"만 후보가 되도록.

### 실 DB 사본 실측 (21,203행 / active NSM 19,845행)

`lawcast.db` 사본에 마이그레이션을 적용하고 목록 스캔 시나리오를 재생한 결과:

| 시나리오 | 프로브 수 | 비고 |
| --- | --- | --- |
| 완전한 목록(19,845행 전부 반환) | **0** | 스탬프 19,845 |
| 60% 겹침 목록(라이브 LIKMS 계류의안 형태) | **50**(상한) | 구 코드 후보 풀 = **7,938** |
| 같은 목록 반복(2·3·4회차) | 50, 50 | 매 회 **서로 다른 50** — 풀 진행, 159사이클이면 소진 |
| 완전한 목록으로 복귀 | **0** | 사라진 행이 없으면 프로브도 없다 |
| 목록에서 정확히 200행 제거 | 50 | **프로브된 50행 전부가 그 200행 안**(밖 0건) |
| 같은 200행 결손 2회차 | 50(누적 서로 다른 100) | 쿨다운이 같은 행 재프로브를 막음 |
| 200행이 목록에 복귀 | **0** | 결손 에피소드 종료 |

사이클 소요: 스탬프 12k~19.8k행 기준 **2.4~5.9초**(5.5GB 사본, 콜드 캐시 첫 회 27초). 20분 크론에서 허용 범위이며, 기존 동작(사이클당 1만 건 HTTP 프로브)과 비교하면 비용 성격이 완전히 다르다. 같은 사이클에 cron 경로와 sync 경로가 둘 다 돌면 스탬프가 2회 발생(비용 2배) — "이번 사이클에 이미 찍힌 행은 스탬프 생략" 최적화 여지로 남겨 둔다.

### 새 설정

- `ARCHIVE_SYNC_NSM_LIST_ABSENCE_REPROBE_COOLDOWN_HOURS` (기본 168)
- 기존 `ARCHIVE_SYNC_NSM_MISSING_PROBE_MAX_CANDIDATES`(50)·`ARCHIVE_SYNC_NSM_MISSING_PROBE_UNUSABLE_ABORT_THRESHOLD`(5)는 그대로 후보 상한·중단 조건으로 사용.

### 검증

`src/modules/notice/notice-archive-nsm-list-absence.spec.ts`(신규 9케이스, 실제 SQLite 스키마 + 마이그레이션 체인 + 불변성 트리거): 스탬프/무프로브, 사라진 행만 프로브, 우선순위, 쿨다운 억제·만료, source_deleted·PAL 행 제외, 감지 꺼짐 상태 스탬프, 불변 컬럼 보존, 2,000행 스탬프 후에도 상한만 프로브. 기존 mock 스펙도 그룹별 `find`(사라진/미관측) 계약으로 갱신. 게이트: lint/tsc/build exit 0, **75 suites / 1042 tests pass**, comment-language exit 0.

### 남은 것

- **상세 프로브 경로**(`getActiveNsmBillsForProbe` → `probeExistingNsmBillsForSourceDeletion`, 20건/사이클)는 아직 매 사이클 같은 풀(활성 NSM 19.8k, `contentBillNumber IS NULL` 우선)에서 랜덤 추출한다. 같은 추적 컬럼을 공유해 "조사한 행은 쿨다운" 규칙을 적용하는 게 다음 단계다(현재는 폭주 규모가 20/사이클이라 우선순위가 낮다).
- UA 교체 vs NSM 소스 폐기는 여전히 운영자 결정.

## 3-3. 0건 스캔의 승격 — 경고를 넘어 "수집 중단"으로 (구현 완료, 2026-10-14)

§3-1 P1은 0건 스캔을 **경고 한 줄**로만 올렸다. 경고는 매 사이클 같은 문장으로 묻히고, `/status`는 계속 `대기`로 보였으며, 전체 상태도 `정상`이었다. 이번 작업은 0건을 **실패 관찰**로 취급해 상태·알림·UI까지 승격한다.

### 상태 기록 (런렝스)

캐시 키 `crawling:nsmListScanHealth` (만료 없음, Keyv `ttl=0` 확인) 에 스냅샷 하나를 유지한다:

| 필드 | 의미 |
| --- | --- |
| `lastScanAt` / `lastScanItemCount` | 마지막 완료 스캔(행 수 무관) |
| `lastSuccessfulScanAt` / `...ItemCount` | **행을 실제로 반환한** 마지막 스캔 — 이 시각이 "수집이 멈춘 지 얼마나 됐나"의 기준 |
| `consecutiveZeroRowScans` | 연속 0건 스캔 수 |
| `degraded` / `degradedSince` | 임계값 도달 여부·시점 |
| `lastAlertAt` | 반복 알림 레이트리밋 |

동작 규칙:

- 0건 → 스트리크 +1, 행 반환 → 스트리크 0(회복 시 "N회 연속 0건 이후 회복" 경고).
- **같은 사이클 중복 방지**: 5분 이내 두 번째 스캔(크론 패스 + 아카이브 동기화 패스)은 같은 사이클로 보고 스트리크를 늘리지 않는다. 임계값(기본 3, `CRAWLING_NSM_LIST_SCAN_DEGRADED_THRESHOLD`)은 곧 **약 1시간의 무응답**을 의미한다.
- 임계값 도달 시 ERROR 레벨 로그 + Discord 브리지 알림. 이후에는 `CRAWLING_NSM_LIST_SCAN_ALERT_REPEAT_HOURS`(기본 6)마다 한 번씩만 반복 — 20분 크론마다 알림을 난사하지 않는다.
- 책임 분리: 순수 유틸(`nsm-list-scan-health.util.ts`)은 상태만 계산하고, 리포터(`nsm-list-scan-reporting.ts`)가 로그·브리지를 담당하며, 캐시 오류는 삼키고 기존 경고만 남긴다(수집 실패로 승격되지 않음).

### 노출

- `GET /api/stats` → `crawlers.nsmPendingCrawler.status`가 `degraded`가 되고(진행 중 > degraded > failed > idle 순), `listScan` 블록이 `consecutiveZeroRowScans`·`lastSuccessfulScanAt`·`staleHours`를 보고한다. 기록이 없으면 `null`(가짜 정상 금지).
- `/status` 카드: 배지 `수집 중단`(lc-chip-warning) + "목록이 N회 연속 0건입니다. 마지막 정상 수집: … (N시간 전)" — 정상일 때는 "목록 수신: …·N건" 한 줄. `degraded`는 페이지 전체 판정(`주의 필요`)에도 포함된다.
- `/crawling-transparency`는 이번 범위에서 제외(다음 단계), PAL 크롤러도 동일 승격 미적용.

### 검증

- 백엔드: `nsm-list-scan-health.util.spec.ts`(12) + `nsm-list-scan-reporting.spec.ts`(8) — 임계값 승격·중복 사이클·반복 알림 제한·회복·캐시 장애, 그리고 `crawling-scheduler.service.spec.ts`에 **가짜 타이머로 20분 간격 3사이클을 실제로 돌려** ERROR 승격을 확인하는 배선 테스트, `runtime-stats.service.spec.ts`에 degraded 노출 테스트.
- 프론트: `status.spec.ts` 14 pass(정상 상태), 신규 `status-nsm-degraded.spec.ts` 5 pass + 전용 설정 `playwright.nsm-degraded.config.ts`(`DIFFCHAIN_UI_MOCK_NSM_DEGRADED=1`, 전용 포트 5202).
- 게이트: lint/tsc/build exit 0, **77 suites / 1065 tests pass**, comment-language exit 0, `npm run check` 0 errors.

### 남은 한계

- 상태 기록이 캐시에 있으므로 Redis/프로세스 초기화로 스트리크가 0으로 돌아간다(재시작 후 첫 0건 스캔은 다시 경고부터 — 조용해지지는 않는다).
- PAL 크롤러의 "0건 페이지"와 `/crawling-transparency` 노출은 미적용.

## 3-4. UA 순환 — 요청마다 실제 브라우저 신원 (구현 완료, 2026-10-14)

§3의 2번("NSM 요청 UA에서 `LawCast/1.0` 토큰을 제거/교체")을 **교체 방향으로 기본값화**한 작업. UA 문자열만 바꾸면 다음 신호가 그대로 남으므로, 요청 헤더 전체를 한 브라우저 신원에서 파생시킨다.

### 구성

| 파일 | 역할 |
| --- | --- |
| `backend/src/utils/browser-identities.util.ts` | 실제 브라우저 UA 12개(Chrome 154/155, Edge 155, Firefox 156/157, Safari 27 — Windows/macOS/Linux/Android/iOS). 각 항목이 `family`/`platform`/`mobile`/`significantVersion`을 함께 들고 있어 **헤더가 그 신원에서 파생**된다 |
| `backend/src/utils/browser-request-headers.util.ts` | 신원 → 헤더 변환, 요청별 회전, `CRAWLING_USER_AGENT` 고정 처리 |

버전은 2026-10-14 기준 릴리스(Edge 155.0.4283.45, Chrome 154/155, Firefox 157.0, Safari 27)에 맞췄다. UA 형식은 안정적이므로 major가 올라가면 숫자만 갱신하면 된다.

### pal-crawl 경로의 요청별 회전 (핵심)

pal-crawl `dist/http-client.js`의 `makeRequest`는 요청마다 헤더를

```js
{ 'User-Agent': this.userAgent, ...this.customHeaders, ...extraHeaders }
```

로 만든다. 객체 스프레드는 own key를 **삽입 순서로** 읽고 접근자(getter)를 실행하므로, `customHeaders`에 접근자를 심으면 **클라이언트 하나로 요청마다 UA를 바꿀 수 있다**(클라이언트를 요청마다 새로 만들 필요가 없다). `'User-Agent'`를 첫 키로 정의하는 이유는 나머지 힌트가 같은 신원을 가리키게 하기 위해서다 — 순서가 어긋나면 "UA는 Chrome, `sec-ch-ua`는 Edge"라는, 봇 필터가 정확히 찾는 조합이 만들어진다.

**family는 클라이언트 생성 시 한 번 고정한다.** 헤더 *이름 집합*은 family가 결정하는데(Chromium=`sec-ch-ua*`, Chromium+Firefox=`Sec-Fetch-*`, Safari=둘 다 없음 — Firefox/Safari는 UA-CH 미구현), pal-crawl은 요청마다 같은 이름 집합만 병합하므로 family를 요청마다 바꿀 수 없다. 회전하는 것은 신원(버전·플랫폼·모바일)이다. 클라이언트는 오퍼레이션마다 새로 만들어지므로(상세 1건 조회 = 클라이언트 1개) 전체 트래픽에서는 family도 섞인다.

### 우리 axios 경로

`fetchHtmlPage`(NSM 상세 삭제 프로브, PAL 원본 HTML 캡처)는 요청마다 헤더 객체를 통째로 만들므로 **family를 포함한 전체 신원을 회전**한다.

### 보내는 헤더

- 내비게이션 `Accept`, `Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7`
- Chromium: `sec-ch-ua`(grease + Chromium + 브랜드, 같은 major), `sec-ch-ua-mobile`, `sec-ch-ua-platform`
- Chromium·Firefox: `Upgrade-Insecure-Requests: 1`, `Sec-Fetch-Dest: document`, `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Site: none`, `Sec-Fetch-User: ?1`
- Safari: 힌트·Sec-Fetch 없음(실제 Safari도 보내지 않는다)

`Sec-Fetch-Site`는 `none`(주소창 직접 이동)이다. pal-crawl은 직전 URL을 노출하지 않아 `Referer`를 만들 수 없는데, Referer 없이 `same-origin`을 주장하면 그 자체가 모순이기 때문이다.

**의도적 예외 둘**
- `Cache-Control: no-cache` 유지 — 중간 캐시가 목록을 대신 서빙하면 신규 의안을 놓친다. 조건부 헤더를 보내지 않으므로 응답은 여전히 200 전문이다.
- `Accept-Encoding`은 **넣지 않았다** — pal-crawl의 `HttpClient`는 압축을 해제하지 않아 gzip을 요청하면 본문이 깨진다. axios 경로는 axios가 스스로 `gzip, compress, deflate, br`를 보내고 해제한다(dev 서버로 실측).

### 설정

`CRAWLING_USER_AGENT` **미설정(기본)이면 순환**, 설정하면 그 값을 모든 요청에 고정하고 힌트는 보내지 않으며 기존 `CRAWLING.HEADERS`(Accept-Language/Accept/Cache-Control)만 붙인다. 즉 이 환경변수는 이제 "교체" 스위치가 아니라 **운영자 이스케이프 해치**(차단 회피 실패 시 제품 토큰으로 되돌리기)다. 코드 기본값에서 `LawCast/1.0 (Legislative Notice Crawler)`를 제거했다(`app.config.ts`). `.env.example`에 미설정=순환 주석 추가.

### 검증

- 신규 스펙 2개(28 tests): 풀 무결성(UA 형식, UA 버전↔힌트 버전 일치, mobile/platform 토큰 일치), 선택 분포, family별 이름 집합, 고정/회전 분기.
- **pal-crawl 실물 검증**: `browser-request-headers.util.spec.ts`가 `https.request`를 스텁하고 **실제 `NsmLmSts.search()`를 6회 호출**해 wire 헤더를 캡처한다 → (a) 매 요청 UA가 풀 안에 있고, (b) 같은 신원의 헤더 집합과 **완전히 일치**하며, (c) 요청 간 UA가 바뀌는지 확인. pal-crawl이 스프레드 순서를 바꾸거나 접근자 평가를 멈추면 이 테스트가 먼저 깨진다(조용한 UA 고정으로 흘러가지 않음).
- 서비스 스펙(`crawling-core.service.spec.ts`: PalCrawl/LikmsCrawler/LikmsNsmAdapter 설정 + 삭제 프로브 fetch, `archive-orchestrator.service.spec.ts`: 원본 HTML fetch)에서 옛 `LawCast/1.0` 단정을 "브라우저 신원 + 힌트 일치" 단정으로 교체.

### 남은 한계

- **pal-crawl 경로는 `Accept-Encoding`을 붙일 수 없다**(압축 해제 미지원) → 헤더 집합이 실제 브라우저와 완전히 같지는 않다.
- 헤더 *순서*와 TLS 지문(JA3)은 그대로다. 이번 작업은 헤더 모양만 맞춘다.
- 브라우저 경로(Puppeteer)는 여전히 `HeadlessChrome` UA·`navigator.webdriver`를 노출한다(이번 범위 밖, 별도 작업).
- 요청마다 플랫폼까지 바뀌는 것은 실제 세션과 다르다. 차단이 반복되면 "family당 신원 1개 고정"이 더 자연스러운 다음 단계다.

## 4. Notion WARN은 별개

`AdminNoticesService`의 WARN은 undici 네트워크 레벨 `fetch failed`로, 같은 시각 `api.notion.com`은 정상 도달(401 = 미인증 curl 기준)했다. `refresh()`가 실패 시 마지막 스냅샷을 계속 서빙하는 설계대로 동작한 것이며(`stale-while-revalidate`), 429 백오프도 별도로 있다. 다만 프로브 폭주와 동시에 발생했으므로 대량 요청과의 상관 가능성은 배제하지 말고 관찰할 것.

## 5. 진단에 사용한 명령

```bash
# UA 매트릭스 (완전 재현)
curl -s -A 'LawCast/1.0 (Legislative Notice Crawler)' \
  'https://opinion.lawmaking.go.kr/gcom/nsmLmSts/out?pageIndex=1&pageSize=100' | grep -c errorWrap
# 목록 인구 (pal-crawl 직접 호출, 요청 1~4회)
node -e "const {NsmLmSts}=require('pal-crawl');new NsmLmSts({userAgent:'LawCast/1.0 (Legislative Notice Crawler)'}).search({pageIndex:1,pageSize:100}).then(r=>console.log(r.total))"
# DB (읽기 전용)
sqlite3 -readonly lawcast.db "SELECT MAX(archived_at) FROM notice_archives WHERE contentId IS NULL;"
sqlite3 -readonly lawcast.db "SELECT lifecycle_status, COUNT(*) FROM notice_archives GROUP BY 1;"
sqlite3 -readonly lawcast.db "SELECT date(source_deleted_at), COUNT(*) FROM notice_archives GROUP BY 1 ORDER BY 1 DESC LIMIT 5;"
```

## 5-1. 검증 (P1~P6 패치 후 실행)

```bash
cd backend && npm run lint         # exit 0
cd backend && npx tsc --noEmit     # exit 0
cd backend && npm run build        # exit 0
cd backend && npm test             # 74 suites / 1031 tests pass
python3 tools/check-comment-language.py   # exit 0
cd frontend && npm run check       # 0 errors, 0 warnings
cd frontend && DIFFCHAIN_UI_MOCK=1 npx playwright test --config playwright-configs/playwright.config.ts e2e/status.spec.ts   # 13 pass
```

라이브 실측(빌드된 `dist` 유틸로 실제 포털 호출, 2요청): 차단 UA(`LawCast/1.0`) → 200 / 5,351 B / `errorPage=true` / 삭제 마커 없음 ⇒ 패치 전에는 `alive`로 분류되어 조용히 넘어가던 응답이 이제 `blocked`로 분류된다. 브라우저 UA → 200 / 51,737 B / `errorPage=false` ⇒ 정상 상세 페이지는 여전히 `alive`로 남는다. **오류 페이지 크기는 5,351~5,451 B로 변동**하므로 크기로 판별하지 말고 `errorWrap`/`요청페이지가 없습니다` 구조로 판별할 것.

후속 재설계(§3-2) 실측: 완전 목록 0 프로브, 200행 제거 시 프로브 50건 전부 그 200행 안(밖 0건), 결손 행 복귀 시 0 프로브.

새/확장 스펙: `nsm-portal-error-page.util.spec.ts`(신규), `crawling-core.service.spec.ts`(outcome 분류 — 오류 페이지/Waitingroom/삭제 확정/생존), `notice-archive.service.spec.ts`(상한 초과 표본 3건만 프로브, unreadable 3회에 중단, 정상 페이지 1건이면 계속), `crawling-scheduler.service.spec.ts` + `fault-isolation.spec.ts`(0행 스캔 경고), `runtime-stats.service.spec.ts`.

## 6. 미확인 / 주의

- 차단 시작 시점을 로그로 직접 확인하지는 못했다. DB상 **마지막 NSM 수집 = 2026-09-09 16:33**이 가장 강한 단서다.
- 차단이 포털의 자동 어뷰즈 룰인지, 운영자의 명시적 차단인지, `LawCast/1.0` 문자열에 대한 정확한 매칭 규칙(`LawCast/1` prefix인지 전체 토큰인지)은 확인하지 않았다.
- LIKMS 경로는 같은 LawCast UA로도 정상 동작한다(계류의안 15,950건). 차단은 NSM 포털에만 적용된다.
- 프로브 후보 추정치(약 10,300건)는 4개 페이지 표본(331건) 기반 외삽이다.
