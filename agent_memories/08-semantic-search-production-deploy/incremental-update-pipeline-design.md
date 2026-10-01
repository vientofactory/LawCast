# Scheduled Index Refresh Pipeline (Design)

Design deliverable for the request: _periodically re-read the backend DB and
update the semantic index, connecting the two independently deployed Docker
containers._ **Design only — no implementation in this pass.** The completion
criterion is that an implementer can start without further questions and
without contradicting existing code or docs.

Related single-owner docs:

- `agent_memories/07-incremental-indexing/plan.md` — incremental algorithm,
  atomic write order, crash-repair equivalence (all verified; reused unchanged).
- `agent_memories/08-semantic-search-production-deploy/plan.md` — deploy
  context; items B2 (hot reload) and B3 (scheduling) are the roadmap entries
  this design closes.

## 0. Scope

**In scope**: refresh flow, container connection medium (decision), scheduler
executor + interval (decision), atomic artifact swap with readiness maintained,
failure/rollback/retry policy, file-level change list, verification plan.

**Non-goals**: frontend, full-corpus eval relabeling, scheduled model swaps or
chunking-parameter changes (both are full rebuilds per 07 §2.1 — explicitly
refused by the incremental contract), multi-host deployment (would revisit
§3), any backend (NestJS) code change.

## 1. Reuse inventory — already decided vs open

### 1.1 Decided (do not redesign)

| Topic             | Decision (source)                                                                                                                                                                                                                                            |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Corpus source     | `notice_archives.proposalReason` via `datasource.load_notices_from_db` — `sqlite3` `mode=ro` URI, one connection per read (07, `datasource.py`)                                                                                                              |
| Change detection  | Content digests: full re-chunk (~4 s) + `plan_update` diff against committed `chunks.jsonl`. No timestamps, no state file (07 §2.2)                                                                                                                          |
| Update algorithm  | `plan_update` / `apply_update` library functions (the `06` script is a thin CLI over them). No-change run = seconds, embedding model never loaded (07 §3)                                                                                                    |
| On-disk atomicity | Per-file temp + `os.replace`; write order `embeddings.npz → id_map.json → faiss.index → chunks.jsonl` (commit point). Any interleaving = old set or a mix that fails validation (07 §2.2)                                                                    |
| Crash recovery    | Rerun repairs; after a crash the rerun re-embeds **0** rows (self-describing `chunk_text_digests`) — verified V3/V4                                                                                                                                          |
| Equivalence       | Incremental output == full rebuild (byte-identical chunks/id_map, max abs diff 0.0 vectors, search parity) — verified V1/V2/V2b                                                                                                                              |
| Reload validation | `SemanticSearcher.load` gates: fingerprint, model, dim, `ntotal == len(chunk_ids)`                                                                                                                                                                           |
| Serving process   | `EngineState` single-writer lock; handlers take a snapshot (strong ref to current searcher) and search **outside** the lock; lifespan background engine-load thread; `/health {status, model, indexedChunks, error}`; healthcheck unhealthy only on `failed` |
| Compose           | artifacts bind mount rw `./semantic-search/artifacts:/app/artifacts`, `LAWCAST_SEMANTIC_ARTIFACTS_DIR=/app/artifacts`, HF cache volume, TZ Asia/Seoul, network `lawcast-network`, backend → `SEMANTIC_SEARCH_API_URL=http://semantic-search:8300`            |
| DB location       | named volume `lawcast_db:/app/data`, `DATABASE_PATH=/app/data/lawcast.db`, WAL mode; backend cron infra staggers jobs away from minute-0 (`app.config.ts`)                                                                                                   |
| UID direction     | plan.md pitfall already prescribes: _"align uids or run the update as a matching user"_ when wiring B3                                                                                                                                                       |
| Legal producers   | README 교체 규칙: two producers — full `01→03` and incremental `06`; no hand-partial replacement                                                                                                                                                             |

### 1.2 Open (decided in this document)

1. Connection medium between the two containers (§3) → **shared `lawcast_db`
   volume mounted rw into the sidecar**.
2. Scheduler executor (§4.1) → **sidecar-internal lifespan thread**.
3. Interval (§4.2) → **60 min default**, env-tunable, jittered, off unless
   configured.
