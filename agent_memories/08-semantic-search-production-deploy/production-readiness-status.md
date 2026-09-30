# Semantic Search Production-Readiness Status (measured 2026-10-01)

Three-axis status of the semantic-search stack — ① engine implementation,
② Docker environment, ③ backend/frontend — plus the remaining work to
production-ready, each item with **why it remains** and a **completion
criterion**. Supersedes the stale "implementation pending" markers in
`plan.md` §3.B items 2–4. Cross-referenced against `../07-incremental-indexing/plan.md`,
`plan.md` (this folder) and `incremental-update-pipeline-design.md`.

**Method**: every claim below was re-measured in this session (containers,
HTTP endpoints, git state, test suite) or explicitly attributed to a prior
measured run. Section 5 separates verified from unverified.

---

## 1. Verification basis (measured 2026-10-01)

| Check | Result |
| ----- | ------ |
| `pytest tests/ -q` (semantic-search) | **110 passed** (84 pre-existing + 21 update-runner contract + config/entrypoint) |
| `ruff check` + `ruff format --check` | **clean** (33 files) |
| `docker compose config -q` | **passes** with `user: 1001:1001` + `lawcast_db:/data` + three gates rendered |
| Live sidecar `lawcast-semantic-search` | `Up (healthy)`, `/health` = `ready`, generation 1, `indexedChunks 96757` (matches design baseline 96,757) |
| Live container identity/mounts/env | `user=1001:1001`; mounts = artifacts bind + `lawcast_lawcast_db -> /data` + `lawcast_lawcast_semantic_hf_cache -> /cache`; env = `DB_PATH=/data/lawcast.db`, `INTERVAL_MINUTES=60`, `ALLOW_LARGE_DELETE=false` |
| Live `/search` | 200, model `nlpai-lab/KURE-v1`, ranked hits (both before and during the in-container tick) |
| Live `POST /reload` | **HTTP 409** `an index update is already in progress` — the cross-process flock single-flight boundary working live (probe tick held `.update.lock`) |
| In-container DB read as uid 1001 | `mode=ro` query OK: **19,997 notices**; SQLite created `lawcast.db-shm` `-wal` 1001-owned (same uid as backend data files) |
| In-container `plan_update` (read-only probe) | load 4.0 s + plan **2.1 s**: `added=0 deleted=923 updated=6760 embed_records=19644`, shrink guard **passes** (923 > 100 but ≤ 20%) |
| Bare-metal `plan_update` A/B | load 2.8 s + plan **1.9 s** against live host DB (20,960 rows) — plan code itself is seconds-fast |
| In-container scheduled tick (INTERVAL=1 probe, scratch artifacts) | fired; py-spy stack proves the full production path `update_runner._apply -> apply_update -> embed_texts -> XLM-R forward`; ~63 min CPU at 100 % of one core, **completion not yet observed** (see §5.1) |
| Host uvicorn scratch-DB run (prior pass) | full success path exercised end-to-end: tick `changed`, chunks 96,757 → 96,825, marker notice top `/search` hit (0.782), `POST /reload` 200 gen 2 → 3 |
| Query during in-container embed burst | `/search` answered in **0.89 s** while the tick held the lock and embedded (single sample, not a load test) |
| Backend/frontend git state | both on feature branches with **uncommitted** changes (§4) — untouched by this pipeline work |
| CI (`.github/workflows/ci.yml`) | backend + frontend only; **no workflow runs the semantic-search python suite** |

---

## 2. Axis ① — Engine implementation status

### 2.1 Done (with evidence)

| Design source | Item | Status |
| ------------- | ---- | ------ |
| `../07-incremental-indexing/plan.md` §6 | Incremental plan/apply, per-chunk digests, atomic write order, full-rebuild equivalence (V1/V2/V2b/V3/V4), live `06` run | **Done, verified** (07 plan §6: byte-identical outputs, search parity, crash repair) |
| design §7.2 | `lawcast_semantic/config.py` three env gates (`DB_PATH` empty = off, `INTERVAL=0` = off, `ALLOW_LARGE_DELETE` spelling set) | **Done** — `tests/test_config.py` (fresh-interpreter, 7 cases) |
| design §7.3 | `service/update_runner.py`: `_update_lock` flock, `_plan_for`, `_shrink_refused` (20 % AND >100), `_apply`, `_disk_fingerprint` §5.3 self-heal, `run_boot_repair` §6.1, `run_update_cycle`, `start_scheduler` (±10 % jitter, ready-gated, failed stops) | **Done** — contract tests pin every branch (shrink matrix, skip/failure outcomes, scheduler gates, boot-repair approve/refuse) |
| design §5.2/§7.4 | `EngineState` generation/`loaded_fingerprint`/`reloadError`/`lastUpdate*`, `reload()` load–validate–swap keeping `ready`, phase-split `load_engine` (searcher-phase repair hook only), lifespan scheduler thread, `/health` additive fields | **Done** — swap/rollback/self-heal tests + live `/health` fields observed |
| design §5.2.1 | `POST /reload` reusing the scheduler's swap path (409 not-ready / 409 in-flight / 503 failed-validation) | **Done** — 5 endpoint contract tests + **live 409** observed this session |
| design §7.1 | compose wiring: `lawcast_db:/data` rw (WAL `-shm`), three gates, `user:` alignment after §3.2 measurement | **Done** — see axis ② |

