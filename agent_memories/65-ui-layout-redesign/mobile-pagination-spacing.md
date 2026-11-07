# Mobile pagination spacing

## Production finding

The owner's Android screenshot of the first page with 1,109 total pages showed cramped pagination controls. The shared pagination CSS used 44px minimum targets, 8px horizontal padding and a 2px flex gap. Centering the entire control cluster left unused space at both sides while multi-digit page numbers looked crowded.

The earlier pagination fixture had only two pages. It covered the nominal 44px target floor and keyboard/pending feedback, but not the visual breathing room of four-digit pages. New tests use a real SSR API fixture with 22,180 items and 1,109 pages, rather than replacing rendered text after hydration.

## Change

- Below 640px, the shared navigation uses a full-width three-column grid (48px arrows at the edges, a shrinkable center track) capped at 26rem.
- Buttons have at least 48px by 48px targets and 12px horizontal padding. The transparent surfaces and selected-page underline remain unchanged.
- The center page track has 6px gaps and can wrap for enlarged text without shrinking targets or removing first/current/last links.
- Below 360px, only decorative ellipses disappear and center gaps become 4px, preserving the real numbered jumps and arrows.
- Desktop pagination remains unchanged. The shared CSS applies consistently to every PaginationNav consumer.

## Local verification

- Baseline reproduction: the new 390px regression fails with `Expected: >= 48`, `Received: 44`.
- Frontend lint, strict Svelte/native TypeScript checks and build pass; npm 11.13.0 real install synchronizes package metadata and lockfile for patch 2.0.1.
- SSR consumer suite: 34 passing cases across desktop and mobile-touch projects. New checks cover 320/360/390/430px, light/dark themes, pages 1/555/1108/1109, 48px targets, 24px combined label padding, no horizontal overflow, actual touch navigation and 200-percent root text size.
- Existing flat-pagination accessibility, keyboard and pending-width tests: nine cases pass.
- Unchanged backend lint/typecheck/build pass; full unit suite passes 89 suites/1,284 tests when the local HTTP fixtures have loopback binding access. An initial sandbox-only run encountered `listen EPERM`; its failure is not a source regression and no test was skipped or weakened.
- Original CSS hash is preserved. Independent-copy rollback restores the 44px/8px rendering and original hash; the real working source stays at 48px/12px.

## Release evidence

Frontend PR and deployment details are appended after the rollout. Local logs, original/modified CSS, patch, executable independent-copy rollback and final verification record live under `/private/tmp/lawcast-mobile-pagination-20261107/`.

### Production rollout

- [Frontend PR 191](https://github.com/vientofactory/LawCast-Frontend/pull/191) merged as `e859d7a031352d245bb23195dba887f487f95a19`, matching main/dev and tag `frontend-v2.0.1`.
- [PR CI 42291212825](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42291212825) passes all eight jobs and 585 browser checks, including the expanded 34-case SSR consumer suite.
- [Pages deploy 42293821116](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42293821116) succeeds. Canonical production deployment `557b24c0-ab7e-41da-b456-7392a376f882` reports the exact release SHA. Domains, existing seven runtime binding keys and the disconnected native Git source remain unchanged; no secret values were exported.
- Read-only production probes pass 32 mobile states (320/360/390/430px, light/dark, first/middle/final-neighbor/final page), 48px targets, 24px combined label padding, non-overlapping controls, viewport containment and actual touch navigation. The footer reports frontend 2.0.1; backend remains 2.0.0.
- The first external probe had an overly strict whitespace-sensitive current-page selector; the harness now normalizes through text containment plus exact trimmed assertion. Repeated document loads also reached the existing 30-read/60-second visitor limit and rendered the expected retry UI. Completed states were preserved, the advertised cooldown was respected, and remaining checks resumed with 12-second document spacing and five-second touch spacing. No identity/header rotation or rate-limit change was used. All initial failure logs remain separate evidence.
- The released main tree is independently checked by [run 42293821288](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42293821288). Final main/root CI outcomes and all registered worktree checks are recorded in the external `VERIFICATION.txt`; the root pointer records the released tag, not the feature-only commit.

## Follow-up: Restore the pre-flat pagination window

The 2.0.1 width increase left the mobile-only first/current/last list in place. That list was introduced by the flattening change, not inherited from the pre-flat component. The user wanted the original omission rules, with only the visual treatment changed.

The pre-flat component at frontend `4829437^` uses one page window at every width: all pages when there are at most seven, the first four or last four near an edge, and the current page with one neighbor on each side in the middle, with first/last links and gap markers where needed. The follow-up keeps that page selection code unchanged, restores the first/last arrows on mobile, and lets the controls wrap instead of substituting a different list. Gap markers wrap with the following number. Flat styling, the 48px mobile targets, 12px side padding, keyboard focus and pending feedback are retained.

The same 1,109-page SSR fixture now asserts the exact visible page sequence at widths 320/360/390/430px in both themes and both input projects. The old mobile renderer fails the first-page sequence assertion; the restored renderer passes all 34 SSR consumer tests and nine existing flat pagination checks. This follow-up is verified locally.

### Follow-up release

[Frontend PR](https://github.com/vientofactory/LawCast-Frontend/pull/196) restored the original page window and was released as [frontend-v2.0.2](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v2.0.2), commit `18902ceb81d841c55fd5d52032344497fb19497c`. Pre-release checks passed: 43 focused frontend browser tests, 1,284 backend tests, 345 sidecar tests and the agent-guideline checker. Frontend PR CI succeeded before merging.

[Pages deployment 42348729456](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42348729456) succeeded, and canonical Cloudflare deployment `28f0fc7f-81f6-47c1-83ef-15eb5f55e661` matches the release SHA. Production checks confirmed the first and middle page windows, 48px mobile touch targets, no horizontal overflow, and tapping page 2 from page 1. The frontend main run is [run 42348729501](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42348729501); full final results are in `/private/tmp/lawcast-pagination-parity.qM1hHS/VERIFICATION.txt`.