4. Hot reload / in-memory swap with readiness maintained (§5) → **load-validate-swap**,
   old generation serves until the new one passes validation.
5. Failure, rollback, retry policy incl. the torn-boot deadlock (§6).

## 2. End-to-end flow (one tick)

```
sidecar lifespan
 └─ update-scheduler thread (sleep interval ± jitter)
     ├─ gate: DB_PATH configured, EngineState.status == 'ready', not already running (single-flight)
     ├─ 0. acquire artifacts flock (artifacts/.update.lock)
     ├─ 1. read full corpus: load_notices_from_db(DB_PATH)      # WAL snapshot, seconds
     ├─ 2. plan = plan_update(notices, artifacts...)            # content-digest diff; no model
     ├─ 3. safety rail: refuse if shrink beyond §6 threshold    # wrong/empty DB guard
     ├─ 4. if plan.needs_embedding: embed via the LIVE embedder # batch-locked per §5.4
     ├─ 5. apply_update(...)                                    # 07 write order, atomic per file
     ├─ 6. if plan.has_changes or disk/in-memory mismatch: reload()  # §5.2
     ├─ 7. record result (/health additive fields), release flock
     └─ on any exception: log, record lastUpdateError, end tick (no tight retry)
```

Properties: queries at every point serve either the complete old generation or
the complete new one (steps 1-5 do not touch the serving objects; step 6 swaps
atomically). A no-change tick costs one DB read + one re-chunk + artifact read
and never loads a model or touches files.

## 3. Connection medium (두 컨테이너 연결 매개체)

### 3.1 Options

| #      | Medium                                                           | How                                                                                  | Pros                                                                                                                                                                                                                                                 | Cons                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **M1** | **Shared named volume `lawcast_db` mounted rw into the sidecar** | compose: `- lawcast_db:/data`; `datasource.py` opens `file:/data/lawcast.db?mode=ro` | Zero new code (datasource exists, `06 --db` already verified against a DB clone — 07 V2b); no extra service; WAL gives a consistent snapshot per read while the backend keeps writing; read cost seconds vs 20k rows; `mode=ro` cannot mutate the DB | Couples sidecar to backend storage layout (same host only); SQLite WAL needs `-shm` **write** access even for `mode=ro` (plan.md B3 already states this) → uid alignment required                                                                                                                                                                                                                             |
| M1b    | DB snapshot file (backend `VACUUM INTO` / `.backup` on a cron)   | snapshot has no WAL, sidesteps `-shm`                                                | **Requires backend code** (new cron job — contradicts the no-backend-change scope), ~GB-scale copy per cycle, snapshot lag                                                                                                                           | rejected as primary; kept as fallback if uid alignment proves impossible (§3.2)                                                                                                                                                                                                                                                                                                                               |
| M2     | Backend HTTP export endpoint                                     | sidecar polls a new `GET /api/notices/export`                                        | Decouples storage; uses the HTTP boundary both services already have                                                                                                                                                                                 | **New backend endpoint** (scope + contract + rate-limit/error-envelope handling); full corpus ≈ 20k rows re-shipped as JSON every tick (paginated: dozens of requests); duplicates corpus-selection logic (`NOTICE_SELECT_COLUMNS`, lifecycle filters) that `datasource.py` already owns — drift risk; reverses the established call direction (backend→sidecar only)                                         |
| M3     | Message queue (Redis pub/sub — Redis is in the stack)            | backend publishes "db changed", sidecar reacts                                       | Decoupled, event-driven                                                                                                                                                                                                                              | Queue carries no data — the sidecar still needs M1 or M2 to read the corpus; publishing requires invasive write-path hooks in the backend (crawl, backfill, is_done sync, manual edits all write the DB); the job is a **state sync** ("make artifacts equal current corpus"), which content-digest diffing already makes idempotent — events add loss/duplication semantics for nothing; a third moving part |

### 3.2 Decision: **M1 — shared volume**

The pipeline is a periodic full-state sync, not an event stream: M3's events
are redundant (every tick re-derives changes from content), and M2's
duplicate-export surface is strictly more new code than M1's compose line —
for data `datasource.py` already reads today. M1 keeps the backend untouched
(its only "API" to the pipeline is the DB it already maintains) and matches
plan.md B3's pre-investigated direction. Constraint: same host (true for this
compose deployment); if the sidecar ever moves off-host, M2 becomes the choice
— recorded here so the reversal trigger is explicit.

