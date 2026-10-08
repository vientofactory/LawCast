# Production `node build/index.js` Served a Stale Artifact + Missing Runtime Env (2026-10-08)

## Symptom

Everything renders in `npm run dev`, but the production server (`node build/index.js`) was
missing large portions of the UI: `/discussions`, `/announcements`, `/proposals` returned
**404**, the home hero pinned chip, 토론 / 발의 통계 nav items, and the recent-discussions
section were absent, and every route's HTML was a fraction of the dev size
(`/` 62,860 B vs 188,461 B).

## Root cause 1 — **CRITICAL**: adapter switch left `build/` permanently stale

- Commit `43471c6` (2026-08-15, frontend submodule) changed `svelte.config.js` from
  `@sveltejs/adapter-node` to `@sveltejs/adapter-cloudflare` and removed adapter-node from
  `package.json`.
- Since then `npm run build` writes `.svelte-kit/cloudflare/_worker.js` and **never touches
  `build/`**. The local `build/` directory was frozen at **2026-08-14 19:57** (commit
  `dd41252`), so `node build/index.js` ran a ~2-month-old app (20+ commits behind: no
  discussions, semantic search, announcement board, proposals page...).
- `frontend/Dockerfile` was broken the same way: `COPY --from=builder /app/build ./build`
  cannot succeed when the builder stage emits `.svelte-kit/cloudflare`.
- The uncommitted SSR payload minimization WIP was **innocent** — `npm run build` was green
  with it; its output simply could never reach `build/`.

## Root cause 2 — `PUBLIC_*` vars are runtime-only in the node build

- Feature gates use `$env/dynamic/public` (Discord community section, footer Discord link,
  semantic-search enable → `/notices/semantic-search`), and the adapter-node server resolves
  them from `process.env` at `Server.init()`. The dev server loads `.env`; `node build/index.js`
  does not, so with a bare start command those elements silently disappear (semantic search
  answered **303 → /notices**).

## Patch (frontend submodule, uncommitted)

| File | Change |
| --- | --- |
| `svelte.config.js` | dual adapter: `SVELTE_ADAPTER=node` → adapter-node, default stays adapter-cloudflare (CI + Cloudflare Pages dashboard build command `npm run build` unchanged) |
| `package.json` | `@sveltejs/adapter-node` `^5.4.0` (devDeps), scripts `build:node` and `start:node` (`node --env-file-if-exists=.env build/index.js`); `package-lock.json` synced with `npm install` |
| `Dockerfile` | `ENV SVELTE_ADAPTER=node` before `RUN npm run build`; runner copies `.env`; `CMD ["node", "--env-file-if-exists=.env", "build"]` |
| cleanup | removed previous session's `tmp-probe1~5.mjs` + `.tmp-shots/` (they broke `npm run lint`) |

## Verification

- `SVELTE_ADAPTER=node npm run build` regenerates `build/index.js`; plain `npm run build`
  still emits `.svelte-kit/cloudflare` (checked both).
- All 10 routes **200** on `node build/index.js` (previously 3× 404); home visible text
  **prod 1,427 == dev 1,427 chars, 0 word diff**; `/discussions` 359 == 359, 0 word diff.
- Env-gated elements confirmed back with only `.env` (no manual vars): Discord section,
  footer `discord.gg` link, semantic search 200.
- `npm run lint` exit 0, `npm run check` 0 errors / 0 warnings.

## Pitfalls

- **Do not compare raw HTML bytes** between dev and prod: dev inlines ~116 KB of Tailwind
  CSS in `<style>` tags; prod serves it as an external `/_app/immutable/assets/*.css`
  (verified 200, 87,559 B) plus `html-minifier-terser` runs only outside dev
  (`src/hooks.server.ts` skips minify when `dev`).
- **`npm run build` alone still leaves `build/` untouched** — self-hosted node deployments
  MUST use `npm run build:node` (or the Dockerfile, which sets `SVELTE_ADAPTER=node`).
- **Deploy ordering**: the WIP layout/page loaders call `GET /api/announcements/top`, which
  exists only in the uncommitted backend controller change. Release the backend first or the
  pinned chip / urgent banner render as `null`.
- `.env` reaches the runner image via an explicit `COPY --from=builder`; if someone strips
  that line, `--env-file-if-exists` silently no-ops and the feature gates disappear again.
