# Semantic Search Latency Optimization (Round 1)

## Problem

After the hybrid lexical gate + cross-encoder rerank rollout, semantic search
felt much slower. Breakdown (from session 42 bake-off numbers + code paths):

- Dense (KURE-v1 embed on CPU + FAISS exact over ~118k chunks): ~0.3-0.7s
- Lexical annotation (regex per hit): milliseconds
- **Rerank shadow (nano 149M, top-20, max_length=512, CPU, single-thread OMP): ~0.9-1.9s**
- Backend hydration (archive + change counts): extra sequential latency

The rerank pass runs synchronously inside `GET /search`, even in shadow mode
(log-only) and even when the backend never consumes the scores.

## Changes (this session, uncommitted)

All defaults preserve current behavior; activation is env-only.

1. `semantic-search/lawcast_semantic/config.py`: new `RERANK_MAX_LENGTH`
   (`LAWCAST_SEMANTIC_RERANK_MAX_LENGTH`, default 512, fail-fast below 1).
2. `semantic-search/lawcast_semantic/reranking.py`: `load_reranker` takes
   `max_length` (default from config) instead of hardcoded 512.
3. `semantic-search/service/app.py`:
   - `GET /search` gains optional `rerank: bool | None` (None = legacy:
     score whenever the scorer is loaded; false = skip scoring).
   - One `search-timing` INFO line per request
     (`dense_ms / annotate_ms / rerank_ms / total_ms / rerank=scored|skipped`).
   - `rerank-shadow` log line gains `rerank_ms` (existing `n=`/`top1=`
     substrings kept for current tests).
4. `backend/src/modules/semantic-search/semantic-search.service.ts`:
   `fetchChunks` sends `rerank: this.rerankCutoff !== null`, so the sidecar
   skips its ~1s CPU pass exactly when the logits are never consumed.
   Old sidecars ignore the unknown param (fail-open).
5. Tests: backend spec exact-params assertion updated + new opt-in/opt-out
   test; sidecar `rerank=false` skip test; config defaults/override/floor
   tests; reranker source-wiring assertion extended.
6. `semantic-search/.env.example`: documents `RERANK_MAX_LENGTH`.

## Follow-up session (2026-10-16, shell-capable): measured + shipped as v2.6.1

Local gates (all green): `ruff check` + `ruff format --check` (2 files needed
reformat: `config.py`, `service/app.py`), pytest 339 passed, backend
`tsc --noEmit` clean, `npm run lint` clean, semantic jest 5 suites / 73 tests.

Local A/B (Apple Silicon, 118,711 chunks, single-thread OMP): dense ~100ms;
rerank top-5 window 293-1109ms (first query = warmup), top-15 window
~850-970ms; `max_length` 512 vs 256 identical latency AND identical scores
(max abs drift 0.000000 on 3 probes) — inputs are <=200 chars so both fit
under 256 tokens and batch padding dominates. `rerank=false` skip = 0ms.
Conclusion: the skip is the real optimization; 256 buys nothing locally and
was NOT activated (env default stays 512).

Prod findings (10.20.0.1, project dir is lowercase `~/lawcast`): sidecar runs
`RERANK_MODE=shadow` (container env, not the `.env` file) and backend
`SEMANTIC_SEARCH_RERANK_CUTOFF=-1` + `LEXICAL_GATE=enforce`, so every prod
request pays the full shadow pass — the skip only helps when the cutoff is
null. Pre-deploy baseline: ~7.6s per `GET /search k=15` (3 consecutive).

Shipped: semantic-search v2.6.1 (branch `release/v2.6.1-rerank-opt`, PR #14
squash-merged, tag + Release `semantic-search-v2.6.1`), root pointer bump
pushed, `./deploy.sh semantic-search` rebuilt on prod (healthy, 117,986
chunks). Backend `rerank` param change deliberately NOT shipped (its tree
holds unrelated uncommitted admin-notices work from session 43; prod cutoff
-1 means it would send `rerank=true` = no behavior change anyway).

