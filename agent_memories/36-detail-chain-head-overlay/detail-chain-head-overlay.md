# Default Detail Response Served the Previous Revision

Production bug found on 2026-10-14: after the LIKMS detail capture fix (`backend-v1.15.2`,
`agent_memories/35-likms-detail-capture-source-fix/`) the `proposalReason` backfill started landing on
the diffchain, but the notice detail page still rendered the pre-backfill snapshot values for every
other detail field while the response advertised the chain head revision. The UI looked "stuck on the
previous revision".

## 1. Symptom

`GET /api/notices/2221891/detail` (the request the page load uses — no `rev`, no `includeTimeline`):

```json
{"revision": {"requestedRev": null, "resolvedRev": 2, "headRev": 2, "isHistorical": false},
 "originalContent": {"proposalReason": "<732 chars: backfilled>",
                     "billNumber": null, "proposer": null, "proposalDate": null,
                     "committee": null, "referralDate": null, "noticePeriod": null,
                     "proposalSession": null}}
```

`GET /api/notices/2221891/detail?rev=2` (the same revision the default response claims to serve):

```json
{"originalContent": {"billNumber": "2221891", "proposer": "송영길의원 등 11인",
                     "proposalDate": "2026-10-14", "proposalSession": "제439회", ...}}
```

So the response *said* `Rev #2` while serving `Rev #1` values. The public SSR payload
(`https://law.viento.me/notices/2221891`) confirmed the same nulls reached the UI, and the content
facts row rendered none of `의안번호` / `제안자` / `제안일` / `소관위원회` / `회부일` / `입법예고기간` /
`제안회기`.

`GET /api/notices/2221891/detail?rev=1` returns the same nulls plus an empty `proposalReason` — i.e.
the default response *was* the previous revision.

## 2. Root cause

`NoticeArchiveService.applyCurrentOverlayToDetail` (`backend/src/modules/notice/notice-archive.service.ts`)
overlaid the diffchain head onto the immutable snapshot columns, but only for a fixed subset:
`subject`, `proposerCategory`, `committee`, `contentId`, `proposalReason`, `lifecycleStatus`,
`sourceDeletedAt` (the list-item fields, applied through `applyCurrentOverlayFromDiffchain`).

The revision-aware path (`?rev=<head>`) instead runs `applyRevisionOverlay` over every entry of
`revisionTrackedFieldPaths`, which additionally covers `billNumber` / `contentBillNumber`, `proposer` /
`contentProposer`, `proposalDate` / `contentProposalDate`, `contentCommittee`, `referralDate` /
`contentReferralDate`, `noticePeriod` / `contentNoticePeriod`, `proposalSession` /
`contentProposalSession`.

Because `fetchAndUpdateProposalReason` recovered those fields through `updateNsmHtmlAndDetail` — an
append-only diffchain event that never rewrites the immutable snapshot row — they were present at the
chain head but invisible to the default response. Note the shape of the bug: the claim
(`revision.resolvedRev = headRev`) and the payload disagreed, which is what makes it a defect rather
than a documented "snapshot only" contract.

## 3. Fix

`applyCurrentOverlayToDetail` gained a second, explicit chain-head pass over a new
`detailChainHeadFieldPaths` list: the remaining revision-tracked fields (plus their legacy/alias keys).
It reads them with one `getLatestFieldValuesForFields` call and writes each through
`applyTrackedValue` — the **same writer** `applyRevisionOverlay` uses — so the default response is
defined to equal `?rev=headRev` for every tracked field. Fields without a diffchain record keep the
immutable snapshot value (a repair that never touched them is not authoritative). `isDone` stays out
of both passes, mirroring the revision-aware path's exclusion, because it lives in the summary-state
table.

Deliberately *not* changed: the legacy subset keeps its own guards (`canonicalizeProposalReason`,
non-empty required text, `contentId` write-back), so existing list/detail behavior is untouched. The
extra pass is additive.

## 4. Verification

- Live, pre-fix: the nulls above on the production API and the SSR payload for notice 2221891.
- Unit (`notice-archive.service.spec.ts`, "serves the chain head on the default detail response
  instead of the stale snapshot"): snapshot row with empty detail columns + a mocked chain head ->
  `revision.resolvedRev = 7` and every head value in `originalContent`.
- E2E (`diffchain.e2e-spec.ts`, "serves every chain-head detail field on the default response, not
  the previous revision"): seeds notice 1006 through the real `upsertNoticeArchive` +
  `updateNsmHtmlAndDetail` append-only path on a real in-memory SQLite DB, then compares the default
  response against `?rev=<headRev>`. **Discriminating check**: stashing only the service change makes
  this test fail (1 failed / 10 passed) and restoring it makes the suite pass (11 passed), so the
  test really pins the regression rather than restating the implementation.
- Gates: `npm run lint`, `npx tsc --noEmit`, `npm run build`, `npm test` (80 suites / 1111 tests),
  `npm run test:e2e` (43 passed, 3 suites env-skipped), `python3 tools/check-comment-language.py`
  (0 Korean prose comment lines).

## 5. Remaining / not fixed

- **`contentCommittee`, `referralDate`, `noticePeriod` can still be null even at the chain head** for
  LIKMS rows: pal-crawl's `INsmBillDetail` (`getDetail`) has no field for them, so
  `fetchAndUpdateProposalReason` has nothing to write and `preferIncomingTrackedValue` keeps the
  snapshot value. Filling them needs a new source (the likms `심사정보` fragment carries 제안이유 only;
  `소관위원회`/`회부일` would need the likms bill page's own panels or the list item).
- **Already-archived wrong `source_html`/`screenshot_blob`** remain unrewritable (first-fill
  immutability trigger); a one-off migration is still the only way to replace them
  (`agent_memories/35-likms-detail-capture-source-fix/` §backlog).
- The earlier finding that `INsmBillDetail` cannot express committee/referral/noticePeriod is the
  reason the detail row for a LIKMS bill still shows only the fields the adapter exposes.
