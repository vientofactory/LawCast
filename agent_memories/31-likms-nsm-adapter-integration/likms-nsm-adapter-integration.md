# LikmsNsmAdapter Integration into the NSM Crawling Pipeline

## 목표

백엔드 `pal-crawl`을 `2.2.0` → `2.3.0`으로 올리고, 2.3.0에 추가된 `LikmsNsmAdapter`를 기존 NSM 크롤러(`NsmLmSts`) 자리에 끼워 국회 의안정보시스템(계류의안) 목록을 **기존 NSM 데이터 처리 파이프라인 그대로** 태우는 것. 대규모 호출부 수정 없이 소스 전환만 가능해야 한다.

## 배경: 2.3.0이 제공하는 것

`pal-crawl@2.3.0`의 새 export(`node_modules/pal-crawl/dist/index.d.ts`):

- `LikmsNsmAdapter`, `INsmListCrawler`, `INsmDetailCrawler`
- `LikmsStateCrawler`, `LikmsStateParser`, `LikmsDetailParser`
- `ILikmsStateBillItem`, `ILikmsStateSearchResult`, `LikmsStateCrawlerConfig` 등

핵심 구조:

```ts
export declare class LikmsNsmAdapter implements INsmListCrawler, INsmDetailCrawler {
  readonly likms: LikmsStateCrawler;
  constructor(config?: LikmsStateCrawlerConfig);
  search(query?: INsmSearchQuery): Promise<INsmSearchResult>;
  getAllPages(query?, options?): AsyncGenerator<INsmSearchResult>;
  getAllPendingPages(query?, options?): AsyncGenerator<INsmSearchResult>;
  getDetail(billNoOrBillId: string): Promise<INsmBillDetail>;
  parseDetail(html: string): INsmBillDetail;
  // ...
}
```

- `NsmLmSts`는 `implements`를 선언하지 않지만 **구조적으로** 같은 포트를 만족한다(README의 `const crawler: INsmListCrawler = useLikms ? new LikmsNsmAdapter() : new NsmLmSts()` 패턴).
- **`searchPending`/`getAllPendingPages`는 일부러 포트(`INsmListCrawler`)에 없다.** NSM은 `rslRsltNmL=900101` 서버 필터로 좁히지만 likms에는 동일 축이 없어 **스캔**해야 하므로, 같은 이름으로 숨기면 비용이 드러나지 않는다. 두 구현 모두 같은 시그니처의 메서드를 제공하므로 호출부에서는 그대로 쓸 수 있다.
- 값 형식 차이(비교 로직 주의): likms `proposalDate`는 `YYYY-MM-DD`, `session`은 `제22대(2024~2028)제439회`, `attachments.fileId`는 다운로드 URL. 계류의안 목록에 없는 `ministry`/`progressDate`/`resolutionStatus`/`resolutionDate`는 빈 문자열.
- likms는 제안자 **이름**을 받지 않으므로 `scPpsUsr`를 주면 예외를 던진다(조용히 무시하지 않음). `scCptPpostCmt`(상임위 이름)는 코드로 해석하며 확정 불가 시 예외.

## 구현 (변경 면적 최소)

### 1. 소스 선택 플래그

`backend/src/utils/crawler-activation.utils.ts`

- `CRAWLING_NSM_SOURCE` (`nsm` 기본 | `likms`), `NSM_SOURCE` 상수 + `isLikmsNsmSourceEnabled()` 추가.
- 기존 `CRAWLING_NSM_ENABLED`와 동일하게 **매 호출 `process.env` 조회**(재시작 없이 토글 가능), 정확히 `likms`(trim/lowercase)일 때만 전환 → **opt-in**, 기본 동작 불변.
- `isNsmCrawlerEnabled()`(수집 on/off)와 직교한다: 소스 선택은 "어디서", 활성 플래그는 "수집 여부".

### 2. NSM 클라이언트 팩토리 교체

`backend/src/modules/crawling/crawling-core.service.ts`