### 2.2 Verified live vs unit-only

- **Live-verified**: boot → ready (gen 1, 96,757), `/search`, `/health` additive
  fields, `POST /reload` 409 boundary, volume DB read + `-shm` creation as
  uid 1001, scheduler tick reaching `embed_texts` with real plan numbers,
  readiness held during the tick (0.89 s query), full success path on a host
  run (`changed`, generation bump, marker hit).
- **Unit/contract-only (no live run yet)**: boot-repair after a mid-apply
  kill, shrink-guard refusal on the live stack, disable-by-default bare
  `uvicorn`, concurrent-query latency tail under an embed burst (§8.4),
  tick completion (`apply` write → `reload` → `changed`) inside a container.

---

## 3. Axis ② — Docker environment status

### 3.1 In place and live-verified

- Image stack from `plan.md` §3.A: `Dockerfile` (CPU-only torch, `requirements.lock`,
  non-root `semantic` user), `.dockerignore`, compose service, loopback
  publish, HF-cache named volume, artifacts bind, healthcheck failing only on
  `failed`, backend `SEMANTIC_SEARCH_API_URL` override.
- **§3.2 uid alignment applied (rung 1, design-primary)**: `user: "1001:1001"`
  on `semantic-search`, chosen after measurement:
  - volume `/data` = uid **1001** 755 → old uid 100 got `EACCES` creating
    `lawcast.db-shm` → every query failed `attempt to write a readonly
    database` (WAL requires `-shm` write even for `mode=ro`);
  - **OrbStack bind mounts present as the container's own uid** (macOS
    501-owned artifacts appear as the running user) → artifacts bind writes
    keep working for 1001 (create + append to 644 both measured);
  - backend data files are **1001-owned** → sidecar and backend now share one
    uid, which is the only configuration where a WAL `-shm` created by either
    side stays writable for both;
  - **measured trade-off**: HF-cache volume stays 100-owned → under 1001 the
    model loads **read-only** (verified: ready in ~16 s) but a re-download
    would fail; mitigation recorded in the compose comment (one-off
    `docker run --user 100` maintenance container).
- Ladder rung 2 (`chmod`/`setfacl` on the volume dir) was deliberately **not**
  needed and would be worse: `777` + mixed-uid `-shm` files cannot keep both
  producers working without same-uid alignment.

### 3.2 Residual data/ops facts (not code gaps)

- **Stale volume DB**: `lawcast_lawcast_db` holds the **2026-08-10** snapshot
  (19,997 notices) while the live host DB is 2026-09-30 (20,960). Every tick
  against it plans `6,760` edited notices / `19,644` chunks to re-embed —
  measured ~60+ min single-core in the container. Production needs a freshness
  policy for the shared volume (§5.4).
- Same-host only (M1), not NFS-safe; Linux hosts need the plan.md pitfall
  treatment (bind written as container uid → one-time artifacts ownership
  fix) — **not re-measured outside OrbStack**.
- Scratch state left by this session (safe to clean): containers
  `lawcast-semantic-search` (keep — the deployment), `lawcast-tick-probe`
  (in-flight tick); dirs `/tmp/lawcast-uidfix`, `/tmp/lawcast-semantic-demo`.

---

## 4. Axis ③ — Backend / frontend status

### Backend — functionally done for this pipeline, hygiene open

- `backend/src/modules/semantic-search/` on branch
  **`feat/semantic-search-integration`**: controller + service + k-fill
  widening policy + `semantic-search.constants.ts` + cross-language
  `semantic-search.contract.spec.ts` (pinned field-by-field against the
  Python sidecar; runs in root CI). All measured in `plan.md` §4.
- **This pipeline work changed zero backend files** (design §7 promise kept).
- **Open**: the working tree is **uncommitted** — 4 modified files plus
  untracked `semantic-search.constants.ts` / `semantic-search.contract.spec.ts`
  (`git status` measured this session). Ownership of that WIP predates this
  session; it must land via PR before CI protects it.

