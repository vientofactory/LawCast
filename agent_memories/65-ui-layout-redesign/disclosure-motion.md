# Disclosure Motion

## Scope and implementation

The screenshot showed that the notice facts panel changed abruptly between a heading-only state and the complete facts list. This follow-up retains its layout, native summary semantics, labels, dividers and responsive initial state; it adds measured height motion rather than another container.

`frontend/src/lib/utils/disclosure-motion.ts` provides a native details action with 240ms opening and 180ms closing, an ease-out curve, interruption from the current height, resize-aware target measurement and immediate reduced-motion updates. It enhances all nine native disclosure sites: facts, archive metadata, revision history, nested collection metadata, comparison fields, folded unchanged context, statistics settings, change settings and recursively rendered Markdown toggles. Existing button-controlled webhook guidance and advanced unsubscribe sections use matching reduced-motion-aware Svelte transitions.

## Native closing lifetime

The native `open` attribute must remain present while the body shrinks; removing it at the start hides the content before any closing frame can paint. Lazy history/archive bodies also remain mounted until motion finishes. Their controlled state callbacks are called before the opening measurement and after the closing animation. Old nested slide/fade wrappers are removed to avoid two independent height animations fighting each other.

A generation guard rejects stale animation completions. Closing children become inert until they disappear; an already-focused body control returns focus to the summary. Cleanup restores original inline styles and inert values. A bounded completion timer handles animations suspended by deferred offscreen rendering. Child-only resize observations avoid observing the animated height itself.

## Responsive and hydration state

Do not reset a mobile disclosure during hydration: it may already have been opened with native browser interaction. The wide viewport may auto-open facts on mount. Subsequent breakpoint changes use `syncDisclosure` to settle immediately, including an in-flight close where native `open` is still true. An idempotent `.open = true` assignment alone would emit no mutation in that state, so a MutationObserver alone does not handle this case.

## Evidence

Artifact root:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/disclosure-refinement/`

The production focused suite covers 390/1440px, light/dark, normal/reduced motion, Enter/Space, real intermediate painted heights, focus retention, rapid reversals, resize interruption, nested/lazy content, Markdown and settings. Expanded facts receive axe scans. Browser screenshots and sampled heights are retained. Baseline and independent rollback browser probes exercise the same facts panel with no animation calls; the modified build records opening/closing durations of 240/180ms.

Final observed test results and exact commands are in `VERIFICATION.txt` and `results.json`. Original source hashes include all earlier uncommitted UI work. Guarded rollback is tested only on an independent extracted copy, and patch replay must reproduce every final source hash. The working frontend remains modified on `codex/open-layout-redesign`. No dependency change, commit, release or deployment is part of this follow-up.

## Final observed results

- Default mock regression: 358 passed, 28 existing dedicated-environment skips.
- Production Web Vitals/accessibility/theme regression: 62 passed.
- Focused production disclosure suite: nine passed; four normal-motion combinations record intermediate heights and four reduced-motion combinations record no native animations.
- Lint, Svelte check (zero errors/warnings), Cloudflare build and agent-guideline checker pass. Test instrumentation lint and a wrong Markdown fixture path were corrected; final suites pass.
- Baseline/rollback browser probes record no native details animations; modified records 240/180ms. Actual paused midpoint screenshots retain closing content; normal running frames are sampled separately.
- All 250 originals are preserved. Final archive contains 251 source files with 12 changed paths. Two independently restored copies match original hashes; patch replay matches all final hashes. Four completion artifacts are reopened and the working source remains modified.
