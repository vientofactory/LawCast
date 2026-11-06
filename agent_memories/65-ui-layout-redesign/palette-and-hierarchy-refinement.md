# Neutral Palette and Section Hierarchy Refinement

## Feedback and reference

The second iteration responds to the owner's feedback that the initial open layout felt too dark, its colors unnatural, the header cramped, and its card removal insufficiently replaced by clear section boundaries. The reference is https://miseskorea.org/ . Actual desktop (1440px) and mobile (390px) browser screenshots were opened before changing styles. The reference supplies an editorial direction: bright neutral surfaces, gray section bands, restrained color and clear typography. Its photography, content and yellow identity are not copied.

This work continues `codex/open-layout-redesign`; all earlier uncommitted redesign work is preserved. No API, dependency, package version, release or deployment changes are included.

## Implementation

- `frontend/src/app.css`: white light-mode page, neutral charcoal dark-mode page, opaque neutral surfaces and graphite secondary text. Non-status metadata/file actions use neutral chips; success/deadline/error/diff semantics retain their colors. Shared surfaces no longer revert to hard-coded blue-black backgrounds in dark mode. Primary actions remain brand blue in both themes; brand files are unchanged.
- `frontend/src/lib/styles/layout.css`: 16px mobile / 20px desktop header padding, strong heading/list-start rules, result count and platform-status bands, consistent row separators and AI-summary left rules. Reading and comparison text keep their horizontal width instead of regaining nested-card gutters.
- `frontend/src/lib/components/Header.svelte`: opaque sticky background, no translucent backdrop/shadow treatment; active desktop navigation uses an underline rather than a filled tile. Logo and tagline retain their behavior.
- The urgent notice remains an alert with its original destination and text. Its full-width saturated red fill becomes a neutral band with a semantic warning icon.
- Theme chrome is synchronized through `src/app.html`, `src/lib/theme.ts`, static launch/offline documents and the web manifest. Saved/system theme selection remains unchanged.
- Input boundaries receive separate control-border tokens. Focus uses an actual outline, not a box shadow erased by the existing global shadow reset. New regression tests assert visible outline and at least 3:1 inactive input-boundary contrast.

- The full regression exposed a pre-hydration GET-form race in `e2e/changes.spec.ts`. The search test now retries the complete input-and-submit action until the exact query is reflected in the URL, then asserts the retained input value. It does not weaken the assertion, bypass the interface or add a timing sleep.

## Browser measurements

At 390px, actual logo breathing room changes from 4px above/below to 16px. At 1440px it becomes 20px. Header height changes from 73px to 97px / 105px. Mobile first-result title changes from y=407.953125 to y=440.953125, retaining first-viewport access while honoring the requested breathing room. Result-start rule changes from 0px to 2px. Page background changes from `rgb(244, 246, 248)` to white, and from `rgb(16, 24, 32)` to `rgb(36, 37, 38)` in dark mode. Brand blue is unchanged in both theme-specific brand variants. No horizontal overflow occurs in the direct comparison checks.

## Verification evidence

The final artifact directory is:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/palette-refinement/`

The report and `VERIFICATION.txt` contain final test commands, literal outputs, exit codes, screenshots and their review evidence. `results.json` records this follow-up's actual results, not counts carried over from the first redesign. The production open-layout suite covers 120 route/viewport/theme combinations and adds eight palette/header/hierarchy/focus regression cases. The static first-paint/PWA tests use the new palette expectations, not deleted assertions.

The original state for this follow-up includes the earlier redesign. All 247 current source hashes were preserved before edits. The follow-up patch covers 12 paths. The modified source archive, guarded executable rollback, patch replay and independent restored-source browser run verify the transaction without resetting the working frontend.


## Final observed results

- Complete default mock regression: 358 passed, 28 environment-gated skips. Those dedicated analytics/429/degraded/challenge/IP branches were not re-executed in this palette-only follow-up.
- Production Web Vitals/accessibility/theme regressions: 62 passed.
- Node PWA: 36 passed; Cloudflare PWA: 36 passed.
- Final production open-layout suite: 19 passed, including the 120 route/viewport/theme combinations and eight new visual-state/focus cases. All 120 axe reports have zero violations; the suite detects no page errors or horizontal overflow.
- Lint, Svelte check (zero errors/warnings), Cloudflare build and project guideline checker passed. Root/frontend `git diff --check` passed; no package or lockfile change.
- Additional light/dark 390px filter interaction scans have zero axe violations and verify focus restoration. Final focus, filter and fully entered mobile-menu screenshots were opened. The capture helper waits for the menu's entry animation rather than retaining a backdrop-only frame.
- The HTML report renders with 11 loaded images, no missing links/browser errors and no mobile overflow. Its desktop/mobile previews and final before/after image were opened and reviewed.
- Final archive and working checkout match all 247 modified snapshot hashes; guarded rollback restores all 247 prior hashes; the 12-path patch replays to the same final snapshot. The working frontend remains modified, with no commit or deployment.
