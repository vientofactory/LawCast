# 키워드 검색 FTS 기본화 (제안이유 토글 제거)

`/notices` 검색의 "제안이유(원문) 포함 검색" 토글이 있던 것을 제거하고,
**키워드 검색이 기본으로 제안이유까지 FTS5 인덱스로 매칭**하도록 백엔드·프론트엔드를 함께 고친 기록.

**Status: 구현·실측 완료 (2026-10-13).** 커밋/릴리스는 하지 않음(버전 범프 미실행).

---

## 1. 요구와 해석

요구: "제안이유 포함 검색 토글을 제거하고 기본값으로 키워드 검색에서는 FTS를 사용하도록."

해석한 계약:

- 키워드 검색은 **항상** 제안이유(proposalReason)를 포함한다 (이전 `fullText=true`와 동일한 범위).
- 제안이유 본문은 LIKE 스캔이 감당할 수 없는 크기이므로 **FTS5 `notice_archives_fts` MATCH**로 매칭한다.
- `subject`/`committee`/`contentProposer`는 **LIKE 부분일치를 그대로 유지**한다. FTS `unicode61`
  토크나이저는 단어 경계로 자르기 때문에 `보호`로 `상가건물 임대차보호법`을 찾지 못한다 —
  FTS만 쓰면 한국어 법률안명 검색 재현율이 크게 떨어진다.
- 요청 파라미터 `fullText`는 **API 표면에서 제거**한다. 남겨 두면 "무시되는 파라미터"가 되어
  두 가지 검색 의미가 공존하는 것처럼 보인다. 값을 보내던 옛 링크는 그대로 동작한다
  (true는 새 기본값과 동일, false는 의도적으로 새 기본값으로 바뀜 = 결과가 늘어남).

---

## 2. 변경 지점

### 백엔드

| 파일 | 변경 |
| ---- | ---- |
| `modules/notice/notice-archive.service.ts` | `applyArchiveSearchFilters`가 `fullText` 없이 **항상** FTS 분기를 적용. `ArchiveListQuery`/`ArchiveOffsetQuery`/`getArchiveNoticesByRankedNums`/`queryArchiveNoticeNumsByIsDoneFilter`/`getArchiveNoticesByOffset`에서 `fullText` 제거 |
| `modules/crawling/notices-query.service.ts` | `ArchivedNoticesQuery.fullText` 제거, 호출 2곳 정리, **캐시 전용 매처(`matchesSearchKeyword`)에 `proposalReason` 추가** |
| `modules/crawling/notice-search.service.ts` | `SearchNoticesQuery.fullText`·캐시 키·전달 인자 제거 |
| `modules/semantic-search/notices-hybrid-search.service.ts` | `BoardSearchParams.fullText` 제거 (키워드 경로 2곳) |
| `modules/semantic-search/semantic-search.service.ts` | 키워드 폴백 호출에서 `fullText: false` 제거 |
| `controllers/api.controller.ts` | `GET /notices/archive`, `GET /notices/search`에서 `@Query('fullText')` 제거 |
| `modules/notice/notice-archive.helpers.ts` | `buildArchiveWhereConditions`에서 `fullText` 제거, `proposalReason ILike`를 **무조건 포함** |
| `README.md` | `fullText` 파라미터 항목 삭제 + 검색 범위 설명으로 대체 |

### 프론트엔드

| 파일 | 변경 |
| ---- | ---- |
| `routes/notices/+page.svelte` | 토글 UI·`fullText` 상태·hidden input·"원문 포함 검색" 칩·`buildFilterLink` 오버라이드·폼 제출 처리 제거. `buildQueryLink`는 `params.delete('fullText')`로 옛 링크를 정리. 검색 입력 placeholder를 `법률안명, 소관위원회, 제안자, 제안이유 검색`으로 |
| `routes/notices/+page.server.ts`, `lib/api/client.ts` | `fullText` 읽기/전송 제거 |
| `routes/+page.svelte` | 홈 빠른검색 링크·hidden input에서 `fullText=true` 제거 |
| `routes/api/[...path]/+server.ts`, `lib/server/diffchain-ui-mock.ts` | mock에서 `fullText` 파라미터 제거, **제안이유 확장 매칭을 기본값으로** (실 백엔드와 동일 동작) |

**부수 개선(측정 근거 있음)**: 의미 검색이 "명확한 결과 0건 + 약한 계층 있음"인 상태의 빈 화면은
약한 결과 보기만 제공하고 키워드로 빠져나갈 동선이 없었다. 실측(`search=희토류`, 엔진 0건 /
키워드 4건)에서 이 동선이 더 유용하므로 **약한 계층 분기에도 `키워드 검색으로 다시 찾기`를 추가**했다.

---

## 3. 실측 (실 백엔드 + 21,188행 실 인덱스)