**WAL / `-shm` handling** (the one real cost of M1):

1. Mount rw: `- lawcast_db:/data` on `semantic-search` (rw is required for
   `-shm` even though the reader uses `mode=ro` — plan.md B3).
2. **Deploy-time measurement (not assumed)**:
   ```bash
   docker compose exec backend stat -c '%u %g' /app/data/lawcast.db-wal
   docker compose exec semantic-search id -u -g
   ```
   If the sidecar uid cannot write `-shm`: primary fix = compose `user:` on
   `semantic-search` aligned to the backend data-file uid (exactly the
   "align uids" direction plan.md prescribes), with a one-time ownership fix
   for the artifacts dir on Linux hosts (macOS/OrbStack mounts are
   permission-transparent — existing pitfall note). Fallback ladder:
   (a) `setfacl`/`chmod` on the volume dir, (b) M1b snapshot.
3. Not NFS-safe (file locking assumes a local filesystem) — true for named
   local volumes; recorded as a deployment constraint.
4. The read holds one connection for seconds; backend WAL writers are
   unaffected (readers never block writers). The only observed contention is
   the weekly `SQLITE_VACUUM` (`31 5 * * 0`), which cannot run alongside an
   open read — tick duration is seconds and interval is env-tunable; if
   overlap ever matters, offset the interval (documented mitigation, no code).

## 4. Scheduler (실행 주체와 주기)

### 4.1 Executor options

| #      | Executor                                                                                              | Pros                                                                                                                                                                                                                                                                                                        | Cons                                                                                                                                                                                                                      |
| ------ | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **E1** | **Sidecar-internal thread started in FastAPI `lifespan`** (alongside the existing engine-load thread) | Read → write → reload in **one process**: reload needs no HTTP hop; reuses the **already-loaded embedder** (a second copy would cost ~2.2 GB RAM); zero new containers/services; matches the existing lifespan-thread pattern; interval failure cannot affect the request path (exceptions caught per tick) | Build and serve share CPU/RAM (embedding burst ≈ 21.5 chunks/s on CPU — see §9); a hard crash (OOM) in the runner restarts the serving process too (mitigated by §6 torn-boot repair)                                     |
| E2     | Separate indexer container                                                                            | Crash/OOM isolation                                                                                                                                                                                                                                                                                         | Duplicates the model (~2.2 GB RAM, shares HF cache volume only after first download); needs its own scheduling _and_ an IPC trigger for reload; far more moving parts for a job whose heavy step is seconds of embedding  |
| E3     | Backend NestJS cron (`cronjobs.service.ts`) triggering the sidecar over HTTP                          | Uses the existing cron infra; triggers right after crawl/backfill jobs                                                                                                                                                                                                                                      | Backend code change (out of scope); only _triggers_ — the read medium is still M1, so it adds an endpoint + a failure path without removing anything; index freshness couples to backend deploys/config                   |
| E4     | Host cron via `docker compose exec` (plan.md B3 option)                                               | No in-container code                                                                                                                                                                                                                                                                                        | Outside compose lifecycle (missed when only containers are managed; host-dependent; `deploy.sh`-style ops drift). Listed in B3, rejected here as the primary — kept as the emergency manual runbook (`flock`-guarded, §6) |

### 4.2 Decision: **E1**, interval **60 minutes** (default)

