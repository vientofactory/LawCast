# Frontend 1.28.1 release verification

## Release identity

- Explicit owner authorization: merge PR 185, release/deploy according to project instructions and verify production.
- [Frontend PR 185](https://github.com/vientofactory/LawCast-Frontend/pull/185) squash-merged at 2026-11-06 20:08 JST.
- Release commit: `5741d0076733a8a3b81c393ecca4383f17a9777a`.
- [Release frontend-v1.28.1](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.28.1) targets that exact commit and matches package/lockfile version 1.28.1. The reviewed and released Git trees are identical: `5f5aece332218dcb5f69b75cffab0926c321c38c`.
- The two original feature commits were explicitly PGP-signed; GitHub verified the final reviewed head with reason `valid`. Only the short-lived feature branch was deleted. Persistent `dev` was preserved.

## Verification and deployment

- Premerge local frontend lint, check (zero errors/warnings), 23 script tests and agent guidelines passed. The original PR CI passed all 483 browser cases; its same-SHA warm job rerun passed all 147 cross-engine cases again. See [implementation evidence](implementation-and-verification.md).
- [Production deployment workflow](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42207979511) completed successfully in 2m8s, including lint, type check, production build and Pages upload.
- Cloudflare canonical production deployment `5cdd82b2-fff2-464e-b0cc-ea49e207e575` has the exact release SHA, branch `main`, environment `production` and successful deploy stage (2026-11-06 20:10 JST).
- Existing Pages project, two domains, disconnected native Git source and all seven encrypted runtime binding types were preserved. No secret values were printed or changed.
- [Postmerge full browser CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42207979583) runs on the release SHA with all original suites intact.
- Local backend lint, TypeScript check, build and all 88 Jest suites / 1,282 tests passed. Backend source and package lock remained unchanged.

## Actual production checks

The in-app browser checked https://law.viento.me after deployment, without mocking production data:

- Home renders the archive count and recent notices; footer changed from v1.28.0 to v1.28.1, with API v1.20.0 unchanged.
- Submitting the home search for `인공지능` navigates to the search results, showing 47 matches and populated records/AI summaries.
- Opening notice 2220608 renders its source text and AI summary. Expanding history loads all five records; recent comparison selects records 4/5 and renders one changed field with 14 unchanged fields.
- System status shows the overall normal state, healthy AI service and initialized cache. Refresh updates its query timestamp. Captured browser error logs are empty.
- No discussion, notification subscription or production data write was performed. Cookie consent was rejected for this isolated browser session.

## Synchronization and evidence

Frontend `dev` was fast-forwarded to release main and pushed. Backend `dev` and semantic-search `main` were synchronized without source changes. Actual npm install in both JavaScript submodules left their lockfiles unchanged. The root release branch changes only the frontend gitlink and session documentation; backend/semantic pointers remain unchanged.

Evidence is retained under `/private/tmp/lawcast-v1.28.1-release/`, including workflow JSON/logs, Cloudflare before/after metadata with binding types only, production accessibility snapshots and screenshots. The executable rollback script was tested only against an independent Git-index fixture; it restores the old frontend pointer with no production rollback. Active release/deployment stays at 1.28.1.
