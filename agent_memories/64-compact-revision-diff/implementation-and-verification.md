# Compact Revision Comparison

## Scope

Implemented locally on `codex/compact-revision-diff` in the root and frontend repositories. No release, version bump or commit was requested. Backend/API contracts, archive data and snapshot reconstruction are unchanged.

Related context: [revision-history UX](../62-revision-history-ux/implementation-and-verification.md), [progressive history](../63-progressive-revision-history/implementation-and-verification.md), and [frontend testing pitfalls](../repo/frontend-notes.md).

## Rendering and interaction

- `frontend/src/lib/components/NoticeRevisionCompare.svelte` uses automatic layout: viewport widths of at least 1024px show before/after hunks side by side; smaller screens keep each pair vertically adjacent. Manual layout buttons, local layout state and the child layout prop were removed in the automatic-layout follow-up below.
- `RevisionTextDiff.svelte` folds long unchanged intervals. Complete changed sentences supply immediate context; an optional checkbox adds short surrounding previews. Native disclosures expose the entire retained context. Empty/identical field evidence and reverse direction continue to use the existing parent contracts.
- Per-field previous/next controls move focus to the selected hunk with an explicit sticky-header offset. Writable derived selection resets when comparison text changes, but not when the display mode or context option changes. Navigation labels are compact enough for nested mobile panels.
- The hierarchy preserves the existing field selection, history pagination, endpoint controls and `noScroll` policy. UI labels remain Korean and all test descriptions/comments remain English.

## Diff correctness and bounds

The baseline `frontend/src/lib/utils/revision-comparison.ts` at `ffb4c5349150d6f563211b575dcea385ff80d637` capped its token LCS matrix at 40,000 cells and then marked everything between the shared prefix and suffix as changed. Two distant edits around 600 repetitions of unchanged Korean text reproduced this false highlighting.

`revision-text-diff.ts` now splits lossless sentence/newline units, matches shared intervals using bounded Myers edit-distance search, then refines changed sentences on Unicode code points. Very long unpunctuated changed sentences also split around long matching internal intervals. Every source character, delimiter and whitespace remains reconstructable. Each search caps its edit distance at 256 and work at 250,000 steps; wholesale changes retain a lossless coarse representation and receive an explicit UI notice rather than pretending to have precise highlights. Pure additions/removals bypass search.

`buildInlineDiffSegments` remains available from the original utility module as a compatibility re-export. Snapshot reconstruction and revision value formatting are untouched.

## Regression coverage

- `frontend/e2e/revision-text-diff.spec.ts` adds 17 tests: 13 algorithm cases and four browser width/theme cases. The deterministic randomized case checks 400 text pairs.
- Browser cases cover 1280px light, 820px dark, 390px light and 360px dark; disclosure/context toggles, selected mode, resizing without losing mode, hunk focus/navigation, reset after reversing direction, exact DOM sentence text, compact fixture height below 780px, no overflow, runtime errors and scoped axe A/AA checks.
- The mock-only notice `2210004`, comparison `cmpFrom=1&cmpTo=2`, has two small edits separated by long unchanged regions. Fixture content lives in `frontend/src/lib/server/revision-diff-mock.ts`; production data is unaffected.
- Pagination assertions now expect changed text separately from shared newline context. Shared context is checked independently; exact complete-source reconstruction is covered by the new utility tests.
- The existing frontend `web-vitals.yml` revision-regression step explicitly includes the new spec so CI will run it.

## Observed verification

- Baseline utility tests: 4 passed.
- Final focused comparison/history/pagination/navigation/detail run: **71 passed**.
- Production Node SSR consumer suite: **16 passed**, across desktop and Pixel 7 projects.
- Frontend lint, Svelte check (0 errors/warnings), Cloudflare adapter build, guideline checker (0 violations), and whitespace checks passed.
- A separate rollback copy restored five original files, removed four additions and matched every original SHA-256. The original long-text false-highlight behavior returned on that copy; workspace source stayed changed. Applying the saved patch to another restored copy reproduced all nine modified file hashes.
- Detailed commands, inputs, outputs, hashes, logs, snapshots, screenshots and the hash-guarded executable rollback are retained in `/Users/doyeonkim/.codex/visualizations/2026/11/02/01a19dc2-eedc-7ca0-a493-58a7eb0bdb0e/compact-diff-verification/VERIFICATION.txt`.

## Active revision feedback follow-up

`NoticeChangeTimeline.svelte` now renders the active revision's viewing action as a native disabled button labeled `열람 중`, with `aria-current="page"`, a revision-specific accessible label and muted non-hover styling. Other records retain real navigation links. The existing `activeRevisionForUi` value covers both explicitly viewed historical records and the implicit latest revision; no additional route state was introduced.

Two new desktop/mobile browser cases in `revision-history.spec.ts` first failed against the original enabled links, then passed after the change. They cover disabled state/no href/no native click navigation, switching to two historical records (including keyboard activation), re-enabling the previous record and returning to the implicit latest record. A fresh-server comparison/history/pagination/navigation run passed **48 tests**, including scoped accessibility checks; lint and Svelte check also passed. The first broad run reused a terminating development server and reported connection errors; the successful run used `CI=1`, zero retries and a fresh owned server.

This follow-up preserves all earlier uncommitted comparison improvements. Its separately scoped artifacts and rollback hashes are under the verification directory's `active-revision/` child.

## Automatic comparison layout follow-up

The owner requested removing the manual unified/split controls. `NoticeRevisionCompare.svelte` no longer has layout buttons, selection styling or local layout state; `RevisionTextDiff.svelte` no longer accepts a layout prop. Its existing 1024px CSS media query now directly controls `.lc-diff-pair`, keeping SSR and client behavior consistent without viewport listeners or navigation.

The four browser width/theme cases now assert that both mode buttons and the control group are absent. They verify the initial column count and resize through 390px, 1023px, 1024px and 1280px without clicking any view control. Context expansion, hunk navigation, direction changes, compact field geometry, accessibility and existing history/scroll behavior remain covered. The updated desktop case failed against the original controls before modification; the final focused run passed **48 tests** with zero retries, using an isolated owned server on port 5279. Frontend lint and Svelte check passed.

Scoped original hashes, patch, source snapshot, rollback and exact verification commands live in the verification directory's `auto-layout/` child. Rollback restored all three pre-follow-up file hashes on a separate copy while the workspace retained automatic layout.

## Signed feature-branch checkpoint

The owner subsequently requested committing and pushing the current state only, explicitly excluding PR creation and deployment. Frontend commit `64f0d2b45144994f927739a8bc8047ff2c54fd10` (`feat: improve responsive revision comparison`) was created with explicit `git commit -S`; local signature status is `G`. The commit is published on `origin/codex/compact-revision-diff`, verified with `git ls-remote`. The root checkpoint records that exact reachable submodule commit together with these notes. Both repositories remain on the feature branch; no version bump, main/dev update, PR, release or deployment is part of this checkpoint. Frontend lint and Svelte check were rerun immediately before committing and passed.
