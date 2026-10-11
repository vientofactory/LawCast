# 청킹·파생 필드 능력(capability) 회귀 게이트

세션 24에서 **사람이 손으로 발견한** 405건 title-chunk 회귀를, 다음부터는 테스트가 자동으로
잡게 만든 작업 기록.

## 1. 해결하는 문제 클래스

집계 지표(recall@k, MRR)는 **기존 청크를 대체하는 변경**에 거의 눈이 멀다. 요약 필드를 처음 넣은
구현은 지표를 올렸다 — title recall@1 0.167 → 0.333 — 그런데 그 상승의 원인은 요약이 아니라
**빈 `proposal_reason` 405건의 제목-only 청크를 인덱스에서 지운 부작용**이었고, 그 405건은 자기
제목으로 정확히 검색되던 능력을 잃었다(name_bench added coverage 80/133 → 48/133; 세션 24 §4).

지표는 "평균이 올랐다"만 말한다. 이 게이트는 **"어떤 공고가 어떤 능력을 잃었는가"**를 값으로 만들고,
후보 규칙을 직전 규칙과 비교한다.

## 2. 능력 오라클 — `semantic-search/lawcast_semantic/capabilities.py`

공고별 능력은 청커의 장부가 아니라 **원문 레코드에서 다시 유도**한다(수정된 청커가 스스로 만족시킬 수
없게):

| 능력 | 의미 |
| ---- | ---- |
| `indexed` | 청크가 하나 이상 생겼다 |
| `title_text` | 어떤 청크의 **텍스트**가 이 공고의 `subject`를 담고 있다 |
| `section:<라벨>` | `proposal_reason`이 만든 섹션마다 그 라벨을 단 청크가 있다 |
| `derived:<필드>` | 비어 있지 않은 파생 필드의 **텍스트**가 어떤 청크에 들어 있다 |

**함정(이 세션에서 잡음)**: `section:<라벨>`을 "원문에서 유도한 라벨 집합"으로만 계산하면 그 능력은
**공허하다** — 어떤 청커도 그 집합을 바꿀 수 없으므로, 모든 규칙 변경에 대해 항상 참이 된다. 라벨은
원문에서, **그 라벨을 단 청크가 있는지는 청크 집합에서** 판정해야 한다. 민감도 실측(픽스처 24건,
원문 유도 섹션 보유 12건): 라이브 규칙 위반 **0/24**, 섹션 라벨을 전부 `body`로 바꾸는 규칙 **8/24**,
라벨을 지우는 규칙 **12/24**. 같은 이유로 `title_text`·`derived:*`는 처음부터 청크 텍스트 포함으로
판정했고, `section:*`만 이 함정에 빠져 있었다.

`title_text`를 **엄격형**으로 정의한 이유: `compose_embedding_text`가 모든 청크 임베딩 입력에
제목을 앞에 붙이므로, 청크가 하나라도 있으면 "제목 어휘"는 언제나 존재한다(그 정의는 공허하다).
스왑이 지운 것은 **텍스트 자체가 제목인 청크** — 이름 질의가 score 1.000으로 받던 그 답이다.
본문이 법안명을 반복하는 공고는 능력을 유지하고, `proposal_reason`이 빈 폴백만 이 능력에 의존한다.

`derived:<필드>`도 메타데이터가 아니라 **텍스트 포함 관계**로 판정한다 — 라벨만 붙은 청크는 능력이
아니다(`test_derived_capability_is_re_derived_from_the_text_not_the_metadata`).

## 3. 게이트 3종 + 레지스트리

1. **`derived_field_diff(notices, chunker=...)`** — 파생 필드 게이트. `strip_derived`로 필드를 뺀
   baseline과 필드를 넣은 후보를 같은 규칙으로 청킹해 능력 집합을 비교한다. `lost`가 비어야 한다:
   **enrichment는 청크를 더할 수만 있고 뺄 수는 없다.**
2. **`compare_capability_indexes(before, after)`** — 규칙 대 규칙 A/B(패킹·예산 변경 등).
3. **레지스트리 강제** — `unregistered_fields(record_from_row(...))`가 비어야 하고, 테스트는
   `record_from_row`의 키 집합이 `{IDENTITY_FIELDS, LEARNING_FIELD} ∪ DERIVED_NOTICE_FIELDS`와
   **정확히 같음**을 단정한다. 새 레코드 필드를 선언 없이 추가하면 여기서 실패하므로,
   **새 파생 필드는 게이트를 우회할 수 없다**(등록하면 `derived_field_diff`와
   `test_every_registered_derived_field_reaches_the_index`가 즉시 그 필드를 감시한다).

## 4. 픽스처 — `tests/fixtures/notices-capability-gate.jsonl` (24건)

게이트가 구별해야 하는 네 형태를 실제 공고로 담는다(코퍼스 실측 2026-10-11):

