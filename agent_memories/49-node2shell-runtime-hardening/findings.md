# Node2Shell Runtime Hardening

## Scope and primary evidence

Reviewed on 2026-10-24 in response to the Node2Shell report. The underlying issue is CVE-2026-111497, an out-of-bounds write in Node.js's bundled Brotli decoder. Fixed supported releases are 22.23.4, 24.22.1, and 26.12.1.

- [Node.js security advisory](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases)
- [Imperva research](https://www.imperva.com/blog/node2shell-from-brotli-data-to-remote-code-execution/)
- [Cloudflare Node.js compatibility](https://developers.cloudflare.com/workers/runtime-apis/nodejs/)
- [Cloudflare Pages build version selection](https://developers.cloudflare.com/pages/configuration/build-image/)

## Exposure traced in this checkout

**HIGH: backend exposure is confirmed when the process runs a vulnerable Node binary.** Installed dependencies are Express 5.2.1, body-parser 2.3.0, and Nest platform-express 11.2.6. The pre-release production binary was not inspected; after remediation the deployed container reports Node v24.22.1 (see production verification below).

- `backend/src/main.ts:67-68` installs JSON and URL-encoded parsers with inflation enabled by default. Their limits of 256kb and 32kb do not prevent execution of the native decoder. Guards and DTO validation run after body parsing.
- `backend/node_modules/body-parser/lib/read.js` dispatches `Content-Encoding: br` to `zlib.createBrotliDecompress()`. This is an installed dependency inspection, not a tracked source file.
- `backend/src/utils/http-fetch.utils.ts:50-55` uses Axios with default response decompression. Installed Axios 1.20.0's HTTP adapter invokes `createBrotliDecompress` for Brotli responses.
- `backend/src/modules/admin-notices/admin-notices.service.ts:112-114` delegates Notion responses to native fetch. Outbound exploitation requires control of the compressed upstream response; no arbitrary public URL input was established in this review.
- Existing Dockerfiles used floating `node:24-alpine` tags. This does not prove the running image is patched: already-built images retain their embedded binary.

**Frontend requires separate treatment by execution target.** `frontend/svelte.config.js:13` defaults to adapter-cloudflare and selects adapter-node when `SVELTE_ADAPTER=node`. `frontend/src/hooks.server.ts:59-64` and `frontend/src/routes/api/[...path]/+server.ts:95` fetch backend responses. Under Node, response decompression reaches the Node runtime; under Cloudflare, it uses the provider's Workers runtime. `nodejs_compat` is not evidence that the published Node exploit applies or that Brotli is patched. Cloudflare's actual fleet Brotli patch status remains unverified; do not describe Pages as categorically unaffected.

The default local binary was Node 26.10.0, arm64, Brotli 1.2.0, behind `~/.local/bin/node` pointing to the Hermes-managed installation. It was not replaced globally. Development processes must switch to a patched version and restart; `.node-version` alone does not change a running process.

## Changes

- Root, backend, and frontend have `.node-version` set to 24.22.1.
- Every Node Docker stage in both submodules pins `node:24.22.1-alpine`.
- Both package manifests and lockfiles declare `^22.23.4 || ^24.22.1 || ^26.12.1`; unsupported odd majors, EOL lines, and pre-fix supported versions are excluded.
- Backend adds `engine-strict=true`; frontend already had it. npm installation enforces the engine requirement. This is an installation safeguard, not a check for direct `node dist/main` invocations.
- Root CI uses patched 22.23.4 and 24.22.1 versions, with its coverage upload condition updated to match the new matrix value.
- Both READMEs document patched Node requirements. Frontend Pages setup documents `.node-version` and the need to align any explicit `NODE_VERSION` override.
- Ran actual `npm install` in both submodules. Lockfile changes contain only root-package engine metadata; dependency versions did not change.

Release work was authorized after local verification. Backend 1.19.3 was signed, merged via [PR #221](https://github.com/vientofactory/LawCast-Backend/pull/221), and tagged `backend-v1.19.3` at `ac75780`. [Root PR #21](https://github.com/vientofactory/LawCast/pull/21) deployed it before frontend [PR #165](https://github.com/vientofactory/LawCast-Frontend/pull/165) was merged. Frontend 1.22.2 is tagged `frontend-v1.22.2` at `d93c6b3`. Both `dev` branches were fast-forwarded to their release commits and pushed. GitHub reports valid signatures for both squash-merge commits; feature commits were signed with the configured maintainer key.

## Verification

Used official Node 24.22.1 darwin-arm64 extracted under `/private/tmp`, checked against the official SHASUMS256.txt. No exploit payload was downloaded or executed.

- Backend lint, TypeScript, and Nest build passed.
- Initial backend test run: 83 suites / 1,235 tests passed; the remaining suite's three cases failed because sandbox policy denied localhost `listen` with EPERM. The isolated retry passed all three tests. A complete rerun with localhost permitted then passed **84 suites / 1,238 tests**, with no failures.
- Frontend lint, Svelte check (zero errors and warnings), and Cloudflare production build passed.
- Twenty semver boundary assertions checked acceptance of the three fixed releases and rejection of seven unsupported or pre-fix versions in both manifests.
- Four safe local HTTP probes passed: real Nest ExpressAdapter with matching body parser settings decoded benign JSON and URL-encoded Brotli requests; native fetch and Axios decoded a benign Brotli response.
- Agent guideline checker reported zero violations.

The safe probes establish decoder reachability and compatibility under the patched runtime; they are not exploit reproduction. The local Docker daemon was unavailable; the production workflow subsequently built and verified the actual container.

## Release follow-through

Follow [AGENTS.md](../../AGENTS.md)'s submodule release procedure. Before merge, apply patch version bumps and run `npm install` again, then create signed commits and per-submodule PRs. Release the backend and update the root submodule pointer to trigger production deployment. Frontend main pushes trigger Pages deployment; any explicit Pages `NODE_VERSION` override must also be 24.22.1 or another allowed patched release.

The root deployment workflow now compares `docker compose exec -T backend node --version` with `backend/.node-version` after the health check and before recording deployment success. A mismatch fails the deployment. Cloudflare Pages project inspection confirmed no `NODE_VERSION` override in production or preview, so the committed `.node-version` selects the build runtime.

## Production verification

- [Root CI and deployment run 40073886488](https://github.com/vientofactory/LawCast/actions/runs/40073886488) succeeded: backend/frontend CI on Node 22.23.4 and 24.22.1, sidecar checks, and both deployment jobs. The backend container check at 2026-10-24 16:29:28 JST logged `Backend runtime: v24.22.1 (expected v24.22.1)` after the health check. It recorded backend `ac7578078b4b` at root `9a8259485c14`.
- Public `/api/health` changed from 1.19.2 to **1.19.3**, with `status=healthy`, Redis `up`, and Ollama `healthy`.
- Cloudflare Pages production deployment `8224edef-540f-4608-9ec1-8d6859b5afa3` served frontend commit `d93c6b3b46d1558eca4d6a0a32651b16c82a7396` successfully at 2026-10-24 16:32:01 JST. Its build log detected and installed **Node 24.22.1**. The serving runtime remains Cloudflare Workers; the build log is not a Node version check for the Workers fleet.
- A real browser loaded the home page showing **v1.22.2 / API v1.19.3**, then followed bill 2222066 to a rendered detail page with its source text, AI summary, discussion region, and timeline controls.
- Read-only public HTTP checks verified health, archive listing, bill detail, change listing, status HTML, and notice-list HTML. No exploit payload or production write was used.
- The local Hermes-managed default Node binary was left unchanged. This is separate from the verified production and build runtimes.