- Thread: `update-scheduler` daemon thread in `lifespan`, same pattern as
  `semantic-engine-load`; sleeps `interval ± 10% jitter` (jitter avoids the
  repo's minute-0 contention convention since the tick is start-time-relative).
- Only ticks when `EngineState.status == 'ready'` (embedder available);
  `loading` → wait; `failed` → no ticks (boot repair in §6 covers the
  artifact-failure case).
- Single-flight: a non-blocking lock; a tick that overlaps the previous one is
  skipped and logged (embedding is the long step; at 60 min it cannot overlap
  in practice, but slow DB or a hung model must not queue work).
- **Why 60 min**: the backend crawls every 10 min, backfill every 15 min,
  `is_done` sync every 6 h — content drifts continuously, so there is no
  "right" event to align with; a no-change tick costs seconds and touches
  nothing, so a tighter interval buys little while a looser one (24 h) would
  leave new notices unsearchable for a day. 60 min bounds staleness at ≤1 h
  for ~0 marginal cost. Env-tunable for operators who want tighter (crawl
  bursts) or looser (quiet installs).
- Configuration (single owner: `lawcast_semantic/config.py`, `LAWCAST_SEMANTIC_*`
  convention):

  | Env var                                    | Default   | Meaning                                                                                                 |
  | ------------------------------------------ | --------- | ------------------------------------------------------------------------------------------------------- |
  | `LAWCAST_SEMANTIC_DB_PATH`                 | _(empty)_ | backend DB path; **empty = scheduling disabled** (host dev runs and existing tests stay byte-identical) |
  | `LAWCAST_SEMANTIC_UPDATE_INTERVAL_MINUTES` | `60`      | tick period; `0` also disables                                                                          |
  | `LAWCAST_SEMANTIC_ALLOW_LARGE_DELETE`      | off       | operator override for the §6 shrink guard; parsing rule below                                           |

  **Boolean parsing rule (single definition, implemented in `config.py`
  next to the existing `os.environ.get` vars)**:
  `os.environ.get('LAWCAST_SEMANTIC_ALLOW_LARGE_DELETE', '').strip().lower() in {'1', 'true', 'yes', 'on'}`.
  Unset, empty, or any other value = `false`; no other truthy spelling is
  accepted, so a typo (`ye`, `on?`) fails safe with the guard still closed.
  This is the only place the accepted spellings are defined — §6.1's
  `ALLOW_LARGE_DELETE=true` obeys it.

  compose sets `LAWCAST_SEMANTIC_DB_PATH=/data/lawcast.db` (+ the volume of
  §3.2).

## 5. Atomic swap & readiness during refresh

Two distinct swaps — both required by "갱신된 인덱스 아티팩트의 원자적 교체
및 교체 중 readiness 유지".

### 5.1 On disk — reuse 07 verbatim

`apply_update` already writes temp + `os.replace` in the order
npz → id_map → faiss.index → chunks.jsonl (commit point); every partial
interleaving is either the complete old set or a validation-failing mix, and a
rerun repairs it (V3/V4). **No new mechanism** — this level is done. Space
note: a tick needs ≈1 GB free in the artifacts mount for temp files
(npz ≈ 400 MB, index ≈ 400 MB, chunks ≈ 54 MB).

### 5.2 In memory — load-validate-swap (`EngineState.reload()`)

The sidecar loads artifacts once at startup today (plan.md B2). Design:

1. **Trigger**: end of a successful tick with changes (in-process call), plus
   `POST /reload` on the sidecar (internal network, no auth — same stance as
   the rest of the service) for manual/ops runs and for the host-pipeline case
   (`01→03` on the host → one curl instead of a restart).
2. **Load outside the lock**: build a _new_ `SemanticSearcher` via the
   existing `SemanticSearcher.load` (all validation gates run here) while the
   old searcher keeps serving. Seconds for 96k chunks; no lock held → zero
   query blocking.
3. **Swap under the lock**: single reference assignment + `indexed_chunks`
   update (same pattern as `mark_ready`). `status` stays `ready` the whole
   time — readiness is never dropped (unlike a restart, which re-enters
   `loading` for ~17 s warm). In-flight requests that already took a snapshot
   finish on the old generation (snapshot holds a strong ref) — no request
   ever sees a half-swapped state.
4. **Failure**: validation/IO error → new searcher discarded, **old generation
   stays active**, `status` stays `ready`, error recorded in a new additive
   `/health` field `reloadError`; next tick retries (§5.3).
5. **Additive `/health` fields** (existing consumers read `status` only —
   compose healthcheck and the contract spec are unaffected):
   `reloadError: string|null`, `lastUpdateAt: iso8601|null`,
   `lastUpdateResult: 'changed'|'unchanged'|'failed'|'skipped'|null`,
   `lastUpdateError: string|null`, `generation: int` (increments per
   successful load/reload — cheap observability for "did my change land?").

### 5.3 Self-healing retry: fingerprint mismatch

Failure mode to close: reload fails once, next tick sees `has_changes == false`
(disk already new) and would never retry → permanently stale memory. Rule:

> Every tick compares the disk `chunks_fingerprint` (from `id_map.json`,
> ~2 MB parse) with the generation the engine currently serves
> (`state.loaded_fingerprint`, recorded at load/reload). Mismatch → attempt a
> reload **even when `plan.has_changes` is false**.

This invariant ("memory generation == disk generation, or a reload was
attempted this tick") also covers the host-built-artifacts case for free.

### 5.4 Embedding concurrency

The updater embeds changed chunks with the **live embedder** (no second model
copy). PyTorch inference is thread-safe; the process already runs
single-threaded OMP (`use_single_threaded_omp`). Design: embed in
`EMBED_BATCH_SIZE` (32) batches with a lock held **per batch** (~1.5 s at the
measured 21.5 chunks/s CPU), so worst-case query latency impact is one batch's
encode, bounded and rare (only ticks with changes). Verification step in §8
confirms concurrent embed+query correctness; if it ever regresses, the fallback
is a dedicated updater embedder (2.2 GB) — recorded, not planned.

## 6. Failure, rollback, retry

### 6.1 Failure matrix

| Failure                                                 | Detection                                                                    | Behavior                                                                                         | Recovery                                                                                                                                                                                                                                                                 |
| ------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| DB missing / unreadable / locked                        | `sqlite3.connect` or read raises                                             | tick aborts before any write; log WARN; `lastUpdateResult='failed'`                              | next tick (no tight retry)                                                                                                                                                                                                                                               |
| Corpus shrink beyond guard (wrong/empty DB mounted)     | plan reports deletions > **20% AND > 100** notices vs current `chunks.jsonl` | **refuse to apply**; log ERROR with counts; serving untouched                                    | operator investigates, re-runs with `LAWCAST_SEMANTIC_ALLOW_LARGE_DELETE=true` (spelling per §4.2) or the manual `06` (manual stays authoritative — this guard is runner-level policy, not an artifact-contract change, so 07's verified delete semantics are untouched) |
| Embed fails / OOM during embed                          | exception before `apply_update` writes                                       | disk untouched (plan/apply split); serving untouched                                             | next tick re-embeds only what's missing (idempotent)                                                                                                                                                                                                                     |
| **Process killed mid-`apply_update` (torn disk)**       | process dies; Docker restarts container                                      | on-disk mix fails `SemanticSearcher.load` → boot would stick at `failed`                         | **boot repair** (below)                                                                                                                                                                                                                                                  |
| Reload validation fails (corrupt/partial artifact read) | `SemanticSearcher.load` raises in `reload()`                                 | old generation keeps serving; `reloadError` set; `ready` unchanged                               | fingerprint mismatch (§5.3) re-attempts every tick; persistent → ERROR log each tick, operator action: `docker compose restart semantic-search`                                                                                                                          |
| Engine `failed` for model reasons (bad env)             | existing path                                                                | unchanged: `failed` → healthcheck unhealthy → restart loop cannot heal bad config                | existing documented fix-env-and-recreate path                                                                                                                                                                                                                            |
| Repeated tick failures                                  | consecutive `failed` counters in logs                                        | serving continues; healthcheck **stays healthy** (stale-but-serving beats keyword-only fallback) | inspect `lastUpdateError` via `/health`                                                                                                                                                                                                                                  |

**Torn-boot deadlock and its closure** — the one non-obvious failure:
crash mid-write leaves a set that fails boot validation; a naive
`status == ready` gate would then never let the repair run (deadlock).

**Discrimination = load phase, never exception type.** Today's `load_engine`
is one `try` wrapping both loads, so "which load failed" cannot be recovered
from the exception (`SemanticSearcher.load` raises `ValueError` at each of
its four gates — ntotal/fingerprint/model/dim — but `KoreanEmbedder()` can
raise `ValueError` too; type or message matching is guesswork). Restructure
`load_engine` into two sequential phases, each with its own `except`:

1. **Phase 1 — embedder** (`embedder = KoreanEmbedder()`): failure →
   `mark_failed` immediately, **no repair hook**. Without a working embedder
   no cycle can produce vectors and `reload()` can never validate a set, so
   model/env failures stay on the existing fix-env-and-recreate path
   (plan.md lifecycle matrix unchanged — e.g. `RepositoryNotFoundError` on a
   bogus model, `failed` in ~8 s).
2. **Phase 2 — searcher** (`SemanticSearcher.load(embedder)`): failure →
   **repair hook, and only here**, and only when `DB_PATH` is configured.
   This phase covers both validation gates (`ValueError`) and
   missing/corrupt artifact files (`FileNotFoundError`/`OSError`).

**Repair scope guard** — the hook runs one cycle with the _already-loaded
phase-1 embedder_ (no second model load: at boot it is already in memory),
then applies **iff `plan.needs_embedding` is False**:

- Torn window (the deadlock case): npz is write #1 and already carries the
  embedded rows + digests, so every crash interleaving of an existing
  baseline plans with **0 embeds** (V3 measured exactly this) →
  `apply_update` → `reload()` → `mark_ready`.
- Artifacts absent or foreign (no usable baseline — index bootstrap is B1's
  manual decision): the plan needs a full embed → **refuse, `mark_failed`**.
  This preserves today's measured fast-fail for missing artifacts (plan.md
  matrix: `FileNotFoundError` → `failed` in ~16 s) and stops an in-container
  auto-rebuild from hijacking B1's "host-built artifacts" runbook.
- Known corner, documented not hidden: a DB write landing inside the apply
  window makes the repair plan need embedding → refuse → `failed` →
  healthcheck unhealthy → Docker restarts (each boot retries the repair, so
  the state is visible, not silent); recovery is the §6.2 runbook (manual
  `06` + `POST /reload`).

During repair the status stays `loading` (the hook runs inside the load
thread before any `mark_*`), so the healthcheck remains healthy — same
semantics as a slow cold boot — and flips to `ready` (generation 1) or
`failed`. The hook's imports stay function-level, exactly like
`load_engine`'s existing lazy `from lawcast_semantic import ...`, so
`import service.app` still pulls no faiss/torch (`incremental` imports
`.indexing` → faiss at module level; the light-import property is what
`tests/test_service.py` relies on). Even when a cycle runs, plan/load gates
still refuse model-mismatched sets (07-tested) — validation remains the
final arbiter.

### 6.2 Rollback stance

- **Automatic rollback = the un-swapped generation.** The serving process only
  ever exposes a generation after it passed `SemanticSearcher.load`; a failed
  swap is a no-op (§5.2.4). Disk state either validates (serves it next boot)
  or self-repairs via the boot/next-tick cycle (§6.1) — the convergent
  property 07 verified.
- **No automatic multi-generation file backup**: keeping a previous full set
  would double ≈850 MB of writes per tick (≈20 GB/day at 60 min) for a
  rollback scenario that (a) cannot be detected mechanically (a loadable but
  worse index is a quality question, not a validity one) and (b) already has
  manual paths: rebuild `01→03`, `artifacts/backup-sample-300/`, and the
  host pipeline (README 교체 규칙).
- **Manual emergency run** (runbook, E4): on the production Linux host,
  `flock semantic-search/artifacts/.update.lock python scripts/06_incremental_update.py --db ...`
  then `POST /reload` — same lock the runner takes (`fcntl.flock` in Python),
  so manual and scheduled runs cannot interleave. On host dev the scheduler is
  disabled by default (empty `DB_PATH`) and no lock is needed. macOS has no
  `flock(1)` — disable the scheduler (unset `DB_PATH`) before a manual host
  run there.

## 7. File-level change list (for the implementer)

No backend (NestJS) changes. All semantic-search changes are additive and
config-gated (default off ⇒ existing tests/behavior unchanged).

1. `docker-compose.yml` — `semantic-search`: add `- lawcast_db:/data`,
   `LAWCAST_SEMANTIC_DB_PATH=/data/lawcast.db`, `LAWCAST_SEMANTIC_UPDATE_INTERVAL_MINUTES=60`,
   and (after the §3.2 measurement) `user:` alignment if required.
2. `semantic-search/lawcast_semantic/config.py` — the three env vars of §4.2
   (single-owner convention; empty `DB_PATH` ⇒ disabled).
3. `semantic-search/service/` — new `update_runner.py`: one
   `run_update_cycle(state, embedder) -> result` implementing §2 (guards,
   flock, plan/apply, reload call, result recording) + `start_scheduler(state)`
   loop (§4.2) + `run_boot_repair(embedder, db_path) -> bool` (the §6.1
   cycle with the `needs_embedding is False` scope guard; returns whether a
   set was repaired). **Function-level imports only** — `incremental` pulls
   faiss at module level and `import service.app` must stay light (§6.1).
4. `semantic-search/service/app.py` — `EngineState`: `loaded_fingerprint`,
   `generation`, `reloadError`, update-result fields; `reload()` per §5.2;
   lifespan starts the scheduler thread when configured; `POST /reload`
   (409 unless `status == 'ready'`); `GET /health` adds the §5.2 fields;
   **restructure `load_engine` into embedder-phase and searcher-phase
   `try/except`** — the boot-repair hook hangs on the **searcher phase only**
   and calls `update_runner.run_boot_repair` (function-level import) when
   `DB_PATH` is configured, per the §6.1 discrimination rule.
5. `semantic-search/tests/` — new `test_update_runner.py` (fake
   plan/apply: single-flight skip, shrink guard, fingerprint self-heal,
   disabled-by-default, boot repair path) and additions to `test_service.py`
   (reload swap keeps `ready`, failed reload keeps old searcher, `POST /reload`
   codes, health fields).
6. Docs — semantic-search README: env table, schedule, `POST /reload`,
   flock rule for host runs; plan.md B2/B3: "designed (this doc), implementation
   pending" + uid-measurement runbook; this file stays the design owner.

## 8. Verification plan (implementer's definition of done)

1. Suites stay green: `pytest -q` (72 + new), `ruff check`/`format`, backend
   `tsc --noEmit` + full `npm test` (should be untouched), contract spec.
2. Mount check: §3.2 uid measurement on a live compose stack; in-container
   `load_notices_from_db` returns 20,919+ rows; `--plan-only` JSON sane
   (plan.md's live baseline: 96,757 chunks).
3. Freshness end-to-end: dev stack with `UPDATE_INTERVAL_MINUTES=2`; insert a
   synthetic notice into a **DB clone** (guard triggers respected — clone-only,
   as in 07 V2b); assert: tick reports `changed`, `generation` increments,
   `/health.status` observed `ready` **at every poll during the swap**, marker
   notice becomes a top `/search` hit.
4. Continuity under load: concurrent query loop during a tick with embedding —
   no 5xx, no `loading`, latency tail bounded (§5.4).
5. Kill test: `docker kill` mid-apply → restart → boot repair → `ready`,
   `indexedChunks` matches `chunks.jsonl`, search parity with pre-kill baseline
   (07 V2b-style marker queries).
6. Guard test: point `DB_PATH` at an empty/foreign DB clone → refusal logged,
   `lastUpdateResult='failed'`, serving and artifacts byte-identical.
7. Disable-by-default: compose-less `uvicorn service.app:app` behaves exactly
   as today (no thread, no env, no `/reload` side effects on readiness).

## 9. Risks & constraints (honest list)

- **Memory**: steady ≈ model 2.2 GB + index ~400 MB; a tick adds ~1.2-1.5 GB
  transient (npz load + merged matrix + new index before swap). compose has no
  memory limits today — keep it that way or set ≥6 GB if a limit is added.
- **CPU during embed**: ~21.5 chunks/s (measured) — a 100-chunk change is
  ~5 s of contention; bounded by batch-lock design (§5.4).
- **Same-host only** (M1): recorded reversal trigger → M2 if split.
- **UID alignment** is deploy-time measurement, not assumption (§3.2); the
  artifacts-dir ownership side effect on Linux is the known plan.md pitfall,
  resolved by the same alignment.
- **Quality regressions are out of mechanical scope**: load validation proves
  consistency, not relevance; 07's eval-gate procedure stays the manual check
  for risky corpus/model changes.
- **Fleet note**: `/health` gains fields — additive only; the compose
  healthcheck and backend contract consumers read `status`/`/search` shapes
  only (pinned by the contract spec), so nothing breaks.