### Frontend — UI exists (correction), merge/gating open

- **Correction to the "no consumer UI" premise**: a semantic-search UI **does
  exist** on branch **`feat/semantic-search-ui`** —
  `frontend/src/routes/notices/semantic-search/` (+page.server/+page),
  `src/lib/utils/semantic-search.ts`, api-client/types wiring, and
  `e2e/semantic-search.spec.ts`, feature-gated by
  `PUBLIC_SEMANTIC_SEARCH_ENABLED` (redirect to `/notices` when off).
- **Open**: 5 files modified/uncommitted on that branch; the flag is off by
  default; the UI does **not** surface pipeline status (no generation /
  `lastUpdateResult` from the sidecar's `/health`).

### CI gap

- Root `ci.yml` covers backend (incl. the contract spec) and frontend.
  **Nothing runs `semantic-search`'s 110 pytest cases or ruff** — a regression
  in `service/update_runner.py`/`app.py` would merge green today.

---

## 5. Remaining work to production-ready (reason → completion criterion)

| # | Work | Why it remains | Completion criterion | Priority |
| - | ---- | -------------- | -------------------- | -------- |
| 5.1 | **Observe in-container tick completion** | The INTERVAL=1 probe is mid-embed (~63 min CPU, py-spy proven); apply→reload→`changed` not yet seen inside a container | probe `/health` shows `lastUpdateResult='changed'` + generation 2 + scratch index equals a full-rebuild of the volume corpus + query parity; probe then removed | **HIGH** (last unverified link of design §8.3) |
| 5.2 | **§5.4 embed-burst latency policy** | 19,644-chunk burst ran 60+ min at 100 % of one core; batching exists (`EMBED_BATCH_SIZE=32`) but the designed per-batch lock is **not wired**; only a single 0.89 s query sample was taken | either implement §5.4 per-batch release **or** run design §8.4 (concurrent query loop during a tick, no 5xx, bounded p99) and amend §5.4 with the measured numbers; pin with a test or a recorded runbook | **HIGH** |
| 5.3 | **Stale volume DB freshness policy** | Aug-10 snapshot makes every production tick a 6,760-notice re-embed (§3.2) — slow, and deletes 923 newer notices from artifacts when applied | documented + executed refresh step for `lawcast_db` (compose backend current, or snapshot copy); then a measured steady-state tick on a fresh volume (`unchanged` or seconds-scale `changed`) | **HIGH** (data ops, not code) |
| 5.4 | **§8 residual live checks**: kill test mid-apply → boot repair; guard-refusal on the live stack; bare no-env run; §8.4 load loop | all covered by unit tests but never executed on the real stack (design §8 items 5, 6, 7, 4) | each scenario run once against a scratch clone with recorded `/health`/logs, as design §8 defines | MEDIUM |
| 5.5 | **Frontend**: commit + PR `feat/semantic-search-ui`, decide flag default, optionally show pipeline status | UI uncommitted and flag-gated → users cannot reach semantic search | merged PR, flag policy decided, e2e green in CI | MEDIUM |
| 5.6 | **Backend**: commit + PR the `feat/semantic-search-integration` working tree | contract-pinning tests exist only in an uncommitted tree | merged PR; CI green on `main` | MEDIUM |
| 5.7 | **CI for semantic-search** (pytest + ruff) | 110 tests + ruff are run manually only (§4) | workflow job running `.venv/bin/python -m pytest tests/ -q` + ruff on `semantic-search/**` PRs, green once | MEDIUM |
| 5.8 | **§3.2 runbook** | measurement done this session (§1/§3.1) but not written up as the deploy runbook design §8.2 asks for | runbook section (commands + measured numbers + ladder decision) in README/design; plan.md pitfall cross-linked | LOW |
| 5.9 | **Index bootstrap runbook** (`plan.md` B1) | image ships code-only; artifacts are gitignored | documented host-build → `./semantic-search/artifacts` sync executed once on the server | LOW (independent) |
| 5.10 | **Full-corpus eval relabeling** + optional hardening (`plan.md` B5/B6) | holdout labels are 300-sample; readiness detail/provenance not done | new labels recorded; hardening items decided individually | LOW |

---

## 6. Known unverified / environment caveats

- Linux-host bind ownership under `user: 1001:1001` (OrbStack's per-container
  uid presentation does not generalize) — measure before a non-macOS deploy.
- Compose **backend** container is not running in this environment; backend↔sidecar
  service-DNS was verified 2026-09-30 (`plan.md` §4) but not re-run this session.
- Probe tick completion (5.1) and any p99 latency claim beyond the single
  0.89 s sample remain open.