Prod breakdown via the new `search-timing` log (steady state, k=15):
`dense_ms~1010-1028 / annotate_ms~2.5 / rerank_ms~6855-7010 / total~7.9-8.0s`
(first request after deploy: dense 3548 / rerank 7853 / total 11.4s — warmup).
Rerank is ~87% of serving latency.

## Prod thread-tuning experiment (2026-10-16, same session)

Root cause of single-threadedness: `omp_env.use_single_threaded_omp()`
forces `OMP_NUM_THREADS=1` to dodge a macOS-only torch+faiss libomp crash;
on prod Linux (no CPU limit, 4 shared vCPU) it needlessly caps FAISS/OpenMP
while torch intra/inter-op already run at 2. `setdefault` semantics mean a
pre-set `OMP_NUM_THREADS` is respected — env-only, no code change.

Method: 10-query probe set (8 valid + vague `돈 관련 법` + noise
`asdfghjkl`, k=15) saved to `/tmp/probe_{baseline,omp2,omp4}.json` on prod;
latency via client timing + `search-timing` logs, quality via top-5 noticeNum
rank equality. Prod-local config only (`semantic-search/.env` is gitignored
+ untracked; original saved to `/tmp/ss_env.orig`).

| setting | avg client | rerank_ms | dense_ms | rank diffs |
| ------- | ---------- | --------- | -------- | ---------- |
| unset (=1) | 7508ms | ~6855-7010 | ~1010-1028 | — |
| `OMP_NUM_THREADS=2` | 5235ms (−30%) | ~3081-5594 | ~685-1195 | 1/10 |
| `OMP_NUM_THREADS=4` | 5061ms (−33%) | ~3107-5128 | ~705-1393 | 1/10 |

The single rank diff (`돈 관련 법`) is a 4-way exact score tie at 0.5787
whose order flips with thread count — top-1 identical everywhere, `asdfghjkl`
empty everywhere. Benign tie-order noise, not a regression.

Decision: **kept `OMP_NUM_THREADS=2`** (appended to prod `.env`, container
recreated, healthy re-verified). OMP=4 gains only ~170ms more but pushed host
load 2.5 → 4.1 on 4 shared cores (ollama/gatekeeper/backend are neighbors).
Not committed anywhere (prod `.env` is gitignored by design); to reproduce:
add `OMP_NUM_THREADS=2` to `semantic-search/.env` and recreate.
Remaining wall: rerank still ~70% even threaded.

## Next-pass analysis (2026-10-16): RERANK_TOP_K reduction selected

Serving order is dense-only (rerank gates, never reorders), so dense-side
work is bounded small — measured locally (single-thread): embed 34ms /
FAISS-full 22ms / Python 118k-sort 33ms. The Python full sort is pure waste
(`VectorIndex.search` always scans ntotal then `hits.sort` in Python;
FAISS top-(k+64) + `np.lexsort` reproduces full-sort order 6/6 probes) but
saves only ~0.3s prod (~6%) — bundle it with the release below, not a pass
of its own. Backend hydration is negligible (backend e2e k=5 ~4.5-4.7s ≈
sidecar time for the same window; no hydration lever).

Ranked candidates:

1. **RERANK_TOP_K 20 → 10 (+ calibration) — REJECTED 2026-10-16.**
   Calibrated with tracked probe set (`08 --k 20` → 54 windows, then `09
   --rk 20 vs 10` at prod cutoff −1.0, bypass 0.6): unrelated emptied
   **30/40 → 13/40**, control 8/8 both, vague 5/6 vs 3/6. Ranks 11–20
   unscored fall back to the lexical rule and generic tokens match, so the
   noise gate collapses. Do NOT ship without a gate redesign. (Labeled
   family n=0 in the tracked set — session 42's 40-labeled files were
   host-local and are gone; control 8/8 held.)
