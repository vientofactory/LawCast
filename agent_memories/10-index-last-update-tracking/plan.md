# Semantic Index Last-Update Timestamp — Analysis, Design, and Mission Plan

Mission: surface "index last updated" end to end — (1) record the time,
(2) ship it from the sidecar HTTP server, (3) backend -> frontend semantic
search UI. This file is the single source of truth for the analysis and the
design decisions; **all three steps are implemented (2026-10-02)**.

## 1. Analysis: index update paths (as found)

### Where the on-disk index is (re)written

Every artifact writer funnels through **`VectorIndex.save()`**
(`semantic-search/lawcast_semantic/indexing.py`) — the single convergence
point that persists `faiss.index` + `id_map.json`:

| Writer                  | Entry point                                            | Path to `VectorIndex.save`            |
| ----------------------- | ------------------------------------------------------ | ------------------------------------- |
| Host full rebuild       | `scripts/03_build_index.py`                            | direct `index.save(...)`              |
| Host incremental update | `scripts/06_incremental_update.py`                     | `apply_update` -> `_write_artifacts`  |
| Sidecar scheduled tick  | `service/update_runner.run_update_cycle` -> `_tick`    | `_apply` -> `apply_update` (same)     |
| Sidecar boot repair     | `service/update_runner.run_boot_repair`                | `_apply` (same)                       |

### Where the serving generation changes (in-memory swap)

`service/app.py::EngineState` — exactly two methods bump `generation`:

- `mark_ready()` — boot load (including after a successful boot repair)
- `reload()` — tick with changes (`_tick`), fingerprint-mismatch self-heal
  (design §5.3), and `POST /reload` (host pipeline pickup, design §5.2.1)

### What existed before this pass (and its gaps)

`EngineState.record_update()` (called only from `run_update_cycle`) set
`last_update_at = now()` for **every tick** regardless of outcome and
exposed it as `/health.lastUpdateAt`. Gaps:

1. **Not durable** — in-memory only; a sidecar restart reported `null`
   until the next tick (default interval 60 min).
2. **Wrong semantics** — the value was the last *check* time (even for
   `unchanged`/`failed`/`skipped` ticks), not the last index *update*.
3. **Partial coverage** — boot load, boot repair, `POST /reload` (host
   writes via scripts 01->03 or 06) never moved it.

## 2. Step-1 design (implemented)

**Single owner of the time record = `VectorIndex.save()`**, the write-side
convergence point of all four writers:

- `save()` stamps `payload['updated_at'] = datetime.now(UTC).isoformat()`
  into `id_map.json` **after** merging caller meta, so callers cannot fake
  it and every write path records automatically (additive key; legacy sets
  simply lack it).
- `SemanticSearcher.load()` retains it as `searcher.index_updated_at`
  (constructor kwarg, default `None`).
- `EngineState.mark_ready()` / `EngineState.reload()` **adopt** the value
  under the lock — one read-side rule: the serving generation's stamp is
  the reported time. A failed reload keeps the previous generation's time.
- `EngineState.record_update()` no longer touches the time; it owns only
  `lastUpdateResult` / `lastUpdateError` (tick vocabulary).
- External query: `GET /health -> lastUpdateAt` (unchanged field name, now
  durable + semantically "index last updated").

Consequences pinned by tests:

- Restart keeps the value (comes from `id_map.json`, not process memory).
- `unchanged`/`failed` ticks never move it (single ownership).
- `POST /reload` after a host pipeline write reports the **write** time,
  not the reload time.
- Legacy `id_map.json` without the stamp loads fine and reports `null`.

**Deliberately rejected**: falling back to `id_map.json` mtime for legacy
sets — mtime reflects checkout/copy time in many deployments, and showing
a wrong time is worse than `null` for a user-facing "last updated" label.

## 3. Files changed (steps 1-2)

- `semantic-search/lawcast_semantic/indexing.py` — stamp in `save()`
- `semantic-search/lawcast_semantic/search.py` — `index_updated_at` on the
  searcher, populated in `load()`
- `semantic-search/service/app.py` — adopt at `mark_ready`/`reload`;
  `record_update` reduced to result/error; `SearchResponse.lastUpdateAt`
  (step 2) + `/search` populates it from the snapshot
- `semantic-search/service/update_runner.py` — `run_reload` docstring updated
- `semantic-search/README.md` — `/health` + `/search` field semantics
- `backend/src/modules/semantic-search/semantic-search.types.ts` — one-field
  contract mirror (type only; cross-language pin requires it)
