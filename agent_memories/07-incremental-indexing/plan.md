# Incremental Index Updates for semantic-search (Design)

## H1 topic: replacing full-corpus rebuilds with notice-level incremental updates

Rebuild cost measured on the production corpus (20,919 notices / 96,754 chunks):
stage 1 chunking ~4s, stage 2 embedding ~40 min (MPS), stage 3 index build
seconds. Only stage 2 is expensive, so the design goal is: **embed only chunks
whose embedded text actually changed**, and let everything else be derived.

---

## 1. How consistency is enforced today (read of the current system)

### 1.1 Artifact set and roles

| Artifact | Role | Contents |
| --- | --- | --- |
| `artifacts/chunks.jsonl` | canonical chunk set | one `Chunk.to_dict` per line |
| `artifacts/embeddings.npz` | derived matrix | `embeddings`, `chunk_ids`, `chunks_fingerprint`, `model_name` |
| `artifacts/faiss.index` + `artifacts/id_map.json` | derived index | index rows positional; `id_map` payload = `{chunk_ids, chunks_fingerprint, model_name}` |

Row identity is **positional**: FAISS row `i` corresponds to `chunk_ids[i]`.
The same matrix exists twice (npz and index) and must never diverge.

### 1.2 The fingerprint is a whole-set invariant

`compute_chunks_fingerprint(records)` (in `lawcast_semantic/chunking.py`) is a
SHA-256 over the records **sorted by chunk_id**, so it is an order-independent
**set hash** of `chunk_id + '\0' + compose_embedding_text(subject, text) + '\n'`.

`SemanticSearcher.load` rejects the artifact set unless:

1. `chunks_fingerprint` (in id_map) equals the fingerprint recomputed from
   `chunks.jsonl`,
2. `model_name` matches the query embedder,
3. index dimension matches the embedder.

### 1.3 Why the README 교체 규칙 forbids partial replacement

The fingerprint authenticates one statement: *"this index embeds exactly this
chunk set."* It carries no per-row provenance — nothing in the artifacts says
which vector was computed from which text. Therefore:

- Appending rows to `faiss.index` alone leaves `chunk_ids` and the stored
  fingerprint describing the old set; load either fails or, if the fingerprint
  were patched by hand, would vouch for rows nobody can prove.
- Deleting rows shifts every positional row mapping.
- The only sound repair has been: rebuild stages 1-3 as one set. That is what
  the README documents and what `SemanticSearcher.load` enforces.

The missing piece is exactly per-row provenance. Add it, and partial
replacement becomes sound without weakening any existing check.

---

## 2. Design decisions

### 2.1 Scope: append + update + delete (notice-keyed chunk replacement)

**Decision: all three.** The corpus source (`notice_archives`) is mutable in
practice:

- `proposalReason` is backfilled after the fact (NSM refetch fills empty
  reasons; the DB carries partial indexes for exactly those gaps),
- subjects/committees get corrected,
- rows leave the searchable set (`lifecycle_status` / `source_deleted_at`
  transitions).

Tradeoffs considered:

| Scope | Pros | Cons |
| --- | --- | --- |
| append-only (new notices) | simplest | stale vectors survive corrections forever; deletion cannot be expressed at all, so the set fingerprint would break the first time a row disappears |
| append + update + delete | artifacts always equal a full rebuild of the current corpus | update re-embeds one notice (seconds); delete is free (row drop) |

Delete is not optional even for an "additions mostly" workload: the invariant
is set equality with the corpus, and sets shrink. Update/delete granularity is
the **notice** (`chunk_id = {notice_num}-{chunk_index:04d}`); finer reuse is
free via per-chunk digests (2.2): a notice edited at the tail keeps its early
chunks byte-identical and their rows are reused.

**DB reality check (discovered during verification):** `notice_archives` has
immutability triggers — content columns (incl. `proposalReason`) cannot change
after archive and physical DELETE is forbidden; only `lifecycle_status`
transitions `active -> source_deleted/renumbered` are legal. So in production
the update/delete paths serve: (a) JSONL snapshot corpora (first-class corpus
source) being corrected, (b) corpus-selection changes such as excluding
`source_deleted` notices, (c) any future schema relaxation. Supporting all
three costs little (delete is free, update is one notice) and keeps the
invariant "artifacts == full rebuild of the current corpus" total, which is
also what makes the equivalence argument in section 3 hold unconditionally.

**Explicit non-goals:** model swap and chunking-parameter changes are full
rebuilds. A model mismatch is refused with an error (old vectors are from
another model; silently mixing them is exactly what the fingerprint exists to
prevent). A chunking-parameter change makes every digest change, so an
incremental run would correctly re-embed everything — that works but costs the
same as a rebuild; the README will say "run 01-03" for that case.

### 2.2 Consistency: chunks.jsonl is the identity source; per-chunk digests are row provenance

