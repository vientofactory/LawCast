# Open Frontend Layout Implementation and Verification

The later [neutral palette and section-hierarchy refinement](palette-and-hierarchy-refinement.md) supersedes the color/header/separator treatment described here while retaining the original open-layout architecture.

## Scope and source state

Implemented the [screenshot-based proposal](analysis-and-plan.md) on frontend branch `codex/open-layout-redesign`, based on `64f0d2b45144994f927739a8bc8047ff2c54fd10`. Root notes remain on `codex/ui-layout-audit`. No commit, push, PR, version change, release or production deployment was requested or performed. Backend/API contracts, archive snapshots, comparison algorithms and dependencies are unchanged.

Evidence directory:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/ui-redesign/`

The reader-facing `verification-report.html` links before/after screenshots, per-state axe JSON, source snapshots, commands, logs, patch replay and rollback evidence. `VERIFICATION.txt` and `results.json` are the detailed verification record and machine-readable summary.

## Layout architecture

- `frontend/src/lib/styles/layout.css` centralizes the page gutter (16/24/32px), working/document/form widths, open page headings/sections, row-based results, reading/metadata columns and comparison surfaces. The root layout imports it after the existing theme styles. Existing surfaces are preserved for independent objects, charts and exceptional states rather than globally deleting every panel's padding.
- Home physically places search before the platform facts. The facts are open summaries, not a stack of cards. Recent notices/discussions use aligned rows.
- Archive search has one form and one native `FilterDialog`. Search, status and reset remain available; dates, sort, page size, search modes and examples are disclosed. Query/URL contracts, weak relevance behavior and downloads are unchanged. Result titles precede supporting metadata.
- Detail original content precedes facts in DOM order. Desktop facts occupy an auxiliary column; mobile facts are a native disclosure. Important notice status, opinion eligibility, historical/source-deleted distinctions and the AI caveat remain available.
- `NoticeRevisionCompare` is a sibling before the history disclosure. Selected results therefore retain full width while record navigation remains independent. The diff algorithm, folding, automatic 1024px split, in-place selection and deep-link scrolling are preserved.
- Forms have a 44rem working width; dashboards/documents use purpose-specific open sections. Statistics and changes expose advanced settings through native disclosures.
- Visual review found that a long thread context still shrank beside utility buttons at 320px. The context now stacks actions on narrow screens, exposes the complete title and removes its redundant outer card.

## Accessibility corrections

- `FilterDialog` names the modal, makes background content inert through native `showModal`, traps Tab/Shift+Tab, returns focus on close, restores cancelled drafts and preserves committed URL parameters. A native dialog alone can allow Tab to enter browser chrome; the explicit guard keeps focus within the intended dialog sequence.
- `modal-focus.ts` adds inert isolation, focus entry/trapping/restoration and scroll locking to the existing animated `ModalShell`. The consent-banner coexistence and full-unsubscribe transition/API contracts remain covered.
- Corrected low contrast caused by the engine-status trigger's group opacity, quoted-comment helper text and the tagline's opacity animation. Decorative logo assembly/motion remains; supporting tagline text stays fully opaque throughout. The PWA animation regression now checks stable geometry and 4.5:1 tagline contrast instead of expecting invisible text.
- Increased history metadata summaries and comment actions, retained visible focus outlines and supplied an accessible chart description.
- Final screenshot inspection exposed two issues not caught by the first automated scan: the dialog surface was translucent, and date labels still inherited Tailwind's `clip-path` despite restoring their size/position. The dialog now uses an opaque theme background; disclosed labels explicitly clear `clip-path`. The expanded-dialog regression asserts both computed styles. Intermediate and corrected screenshots are retained.

## Test maintenance and new coverage

- Existing filter/statistics tests now open the real disclosure/dialog before interacting with its controls; they do not bypass the UI or silently skip the affected behavior.
- Native details can be opened before Svelte hydration. Initializing `bind:open` to false and resetting it on mount could close that user-opened panel. Facts now bind the element and only auto-open on a wide initial viewport; later breakpoint changes update the element directly.
- Navigation and challenge tests wait for a real hydrated interaction rather than racing SSR anchors. The latter previously performed a full document navigation, missing the intended `__data.json` intercept.
- The 429 configuration explicitly disables route-level mock fast paths and uses an unreachable backend fallback; otherwise the mock loader bypassed `handleFetch` and the forced-429 simulation never executed.
- PWA Cloudflare configuration resolves installed Wrangler through `npx --no-install`, so direct Playwright invocation does not depend on an npm-script PATH.
- `playwright.open-layout.config.ts` runs an isolated production Node build with deterministic fixture/feature flags. It is excluded from generic/live-backend configs and explicitly included in the Web Vitals CI workflow.
- The new suite scans 15 route/states at 320/390/820/1440 CSS px in light/dark themes, saves screenshots and per-state axe results, and covers content geometry, filter cancellation/application, expanded controls and focus containment. Full-DOM scans expose deferred content; existing production Web Vitals regressions separately retain native reveal/theme behavior.

## Observed browser geometry

At 390 by 900 CSS px with deterministic mock data:

- Home search input bottom: 1154px baseline, 358px modified.
- First archive title top: 1120px baseline, 408px modified.
- Comparison text width: 246px baseline, 358px modified.
- Original-content section top: approximately 1774px baseline, 763px modified.

The rollback copy returns the original geometry. These are local layout measurements, not shipped improvements or controlled usability/conversion metrics. All claimed visual findings have screenshots that were opened and inspected.

## Final verification and artifacts

The final evidence record includes lint/check (zero Svelte errors/warnings), Cloudflare/Node builds, the complete default mock regression, dedicated consent/429/degraded/challenge/IP suites, production Web Vitals and SSR consumers, Node/Cloudflare PWA suites, the final 120-state accessibility matrix and the guideline checker. See `results.json` for exact final per-suite counts rather than adding overlapping scenarios as unique tests.

Original SHA-256 values for 241 tracked files are preserved. `MODIFIED_FILE.tar.gz` contains the changed checkout; `DIFF_FILE.patch` applies to an original copy. `ROLLBACK.sh` guards modified hashes before restoring originals/removing additions on an explicitly named target. Rollback and patch replay run on separate copies; the working frontend stays modified. The release/deployment workflow has not been invoked.

Automated WCAG-tagged scans and keyboard regressions do not constitute full accessibility certification. Real screen-reader/OS keyboard/permission/installation behavior and all production content distributions remain distinct manual acceptance work.
