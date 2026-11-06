# Disclosure Header Affordance

The current unboxed design and initialization fix supersede this iteration; see [interaction consistency](interaction-consistency.md).

## Implementation

The reference showed a facts header with only a generated plus/minus sign and little visual indication that the whole row was interactive. The change preserves native summary semantics and the existing disclosure-motion action.

- `DisclosureIndicator.svelte` renders a decorative FontAwesome chevron inside a 44px outlined surface; it is not a nested button and adds no accessible-name noise.
- `.lc-disclosure-trigger` supplies a subtle background, border, full-row pointer target, hover and pressed colors, and the existing visible keyboard outline. The chevron rotates with native `open`; reduced-motion users receive immediate state changes.
- Apply the same header to notice facts, archive metadata, revision history, changes settings and statistics settings. Already explicit webhook/Markdown controls retain their existing treatment.
- Remove the facts header's generated plus/minus text. Keep content panels open rather than wrapping their bodies in new cards.
- Flexing labels and nonshrinking indicators preserve narrow layout and enlarged root fonts. The prior NProgress blue change is preserved.

## Verified results

Artifact directory: `/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/disclosure-affordance/`.

- Baseline and modified browser probes: 12 cases each, covering Chromium/Firefox/WebKit, light/dark and 390/1440px. Five headers per case: 60 header checks. Each header retains real pointer and Enter/Space interaction.
- Modified facts receive scoped WCAG axe checks, hover and keyboard-focus screenshots, open/closed state checks, 44px indicator measurements and enlarged-font overflow checks.
- Additional 320px checks: six cases verify pressed feedback and root-font 200% reflow in all engines/themes.
- Existing focused disclosure, nested/lazy-content, content-priority and opinion-divider regressions: 33 passed across the three engines. Normal/reduced motion behavior is retained.
- Scoped formatting/ESLint, Svelte check and the Cloudflare build are recorded in the artifact logs. Source comments follow the project guidelines.
- The source snapshot preserves 253 files; the modified archive contains 254, with six task-only changed paths. Hash-guarded rollback is applied only to a separate copy; replaying the patch reproduces every modified source hash. Browser rollback reproduces the original unenhanced headers while retaining original native behavior. The real working frontend remains changed.

See `VERIFICATION.txt` for completed commands, literal results, exit statuses, hashes and the four deliverable paths. No commit, release or deployment was requested. All earlier uncommitted changes remain on `codex/open-layout-redesign`.
