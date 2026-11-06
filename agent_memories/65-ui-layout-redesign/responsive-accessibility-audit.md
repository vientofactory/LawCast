# Responsive and Accessibility Audit

## Read-only baseline and coverage

This audit follows the landing typography changes. **No application or test source was modified:** all 251 frontend source filename/hash pairs remain identical. Branch remains `codex/open-layout-redesign`; no release or deployment was requested.

Artifact root:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/responsive-a11y-audit/`

- 1,584 baseline cases: 22 route/data/error states x 12 screens x light/dark x Chromium 151, Firefox 153 and WebKit 26.5. All public page templates are included, with a diagnostic route separated from the public finding count.
- 576 additional expanded-disclosure scans; 2,160 axe scans in total. Both normal and expanded document overflow counts are zero.
- 108 interaction/stress scenarios plus dedicated triage. Text spacing: 42 cases, no document overflow. CSS root-font 200%: 31/42 cases overflow. This is a font-preference stress test, not native browser zoom certification.
- Existing cross-engine regression: 192 passed, 18 failed. Failures are classified below instead of counted as 18 product bugs.
- Sixteen contact sheets (84 representative viewport captures) and individual issue evidence were opened and visually reviewed. Not every pixel of every screenshot received manual inspection.

## Confirmed findings and priorities

1. **P1 — Invisible home keyboard stops:** `frontend/src/routes/+page.svelte:384` hides a nav with `sr-only`, but its four links remain tabbable. Chromium/Firefox Tab and WebKit Option+Tab reproduce invisible focus. Reveal the nav on focus-within or make the section shortcuts visible.
2. **P1 — Landscape mobile menu clipping:** `frontend/src/lib/components/Header.svelte:243–254` uses a fixed overlay with an unconstrained, non-scrollable panel. At 667x375 its 425px panel clips the final menu item; scrolling leaves the item below the viewport. Bound and scroll the panel; coordinate background/focus behavior.
3. **P2 — Invalid expanded archive definition list:** `frontend/src/routes/notices/[num]/+page.svelte:1284–1302` places explanatory `p` siblings beside `dt/dd` inside a `dl` grouping div. Native Enter opening reproduces `definition-list` in all engines. Move explanatory paragraphs into `dd`.
4. **P2 — Push error contrast:** `frontend/src/lib/components/WebPushConsentForm.svelte:384–389` uses 14px red error text on a translucent red background. Light theme measures about 4.13:1, below 4.5:1. Twelve native Firefox matrix cases exposed it. An enabled-config + rejected-getSubscription fixture deterministically reproduces the same UI/style for screenshots and axe. A config failure alone hides the whole component and is the wrong reproduction state.
5. **P2 — User font-preference overflow:** increased root font size pushes narrow headers/documents to 497px on a 390px viewport and some desktop documents to 1792px on 1440px. Normal 320px reflow remains good. Review flexible header sizing/content-dependent breakpoints; do not confuse this test with browser zoom.
6. **P2 — Missing disclosure state:** `frontend/src/lib/components/WebhookGuide.svelte:9` opens content but exposes no `aria-expanded` before or after. Use native details or programmatic expanded state. `aria-controls` is optional, not the basis of the finding.
7. **P3 — Duplicate comparison landmarks:** `frontend/src/lib/components/RevisionTextDiff.svelte:95` labels each field's first change identically. Include the field's user-facing label in the region name.
8. **P3 — Markdown heading/name semantics:** `frontend/src/lib/components/MarkdownBody.svelte:37` maps the first body `##` to h3 after a page h1; announcement body also labels a generic div without a region role (`frontend/src/routes/announcements/[id]/+page.svelte:89`). Normalize heading levels and intentional landmark naming.
9. **P2 — Broken target references:** `frontend/src/routes/+error.svelte:43` lacks `id="main-content"` for the global skip link. The thread main references missing `discussion-thread-title` (`frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte:445,488`). Add stable targets including error/loading states.

## Test and environment interpretation

- Four Firefox failures are fractional geometry (`11.999984741210938` versus strict `>=12`), not a visual 12px-gap defect.
- Ten WebKit failures assume mouse clicks focus buttons and default Tab traverses the same controls as Chromium. Keyboard-origin dialog opening restores focus in all engines; Option+Tab stays within the WebKit modal. Update test starting conditions and platform keyboard assumptions rather than blindly changing app behavior.
- Four WebKit contrast failures sample opacity-transition intermediates. After a 350ms settle, focused and blurred status-hint contrast has no violations.
- The raw triage `keyboardEscapeClosed` field is sampled before the menu outro ends; it is not used as an Escape failure verdict.
- Initial WebKit native PushManager initialization stalled. Interrupted attempts are retained. Of 528 WebKit cases including real 404, 426 use an unsupported-PushManager fixture. **Native Safari/iOS push delivery and permission UX remain unverified.**
- A few bulk WebKit captures had an unpainted sticky header; isolated `networkidle + 400ms` captures show a visible 97px header at y=0. Settled evidence is retained rather than treating the transient capture as a persistent app defect.
- Mock `/notices/9999999` returns a detail fixture with HTTP 200. Real 404 coverage uses a truly absent path in a separate 72-case run.
- Axe `incomplete` is not pass. Common footer foreground/opaque-background colors were manually measured; raw incomplete nodes remain available. Invalid thread/Markdown references were manually confirmed.
- The `/cf-challenge-test` diagnostic route lacks ordinary page metadata/main/skip target; keep it separate from public findings and review production gating.

## Deliverables

- `audit-report.html`: findings, source links, screenshots, filterable full state index and scope limitations.
- `audit-summary.json`, `case-index.json`, `cases/`, `extra-404/cases/`: machine-readable evidence.
- `VERIFICATION.txt`: exact commands, outputs, statuses, source-hash verification and tool assumptions.
- `lawcast-responsive-a11y-audit.canvas.tsx`: standalone results canvas, also installed in the LawCast workspace's managed canvases directory and typechecked independently.

This is local production-build/mock evidence, not a deployed-state audit, real-device screen-reader certification or exhaustive arbitrary data/permission testing. Public findings were investigated but intentionally not patched in this audit-only request.
