# Site hierarchy audit

Reviewed all 15 page templates, revision-comparison state and error page across 390/1440px and light/dark themes. Diagnostic template was inventoried but left unchanged.

Explicit title roles in `frontend/src/lib/styles/layout.css` distinguish page (28–32px), section (20px), subsection (16px) and list title (18px). Status, transparency, proposals and license now use section roles. Announcement/discussion titles wrap instead of truncating. Shared page headings have 16px lower padding. Existing open layouts and single-owner boundaries remain.

Evidence: /Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/site-hierarchy/REPORT.md

68 browser cases: no overflow; 64 WCAG scans: no violations with reduced motion. Three-engine hierarchy tests: 12 passed. Additional existing open-layout suite exposed a normal-motion logo tagline contrast failure at 320px/light (3.17:1); suite was interrupted, not certified. Independent rollback restored 263 baseline hashes; active source remains modified.


## Follow-up

The contrast regression and supporting typography/action-priority findings were addressed in [readability and action priority](readability-action-priority.md), including completed full regression matrices and explicit native WebKit push initialization limits.