- `semantic-search/tests/test_update_runner.py` — stamp / dual-surface /
  tick-ownership / reload-adoption / legacy-null contract tests + stub fix
- `semantic-search/tests/test_service.py` — stub searchers carry
  `index_updated_at`; dual-surface contract test

Verification: `ruff check` + `ruff format --check` clean, **119 passed**;
backend `semantic-search.contract.spec.ts` 3/3; `tsc --noEmit` clean.

## 4. Step 2 (implemented): sidecar ships the time on the main responses

- `SearchResponse` gained `lastUpdateAt: str | None`, populated from the
  same snapshot `/health` uses — one call to `GET /search` now returns the
  results *and* the index time (the decider's requirement: no second call).
  `POST /reload` returns `health()`, so it carried the field all along.
- **CRITICAL — the `/search` contract is dual-owned**: `SearchResponse`
  (Python) is pinned field-by-field against
  `backend/src/modules/semantic-search/semantic-search.types.ts::SemanticSidecarSearchResponse`
  by `semantic-search.contract.spec.ts` (Jest, `toEqual`). Adding a field
  to one side **requires** mirroring it on the other or backend CI fails.
  The TS side is a type-only mirror — no backend logic was touched in
  step 2 (controller/service/UI belong to step 3).
- Contract tests (fail-first verified with `KeyError: 'lastUpdateAt'`):
  - `test_service.py::test_last_update_at_reported_on_health_and_search`
    — field on both surfaces, value == serving generation's stamp.
  - `test_update_runner.py::test_responses_report_serving_index_updated_at`
    — real artifacts: health + search == id_map `updated_at` == adopted
    `state.last_update_at`.
  - `test_update_runner.py::test_legacy_id_map_without_stamp_reports_null`
    — legacy null rule on both surfaces.

## 5. Step 3 (implemented): backend -> frontend display

Value flow (one request, no extra call anywhere):

`VectorIndex.save` stamp -> `EngineState` -> sidecar `SearchResponse.lastUpdateAt`
-> `SemanticSearchService.collectChunks` (last successful window)
-> `SemanticSearchResponse.lastUpdateAt` (controller passes through, envelope
`success/data`) -> frontend `SemanticSearchResponse` type ->
`+page.svelte` line `마지막 업데이트: <KST time | 기록 없음>`.

- Rule table pinned by tests:

  | Path                                            | `lastUpdateAt` |
  | ----------------------------------------------- | -------------- |
  | semantic hits (sidecar answered)                | sidecar stamp  |
  | keyword fallback after sidecar answered (no hits) | sidecar stamp  |
  | keyword fallback, engine down / disabled        | `null`         |
  | legacy artifacts (no stamp)                     | `null` -> `기록 없음` |

- Backend: `semantic-search.types.ts` (`SemanticSearchResponse` field),
  `semantic-search.service.ts` (`collectChunks` returns
  `{chunks, lastUpdateAt}`; `fetchChunks` returns the full payload;
  `keywordFallback` takes an optional `lastUpdateAt = null`). Controller
  unchanged (pass-through, pinned by its spec).
- Frontend: `lib/types/api.ts` field; display line at the top of the
  results region (single `{#if response}` block, `data-testid=
  "semantic-search-last-update"`), reusing `formatDateTimeKST` (fixed KST,
  timezone-deterministic for tests).
- Contract tests: backend service spec (3 assertions: semantic stamp /
  first-window-failure null / no-hits stamp), controller pass-through
  `toEqual`, frontend e2e `semantic-search.spec.ts` (value shows time +
  new `기록 없음` null case; `semanticEnvelope` carries `lastUpdateAt`).

## 6. Remaining mission steps

- None — mission complete. Before merge/release per AGENTS.md:
  `semantic-search/pyproject.toml` version bump + tag (not done in these
  passes).

## 7. Gotchas for follow-up passes

- **Never** re-introduce a second writer of the time (e.g. stamping in
  `record_update` or in `reload()` itself) — the stamp must describe the
  artifact write, not the reader.
- `updated_at` participates in `artifact_snapshot` byte comparisons in
  tests: those compare before/after around *no-write* paths, so they stay
  equal; do not add tests comparing id_map bytes across two different
  builds (they legitimately differ by the stamp).
- Stub searchers (`SimpleNamespace`) passed to `mark_ready` must include
  `index_updated_at` — direct attribute access, fail loud on contract drift.
