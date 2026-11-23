# Hashguard Adaptive PoW and Discussion Writes

## Upstream contract

Reviewed the official [v2.0.0 release](https://github.com/vientorepublic/hashguard-client/releases/tag/v2.0.0), [source comparison](https://github.com/vientorepublic/hashguard-client/compare/v1.5.2...v2.0.0), README and installed declarations on 2026-11-16.

- `execute()` now assesses risk before solving. Low-risk responses contain an assertion without a challenge or solve statistics; narrow `challengeRequired` before accessing those fields.
- `assessRequest(context)` returns `allow` with `verification`, or `challenge` with the challenge. Assessment failures must not trigger a legacy challenge fallback.
- `introspectToken(token, true, { expectedContext, expectedSubject })` applies binding constraints before consuming the single-use assertion. Local signatures and cached approvals do not establish single use.
- Upstream also hardens ResourceGuard cache/binding checks, JWT claim validation and JWKS refresh coalescing/cooldowns. LawCast uses authoritative introspection rather than those local/cache validation APIs.

### v2.0.1 patch (2026-11-21)

The `2.0.0` -> `2.0.1` bump is a backward-compatible patch (release notes: 42 unit tests, type-check, ESLint, formatting, and a real-WASM end-to-end solve all passed upstream). It changes only internal `ResourceGuard`/`TokenCache`/`solver` behavior:

- `ResourceGuard.getCacheStats()` reports the configured `maxEntries` instead of a hardcoded `1000`; `TokenCache.maxEntries` is now a `readonly` public field.
- `ResourceGuard.checkAll()` no longer injects the token into the options object (it is passed as the first argument to `checkAccess`), and `ResourceAccessOptions.token` is now optional and marked `@deprecated` for backward compatibility.
- `solver.ts` removes the per-attempt and JS-fallback `console.log` debug noise (WASM-active, WASM-solve-returned, JS-fallback, solution-found logs); the `solvePow` signature and the adaptive flow are unchanged.

LawCast consumes only `assessRequest` / `verifyChallenge` / `introspectToken` / `solvePow` / `HashGuardClient` / `HashGuardError` / `initHashGuardWasm`; a source search found zero uses of `checkAll`, `ResourceGuard`, `ResourceAccessOptions`, `getCacheStats`, `TokenCache` or `TokenValidator`. No LawCast source change is therefore required - the assess -> allow/challenge -> verify contract is identical - and the update is a version/lockfile bump plus a clean `npm install` (only the `hashguard-client` version/resolved/integrity lines changed in each `package-lock.json`).

Verified against `2.0.1`: frontend Svelte/TS check, license tests, and the Cloudflare production build pass; backend lint, TypeScript 6 check, native TypeScript 7 check, Nest build, and 105 Jest suites / 1405 tests pass; `python3 tools/check-agent-guidelines.py` reports zero violations.

## Implementation

Both service manifests and lockfiles pin `hashguard-client` to `2.0.1` (patched from `2.0.0` on 2026-11-21; see the v2.0.1 note above), installed with npm 11.13.0. Work remains on `codex/hashguard-v2-discussions`; no commit, release or deployment was performed.

### Frontend

`frontend/src/lib/hashguard-flow.ts` shares assessment/allow/challenge behavior across the existing Web Worker and main-thread fallback. An allow response skips both WASM warmup and nonce calculation. Only a challenge enters warmup, solve and verify. The main-thread solver remains dynamically imported; supported browsers keep computation in the worker.

`frontend/src/lib/hashguard-worker.ts` preserves upstream error status/code across worker messages, including 429/503, and recreates a worker after a fatal worker error. Both execution paths fail closed on assessment failures, unknown decisions or empty assertions.

The shared display state clears old solve metrics on assessment and completion. Existing webhook/web-push forms use this same adaptive path. New-thread and comment submission obtain a fresh proof for every attempt, include it in the typed API payload, expose live security status, disable duplicate submission and keep drafts on errors. Existing success, comment-list, quote-consent and rate-limit behavior remains in place. Modal feedback stays within the modal focus scope.

### Backend

`backend/src/modules/shared/hashguard.service.ts` explicitly consumes tokens with context/IP constraints and independently rejects missing or mismatched returned claims. It logs only validity, not the assertion/subject/context payload.

The protected contexts are:

- Webhook registration: `webhook-registration`.
- Web push and quote-push binding registration: `webpush-subscription`.
- New discussion thread: `discussion-thread`.
- New discussion comment: `discussion-comment`.

Webhook registration now uses the same forwarded-client-IP extractor as discussion/web-push registration, rather than preferentially binding to the reverse proxy socket IP.

`CreateThreadDto` and `CreateCommentDto` require a nonempty string `proof`, with a 4096-character cap and write-only OpenAPI metadata. Discussion controllers retain the existing write limiter and IP validation before token consumption, and verify before invoking persistence. Domain services accept the validated writing fields without requiring a proof in internal fixtures; they explicitly select saved fields and never store assertions.

## Verification

- Original targeted backend baseline: 5 suites, 44 tests passed.
- Modified backend: lint, TypeScript 6 and native TypeScript 7 checks, Nest build, 105 Jest suites and 1405 tests passed; vendor tests also passed.
- Frontend: lint, Svelte check (zero errors/warnings), native TypeScript check, vendor/license tests and Cloudflare production build passed.
- Isolated Chromium: 34 tests passed across existing discussion behavior and adaptive worker/fallback allow/challenge/429/503/unknown/empty cases. The challenge case runs the installed SDK solver and checks its submitted nonce. Tests also cover stale-metric clearing, mobile dark-mode feedback, draft preservation, duplicate-submit prevention and fresh assertions after failures.
- Nest HTTP contract tests use the real SDK against a loopback stand-in. They verify one-time consumption, rejected cross-context/IP use without consuming the correct assertion, DTO rejection before introspection/storage, and unavailable token-state denial. These establish local integration behavior, not production Hashguard availability.
- Independent rollback copy: all 26 changed original files restored byte-for-byte, four added files removed, runtime SDK restored to 1.5.2, original 5 suites/44 tests passed. The working checkout remains modified at SDK 2.0.1.
- `python3 tools/check-agent-guidelines.py`: zero violations.

Raw logs, original hashes, source bundles, complete patch and guarded executable rollback stay in ignored `_workspace/hashguard-v2/`. The rollback script restores source/manifests/lockfiles only; rerun npm 11.13.0 install in both services to reify dependencies when applying it to an installed checkout.

## Rollout invariants

Deploy an assessment-capable Hashguard server before these clients. Keep trusted original-client-IP forwarding consistent between browser assessment and backend introspection. The SDK appends `/v1` itself: configure its base URL before the version segment, as in the checked-in environment examples.

For a release, follow [AGENTS.md](../../AGENTS.md): backend first, then frontend, with matching app version bumps, signed commits, per-service PRs and verified deployment gates. This change adds required proof fields to public discussion creation requests; clients outside the LawCast UI must obtain a fresh correctly bound assertion too. Existing passwords and hard limits are not replaced by Hashguard.

Related context: [backend testing notes](../repo/backend-testing-notes.md), [frontend notes](../repo/frontend-notes.md), [quote notification plan](../03-quote-notification-plan/plan.md).