- `createNsmClient(): NsmCrawlerClient`가 `isLikmsNsmSourceEnabled()`에 따라 `new LikmsNsmAdapter(...)` 또는 `new NsmLmSts(this.crawlConfig)`를 반환.
- 로컬 포트 타입으로 두 구현을 하나로 묶었다:

```ts
type NsmPendingListCrawler = {
  getAllPendingPages(query?: Omit<INsmSearchQuery, 'pageIndex'>, options?: IBulkOptions): AsyncGenerator<INsmSearchResult>;
};
type NsmCrawlerClient = INsmListCrawler & INsmDetailCrawler & NsmPendingListCrawler;
```

- `getAllNsmPages` / `getAllNsmPendingPages` / `getNsmDetail`의 **호출부는 한 줄도 바뀌지 않았다** — 이들이 `INsmBillItem`/`INsmSearchResult` 동일 셰이프를 받으므로 `nsmBillToCachedNotice` → 아카이브 → 캐시 → 알림 파이프라인이 그대로 동작한다.
- likms 설정에는 `hydrateProposalReason`을 **넣지 않는다**. 건당 2회 추가 요청이 붙어 대량 목록 스캔이 느려지고, 제안이유는 기존 백필/재시도 경로가 담당한다.
- 브라우저 폴백(`fetchNsmListPagesViaBrowser`, `captureNsmDetailFull`, `captureNsmDetailScreenshot`)은 NSM 전용(Watingroom·opinion URL)이라 `NsmLmSts` 그대로 유지. LIKMS 경로에서는 Waitingroom 307이 나오지 않으므로 문제 없음.

### 3. 계류(bill) 판정 공유 + 비의안 행 차단

`CrawlingCoreService`에 정적 헬퍼 2개를 두고 **두 수집기**(`utils/crawling-scheduler-pending-support.ts`, `utils/archive-sync-phase-executors.ts`)가 함께 사용한다(중복 제거).

```ts
// `발의`(NSM, rslRsltNmL=900101)와 `접수`(likms)는 같은 단계 = pending-like
static isPendingProgressStatus(progressStatus) { ... }  // Set(['발의','접수'])

// 파이프라인은 numeric `의안번호`(num)로만 공지를 식별한다
static isCrawlableNsmBill(item) {
  const parsed = Number.parseInt(item.billNo?.trim() ?? '', 10);
  return Number.isInteger(parsed) && parsed > 0;
}
```

- `collectPageItems`가 매핑 **전에** `isCrawlableNsmBill`로 거른다.
- `isPendingLike`(`발의`)에 `접수`를 추가 → LIKMS 활성 시 전체 스윕에서도 `접수` 건이 pending 후보로 분류된다(펜딩 스캔은 `maxPages` 캡이 있어 빈 결과가 나올 수 있음).

## 실측 근거 (2026-10-14)

### 1) 비의안 행 발견 — 필터가 필요한 이유

LIKMS 계류의안 목록(22대, `pageSize=100`)에 **numeric id가 없는 행**이 섞여 있다:

| billNo | billName | progressStatus |
| --- | --- | --- |
| `ZZ22142` | 중대범죄수사청장후보자(김지용) 인사청문요청안(대통령) | `소관위접수` |

`parseInt('ZZ22142')` = `NaN` → 필터 없이는 `num=NaN` 공지가 `NEW_SYNC_ONLY_BILLS`로 아카이브될 수 있다(파이프라인이 num 키 기반). `isCrawlableNsmBill`로 매핑 전에 제거한다.

### 2) 실제 서비스 경로 라이브 검증

`CRAWLING_NSM_SOURCE=likms`로 실제 `CrawlingCoreService` 인스턴스를 만들어(`browserLeaseManager`는 runWithLease 호출 시 throw하는 스텁) 네트워크에서 직접 수집:

