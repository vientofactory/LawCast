# Production `/api/version` Returns Hardcoded `0.0.1` — Compose Fallback Stamp

## Symptom (live, 2026-10-03)

`GET https://law.viento.me/api/version` returns

```json
{ "version": "0.0.1", "buildEnv": "env" }
```

- **`buildEnv: "env"` proves the value comes from the `APP_VERSION` environment
  variable**, not from `package.json` (`backend/package.json` is `1.3.0`).
- Response headers show `cf-cache-status: DYNAMIC` — it is live, not cached.
- `GET /api/health` reports the same `version: "0.0.1"`.

## Version resolution chain

`backend/src/modules/shared/packages.service.ts` `loadVersion()` priority:

1. `process.env.APP_VERSION` (trimmed; empty string falls through)
2. `version` field in `package.json` (read from `process.cwd()`)
3. hardcoded `'unknown'`

So an **explicitly set wrong value always wins** over the real package version.

## The only producer of `0.0.1` in the whole system

Repo-wide grep (`APP_VERSION` / `0\.0\.1`): the literal `0.0.1` exists only in
`docker-compose.yml` (pre-patch lines 7 and 17):

```yaml
args:
  - APP_VERSION=${APP_VERSION:-0.0.1}      # build arg (dead: Dockerfile declares no ARG)
environment:
  - APP_VERSION=${APP_VERSION:-0.0.1}      # container runtime env
```

**HIGH** — the hardcoded default converts "APP_VERSION not available" into a
*fake* version that outranks `package.json` in the backend's priority chain.

## Why CI's export does not protect production

- `.github/workflows/deploy-backend.yml:139` exports
  `APP_VERSION=$(grep '"version"' backend/package.json | ...)` right before
  `./deploy.sh backend`; CI logs confirm the value
  (`APP_VERSION=1.3.0` in run `37108502699`, `1.2.0` in `37077016912`, ...).
- Compose interpolates from the deploying shell first (Docker docs precedence;
  `docker/compose#9045` "`.env` ignores shell" fixed 2022-01-26; server compose
  must be ≥ v2.24 because `docker-compose.yml` uses the long `env_file: path:`
  syntax — verified: `docker compose config` local v5.1.2 renders shell value).
- **Any compose run outside that one CI step** (manual `./deploy.sh`,
  `docker compose up -d --build` — both documented in README/AGENTS) has **no**
  `APP_VERSION` in its shell, so `${APP_VERSION:-0.0.1}` stamps the recreated
  backend container with `0.0.1`.

## Evidence the live container was stamped outside CI

- Last CI backend deploy: run `37108502699`, `2026-10-03 08:07:40Z`
  (`Container lawcast-backend Running` — no recreate; guard "changes detected").
- The live API's startup pipeline timestamps
  (`pending sync` 09:34:31Z, `legacy genesis seed` 09:34:31Z, `full sync`
  09:34:35Z, `summary backfill` 09:56:07Z — all from `runBootstrapPipeline` in
  `backend/src/modules/crawling/archive-sync.service.ts:270-339`) show the
  serving process **booted ≈ 09:34Z, ~87 minutes after CI's deploy**.
- A plain `docker restart` keeps container env, so `0.0.1` implies a
  **recreate by a compose run without `APP_VERSION`** (manual deploy or a
  server-side script), not a crash-restart.

## Patch

`docker-compose.yml` — remove the hardcoded default on both occurrences:

```yaml
args:
  - APP_VERSION=${APP_VERSION:-}
environment:
  - APP_VERSION=${APP_VERSION:-}
```

- With `APP_VERSION` exported (CI): container gets the real value (unchanged).
- Without it (manual/raw compose): container gets `""`, the backend's
  `.trim()` guard falls through to `package.json` → correct deployed version.

## Verification

- `docker compose config`: shell `APP_VERSION=1.3.0` → `APP_VERSION: 1.3.0`;
  no shell → `APP_VERSION: ""` (was `0.0.1`); `docker compose config -q` OK.
- `cd backend && npx jest src/modules/shared/packages.service.spec.ts` —
  13/13 pass, including "ignores empty APP_VERSION and falls through to
  package.json".
- `docker-compose.yml` is listed in the backend deploy-guard paths
  (`.github/scripts/deploy-change-guard.sh`), so the next push touching it
  forces a backend redeploy that recreates the container and clears the stamp.

## Remaining uncertainty

- **Which actor** ran compose at ≈09:34Z on the server is not visible from the
  repo (no SSH access from the workspace). Check on the host:
  `history | grep -E 'deploy.sh|compose'`,
  `docker events --filter event=create --since 2026-10-03T09:00:00Z`.
- Whether the server's gitignored `.env` files pin `APP_VERSION` could not be
  inspected; no repo template (`.env.example`, `backend/.env.example`) defines
  it.

## Pitfall for all agents

Never re-introduce a hardcoded default for a version env var in compose.
A default that is *not* a real version silently overrides the package manifest
fallback and makes `/api/version`, `/api/health`, and the frontend footer lie.
