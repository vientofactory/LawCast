# Full Worktree Reconciliation for Search

## Source coverage

The original feature worktrees were snapshotted, including all non-ignored untracked files. Apply changes to the current release commits, not to the older workspace bases. The backend input is already represented by v2.1.1, including later bounded-candidate and page-scoped enrichment refinements. The semantic release candidate adds the remaining 47 aliases, regression tests and documentation to existing SQ8/BGE20 tooling. The frontend candidate retains the existing correction UI and adds the public guide, discovery link, keyword metadata and a browser assertion. The guide reflects the live exact bill-number path.

## Verification

- Backend: 1,297 tests passed on the current v2.1.1 release. The preceding fixed-index local API replay found all 336 response pairs byte-identical.
- Frontend: the guide and its discovery link passed a Chromium check. The separate semantic browser suite passed 48 tests; Svelte diagnostics, native TypeScript and the Pages build passed.
- Search engine: 361 tests passed and four skipped; the 22,149-notice candidate chunk-set comparison found no capability loss. On the same local FP32 index, alias-family Hit@5 increased from 25/47 to 47/47; rank one improved from 17/47 to 39/47, with no rank-one regressions. This is an alias-only local retrieval replay, not a production traffic sample. The index format and serving model do not change.