```
[service.getAllNsmPages] pages=2
[nsmBillToCachedNotice(all)] items=199 numValid=199 pendingLike=13 droppedNonBill=1
[nsmBillToCachedNotice(all)] dropped billNos: "ZZ22142"
[service.getAllNsmPendingPages] pages=2
[nsmBillToCachedNotice(pending)] items=13 numValid=13 pendingLike=13 droppedNonBill=0
RESULT: OK
```

샘플 매핑 결과(기존 `nsmBillToCachedNotice` 그대로 통과):

```json
[
  { "num": 2221883, "status": "접수", "pendingLike": true, "subject": "이재명 대통령 일가의 ... 특별검사 임명 등에 관한 법률안(주진우의원 등 10인)" },
  { "num": 2221882, "status": "접수", "pendingLike": true, "subject": "학교체육 진흥법 일부개정법률안(최혁진의원 등 12인)" }
]
```

### 3) 계약 → 배포 전 게이트

- `npm run lint` 0, `npx tsc --noEmit` 0, `npm run build` 0
- `npm test` → **73 suites / 1013 tests passed**
- `python3 tools/check-comment-language.py` → `0` (신규 주석의 한국어는 전부 backtick 인용으로 처리)
- 신규/수정 테스트: `crawler-activation.utils.spec.ts`(`isLikmsNsmSourceEnabled`), `crawling-core.service.spec.ts`(소스 전환 3건 + 분류 헬퍼 2건), `crawling-scheduler.service.spec.ts`(`접수` pending 분류, `ZZ22142` 드롭)

## 남은 작업 / 주의