| shape | 건수(픽스처/코퍼스) | 능력 |
| ----- | ------------------- | ---- |
| `empty_reason_summary` | 8 / **405** | `indexed`, `title_text`, `derived:ai_summary` |
| `empty_reason_plain` | 4 / 106 | `indexed`, `title_text` |
| `body_summary` | 8 / 19,396 | `indexed`, `section:*`, `derived:ai_summary` |
| `short_body_summary` | 4 / - | 위와 같음(짧은 본문) |

- 코퍼스에는 **긴 본문 + 요약 없음** 조합이 0건이다 — 요약이 없는 106건은 정확히 빈
  `proposal_reason`(`not_supported`) 공고라서 네 번째 조합은 존재하지 않는다.
- 재생성: `_workspace/build_capability_fixture.py`(호스트 전용, gitignored. 코퍼스는 CI에 없다).

## 5. 검증 — 게이트가 실제로 물어야 한다

**(a) 실제 회귀에 대한 bite 검증.** `lawcast_semantic/chunking.py`를 세션 24의 스왑 구현으로
되돌리고(빈 `proposal_reason` + 요약이면 요약 청크가 제목 폴백을 대체) 테스트를 돌렸다:

```
5 failed  (구조 계층)   ... corpus sweeps: LOST title_text 405 notices
8 failed  (검색 계층)   test_a_title_bearing_notice_is_reachable_by_its_own_title[2221827/16/15/13/12/11/05/04]
10 passed
```

코퍼스 스윕이 **405건**(실측한 그 클래스)을 그대로 보고했고, 검색 계층은 제목을 담은 청크가 없는
8건에서 실패했다. `cp -p` 백업으로 되돌린 뒤(sha256 동일 확인) **23 passed**. 즉 실패/통과 양방향이
모두 실측으로 확인됐다.

**(b) 검색 계층의 자기 축소 방지.** 처음엔 프로브 대상 집합을 현재 청커의 오라클에서 유도했는데,
그러면 회귀가 살아 있을 때 검사가 **조용히 좁아지고** 실패하지 않는다. 픽스처 identity로 고정해
(`TITLE_NOTICES` = 빈 `proposal_reason` 두 형태 12건) 회귀 시 8건이 실패하도록 바꿨다.

**(c) 스왑 감도 테스트.** `summary_swap`(스왑 헬퍼)을 chunk set으로 인덱싱해(프로브의 `chunks` 키 —
같은 검색 경로로 규칙 변형을 A/B하기 위해 추가) 그 클래스가 제목 청크를 되찾지 못함을,
영향 없는 공고(요약 없음)는 그대로임을 단정한다. 게이트의 입력이 실제로 물 수 있음을 고정한다.

**(d) 섹션 능력 민감도.** 위 함정을 잡은 뒤, 규칙 변경이 섹션 능력을 실제로 깎는지 별도로 측정:
라이브 0/24, 라벨 전부 `body` 8/24, 라벨 제거 12/24. `test_every_source_section_stays_carried_by_a_chunk`가
이를 고정한다(원문 유도 expected ⊆ 청크가 실제로 단 라벨).

**(e) 전체 상태.** ruff check/format clean, `pytest tests/ -q` → **304 passed**(+24; 기존 280).
게이트 모듈 단독은 24건 / 0.5~3초.

## 6. 사용법 (다음 에이전트용)

새 파생 필드(예: 공고 요약 외 enrichment)를 청킹에 넣을 때:

1. `capabilities.DERIVED_NOTICE_FIELDS`에 필드를 **등록**한다(등록하지 않으면 스키마 검사에서 실패).
2. 청킹에 배선하고 `chunker`가 그 텍스트를 실제로 담게 한다.
3. `pytest tests/test_capability_gate.py -q` — `derived_field_diff`가 손실 0을 확인하고,
   `gained`에 새 `derived:<필드>`가 나타나는지 확인한다.
4. 그 다음에야 `scripts/05_evaluate.py`의 지표를 본다(지표는 능력 손실을 못 본다).

패킹 규칙·예산을 바꿀 때는 `compare_capability_indexes(before, after)`로 같은 방식으로 대조한다.
A/B 측정 하니스는 세션 24의 `_workspace/ai_summary_ab.py`·`name_bench.py`가 여전히 유효하다.
배포 전후(또는 롤백 세트 대조)는 §7의 `scripts/07_capability_report.py`가 한 줄로 처리한다.

## 7. 아티팩트 리포트 — `scripts/07_capability_report.py`

게이트가 **규칙 대 규칙**이라면 이 스크립트는 **아티팩트 대 아티팩트**이며, 같은 오라클을 쓴다
(`capability_index_from_records` — 게이트 모듈의 테스트가 두 경로가 같은 청크 집합에 대해 같은 값을
낸다는 것을 고정한다). 능력은 청크 텍스트 + 소스 레코드의 성질이라 모델·FAISS를 쓰지 않는다:
전량 코퍼스도 수 초이고 OMP 충돌 경로가 아니다.

실측(2026-10-12, 라이브 21,177공고 / 117,718청크, DB 포함 **4.4초**):

