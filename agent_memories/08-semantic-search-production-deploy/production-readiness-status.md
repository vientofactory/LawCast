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
| Live sidecar `lawcast-semantic-search` | `Up (healthy)`, `/health` = `ready`, generation **2**, `indexedChunks 93031`, `lastUpdateResult='unchanged'`, `lastUpdateError=null` — its own first 60-min tick (started ~18:44 UTC) applied the snapshot plan, artifacts rewritten 2026-09-30 22:15 UTC; 96,757 → 93,031 ≈ the 923 snapshot-missing notices removed (plan `deleted=923`, `added=0`) |
| Live container identity/mounts/env | `user=1001:1001`; mounts = artifacts bind + `lawcast_lawcast_db -> /data` + `lawcast_lawcast_semantic_hf_cache -> /cache`; env = `DB_PATH=/data/lawcast.db`, `INTERVAL_MINUTES=60`, `ALLOW_LARGE_DELETE=false` |
| Live `/search` | 200, model `nlpai-lab/KURE-v1`, ranked hits — before, during, **and after the generation-2 swap** (post-swap probe 18301: 200 in 3.36 s cold / 2.0 s warm; response JSON **byte-identical** to live 8300 for the same query) |
| Live `POST /reload` | **HTTP 409** `an index update is already in progress` — the cross-process flock single-flight boundary working live (probe tick held `.update.lock`) |
| In-container DB read as uid 1001 | `mode=ro` query OK: **19,997 notices**; SQLite created `lawcast.db-shm` `-wal` 1001-owned (same uid as backend data files) |
| In-container `plan_update` (read-only probe) | load 4.0 s + plan **2.1 s**: `added=0 deleted=923 updated=6760 embed_records=19644`, shrink guard **passes** (923 > 100 but ≤ 20%) |
| Bare-metal `plan_update` A/B | load 2.8 s + plan **1.9 s** against live host DB (20,960 rows) — plan code itself is seconds-fast |
| In-container scheduled tick (INTERVAL=1 probe, scratch artifacts) | **completed** — apply wrote the full artifact set at 2026-09-30 21:21 UTC (Oct 1 06:21 KST), reload bumped generation 1 → 2, subsequent ticks report `unchanged` / `lastUpdateError=null`; total ~228 min CPU single-core (1,370,392 utime ticks; post-completion idle ≈0.4 % CPU); py-spy had proven the `update_runner._apply -> apply_update -> embed_texts` path mid-run |
| Probe scratch vs live artifacts | md5 **identical** on all four files (`chunks.jsonl 138e8b15…`, `embeddings.npz c4f818e7…`, `faiss.index 57ab320e…`, `id_map.json c8830b85…`) — both containers independently applied the same plan to the same DB; `chunks_fingerprint bd04841a…`, 93,031 rows = `wc -l chunks.jsonl` = `/health.indexedChunks` |
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
  run (`changed`, generation bump, marker hit), and the design §8.4
  concurrent-query loop under a real embed tick (§5.2: 336/336 200 across a
  223.6 s burst, p99 631 ms, never `loading`).