- **버전 범프 미실행**: `backend/package.json`은 1.14.0 그대로다(기능 추가 → minor, 1.15.0 예상). 커밋/PR/릴리스는 요청받지 않아 수행하지 않았다.
- **`.env.example` 안내만 추가**: 운영 배포 시 `CRAWLING_NSM_SOURCE=likms`를 명시해야 전환된다. docker-compose의 `environment`는 `env_file`을 덮어쓰므로(세션 12 버그) 컨테이너에서 켤 때는 compose 쪽 주입도 확인해야 한다.
- **`getNsmDetail`만 소스를 따라간다**: 목록/상세 조회는 어댑터를 타지만, 스크린샷·스냅샷 캡처(`captureNsmDetailFull`/`captureNsmDetailScreenshot`)와 삭제 프로브(`probeNsmDeletedBillAlert`)는 NSM(opinion.lawmaking.go.kr) URL을 그대로 쓴다. 의안번호가 양쪽에서 동일하므로 동작은 하지만, LIKMS를 장기 기본 소스로 삼으면 캡처 경로도 likms로 옮기는 별도 작업이 필요하다.
- **미지원 필터**: `rslRsltNmL`/`rslRsltNmR`/`cptOfiOrgCd`/`sortCol`/`issLawitmYn`/`stDt`/`edDt`는 likms에 동일 축이 없어 무시된다. `scPpsUsr`는 예외를 던진다. 현재 파이프라인은 `pageSize`만 보내므로 영향 없음.
- **통계 표기 (해결됨, 2026-10-14 후속)**: 백엔드가 이제 활성 NSM 소스를 payload로 보고한다. `RuntimeStatsService`의 `resolveNsmSourceInfo()`가 `CRAWLING_NSM_SOURCE`에 따라 `source`/`name`/`url`/`description`/`crawlerName`/`scheduleName`/`scheduleDescription`/`transferFlowDescription`를 고르고, `GET /api/stats`(`crawlers.nsmPendingCrawler.source`·`name`)와 `GET /api/crawling-transparency`(`noticeSources[nsm]`·`schedules[nsm-pending]`·`transferFlow.description`)에 반영된다. 집계 시점마다 조회하므로 재시작 없이 전환된다(단, 투명성 payload는 5분 캐시가 있다). 기본값 `nsm`이면 기존 문자열과 완전히 동일하다. 검증: `runtime-stats.service.spec.ts`에 소스 보고 describe 3건 추가(기본값/likms/런타임 전환).
- **프론트 상태 페이지 표기 (해결됨, 2026-10-14 후속 2)**: `/status`가 이제 수집 소스에 맞는 크롤러 이름을 표시한다. (1) 카드 제목은 payload의 `crawlers.*.name`을 그대로 쓴다(`palCrawler.name`/`nsmPendingCrawler.name`, 없으면 기존 문구로 폴백), (2) 크론 작업 카드의 `pending bills crawl (NsmLmSts)` 라벨은 `nsmShortName`으로 파생(기본 source면 `국민참여입법센터 신규 의안 수집` 문자열이 그대로 유지), (3) 비활성 크롤러 배너 이름도 같은 short label을 쓴다. (4) 크롤러가 소유한 크론 작업 카드에는 활성 수집 소스 호스트를 배지로 붙인다(`data-testid="cron-source-pal"`/`"cron-source-nsm"`, globe 아이콘 + `likms.assembly.go.kr` 형태, hover title에 `수집 소스: …`) — 소유 판별은 `CRON_JOB_SOURCE_GATE`(`crawling and notification`→pal, `pending bills crawl (NsmLmSts)`→nsm)를 그대로 쓰고, 정리·감사·미러 같은 플랫폼 작업은 배지가 없다. short label은 `CRAWLER_SHORT_LABELS`(source 호스트 → 짧은 이름: `pal.assembly.go.kr`/`opinion.lawmaking.go.kr`/`likms.assembly.go.kr`)로 해석하므로 미지의 source는 폴백으로 처리된다. 카드에 `data-testid="crawler-pal"`/`"crawler-nsm"`을 추가하고, `e2e/helpers/responsive-contracts.ts`의 `/status` 계약을 텍스트 매칭(`main h3:has-text("...크롤러")`)에서 testid 기반으로 바꿨다 — **소스에 따라 제목 문자열이 바뀌면 텍스트 매칭 계약은 깨지므로 주의**. 검증: `svelte-check` 0, `e2e/status.spec.ts` 13 pass(소스–제목 일치 + 배지–소스 일치 테스트 포함, mock 모드), 실 백엔드(LIKMS 활성) 브라우저 실측 — 카드 `국회 의안정보시스템 계류의안 크롤러`/`likms.assembly.go.kr`, 크론 카드 `국회 의안정보시스템 신규 의안 수집` + 배지 `likms.assembly.go.kr`(PAL 카드는 `pal.assembly.go.kr`, 플랫폼 작업에는 배지 없음). `/status` 계약은 5개 뷰포트(320/390/768/1024/1440)에서 임시 스펙으로 전수 실행해 통과를 확인한 뒤 계약에 `cron-source-pal`/`cron-source-nsm` visible 항목과 nsm 배지 1줄 제한을 추가했다(임시 스펙은 삭제).
- **남은 프론트 정적 문구**: `/crawling-transparency` 의안 이관 흐름 다이어그램의 `국민참여입법센터` / `입법진행현황(국회입법현황)` 박스는 아직 하드코딩이다(설명 문장 `transferFlow.description`은 이미 payload를 따른다). payload의 `noticeSources` 항목을 사용해 배선하면 된다.
- **프론트 e2e 사전 실패 주의**: `e2e/responsive.spec.ts`는 `/discussions`의 `[data-testid="discussions-list"]`가 mock 모드에서 보이지 않아 첫 라우트에서 실패하고, 그 뒤 `/status` 계약은 아예 평가되지 않는다. 내 변경 이전(pristine 체크아웃, `git stash` 기준선)에도 동일하게 실패하므로 **선행 실패이며 이 작업과 무관**하다. `/status` 계약만 따로 확인하려면 `routes`에서 `/status`를 찾아 visible 셀렉터를 직접 검사하는 임시 스펙을 쓰면 된다. 크론 배지 추가 때 이 방식으로 `/status` 계약 전 항목을 5개 뷰포트에서 확인했고 모두 통과했다 — 즉 계약 자체는 현재 유효하고, 막는 것은 `/discussions` 선행 실패뿐이다.
