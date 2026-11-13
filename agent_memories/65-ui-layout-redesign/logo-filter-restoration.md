# Logo Animation and Discussion Filter Restoration

## Root causes

The logo component already matched historical commit `c82ae63398eb38d56f2b4ca9043ce27ba814d02c`. The regression was the Header tagline keyframe: `from.opacity` changed from 0 to 1, revealing the caption before the symbol and wordmark assembled. Restore the original media/keyframe block rather than replacing current responsive navigation.

Discussion status anchors inherited a 44px minimum height from shared button styles, but block layout left text above center. Explicit inline flex alignment centers every state while preserving the hit target; the tablist is constrained to available width.

## Verification

Three engines, two themes and two widths passed 12 timeline/geometry cases. Chromium text center offset changed from -10px to 0px. Four PWA logo regressions and six cross-engine filter regressions passed. Lint, typecheck and guideline checks passed. A separate restored copy reproduced both original defects across all 12 cases; all 254 source hashes were restored. Existing unrelated edits were preserved.

Evidence: `/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/logo-filter-restoration/VERIFICATION.txt`. Actual browser comparison: `/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/logo-filter-restoration/screenshots/verification-overview.png`.

## Symbol-only reference motion (2026-11-13, local working tree)

The owner's new video-reference request explicitly supersedes the historical intro contract above: keep the wordmark and tagline continuously visible, remove the header link's whole-logo hover scaling, and animate only the existing C/L/dot geometry. `BrandLogo.svelte` now uses a finite 1,800 ms stroke-thinning, erase/redraw and refill sequence. It runs once on document load and replays on brand-link pointer entry or keyboard focus, without restarting an already-running sequence. Static footer and icon assets stay unchanged. Cancellation restores the original complete mark; reduced motion disables playback and cancels in-progress effects.

**WebKit pitfall:** after toggling reduced-motion emulation back off, a retained `MediaQueryList.matches` can still report true when a newly created query already reports false. A focus event in this interval skipped playback. Re-read `matchMedia(preference.media).matches` in the playback guard and cancellation listener; keep the retained query only for change subscription. Tests wait for the setting to apply and explicitly blur before checking a new focus entry.

Chromium, Firefox and WebKit passed 27 viewport/theme/motion/frame/replay cases. The previous source and historical tests were preserved separately; baseline and separate-copy rollback each passed eight cases and all four original file SHA-256 hashes matched after restoration. Evidence and actual browser playback: `/Users/doyeonkim/.codex/visualizations/2026/11/12/01a1d1de-34f0-7550-94f8-f3d961cea01a/symbol-motion/`. This is a local preview change, not a release.

### Perimeter correction (same session)

The owner clarified that the reference redraws the silhouette boundary, not a thinned centerline. The initial attempt above is superseded. The corrected component keeps the original filled geometry in `data-brand-fill` and adds closed C/L/dot perimeter paths in `data-brand-outline`. The C boundary expands the radius-25 arc to radii 30/20 with round endpoint caps; the L boundary retains round caps and its outer join. Only perimeter dash offsets animate. The unchanged fill layer fades back in after all three outlines complete, and the outline layer fades away. No stroke-width animation remains.

The updated 30-case Chromium/Firefox/WebKit suite covers perimeter drawing, late fill, static text, reduced motion and replay. A browser-rasterized silhouette comparison requires intersection-over-union above 0.995 between the closed contour's filled shape and the original mark. Actual 1.8-second playback and refreshed artifacts replace the previous preview in the same evidence folder. The correction's baseline and separate-copy rollback use the immediately preceding centerline implementation, not the original historical assembly animation.

### Hover-only playback (same session)

The owner subsequently requested a static default and mouse-hover playback only. Remove the document-load intro claim, mount-time playback and focus listener entirely. Subscribe only to `pointerenter` and accept `PointerEvent.pointerType === 'mouse'`; touch entry and keyboard focus stay static. The 1,800 ms perimeter/fill sequence, non-restarting in-progress playback, reduced-motion cancellation and static footer are unchanged. Tests wait for the action's `data-motion-ready` marker before hovering so they exercise the real listener rather than a pre-hydration pointer event.

### Reverse-then-forward hover cycle (same session)

The owner requested removal of the hover-start fade and a continuous reverse/forward cycle. The current motion uses one mirrored 2,600 ms timeline: spatially unfill the complete mark, retract the full closed outlines in reverse order, then redraw them in forward order and spatially refill the mark. `clipPath` wipes the fill layer; no opacity keyframes are used on any symbol layer. Outline visibility is constant during playback and returns to hidden on completion/cancellation. Dash timing and easing mirror around 1,300 ms, with zero-speed reversal rather than restarting a second animation. Default static state, mouse-only triggering, no focus/touch replay and reduced-motion cancellation remain unchanged. The tests sample paired mirrored frames, absence of opacity effects and continuity immediately around the reversal point.

### Fill-only fades (same session)

The owner's latest reference clarification restores fade-out/in only for the internal fill. Replace the fill group's spatial `clipPath` wipe with opacity 1 -> 0 -> 1 at the same mirrored timeline offsets (0, 0.18, 0.82, 1). Keep the outer contour's reverse/forward dash sequence and constant visibility during playback unchanged. The entire logo, outline and text do not fade. The 2,600 ms duration, midpoint continuity, mouse-only trigger, static default and reduced-motion cancellation are preserved. Regression tests require intermediate fill opacity near 0.5 at 234/2366 ms, no clipping keyframes and opacity effects targeting only `brand-fill`.

