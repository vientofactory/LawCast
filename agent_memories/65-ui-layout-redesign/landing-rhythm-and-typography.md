# Landing Rhythm and Typography

## Screenshot findings

The supplied landing screenshot shows the eyebrow badges touching the main heading, undersized explanatory text and metadata, and status tags pushed toward the next column separator. A production browser baseline confirms a zero-pixel badge/title gap, 14px body/search text and 12px status descriptions. The introduction had no internal layout gap after the card removal; the open-layout style also reduced text sizes without establishing a replacement hierarchy.

## Implementation

`frontend/src/lib/styles/layout.css` gives the introduction a 20px grid gap, a 30–48px fluid heading, 16px mobile/18px desktop body copy and a bounded reading width. Hero sections use 28px mobile/36px desktop gaps. Badge text is 13px with a 36px minimum height; explanatory copy uses a relaxed line height.

Search controls use 16px type and 56px minimum height. Below 480px the input and submit button stack at equal width with a 12px gap. The submit selector includes its form because a later generic primary-button rule otherwise overrides its minimum height when the row stops stretching the button. The existing native GET form, loading state and query behavior are unchanged.

Keyword labels/metadata use 14/13px type. A dedicated grid and header replace mixed `space-y` utility margins and ad-hoc 11px text, providing a 12px header/chip gap and natural metadata wrapping.

Status summaries use 20–22px values, 14px descriptions and 32px icons. English labels stay next to their icons rather than at the next divider. The summaries stay in two columns through tablet widths and switch to four at 1024px. Previously fixed independent desktop dividers and the centered, unboxed scroll link remain intact. No new nested card containers or palette changes are introduced.

## Evidence and regression scope

Artifact root:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/landing-rhythm-refinement/`

The focused suite covers six widths (320/390/640/820/1024/1440px) in light/dark. It measures actual painted gaps, font sizes, control dimensions, responsive columns and overflow, and performs axe scans. The mobile priority guard now keeps readable search within the first viewport (675px on a 390x844 screen) rather than the old 450px slot that assumed tiny copy. Search still precedes status summaries. All metrics use a 900px-high viewport; component-only screenshots extend height after measurements so the sticky header does not cover the top of an oversized hero during locator capture.

The complete mock functional suite and production accessibility/theme suite run alongside the focused landing, scroll-cue and straight-divider cases. `VERIFICATION.txt` and `results.json` contain final observed results and exact commands. Original source hashes retain previous uncommitted work; independent rollback and patch replay verify reversibility while the working frontend remains modified on `codex/open-layout-redesign`. No package/version change, commit, release or deployment is included.

Korean introduction/search copy and status descriptions use `word-break: keep-all`; the first mobile capture exposed mid-word syllable breaks in the otherwise enlarged text. The final accessibility/layout suite is rerun after this visual adjustment. The main overflow fallback remains available for genuinely unbroken long tokens.

## Final observed results

- 462 cases pass: 358 default mock functional cases (28 existing dedicated-environment skips), 62 production Web Vitals/accessibility/theme cases and 42 focused cases (12 landing, 17 scroll-cue, 12 straight-divider and one mobile-priority/comparison case).
- Final production accessibility and focused layout cases are rerun after the Korean word-wrapping-only adjustment. Lint, Svelte check (zero errors/warnings), Cloudflare build and production Node build pass.
- Baseline/restored desktop: zero badge/title gap, 14px body/input, 12px status descriptions. Modified desktop: 20px gap, 18px body, 16px input and 14px status descriptions. Mobile input ends at approximately 452px in a 390x844 viewport and has a 56px height.
- All 12 landing cases have zero axe violations, no horizontal overflow and the expected control sizes/column counts. Final desktop/mobile/tablet and light/dark screenshots are opened and visually reviewed.
- Original/final snapshots contain 251 files, with three changed paths. Guarded rollback restores original hashes and patch replay matches final hashes. All four completion artifacts are reopened; working source remains modified. No release or deployment is performed.
