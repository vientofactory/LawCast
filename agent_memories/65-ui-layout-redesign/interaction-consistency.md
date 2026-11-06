# Interaction Consistency and Initial Indicator Motion

## Current design

This supersedes the boxed indicator styling in [disclosure affordance](disclosure-affordance.md). Keep a 44px minimum native summary hit area, but render a bare 20px decorative chevron with no border, background or separate button surface. Use only restrained full-row hover/pressed feedback and the standard visible keyboard outline.

Ten native summary declaration sites now share the same trigger/indicator: facts, archive, history, record metadata, comparison fields, unchanged context, Markdown toggles, changes settings, statistics settings and webhook guidance. Advanced push settings reuse the same visual treatment without replacing its button/expanded semantics.

Text links receive a subtle underline; linked discussion titles use the link treatment. Home status links permanently name their destinations instead of relying on hover-only copy. Mobile comment actions show their existing action labels rather than icons alone. Already explicit buttons, navigation and form controls retain their existing structure.

## Initial-motion root cause and fix

Facts start closed in server markup; the wide-viewport mount handler synchronizes native `open`. An unconditional transform transition on the old boxed indicator animated this initialization, including rotating the entire outlined box. Browser transition events reproduce this in all six engine/theme cases. A diagnostic image pauses the observed old CSS transition at 90ms to expose the intermediate state; it is explicitly labelled as a paused diagnostic frame.

A persistent CSS animation-enable flag alone is insufficient: WebKit can deliver a stale user transition around breakpoint synchronization. Native indicator transforms now have **no CSS transition**. Only the explicit user `request()` path starts a finite, cancellable Web Animation from the current rendered transform. Programmatic `settle()`, external open-state observation, reduced-motion changes and disposal cancel it and synchronize immediately. This preserves interrupted/reversed user motion without animating initialization or responsive state changes.

The new Playwright regression covers initial entry with delayed hydration, real keyboard motion and a round-trip breakpoint change. It records both CSS transition events and explicit indicator animation calls. Initial motion is 0/6; real user motion remains 6/6. Reduced-motion controls remain immediate.

## Coverage and observed results

Artifact directory: `/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/interaction-consistency/`.

- Source inventory: 230 declarations (94 buttons, 10 summaries, 92 anchors, 24 inputs, seven selects, three textareas).
- Fourteen public page templates plus the error template are represented by 21 route/data/error states. Diagnostic-page controls are separately captured.
- Public visual/accessibility matrix: 252 cases (21 states x 390/1440px x two themes x three engines), 108 expanded scans and 360 axe scans; zero detected selected-rule violations and normal/expanded overflow.
- Six additional 320px/theme/engine cases cover enlarged fonts, persistent home cues, visible mobile action labels, conditional subscribed-push settings and reduced motion. Push fixtures perform no delivery/unsubscribe request.
- Cross-engine regressions: 246 passed. Functional regressions: 370 passed, 28 existing conditional skips. Lint, Svelte check (zero errors/warnings), Cloudflare/Node builds and the project guideline checker pass.
- An exploratory dark CTA contrast failure was corrected by using the theme accent token instead of fixed sky blue. The exploratory WebKit breakpoint failure led to the explicit user-only animation implementation; neither exploratory failure is presented as a final pass.
- Mobile dark captures cover every public route/state before and after; representative direct control captures and before/after initial-motion frames were visually opened. Raw axe incomplete nodes remain review states, not passes. Browser viewport and local fixture coverage is not native-device/push-delivery certification.
- All 254 original source hashes are preserved. The modified archive also contains 254 files, with 15 task-only changed paths. A separate-copy rollback restores the original styles and initialization motion; patch replay matches every modified hash. The actual frontend remains modified on `codex/open-layout-redesign`.

Exact commands, outputs, status codes and four artifact paths are in `VERIFICATION.txt`; the browsable report is `final-report.html`. No commit, release or deployment is part of this task.

## Theme switch idle surface

The dark header switch appeared hovered because its default wrapper used
`--lc-surface-primary` over the darker header background. Real browser measurements
confirmed `:hover` was false. The track and thumb already convey theme state, so
the wrapper now has transparent background/border and no idle shadow. Hover fill
is limited to fine pointers with hover support, avoiding sticky touch feedback;
the shared focus-visible outline remains unchanged. Regression coverage checks
both themes, desktop hover/leave, keyboard focus/Space, and mobile-menu touch toggle.
Evidence: `theme-switch-idle/VERIFICATION.txt`.

## Webhook creation guide

WebhookGuide now uses an open six-step ordered list with separate headings and
explanations, subdued numeric markers, and a single neutral URL reference band.
The old information card, warning card and boxed header icon are removed. Both
accepted URL prefixes remain literal text and wrap at narrow/enlarged widths.
The native details/summary, disclosureMotion action and bare chevron are preserved.
Tests cover keyboard and pointer disclosure, reduced motion, 320–1440px widths,
200% text and both themes; browser axe scans are scoped to the guide.
Evidence: `webhook-guide/VERIFICATION.txt`.