2b. **Vectorized 118k sort — REJECTED 2026-10-16.** `np.lexsort` over
   (-score, chunk_id) is exactly equivalent (verified: same-vector repeat
   identical, equals Python-sort-of-same-call) but measures **32ms vs 33ms
   for the Python comparator sort** — numpy string sorts are slow, no gain.
   Bounded-heap variant (FAISS top-79 = 12.7ms vs full 20.8ms) would save
   only ~40ms/query (~8% of prod total) while adding a tie-span fallback
   invariant — below the ship bar, not implemented. Incidental finding:
   FAISS scores wobble ~1e-7 between identical calls (nondeterministic
   reduction), so near-tie order flips run-to-run even today (explains the
   prod `돈 관련 법` tie flip). `CrossEncoder.predict` is already
   single-call batched — no batching win left.
2. FAISS top-(k+margin) + lexsort (code, exact on probes): ~-0.3s. Ship in
   the same release as (1).
3. Conditional rerank skip (already coded; needs backend release +
   `SEMANTIC_SEARCH_RERANK_CUTOFF=null`): −3.5s but noise rejection falls
   5/5 → 1/5 per calibration. Product decision — parked, not a perf pass.
4. Rejected for now: int8 embed (small share, quality risk), uvicorn
   workers (RAM-tight: 7GB host, models ~2.5GB × N), query cache
   (freshness semantics), IVF index (rebuild + recall risk for ~22ms gain).

## Quantization A/B (2026-10-16): ONNX dynamic INT8, conditional go

Web research (agent): KURE-nano 149M already the smallest verified Korean
reranker (nDCG 0.8757); smaller alts are bigger or Korean-unknown (mMiniLM
117M has no Korean in training langs — not tested, strictly worse bet).
Supported path: ST `CrossEncoder(backend="onnx")` +
`export_dynamic_quantized_onnx_model` (needs `optimum[onnxruntime]`; the
bare `optimum` package is NOT enough — `optimum.onnxruntime` import is what
ST checks). Exported locally (arm64 config): 151MB INT8 artifact. The
export dir lacks config/tokenizer — copy them from the HF snapshot for
`CrossEncoder(local_dir, backend="onnx")` to load.

Local A/B (arm64, single-thread, n=15 pairs, warmed, min-of-3): torch FP32
782–909ms vs INT8 483–561ms → **~1.6x (~35–40% off rerank)**. Projected
prod: rerank ~3.5–4s → ~2.2–2.5s, total ~5.2s → ~3.7–4.0s.

Parity (54 probe windows, backend enforce rule): max abs drift 0.61,
gate agreement 48/54 at cutoff −1.0 (incl. one valid-control false-reject
`해외직구 관세`). Cutoff sweep on INT8 scores: −1.2 gives 28/40 | 8/8 |
3/6 vs torch@−1.0 30/40 | 8/8 | 3/6 — control fixed, but 2 unrelated leak.
Drift is non-uniform so no cutoff reproduces exactly.

Verdict: CONDITIONAL GO, not shipped. Ship cost is sizable (onnxruntime in
image, 151MB artifact plumbing, loader branch, cutoff −1.2, and mandatory
x86/avx2 verification since arm64 numbers don't transfer). Needs owner
decision: −30% latency vs 2/40 noise leak + release complexity. Experiment
left no repo pollution (onnx/optimum installed in .venv only — gitignored;
artifacts in /tmp).

Next options in order: (a) skip scoring
when the backend leg is off (already coded, needs backend release + cutoff
null decision); (b) lower RERANK_TOP_K 20 (linear cost); (c) threads/quantized
reranker; dense itself (~1s) is the next wall after rerank is gone.

## Next steps for a shell-capable session

1. `cd semantic-search && .venv/bin/ruff check . && .venv/bin/ruff format --check .`
2. `cd semantic-search && .venv/bin/python -m pytest tests/ -q`
3. `cd backend && npm run lint && npx tsc --noEmit && npm test -- --runInBand`
4. Latency A/B: `scripts/04_search.py` or live sidecar before/after
   `LAWCAST_SEMANTIC_RERANK_MAX_LENGTH=256` (shadow), compare `rerank_ms`.
5. Deploy to 10.20.0.1 `~/LawCast`, watch `search-timing` /
   `rerank-shadow ... rerank_ms=` lines, then set
   `LAWCAST_SEMANTIC_RERANK_MAX_LENGTH=256` after calibration shows no
   score drift.
