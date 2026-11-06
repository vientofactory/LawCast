# Single-Owner Section Dividers

## Report and baseline

The owner supplied a screenshot with a thin opinion-guidance bottom border followed by a strong original-content top border. The same pattern was reproduced in a real browser, including the pre-transfer fixture `/notices/2210013` with the original disabled opinion action and guidance text.

A production-build baseline scanned 15 routes at 390px and 1440px in default/expanded native-details states (60 states). It found 60 rule pairs under a content-empty boundary heuristic, including repeated responsive/expanded observations, not 60 unique source defects. Every cited family has before/after screenshots opened for visual inspection.

## Ownership rules and implementation

- `frontend/src/lib/styles/layout.css`: opinion guidance and comparison workspaces own only their incoming top rule; the original-content/history section owns the next boundary. This removes both separated double lines and adjacent stacked borders.
- Mobile facts retain their top rule, but no longer terminate with an outer bottom rule. Last fact/data/table rows have no redundant ending rule; internal row separators remain.
- A page heading followed directly by an open section, form or settings disclosure owns their shared boundary. The following section drops its top rule and redundant first-section gap.
- `frontend/src/routes/status/+page.svelte` marks the crawler grid with `lc-section-grid`. The first row defers to the page-heading rule: one item on mobile, both items in the two-column layout.
- The existing brand, neutral palette, navigation spacing, reading width, API contracts, opinion eligibility and disclosure behavior are preserved.

## Regression design

`frontend/e2e/helpers/section-dividers.ts` runs inside Chromium. It examines painted, broad, open horizontal border edges within main content. Pairs must overlap by at least 85%, be no more than 64px apart and contain no rendered text between them. Invisible closed descendants, outlined controls/panels, intentional text-separated boundaries and unrelated columns are excluded. This is a layout regression heuristic, not a universal image-comparison or accessibility certification.

`frontend/e2e/open-layout.spec.ts` applies the rule to 15 routes x four widths x two themes, in both default and expanded native-details states (240 scans). Each per-state axe JSON also records both divider-pair arrays. A separate case checks pre-transfer, ongoing and ended opinion states at two widths and two themes, including retained disabled/enabled behavior and the actual guidance wording.

## Artifacts and rollback

Evidence directory:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/divider-refinement/`

The original 247 source hashes were preserved before edits. The final 248-file source snapshot changes four paths, including the new test helper. The guarded rollback restores all original hashes and removes only that helper on an independent copy; the working frontend remains modified. Patch replay verifies the final snapshot. See `VERIFICATION.txt`, `results.json` and `verification-report.html` for exact commands, outputs and final test counts.

The restored copy reproduces the same baseline 60 rule pairs. Final production direct-audit and full-matrix results record zero detected duplicate boundaries. No commit, dependency/version change, release or deployment is included.


## Final observed results

- Default mock regression: 358 passed, 28 environment-gated skips. Dedicated analytics/429/degraded/challenge/IP branches were not re-executed for this border-only change.
- Production Web Vitals/accessibility/theme regression: 62 passed.
- Final full production open-layout suite: 20 passed. All 120 per-route axe JSON files have zero violations and record empty default/expanded divider-pair arrays (240 boundary scans). No horizontal overflow or page errors were detected.
- Opinion-boundary test additionally covers 12 pre-transfer/ongoing/ended viewport/theme combinations and preserves enabled/disabled behavior. The screenshot reproducing the owner's exact guidance state confirms two borders become one.
- Lint, Svelte check (zero errors/warnings), Cloudflare build and guideline checker passed; root/frontend diff checks are clean. Packages, versions and deployment remain unchanged.
- Independent direct browser audits: baseline 60 detected pairs, modified zero pairs, restored copy 60 pairs, each across the same 60 states with zero overflow. Those are repeated state observations, not unique defect counts.
- Final 248-file archive and checkout hashes match; the four-path patch replays to the same 248 hashes. Rollback restores 247 originals and removes only the added helper. The working frontend stays modified.
- Report QA: 14 loaded images, no missing links/browser errors, no mobile overflow. All cited before/after families, the extra discussion/thread/statistics contact and report previews were opened and visually inspected.
