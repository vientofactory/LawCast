# Dependency Release Analysis

## Review boundary

All pending dependency, compatibility, vendored-source and verification changes were reviewed against the actual published service commits, not only the intermediate compatible-update snapshot. Public API routes/envelopes and the SQLite schema remain unchanged. Both releases use version 2.0.0 because internal framework/storage architecture changes are major.

## Backend

### dependencies

- `@keyv/redis`: `^5.1.4` -> `^6.1.0`.
- `@nestjs/cache-manager`: `^3.0.1` -> `^12.0.4`.
- `@nestjs/common`: `^11.2.5` -> `^12.4.0`.
- `@nestjs/config`: `^4.0.2` -> `^12.1.1`.
- `@nestjs/core`: `^11.0.0` -> `^12.4.0`.
- `@nestjs/platform-express`: `^11.0.0` -> `^12.4.0`.
- `@nestjs/schedule`: `^6.0.1` -> `^12.0.3`.
- `@nestjs/typeorm`: `^11.0.3` -> `^12.0.3`.
- `@notionhq/client`: `^5.27.0` -> `^5.31.0`.
- `axios`: `^1.13.2` -> `^1.21.0`.
- `better-sqlite3`: `(absent)` -> `^12.0.0`.
- `cache-manager`: `^7.2.5` -> `^7.2.9`.
- `class-validator`: `^0.15.0` -> `^0.15.1`.
- `cron`: `^4.3.4` -> `^4.4.0`.
- `cronstrue`: `^3.24.0` -> `^3.38.0`.
- `discord.js`: `^14.26.3` -> `^14.28.1`.
- `hashguard-client`: `^1.5.0` -> `^1.5.2`.
- `jszip`: `^3.10.1` -> `^3.10.2`.
- `keyv`: `^5.5.4` -> `^6.1.0`.
- `pal-crawl`: `^2.3.0` -> `^2.3.1`.
- `reflect-metadata`: `^0.2.0` -> `^0.2.2`.
- `rxjs`: `^7.8.1` -> `^7.8.2`.
- `sharp`: `^0.35.0` -> `^0.35.5`.
- `sqlite3`: `^6.0.0` -> `^6.0.1`.
- `typeorm`: `^0.3.27` -> `^1.1.2`.
- `web-push`: `^3.6.7` -> `^4.0.0`.

### devDependencies

- `@nestjs/cli`: `^11.0.0` -> `^12.0.12`.
- `@nestjs/schematics`: `^11.0.0` -> `^12.0.13`.
- `@nestjs/testing`: `^11.0.0` -> `^12.4.0`.
- `@types/express`: `^5.0.0` -> `^5.0.6`.
- `@types/node`: `^24.0.0` -> `^26.6.6`.
- `@types/supertest`: `^7.0.0` -> `^7.2.1`.
- `@typescript-eslint/eslint-plugin`: `^8.0.0` -> `^8.72.1`.
- `@typescript-eslint/parser`: `^8.0.0` -> `^8.72.1`.
- `deepmerge`: `(absent)` -> `file:./vendor/deepmerge`.
- `eslint`: `^10.0.0` -> `^10.14.0`.
- `eslint-config-prettier`: `^10.0.0` -> `^10.1.8`.
- `eslint-plugin-prettier`: `^5.0.0` -> `^5.5.7`.
- `jest`: `^30.0.0` -> `^30.5.2`.
- `prettier`: `^3.0.0` -> `^3.9.10`.
- `supertest`: `^7.0.0` -> `^7.3.1`.
- `ts-jest`: `^29.1.0` -> `^29.4.15`.
- `ts-loader`: `^9.4.3` -> `^9.6.2`.
- `ts-node`: `^10.9.1` -> `^10.9.2`.
- `typescript`: `^5.1.3` -> `^6.0.3`.
- `typescript-native`: `(absent)` -> `npm:typescript@^7.0.2`.

### overrides

- `deepmerge`: `(absent)` -> `$deepmerge`.
- `glob`: `^13.0.0` -> `^14.0.4`.
- `js-yaml`: `^5.0.0` -> `^5.5.0`.
- `minimatch`: `(absent)` -> `^11.0.5`.
- `multer`: `2.4.0` -> `2.5.0`.

### Compatibility review

- Nest packages are upgraded together; CommonJS output is retained on the declared Node runtimes. Root CI validates Node 22 and Node 24 before merge.
- TypeORM changes use object selections and `In` queries, retain entity fields and immutable archive semantics, and switch only the SQLite driver. Automatic schema synchronization/migration remain disabled.
- Keyv 6 adapts Nest identity detection and cache-manager raw reads; real Redis tests cover old envelopes/namespaces, TTL, cached wrap hits and isolated clear.
- Native SQLite build tools and local vendor files are included in both production/build Docker stages. TypeScript 7 checks alongside the TypeScript 6 compiler APIs.
- The existing scheduler assertion now freezes/restores its wall clock, preserving its assertions and application behavior.

## Frontend

### dependencies

- `@fortawesome/fontawesome-svg-core`: `^7.1.0` -> `^7.3.1`.
- `@fortawesome/free-brands-svg-icons`: `^7.1.0` -> `^7.3.1`.
- `@fortawesome/free-solid-svg-icons`: `^7.1.0` -> `^7.3.1`.
- `@sveltejs/adapter-cloudflare`: `^7.2.9` -> `(removed)`.
- `axios`: `^1.13.2` -> `^1.21.0`.
- `chart.js`: `^4.5.1` -> `^4.6.1`.
- `harfbuzz-upstream`: `(absent)` -> `npm:harfbuzzjs@0.10.0`.
- `harfbuzzjs`: `(absent)` -> `file:./vendor/harfbuzz-edge`.
- `hashguard-client`: `^1.5.0` -> `^1.5.2`.
- `marked`: `^18.1.0` -> `^18.1.3`.

