# Major Dependency Migration

## Scope and rollback boundary

This continues session 66 on both `codex/dependency-refresh-20261107` service branches. The baseline is the compatible-update state, not the original `dev` checkout. A full tracked-file snapshot and SHA-256 inventory were saved before migration at `_workspace/major-refresh-20261107/baseline/`. Unrelated root documentation and semantic-search pointer changes remain untouched. No release, production deployment or shared-branch update is part of this work.

## Backend compatibility work

- NestJS packages advance together to v12, TypeORM to 1.1.2, Redis/Keyv to 6.1.0, web-push to 4, and Node declarations to 26.
- TypeORM 1 removed its `sqlite3` driver. Application, migration predicates and real database fixtures now use supported `better-sqlite3@12.11.1`; database paths and schema remain unchanged. The separate observation script still uses `sqlite3`. SQLite immutability, diffchain, pagination, persisted locks and summary-state tests run against the replacement driver. The existing query-performance e2e also passes.
- Removed `baseUrl`, declared the build `rootDir`, kept legacy class-field initialization explicitly, migrated array-select/findByIds APIs and adjusted typed exception narrowing. These are compatibility changes, not an API contract redesign.
- NestJS 12 is ESM. CommonJS application output is retained on the existing supported Node 24 runtime; Jest enables VM modules to execute ESM dependencies.
- TypeScript 7 supplies the native checker through the explicit `typescript-native` alias and `check:native` script. TypeScript 6 remains the JavaScript compiler API for ts-jest, Nest CLI and ESLint, whose supported peer range excludes 7. The build/check paths run the native checker rather than forcing unsupported compiler APIs into those tools.

### Keyv 6 is not a drop-in store for the current Nest cache provider

**HIGH:** Nest's identity detection checks legacy `opts`/`hooks` fields; absent those, it wraps a Keyv 6 instance as another storage adapter and can double-serialize values. cache-manager 7 also requests `get(key, {raw:true})`, which Keyv 6 replaced with `getRaw`. `cache-keyv.util.ts` bridges identity detection and raw reads without changing Keyv 6 globally. Error listeners preserve cache-miss behavior during adapter errors. Real Nest-module regressions cover wrap cache hits, TTL, batches, deletion and adapter failure. `scripts/verify-redis-migration.cjs` starts an independent Redis server and checks legacy Keyv 5 envelopes/key names, new round trips, TTL expiry, wrap hits and namespace-isolated clear; it does not connect to production Redis.

## Frontend framework migration

SvelteKit 3, Vite 8, vite-plugin-svelte 7 and Cloudflare/Node adapters 8/6 are upgraded together. Configuration moves to the Vite plugin, `$lib` becomes explicit `#lib` package imports with extensions, environment variables are declared in `src/env.ts`, URL snapshots are copied from readonly framework URLs, and navigation options use `reset`/`replace`/`refreshAll`. Optional variable defaults preserve prior behavior. GTM remains explicitly public and static. The Node adapter origin comes from `paths.origin` for existing fixture/build commands. The custom static service worker stays classic and is not replaced by SvelteKit's generated worker.

The official migrator required manual repair of an environment-variable name collision and stopped before the import pass; remaining import and navigation changes were reviewed and completed rather than accepting the partial migration. No generated migration task document is left unfinished.

## Remaining advisories patched

### deepmerge

The registry's latest deepmerge 4.3.1 is still vulnerable. Both services vendor a minimal MIT-licensed source patch under `vendor/deepmerge`, with explicit local-package overrides. `mergeObject` defines own enumerable data properties for both operands instead of invoking the inherited `__proto__` setter. This is a local maintained fork, not an upstream release or advisory suppression. Separate tests exercise both attack operands, nested data, ordinary array merges, symbols, cloning and custom merge functions. The patch is also consumed by Jest/Vite themselves. CI check/test commands execute these regressions.

### Satori and HarfBuzz on workerd

Satori advances to patched 0.33.5. Its HarfBuzz dependency eagerly initializes a loader that expects browser/Node file loading and runtime compilation of callback shims; workerd permits neither. `vendor/harfbuzz-edge` keeps the upstream HarfBuzz 0.10 API/WASM and uses a workerd-specific loader with static WASM imports for the main module and every callback signature. Node keeps the upstream loader. The six tiny callback bridge binaries contain only typed function imports/exports; `generate-bridges.mjs` derives all signatures from upstream hbjs.js, verifies their bytes and instantiates them. Actual Cloudflare OG PNG generation verifies the integration, not merely a Node-side render.

The original MIT licenses accompany both vendored sources. Docker build stages copy vendor inputs before installation, include native driver build tools, and copy vendor files into the runner so local-package symlinks survive multi-stage packaging.

## Existing frontend failures and new regressions

