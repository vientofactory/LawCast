# AGENTS.md — LawCast Project Guidelines for Coding Agents

> **This file is the single source of truth for all coding agents** (GitHub Copilot, Claude Code, Codebuff, Cursor, etc.).
> Every agent MUST read this file before making any code change in this repository.

---

## 1. Project Overview

LawCast is a self-hosted platform that collects Korean National Assembly legislative notices (입법예고) and provides Discord webhook notifications and a web UI.

### Tech Stack

| Layer          | Technology                                                   |
| -------------- | ------------------------------------------------------------ |
| Backend        | NestJS 11.x, TypeORM 0.3.x, SQLite 3, Redis (Keyv), Jest     |
| Frontend       | SvelteKit 2.x, Svelte 5.x, Tailwind CSS v4, FontAwesome v7   |
| Infrastructure | Docker Compose, Cloudflare (frontend), Ollama (AI summaries) |

### Repository Structure

- **Root**: Orchestration layer (docker-compose, deploy scripts)
- **`backend/`**: NestJS API server (submodule)
- **`frontend/`**: SvelteKit web app (submodule)
- **`agent_memories/`**: Agent exploration notes, bug findings, implementation plans
  - `01-project-exploration-and-discussion-plan/`: Architecture exploration + discussion system plan
  - `02-security-bugs-and-pagination/`: Security audits, bug investigations, pagination plans
  - `03-quote-notification-plan/`: Quote notification system implementation plan
  - `repo/`: Cross-cutting testing notes shared across all agents

---

## 2. Mandatory: Read Agent Memories First

**Before making any non-trivial code change**, agents MUST read the relevant notes in `agent_memories/`:

1. **Always read**: `agent_memories/README.md` (index of all notes)
2. **For backend work**: `agent_memories/repo/backend-testing-notes.md`
3. **For frontend work**: `agent_memories/repo/frontend-notes.md`
4. **For architecture context**: `agent_memories/01-project-exploration-and-discussion-plan/lawcast-backend-exploration.md` and `lawcast-frontend-exploration.md`
5. **For security/pagination context**: `agent_memories/02-security-bugs-and-pagination/` files
6. **For discussion/notification context**: `agent_memories/03-quote-notification-plan/plan.md`

These notes contain **critical findings** from prior agent sessions including production bugs, security vulnerabilities, and architectural decisions. Ignoring them will result in regressions.

---

## 3. Agent Memory Writing Structure

### When to Create a New Memory

Create a new agent memory file when **any** of the following is true:

| Situation                                                 | Where                                                    | Example                                |
| --------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------- |
| Found a production bug or root cause                      | `XX-security-bugs-and-pagination/` or new session folder | `bug-investigation-findings.md`        |
| Completed a security or performance audit                 | `XX-security-bugs-and-pagination/` or new session folder | `security-audit-unbounded-requests.md` |
| Designed an implementation plan for a new feature         | New session folder                                       | `plan.md`                              |
| Explored project architecture and gathered context        | New session folder                                       | `lawcast-backend-exploration.md`       |
| Discovered a cross-cutting pitfall all agents should know | `repo/`                                                  | `backend-testing-notes.md`             |

**Do NOT create a memory when:**

- A code comment or TODO in the source file is sufficient
- The finding is a trivial typo or formatting fix
- The information is already covered by an existing memory file (update it instead)

### Folder Naming Rules

Session folders follow this pattern:

```
{NN}-{descriptive-english-name}/
```

- **`NN`**: Two-digit zero-padded sequence number (e.g., `01`, `02`, `03`)
- **`descriptive-english-name`**: Lowercase kebab-case describing the session topic
- Max ~5 words; be specific but concise

**Examples:**
| Good | Bad |
|---------|--------|
| `01-project-exploration-and-discussion-plan/` | `notes/` |
| `02-security-bugs-and-pagination/` | `temp/` |
| `03-quote-notification-plan/` | `copilot-session-2026-09-14/` |
| `04-api-rate-limiting/` | `backend/` (conflicts with real backend dir) |

**`repo/` folder**: Reserved for cross-cutting notes that apply to ALL agents regardless of session. Never create numbered subfolders inside `repo/`.