- **Unit/contract-only (no live run yet)**: boot-repair after a mid-apply
  kill, shrink-guard refusal on the live stack, disable-by-default bare
  `uvicorn`, tick completion (`apply` write → `reload` → `changed`) inside a container.

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
| 5.1 | **Observe in-container tick completion** — **DONE (2026-10-01)** | was the last unverified link of design §8.3; now observed: apply wrote all four artifacts 2026-09-30 21:21 UTC → reload generation 1 → 2 → follow-up ticks `unchanged` / `lastUpdateError=null` (1,370,392 utime ticks ≈ 228 min single-core total, idle after); probe scratch artifacts **md5-identical** to the live index; `/search` post-swap 200, response byte-identical to live 8300 | met — note: the applying tick's own `'changed'` value is transient: 1-min ticks overwrite `lastUpdateResult` with `'unchanged'`, so `generation 2` + artifact mtime is the durable evidence | **DONE** (residual LOW: probe container still running — remove when no longer needed) |
| 5.2 | **§5.4 embed-burst latency policy — DONE (2026-10-01, design §8.4 measured live)** | was HIGH: the 19,644-chunk burst ran 60+ min at 100 % of one core; batching (`EMBED_BATCH_SIZE=32`) exists but the designed per-batch lock was never wired; only a single 0.89 s query sample existed | **met via §8.4's measured alternative** (per-batch release not implemented — measurement showed it is not needed; code-free pass, so the pin is this recorded runbook, not a test): isolated probe `lawcast-latency-probe` (prod image, `user 1001:1001`, scratch artifacts md5-identical to live, scratch DB = in-container sqlite `backup()` clone of the `lawcast_db` volume converted to DELETE journal, then 67 cloned notices added — pre-flight `plan_update` pinned **embed=294** chunks exactly, `added=67 deleted=0 updated=0`, pristine baseline all-zero), `INTERVAL=2`; 2-worker query loop (4 rotating Korean queries, `k=5`, host→loopback) + 4 s `/health` polls + 2 s container `/proc/1/stat` CPU sampling (`/tmp/lawcast-latency/{prep_db.py,measure.py,analyze.py}` + `samples/health/cpu.jsonl` evidence, ephemeral /tmp): tick reported `changed` after a **223.6 s** embed+apply+swap burst (273.1 CPU-s = 1.22 cores avg, **1.31 chunks/s wall** — in-container rate vs design §9's 21.5 chunks/s host figure), gen 1 → 2, `indexedChunks` 93,031 → **93,325** (+294 = the exact batch). Latency (ms): control-pre n=80 p50 **330** / p95 350 / p99 547 / max 547; **burst n=192 p50 304** / p95 504 / p99 **631** / max **1,075**; control-post n=64 p50 387 / p99 575. **336/336 HTTP 200** (0 timeouts, 0 5xx), `/health` `ready` at **all 98 polls** (never `loading`), `error`/`reloadError` null, probe logs clean. Budget (§8.4: no 5xx, no `loading`, tail bounded by §5.4's one-batch ≈1.5 s) **met**: burst p99 +84 ms over control, burst p50 statistically unchanged (304 vs 330), worst sample 1.08 s < 1.5 s. Relationship to §5.4: serving never waits on `.update.lock` (p50 flat while the tick held the lock for 224 s), so the unwired per-batch lock release cannot explain query latency — residual risk is CPU contention only, unobservable at this 2-worker/≈0.9 qps scale → no new remaining-work item; re-measure on the target Linux host at deploy (§6) | **DONE** (residual LOW: higher-concurrency load and Linux-host numbers) |
| 5.3 | **Stale volume DB freshness — `결정 필요` (데이터 운영 문제, 코드 아님): 분석 완료 2026-10-01, 실행 미결** | **Ground-truth 규명 (read-only derisk)**: compose production에서는 볼륨 `lawcast_db`가 truth (백엔드 `DATABASE_PATH=/app/data/lawcast.db`가 기록, 사이드카는 같은 볼륨 `mode=ro`)지만 백엔드 컨테이너는 8/10 이후 미기동 → 실제 기록자는 호스트 `backend/lawcast.db`인 **이중 상태**. 볼륨 **19,997행 · migrations 18/30** vs 호스트 **20,973행 · 30** (10/1 재측정; §3.2의 20,960은 9/30 기준). 라이브 인덱스는 8/10 코퍼스 — 첫 틱이 최신 공지 **923건 삭제** (§1) — 그리고 아티팩트가 최신 소스로 재빌드되면 다음 틱이 6,760 edited / 19,644 embeds ≈ **4.1 h** 리임베드 + 923건 재삭제 (19,644 ÷ §5.2 실측 1.31 chunks/s; §1의 228-min 실측 틱과 정합 — 현재 틱이 `unchanged`인 것은 아티팩트가 오래된 볼륨과 일치해서일 뿐) | **후보 비교 → 결정 지점까지 사용자 결정 대기**: **A (권고 1순위)** 호스트→볼륨 일회 시드 (WAL-일관 `VACUUM INTO`, raw cp 금지) 후 compose 백엔드를 유일한 기록자로 전환 — 리스크: 볼륨 마이그레이션 18→30 (사전 백업 필수), 시드 후 틱 1회 ≈4.1 h 리임베드 (서빙 영향 없음 — §5.2 실측), `backend/` 미커밋 WIP로 이미지 빌드 / 완료 기준: 볼륨 행수 = 시드 시점 호스트 (20,973), migrations 30/30, 백엔드 healthy + 행수 증가, 틱 `changed` 1회 후 `unchanged`, 9월 마커 공지 `/search` 히트 · **B** 주기 스냅샷 동기화 (backup API + launchd/cron) — 리스크: 이중 truth 영구화 · 복사 중 WAL 일관성 · 5.25 GB 주기 I/O / 완료 기준: 스케줄 등록 + 행수 패리티 실측 + steady-state 틱 `unchanged` 또는 초 단위 `changed` · **C** 컨테이너 크롤 재수집 — 리스크: 8/10~9/30 공백 재크롤 능력 미확인 (`maxPages` 페이지 정책) / 완료 기준: 행수 패리티 + backfill 크론 소진. **결정 지점 3 (사용자)**: (1) A vs B, (2) 호스트 백엔드 영구 중단 여부, (3) 시드 전 볼륨·아티팩트 백업 승인. **배포 전 임시 완화**: `LAWCAST_SEMANTIC_UPDATE_INTERVAL_MINUTES=0` (§4.2 off-gate) 으로 틱을 끄고 서빙만 배포 → 인덱스 축소 방지 | **HIGH — BLOCKED ON USER DECISION** (data ops, not code) |
| 5.4 | **§8 residual live checks** — kill/crash → boot repair **DONE (2026-10-01, measured)**; §8.4 load loop **DONE (2026-10-01, measured — see 5.2)**; still open: literal mid-apply kill, guard-refusal (foreign DB), bare no-env run | boot-repair was unit-only until this session; the remaining scenarios still are (design §8 item 5 partial — corruption-restart done, embed-window kill not — plus items 6, 7) | **met for boot repair**: isolated probe `lawcast-boot-probe` (prod image, `user 1001:1001`, scratch artifacts clone md5-identical to live, `DB_PATH=/data/lawcast.db`, `INTERVAL=0` so no tick could mask the result, port 18301) measured: ① clean boot → `loading→ready` **15 s**, gen **1**, `indexedChunks 93031`, artifact md5 4/4 unchanged; ② `docker kill` + restart → ready **11 s**, same set, md5 unchanged; ③ torn set (`chunks.jsonl` cut to 92,031 parseable lines against the intact npz) → phase-2 load fails → `run_boot_repair` **approved** → ready **23 s** (vs 11–15 s clean: plan+800 MB rewrite, 0 embeds — a 1,000-row re-embed would be minutes), `chunks.jsonl` restored to 93,031 lines, **all four md5 byte-identical** to pre-corruption, `lastUpdate*` null (repair writes no tick fields), gen 1; ④ all four deleted → phase-2 `FileNotFoundError` → repair **refused** (`needs_embedding`, no baseline) → `failed` **10 s**, error surfaced in `/health.error`, artifacts dir left with only `.update.lock` (nothing resurrected); ⑤ restore → ready **18 s**, `GET /search` 200 and **byte-identical** to live 8300; mid-line byte-truncation also measured — see §6 caveat | MEDIUM (boot-repair portion **DONE**; residual = literal mid-apply kill + §8 items 6/7) |
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
- ~~Probe tick completion (5.1)~~ — observed 2026-10-01 (§1/§5.1); the p99
  claim is now measured too (§5.2: **631 ms** burst p99 vs 547 ms control p99
  over 336 queries, 0 5xx, 98/98 `ready` polls). Still open: latency at
  higher concurrency than the 2-worker ≈0.9 qps loop, and re-measure on the
  target Linux host; the 0.89 s mid-tick sample and the two post-swap samples
  (3.36 s cold / 2.0 s warm) remain the historical cold-start references.
- `lastUpdateResult` is last-tick-wins: with a 1-min interval the applying
  tick's `'changed'` is overwritten by subsequent `'unchanged'` within a
  minute — do not rely on polling `/health` alone to catch `'changed'`;
  `generation` increments and artifact mtimes are the durable markers.
- `generation` is in-memory per process: every fresh boot serves generation
  **1** no matter how many swaps the previous process performed (the live
  sidecar's `2` came from a runtime swap). Restart continuity is evidenced by
  byte-identical artifacts (md5 4/4) and byte-identical `/search` responses,
  not by the generation number.
- **Boot-repair approve/refuse live-verified 2026-10-01 (§5.4) with one
  measured asymmetry** — a **deleted** `chunks.jsonl` plans from the npz
  digests (0 embeds) and is approved/rebuilt (ready in 23 s), while a
  **byte-truncated (mid-line unparseable)** `chunks.jsonl` fails inside
  `plan_update`'s `load_chunks_jsonl` *before* the `needs_embedding` gate:
  `load_engine` contains the exception and boots `failed` with
  `JSONDecodeError: Unterminated string…; boot repair failed:
  JSONDecodeError: …` in `/health.error`, all other artifacts untouched.
  **Fail-closed, not self-healing**: a reboot (or a scheduler tick — the same
  planner raises) never repairs this state; recovery is operator restore
  (§6.2). Unreachable via an app crash (writes are temp+rename, so a crash
  leaves `chunks.jsonl` old-complete or new-complete — only external
  corruption hits it), but it does narrow design §6.1's "self-repairs via the
  boot/next-tick cycle" convergence claim to *structurally-torn-or-missing*,
  not *parse-corrupt* — flagged for a follow-up decision (treat unreadable
  chunks as empty in the planner vs keep fail-closed).
