# Straight Vertical Status Dividers

## Root cause and patch

The homepage status band uses an open grid, but the desktop rule was implemented as the left border of each former signal card. `app.css` still gives those cards an 8px radius, so the border curves around both endpoints. The supplied screenshot and a local production Chromium capture reproduce the same artifact.

`frontend/src/lib/styles/layout.css` replaces the desktop card border and extra left padding with an independent `::before` rule. It sits in the center of the existing 16px column gap, has a 1px width, a straight edge, a 4px inset at both ends and no pointer events. All four columns keep equal content width. The status band and labels remain unchanged; below 1024px the existing border-free responsive grid is preserved. No global radius change affects controls, icons, modals or other components.

## Regression evidence

`frontend/e2e/open-layout.spec.ts` covers six viewport widths (320/390/640/820/1024/1440px), each in light/dark. The cases assert zero card borders/padding, equal column widths, exactly three straight gap rules on desktop, no desktop rules in wrapped grids, unchanged destination links/focus, zero axe violations and no horizontal overflow. Per-case screenshots and measurements are retained.

Artifact root:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/vertical-divider-refinement/`

`VERIFICATION.txt` and `results.json` record final observed commands, outputs, exit statuses, browser screenshots and independent rollback/patch replay. The original snapshot preserves all previous uncommitted UI and disclosure work. This follow-up changes only layout CSS and its browser regression spec; the frontend remains modified on `codex/open-layout-redesign` without a dependency/version change, commit or deployment.

## Final observed results

- 91 browser tests passed: 62 production Web Vitals/accessibility/theme cases and 29 focused cases (12 straight-divider, nine disclosure, eight modal). Divider axe scans report zero violations.
- Lint, Svelte check (zero errors/warnings), Cloudflare build and guideline checks pass. Default functional suite is not re-run for this two-path CSS-only follow-up.
- Baseline and independently restored browser samples show three 1px card borders with 8px curved corners; modified samples show no card borders and three 1px independent gap rules with zero radius.
- Original and final snapshots contain 251 files; only layout CSS and the browser spec differ. Guarded rollback restores all original hashes and patch replay matches all final hashes. Four artifacts are reopened; workspace retains the patch.
- Desktop before/after, mobile light and desktop dark screenshots are opened and visually reviewed. No release or deployment is performed.