### File Naming

- Format: `kebab-case-english.md` (e.g., `pagination-implementation-plan.md`)
- One topic per file; split if a file exceeds ~500 lines
- Place session-specific notes in the appropriate session folder under `agent_memories/`
- Place cross-cutting notes in `agent_memories/repo/`

### Document Structure

````markdown
# Title (H1 — single topic)

## Section (H2 — major divisions)

### Subsection (H3 — detailed points)

**Bold emphasis** for critical/urgent findings.

- Bullet points for lists
- `backtick` for file paths, function names, variables

```typescript
// Code blocks for examples
```
````

| Table | For structured data |
| ----- | ------------------- |

````

### Key Rules
- **H1 title**: One per file, describing the single topic
- **H2/H3 sections**: Logical grouping of findings
- **File paths**: Use relative paths from repo root (e.g., `backend/src/modules/...`)
- **Language**: Technical docs in English; user-facing descriptions may use Korean
- **Importance markers**: `**CRITICAL**`, `**URGENT**`, `**HIGH**`, `**MEDIUM**`, `**LOW**`
- **Cross-references**: Link to related files and sections explicitly
- **Evidence trails**: Include line numbers and code snippets for bug findings

---

## 4. Backend Coding Conventions (`backend/`)

### File & Folder Naming
- **Modules**: `backend/src/modules/{feature-name}/` (e.g., `discussions/`, `notification/`)
- **Entities**: `{entity-name}.entity.ts` (e.g., `discussion-thread.entity.ts`)
- **Services**: `{feature-name}.service.ts` (e.g., `discussions.service.ts`)
- **Controllers**: `{feature-name}.controller.ts` or `api.controller.ts`
- **DTOs**: `dto/{action-name}.dto.ts` (e.g., `create-thread.dto.ts`)
- **Migrations**: `YYYYMMDDHHMM-description.migration.ts` (e.g., `202609080001-add-indexes.migration.ts`)
- **Utilities**: `{utility-name}.util.ts` (e.g., `ip-masking.util.ts`)
- **Tests**: `{filename}.spec.ts` (co-located or in `test/`)

### Code Style
- **Module system**: CommonJS (`require`/`module.exports`)
- **Prettier**: `singleQuote: true`, `trailingComma: "all"`, 2-space indent
- **TypeScript**: `strictNullChecks: false`, `noImplicitAny: false`, ES2021 target
- **Decorators**: NestJS standard (`@Injectable()`, `@InjectRepository()`, etc.)
- **DI pattern**: Constructor injection with `@InjectRepository()` for TypeORM
- **Error handling**: NestJS exceptions (`NotFoundException`, `BadRequestException`, `UnauthorizedException`)
- **Transactions**: `DataSource.transaction(async (manager) => { ... })`

### Comment Format (English Only)
```typescript
/**
 * Brief description of the method's purpose.
 * Detailed explanation of behavior when non-obvious.
 */
async myMethod(): Promise<Result> {
  // Inline comments explain WHY, not WHAT
  // Use TODO: prefix for known issues
}
````

### Naming Conventions

- **Classes**: PascalCase (`DiscussionsService`, `IpMaskingUtil`)
- **Methods**: camelCase (`getThreadDetail`, `createThread`, `addComment`)
- **Variables**: camelCase (`savedComment`, `nextSequence`)
- **Constants**: UPPER_SNAKE_CASE (`NOTICE_LIFECYCLE_STATUS`, `CHANGE_EVENT_TYPE`)
- **Interface names**: No `I` prefix for internal types (e.g., `SanitizedComment` not `ISanitizedComment`)
- **Entity fields**: camelCase in TS, snake_case in DB (TypeORM handles mapping)
- **Unused params**: Prefix with `_` (eslint enforced)

### Testing

- Framework: Jest (run with `cd backend && npm test`)
- Mock pattern: `jest.fn()` with explicit method names matching the real service
- Run specific tests: `npm test -- --testPathPattern=discussions`
- Run in band: `npm test -- --runInBand`
- **Critical**: When adding methods to services (e.g., `CacheService`), update ALL test mocks immediately

---

## 5. Frontend Coding Conventions (`frontend/`)

### File & Folder Naming

- **Routes**: `frontend/src/routes/{path}/+page.svelte` and `+page.server.ts`
- **Components**: `frontend/src/lib/components/{FeatureName}.svelte` (PascalCase)
- **Feature components**: `frontend/src/lib/components/{feature}/` subfolder
- **Lib utilities**: `frontend/src/lib/api/client.ts`, `frontend/src/lib/types/api.ts`
- **Styles**: `frontend/src/app.css` (Tailwind base)
- **Tests**: `frontend/e2e/{feature}.spec.ts` (Playwright)

### Code Style

- **Module system**: ES modules (`import`/`export`)
- **Prettier**: `useTabs: true`, `singleQuote: true`, `trailingComma: "none"`, `printWidth: 100`
- **Indentation**: Tabs (NOT spaces)
- **TypeScript**: Strict mode enabled
- **Svelte**: Svelte 5 with runes mode (`$state`, `$derived`, `$effect`)

### Svelte Component Patterns

```svelte
<script lang="ts">
  // Props with $state rune
  let { isOpen, onClose }: { isOpen: boolean; onClose: () => void } = $props();

  // Derived state with $derived
  let isReady = $derived(someCondition && anotherCondition);

  // Side effects with $effect
  $effect(() => {
    // react to state changes
  });
