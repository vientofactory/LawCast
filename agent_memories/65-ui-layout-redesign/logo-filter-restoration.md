# Logo Animation and Discussion Filter Restoration

## Root causes

The logo component already matched historical commit `c82ae63398eb38d56f2b4ca9043ce27ba814d02c`. The regression was the Header tagline keyframe: `from.opacity` changed from 0 to 1, revealing the caption before the symbol and wordmark assembled. Restore the original media/keyframe block rather than replacing current responsive navigation.

Discussion status anchors inherited a 44px minimum height from shared button styles, but block layout left text above center. Explicit inline flex alignment centers every state while preserving the hit target; the tablist is constrained to available width.

## Verification

Three engines, two themes and two widths passed 12 timeline/geometry cases. Chromium text center offset changed from -10px to 0px. Four PWA logo regressions and six cross-engine filter regressions passed. Lint, typecheck and guideline checks passed. A separate restored copy reproduced both original defects across all 12 cases; all 254 source hashes were restored. Existing unrelated edits were preserved.

Evidence: `/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/logo-filter-restoration/VERIFICATION.txt`. Actual browser comparison: `/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/logo-filter-restoration/screenshots/verification-overview.png`.