### devDependencies

- `@eslint/compat`: `^2.0.0` -> `^2.1.1`.
- `@eslint/js`: `^10.0.0` -> `^10.0.1`.
- `@playwright/test`: `^1.62.1` -> `^1.65.0`.
- `@sveltejs/adapter-cloudflare`: `(absent)` -> `^8.0.2`.
- `@sveltejs/adapter-node`: `^5.4.0` -> `^6.0.1`.
- `@sveltejs/kit`: `^2.47.1` -> `^3.1.1`.
- `@sveltejs/load-config`: `(absent)` -> `^0.2.2`.
- `@sveltejs/vite-plugin-svelte`: `^6.2.1` -> `^7.3.1`.
- `@tailwindcss/vite`: `^4.1.14` -> `^4.3.5`.
- `@types/node`: `^24.0.0` -> `^26.6.6`.
- `chrome-launcher`: `1.2.2` -> `^1.2.3`.
- `deepmerge`: `(absent)` -> `file:./vendor/deepmerge`.
- `eslint`: `^10.0.0` -> `^10.14.0`.
- `eslint-plugin-svelte`: `^3.12.4` -> `^3.24.0`.
- `globals`: `^17.0.0` -> `^17.14.0`.
- `lighthouse`: `13.6.0` -> `^13.6.0`.
- `prettier`: `^3.6.2` -> `^3.9.10`.
- `prettier-plugin-svelte`: `^4.0.0` -> `^4.1.1`.
- `prettier-plugin-tailwindcss`: `^0.8.0` -> `^0.8.1`.
- `svelte`: `^5.41.0` -> `^5.57.3`.
- `svelte-check`: `^4.3.3` -> `^4.7.8`.
- `tailwindcss`: `^4.1.14` -> `^4.3.5`.
- `typescript`: `^6.0.0` -> `^6.0.3`.
- `typescript-eslint`: `^8.46.1` -> `^8.72.1`.
- `typescript-native`: `(absent)` -> `npm:typescript@^7.0.2`.
- `vite`: `^7.1.10` -> `^8.3.6`.
- `wrangler`: `4.131.0` -> `^4.158.0`.

### overrides

- `cookie`: `0.7.2` -> `(removed)`.
- `deepmerge`: `(absent)` -> `$deepmerge`.
- `fflate@<0.7.5`: `(absent)` -> `^0.7.5`.
- `glob`: `(absent)` -> `^14.0.4`.
- `harfbuzzjs`: `(absent)` -> `$harfbuzzjs`.
- `minimatch`: `(absent)` -> `^11.0.5`.
- `satori`: `(absent)` -> `^0.33.5`.

### Compatibility review

- SvelteKit configuration, declared environment variables, readonly URLs and navigation option names migrate together; form/error/query behavior remains covered.
- The local HarfBuzz loader uses statically imported WASM/callback modules on workerd and the upstream loader on Node. Real Cloudflare PNG rendering validates this boundary.
- The default suite owns analytics-disabled fixtures; analytics/floating tests run explicitly. PWA/classic-worker behavior and comparison reading-position preservation have real workerd coverage.
- CI retains all previous browser suites and adds framework/PNG, analytics and Cloudflare PWA checks, with a budget increase instead of removing cases.

## Shared audit and licensing

- Both services vendor the minimal MIT deepmerge source patch with its license and security regressions. The patch creates own data properties rather than invoking inherited prototype setters.
- Fresh npm 11 full audit reports zero vulnerabilities for both updated lockfiles. Clean-install/production-only checks and CI validate local package links rather than relying only on an existing node_modules tree.
- The API version contract remains `{success:true,data:{version,buildEnv}}`; the rollout verifies version transitions and read-only real search/detail/navigation behavior.

## Rollout and recovery

- Release backend first; use a candidate pointer PR to run the root Node matrix before the backend release merge. Replace that pointer with the exact tag/main/dev SHA before root merge/deployment.
- Merge the frontend release only after backend deployment and real API verification are green. Pages deploys automatically from frontend main.
- Publish all agent memories and final pointers; synchronize service branches with fast-forward-only operations, then verify every registered worktree with porcelain status.
- Baseline snapshots/hashes and executable independent-fixture rollback are retained under `/private/tmp/lawcast-major-release-20261107/`. No production rollback is performed during successful validation.

## CI compatibility follow-up

The first candidate CI exposed Jest's synchronous ESM VM boundary on Node 22. Production dependencies support Node 22, so support and assertions are retained: `jest.config.cjs` uses native ESM on Node 24.9+ and a test-only Babel CommonJS/import.meta bridge on older supported runtimes. Added development packages are `@babel/core` (`^7.29.13`), `babel-jest` (`^30.5.2`) and `@babel/plugin-transform-modules-commonjs` (`^7.29.7`). Application output/production dependencies are unaffected. Actual isolated Node 22 and normal Node 24 runs each pass 89 suites/1,284 tests. See the [official Jest ESM boundary](https://jestjs.io/docs/next/ecmascript-modules).

A full frontend run also exposed reuse of an already-running historical dev server. The default config now starts its own strict-port server with reuse disabled, and the pagination regression uses its current accessible label. The fresh isolated run passes all 413 default cases (74 existing feature-gated skips) plus the explicit 14 analytics cases. Actual workerd framework/PNG and PWA suites pass 17 and 36 cases respectively. No assertion was removed or relaxed to obtain these results.