</script>

{#if isReady}
  <div class="lc-panel-card">Content</div>
{/if}
```

### Styling Conventions

- **Utility-first**: Tailwind CSS classes
- **Custom prefix**: `lc-` prefix for custom component classes (e.g., `lc-button-primary`, `lc-text-primary`)
- **CSS variables**: `--lc-*` namespace (e.g., `--lc-text-primary`, `--lc-surface-primary`)
- **Dark mode**: `html[data-theme='dark']` selector
- **Border radius**: Custom override — all `rounded-*` resolves to `0.5rem`
- **Transitions**: `transition-all duration-200`, `hover:-translate-y-0.5`
- **Responsive**: `sm:`, `lg:` breakpoints frequently used

### Comment Format (English Only)

```svelte
<script lang="ts">
  // Brief inline comments for non-obvious logic
  // TODO: this needs optimization for large datasets
</script>

<!-- Accessible markup with ARIA labels -->
<nav aria-label="Main navigation">
  ...
</nav>
```

### Testing

- **Type check**: `cd frontend && npm run check`
- **E2E**: `cd frontend && npx playwright test`
- **With mock data**: `DIFFCHAIN_UI_MOCK=1 npx playwright test`
- **data-testid**: Always add on primary regions and interactive elements

---

## 6. General Project Rules

### Language Policy

- **Code**: All code comments, variable names, and API responses in **English**
- **User-facing text**: Korean for UI strings, error messages, and documentation
- **Agent notes**: Technical docs in English; exploration notes may mix Korean
- **No emojis**: Never use emojis in code, commit messages, documentation, or PR descriptions

### Git & CI

- CI runs on push/PR to `main`: backend lint/typecheck/build/test, frontend typecheck/build
- Always verify locally: `cd backend && npm run lint && npx tsc --noEmit && npm run build && npm test`
- Always verify frontend: `cd frontend && npm run check`

### Branching & Merging

- **`dev` is the persistent development workspace** — NEVER delete it
- **NEVER commit directly to `main` or `dev`** — always use feature branches
- PRs target `main` via squash merge from feature branches
- When merging PRs, **never use `--delete-branch`** on `dev` or any shared branch
- Only delete short-lived feature branches (e.g. `feat/xxx`) that are not targets for other PRs
- **Why**: Deleting a branch that serves as a PR base (like `dev`) causes GitHub to auto-close all PRs targeting it (e.g. Renovate dependency updates)

### Commit Rules

- **Always create a feature branch** before making changes (e.g. `feat/color-scheme-fix`, `fix/theme-conflict`)
- **Never commit directly to `main` or `dev`** — this prevents unreviewed code from reaching production
- **Commit message format**: Use conventional commits (`feat:`, `fix:`, `chore:`, etc.)
- **After committing**: Create a PR targeting `main`, do not push directly to shared branches
- **Exception**: Only maintainers may push hotfixes directly to `main` with explicit approval

### PR and Release Rules

- **PR scope**: PRs are opened per submodule (`frontend/` or `backend/`), NOT the root repository
- **Release scope**: Releases are created per submodule, tagged with the submodule's version (e.g. `frontend-v1.0.3`, `backend-v1.2.0`)
- **Workflow**: feature branch -> commit -> open PR -> review -> merge -> create GitHub Release with matching tag
- **Version bump before merge**: Before the final merge, agents MUST verify that `package.json` version has been appropriately bumped:
  - **Patch** (`x.x.N`): bug fixes, dependency updates, internal refactors
  - **Minor** (`x.N.0`): new features, non-breaking API changes
  - **Major** (`N.0.0`): breaking changes, architecture rewrites
- **No version conflicts**: Before bumping, check the existing version tags (`git tag -l`) to ensure no collision with already-released versions
- **Release creation**: After merge to `main`, create a GitHub Release via `gh release create` with the submodule tag and auto-generated release notes

### **MANDATORY: Deployment & Release Workflow**

When releasing changes across submodules, agents MUST follow these steps **in exact order**. Skipping steps causes broken deployments.

**Step 0 — Lint, format, typecheck, and lockfile sync (BEFORE any commit)**
Before creating a commit or bumping versions, agents MUST run all quality checks and fix any issues:
```bash
# Frontend
cd frontend && npm run lint && npm run check

# Backend
cd backend && npm run lint && npx tsc --noEmit && npm run build && npm test
```
- `npm run lint` runs Prettier auto-fix + ESLint fix — all files MUST be `(unchanged)` or auto-fixed
- `npm run check` (frontend) / `npx tsc --noEmit` (backend) MUST pass with 0 errors
- **NEVER commit without running these first** — unformatted code will cause CI failures and unnecessary version bumps
- If lint or check produces changes, include those changes in the same commit as the feature/fix

**CRITICAL: Lockfile sync after any package change**
If ANY package-related file was modified (`package.json`, overrides, resolutions, dependency additions/removals), agents MUST run `npm install` in the affected submodule and verify no `package-lock.json` diff remains **before committing**:
```bash
cd <backend|frontend> && npm install
git diff --stat package-lock.json  # must be empty or included in commit
```
- `npm install --package-lock-only` is NOT sufficient — it only updates the top-level version field, not the resolved dependency tree. Always use `npm install`.
- If `package-lock.json` has changes after `npm install`, those changes MUST be included in the same commit as the `package.json` change.
- **Why**: CI runs `npm ci` which installs from the lockfile exactly. A mismatched lockfile causes silent dependency resolution differences between local and CI, leading to test failures like `Cannot find module` errors.

**Step 1 — Version bump**
- Bump `package.json` version in the affected submodule(s)
- Check existing tags first (`git tag -l`) to avoid collisions

**Step 2 — Commit on feature branch, push, open PR**
```bash
git checkout -b fix/your-branch
git add <files> && git commit -m "fix: description"
git push -u origin fix/your-branch
gh pr create --base main --head fix/your-branch --title "..." --body "..."
```

**Step 3 — Merge PR, delete feature branch**
```bash
gh pr merge <PR#> --squash --delete-branch
```

**Step 4 — Create GitHub Release**
```bash
gh release create <tag> --title "<tag>" --notes "## Changes\n- ..."
```

**Step 5 — Sync local `dev` branch in BOTH submodules**
```bash
# In each submodule directory:
cd backend && git checkout dev && git pull origin dev
cd ../frontend && git checkout dev && git pull origin dev
```
**Why**: After merge, submodules may be in detached HEAD on `main`. Always return to `dev`.

**CRITICAL: Sync main into dev with --ff-only ONLY**
`dev` must never accumulate merge commits from `main`. Sync with a fast-forward only:
```bash
cd <backend|frontend> && git merge --ff-only origin/main && npm install
git diff --stat package-lock.json  # if changed, commit and push
```
- **NEVER use `git merge main --no-edit` (or any non-ff merge) on `dev`.** Regular merges create commits whose net diff against `main` is zero, so `main...dev` comparisons show meaningless commits with 0 changed files.
- If `--ff-only` fails, `dev` has diverged. Check first:
  ```bash
  git diff --stat origin/main origin/dev   # must be empty
  ```
  - Empty → `dev` holds no unique work; reset it: `git reset --hard origin/main` then `git push --force-with-lease origin dev`
  - Non-empty → `dev` has real unique work; do NOT reset. Rebase or open a PR from `dev` instead.
- After the sync, run `npm install` to re-resolve the dependency tree (`git diff --stat package-lock.json`; if changed, commit and push to `dev`).
- Fast-forwarding `package.json`/`package-lock.json` alone is NOT enough — the lockfile may reference dependency versions resolved in a different context.

**Step 6 — Update root repo submodule reference to `dev`**
```bash
# From root repo — record the dev branch commit for each submodule
git add backend frontend   # only changed submodules
git commit -m "chore: update submodules to vX.Y.Z"
git push
```
**Critical**: The root repo records the exact commit each submodule points to. After step 5, `git add backend frontend` captures the `dev` branch HEAD commits. Verify with `git ls-tree HEAD backend frontend` that the recorded commits match `origin/dev`.
- The recorded commit MUST be reachable from `origin/dev` (or `main`) and match the release tag. Never record a commit that exists only on a branch you are about to rewrite or delete — a fresh clone would then fail to check out the submodule.
- If `origin/dev` was reset, re-run `git add backend frontend` so the pointer captures the new HEAD.

**Step 7 — Verify final state**
```bash
# Submodule refs should show dev branch commits (no +/- prefix)
git submodule status

# Each submodule should be on dev branch, up to date
cd backend && git log --oneline -1 && git branch --show-current
cd ../frontend && git log --oneline -1 && git branch --show-current
```
- `git submodule status` must show **no `+` or `-` prefix** (meaning working tree matches recorded commit)
- Each submodule's current branch must be `dev`
- `dev` must be up to date with `origin/dev`

> **NEVER commit directly to `main` in submodules.**
> **NEVER skip the root repo submodule update — production deploys pull from root `main`.**
> **NEVER leave submodules in detached HEAD or on `main` after operations complete.**

### Docker

- Build: `docker compose up -d --build`
- Default ports: Frontend 3002, Backend 3001, Redis 6399, Ollama 11434

### Important Patterns to Preserve

1. **Immutable archive snapshots**: `notice_archives` has immutability triggers; never mutate archived rows directly
2. **Diffchain integrity**: Event hashes must be computed consistently; see `backend-testing-notes.md`
3. **Lifecycle status**: Use `NOTICE_LIFECYCLE_STATUS` const, not raw strings
4. **Browser lease management**: Use `BrowserLeaseManagerService` for all browser operations
5. **Web push dispatch**: Bounded concurrency with retry/backoff (429/5xx aware)
6. **NSM deletion detection**: Always double-confirm with HTTP probe before marking `source_deleted`

### Common Pitfalls (from `agent_memories/repo/`)

- CacheService mock must include ALL methods used by the code under test
- `proposalReason` must preserve `\n` line breaks — do not use `/\s+/g` collapse
- `source_deleted` detection requires two independent confirmations
- `isDone` filtering needs lifecycle status filters on all candidate queries
- Frontend Playwright tests hit real backend by default — use `DIFFCHAIN_UI_MOCK=1` for isolated testing

---

## 7. Quick Reference Commands

```bash
# Backend
cd backend && npm install
cd backend && npm run start:dev          # Development server
cd backend && npm run lint               # Lint
cd backend && npx tsc --noEmit           # Type check
cd backend && npm run build              # Build
cd backend && npm test                   # Unit tests
cd backend && npm test -- --runInBand    # Tests sequentially

# Frontend
cd frontend && npm install
cd frontend && npm run dev               # Development server
cd frontend && npm run check             # Type check
cd frontend && npm run build             # Build
cd frontend && npx playwright test       # E2E tests

# Docker
docker compose up -d --build             # Start all services
docker compose down                      # Stop all services

# Deploy
./deploy.sh                              # Rolling update all
./deploy.sh backend                      # Update backend only
./deploy.sh frontend                     # Update frontend only
```
