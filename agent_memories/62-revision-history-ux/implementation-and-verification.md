# Revision History and Comparison UX

## Scope and state

Frontend implementation on `codex/preserve-comparison-scroll`, including the scroll regression fix after frontend 1.25.10. The owner subsequently authorized release as frontend 1.26.0. Backend code and API contracts are unchanged; release evidence is recorded below.

Related context: [frontend pitfalls](../repo/frontend-notes.md), especially route scrolling, reactive URL state and mock SSR boundaries; [detail head overlay](../36-detail-chain-head-overlay/detail-chain-head-overlay.md) documents why detail reconstruction and timeline display must not modify archived data.

## Interaction model

- The detail page distinguishes viewing a preserved record (`rev`) from selecting two records (`cmpFrom` / `cmpTo`). Historical viewing retains the top warning and a latest-record link.
- The history disclosure shows newest records first, dates, changed field labels and independent viewed/base/target badges. Technical collection source and full verification hashes live in nested disclosures.
- Two native labeled selects support either selection order, changing either endpoint, reversing direction and clearing the selection. Identical endpoint options are disabled; malformed, missing or equal URL revisions receive explicit guidance instead of an empty comparison.
- Recent-pair and per-record previous-pair actions reduce selection effort. The changes listing also links directly to its event's previous/current pair.
- Comparison URLs open the history disclosure on hydration. Explicit timeline/comparison entry scrolls instantly with a sticky-header offset. Selection and field toggles preserve scroll and keyboard focus, including focus restoration after temporarily disabling a control.
- Diff summaries show changed/unchanged counts, dates and explicit baseline/target direction. Only changed fields are initially visible; unchanged fields appear collapsed when requested. Empty field coverage is distinct from identical known values. Booleans and lifecycle values use readable Korean labels.
- Network failure no longer masquerades as an empty timeline: the server loader returns a separate `changesLoadError` and the UI exposes retry through `invalidateAll` without resetting scroll.

## Comparison correctness

**MEDIUM**: the previous `buildSnapshotsByRevision` in `frontend/src/routes/notices/[num]/+page.svelte` (1.25.10, lines 551–567) initialized an empty state and applied only `afterValue`. If record 1 omitted a field and record 2 first changed it from an existing value, record 1 appeared to contain null. Comparing 1 to 2 mislabeled a modification as an addition.

`frontend/src/lib/utils/revision-comparison.ts:55` now seeds each field from its earliest available `beforeValue`, then replays events in ascending height order. A regression uses a proposal reason containing a newline, omitted from the first event, then modified and removed in later events. Additions still seed as null. The comparison uses only observed fields, rather than manufacturing empty rows for every label in the dictionary.

The bounded token LCS keeps unchanged text between separate edits. Shared prefix/suffix matching uses Unicode code points so highlights do not split supplementary characters. The matrix is capped at 40,000 cells; a lossless prefix/suffix fallback handles larger text. Original whitespace and line breaks are retained. Inline content remains Svelte-escaped text.

## Limits

The existing timeline endpoint defaults to the latest 20 events and returns the loaded length as `count`, not a total. This change does not expand or refetch that window. When the earliest visible height exceeds 1, the UI discloses the recent-record window. A deep link to an older, unloaded pair receives the unavailable-selection message and can be repaired through the visible controls. Comparisons describe fields evidenced in the available event window, not an independently fetched complete snapshot.

## Verification

- `e2e/revision-history.spec.ts`: snapshot seeding, lossless/multiple-edit/long-text/Unicode diff behavior, direct comparison entry from the changes list, editable endpoints, reverse/clear, invalid URLs, past-record navigation, desktop light/mobile dark layout, keyboard focus, scoped axe checks and highlight contrast.
- `e2e/navigation-scroll.spec.ts`: native link/pagination/history and anchor behavior plus comparison selection/toggle/clear scroll preservation. SPA tests first exercise a hydrated client handler; otherwise a premature anchor click can test full document history instead of the router.
- `e2e/notice-detail.spec.ts`: existing detail and comparison regressions, updated to semantic regions and the new history heading.
- `e2e/api-consumers.spec.ts` and its existing fixture: production SSR error/retry, zero/one-record states, a partial window, identical known content and absent field evidence, on desktop and mobile.
- The frontend workflow now runs revision and navigation regressions before the existing production Web Vitals and SSR consumer suites. Mock-specific UI cases require `DIFFCHAIN_UI_MOCK=1` and do not run against an integration backend accidentally.

Final local verification: frontend lint and Svelte check passed (0 errors, 0 warnings); the Cloudflare adapter build passed. The focused mock UI/detail/navigation run passed **42 tests**, and the production Node SSR consumer run passed **14 tests** across desktop and mobile. Scoped axe audits reported no violations in desktop light and mobile dark comparison views; added/removed highlight contrast was at least 4.5:1. Screenshots were reviewed locally. These results are local validation, not a GitHub Actions run or production deployment.


## Release frontend 1.26.0

- Feature commit `e04a03d3458502de77137ebbad56346adc3b8a0e` was explicitly GPG-signed, with a good local signature and GitHub verification.
- [PR 181](https://github.com/vientofactory/LawCast-Frontend/pull/181) passed GitGuardian and [PR CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/41221570025), including the 17 revision/navigation tests plus production Web Vitals and all 14 SSR consumer tests, before squash merge `9a7eadd342fc7f8d3790f87d63d23c098caf8d05`.
- [Release frontend-v1.26.0](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.26.0) targets that merge. `npm install` changed only version metadata before commit; reinstalling after fast-forwarding frontend `dev` and checking backend `dev` left both lockfiles unchanged. Frontend `dev`, `origin/dev`, `origin/main` and the tag match the merge commit.
- The history panel shell, hover/chevron controls and slide/fade durations match the archive panel. Accessibility snapshots wait for the disclosure animation to finish before measuring final contrast.
- [Production Pages deployment](https://github.com/vientofactory/LawCast-Frontend/actions/runs/41221966290) succeeded. Cloudflare canonical deployment `1b721349-8229-4ea6-94b7-c09f7a0dfc89` independently reports success and the exact release commit `9a7eadd342fc7f8d3790f87d63d23c098caf8d05`. [Post-merge regressions](https://github.com/vientofactory/LawCast-Frontend/actions/runs/41221966268) target the same commit.
- Actual production verification on `https://law.viento.me` used isolated desktop Chrome and Pixel 7 contexts with public production records and no response mocks. **Both complete scenarios passed**: version 1.26.0 in the footer, entry from a real changes-list comparison link, editable comparison direction, unchanged nonzero scroll through swap/show-all/clear, historical-record viewing and return to latest, opening/closing both disclosures, matching computed shell/summary styles, no horizontal overflow and no page runtime errors. These checks performed no production data writes or notification actions.
