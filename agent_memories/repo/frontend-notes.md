- Frontend lives in frontend/ and validates with `cd frontend && npm run check`.
- Svelte frontend uses runes mode; use `$derived`/`$effect` instead of legacy `$:` reactive statements in route components.
- Stable AI/test navigation benefits from semantic landmarks plus explicit `data-testid` hooks on primary regions and nav links.

- Large multi-hunk apply_patch edits in frontend/src/app.css can misapply; prefer restoring from frontend submodule HEAD and reapplying targeted patches, then run npm run check.

- Playwright e2e (`npx playwright test`, run from frontend/) proxies /notices, /proposals, etc. to the REAL backend unless DIFFCHAIN_UI_MOCK=1 is set (status/home/changes pages use lib/server/diffchain-ui-mock.ts under that flag). If the real backend isn't reachable, notices/proposals specs fail with ERR_CONNECTION_REFUSED/502 Bad Gateway — unrelated to unrelated frontend edits; rerun the specific specs to confirm before treating as a regression.
- notice-detail.spec.ts "invalid notice number shows error page" and notices.spec.ts "pagination is shown when there are results" are pre-existing data-dependent flaky failures (depend on live archive DB state), not caused by status-page/UI changes.
