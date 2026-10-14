# PAL Detail HTML Fallback Parsed Non-PAL Pages

Second production defect found on 2026-10-14 while verifying the previous-revision overlay fix
(`agent_memories/36-detail-chain-head-overlay/`). Fixed in `backend-v1.15.4`.

## 1. Symptom

`GET /api/notices/2221897/detail` (a LIKMS-sourced row) returned:

```json
{"originalContent": {"billNumber": "2221897", "proposer": "강승규의원 등 29인",
                     "proposalDate": "2026-10-14", "proposalSession": "제22대(2024~2028)제439회",
                     "committee": "제안회기 제22대(2024~2028)제439회",
                     "referralDate": "문서"}}
```

while the same row's chain head modified only `proposalSession` and its archive columns
`contentCommittee`/`contentReferralDate` were null. So the two junk values did not come from the
snapshot or the diffchain - they were **parsed out of the archived HTML**.

This also shadowed correct data in the UI: `buildDisplayContentFromDetail` uses
`input.originalContent.committee ?? input.notice.committee`, so a junk `originalContent.committee`
overrides the real list-level `소관위원회`.

## 2. Root cause

`NoticeArchiveArtifactSupport.extractPalFieldsFromSourceHtml`
(`backend/src/modules/notice/utils/notice-archive-artifact-support.ts`) reconstructs missing detail
fields from the archived `source_html`, assuming the PAL (`pal.assembly.go.kr`) legislative-notice
markup: `<li>제안회기 : ...</li>` labels and a first `<tbody><tr>` whose `<td>` 0-4 are
의안번호 / 제안자 / 제안일 / 소관위원회 / 회부일.

It was applied to **every** row with an empty detail column, whatever page was archived. It works by
accident on the old NSM `errorWrap` pages (no `<tbody>` row, thus no cell extraction), which hid the
bug. Once `backend-v1.15.2` made the capture follow the active source, LIKMS rows began archiving a
`likms.assembly.go.kr` bill-detail page - where the same cell positions hold unrelated text, giving
the committee cell "제안회기 제22대(2024~2028)제439회" and the referral cell "문서".

Observation window for the live symptom is therefore narrow: rows re-captured through the new LIKMS
code path (`2221897` was captured at 08:49 on 2026-10-14 and already showed the junk), while older
rows still holding the pre-fix error page show `null` instead of junk.

## 3. Fix

Gate the fallback on the archived page actually being PAL: `isPalNoticePage(httpMetadata)` accepts
`requestUrl` or `responseUrl` matching `/^https?:\/\/pal\.assembly\.go\.kr(\/|$)/i`. Non-PAL rows fall
back to nothing and keep the archive columns plus the diffchain as their authority.

The discriminator is clean in production data (`lawcast.db` probe, 21,030 rows):

| row kind | archived URL |
| --- | --- |
| PAL (`contentId` non-null, 1,163 rows) | `https://pal.assembly.go.kr/napal/lgsltpa/lgsltpaOngoing/view.do?lgsltPaId=ARC_...` |
| NSM (`contentId` null) | `https://opinion.lawmaking.go.kr/gcom/nsmLmSts/out/<billNo>/detailRP` |
| LIKMS (`contentId` null) | `https://likms.assembly.go.kr/bill/bi/billDetailPage.do?billId=PRC_...` |

A URL gate was chosen over a `contentId` gate deliberately: `contentId` is the PAL *notice* id and
the likms `billId` is documented as identical to it, so a future PAL enrichment pass could set
`contentId` on a LIKMS row whose `source_html` is still the likms page - the URL gate stays correct
there because it asks what page was actually archived.

## 4. Verification

- `does not read detail fields out of a non-PAL archived page`: LIKMS URLs + PAL-shaped markup ->
  every field stays null. **Fails without the guard** (stashing only the artifact-support change),
  passes with it.
- `still reads detail fields out of a PAL archived page`: same markup under a
  `pal.assembly.go.kr/napal/lgsltpa/...` URL -> fields are extracted, so the PAL path is pinned too.
- Gates: `npm run lint`, `npx tsc --noEmit`, `npm run build`, `npm test` (80 suites / 1113 tests),
  `npm run test:e2e` (43 passed, 3 suites env-skipped), `python3 tools/check-comment-language.py`
  (0 Korean prose comment lines).

## 5. Not fixed / adjacent findings

- **`originalContent.title` is the proposal-info line, not the bill title** for LIKMS rows
  (`"강승규의원 등 29인, 제2221897호(2026-10-14). 제22대(2024~2028)제439회"`). It comes from
  `sourceTitle` at upsert time. UI impact is low (the page heading uses `notice.subject`), so it was
  left alone - but do not treat `originalContent.title` as the bill title.
- **Some LIKMS rows still end with an empty `proposalReason`** even after a capture event
  (`2221897`: rev 2 carried only a `proposalSession` change). Whether likms genuinely has no text for
  those bills (`hasProposalReason: false` on the list item) or the `심사정보` fragment failed was not
  determined.
- Still unrewritable: the wrong `source_html`/`screenshot_blob` already archived for the 270 rows
  (first-fill immutability trigger), see `agent_memories/35-likms-detail-capture-source-fix/`.
