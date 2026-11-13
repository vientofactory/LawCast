# UI and Fixed-Copy Consistency Release

## Scope

Frontend 3.1.6 aligns discussion opinions, announcements, dedicated semantic
results and the board's weak-result tiers with the existing flat-list design.
Data loaders, API contracts, archive rows and received legislative, announcement,
discussion and AI-summary content are unchanged.

- Opinion rows use a transparent surface, shared separators, readable author/time
  metadata and shared actions after the body. System messages omit the extra role
  label in the masked-IP slot so the author is not repeated.
- Pagination skeletons follow the author/time/body/action structure. Closed
  threads do not show fake action placeholders.
- Quote navigation waits for scroll arrival, holds a subtle wash and leading
  marker for 2.2 seconds, then fades away. Repeated jumps cancel earlier timers;
  unmount clears the active target. Reduced motion uses instant scrolling and
  static feedback. No geometry change or pointer interception is introduced.
- Announcement and semantic/weak-result rows no longer use gray cards, thick
  leading borders or boxed metadata. Weak-result reveal/hide, batches of ten,
  native disclosure and first-new-result focus remain unchanged.

## Fixed Korean copy

The source inventory covers 1,492 Korean text/literal occurrences in 101 frontend
source/static files, deduplicated into 1,172 candidates. Mock fixtures, type/data
identifiers, branded assets, machine-facing documentation and received content
are protected or excluded rather than rewritten indiscriminately.

The `humanize-korean` Codex workflow performed diagnosis, all 11 shim-generated
chunks, strict reassembly and independent finalization. It changed 30 unique
phrases at 31 source occurrences in 18 files. Two existing toast assertions were
updated; fixture payloads were retained. Number/identifier/template guards and
non-copy AST structure checks pass.

The gate displays 0.2% change, grade B and self-check 6/6. The sole remaining
`footnote_anchor` warning misreads the unchanged JavaScript `60_000)` and `1_000)`
as repeated footnote `000)`. It also reproduces for original versus original;
the checker was not patched or the warning hidden. Grade B reflects the formal
minimum-change criterion for A, not detected semantic loss. Most labels were
already concise, so there was no change quota.

Evidence is retained locally in `_workspace/2026-11-14-001-c639/`: the complete
searchable before/after catalog, original snapshot, diagnosis, chunk outputs,
finalizer, guard control, literal test logs and guarded rollback bundle. A
separate copy restores all 19 task-file hashes and 15 Svelte compilations to the
pre-copy baseline; the actual checkout retains the edits.

## Final review and local gates

The Bugbot and security reviews ran independently and read-only. No production
blocker or security vulnerability was found. Bugbot identified one P2 coverage
issue: changing only the DOM theme after SSR content appears can race late
`theme.ts` initialization. The new discussion design/feedback fixtures now save
`lawcast-theme` before navigation and assert the actual theme before capture.
The corrected suites pass all 22 tests. The first remote CI run also exposed
obsolete card-background expectations in the broader layout/theme suites. Their
expectations now assert transparent rows, zero leading borders/insets and flat
metadata; contrast, axe and touch assertions remain intact. Test discovery is
unchanged: 148 layout cases and 48 cross-engine theme cases, all passing locally.
The test-only follow-up is GPG-signed as
`15f1baa2826b9cad24c8618a809b8bd9c4bea982`. See the shared
[frontend testing notes](../repo/frontend-notes.md).

- Default browser suite: 471 passed, 94 existing environment-gated skips.
- Dedicated semantic suite: 67 passed.
- Production theme/contrast checks: four passed.
- Frontend lint, Svelte/native TypeScript checks, Cloudflare build and agent
  guideline checker pass. npm 11.13.0 install changes only version metadata.
- Unchanged backend: 104 suites / 1,389 tests pass, alongside lint/type/build.
- Unchanged semantic sidecar: ruff and 421 tests pass. The local capability
  baseline has 123,344 consistent index rows and 22,400 indexed notices.
- Initial sandboxed gRPC bind failures are retained separately; the final local
  socket-capable runs pass without removing tests.

## Release integration

[Frontend PR 209](https://github.com/vientofactory/LawCast-Frontend/pull/209)
contains the complete UI/copy changes and version 3.1.6. Feature commit
`aec1f55316ce3d70bb59c55570fbf1b734df60b6` is explicitly GPG-signed and verified
by GitHub. Its reviewed source tree exactly matches the squash merge released below.

The root integration also includes the requested `AGENTS.md` Markdown-fence
correction and all previously uncommitted cache/ONNX/Attention verification
notes. The ONNX experiments remain local documentation only; no experimental
model, service source, dependency or production binding is promoted.

## Published frontend verification

- Release: [frontend-v3.1.6](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v3.1.6).
- Squash/main/tag/origin-dev commit: `b176dd4f6565df0051202f338e3c1294c2de0c1b`.
- Final [PR CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/43458050504)
  passes every job, including all cross-engine theme and shared-UI groups. The
  initial obsolete-expectation failures are retained, not presented as passes.
- [Production Pages action](https://github.com/vientofactory/LawCast-Frontend/actions/runs/43460342037)
  succeeds. Cloudflare deployment `39a5611c-1d18-459c-9229-518c5fe5dc33` reports
  production/main, the exact release SHA, `commit_dirty=false` and successful
  deploy stage. All seven encrypted binding names/types are preserved.
- The custom domain serves footer version 3.1.6. Read-only production browser
  checks pass announcement detail/back navigation, ten real semantic results,
  the real thread `/notices/2221556/discussions/4` and its visible quote-target
  feedback, plus a 390px dark announcement view with no horizontal overflow.
  There are no page errors. The all-status discussion tab is used because the
  current open-only list is empty; no thread/comment/subscription is created.
- Frontend and backend finish on `dev`, semantic-search on `main`; installs do
  not dirty either package lock. Only the frontend gitlink changes in the root
  integration; backend and semantic source commits stay unchanged.
- A separate complete source-copy rollback verifies all 330 original hashes and
  71 Svelte server compilations against frontend-v3.1.5. The deployed and working
  release remain 3.1.6. This is not a production rollback exercise.

Release logs, deployment metadata, production screenshots, source archives,
review receipts and the executable local rollback are in ignored
`_workspace/ui-release-20261114/`. Root CI/deployment outcome is retained there
and in the integration PR's Actions records after merge.
