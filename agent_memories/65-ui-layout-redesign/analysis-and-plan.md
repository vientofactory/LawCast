# Screenshot-Based UI Layout Review and Redesign Plan

## Scope (proposal phase)

The owner requested analysis and a redesign proposal before implementation. No frontend source, dependency, API, version or deployment changes were made. The root documentation branch is `codex/ui-layout-audit`; the frontend remains at `64f0d2b45144994f927739a8bc8047ff2c54fd10`, including the existing compact comparison work.

Related notes: [frontend guidance](../repo/frontend-notes.md), [search UX](../29-search-ui-persona-audit/usability-audit-and-improvements.md), [progressive history](../63-progressive-revision-history/implementation-and-verification.md), and [compact comparison](../64-compact-revision-diff/implementation-and-verification.md).

The subsequent implementation and final evidence are recorded in [implementation and verification](implementation-and-verification.md).

## Evidence

The Korean reader-facing report, original Chromium captures, JSON geometry and a separate structural prototype are retained at:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/ui-layout-audit/report.html`

The report directly embeds the screenshots behind each finding. The companion `capture.mjs`, `extra-capture.mjs` and `proposal-capture.mjs` record the capture workflow. The isolated dev server used port 5286 with `DIFFCHAIN_UI_MOCK=1`, `E2E_SEMANTIC_SEARCH=1`, and an empty analytics container ID. These are local fixture observations, not production measurements.

- Twelve representative pages plus expanded comparison were captured in 35 initial route/width combinations at 1440, 820, 390 and 360 CSS px, height 900px. Additional scrolled sections, 1024px comparison, and dark comparison were inspected.
- At 390px, home search starts at document y=1100px; the first archive title starts at y=1120px (1143px at 360px).
- At 390px, detail facts start at y=1182px and occupy 568px; the original-content section starts at y=1774px in the selected fixture.
- Comparison text measures 246px at a 390px viewport and 216px at 360px, after the history/comparison/field/hunk/text insets accumulate.
- The webhook input is 1166px wide at 1440px but 308px at 390px: page gutter plus the form card's 24px inset compounds width loss.
- The 35 initial states showed no document-wide horizontal overflow. The problem is content priority and nested reading width, not a demonstrated global overflow bug.
- `app.css:143-156` already neutralizes most shadow/blur and overrides rounded classes. `lc-page-shell` itself has no padding. Fixing these globally would not solve independent route/component padding ownership.

## Recommended Architecture

Use a single page-gutter owner; open headings and sections; bounded form/read widths; row-based results; metadata sidebars that become disclosures on narrow screens; and sibling history/comparison workspaces instead of stacked decorative panels. Retain cards where a genuine independent object, chart or exceptional state needs a boundary.

Implementation order: freeze visual baselines, pilot archive list, detail/comparison, home/forms, then remaining dashboards/documents. The report specifies component boundaries, breakpoint behavior, measurable acceptance targets, accessibility checks and alternatives not selected.

Preserve search-mode/weak-result semantics, filter URLs, keyboard focus, archive provenance, opinion deadlines, source-deleted/historical distinctions, comparison folding/automatic layout and noScroll/hash behavior. Preserve content-visibility performance work and verify deferred theme contrast again.

## Prototype Limits

`proposal.html` is a standalone static wireframe, not application implementation. It does not connect search, persistence or comparison APIs. Its filter dialog opens, accepts input, dismisses with Escape and returns focus. Nine viewport/screen combinations at 390/820/1440px were checked without document overflow. The 390px prototype places the first result title around y=383px and exposes 358px comparison text width; these are structural feasibility measurements, not shipped improvements or controlled UX results.

Before implementation, extend coverage to 320px/400% zoom, announcement and discussion detail, real long content, all exceptional states and native keyboard/permission/PWA overlays. Every claimed visual issue or improvement must have an actual screenshot that was opened and inspected.
