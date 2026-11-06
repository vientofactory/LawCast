# Dependency Refresh Verification

## Scope

Backend and frontend dependency review on 2026-11-07 (Asia/Tokyo). Both started clean on `dev`; the root workspace already contained unrelated documentation and submodule-pointer changes, which were preserved. Both service worktrees use `codex/dependency-refresh-20261107`. No release or deployment was performed.

## Update Selection

All 10 open Renovate PRs per service were read, including their diffs. Registry inventories contained 29 outdated direct backend dependencies and 27 frontend dependencies. The update refreshes compatible declared versions and their transitive dependency trees. Node 24 type definitions remain aligned with the runtime. NestJS 12, TypeORM 1, TypeScript 7, web-push 4 and the coupled SvelteKit 3/Vite 8/adapter migration remain separate major migrations.

Backend Renovate PRs 167, 168, 172, 173, 175, 177, 179 and 199 are covered locally. PRs 183 and 184 (Redis/Keyv 6) remain pending: `cache-manager@7.2.9` still depends on Keyv 5, while Redis 6 requires Keyv 6 and Keyv 6 changes error handling. Cache outage and stored-data compatibility need dedicated migration coverage, not independent bot merges.

All 10 frontend Renovate updates (109, 110, 115, 116, 118, 119, 120, 121, 122, 123) are covered locally. Wrangler advances from 4.131.0 to 4.158.0, beyond the old exact pin. Existing SheetJS tarball provenance and the cookie override remain unchanged.

The updated Tailwind Prettier plugin reorders class tokens in 19 Svelte files. A normalization assertion verifies that these files have no other byte changes; no product logic or test assertion was changed.

## Security Findings

Backend audit: 44 findings (2 critical, 8 high, 29 moderate, 5 low) to 8 low findings, all caused by the remaining build/test `deepmerge` dependency. Production-only backend audit is clean.

Frontend audit: 32 findings (9 high, 16 moderate, 7 low) to 9 findings (2 moderate, 7 low). Production-only audit retains the Satori advisory and SvelteKit advisory chains. No high or critical finding remains.

Backend overrides update vulnerable `multer`, `js-yaml`, `glob` and `minimatch`. Frontend `glob`/`minimatch` overrides patch lint/build dependency paths. Normal resolution updates the vulnerable HTTP, image, schema, selector and source-map dependencies. Full before/after npm audit JSON is preserved in the verification artifacts.

### Satori compatibility gate

**MEDIUM:** `@cf-wasm/satori@0.4.2` pins `satori@0.32.0`, which remains affected by GHSA-wx4j-mvgx-mqwp. An experiment overriding Satori to patched 0.33.5 produced a valid 1200x630 PNG in Node but failed with HTTP 500 under actual local workerd. The new HarfBuzz loader dereferenced an unavailable location `href` from `harfbuzzjs/hb.js`; the wrapper only initializes Yoga WASM. The candidate was removed rather than shipping a broken share-image route. Upgrade the Cloudflare wrapper and HarfBuzz static-WASM integration together, then recheck the actual workerd image route. A Node-only test does not detect this regression.

### Remaining low findings

`deepmerge@4.3.1` remains the registry latest and has no patched 4.x release for GHSA-gcqx-w48m-w2h4. Do not use a forced toolchain downgrade or suppress the advisory to manufacture a clean report.

SvelteKit 2 advisories require SvelteKit 3. The official migration changes Vite configuration, aliases, navigation options, service-worker interfaces and adapter requirements. This is not an isolated lockfile patch: https://svelte.dev/docs/kit/migrating-to-sveltekit-3.

## Verification Evidence

Detailed commands, exit codes, literal output excerpts, file hashes and baseline/modified/rollback comparison are stored at `../../_workspace/dependency-refresh-20261107/VERIFICATION.txt`. Raw inventories and logs are alongside it. The executable rollback script checks original and modified hashes and restores only this task's files; it was exercised on an independent checkout copy rather than reverting the updated service worktrees.

**npm 12:** `allow-remote` defaults to `none`; use `npm install --allow-remote=root` and `npm ci --allow-remote=root` for the existing direct SheetJS tarball dependency. Do not change it to the obsolete public-registry SheetJS package. Package install-script approval remains a distinct local setting; this task did not globally enable arbitrary install scripts.

## Final Results

- Backend baseline, final update and independent rollback: 88 suites and 1,282 tests pass (exit 0).
- Frontend baseline and final update: 405 passed, 79 skipped and the same 15 failed (exit 1). The failing-test identity comparison contains zero new failures. Existing failures include disabled-analytics prompt fixtures, stale accessibility expectations and the rate-limit message expectation; the suite is not represented as all green.
- Frontend final lint, type check and Cloudflare build pass; both service dependency trees and repeated-install lockfile equality pass. Agent guideline violations: 0.
- Final local workerd: OG route returns HTTP 200, PNG 1200x630; home, notice list, offline and PWA start routes return HTTP 200. This is local runtime evidence, not a production deployment.
- Independent rollback restores all 23 original hashes and original installations, then passes backend tests and frontend type check. The working service copies remain updated.
- [Complete PR and outdated inventories](inventory.md) list every initial package and retained major update. Raw evidence and the hash-guarded executable rollback are in the workspace artifact directory named above.
