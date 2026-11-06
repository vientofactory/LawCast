# Home Scroll Cue

## Screenshot finding and implementation

The supplied screenshot shows a generic instruction and a separate boxed chevron sitting at the left edge of a wide empty row. The open-layout override stretched the inline link across the hero (`align-self: auto`, 1216px wide in the desktop baseline), while its children stayed left aligned. The old icon retained a border, background, blur and infinite bounce from the former card-based hero.

The cue now sits at the center of the transition between the status band and recent notices. Its visible label is `최근 입법예고 보기`, paired with one small decorative FontAwesome chevron. The separate icon box and bounce are removed, the link keeps a 44px minimum hit height and a visible keyboard outline, and hover changes only the text color. Reduced motion also removes the color transition. There is no global scroll-behavior change or JavaScript scrolling handler.

The native `#recent-notices` target receives `tabindex="-1"` and a 7rem scroll margin. Both native browser navigation and the hydrated SvelteKit hash path can move focus to the destination, while its heading stays below the sticky header. The accessible name follows the visible destination label, without a stale aria-label override; the section landmark remains intact.

## Verification

`frontend/e2e/open-layout.spec.ts` covers 320/390/820/1440px, light/dark and normal/reduced motion, plus JavaScript-disabled navigation. It checks centered content-sized placement, no icon box/looping motion, keyboard outline and Enter navigation, focused destination, heading visibility below the header, no horizontal overflow and axe. The existing home and navigation-scroll specs cover the surrounding page and route-scroll behavior; straight-divider cases retain the preceding status-band correction.

Artifact root:

`/Users/doyeonkim/.codex/visualizations/2026/11/03/01a19fac-56a1-7340-bd8e-f560fde41d36/scroll-cue-refinement/`

Final observed outputs and counts are recorded in `VERIFICATION.txt` and `results.json`. Before/after browser captures show the status-band/cue/recent-heading boundary. Original hashes preserve every previous uncommitted UI change. Guarded rollback and patch replay use independent source copies; the working frontend retains the patch on `codex/open-layout-redesign`. No dependency/version change, commit, release or deployment is included.

## Validation fixes

The complete accessibility suite caught a label-in-name mismatch when the old aria-label overrode the new visible label. The override is removed, the visible destination text is the accessible name, and the focused suite explicitly checks both that name and WCAG 2.5.3. Existing home/anchor tests use the new name. FontAwesome's component does not accept arbitrary `aria-hidden` props; its standard decorative SVG output already supplies `aria-hidden="true"`, which the browser tests verify.

## Final observed results

- 116 browser cases pass: 29 focused (17 scroll-cue and 12 straight-divider), 25 home/navigation and 62 production Web Vitals/accessibility/theme. No accessibility violations remain in the checked cases.
- Lint, Svelte check (zero errors/warnings), Cloudflare build, final Node build and guideline checker pass.
- Desktop baseline/restored cue spans 1216px with the old boxed icon; final cue is approximately 144px wide, centrally aligned within 0.01px and has no boxed icon. Native hash activation focuses the destination. Four final viewport/theme context images and keyboard-focus captures are retained and visually checked.
- All 251 original hashes are preserved. The final 251-file snapshot changes six paths (three source files, three browser specs). Independent rollback restores original hashes; patch replay matches all final hashes. All four completion artifacts are reopened; workspace retains the patch.
