# Progressive History Release Verification

## Released commits and order

The owner requested committing the existing implementation without further feature fixes, deploying backend before frontend, checking CI and actual production, and leaving clean working trees. Only mandatory version metadata, lockfile version metadata and release documentation were added during release preparation.

- Backend [PR 225](https://github.com/vientofactory/LawCast-Backend/pull/225), [backend-v1.20.0](https://github.com/vientofactory/LawCast-Backend/releases/tag/backend-v1.20.0), release SHA `366822050ed63f4b25a7c878c522a302b9cbb74a`. Implementation commit `c0532dd` was explicitly GPG-signed, locally verified and GitHub-verified.
- Signed root pointer `79b485a02e348b1405f0fcec53a4ac8159def91f` triggered [backend CI and deployment](https://github.com/vientofactory/LawCast/actions/runs/41230652086). Both Node backend and frontend matrix jobs, sidecar, CI gate and both deployment jobs succeeded. The unchanged semantic service exited through its deployment guard.
- The backend deployment log records `APP_VERSION=1.20.0`, a healthy service at `2026-10-31T18:48:36Z`, runtime Node `v24.22.1`, and the exact root/backend SHAs. Before merging the frontend, the public API independently returned version 1.20.0 and healthy Redis/Ollama. [Production API evidence](release-verification/backend-api.json) traverses a real notice's heights 4, 3, 2, 1 using `limit=1` with exclusive cursors, a terminal null cursor, no duplicates and invalid-cursor 400 responses. Python's default HTTP client was rejected at the edge; the same checks used the existing working curl path.
- Frontend [PR 182](https://github.com/vientofactory/LawCast-Frontend/pull/182), [frontend-v1.27.0](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.27.0), release SHA `184eb73f5d9d489ff3d94dca463da8893278fb10`. Implementation commit `470b6c8` was explicitly GPG-signed, locally verified and GitHub-verified. The frontend merged at `2026-10-31T18:50:04Z`, after the backend production API verification at `18:49:45Z`.
- The complete trees of each implementation and its squash release are identical (`git diff --exit-code`). Both service `dev` branches fast-forward to their release tags and `origin/main`; `npm install` after synchronization leaves lockfiles unchanged. The unchanged semantic service stays on `main` matching `origin/main`.

## Checks and retained intermittent failures

Local backend lint, TypeScript check and build passed, with **88 suites / 1,282 Jest tests**. Frontend lint, Svelte check (zero errors/warnings), Cloudflare build and **16 production Node SSR tests** passed. Sidecar ruff check/format, **345 tests** and local artifact capability integrity passed. The project guideline checker reports zero violations.

The latest mock/list run passed **93 tests with 1 skipped**. The release-time 29-case history/navigation run passed 28 but failed the final comparison-position assertion once (201 px versus less than 100 px). The exact unchanged test then passed all three isolated repeats. No source or test fix was made during release preparation.

[Frontend PR CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/41230643175) succeeded: history/navigation reports 28 passed and 1 flaky, with the skeleton visibility case succeeding on the configured retry; production Web Vitals reports 62 passed; production SSR consumers reports 16 passed. This is an observed intermittent test result, not a claim that the timing race was resolved. [Post-merge regression CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/41231318391) runs the identical released source.

## Actual frontend deployment

[Production Pages CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/41231318453) succeeded. Cloudflare's independent [deployment metadata](release-verification/pages.json) identifies production deployment `e6a0b64e-50ab-4fb4-8baa-9812035dc654`, status success at `2026-10-31T18:51:28Z`, branch `main` and the exact frontend release SHA. All seven existing runtime environment bindings remain `secret_text`; no binding values were exposed or changed.

The [new frontend API proxy](release-verification/frontend-proxy-api.json) independently passes the same real cursor traversal and invalid-input checks after the frontend deployment. The production data sample has four records and uses `limit=1` to verify paging. Complete loading beyond 100 and visible skeletons are established by the isolated 125-event mock/SSR regressions, not by manufacturing production history.

Read-only production browser checks use fresh desktop Chrome and Pixel 7 contexts without response interception. The desktop scenario passes version 1.27.0, changes-list comparison entry, reversing/show-all/clearing with retained nonzero scroll, historical viewing/return, both disclosure controls, matching computed shell styles, no horizontal overflow, no page errors and timeline/comparison deep-link positioning.

The initial full mobile scenario passes those actions and timeline positioning, but its final direct comparison-position assertion fails: the result starts 294 px below the expected 160 px margin. This observation is retained and no source fix was made. A separate fresh mobile context then loads the same timeline once and comparison twice: offsets are 0.25, 0 and 0 px, with no runtime errors ([measured coordinates](release-verification/mobile-position.json)). This establishes intermittent positioning, not a resolved defect.

The identical full mobile production scenario subsequently passed unchanged (3.9 s). Both actual device scenarios therefore have passing runs, while the initial mobile positioning failure remains an explicit limitation. No attempt was made to fix it during this release.

Post-merge frontend CI finished successfully: 28 history/navigation passed plus 1 flaky comparison-position case that passed its configured retry, 62 production tests passed and 16 SSR consumers passed. The main flaky case differs from the PR's skeleton-visibility case; neither was removed or relaxed. Root verification documentation already pending from the earlier 1.19.6 audit is committed as-is alongside the current release notes so the workspace can finish clean.
