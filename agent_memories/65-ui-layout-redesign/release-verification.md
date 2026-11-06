# Frontend 1.28.0 release and production verification

## Authorization and release identity

The owner explicitly authorized merging PR 184, releasing and deploying under the project workflow, and verifying production on 2026-11-06 JST. This supersedes the earlier premerge instruction to leave PR 184 open.

- [Frontend PR 184](https://github.com/vientofactory/LawCast-Frontend/pull/184) was squash-merged at `f35595f6234809b4c487c1f988bd9dbc1d32e64f`.
- [Release frontend-v1.28.0](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.28.0) targets that exact commit, with generated release notes.
- The existing minor version `1.28.0` was already appropriate for this non-breaking feature release. Both package-lock version fields match package.json, and no existing tag collision existed.
- Reviewed feature head `dadb7a6` and released squash commit `f35595f` have the identical source tree `2a3b205500e78be1ba6096ace90c5ebb1180e56f`.

Related implementation: [common notifications and premerge review follow-up](common-notifications.md), [request failure states](request-failure-states.md), and [frontend testing guidance](../repo/frontend-notes.md).

## Preflight and frontend deployment

Frontend lint, Svelte check (zero errors/warnings), Cloudflare production build, clean diff verification and the root agent-guideline checker passed immediately before merging. The latest PR CI already passed 483 browser cases and GitGuardian.

[Production Pages deployment 42158276164](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42158276164) succeeded in 1m52s. Cloudflare independently reported:

- Project `lawcast-frontend`, production branch `main`.
- Canonical deployment `f9b1d5fe-30f1-498d-ba59-acda5fb0c7dc`, successful, exact release SHA.
- Custom domain `law.viento.me` and the Pages subdomain unchanged.
- Production runtime binding key set unchanged; no credentials or binding values were changed.
- Native Pages Git source remains disconnected, preserving the main-only GitHub Actions deployment path.
- Before deployment, the canonical revision and production footer were frontend 1.27.1. After deployment, the real production footer reported `v1.28.0 / API v1.20.0`.

Postmerge frontend CI: [42158276328](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42158276328). It finished successfully after rerunning only the notifications job. Its first attempt hit the 25-minute budget during Ubuntu mirror OS-package downloads before any notification assertion ran; the second notifications attempt passed all 46 cases. The other successful jobs were retained. The postmerge run therefore confirms all 483 browser cases at the exact released SHA without skipping tests or weakening failure handling.

## Root pointer and local synchronization

The frontend `dev` branch was fast-forwarded to `origin/main`, followed by a real `npm install`. No lockfile diff remained. `dev`, `origin/dev`, `origin/main` and `frontend-v1.28.0` all resolve to the release SHA. Backend `dev` and semantic-search `main` were also pulled with fast-forward-only synchronization; their existing release commits and source files stayed unchanged. Backend `npm install` left its lockfile unchanged.

A separate managed worktree based on root `origin/main` isolated the pointer-only PR from the original workspace's existing checkpoint and uncommitted notes. PGP-signed commit `13afd1f` changed only the frontend gitlink. [Root PR 24](https://github.com/vientofactory/LawCast/pull/24) passed its complete backend/frontend/sidecar matrix and was squash-merged at `494d051df19734cee8138af17cc466d97971c859`.

[Root main CI/deploy run 42158806941](https://github.com/vientofactory/LawCast/actions/runs/42158806941) succeeded. Both service deployment jobs executed their change guards and reported no actual backend or semantic-search changes, so they correctly skipped rebuild/restart. The semantic index capability comparison was not invoked because there was no actual semantic-search deployment; no break-glass option was used.

The original workspace's `db7a180` checkpoint and unstaged notes were preserved. PGP-signed local pointer-sync commit `8d6c3c2` updates only its frontend gitlink, without publishing its unrelated checkpoint. Final submodule status in the original workspace has no `+` or `-` prefixes:

- Backend: `dev`, `366822050ed63f4b25a7c878c522a302b9cbb74a`.
- Frontend: `dev`, `f35595f6234809b4c487c1f988bd9dbc1d32e64f`.
- Semantic search: `main`, `8438508b61d42b7b5586633ac1af43ac4d71cff8`.

The temporary pointer-PR worktree was submitted for archival after merge, but the app's primary-checkout protection rejected removal. It was left intact rather than forcing removal; the original workspace remains fully preserved and was used explicitly for service checks.

## Real production checks

Checks used the actual deployed site in the in-app browser, with real read-only data rather than mock mode. No thread/comment/webhook was created.

- Homepage rendered the current release footer.
- Searching the literal `인공지능` from the home form navigated to the results page and rendered 47 results.
- The filter modal opened; changing page size from 20 to 10 and cancelling restored the DOM value to 20 and preserved the original search URL.
- Real notice `/notices/2220608` rendered content, metadata, discussions and five revision records.
- The latest comparison selected revisions 4 and 5, displayed the processing-status change and preserved the mobile reading workspace.
- A blank new-thread submission triggered client validation. After its toast expired, the persistent field description remained with `aria-invalid=true` and `aria-describedby=thread-validation-error`. Escape closed the modal without a write.
- A 390px layout opened/closed the mobile menu, switched dark to light, and had no document horizontal overflow. The viewport override was reset afterward.
- The actual stored screenshot loaded at 1280x947. Original-size mode showed 100%; fit mode showed 24%; Escape closed the viewer.
- After root CI/deploy completion, `/status` displayed `전체 상태 정상`, AI connection `healthy`, and the new frontend version. The browser error-log query returned an empty list.
- The final home revisit rendered the expected release and had no document horizontal overflow.

## Evidence and rollback verification

Task evidence lives in `/private/tmp/lawcast-v1.28.0-release/`, including Cloudflare before/after metadata, action logs/results, screenshots and accessibility snapshots, release/merge metadata and `VERIFICATION.txt`.

The four primary artifacts are `MODIFIED_FILE.json`, `DIFF_FILE.patch`, `VERIFICATION.txt` and executable `ROLLBACK.sh`. Their exact commands and literal outputs are in the verification file. Baseline/modified/rollback checks operate on independent disposable Git index fixtures: rollback restores only the supplied fixture/checkout's frontend index pointer, not production. The baseline pointer is reproduced after restoration, while active local/remote release pointers and the production deployment retain 1.28.0.

No production rollback was performed. The prior canonical Pages deployment metadata was preserved for a future explicitly requested recovery.

## Flat UI release frontend-v1.28.3 (2026-11-07)

Frontend [PR 187](https://github.com/vientofactory/LawCast-Frontend/pull/187) shipped only the remaining flat-surface and pagination follow-ups, retaining the published framework/dependencies. Signed feature commit `2db8dde` and verified squash commit/tag/dev/main `48294376ff233e3e0e2839b53d1649b4bb226263` have identical source trees. Package and lockfile version metadata advance to 1.28.3; a real CI-matched npm 11 installation leaves dependency versions unchanged.

- Local lint/check/Cloudflare build/guidelines passed; the full open-layout suite passed 148 cases.
- [PR CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42272693633) and [main CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42275932092) each pass all 500 browser checks across the full five-job workflow.
- [Pages deployment](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42275932037) succeeded in 2m13s. Cloudflare canonical deployment `0f17b7bb-3c3b-4e0a-80e7-efc4f37e1c0a` independently reports production/success and exact release SHA. Domains/runtime binding keys remain unchanged; native Git deployment stays disconnected.
- Real production checks cover eight route/theme states at 1440px/light and 390px/dark, including keyword-empty results, recent changes, closed discussions, version footer, pagination 2-to-3 keyboard navigation and no horizontal overflow. Screenshots were visually inspected. No thread/comment/webhook was written.
- [Root PR 28](https://github.com/vientofactory/LawCast/pull/28) changed only the frontend gitlink and merged at `66941348f41ad88ec0cad12184d34ae31adfa196`. Its PR CI passed. [Root main CI](https://github.com/vientofactory/LawCast/actions/runs/42276624368) passed on attempt 2 after rerunning only a pre-existing 1ms wall-clock-sensitive scheduler assertion/dependents; no test or guard was changed. Both backend matrices pass 88 suites/1,282 tests. Actual backend/semantic deploy guards detected no source changes and exited without rebuilding; no new capability comparison is claimed.
- The original workspace's framework/dependency migration remains local: 133 paths were preserved, with 131 identical non-version hashes and only release-version metadata changing in the two package files. Frontend/backend finish on `dev`, semantic-search on `main`, with all gitlinks matching recorded commits. Signed local root checkpoint `9618589` aligns published refs without pushing unrelated notes/checkpoints. The preservation stash remains available.

Evidence and exact commands: `/private/tmp/lawcast-flat-ui-release/VERIFICATION.txt`. Primary artifacts are `MODIFIED_FILE.json`, `DIFF_FILE.patch`, `VERIFICATION.txt` and executable `ROLLBACK.sh`. The disposable state rollback restores 1.28.2 exactly; actual production retains 1.28.3. The earlier UI task artifacts also retain actual source/browser rollback checks.
