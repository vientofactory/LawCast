# Notice consultation status

## Root cause and ownership

The home/board/detail UI interpreted `isDone=false` as an open consultation, including bills without a PAL `contentId`. The minimal `NoticeCard` mapper also dropped `contentId`, although the API model already exposed it. The detail opinion CTA already used the identifier, so its disabled action contradicted the green ongoing badge.

`frontend/src/lib/utils/notice-consultation.ts` now owns consultation classification; `NoticeConsultationStatus.svelte` renders it on the home, board and detail routes. `toNoticeCard` preserves the identifier. A nonempty identifier remains authoritative even when the archived link still points at LIKMS. For legacy responses omitting the field, only a PAL hostname plus nonempty `lgsltPaId` supplies positive evidence. An explicit null/blank identifier means pre-notice. Missing evidence means unknown, not open. Archive lifecycle badges remain independent and unchanged.

The UI does not claim that pre-notice or consultation-ended means a particular parliamentary disposition. The existing `isDone=false` filter includes pre-notice bills, so its label is now explicitly unfinished rather than an open opinion-window promise.

## Period and action consistency

The existing KST deadline helper determines expiration; a future start is scheduled. Pre-notice/unknown/scheduled entries do not display active D-day chips. Detail facts do not append deadline suffixes to those states. The opinion CTA uses the same classification and enables only for open consultation. Existing PAL URL construction remains unchanged.

## Search API limitation

Dedicated semantic results and weak-tier results currently contain only number/title/committee/score/excerpt, not consultation metadata. They explicitly display an unknown status and retain the detail link. This change does not introduce per-result HTTP requests or infer participation from relevance scores. The normal semantic-mode board uses full notice cards and the shared classifier.

## Verification

- Regression first: the pinned pre-transfer detail test failed on the original source because the new status badge was absent.
- Modified: 127 Chromium home/list/detail/classification checks passed, including 320px light/dark screenshots; a dedicated semantic search check passed.
- `npm run lint`, `npm run check`, and root agent-guidelines passed. See `/tmp/lawcast-notice-status/VERIFICATION.txt` for exact commands/results and build evidence.
- A separate restored checkout passed a browser test proving that rollback restores the old ongoing badge and disabled pre-transfer CTA; original hashes matched while the actual working checkout remained modified.
- Full-source design CLI: the new status component passes. Existing route/component source has 53 inherited errors, with identical error-rule counts before/after (27 missing test IDs, 7 raw colors, 4 unknown classes, 14 decoration utilities, 1 unknown token). They are not newly introduced by this feature. Browser screenshots and functional tests verify the changed status presentation, not a complete site accessibility audit.

## Delivery

Local feature branch: `codex/notice-consultation-status`. No release/version change, commit, push or deployment was requested or performed. Existing root-memory changes were preserved.


## CI stale-copy regression (PR 220)

- Run 45777754577 failed only in `web-vitals` -> `Test open layout and accessibility`: 147 passed, one failed. The production-performance step and all seven shared UI jobs passed. This was not an LCP/CLS budget failure.
- `frontend/e2e/open-layout.spec.ts` still expected the old pre-transfer guidance fragment `이관되기 전`, but the consultation-status change renders `아직 입법예고 전입니다`. Local production Node reproduction failed at the same assertion.
- Updated only this test's expected guidance and added explicit `pre_notice`/`open`/`ended` state and Korean label checks for all three pinned notices. Existing action enabled/disabled and divider assertions, 390/1440 widths and both themes remain. No app copy, performance thresholds, timeouts, retries or workflow changes.
- Validation/independent-copy rollback evidence: `/private/tmp/lawcast-ci-repair/VERIFICATION.txt`. Follow the same `codex/legal-review-defenses` branch and PR; this test-only correction does not start a new release or change the already-pending 3.3.0 version.

- Local modified full suite: 140 passed / 8 failed; the changed opinion-boundary case passed. The eight failures were broad accessibility scans observing transient notification contrast after proxy read errors. An unchanged original-spec copy also reproduces the 320px light notification contrast failure, separately from its old-copy assertion failure. No thresholds or unrelated notification code were changed for this CI repair.
- The isolated corrected case passes production Node (1 passed); the separately restored original case fails with the exact old expected fragment (1 failed). Signed test-only commit: `f6fa0960519782c778f0ed1dbb01a49ba8aca8ad`. New remote run: `45782940884`.

- Remote re-observation completed: run `45782940884` on exact patch SHA succeeds; all 9 jobs pass, including performance/production build and open-layout 148/148. GitGuardian also passes. Frontend working tree is clean, PR 220 remains open; no merge or deployment was performed.


## Release and deployment (2026-11-26)

- Final reviewed backend PR [254](https://github.com/vientofactory/LawCast-Backend/pull/254) merged to `4303e7fc33229e29b15bb1dc1f711a5c570729be`; release `backend-v3.2.10`. Root pointer PR [75](https://github.com/vientofactory/LawCast/pull/75) triggered successful main-push deployment run `45786456158`. Container verification reported `version=3.2.10 compiled_workers=2 no_ts_loader=true`; public `/api/version` returned `3.2.10`.
- Only after backend production verification, frontend PR [220](https://github.com/vientofactory/LawCast-Frontend/pull/220) merged to `c6aa9b5df8c6f00b8b8a8a3d93d698361b372270`; release `frontend-v3.3.0`. Production Pages run `45787647356` succeeded. Cloudflare canonical deployment `01092f6f-ab4c-456c-990a-0d5de8fd8079` reports production/success on that exact commit; public `/legal` contains `2026-11-26.3`.
- Root pointer PR [76](https://github.com/vientofactory/LawCast/pull/76) merged to `228de96928bc7ba73974e8e434fc2a7ffde15304` after PR CI passed. Both pointer commits were GPG-signed and changed only their corresponding gitlink. Memories were excluded.
- Local backend/frontend `dev` branches fast-forwarded to release commits; npm 11.13.0 full installs produced no package/lockfile changes. Root feature checkout fast-forwarded to final root main, preserving all memory WIP. Semantic-search pointer is unchanged.
- Evidence: `/private/tmp/lawcast-release-20261126/VERIFICATION.txt`. Existing LIKMS operational/legal review and inherited design-checker findings remain unresolved; deployment does not imply their resolution.

- Final re-observation: frontend main-push Web Vitals run `45787647276` and root final main-push run `45788634541` both completed successfully, all nine jobs each. Root backend and semantic-search deployment jobs both report success; public API still returns `3.2.10`.
