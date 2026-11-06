# Modal Close Icons and Motion

## Changes

- `frontend/src/lib/components/ModalCloseButton.svelte` provides the shared FontAwesome `faXmark` close affordance, a 44px target, theme-aware hover/focus styling and a preserved accessible label.
- `ModalShell.svelte`, `FilterDialog.svelte` and `SemanticEngineStatus.svelte` use the shared control. The existing mobile-navigation control is not a modal header and remains unchanged.
- `frontend/src/lib/utils/modal-motion.ts` centralizes gentle opacity/translation/scale motion: 200ms enter, 150ms exit, no bounce, zero motion duration when reduced motion is requested.
- Shared custom dialogs retain Svelte intro/outro lifecycle and modal-focus isolation. Native filters keep `showModal()` and their existing single-form ownership rather than remounting fields.

## Native close lifecycle

A native `close()` or default Escape cancellation removes the dialog from the top layer immediately, cutting off its exit. The filter prevents the native cancel default, restores cancelled draft fields, and changes its desired open state. The native dialog stays open, modal and scroll-locked until the 150ms exit finishes. Focus restoration then happens through `close()`.

A generation token discards stale animation completions. Reopening can start from current opacity/transform; disposal cancels animations and closes the native element. Apply/navigation closure does not revert committed fields. Scroll locking follows displayed lifetime, not just requested `isOpen`, so the background stays blocked throughout exit.

The backdrop has matching enter/exit fades and disables animation for reduced motion. The motion phase is a real Svelte-bound attribute so its scoped selectors are retained by the compiler.

## Evidence

Artifact directory:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/modal-refinement/`

The production modal suite covers 390/1440px, light/dark and normal/reduced motion: eight cases, each exercising native filters and shared new-thread dialogs. It checks FontAwesome SVG identity, no visible close text, target size, filter axe results, cancel/Escape/focus restoration, native modal/scroll locking during exit, sampled opacity/scale and zero-duration reduced motion. Screenshots and per-case samples are retained. Existing discussion/unsubscribe transition regressions remain in the complete default suite.

Original hashes for 248 files were preserved before edits. The final source snapshot contains 250 files and nine changed paths. Guarded rollback restores the prior source and removes only the two added shared modules; independent patch replay verifies final hashes. The working frontend remains modified on `codex/open-layout-redesign`; no dependency/version change, commit, release or deployment is included. See `VERIFICATION.txt` and `results.json` for final observed outputs and counts.

The filter test opener now waits for a routed closing phase to finish before reopening, rather than mistaking the still-painted outro for a ready dialog. The changes-page GET tests also retry their complete action after the observed pre-hydration field race and assert both exact URL values and retained controls.


## Final observed results

- Complete default mock regression: 358 passed, 28 dedicated-environment skips. Production Web Vitals/accessibility/theme regression: 62 passed.
- Final production modal suite: 8 passed (native + shared dialogs in each viewport/theme/motion case); native filter axe violations are zero in all eight. Ordinary frames confirm animated normal motion and zero positive duration for reduced motion.
- Native probe: baseline text/[] durations, modified FontAwesome X/[200,150] durations, rollback text/[] durations, each with restored focus and exit 0.
- Controlled real-animation midpoint captures confirm the closing dialog stays in the top layer and remains scroll-locked; the engine panel's shared X closes normally. Two paint frames follow seeking before capture to avoid a stale compositor frame.
- Lint, Svelte check (0 errors/0 warnings), Cloudflare build and guideline checks pass. Root/frontend diff checks pass and packages/lockfiles remain unchanged.
- Final 250-file archive and checkout hashes match; nine-path patch replay matches all final hashes. Independent rollback restores 248 originals and removes only the two added modules. Working frontend remains modified.
- Seven report images load, all links exist, no browser errors/mobile overflow. Native/shared/engine screenshots, intermediate frames and desktop/mobile report previews were opened and reviewed. No commit or deployment was performed.

## Floating consent and installation prompts

CookieConsentBanner and PwaInstallPrompt now share a reversible 200 ms opacity/12 px
translation transition in `frontend/src/lib/utils/floating-prompt-motion.ts`.
Reduced motion uses duration zero. Native installation still calls the single-use
browser prompt synchronously in the click handler, before any animation wait.
The outgoing install offer retains its CTA so dismissal does not shrink the card.

The cookie banner's action lifetime, rather than only its visible flag, owns
`--lc-consent-banner-height`. Release the reservation only after its outro removes
the node. Svelte freezes outgoing conditional content and makes it inert; do not
assume button `disabled` bindings inside an exiting branch will update. Regression
tests assert inertness and retained geometry instead. Restore keyboard focus to
the cookie settings shortcut after dismissal, without stealing focus moved elsewhere.

WebKit with reduced motion exposed a pointer-down blur race: the focused settings
label collapsed before pointer-up, moving the click target. Keep its label expanded
while either focused or hovered. The cross-engine floating-prompts suite exercises
actual pointer reopening, light/dark layouts, reduced motion, both consent choices,
installation errors, and prompt stacking.