**Identity source of truth:** the chunk set derived from the corpus by
`chunk_notices()` — deterministic and cheap (~4s for the full corpus). Every
incremental run re-chunks the whole corpus and diffs against the committed
`chunks.jsonl`. Consequences:

- **Change detection is content-derived, not timestamp-based.** The table has
  no `updated_at`; `archived_at` does not move on backfill. Content digests
  cannot miss a change and never need a maintenance job.
- **No state file exists that can drift or corrupt.** State = artifacts + DB.
  If all artifacts are lost, a full rebuild reproduces them exactly.

**Row provenance:** `embeddings.npz` gains one optional member,
`chunk_text_digests` — per-row SHA-256 of `chunk_id + '\0' + embedded_text`
(the same per-item digest the set fingerprint is composed of). A stored vector
is reusable **iff** its stored digest equals the digest of the chunk's current
embedded text. Because each row self-describes the text it was computed from,
reuse is safe under **any** crash interleaving — there is no generation-skew
hazard to reason about.

Legacy npz (built by stage 2 without the member): if its set fingerprint
equals the fingerprint of current `chunks.jsonl`, row correspondence is proven
by the set hash and digests are derived from `chunks.jsonl` (then stamped on
the next write). Otherwise the run refuses with a rebuild instruction — a
state reachable only from a crash mid-update on a legacy npz followed by a
corpus change.

**Write order** (each file via temp + `os.replace`, atomic per file):

1. `embeddings.npz`
2. `id_map.json`
3. `faiss.index`
4. `chunks.jsonl` (commit point)

Every partial interleaving leaves either the complete old generation (load
passes on it) or a mix that fails the existing fingerprint validation.
**Crash recovery = rerun `06_incremental_update.py`.** Per-chunk digests make
the rerun idempotent and minimal: it embeds exactly the chunks lacking a valid
vector, which after a crash is only the work that was lost.

Additionally `SemanticSearcher.load` gains one cross-check: `index.ntotal ==
len(chunk_ids)`, so an index/id_map skew fails loudly instead of serving
mislabelled hits.

### 2.3 Fingerprint stance: incremental output passes the EXISTING validation unchanged

**Decision: no incremental marker in the artifact contract.** The fingerprint
answers "do these artifacts belong together?", not "how were they built?".
Incrementality is a build *method*; if the result equals the full-rebuild
result, tagging it would create two artifact classes for the validator to
treat differently — and the incremental class would have to be held to a
*weaker* invariant (a provenance flag proves nothing about consistency).
Consumers would gain a branch that breaks substitutability for zero safety.

Where incrementality legitimately lives:

- **inside the artifact**: `chunk_text_digests` is honest per-row provenance
  ("this vector was computed from this text") and is what makes incremental
  writes sound;
- **in the producer**: `scripts/06_incremental_update.py` documents and
  reports what changed (added/updated/deleted notices, reused/embedded/dropped
  rows).

The README 교체 규칙 is amended accordingly: the set must still be replaced
(or produced) as a *consistent* set, but two producers are now legal —
`01→02→03` (full) and `06` (incremental) — both emitting artifacts that pass
`SemanticSearcher.load` untouched.

---

## 3. Algorithm

```
plan_update(notices, chunks_path, embeddings_path):
    new_records  = chunk_notices(notices)          # canonical set, full-rebuild order
    old_records  = load_chunks_jsonl(chunks_path)  # committed generation (may be absent)
    stored       = npz(chunk_ids, chunk_text_digests | legacy fallback)
    for record in new_records:
        if stored.digest(record.chunk_id) == compute_chunk_text_digest(record):
            reuse stored row
        else:
            embed record
    dropped = stored rows whose chunk_id is not in new_records
    summarize added / updated / deleted notices (grouped by notice_num)

apply_update(plan, embed_texts, model_name, paths):
    new_vectors = embed_texts(compose_embedding_text(r) for r in plan.embed_records)
    merged matrix in new_records order (reuse rows by chunk_id)
    fingerprint = compute_chunks_fingerprint(new_records)
    write npz(+ chunk_text_digests) -> id_map -> index -> chunks.jsonl
```

The script calls plan then apply separately and loads the embedding model
**only when the plan needs embedding**, so a no-change run is seconds and
downloads nothing.

### Why full rebuild == incremental (equivalence argument)

- `chunks.jsonl`: byte-identical — same `chunk_notices` over the same corpus in
  the same deterministic order.
- `chunks_fingerprint`: set hash over `chunk_id + embedded text` — equal iff
  the chunk sets and texts are equal.
- vectors: reused rows are literally the previous rows; re-embedded rows are a
  deterministic function of the same text (same model).
- index: rebuilt from the merged matrix by the same `VectorIndex.build`.