### Reference-paced timing (same session)

The owner found the 2,600 ms cycle visually rushed. Rechecked the full 6.858-second reference at 2 fps: its active outline/fill change occupies roughly four seconds, with a substantial outline-only phase before the filled logo returns. These are visual sampling estimates, not measured input-event timestamps.

The revised cycle lasts 4,000 ms. Fill fades occupy 0–400 ms and 3,600–4,000 ms. Each contour now has a 1,360 ms retraction and redraw sweep, rather than 572 ms, with a gentler sine-like `cubic-bezier(0.37, 0, 0.63, 1)` instead of the steeper prior curve. Staggering is 80 ms and mirrored around 2,000 ms. The change allocates more actual time to reading the contour rather than merely adding a pause. Hover-only/default-static behavior, fill-only fades and reduced-motion cancellation are unchanged. Regression assertions pin both total effect duration and per-contour sweep duration, plus mirrored frames and continuity.

### Overlapping reversals without a blank midpoint (same session)

The owner found the slow midpoint visually empty/paused. Keep the 4,000 ms cycle and fill-only fades, but replace the shared fully-erased midpoint with overlapping per-contour turns. C/L/dot reverse at 1,840/2,000/2,160 ms respectively, with no duplicate hold keyframes. The C has already started redrawing while the dot is still retracting, giving a 320 ms overlap rather than a shared stop. Cap C retreat at 82/100 (at least 18% of its closed perimeter stays visible), L at 94/100, and allow only the dot to retract completely. Individual easing still has smooth local turns; the aggregate symbol keeps moving. Source tests pin 4,000 ms, original static/hover behavior and fill-only fades, retain-arc bounds throughout the cycle, continuous values at each turn and nonzero aggregate movement in every sampled 40 ms interval around the transition.

### Completion silhouette handoff (same session)

The owner noticed a sudden thinning at completion after increasing the contour width to 1.5. The width property was not shrinking. The closed-boundary stroke was still opaque over the fully restored fill, extending 0.75 SVG units beyond each silhouette boundary; `fill: 'backwards'` then removed the effect and the default `visibility: hidden` instantly dropped this extra overlay. A dedicated browser before/after comparison reproduced unequal screenshots at 3,999/4,000 ms.

The correction preserves width 1.5 and all four-second contour/fill timing, but blends the outline into the fill during the existing first/last 400 ms: outline opacity is the fill opacity's complement, stays 1 throughout contour movement, and reaches 0 before visibility cleanup. Default outline opacity is also 0, matching the final effect state. This is a silhouette handoff, not stroke-width interpolation. The animated fill also retains `will-change: opacity` so Chromium keeps the same compositing path at rest and during playback. Without this, the initial handoff fix still showed up to 48/255 channel differences at the final rasterization change; stable compositing reduced them to at most one quantization step. The finishing screenshot regression compares 3,999/4,000/4,050 ms, permits at most one 8-bit channel step before completion, and requires exact screenshot equality after settling; frame assertions also require complementary fill/outline opacity and a constant computed 1.5px outline width. Reduced motion still cancels directly to the static mark.

### Release CI: explicit static-link transitions

PR 208's first remote run passed the shared UI suites and all 24 brand cases, but the eight hard-reload style cases rejected `site-brand: all`. Removing the old parent `transition-transform` class had exposed CSS's initial `transition-property: all`, even though the link no longer had its scale motion. Explicit `transition-none` preserves the intended static parent and the existing startup border/outline guard. Do not restore whole-logo scaling or weaken the guard to fix this. The release follow-up changes only the parent link class.

## Frontend 3.1.5 release

[PR 208](https://github.com/vientofactory/LawCast-Frontend/pull/208) merged as `3accbf5610ddde7296834eae4386cb72c7bc9ed8`; [frontend-v3.1.5](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v3.1.5), frontend main and origin/dev all identify that commit. Both feature commits (`c89021e`, `397ad53`) were explicitly maintainer-PGP signed, and GitHub verifies the squash commit signature. Final PR checks passed in [run 43404760355](https://github.com/vientofactory/LawCast-Frontend/actions/runs/43404760355), including the unmodified hard-reload guard and all shared-browser suites. The first run's implicit-transition failure was fixed with explicit static-parent `transition-none`, not by changing the guard.

Cloudflare reports canonical production deployment `80245c2a-0292-43d2-aec9-6ddec73c5df0` as successful for the exact release SHA, completed 2026-11-13 19:06:11 JST. [Pages workflow](https://github.com/vientofactory/LawCast-Frontend/actions/runs/43406333546) uses the existing main-only project. All seven encrypted runtime binding names/types and the compatibility date/flags are unchanged; no binding value was logged or rewritten.

Local release gates passed frontend lint/check/Cloudflare build, 36 three-engine brand cases, all 32 production hard-reload/brand cases, full 36-case Node and 36-case Cloudflare PWA suites, backend 104 suites/1,389 tests, semantic-search 421 tests, and the agent guideline checker. The local capability baseline reports 123,308 consistent chunks and 22,394 indexed notices. Backend and semantic-search source versions are unchanged. Root pointer deployment verification is tracked with this release's external evidence in `symbol-motion/release-3.1.5/`.
