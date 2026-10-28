# Search and Prompt UX Release Verification

## Scope

Frontend 1.25.5 contains the owner-requested PWA prompt placement, Open Signal search loader, and mobile keyboard fixes. Backend and semantic-search code and versions are unchanged.

- PWA installation aligns above cookie consent at matching widths with a 12px gap. Its content can scroll on short screens.
- `OpenSignalLoader.svelte` reuses the shared brand geometry on both semantic search surfaces. Colors follow the existing light/dark theme variables. Reduced motion shows a complete static symbol.
- The notices board chooses its loader from the destination URL, including the first transition from keyword search to semantic/auto mode. Keyword-only requests retain the spinner.
- Valid touch submissions blur editable fields before navigation or invalidation. Invalid semantic queries retain focus. Headless touch tests verify focus behavior, not native OS keyboard pixels.

## Local validation

- Frontend lint and Svelte check passed with zero errors and warnings.
- Version 1.25.5 does not collide with existing tags. `npm install` synchronized package and lockfile versions; the resolved dependency tree is unchanged.
- Full semantic browser suite: 45 passed.
- PWA production-runtime suite: 19 passed on Node and 19 passed on Cloudflare Pages. Both builds passed.
- Agent guideline checker: zero violations.

## Release evidence

- [Frontend PR 175](https://github.com/vientofactory/LawCast-Frontend/pull/175).
- Feature commit `27a7ae6c1c6d7d8be38a32fc89097ebb9b3b109b` was explicitly GPG-signed. Local verification reported a good maintainer signature; GitHub reported `verified: true`.
- [PR Web Vitals CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40692342176).
- PR checks passed, including Web Vitals, SSR API consumers and GitGuardian. Squash merge commit: `c775b37916d7db77b820008cd314333bde2feab5`.
- [Release frontend-v1.25.5](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.25.5) targets the merged release commit.

Related context: [frontend testing notes](../repo/frontend-notes.md), [PWA architecture](../50-pwa-installation/architecture-and-implementation.md), and [Pages deployment workflow](../52-pages-production-actions/migration.md).
