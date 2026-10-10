# Embedding device auto-detection (CPU → CUDA / MPS / XPU)

Request: when the environment running the embedding model supports compute hardware better than
CPU, detect it automatically and use it — instead of the hardcoded `cpu` default.

**Status: implemented and verified (2026-10-10).** Version `semantic-search` 2.3.0 → **2.4.0**.
Commit / PR / release not yet made.

## 0. Test environment — where these numbers come from (and where they do NOT)

Every measurement in this document (including the device A/B in
`13-sidecar-concurrency-audit/`) was produced on **ONE host**:

| | |
| --- | --- |
| OS | **macOS 26.6.2** (Darwin arm64, build 25G83) |
| CPU / RAM | **Apple M4**, 10 cores, 16 GB |
| Accelerator backend | **Apple MPS** (`torch.backends.mps`: built + available) |
| Stack | Python 3.13.5 · torch 2.14.0 · sentence-transformers 6.1.0 · **faiss-cpu** 1.15.1 · numpy 2.5.3 |
| Device modes actually exercised | `auto` → **mps** · explicit **`cpu` pin** · unusable pin (`cuda`, `gpu`) → **cpu fallback + warning** |
| Never exercised on real hardware | **CUDA, XPU** (stub/subprocess simulation + fallback path only), Windows/Linux hosts, the CPU-only Docker image at runtime, multi-GPU |

**Other environments can differ — do not transplant these numbers:**

- **Latencies, speedups (2.98x query / 2.06x batch), concurrency overlap ratios and test
  threshold margins are host-, OS-, torch-build- and load-specific.** Re-measure on the
  target machine before quoting a figure or gating a test on it.
- Vector equality (cosine `1.000000`, `max_abs_delta = 0.000000`) holds **for this stack**;
  another torch build/OS can show small float32 drift between cpu and accelerator output.
  Rankings are practically unaffected (cross-mode checks passed with a 1e-4 tolerance), but
  bit-identical scores across devices must not be assumed everywhere.
- What transfers to other hosts is the **mechanism** (probe → pin → fallback, lock-free
  snapshot serving, latency-ladder queue detection), not the absolute numbers.

## 1. Design — single owner of device resolution

| Concern | Owner |
| ------- | ----- |
| Requested device (`auto` default) | `semantic-search/lawcast_semantic/config.py` → `DEVICE` |
| Probe / pin resolution | **`semantic-search/lawcast_semantic/device.py`** (new) |
| Load + probe + cpu fallback | `semantic-search/lawcast_semantic/embedding.py` → `KoreanEmbedder._load_model` |
| Observability | stage-2 `device` line, sidecar `/health.device` (`EngineState.record_device`) |

- `config.DEVICE` now defaults to **`auto`** (was `cpu`). It stays env-only and import-light —
  **torch is imported lazily inside `resolve_device`**, so the library's light-import contract
  (`tests/test_entrypoints.py::test_package_imports_stay_light`) still holds.
- `resolve_device(requested)`:
  - non-`auto` value → returned as an explicit pin (trimmed + lowercased), **never probed** —
    so `LAWCAST_SEMANTIC_DEVICE=cpu` still forces CPU (the old behavior is one env value away).
  - `auto` / empty / `None` → probe order **`cuda` > `mps` > `xpu` > `cpu`**, each availability
    check isolated in its own try/except so a broken driver degrades to the next candidate with a
    WARNING instead of raising.
- `KoreanEmbedder` records `self.requested_device` and `self.device`, and gates the accelerator
  path with a **probe**: build the model → encode one short text → assert shape `(1, dim)` and
  `np.isfinite`. Any failure on a non-cpu device logs a WARNING and reloads on `cpu`.
  **Why the probe**: a device can construct the model and still fail (or return NaN) on the first
  forward pass; a mid-corpus failure would strand a long stage-2 run halfway through.
- **Device choice never invalidates artifacts**: same model, same vectors (measured below), so
  `embeddings.npz` / `faiss.index` stay valid across a device switch and incremental reuse is safe.

## 2. Measured benefit (this host, Apple Silicon, torch 2.14.0, KURE-v1)

Harness: `semantic-search/_workspace/device_autodetect_bench.py` (gitignored one-off), 96 real
corpus chunks, batch 32, 150 single-query timings, 3 warmup rounds omitted from the median.

| metric | cpu | mps | mps over cpu |
| ------ | --- | --- | ------------- |
| single query median | 96.8 ms | 32.5 ms | **2.98x faster** |
| single query p95 | 122.7 ms | 35.9 ms | 3.4x faster |
| batch throughput | 14.4 chunks/s | 29.6 chunks/s | **2.06x faster** |
| model load (one-time) | 1.0 s | 4.0 s | mps slower to load (background thread) |

**Correctness**: cosine similarity between cpu and mps embeddings of the same query =
`1.000000`, `max_abs_delta = 0.000000` (float32 identical on this stack) → switching devices is
safe for existing artifacts and for shared query/corpus embedding.

Both paths matter here: the sidecar serves single queries (`/search`) and the host pipeline
embeds ~97k chunks in batches (stage 2 / incremental), and **MPS wins both**.