- Analytics/floating-prompt tests now own a separate GTM-enabled fixture. The regular server remains analytics-disabled; its test discovery excludes those files, and `npm run test:e2e` explicitly runs both configurations. No failing test is skipped to obtain a green result.
- Accessibility tests wait for comparison rendering and target current disclosure content and uniquely named diff regions. Push initialization failures are verified through the current accessible notification viewport and retain contrast coverage.
- The 429 test selects the persistent described validation error, verifies its Korean message and disabled submit state instead of matching the duplicate toast text.
- A real status-page 390px/200-percent overflow came from min-content cron cards; cards now shrink, wrap long values and allow header items to wrap.
- Native installation failure automatically closes the consumed offer and reports through a toast. The regression now verifies toast dismissal and recovery with a fresh prompt event rather than clicking an inert outgoing offer.
- The enlarged-text composer assertion polls the unchanged no-overflow invariant after reactive layout settles, rather than sampling an intermediate frame.
- A mobile comparison return regression overwrote the captured record scroll position after URL navigation had already shifted layout. The comparison-entry path now preserves its original capture; the strict reading-position and focus contract remains tested.

## Evidence

Final commands, statuses, package inventories, before/after/rollback results, hashes and the executable hash-guarded rollback are in `_workspace/major-refresh-20261107/VERIFICATION.txt`. CI compatibility is checked with a separate clean npm 11.13.0 installation, matching the Pages deployment workflow, in addition to the working npm 12 installation. Local workerd and browser checks are not claimed as a production deployment.

## References

- https://docs.nestjs.com/migration-guide
- https://typeorm.io/blog/typeorm-1-0/
- https://keyv.org/docs/migration/v5-to-v6/
- https://svelte.dev/docs/kit/migrating-to-sveltekit-3
- https://developers.cloudflare.com/pages/functions/local-development/

## Final verification results

- Backend: 89 Jest suites / 1,284 tests pass, including both new cache compatibility regressions. The separate vendored security suite passes all three cases. Lint, TypeScript 6 API typecheck, TypeScript 7 native check, build, real Redis migration probe and SQLite query-performance e2e pass.
- Frontend default suite: 413 passed, 74 feature-gated cases skipped, zero failures. The explicitly enabled analytics/floating suite adds 14 passing cases; all 15 original failures are fixed. Two new framework/OG smoke cases are included in the default count.
- Actual local Cloudflare framework suite: 17 passed, no skips. It covers patched OG PNG rendering, platform document normalization, navigation and reading-position/focus preservation. The production PWA suite passes 36 cases on Cloudflare and the same 36 on Node.
- Both full and production-only npm audit reports contain zero findings. This includes a real local deepmerge source fix, not an assertion that registry 4.3.1 was patched.
- Clean npm 11 CI installs pass for both services. The final backend CI tree is valid; the working frontend tree contains only SvelteKit's expected generated `$app` module as extraneous metadata, with no invalid or missing dependencies. An old candidate lockfile had retained a dangling nested local-package link; a clean backend lockfile/install removed it and full tests were rerun.
- The final archive/hash inventory contains 183 changed paths relative to the session-66 boundary, including a deleted legacy Svelte config. Generated TypeScript incremental metadata is ignored rather than packaged as source. Original and final hashes, archive contents, executable rollback and independent restored copy all verify.
- Rollback restores the compatible-update baseline in another copy only. Its 88 backend suites / 1,282 tests and original frontend typecheck pass. Both actual worktrees remain migrated on the existing feature branches.

The strict mobile scroll failure was traced to `scrollTo(2383)` followed by native anchoring changing the position to 2367. The manually managed history disclosure now disables native overflow anchoring, and the original capture is preserved across navigation. The strict browser assertions still require the same focus target and less than three pixels of displacement; the final workerd suite also passes them.

Remaining `npm outdated` entries describe supported integration pins, not missing security patches: TypeScript 6 API alongside the installed TypeScript 7 native compiler; TypeORM's supported better-sqlite3 12 line; and Satori's upstream HarfBuzz 0.10 API alongside the local workerd loader. There is no claim that these integration APIs can be upgraded independently without further changes.

## Release review and sequencing (2026-11-07)

The owner authorized releasing all pending package updates and publishing all root agent memories. These are major architecture migrations, so backend and frontend are each versioned 2.0.0. External JSON envelopes/routes remain unchanged; deployment is backend first, root pointer/deploy verification, then frontend Pages, then the final root pointer and evidence update.

Reviewed boundaries include unchanged SQLite paths/schema (automatic synchronization/migrations remain disabled), immutable archive/FTS/query regressions, Redis legacy namespace/envelope/TTL compatibility, Nest/cache-manager raw reads and store identity, CommonJS on the supported Node runtimes, dual TypeScript native/API toolchains, vendored licenses/prototype handling, static HarfBuzz WASM loading on workerd, explicit public/private environment declarations, SPA navigation semantics and retained classic PWA worker behavior. Real Redis, SQLite, Cloudflare PNG/navigation and PWA tests supplement unit/type checks. The public version endpoint retains `{success:true,data:{version,buildEnv}}`.

The previously observed immediate-start scheduler test now freezes only its wall clock and restores it in `finally`, retaining every assertion without depending on crossing a millisecond boundary. Production scheduler behavior is unchanged. CI gains actual Cloudflare framework/PNG, analytics/floating and PWA suites; the web-vitals job budget increases to accommodate these additional checks instead of dropping existing tests.

Evidence and rollback snapshots: `/private/tmp/lawcast-major-release-20261107/`. This section is the release review; final deployment SHAs and CI results are recorded below after the rollout completes.