```
index integrity : OK (117718 rows == id_map rows, fingerprint 7d8b7ff5da85)
capabilities    : indexed=21177 title_text=545 section:body=805 section:제안 이유=1 section:제안이유=3831
                  section:제안이유 및 주요 내용=22 section:제안이유 및 주요내용=16000 section:주요 내용=2
                  section:주요내용=3668 section:참고사항=1774 derived:ai_summary=21071
```

- `derived:ai_summary=21071`이 세션 24에서 실측한 요약 보유 21,071건과 **정확히 일치**한다 — 인덱스가
  DB의 요약 전량을 담고 있다는 독립 확인이다.
- 섹션 라벨에 **공백 변형**(`제안 이유`, `제안이유 및 주요 내용`, `주요 내용`)이 그대로 드러난다.
  라벨을 원문에서 재유도하기 때문에 생기는 정직한 목록이다.

롤백 세트 대조(실제 §8.1 사고 재현): `--artifacts artifacts/backup-pre-ai-summary --compare <라이브 기준선>`

```
capability deltas : title_text 545 -> 542 | derived:ai_summary 21071 -> 0
release check     : LOST — title_text (3 notices, e.g. [2200731, 2212742, 2214708]); derived:ai_summary (21071 notices, ...)
exit=1
```

- 요약 벡터 전량 손실을 잡는다(exit 1). **공고 단위 비교**이므로 "405건 잃고 405건 얻음" 같은 스왑이
  델타 0으로 숨지 않는다.
- `title_text 545 → 542`의 3건은 조사 결과 **요약 청크 텍스트가 법안명을 담고 있어**, 롤백 세트에서
  제목 청크가 사라져도 능력이 유지되는 정당한 사례였다(청크별 carrier 확인: `carrier_chunks=[9]`).
  즉 리포트는 거짓 경보를 내지 않으며, 동시에 `title_text`가 요약으로도 만족될 수 있음을 보여준다.
  이 발견을 `capabilities.py` 모듈 docstring에 명시했다.
- 같은 읽기에서 `chunks.jsonl` ↔ `id_map.json`의 행/ID 일치와 청크 지문 일치도 확인하고, 어긋나면
  `MISMATCH` + exit 1이다(구 이미지가 인덱스를 되돌려 놓는 사고를 사후에라도 잡는 줄).
- 종료 코드: `0` = 손실 없음, `1` = 능력 손실 또는 아티팩트 불일치, `2` = 인자/사용 오류.

테스트 5종(`tests/test_entrypoints.py`): 카운트 라인, JSONL 소스 경로와 무소스 오류, 스왑 회귀
(`title_text 3 -> 2` + `LOST (1 notice, e.g. [1])` + exit 1), 같은 세트 대조(`deltas : none`, exit 0),
지문 불일치(`MISMATCH`, exit 1). 테스트 픽스처 4형태 중 하나는 **요약이 법안명을 담은 공고**로 두어,
스왑이 제목 청크를 없애도 능력이 유지되는 쪽(거짓 경보 방지)까지 고정한다.

## 8. 한계 (주장하지 않는 것)

- 능력은 **구조적·이산적**이다. `title_text`가 있다는 것은 그 청크가 인덱스에 있고 검색 경로로
  도달 가능함을 뜻하지만, 실모델 랭킹에서 항상 1위라는 뜻은 아니다(픽스처 스텁 프로브에서만 확인).
  랭킹 품질은 여전히 `05_evaluate.py`·`name_bench`의 몫이다.
- `section:<라벨>`은 엄격하다: 메타데이터에서 라벨이 사라져도(텍스트는 유지) 손실로 보고된다.
  UI가 섹션 칩을 렌더하므로 의도한 엄격함이지만, 의도적 변경이면 게이트를 갱신해야 한다.
  반대로 **한 섹션의 본문이 전부 보일러플레이트라 청크가 안 생기는 경우**는 `detect_sections`가 그
  섹션을 드롭하므로 요구되지 않는다(거짓 실패 없음). 넓은 코퍼스 스윕에는 이 능력 검사를 넣지
  않았다 — 픽스처와 합성 형태에만 적용한다.
- `derived:<필드>`는 필드 **원문 텍스트 전체**의 포함을 요구한다. 요약을 의도적으로 압축·변형해
  인덱싱하는 구현은 손실로 보고된다(그 판단을 사람이 하도록 실패시키는 설계).
- 리포트의 소스는 **현재 코퍼스**다. DB가 인덱스보다 앞서 나가면 커버리지 감소로 나타난다(신선도
  신호) — 즉 인덱스 자체의 회귀와 소스 드리프트를 구분하려면 두 줄을 함께 읽어야 한다.
- 리포트는 텍스트 채널만 본다. 임베딩 벡터가 그 텍스트와 맞는지는 청크 지문 일치로만 확인한다
  (벡터 내용 자체를 읽지는 않는다).
- 픽스처는 24건·시점 1개(2026-10-11), 리포트 실측은 라이브 세트 1개(2026-10-12) 기준이다.
  코퍼스에서 재생성하면 수치가 달라질 수 있다.
- 커밋·버전 범프·배포는 미실시.