## 3. Where the resolved device is surfaced

- `scripts/02_extract_embeddings.py` prints `device : mps (requested: auto)`.
- Sidecar `GET /health` gained **`device`** (additive field; existing consumers read `status`
  only — backend `SemanticEngineHealthResponse` destructures a fixed subset, so no cross-stack
  contract change was needed). It is stamped by `EngineState.record_device` **right after the
  model phase**, so it is reported even when the artifact phase then fails — model-ok /
  index-missing vs model-failed is the diagnosis an operator needs first.
  **CRITICAL**: the stamp must NOT live in `mark_ready` — `mark_ready` is called without a device
  by stub loaders and by the repair path, so it would erase a correctly recorded value.
- Follow-up (same-day analysis): `embedding-map` `GET /api/status` gained the same **`device`**
  field (`AppState.record_device`, stamped by `server/loader.py` at the model phase) — it loads
  the same model, so a silent cpu fallback there was previously invisible.

## 4. Environment wiring

- `semantic-search/.env` and `.env.example`: `LAWCAST_SEMANTIC_DEVICE=cpu` → **`auto`**
  (`.env` is gitignored but is what this host's scripts/sidecar actually read).
- Root `docker-compose.yml` does **not** set `LAWCAST_SEMANTIC_DEVICE`; it injects
  `semantic-search/.env` via `env_file`, so the container now sees `auto` too.
- **Production container behavior is unchanged**: the Docker image installs the CPU-only torch
  wheel (`Dockerfile`, `download.pytorch.org/whl/cpu`) → probe reports no accelerator → `cpu`.
  A CUDA-capable image/host would pick `cuda` automatically with no config change.

## 5. Tests (why the split)

`semantic-search/tests/test_device.py`:

- **In-process, fake torch** injected via `monkeypatch.setitem(sys.modules, 'torch', ...)`:
  pin honored verbatim (`cpu`/`mps`/`cuda:1`/`CUDA:0`), preference order, empty/`AUTO` spellings,
  torch unimportable → `cpu`, broken cuda probe → skips to `mps`, INFO log of the pick.
  Fake backends are also the only way to assert deterministically on hosts with/without GPUs —
  and importing the **real** torch into the pytest process is deliberately avoided (macOS
  torch+faiss libomp double-init abort, see `tests/retrieval_probe.py` and session 22).
- **Subprocess with a stubbed `SentenceTransformer`** (same isolation style as
  `tests/test_entrypoints.py`): working pin kept, construct-failure → `cpu`, NaN probe → `cpu`,
  `cpu` pin never probes, and one end-to-end `resolve_device('auto')` vs real torch capabilities
  check (runs in a torch-only process, no faiss). Every embedder case pins its device so the
  assertions hold on any host.
- `tests/test_config.py`: default expectation `cpu` → `auto`, plus explicit pin-stays-verbatim
  tests. `tests/test_service.py`: `/health.device` stamped on the ready path and kept on the
  artifact-failure path.

**Verification run (2026-10-10)**: `ruff check .` + `ruff format --check .` clean;
`pytest tests/ -q` → **267 passed, 1 skipped, 1 failed**.

- The failure is **pre-existing and environmental**, not caused by this change:
  `test_real_index_surfaces_every_dropped_clause_within_a_page` fails with
  `faiss::FileIOReader ... could not open .../artifacts/faiss.index: No such file or directory`.
  `artifacts/` currently holds **only `chunks.jsonl`** (mtime 16:41, observed before any test run
  in this session) — `embeddings.npz` / `faiss.index` / `id_map.json` are absent, so
  `test_concurrency.py:218` skips for the same reason. Restoring requires a real pipeline run
  (`scripts/02` → `03`, or `scripts/06_incremental_update.py`); do **not** hand-copy from
  `artifacts/backup-*` (mixed generations are rejected by the fingerprint gate).
- Live checks: stage-2 CLI printed `device : mps (requested: auto)`; a real uvicorn sidecar
  returned `"device":"mps"` from `/health` while reporting `status: failed` for the missing index.

## 6. Known trade-offs / follow-ups

- **MPS costs ~3 s extra model load** (background boot thread, no request impact).
- faiss stays CPU (exact `IndexFlatIP` search over ~97k vectors is sub-millisecond); GPU faiss
  would only matter at much larger scale.
- If a future host needs CPU pinning for reproducibility of published benchmark numbers, set
  `LAWCAST_SEMANTIC_DEVICE=cpu` — `scripts/benchmark_device.py` compares `cpu` against the
  auto-detected accelerator (`resolve_device('auto')`, independent of that pin) and verifies the
  resolved device before timing: `KoreanEmbedder` silently degrades an unavailable accelerator
  to cpu, so timing anyway would publish cpu numbers under the accelerator label (fixed
  2026-10-10; the old hardcoded `('cpu', 'mps')` loop also never covered a cuda/xpu host).
- The Docker image would need a CUDA torch base (and compose `deploy.resources` reservations)
  before `auto` can pick `cuda` in production; the code path is already there.
