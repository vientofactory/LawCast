# Frontend Design Guardrail MCP

## Ownership and source precedence

`frontend-mcp/` is an independent Node ESM stdio MCP server, registered as a root submodule with origin `https://github.com/vientofactory/lawcast-frontend-mcp.git`. It is tooling, not a production service: existing service-only CI/deploy checkout lists remain unchanged.

The frontend 3.2.0 snapshot includes shared CSS, 53 components, layout/theme and lifecycle helpers. Per-source SHA-256 and the combined fingerprint, not only Git HEAD, identify the actual checkout. The old frontend exploration document contains legacy Svelte information; current source, `repo/frontend-notes.md` and `65-ui-layout-redesign/` supersede it.

## Guardrails and limits

Tools expose tokens/classes/patterns/rules, exact component reference source, shared CSS declarations and AST-based Svelte review. Resources and a reusable prompt guide pre-change inspection. The CLI uses exit 1 for violations and exit 2 for manual review/input errors. MCP alone is advisory; no frontend CI/client configuration is silently changed.

Shared classes distinguish actual CSS definitions from observed markup hooks. Existing decorations/legacy implementations are reference data, not permission to add new exceptions. Runtime styling/spreads and custom CSS require independent review. Keep light/dark, keyboard/focus, 320px, 200% text, reduced motion and state-matrix browser acceptance separate from static checks.

## Verification and rollback

`frontend-mcp/test/` exercises rules, provenance, CLI exits and real SDK stdio discovery/calls/resources/prompts. `frontend-mcp/verification/VERIFICATION.txt` records literal baseline/modified/rollback results. The guarded executable rollback restores only a separate demo copy, never the actual frontend or the retained modified fixture.

Regenerate with `npm run snapshot -- ../frontend`, review snapshot/policy diffs and run format/lint/test. No production deployment is part of this work. Existing root memory/frontend pointer changes were preserved separately.

## Published bootstrap

The GPG-signed initial commit is `3f0ac386364eb8c82a8eda007a89c17b734f7e3d`. The empty remote was bootstrapped on the feature branch, then that first default branch was renamed to `main`; no existing shared history was overwritten. GitHub Actions run `45120382170` passed Node 22/24 lint/tests/audit. The root `.gitmodules` and gitlink are staged, not committed or pushed, keeping the owner's pre-existing root documentation commit and uncommitted memory/frontend pointer changes out of publication.

Local proof passes 31 MCP tests, frontend lint/check, backend lint/type/build and 105 suites/1,419 tests, semantic ruff and 421 tests, and the root guideline checker. Initial sandbox socket failures were rerun unchanged with loopback access. No frontend/backend/semantic tracked source was modified.

## TypeScript refactor

The follow-up keeps the MCP protocol, snapshots, rule results and CLI exit codes unchanged while moving implementation, scripts and tests into strict TypeScript. `tsconfig.json` builds NodeNext ESM into ignored `dist/`; npm's prepare hook builds on installation, and pretest rebuilds before running compiled tests. The four original server/CLI/script JavaScript paths remain thin launchers so existing MCP client commands keep working. Snapshot asset paths resolve from compiled module locations, not the process working directory.

Explicit snapshot/policy/finding/result types and Svelte's AST types replace implicit JavaScript shapes. Node/TypeScript dependencies are development-only; no runtime transpiler is added. CI now includes typechecking. README retains installation, client wiring, interfaces, CLI exits and development commands, linking detailed analysis rather than repeating it.

Baseline: 31 tests pass. Modified: 32 pass, including a real stdio launch from an unrelated working directory. Shared snapshot regeneration is byte-identical. Full-tree original/modified archives, diff and a guarded independent-copy rollback are stored locally in `_workspace/frontend-mcp-typescript/`. No release, commit or remote push is included in this follow-up.

## Main PR required-check workflow

The existing MCP workflow now runs for PRs targeting main and main pushes, without path-based omissions. Node 22/24 retain npm 11.13.0 locked installation, type/format checks, build-through-pretest, the full MCP tests and high-severity production dependency auditing. Matrix fail-fast is disabled; concurrency cancels superseded runs and job timeouts bound execution.

The stable `Required checks` job always evaluates the matrix result and passes only for `success`, rejecting failure/cancelled/skipped/empty states. Repository main branch protection must select that check to enforce merge blocking; no remote rule/settings changes or push are included in this request. The README documents this distinction.

Local proof includes actionlint 1.7.7, YAML contract controls against baseline/modified/restored copies, all five gate-result cases, type/format checks and 32 passing tests. Original hash, modified workflow, diff, literal commands/results and guarded independent-copy rollback live in `_workspace/frontend-mcp-ci/`.

## Root repository integration

MCP PR #1 merged at `798f8d021aa4e16d218da845e223f9f15e8b2e9a`; the root gitlink records that main commit rather than a feature-only SHA. The existing frontend checkout `139f664caf9d46af45694462ee718071e4563804` is byte-for-byte tree-equivalent to merged main `ad945b84d789b39ad2637967ba139a3b6ba0bb44`, so the root records the latter. Frontend dev fast-forwards to that main commit; the original feature branch is retained. MCP remains on a local integration branch at its merged main commit.

At the owner's request, the root README now lists the MCP development-tool submodule, links its detailed documentation, and includes npm installation and stdio startup/client guidance without adding it to production Compose or deployment. The root commit also includes existing memory index entries, sessions 90/91 and the previously staged submodule registration. Existing root deployment-trigger documentation is already tree-equivalent on origin/main and stays intact; the original local documentation commit remains on its original docs branch. No PR merge or production deployment is requested here.

Root precommit checks pass frontend lint/check, backend lint/type/build and 105 suites/1,419 tests, semantic ruff and 421 tests, MCP type/format and 32 tests, and the repository guideline checker. The pre-existing unsigned, tree-equivalent documentation-only commit is not republished: the integration branch starts from origin/main and consolidates all pending root changes into a new signed commit, while docs/deploy-trigger-guidance retains that original commit.