`search=<q>` 한 번에 대해 API가 반환한 `total`을 DB에서 직접 계산한 집합과 비교했다.

| 검색어 | API total | LIKE 3열(subject/committee/proposer) | LIKE 4열 | FTS | 해석 |
| ------ | --------: | -----------------------------------: | -------: | --: | ---- |
| `보호` | 4,953 | 1,266 | 5,345 | 4,634 | LIKE3 ∪ FTS = 1,266 ∪ 4,634 = **4,953** 일치 |
| `임대차` | 170 | 55 | 192 | 161 | 55 ∪ 161 = **170** 일치 |
| `국민` | 4,586 | 509 | 4,663 | 4,571 | 509 ∪ 4,571 ⊇ **4,586** |
| `국민연금` | 186 | 118 | 186 | 186 | 118 ∪ 186 = **186** 일치 |
| `희토류` | **4** | 0 | 7 | 4 | 제안이유에만 있는 단어 → 이전 기본값에서는 **0** |
| `제도적 기반` | 524 | 0 | 349 | 524 | 다중 토큰 AND 경로 확인 |
| `!!!` | 0 | 0 | 0 | – | FTS 질의어가 없어 LIKE 폴백, 500 없음 |

즉 새 기본값의 의미는 정확히 **`LIKE(subject/committee/proposer) OR FTS(subject/committee/proposalReason)`**다.

캐시 경로도 같은 의미를 얻는다: 활성 공지의 제안이유에만 있는 단어(`로봇산업은`, `패러다임`,
`맞이하고`)로 조회하면 `stats.matchedCacheCount`가 1/4/3으로 잡힌다 (이전에는 0).

`GET /api/notices/search?q=희토류`도 동일하게 4건을 반환한다(두 엔드포인트 동시 수정).

### UI 확인 (실 백엔드, 5197)

- `search=희토류` + `searchMode=keyword` → `현재 검색 결과 4건`
- 토글 DOM(`notices-full-text-toggle`) 없음, "원문 포함 검색" 칩 없음, placeholder 갱신
- 옛 링크 `?search=희토류&fullText=true` → 4건, 폼 제출 후 URL에서 `fullText` 사라짐
- `searchMode=auto`는 이 단어에 0건(엔진의 명확 결과 없음) → 빈 화면에서 키워드 동선으로 이동하면 4건

---

## 4. 검증 게이트

| 게이트 | 결과 |
| ------ | ---- |
| `backend`: `npx tsc --noEmit` | 0 errors |
| `backend`: `npm run lint` | clean |
| `backend`: `npm run build` | 성공 |
| `backend`: `npm test` | **70 suites / 928 tests passed** (FTS 술어 스펙 2건 신규) |
| `frontend`: `npm run check` | 0 errors / 0 warnings |
| `frontend`: `npm run lint` | clean |
| `frontend`: `DIFFCHAIN_UI_MOCK=1 npm run test:e2e` | **253 passed / 52 skipped / 0 failed** |
| `frontend`: `npm run test:e2e:semantic-search` | **33 passed / 0 failed** |
| 실 백엔드 응답 지연(21,188행, 최소 3회) | 검색 없음 11.4ms, `국민` 45.7ms, `보호` 76.1ms, `희토류` 69.9ms, `!!!` 74.2ms — 모두 100ms 미만 |

e2e는 `fullText` 스펙을 기본 동작 스펙으로 바꿨다: 제안이유 키워드가 플래그 없이 매칭되는지,
옛 링크가 계속 동작하고 제출 시 파라미터가 정리되는지, 토글이 사라졌는지. 홈 빠른검색 링크는
`fullText`를 포함하지 않는지로 반전했다.

---

## 5. 남은 관찰

- **중간 부분일치 구멍(의도)**: `LIKE4`(7) vs FTS(4)의 `희토류` 차이는 제안이유 안에서 단어 중간에
  걸린 3건이다. FTS 접두 매칭으로는 못 잡고, 제안이유에 LIKE를 걸면 21k행 전체 스캔이 된다.
  이전 `fullText=true`도 같은 한계였고, 속도를 위해 유지한다. 정확한 총계가 필요하면
  제안이유용 trigram 인덱스가 별도 과제다.
- **`auto`(의미 우선) 기본값**: 희토류처럼 엔진이 명확 결과를 못 내는 키워드에서는 기본 모드가
  0건을 보여준다. 이제 키워드 경로가 더 완전(제안이유 포함)하므로 "auto를 기본으로 둘지"는
  제품 판단이 필요하다. 이번 범위에서는 빈 화면의 키워드 동선만 보강했다.
- **API 파라미터 제거 = 계약 변경**: 외부에서 `fullText=false`로 호출하던 클라이언트는 이제
  결과가 늘어난다. 저장된 URL은 그대로 동작한다. 릴리스 시 backend 버전 범프(마이너 이상) 필요.
