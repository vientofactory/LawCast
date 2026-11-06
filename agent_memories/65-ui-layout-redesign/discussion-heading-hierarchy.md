# Discussion Heading Hierarchy

## Visual change

The detail route previously gave bill context and the discussion title the same
18px type and white/transparent background, with separate context and toolbar
rules. The browser baseline reproduces this at 390px and 1440px in both themes.

The bill context now uses the existing muted surface token, a context label and
one soft bottom boundary. The discussion body starts after a responsive 24–40px
gap. Its title uses 24px on mobile and 30px on desktop; a topic label and a single
summary bottom rule separate the conversation from its comments. The toolbar no
longer contributes a redundant horizontal rule. No new nested card wrapper was
introduced; the existing heading semantics, actions and API behavior are retained.

## Responsive regression

The new cross-engine hierarchy suite includes 320/390/768/1440px, light/dark and
200% root text at 320px. The latter exposed a nonwrapping comment action row;
allowing that row to wrap fixes the measured 353px right edge at a 320px viewport.
Existing discussion tests cover posting, quote insertion, pagination and modals.

Allow theme color transitions to settle before running axe: a mid-transition
sample briefly reported 4.39 contrast on an unchanged quoted-comment control.
Stable light/dark scans of the complete main region have no violations.

## Evidence

Task-only originals, hashes, patch, source archive, guarded rollback, browser
captures and exact results are under the visualization directory
`discussion-hierarchy/VERIFICATION.txt`. The rollback is tested on a separate
copy; the workspace retains the changes. No commit or deployment is requested.

## Reply composer follow-up

The reply composer uses a single muted surface with a soft incoming boundary,
20px heading, persistent guidance, 14px inline-flex field labels and 16px inputs.
The privacy note and counter wrap independently. The submit button fills the
mobile width and returns to content width at the small breakpoint. Its named
section and textarea descriptions make the writing area discoverable without
changing submission, validation, quoting or closed-thread behavior.

Visual capture must scroll to the composer repeatedly until the existing comment
pagination settles; a single scroll can capture newly appended comments instead
of the composer. Evidence is in `discussion-composer/VERIFICATION.txt`.

The taller composer also exposed WebKit test clicks racing automatic pagination.
Reply submission regressions now wait for fixture comment 54 before filling and
clicking; submission itself is never retried. This avoids treating a moving click
target as a failed API submission and preserves the real click path.

## Thread skeleton follow-up

`ThreadDetailSkeleton.svelte` mirrors the current open toolbar, unboxed topic
heading, comment metadata/actions and muted reply composer. Its parent uses the
same `lc-discussion-body` gutter and top gap as loaded content; the old outer card
and boxed title placeholder are removed. Decorative blocks are aria-hidden,
contain no interactive elements and disable their pulse under reduced motion.
The loading region retains the existing rate-limit retry overlay.

The SSR page renders this fallback until hydration assigns discussionData; test
it using a JavaScript-disabled browser context, then separately verify normal
hydration removes the placeholders. No loader/API change or artificial delay is
needed to capture the real fallback. Evidence: `discussion-skeleton/VERIFICATION.txt`.
