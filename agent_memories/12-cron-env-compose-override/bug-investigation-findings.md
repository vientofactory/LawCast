# Production Sidecar Ignores `LAWCAST_SEMANTIC_UPDATE_CRON` from `.env` — Compose `environment` Outranks `env_file`

## Symptom (live, 2026-10-03)

`semantic-search/.env` on the server declares a daily schedule, but the running
container ticks hourly:

```console
root@multiverse:~# docker exec lawcast-semantic-search env | grep LAWCAST
LAWCAST_SEMANTIC_UPDATE_CRON=0 * * * *     <- hourly (compose hardcode)
LAWCAST_SEMANTIC_DB_PATH=/data/lawcast.db
LAWCAST_SEMANTIC_ARTIFACTS_DIR=/app/artifacts
LAWCAST_SEMANTIC_ALLOW_LARGE_DELETE=false
LAWCAST_SEMANTIC_MODEL=nlpai-lab/KURE-v1    <- only in .env
LAWCAST_SEMANTIC_DEVICE=cpu                 <- only in .env
LAWCAST_SEMANTIC_BATCH=16                   <- only in .env

root@multiverse:~# cat lawcast/semantic-search/.env
LAWCAST_SEMANTIC_UPDATE_CRON="0 0 * * *"    <- expected value, ignored
```

The 3 `.env`-only keys arrive correctly, while the one key that exists in
**both** sources takes the compose value. That split is the signature of an
override, not a broken loader.

The live health endpoint confirms the hourly schedule is actually firing:

```json
{"indexedChunks":96587,"lastUpdateAt":null,"lastUpdateTriggeredAt":"2026-10-03T14:00:00.000695+00:00"}
```

## Root cause

`docker-compose.yml` (pre-patch line 86) hardcodes the expression inside the
service `environment` block:

```yaml
env_file:
  - path: ./semantic-search/.env
environment:
  - LAWCAST_SEMANTIC_DB_PATH=/data/lawcast.db
  - "LAWCAST_SEMANTIC_UPDATE_CRON=0 * * * *"   # wins over env_file
  - LAWCAST_SEMANTIC_ALLOW_LARGE_DELETE=false
```

**Docker Compose precedence: service `environment` (3rd) > service `env_file`
(4th).** Values merged from `env_file` are merged into the same map, and an
explicit `environment` entry replaces them. So `.env` was read but its
`UPDATE_CRON` line was silently discarded.

**HIGH** — the same pattern as `11-api-version-fallback-stamp` (a hardcoded
compose value outranking a file owned by another layer). Two consequences:

1. Editing `semantic-search/.env` to retune the cadence did nothing.
2. The documented **off-gate was unreachable**: design §4.2 and the compose
   comment say "empty cron expression turns scheduling off", but an empty
   value in `.env` could never reach the container while the hardcode sat
   above it — the recommended pre-deploy mitigation in
   `08-.../production-readiness-status.md` item 5.3 could not be applied.

Quotes were **not** the problem: compose strips them (`"0 0 * * *"` renders as
`0 0 * * *`), proven by the `BATCH`/`MODEL` keys arriving unquoted.

## Proof (local, patched vs unpatched, identical `.env`)

Both runs used `docker compose ... run --rm --no-deps --entrypoint "" semantic-search env`
with `.env` set to `LAWCAST_SEMANTIC_UPDATE_CRON="0 0 * * *"`:

| Compose file      | Rendered / container value |
| ----------------- | -------------------------- |
| `HEAD` (hardcode) | `LAWCAST_SEMANTIC_UPDATE_CRON=0 * * * *`  (reproduces production) |
| patched           | `LAWCAST_SEMANTIC_UPDATE_CRON=0 0 * * *`  (env_file wins) |

`docker compose config semantic-search` agrees: patched + prod-like `.env` ->
`LAWCAST_SEMANTIC_UPDATE_CRON: 0 0 * * *`.

## Patch

`docker-compose.yml` only (root repo, no submodule bump):

1. **Removed** the `- "LAWCAST_SEMANTIC_UPDATE_CRON=0 * * * *"` line from
   `semantic-search.environment`, replaced with a comment explaining why it
   must stay absent. Ownership moves to `semantic-search/.env`; if the file is
   missing, `lawcast_semantic/config.py:108` falls back to `0 * * * *`.
   - `DB_PATH` stays in `environment` (deliberate: it is not in the server
     `.env`, and it is the scheduling master gate).
   - `ARTIFACTS_DIR` stays (`.env.example` says it is intentionally absent).
   - `ALLOW_LARGE_DELETE` stays (both sources agree on `false`; no conflict).
2. **Added `required: false`** to the `env_file` entry. Compose's default is
   `required: true`, so a missing `semantic-search/.env` (it is gitignored)
   made `docker compose up`/`config` **hard-fail**:
   `env file .../.env not found`. README.md and `.env.example` both claimed
   `required:false` already — the compose file never set it. Now:
   - `.env` present -> operator values apply;
   - `.env` absent -> compose runs, code defaults apply, and the empty
     `DB_PATH` default keeps scheduling off (the documented safe state).

## Verification

- `docker compose config` with prod-like `.env` -> `0 0 * * *`; with the file
  removed -> RC=0 and no `UPDATE_CRON` key (code default path).
- Runtime `env` inside a compose-created container: `0 * * * *` before the
  patch, `0 0 * * *` after (same `.env`).
- Quality gates: backend `lint` / `tsc --noEmit` / `build` / `npm test`
  (66 suites, 855 tests); frontend `lint` (all unchanged) / `check` (0 errors);
  semantic-search `ruff check` / `ruff format --check` (34 files) / `pytest`
  (129 passed).
- Post-deploy server check: `docker exec lawcast-semantic-search env | grep
  LAWCAST` must show `LAWCAST_SEMANTIC_UPDATE_CRON=0 0 * * *`, and
  `lastUpdateTriggeredAt` should stop landing on the top of the hour.

## Deploy implications

- `docker-compose.yml` is in **both** services' guard `PATHS`
  (`.github/scripts/deploy-change-guard.sh`), so the merge deploys backend and
  semantic-search; the sidecar is recreated and picks up the new env.
- Recreating the sidecar does **not** touch artifacts: `run_boot_repair` only
  runs when artifact load *fails* (`service/app.py` phase 2), so a healthy
  boot is a clean load (~15 s, no rewrite).
- Behaviour change on the server: hourly -> **daily** (that is what the
  server's `.env` asks for). The next tick moves to the next local midnight.

## Pitfall for all agents

In Docker Compose, `environment` always beats `env_file` for the same key.
Never put an operator-tunable value in `environment` while a gitignored
`.env` is presented as its owner — the edit silently does nothing, and an
intended "set it empty to disable" kill switch silently never fires. Keep
infra-owned invariants (`TZ`, `DB_PATH`, cache dirs) in `environment`, and
operator-owned knobs in `env_file`.

Cross-references:
- `agent_memories/11-api-version-fallback-stamp/bug-investigation-findings.md`
  (same class of bug, one layer up: compose interpolation default)
- `agent_memories/08-semantic-search-production-deploy/incremental-update-pipeline-design.md`
  §4.2 (cron/off-gate contract)
- `agent_memories/08-semantic-search-production-deploy/production-readiness-status.md`
  item 5.3 (its `LAWCAST_SEMANTIC_UPDATE_CRON=` mitigation only became
  reachable with this patch)
