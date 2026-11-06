# Revision Comparison Workspace

## Problem and interaction model

The comparison result was rendered before and outside the history disclosure, while selection, swap and clear controls lived below it. A real browser baseline confirmed the clear action was outside the viewport while reading the diff.

`NoticeChangeTimeline.svelte` now owns the presentation of a single history workspace. Desktop shows a record list alongside a sticky, keyboard-scrollable diff reader. Mobile switches between records and results rather than stacking a long diff above the list. URL selection and immutable snapshot reconstruction still belong to the route; no API or archive changes were made.

The shared selection bar remains available during scrolling. It measures the real sticky header and toolbar with ResizeObserver. If the header and settings consume more than 60 percent of the viewport, only the action row remains pinned; settings can be reached by scrolling upward. Narrow screens use compact pane labels and a labeled swap icon without losing the 44px target.

Mobile comparisons save the record reading position and invoker; switching back restores the position, and ending comparison restores focus. Deep links open the result pane. Resizing retains selection and switches layout without duplicate controls. Changing a comparison pair resets the bounded desktop reader, while field visibility changes do not. Short desktop viewports use document flow instead of a constrained reader.

## Deep-link positioning

The comparison is now inside the disclosure and its scroll margin includes the measured header and visible toolbar. The route waits for font readiness before the existing two layout frames, avoiding a Firefox comparison-entry offset after client navigation. In-place URL changes still retain `noScroll` and keyboard focus. The history section no longer uses deferred content visibility: its closed disclosure already omits the body, while a live open workspace needs accurate sticky, hit-test and enlarged-text scroll geometry. Enlarged-text tests remeasure native reveal geometry when upstream deferred sections resize.

## Verification

Evidence, commands, results and screenshots: `/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/revision-workspace/VERIFICATION.txt`.

The isolated browser configuration blocks service workers so response interception exercises the existing cursor/error fixtures rather than racing a newly controlling worker. Dedicated PWA tests remain responsible for worker behavior. The final report separately records any unchanged general-list navigation failures; the baseline copy is retained for comparison.


## Final local results

All 249 focused regressions passed on the fixed Node production build across Chromium, Firefox and WebKit. The suite includes 24 new viewport/theme accessibility cases, existing comparison axe/contrast checks, enlarged-text focus visibility, mobile return position/focus, responsive resize, native keyboard reader scrolling, deep links and 125-record paging/error recovery. Lint, Svelte check (zero errors/warnings), both adapter builds and the guideline checker passed.

The general pagination/history test was not counted in that focused suite. Its unchanged WebKit page-2 pointer navigation failure was reproduced against the original copy; Firefox scroll-origin assertions were intermittent in broader runs. Retained logs distinguish those findings from the fixed comparison work. No claim is made that the entire frontend suite is green.

The enlarged-text selection bar reveals its settings on select focus and aligns the toolbar when sticky containment near the section end would otherwise obscure the focused select. Pane buttons derive their accessible names from the same single visible text, avoiding a fragmented-label name mismatch.