So the two artifact sets agree up to float noise in re-embedded rows; the
verification below checks chunk sets, fingerprints, and actual search results.

---

## 4. Verification plan

Executed — the plan items are the §6 subsections (unit suite, V1 sample
equivalence, V2 full-corpus equivalence, V2b live scenarios, V3/V4 crash
repair + idempotence, gates).

## 5. Files

- `semantic-search/lawcast_semantic/chunking.py` — `compute_chunk_text_digest`
  (per-row provenance atom; lives here so the torch-only stage 2 can stamp it
  without importing faiss).
- `semantic-search/lawcast_semantic/incremental.py` —
  `plan_update` / `apply_update`, atomic writers.
- `semantic-search/scripts/06_incremental_update.py` — CLI
  (`--db`/`--input`, `--plan-only`, artifact path overrides), lazy model load,
  `use_single_threaded_omp()` before any faiss/torch import.
- `semantic-search/scripts/02_extract_embeddings.py` — stamps
  `chunk_text_digests` into npz (additive member).
- `semantic-search/lawcast_semantic/search.py` — `ntotal == len(chunk_ids)`
  cross-check (tightening, same contract).
- `semantic-search/tests/test_incremental.py` (+ entrypoint tests).

---

## 6. Verification results (2026-09-30)

All behavioral; harness = stub embedder in `tests/test_incremental.py` plus
real-model runs against the KURE-v1 corpus.

### 6.1 Unit suite

69 passed (53 pre-existing + 16 new), `ruff check` + `ruff format --check`
clean. New coverage: plan detection (add/update/delete), full-rebuild vs
incremental equivalence, update/delete scenarios, load-validation pass,
model-mismatch refusal, both crash-window repairs, legacy npz fallback and
refusal, empty-corpus delete-all, script no-op without model load.

### 6.2 V1 sample equivalence (real model, 300 notices / 1,973 chunks)

`01-03` full rebuild vs (`01-03` on 200-notice subset + `06` to the same
corpus):

- `chunks.jsonl` byte-identical; `id_map.json` byte-identical
- `embeddings.npz`: all members exactly equal (`np.array_equal`, max abs
  diff 0.0) — re-embedded rows reproduced the full-build vectors bit-for-bit
- identical `chunks_fingerprint` (`364dd361b9ac`)
- search parity: 10 queries, top-10 identical (chunk_id + score)

### 6.3 V2 full-corpus equivalence (20,919 notices / 96,754 chunks)

"Past" fabricated by pruning 50 notices (263 chunks, legacy npz) from the
production artifacts — no re-embedding needed to make the past — then `06`
back to the exact build corpus:

- embedded exactly 263 chunks, reused 96,491
- `chunks.jsonl` byte-identical to the production full rebuild; `id_map.json`
  byte-identical; all 96,754 `chunk_ids` identical
- embeddings max abs diff **0.0** (exactly equal) incl. the re-embedded rows
  vs their 40-min-build originals; identical fingerprint (`60777828c403`)
- search parity: 29 queries (24 holdout + 5 ad-hoc), top-10 identical
- legacy npz auto-upgraded with 96,754 `chunk_text_digests`

### 6.4 V2b live scenarios (DB clone + artifacts clone)

One run against a mutated DB clone (guard triggers dropped in the clone only):
added synthetic notice + real new notice `2221592`, updated `2219936`
proposalReason, deleted `2200001` — plan reported exactly `added=[2221592,
9900001] updated=[2219936] deleted=[2200001]`, embedded 7 chunks, reused
96,735, dropped 18 rows. Behavior: updated/added notices are top hits for
marker queries (e.g. `2219936-0000` score 0.725), deleted notice absent from
results and from `chunks.jsonl`/npz.

### 6.5 V3/V4 crash repair + idempotence (same scale)

- Second run on unchanged DB: 0 embedded, `artifacts: unchanged`.
- Torn state (`chunks.jsonl` rolled back = crash before commit point): rerun
  re-embedded **0** chunks (every stored row self-describes its text), rewrote
  artifacts, converged byte-identical to the pre-crash state.
- Incremental output passes `SemanticSearcher.load` unchanged (fingerprint /
  model / dim / row-count gates).

### 6.6 Live run + gates

- Live `06 --db` on production: 1 added notice (`2221592`, 3 chunks) embedded
  in seconds, 96,754 reused; sidecar restarted, `/health` reports
  `indexedChunks: 96757` (matches `chunks.jsonl`), live `/search` returns the
  identical pre-update top hit and score (`2219936-0000`, 0.7360).
- Holdout eval (24 queries) unchanged vs baseline: r@1 0.042 / r@5 0.292 /
  MRR 0.170; default eval (16 queries): r@5 0.812 / MRR 0.559 — both exactly
  the recorded full-corpus values.
- `pytest` 69 passed; `ruff check` + `ruff format --check` clean.
